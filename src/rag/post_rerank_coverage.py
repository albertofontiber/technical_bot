"""Default-off, fail-open post-rerank source-evidence coverage.

The main reranker's output is a protected prefix.  Independently validated
real source chunks may only be appended; they can never reorder or mutate that
prefix.  This makes retrieval-stage movement observable without silently
changing the established ranking contract.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

import yaml

from ..config import (
    CANONICAL_HYQ_COVERAGE,
    COMPATIBILITY_BUNDLE_COVERAGE,
    LOGICAL_RECORD_COVERAGE,
    POST_RERANK_COVERAGE,
    RERANK_POOL_COVERAGE,
    STRUCTURAL_CASCADE_COVERAGE,
    STRUCTURAL_NEIGHBOR_COVERAGE,
)
from .compatibility_bundle_coverage import (
    LANE as COMPATIBILITY_LANE,
    collect_compatibility_bundle,
    is_compatibility_bundle_query,
    validate_compatibility_bundle,
)
from .doc_scoped_hyq_coverage import (
    LANE as HYQ_LANE,
    collect_document_scoped_hyq,
)
from .structural_neighbor_coverage import (
    CASCADED_CONFIG as STRUCTURAL_CASCADE_CONFIG,
    CASCADED_EVIDENCE_CONFIG,
    CASCADED_LANE as STRUCTURAL_CASCADE_LANE,
    CASCADED_QUERY_FACETS,
    CASCADED_VALIDATION as STRUCTURAL_CASCADE_VALIDATION,
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
ALLOWED_LANES = frozenset(
    {
        STRUCTURAL_LANE,
        STRUCTURAL_CASCADE_LANE,
        HYQ_LANE,
        POOL_LANE,
        COMPATIBILITY_LANE,
    }
)
MAX_APPENDED = 4
MAX_APPENDED_PER_LANE = 2
MAX_APPENDED_BY_LANE = {COMPATIBILITY_LANE: 3}
STRUCTURAL_SERVING_TIMEOUT_SECONDS = 2.0
MAX_LOGICAL_TABLE_ROW_CHARS = 1400
MAX_EXPANDED_EXCERPT_CHARS = 1800
_NON_SUBSTANTIVE_DIAGRAM_CARD = re.compile(
    r"^\[(?:(?:technical|t[eé]cnico)\s+)?(?:wiring\s+)?(?:diagram|diagrama|image|imagen)\b.*:\]$",
    re.IGNORECASE,
)
_SUBSTANTIVE_HEADING_VALUE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|km|m|v(?:dc|ac)?|ma|a|kw|w|"
    r"ohm(?:ios?)?|ω|seg|s|min|h|°c|%|[µu]f|nf|pf)\b",
    re.IGNORECASE,
)


def _has_exact_card_receipts(chunk: dict[str, Any], field: str) -> bool:
    """Revalidate every card in ``field`` against the immutable parent text."""
    content = chunk.get("content")
    cards = chunk.get(field)
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


def has_exact_coverage_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate the selector's original source-span receipts."""
    return _has_exact_card_receipts(chunk, "coverage_cards")


