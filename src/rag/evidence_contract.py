"""(S278 §5 · flag ``EVIDENCE_CONTRACT``=off|on, default off, perfil-owned) Evidence
Contract v1: validador post-writer DETERMINISTA y fail-closed sobre el CONTEXTO SERVIDO.

Diseño canónico: ``evals/s278_vnext_design_v2.md`` §5 + tabla por-ítem
``evals/s278_ec_item_table_v1.md``. Corre como ÚLTIMO eslabón del serving path
(después de answer_planner → must_preserve → conflict_guard); el seam del generador
relee el flag en runtime y con flag off este módulo NI SE IMPORTA (byte-idéntico).

Mecanismo:

  1. LEDGER de obligaciones construido desde la evidencia SERVIDA (cards con
     source/página/contenido — la MISMA vista que ve el generador, paridad
     ``must_preserve._chunk_text``). Clases:
       ``safety_mandatory``      callouts de advertencia (detección determinista de
                                 must_preserve, IMPORTADA — no duplicada)
       ``relation_table``        filas de tabla ligadas a términos de la pregunta
       ``attribution_conflict``  mismo parámetro con valores distintos entre fuentes
                                 servidas, o conteo declarado vs enumeración servida
                                 (F-COUNT intra + cross de must_preserve) → DISCLOSE
       ``universal_compound``    cualificador universal con compuesto AND/rango/modal
       ``arithmetic``            derivación entera simple N × (A + B) con TODOS los
                                 operandos en spans servidos y pregunta de agregado
  2. VALIDACIÓN post-writer: una obligación solo actúa si es APLICABLE a la pregunta
     (matching lexical determinista pregunta↔span, umbral conservador por clase) y la
     respuesta NO la cubre ya.
  3. ACCIÓN: APPEND del span EXACTO verbatim con cita local ``(fuente, p.X) [Fn]``
     (formato de la casa) o DISCLOSE con frase-plantilla determinista que cita AMBOS
     valores y AMBAS fuentes. La derivación aritmética SIEMPRE declara sus operandos
     citados — jamás inyecta el literal derivado sin traza. Cap propio de
     ``APPEND_CAP`` entradas por respuesta, orden ESTABLE (prioridad de clase →
     fragmento → posición).
  4. FAIL-CLOSED: si un span no ancla EXACTO en su fragmento servido, o falta la
     fuente citable, NO se actúa (silencio > invención). Sin identificadores de eval
     en runtime. Puro código, cero LLM, cero red. Idempotente: re-aplicar sobre la
     salida no produce acciones nuevas (los appends satisfacen su obligación y las
     plantillas de disclosure usan el léxico de disclosure de must_preserve).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .catalog import _fold
from .mp_lexicon import (
    line_spans as _line_spans,
    sentence_spans as _sentence_spans,
)
# Reuso DELIBERADO de la detección/satisfacción determinista de must_preserve
# (mandato del diseño §5: importarla, no duplicarla).
from .must_preserve import (
    APPENDIX_EMOJI_DISCLOSURE,
    APPENDIX_EMOJI_GENERIC,
    APPENDIX_EMOJI_MANDATORY,
    APPENDIX_SEPARATOR,
    FAMILY_COUNT,
    FAMILY_MANDATORY,
    _chunk_text,
    _content_tokens,
    _COUNT_WORDS,
    _FRAG_CITE,
    _is_pipe_row,
    _numbers_in,
    _PIPE_SEP,
    _strip_blockquote_markers,
    atom_good_form,
    atom_satisfied,
    detect_atoms,
    detect_cross_fragment_count_atoms,
    informative_span,
    span_good_form,
)

SCHEMA = "evidence_contract_v1"

CLASS_SAFETY = "safety_mandatory"
CLASS_ATTRIBUTION = "attribution_conflict"
CLASS_RELATION_TABLE = "relation_table"
CLASS_UNIVERSAL = "universal_compound"
CLASS_ARITHMETIC = "arithmetic"

# Orden ESTABLE del render (seguridad primero — precedente de la selección v2 de
# must_preserve); también desempata el dedup por span entre clases.
_CLASS_PRIORITY = {
    CLASS_SAFETY: 0,
    CLASS_ATTRIBUTION: 1,
    CLASS_RELATION_TABLE: 2,
    CLASS_UNIVERSAL: 3,
    CLASS_ARITHMETIC: 4,
}

# Umbral conservador de aplicabilidad pregunta↔span por clase (tokens de contenido
# matcheados, tolerancia de plural es/en). relation_table exige 3: una fila de tabla
# solo es exigible si la pregunta toca su dominio con fuerza (2 tokens genéricos del
# encabezado no bastan — silencio > filas arbitrarias).
_THRESHOLD = {
    CLASS_SAFETY: 2,
    CLASS_ATTRIBUTION: 2,
    CLASS_RELATION_TABLE: 3,
    CLASS_UNIVERSAL: 2,
    CLASS_ARITHMETIC: 2,
}

# Cap PROPIO del contrato (diseño §5): máximo de entradas anexadas por respuesta.
APPEND_CAP = 3

APPENDIX_HEADER = "Obligaciones de evidencia del manual:"

# Clases cuyo span verbatim se anexa tal cual → dedup por (fragmento, span foldeado);
# los disclosures/derivaciones renderizan plantillas distintas y no se dedupean aquí.
_SPAN_DEDUP_CLASSES = {CLASS_SAFETY, CLASS_RELATION_TABLE, CLASS_UNIVERSAL}


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# ─────────────────────── matching lexical pregunta↔span ───────────────────────

def _token_match(a: str, b: str) -> bool:
    """Igualdad de tokens foldeados con tolerancia de plural es/en (``sirena`` ≈
    ``sirenas``, ``relacion`` ≈ ``relaciones``). Cerrada y determinista."""
    if a == b:
        return True
    for x, y in ((a, b), (b, a)):
        if x == y + "s" or x == y + "es":
            return True
    return False


def _matched_tokens(question_tokens: set[str], texts) -> set[str]:
    """Tokens de contenido PROPIOS de los textos que la pregunta también trae."""
    own: set[str] = set()
    for text in texts:
        own.update(_content_tokens(text or ""))
    return {t for t in own if any(_token_match(t, q) for q in question_tokens)}


# ─────────────────────────── vista servida + citas ───────────────────────────

def _views(served_cards) -> list[tuple[int, dict, str]]:
    """(fragment_number 1-based, card, vista servida) — paridad con el prompt."""
    views: list[tuple[int, dict, str]] = []
    for idx, card in enumerate(served_cards or [], start=1):
        if not isinstance(card, dict):
            continue
        text = _chunk_text(card)
        if text and text.strip():
            views.append((idx, card, text))
    return views


def _cite_parts(card: dict, fragment_number: int) -> dict[str, Any] | None:
    """Cita local de la casa ``(fuente, p.X) [Fn]`` — mismo naming que el header de
    fragmento del generador (source_file sin ``.pdf``). Sin fuente → None
    (fail-closed: sin cita no hay acción)."""
    source_file = str(card.get("source_file") or "").strip()
    if not source_file:
        return None
    manual = source_file.rsplit(".pdf", 1)[0]
    page = card.get("page_number")
    if page in (None, ""):
        label = f"({manual}) [F{fragment_number}]"
    else:
        label = f"({manual}, p. {page}) [F{fragment_number}]"
    return {"manual": manual, "page": page, "label": label}


def _obligation(
    cls: str,
    kind: str,
    fragment_number: int,
    card: dict,
    span_text: str,
    span_start: int,
    applicable: bool,
    matched: set[str],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "class": cls,
        "kind": kind,
        "fragment_number": fragment_number,
        "source_file": str(card.get("source_file") or ""),
        "page_number": card.get("page_number"),
        "span_text": span_text,
        "span_start": int(span_start),
        "applicable": bool(applicable),
        "matched_question_tokens": sorted(matched),
        "meta": dict(meta or {}),
    }


# ──────────────────────────── builders del ledger ────────────────────────────

def _atom_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """safety_mandatory (F-MANDATORY con forma-buena de la casa) + conflicto
    conteo-declarado↔enumeración DENTRO de un fragmento (F-COUNT, conflict=True)."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        for atom in detect_atoms(text):
            family = atom.get("family")
            meta = atom.get("meta") or {}
            span = str(atom.get("span_text") or "")
            start = int(atom.get("span_start") or 0)
            if family == FAMILY_MANDATORY:
                if not atom_good_form(atom):
                    continue  # whitelist v5: jamás anexar cabecera-sola/ruido
                proc = " ".join(meta.get("procedural_context_tokens") or [])
                matched = _matched_tokens(question_tokens, (span, proc))
                out.append(_obligation(
                    CLASS_SAFETY, "mandatory_callout", idx, card, span, start,
                    len(matched) >= _THRESHOLD[CLASS_SAFETY], matched,
                    {"atom": atom},
                ))
            elif family == FAMILY_COUNT and meta.get("conflict"):
                enum_span = str(meta.get("enum_span_text") or "")
                matched = _matched_tokens(question_tokens, (span, enum_span))
                out.append(_obligation(
                    CLASS_ATTRIBUTION, "declared_vs_enumerated", idx, card, span,
                    start, len(matched) >= _THRESHOLD[CLASS_ATTRIBUTION], matched,
                    {
                        "atom": atom,
                        "declared": meta.get("declared_n"),
                        "enumerated": meta.get("enumerated_n"),
                        "noun": str(meta.get("noun") or "elementos"),
                        "enum_fragment_number": idx,
                        "enum_span_text": enum_span,
                    },
                ))
    return out


