"""Default-off, fail-open post-rerank source-evidence coverage.

The main reranker's output is a protected prefix.  Independently validated
real source chunks may only be appended; they can never reorder or mutate that
prefix.  This makes retrieval-stage movement observable without silently
changing the established ranking contract.

Contrato de la VISTA SERVIDA (s110/s111 + s274 C1, explícito — dúo Sol-M4): para un
chunk de lane validada, ``coverage_context_content`` sirve SOLO spans exactos
receipted del padre inmutable — las ``coverage_cards`` del selector (alineadas a
facetas de la query, con validación semántica de la lane) y, opcionalmente:

  * expansión de fila lógica de tabla (``served_coverage_cards``, flag
    ``LOGICAL_RECORD_COVERAGE``) — completa la fila intersecada, jamás añade spans;
  * **card de callout-MANDATORY** (s274 C1, flag ``COVERAGE_MANDATORY_CALLOUT``
    default-off): clase PROPIA ``card_class="mandatory_callout"`` en CAMPO PROPIO
    ``mandatory_callout_cards`` (jamás dentro de ``served_coverage_cards``) —
    oraciones con gatillo del léxico cerrado F-MANDATORY (mp_lexicon) FUERA de los
    spans ya servidos, 1 card máx por chunk, ≤600 chars, receipt exacto propio
    (``has_exact_mandatory_callout_receipt``). NO hereda la validación semántica
    del selector (``local_semantic_validated`` explícito a False): su justificación
    es la CLASE de seguridad (mandatory_safety_omission s243), sistemáticamente
    fuera de las facetas de query — punto ciego medido en
    evals/s274_serving_view_diag_v1.json (el bloque warning de hp017 F12 quedaba
    fuera de toda card y ni generador ni detector lo veían). Al vivir en campo
    propio, los consumidores que derivan OBLIGACIONES de ``served_coverage_cards``
    (answer_planner) NO la ven por construcción (fail-closed estructural, sin
    tocar el módulo pineado por s201/s260).

s278 §3 (flag ``OBLIGATION_WARNING_RESERVE``, default-off byte-inerte): reserva
obligation-aware de A LO SUMO un chunk-warning del pool ya pagado (clase
hp002) con presupuesto PROPIO de 1 fila FUERA del cap global ``MAX_APPENDED``,
solo en preguntas procedimentales/diagnósticas y solo del MISMO scope canónico
de documento que lo ya servido; el chunk exacto (id+content) se revalida
contra el pool antes de reservar.  Selector determinista en
``rerank_pool_coverage.select_obligation_warning_reserve``.

s278 §4 (flag ``PROSE_SOURCE_CARD``, default-off byte-inerte, releído
at-call-time): el lane document-local admite una SEGUNDA clase de card servida
— ``card_class="prose_source_card"`` / ``record_kind="prose_sentence_span_v1"``
(campo propio ``prose_source_cards``, seleccionada y atestada en
``document_local_coverage``) — SOLO cuando la clase de fila
``markdown_pipe_row_v1`` no es derivable del chunk (clases complementarias,
jamás mezcladas).  El span servido es la(s) oración(es) completa(s) verbatim
de la card; su receipt completo (document+extraction+source+chunk+
content-hash+quote-hash+bounds, ``has_exact_prose_source_card_receipt``) se
revalida aquí antes de servir y cualquier fallo => la fila NO se sirve
(fail-closed).  La clase de fila queda byte-exacta con la prosa off Y on.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from ..config import (
    CANONICAL_HYQ_COVERAGE,
    COMPATIBILITY_BUNDLE_COVERAGE,
    DOCUMENT_LOCAL_COVERAGE,
    LOGICAL_RECORD_COVERAGE,
    OBLIGATION_WARNING_RESERVE,
    POST_RERANK_COVERAGE,
    RERANK_POOL_COVERAGE,
    STRUCTURAL_CASCADE_COVERAGE,
    STRUCTURAL_NEIGHBOR_COVERAGE,
    TABLE_PREAMBLE_CLOSURE,
)
from .compatibility_bundle_coverage import (
    LANE as COMPATIBILITY_LANE,
    collect_compatibility_bundle,
    is_compatibility_bundle_query,
    validate_compatibility_bundle,
)
from .doc_scoped_hyq_coverage import (
    LANE as HYQ_LANE,
    collect_document_scoped_hyq,
)
from .catalog_resolver import governed_catalog_scope_owners, resolve_query
from ..release_profiles import DOCUMENT_LOCAL_LANE, DOCUMENT_LOCAL_VALIDATION
from .structural_neighbor_coverage import (
    CASCADED_CONFIG as STRUCTURAL_CASCADE_CONFIG,
    CASCADED_EVIDENCE_CONFIG,
    CASCADED_LANE as STRUCTURAL_CASCADE_LANE,
    CASCADED_QUERY_FACETS,
    CASCADED_VALIDATION as STRUCTURAL_CASCADE_VALIDATION,
    DEFAULT_CONFIG as STRUCTURAL_CONFIG,
    LANE as STRUCTURAL_LANE,
    select_structural_neighbors,
)
from .structural_neighbor_shadow import fetch_structural_neighbor_rows
from .table_preamble_closure import (
    LANE as TABLE_PREAMBLE_LANE,
    select_table_preambles,
)
from .mp_lexicon import mandatory_triggers, sentence_spans
from .rerank_pool_coverage import (
    LANE as POOL_LANE,
    OBLIGATION_WARNING_LANE,
    WINDOW_CHARS as FACET_WINDOW_CHARS,
    _exact_windows as _facet_exact_windows,
    _fold as _facet_fold,
    _tokens as _facet_tokens,
    select_obligation_warning_reserve,
    select_rerank_pool_coverage,
)

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
ALLOWED_LANES = frozenset(
    {
        STRUCTURAL_LANE,
        STRUCTURAL_CASCADE_LANE,
        HYQ_LANE,
        POOL_LANE,
        DOCUMENT_LOCAL_LANE,
        COMPATIBILITY_LANE,
        TABLE_PREAMBLE_LANE,
        OBLIGATION_WARNING_LANE,
    }
)
MAX_APPENDED = 4
MAX_APPENDED_PER_LANE = 2
# s278 §3: presupuesto PROPIO de la reserva de warning — NO compite con los 4
# huecos de MAX_APPENDED (el fallo hp002:r1 era exactamente ese desplazamiento).
OBLIGATION_WARNING_RESERVE_BUDGET = 1
# s279 compuerta 2 [VIA-INALCANZABLE · ATTEST · TIEBREAK]: presupuesto PROPIO de la
# vía complementaria por-faceta — espejo EXACTO de OBLIGATION_WARNING_RESERVE_BUDGET,
# FUERA del cap global MAX_APPENDED (A8).  N_FACET = umbral de cobertura de una
# need-group (grado>=N_FACET => cubierta) y de elegibilidad de un candidato
# (ventana con >=N_FACET términos distintos del grupo) — pre-registrado, sin
# calibrar (A4/A7).  La regla de ventana reusa la de 360 chars del pool selector.
FACET_COMPLEMENT_BUDGET = 1
N_FACET = 3
MAX_APPENDED_BY_LANE = {
    COMPATIBILITY_LANE: 3,
    DOCUMENT_LOCAL_LANE: 1,
}
STRUCTURAL_SERVING_TIMEOUT_SECONDS = 2.0
TABLE_PREAMBLE_CONFIG = ROOT / "config/table_preamble_closure_v3.yaml"
MAX_LOGICAL_TABLE_ROW_CHARS = 1400
MAX_EXPANDED_EXCERPT_CHARS = 1800
DOCUMENT_LOCAL_RECORD_KIND = "markdown_pipe_row_v1"
# s278 §4: contrato de la clase de PROSA del lane document-local.
DOCUMENT_LOCAL_PROSE_CONTRACT = "exact_source_bounded_prose_sentence_span_v1"
DOCUMENT_LOCAL_ANCHOR_LIMIT = 2
DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR = "governed_source_contract"
DOCUMENT_LOCAL_PREFIX_ANCHOR = "protected_rerank_prefix"
DOCUMENT_LOCAL_STRUCTURAL_ANCHOR = "served_structural_append"
DOCUMENT_LOCAL_SOURCE_CONTRACT_CONFIG = (
    ROOT / "config/document_local_source_contracts_v1.yaml"
)
_DOCUMENT_LOCAL_SOURCE_CONTRACT_KEYS = frozenset(
    {
        "document_id",
        "extraction_sha256",
        "source_file",
        "document_family",
        "language",
        "doc_type",
        "manufacturer",
        "product_model",
    }
)
_DOCUMENT_LOCAL_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_DOCUMENT_LOCAL_IDENTITY_FIELDS = (
    "document_family",
    "language",
    "doc_type",
    "manufacturer",
    "product_model",
)
# s274 C1: card de callout-MANDATORY (1 máx por chunk, acotada)
MAX_MANDATORY_CALLOUT_CHARS = 600
MANDATORY_CALLOUT_CARD_CLASS = "mandatory_callout"
_CALLOUT_GAP_ALNUM = re.compile(r"[A-Za-z0-9]")
_NON_SUBSTANTIVE_DIAGRAM_CARD = re.compile(
    r"^\[(?:(?:technical|t[eé]cnico)\s+)?(?:wiring\s+)?(?:diagram|diagrama|image|imagen)\b.*:\]$",
    re.IGNORECASE,
)
_SUBSTANTIVE_HEADING_VALUE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|km|m|v(?:dc|ac)?|ma|a|kw|w|"
    r"ohm(?:ios?)?|ω|seg|s|min|h|°c|%|[µu]f|nf|pf)\b",
    re.IGNORECASE,
)


def _has_exact_card_receipts(chunk: dict[str, Any], field: str) -> bool:
    """Revalidate every card in ``field`` against the immutable parent text."""
    content = chunk.get("content")
    cards = chunk.get(field)
    if not isinstance(content, str) or not content or not isinstance(cards, list) or not cards:
        return False
    candidate_id = str(chunk.get("id") or "")
    if not candidate_id or chunk.get("retrieval_lane") not in ALLOWED_LANES:
        return False
    for card in cards:
        if not isinstance(card, dict) or card.get("exact_source_span_validated") is not True:
            return False
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
            return False
    return True


def has_exact_coverage_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate the selector's original source-span receipts."""
    return _has_exact_card_receipts(chunk, "coverage_cards")