def has_exact_served_coverage_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate the exact spans admitted by optional logical-row serving."""
    if (
        not has_exact_coverage_receipt(chunk)
        or not _has_exact_card_receipts(chunk, "served_coverage_cards")
    ):
        return False
    try:
        expected = _build_served_coverage_cards(chunk)
    except (KeyError, TypeError, ValueError):
        return False
    return chunk.get("served_coverage_cards") == expected


def is_validated_coverage_chunk(chunk: dict[str, Any]) -> bool:
    lane = chunk.get("retrieval_lane")
    lane_validated = (
        lane in {STRUCTURAL_LANE, STRUCTURAL_CASCADE_LANE}
        and chunk.get("structural_neighbor_validated") is True
    ) or (
        lane == HYQ_LANE
        and chunk.get("hyq_navigation_validated") is True
    ) or (
        lane == POOL_LANE
        and chunk.get("rerank_pool_coverage_validated") is True
    ) or (
        lane == COMPATIBILITY_LANE
        and chunk.get("compatibility_bundle_validated") is True
    )
    return (
        bool(str(chunk.get("source_file") or "").strip())
        and lane_validated
        and chunk.get("post_rerank_coverage") is True
        and chunk.get("coverage_validated") is True
        and chunk.get("local_semantic_validated") is True
        and has_exact_coverage_receipt(chunk)
    )


def coverage_context_content(
    chunk: dict[str, Any], *, logical_record_expansion: bool | None = None
) -> str:
    """Serve bounded exact excerpts for every validated coverage lane.

    Coverage complements can be long table/UI chunks, so synthesis sees only
    spans independently attested by the lane. This bounds token cost and
    prevents an unrelated tail of the same chunk from influencing the answer.
    The original parent row remains intact for provenance and revalidation.
    """
    content = str(chunk.get("content") or "")
    if not is_validated_coverage_chunk(chunk):
        return content
    expand = (
        LOGICAL_RECORD_COVERAGE
        if logical_record_expansion is None else logical_record_expansion
    )
    cards = (
        chunk.get("served_coverage_cards")
        if expand and has_exact_served_coverage_receipt(chunk)
        else chunk.get("coverage_cards")
    ) or []
    ranges = sorted((int(card["start"]), int(card["end"])) for card in cards)
    merged: list[list[int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return "\n\n[... otro extracto fuente ...]\n\n".join(
        content[start:end] for start, end in merged
    )


def _expand_logical_table_boundaries(
    content: str, start: int, end: int
) -> tuple[int, int]:
    """Finish an intersected Markdown table row instead of clipping its value.

    Fixed evidence windows are safe for prose but can end halfway through a
    long key/value row.  Serving that partial row makes a selected fact look as
    if it reached synthesis while its value was actually removed.  Expansion
    is allowed only to exact newline boundaries of bounded pipe-table rows;
    prose and oversized records remain byte-identical to their attested span.
    """
    start_line = content.rfind("\n", 0, start) + 1
    start_break = content.find("\n", start)
    start_line_end = len(content) if start_break < 0 else start_break
    end_line = content.rfind("\n", 0, max(start, end - 1)) + 1
    end_break = content.find("\n", end)
    end_line_end = len(content) if end_break < 0 else end_break

    def bounded_table_row(line_start: int, line_end: int) -> bool:
        line = content[line_start:line_end]
        stripped = line.strip()
        return (
            len(line) <= MAX_LOGICAL_TABLE_ROW_CHARS
            and stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 3
        )

    expanded_start = (
        start_line if bounded_table_row(start_line, start_line_end) else start
    )
    expanded_end = (
        end_line_end if bounded_table_row(end_line, end_line_end) else end
    )
    if expanded_end - expanded_start > MAX_EXPANDED_EXCERPT_CHARS:
        return start, end
    return expanded_start, expanded_end


def _build_served_coverage_cards(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive separately receipted serving spans from validated selector cards."""
    content = str(candidate.get("content") or "")
    served_cards = []
    for card in candidate.get("coverage_cards") or []:
        original_start = int(card["start"])
        original_end = int(card["end"])
        start, end = _expand_logical_table_boundaries(
            content, original_start, original_end
        )
        served = dict(card)
        served.update(
            {
                "start": start,
                "end": end,
                "quote": content[start:end],
                "selector_start": original_start,
                "selector_end": original_end,
                "logical_record_expanded": (
                    start != original_start or end != original_end
                ),
                "exact_source_span_validated": True,
            }
        )
        served_cards.append(served)
    return served_cards