def _cross_count_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """Conteo declarado en un fragmento vs enumeración servida en OTRO (mismo
    documento, página adyacente — contrato cross de must_preserve, importado)."""
    card_map = {idx: card for idx, card, _text in views}
    fragments = [
        {
            "fragment_number": idx,
            "text": text,
            "document_id": card.get("document_id"),
            "page_number": card.get("page_number"),
        }
        for idx, card, text in views
    ]
    out: list[dict[str, Any]] = []
    for atom in detect_cross_fragment_count_atoms(fragments):
        meta = atom.get("meta") or {}
        i = meta.get("count_fragment_number")
        j = meta.get("enum_fragment_number")
        if i not in card_map or j not in card_map:
            continue
        span = str(atom.get("span_text") or "")
        enum_span = str(meta.get("enum_span_text") or "")
        matched = _matched_tokens(question_tokens, (span, enum_span))
        out.append(_obligation(
            CLASS_ATTRIBUTION, "declared_vs_enumerated", i, card_map[i], span,
            int(atom.get("span_start") or 0),
            len(matched) >= _THRESHOLD[CLASS_ATTRIBUTION], matched,
            {
                "atom": atom,
                "declared": meta.get("declared_n"),
                "enumerated": meta.get("enumerated_n"),
                "noun": str(meta.get("noun") or "elementos"),
                "enum_fragment_number": j,
                "enum_span_text": enum_span,
            },
        ))
    return out


