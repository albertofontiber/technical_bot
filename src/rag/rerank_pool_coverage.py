"""Deterministic post-rerank coverage over the already-retrieved pool.

Lane VETADA bajo todo perfil C1 (release_profiles): solo sus deudores en
cuarentena la importan.  El motor de selección compartido y la reserva viva
obligation-warning se graduaron a sus módulos propios (``pool_selection`` y
``obligation_warning``) en el split L2c/s313.

The main reranker remains authoritative and immutable.  This lane only looks
at real source rows already paid for by retrieval, restricts them to canonical
document scope when the product resolver is confident, and appends at most two
query-aligned complements.  No gold fact, QID, expected value, model endpoint
or database call is available to the selector.
"""
from __future__ import annotations

from typing import Any

from .catalog_resolver import resolve_query
from .evidence_coverage import (
    POOL_COMPLEMENT_CONFIG,
    match_evidence_facets,
    select_evidence_coverage_cards,
)
from .pool_selection import (
    POOL_LIMIT,
    QUERY_CONFIG,
    _bm25_scores,
    _cosine,
    _fold,
    _in_canonical_scope,
    _incremental_needs,
    _query_card,
    _tokens,
)
from .query_facets import expand_query_facets
from .toc_detection import is_toc_page

LANE = "retrieval_pool_coverage_v1"
VALIDATION = "same_query_retrieval_pool_canonical_scope_exact_span_v1"
APPEND_LIMIT = 2


