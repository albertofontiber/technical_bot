#!/usr/bin/env python3
"""s289 G-1 — sweep-39 de COMPOSICIÓN de los 2 fixes de orden/fallback (dúo r3).

Diseño del gate: `evals/s289_etapa2_order_fixes_design_v1.md` §Plan de
verificación (re-diseñado por el crítico S1 de Sol: con el pool
VENTANA-DEPENDIENTE, comparar on-vs-HEAD end-to-end no atribuye — TODOS los
brazos corren sobre la MISMA captura serializada).

FASES
  capture  (pagada, UNA vez, idempotente): 39 golds dev × `execute_rag_turn`
           con generate NO-OP → congela {pool completo, prefijo topk} + la
           composición in-capture (referencia de fidelidad del replay).
           Coste declarado: 39 embeddings Voyage + 39 llamadas del reranker
           LLM. 0 generación, 0 juez.
  arms     ($0 LLM): OFF / ON / OFF-replica → `apply_profiled_post_rerank_
           coverage` sobre la MISMA captura (deepcopy por brazo). Flags vía
           override DECLARADO post-DEMO_FLAGS (contrato s289 §flags).
           - `capture_appended == arm OFF` ⇒ fidelidad del replay (si no, STOP
             harness).
           - `OFF == OFF-replica` ⇒ estabilidad de lecturas vivas del RPC
             (patrón DEC-096b; si no, STOP harness).
           - diff OFF→ON = la LISTA de golds para G-3 (per-fact pareado).

Uso:
  python scripts/s289_order_fixes_sweep.py capture   # pagada, idempotente
  python scripts/s289_order_fixes_sweep.py arms      # $0, exige captura
Salidas:
  evals/s289_g1_sweep39_capture_v1.json.gz   (pools+prefijos completos)
  evals/s289_g1_sweep39_result_v1.json       (diffs por gold, sin contenidos)
  evals/s289_g1_sweep39_report_v1.md         (veredicto G-1 legible)
"""
from __future__ import annotations

