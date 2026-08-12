# -*- coding: utf-8 -*-
"""s320 E1 — Sonda `allowed_sources` PRE/POST escritura tier-A (gate PRIMARIO).

Freeze-contract: evals/s320_e1_freeze_contract_v1.md. Para cada doc tier-A la
query congelada es su pm literal; la métrica es si el source_file del doc entra
en el alcance resuelto (doc_map → allowed_sources) bajo la CONFIG SERVIDA
(IDENTITY_RESOLVE=on + POLICY=replace — la de producción, no el default de
código).

Uso:
    python scripts/s320_e1_sonda_allowed_sources.py --fase pre
    python scripts/s320_e1_sonda_allowed_sources.py --fase post
El recibo acumula ambas fases y evalúa el esperado PRE=ausente / POST=presente.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

# CONFIG SERVIDA (freeze-contract): la de producción C1, no el default de código
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"

from src.rag.catalog_resolver import resolve_for_retrieval  # noqa: E402


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True,
                          cwd=ROOT).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", required=True, choices=("pre", "post"))
    args = ap.parse_args()

    detalle = json.loads(
        (ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json")
        .read_text(encoding="utf-8"))
    tier_a = detalle["tier_a"]

    resultados = []
    for caso in tier_a:
        pm = caso["pm"]
        source = caso["source_file"]
        _models_after, res = resolve_for_retrieval(pm, [pm])
        allowed = (res or {}).get("allowed_sources") or frozenset()
        allowed_norm = {str(a).strip().lower().removesuffix(".pdf")
                        for a in allowed}
        resultados.append({"query": pm, "source_file": source,
                           "presente": source in allowed_norm,
                           "n_allowed": len(allowed)})

    destino = ROOT / "evals" / "s320_e1_sonda_allowed_sources_v1.json"
    recibo = (json.loads(destino.read_text(encoding="utf-8"))
              if destino.exists() else
              {"que_es": ("Sonda PRE/POST del gate primario de E1 "
                          "(freeze: evals/s320_e1_freeze_contract_v1.md)."),
               "config": {"IDENTITY_RESOLVE": "on",
                          "IDENTITY_RESOLVE_POLICY": "replace"}})
    presentes = sum(1 for r in resultados if r["presente"])
    recibo[f"fase_{args.fase}"] = {
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "commit": _commit(),
        "queries": len(resultados),
        "docs_presentes_en_alcance": presentes,
        "detalle": resultados,
    }
    if "fase_pre" in recibo and "fase_post" in recibo:
        pre = {r["source_file"]: r["presente"]
               for r in recibo["fase_pre"]["detalle"]}
        post = {r["source_file"]: r["presente"]
                for r in recibo["fase_post"]["detalle"]}
        flips = [s for s in pre if not pre[s] and post.get(s)]
        ya_presentes_pre = [s for s in pre if pre[s]]
        recibo["veredicto"] = {
            "esperado": "PRE ausente / POST presente por doc",
            "flips_ausente_a_presente": len(flips),
            "ya_presentes_en_pre": ya_presentes_pre,
            "post_aun_ausentes": [s for s in post if not post[s]],
            "gate": ("PASS" if len(flips) == len(pre) else
                     "REVISAR (ver listas)"),
        }
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"fase {args.fase}: {presentes}/{len(resultados)} presentes · "
          f"commit {_commit()}")
    if "veredicto" in recibo:
        print(f"veredicto: {recibo['veredicto']['gate']} · "
              f"flips {recibo['veredicto']['flips_ausente_a_presente']}"
              f"/{len(tier_a)}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
