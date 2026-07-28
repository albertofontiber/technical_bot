"""s286 — TRAZA hp018 (PRIORIDAD-1 seguridad, DEC-160c): frecuencia de «en serie» + chunk inductor.

Reproduce K veces la pregunta hp018 por el MISMO seam que el harness bvg (run_bot espejado de
scripts/test_bot_vs_gold.py, sin juez — solo necesitamos el texto) bajo paridad de flags
(CHUNKS_TABLE=chunks_v2 + HYQ_TABLE=on + VISUAL_ASSETS_REGISTRY=on, DEC-157).
Por corrida: respuesta completa, matches de la clase peligrosa con contexto, fuentes servidas y
qué chunks servidos contienen 'serie'. Salida: evals/s286_hp018_trace_v1.jsonl + resumen stdout.
Diagnóstico puro: 0 escrituras, no cambia el sistema.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("HYQ_TABLE", "on")
os.environ.setdefault("VISUAL_ASSETS_REGISTRY", "on")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from src.config import RETRIEVAL_TOP_K as RETRIEVE_K, RERANK_TOP_K as RERANK_K  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402

QUESTION = "¿Cómo se conecta una sirena convencional en las salidas de sirena de la Morley ZXe?"
K = int(os.getenv("TRACE_K", "10"))
PELIGRO = re.compile(r"en\s+serie", re.IGNORECASE)
DEST = os.path.join("evals", "s286_hp018_trace_v1.jsonl")


def _strict_rerank(query, chunks, **kw):
    return rerank(query, chunks, strict=True, **kw)


def run_bot(query: str) -> dict:
    pipeline = execute_rag_turn(
        query=query,
        query_for_retrieval=query,
        target_models=None,
        available_models=None,
        retrieval_top_k=RETRIEVE_K,
        rerank_top_k=RERANK_K,
        adapters=RagServingAdapters(
            retrieve=retrieve_chunks,
            rerank=_strict_rerank,
            observe_structural_shadow=observe_structural_neighbor_shadow,
            generate=generate_answer,
        ),
    )
    return pipeline


def main() -> None:
    rows = []
    hits = 0
    for i in range(K):
        t0 = time.time()
        try:
            p = run_bot(QUESTION)
        except Exception as exc:  # una corrida caída no debe tirar la traza entera
            rows.append({"run": i, "error": str(exc)[:400]})
            print(f"run {i}: ERROR {str(exc)[:120]}")
            continue
        chunks = p["chunks"]
        res = p["generation"]
        answer = res.get("answer") if isinstance(res, dict) else str(res)
        matches = []
        for m in PELIGRO.finditer(answer or ""):
            a, b = max(0, m.start() - 140), min(len(answer), m.end() + 140)
            matches.append(answer[a:b])
        served = [
            {
                "id": c.get("id"),
                "source_file": c.get("source_file"),
                "page": c.get("page_number"),
                "contiene_serie": bool(PELIGRO.search(c.get("content") or "")),
            }
            for c in chunks
        ]
        row = {
            "run": i,
            "secs": round(time.time() - t0, 1),
            "len": len(answer or ""),
            "peligro_matches": matches,
            "n_matches": len(matches),
            "sources": sorted({c.get("source_file") for c in chunks if c.get("source_file")}),
            "served": served,
            "coverage_status": p["coverage_trace"].get("status"),
            "answer": answer,
        }
        rows.append(row)
        if matches:
            hits += 1
        print(f"run {i}: {len(matches)} match(es) · {row['secs']}s · servidos con 'serie': "
              f"{[s['source_file'] + ':' + str(s['page']) for s in served if s['contiene_serie']]}")

    with open(DEST, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in rows if "error" not in r]
    print(f"\nRESUMEN: {hits}/{len(ok)} corridas con la frase peligrosa "
          f"({len(rows) - len(ok)} errores) → {DEST}")


if __name__ == "__main__":
    main()
