"""Privacy-bounded telemetry for the live RAG serving path.

Raw coverage and must-preserve traces contain source/chunk identifiers.  This
module deliberately does not offer a generic serializer: it builds a new object
from a closed allowlist of booleans, counters, and controlled status tokens.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


TRACE_SCHEMA = "rag_serving_trace_v1"
TRACE_MAX_BYTES = 8192
_MAX_LANE_OUTCOMES = 8
_ALLOWED_PROFILES = frozenset(
    {"legacy", "off", "coverage_c1_v1", "coverage_c1_v2"}
)
_ALLOWED_COVERAGE_STATUSES = frozenset(
    {"disabled_or_not_applicable", "appended", "no_append", "error"}
)
_DOCUMENT_LOCAL_LANE_STATUSES = frozenset(
    {
        "selected",
        "no_validated_structural_anchor",
        "source_scope_overflow",
        "no_bounded_query_plan",
        "invalid_anchor_scope",
        "document_seed_not_found",
        "ambiguous_document_family",
        "unsupported_document_language",
        "active_revision_not_bound_to_anchor_blob",
        "document_scope_overflow",
        "invalid_revision_status",
        "ambiguous_active_revision",
        "branched_or_cyclic_revision_chain",
        "nonreciprocal_revision_chain",
        "incomplete_revision_chain",
        "no_authoritative_source_scope",
        "candidate_scope_mismatch",
        "combined_candidate_cap_exceeded",
        "candidate_cap_exceeded",
        "no_fts_candidates",
        "no_candidates",
        "fetched",
        "selector_pool_overflow",
        "no_query_aligned_candidate",
        "best_candidate_already_covered",
        "winner_scope_mismatch",
        "skipped_no_append_capacity",
        "skipped_no_served_structural_anchor",
        "error",
    }
)
_ALLOWED_LANE_STATUSES = frozenset(
    {
        "selected",
        "selected_complete_relational_bundle",
        "no_validated_source_span",
        "no_exact_table_preamble",
        "no_pool_seed",
        "no_query_aligned_candidate",
        "no_complete_relational_bundle",
        "not_applicable",
        "not_applicable_or_pool_overflow",
        "no_canonical_candidates",
        "skipped_no_append_capacity",
        "skipped_no_served_pool_seed",
        "error",
    }
) | _DOCUMENT_LOCAL_LANE_STATUSES
_ALLOWED_MP_STATUSES = frozenset(
    {"disabled", "evaluated", "error", "not_available", "not_applicable"}
)
_ALLOWED_ERROR_TYPES = frozenset(
    {
        "Exception",
        "RuntimeError",
        "TypeError",
        "ValueError",
        "KeyError",
        "TimeoutError",
        "ReadTimeout",
        "ConnectTimeout",
        "HTTPStatusError",
        "JSONDecodeError",
    }
)
_ALLOWED_LANES = frozenset(
    {
        "same_blob_structural_neighbor_coverage_v1",
        "same_blob_table_preamble_closure_v3",
        "canonical_document_hyq_coverage_v1",
        "canonical_compatibility_bundle_coverage_v2",
        "retrieval_pool_coverage_v1",
        "document_local_content_coverage_v1",
        "cascaded_structural_neighbor_coverage_v1",
    }
)
_ALLOWED_MP_REASONS = frozenset({"identity_unresolved"})
_ALLOWED_RENDER_STATUSES = frozenset(
    {"html", "plain_fallback", "empty_answer_fallback"}
)

# Used only by tests/audits; no value from these fields is ever copied.
SENSITIVE_RAW_KEYS = frozenset(
    {
        "query",
        "qid",
        "question",
        "answer",
        "expected_fact",
        "gold",
        "content",
        "quote",
        "source_file",
        "candidate_id",
        "selected_ids",
        "appended_ids",
        "resolved_ids",
        "cited_fragments",
        "document_id",
        "chunk_id",
    }
)


def _bounded_int(value: Any, *, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(value, maximum))


def _safe_enum(value: Any, allowed: frozenset[str], *, default: str) -> str:
    text = str(value or "")
    return text if text in allowed else default


def _safe_error_type(value: Any) -> str:
    return _safe_enum(value, _ALLOWED_ERROR_TYPES, default="OtherError")


def _selected_count(lane_trace: Mapping[str, Any]) -> int:
    for field in ("selected_ids", "selected_parent_ids"):
        selected = lane_trace.get(field)
        if isinstance(selected, list):
            return min(len(selected), 1000)
    return 0


def _lane_outcomes(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    lanes = raw.get("lanes")
    if not isinstance(lanes, list):
        return outcomes
    for item in lanes[:_MAX_LANE_OUTCOMES]:
        if not isinstance(item, Mapping):
            continue
        lane = str(item.get("lane") or "")
        if lane not in _ALLOWED_LANES:
            lane = "unknown_lane"
        outcome: dict[str, Any] = {
            "lane": lane,
            "status": _safe_enum(
                item.get("status"), _ALLOWED_LANE_STATUSES, default="unknown"
            ),
            "selected_rows": _selected_count(item),
        }
        if item.get("error_type"):
            outcome["error_type"] = _safe_error_type(item.get("error_type"))
        outcomes.append(outcome)
    return outcomes


def _mandatory_card_count(
    chunks: list[dict[str, Any]],
    coverage_trace: Mapping[str, Any],
    *,
    enabled: bool,
) -> int:
    """Count only exact, attested callouts that were appended and served."""
    if not enabled:
        return 0
    appended = coverage_trace.get("appended_ids")
    if not isinstance(appended, list):
        return 0
    appended_ids = {str(value) for value in appended if value}
    if not appended_ids:
        return 0

    # Import lazily to keep this privacy serializer independent at import time.
    from .post_rerank_coverage import (
        has_exact_mandatory_callout_receipt,
        is_validated_coverage_chunk,
    )

    count = 0
    for chunk in chunks[:100]:
        if (
            str(chunk.get("id") or "") not in appended_ids
            or not is_validated_coverage_chunk(chunk)
            or not has_exact_mandatory_callout_receipt(chunk)
        ):
            continue
        cards = chunk.get("mandatory_callout_cards")
        if isinstance(cards, list):
            count += min(len(cards), 4)
    return min(count, 100)


def _coverage_section(
    raw: Mapping[str, Any],
    chunks: list[dict[str, Any]],
    release_policy: Mapping[str, Any],
) -> dict[str, Any]:
    lane_outcomes = _lane_outcomes(raw)
    executed_lanes = [item["lane"] for item in lane_outcomes]
    configured_lanes: list[str] = []
    if (
        release_policy.get("structural_neighbor_coverage") is True
        and "same_blob_structural_neighbor_coverage_v1" not in configured_lanes
    ):
        configured_lanes.append("same_blob_structural_neighbor_coverage_v1")
    if release_policy.get("document_local_coverage") is True:
        configured_lanes.append("document_local_content_coverage_v1")

    appended = raw.get("appended_ids")
    section: dict[str, Any] = {
        "enabled": bool(raw.get("enabled")),
        "status": _safe_enum(
            raw.get("status"), _ALLOWED_COVERAGE_STATUSES, default="unknown"
        ),
        "configured_lanes": configured_lanes[:_MAX_LANE_OUTCOMES],
        "executed_lanes": executed_lanes[:_MAX_LANE_OUTCOMES],
        "prefix_rows": _bounded_int(raw.get("protected_prefix_rows")),
        "appended_rows": min(len(appended), 100) if isinstance(appended, list) else 0,
        "protected_prefix_equal": bool(raw.get("protected_prefix_equal")),
        "lane_outcomes": lane_outcomes,
        "mandatory_callout_enabled": bool(
            release_policy.get("coverage_mandatory_callout")
        ),
        "mandatory_callout_cards": _mandatory_card_count(
            chunks,
            raw,
            enabled=bool(release_policy.get("coverage_mandatory_callout")),
        ),
    }
    if raw.get("error_type"):
        section["error_type"] = _safe_error_type(raw.get("error_type"))
    return section


def _must_preserve_section(
    raw: Mapping[str, Any] | None,
    outcome: Mapping[str, Any] | None,
) -> dict[str, Any]:
    raw = raw if isinstance(raw, Mapping) else {}
    outcome = outcome if isinstance(outcome, Mapping) else {}
    status = _safe_enum(
        outcome.get("status"), _ALLOWED_MP_STATUSES, default="not_available"
    )
    section: dict[str, Any] = {
        "status": status,
        "identity_resolved": bool(raw.get("identity_resolved")),
        "cited_fragment_count": (
            min(len(raw.get("cited_fragments")), 100)
            if isinstance(raw.get("cited_fragments"), list)
            else 0
        ),
        "atoms_detected": _bounded_int(raw.get("atoms_detected")),
        "atoms_bound": _bounded_int(raw.get("atoms_bound")),
        "atoms_missing": _bounded_int(raw.get("atoms_missing")),
        "atoms_appended": _bounded_int(raw.get("atoms_appended")),
        "appendix_appended": bool(raw.get("appendix_appended")),
    }
    reason = str(raw.get("reason") or "")
    if reason in _ALLOWED_MP_REASONS:
        section["reason"] = reason
    if outcome.get("error_type"):
        section["error_type"] = _safe_error_type(outcome.get("error_type"))
    return section


def build_rag_serving_trace(
    *,
    coverage_trace: Mapping[str, Any] | None,
    served_chunks: list[dict[str, Any]],
    must_preserve_trace: Mapping[str, Any] | None,
    must_preserve_outcome: Mapping[str, Any] | None,
    release_policy: Mapping[str, Any],
    transport_parts: int,
    transport_status: str = "html",
    transport_error_type: str | None = None,
) -> dict[str, Any]:
    """Build the only runtime trace shape allowed into ``query_logs``."""
    profile = _safe_enum(
        release_policy.get("profile"), _ALLOWED_PROFILES, default="unknown"
    )
    trace = {
        "schema": TRACE_SCHEMA,
        "release_profile": profile,
        "coverage": _coverage_section(
            coverage_trace if isinstance(coverage_trace, Mapping) else {},
            served_chunks,
            release_policy,
        ),
        "must_preserve": _must_preserve_section(
            must_preserve_trace,
            must_preserve_outcome,
        ),
        "transport": {
            "message_parts": _bounded_int(transport_parts, maximum=100),
            "render_status": _safe_enum(
                transport_status,
                _ALLOWED_RENDER_STATUSES,
                default="plain_fallback",
            ),
        },
    }
    if transport_error_type:
        trace["transport"]["error_type"] = _safe_error_type(transport_error_type)
    encoded = json.dumps(
        trace, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > TRACE_MAX_BYTES:
        raise RuntimeError("bounded RAG trace unexpectedly exceeds size contract")
    return trace


def _validate_rag_serving_trace(value: Any) -> dict[str, Any] | None:
    """Implement the closed-schema validation without trusting input types.

    This is the defense-in-depth boundary used by the database sink. A future
    caller cannot persist arbitrary JSON merely by bypassing the builder.
    """

    def exact_keys(
        item: Any,
        required: set[str],
        optional: set[str] | None = None,
    ) -> bool:
        if not isinstance(item, dict):
            return False
        keys = set(item)
        return required <= keys <= required | (optional or set())

    def safe_int(item: Any, maximum: int = 1_000_000) -> bool:
        return isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= maximum

    if not exact_keys(
        value,
        {"schema", "release_profile", "coverage", "must_preserve", "transport"},
    ):
        return None
    if value["schema"] != TRACE_SCHEMA or value["release_profile"] not in (
        _ALLOWED_PROFILES | {"unknown"}
    ):
        return None

    coverage = value["coverage"]
    coverage_required = {
        "enabled",
        "status",
        "configured_lanes",
        "executed_lanes",
        "prefix_rows",
        "appended_rows",
        "protected_prefix_equal",
        "lane_outcomes",
        "mandatory_callout_enabled",
        "mandatory_callout_cards",
    }
    if not exact_keys(coverage, coverage_required, {"error_type"}):
        return None
    if (
        type(coverage["enabled"]) is not bool
        or coverage["status"] not in (_ALLOWED_COVERAGE_STATUSES | {"unknown"})
        or type(coverage["protected_prefix_equal"]) is not bool
        or type(coverage["mandatory_callout_enabled"]) is not bool
        or not safe_int(coverage["prefix_rows"])
        or not safe_int(coverage["appended_rows"], 100)
        or not safe_int(coverage["mandatory_callout_cards"], 100)
    ):
        return None
    for field in ("configured_lanes", "executed_lanes"):
        lanes = coverage[field]
        if (
            not isinstance(lanes, list)
            or len(lanes) > _MAX_LANE_OUTCOMES
            or any(lane not in (_ALLOWED_LANES | {"unknown_lane"}) for lane in lanes)
        ):
            return None
    outcomes = coverage["lane_outcomes"]
    if not isinstance(outcomes, list) or len(outcomes) > _MAX_LANE_OUTCOMES:
        return None
    for outcome in outcomes:
        if not exact_keys(outcome, {"lane", "status", "selected_rows"}, {"error_type"}):
            return None
        if (
            outcome["lane"] not in (_ALLOWED_LANES | {"unknown_lane"})
            or outcome["status"] not in (_ALLOWED_LANE_STATUSES | {"unknown"})
            or not safe_int(outcome["selected_rows"], 1000)
            or (
                "error_type" in outcome
                and outcome["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
            )
        ):
            return None
    if "error_type" in coverage and coverage["error_type"] not in (
        _ALLOWED_ERROR_TYPES | {"OtherError"}
    ):
        return None

    must_preserve = value["must_preserve"]
    mp_required = {
        "status",
        "identity_resolved",
        "cited_fragment_count",
        "atoms_detected",
        "atoms_bound",
        "atoms_missing",
        "atoms_appended",
        "appendix_appended",
    }
    if not exact_keys(must_preserve, mp_required, {"reason", "error_type"}):
        return None
    if (
        must_preserve["status"] not in _ALLOWED_MP_STATUSES
        or type(must_preserve["identity_resolved"]) is not bool
        or type(must_preserve["appendix_appended"]) is not bool
        or any(
            not safe_int(must_preserve[field], 1_000_000)
            for field in (
                "cited_fragment_count",
                "atoms_detected",
                "atoms_bound",
                "atoms_missing",
                "atoms_appended",
            )
        )
        or (
            "reason" in must_preserve
            and must_preserve["reason"] not in _ALLOWED_MP_REASONS
        )
        or (
            "error_type" in must_preserve
            and must_preserve["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
        )
    ):
        return None

    transport = value["transport"]
    if not exact_keys(transport, {"message_parts", "render_status"}, {"error_type"}):
        return None
    if (
        not safe_int(transport["message_parts"], 100)
        or transport["render_status"] not in _ALLOWED_RENDER_STATUSES
        or (
            "error_type" in transport
            and transport["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
        )
    ):
        return None

    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > TRACE_MAX_BYTES:
        return None
    return json.loads(encoded.decode("utf-8"))


def validate_rag_serving_trace(value: Any) -> dict[str, Any] | None:
    """Return a detached trace only when it matches the closed storage schema.

    Malformed caller input is treated as absent telemetry, never as a reason to
    lose the underlying query log.
    """
    try:
        return _validate_rag_serving_trace(value)
    except (TypeError, ValueError, OverflowError):
        return None
