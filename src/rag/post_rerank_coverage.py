"""Default-off, fail-open post-rerank source-evidence coverage.

The main reranker's output is a protected prefix.  Independently validated
real source chunks may only be appended; they can never reorder or mutate that
prefix.  This makes retrieval-stage movement observable without silently
changing the established ranking contract.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import yaml

from ..config import (
    CANONICAL_HYQ_COVERAGE,
    POST_RERANK_COVERAGE,
    RERANK_POOL_COVERAGE,
    STRUCTURAL_NEIGHBOR_COVERAGE,
)
from .doc_scoped_hyq_coverage import (
    LANE as HYQ_LANE,
    collect_document_scoped_hyq,
)
from .structural_neighbor_coverage import (
    DEFAULT_CONFIG as STRUCTURAL_CONFIG,
    LANE as STRUCTURAL_LANE,
    select_structural_neighbors,
)
from .structural_neighbor_shadow import fetch_structural_neighbor_rows
from .rerank_pool_coverage import (
    LANE as POOL_LANE,
    select_rerank_pool_coverage,
)

logger = logging.getLogger(__name__)
ALLOWED_LANES = frozenset({STRUCTURAL_LANE, HYQ_LANE, POOL_LANE})
MAX_APPENDED = 4
MAX_APPENDED_PER_LANE = 2
STRUCTURAL_SERVING_TIMEOUT_SECONDS = 2.0


def has_exact_coverage_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate every claimed source span at the final serving boundary."""
    content = chunk.get("content")
    cards = chunk.get("coverage_cards")
    if not isinstance(content, str) or not content or not isinstance(cards, list) or not cards:
        return False
    candidate_id = str(chunk.get("id") or "")
    if not candidate_id or chunk.get("retrieval_lane") not in ALLOWED_LANES:
        return False
    for card in cards:
        if not isinstance(card, dict) or card.get("exact_source_span_validated") is not True:
            return False
        start, end, quote = card.get("start"), card.get("end"), card.get("quote")
        if (
            str(card.get("candidate_id") or "") != candidate_id
            or isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or not isinstance(quote, str)
            or not 0 <= start < end <= len(content)
            or content[start:end] != quote
        ):
            return False
    return True


def is_validated_coverage_chunk(chunk: dict[str, Any]) -> bool:
    lane = chunk.get("retrieval_lane")
    lane_validated = (
        lane == STRUCTURAL_LANE
        and chunk.get("structural_neighbor_validated") is True
    ) or (
        lane == HYQ_LANE
        and chunk.get("hyq_navigation_validated") is True
    ) or (
        lane == POOL_LANE
        and chunk.get("rerank_pool_coverage_validated") is True
    )
    return (
        bool(str(chunk.get("source_file") or "").strip())
        and lane_validated
        and chunk.get("post_rerank_coverage") is True
        and chunk.get("coverage_validated") is True
        and chunk.get("local_semantic_validated") is True
        and has_exact_coverage_receipt(chunk)
    )


