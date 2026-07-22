"""Bounded second-hop recovery inside one authoritative document revision.

The lane starts from an exact-blob hint selected by a governed catalog source
contract or, as a fallback, by the protected-prefix/structural recovery path.
One read-only STABLE RPC resolves the complete document family, active revision
and exact-blob full-text candidates in the same PostgreSQL statement snapshot.
The existing retrieval-pool selector remains the semantic authority; this
module only broadens its candidate set inside a source boundary revalidated by
the RPC.

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
from .mp_lexicon import line_spans, sentence_spans
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
# s279 A5' [TSQUERY-TRIM · SUELO] (cambio de diseño POST-census): el suelo por
# need-group del trim.  Un grupo que el gate A7 puede usar (>=N_FACET términos
# ANTES del trim) jamás se degrada por debajo de N_FACET términos por el recorte
# — la coherencia A5<->A7 (un grupo gate-elegible no debe quedar sub-umbral por
# el trim).  Los grupos de 1-2 términos (que A7 ya excluye) conservan el suelo
# histórico de 1.  DEBE igualar ``post_rerank_coverage.N_FACET`` (el umbral del
# gate); un test de sincronía lo pinea contra la deriva.  Constante LOCAL
# deliberada: el módulo no importa post_rerank_coverage en import-time (patrón de
# desacople existente — los imports de ese módulo son function-local).
NEED_GROUP_GATE_FLOOR = 3
# s279 §3 [SEAM-DELEGADO]: la vía document-local bajo DOCUMENT_LOCAL_SELECTION_V2
# consume el fork de facetas v5 con multi-match acotado y un tope de need-groups
# PROPIO de la vía; la constante global MAX_NEED_GROUPS=3 queda intacta (y por
# tanto el plan v4 flag-off byte-inerte).  El v5 vive junto al v4 en config/.
MAX_NEED_GROUPS_MULTI = 5
QUERY_CONFIG_V5 = QUERY_CONFIG.parent / "retrieval_facets_v5_document_local.yaml"

_SHA256 = re.compile(r"[0-9a-f]{64}")
# s278 (DEC-150): flip a v3 — mismo contrato que v2 con la comparación de blob
# CANÓNICA en SQL (strip de UNA extensión .pdf, los DOS sitios; migración aplicada
# por Alberto 22-jul desde migration_proposals/20260722200000_...). El v2 sigue
# vivo en DB para los seals históricos del P1.
SNAPSHOT_RPC = "document_local_snapshot_v3"
SNAPSHOT_SCHEMA = "document_local_snapshot_v3"
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

# s278 §4 — identidad de blob canónica documento<->chunks/doc_map.
BLOB_EXTENSION = ".pdf"
# s278 §4 — clase de source card de PROSA (flag PROSE_SOURCE_CARD, default off).
PROSE_SOURCE_CARD_CLASS = "prose_source_card"
PROSE_SOURCE_CARD_KIND = "prose_sentence_span_v1"
MAX_PROSE_SOURCE_CARD_CHARS = 600


def canonical_blob_stem(name: str) -> str:
    """Canonical form of a source-blob name: strip exactly ONE declared
    ``.pdf`` suffix (case-sensitive); everything else is returned verbatim."""
    text = str(name or "")
    if text.endswith(BLOB_EXTENSION):
        return text[: -len(BLOB_EXTENSION)]
    return text


def blob_identity_match(a: str, b: str) -> bool:
    """THE single canonical blob-identity comparison (s278 §4) — SYMMETRIC.

    Contract: each side is reduced to its canonical stem by stripping exactly
    one DECLARED ``.pdf`` extension (case-sensitive, at most once), then the
    stems must be STRICTLY equal and non-empty.  The matching is deliberately
    SYMMETRIC — either side may carry the declared extension — because blob
    identity is already bound by ``document_id`` + ``extraction_sha256`` +
    ``revision_lineage_id`` at every seam that consults this helper; the name
    only corroborates (s278 dúo r2, Fable#5).  Nothing else is normalized — no
    case folding, no whitespace trimming, no other extensions, no repeated
    strips — so the only mismatch this closes is the confirmed
    ``documents.source_pdf_filename = '<stem>.pdf'`` vs chunks/doc_map
    ``source_file = '<stem>'`` drift.  Every other difference (``<stem>-v2``,
    ``<stem>.pdf.pdf``, case variants, empty names) fails closed.
    """
    stem_a = canonical_blob_stem(a)
    stem_b = canonical_blob_stem(b)
    return bool(stem_a) and stem_a == stem_b


def _prose_source_card_enabled() -> bool:
    """Flag estricto default-off, releído en runtime (patrón contract_enabled)."""
    from ..config import _strict_on_off

    return _strict_on_off("PROSE_SOURCE_CARD")


def _document_local_selection_v2_enabled() -> bool:
    """s279 §0 [PERFIL-CAPACIDAD]: flag profile-owned default-off, releído en
    runtime (patrón contract_enabled).  Off ⇒ el alcance de selección v2
    (compuertas 1 y 3) ni se alcanza; el plan/receipt queda byte-inerte."""
    from ..config import _strict_on_off

    return _strict_on_off("DOCUMENT_LOCAL_SELECTION_V2")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        "seed_scope_count": 0,
        "seed_sources": {},
        "seed_scopes_sha256": _stable_sha256([]),
        "seed_scopes_truncated": False,
        "document_rows": 0,
        "authoritative_documents": 0,
        "ambiguous_lineages": 0,
        "fts_queries": 0,
        "fts_candidate_rows": 0,
        "eligible_rows": 0,
        "selected_ids": [],
        "satisfied_ids": [],
        "satisfaction_route": None,
        "http_requests": 0,
        "rows_read": 0,
        "model_calls": 0,
        "database_writes": 0,
        "overflow": False,
    }


def _anchor_scopes(anchor_rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], str]:
    """Extract exact source hints admitted by the closed anchor-route set."""
    scopes: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in anchor_rows:
        anchor_route = row.get("document_local_anchor_route")
        structural_anchor = (
            row.get("retrieval_lane") == STRUCTURAL_LANE
            and row.get("structural_neighbor_validated") is True
            and anchor_route in {None, "served_structural_append"}
        )
        protected_prefix_anchor = anchor_route == "protected_rerank_prefix"
        source_contract_anchor = anchor_route == "governed_source_contract"
        if not (
            structural_anchor
            or protected_prefix_anchor
            or source_contract_anchor
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
            # s278 §4: el seed viene de chunks/doc_map y el activo de
            # documents.source_pdf_filename — única comparación canónica.
            and blob_identity_match(source_file, scope["source_file"])
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
    if _document_local_selection_v2_enabled():
        # s279 compuerta 3 [SEAM-DELEGADO · VALIDADOR · TRIM]: bajo el flag la
        # función pura re-invocable (A2) sirve el plan v5 (multi-match acotado +
        # trim A5).  El cuerpo v4 de abajo queda inalcanzable para flag-off.
        return _build_document_local_query_plan_v5(query, seed_scopes)
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
    tsquery = _compose_document_local_tsquery(anchors, need_groups)
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


def _compose_document_local_tsquery(
    anchors: list[str], need_groups: list[list[str]]
) -> str:
    """THE single anchors∧need-clause tsquery composition.

    Extracted verbatim from the historical v4 body so the flag-off plan stays
    byte-identical (pinned by the golden-receipt equality test) and the v5 trim
    reasons over the exact operator shape the RPC will receive.
    """
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
    return f"{anchor_clause}&{need_clause}"


def _trim_document_local_need_groups(
    anchors: list[str], need_groups: list[list[str]]
) -> tuple[list[list[str]] | None, dict[str, Any]]:
    """s279 §3 / A5 + A5' [TSQUERY-TRIM · SUELO]: pre-registered deterministic trim.

    While the composed tsquery exceeds ``MAX_TSQUERY_CHARS``: (1) round-robin
    from the LAST need-group, dropping the last term of each group, never below
    its A5' FLOOR — ``NEED_GROUP_GATE_FLOOR`` (=N_FACET) for a group that was
    gate-eligible before the trim (>=N_FACET terms), 1 for the 1-2 term groups
    A7 already excludes; (2) if it still does not fit, drop WHOLE groups from the
    last, keeping at least one; (3) if the minimal base (anchors ∧ a single
    floored group) still exceeds the bound, refuse the plan (``None``).  Removed
    terms and groups are listed in removal order and group indices stay stable
    (only the tail is ever removed) — never adjusted after the RPC result.

    A5' (design change POST-census, s279): the round-robin can no longer degrade a
    group the A7 gate would use below the gate's own N_FACET threshold — the
    coherence A5<->A7.  When flooring every gate-eligible group still overflows
    (the floor-infeasible regime), phase 2 removes whole tail groups; it never
    leaves a sub-N_FACET "zombie" group.  The floor is positional and computed
    ONCE from the untrimmed groups.
    """
    groups = [list(group) for group in need_groups]
    terms_removed: list[dict[str, Any]] = []
    groups_removed: list[dict[str, Any]] = []
    if len(_compose_document_local_tsquery(anchors, groups)) <= MAX_TSQUERY_CHARS:
        return groups, {
            "trimmed": False,
            "terms_removed": [],
            "groups_removed": [],
        }
    # A5' per-group floor by PRE-trim size (stable positional index): a group the
    # A7 gate can use keeps at least N_FACET terms; the 1-2 term groups keep 1.
    floors = [
        NEED_GROUP_GATE_FLOOR if len(group) >= NEED_GROUP_GATE_FLOOR else 1
        for group in need_groups
    ]
    # Phase 1: round-robin last-term removal, never below each group's floor.
    while (
        len(_compose_document_local_tsquery(anchors, groups)) > MAX_TSQUERY_CHARS
    ):
        removed_in_round = False
        for index in range(len(groups) - 1, -1, -1):
            if len(groups[index]) > floors[index]:
                dropped = groups[index].pop()
                terms_removed.append({"group_index": index, "term": dropped})
                removed_in_round = True
                if (
                    len(_compose_document_local_tsquery(anchors, groups))
                    <= MAX_TSQUERY_CHARS
                ):
                    break
        if not removed_in_round:
            break
    # Phase 2: drop whole groups from the last, keeping at least one.
    if len(_compose_document_local_tsquery(anchors, groups)) > MAX_TSQUERY_CHARS:
        while (
            len(groups) > 1
            and len(_compose_document_local_tsquery(anchors, groups))
            > MAX_TSQUERY_CHARS
        ):
            dropped_group = groups.pop()
            groups_removed.append(
                {"group_index": len(groups), "terms": dropped_group}
            )
    trim_receipt: dict[str, Any] = {
        "trimmed": True,
        "terms_removed": terms_removed,
        "groups_removed": groups_removed,
    }
    # Phase 3: base still over the bound -> refuse (existing plan-None conduct).
    if len(_compose_document_local_tsquery(anchors, groups)) > MAX_TSQUERY_CHARS:
        trim_receipt["blocked"] = "base_exceeds_tsquery_bound"
        return None, trim_receipt
    return groups, trim_receipt


def _build_document_local_query_plan_v5(
    query: str,
    seed_scopes: list[dict[str, str]],
) -> dict[str, Any] | None:
    """s279 compuerta 3: document-local plan from the v5 facet fork.

    LOCAL PURE re-invocable function (A2): depends only on ``(query,
    seed_scopes)`` and the flag; it never touches fetch state.  The v5 fork is
    loaded with bounded multi-match (the phase-I signature) and its own
    ``MAX_NEED_GROUPS_MULTI`` cap.  need-groups travel with a stable positional
    index (for ``plan_sha256`` and the phase-III per-group assignment) and the
    A5 trim keeps the tsquery within ``MAX_TSQUERY_CHARS``.
    """
    facet_plan = expand_query_facets(
        query, config_path=QUERY_CONFIG_V5, multi_match=True
    )
    expanded = list(facet_plan.get("needs") or [])
    needs = _incremental_needs(query, expanded)
    identity_terms = {
        token
        for scope in seed_scopes
        for field in ("manufacturer", "product_model")
        for token in _tokens(scope.get(field) or "")
    }
    anchors: list[str] = []
    for token in _tokens(query):
        if token not in identity_terms and token not in anchors:
            anchors.append(token)
    anchors = anchors[:MAX_ANCHOR_TERMS]

    anchor_set = set(anchors)
    need_groups: list[list[str]] = []
    for need in needs[:MAX_NEED_GROUPS_MULTI]:
        group: list[str] = []
        for token in _tokens(need):
            if token not in anchor_set and token not in group:
                group.append(token)
        if group:
            need_groups.append(group[:MAX_NEED_TERMS_PER_GROUP])
    if len(anchors) < 2 or not need_groups:
        return None
    trimmed_groups, trim_receipt = _trim_document_local_need_groups(
        anchors, need_groups
    )
    if trimmed_groups is None:
        return None
    tsquery = _compose_document_local_tsquery(anchors, trimmed_groups)
    receipt = {
        "archetype": facet_plan.get("archetype"),
        "archetypes": list(facet_plan.get("archetypes") or []),
        "anchor_terms": anchors,
        "need_groups": trimmed_groups,
        "fts_config": "spanish_unaccent",
        "query_facets_sha256": hashlib.sha256(
            QUERY_CONFIG_V5.read_bytes()
        ).hexdigest(),
        "config": "v5",
        "trim": trim_receipt,
    }
    return {**receipt, "tsquery": tsquery, "sha256": _stable_sha256(receipt)}


def _combined_waterfall_truncation(
    candidates_with_rank: list[tuple[int, dict[str, Any]]],
    authority_by_rank: dict[int, dict[str, str]],
    overflow_ranks: set[int],
    trace: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    """s279 compuerta 1 [WATERFALL]: work-conserving combined truncation.

    An overflowing scope is NO LONGER discarded whole (that total discard stays
    on flag-off only); each scope keeps its first ``CANDIDATE_LIMIT`` rows by
    chunk_index (the SQL-guaranteed order the RPC returns).  A deterministic
    single-pass waterfall then caps the combined pool at
    ``TOTAL_CANDIDATE_LIMIT``: ``floor(cap / n_scopes)`` per scope in
    ``source_file`` asc order, each takes ``min(observed, quota)`` and its unused
    quota spills to the next scope in one pass (10+65⇒10+54, 65+65⇒32+32,
    n=1⇒64).  Pinned to two scopes (A10).
    """
    assert SOURCE_LIMIT == 2  # A10: the single-pass spill is a two-scope pin.
    eligible_ranks = sorted(authority_by_rank)
    per_scope: dict[int, list[dict[str, Any]]] = {
        rank: [] for rank in eligible_ranks
    }
    for rank, row in candidates_with_rank:
        per_scope[rank].append(row)
    # Stable spill order: source_file asc (design §1), rank as the tiebreak.
    ordered_ranks = sorted(
        eligible_ranks,
        key=lambda rank: (authority_by_rank[rank]["source_file"], rank),
    )
    base_quota = (
        TOTAL_CANDIDATE_LIMIT // len(ordered_ranks) if ordered_ranks else 0
    )
    carry = 0
    kept: list[dict[str, Any]] = []
    truncation: list[dict[str, Any]] = []
    for rank in ordered_ranks:
        available = per_scope[rank]
        quota = base_quota + carry
        retained = min(len(available), quota)
        carry = quota - retained
        kept.extend(available[:retained])
        overflowed = rank in overflow_ranks
        truncation.append(
            {
                "scope_rank": rank,
                "source_file": authority_by_rank[rank]["source_file"],
                "observed_rows": ">=65" if overflowed else len(available),
                "candidate_truncated": overflowed,
                "available_rows": len(available),
                "waterfall_quota": quota,
                "retained": retained,
            }
        )
    eligible_authorities = [authority_by_rank[rank] for rank in eligible_ranks]
    trace["candidate_waterfall"] = truncation
    trace["candidate_truncated"] = any(
        entry["candidate_truncated"] for entry in truncation
    )
    if overflow_ranks:
        trace["candidate_overflow_scopes"] = sorted(overflow_ranks)
        trace["overflow"] = True
    trace["authoritative_documents"] = len(eligible_authorities)
    trace["status"] = "fetched" if kept else "no_fts_candidates"
    return kept, eligible_authorities, trace


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
    trace["seed_scope_count"] = len(scopes)
    trace["seed_sources"] = {
        route: sum(
            row.get("document_local_anchor_route") == route for row in anchor_rows
        )
        for route in (
            "governed_source_contract",
            "protected_rerank_prefix",
            "served_structural_append",
        )
        if any(row.get("document_local_anchor_route") == route for row in anchor_rows)
    }
    trace["seed_scopes_sha256"] = _stable_sha256(
        [
            {
                "document_id": scope["document_id"],
                "extraction_sha256": scope["extraction_sha256"],
                "source_file": scope["source_file"],
            }
            for scope in scopes
        ]
    )
    trace["seed_scopes_truncated"] = any(
        row.get("document_local_anchor_scopes_truncated") is True
        for row in anchor_rows
    )
    if scope_reason != "ok":
        trace["status"] = scope_reason
        trace["overflow"] = scope_reason == "source_scope_overflow"
        return [], [], trace
    plan = build_document_local_query_plan(query, scopes)
    if plan is None:
        # s279 compuerta 1 (§1 / A3): plan None sigue APAGANDO el lane, pero bajo
        # el flag el receipt lo declara VISIBLE en vez del silencioso
        # no_bounded_query_plan.
        trace["status"] = (
            "blocked_tsquery_unrepresentable"
            if _document_local_selection_v2_enabled()
            else "no_bounded_query_plan"
        )
        return [], [], trace
    trace["query_plan_sha256"] = plan["sha256"]
    trace["query_facets_sha256"] = plan["query_facets_sha256"]
    if _document_local_selection_v2_enabled():
        # s279 compuerta 3 (B4): estampa qué config sirvió el plan y el trim
        # determinista (términos/grupos retirados).  Byte-inerte para flag-off.
        trace["query_plan_config"] = plan["config"]
        trace["query_plan_trim"] = plan["trim"]
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
            # s278 §4: candidato = chunk, autoridad = documents; misma y única
            # comparación canónica de blob (fail-closed para el resto).
            or not blob_identity_match(
                authority["source_file"],
                str(source_row.get("source_file") or ""),
            )
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
    if _document_local_selection_v2_enabled():
        # s279 compuerta 1 [WATERFALL]: truncado combinado work-conserving.  El
        # descarte total de un scope con overflow (bloque de abajo) queda SOLO
        # para flag-off.
        return _combined_waterfall_truncation(
            candidates_with_rank, authority_by_rank, overflow_ranks, trace
        )
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
    if row.get("duplicate_of") is not None:
        return False
    document_id = str(row.get("document_id") or "")
    lineage_id = str(row.get("document_revision_lineage_id") or "")
    extraction_sha256 = str(row.get("extraction_sha256") or "").casefold()
    source_file = str(row.get("source_file") or "")
    return any(
        document_id == authority["document_id"]
        and lineage_id == authority["revision_lineage_id"]
        and extraction_sha256 == authority["extraction_sha256"]
        # s278 §4: chunk vs documents — única comparación canónica de blob.
        and blob_identity_match(authority["source_file"], source_file)
        for authority in authorities
    )


def _is_complete_sentence_span(content: str, start: int, end: int) -> bool:
    """s278 dúo r2 (Sol#2): validación POSITIVA y conservadora de oración completa.

    (a) el span termina en puntuación TERMINAL ``.``/``!``/``?`` — ``;`` separa
        cláusulas, no oraciones, y el final-de-línea sin puntuación no termina
        nada;
    (b) el último carácter no-blanco ANTES del span (si existe) debe ser él
        mismo terminal — rechaza cortes a mitad de palabra y continuaciones de
        línea con hard-wrap (la línea previa quedó sin terminar).

    Heurística deliberadamente conservadora y documentada: una oración partida
    por hard-wrap NO se sirve en v1.  Si no valida, la card NO se sirve
    (fail-closed) — el campo ``sentence_complete_validated`` jamás se rebaja.
    """
    if content[end - 1] not in ".!?":
        return False
    preceding = content[:start].rstrip()
    return not preceding or preceding[-1] in ".!?"


def _span_is_prose(
    content_lines: list[tuple[int, int, str]], start: int, end: int
) -> bool:
    """s278 dúo r2 (Fable#2): verificación POSITIVA de prosa-idad del span.

    Rechaza cualquier span cuyas líneas contenedoras sean filas pipe de tabla
    (datos, encabezados o separadores — ``_markdown_pipe_row_kind`` distinto de
    ``None``).  Sin esto, la clase de prosa servía filas pipe TRUNCADAS cuando
    la clase de fila fallaba (probe reproducido: span sobre dos data-rows).
    Import function-local para no acoplar el módulo en import-time.
    """
    from .post_rerank_coverage import _markdown_pipe_row_kind

    return all(
        _markdown_pipe_row_kind(line) is None
        for line_start, line_end, line in content_lines
        if start < line_end and line_start < end
    )


def build_prose_source_cards(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """s278 §4: derive AT MOST ONE complete-sentence prose card, fully attested.

    The card is an exact ``[start, end)`` span of the ACTIVE chunk, attested by
    document_id + extraction_sha256 + source_file + chunk id + content-hash of
    the whole chunk + quote-hash of the span.  The span is derived ONLY from
    the selector's already-validated query-aligned ``coverage_cards`` (never an
    eval-identifier lookup): each selector span is snapped OUTWARD to the
    complete sentence(s) it intersects and overlapping snaps are merged.
    Candidate spans are then tried in this order (s278 dúo r2, Sol#3): first
    the group(s) containing the DECISIVE alignment card of the selector
    (``facet == "query_alignment"``, the card that drove the selection), ties
    and the remainder by position.  A span is served verbatim only if it is
    bounded (<= ``MAX_PROSE_SOURCE_CARD_CHARS``), positively PROSE (no
    pipe-table line, Fable#2) and a genuinely complete sentence span (Sol#2);
    otherwise it is omitted entirely — never clipped, never downgraded.  Any
    invalid input fails closed to ``[]``.
    """
    content = candidate.get("content")
    candidate_id = str(candidate.get("id") or "")
    document_id = str(candidate.get("document_id") or "")
    extraction_sha256 = str(candidate.get("extraction_sha256") or "").casefold()
    # s278 dúo r2 (Fable#5): sin .strip() — el contrato del helper canónico es
    # matching simétrico SIN normalizaciones extra; la identidad la ligan
    # document_id + extraction_sha256 + revision_lineage_id.
    source_file = str(candidate.get("source_file") or "")
    authority_source_file = str(
        candidate.get("document_local_authority_source_file") or ""
    )
    lineage_id = str(candidate.get("document_revision_lineage_id") or "")
    if (
        not isinstance(content, str)
        or not content
        or not candidate_id
        or not document_id
        or not _valid_sha256(extraction_sha256)
        or not source_file
        or candidate.get("duplicate_of") is not None
        or candidate.get("document_status") != "active"
        or document_id
        != str(candidate.get("document_local_authority_document_id") or "")
        or extraction_sha256
        != str(
            candidate.get("document_local_authority_extraction_sha256") or ""
        ).casefold()
        or not lineage_id
        or lineage_id
        != str(
            candidate.get("document_local_authority_revision_lineage_id") or ""
        )
        or not blob_identity_match(authority_source_file, source_file)
    ):
        return []
    cards = candidate.get("coverage_cards")
    if not isinstance(cards, list) or not cards:
        return []
    sentences = sentence_spans(content)
    content_lines = line_spans(content)
    snapped: list[list[int]] = []
    decisive_spans: list[tuple[int, int]] = []
    for card in cards:
        if (
            not isinstance(card, dict)
            or card.get("exact_source_span_validated") is not True
        ):
            return []
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
            return []
        if str(card.get("facet") or "") == "query_alignment":
            decisive_spans.append((start, end))
        touched = [
            (sentence_start, sentence_end)
            for sentence_start, sentence_end in sentences
            if start < sentence_end and sentence_start < end
        ]
        if not touched:
            continue
        snapped.append(
            [
                min(sentence_start for sentence_start, _ in touched),
                max(sentence_end for _, sentence_end in touched),
            ]
        )
    merged: list[list[int]] = []
    for span_start, span_end in sorted(map(tuple, snapped)):
        if merged and span_start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], span_end)
        else:
            merged.append([span_start, span_end])

    def _contains_decisive(span_start: int, span_end: int) -> bool:
        return any(
            span_start < decisive_end and decisive_start < span_end
            for decisive_start, decisive_end in decisive_spans
        )

    # s278 dúo r2 (Sol#3): la card decisiva de ALINEACIÓN manda; empate y
    # resto por posición.  Sin card decisiva identificable => orden posicional.
    ordered = sorted(
        (tuple(span) for span in merged),
        key=lambda span: (0 if _contains_decisive(*span) else 1, span[0]),
    )
    for span_start, span_end in ordered:
        if span_end - span_start > MAX_PROSE_SOURCE_CARD_CHARS:
            continue
        if not _span_is_prose(content_lines, span_start, span_end):
            continue
        if not _is_complete_sentence_span(content, span_start, span_end):
            continue
        quote = content[span_start:span_end]
        return [
            {
                "candidate_id": candidate_id,
                "card_class": PROSE_SOURCE_CARD_CLASS,
                "record_kind": PROSE_SOURCE_CARD_KIND,
                "document_id": document_id,
                "extraction_sha256": extraction_sha256,
                "source_file": source_file,
                "content_sha256": _sha256_text(content),
                "start": span_start,
                "end": span_end,
                "quote": quote,
                "quote_sha256": _sha256_text(quote),
                "sentence_complete_validated": True,
                "local_semantic_validated": True,
                "exact_source_span_validated": True,
            }
        ]
    return []


def has_exact_prose_source_card_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate every prose-card attestation field against the parent chunk.

    Field-level checks make each attested value load-bearing (bounds, verbatim
    quote, content/quote hashes, chunk and document identity, canonical blob
    identity via :func:`blob_identity_match`); the deterministic re-derivation
    equality is the backstop — any tampered card, tampered selector span or
    tampered parent content fails closed.
    """
    cards = chunk.get("prose_source_cards")
    content = chunk.get("content")
    if (
        not isinstance(cards, list)
        or len(cards) != 1
        or not isinstance(cards[0], dict)
        or not isinstance(content, str)
        or not content
    ):
        return False
    card = cards[0]
    start, end, quote = card.get("start"), card.get("end"), card.get("quote")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or not isinstance(quote, str)
        or not 0 <= start < end <= len(content)
        or content[start:end] != quote
        or card.get("card_class") != PROSE_SOURCE_CARD_CLASS
        or card.get("record_kind") != PROSE_SOURCE_CARD_KIND
        or card.get("content_sha256") != _sha256_text(content)
        or card.get("quote_sha256") != _sha256_text(quote)
        or card.get("sentence_complete_validated") is not True
        or card.get("exact_source_span_validated") is not True
        or str(card.get("candidate_id") or "") != str(chunk.get("id") or "")
        or str(card.get("document_id") or "")
        != str(chunk.get("document_id") or "")
        or str(card.get("extraction_sha256") or "").casefold()
        != str(chunk.get("extraction_sha256") or "").casefold()
        or not blob_identity_match(
            str(card.get("source_file") or ""),
            str(chunk.get("source_file") or ""),
        )
    ):
        return False
    try:
        expected = build_prose_source_cards(chunk)
    except (KeyError, TypeError, ValueError):
        return False
    return cards == expected


def _blob_identity_drift_pairs(
    authorities: list[dict[str, str]],
    identity_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """s278 dúo r2 (Fable#3): pares blob canónico-pero-NO-estricto por documento.

    Con autoridad presente y CERO candidatos, un par documents-blob vs
    chunks-blob que empareja canónicamente pero no estrictamente ES la
    explicación estructural (el join de chunks del RPC v2 es estricto en SQL)
    y debe quedar VISIBLE, no misatribuido a not_applicable/no_fts_candidates.
    Los identificadores chunk-side disponibles son los anchors y el contexto
    ya servido del mismo document_id.
    """
    pairs: list[dict[str, str]] = []
    for authority in authorities:
        document_id = str(authority.get("document_id") or "")
        document_blob = str(authority.get("source_file") or "")
        if not document_id or not document_blob:
            continue
        for row in identity_rows:
            if str(row.get("document_id") or "") != document_id:
                continue
            chunk_blob = str(row.get("source_file") or "")
            if (
                chunk_blob
                and chunk_blob != document_blob
                and blob_identity_match(document_blob, chunk_blob)
            ):
                pair = {
                    "document_id": document_id,
                    "documents_blob": document_blob,
                    "chunks_blob": chunk_blob,
                }
                if pair not in pairs:
                    pairs.append(pair)
    return pairs


def _prose_source_card_fetch_receipt(
    read_trace: dict[str, Any],
    *,
    authorities: list[dict[str, str]] | tuple = (),
    identity_rows: list[dict[str, Any]] | tuple = (),
) -> dict[str, Any]:
    """s278 §4 fail-closed VISIBLE: when the snapshot RPC rejects the document
    (lineage/doc_type NULL — the known live class until the adjudicated
    data-fix), no card is served and the receipt declares the exact RPC reason
    (e.g. ``blocked_unverified_document_lineage``), never a silent drop.

    s278 dúo r2 (Fable#3): with an AUTHORITY present and zero candidates, a
    canonical-but-not-strict blob pair among the available identifiers is
    declared as ``blocked_blob_identity_drift_requires_rpc_v3`` (the strict SQL
    chunk join of the v2 RPC is the structural cause; the canonical SQL lives
    in ``supabase/migration_proposals/`` pending sign-off) instead of being
    misattributed to ``not_applicable``.
    """
    drift = _blob_identity_drift_pairs(list(authorities), list(identity_rows))
    if drift:
        return {
            "status": "blocked_blob_identity_drift_requires_rpc_v3",
            "blob_identity_drift": drift,
            "cards": 0,
        }
    reasons = sorted(
        {
            str(reason)
            for reason in (read_trace.get("authority_rejections") or [])
            if str(reason)
        }
    )
    if reasons:
        status = (
            f"blocked_{reasons[0]}"
            if len(reasons) == 1
            else "blocked_multiple_snapshot_rejections"
        )
        return {"status": status, "snapshot_rejections": reasons, "cards": 0}
    return {"status": "not_applicable", "cards": 0}


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
    if not _matches_authority(winner, authorities):
        trace["status"] = "winner_scope_mismatch"
        return [], trace
    covered_ids = {str(row.get("id") or "") for row in covered_context}
    if winner_id in covered_ids:
        trace.update(
            status="best_candidate_already_covered",
            satisfied_ids=[winner_id],
            satisfaction_route="already_served",
        )
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
    if _prose_source_card_enabled():
        # s278 §4: clase COMPLEMENTARIA de card de prosa sobre el MISMO ganador
        # (mismos gates de elegibilidad/dedup/cap que la fila); byte-inerte off.
        # dúo r2 (Fable#4): la card se construye SOLO en el path complementario
        # — si la clase de fila markdown es derivable del ganador, adjuntar
        # prosa daría un framing/receipt engañoso con bytes servidos idénticos.
        from .post_rerank_coverage import _document_local_markdown_record_cards

        if _document_local_markdown_record_cards(selected):
            trace["prose_source_card"] = {
                "status": "not_applicable_markdown_pipe_row_class",
                "cards": 0,
            }
        else:
            prose_cards = build_prose_source_cards(selected)
            if prose_cards:
                selected["prose_source_cards"] = prose_cards
                trace["prose_source_card"] = {
                    "status": "selected",
                    "cards": len(prose_cards),
                    "record_kind": PROSE_SOURCE_CARD_KIND,
                    "spans": [
                        [card["start"], card["end"]] for card in prose_cards
                    ],
                    "quote_sha256": [
                        card["quote_sha256"] for card in prose_cards
                    ],
                }
            else:
                trace["prose_source_card"] = {
                    "status": "no_complete_sentence_span",
                    "cards": 0,
                }
    trace.update(
        status="selected",
        selected_ids=[winner_id],
        satisfied_ids=[winner_id],
        satisfaction_route="coverage_append",
    )
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
        if _prose_source_card_enabled():
            # s278 §4: bloqueo del RPC visible en el receipt, nunca silencioso;
            # dúo r2 (Fable#3): el drift de blob con autoridad presente y cero
            # candidatos también, con su par exacto.
            trace = dict(read_trace)
            trace["prose_source_card"] = _prose_source_card_fetch_receipt(
                read_trace,
                authorities=authorities,
                identity_rows=[*anchor_rows, *covered_context],
            )
            return [], trace
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
            "satisfied_ids": selection_trace.get("satisfied_ids", []),
            "satisfaction_route": selection_trace.get("satisfaction_route"),
            "catalog_scope_applied": selection_trace.get("catalog_scope_applied"),
            "model_calls": 0,
            "database_writes": 0,
        }
    )
    if "prose_source_card" in selection_trace:
        trace["prose_source_card"] = selection_trace["prose_source_card"]
    return selected[:APPEND_LIMIT], trace
