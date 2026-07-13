#!/usr/bin/env python3
"""Pure in-memory join and redacted receipt for the R2 shadow adjudication.

The module intentionally has no database, filesystem, HTTP, or logging code. An
operations-only loader may provide the two minimum projections described below;
raw technician queries and manual content exist only in ``AdjudicationCase``
objects and are never accepted by the receipt serializer.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


EVENT_SCHEMA = "structural_neighbor_shadow_event_v1"
RECEIPT_SCHEMA = "s107_structural_neighbor_adjudication_receipt_v1"
QUERY_PROJECTION_FIELDS = frozenset({"query", "created_at"})
CHUNK_PROJECTION_FIELDS = frozenset(
    {
        "id",
        "content",
        "source_file",
        "page_number",
        "section_title",
        "document_id",
        "extraction_sha256",
        "language",
    }
)
FORBIDDEN_EVENT_FIELDS = frozenset(
    {"raw_query", "raw_content", "query", "content", "answer", "user_id", "api_key", "hmac_key"}
)
CRITICAL_REASONS = frozenset(
    {
        "cross_document_or_cross_blob",
        "wrong_oem_or_model",
        "wrong_numeric_attribute_operator_unit_or_qualifier",
        "toc_or_index_only",
        "regional_or_revision_conflict",
    }
)


@dataclass(frozen=True)
class SourceAnchor:
    id: str
    content: str
    source_file: str | None
    page_number: int | None
    section_title: str | None
    document_id: str | None
    extraction_sha256: str | None
    language: str | None


@dataclass(frozen=True)
class AdjudicationCase:
    """Ephemeral source-visible case. Never serialize or persist this object."""

    event_id: str
    query_hmac_sha256: str
    query: str
    query_occurrences: int
    anchors: tuple[SourceAnchor, ...]


@dataclass(frozen=True)
class JoinResult:
    cases: tuple[AdjudicationCase, ...]
    events_input: int
    duplicate_event_ids: int
    duplicate_query_events: int
    events_without_anchors: int
    unjoinable_query_events: tuple[str, ...]
    missing_anchor_events: tuple[str, ...]
    wrong_key_version_events: tuple[str, ...]
    duplicate_query_rows: int

    @property
    def promotion_blocked(self) -> bool:
        return bool(
            self.unjoinable_query_events
            or self.missing_anchor_events
            or self.wrong_key_version_events
        )


def hmac_sha256_utf8_exact(secret: str, value: str) -> str:
    """HMAC-SHA256 over exact UTF-8 bytes; no case-folding or normalization."""
    if not isinstance(secret, str) or len(secret) < 32:
        raise ValueError("HMAC secret must contain at least 32 characters")
    if not isinstance(value, str):
        raise TypeError("HMAC input must be a string")
    return hmac.new(
        secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _strict_projection(
    rows: Iterable[Mapping[str, Any]], allowed: frozenset[str], required: frozenset[str]
) -> list[Mapping[str, Any]]:
    projected: list[Mapping[str, Any]] = []
    for row in rows:
        fields = set(row)
        if not required <= fields or not fields <= allowed:
            raise ValueError(
                f"unsafe projection fields: got={sorted(fields)}, allowed={sorted(allowed)}"
            )
        projected.append(row)
    return projected


def join_shadow_events_in_memory(
    events: Sequence[Mapping[str, Any]],
    *,
    query_rows: Iterable[Mapping[str, Any]],
    chunk_rows: Iterable[Mapping[str, Any]],
    hmac_secret: str,
    hmac_key_version: str,
) -> JoinResult:
    """Join redacted events to minimum database projections without persistence."""
    if not hmac_key_version.startswith("v") or not hmac_key_version[1:].isdigit():
        raise ValueError("invalid HMAC key version")
    queries = _strict_projection(
        query_rows, QUERY_PROJECTION_FIELDS, frozenset({"query", "created_at"})
    )
    chunks = _strict_projection(
        chunk_rows, CHUNK_PROJECTION_FIELDS, frozenset({"id", "content"})
    )

    query_by_digest: dict[str, str] = {}
    query_occurrences: dict[str, int] = {}
    duplicate_query_rows = 0
    for row in queries:
        query = row["query"]
        if not isinstance(query, str):
            raise TypeError("query projection contains a non-string query")
        digest = hmac_sha256_utf8_exact(hmac_secret, query)
        previous = query_by_digest.setdefault(digest, query)
        if previous != query:
            raise RuntimeError("HMAC collision between distinct query strings")
        query_occurrences[digest] = query_occurrences.get(digest, 0) + 1
        if query_occurrences[digest] > 1:
            duplicate_query_rows += 1

    chunk_by_id: dict[str, SourceAnchor] = {}
    for row in chunks:
        chunk_id = str(row["id"])
        content = row["content"]
        if not chunk_id or not isinstance(content, str):
            raise ValueError("invalid source projection row")
        anchor = SourceAnchor(
            id=chunk_id,
            content=content,
            source_file=row.get("source_file"),
            page_number=row.get("page_number"),
            section_title=row.get("section_title"),
            document_id=(str(row["document_id"]) if row.get("document_id") else None),
            extraction_sha256=row.get("extraction_sha256"),
            language=row.get("language"),
        )
        if chunk_id in chunk_by_id and chunk_by_id[chunk_id] != anchor:
            raise ValueError(f"conflicting source projection for chunk {chunk_id}")
        chunk_by_id[chunk_id] = anchor

    seen_events: set[str] = set()
    seen_query_digests: set[str] = set()
    duplicate_events = 0
    duplicate_query_events = 0
    without_anchors = 0
    unjoinable: list[str] = []
    missing_anchors: list[str] = []
    wrong_version: list[str] = []
    cases: list[AdjudicationCase] = []
    for event in events:
        forbidden = set(event) & FORBIDDEN_EVENT_FIELDS
        if forbidden:
            raise ValueError(f"raw/sensitive fields in shadow event: {sorted(forbidden)}")
        if event.get("schema") != EVENT_SCHEMA:
            raise ValueError("unexpected shadow event schema")
        event_id = str(event.get("event_id") or "")
        if not event_id:
            raise ValueError("shadow event lacks event_id")
        if event_id in seen_events:
            duplicate_events += 1
            continue
        seen_events.add(event_id)
        selected_ids = event.get("selected_ids") or []
        if not isinstance(selected_ids, list) or not all(
            isinstance(value, str) and value for value in selected_ids
        ):
            raise ValueError(f"invalid selected_ids in event {event_id}")
        if not selected_ids:
            without_anchors += 1
            continue
        if event.get("sampling_hmac_key_version") != hmac_key_version:
            wrong_version.append(event_id)
            continue
        digest = str(event.get("query_hmac_sha256") or "")
        if digest in seen_query_digests:
            duplicate_query_events += 1
            continue
        seen_query_digests.add(digest)
        query = query_by_digest.get(digest)
        if query is None:
            unjoinable.append(event_id)
            continue
        anchors = tuple(chunk_by_id[value] for value in selected_ids if value in chunk_by_id)
        if len(anchors) != len(selected_ids):
            missing_anchors.append(event_id)
            continue
        cases.append(
            AdjudicationCase(
                event_id=event_id,
                query_hmac_sha256=digest,
                query=query,
                query_occurrences=query_occurrences[digest],
                anchors=anchors,
            )
        )
    return JoinResult(
        cases=tuple(cases),
        events_input=len(events),
        duplicate_event_ids=duplicate_events,
        duplicate_query_events=duplicate_query_events,
        events_without_anchors=without_anchors,
        unjoinable_query_events=tuple(sorted(unjoinable)),
        missing_anchor_events=tuple(sorted(missing_anchors)),
        wrong_key_version_events=tuple(sorted(wrong_version)),
        duplicate_query_rows=duplicate_query_rows,
    )


def build_redacted_receipt(
    result: JoinResult, decisions: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Validate exhaustive anchor labels and return a raw-content-free receipt."""
    case_by_id = {case.event_id: case for case in result.cases}
    decisions_by_id: dict[str, Mapping[str, Any]] = {}
    sanitized: list[dict[str, Any]] = []
    for decision in decisions:
        if set(decision) != {"event_id", "anchors"}:
            raise ValueError("decision must contain only event_id and anchors")
        event_id = str(decision["event_id"])
        if event_id in decisions_by_id or event_id not in case_by_id:
            raise ValueError(f"unknown or duplicate decision event: {event_id}")
        labels = decision["anchors"]
        if not isinstance(labels, list):
            raise ValueError("anchors decision must be a list")
        selected_ids = {anchor.id for anchor in case_by_id[event_id].anchors}
        labeled_ids: set[str] = set()
        clean_labels: list[dict[str, Any]] = []
        for label in labels:
            if set(label) != {"id", "relevant", "critical_reason"}:
                raise ValueError("anchor label contains a free-text or raw field")
            anchor_id = str(label["id"])
            relevant = label["relevant"]
            critical_reason = label["critical_reason"]
            if anchor_id not in selected_ids or anchor_id in labeled_ids:
                raise ValueError(f"unknown or duplicate anchor label: {anchor_id}")
            if not isinstance(relevant, bool):
                raise TypeError("relevant must be boolean")
            if critical_reason is not None and critical_reason not in CRITICAL_REASONS:
                raise ValueError(f"invalid critical_reason: {critical_reason}")
            if relevant and critical_reason is not None:
                raise ValueError("a relevant anchor cannot be a critical false positive")
            labeled_ids.add(anchor_id)
            clean_labels.append(
                {
                    "id": anchor_id,
                    "relevant": relevant,
                    "critical_reason": critical_reason,
                }
            )
        if labeled_ids != selected_ids:
            raise ValueError(f"incomplete anchor labels for event {event_id}")
        decisions_by_id[event_id] = decision
        sanitized.append(
            {"event_id": event_id, "anchors": sorted(clean_labels, key=lambda x: x["id"])}
        )
    if set(decisions_by_id) != set(case_by_id):
        raise ValueError("every joinable case must be adjudicated before receipt creation")

    all_labels = [label for decision in sanitized for label in decision["anchors"]]
    relevant_count = sum(1 for label in all_labels if label["relevant"])
    critical_count = sum(1 for label in all_labels if label["critical_reason"] is not None)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "promotion_blocked": result.promotion_blocked,
        "events_input": result.events_input,
        "joinable_cases": len(result.cases),
        "duplicate_event_ids": result.duplicate_event_ids,
        "duplicate_query_events": result.duplicate_query_events,
        "events_without_anchors": result.events_without_anchors,
        "unjoinable_query_events": list(result.unjoinable_query_events),
        "missing_anchor_events": list(result.missing_anchor_events),
        "wrong_key_version_events": list(result.wrong_key_version_events),
        "duplicate_query_rows": result.duplicate_query_rows,
        "anchors_adjudicated": len(all_labels),
        "relevant_anchors": relevant_count,
        "critical_false_positives": critical_count,
        "decisions": sorted(sanitized, key=lambda x: x["event_id"]),
    }
    return receipt