def has_exact_served_coverage_receipt(chunk: dict[str, Any]) -> bool:
    """Revalidate the exact spans admitted by optional logical-row serving."""
    if (
        not has_exact_coverage_receipt(chunk)
        or not _has_exact_card_receipts(chunk, "served_coverage_cards")
    ):
        return False
    try:
        expected = _build_served_coverage_cards(chunk)
    except (KeyError, TypeError, ValueError):
        return False
    return chunk.get("served_coverage_cards") == expected


def _has_document_local_authority_identity(chunk: dict[str, Any]) -> bool:
    lineage_id = str(chunk.get("document_revision_lineage_id") or "")
    return (
        bool(lineage_id)
        and lineage_id
        == str(
            chunk.get("document_local_authority_revision_lineage_id") or ""
        )
        and all(
            bool(str(chunk.get(field) or "").strip())
            and str(chunk.get(field) or "")
            == str(chunk.get(f"document_local_authority_{field}") or "")
            for field in _DOCUMENT_LOCAL_IDENTITY_FIELDS
        )
    )


def is_validated_coverage_chunk(chunk: dict[str, Any]) -> bool:
    lane = chunk.get("retrieval_lane")
    lane_validated = (
        lane in {STRUCTURAL_LANE, STRUCTURAL_CASCADE_LANE}
        and chunk.get("structural_neighbor_validated") is True
    ) or (
        lane == TABLE_PREAMBLE_LANE
        and chunk.get("table_preamble_validated") is True
    ) or (
        lane == HYQ_LANE
        and chunk.get("hyq_navigation_validated") is True
    ) or (
        lane == POOL_LANE
        and chunk.get("rerank_pool_coverage_validated") is True
    ) or (
        lane == OBLIGATION_WARNING_LANE
        and chunk.get("obligation_warning_reserve_validated") is True
    ) or (
        lane == DOCUMENT_LOCAL_LANE
        and chunk.get("document_local_coverage_validated") is True
        and chunk.get("document_local_coverage_validation")
        == DOCUMENT_LOCAL_VALIDATION
        and _has_document_local_authority_identity(chunk)
    ) or (
        lane == COMPATIBILITY_LANE
        and chunk.get("compatibility_bundle_validated") is True
    )
    return (
        bool(str(chunk.get("source_file") or "").strip())
        and lane_validated
        and chunk.get("post_rerank_coverage") is True
        and chunk.get("coverage_validated") is True
        # s279 compuerta 2: la fila por-faceta NUNCA estampa
        # ``local_semantic_validated`` (su selección es determinista por ventana,
        # no semántica del selector); su justificación de servido es
        # ``facet_complement_validated`` — solo para el lane document-local.  Off
        # ninguna fila lleva ese campo => rama muerta byte-inerte.
        and (
            chunk.get("local_semantic_validated") is True
            or (
                lane == DOCUMENT_LOCAL_LANE
                and chunk.get("facet_complement_validated") is True
            )
        )
        and has_exact_coverage_receipt(chunk)
    )


