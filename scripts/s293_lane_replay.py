#!/usr/bin/env python3
"""s293_lane_replay.py — replay $0 de la ETAPA DE COVERAGE sobre el pool grabado.

Cierra el paso que DEC-169 dejó pre-declarado para cat017#2: «probe $0 de las 2
lanes existentes (RERANK_POOL_COVERAGE off-por-stack-C1; hyq doc_scoped pendiente
A3) … ANTES de diseñar lane nueva», sin encender nada en el stack medido (encender
`RERANK_POOL_COVERAGE` global está descartado en DEC-169: re-abre la stack C1).

Cómo es $0: el pool (50) y el prefijo protegido (top-k 10) se REPRODUCEN del recibo
del FULL v3.2 e hidratan de DB; no se llama a retrieval, ni al reranker (backend
llm), ni al generador.  Solo corre `apply_profiled_post_rerank_coverage`, que es
código determinista.

Fidelidad (auto-verificable): el brazo `baseline` DEBE reproducir exactamente los
`appended_ids` + lanes que estampó el recibo.  Si no los reproduce, el replay no es
fiel y los brazos contrafactuales no valen — el script lo declara en el recibo en
vez de asumirlo (lección #57: una sonda que confirma lo que quiero exige el mismo
escrutinio que un resultado adverso).

Uso:  python scripts/s293_lane_replay.py <qid> <brazo>
      brazos: baseline | pool | hyq
Salida: evals/s293_lane_replay_<qid>_<brazo>.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

QID = sys.argv[1] if len(sys.argv) > 1 else "cat017"
ARM = sys.argv[2] if len(sys.argv) > 2 else "baseline"

# ── Freeze-contract: el MISMO flag-set de la demo que usó el FULL v3.2 ──────────
# FUENTE ÚNICA: se lee `DEMO_FLAGS` de scripts/factlevel_assessment.py por AST (sin
# importar el módulo: sus flags se aplican en import-time y pisarían los overrides
# de brazo, que deben fijarse ANTES de importar el pipeline porque los flags-hoja
# del seam de coverage son boot-resolved).  Copiar el bloque a mano ya falló una vez
# en esta misma sonda: se me quedaron fuera FACET_COMPLEMENT_FALLBACK /
# OBLIGATION_RESERVE_ORDERED y el brazo baseline NO reprodujo el recibo.
def _load_demo_flags() -> dict[str, str]:
    import ast

    source = open(
        os.path.join(os.getcwd(), "scripts", "factlevel_assessment.py"),
        encoding="utf-8",
    ).read()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "DEMO_FLAGS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("no se pudo leer DEMO_FLAGS del instrumento")


DEMO_FLAGS = _load_demo_flags()
ARM_OVERRIDES = {
    "baseline": {},
    "pool": {"RERANK_POOL_COVERAGE": "on"},
    "hyq": {"CANONICAL_HYQ_COVERAGE": "on"},
}
if ARM not in ARM_OVERRIDES:
    raise SystemExit(f"brazo desconocido: {ARM} (baseline|pool|hyq)")

for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v
for _k, _v in ARM_OVERRIDES[ARM].items():
    os.environ[_k] = _v

sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v
for _k, _v in ARM_OVERRIDES[ARM].items():
    os.environ[_k] = _v

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402
from src.rag.retriever import _HYDRATE_SELECT  # noqa: E402

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"
# Carriers de interés declarados por el diagnóstico (DEC-169/171) para cat017#2.
WATCH = ("4c186fb2", "5bb83899", "b0273b01", "809cd704")


def hydrate(ids: list[str]) -> list[dict]:
    rows: dict[str, dict] = {}
    with httpx.Client(timeout=90.0) as client:
        for start in range(0, len(ids), 40):
            batch = ",".join(f'"{cid}"' for cid in ids[start:start + 40])
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{os.environ['CHUNKS_TABLE']}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                },
                params={"select": _HYDRATE_SELECT, "id": f"in.({batch})"},
            )
            resp.raise_for_status()
            for row in resp.json():
                rows[row["id"]] = row
    return [rows[cid] for cid in ids if cid in rows]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    row = [r for r in receipt["per_gold"] if r["qid"] == QID][0]
    query = row["question"]
    pool_ids = list(row["pool_ids"])
    topk_ids = list(row["topk_ids"])
    recorded_appended = list(row.get("appended_ids") or [])
    recorded_lane = dict(row.get("appended_lane") or {})

    pool = hydrate(pool_ids)
    topk = hydrate(topk_ids)
    missing_pool = [cid for cid in pool_ids if cid not in {c["id"] for c in pool}]
    missing_topk = [cid for cid in topk_ids if cid not in {c["id"] for c in topk}]

    served, trace = apply_profiled_post_rerank_coverage(
        query, [dict(c) for c in topk], retrieval_pool=[dict(c) for c in pool]
    )
    served_ids = [str(c.get("id") or "") for c in served]
    appended = served_ids[len(topk):]

    fidelity = {
        "recorded_appended": recorded_appended,
        "replay_appended": appended,
        "equal_set": sorted(recorded_appended) == sorted(appended),
        "equal_order": recorded_appended == appended,
        "missing_from_db_pool": missing_pool,
        "missing_from_db_topk": missing_topk,
    }

    watch = {}
    for prefix in WATCH:
        full = next((cid for cid in pool_ids if cid.startswith(prefix)), None)
        watch[prefix] = {
            "in_pool": full is not None,
            "pool_rank": pool_ids.index(full) if full else None,
            "in_topk": bool(full and full in topk_ids),
            "served_in_replay": bool(full and full in served_ids),
            "appended_in_replay": bool(full and full in appended),
        }

    out = {
        "probe": "s293_lane_replay_v1",
        "qid": QID,
        "arm": ARM,
        "arm_overrides": ARM_OVERRIDES[ARM],
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "query": query,
        "n_pool": len(pool),
        "n_topk": len(topk),
        "n_served_replay": len(served),
        "fidelity_vs_receipt": fidelity,
        "recorded_lane": recorded_lane,
        "coverage_trace": trace,
        "watch_carriers": watch,
    }
    path = os.path.join(
        os.getcwd(), "evals", f"s293_lane_replay_{QID}_{ARM}.json"
    )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    print(f"escrito: {path}")
    print(json.dumps(
        {
            "arm": ARM,
            "fidelidad_baseline": fidelity["equal_order"],
            "appended": appended,
            "status": trace.get("status"),
            "lanes": [
                lane.get("lane") if isinstance(lane, dict) else lane
                for lane in (trace.get("lanes") or [])
            ],
            "watch": {k: v["served_in_replay"] for k, v in watch.items()},
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
