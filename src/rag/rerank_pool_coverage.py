"""Deterministic post-rerank coverage over the already-retrieved pool.

The main reranker remains authoritative and immutable.  This lane only looks
at real source rows already paid for by retrieval, restricts them to canonical
document scope when the product resolver is confident, and appends at most two
query-aligned complements.  No gold fact, QID, expected value, model endpoint
or database call is available to the selector.

s278 §3 añade una segunda selección INDEPENDIENTE sobre el mismo pool pagado:
la reserva obligation-aware de UN chunk-warning (clase hp002), flag
``OBLIGATION_WARNING_RESERVE``.  Ver ``select_obligation_warning_reserve``.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

from .catalog_resolver import resolve_query
from .evidence_coverage import (
    POOL_COMPLEMENT_CONFIG,
    match_evidence_facets,
    select_evidence_coverage_cards,
)
from .evidence_window import _candidate_windows
from .mp_lexicon import mandatory_triggers, sentence_spans, trigger_present
from .query_facets import ROOT as QUERY_ROOT, expand_query_facets
from .toc_detection import is_toc_page

LANE = "retrieval_pool_coverage_v1"
VALIDATION = "same_query_retrieval_pool_canonical_scope_exact_span_v1"
POOL_LIMIT = 64
APPEND_LIMIT = 2
WINDOW_CHARS = 360
MIN_ALIGNMENT_TERMS = 6
QUERY_CONFIG = QUERY_ROOT / "config/retrieval_facets_v4.yaml"

# ───────── s278 §3: reserva obligation-aware de UN chunk-warning (hp002) ─────────
# Fallo real (hp002:r1, chunk 5b6a3a19 ASD535 p121): la advertencia obligatoria
# estaba en el pool (#28) y no se sirvió — la puerta de alineación de 6 términos
# de `_query_card` la dejó fuera (el léxico de un bloque de ADVERTENCIA no
# comparte términos con la pregunta) y el cap global MAX_APPENDED=4 se consumió
# antes.  Esta selección NO compite por esos 4 huecos: `post_rerank_coverage`
# le da un presupuesto PROPIO de 1 fila, fail-open en cualquier duda.
OBLIGATION_WARNING_LANE = "obligation_warning_reserve_v1"
OBLIGATION_WARNING_VALIDATION = (
    "procedural_query_served_document_scope_mandatory_warning_exact_span_v1"
)
# Espejo del bound de la card de callout-MANDATORY (s274,
# MAX_MANDATORY_CALLOUT_CHARS): un bloque de aviso mayor se omite ENTERO,
# jamás se recorta a media oración.
MAX_WARNING_RESERVE_CHARS = 600
# Extensión mínima del léxico MANDATORY cerrado (mp_lexicon, DEC-122/130) para
# bloques de aviso: "precaución" es cabecera normativa de callout y no está en
# el léxico de Etapa-1.  Lista versionada en código (sin LLM), formas foldeadas.
_WARNING_EXTRA_TERMS = ("precaucion", "precauciones")
_WARNING_GAP_ALNUM = re.compile(r"[A-Za-z0-9]")
# (s278 §3, calca el estilo de `_SELECTION_INTENT` DEC-101 en generator.py)
# Detector code-gated DETERMINISTA de pregunta procedimental/diagnóstica sobre
# la query FOLDEADA (minúsculas, sin acentos).  Conservador a propósito
# (fail-open: en duda NO se reserva): una pregunta de spec/identificación
# (hp009 «¿cuál es la resistencia de fin de línea…?») no dispara.
_OBLIGATION_INTENT = re.compile(
    r"(\bcomo\s+(se|debo|puedo|hago|realizo|reviso|compruebo)\b"
    r"|\bpasos\b"
    r"|\bprocedimiento\w*"
    r"|\bmantenimiento\b"
    r"|\bpuesta\s+en\s+(marcha|servicio)\b"
    r"|\bdiagnost\w+"
    r"|\baveria\w*"
    r"|\btroubleshoot\w*"
    r"|\bcausa\s+(mas\s+)?probable\b"
    r"|\bhow\s+(do|to|can|should)\b)"
)
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


def _is_procedural_diagnostic_query(query: str) -> bool:
    """Trigger determinista de la reserva (el LLM no decide si aplica)."""
    return bool(_OBLIGATION_INTENT.search(_fold(query)))


def _warning_sentence_triggers(sentence: str) -> list[str]:
    """Léxico MANDATORY cerrado (reusado de mp_lexicon) + extensión de aviso."""
    triggers = mandatory_triggers(sentence)
    folded = _fold(sentence)
    triggers.extend(
        term for term in _WARNING_EXTRA_TERMS if trigger_present(term, folded)
    )
    return triggers


def _warning_span(content: str) -> tuple[int, int, list[str]] | None:
    """Primer bloque de aviso acotado del chunk, o None.

    Misma mecánica de agrupación que la card de callout-MANDATORY (s274,
    ``_mandatory_callout_card``): oraciones con gatillo del léxico cerrado,
    contiguas se mergean cuando el hueco no contiene alfanuméricos, y un grupo
    mayor que el bound se omite entero — jamás se recorta a media oración.
    """
    groups: list[list[int]] = []
    for start, end in sentence_spans(content):
        if not _warning_sentence_triggers(content[start:end]):
            continue
        if groups and not _WARNING_GAP_ALNUM.search(content[groups[-1][1]:start]):
            groups[-1][1] = end
        else:
            groups.append([start, end])
    for start, end in groups:
        if end - start > MAX_WARNING_RESERVE_CHARS:
            continue
        return start, end, _warning_sentence_triggers(content[start:end])
    return None


def select_obligation_warning_reserve(
    query: str,
    retrieval_pool: list[dict[str, Any]],
    served_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """s278 §3 (clase hp002): a lo sumo UN chunk-warning del pool ya pagado.

    Determinista y fail-open: solo para pregunta procedimental/diagnóstica
    (``_OBLIGATION_INTENT``), solo chunks del MISMO documento canónico
    (``source_file``, la noción de scope de esta lane) que lo YA SERVIDO —
    jamás cross-family — y solo si el contenido lleva un bloque acotado del
    léxico MANDATORY.  Cualquier duda => no reservar.  El presupuesto (1 fila
    FUERA del cap global de 4) y la revalidación exacta contra el pool los
    aplica ``post_rerank_coverage``.
    """
    trace: dict[str, Any] = {
        "lane": OBLIGATION_WARNING_LANE,
        "validation": OBLIGATION_WARNING_VALIDATION,
        "input_pool_rows": len(retrieval_pool),
        "served_scope_files": 0,
        "selected_ids": [],
        "model_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }
    if not query.strip() or not retrieval_pool or len(retrieval_pool) > POOL_LIMIT:
        trace["status"] = "not_applicable_or_pool_overflow"
        return [], trace
    if not _is_procedural_diagnostic_query(query):
        trace["status"] = "non_procedural_query"
        return [], trace
    served_scopes = {
        str(row.get("source_file") or "")
        for row in served_rows
        if str(row.get("source_file") or "")
    }
    trace["served_scope_files"] = len(served_scopes)
    if not served_scopes:
        trace["status"] = "no_served_document_scope"
        return [], trace
    served_ids = {str(row.get("id") or "") for row in served_rows}
    for pool_rank, source_row in enumerate(retrieval_pool[:POOL_LIMIT]):
        row_id = str(source_row.get("id") or "")
        source_file = str(source_row.get("source_file") or "")
        content = str(source_row.get("content") or "")
        if (
            not row_id
            or row_id in served_ids
            or not source_file
            or source_file not in served_scopes
            or not content
            or is_toc_page(
                f"{source_row.get('section_title') or ''}\n\n{content}"
            )
        ):
            continue
        span = _warning_span(content)
        if span is None:
            continue
        start, end, triggers = span
        enriched = dict(source_row)
        enriched.update(
            {
                "retrieval_lane": OBLIGATION_WARNING_LANE,
                "obligation_warning_reserve_validated": True,
                "obligation_warning_reserve_validation": (
                    OBLIGATION_WARNING_VALIDATION
                ),
                "obligation_warning_pool_rank": pool_rank,
                # La validación de esta lane ES determinista (intención
                # procedimental + scope de documento servido + léxico
                # MANDATORY): la clase de seguridad sustituye a la alineación
                # por facetas de query (punto ciego medido en hp002:r1).
                "local_semantic_validated": True,
                "coverage_cards": [
                    {
                        "candidate_id": row_id,
                        "candidate_rank": 1,
                        "start": start,
                        "end": end,
                        "quote": content[start:end],
                        "facet": "mandatory_warning",
                        "mandatory_warning": True,
                        "warning_term_hits": sorted(set(triggers)),
                        "exact_source_span_validated": True,
                    }
                ],
            }
        )
        trace["status"] = "selected"
        trace["selected_ids"] = [row_id]
        return [enriched], trace
    trace["status"] = "no_warning_in_served_scope"
    return [], trace