def coverage_context_content(
    chunk: dict[str, Any], *, logical_record_expansion: bool | None = None
) -> str:
    """Serve bounded exact excerpts for every validated coverage lane.

    Coverage complements can be long table/UI chunks, so synthesis sees only
    spans independently attested by the lane. This bounds token cost and
    prevents an unrelated tail of the same chunk from influencing the answer.
    The original parent row remains intact for provenance and revalidation.
    """
    content = str(chunk.get("content") or "")
    if not is_validated_coverage_chunk(chunk):
        return content
    expand = (
        chunk.get("retrieval_lane") == DOCUMENT_LOCAL_LANE
        if logical_record_expansion is None
        else logical_record_expansion
    ) or (
        logical_record_expansion is None
        and chunk.get("retrieval_lane") != DOCUMENT_LOCAL_LANE
        and LOGICAL_RECORD_COVERAGE
    )
    cards = (
        chunk.get("served_coverage_cards")
        if expand and has_exact_served_coverage_receipt(chunk)
        else chunk.get("coverage_cards")
    ) or []
    if _mandatory_callout_enabled() and has_exact_mandatory_callout_receipt(chunk):
        # s274 C1: la card de callout vive en campo PROPIO y se sirve con SU flag,
        # independiente de la expansión de fila lógica (fixes desacoplados).
        cards = [*cards, *(chunk.get("mandatory_callout_cards") or [])]
    ranges = sorted((int(card["start"]), int(card["end"])) for card in cards)
    merged: list[list[int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return "\n\n[... otro extracto fuente ...]\n\n".join(
        content[start:end] for start, end in merged
    )


def _expand_logical_table_boundaries(
    content: str, start: int, end: int
) -> tuple[int, int]:
    """Finish an intersected Markdown table row instead of clipping its value.

    Fixed evidence windows are safe for prose but can end halfway through a
    long key/value row.  Serving that partial row makes a selected fact look as
    if it reached synthesis while its value was actually removed.  Expansion
    is allowed only to exact newline boundaries of bounded pipe-table rows;
    prose and oversized records remain byte-identical to their attested span.
    """
    start_line = content.rfind("\n", 0, start) + 1
    start_break = content.find("\n", start)
    start_line_end = len(content) if start_break < 0 else start_break
    end_line = content.rfind("\n", 0, max(start, end - 1)) + 1
    end_break = content.find("\n", end)
    end_line_end = len(content) if end_break < 0 else end_break

    def bounded_table_row(line_start: int, line_end: int) -> bool:
        line = content[line_start:line_end]
        stripped = line.strip()
        return (
            len(line) <= MAX_LOGICAL_TABLE_ROW_CHARS
            and stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 3
        )

    expanded_start = (
        start_line if bounded_table_row(start_line, start_line_end) else start
    )
    expanded_end = (
        end_line_end if bounded_table_row(end_line, end_line_end) else end
    )
    if expanded_end - expanded_start > MAX_EXPANDED_EXCERPT_CHARS:
        return start, end
    return expanded_start, expanded_end


def _markdown_pipe_row_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if (
        not stripped.startswith("|")
        or not stripped.endswith("|")
        or stripped.count("|") < 3
    ):
        return None
    cells = [cell.strip() for cell in stripped[1:-1].split("|")]
    if len(cells) < 2:
        return None
    return cells


def _markdown_pipe_row_kind(line: str) -> str | None:
    cells = _markdown_pipe_row_cells(line)
    if cells is None:
        return None
    if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
        return "separator"
    return "data"


def _document_local_markdown_record_cards(
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return one bounded complete Markdown data row or fail closed.

    Runtime heuristics cannot prove generic prose or multiline-record
    boundaries.  The document-local v1 contract therefore admits only a
    single-line Markdown pipe row.  A selector span may begin in the adjacent
    separator row, but every card must intersect the same data row and no
    other substantive line.
    """
    content = str(candidate.get("content") or "")
    cards = candidate.get("coverage_cards") or []
    if not content or not cards:
        return []

    line_spans: list[tuple[int, int, str]] = []
    cursor = 0
    for raw_line in content.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        line_spans.append((cursor, cursor + len(line), line))
        cursor += len(raw_line)
    if cursor < len(content) or not line_spans:
        line_spans.append((cursor, len(content), content[cursor:]))

    touched_by_card: list[set[int]] = []
    data_rows: set[int] = set()
    for card in cards:
        start, end = int(card["start"]), int(card["end"])
        touched = {
            index
            for index, (line_start, line_end, _line) in enumerate(line_spans)
            if start < line_end and line_start < end
        }
        touched_by_card.append(touched)
        data_rows.update(
            index
            for index in touched
            if _markdown_pipe_row_kind(line_spans[index][2]) == "data"
        )
    if len(data_rows) != 1:
        return []
    record_index = next(iter(data_rows))
    record_start, record_end, record_line = line_spans[record_index]
    header_cells = (
        _markdown_pipe_row_cells(line_spans[record_index - 2][2])
        if record_index >= 2
        else None
    )
    separator_cells = (
        _markdown_pipe_row_cells(line_spans[record_index - 1][2])
        if record_index >= 1
        else None
    )
    record_cells = _markdown_pipe_row_cells(record_line)
    if (
        not record_line.strip()
        or record_end - record_start > MAX_LOGICAL_TABLE_ROW_CHARS
        or record_end - record_start > MAX_EXPANDED_EXCERPT_CHARS
        or record_index < 2
        or _markdown_pipe_row_kind(line_spans[record_index - 2][2]) != "data"
        or _markdown_pipe_row_kind(line_spans[record_index - 1][2])
        != "separator"
        or header_cells is None
        or separator_cells is None
        or record_cells is None
        or len({len(header_cells), len(separator_cells), len(record_cells)}) != 1
    ):
        return []

    for card, touched in zip(cards, touched_by_card):
        start, end = int(card["start"]), int(card["end"])
        if not (start < record_end and record_start < end):
            return []
        for index in touched:
            if index == record_index or not line_spans[index][2].strip():
                continue
            if (
                index != record_index - 1
                or _markdown_pipe_row_kind(line_spans[index][2]) != "separator"
            ):
                return []

    served_cards: list[dict[str, Any]] = []
    for card in cards:
        served = dict(card)
        served.update(
            {
                "start": record_start,
                "end": record_end,
                "quote": content[record_start:record_end],
                "selector_start": int(card["start"]),
                "selector_end": int(card["end"]),
                "logical_record_expanded": (
                    record_start != int(card["start"])
                    or record_end != int(card["end"])
                ),
                "record_kind": DOCUMENT_LOCAL_RECORD_KIND,
                "record_start": record_start,
                "record_end": record_end,
                "complete_record_validated": True,
                "exact_source_span_validated": True,
            }
        )
        served_cards.append(served)
    return served_cards


def _mandatory_callout_enabled() -> bool:
    """Flag estricto default-off, releído en runtime (patrón contract_enabled)."""
    from ..config import _strict_on_off

    return _strict_on_off("COVERAGE_MANDATORY_CALLOUT")


def _prose_source_card_enabled() -> bool:
    """Flag estricto default-off, releído en runtime (patrón contract_enabled)."""
    from ..config import _strict_on_off

    return _strict_on_off("PROSE_SOURCE_CARD")


def _document_local_prose_served_cards(
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    """s278 §4: serving de la clase ``prose_source_card`` — o receipt completo o nada.

    Solo se llama cuando la clase de fila ``markdown_pipe_row_v1`` no es
    derivable y el flag está on.  La attestation completa de la card (document
    +extraction+source+chunk+content-hash+quote-hash+bounds, oración completa
    verbatim) se revalida vía ``has_exact_prose_source_card_receipt``; si NO
    revalida devuelve ``[]`` y la fila no se sirve (fail-closed).  Igual que la
    fila markdown, el span servido ES el record completo
    (``record_start``/``record_end`` = bounds exactos de la card).  Import
    function-local por diseño (aislamiento del closure de coverage_c1_v1).
    """
    from .document_local_coverage import has_exact_prose_source_card_receipt

    if not has_exact_prose_source_card_receipt(candidate):
        return []
    served_cards: list[dict[str, Any]] = []
    for card in candidate.get("prose_source_cards") or []:
        served = dict(card)
        served.update(
            {
                "record_start": int(card["start"]),
                "record_end": int(card["end"]),
            }
        )
        served_cards.append(served)
    return served_cards


def _document_local_prose_class_ok(
    candidate: dict[str, Any], served_cards: list[dict[str, Any]]
) -> bool:
    """s278 §4: gate de clase para cards de prosa servidas por el lane
    document-local — flag releído at-call-time + receipt completo de la card
    contra el padre inmutable + framing de record exacto en cada card."""
    if not served_cards or not _prose_source_card_enabled():
        return False
    from .document_local_coverage import (
        PROSE_SOURCE_CARD_CLASS,
        PROSE_SOURCE_CARD_KIND,
        has_exact_prose_source_card_receipt,
    )

    return has_exact_prose_source_card_receipt(candidate) and all(
        card.get("record_kind") == PROSE_SOURCE_CARD_KIND
        and card.get("card_class") == PROSE_SOURCE_CARD_CLASS
        and card.get("sentence_complete_validated") is True
        and card.get("exact_source_span_validated") is True
        and card.get("record_start") == card.get("start")
        and card.get("record_end") == card.get("end")
        for card in served_cards
    )


def _mandatory_callout_card(
    candidate: dict[str, Any], served_cards: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """s274 C1: UNA card acotada para el bloque de callout-MANDATORY que quedó FUERA
    de los spans servidos. Oraciones con gatillo del léxico cerrado (mp_lexicon) que
    no solapan ningún span servido; contiguas se mergean cuando el hueco no contiene
    alfanuméricos (``\\n>\\n`` de blockquote); se sirve el PRIMER grupo que quepa en
    ≤600 chars (un grupo mayor se omite entero — conservador, jamás se recorta a
    media oración). La card NO hereda la validación semántica del selector
    (``local_semantic_validated: False`` explícito — dúo Sol-M4)."""
    content = str(candidate.get("content") or "")
    candidate_id = str(candidate.get("id") or "")
    if not content or not candidate_id:
        return None
    covered = sorted(
        (int(card["start"]), int(card["end"])) for card in served_cards
    )

    def overlaps(start: int, end: int) -> bool:
        return any(start < c_end and c_start < end for c_start, c_end in covered)

    groups: list[list[int]] = []
    for s_start, s_end in sentence_spans(content):
        if overlaps(s_start, s_end):
            continue
        if not mandatory_triggers(content[s_start:s_end]):
            continue
        if groups and not _CALLOUT_GAP_ALNUM.search(content[groups[-1][1]:s_start]):
            groups[-1][1] = s_end
        else:
            groups.append([s_start, s_end])
    for start, end in groups:
        if end - start > MAX_MANDATORY_CALLOUT_CHARS:
            continue
        return {
            "candidate_id": candidate_id,
            "card_class": MANDATORY_CALLOUT_CARD_CLASS,
            "mandatory_callout": True,
            "start": start,
            "end": end,
            "quote": content[start:end],
            "selector_start": start,
            "selector_end": end,
            "logical_record_expanded": False,
            "local_semantic_validated": False,
            "exact_source_span_validated": True,
        }
    return None


def _build_served_coverage_cards(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive separately receipted serving spans from validated selector cards."""
    if candidate.get("retrieval_lane") == DOCUMENT_LOCAL_LANE:
        served = _document_local_markdown_record_cards(candidate)
        # s278 §4: la clase de PROSA es COMPLEMENTARIA — solo cuando la fila
        # markdown no es derivable y con el flag on (off => byte-inerte).
        if served or not _prose_source_card_enabled():
            return served
        return _document_local_prose_served_cards(candidate)
    content = str(candidate.get("content") or "")
    served_cards = []
    for card in candidate.get("coverage_cards") or []:
        original_start = int(card["start"])
        original_end = int(card["end"])
        start, end = _expand_logical_table_boundaries(
            content, original_start, original_end
        )
        served = dict(card)
        served.update(
            {
                "start": start,
                "end": end,
                "quote": content[start:end],
                "selector_start": original_start,
                "selector_end": original_end,
                "logical_record_expanded": (
                    start != original_start or end != original_end
                ),
                "exact_source_span_validated": True,
            }
        )
        served_cards.append(served)
    return served_cards


def _build_mandatory_callout_cards(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """s274 C1: derivación determinista del campo PROPIO ``mandatory_callout_cards``
    (0 o 1 card) a partir de los spans servidos — separada de
    ``_build_served_coverage_cards`` para que la revalidación v3 y los consumidores
    de ``served_coverage_cards`` queden byte-intactos."""
    served_cards = _build_served_coverage_cards(candidate)
    if not served_cards:
        return []
    callout = _mandatory_callout_card(candidate, served_cards)
    return [callout] if callout is not None else []


def has_exact_mandatory_callout_receipt(chunk: dict[str, Any]) -> bool:
    """Receipt propio de la card de callout: spans exactos contra el padre inmutable
    + igualdad con la re-derivación determinista (mismo patrón que
    ``has_exact_served_coverage_receipt``)."""
    if not _has_exact_card_receipts(chunk, "mandatory_callout_cards"):
        return False
    try:
        expected = _build_mandatory_callout_cards(chunk)
    except (KeyError, TypeError, ValueError):
        return False
    return chunk.get("mandatory_callout_cards") == expected


def _has_substantive_coverage_card(candidate: dict[str, Any]) -> bool:
    """Reject title/placeholder-only cards that add no field-support fact."""
    for card in candidate.get("coverage_cards") or []:
        quote = str(card.get("quote") or "").strip()
        lines = [line.strip() for line in quote.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 and (
            (
                lines[0].startswith("#")
                and not candidate.get("structured_numeric_claims")
                and not _SUBSTANTIVE_HEADING_VALUE.search(lines[0])
            )
            or _NON_SUBSTANTIVE_DIAGRAM_CARD.fullmatch(lines[0])
        ):
            continue
        return True
    return False


def _attest(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if not candidate.get("source_file") or not has_exact_coverage_receipt(candidate):
        return None
    lane = candidate["retrieval_lane"]
    if (
        lane in {STRUCTURAL_LANE, STRUCTURAL_CASCADE_LANE}
        and candidate.get("structural_neighbor_validated") is not True
    ):
        return None
    if (
        lane == TABLE_PREAMBLE_LANE
        and candidate.get("table_preamble_validated") is not True
    ):
        return None
    if lane == HYQ_LANE and candidate.get("hyq_navigation_validated") is not True:
        return None
    if lane == POOL_LANE and candidate.get("rerank_pool_coverage_validated") is not True:
        return None
    if (
        lane == OBLIGATION_WARNING_LANE
        and candidate.get("obligation_warning_reserve_validated") is not True
    ):
        return None
    if lane == DOCUMENT_LOCAL_LANE:
        # s278 §4: chunk vs autoridad (documents) — la comparación de blob es
        # la ÚNICA canónica declarada (import function-local por aislamiento).
        from .document_local_coverage import blob_identity_match

        if (
            candidate.get("document_local_coverage_validated") is not True
            or candidate.get("document_local_coverage_validation")
            != DOCUMENT_LOCAL_VALIDATION
            or candidate.get("duplicate_of") is not None
            or str(candidate.get("document_id") or "")
            != str(candidate.get("document_local_authority_document_id") or "")
            or str(candidate.get("extraction_sha256") or "").casefold()
            != str(
                candidate.get("document_local_authority_extraction_sha256") or ""
            ).casefold()
            or not blob_identity_match(
                str(candidate.get("document_local_authority_source_file") or ""),
                str(candidate.get("source_file") or ""),
            )
            or not _has_document_local_authority_identity(candidate)
        ):
            return None
    if lane == COMPATIBILITY_LANE and candidate.get("compatibility_bundle_validated") is not True:
        return None
    attested = dict(candidate)
    attested["served_coverage_cards"] = _build_served_coverage_cards(candidate)
    if not has_exact_served_coverage_receipt(attested):
        return None
    document_local_prose_class = False
    if lane == DOCUMENT_LOCAL_LANE:
        served_cards = attested["served_coverage_cards"]
        pipe_class = bool(served_cards) and all(
            card.get("record_kind") == DOCUMENT_LOCAL_RECORD_KIND
            and card.get("complete_record_validated") is True
            and card.get("record_start") == card.get("start")
            and card.get("record_end") == card.get("end")
            for card in served_cards
        )
        # s278 §4: segunda clase admitida (prosa oración-completa), jamás
        # mezclada con la clase de fila; sin flag o sin receipt => no-servir.
        document_local_prose_class = not pipe_class and _document_local_prose_class_ok(
            candidate, served_cards
        )
        if not pipe_class and not document_local_prose_class:
            return None
        if pipe_class:
            # dúo r2 (Fable#4): una fila servida como clase markdown no debe
            # arrastrar un campo de prosa residual (framing engañoso).
            attested.pop("prose_source_cards", None)
    if _mandatory_callout_enabled():
        # s274 C1: campo propio, 0-1 card, receipt propio; en fallo → sin card
        # (fail-open conservador, la vista queda como v3).
        callouts = _build_mandatory_callout_cards(attested)
        if callouts:
            attested["mandatory_callout_cards"] = callouts
            if not has_exact_mandatory_callout_receipt(attested):
                attested.pop("mandatory_callout_cards", None)
    attested.update(
        {
            "coverage_validated": True,
            "post_rerank_coverage": True,
            "post_rerank_coverage_contract": (
                DOCUMENT_LOCAL_PROSE_CONTRACT
                if document_local_prose_class
                else "exact_source_bounded_markdown_pipe_row_v1"
                if lane == DOCUMENT_LOCAL_LANE
                else "exact_source_span_with_bounded_logical_record_receipt_v2"
            ),
        }
    )
    return attested


def append_validated_coverage(
    reranked: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Append at most four unique attestations; never touch the reranked prefix."""
    if not candidates:
        return reranked
    compatibility_groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        if candidate.get("retrieval_lane") == COMPATIBILITY_LANE:
            bundle_id = str(candidate.get("compatibility_bundle_id") or "")
            compatibility_groups.setdefault(bundle_id, []).append(candidate)
    valid_compatibility_ids = {
        bundle_id
        for bundle_id, rows in compatibility_groups.items()
        if bundle_id and validate_compatibility_bundle(rows)
    }
    # A relational bundle is atomic. Reject ambiguity, a parent already in the
    # protected prefix, or any state in which fewer than all three rows could
    # reach the generator. Put the one valid bundle first so other optional
    # lanes cannot consume its three-row reservation.
    if len(valid_compatibility_ids) == 1:
        valid_bundle_id = next(iter(valid_compatibility_ids))
        valid_bundle = compatibility_groups[valid_bundle_id]
        protected_ids = {str(base.get("id") or "") for base in reranked}
        if any(
            str(row.get("id") or "") in protected_ids for row in valid_bundle
        ):
            valid_compatibility_ids = set()
            valid_bundle = []
    else:
        valid_bundle = []
        valid_compatibility_ids = set()
    other_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("retrieval_lane") != COMPATIBILITY_LANE
    ]
    candidates = [*valid_bundle, *other_candidates]
    if not candidates:
        return reranked
    output = list(reranked)
    seen = {str(row.get("id") or "") for row in reranked}
    appended_by_lane: dict[str, int] = {}
    for candidate in candidates:
        attested = _attest(candidate)
        candidate_id = str((attested or {}).get("id") or "")
        lane = str((attested or {}).get("retrieval_lane") or "")
        if (
            not attested
            or candidate_id in seen
            or appended_by_lane.get(lane, 0)
            >= MAX_APPENDED_BY_LANE.get(lane, MAX_APPENDED_PER_LANE)
        ):
            continue
        attested["post_rerank_coverage_rank"] = len(output) - len(reranked) + 1
        output.append(attested)
        seen.add(candidate_id)
        appended_by_lane[lane] = appended_by_lane.get(lane, 0) + 1
        if len(output) - len(reranked) == MAX_APPENDED:
            break
    return output if len(output) > len(reranked) else reranked


def _append_obligation_warning_reserve(
    served: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    retrieval_pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """s278 §3: anexa a lo sumo UNA fila-warning con presupuesto PROPIO.

    No compite con los 4 huecos de ``append_validated_coverage`` ni toca lo ya
    servido (la vista servida completa actúa aquí de prefijo protegido).  Antes
    de reservar revalida el chunk EXACTO — mismo ``id`` y mismo ``content``
    presentes en el pool pagado; cualquier discrepancia => no-op (fail-open).
    """
    pool_by_id = {str(row.get("id") or ""): row for row in retrieval_pool}
    served_ids = {str(row.get("id") or "") for row in served}
    for candidate in candidates[:OBLIGATION_WARNING_RESERVE_BUDGET]:
        if candidate.get("retrieval_lane") != OBLIGATION_WARNING_LANE:
            continue
        attested = _attest(candidate)
        if not attested:
            continue
        candidate_id = str(attested.get("id") or "")
        exact = pool_by_id.get(candidate_id)
        if (
            not candidate_id
            or candidate_id in served_ids
            or exact is None
            or str(exact.get("content") or "")
            != str(attested.get("content") or "")
        ):
            continue
        attested["obligation_warning_reserve_rank"] = 1
        return [*served, attested]
    return served


# ───────── s279 compuerta 2: vía complementaria por-faceta (§2 + A2..A10) ─────────
# TODA gated por DOCUMENT_LOCAL_SELECTION_V2 (off => byte-inerte).  Corre DESPUÉS
# de _append_obligation_warning_reserve (A8, ve la vista final, reserve incluida),
# con presupuesto PROPIO FACET_COMPLEMENT_BUDGET fuera de MAX_APPENDED.  Cambia
# SELECCIÓN, no clases: la fila sirve por las clases existentes (pipe-row si
# derivable; si no, prose_source_card con todos sus checks).  NUNCA estampa
# ``local_semantic_validated``: su justificación de servido es determinista
# (regla de ventana, no semántica) => ``facet_complement_validated``.


def _facet_selection_v2_enabled() -> bool:
    """s279 §0: flag profile-owned default-off, releído at-call-time (patrón
    contract_enabled).  Off ⇒ la vía complementaria por-faceta ni se alcanza."""
    from ..config import _strict_on_off

    return _strict_on_off("DOCUMENT_LOCAL_SELECTION_V2")


def _facet_stable_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _facet_sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _facet_min_span(folded_quote: str, hit_terms: list[str]) -> int:
    """Min char span (folded space) que contiene >=1 ocurrencia de CADA hit —
    la clave de densidad (asc, A4).  Determinista; 0 si algún hit no aparece."""
    from collections import Counter

    hit_set = set(hit_terms)
    if not hit_set:
        return 0
    occurrences: list[tuple[int, int, str]] = []
    for term in hit_set:
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        for match in re.finditer(pattern, folded_quote):
            occurrences.append((match.start(), match.end(), term))
    if {term for _, _, term in occurrences} != hit_set:
        return 0
    occurrences.sort()
    need = len(hit_set)
    counts: Counter[str] = Counter()
    have = 0
    left = 0
    best: int | None = None
    for right in range(len(occurrences)):
        if counts[occurrences[right][2]] == 0:
            have += 1
        counts[occurrences[right][2]] += 1
        while have == need:
            span_start = occurrences[left][0]
            span_end = max(end for _, end, _ in occurrences[left : right + 1])
            span = span_end - span_start
            if best is None or span < best:
                best = span
            counts[occurrences[left][2]] -= 1
            if counts[occurrences[left][2]] == 0:
                have -= 1
            left += 1
    return best if best is not None else 0


def _facet_best_window(
    content: Any, group_terms: list[str]
) -> dict[str, Any] | None:
    """Mejor ventana de 360 chars de ``content`` para una need-group (A4).

    Reusa la regla de ventana del pool selector (``_exact_windows`` +
    ``_tokens``): elige la ventana que MAXIMIZA términos-distintos del grupo
    (``terms_hit``), desempatando por densidad mínima (span que contiene los
    hits, asc) y luego por ``start`` más temprano (determinismo).  None si no
    hay ningún hit.
    """
    group_set = set(group_terms)
    if not group_set:
        return None
    text = content if isinstance(content, str) else str(content or "")
    if not text:
        return None
    best: tuple[tuple[int, int, int], dict[str, Any]] | None = None
    for start, end, quote in _facet_exact_windows(text):
        hits = group_set & set(_facet_tokens(quote))
        if not hits:
            continue
        density = _facet_min_span(_facet_fold(quote), sorted(hits))
        key = (-len(hits), density, start)
        if best is None or key < best[0]:
            best = (
                key,
                {
                    "terms_hit": len(hits),
                    "density": density,
                    "start": start,
                    "end": end,
                    "hits": sorted(hits),
                },
            )
    return best[1] if best is not None else None


def _facet_served_row_text(row: dict[str, Any]) -> str:
    """Texto que la fila entrega al generador (la vista SERVIDA): excerpt
    acotado para filas de cobertura, contenido completo para el prefijo."""
    return coverage_context_content(row)


def _facet_need_group_grade(
    served: list[dict[str, Any]], group_terms: list[str]
) -> int:
    """GRADO entero (A4): máx términos-distintos del grupo cubiertos por ALGUNA
    fila servida bajo la regla de ventana (0..len(group))."""
    grade = 0
    for row in served:
        window = _facet_best_window(_facet_served_row_text(row), group_terms)
        if window is not None and window["terms_hit"] > grade:
            grade = window["terms_hit"]
    return grade


def _facet_served_view_sha256(served: list[dict[str, Any]]) -> str:
    """A3: sha256 del CONJUNTO de la vista servida — ids ordenados + content-sha
    por fila (orden-independiente).  Omitir o mutar una fila cambia el sha."""
    rows = sorted(
        (
            str(row.get("id") or ""),
            _facet_sha256_text(str(row.get("content") or "")),
        )
        for row in served
    )
    return _facet_stable_sha256(rows)


def _facet_chunk_index(candidate: dict[str, Any]) -> int:
    value = candidate.get("chunk_index")
    if isinstance(value, bool) or not isinstance(value, int):
        value = candidate.get("document_local_candidate_rank")
    if isinstance(value, bool) or not isinstance(value, int):
        return 1 << 30
    return value


def _facet_gate_and_select(
    served: list[dict[str, Any]],
    reranked: list[dict[str, Any]],
    plan: dict[str, Any],
    candidate_pool: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, list[int], list[list[str]]]:
    """A7 gate + A4 orden pre-registrado TOTAL (cero libertad).

    Gate A7: >=1 need-group NO cubierta (grado < N_FACET) con >=N_FACET términos
    EN el grupo — grupos de 1-2 términos EXCLUIDOS del gate y del orden.  Orden
    entre grupos: grado asc -> índice asc.  Un candidato multi-grupo se asigna al
    PRIMER grupo de ese orden para el que es elegible (ventana >=N_FACET términos
    distintos).  Dentro del grupo: terms_hit desc -> densidad asc -> chunk_index
    asc -> source_file asc -> id asc.
    """
    need_groups = [list(group) for group in plan.get("need_groups") or []]
    grades = [_facet_need_group_grade(served, group) for group in need_groups]
    gate_indices = [
        index
        for index, group in enumerate(need_groups)
        if len(group) >= N_FACET and grades[index] < N_FACET
    ]
    if not gate_indices:
        return None, "skipped_no_uncovered_group", grades, need_groups
    ordered = sorted(gate_indices, key=lambda index: (grades[index], index))
    served_ids = {str(row.get("id") or "") for row in served}
    reranked_ids = {str(row.get("id") or "") for row in reranked}
    assigned: dict[int, list[tuple[dict[str, Any], dict[str, Any]]]] = {
        index: [] for index in ordered
    }
    for candidate in candidate_pool:
        candidate_id = str(candidate.get("id") or "")
        if not candidate_id or candidate_id in served_ids or candidate_id in reranked_ids:
            continue
        content = str(candidate.get("content") or "")
        for index in ordered:
            window = _facet_best_window(content, need_groups[index])
            if window is not None and window["terms_hit"] >= N_FACET:
                assigned[index].append((candidate, window))
                break
    for index in ordered:
        bucket = assigned[index]
        if not bucket:
            continue
        bucket.sort(
            key=lambda pair: (
                -pair[1]["terms_hit"],
                pair[1]["density"],
                _facet_chunk_index(pair[0]),
                str(pair[0].get("source_file") or ""),
                str(pair[0].get("id") or ""),
            )
        )
        candidate, window = bucket[0]
        return (
            {
                "group_index": index,
                "group_terms": list(need_groups[index]),
                "candidate": candidate,
                "window": window,
            },
            "ok",
            grades,
            need_groups,
        )
    return None, "no_eligible_candidate", grades, need_groups


def _facet_complement_row(
    selection: dict[str, Any],
    served: list[dict[str, Any]],
    *,
    plan_sha256: str,
) -> dict[str, Any] | None:
    """Construye la fila por-faceta y la atesta por las CLASES EXISTENTES (A/§2).

    El candidato es una fila cruda del pool document-local (identidad de autoridad
    ya estampada por el RPC).  La evidencia servida es la ventana ganadora; el
    servido lo resuelve _attest (pipe-row si derivable; si no, prose_source_card
    con su flag+receipt).  Se estampa la attestation re-derivable (A3) y NUNCA
    ``local_semantic_validated``.
    """
    candidate = selection["candidate"]
    window = selection["window"]
    candidate_id = str(candidate.get("id") or "")
    content = str(candidate.get("content") or "")
    start, end = int(window["start"]), int(window["end"])
    if not candidate_id or not content or not 0 <= start < end <= len(content):
        return None
    quote = content[start:end]
    row = dict(candidate)
    for key in list(row):
        if key.startswith("rerank_pool_"):
            row.pop(key)
    row.pop("local_semantic_validated", None)
    row.pop("prose_source_cards", None)
    row.update(
        {
            "retrieval_lane": DOCUMENT_LOCAL_LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": DOCUMENT_LOCAL_VALIDATION,
            "facet_complement_validated": True,
            "coverage_cards": [
                {
                    "candidate_id": candidate_id,
                    "candidate_rank": 1,
                    "start": start,
                    "end": end,
                    "quote": quote,
                    "facet": "facet_complement",
                    "exact_source_span_validated": True,
                }
            ],
        }
    )
    # Serving por CLASES EXISTENTES: prosa SOLO si la fila markdown no es
    # derivable y su flag+receipt lo permiten (byte-igual al path existente).
    if not _document_local_markdown_record_cards(row) and _prose_source_card_enabled():
        from .document_local_coverage import build_prose_source_cards

        prose_cards = build_prose_source_cards(row)
        if prose_cards:
            row["prose_source_cards"] = prose_cards
    attested = _attest(row)
    if attested is None:
        return None
    attested.update(
        {
            "facet_complement_validated": True,
            "facet_complement_plan_sha256": plan_sha256,
            "facet_complement_need_group_index": selection["group_index"],
            "facet_complement_need_group_terms": list(selection["group_terms"]),
            "facet_complement_window_bounds": [start, end],
            "facet_complement_quote_sha256": _facet_sha256_text(quote),
            "facet_complement_served_view_sha256": _facet_served_view_sha256(served),
        }
    )
    return attested


def _attest_facet_complement(
    row: dict[str, Any], served: list[dict[str, Any]], plan: dict[str, Any]
) -> bool:
    """A3: re-verifica la attestation por-faceta contra la vista compuesta REAL.

    Cada campo estampado es portante: ``plan_sha256`` y (``need_group_index``,
    ``need_group_terms``) se atan al plan real; ``served_view_sha256`` exige
    igualdad EXACTA del conjunto de la vista (ids + contenidos); ``window_bounds``
    + ``quote_sha256`` re-corren la regla de ventana sobre el candidato (mismos
    bounds, >=N_FACET términos, mismo quote); y la need-group DEBE seguir sin
    cubrir.  Cualquier mismatch => False (fail-closed).
    """
    if row.get("facet_complement_validated") is not True:
        return False
    group_index = row.get("facet_complement_need_group_index")
    group_terms = row.get("facet_complement_need_group_terms")
    bounds = row.get("facet_complement_window_bounds")
    if (
        isinstance(group_index, bool)
        or not isinstance(group_index, int)
        or not isinstance(group_terms, list)
        or not group_terms
        or any(not isinstance(term, str) or not term for term in group_terms)
        or not isinstance(bounds, list)
        or len(bounds) != 2
        or any(isinstance(bound, bool) or not isinstance(bound, int) for bound in bounds)
    ):
        return False
    # Plan-binding: plan_sha256 + (índice, términos) coinciden con el plan real.
    need_groups = list(plan.get("need_groups") or [])
    if (
        row.get("facet_complement_plan_sha256") != str(plan.get("sha256") or "")
        or not 0 <= group_index < len(need_groups)
        or list(need_groups[group_index]) != list(group_terms)
    ):
        return False
    if row.get("facet_complement_served_view_sha256") != _facet_served_view_sha256(
        served
    ):
        return False
    if _facet_need_group_grade(served, group_terms) >= N_FACET:
        return False
    content = str(row.get("content") or "")
    start, end = int(bounds[0]), int(bounds[1])
    if not 0 <= start < end <= len(content):
        return False
    window = _facet_best_window(content, group_terms)
    if (
        window is None
        or window["terms_hit"] < N_FACET
        or [window["start"], window["end"]] != [start, end]
        or row.get("facet_complement_quote_sha256")
        != _facet_sha256_text(content[start:end])
    ):
        return False
    return True


def _resolve_facet_complement_source(
    query: str,
    reranked: list[dict[str, Any]],
    served: list[dict[str, Any]],
    cache: dict[str, Any],
) -> dict[str, Any]:
    """A2/A9: origen del candidate-pool de la vía.

    (a) lane CORRIÓ en esta composición -> reusa su pool cacheado ($0);
    (b) lane SALTADO -> re-deriva anchors LOCALMENTE (mismas funciones puras) +
        el plan (v5 pura), y SOLO si el gate A7 puede pasar hace UNA llamada RPC
        propia GET-only.  ``facet_plan_rederived: true`` en ese path (A2).
    Enum A9: own | reused | skipped_no_uncovered_group | skipped_no_plan |
    skipped_scope_overflow | skipped_no_anchors.
    """
    if cache.get("candidates") is not None:
        return {
            "plan": cache.get("plan"),
            "candidate_pool": cache["candidates"],
            "facet_fetch": "reused",
            "plan_rederived": False,
        }
    from .document_local_coverage import (
        _anchor_scopes,
        build_document_local_query_plan,
        fetch_document_local_candidates,
    )

    source_contract_anchors, overflow = _document_local_source_contract_rows(query)
    if overflow:
        return {"facet_fetch": "skipped_scope_overflow", "plan_rederived": True}
    structural_anchors = [
        row
        for row in served[len(reranked) :]
        if row.get("retrieval_lane") == STRUCTURAL_LANE
    ]
    if not source_contract_anchors and not structural_anchors:
        return {"facet_fetch": "skipped_no_anchors", "plan_rederived": True}
    anchors = _document_local_anchor_rows(
        reranked, structural_anchors, source_contract_anchors
    )
    if not anchors:
        return {"facet_fetch": "skipped_no_anchors", "plan_rederived": True}
    scopes, scope_reason = _anchor_scopes(anchors)
    if scope_reason != "ok":
        return {
            "facet_fetch": (
                "skipped_scope_overflow"
                if scope_reason == "source_scope_overflow"
                else "skipped_no_anchors"
            ),
            "plan_rederived": True,
        }
    plan = build_document_local_query_plan(query, scopes)
    if plan is None:
        return {"facet_fetch": "skipped_no_plan", "plan_rederived": True}
    # Gate A7 ANTES de fetchear (anti dead-fetch): sin need-group descubierta con
    # >=N_FACET términos EN el grupo no se gasta la llamada RPC propia.
    need_groups = list(plan.get("need_groups") or [])
    grades = [_facet_need_group_grade(served, group) for group in need_groups]
    if not any(
        len(group) >= N_FACET and grades[index] < N_FACET
        for index, group in enumerate(need_groups)
    ):
        return {
            "facet_fetch": "skipped_no_uncovered_group",
            "plan_rederived": True,
            "plan": plan,
        }
    candidates, _authorities, _read_trace = fetch_document_local_candidates(
        query, anchors
    )
    return {
        "plan": plan,
        "candidate_pool": candidates,
        "facet_fetch": "own",
        "plan_rederived": True,
    }


def _append_facet_complement(
    served: list[dict[str, Any]],
    reranked: list[dict[str, Any]],
    *,
    plan: dict[str, Any] | None,
    candidate_pool: list[dict[str, Any]],
    facet_fetch: str | None,
    plan_rederived: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """A8: anexa a lo sumo UNA fila por-faceta con presupuesto PROPIO, tras la
    reserve.  No toca lo ya servido (la vista servida completa es prefijo)."""
    trace: dict[str, Any] = {
        "lane": DOCUMENT_LOCAL_LANE,
        "conduct": "facet_complement",
        "facet_fetch": facet_fetch,
        "facet_plan_rederived": plan_rederived,
        "selected_ids": [],
        "status": facet_fetch,
    }
    if (
        sum(1 for row in served if row.get("facet_complement_validated") is True)
        >= FACET_COMPLEMENT_BUDGET
    ):
        trace["status"] = "facet_budget_consumed"
        return served, trace
    if facet_fetch not in {"own", "reused"} or plan is None:
        return served, trace
    selection, status, grades, _need_groups = _facet_gate_and_select(
        served, reranked, plan, candidate_pool or []
    )
    trace["need_group_grades"] = grades
    if selection is None:
        trace["status"] = status
        return served, trace
    attested = _facet_complement_row(
        selection, served, plan_sha256=str(plan.get("sha256") or "")
    )
    if attested is None or not _attest_facet_complement(attested, served, plan):
        trace["status"] = "facet_attestation_failed"
        return served, trace
    attested["facet_complement_rank"] = 1
    trace.update(
        status="selected",
        selected_ids=[str(attested.get("id") or "")],
        need_group_index=selection["group_index"],
        need_group_terms=list(selection["group_terms"]),
    )
    return [*served, attested], trace


def collect_structural_coverage(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    fetcher=fetch_structural_neighbor_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = yaml.safe_load(STRUCTURAL_CONFIG.read_text(encoding="utf-8"))
    runtime = payload["shadow_runtime"]
    hydrated, candidates, read_trace = fetcher(
        reranked[: payload["max_seeds"]],
        max_gap=payload["max_gap"],
        max_candidates=payload["max_candidates"],
        max_http_requests=runtime["max_http_requests"],
        # Serving gets the maximum budget already allowed by the shadow
        # contract.  The 750 ms sampling budget proved too short in the real
        # HTTP path and caused deterministic false negatives.
        timeout_seconds=STRUCTURAL_SERVING_TIMEOUT_SECONDS,
    )
    selected, selection_trace = select_structural_neighbors(
        query, hydrated, candidates
    )
    # Recheck the identity relationship at the release seam rather than
    # trusting metadata produced by the selector alone.
    seed_identities = {
        (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        for row in hydrated
    }
    validated = [
        row for row in selected
        if (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        in seed_identities
    ]
    return validated, {
        "lane": STRUCTURAL_LANE,
        "status": "selected" if validated else "no_validated_source_span",
        "selected_ids": [str(row["id"]) for row in validated],
        "http_requests": read_trace.get("http_requests", 0),
        "selector_reason": selection_trace.get("reason"),
    }


def collect_table_preamble_closure(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    fetcher=fetch_structural_neighbor_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recover exact table preambles without performing semantic discovery."""
    del query  # relevance is inherited from the protected table seed
    payload = yaml.safe_load(TABLE_PREAMBLE_CONFIG.read_text(encoding="utf-8"))
    if payload.get("schema") != "table_preamble_closure_v3":
        raise RuntimeError("unsupported table preamble closure config")
    bounds = {
        "max_seeds": (1, 20),
        "max_gap": (1, 1),
        "max_candidates": (16, 128),
        "max_preambles": (1, 2),
        "max_http_requests": (2, 12),
    }
    for key, (low, high) in bounds.items():
        value = payload.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not low <= value <= high
        ):
            raise RuntimeError(f"invalid table preamble closure {key}")
    timeout = payload.get("timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 2.0:
        raise RuntimeError("invalid table preamble closure timeout")
    serving = payload.get("serving") or {}
    if serving.get("default_enabled") is not False or serving.get("fail_open") is not True:
        raise RuntimeError("unsafe table preamble serving contract")

    hydrated, candidates, read_trace = fetcher(
        reranked[: payload["max_seeds"]],
        max_gap=payload["max_gap"],
        max_candidates=payload["max_candidates"],
        max_http_requests=payload["max_http_requests"],
        timeout_seconds=float(timeout),
    )
    selected, selection_trace = select_table_preambles(
        hydrated,
        candidates,
        max_preambles=payload["max_preambles"],
    )
    seed_identities = {
        (
            str(row.get("document_id") or ""),
            str(row.get("extraction_sha256") or ""),
        )
        for row in hydrated
    }
    validated = []
    seen_exact_preambles: set[str] = set()
    duplicate_preambles = 0
    for row in selected:
        identity = (
            str(row.get("document_id") or ""),
            str(row.get("extraction_sha256") or ""),
        )
        cards = row.get("coverage_cards") or []
        quote = str(cards[0].get("quote") or "") if len(cards) == 1 else ""
        if identity not in seed_identities or not quote:
            continue
        if quote in seen_exact_preambles:
            duplicate_preambles += 1
            continue
        seen_exact_preambles.add(quote)
        validated.append(row)
    return validated, {
        "lane": TABLE_PREAMBLE_LANE,
        "status": "selected" if validated else "no_exact_table_preamble",
        "selected_ids": [str(row["id"]) for row in validated],
        "http_requests": read_trace.get("http_requests", 0),
        "cross_table_rejected_rows": selection_trace.get(
            "cross_table_rejected_rows", 0
        ),
        "duplicate_exact_preambles_rejected": duplicate_preambles,
        "selector_status": selection_trace.get("status"),
    }


def collect_cascaded_structural_coverage(
    query: str,
    pool_seeds: list[dict[str, Any]],
    *,
    fetcher=fetch_structural_neighbor_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one bounded document-local hop from already selected pool evidence."""
    if not pool_seeds:
        return [], {
            "lane": STRUCTURAL_CASCADE_LANE,
            "status": "no_pool_seed",
            "selected_ids": [],
            "http_requests": 0,
        }
    payload = yaml.safe_load(
        STRUCTURAL_CASCADE_CONFIG.read_text(encoding="utf-8")
    )
    runtime = payload["shadow_runtime"]
    hydrated, candidates, read_trace = fetcher(
        pool_seeds[: payload["max_seeds"]],
        max_gap=payload["max_gap"],
        max_candidates=payload["max_candidates"],
        max_http_requests=runtime["max_http_requests"],
        timeout_seconds=STRUCTURAL_SERVING_TIMEOUT_SECONDS,
    )
    max_page_gap = payload.get("max_page_gap")
    if (
        isinstance(max_page_gap, bool)
        or not isinstance(max_page_gap, int)
        or not 0 <= max_page_gap <= 2
    ):
        raise RuntimeError("invalid structural cascade max_page_gap")
    seed_pages: dict[tuple[str, str], list[int]] = {}
    for seed in hydrated:
        identity = (
            str(seed.get("document_id") or ""),
            str(seed.get("extraction_sha256") or ""),
        )
        page = seed.get("page_number")
        if (
            identity[0]
            and identity[1]
            and isinstance(page, int)
            and not isinstance(page, bool)
        ):
            seed_pages.setdefault(identity, []).append(page)
    page_local_candidates = []
    for candidate in candidates:
        identity = (
            str(candidate.get("document_id") or ""),
            str(candidate.get("extraction_sha256") or ""),
        )
        page = candidate.get("page_number")
        pages = seed_pages.get(identity) or []
        if (
            isinstance(page, int)
            and not isinstance(page, bool)
            and pages
            and min(abs(page - seed_page) for seed_page in pages) <= max_page_gap
        ):
            page_local_candidates.append(candidate)
    selected, selection_trace = select_structural_neighbors(
        query,
        hydrated,
        page_local_candidates,
        config_path=STRUCTURAL_CASCADE_CONFIG,
        query_facets_path=CASCADED_QUERY_FACETS,
        evidence_match_config_path=CASCADED_EVIDENCE_CONFIG,
        evidence_card_config_path=CASCADED_EVIDENCE_CONFIG,
        query_aligned_cards=True,
        lane=STRUCTURAL_CASCADE_LANE,
        validation=STRUCTURAL_CASCADE_VALIDATION,
    )
    substantive = [row for row in selected if _has_substantive_coverage_card(row)]
    non_substantive_rejected = len(selected) - len(substantive)
    seed_identities = {
        (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        for row in hydrated
    }
    validated = [
        row for row in substantive
        if (str(row.get("document_id") or ""), str(row.get("extraction_sha256") or ""))
        in seed_identities
    ]
    return validated, {
        "lane": STRUCTURAL_CASCADE_LANE,
        "status": "selected" if validated else "no_validated_source_span",
        "selected_ids": [str(row["id"]) for row in validated],
        "http_requests": read_trace.get("http_requests", 0),
        "page_local_candidates": len(page_local_candidates),
        "non_substantive_selected_rejected": non_substantive_rejected,
        "selector_reason": selection_trace.get("reason"),
    }


def _document_local_source_contract_rows(
    query: str,
) -> tuple[list[dict[str, Any]], bool]:
    """Resolve query identity to versioned exact-blob source hints.

    The repository catalog supplies the governed product-to-document mapping;
    this small registry supplies the corresponding active blob identity.  Both
    are hints only: the atomic RPC independently revalidates the live lineage,
    active revision and exact blob before any chunk can be selected.
    """

    payload = yaml.safe_load(
        DOCUMENT_LOCAL_SOURCE_CONTRACT_CONFIG.read_text(encoding="utf-8")
    )
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "max_scopes_per_query", "contracts"}
        or payload.get("schema") != "document_local_source_contracts_v1"
        or payload.get("max_scopes_per_query") != DOCUMENT_LOCAL_ANCHOR_LIMIT
        or not isinstance(payload.get("contracts"), list)
        or len(payload["contracts"]) > 256
    ):
        raise RuntimeError("invalid document-local source-contract registry")

    by_scope: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in payload["contracts"]:
        if (
            not isinstance(raw, dict)
            or set(raw) != _DOCUMENT_LOCAL_SOURCE_CONTRACT_KEYS
        ):
            raise RuntimeError("invalid document-local source-contract row")
        row = {key: str(raw.get(key) or "").strip() for key in raw}
        document_id = row["document_id"]
        extraction_sha256 = row["extraction_sha256"].casefold()
        source_file = row["source_file"]
        if (
            _DOCUMENT_LOCAL_UUID.fullmatch(document_id) is None
            or re.fullmatch(r"[0-9a-f]{64}", extraction_sha256) is None
            or any(not row[key] for key in _DOCUMENT_LOCAL_SOURCE_CONTRACT_KEYS)
            or row["language"].casefold() != "es"
        ):
            raise RuntimeError("invalid document-local source-contract identity")
        scope = (document_id, source_file)
        if scope in by_scope:
            raise RuntimeError("duplicate document-local source-contract scope")
        row["extraction_sha256"] = extraction_sha256
        by_scope[scope] = row

    scope_owners = governed_catalog_scope_owners()
    if set(by_scope) - set(scope_owners):
        raise RuntimeError("orphan document-local source-contract scope")
    governed_scopes_by_product: dict[str, set[tuple[str, str]]] = {}
    for scope in by_scope:
        for product_id in scope_owners[scope]:
            governed_scopes_by_product.setdefault(product_id, set()).add(scope)
    if any(
        len(scopes) > DOCUMENT_LOCAL_ANCHOR_LIMIT
        for scopes in governed_scopes_by_product.values()
    ):
        raise RuntimeError("document-local source-contract product overflow")

    resolution = resolve_query(query)
    resolved_documents = resolution.get("resolved_documents") or []
    if not isinstance(resolved_documents, list):
        raise RuntimeError("invalid catalog document resolution")
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for document in resolved_documents:
        if not isinstance(document, dict):
            raise RuntimeError("invalid catalog document scope")
        scope = (
            str(document.get("document_id") or ""),
            str(document.get("source_file") or ""),
        )
        if scope in seen:
            continue
        seen.add(scope)
        contract = by_scope.get(scope)
        if contract is not None:
            selected.append(
                {
                    **contract,
                    "document_local_anchor_route": (
                        DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
                    ),
                }
            )
    overflow = len(selected) > DOCUMENT_LOCAL_ANCHOR_LIMIT
    return ([] if overflow else selected), overflow


def _document_local_anchor_rows(
    reranked: list[dict[str, Any]],
    structural_anchors: list[dict[str, Any]],
    source_contract_anchors: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Choose bounded exact-blob seeds; the RPC remains the authority.

    A governed source contract, when present, is exclusive: silently mixing it
    with a different retrieval scope would weaken the catalog decision.  With
    no contract, protected-prefix scopes come first and served structural
    recoveries may fill remaining slots.  Every row is only a hint; the atomic
    RPC remains the sole lifecycle and exact-blob authority.
    """

    selected: list[dict[str, Any]] = []
    seen_scopes: set[tuple[str, str, str]] = set()
    truncated = False
    source_contract_anchors = source_contract_anchors or []
    routed_rows = (
        ((DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR, source_contract_anchors),)
        if source_contract_anchors
        else (
            (DOCUMENT_LOCAL_PREFIX_ANCHOR, reranked),
            (DOCUMENT_LOCAL_STRUCTURAL_ANCHOR, structural_anchors),
        )
    )
    for route, rows in routed_rows:
        for row in rows:
            document_id = str(row.get("document_id") or "")
            extraction_sha256 = str(row.get("extraction_sha256") or "").casefold()
            source_file = str(row.get("source_file") or "").strip()
            if (
                not document_id
                or re.fullmatch(r"[0-9a-f]{64}", extraction_sha256) is None
                or not source_file
            ):
                continue
            scope = (document_id, extraction_sha256, source_file)
            if scope in seen_scopes:
                continue
            seen_scopes.add(scope)
            if len(selected) >= DOCUMENT_LOCAL_ANCHOR_LIMIT:
                truncated = True
                continue
            anchor = dict(row)
            anchor["document_local_anchor_route"] = route
            selected.append(anchor)
    for anchor in selected:
        anchor["document_local_anchor_scopes_truncated"] = truncated
    return selected


def apply_post_rerank_coverage_with_trace(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    retrieval_pool: list[dict[str, Any]] | None = None,
    enabled: bool | None = None,
    structural_enabled: bool | None = None,
    table_preamble_enabled: bool | None = None,
    hyq_enabled: bool | None = None,
    pool_enabled: bool | None = None,
    document_local_enabled: bool | None = None,
    cascade_enabled: bool | None = None,
    compatibility_enabled: bool | None = None,
    obligation_reserve_enabled: bool | None = None,
    structural_collector: Callable[..., tuple[list[dict], dict]] = collect_structural_coverage,
    table_preamble_collector: Callable[..., tuple[list[dict], dict]] = collect_table_preamble_closure,
    hyq_collector: Callable[..., tuple[list[dict], dict]] = collect_document_scoped_hyq,
    pool_collector: Callable[..., tuple[list[dict], dict]] = select_rerank_pool_coverage,
    document_local_collector: Callable[..., tuple[list[dict], dict]] | None = None,
    cascade_collector: Callable[..., tuple[list[dict], dict]] = collect_cascaded_structural_coverage,
    compatibility_collector: Callable[..., tuple[list[dict], dict]] = collect_compatibility_bundle,
    obligation_reserve_collector: Callable[..., tuple[list[dict], dict]] = select_obligation_warning_reserve,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply enabled lanes independently; every failure is contained."""
    active = POST_RERANK_COVERAGE if enabled is None else enabled
    structural = (
        STRUCTURAL_NEIGHBOR_COVERAGE
        if structural_enabled is None else structural_enabled
    )
    table_preamble = (
        TABLE_PREAMBLE_CLOSURE
        if table_preamble_enabled is None
        else table_preamble_enabled
    )
    hyq = CANONICAL_HYQ_COVERAGE if hyq_enabled is None else hyq_enabled
    pool = RERANK_POOL_COVERAGE if pool_enabled is None else pool_enabled
    document_local = (
        DOCUMENT_LOCAL_COVERAGE
        if document_local_enabled is None
        else document_local_enabled
    )
    if document_local and document_local_collector is None:
        # Function-local by design: coverage_c1_v1 keeps the new default-off
        # implementation outside its loaded/static dependency closure.
        from .document_local_coverage import collect_document_local_coverage

        document_local_collector = collect_document_local_coverage
    compatibility = (
        COMPATIBILITY_BUNDLE_COVERAGE
        if compatibility_enabled is None else compatibility_enabled
    )
    compatibility_applicable = compatibility and is_compatibility_bundle_query(query)
    obligation_reserve = (
        OBLIGATION_WARNING_RESERVE
        if obligation_reserve_enabled is None
        else obligation_reserve_enabled
    )
    # s278 §3: la reserva lee el MISMO pool ya pagado; bajo bundle de
    # compatibilidad (atómico y excluyente) se apaga como el resto de lanes.
    obligation_reserve_applicable = (
        obligation_reserve and bool(retrieval_pool) and not compatibility_applicable
    )
    cascade_requested = (
        STRUCTURAL_CASCADE_COVERAGE
        if cascade_enabled is None else cascade_enabled
    )
    cascade = (
        cascade_requested
        and pool
        and bool(retrieval_pool)
        and not compatibility_applicable
    )
    # s279 compuerta 2: la vía por-faceta es una conducta post-composición gated
    # por su propio flag; puede correr aunque ningún otro lane sirva (re-deriva
    # anchors+plan y, si el gate pasa, hace su propia RPC).  Off => byte-inerte.
    facet_complement_applicable = (
        _facet_selection_v2_enabled() and not compatibility_applicable
    )
    trace: dict[str, Any] = {
        "enabled": active,
        "protected_prefix_rows": len(reranked),
        "lanes": [],
        "appended_ids": [],
        "model_calls": 0,
        "database_writes": 0,
    }
    if not active or not reranked or not (
        structural
        or table_preamble
        or hyq
        or pool
        or document_local
        or compatibility_applicable
        or obligation_reserve_applicable
        or facet_complement_applicable
    ):
        trace["status"] = "disabled_or_not_applicable"
        return reranked, trace

    candidates: list[dict[str, Any]] = []
    # s279 compuerta 2 (A2): caché del candidate-pool del lane document-local para
    # reuso $0 por la vía por-faceta.  Se puebla SOLO bajo el flag y solo si el
    # collector expone el seam ``fetcher`` (el default collect_document_local_
    # coverage lo hace); en cualquier otro caso queda vacío y la vía re-deriva.
    facet_pool_cache: dict[str, Any] = {}
    lane_calls = []

    def collect_cascade_if_capacity() -> tuple[list[dict], dict]:
        already_appendable = append_validated_coverage(reranked, candidates)
        if len(already_appendable) - len(reranked) >= MAX_APPENDED:
            return [], {
                "lane": STRUCTURAL_CASCADE_LANE,
                "status": "skipped_no_append_capacity",
                "selected_ids": [],
                "http_requests": 0,
            }
        served_pool_ids = {
            str(row.get("id") or "")
            for row in already_appendable[len(reranked):]
            if row.get("retrieval_lane") == POOL_LANE
        }
        pool_seeds = [
            row for row in candidates
            if row.get("retrieval_lane") == POOL_LANE
            and str(row.get("id") or "") in served_pool_ids
        ]
        if not pool_seeds:
            return [], {
                "lane": STRUCTURAL_CASCADE_LANE,
                "status": "skipped_no_served_pool_seed",
                "selected_ids": [],
                "http_requests": 0,
            }
        return cascade_collector(
            query,
            pool_seeds,
        )

    def collect_document_local_if_capacity() -> tuple[list[dict], dict]:
        already_appendable = append_validated_coverage(reranked, candidates)
        if len(already_appendable) - len(reranked) >= MAX_APPENDED:
            return [], {
                "lane": DOCUMENT_LOCAL_LANE,
                "status": "skipped_no_append_capacity",
                "selected_ids": [],
                "http_requests": 0,
                "model_calls": 0,
                "database_writes": 0,
            }
        source_contract_anchors, source_contract_overflow = (
            _document_local_source_contract_rows(query)
        )
        if source_contract_overflow:
            return [], {
                "lane": DOCUMENT_LOCAL_LANE,
                "status": "source_scope_overflow",
                "selected_ids": [],
                "satisfied_ids": [],
                "satisfaction_route": None,
                "http_requests": 0,
                "model_calls": 0,
                "database_writes": 0,
                "overflow": True,
            }
        served_structural_ids = {
            str(row.get("id") or "")
            for row in already_appendable[len(reranked) :]
            if row.get("retrieval_lane") == STRUCTURAL_LANE
        }
        structural_anchors = [
            row
            for row in candidates
            if row.get("retrieval_lane") == STRUCTURAL_LANE
            and str(row.get("id") or "") in served_structural_ids
        ]
        if not source_contract_anchors and not structural_anchors:
            return [], {
                "lane": DOCUMENT_LOCAL_LANE,
                "status": "skipped_no_served_structural_anchor",
                "selected_ids": [],
                "http_requests": 0,
                "model_calls": 0,
                "database_writes": 0,
            }
        document_local_anchors = _document_local_anchor_rows(
            reranked,
            structural_anchors,
            source_contract_anchors,
        )
        if not document_local_anchors:
            return [], {
                "lane": DOCUMENT_LOCAL_LANE,
                "status": "skipped_no_exact_blob_anchor",
                "selected_ids": [],
                "http_requests": 0,
                "model_calls": 0,
                "database_writes": 0,
            }
        if _facet_selection_v2_enabled():
            # s279 compuerta 2 (A2): captura el candidate-pool que el lane fetchea
            # para reuso $0 por la vía, SIN duplicar la RPC.  Solo si el collector
            # acepta ``fetcher`` (seam del default); si no, la vía re-deriva.
            import inspect

            try:
                accepts_fetcher = (
                    "fetcher"
                    in inspect.signature(document_local_collector).parameters
                )
            except (TypeError, ValueError):
                accepts_fetcher = False
            if accepts_fetcher:
                from .document_local_coverage import (
                    _anchor_scopes,
                    build_document_local_query_plan,
                    fetch_document_local_candidates,
                )

                def _capturing_fetcher(fetch_query, fetch_anchors, **kwargs):
                    pool, authorities, read_trace = fetch_document_local_candidates(
                        fetch_query, fetch_anchors, **kwargs
                    )
                    scopes, scope_reason = _anchor_scopes(fetch_anchors)
                    facet_pool_cache["candidates"] = list(pool)
                    facet_pool_cache["authorities"] = list(authorities)
                    facet_pool_cache["plan"] = (
                        build_document_local_query_plan(fetch_query, scopes)
                        if scope_reason == "ok"
                        else None
                    )
                    return pool, authorities, read_trace

                return document_local_collector(
                    query,
                    document_local_anchors,
                    already_appendable,
                    fetcher=_capturing_fetcher,
                )
        return document_local_collector(
            query,
            document_local_anchors,
            already_appendable,
        )

    if structural and not compatibility_applicable:
        lane_calls.append((STRUCTURAL_LANE, lambda: structural_collector(query, reranked)))
    if table_preamble and not compatibility_applicable:
        lane_calls.append(
            (
                TABLE_PREAMBLE_LANE,
                lambda: table_preamble_collector(query, reranked),
            )
        )
    if compatibility_applicable:
        lane_calls.append(
            (COMPATIBILITY_LANE, lambda: compatibility_collector(query))
        )
    if hyq and not compatibility_applicable:
        lane_calls.append((HYQ_LANE, lambda: hyq_collector(query)))
    # Pool coverage is deliberately last. Existing S109 candidates keep their
    # places inside the global four-row append budget; this lane only fills
    # unused capacity and cannot displace a previously validated recovery.
    if pool and retrieval_pool and not compatibility_applicable:
        lane_calls.append(
            # The pool lane sees earlier validated candidates as coverage
            # context, so its two-row budget complements rather than repeats
            # structural/HYQ recoveries. The protected prefix itself remains
            # unchanged and is still the only ordering authority.
            (POOL_LANE, lambda: pool_collector(
                query, retrieval_pool, [*reranked, *candidates]
            ))
        )
    if document_local and not compatibility_applicable:
        lane_calls.append(
            (
                DOCUMENT_LOCAL_LANE,
                collect_document_local_if_capacity,
            )
        )
    if cascade:
        lane_calls.append(
            (
                STRUCTURAL_CASCADE_LANE,
                collect_cascade_if_capacity,
            )
        )
    for lane, call in lane_calls:
        try:
            selected, lane_trace = call()
            candidates.extend(selected)
            trace["lanes"].append(lane_trace)
        except Exception as exc:
            logger.warning("post-rerank coverage lane failed open: %s", type(exc).__name__)
            trace["lanes"].append(
                {"lane": lane, "status": "error", "error_type": type(exc).__name__}
            )

    output = append_validated_coverage(reranked, candidates)
    if obligation_reserve_applicable:
        # s278 §3: la reserva corre DESPUÉS de conocer la vista servida (de
        # ahí toma su scope canónico de documento) pero con presupuesto PROPIO
        # — el cap global de 4 ya no puede desplazarla (fallo hp002:r1: el
        # warning ASD535 p121 quedó en el pool #28 sin servir).
        try:
            reserve_rows, reserve_trace = obligation_reserve_collector(
                query, retrieval_pool, output
            )
            trace["lanes"].append(reserve_trace)
            output = _append_obligation_warning_reserve(
                output, reserve_rows, retrieval_pool
            )
        except Exception as exc:
            logger.warning(
                "obligation warning reserve failed open: %s", type(exc).__name__
            )
            trace["lanes"].append(
                {
                    "lane": OBLIGATION_WARNING_LANE,
                    "status": "error",
                    "error_type": type(exc).__name__,
                }
            )
    if facet_complement_applicable:
        # s279 compuerta 2 (A8): la vía por-faceta corre DESPUÉS de la reserve
        # (ve la vista final, reserve incluida) con presupuesto PROPIO fuera de
        # MAX_APPENDED.  Reusa el pool cacheado del lane o re-deriva+own-fetch.
        try:
            source = _resolve_facet_complement_source(
                query, reranked, output, facet_pool_cache
            )
            output, facet_trace = _append_facet_complement(
                output,
                reranked,
                plan=source.get("plan"),
                candidate_pool=source.get("candidate_pool") or [],
                facet_fetch=source.get("facet_fetch"),
                plan_rederived=source.get("plan_rederived", False),
            )
            trace["lanes"].append(facet_trace)
        except Exception as exc:
            logger.warning(
                "facet complement failed open: %s", type(exc).__name__
            )
            trace["lanes"].append(
                {
                    "lane": DOCUMENT_LOCAL_LANE,
                    "conduct": "facet_complement",
                    "status": "error",
                    "error_type": type(exc).__name__,
                }
            )
    trace.update(
        {
            "status": "appended" if len(output) > len(reranked) else "no_append",
            "appended_ids": [str(row.get("id") or "") for row in output[len(reranked):]],
            "protected_prefix_equal": output[: len(reranked)] == reranked,
        }
    )
    return output, trace


def apply_post_rerank_coverage(
    query: str,
    reranked: list[dict[str, Any]],
    *,
    retrieval_pool: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    output, _ = apply_post_rerank_coverage_with_trace(
        query, reranked, retrieval_pool=retrieval_pool
    )
    return output
