#!/usr/bin/env python3
"""s79 Paso 0b — rank vectorial CRUDO de las citas faltantes (cierra el hueco del death-stage probe).

Para cada cita que NO entra al pool: ¿a qué profundidad la encuentra el canal vectorial solo?
  - rank R <= effective_top_k         -> estaba; murió en merge/filtros (re-revisar)
  - rank R en (top_k, 200]            -> VECTOR-DEPTH: recuperable subiendo k/ef_search (¿s59?)
  - no en top-200 con threshold 0     -> miss vectorial profundo / genuino
Tambien reporta metadata del chunk macheado (product_model, source_file, status, lang) para ver
si un filtro aguas-abajo lo mataria. Read-only, $0 (embed cacheado). Uso: python scripts/s79_vecrank.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import json
import sys
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

# (qid, [indices de citas faltantes del death-stage probe])
TARGETS = {
    "cat016": [1], "hp001": [0, 2], "hp017": [0, 1], "hp011": [2], "cat007": [0, 1],
}
DEEP_K = 200


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    out = []
    print(f"=== s79 rank vectorial crudo (vector_search solo, top_k={DEEP_K}, threshold=0) ===\n")
    for qid, miss_idx in TARGETS.items():
        g = golds[qid]
        quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
        # vector solo, profundo, sin threshold
        vres = rt.vector_search(g["question"], top_k=DEEP_K, threshold=0.0)
        print(f"{qid:7} (vector devolvio {len(vres)} chunks)")
        for qi in miss_idx:
            q = quotes[qi]
            rank = None; meta = None
            for i, c in enumerate(vres):
                if chunk_has_quote_strict(c.get("content") or "", q):
                    rank = i
                    meta = {"product_model": c.get("product_model"),
                            "source_file": (c.get("source_file") or "")[:45],
                            "similarity": round(c.get("similarity", 0), 3)}
                    break
            if rank is None:
                verdict = f"NO en top-{DEEP_K} -> miss vectorial profundo/genuino"
            elif rank < 50:
                verdict = f"rank {rank} (<50!) -> estaba en alcance vectorial; murio aguas-abajo (RE-REVISAR)"
            else:
                verdict = f"rank {rank} -> VECTOR-DEPTH (recuperable subiendo k/ef_search; territorio s59)"
            out.append({"qid": qid, "quote_idx": qi, "vec_rank": rank, "meta": meta, "verdict": verdict})
            print(f"        cita[{qi}]: {verdict}")
            if meta:
                print(f"                  {meta}")
        print()

    p = ROOT / "evals" / "s79_vecrank.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Reporte -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
