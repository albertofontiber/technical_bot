#!/usr/bin/env python3
"""Paso 0b (s78) — punto-de-muerte por-gold del hecho-respuesta en los 16 retrieval-miss (judge-free, $0).

Confirma/refina los 4 clusters inferidos de s74 (ventana-rerank / within-doc / recall / rerank-elige-mal)
con la traza REAL del pipeline en PROD (flags OFF): para cada CITA del gold (texto literal del manual,
gold_answers_v1.yaml), ¿dónde muere?
  - NO en el pool top-50            -> RECALL (el chunk ni entra: pool/keyword/vector)
  - en pool pero NO en top-5 @800   -> RERANK/WITHIN-DOC (el reranker no lo sube)
       * y si @2400 SÍ entra        -> VENTANA del reranker (cluster A, fix = preview-2400)
       * within-doc si el chunk comparte source_file con muchos del pool (manual largo)
  - en top-5 @800                   -> SERVIDO (esa cita no es el problema)

Reusa la lógica de anclas de s74_lever1_gate0 (chunk_has_quote_strict) + su factcov@800/@2400 ya medido.
La traza de pool es $0 (retrieve_chunks con embed-cache; sin LLM). reach != PASS. Read-only.

Uso: python scripts/retrieval16_deathpoint.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import json
import sys
from collections import Counter
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import src.rag.retriever as rt  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from strict_match import chunk_has_quote_strict  # noqa: E402

RET16 = ["cat007", "cat013", "cat021", "hp006", "hp009", "hp013", "cat016", "hp003",
         "cat017", "hp002", "hp008", "hp001", "hp017", "cat001", "hp011", "hp018"]
GATE0 = json.loads((ROOT / "evals" / "s74_lever1_gate0.json").read_text(encoding="utf-8"))


def set_prod_flags():
    for f in ("LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER", "LEVER2_IDENTITY", "LEVER2_PM_RESCUE"):
        os.environ.pop(f, None)


def quote_rank(pool, quote):
    """rank (0-based pos en el pool) del 1er chunk que contiene la cita; (rank, source_file) o None."""
    for i, c in enumerate(pool):
        if chunk_has_quote_strict(c.get("content") or "", quote):
            return i, (c.get("source_file") or "")[:40]
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    set_prod_flags()
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    out = []
    print("=== Paso 0b: punto-de-muerte por-gold (PROD flags OFF, pool top-50, $0) ===\n")
    for qid in RET16:
        g = golds.get(qid)
        if not g:
            print(f"{qid}: NO ENCONTRADO"); continue
        quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
        pool = rt.retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        src_counts = Counter((c.get("source_file") or "")[:40] for c in pool)
        ranks = []
        for q in quotes:
            r = quote_rank(pool, q)
            ranks.append(r)
        in_pool = [r for r in ranks if r is not None]
        n_miss = sum(1 for r in ranks if r is None)
        # within-doc: ¿los chunks-cita están en un source MUY representado en el pool?
        wd = [(r[0], r[1], src_counts.get(r[1], 0)) for r in in_pool]
        fc800 = GATE0.get("base_off_800", {}).get(qid, {}).get("factcov")
        fc2400 = GATE0.get("batch_2400", {}).get(qid, {}).get("factcov")

        # clasificación del punto-de-muerte
        if not quotes:
            cls = "SIN-CITAS (revisar gold)"
        elif n_miss == len(quotes):
            cls = "RECALL (ninguna cita entra al pool-50)"
        elif fc800 and fc2400 and fc2400[0] > fc800[0]:
            cls = "VENTANA-rerank (preview-2400 rescata) [A]"
        elif in_pool and (fc800 is None or fc800[0] < len(quotes)):
            maxsrc = max((w[2] for w in wd), default=0)
            cls = f"RERANK/WITHIN-DOC (citas en pool rank {[w[0] for w in wd]}, no top-5; max {maxsrc} chunks/source)"
        else:
            cls = "MIXTO/servido (revisar)"

        out.append({"qid": qid, "n_quotes": len(quotes), "n_in_pool": len(in_pool),
                    "n_recall_miss": n_miss, "ranks": [w[0] for w in wd],
                    "fc800": fc800, "fc2400": fc2400, "clase": cls})
        print(f"{qid:7} [{cls}]")
        print(f"        citas={len(quotes)} en_pool={len(in_pool)} recall-miss={n_miss} "
              f"ranks_en_pool={[w[0] for w in wd]}")
        print(f"        top-5 factcov 800->2400: {fc800} -> {fc2400}")
        if wd:
            top_src = src_counts.most_common(3)
            print(f"        pool dominado por: {top_src}")
        print()

    rep = {"meta": {"proposito": "Paso 0b s78 — punto-de-muerte del hecho-respuesta (PROD). judge-free, $0.",
                    "stages": "RECALL(no-pool) / VENTANA(2400-rescata) / RERANK-WITHIN-DOC(pool-no-top5)"},
           "deathpoint": out}
    p = ROOT / "evals" / "s78_retrieval16_deathpoint.yaml"
    p.write_text(yaml.safe_dump(rep, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

    print("=== Resumen por punto-de-muerte ===")
    cnt = Counter(r["clase"].split(" ")[0].split("/")[0] for r in out)
    for cls, n in cnt.most_common():
        print(f"  {cls:14} {n:2}  {[r['qid'] for r in out if r['clase'].startswith(cls.split('(')[0])]}")
    print(f"\nReporte -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
