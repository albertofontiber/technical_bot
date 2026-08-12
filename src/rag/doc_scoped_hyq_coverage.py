"""Bounded, document-scoped HYQ navigation returning only real source chunks.

Hypothetical questions are navigation hints, never evidence.  The canonical
catalog limits the DOCUMENTS that may be searched, BM25 selects a small,
source-diverse set of parent IDs, and the returned rows are hydrated from
``chunks_v2``.  No model endpoint or database write is used.

s288 F2 (lane hardening) — three normative properties, all declared:

* **Scope is ``document_id``, never a file name.**  The scope comes from the
  resolver's ``resolved_documents`` and is enforced through the authoritative
  ``chunks_v2_hyq.chunk_id -> chunks_v2.id`` relation (PostgREST embed), so two
  documents sharing a ``source_file`` can no longer bleed into each other.
* **The denormalised hyq copies are demoted.**  ``source_file``/``page_number``
  are read from the EMBEDDED parent; the lane no longer selects the hyq columns
  at all, so a stale copy cannot influence ranking, diversity or grouping.
* **Authority tier = BLOB-VERIFIED**: a parent may serve only if its document is
  ``active``, carries a real 64-hex ``source_pdf_sha256`` (not a ``backfill:``
  placeholder) and the chunk's ``extraction_sha256`` binds to it.  Lineage and
  language are deliberately NOT required here — the lineage-adjudicated tier
  belongs to ``document_local``; naming the tier is how this lane avoids
  over-claiming canonical authority.

s288b (lever de ontología) — el PAR de configs de la lane pasa a ser el que ya
sirve la lane hermana ``rerank_pool_coverage``: match = ``retrieval_facets_v4``
(ontología bilingüe con ``stem_prefixes``), cards = ``evidence_coverage_facets_v5``.
Las configs quedan byte-intactas; lo único que cambia es a cuál apunta la lane, y
la **barrera espejo** de alineación query↔card que ese par exige (ver
``MIN_QUERY_ALIGNED_CARD_TERMS``).  Todo descarte de parent queda TRAZADO en
``parents_rejected`` — un parent que no produce card ya no desaparece en silencio.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
from collections import Counter, defaultdict
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import httpx

from ..http_pool import abierto

from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from .catalog_resolver import resolve_query
from .evidence_coverage import POOL_COMPLEMENT_CONFIG, select_evidence_coverage_cards
from .query_facets import ROOT as QUERY_ROOT, expand_query_facets

LANE = "canonical_document_hyq_coverage_v1"
# Mismo match-config que la lane hermana del pool (rerank_pool_coverage.py:38).
QUERY_FACETS_CONFIG = QUERY_ROOT / "config/retrieval_facets_v4.yaml"
SCOPE_LIMIT = 32
ROW_LIMIT = 4000
PAGE_SIZE = 1000
SOURCE_LIMIT = 2
PARENTS_PER_SOURCE_NEED = 2
PARENT_LIMIT = 6
APPEND_LIMIT = 2
MAX_HTTP_REQUESTS = 6
TIMEOUT_SECONDS = 5.0
_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o",
    "en", "por", "para", "como", "con", "que", "se", "al", "es",
    "su", "the", "and", "for", "of", "to", "a",
}
_PARENT_SELECT = (
    "id,content,context,product_model,category,section_title,content_type,"
    "manufacturer,protocol,doc_type,language,has_diagram,diagram_url,"
    "source_file,page_number,document_id,extraction_sha256,chunk_index,"
    "duplicate_of"
)
# Navigation reads the hyq row plus its authoritative parent (FK chunk_id ->
# chunks_v2.id, migration 013:21).  The denormalised hyq ``source_file`` /
# ``page_number`` columns are deliberately NOT selected.
_HYQ_SELECT = (
    "chunk_id,question,"
    "chunks_v2!inner(document_id,duplicate_of,source_file,page_number)"
)
# Deterministic pagination needs a TOTAL order over top-level columns of the
# navigated table; embedded-resource columns are not a supported ordering key
# for a paged read.  ``UNIQUE (chunk_id, question)`` (migration 013:38) makes
# this exact pair a total order over ``chunks_v2_hyq``, so pages cannot repeat
# or skip a row between requests.
_HYQ_ORDER = "chunk_id.asc,question.asc"
_DOCUMENT_SELECT = "id,status,source_pdf_sha256"
_ACTIVE_STATUS = "active"
_REAL_SHA256 = re.compile(r"[0-9a-f]{64}")

# Traced rejection reasons.  ``scope`` says what ``id`` refers to: a whole
# document dropped before navigation, or an individual hydrated parent.
REJECTED_DOCUMENTS_READ_FAILED = "documents_read_failed"
REJECTED_DOCUMENT_MISSING = "document_row_missing"
REJECTED_DOCUMENT_NOT_ACTIVE = "document_not_active"
REJECTED_DOCUMENT_SHA_PLACEHOLDER = "document_sha_placeholder"
REJECTED_PARENT_OUT_OF_SCOPE = "parent_document_out_of_scope"
REJECTED_PARENT_SHA_MISMATCH = "parent_extraction_sha_mismatch"
REJECTED_PARENT_DUPLICATE = "parent_marked_duplicate"
# s288b: los dos descartes de la capa de cards.  El primero EXISTÍA como
# ``continue`` mudo — un parent sin card se contaba como "no había material",
# indistinguible de un hueco de corpus (feedback_corpus_gap).  Ahora se traza.
REJECTED_PARENT_NO_MATCHING_CARD = "no_matching_card"
REJECTED_PARENT_NO_QUERY_ALIGNED_CARD = "no_query_aligned_card"

# s288b (r2-i) — BARRERA ESPEJO de la alineación query↔card.
# ``evidence_coverage_facets_v5`` declara ``query_alignment_min_terms: 0`` para
# TODOS sus arquetipos (config/evidence_coverage_facets_v5.yaml:6-15).  En la lane
# hermana eso es seguro porque ``rerank_pool_coverage`` impone su PROPIA barrera
# antes de servir: ``_query_card`` (pool_selection.py — graduada en L2c/s313) exige una
# ventana con al menos ``MIN_ALIGNMENT_TERMS = 6`` términos alineados
# (pool_selection.py) y el candidato se descarta cuando devuelve ``None``
# (rerank_pool_coverage.py:341-342).  Sin barrera aquí, adoptar v5 relajaría la
# alineación TAMBIÉN para los arquetipos preexistentes de esta lane (v4 exigía
# 2 / 2 / 3 / 1 en connect_install_wire / fault_reset_recovery /
# program_delay_cause_effect / capacity_quantity).
# El NÚMERO de rerank_pool no es transferible, y por eso se cita aquí en vez de
# copiarse: allí se cuentan los aciertos de ``query ∪ needs`` (todo el vocabulario
# expandido de la faceta, ~40 términos) contra la ventana, mientras que
# ``query_term_hits`` cuenta SOLO los anclajes DISTINTIVOS de la pregunta
# (``_query_alignment_hits`` descarta genéricos y términos de la propia faceta),
# magnitud cuyo rango de esquema es 0..4 (evidence_coverage.py:94-101).  Lo que se
# espeja es la BARRERA: ningún parent sirve sin ≥1 card con alineación de query.
MIN_QUERY_ALIGNED_CARD_TERMS = 1


def _tokens(text: str) -> list[str]:
    value = unicodedata.normalize("NFKD", text or "")
    folded = "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()
    return [
        token for token in re.findall(r"[a-z0-9]+", folded)
        if len(token) >= 2 and token not in _STOP
    ]


def _rank_bm25(
    query: str, rows: list[dict[str, Any]]
) -> list[tuple[float, dict[str, Any]]]:
    if not rows:
        return []
    query_terms = _tokens(query)
    documents = [_tokens(row.get("question") or "") for row in rows]
    document_frequency: Counter[str] = Counter()
    for terms in documents:
        document_frequency.update(set(terms))
    average_length = sum(map(len, documents)) / len(documents) or 1.0
    ranked = []
    for row, terms in zip(rows, documents):
        frequencies = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = document_frequency[term]
            if not frequency:
                continue
            inverse = math.log(
                1 + (len(documents) - frequency + 0.5) / (frequency + 0.5)
            )
            term_frequency = frequencies[term]
            denominator = term_frequency + 1.5 * (
                0.25 + 0.75 * len(terms) / average_length
            )
            if denominator:
                score += inverse * (term_frequency * 2.5 / denominator)
        ranked.append((score, row))
    return sorted(
        ranked,
        key=lambda item: (
            -item[0],
            item[1].get("source_file") or "",
            item[1].get("page_number") or 0,
            item[1].get("chunk_id") or "",
            item[1].get("question") or "",
        ),
    )


def select_document_diverse_parents(
    needs: list[str],
    rows: list[dict[str, Any]],
    *,
    source_groups: list[dict[str, Any]] | None = None,
    focus_query: str = "",
) -> list[str]:
    """Select a bounded parent set without letting one manual monopolise it."""
    # Preserve the established single-entity lane exactly. Stratification is
    # only needed when a compound query resolves two or more governed entities.
    if source_groups and len(source_groups) >= 2:
        selected: list[str] = []
        for need in needs:
            query_terms = set(_tokens(focus_query))
            focus_terms = [token for token in _tokens(need) if token not in query_terms]
            focused_need = " ".join(focus_terms) or need
            ranked = _rank_bm25(focused_need, rows)
            for group in source_groups:
                group_sources = set(group.get("sources") or [])
                candidate = next(
                    (
                        str(row.get("chunk_id") or "")
                        for score, row in ranked
                        if score > 0
                        and str(row.get("source_file") or "") in group_sources
                        and str(row.get("chunk_id") or "") not in selected
                    ),
                    "",
                )
                if candidate:
                    selected.append(candidate)
                    if len(selected) == PARENT_LIMIT:
                        return selected
        if selected:
            return selected

    per_need = []
    source_need_best: dict[str, dict[int, float]] = defaultdict(dict)
    for need_index, need in enumerate(needs):
        grouped: dict[str, list[tuple[float, str]]] = defaultdict(list)
        seen: dict[str, set[str]] = defaultdict(set)
        for score, row in _rank_bm25(need, rows):
            source = str(row.get("source_file") or "")
            parent_id = str(row.get("chunk_id") or "")
            if score <= 0 or not source or not parent_id or parent_id in seen[source]:
                continue
            seen[source].add(parent_id)
            grouped[source].append((score, parent_id))
        for source, parents in grouped.items():
            source_need_best[source][need_index] = parents[0][0]
        per_need.append(grouped)

    source_scores = {
        source: sum(scores.values()) for source, scores in source_need_best.items()
    }
    selected_sources = sorted(
        source_scores, key=lambda source: (-source_scores[source], source)
    )[:SOURCE_LIMIT]
    selected: list[str] = []
    for local_rank in range(PARENTS_PER_SOURCE_NEED):
        for grouped in per_need:
            for source in selected_sources:
                candidates = grouped.get(source) or []
                if local_rank >= len(candidates):
                    continue
                parent_id = candidates[local_rank][1]
                if parent_id not in selected:
                    selected.append(parent_id)
                if len(selected) == PARENT_LIMIT:
                    return selected
    return selected


def _postgrest_in(values: list[str]) -> str:
    escaped = [
        '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        for value in values
    ]
    return "in.(" + ",".join(escaped) + ")"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _rejection(identifier: str, reason: str, scope: str) -> dict[str, str]:
    return {"id": identifier, "reason": reason, "scope": scope}


def _resolved_document_ids(resolution: dict[str, Any]) -> list[str]:
    """Read the document scope from the resolver contract, fail-closed.

    ``resolve_query`` owns ``resolved_documents`` ([{document_id, source_file}]);
    this lane consumes the ids only and never widens them.  Anything malformed
    yields an EMPTY scope, which the caller turns into ``not_applicable`` — the
    same fail-closed shape the old name-scope had when the catalog resolved
    nothing.
    """
    resolved = resolution.get("resolved_documents")
    if not isinstance(resolved, list):
        return []
    document_ids: set[str] = set()
    for document in resolved:
        if not isinstance(document, dict):
            continue
        document_id = str(document.get("document_id") or "").strip()
        if document_id:
            document_ids.add(document_id)
    return sorted(document_ids)


def _flatten_navigation_rows(
    page: list[dict[str, Any]], authorized: dict[str, str]
) -> list[dict[str, Any]]:
    """Project each hyq row onto its EMBEDDED parent's identity fields.

    ``source_file``/``page_number`` are taken from the parent, so BM25
    tie-breaks, per-source diversity and grouping downstream can only ever see
    parent-derived values.  The document-scope and duplicate filters are already
    applied server-side by the embed; repeating them here is a cheap belt that
    keeps a permissive or misconfigured deploy from widening the scope.
    """
    flattened: list[dict[str, Any]] = []
    for row in page:
        parent = row.get("chunks_v2")
        if isinstance(parent, list):
            parent = parent[0] if len(parent) == 1 else None
        if not isinstance(parent, dict) or parent.get("duplicate_of") is not None:
            continue
        chunk_id = str(row.get("chunk_id") or "")
        document_id = str(parent.get("document_id") or "")
        if not chunk_id or document_id not in authorized:
            continue
        flattened.append(
            {
                "chunk_id": chunk_id,
                "question": str(row.get("question") or ""),
                "document_id": document_id,
                "source_file": str(parent.get("source_file") or ""),
                "page_number": parent.get("page_number"),
            }
        )
    return flattened


def _authorized_documents(
    get_rows,
    request_client: httpx.Client,
    scope: list[str],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Resolve the blob-verified subset of the scope in ONE ``documents`` read.

    Servible document  <=>  ``status == 'active'``  AND  ``source_pdf_sha256``
    is a real 64-hex digest (a ``backfill:`` placeholder is not identity).  The
    per-chunk binding is checked later, against the sha returned here.

    Fail-closed: any read failure discards the WHOLE scope with a traced reason
    instead of raising, so the lane degrades to ``no_validated_source_span``
    rather than crashing serving.
    """
    try:
        rows = get_rows(
            request_client,
            "documents",
            {
                "select": _DOCUMENT_SELECT,
                "id": _postgrest_in(scope),
                "limit": str(len(scope)),
            },
        )
    except (httpx.HTTPError, TimeoutError, RuntimeError, ValueError):
        return {}, [
            _rejection(document_id, REJECTED_DOCUMENTS_READ_FAILED, "document")
            for document_id in scope
        ]
    authorized: dict[str, str] = {}
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        document_id = str(row.get("id") or "")
        if not document_id or document_id in seen:
            continue
        seen.add(document_id)
        if str(row.get("status") or "") != _ACTIVE_STATUS:
            rejected.append(
                _rejection(document_id, REJECTED_DOCUMENT_NOT_ACTIVE, "document")
            )
            continue
        sha256 = str(row.get("source_pdf_sha256") or "").strip().casefold()
        if _REAL_SHA256.fullmatch(sha256) is None:
            rejected.append(
                _rejection(
                    document_id, REJECTED_DOCUMENT_SHA_PLACEHOLDER, "document"
                )
            )
            continue
        authorized[document_id] = sha256
    rejected.extend(
        _rejection(document_id, REJECTED_DOCUMENT_MISSING, "document")
        for document_id in scope
        if document_id not in seen
    )
    return authorized, rejected


