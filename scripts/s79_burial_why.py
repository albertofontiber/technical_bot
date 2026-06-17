#!/usr/bin/env python3
"""s79 Paso 0c — ¿POR QUÉ las citas están tan lejos? Caracterización de la causa-raíz del entierro.

Pregunta de Alberto: antes de ampliar el pool (parche), entender por qué el canal vectorial
rankea en pos 53-87 un chunk que CONTIENE la respuesta. Hipotesis a falsar: las citas son
TABLAS/spec-data que embeben mal vs query NL -> enterradas bajo prosa (raiz = contextual-retrieval
/ chunking, no profundidad).

Para cada cita objetivo:
  1. localiza su chunk en vector_search(top_k=300, thr=0) -> rank, similarity, content_type,
     product_model, section_title, tamaño, snippet.
  2. caracteriza QUÉ la entierra: los chunks por ENCIMA (mismo source? mismo product? que content_type?
     near-dups?) -> distingue entierro-por-near-dups vs prosa-gana-a-tabla vs ruido.
Read-only, $0 (embed cacheado). Uso: python scripts/s79_burial_why.py
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
from strict_match import chunk_has_quote_strict  # noqa: E402

# citas recuperables-por-profundidad (rank 53-87) — el caso donde "por qué tan lejos" es la pregunta viva
TARGETS = {
    "hp001": [0, 2], "hp011": [2], "hp017": [0], "cat007": [0, 1], "cat016": [1],
}
DEEP_K = 300


def desc(c):
    return {
        "ct": c.get("content_type"), "pm": c.get("product_model"),
        "sf": (c.get("source_file") or "")[:38], "sec": (c.get("section_title") or "")[:40],
        "len": len(c.get("content") or ""), "sim": round(c.get("similarity", 0), 3),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    report = []
    for qid, idxs in TARGETS.items():
        g = golds[qid]
        quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
        vres = rt.vector_search(g["question"], top_k=DEEP_K, threshold=0.0)
        print(f"\n{'='*70}\n{qid}: {g['question'][:90]}...")
        for qi in idxs:
            q = quotes[qi]
            rank = None; chunk = None
            for i, c in enumerate(vres):
                if chunk_has_quote_strict(c.get("content") or "", q):
                    rank, chunk = i, c
                    break
            if rank is None:
                print(f"  cita[{qi}]: NO en top-{DEEP_K} (deep-miss)")
                report.append({"qid": qid, "qi": qi, "rank": None, "quote": q[:120]})
                continue
            above = vres[:rank]
            ct_above = Counter(c.get("content_type") for c in above)
            pm_above = Counter(c.get("product_model") for c in above)
            sf_above = Counter((c.get("source_file") or "")[:38] for c in above)
            # cuantos por encima son del MISMO source_file que la cita (entierro intra-doc)
            same_sf = sum(1 for c in above if (c.get("source_file") or "")[:38] == (chunk.get("source_file") or "")[:38])
            print(f"  cita[{qi}] @rank {rank}  {desc(chunk)}")
            print(f"     quote: {q[:110]}")
            print(f"     content_type de los {rank} por ENCIMA: {dict(ct_above)}")
            print(f"     mismo source_file que la cita, por encima: {same_sf}/{rank}")
            print(f"     top product_models por encima: {pm_above.most_common(4)}")
            report.append({
                "qid": qid, "qi": qi, "rank": rank, "quote": q[:120],
                "chunk": desc(chunk),
                "above_content_type": dict(ct_above),
                "above_same_source": f"{same_sf}/{rank}",
                "above_top_pm": pm_above.most_common(5),
            })

    p = ROOT / "evals" / "s79_burial_why.json"
    p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nReporte -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
