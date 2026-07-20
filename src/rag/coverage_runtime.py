"""Profile-governed facade for production post-rerank coverage.

The measured historical module still exposes per-switch parameters for legacy
offline experiments. Production and new orchestration code use this narrower
facade, whose signature cannot override release-profile switches.
"""

from __future__ import annotations

from typing import Any, Callable

from .post_rerank_coverage import (
    apply_post_rerank_coverage_with_trace,
    collect_structural_coverage,
)
from .structural_neighbor_shadow import fetch_structural_neighbor_rows


def apply_profiled_post_rerank_coverage(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    retrieval_pool: list[dict[str, Any]] | None = None,
    structural_fetcher: Callable[..., tuple[list[dict], list[dict], dict]] = (
        fetch_structural_neighbor_rows
    ),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply boot-resolved flags while keeping the real selector non-injectable."""

    def collect_with_runtime_selector(query_text, seeds):
        return collect_structural_coverage(
            query_text,
            seeds,
            fetcher=structural_fetcher,
        )

    return apply_post_rerank_coverage_with_trace(
        query,
        reranked,
        retrieval_pool=retrieval_pool,
        structural_collector=collect_with_runtime_selector,
    )
