"""Profile-governed facade for production post-rerank coverage.

The measured historical module still exposes per-switch parameters for legacy
offline experiments. Production and new orchestration code use this narrower
facade, whose signature cannot override release-profile switches.
"""

from __future__ import annotations

from typing import Any, Callable

from ..config import DOCUMENT_LOCAL_COVERAGE
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
    document_local_fetcher: Callable[..., tuple[
        list[dict], list[dict], dict
    ]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply boot-resolved flags while keeping the real selector non-injectable."""

    def collect_with_runtime_selector(query_text, seeds):
        return collect_structural_coverage(
            query_text,
            seeds,
            fetcher=structural_fetcher,
        )

    coverage_kwargs: dict[str, Any] = {}
    if DOCUMENT_LOCAL_COVERAGE:
        # Keep coverage_c1_v1 import-isolated.  Its profile resolves this flag
        # off, so the unreleased implementation is neither loaded nor admitted
        # to the old profile's dependency closure.
        from .document_local_coverage import (
            collect_document_local_coverage,
            fetch_document_local_candidates,
        )

        active_fetcher = document_local_fetcher or fetch_document_local_candidates

        def collect_document_local_with_runtime_selector(
            query_text, anchors, covered_context
        ):
            return collect_document_local_coverage(
                query_text,
                anchors,
                covered_context,
                fetcher=active_fetcher,
            )

        coverage_kwargs["document_local_collector"] = (
            collect_document_local_with_runtime_selector
        )

    return apply_post_rerank_coverage_with_trace(
        query,
        reranked,
        retrieval_pool=retrieval_pool,
        structural_collector=collect_with_runtime_selector,
        **coverage_kwargs,
    )
