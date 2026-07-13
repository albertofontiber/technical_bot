"""Deterministic exact-span coverage cards for bounded retrieval candidates."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .evidence_window import _candidate_windows

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/evidence_coverage_facets_v1.yaml"
MULTIFACET_CONFIG = ROOT / "config/evidence_coverage_facets_v2.yaml"
ALIGNED_CONFIG = ROOT / "config/evidence_coverage_facets_v3.yaml"
STRICT_ALIGNED_CONFIG = ROOT / "config/evidence_coverage_facets_v4.yaml"
_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o", "en", "por",
    "para", "como", "con", "que", "se", "al", "es", "su", "the", "and", "for", "of",
    "to", "a",
}


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in value if not unicodedata.combining(char)).casefold()


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", _norm(text))
        if len(token) >= 2 and token not in _STOP
    ]


@lru_cache(maxsize=4)
def _load_config(path_string: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path_string).read_text(encoding="utf-8"))
    if payload.get("schema") not in {
        "evidence_coverage_facets_v1",
        "evidence_coverage_facets_v2",
        "evidence_coverage_facets_v3",
        "evidence_coverage_facets_v4",
    }:
        raise RuntimeError("unsupported evidence coverage schema")
    for key, low, high in (
        ("max_cards", 1, 4),
        ("window_chars", 100, 800),
        ("min_window_chars", 20, 200),
        ("min_distinct_terms", 1, 6),
    ):
        value = payload.get(key)
        if not isinstance(value, int) or not low <= value <= high:
            raise RuntimeError(f"invalid evidence coverage {key}")
    if payload["min_window_chars"] >= payload["window_chars"]:
        raise RuntimeError("minimum window must be smaller than the window bound")
    archetypes = payload.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise RuntimeError("evidence coverage config lacks archetypes")
    for archetype, facets in archetypes.items():
        if not isinstance(archetype, str) or not isinstance(facets, list) or not facets:
            raise RuntimeError("invalid evidence coverage archetype")
        seen = set()
        for facet in facets:
            facet_id = facet.get("id")
            terms = facet.get("terms")
            max_cards = facet.get("max_cards", 1)
            required_any = facet.get("required_any", [])
            if not isinstance(facet_id, str) or facet_id in seen:
                raise RuntimeError("coverage facet IDs must be unique")
            if (
                not isinstance(terms, list)
                or len(terms) < payload["min_distinct_terms"]
                or any(not isinstance(term, str) or not re.fullmatch(r"[a-z]+", term) for term in terms)
            ):
                raise RuntimeError("coverage facet terms must be normalized words")
            if any(re.search(r"\d", term) for term in terms):
                raise RuntimeError("coverage facets must not inject target values")
            if not isinstance(max_cards, int) or not 1 <= max_cards <= 2:
                raise RuntimeError("coverage facet max_cards must be 1..2")
            if (
                not isinstance(required_any, list)
                or any(term not in terms for term in required_any)
            ):
                raise RuntimeError("coverage facet required_any must be a subset of terms")
            seen.add(facet_id)
    alignment = payload.get("query_alignment_min_terms", {})
    if not isinstance(alignment, dict) or any(
        archetype not in archetypes
        or not isinstance(minimum, int)
        or not 0 <= minimum <= 4
        for archetype, minimum in alignment.items()
    ):
        raise RuntimeError("invalid query alignment policy")
    return payload


_QUERY_GENERIC = {
    "como", "cual", "cuanto", "cuantos", "cuanta", "cuantas", "central", "panel",
    "sistema", "manual", "hacer", "realizar", "configurar", "programar", "conectar",
    "cablear", "instalar", "montar", "soportar", "admitir", "comprobar", "pregunta",
    "solo",
}
_QUERY_GENERIC_PREFIXES = {
    "configur", "program", "conect", "cable", "instal", "mont", "soport", "admit",
    "comprob", "realiz",
}


def _query_alignment_hits(
    query: str,
    quote: str,
    *,
    facet_terms: set[str],
) -> list[str]:
    """Return distinctive query anchors also present in an exact source span."""
    query_tokens = list(dict.fromkeys(_tokens(query)))
    quote_tokens = set(_tokens(quote))
    anchors = []
    for token in query_tokens:
        if token in _QUERY_GENERIC or any(
            token.startswith(prefix) for prefix in _QUERY_GENERIC_PREFIXES
        ) or any(
            token.startswith(term) or term.startswith(token)
            for term in facet_terms
        ):
            continue
        if any(
            len(token) >= 4
            and len(source) >= 4
            and (token.startswith(source[:4]) or source.startswith(token[:4]))
            for source in quote_tokens
        ):
            anchors.append(token)
    return anchors


def _project_terms(tokens: list[str], terms: list[str]) -> list[str]:
    """Map inflected source tokens to versioned, >=4-char technical stems."""
    return [term for token in tokens for term in terms if token.startswith(term)]


def _bm25_scores(terms: list[str], windows: list[dict[str, Any]]) -> list[float]:
    docs = [_project_terms(_tokens(row["quote"]), terms) for row in windows]
    if not docs:
        return []
    document_frequency = Counter()
    for tokens in docs:
        document_frequency.update(set(tokens))
    average_length = sum(map(len, docs)) / len(docs) or 1.0
    scores = []
    for tokens in docs:
        frequencies = Counter(tokens)
        score = 0.0
        for term in terms:
            df = document_frequency[term]
            if not df:
                continue
            idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
            tf = frequencies[term]
            denominator = tf + 1.5 * (0.25 + 0.75 * len(tokens) / average_length)
            if denominator:
                score += idf * (tf * 2.5 / denominator)
        scores.append(score)
    return scores


def match_evidence_facets(
    text: str,
    *,
    archetype: str | None,
    config_path: Path = STRICT_ALIGNED_CONFIG,
) -> list[dict[str, Any]]:
    """Return facets structurally supported by one text span.

    This reusable primitive applies the same versioned vocabulary, minimum term
    count and ``required_any`` policy as coverage-card selection, without adding
    query alignment or ranking. It is useful when another independently scoped
    navigation lane must prove that its hint and exact source span express the
    same technical facet.
    """
    payload = _load_config(str(config_path.resolve()))
    facets = payload["archetypes"].get(archetype or "") or []
    tokens = _tokens(text or "")
    matches = []
    for facet in facets:
        terms = list(dict.fromkeys(facet["terms"]))
        hits = sorted(set(_project_terms(tokens, terms)))
        required_any = set(facet.get("required_any", []))
        if len(hits) < payload["min_distinct_terms"]:
            continue
        if required_any and not required_any.intersection(hits):
            continue
        matches.append({"facet": facet["id"], "term_hits": hits})
    return matches


def select_evidence_coverage_cards(
    candidates: list[dict[str, Any]],
    *,
    archetype: str | None,
    config_path: Path = DEFAULT_CONFIG,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Return bounded exact source windows for field-support facets.

    Candidate order breaks ties.  The vocabulary is archetype-level and cannot
    contain numbers or product codes, so no gold fact is smuggled into ranking.
    Facets that structurally require comparison may request two spans; the
    global card cap remains authoritative.
    """
    payload = _load_config(str(config_path.resolve()))
    facets = payload["archetypes"].get(archetype or "")
    if not candidates or not facets:
        return []
    min_query_terms = (payload.get("query_alignment_min_terms") or {}).get(
        archetype or "", 0
    )
    if min_query_terms and not query:
        return []
    all_facet_terms = {
        term for configured_facet in facets for term in configured_facet["terms"]
    }

    windows = []
    for candidate_rank, candidate in enumerate(candidates, start=1):
        content = candidate.get("content") or ""
        for start, end, quote in _candidate_windows(content, payload["window_chars"]):
            if len(quote.strip()) < payload["min_window_chars"]:
                continue
            windows.append(
                {
                    "candidate_id": candidate.get("id"),
                    "candidate_rank": candidate_rank,
                    "start": start,
                    "end": end,
                    "quote": quote,
                }
            )

    selected = []
    selected_spans = set()
    for facet in facets:
        terms = list(dict.fromkeys(facet["terms"]))
        required_any = set(facet.get("required_any", []))
        facet_limit = facet.get("max_cards", 1)
        facet_selected = 0
        scores = _bm25_scores(terms, windows)
        ranked = sorted(
            zip(scores, windows),
            key=lambda item: (
                -item[0],
                item[1]["candidate_rank"],
                item[1]["start"],
                item[1]["end"],
            ),
        )
        for score, window in ranked:
            key = (window["candidate_id"], window["start"], window["end"])
            hits = sorted(set(_project_terms(_tokens(window["quote"]), terms)))
            query_hits = _query_alignment_hits(
                query or "", window["quote"], facet_terms=all_facet_terms
            )
            if (
                score <= 0
                or len(hits) < payload["min_distinct_terms"]
                or (required_any and not required_any.intersection(hits))
                or len(query_hits) < min_query_terms
                or key in selected_spans
            ):
                continue
            selected.append(
                {
                    **window,
                    "facet": facet["id"],
                    "facet_term_hits": hits,
                    "query_term_hits": query_hits,
                    "score": round(score, 6),
                    "exact_source_span_validated": True,
                }
            )
            selected_spans.add(key)
            facet_selected += 1
            if facet_selected == facet_limit or len(selected) == payload["max_cards"]:
                break
        if len(selected) >= payload["max_cards"]:
            break
    return selected
