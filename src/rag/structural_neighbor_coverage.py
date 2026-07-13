"""Bounded same-blob context expansion after the main reranker.

This module is deliberately pure and unserved.  It selects source chunks near
rows that already survived reranking, but only within the same document and
the same immutable extraction hash.  Query-derived facets and fail-closed
structured claims rank candidates; generated prose, QIDs and expected values
are never inputs.
"""
from __future__ import annotations

import re
import math
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .evidence_coverage import (
    MULTIFACET_CONFIG,
    POOL_COMPLEMENT_CONFIG,
    STRICT_ALIGNED_CONFIG,
    match_evidence_facets,
    select_evidence_coverage_cards,
)
from .query_facets import expand_query_facets
from .structured_claims import extract_numeric_claims
from .toc_detection import is_toc_page

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/structural_neighbor_coverage_v1.yaml"
CASCADED_CONFIG = ROOT / "config/structural_cascade_coverage_v1.yaml"
QUERY_FACETS = ROOT / "config/retrieval_facets_v3.yaml"
CASCADED_QUERY_FACETS = ROOT / "config/retrieval_facets_v4.yaml"
CASCADED_EVIDENCE_CONFIG = (
    ROOT / "config/evidence_coverage_facets_cascade_v1.yaml"
)
LANE = "same_blob_structural_neighbor_coverage_v1"
VALIDATION = "same_document_same_blob_bounded_index_query_facets_v1"
CASCADED_LANE = "cascaded_structural_neighbor_coverage_v1"
CASCADED_VALIDATION = (
    "pool_seed_same_document_same_blob_bounded_index_query_facets_v1"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o", "en",
    "por", "para", "como", "con", "que", "se", "al", "es", "su", "the",
    "and", "for", "of", "to", "a",
}


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", _fold(text))
        if len(token) >= 2 and token not in _STOP
    ]


def _rank_bm25(
    query: str, rows: list[dict[str, Any]]
) -> list[tuple[float, dict[str, Any]]]:
    """Rank bounded source rows locally, without importing another RAG lane."""
    if not rows:
        return []
    query_terms = _tokens(query)
    documents = [
        _tokens((row.get("section_title") or "") + " " + (row.get("content") or ""))
        for row in rows
    ]
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
            inverse_frequency = math.log(
                1 + (len(rows) - frequency + 0.5) / (frequency + 0.5)
            )
            term_frequency = frequencies[term]
            denominator = term_frequency + 1.5 * (
                0.25 + 0.75 * len(terms) / average_length
            )
            if denominator:
                score += inverse_frequency * (term_frequency * 2.5 / denominator)
        ranked.append((score, row))
    return sorted(
        ranked,
        key=lambda item: (
            -item[0],
            item[1].get("page_number") or 0,
            item[1].get("id") or item[1].get("content") or "",
        ),
    )