def _parent_rejection_reason(
    parent: dict[str, Any], authorized: dict[str, str]
) -> str:
    """Blob-verified predicate for one hydrated parent; "" means servible."""
    if parent.get("duplicate_of") is not None:
        return REJECTED_PARENT_DUPLICATE
    document_sha256 = authorized.get(str(parent.get("document_id") or ""))
    if not document_sha256:
        return REJECTED_PARENT_OUT_OF_SCOPE
    if str(parent.get("extraction_sha256") or "").strip().casefold() != document_sha256:
        return REJECTED_PARENT_SHA_MISMATCH
    return ""


def fetch_document_scoped_rows(
    document_ids: list[str],
    needs: list[str],
    *,
    source_groups: list[dict[str, Any]] | None = None,
    focus_query: str = "",
    client: httpx.Client | None = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    include_receipts: bool = False,
) -> tuple[list[dict[str, Any]], int, int] | tuple[
    list[dict[str, Any]], int, int, dict[str, Any]
]:
    """GET-only bounded navigation followed by authorised real-parent hydration.

    Request budget, declared with ZERO slack:
    ``1 documents + 4 navigation pages + 1 hydration == MAX_HTTP_REQUESTS``.
    The authority read runs FIRST, on purpose: the navigation scope is then only
    the servible documents, so no ``PARENT_LIMIT`` slot is ever spent on a
    parent that could not have served.  Any new read must be re-budgeted, not
    slipped in.

    Authority tier = blob-verified (active + real sha + chunk binding).  Lineage
    and language are NOT required by this lane; see the module docstring.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for HYQ coverage read")
    scope = sorted(
        {
            str(document_id).strip()
            for document_id in document_ids
            if str(document_id or "").strip()
        }
    )
    if not scope or len(scope) > SCOPE_LIMIT:
        raise RuntimeError("HYQ document scope is empty or over limit")
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    started = time.monotonic()
    requests = 0

    def get_rows(request_client: httpx.Client, table: str, params: dict) -> list[dict]:
        nonlocal requests
        requests += 1
        if requests > MAX_HTTP_REQUESTS:
            raise RuntimeError("HYQ coverage HTTP request cap exceeded")
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("HYQ coverage read deadline exceeded")
        response = request_client.get(
            f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}",
            headers=headers,
            params=params,
            timeout=remaining,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("HYQ coverage read returned non-list payload")
        return payload

    context = (
        abierto(timeout=timeout_seconds) if client is None else nullcontext(client)
    )
    with context as request_client:
        # Request 1/6 — authority.  Runs before navigation so the scope handed
        # to PostgREST already excludes every non-servible document.
        authorized, rejected = _authorized_documents(get_rows, request_client, scope)
        rows: list[dict[str, Any]] = []
        navigation_rows_skipped = 0
        parent_ids: list[str] = []
        ordered_parents: list[dict[str, Any]] = []
        if authorized:
            # Requests 2..5/6 — navigation, scoped by document_id through the
            # authoritative chunk_id -> chunks_v2 relation.
            navigation_scope = sorted(authorized)
            for offset in range(0, ROW_LIMIT, PAGE_SIZE):
                page = get_rows(
                    request_client,
                    "chunks_v2_hyq",
                    {
                        "select": _HYQ_SELECT,
                        "chunks_v2.document_id": _postgrest_in(navigation_scope),
                        "chunks_v2.duplicate_of": "is.null",
                        "order": _HYQ_ORDER,
                        "limit": str(PAGE_SIZE),
                        "offset": str(offset),
                    },
                )
                flattened = _flatten_navigation_rows(page, authorized)
                navigation_rows_skipped += len(page) - len(flattened)
                rows.extend(flattened)
                # Truncation is judged on the RAW page: a client-side skip must
                # never be mistaken for the last page.
                if len(page) < PAGE_SIZE:
                    break
            else:
                # Exactly-at-cap is rejected too: without another request we
                # cannot distinguish it from truncation, and fail-closed is
                # safer.
                raise RuntimeError("HYQ scope reached row cap")

            parent_ids = select_document_diverse_parents(
                needs,
                rows,
                source_groups=source_groups,
                focus_query=focus_query,
            )
        if parent_ids:
            # Request 6/6 — hydration of the real parents.
            hydrated = get_rows(
                request_client,
                "chunks_v2",
                {
                    "select": _PARENT_SELECT,
                    "id": _postgrest_in(parent_ids),
                    "limit": str(PARENT_LIMIT),
                },
            )
            by_id = {str(row.get("id") or ""): row for row in hydrated}
            if any(parent_id not in by_id for parent_id in parent_ids):
                raise RuntimeError("HYQ parent hydration incomplete")
            for parent_id in parent_ids:
                parent = by_id[parent_id]
                reason = _parent_rejection_reason(parent, authorized)
                if reason:
                    rejected.append(_rejection(parent_id, reason, "parent"))
                    continue
                ordered_parents.append(parent)
        result = (ordered_parents, len(rows), requests)
        if include_receipts:
            parent_manifest = [
                {
                    "id": str(row.get("id") or ""),
                    "source_file": str(row.get("source_file") or ""),
                    "document_id": str(row.get("document_id") or ""),
                    "extraction_sha256": str(row.get("extraction_sha256") or ""),
                    "chunk_index": row.get("chunk_index"),
                    "content_sha256": hashlib.sha256(
                        str(row.get("content") or "").encode("utf-8")
                    ).hexdigest(),
                }
                for row in ordered_parents
            ]
            return (*result, {
                # Fingerprints cover the rows the lane actually consumed (the
                # flattened, parent-derived projection), which is the artefact
                # that drives selection.
                "hyq_rows_sha256": _canonical_sha256(rows),
                "selected_parent_ids_sha256": _canonical_sha256(parent_ids),
                "hydrated_parents_sha256": _canonical_sha256(parent_manifest),
                "scope_document_ids": scope,
                "parents_rejected": rejected,
                "navigation_rows_skipped": navigation_rows_skipped,
            })
        return result


def collect_document_scoped_hyq(
    query: str,
    *,
    fetcher=fetch_document_scoped_rows,
    query_facets_path: Path = QUERY_FACETS_CONFIG,
    evidence_config_path: Path = POOL_COMPLEMENT_CONFIG,
    append_limit: int = APPEND_LIMIT,
    entity_stratified: bool = False,
    include_fetch_receipts: bool = False,
    require_query_aligned_card: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return exact-source candidates; never expose generated HYQ prose.

    ``require_query_aligned_card`` es fail-closed por default (barrera espejo,
    ver ``MIN_QUERY_ALIGNED_CARD_TERMS``).  Un consumidor solo puede apagarla si
    su PROPIO contrato sustituye a la alineación por query — hoy únicamente
    ``compatibility_bundle_coverage``, cuyo gate relacional (roster + protocolo +
    topología, ligados a dos entidades gobernadas) es estrictamente más fuerte y
    NO cambia de par de configs en este lever; mantenerlo intacto es lo que
    impide que este cambio se filtre a una lane que nadie revisó aquí.
    """
    if not isinstance(append_limit, int) or isinstance(append_limit, bool) or not 1 <= append_limit <= 3:
        raise ValueError("HYQ append limit must be 1..3")
    if not isinstance(entity_stratified, bool):
        raise ValueError("HYQ entity_stratified must be boolean")
    resolution = resolve_query(query)
    # s288 F2.1: the scope is the resolver's document IDENTITIES.  Scoping by
    # ``allowed_sources`` (file names) is dead — a name is not an identity.
    scope = _resolved_document_ids(resolution)
    source_groups = resolution.get("source_groups") or []
    active_source_groups = source_groups if entity_stratified else []
    # Los DOS punteros de configs son defaults de ESTA firma (el test de paridad
    # por lane los lee por introspección, no por una ruta copiada a mano).
    plan = expand_query_facets(query, query_facets_path)
    trace = {
        "lane": LANE,
        "scope_rows": len(scope),
        "scope_document_ids": scope,
        "source_groups": len(source_groups),
        "entity_stratified": entity_stratified,
        "selected_parent_ids": [],
        "parents_rejected": [],
        "served_hyq_prose": False,
    }
    if not scope or len(scope) > SCOPE_LIMIT or not plan.get("archetype"):
        trace["status"] = "not_applicable"
        return [], trace

    fetched = (
        fetcher(
            scope,
            plan["needs"],
            source_groups=active_source_groups,
            focus_query=query,
            include_receipts=include_fetch_receipts,
        )
        if fetcher is fetch_document_scoped_rows
        else fetcher(scope, plan["needs"])
    )
    fetch_receipts: dict[str, Any] = {}
    if len(fetched) == 4:
        parents, hyq_row_count, http_requests, fetch_receipts = fetched
        if not isinstance(fetch_receipts, dict):
            raise RuntimeError("invalid HYQ fetch receipts")
    elif len(fetched) == 3:
        parents, hyq_row_count, http_requests = fetched
    elif len(fetched) == 2:
        # Backwards-compatible test/custom fetchers predate request telemetry.
        parents, hyq_row_count = fetched
        http_requests = 0
    else:
        raise RuntimeError("invalid HYQ fetcher result")
    # Rejections reported by the fetcher (document authority + per-parent
    # binding) are carried through so the trace explains every drop; the
    # re-assert below adds the ones this function itself makes.
    parents_rejected: list[dict[str, str]] = [
        dict(entry)
        for entry in (fetch_receipts.get("parents_rejected") or [])
        if isinstance(entry, dict)
    ]
    scope_ids = set(scope)
    eligible = []
    for parent in parents:
        # Reassert canonical document scope after parent hydration.  The HYQ row
        # is navigation metadata and cannot authorize a cross-scope parent — and
        # the identity that authorizes is the hydrated chunk's ``document_id``,
        # never its ``source_file`` (two documents can carry the same name).
        parent_id = str(parent.get("id") or "")
        if str(parent.get("document_id") or "") not in scope_ids:
            parents_rejected.append(
                _rejection(parent_id, REJECTED_PARENT_OUT_OF_SCOPE, "parent")
            )
            continue
        if parent.get("duplicate_of") is not None:
            parents_rejected.append(
                _rejection(parent_id, REJECTED_PARENT_DUPLICATE, "parent")
            )
            continue
        cards = select_evidence_coverage_cards(
            [parent],
            archetype=plan["archetype"],
            query=query,
            config_path=evidence_config_path,
        )
        if not cards:
            parents_rejected.append(
                _rejection(parent_id, REJECTED_PARENT_NO_MATCHING_CARD, "parent")
            )
            continue
        if require_query_aligned_card and not any(
            len(card.get("query_term_hits") or []) >= MIN_QUERY_ALIGNED_CARD_TERMS
            for card in cards
        ):
            parents_rejected.append(
                _rejection(
                    parent_id, REJECTED_PARENT_NO_QUERY_ALIGNED_CARD, "parent"
                )
            )
            continue
        row = dict(parent)
        row.update(
            {
                "retrieval_lane": LANE,
                "hyq_navigation_validated": True,
                "local_semantic_validated": True,
                "coverage_cards": cards,
                "coverage_card_facets": [card["facet"] for card in cards],
            }
        )
        eligible.append(row)

    # Greedy set coverage is manufacturer-agnostic: prefer candidates that add
    # a facet not yet represented, then distinctive query anchors.  This stops
    # several near-duplicate "per unit" chunks from burying a complementary
    # system-total or variant span merely because it was navigated later.
    selected: list[dict[str, Any]] = []
    remaining = list(enumerate(eligible))
    covered_facets: set[str] = set()
    while remaining and len(selected) < append_limit:
        def coverage_key(item):
            original_rank, row = item
            cards = row.get("coverage_cards") or []
            facets = {str(card.get("facet") or "") for card in cards}
            query_hits = {
                str(hit)
                for card in cards
                for hit in (card.get("query_term_hits") or [])
            }
            return (
                len(facets - covered_facets),
                len(query_hits),
                len(facets),
                -original_rank,
            )

        best = max(remaining, key=coverage_key)
        remaining.remove(best)
        row = best[1]
        selected.append(row)
        covered_facets.update(row.get("coverage_card_facets") or [])
    trace.update(
        {
            "status": "selected" if selected else "no_validated_source_span",
            "hyq_rows": hyq_row_count,
            "http_requests": http_requests,
            "selected_parent_ids": [str(row["id"]) for row in selected],
            "parents_rejected": parents_rejected,
            "fetch_receipts": fetch_receipts,
        }
    )
    return selected, trace