def _has_substantive_coverage_card(candidate: dict[str, Any]) -> bool:
    """Reject title/placeholder-only cards that add no field-support fact."""
    for card in candidate.get("coverage_cards") or []:
        quote = str(card.get("quote") or "").strip()
        lines = [line.strip() for line in quote.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 and (
            (
                lines[0].startswith("#")
                and not candidate.get("structured_numeric_claims")
                and not _SUBSTANTIVE_HEADING_VALUE.search(lines[0])
            )
            or _NON_SUBSTANTIVE_DIAGRAM_CARD.fullmatch(lines[0])
        ):
            continue
        return True
    return False


def _attest(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if not candidate.get("source_file") or not has_exact_coverage_receipt(candidate):
        return None
    lane = candidate["retrieval_lane"]
    if (
        lane in {STRUCTURAL_LANE, STRUCTURAL_CASCADE_LANE}
        and candidate.get("structural_neighbor_validated") is not True
    ):
        return None
    if lane == HYQ_LANE and candidate.get("hyq_navigation_validated") is not True:
        return None
    if lane == POOL_LANE and candidate.get("rerank_pool_coverage_validated") is not True:
        return None
    if lane == COMPATIBILITY_LANE and candidate.get("compatibility_bundle_validated") is not True:
        return None
    attested = dict(candidate)
    attested["served_coverage_cards"] = _build_served_coverage_cards(candidate)
    if not has_exact_served_coverage_receipt(attested):
        return None
    attested.update(
        {
            "coverage_validated": True,
            "post_rerank_coverage": True,
            "post_rerank_coverage_contract": (
                "exact_source_span_with_bounded_logical_record_receipt_v2"
            ),
        }
    )
    return attested


def append_validated_coverage(
    reranked: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Append at most four unique attestations; never touch the reranked prefix."""
    if not candidates:
        return reranked
    compatibility_groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        if candidate.get("retrieval_lane") == COMPATIBILITY_LANE:
            bundle_id = str(candidate.get("compatibility_bundle_id") or "")
            compatibility_groups.setdefault(bundle_id, []).append(candidate)
    valid_compatibility_ids = {
        bundle_id
        for bundle_id, rows in compatibility_groups.items()
        if bundle_id and validate_compatibility_bundle(rows)
    }
    # A relational bundle is atomic. Reject ambiguity, a parent already in the
    # protected prefix, or any state in which fewer than all three rows could
    # reach the generator. Put the one valid bundle first so other optional
    # lanes cannot consume its three-row reservation.
    if len(valid_compatibility_ids) == 1:
        valid_bundle_id = next(iter(valid_compatibility_ids))
        valid_bundle = compatibility_groups[valid_bundle_id]
        protected_ids = {str(base.get("id") or "") for base in reranked}
        if any(
            str(row.get("id") or "") in protected_ids for row in valid_bundle
        ):
            valid_compatibility_ids = set()
            valid_bundle = []
    else:
        valid_bundle = []
        valid_compatibility_ids = set()
    other_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("retrieval_lane") != COMPATIBILITY_LANE
    ]
    candidates = [*valid_bundle, *other_candidates]
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
            or appended_by_lane.get(lane, 0)
            >= MAX_APPENDED_BY_LANE.get(lane, MAX_APPENDED_PER_LANE)
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


def collect_cascaded_structural_coverage(
    query: str,
    pool_seeds: list[dict[str, Any]],
    *,
    fetcher=fetch_structural_neighbor_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one bounded document-local hop from already selected pool evidence."""
    if not pool_seeds:
        return [], {
            "lane": STRUCTURAL_CASCADE_LANE,
            "status": "no_pool_seed",
            "selected_ids": [],
            "http_requests": 0,
        }
    payload = yaml.safe_load(
        STRUCTURAL_CASCADE_CONFIG.read_text(encoding="utf-8")
    )
    runtime = payload["shadow_runtime"]
    hydrated, candidates, read_trace = fetcher(
        pool_seeds[: payload["max_seeds"]],
        max_gap=payload["max_gap"],
        max_candidates=payload["max_candidates"],
        max_http_requests=runtime["max_http_requests"],
        timeout_seconds=STRUCTURAL_SERVING_TIMEOUT_SECONDS,
    )
    max_page_gap = payload.get("max_page_gap")
    if (
        isinstance(max_page_gap, bool)
        or not isinstance(max_page_gap, int)
        or not 0 <= max_page_gap <= 2
    ):
        raise RuntimeError("invalid structural cascade max_page_gap")
    seed_pages: dict[tuple[str, str], list[int]] = {}
    for seed in hydrated:
        identity = (
            str(seed.get("document_id") or ""),
            str(seed.get("extraction_sha256") or ""),
        )
        page = seed.get("page_number")
        if (
            identity[0]
            and identity[1]
            and isinstance(page, int)
            and not isinstance(page, bool)
        ):
            seed_pages.setdefault(identity, []).append(page)
    page_local_candidates = []
    for candidate in candidates:
        identity = (
            str(candidate.get("document_id") or ""),
            str(candidate.get("extraction_sha256") or ""),
        )
        page = candidate.get("page_number")
        pages = seed_pages.get(identity) or []
        if (
            isinstance(page, int)
            and not isinstance(page, bool)
            and pages
            and min(abs(page - seed_page) for seed_page in pages) <= max_page_gap
        ):
            page_local_candidates.append(candidate)
    selected, selection_trace = select_structural_neighbors(
        query,
        hydrated,
        page_local_candidates,
        config_path=STRUCTURAL_CASCADE_CONFIG,
        query_facets_path=CASCADED_QUERY_FACETS,
        evidence_match_config_path=CASCADED_EVIDENCE_CONFIG,
        evidence_card_config_path=CASCADED_EVIDENCE_CONFIG,
        query_aligned_cards=True,
        lane=STRUCTURAL_CASCADE_LANE,
        validation=STRUCTURAL_CASCADE_VALIDATION,
    )
    substantive = [row for row in selected if _has_substantive_coverage_card(row)]
    non_substantive_rejected = len(selected) - len(substantive)
    seed_identities = {
        (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        for row in hydrated
    }
    validated = [
        row for row in substantive
        if (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        in seed_identities
    ]
    return validated, {
        "lane": STRUCTURAL_CASCADE_LANE,
        "status": "selected" if validated else "no_validated_source_span",
        "selected_ids": [str(row["id"]) for row in validated],
        "http_requests": read_trace.get("http_requests", 0),
        "page_local_candidates": len(page_local_candidates),
        "non_substantive_selected_rejected": non_substantive_rejected,
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
    cascade_enabled: bool | None = None,
    compatibility_enabled: bool | None = None,
    structural_collector: Callable[..., tuple[list[dict], dict]] = collect_structural_coverage,
    hyq_collector: Callable[..., tuple[list[dict], dict]] = collect_document_scoped_hyq,
    pool_collector: Callable[..., tuple[list[dict], dict]] = select_rerank_pool_coverage,
    cascade_collector: Callable[..., tuple[list[dict], dict]] = collect_cascaded_structural_coverage,
    compatibility_collector: Callable[..., tuple[list[dict], dict]] = collect_compatibility_bundle,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply enabled lanes independently; every failure is contained."""
    active = POST_RERANK_COVERAGE if enabled is None else enabled
    structural = (
        STRUCTURAL_NEIGHBOR_COVERAGE
        if structural_enabled is None else structural_enabled
    )
    hyq = CANONICAL_HYQ_COVERAGE if hyq_enabled is None else hyq_enabled
    pool = RERANK_POOL_COVERAGE if pool_enabled is None else pool_enabled
    compatibility = (
        COMPATIBILITY_BUNDLE_COVERAGE
        if compatibility_enabled is None else compatibility_enabled
    )
    compatibility_applicable = compatibility and is_compatibility_bundle_query(query)
    cascade_requested = (
        STRUCTURAL_CASCADE_COVERAGE
        if cascade_enabled is None else cascade_enabled
    )
    cascade = (
        cascade_requested
        and pool
        and bool(retrieval_pool)
        and not compatibility_applicable
    )
    trace: dict[str, Any] = {
        "enabled": active,
        "protected_prefix_rows": len(reranked),
        "lanes": [],
        "appended_ids": [],
        "model_calls": 0,
        "database_writes": 0,
    }
    if not active or not reranked or not (
        structural or hyq or pool or compatibility_applicable
    ):
        trace["status"] = "disabled_or_not_applicable"
        return reranked, trace

    candidates: list[dict[str, Any]] = []
    lane_calls = []

    def collect_cascade_if_capacity() -> tuple[list[dict], dict]:
        already_appendable = append_validated_coverage(reranked, candidates)
        if len(already_appendable) - len(reranked) >= MAX_APPENDED:
            return [], {
                "lane": STRUCTURAL_CASCADE_LANE,
                "status": "skipped_no_append_capacity",
                "selected_ids": [],
                "http_requests": 0,
            }
        served_pool_ids = {
            str(row.get("id") or "")
            for row in already_appendable[len(reranked):]
            if row.get("retrieval_lane") == POOL_LANE
        }
        pool_seeds = [
            row for row in candidates
            if row.get("retrieval_lane") == POOL_LANE
            and str(row.get("id") or "") in served_pool_ids
        ]
        if not pool_seeds:
            return [], {
                "lane": STRUCTURAL_CASCADE_LANE,
                "status": "skipped_no_served_pool_seed",
                "selected_ids": [],
                "http_requests": 0,
            }
        return cascade_collector(
            query,
            pool_seeds,
        )

    if structural and not compatibility_applicable:
        lane_calls.append((STRUCTURAL_LANE, lambda: structural_collector(query, reranked)))
    if compatibility_applicable:
        lane_calls.append(
            (COMPATIBILITY_LANE, lambda: compatibility_collector(query))
        )
    if hyq and not compatibility_applicable:
        lane_calls.append((HYQ_LANE, lambda: hyq_collector(query)))
    # Pool coverage is deliberately last. Existing S109 candidates keep their
    # places inside the global four-row append budget; this lane only fills
    # unused capacity and cannot displace a previously validated recovery.
    if pool and retrieval_pool and not compatibility_applicable:
        lane_calls.append(
            # The pool lane sees earlier validated candidates as coverage
            # context, so its two-row budget complements rather than repeats
            # structural/HYQ recoveries. The protected prefix itself remains
            # unchanged and is still the only ordering authority.
            (POOL_LANE, lambda: pool_collector(
                query, retrieval_pool, [*reranked, *candidates]
            ))
        )
    if cascade:
        lane_calls.append(
            (
                STRUCTURAL_CASCADE_LANE,
                collect_cascade_if_capacity,
            )
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