def coverage_context_content(chunk: dict[str, Any]) -> str:
    """Serve bounded exact excerpts for every validated coverage lane.

    Coverage complements can be long table/UI chunks, so synthesis sees only
    spans independently attested by the lane. This bounds token cost and
    prevents an unrelated tail of the same chunk from influencing the answer.
    The original parent row remains intact for provenance and revalidation.
    """
    content = str(chunk.get("content") or "")
    if not is_validated_coverage_chunk(chunk):
        return content
    ranges = sorted(
        (int(card["start"]), int(card["end"]))
        for card in chunk.get("coverage_cards") or []
    )
    merged: list[list[int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return "\n\n[... otro extracto fuente ...]\n\n".join(
        content[start:end] for start, end in merged
    )


def _attest(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if not candidate.get("source_file") or not has_exact_coverage_receipt(candidate):
        return None
    lane = candidate["retrieval_lane"]
    if lane == STRUCTURAL_LANE and candidate.get("structural_neighbor_validated") is not True:
        return None
    if lane == HYQ_LANE and candidate.get("hyq_navigation_validated") is not True:
        return None
    if lane == POOL_LANE and candidate.get("rerank_pool_coverage_validated") is not True:
        return None
    attested = dict(candidate)
    attested.update(
        {
            "coverage_validated": True,
            "post_rerank_coverage": True,
            "post_rerank_coverage_contract": "exact_source_span_v1",
        }
    )
    return attested


def append_validated_coverage(
    reranked: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Append at most four unique attestations; never touch the reranked prefix."""
    if not candidates:
        return reranked
    output = list(reranked)
    seen = {str(row.get("id") or "") for row in reranked}
    appended_by_lane: dict[str, int] = {}
    for candidate in candidates:
        attested = _attest(candidate)
        candidate_id = str((attested or {}).get("id") or "")
        lane = str((attested or {}).get("retrieval_lane") or "")
        if (
            not attested
            or candidate_id in seen
            or appended_by_lane.get(lane, 0) >= MAX_APPENDED_PER_LANE
        ):
            continue
        attested["post_rerank_coverage_rank"] = len(output) - len(reranked) + 1
        output.append(attested)
        seen.add(candidate_id)
        appended_by_lane[lane] = appended_by_lane.get(lane, 0) + 1
        if len(output) - len(reranked) == MAX_APPENDED:
            break
    return output if len(output) > len(reranked) else reranked


def collect_structural_coverage(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    fetcher=fetch_structural_neighbor_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = yaml.safe_load(STRUCTURAL_CONFIG.read_text(encoding="utf-8"))
    runtime = payload["shadow_runtime"]
    hydrated, candidates, read_trace = fetcher(
        reranked[: payload["max_seeds"]],
        max_gap=payload["max_gap"],
        max_candidates=payload["max_candidates"],
        max_http_requests=runtime["max_http_requests"],
        # Serving gets the maximum budget already allowed by the shadow
        # contract.  The 750 ms sampling budget proved too short in the real
        # HTTP path and caused deterministic false negatives.
        timeout_seconds=STRUCTURAL_SERVING_TIMEOUT_SECONDS,
    )
    selected, selection_trace = select_structural_neighbors(
        query, hydrated, candidates
    )
    # Recheck the identity relationship at the release seam rather than
    # trusting metadata produced by the selector alone.
    seed_identities = {
        (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        for row in hydrated
    }
    validated = [
        row for row in selected
        if (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        in seed_identities
    ]
    return validated, {
        "lane": STRUCTURAL_LANE,
        "status": "selected" if validated else "no_validated_source_span",
        "selected_ids": [str(row["id"]) for row in validated],
        "http_requests": read_trace.get("http_requests", 0),
        "selector_reason": selection_trace.get("reason"),
    }


def apply_post_rerank_coverage_with_trace(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    retrieval_pool: list[dict[str, Any]] | None = None,
    enabled: bool | None = None,
    structural_enabled: bool | None = None,
    hyq_enabled: bool | None = None,
    pool_enabled: bool | None = None,
    structural_collector: Callable[..., tuple[list[dict], dict]] = collect_structural_coverage,
    hyq_collector: Callable[..., tuple[list[dict], dict]] = collect_document_scoped_hyq,
    pool_collector: Callable[..., tuple[list[dict], dict]] = select_rerank_pool_coverage,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply enabled lanes independently; every failure is contained."""
    active = POST_RERANK_COVERAGE if enabled is None else enabled
    structural = (
        STRUCTURAL_NEIGHBOR_COVERAGE
        if structural_enabled is None else structural_enabled
    )
    hyq = CANONICAL_HYQ_COVERAGE if hyq_enabled is None else hyq_enabled
    pool = RERANK_POOL_COVERAGE if pool_enabled is None else pool_enabled
    trace: dict[str, Any] = {
        "enabled": active,
        "protected_prefix_rows": len(reranked),
        "lanes": [],
        "appended_ids": [],
        "model_calls": 0,
        "database_writes": 0,
    }
    if not active or not reranked or not (structural or hyq or pool):
        trace["status"] = "disabled_or_not_applicable"
        return reranked, trace

    candidates: list[dict[str, Any]] = []
    lane_calls = []
    if structural:
        lane_calls.append((STRUCTURAL_LANE, lambda: structural_collector(query, reranked)))
    if hyq:
        lane_calls.append((HYQ_LANE, lambda: hyq_collector(query)))
    # Pool coverage is deliberately last. Existing S109 candidates keep their
    # places inside the global four-row append budget; this lane only fills
    # unused capacity and cannot displace a previously validated recovery.
    if pool and retrieval_pool:
        lane_calls.append(
            # The pool lane sees earlier validated candidates as coverage
            # context, so its two-row budget complements rather than repeats
            # structural/HYQ recoveries. The protected prefix itself remains
            # unchanged and is still the only ordering authority.
            (POOL_LANE, lambda: pool_collector(
                query, retrieval_pool, [*reranked, *candidates]
            ))
        )
    for lane, call in lane_calls:
        try:
            selected, lane_trace = call()
            candidates.extend(selected)
            trace["lanes"].append(lane_trace)
        except Exception as exc:
            logger.warning("post-rerank coverage lane failed open: %s", type(exc).__name__)
            trace["lanes"].append(
                {"lane": lane, "status": "error", "error_type": type(exc).__name__}
            )

    output = append_validated_coverage(reranked, candidates)
    trace.update(
        {
            "status": "appended" if len(output) > len(reranked) else "no_append",
            "appended_ids": [str(row.get("id") or "") for row in output[len(reranked):]],
            "protected_prefix_equal": output[: len(reranked)] == reranked,
        }
    )
    return output, trace


def apply_post_rerank_coverage(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    retrieval_pool: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    output, _ = apply_post_rerank_coverage_with_trace(
        query, reranked, retrieval_pool=retrieval_pool
    )
    return output