@lru_cache(maxsize=4)
def _load(path_string: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path_string).read_text(encoding="utf-8"))
    if payload.get("schema") != "structural_neighbor_coverage_v1":
        raise RuntimeError("unsupported structural neighbor schema")
    for key, low, high in (
        ("max_seeds", 1, 20),
        ("max_gap", 1, 12),
        ("max_candidates", 16, 256),
        ("max_anchors", 1, 4),
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise RuntimeError(f"invalid structural neighbor {key}")
    if set(payload.get("allowed_languages") or []) != {"es", "en"}:
        raise RuntimeError("structural neighbor language contract must be ES/EN")
    if any(
        payload.get(key) is not True
        for key in (
            "require_same_document",
            "require_same_extraction_sha256",
            "require_positive_query_score",
            "require_evidence_facet",
        )
    ):
        raise RuntimeError("structural neighbor identity and relevance guards are mandatory")
    serving = payload.get("serving") or {}
    if serving.get("enabled") is not False or serving.get(
        "coverage_validated_field_allowed"
    ) is not False:
        raise RuntimeError("structural neighbor v1 must remain shadow-only")
    priorities = payload.get("numeric_priority_attributes") or {}
    if any(
        not isinstance(archetype, str)
        or not isinstance(attributes, list)
        or not attributes
        or any(not isinstance(item, str) or re.search(r"\d", item) for item in attributes)
        for archetype, attributes in priorities.items()
    ):
        raise RuntimeError("invalid structural neighbor numeric priorities")
    return payload


def _identity(row: dict[str, Any]) -> tuple[str, str] | None:
    document_id = str(row.get("document_id") or "")
    extraction_sha256 = str(row.get("extraction_sha256") or "").lower()
    if not document_id or not _SHA256.fullmatch(extraction_sha256):
        return None
    return document_id, extraction_sha256


def _index(row: dict[str, Any]) -> int | None:
    value = row.get("chunk_index")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _nearest_gap(
    candidate: dict[str, Any],
    seed_indexes: dict[tuple[str, str], list[int]],
) -> int | None:
    identity = _identity(candidate)
    index = _index(candidate)
    if identity is None or index is None or identity not in seed_indexes:
        return None
    gaps = [abs(index - seed_index) for seed_index in seed_indexes[identity]]
    return min(gaps) if gaps else None


def select_structural_neighbors(
    query: str,
    seeds: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    config_path: Path = DEFAULT_CONFIG,
    query_facets_path: Path = QUERY_FACETS,
    evidence_match_config_path: Path = STRICT_ALIGNED_CONFIG,
    evidence_card_config_path: Path = MULTIFACET_CONFIG,
    query_aligned_cards: bool = False,
    lane: str = LANE,
    validation: str = VALIDATION,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return bounded shadow anchors plus a fail-closed diagnostic trace."""
    payload = _load(str(config_path.resolve()))
    bounded_seeds = seeds[: payload["max_seeds"]]
    seed_ids = {str(row.get("id") or "") for row in bounded_seeds}
    seed_indexes: dict[tuple[str, str], list[int]] = {}
    invalid_seeds = 0
    for seed in bounded_seeds:
        identity = _identity(seed)
        index = _index(seed)
        if identity is None or index is None:
            invalid_seeds += 1
            continue
        seed_indexes.setdefault(identity, []).append(index)

    trace: dict[str, Any] = {
        "lane": lane,
        "validation": validation,
        "seed_rows": len(bounded_seeds),
        "valid_seed_rows": len(bounded_seeds) - invalid_seeds,
        "invalid_seed_rows": invalid_seeds,
        "input_candidates": len(candidates),
        "same_blob_candidates": 0,
        "positive_query_candidates": 0,
        "facet_candidates": 0,
        "toc_rejected_ids": [],
        "overflow": False,
        "selected_ids": [],
        "shadow_only": True,
    }
    if not query.strip() or not seed_indexes:
        trace["reason"] = "empty_query_or_no_valid_seed_identity"
        return [], trace

    eligible: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    allowed_languages = set(payload["allowed_languages"])
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "")
        gap = _nearest_gap(candidate, seed_indexes)
        language = str(candidate.get("language") or "").lower()
        if (
            not candidate_id
            or candidate_id in seed_ids
            or candidate_id in seen_ids
            or gap is None
            or gap < 1
            or gap > payload["max_gap"]
            or (language and language not in allowed_languages)
        ):
            continue
        row = dict(candidate)
        row["structural_neighbor_gap"] = gap
        eligible.append(row)
        seen_ids.add(candidate_id)
    trace["same_blob_candidates"] = len(eligible)
    if len(eligible) > payload["max_candidates"]:
        trace.update({"overflow": True, "reason": "candidate_cap_exceeded"})
        return [], trace

    plan = expand_query_facets(query, query_facets_path)
    scores = {str(row["id"]): 0.0 for row in eligible}
    for need in plan["needs"]:
        for score, row in _rank_bm25(need, eligible):
            row_id = str(row["id"])
            scores[row_id] = max(scores[row_id], score)

    positive = [row for row in eligible if scores[str(row["id"])] > 0]
    trace["positive_query_candidates"] = len(positive)
    priority_attributes = set(
        (payload.get("numeric_priority_attributes") or {}).get(
            plan.get("archetype") or "", []
        )
    )
    ranked: list[dict[str, Any]] = []
    for row in positive:
        content = row.get("content") or ""
        section_title = str(row.get("section_title") or "").casefold()
        if is_toc_page(content) or re.search(
            r"\b(?:indice|índice|contents|table of contents)\b", section_title
        ):
            trace["toc_rejected_ids"].append(str(row["id"]))
            continue
        facet_matches = match_evidence_facets(
            content,
            archetype=plan.get("archetype"),
            config_path=evidence_match_config_path,
        )
        if not facet_matches:
            continue
        entity_id = str(row.get("product_model") or "").strip()
        claims = (
            extract_numeric_claims(content, entity_id=entity_id)
            if entity_id
            else []
        )
        priority_claims = [
            claim for claim in claims if claim.attribute in priority_attributes
        ]
        numeric_cards = [
            {
                "candidate_id": row["id"],
                "candidate_rank": 1,
                "start": claim.start,
                "end": claim.end,
                "quote": claim.clause,
                "facet": f"structured_numeric:{claim.attribute}",
                "structured_claim": claim.to_dict(),
                "exact_source_span_validated": True,
            }
            for claim in priority_claims
        ]
        facet_cards = select_evidence_coverage_cards(
            [row],
            archetype=plan.get("archetype"),
            config_path=evidence_card_config_path,
            query=query if query_aligned_cards else None,
        )
        coverage_cards = []
        seen_spans = set()
        for card in [*numeric_cards, *facet_cards]:
            key = (card["start"], card["end"], card["quote"])
            if key in seen_spans:
                continue
            seen_spans.add(key)
            coverage_cards.append(card)
            if len(coverage_cards) == 4:
                break
        enriched = dict(row)
        enriched.update(
            {
                "retrieval_lane": lane,
                "structural_neighbor_validated": True,
                "structural_neighbor_validation": validation,
                "structural_neighbor_query_archetype": plan.get("archetype"),
                "structural_neighbor_query_score": round(
                    scores[str(row["id"])], 6
                ),
                "structural_neighbor_facets": facet_matches,
                "structured_numeric_claims": [
                    claim.to_dict() for claim in claims
                ],
                "structured_priority_claims": [
                    claim.to_dict() for claim in priority_claims
                ],
                "coverage_cards": coverage_cards,
                "coverage_card_facets": [
                    card["facet"] for card in coverage_cards
                ],
                "local_semantic_validated": True,
                # Deliberately absent: coverage_validated.  Only a later source
                # receipt and release gate may set the runtime attestation.
            }
        )
        ranked.append(enriched)
    trace["facet_candidates"] = len(ranked)

    def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
        facets = row["structural_neighbor_facets"]
        hit_counts = [len(item["term_hits"]) for item in facets]
        return (
            -bool(row["structured_priority_claims"]),
            -len(facets),
            -sum(hit_counts),
            -max(hit_counts, default=0),
            -row["structural_neighbor_query_score"],
            row["structural_neighbor_gap"],
            str(row["id"]),
        )

    ranked.sort(key=rank_key)
    selected = ranked[: payload["max_anchors"]]
    for rank, row in enumerate(selected, start=1):
        row["structural_neighbor_rank"] = rank
    trace.update(
        {
            "archetype": plan.get("archetype"),
            "needs": plan["needs"],
            "selected_ids": [str(row["id"]) for row in selected],
            "reason": "selected" if selected else "no_query_aligned_facet_candidate",
        }
    )
    return selected, trace
