"""Bounded, document-scoped HYQ navigation returning only real source chunks.

Hypothetical questions are navigation hints, never evidence.  The canonical
catalog limits the documents that may be searched, BM25 selects a small,
source-diverse set of parent IDs, and the returned rows are hydrated from
``chunks_v2``.  No model endpoint or database write is used.
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
from typing import Any

import httpx

from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from .catalog_resolver import resolve_query
from .evidence_coverage import STRICT_ALIGNED_CONFIG, select_evidence_coverage_cards
from .query_facets import expand_query_facets

LANE = "canonical_document_hyq_coverage_v1"
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
    "source_file,page_number,document_id,extraction_sha256,chunk_index"
)


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


def fetch_document_scoped_rows(
    scope: list[str],
    needs: list[str],
    *,
    source_groups: list[dict[str, Any]] | None = None,
    focus_query: str = "",
    client: httpx.Client | None = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    include_receipts: bool = False,
) -> tuple[list[dict[str, Any]], int, int] | tuple[
    list[dict[str, Any]], int, int, dict[str, str]
]:
    """GET-only bounded navigation followed by real-parent hydration."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for HYQ coverage read")
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
        httpx.Client(timeout=timeout_seconds) if client is None else nullcontext(client)
    )
    with context as request_client:
        rows: list[dict[str, Any]] = []
        for offset in range(0, ROW_LIMIT, PAGE_SIZE):
            page = get_rows(
                request_client,
                "chunks_v2_hyq",
                {
                    "select": "chunk_id,question,source_file,page_number",
                    "source_file": _postgrest_in(scope),
                    "order": "source_file.asc,page_number.asc,chunk_id.asc,question.asc",
                    "limit": str(PAGE_SIZE),
                    "offset": str(offset),
                },
            )
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                break
        else:
            # Exactly-at-cap is rejected too: without another request we cannot
            # distinguish it from truncation, and fail-closed is safer.
            raise RuntimeError("HYQ scope reached row cap")

        parent_ids = select_document_diverse_parents(
            needs,
            rows,
            source_groups=source_groups,
            focus_query=focus_query,
        )
        if not parent_ids:
            result = ([], len(rows), requests)
            if include_receipts:
                return (*result, {
                    "hyq_rows_sha256": _canonical_sha256(rows),
                    "selected_parent_ids_sha256": _canonical_sha256([]),
                    "hydrated_parents_sha256": _canonical_sha256([]),
                })
            return result
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
        ordered_parents = [by_id[parent_id] for parent_id in parent_ids]
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
                "hyq_rows_sha256": _canonical_sha256(rows),
                "selected_parent_ids_sha256": _canonical_sha256(parent_ids),
                "hydrated_parents_sha256": _canonical_sha256(parent_manifest),
            })
        return result


def collect_document_scoped_hyq(
    query: str,
    *,
    fetcher=fetch_document_scoped_rows,
    query_facets_path=None,
    evidence_config_path=STRICT_ALIGNED_CONFIG,
    append_limit: int = APPEND_LIMIT,
    entity_stratified: bool = False,
    include_fetch_receipts: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return exact-source candidates; never expose generated HYQ prose."""
    if not isinstance(append_limit, int) or isinstance(append_limit, bool) or not 1 <= append_limit <= 3:
        raise ValueError("HYQ append limit must be 1..3")
    if not isinstance(entity_stratified, bool):
        raise ValueError("HYQ entity_stratified must be boolean")
    resolution = resolve_query(query)
    scope = sorted(resolution.get("allowed_sources") or [])
    source_groups = resolution.get("source_groups") or []
    active_source_groups = source_groups if entity_stratified else []
    plan = (
        expand_query_facets(query, query_facets_path)
        if query_facets_path is not None
        else expand_query_facets(query)
    )
    trace = {
        "lane": LANE,
        "scope_rows": len(scope),
        "source_groups": len(source_groups),
        "entity_stratified": entity_stratified,
        "selected_parent_ids": [],
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
    fetch_receipts: dict[str, str] = {}
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
    eligible = []
    for parent in parents:
        # Reassert canonical document scope after parent hydration.  The HYQ
        # row is navigation metadata and cannot authorize a cross-scope parent.
        if str(parent.get("source_file") or "") not in scope:
            continue
        cards = select_evidence_coverage_cards(
            [parent],
            archetype=plan["archetype"],
            query=query,
            config_path=evidence_config_path,
        )
        if not cards:
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
            "fetch_receipts": fetch_receipts,
        }
    )
    return selected, trace
