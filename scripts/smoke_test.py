"""
Smoke test for the RAG pipeline — runs 6 representative queries (2 per
manufacturer) end-to-end through retrieve → rerank → generate, and prints
the answers + basic shape checks.

Use BEFORE deploying to Railway (or after major code changes) to confirm the
pipeline still produces non-empty, on-topic answers. Costs ~$0.10-0.30 in
API calls (Anthropic + OpenAI embeddings).

Usage:
    python -m scripts.smoke_test                # all 6 queries
    python -m scripts.smoke_test --quick        # 3 queries, one per manufacturer
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Force UTF-8 stdout so ✓/✗ render on Windows consoles (cp1252 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import validate_config, RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.retriever import retrieve_chunks, extract_product_models  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


SMOKE_QUERIES = [
    # Detnov
    ("Detnov-1", "¿Cuál es la tensión de alimentación del CAD-150-8?"),
    ("Detnov-2", "¿Cómo se conecta el módulo MAD-461 al lazo?"),
    # Notifier
    ("Notifier-1", "¿Qué centrales tienes documentadas de Notifier?"),
    ("Notifier-2", "Especificaciones técnicas de la NFS2-3030"),
    # Morley
    ("Morley-1", "¿Qué modelos de Morley tienes documentados?"),
    ("Morley-2", "Procedimiento de instalación de un lazo en una central Morley"),
]


def run_query(qid: str, query: str) -> tuple[bool, str, float]:
    """Run a single query through the pipeline. Returns (ok, summary, elapsed_s)."""
    start = time.time()
    try:
        target_models = extract_product_models(query)
        chunks = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K)
        chunks = rerank_chunks(query, chunks, top_k=RERANK_TOP_K, target_models=target_models)
        result = generate_answer(query, chunks)
        answer = result.get("answer", "")
        diagrams = result.get("diagrams", [])
        elapsed = time.time() - start

        if not answer or len(answer.strip()) < 30:
            return False, f"answer too short: {len(answer)} chars", elapsed
        return True, f"{len(chunks)} chunks, {len(answer)} chars, {len(diagrams)} diagrams", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, f"exception: {e}", elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="Run only 3 queries (one per manufacturer)")
    args = parser.parse_args()

    validate_config()
    logger.info("Config validated.")

    queries = SMOKE_QUERIES
    if args.quick:
        queries = [SMOKE_QUERIES[0], SMOKE_QUERIES[2], SMOKE_QUERIES[4]]

    print(f"\n=== Smoke test: {len(queries)} queries ===\n")
    results = []
    for qid, q in queries:
        print(f"[{qid}] {q}")
        ok, summary, elapsed = run_query(qid, q)
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status} ({elapsed:.1f}s) — {summary}\n")
        results.append((qid, ok, elapsed))

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    total_time = sum(t for _, _, t in results)
    print("=" * 50)
    print(f"Result: {passed}/{total} passed in {total_time:.1f}s total")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
