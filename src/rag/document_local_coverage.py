"""Bounded second-hop recovery inside one authoritative document revision.

The lane starts only from source rows already selected by a validated
structural-neighbour hop.  One read-only STABLE RPC resolves the complete
document family, active revision and exact-blob full-text candidates in the
same PostgreSQL statement snapshot.  The existing retrieval-pool selector
remains the semantic authority; this module only broadens its candidate set
inside an already-proven source boundary.

Version 1 is deliberately ES-only because ``chunks_v2.search_vector`` is
physically built with ``spanish_unaccent``.  Unsupported source scopes are
rejected independently.  There are no model calls, writes, retries, target
IDs, page numbers or gold values in this module.  Ambiguous lifecycle
metadata, overflow and incomplete snapshot receipts all fail closed; the
post-rerank orchestrator contains I/O failures and preserves the prefix.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from contextlib import nullcontext
from itertools import combinations
from typing import Any, Callable

import httpx

from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from ..release_profiles import (
    DOCUMENT_LOCAL_LANE as LANE,
    DOCUMENT_LOCAL_VALIDATION as VALIDATION,
)
from .query_facets import expand_query_facets
from .rerank_pool_coverage import (
    POOL_LIMIT,
    QUERY_CONFIG,
    _incremental_needs,
    _tokens,
    select_rerank_pool_coverage,
)
from .structural_neighbor_coverage import LANE as STRUCTURAL_LANE

SOURCE_LIMIT = 2
DOCUMENT_ROWS_LIMIT = 16
CANDIDATE_LIMIT = 64
# The downstream deterministic selector has one hard pool ceiling.  Keep the
# per-document SQL sentinel independent, but reject a combined two-scope pool
# explicitly before delegation instead of silently relabelling its overflow as
# a semantic miss.
TOTAL_CANDIDATE_LIMIT = POOL_LIMIT
APPEND_LIMIT = 1
MAX_HTTP_REQUESTS = 1
TIMEOUT_SECONDS = 2.0
MAX_ANCHOR_TERMS = 10
MAX_NEED_GROUPS = 3
MAX_NEED_TERMS_PER_GROUP = 6
MAX_TSQUERY_CHARS = 480

_SHA256 = re.compile(r"[0-9a-f]{64}")
SNAPSHOT_RPC = "document_local_snapshot_v2"
SNAPSHOT_SCHEMA = "document_local_snapshot_v2"
_SNAPSHOT_KEYS = {
    "schema",
    "input_status",
    "authorities",
    "document_rows",
    "candidates",
    "rejections",
    "family_rows_read",
    "candidate_rows",
    "candidate_overflow_scopes",
}
_IDENTITY_FIELDS = (
    "document_family",
    "language",
    "doc_type",
    "manufacturer",
    "product_model",
)


def _stable_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "").casefold()))


def _base_trace(*, anchors: int = 0) -> dict[str, Any]:
    return {
        "lane": LANE,
        "validation": VALIDATION,
        "status": "not_applicable",
        "anchor_rows": anchors,
        "source_scopes_considered": 0,
        "document_rows": 0,
        "authoritative_documents": 0,
        "ambiguous_lineages": 0,
        "fts_queries": 0,
        "fts_candidate_rows": 0,
        "eligible_rows": 0,
        "selected_ids": [],
        "http_requests": 0,
        "rows_read": 0,
        "model_calls": 0,
        "database_writes": 0,
        "overflow": False,
    }


def _anchor_scopes(anchor_rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], str]:
    """Extract exact same-blob scopes from validated structural-hop rows."""
    scopes: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in anchor_rows:
        if (
            row.get("retrieval_lane") != STRUCTURAL_LANE
            or row.get("structural_neighbor_validated") is not True
        ):
            continue
        document_id = str(row.get("document_id") or "")
        extraction_sha256 = str(row.get("extraction_sha256") or "").casefold()
        source_file = str(row.get("source_file") or "").strip()
        if not document_id or not _valid_sha256(extraction_sha256) or not source_file:
            continue
        key = (document_id, extraction_sha256, source_file)
        scopes[key] = {
            "document_id": document_id,
            "extraction_sha256": extraction_sha256,
            "source_file": source_file,
            "manufacturer": str(row.get("manufacturer") or ""),
            "product_model": str(row.get("product_model") or ""),
        }
    if not scopes:
        return [], "no_validated_structural_anchor"
    if len(scopes) > SOURCE_LIMIT:
        return [], "source_scope_overflow"
    return list(scopes.values()), "ok"


def _component(start: str, rows_by_id: dict[str, dict[str, Any]]) -> set[str]:
    pending = [start]
    seen: set[str] = set()
    while pending:
        document_id = pending.pop()
        if document_id in seen:
            continue
        seen.add(document_id)
        row = rows_by_id[document_id]
        for field in ("supersedes_id", "superseded_by_id"):
            related = str(row.get(field) or "")
            if related:
                pending.append(related)
    return seen


def resolve_authoritative_documents(
    document_rows: list[dict[str, Any]],
    seed_scopes: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str]:
    """Resolve one exact governed lineage; never infer membership from labels."""
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in document_rows:
        document_id = str(row.get("id") or "")
        if not document_id or document_id in rows_by_id:
            return [], "invalid_or_duplicate_document_identity"
        rows_by_id[document_id] = row

    seed_ids = {scope["document_id"] for scope in seed_scopes}
    if not seed_ids or not seed_ids.issubset(rows_by_id):
        return [], "document_seed_hydration_incomplete"

    # A missing pointer target means the one-hop lifecycle read did not return
    # the complete chain.  Refuse a partial view instead of choosing a leaf.
    for row in document_rows:
        for field in ("supersedes_id", "superseded_by_id"):
            related = str(row.get(field) or "")
            if related and related not in rows_by_id:
                return [], "incomplete_revision_chain"

    scope_by_seed = {scope["document_id"]: scope for scope in seed_scopes}
    processed: set[str] = set()
    authorities: list[dict[str, str]] = []
    for seed_id in sorted(seed_ids):
        if seed_id in processed:
            continue
        component_ids = _component(seed_id, rows_by_id)
        processed.update(component_ids)
        component = [rows_by_id[document_id] for document_id in component_ids]
        lineage_id = str(rows_by_id[seed_id].get("revision_lineage_id") or "")
        if not lineage_id:
            return [], "unverified_document_lineage"
        lineage_members = {
            document_id
            for document_id, row in rows_by_id.items()
            if str(row.get("revision_lineage_id") or "") == lineage_id
        }
        if component_ids != lineage_members or any(
            str(row.get("revision_lineage_id") or "") != lineage_id
            for row in component
        ):
            return [], "incomplete_revision_chain"

        # Descriptive labels are negative consistency checks only.  They can
        # never add or omit a member; exact lineage UUID equality above is the
        # sole positive membership authority.
        identities = {
            tuple(str(row.get(field) or "") for field in _IDENTITY_FIELDS)
            for row in component
        }
        if len(identities) != 1 or any(not part.strip() for part in next(iter(identities))):
            return [], "lineage_identity_drift"

        active = [row for row in component if row.get("status") == "active"]
        if len(active) != 1:
            return [], "ambiguous_active_revision"
        if any(
            row.get("status") not in {"active", "superseded"}
            for row in component
        ):
            return [], "invalid_revision_status"
        if any(
            row.get("status") != "superseded"
            for row in component
            if row is not active[0]
        ):
            return [], "invalid_revision_status"

        # Validate reciprocal pointers and a single acyclic oldest->active chain.
        for row in component:
            document_id = str(row["id"])
            older_id = str(row.get("supersedes_id") or "")
            newer_id = str(row.get("superseded_by_id") or "")
            if older_id and str(rows_by_id[older_id].get("superseded_by_id") or "") != document_id:
                return [], "nonreciprocal_revision_chain"
            if newer_id and str(rows_by_id[newer_id].get("supersedes_id") or "") != document_id:
                return [], "nonreciprocal_revision_chain"
        roots = [row for row in component if not row.get("supersedes_id")]
        if len(roots) != 1:
            return [], "branched_or_cyclic_revision_chain"
        walked: list[str] = []
        cursor = roots[0]
        while cursor is not None:
            document_id = str(cursor["id"])
            if document_id in walked:
                return [], "branched_or_cyclic_revision_chain"
            walked.append(document_id)
            newer_id = str(cursor.get("superseded_by_id") or "")
            cursor = rows_by_id.get(newer_id) if newer_id else None
        active_row = active[0]
        if set(walked) != component_ids or walked[-1] != str(active_row["id"]):
            return [], "branched_or_cyclic_revision_chain"
        if active_row.get("superseded_by_id") is not None:
            return [], "active_revision_has_successor"

        active_id = str(active_row["id"])
        active_sha = str(active_row.get("source_pdf_sha256") or "").casefold()
        source_file = str(active_row.get("source_pdf_filename") or "").strip()
        if not _valid_sha256(active_sha) or not source_file:
            return [], "active_revision_missing_content_identity"

        matching_seeds = [
            scope_by_seed[document_id]
            for document_id in component_ids & seed_ids
        ]
        exact_active_seeds = [
            scope
            for scope in matching_seeds
            if scope["document_id"] == active_id
            and scope["extraction_sha256"] == active_sha
            and scope["source_file"] == source_file
        ]
        if not exact_active_seeds:
            return [], "active_revision_not_bound_to_anchor_blob"
        authorities.append(
            {
                "document_id": active_id,
                "revision_lineage_id": lineage_id,
                "extraction_sha256": active_sha,
                "source_file": source_file,
                "language": str(active_row.get("language") or ""),
                "revision": str(active_row.get("revision") or ""),
            }
        )

    if len(authorities) > SOURCE_LIMIT:
        return [], "source_scope_overflow"
    return authorities, "ok"


def build_document_local_query_plan(
    query: str,
    seed_scopes: list[dict[str, str]],
) -> dict[str, Any] | None:
    """Build a bounded, operator-safe tsquery from versioned query facets."""
    facet_plan = expand_query_facets(query, config_path=QUERY_CONFIG)
    expanded = list(facet_plan.get("needs") or [])
    needs = _incremental_needs(query, expanded)
    identity_terms = {
        token
        for scope in seed_scopes
        for field in ("manufacturer", "product_model")
        for token in _tokens(scope.get(field) or "")
    }
    anchors = []
    for token in _tokens(query):
        if token not in identity_terms and token not in anchors:
            anchors.append(token)
    anchors = anchors[:MAX_ANCHOR_TERMS]

    anchor_set = set(anchors)
    need_groups: list[list[str]] = []
    for need in needs[:MAX_NEED_GROUPS]:
        group: list[str] = []
        for token in _tokens(need):
            if token not in anchor_set and token not in group:
                group.append(token)
        if group:
            need_groups.append(group[:MAX_NEED_TERMS_PER_GROUP])
    if len(anchors) < 2 or not need_groups:
        return None
    anchor_clause = f"({'|'.join(anchors)})"
    group_clauses = [f"({'|'.join(group)})" for group in need_groups]
    if len(group_clauses) == 1:
        need_clause = group_clauses[0]
    else:
        pair_clauses = [
            f"({left}&{right})"
            for left, right in combinations(group_clauses, 2)
        ]
        need_clause = f"({'|'.join(pair_clauses)})"
    tsquery = f"{anchor_clause}&{need_clause}"
    if len(tsquery) > MAX_TSQUERY_CHARS:
        return None
    receipt = {
        "archetype": facet_plan.get("archetype"),
        "anchor_terms": anchors,
        "need_groups": need_groups,
        "fts_config": "spanish_unaccent",
        "query_facets_sha256": hashlib.sha256(QUERY_CONFIG.read_bytes()).hexdigest(),
    }
    return {**receipt, "tsquery": tsquery, "sha256": _stable_sha256(receipt)}


def fetch_document_local_candidates(
    query: str,
    anchor_rows: list[dict[str, Any]],
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    max_http_requests: int = MAX_HTTP_REQUESTS,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    """Read one atomic lifecycle + exact-blob FTS snapshot using GET only."""
    trace = _base_trace(anchors=len(anchor_rows))
    scopes, scope_reason = _anchor_scopes(anchor_rows)
    trace["source_scopes_considered"] = len(scopes)
    if scope_reason != "ok":
        trace["status"] = scope_reason
        trace["overflow"] = scope_reason == "source_scope_overflow"
        return [], [], trace
    plan = build_document_local_query_plan(query, scopes)
    if plan is None:
        trace["status"] = "no_bounded_query_plan"
        return [], [], trace
    trace["query_plan_sha256"] = plan["sha256"]
    trace["query_facets_sha256"] = plan["query_facets_sha256"]
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for document-local read")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 0 < timeout_seconds <= TIMEOUT_SECONDS
        or isinstance(max_http_requests, bool)
        or not isinstance(max_http_requests, int)
        or not 1 <= max_http_requests <= MAX_HTTP_REQUESTS
    ):
        raise RuntimeError("unsafe document-local read budget")

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    started = time.monotonic()
    context = httpx.Client(timeout=timeout_seconds) if client is None else nullcontext(client)
    with context as request_client:
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("document-local read deadline exceeded")
        if max_http_requests < 1:
            raise RuntimeError("document-local HTTP request cap exceeded")
        response = request_client.get(
            f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/{SNAPSHOT_RPC}",
            headers=headers,
            params={
                "anchor_scopes": json.dumps(
                    [
                        {
                            "document_id": scope["document_id"],
                            "extraction_sha256": scope["extraction_sha256"],
                            "source_file": scope["source_file"],
                        }
                        for scope in scopes
                    ],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "fts_query": plan["tsquery"],
                "family_limit": str(DOCUMENT_ROWS_LIMIT),
                "candidate_limit": str(CANDIDATE_LIMIT),
            },
            timeout=remaining,
        )
        trace["http_requests"] = 1
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict) or set(payload) != _SNAPSHOT_KEYS:
        raise RuntimeError("document-local snapshot returned invalid payload")
    if payload.get("schema") != SNAPSHOT_SCHEMA or payload.get("input_status") != "ok":
        raise RuntimeError("document-local snapshot contract mismatch")
    for field, ceiling in (
        ("family_rows_read", SOURCE_LIMIT * (DOCUMENT_ROWS_LIMIT + 1)),
        ("candidate_rows", SOURCE_LIMIT * (CANDIDATE_LIMIT + 1)),
    ):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= ceiling:
            raise RuntimeError("document-local snapshot count mismatch")
    raw_authorities = payload.get("authorities")
    document_rows = payload.get("document_rows")
    raw_candidates = payload.get("candidates")
    rejections = payload.get("rejections")
    raw_overflow_ranks = payload.get("candidate_overflow_scopes")
    if any(
        not isinstance(value, list)
        or any(not isinstance(row, dict) for row in value)
        for value in (raw_authorities, document_rows, raw_candidates, rejections)
    ) or not isinstance(raw_overflow_ranks, list):
        raise RuntimeError("document-local snapshot rows are invalid")
    if len(document_rows) != payload["family_rows_read"] or len(raw_candidates) != payload[
        "candidate_rows"
    ]:
        raise RuntimeError("document-local snapshot cardinality mismatch")

    valid_ranks = set(range(1, len(scopes) + 1))
    if (
        any(
            isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank not in valid_ranks
            for rank in raw_overflow_ranks
        )
        or raw_overflow_ranks != sorted(set(raw_overflow_ranks))
    ):
        raise RuntimeError("document-local snapshot overflow mismatch")
    overflow_ranks = set(raw_overflow_ranks)
    rejected_ranks: set[int] = set()
    authority_rejections: list[str] = []
    for rejection in rejections:
        rank = rejection.get("scope_rank")
        reason = rejection.get("reason")
        if (
            set(rejection) != {"scope_rank", "reason"}
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank not in valid_ranks
            or rank in rejected_ranks
            or not isinstance(reason, str)
            or not reason
            or reason == "ok"
        ):
            raise RuntimeError("document-local snapshot rejection mismatch")
        rejected_ranks.add(rank)
        authority_rejections.append(reason)

    authorities: list[dict[str, str]] = []
    authority_by_rank: dict[int, dict[str, str]] = {}
    authoritative_identity_by_rank: dict[int, dict[str, str]] = {}
    authority_document_ids: set[str] = set()
    for raw_authority in raw_authorities:
        required = {
            "scope_rank",
            "document_id",
            "revision_lineage_id",
            "extraction_sha256",
            "source_file",
            "language",
            "revision",
            "family_rows",
        }
        rank = raw_authority.get("scope_rank")
        family_rows = raw_authority.get("family_rows")
        if (
            set(raw_authority) != required
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank not in valid_ranks
            or rank in rejected_ranks
            or rank in authority_by_rank
            or isinstance(family_rows, bool)
            or not isinstance(family_rows, int)
            or not 1 <= family_rows <= DOCUMENT_ROWS_LIMIT
        ):
            raise RuntimeError("document-local snapshot authority mismatch")
        component_rows = []
        for source_row in document_rows:
            source_rank = source_row.get("scope_rank")
            if (
                isinstance(source_rank, bool)
                or not isinstance(source_rank, int)
                or source_rank not in valid_ranks
            ):
                raise RuntimeError("document-local snapshot family rank mismatch")
            if source_rank == rank:
                component = dict(source_row)
                component.pop("scope_rank")
                component_rows.append(component)
        if len(component_rows) != family_rows:
            raise RuntimeError("document-local snapshot family count mismatch")
        resolved, reason = resolve_authoritative_documents(
            component_rows, [scopes[rank - 1]]
        )
        authority = {
            "document_id": str(raw_authority.get("document_id") or ""),
            "revision_lineage_id": str(
                raw_authority.get("revision_lineage_id") or ""
            ),
            "extraction_sha256": str(
                raw_authority.get("extraction_sha256") or ""
            ).casefold(),
            "source_file": str(raw_authority.get("source_file") or ""),
            "language": str(raw_authority.get("language") or ""),
            "revision": str(raw_authority.get("revision") or ""),
        }
        if (
            reason != "ok"
            or resolved != [authority]
            or authority["language"].casefold() != "es"
            or authority["document_id"] in authority_document_ids
        ):
            raise RuntimeError("document-local snapshot lifecycle receipt mismatch")
        active_rows = [
            row
            for row in component_rows
            if str(row.get("id") or "") == authority["document_id"]
        ]
        if len(active_rows) != 1:
            raise RuntimeError("document-local active identity receipt mismatch")
        authoritative_identity = {
            field: str(active_rows[0].get(field) or "")
            for field in _IDENTITY_FIELDS
        }
        if (
            any(not value.strip() for value in authoritative_identity.values())
            or authoritative_identity["language"] != authority["language"]
            or str(active_rows[0].get("revision_lineage_id") or "")
                != authority["revision_lineage_id"]
        ):
            raise RuntimeError("document-local authoritative identity mismatch")
        authority_document_ids.add(authority["document_id"])
        authority_by_rank[rank] = authority
        authoritative_identity_by_rank[rank] = authoritative_identity
        authorities.append(authority)

    if set(authority_by_rank) | rejected_ranks != valid_ranks:
        raise RuntimeError("document-local snapshot scope partition mismatch")
    if overflow_ranks - set(authority_by_rank):
        raise RuntimeError("document-local snapshot overflow scope mismatch")
    trace["document_rows"] = len(document_rows)
    trace["rows_read"] = len(document_rows) + len(raw_candidates)
    trace["ambiguous_lineages"] = len(authority_rejections)
    if authority_rejections:
        trace["authority_rejections"] = sorted(authority_rejections)
        trace["overflow"] = "document_scope_overflow" in authority_rejections
    if not authorities:
        if overflow_ranks:
            raise RuntimeError("document-local snapshot orphan overflow")
        trace["status"] = (
            authority_rejections[0]
            if len(set(authority_rejections)) == 1
            else "no_authoritative_source_scope"
        )
        return [], [], trace

    trace["snapshot_authoritative_documents"] = len(authorities)
    trace["fts_queries"] = len(authorities)
    trace["fts_candidate_rows"] = len(raw_candidates)
    snapshot_sha256 = _stable_sha256(payload)
    trace["snapshot_sha256"] = snapshot_sha256
    candidates_with_rank: list[tuple[int, dict[str, Any]]] = []
    observed_overflow_ranks: set[int] = set()
    seen_candidate_ranks: dict[int, set[int]] = {}
    for source_row in raw_candidates:
        rank = source_row.get("authority_scope_rank")
        candidate_rank = source_row.get("snapshot_candidate_rank")
        authority = authority_by_rank.get(rank) if isinstance(rank, int) else None
        if (
            authority is None
            or isinstance(candidate_rank, bool)
            or not isinstance(candidate_rank, int)
            or not 1 <= candidate_rank <= CANDIDATE_LIMIT + 1
            or candidate_rank in seen_candidate_ranks.setdefault(rank, set())
            or source_row.get("duplicate_of") is not None
            or str(source_row.get("document_id") or "")
                != authority["document_id"]
            or str(source_row.get("extraction_sha256") or "").casefold()
                != authority["extraction_sha256"]
            or str(source_row.get("source_file") or "")
                != authority["source_file"]
            or str(source_row.get("document_revision_lineage_id") or "")
                != authority["revision_lineage_id"]
        ):
            trace["status"] = "candidate_scope_mismatch"
            return [], [], trace
        seen_candidate_ranks[rank].add(candidate_rank)
        if candidate_rank > CANDIDATE_LIMIT:
            observed_overflow_ranks.add(rank)
            continue
        row = dict(source_row)
        row.pop("authority_scope_rank", None)
        row.pop("snapshot_candidate_rank", None)
        authoritative_identity = authoritative_identity_by_rank[rank]
        row.update(
            {
                **authoritative_identity,
                "document_status": "active",
                "document_revision": authority["revision"],
                "document_revision_lineage_id": authority[
                    "revision_lineage_id"
                ],
                "document_local_candidate_rank": candidate_rank - 1,
                "document_local_snapshot_sha256": snapshot_sha256,
                "document_local_authority_document_id": authority["document_id"],
                "document_local_authority_extraction_sha256": authority[
                    "extraction_sha256"
                ],
                "document_local_authority_source_file": authority["source_file"],
                "document_local_authority_revision_lineage_id": authority[
                    "revision_lineage_id"
                ],
                **{
                    f"document_local_authority_{field}": value
                    for field, value in authoritative_identity.items()
                },
            }
        )
        candidates_with_rank.append((rank, row))

    if any(
        ranks != set(range(1, max(ranks) + 1))
        for ranks in seen_candidate_ranks.values()
        if ranks
    ) or observed_overflow_ranks != overflow_ranks:
        raise RuntimeError("document-local snapshot candidate rank mismatch")
    candidates = [
        row for rank, row in candidates_with_rank if rank not in overflow_ranks
    ]
    if len(candidates) > TOTAL_CANDIDATE_LIMIT:
        trace.update(status="combined_candidate_cap_exceeded", overflow=True)
        return [], [], trace

    eligible_authorities = [
        authority
        for rank, authority in authority_by_rank.items()
        if rank not in overflow_ranks
    ]
    if overflow_ranks:
        trace["candidate_overflow_scopes"] = sorted(overflow_ranks)
        trace["overflow"] = True
    trace["authoritative_documents"] = len(eligible_authorities)
    if not eligible_authorities:
        trace["status"] = "candidate_cap_exceeded"
        return [], [], trace

    trace["status"] = "fetched" if candidates else "no_fts_candidates"
    return candidates, eligible_authorities, trace


def _matches_authority(
    row: dict[str, Any], authorities: list[dict[str, str]]
) -> bool:
    key = (
        str(row.get("document_id") or ""),
        str(row.get("document_revision_lineage_id") or ""),
        str(row.get("extraction_sha256") or "").casefold(),
        str(row.get("source_file") or ""),
    )
    allowed = {
        (
            authority["document_id"],
            authority["revision_lineage_id"],
            authority["extraction_sha256"],
            authority["source_file"],
        )
        for authority in authorities
    }
    return key in allowed and row.get("duplicate_of") is None


def select_document_local_coverage(
    query: str,
    candidates: list[dict[str, Any]],
    covered_context: list[dict[str, Any]],
    authorities: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select one semantic complement and replace pool stamps atomically."""
    trace = _base_trace()
    trace["fts_candidate_rows"] = len(candidates)
    if not candidates or not authorities:
        trace["status"] = "no_candidates"
        return [], trace
    if len(candidates) > TOTAL_CANDIDATE_LIMIT:
        trace.update(status="combined_candidate_cap_exceeded", overflow=True)
        return [], trace
    if any(not _matches_authority(row, authorities) for row in candidates):
        trace["status"] = "candidate_scope_mismatch"
        return [], trace

    # Rank the complete, authority-bounded candidate set first.  If its best
    # row is already present, the information is satisfied; do not append a
    # weaker second choice merely because the winner was served by another lane.
    ranked, selector_trace = select_rerank_pool_coverage(
        query,
        candidates,
        [],
        apply_catalog_scope=False,
    )
    trace["eligible_rows"] = int(selector_trace.get("eligible_rows") or 0)
    trace["catalog_scope_applied"] = selector_trace.get("catalog_scope_applied")
    if not ranked:
        trace["status"] = (
            "selector_pool_overflow"
            if selector_trace.get("status") == "not_applicable_or_pool_overflow"
            else "no_query_aligned_candidate"
        )
        trace["overflow"] = trace["status"] == "selector_pool_overflow"
        return [], trace
    winner = ranked[0]
    winner_id = str(winner.get("id") or "")
    covered_ids = {str(row.get("id") or "") for row in covered_context}
    if winner_id in covered_ids:
        trace["status"] = "best_candidate_already_covered"
        return [], trace
    if not _matches_authority(winner, authorities):
        trace["status"] = "winner_scope_mismatch"
        return [], trace

    selected = dict(winner)
    for key in list(selected):
        if key.startswith("rerank_pool_"):
            selected.pop(key)
    selected.update(
        {
            "retrieval_lane": LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": VALIDATION,
            "document_local_coverage_rank": 1,
            "local_semantic_validated": True,
        }
    )
    trace.update(status="selected", selected_ids=[winner_id])
    return [selected], trace


def collect_document_local_coverage(
    query: str,
    anchor_rows: list[dict[str, Any]],
    covered_context: list[dict[str, Any]],
    *,
    fetcher: Callable[..., tuple[
        list[dict[str, Any]], list[dict[str, str]], dict[str, Any]
    ]] = fetch_document_local_candidates,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch then select without exposing a selector override to production."""
    candidates, authorities, read_trace = fetcher(query, anchor_rows)
    if not candidates or not authorities:
        return [], read_trace
    selected, selection_trace = select_document_local_coverage(
        query, candidates, covered_context, authorities
    )
    trace = dict(read_trace)
    trace.update(
        {
            "status": selection_trace["status"],
            "eligible_rows": selection_trace.get("eligible_rows", 0),
            "selected_ids": selection_trace.get("selected_ids", []),
            "catalog_scope_applied": selection_trace.get("catalog_scope_applied"),
            "model_calls": 0,
            "database_writes": 0,
        }
    )
    return selected[:APPEND_LIMIT], trace
