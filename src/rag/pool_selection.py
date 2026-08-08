"""Motor de selección compartido sobre el pool ya recuperado.

Nace del split L2c/s313 del doble-inquilino (blueprint §4-L2c): aquí viven las
constantes y funciones deterministas compartidas (folding, tokens, BM25
in-pool, ventanas exactas, scope canónico); las lanes que lo consumen viven en
``obligation_warning`` (viva) y ``rerank_pool_coverage`` (vetada).
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

from .evidence_window import _candidate_windows
from .query_facets import ROOT as QUERY_ROOT

POOL_LIMIT = 64
WINDOW_CHARS = 360
MIN_ALIGNMENT_TERMS = 6
QUERY_CONFIG = QUERY_ROOT / "config/retrieval_facets_v4.yaml"

_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o",
    "en", "por", "para", "como", "con", "que", "se", "al", "es", "su",
    "the", "and", "for", "of", "to", "a", "cual", "cuales", "cuanto",
    "cuantos", "central", "panel", "sistema", "hacer", "realizar",
    "comprobar", "pregunta",
}


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()


def _tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", _fold(text))
        if len(token) >= 3 and token not in _STOP
    ]


def _identity_key(text: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", _fold(text)))


def _search_text(row: dict[str, Any]) -> str:
    title = str(row.get("section_title") or "")
    # BM25F-like field weighting without a second index: repeat the short,
    # curated heading and keep the complete source body available.
    return " ".join((title, title, title, row.get("context") or "", row.get("content") or ""))


def _bm25_scores(query: str, rows: list[dict[str, Any]]) -> list[float]:
    query_terms = list(dict.fromkeys(_tokens(query)))
    documents = [_tokens(_search_text(row)) for row in rows]
    if not query_terms or not documents:
        return [0.0] * len(rows)
    document_frequency: Counter[str] = Counter()
    for terms in documents:
        document_frequency.update(set(terms))
    average_length = sum(map(len, documents)) / len(documents) or 1.0
    scores = []
    for terms in documents:
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
        scores.append(score)
    return scores


def _exact_windows(content: str) -> list[tuple[int, int, str]]:
    """Return paragraph and overlapping fixed windows copied from the source.

    Technical UI/table extractions often put each label in a separate Markdown
    block.  Paragraph-only windows therefore miss relationships such as an
    output action and its selected circuit even though both are adjacent in the
    same chunk.  Fixed windows bridge those extraction boundaries without
    generating or rewriting evidence.
    """
    windows = list(_candidate_windows(content, WINDOW_CHARS))
    stride = WINDOW_CHARS // 2
    for start in range(0, len(content), stride):
        end = min(len(content), start + WINDOW_CHARS)
        if end > start:
            windows.append((start, end, content[start:end]))
        if end == len(content):
            break
    deduped = []
    seen = set()
    for start, end, quote in windows:
        key = (start, end)
        if key not in seen and quote:
            seen.add(key)
            deduped.append((start, end, quote))
    return deduped


def _query_card(queries: list[str], row: dict[str, Any]) -> dict[str, Any] | None:
    alignment_terms = set(_tokens(" ".join(queries)))
    if not alignment_terms:
        return None
    best: tuple[tuple[int, float, int], tuple[int, int, str], list[str]] | None = None
    content = row.get("content") or ""
    for start, end, quote in _exact_windows(content):
        quote_terms = set(_tokens(quote))
        hits = sorted(alignment_terms & quote_terms)
        if len(hits) < MIN_ALIGNMENT_TERMS:
            continue
        density = len(hits) / max(1, len(quote_terms))
        key = (len(hits), density, -start)
        if best is None or key > best[0]:
            best = (key, (start, end, quote), hits)
    if best is None:
        return None
    start, end, quote = best[1]
    return {
        "candidate_id": row.get("id"),
        "candidate_rank": 1,
        "start": start,
        "end": end,
        "quote": quote,
        "facet": "query_alignment",
        "alignment_term_hits": best[2],
        "exact_source_span_validated": True,
    }


def _incremental_needs(query: str, expanded: list[str]) -> list[str]:
    query_terms = set(_tokens(query))
    incremental = []
    for need in expanded:
        terms = [term for term in _tokens(need) if term not in query_terms]
        value = " ".join(dict.fromkeys(terms))
        if value:
            incremental.append(value)
    return incremental or [query]


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _in_canonical_scope(row: dict[str, Any], resolution: dict[str, Any]) -> bool:
    """Accept catalogued documents or exact metadata-model equivalents.

    The catalog is authoritative when complete.  A document can nevertheless
    still be awaiting catalog adjudication while its chunk metadata already has
    the exact resolved model.  The latter is a bounded fail-open for an existing
    retrieved row, not a cross-family expansion.
    """
    allowed_sources = set(resolution.get("allowed_sources") or [])
    allowed_models = {
        _identity_key(model) for model in resolution.get("add_models") or []
        if _identity_key(model)
    }
    if not allowed_sources and not allowed_models:
        return True
    source_file = str(row.get("source_file") or "")
    model = _identity_key(str(row.get("product_model") or ""))
    return source_file in allowed_sources or bool(model and model in allowed_models)