def select_rerank_pool_coverage(
    query: str,
    retrieval_pool: list[dict[str, Any]],
    reranked: list[dict[str, Any]],
    *,
    apply_catalog_scope: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select at most two complementary exact-source rows from a frozen pool."""
    trace: dict[str, Any] = {
        "lane": LANE,
        "validation": VALIDATION,
        "input_pool_rows": len(retrieval_pool),
        "bounded_pool_rows": 0,
        "canonical_scope_rows": 0,
        "eligible_rows": 0,
        "selected_ids": [],
        "model_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "catalog_scope_applied": apply_catalog_scope,
    }
    if not query.strip() or not retrieval_pool or len(retrieval_pool) > POOL_LIMIT:
        trace["status"] = "not_applicable_or_pool_overflow"
        return [], trace

    bounded = retrieval_pool[:POOL_LIMIT]
    trace["bounded_pool_rows"] = len(bounded)
    reranked_ids = {str(row.get("id") or "") for row in reranked}
    # The generic retrieval-pool lane retains its governed catalogue scope.
    # Callers that already hold an exact document/blob authority may disable
    # this second, redundant source filter so historical catalogue preferences
    # cannot influence ranking inside that proven boundary.
    resolution = resolve_query(query) if apply_catalog_scope else {}
    candidates = []
    seen = set()
    location_token_sets: dict[tuple[Any, ...], list[set[str]]] = {}
    duplicate_location_rows = 0
    for pool_rank, source_row in enumerate(bounded):
        row_id = str(source_row.get("id") or "")
        source_file = str(source_row.get("source_file") or "")
        content = source_row.get("content") or ""
        if (
            not row_id
            or row_id in reranked_ids
            or row_id in seen
            or not source_file
            or not content
            or not _in_canonical_scope(source_row, resolution)
            or is_toc_page(
                f"{source_row.get('section_title') or ''}\n\n{content}"
            )
        ):
            continue
        page_number = source_row.get("page_number")
        section_key = _fold(str(source_row.get("section_title") or ""))
        location = (
            (source_file, page_number, section_key)
            if page_number is not None or section_key
            else ("row", row_id)
        )
        content_terms = set(_tokens(content))
        near_duplicate = any(
            len(content_terms & prior_terms) / max(1, len(content_terms | prior_terms))
            >= 0.9
            for prior_terms in location_token_sets.get(location, [])
        )
        if near_duplicate:
            duplicate_location_rows += 1
            continue
        row = dict(source_row)
        row["rerank_pool_rank"] = pool_rank
        candidates.append(row)
        seen.add(row_id)
        location_token_sets.setdefault(location, []).append(content_terms)
    trace["canonical_scope_rows"] = len(candidates)
    trace["duplicate_location_rows_rejected"] = duplicate_location_rows
    if not candidates:
        trace["status"] = "no_canonical_candidates"
        return [], trace

    plan = expand_query_facets(query, config_path=QUERY_CONFIG)
    expanded_needs = list(plan.get("needs") or [query])
    needs = _incremental_needs(query, expanded_needs)
    base_scores = _bm25_scores(query, candidates)
    base_maximum = max(base_scores, default=0.0) or 1.0
    per_need_scores = [_bm25_scores(need, candidates) for need in needs]
    maxima = [max(scores, default=0.0) or 1.0 for scores in per_need_scores]

    covered_facets = {
        str(match["facet"])
        for row in reranked
        if _in_canonical_scope(row, resolution)
        for match in match_evidence_facets(
            row.get("content") or "",
            archetype=plan.get("archetype"),
            config_path=POOL_COMPLEMENT_CONFIG,
        )
    }
    eligible = []
    for index, row in enumerate(candidates):
        facet_cards = select_evidence_coverage_cards(
            [row],
            archetype=plan.get("archetype"),
            config_path=POOL_COMPLEMENT_CONFIG,
        )
        query_card = _query_card([query, *needs], row)
        if query_card is None:
            continue
        cards = list(facet_cards)
        cards.append(query_card)
        if not cards or not any(scores[index] > 0 for scores in per_need_scores):
            continue
        facets = {str(card.get("facet") or "") for card in cards}
        base_score = round(base_scores[index] / base_maximum, 8)
        need_scores = [
            round(scores[index] / maximum, 8)
            for scores, maximum in zip(per_need_scores, maxima)
        ]
        alignment_hits = {
            str(hit)
            for card in cards
            for hit in (
                card.get("query_term_hits")
                or card.get("alignment_term_hits")
                or []
            )
        }
        enriched = dict(row)
        enriched.update(
            {
                "retrieval_lane": LANE,
                "rerank_pool_coverage_validated": True,
                "rerank_pool_coverage_validation": VALIDATION,
                "rerank_pool_query_archetype": plan.get("archetype"),
                "rerank_pool_base_score": base_score,
                "rerank_pool_need_scores": need_scores,
                "rerank_pool_facets": sorted(facets),
                "rerank_pool_alignment_hits": sorted(alignment_hits),
                "coverage_cards": cards[:4],
                "coverage_card_facets": [
                    str(card.get("facet") or "") for card in cards[:4]
                ],
                "local_semantic_validated": True,
            }
        )
        eligible.append(enriched)
    trace["eligible_rows"] = len(eligible)

    selected = []
    remaining = list(eligible)
    uncovered_needs = set(range(len(needs)))
    while remaining and len(selected) < APPEND_LIMIT:
        def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
            facets = set(row["rerank_pool_facets"])
            scores = row["rerank_pool_need_scores"]
            best_uncovered = max(
                (scores[index] for index in uncovered_needs), default=max(scores, default=0.0)
            )
            pool_prior = 1.0 - min(
                int(row["rerank_pool_rank"]), POOL_LIMIT - 1
            ) / POOL_LIMIT
            facet_gain = min(2, len(facets - covered_facets)) / 2
            facet_signal = min(3, len(facets - {"query_alignment"})) / 3
            alignment = min(10, len(row["rerank_pool_alignment_hits"])) / 10
            coverage_score = (
                0.35 * best_uncovered
                + 0.35 * float(row["rerank_pool_base_score"])
                + 0.15 * alignment
                + 0.05 * facet_signal
                + 0.05 * facet_gain
                + 0.05 * pool_prior
            )
            # A two-row budget should cover distinct technical intents rather
            # than two paraphrases with the same need profile.
            redundancy = max(
                (
                    _cosine(scores, prior["rerank_pool_need_scores"])
                    for prior in selected
                ),
                default=0.0,
            )
            coverage_score -= 0.12 * redundancy
            return (
                round(coverage_score, 8),
                best_uncovered,
                float(row["rerank_pool_base_score"]),
                len(facets - covered_facets),
                len(row["rerank_pool_alignment_hits"]),
                -int(row["rerank_pool_rank"]),
                str(row["id"]),
            )

        winner = max(remaining, key=rank_key)
        remaining.remove(winner)
        selected.append(winner)
        covered_facets.update(winner["rerank_pool_facets"])
        if uncovered_needs:
            winner_scores = winner["rerank_pool_need_scores"]
            strongly_covered = {
                index for index in uncovered_needs if winner_scores[index] >= 0.8
            }
            if strongly_covered:
                uncovered_needs.difference_update(strongly_covered)
            else:
                best_need = max(uncovered_needs, key=lambda index: winner_scores[index])
                uncovered_needs.remove(best_need)

    for rank, row in enumerate(selected, start=1):
        row["rerank_pool_coverage_rank"] = rank
    trace.update(
        {
            "status": "selected" if selected else "no_query_aligned_candidate",
            "archetype": plan.get("archetype"),
            "needs": needs,
            "selected_ids": [str(row["id"]) for row in selected],
        }
    )
    return selected, trace


# ── RE-EXPORTS ───────────────────────────────────────────────────────────────
# Shim DECLARADO del split L2c (MIN_ALIGNMENT_TERMS retirado: el sub-agente
# grepeo CERO consumidores por esta ruta — un shim solo re-exporta lo que
# alguien consume). Consumidores REALES por esta ruta (Sol s313 cazó
# que decir solo «tests» sub-declaraba): los monkeypatch de tests/test_rerank_pool_
# coverage.py Y los instrumentos scripts/s291_l2_v1_probe.py + s288c_gate_funnel_
# probe.py. Muere con la lane o cuando TODOS esos consumidores migren.
# OJO semántica de namespace (Sol s313): `select_obligation_warning_reserve` aquí es
# RE-EXPORT — sus globals resuelven en obligation_warning; un monkeypatch de sus
# helpers debe apuntar ALLÍ, no aquí (los 5 patch vivos de resolve_query afectan a la
# selectora vetada, que SÍ vive aquí — intactos).
from .obligation_warning import (  # noqa: E402,F401
    OBLIGATION_WARNING_LANE,
    _group_has_residual_content,
    _is_blockquote_span,
    _is_procedural_diagnostic_query,
    _is_table_group,
    _warning_span,
    select_obligation_warning_reserve,
)