# parámetro := línea ``Etiqueta: valor [unidad]`` (o fila de tabla de 2 celdas con
# valor numérico) — la base determinista de "mismo parámetro, valores distintos".
_PARAM_LINE_RX = re.compile(
    r"^\s*([A-Za-zÁÉÍÓÚÑÜáéíóúñü][\w /().ÁÉÍÓÚÑÜáéíóúñü%-]{2,60}?)\s*[:=]\s*"
    r"(\d{1,6}(?:[.,]\d+)?)\s*([A-Za-zΩµμ%]{0,8})\s*$"
)
_PARAM_VALUE_RX = re.compile(r"(\d{1,6}(?:[.,]\d+)?)\s*([A-Za-zΩµμ%]{0,8})")


def _num_value(raw: str) -> float:
    return float(raw.replace(",", "."))


def _param_entries(fragment_number: int, card: dict, text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for start, _end, line in _line_spans(text):
        raw = line.strip()
        if not raw:
            continue
        if _is_pipe_row(line) and not _PIPE_SEP.match(line):
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if len(cells) == 2 and cells[0]:
                vm = _PARAM_VALUE_RX.fullmatch(cells[1])
                if vm:
                    entries.append({
                        "fragment_number": fragment_number,
                        "card": card,
                        "label": cells[0],
                        "value": _num_value(vm.group(1)),
                        "raw_value": vm.group(1),
                        "unit": vm.group(2) or "",
                        "span_text": line,
                        "span_start": start,
                    })
            continue
        m = _PARAM_LINE_RX.match(line)
        if m:
            entries.append({
                "fragment_number": fragment_number,
                "card": card,
                "label": m.group(1).strip(),
                "value": _num_value(m.group(2)),
                "raw_value": m.group(2),
                "unit": m.group(3) or "",
                "span_text": line,
                "span_start": start,
            })
    return entries


def _param_conflict_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """attribution_conflict (kind ``parameter_two_values``): la MISMA etiqueta (fold)
    con la MISMA unidad y valores numéricos DISTINTOS en fuentes servidas distintas
    ⇒ obligación de DISCLOSE con ambas atribuciones."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for idx, card, text in views:
        for entry in _param_entries(idx, card, text):
            label_tokens = _content_tokens(entry["label"])
            if not label_tokens:
                continue
            key = (
                " ".join(_fold(entry["label"]).split()),
                _fold(entry["unit"]).strip(),
            )
            groups.setdefault(key, []).append(entry)
    out: list[dict[str, Any]] = []
    for key in sorted(groups):
        rows = sorted(
            groups[key], key=lambda r: (r["fragment_number"], r["span_start"])
        )
        first = rows[0]
        partner = next(
            (
                r for r in rows[1:]
                if r["value"] != first["value"]
                and str(r["card"].get("source_file") or "")
                != str(first["card"].get("source_file") or "")
            ),
            None,
        )
        if partner is None:
            continue
        label_tokens = set(_content_tokens(first["label"]))
        matched = _matched_tokens(question_tokens, (first["label"],))
        needed = min(_THRESHOLD[CLASS_ATTRIBUTION], len(label_tokens))
        out.append(_obligation(
            CLASS_ATTRIBUTION, "parameter_two_values",
            first["fragment_number"], first["card"], first["span_text"],
            first["span_start"], len(matched) >= max(1, needed), matched,
            {
                "label": first["label"],
                "unit": first["unit"],
                "value_a": first["value"],
                "value_b": partner["value"],
                "b_fragment_number": partner["fragment_number"],
                "b_span_text": partner["span_text"],
            },
        ))
    return out


def _table_row_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """relation_table: filas de datos de una tabla pipe (≥2 filas de datos; la
    primera hace de encabezado) ligadas con fuerza a la pregunta (umbral 3)."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        lines = _line_spans(text)
        i = 0
        while i < len(lines):
            if not _is_pipe_row(lines[i][2]):
                i += 1
                continue
            j = i
            data: list[tuple[int, int, str]] = []
            while j < len(lines) and _is_pipe_row(lines[j][2]):
                if not _PIPE_SEP.match(lines[j][2]):
                    data.append(lines[j])
                j += 1
            if len(data) >= 2:
                header = data[0][2]
                for start, _end, line in data[1:]:
                    if not informative_span(line):
                        continue
                    matched = _matched_tokens(question_tokens, (line, header))
                    out.append(_obligation(
                        CLASS_RELATION_TABLE, "table_row", idx, card, line, start,
                        len(matched) >= _THRESHOLD[CLASS_RELATION_TABLE], matched,
                        {"header": header},
                    ))
            i = j
    return out


_UNIVERSAL_RX = re.compile(
    r"\b(cada|todos?|todas?|ambos|ambas|ningun[oa]?s?|siempre|nunca|jamas"
    r"|all|every|each|always|never|both|none)\b"
)
_CONJ_RX = re.compile(r"\b(y|e|o|u|and|or)\b")
_RANGE_RX = re.compile(
    r"\bde\s+\d+(?:[.,]\d+)?\s+a\s+\d+(?:[.,]\d+)?\b"
    r"|\bentre\s+\d+(?:[.,]\d+)?\s+y\s+\d+(?:[.,]\d+)?\b"
    r"|\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?"
)
_MODAL_RX = re.compile(r"\b(debe|deben|debera|deberan|must|shall)\b")


def _universal_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """universal_compound: oración con cualificador universal Y un compuesto
    (conjunción AND/OR, rango numérico o modal de obligación), con forma-buena de
    cláusula (whitelist de la casa)."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        for s, e in _sentence_spans(text):
            sentence = text[s:e]
            folded = _fold(sentence)
            if not _UNIVERSAL_RX.search(folded):
                continue
            if not (
                _CONJ_RX.search(folded)
                or _RANGE_RX.search(folded)
                or _MODAL_RX.search(folded)
            ):
                continue
            if not span_good_form(sentence):
                continue
            matched = _matched_tokens(question_tokens, (sentence,))
            out.append(_obligation(
                CLASS_UNIVERSAL, "universal_clause", idx, card, sentence, s,
                len(matched) >= _THRESHOLD[CLASS_UNIVERSAL], matched,
            ))
    return out


_AGGREGATE_RX = re.compile(r"\b(total(?:es)?|cuant[oa]s|maxim[oa]s?|capacidad)\b")
_MULT_RX = re.compile(
    r"total\s+de\s+(\d{1,3}|[a-záéíóúñü]{3,9})\s+"
    r"([A-Za-z0-9ÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü-]{1,})",
    re.IGNORECASE,
)
_ADDEND_RX = re.compile(
    r"\bhasta\s+(\d{1,4})\s+"
    r"([A-Za-zÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü-]{2,})",
    re.IGNORECASE,
)


def _sentence_of(text: str, pos: int) -> str:
    for s, e in _sentence_spans(text):
        if s <= pos < e:
            return text[s:e]
    return text[max(0, pos - 80): pos + 80]


def _arithmetic_obligations(
    question: str, question_tokens: set[str], views
) -> list[dict[str, Any]]:
    """arithmetic: derivación entera simple N × (A + B) SOLO si el multiplicador
    (``total de N <sustantivo>``) y EXACTAMENTE dos sumandos distintos
    (``hasta A <sustantivo>``) están en spans servidos del MISMO fragmento y la
    pregunta pide el agregado. Conservador por construcción: cualquier ambigüedad
    (≠2 sumandos, sustantivos repetidos, N<2) ⇒ sin obligación."""
    if not _AGGREGATE_RX.search(_fold(question or "")):
        return []
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        mult = _MULT_RX.search(text)
        addends = list(_ADDEND_RX.finditer(text))
        if mult is None or len(addends) != 2:
            continue
        raw_n = _fold(mult.group(1))
        n = _COUNT_WORDS.get(raw_n) or (int(raw_n) if raw_n.isdigit() else None)
        if n is None or n < 2:
            continue
        a_m, b_m = addends
        if _fold(a_m.group(2)) == _fold(b_m.group(2)):
            continue  # el mismo sustantivo dos veces = hecho repetido, no suma
        a, b = int(a_m.group(1)), int(b_m.group(1))
        if a < 1 or b < 1:
            continue
        sentences = (
            _sentence_of(text, mult.start()),
            _sentence_of(text, a_m.start()),
            _sentence_of(text, b_m.start()),
        )
        matched = _matched_tokens(question_tokens, sentences)
        out.append(_obligation(
            CLASS_ARITHMETIC, "n_times_a_plus_b", idx, card, mult.group(0),
            mult.start(), len(matched) >= _THRESHOLD[CLASS_ARITHMETIC], matched,
            {
                "n": n,
                "a": a,
                "b": b,
                "total": n * (a + b),
                "mult_span": mult.group(0),
                "addend_a_span": a_m.group(0),
                "addend_b_span": b_m.group(0),
            },
        ))
    return out


def build_obligation_ledger(question: str, served_cards) -> list[dict[str, Any]]:
    """Ledger completo, ordenado ESTABLE y dedupeado (clases de span verbatim)."""
    question_tokens = set(_content_tokens(question or ""))
    views = _views(served_cards)
    ledger: list[dict[str, Any]] = []
    ledger.extend(_atom_obligations(question_tokens, views))
    ledger.extend(_cross_count_obligations(question_tokens, views))
    ledger.extend(_param_conflict_obligations(question_tokens, views))
    ledger.extend(_table_row_obligations(question_tokens, views))
    ledger.extend(_universal_obligations(question_tokens, views))
    ledger.extend(_arithmetic_obligations(question, question_tokens, views))
    ledger.sort(key=lambda ob: (
        _CLASS_PRIORITY.get(ob["class"], 99),
        ob["fragment_number"],
        ob["span_start"],
        _fold(ob["span_text"]),
    ))
    seen: set[tuple[int, str]] = set()
    deduped: list[dict[str, Any]] = []
    for ob in ledger:
        key = (ob["fragment_number"], " ".join(_fold(ob["span_text"]).split()))
        if ob["class"] in _SPAN_DEDUP_CLASSES and key in seen:
            continue
        seen.add(key)
        deduped.append(ob)
    return deduped


# ───────────────────────── satisfacción post-writer ─────────────────────────

def obligation_satisfied(ob: dict[str, Any], answer_text: str) -> bool:
    """¿La respuesta YA cubre la obligación? Las clases basadas en átomos de
    must_preserve delegan en su contrato ``atom_satisfied`` (un F-COUNT en
    conflicto solo se satisface con disclosure explícito, jamás por números)."""
    if not isinstance(answer_text, str) or not answer_text.strip():
        return False
    meta = ob.get("meta") or {}
    atom = meta.get("atom")
    if atom is not None:
        return atom_satisfied(atom, answer_text)
    clean = _FRAG_CITE.sub(" ", answer_text)
    numbers = _numbers_in(clean)
    cls = ob.get("class")
    if cls == CLASS_ARITHMETIC:
        return float(meta["total"]) in numbers
    if cls == CLASS_ATTRIBUTION:
        # parámetro con dos valores: cubierto solo si la respuesta trae AMBOS
        return {float(meta["value_a"]), float(meta["value_b"])} <= numbers
    # relation_table / universal_compound: números propios (excl. 0/1 por
    # ubicuidad) presentes Y ≥80% de los tokens de contenido del span.
    span = ob.get("span_text") or ""
    own_numbers = {v for v in _numbers_in(span) if v not in (0.0, 1.0)}
    if not own_numbers <= numbers:
        return False
    own_tokens = set(_content_tokens(span))
    if not own_tokens:
        return True
    answer_tokens = set(_content_tokens(clean))
    present = sum(
        1 for t in own_tokens if any(_token_match(t, a) for a in answer_tokens)
    )
    return present / len(own_tokens) >= 0.8


# ─────────────────────────────── render ───────────────────────────────

def _display_span(span: str) -> str:
    return " ".join(_strip_blockquote_markers(span).strip().split("\n"))


def _base_action(ob: dict[str, Any], action: str) -> dict[str, Any]:
    return {
        "action": action,
        "class": ob["class"],
        "kind": ob["kind"],
        "fragment_number": ob["fragment_number"],
        "source_file": ob["source_file"],
        "page_number": ob["page_number"],
        "span_sha256": _sha256(ob["span_text"]),
        "matched_question_tokens": ob["matched_question_tokens"],
        "reason": (
            "obligación aplicable a la pregunta (matching lexical) y no cubierta "
            "por la respuesta"
        ),
    }


def _render_action(
    ob: dict[str, Any],
    view_map: dict[int, str],
    card_map: dict[int, dict],
) -> tuple[str, dict[str, Any]] | None:
    """Entrada del anexo + acción del receipt, o None (fail-closed: anclaje EXACTO
    del span en su fragmento servido y fuente citable, o NO se actúa)."""
    idx = ob["fragment_number"]
    view = view_map.get(idx)
    card = card_map.get(idx)
    if view is None or card is None:
        return None
    cite = _cite_parts(card, idx)
    span = ob.get("span_text") or ""
    if cite is None or not span or span not in view:
        return None
    if not informative_span(span):
        return None
    meta = ob.get("meta") or {}
    cls = ob["class"]
    if cls == CLASS_ATTRIBUTION and ob["kind"] == "declared_vs_enumerated":
        j = meta.get("enum_fragment_number")
        enum_span = str(meta.get("enum_span_text") or "")
        view_j = view_map.get(j)
        card_j = card_map.get(j)
        declared = meta.get("declared")
        enumerated = meta.get("enumerated")
        if view_j is None or card_j is None or declared is None or enumerated is None:
            return None
        cite_j = _cite_parts(card_j, j)
        if cite_j is None or not enum_span or enum_span not in view_j:
            return None
        if not informative_span(enum_span):
            return None
        line = (
            f'- Nota: la fuente es inconsistente: "{_display_span(span)}" '
            f"{cite['label']} declara {declared} {meta.get('noun')} y la "
            f"enumeración servida lista {enumerated} {cite_j['label']}."
        )
        action = _base_action(ob, "disclose")
        action["counterpart"] = {
            "fragment_number": j,
            "source_file": str(card_j.get("source_file") or ""),
            "page_number": card_j.get("page_number"),
            "span_sha256": _sha256(enum_span),
        }
        return line, action
    if cls == CLASS_ATTRIBUTION and ob["kind"] == "parameter_two_values":
        j = meta.get("b_fragment_number")
        span_b = str(meta.get("b_span_text") or "")
        view_j = view_map.get(j)
        card_j = card_map.get(j)
        if view_j is None or card_j is None:
            return None
        cite_j = _cite_parts(card_j, j)
        if cite_j is None or not span_b or span_b not in view_j:
            return None
        line = (
            f'- Nota: la fuente es inconsistente en "{meta.get("label")}": '
            f'"{_display_span(span)}" {cite["label"]} frente a '
            f'"{_display_span(span_b)}" {cite_j["label"]}.'
        )
        action = _base_action(ob, "disclose")
        action["counterpart"] = {
            "fragment_number": j,
            "source_file": str(card_j.get("source_file") or ""),
            "page_number": card_j.get("page_number"),
            "span_sha256": _sha256(span_b),
        }
        return line, action
    if cls == CLASS_ARITHMETIC:
        operands = (
            str(meta.get("mult_span") or ""),
            str(meta.get("addend_a_span") or ""),
            str(meta.get("addend_b_span") or ""),
        )
        if not all(op and op in view for op in operands):
            return None  # operando no anclable ⇒ sin derivación (fail-closed)
        n, a, b, total = meta["n"], meta["a"], meta["b"], meta["total"]
        line = (
            f"- Derivación declarada según {cite['label']}: "
            f"{n} × ({a} + {b}) = {total} — operandos citados: "
            f'"{operands[0]}", "{operands[1]}" y "{operands[2]}".'
        )
        action = _base_action(ob, "append")
        action["derivation"] = f"{n} × ({a} + {b}) = {total}"
        action["operand_sha256"] = [_sha256(op) for op in operands]
        return line, action
    # safety_mandatory / relation_table / universal_compound: span EXACTO verbatim
    line = f'- "{_display_span(span)}" {cite["label"]}'
    return line, _base_action(ob, "append")


# ─────────────────────────────── API pública ───────────────────────────────

def apply_evidence_contract(
    answer_text: str,
    served_cards: list[dict],
    question: str,
) -> dict[str, Any]:
    """Punto de entrada único (post-writer, tras el conflict_guard).

    Devuelve ``{"text", "actions", "receipt"}``. Sin acciones ⇒ ``text`` es el
    MISMO objeto respuesta (byte-idéntico). El caller envuelve en try/except
    (fail-open de la respuesta); dentro, cada acción es fail-closed."""
    if not isinstance(answer_text, str):
        raise TypeError("evidence contract requires a string answer")
    if not isinstance(question, str):
        raise TypeError("evidence contract requires a string question")
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "ledger_size": 0,
        "applicable": 0,
        "unsatisfied": 0,
        "actions": [],
        "appended_entries": 0,
        "cap": APPEND_CAP,
        "cap_reached": False,
        "skipped_unanchored": 0,
    }
    if not answer_text.strip() or not served_cards:
        receipt["reason"] = "empty_answer_or_no_served_context"
        return {"text": answer_text, "actions": [], "receipt": receipt}
    views = _views(served_cards)
    view_map = {idx: text for idx, _card, text in views}
    card_map = {idx: card for idx, card, _text in views}
    ledger = build_obligation_ledger(question, served_cards)
    applicable = [ob for ob in ledger if ob["applicable"]]
    pending = [ob for ob in applicable if not obligation_satisfied(ob, answer_text)]
    receipt["ledger_size"] = len(ledger)
    receipt["applicable"] = len(applicable)
    receipt["unsatisfied"] = len(pending)
    entries: list[str] = []
    actions: list[dict[str, Any]] = []
    has_safety = has_disclose = False
    for ob in pending:
        if len(entries) >= APPEND_CAP:
            receipt["cap_reached"] = True
            break
        rendered = _render_action(ob, view_map, card_map)
        if rendered is None:
            receipt["skipped_unanchored"] += 1
            continue
        line, action = rendered
        if line in entries:
            continue
        entries.append(line)
        actions.append(action)
        has_safety = has_safety or ob["class"] == CLASS_SAFETY
        has_disclose = has_disclose or action["action"] == "disclose"
    if not entries:
        return {"text": answer_text, "actions": [], "receipt": receipt}
    if has_safety:
        emoji = APPENDIX_EMOJI_MANDATORY
    elif has_disclose:
        emoji = APPENDIX_EMOJI_DISCLOSURE
    else:
        emoji = APPENDIX_EMOJI_GENERIC
    appendix = "\n".join(
        [APPENDIX_SEPARATOR, f"{emoji} **{APPENDIX_HEADER}**", *entries]
    )
    receipt["actions"] = actions
    receipt["appended_entries"] = len(entries)
    return {
        "text": answer_text.rstrip() + "\n\n" + appendix,
        "actions": actions,
        "receipt": receipt,
    }
