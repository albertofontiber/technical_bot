#!/usr/bin/env python3
"""s92_pin_regen.py — regenera el pool_pin del instrumento s85 con IDENTITY_RESOLVE=on
(plan v2.2 S2: "la famtie NO re-recupera — RE-GENERAR el pin con el flag ON").

Reutiliza los labels GPT ya pagados (facts/votes/manual_pin intactos); solo re-corre
retrieve_chunks(top_k=50) por gold y sustituye pool_pin. top5_ids se VACÍA (sin re-pagar
reranker): los buckets top5/rerank del brazo no son comparables — la métrica es SOLO
retrieval_miss_family (in_pool). Predicciones pre-registradas: evals/s92_f2_predicciones.md.

Uso: python scripts/s92_pin_regen.py add|replace
Salida: evals/s92_retrieval_miss_ON_<arm>.yaml (+ manifest de config estampada)
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml

POOL_K = 50
BASE = ROOT / "evals" / "s85_retrieval_miss_DEF.yaml"


def main() -> int:
    arm = sys.argv[1] if len(sys.argv) > 1 else "add"
    assert arm in ("add", "replace"), arm
    os.environ["IDENTITY_RESOLVE"] = "on"
    os.environ["IDENTITY_RESOLVE_POLICY"] = arm

    from src.rag import catalog_resolver
    from src.rag.retriever import retrieve_chunks
    stamp = catalog_resolver.catalog_commit()
    print(f"arm={arm} · catálogo-commit={stamp}")

    d = yaml.safe_load(open(BASE, encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}
    results = d["reps"][0]["results"]
    for i, res in enumerate(results):
        q = golds[res["qid"]]["question"]
        pool = retrieve_chunks(q, top_k=POOL_K)
        res["pool_pin"] = [{"id": c.get("id"), "pm": c.get("product_model"),
                            "src": c.get("source_file")} for c in pool]
        res["top5_ids"] = []          # no recomputado (sin reranker) — declarado
        print(f"  [{i+1}/{len(results)}] {res['qid']}: pool={len(pool)}")
    d["s92_manifest"] = {"arm": arm, "identity_resolve": "on", "catalog_commit": stamp,
                         "pool_k": POOL_K, "top5": "NO-recomputado", "base": str(BASE.name)}
    out = ROOT / "evals" / f"s92_retrieval_miss_ON_{arm}.yaml"
    yaml.safe_dump(d, open(out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print(f"OK → {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