import copy
import gzip
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Importar el instrumento PIN-ea DEMO_FLAGS (paridad exacta de entorno con la
# medición v3.1) y trae sus adapters de captura/rerank estricto.
import scripts.factlevel_assessment as fla  # noqa: E402  (side-effect: DEMO_FLAGS)
from scripts.gold_store import verified  # noqa: E402
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402

CAPTURE_PATH = ROOT / "evals" / "s289_g1_sweep39_capture_v1.json.gz"
RESULT_PATH = ROOT / "evals" / "s289_g1_sweep39_result_v1.json"
REPORT_PATH = ROOT / "evals" / "s289_g1_sweep39_report_v1.md"

TREATMENT_FLAGS = ("FACET_COMPLEMENT_FALLBACK", "OBLIGATION_RESERVE_ORDERED")


def _noop_generate(question: str, chunks: list[dict], **_kwargs) -> dict:
    return {"answer": ""}


def _flag_set_receipt() -> dict[str, str]:
    """Flag-set efectivo del proceso (los DEMO_FLAGS + tratamiento) — cada
    brazo lo estampa en su recibo (contrato s289 §flags, hallazgo S3=A2)."""
    receipt = dict(fla.DEMO_FLAGS)
    for name in TREATMENT_FLAGS:
        receipt[name] = os.environ.get(name, "off")
    return receipt


def _set_treatment(value: str) -> None:
    for name in TREATMENT_FLAGS:
        os.environ[name] = value


def capture() -> None:
    if CAPTURE_PATH.exists():
        print(f"captura YA existe (idempotente): {CAPTURE_PATH}")
        return
    _set_treatment("off")  # la captura corre el ship actual
    golds = verified()
    print(f"capture: {len(golds)} golds dev · coste declarado = "
          f"{len(golds)} embeddings + {len(golds)} rerank LLM · 0 generación")
    out: dict[str, dict] = {}
    for i, gold in enumerate(golds):
        qid, query = gold["qid"], gold["question"]
        t0 = time.time()
        pipeline: dict = {}
        for _attempt in range(2):
            pipeline = execute_rag_turn(
                query=query,
                query_for_retrieval=query,
                target_models=None,
                available_models=None,
                retrieval_top_k=fla.RETRIEVAL_TOP_K,
                rerank_top_k=fla.RERANK_TOP_K,
                adapters=RagServingAdapters(
                    retrieve=fla._capture_retrieve,
                    rerank=fla._eval_strict_rerank,
                    observe_structural_shadow=fla.observe_structural_neighbor_shadow,
                    generate=_noop_generate,
                ),
            )
            if (pipeline.get("coverage_trace") or {}).get("status") != "error":
                break
        trace = pipeline.get("coverage_trace") or {}
        chunks = pipeline["chunks"]
        n_prefix = pipeline["reranked_rows"]
        out[qid] = {
            "query": query,
            "pool": copy.deepcopy(list(fla._CAPTURED_POOL)),
            "prefix": copy.deepcopy(chunks[:n_prefix]),
            "capture_appended_ids": [
                str(c.get("id") or "") for c in chunks[n_prefix:]
            ],
            "capture_appended_lane": fla._lane_by_appended_id(
                trace, chunks[n_prefix:]
            ),
            "capture_coverage_status": trace.get("status"),
            "capture_degraded": trace.get("status") == "error",
            "secs": round(time.time() - t0, 1),
        }
        print(f"  [{i+1}/{len(golds)}] {qid} pool={len(out[qid]['pool'])} "
              f"prefix={len(out[qid]['prefix'])} "
              f"appended={len(out[qid]['capture_appended_ids'])} "
              f"({out[qid]['secs']}s)")
    payload = {
        "instrument": "s289_g1_sweep39_capture_v1",
        "flag_set": _flag_set_receipt(),
        "n_golds": len(out),
        "golds": out,
    }
    with gzip.open(CAPTURE_PATH, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    print(f"captura -> {CAPTURE_PATH} ({CAPTURE_PATH.stat().st_size/1e6:.1f} MB)")


def _replay_arm(arm: str, treatment: str, captured: dict) -> dict[str, dict]:
    _set_treatment(treatment)
    results: dict[str, dict] = {}
    flag_set = _flag_set_receipt()
    for qid, entry in captured["golds"].items():
        served, trace = apply_profiled_post_rerank_coverage(
            entry["query"],
            copy.deepcopy(entry["prefix"]),
            retrieval_pool=copy.deepcopy(entry["pool"]),
        )
        n_prefix = len(entry["prefix"])
        appended = served[n_prefix:]
        lanes = {}
        for lane_trace in (trace.get("lanes") or []):
            if isinstance(lane_trace, dict):
                for cid in (lane_trace.get("selected_ids") or []):
                    lanes.setdefault(str(cid), lane_trace.get("lane"))
        for row in appended:
            lanes.setdefault(str(row.get("id") or ""), row.get("retrieval_lane"))
        results[qid] = {
            "appended_ids": [str(c.get("id") or "") for c in appended],
            "appended_lane": {
                str(c.get("id") or ""): lanes.get(str(c.get("id") or ""))
                for c in appended
            },
            "served_n": len(served),
            "coverage_status": trace.get("status"),
            # Trazas de atribución de los fixes (vacías con flag off).
            "facet_attempts": next(
                (lt.get("facet_attempts") for lt in (trace.get("lanes") or [])
                 if isinstance(lt, dict) and lt.get("facet_attempts")), None),
            "reserve_discards": next(
                (lt.get("reserve_discards") for lt in (trace.get("lanes") or [])
                 if isinstance(lt, dict) and lt.get("reserve_discards") is not None),
                None),
            "reserve_ranked_ids": next(
                (lt.get("reserve_ranked_ids") for lt in (trace.get("lanes") or [])
                 if isinstance(lt, dict) and lt.get("reserve_ranked_ids")), None),
        }
    return {"flag_set": flag_set, "results": results}


def arms() -> None:
    if not CAPTURE_PATH.exists():
        raise SystemExit("falta la captura: corre primero `capture`")
    with gzip.open(CAPTURE_PATH, "rt", encoding="utf-8") as fh:
        captured = json.load(fh)
    print(f"arms sobre captura de {captured['n_golds']} golds ($0 LLM)")
    arm_off = _replay_arm("off", "off", captured)
    arm_on = _replay_arm("on", "on", captured)
    arm_replica = _replay_arm("off_replica", "off", captured)

    fidelity_fail, replica_fail, diffs = [], [], {}
    for qid, entry in captured["golds"].items():
        off = arm_off["results"][qid]
        on = arm_on["results"][qid]
        rep = arm_replica["results"][qid]
        if off["appended_ids"] != entry["capture_appended_ids"]:
            fidelity_fail.append(qid)
        if off["appended_ids"] != rep["appended_ids"]:
            replica_fail.append(qid)
        if off["appended_ids"] != on["appended_ids"]:
            off_set, on_set = set(off["appended_ids"]), set(on["appended_ids"])
            diffs[qid] = {
                "off_appended": off["appended_ids"],
                "on_appended": on["appended_ids"],
                "gained": sorted(
                    {(cid, on["appended_lane"].get(cid)) for cid in on_set - off_set}
                ),
                "lost": sorted(
                    {(cid, off["appended_lane"].get(cid)) for cid in off_set - on_set}
                ),
                "facet_attempts": on["facet_attempts"],
                "reserve_discards": on["reserve_discards"],
                "reserve_ranked_ids": on["reserve_ranked_ids"],
            }

    verdict = "PASS" if not fidelity_fail and not replica_fail else "STOP-HARNESS"
    result = {
        "instrument": "s289_g1_sweep39_result_v1",
        "verdict": verdict,
        "replay_fidelity_fail": fidelity_fail,
        "replica_off_fail": replica_fail,
        "changed_golds": sorted(diffs),
        "n_changed": len(diffs),
        "diffs": diffs,
        "arm_flag_sets": {
            "off": arm_off["flag_set"], "on": arm_on["flag_set"],
            "off_replica": arm_replica["flag_set"],
        },
    }
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    lines = [
        "# s289 G-1 — sweep-39 de composición (OFF / ON / OFF-réplica sobre captura única)",
        "",
        f"- Veredicto del harness: **{verdict}**"
        f" (fidelidad replay: {len(fidelity_fail)} fallos; réplica-OFF: {len(replica_fail)} fallos)",
        f"- Golds con vista servida CAMBIADA (lista para G-3): **{len(diffs)}** — {sorted(diffs)}",
        "",
    ]
    for qid, d in sorted(diffs.items()):
        lines.append(f"## {qid}")
        lines.append(f"- ganadas: {d['gained']}")
        lines.append(f"- perdidas: {d['lost']}")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"veredicto {verdict} · cambiados {len(diffs)}: {sorted(diffs)}")
    print(f"-> {RESULT_PATH}\n-> {REPORT_PATH}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "capture":
        capture()
    elif mode == "arms":
        arms()
    else:
        raise SystemExit("uso: s289_order_fixes_sweep.py {capture|arms}")
