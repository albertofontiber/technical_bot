"""Reserva obligation-aware de UN chunk-warning (clase hp002) — s278 §3.

Lane VIVA (v3/v4), graduada a módulo propio en el split L2c/s313 del
doble-inquilino (blueprint §4-L2c): el motor de selección compartido vive en
``pool_selection``; la lane vetada quedó en ``rerank_pool_coverage``.
"""
from __future__ import annotations

import re
from typing import Any

from .mp_lexicon import mandatory_triggers, sentence_spans, trigger_present
from .pool_selection import POOL_LIMIT, _fold
from .toc_detection import is_toc_page

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


def _ordered_reserve_enabled() -> bool:
    from ..config import _strict_on_off

    return _strict_on_off("OBLIGATION_RESERVE_ORDERED")


# Los compuestos del léxico ("debe(n)+antes de" / "must+before") no son
# substrings literales del span: para el filtro de contenido-residual se
# retiran por sus COMPONENTES (mismos patrones que trigger_present).
_WARNING_COMPOUND_COMPONENTS = {
    "debe(n)+antes de": (r"\bdebe(?:n)?\b", r"antes de"),
    "must+before": (r"\bmust\b", r"\bbefore\b"),
}
_WARNING_LINE_QUOTE_PREFIX = re.compile(r"^(?:>\s*)+")


def _warning_group_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_table_group(text: str) -> bool:
    """Grupo cuyo texto entero son filas de tabla markdown (changelog/specs).

    Se pliega el prefijo blockquote ANTES de mirar el ``|`` inicial: una tabla
    dentro de un callout sigue siendo tabla.
    """
    lines = _warning_group_lines(text)
    if not lines:
        return False
    return all(
        _WARNING_LINE_QUOTE_PREFIX.sub("", line).startswith("|") for line in lines
    )


def _group_has_residual_content(text: str) -> bool:
    """False = marcador huérfano: sin contenido alfanumérico más allá de los
    gatillos (p.ej. ``> **Peligro**`` con el cuerpo del callout sin gatillo en
    otro grupo).  Retirada boundary-safe: frases multi-palabra como substring,
    términos-token con boundary, compuestos por sus componentes.  Sin umbral."""
    folded = _fold(text)
    for trigger in set(_warning_sentence_triggers(text)):
        for pattern in _WARNING_COMPOUND_COMPONENTS.get(trigger, ()):
            folded = re.sub(pattern, " ", folded)
        if trigger in _WARNING_COMPOUND_COMPONENTS:
            continue
        if " " in trigger:
            folded = folded.replace(trigger, " ")
        else:
            folded = re.sub(
                rf"(?<![a-z0-9]){re.escape(trigger)}(?![a-z0-9])", " ", folded
            )
    return bool(re.search(r"[a-z0-9]", folded))


def _is_blockquote_span(text: str) -> bool:
    """Span cuyas líneas no vacías son TODAS blockquote — la forma en que la
    extracción preserva las cajas de callout reales (censo
    evals/s289_warning_census_v1.json, 284 docs)."""
    lines = _warning_group_lines(text)
    return bool(lines) and all(line.startswith(">") for line in lines)


def _warning_span(
    content: str, *, filtered: bool = False
) -> tuple[int, int, list[str]] | None:
    """Primer bloque de aviso acotado del chunk, o None.

    Misma mecánica de agrupación que la card de callout-MANDATORY (s274,
    ``_mandatory_callout_card``): oraciones con gatillo del léxico cerrado,
    contiguas se mergean cuando el hueco no contiene alfanuméricos, y un grupo
    mayor que el bound se omite entero — jamás se recorta a media oración.

    ``filtered=True`` (solo bajo ``OBLIGATION_RESERVE_ORDERED``) aplica los 2
    filtros de clase POR-GRUPO — grupo-tabla y marcador-huérfano hacen
    ``continue`` al siguiente grupo del MISMO chunk, igual que el bound de
    tamaño (dúo r3 s289, A3: un primer-grupo-FP no entierra un callout real
    más abajo del chunk).  Default False = byte-idéntico al comportamiento
    previo.
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
        if filtered:
            text = content[start:end]
            if _is_table_group(text) or not _group_has_residual_content(text):
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
    ordered = _ordered_reserve_enabled()
    candidates: list[dict[str, Any]] = []
    discards: list[dict[str, Any]] = []
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
        span = _warning_span(content, filtered=ordered)
        if span is None:
            # Atribución para G-1/observabilidad: la fila TENÍA span sin
            # filtros => los filtros de clase la descartaron entera.  La
            # llamada extra solo corre en ese path de miss.
            if ordered and _warning_span(content) is not None:
                discards.append(
                    {
                        "pool_rank": pool_rank,
                        "id": row_id,
                        "filter": "all_groups_filtered",
                    }
                )
            continue
        if not ordered:
            trace["status"] = "selected"
            trace["selected_ids"] = [row_id]
            return [_reserve_enriched_row(source_row, row_id, pool_rank, span)], trace
        start, end, _triggers = span
        candidates.append(
            {
                "pool_rank": pool_rank,
                "row_id": row_id,
                "source_row": source_row,
                "span": span,
                "blockquote": _is_blockquote_span(content[start:end]),
                # v2 (escalada pre-declarada en el diseño s289, disparada por
                # el G-1 orden-v1: fa55311c p.78 «Instalación» ganaba por rank
                # al aviso de la sección procedimental p.121): el aviso que
                # GATEA el procedimiento preguntado vive en la sección cuyo
                # título matchea la MISMA intención que dispara la lane —
                # léxico existente, cero vocabulario nuevo.
                "section_intent": bool(
                    _OBLIGATION_INTENT.search(
                        _fold(str(source_row.get("section_title") or ""))
                    )
                ),
            }
        )
    if ordered:
        trace["reserve_discards"] = discards
        if candidates:
            # Orden determinista v2 (dúo r3 + escalada declarada): sección
            # con intención procedimental primero, callout-blockquote después
            # (censo: la clase = avisos reales), pool-rank de desempate.  Sin
            # señal alguna degrada a pool-rank = first-match actual.
            candidates.sort(
                key=lambda c: (
                    not c["section_intent"],
                    not c["blockquote"],
                    c["pool_rank"],
                )
            )
            trace["reserve_ranked_ids"] = [c["row_id"] for c in candidates]
            winner = candidates[0]
            trace["status"] = "selected"
            trace["selected_ids"] = [winner["row_id"]]
            return [
                _reserve_enriched_row(
                    winner["source_row"],
                    winner["row_id"],
                    winner["pool_rank"],
                    winner["span"],
                )
            ], trace
    trace["status"] = "no_warning_in_served_scope"
    return [], trace


def _reserve_enriched_row(
    source_row: dict[str, Any],
    row_id: str,
    pool_rank: int,
    span: tuple[int, int, list[str]],
) -> dict[str, Any]:
    """Fila de reserva enriquecida — extraído del bucle sin cambio de campos."""
    start, end, triggers = span
    content = str(source_row.get("content") or "")
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
    return enriched
