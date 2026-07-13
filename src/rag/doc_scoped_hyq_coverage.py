"""Bounded, document-scoped HYQ navigation returning only real source chunks.

Hypothetical questions are navigation hints, never evidence.  The canonical
catalog limits the documents that may be searched, BM25 selects a small,
source-diverse set of parent IDs, and the returned rows are hydrated from
``chunks_v2``.  No model endpoint or database write is used.
"""
from __future__ import annotations

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
    needs: list[str], rows: list[dict[str, Any]]
) -> list[str]:
    """Select a bounded parent set without letting one manual monopolise it."""
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


def fetch_document_scoped_rows(
    scope: list[str],
    needs: list[str],
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
) -> tuple[list[dict[str, Any]], int]:
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

        parent_ids = select_document_diverse_parents(needs, rows)
        if not parent_ids:
            return [], len(rows)
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
        return [by_id[parent_id] for parent_id in parent_ids], len(rows)


def collect_document_scoped_hyq(
    query: str,
    *,
    fetcher=fetch_document_scoped_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return exact-source candidates; never expose generated HYQ prose."""
    resolution = resolve_query(query)
    scope = sorted(resolution.get("allowed_sources") or [])
    plan = expand_query_facets(query)
    trace = {
        "lane": LANE,
        "scope_rows": len(scope),
        "selected_parent_ids": [],
        "served_hyq_prose": False,
    }
    if not scope or len(scope) > SCOPE_LIMIT or not plan.get("archetype"):
        trace["status"] = "not_applicable"
        return [], trace

    parents, hyq_row_count = fetcher(scope, plan["needs"])
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
            config_path=STRICT_ALIGNED_CONFIG,
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
    while remaining and len(selected) < APPEND_LIMIT:
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
            "selected_parent_ids": [str(row["id"]) for row in selected],
        }
    )
    return selected, trace
