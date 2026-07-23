"""Single orchestration seam for one production RAG turn.

The Telegram handler and deterministic release gates call this same function.
Only I/O boundaries are injectable, which lets tests replay a frozen retrieval
without bypassing rerank, coverage, or the generator boundary.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import logging
from typing import Any, Callable

from .coverage_runtime import apply_profiled_post_rerank_coverage

logger = logging.getLogger(__name__)
MAX_COVERAGE_APPEND_ROWS = 4


@dataclass(frozen=True)
class RagServingAdapters:
    retrieve: Callable[..., list[dict[str, Any]]]
    rerank: Callable[..., list[dict[str, Any]]]
    observe_structural_shadow: Callable[[str, list[dict[str, Any]]], None]
    generate: Callable[..., dict[str, Any]]
    structural_fetcher: Callable[..., tuple[list[dict], list[dict], dict]] | None = None
    document_local_fetcher: Callable[..., tuple[
        list[dict], list[dict], dict
    ]] | None = None


def execute_rag_turn(
    *,
    query: str,
    query_for_retrieval: str,
    target_models: list[str] | None,
    available_models: list[str] | None,
    retrieval_top_k: int,
    rerank_top_k: int,
    adapters: RagServingAdapters,
) -> dict[str, Any]:
    """Execute retrieval -> rerank -> coverage -> generation once.

    Shadow and coverage failures remain fail-open per request. Retrieval,
    reranking, and generation failures are intentionally left to the transport
    handler's existing error boundary.
    """
    retrieved = adapters.retrieve(query_for_retrieval, top_k=retrieval_top_k)
    retrieval_pool = list(retrieved)
    reranked = adapters.rerank(
        query,
        retrieved,
        top_k=rerank_top_k,
        target_models=target_models,
    )
    if not isinstance(reranked, list) or any(
        not isinstance(row, dict) for row in reranked
    ):
        raise TypeError("reranker must return a list of chunk mappings")
    protected_prefix = copy.deepcopy(reranked)

    try:
        adapters.observe_structural_shadow(query, copy.deepcopy(protected_prefix))
    except Exception as exc:
        logger.warning(
            "structural-neighbor shadow failed open (%s)", type(exc).__name__
        )

    try:
        coverage_kwargs = {}
        if adapters.structural_fetcher is not None:
            coverage_kwargs["structural_fetcher"] = adapters.structural_fetcher
        if adapters.document_local_fetcher is not None:
            coverage_kwargs["document_local_fetcher"] = adapters.document_local_fetcher
        served, coverage_trace = apply_profiled_post_rerank_coverage(
            query,
            copy.deepcopy(protected_prefix),
            retrieval_pool=copy.deepcopy(retrieval_pool),
            **coverage_kwargs,
        )
        if not isinstance(coverage_trace, dict):
            raise TypeError("coverage trace must be a mapping")
        if not isinstance(served, list) or any(
            not isinstance(row, dict) for row in served
        ):
            raise TypeError("coverage must return a list of chunk mappings")
        if len(served) < len(protected_prefix):
            raise ValueError("coverage removed rows from the protected prefix")
        if len(served) > len(protected_prefix) + MAX_COVERAGE_APPEND_ROWS:
            raise ValueError("coverage exceeded the bounded append capacity")
        if served[: len(protected_prefix)] != protected_prefix:
            raise ValueError("coverage mutated or reordered the protected prefix")

        appended_ids = [
            str(row.get("id") or "") for row in served[len(protected_prefix) :]
        ]
        if any(not chunk_id for chunk_id in appended_ids):
            raise ValueError("coverage appended a chunk without an identity")
        if len(set(appended_ids)) != len(appended_ids):
            raise ValueError("coverage appended duplicate chunk identities")
        protected_ids = {
            str(row.get("id") or "") for row in protected_prefix if row.get("id")
        }
        if protected_ids.intersection(appended_ids):
            raise ValueError("coverage appended an identity already in the prefix")
        if appended_ids and coverage_trace.get("status") != "appended":
            raise ValueError("coverage appended rows without status=appended")
        if not appended_ids and coverage_trace.get("status") == "appended":
            raise ValueError("coverage reported status=appended without appended rows")
        coverage_trace = dict(coverage_trace)
        coverage_trace["protected_prefix_rows"] = len(protected_prefix)
        coverage_trace["protected_prefix_equal"] = True
        coverage_trace["appended_ids"] = appended_ids
    except Exception as exc:
        logger.warning("post-rerank coverage failed open (%s)", type(exc).__name__)
        served = protected_prefix
        coverage_trace = {
            "enabled": False,
            "status": "error",
            "error_type": type(exc).__name__,
            "protected_prefix_rows": len(protected_prefix),
            "protected_prefix_equal": True,
            "lanes": [],
            "appended_ids": [],
        }

    generation = adapters.generate(
        query,
        served,
        available_models=available_models,
    )
    return {
        "retrieval_rows": len(retrieval_pool),
        "reranked_rows": len(protected_prefix),
        "chunks": served,
        "coverage_trace": coverage_trace,
        "generation": generation,
    }
