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
  5. RIESGO 7-SEGMENTOS (feedback_7segment): las obligaciones basadas en átomos de
     must_preserve heredan SU contrato de paridad de display (``display_parity_ok``
     — un átomo con riesgo solo actúa si el borrador ya nombra sus tokens display);
     las clases propias del contrato (tabla/universal) NO se bloquean — pero el
     receipt DECLARA ``seven_segment_risk`` cuando el span citado (o su línea
     contenedora) lleva superficie de display, y el display JAMÁS re-afirma un
     tachado OCR con letras (``_apply_struck_ocr`` — ambigüedad declarada,
     residual → técnico).

Iteración-2 de precisión/recall (medida contra el oráculo offline, $0):

  - Léxico VERSIONADO (``LEXICON_VERSION``): stems de dominio genérico
    (``_DOMAIN_STOPSTEMS``) + frames de prosa no-obligacional (capability,
    condicional, definición, UI-locativo, uniformidad, ejemplo, paso numerado).
    El matching pregunta↔span cuenta STEMS DISTINTOS (plural colapsado) y exige
    ≥1 stem distintivo; las filas crudas de tabla exigen token con dígito.
  - Gates de plausibilidad del conflicto declarado↔enumerado (condicional,
    sustantivo de display, comparativa de dos productos, enumeración-basura,
    noun-tie en ties a distancia) y satisfacción por disclosure ESPECÍFICO
    (léxico + ambos valores en la misma línea, no léxico-en-cualquier-parte).
  - Kinds de COMPLETACIÓN answer-gated (la respuesta abrió la unidad servida y
    dejó fuera un miembro): ``enum_alternative`` (hueco único de una enumeración
    con claves), ``limit_pair`` (norma↔restricción del producto adyacentes),
    ``limit_method`` (límite ya citado sin su método con terminales) y
    ``ui_path`` (ruta de menú a medias; números de menú contestados entre
    fragmentos → fail-closed). Ruta SUJETO del universal: exigencia normativa
    sin payload numérico cuyo sustantivo gobernado es stem distintivo de la
    pregunta.
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
    _DISCLOSURE_PATTERNS,
    _FRAG_CITE,
    _is_pipe_row,
    _numbers_in,
    _PIPE_SEP,
    _strip_blockquote_markers,
    atom_good_form,
    atom_satisfied,
    detect_atoms,
    detect_cross_fragment_count_atoms,
    display_parity_ok,
    has_seven_segment_pattern,
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
# must_preserve; la derivación aritmética ANTES que las cláusulas universales:
# un total derivado con operandos citados es más específico que una cláusula
# genérica y no debe morir por cap); también desempata el dedup por span.
_CLASS_PRIORITY = {
    CLASS_SAFETY: 0,
    CLASS_ATTRIBUTION: 1,
    CLASS_RELATION_TABLE: 2,
    CLASS_ARITHMETIC: 3,
    CLASS_UNIVERSAL: 4,
}

# Umbral conservador de aplicabilidad pregunta↔span por clase, contado en STEMS
# DISTINTOS (plural es/en colapsado: «lazo»≈«lazos» cuenta UNA vez — el par
# singular/plural del mismo sustantivo no es evidencia doble). Además de alcanzar
# el umbral, el matching exige ≥1 stem DISTINTIVO (fuera del léxico de dominio
# genérico) — ver `_DOMAIN_STOPSTEMS`; relation_table (filas crudas de tabla)
# exige también un token con dígito (modelo/código/valor): una fila arbitraria
# solo es exigible con anclaje fuerte — silencio > filas arbitrarias.
_THRESHOLD = {
    CLASS_SAFETY: 2,
    CLASS_ATTRIBUTION: 2,
    CLASS_RELATION_TABLE: 3,
    CLASS_UNIVERSAL: 2,
    CLASS_ARITHMETIC: 2,
}

# ─────────────────── léxico de precisión VERSIONADO (s278 iter-2) ───────────────────
# Medido contra el oráculo offline ($0). El criterio de inclusión es GENERAL de
# clase (sustantivos de infraestructura omnipresentes en manuales PCI y verbos de
# capacidad), jamás un identificador de pregunta/documento.
LEXICON_VERSION = "ec_precision_lexicon_v2"

# Sustantivos de dominio tan genéricos que matchear por ellos no liga la evidencia
# a la pregunta (cualquier manual PCI los trae en casi cada página) + verbos de
# capacidad (describen lo que un equipo "hace", no anclan una obligación).
_DOMAIN_STOPSTEMS = frozenset({
    "central", "panel", "sistema", "equipo", "lazo", "cableado", "cable",
    "linea", "zona", "conexion", "instalacion", "salida", "entrada",
    "soporta", "admite", "permite", "dispone", "requiere", "incluye", "utiliza",
})

# Frames de PROSA NO-OBLIGACIONAL (se saltan enteros — la cláusula no es una
# obligación de evidencia aunque lleve cuantificador universal):
#   capability     «puede(n)/permite(n) …» / «es posible …»   posibilidad, no exigencia
#   uniformity     «de igual forma …»      remite a otro procedimiento, sin payload
#   availability   «… siempre disponibles» describe la UI, no una obligación
_FRAME_SKIP_RX = re.compile(
    r"\bpuede(n)?\b|\bpermite(n)?\b|\bes posible\b"
    r"|\bde (igual|la misma) forma\b|\bal igual que\b|\bdisponibles?\b"
)
# Frames por POSICIÓN de arranque de la cláusula (foldeada y sin markup/etiqueta):
#   conditional    «si/cuando/como/al+infinitivo …»  escenario subordinado — no
#                                          declara cardinalidad ni obligación
#   definition     «es el/la …»            definición de un campo/valor de UI
#   ui-locative    «a la izquierda …»      descripción espacial de una pantalla
#   example        «… de este edificio»    prosa de ejemplo trabajado del manual
_CONDITIONAL_START_RX = re.compile(
    r"^(si|cuando|mientras|como|puesto que|ya que|dado que"
    r"|en (el )?caso|al \w+(ar|er|ir))\b"
)
_DEFINITION_START_RX = re.compile(r"^(es|son)\s+(el|la|los|las)\b")
_UI_LOCATIVE_START_RX = re.compile(r"^(a la (izquierda|derecha)|en la parte)\b")
_EXAMPLE_FRAME_RX = re.compile(r"\bde este (edificio|sitio|ejemplo)\b|\bpor ejemplo\b")

# Sustantivos de HARDWARE DE DISPLAY: «pantalla de 7 segmentos» describe el
# display, no un conteo de miembros enumerables (feedback_7segment).
_DISPLAY_NOUN_STEMS = frozenset({"segmento", "digito", "led"})

_MARKUP_LEAD_RX = re.compile(r"^[^a-z0-9]+")
# etiquetas de prosa auxiliar («Nota: …», «Motivo: …», «Regla 2: …») — se pelan
# ANTES de mirar el arranque léxico (la etiqueta no es el frame de la cláusula)
_LABEL_LEAD_RX = re.compile(
    r"^(nota|note|aviso|importante|motivo|regla \d{1,2})\b[:.\s]*"
)
# paso numerado de procedimiento («**1** …», «01 …», «2. …») — un paso no es una
# cláusula universal exigible (pertenece a SU procedimiento, no a la pregunta)
_STEP_LEAD_RX = re.compile(r"^\d")


def _stem(token: str) -> str:
    """Stem plural es/en cerrado (mismo criterio que el `_noun_stem` de
    must_preserve): «lazos»→«lazo», «configuraciones»→«configuracion»."""
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _lead_text(folded: str) -> str:
    """Arranque léxico de la cláusula foldeada, sin markup/viñetas ni etiquetas
    auxiliares («**Nota:** si …» → «si …»)."""
    lead = _MARKUP_LEAD_RX.sub("", folded or "")
    lead = _LABEL_LEAD_RX.sub("", lead)
    return _MARKUP_LEAD_RX.sub("", lead)


def _stems_of(tokens) -> set[str]:
    return {_stem(t) for t in tokens}


def _strong_stems(stems: set[str]) -> set[str]:
    return stems - _DOMAIN_STOPSTEMS


def _has_digit_token(tokens) -> bool:
    return any(any(ch.isdigit() for ch in tok) for tok in tokens)


def _question_gate(cls: str, matched: set[str]) -> bool:
    """Ruta PREGUNTA de aplicabilidad: ≥umbral stems DISTINTOS y ≥1 distintivo
    (fuera del léxico genérico); las filas crudas de tabla exigen además un
    token con dígito (modelo/código/valor)."""
    stems = _stems_of(matched)
    if len(stems) < _THRESHOLD.get(cls, 2):
        return False
    if not _strong_stems(stems):
        return False
    if cls == CLASS_RELATION_TABLE and not _has_digit_token(matched):
        return False
    return True

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


# ──────────────────────── gates GENERALES de conflicto de conteo ────────────────────────

_COUNT_WORD_ALT = "|".join(_COUNT_WORDS)


def _distinct_counts_of_noun(folded_span: str, noun: str) -> set[int]:
    """Valores contados que preceden al MISMO sustantivo en el span («2 salidas …
    4 salidas»): una oración comparativa entre dos productos no es una única
    declaración de cardinalidad reconciliable con una enumeración."""
    stem = _stem(_fold(noun or "").strip())
    if len(stem) < 3:
        return set()
    values: set[int] = set()
    rx = re.compile(rf"\b(\d{{1,4}}|{_COUNT_WORD_ALT})\s+(?:\w+\s+){{0,2}}?({re.escape(stem)}\w*)\b")
    for m in rx.finditer(folded_span):
        raw = m.group(1)
        val = _COUNT_WORDS.get(raw) if not raw.isdigit() else int(raw)
        if val is not None:
            values.add(val)
    return values


def _junk_enumeration(enum_span: str) -> bool:
    """Enumeraciones que no son miembros citables: bloques de código/diagramas
    (mermaid, descripciones «[Diagram …]» del OCR)."""
    folded = _fold(enum_span or "")
    return "```" in (enum_span or "") or "[diagram" in folded


def _enum_noun_tie(noun: str, enum_span: str) -> bool:
    """El sustantivo contado aparece en la enumeración (plural-tolerante) — sin
    dominio compartido, «declara N X y la enumeración lista M» es incoherente."""
    stem = _stem(_fold(noun or "").strip())
    if len(stem) < 3:
        return False
    return any(
        tok == stem or (tok.startswith(stem) and len(tok) <= len(stem) + 2)
        for tok in _content_tokens(enum_span or "", min_len=2)
    )


def _count_conflict_ok(span: str, enum_span: str, noun: str, tie: str) -> bool:
    """Gates de PLAUSIBILIDAD del disclose declarado-vs-enumerado (todas
    generales de clase): (a) una cláusula condicional describe un escenario, no
    declara cardinalidad; (b) los sustantivos de display no cuentan miembros;
    (c) una comparativa de dos productos con el mismo sustantivo no es
    reconciliable; (d) diagramas/código no son enumeraciones; (e) los ties a
    DISTANCIA (sección/fragmento par) exigen el sustantivo en la enumeración —
    el tie adyacente ya lo garantiza por construcción (introduce su bloque)."""
    folded = _fold(span or "")
    if _CONDITIONAL_START_RX.match(_lead_text(folded)):
        return False
    if _stem(_fold(noun or "").strip()) in _DISPLAY_NOUN_STEMS:
        return False
    if _EXAMPLE_FRAME_RX.search(folded):
        return False
    if len(_distinct_counts_of_noun(folded, noun)) >= 2:
        return False
    if _junk_enumeration(enum_span):
        return False
    if tie in ("section", "cross_fragment") and not _enum_noun_tie(noun, enum_span):
        return False
    return True


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
                    _question_gate(CLASS_SAFETY, matched), matched,
                    {"atom": atom},
                ))
            elif family == FAMILY_COUNT and meta.get("conflict"):
                enum_span = str(meta.get("enum_span_text") or "")
                matched = _matched_tokens(question_tokens, (span, enum_span))
                applicable = (
                    _question_gate(CLASS_ATTRIBUTION, matched)
                    and _count_conflict_ok(
                        span, enum_span, str(meta.get("noun") or ""),
                        str(meta.get("tie") or "adjacent"),
                    )
                )
                out.append(_obligation(
                    CLASS_ATTRIBUTION, "declared_vs_enumerated", idx, card, span,
                    start, applicable, matched,
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
        applicable = (
            _question_gate(CLASS_ATTRIBUTION, matched)
            and _count_conflict_ok(
                span, enum_span, str(meta.get("noun") or ""), "cross_fragment"
            )
        )
        out.append(_obligation(
            CLASS_ATTRIBUTION, "declared_vs_enumerated", i, card_map[i], span,
            int(atom.get("span_start") or 0),
            applicable, matched,
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
        applicable = (
            len(_stems_of(matched)) >= max(1, needed)
            and bool(_strong_stems(_stems_of(matched)))
        )
        out.append(_obligation(
            CLASS_ATTRIBUTION, "parameter_two_values",
            first["fragment_number"], first["card"], first["span_text"],
            first["span_start"], applicable, matched,
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
                        _question_gate(CLASS_RELATION_TABLE, matched), matched,
                        {"header": header},
                    ))
            i = j
    return out


_UNIVERSAL_RX = re.compile(
    r"\b(cada|todos?|todas?|ambos|ambas|ningun[oa]?s?|cualquier(?:a)?|siempre"
    r"|nunca|jamas|all|every|each|always|never|both|none|any)\b"
)
_CONJ_RX = re.compile(r"\b(y|e|o|u|and|or)\b")
_RANGE_RX = re.compile(
    r"\bde\s+\d+(?:[.,]\d+)?\s+a\s+\d+(?:[.,]\d+)?\b"
    r"|\bentre\s+\d+(?:[.,]\d+)?\s+y\s+\d+(?:[.,]\d+)?\b"
    r"|\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?"
)
_MODAL_RX = re.compile(r"\b(debe|deben|debera|deberan|must|shall)\b")
# marcador de supervisión/obligación de la ruta SUJETO (verbo normativo de la casa)
_SUPERVISION_RX = re.compile(r"\bse supervisa(n)?\b")
# cuantificador con SUSTANTIVO gobernado (ventana de hasta 3 palabras tras él)
_UNIVERSAL_GOV_RX = re.compile(
    r"\b(?:cada|todos?|todas?|cualquier(?:a)?|ambos|ambas)\b((?:\s+\w+){1,3})"
)


def _universal_frame_skip(folded: str) -> bool:
    lead = _lead_text(folded)
    return bool(
        _CONDITIONAL_START_RX.match(lead)
        or _DEFINITION_START_RX.match(lead)
        or _UI_LOCATIVE_START_RX.match(lead)
        or _STEP_LEAD_RX.match(lead)
        or _FRAME_SKIP_RX.search(folded)
        or _EXAMPLE_FRAME_RX.search(folded)
    )


def _governed_stems(folded: str) -> set[str]:
    """Stems de los sustantivos GOBERNADOS por un cuantificador universal («cada
    circuito de sirena» → {circuito, sirena})."""
    out: set[str] = set()
    for m in _UNIVERSAL_GOV_RX.finditer(folded):
        out.update(_stems_of(_content_tokens(m.group(1))))
    return out


def _universal_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """universal_compound: oración con cualificador universal Y un compuesto
    (conjunción AND/OR, rango numérico, modal de obligación o DOBLE cuantificador
    «CUALQUIER entrada … TODOS los equipos»), con forma-buena de cláusula y sin
    frames no-obligacionales. Aplicable por la ruta PREGUNTA (umbral de stems) o
    por la ruta SUJETO: el sustantivo gobernado por el cuantificador es un stem
    distintivo de la pregunta Y la cláusula es normativa (modal/supervisión) —
    una exigencia universal sobre el sujeto exacto de la pregunta es exigible
    aunque el resto del léxico no solape."""
    out: list[dict[str, Any]] = []
    q_stems = _stems_of(question_tokens)
    for idx, card, text in views:
        for s, e in _sentence_spans(text):
            sentence = text[s:e]
            line_start = text.rfind("\n", 0, s) + 1
            line_end = text.find("\n", s)
            line = text[line_start:line_end if line_end != -1 else len(text)]
            if _is_pipe_row(line):
                continue  # las filas de tabla tienen su clase propia
            folded = _fold(sentence)
            universal_hits = _UNIVERSAL_RX.findall(folded)
            if not universal_hits:
                continue
            if not (
                _CONJ_RX.search(folded)
                or _RANGE_RX.search(folded)
                or _MODAL_RX.search(folded)
                or len(universal_hits) >= 2
            ):
                continue
            if _universal_frame_skip(folded):
                continue
            if not span_good_form(sentence):
                continue
            matched = _matched_tokens(question_tokens, (sentence,))
            applicable = _question_gate(CLASS_UNIVERSAL, matched)
            if not applicable and (
                _MODAL_RX.search(folded) or _SUPERVISION_RX.search(folded)
            ):
                # ruta SUJETO: exigencia universal SIN payload numérico cuyo
                # sustantivo gobernado es un stem distintivo de la pregunta (las
                # cláusulas con números son specs → solo ruta pregunta).
                if not {v for v in _numbers_in(sentence) if v not in (0.0, 1.0)}:
                    subject = (
                        _strong_stems(_governed_stems(folded))
                        & _strong_stems(q_stems)
                    )
                    applicable = bool(subject)
            out.append(_obligation(
                CLASS_UNIVERSAL, "universal_clause", idx, card, sentence, s,
                applicable, matched,
            ))
    return out


# ───────────────── completación de unidades ABIERTAS por la respuesta ─────────────────
# Tres kinds de relation_table cuya aplicabilidad se decide CONTRA LA RESPUESTA
# (gate post-writer `_answer_gate`): la respuesta demostró usar exactamente esa
# unidad servida (enumeración con claves, límite normativo, ruta de menú) y dejó
# fuera UN miembro con payload — completar la relación que la respuesta abrió.

# clave corta de una alternativa: código numérico, rango «De 01 a 30» o guiones
# (incl. tachado OCR «~~- -~~»), seguida de TAB y descripción.
_ALT_KEY_RX = re.compile(
    r"((?:~+[ \t]*)?(?:[Dd]e[ \t]+\d{1,3}[ \t]+a[ \t]+\d{1,3}|\d{1,3}"
    r"|[-–][ ]?[-–])(?:[ \t]*~+)?)\t"
)
_ALT_BREAK = "&#xA;"


def _normalize_alt_key(raw: str) -> str:
    cleaned = raw.replace("~", "").strip()
    return " ".join(cleaned.split())


def _alt_runs(text: str) -> list[list[dict[str, Any]]]:
    """Runs de ≥3 alternativas clave→descripción contiguas (separadas por
    ``&#xA;``/salto de línea) dentro del texto servido."""
    matches = list(_ALT_KEY_RX.finditer(text))
    alts: list[dict[str, Any]] = []
    for pos, m in enumerate(matches):
        desc_start = m.end()
        next_start = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        segment = text[desc_start:next_start]
        cut = len(segment)
        for stop in (_ALT_BREAK, "\n"):
            found = segment.find(stop)
            if found != -1:
                cut = min(cut, found)
        description = segment[:cut]
        if len(_content_tokens(description, min_len=2)) < 2:
            continue
        alts.append({
            "key": _normalize_alt_key(m.group(1)),
            "start": m.start(),
            "end": desc_start + cut,
            "description": description,
        })
    runs: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for alt in alts:
        if current and alt["start"] - current[-1]["end"] > len(_ALT_BREAK) + 2:
            if len(current) >= 3:
                runs.append(current)
            current = []
        current.append(alt)
    if len(current) >= 3:
        runs.append(current)
    return runs


def _enum_alternative_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """relation_table/enum_alternative: enumeración CERRADA de alternativas con
    clave corta; la obligación es cada alternativa (validada contra la respuesta
    en `_answer_gate`: solo actúa la ÚNICA alternativa no cubierta cuando el
    resto de la unidad ya está en la respuesta). El riesgo 7-segmentos se evalúa
    sobre la LÍNEA contenedora (contexto de display) y viaja declarado."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        for run in _alt_runs(text):
            line_start = text.rfind("\n", 0, run[0]["start"]) + 1
            # el contexto de display suele vivir en la línea INTRODUCTORIA de la
            # enumeración → se incluye la línea anterior al evaluar el riesgo
            prev_start = text.rfind("\n", 0, max(line_start - 1, 0)) + 1
            line_end = text.find("\n", run[-1]["end"])
            context = text[prev_start:line_end if line_end != -1 else len(text)]
            risk = has_seven_segment_pattern(context)
            siblings = [
                {"key": alt["key"], "description": alt["description"]} for alt in run
            ]
            for alt in run:
                span = text[alt["start"]:alt["end"]]
                matched = _matched_tokens(question_tokens, (span,))
                out.append(_obligation(
                    CLASS_RELATION_TABLE, "enum_alternative", idx, card, span,
                    alt["start"], True, matched,
                    {
                        "answer_gated": True,
                        "alt_key": alt["key"],
                        "alt_description": alt["description"],
                        "siblings": siblings,
                        "seven_segment_context": risk,
                    },
                ))
    return out


# límite NORMATIVO (norma) seguido del límite MÁS RESTRICTIVO del producto:
# «… un máximo de 32 equipos …. En la central X, no se debe … más de 25 equipos …»
_LIMIT_MAX_RX = re.compile(rf"\bmaximo de (\d{{1,4}}|{_COUNT_WORD_ALT})\s+(\w+)")
_LIMIT_NOMORE_RX = re.compile(r"\bno se debe\b[^.]{0,60}?\bmas de (\d{1,4})\s+(\w+)")


def _limit_pair_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """relation_table/limit_pair: dos oraciones ADYACENTES donde la primera fija
    un máximo normativo de N X y la segunda restringe «no se debe … más de M X»
    (mismo sustantivo, M≠N) — la relación norma↔restricción-del-producto viaja
    ENTERA o no viaja (la respuesta que cita solo M pierde el marco N)."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        spans = _sentence_spans(text)
        for pos in range(len(spans) - 1):
            s1, e1 = spans[pos]
            s2, e2 = spans[pos + 1]
            if s2 - e1 > 3:
                continue  # solo oraciones contiguas de la misma línea/párrafo
            first = _fold(text[s1:e1])
            second = _fold(text[s2:e2])
            m1 = _LIMIT_MAX_RX.search(first)
            m2 = _LIMIT_NOMORE_RX.search(second)
            if not m1 or not m2:
                continue
            raw_n = m1.group(1)
            n = _COUNT_WORDS.get(raw_n) if not raw_n.isdigit() else int(raw_n)
            m = int(m2.group(1))
            if n is None or n == m:
                continue
            if _stem(m1.group(2)) != _stem(m2.group(2)):
                continue
            span = text[s1:e2]
            matched = _matched_tokens(question_tokens, (span,))
            out.append(_obligation(
                CLASS_RELATION_TABLE, "limit_pair", idx, card, span, s1,
                _question_gate(CLASS_ATTRIBUTION, matched), matched,
                {"limit_values": sorted({float(n), float(m)})},
            ))
    return out


# límite «no debe superar los N …» seguido del MÉTODO de comprobación con
# terminales («uniendo B+ y B− y midiendo en A+ y A−»)
_LIMIT_CEILING_RX = re.compile(r"\bno debe superar (?:los |las )?(\d{1,4}(?:[.,]\d+)?)")
_METHOD_VERB_RX = re.compile(r"\b(comprobarlo|compruebe|comprobar|medir|mida|midiendo)\b")
_TERMINAL_CODE_RX = re.compile(r"\b([A-Za-z]{1,2}[+-])(?![\w])")


def _limit_method_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """relation_table/limit_method: límite normativo + su método de comprobación
    con códigos de terminal en la oración siguiente. Answer-gated: solo aplica si
    la respuesta YA cita el número del límite (abrió la relación) y se satisface
    solo cuando los códigos de terminal del método están presentes."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        spans = _sentence_spans(text)
        for pos in range(len(spans) - 1):
            s1, e1 = spans[pos]
            s2, e2 = spans[pos + 1]
            if s2 - e1 > 3:
                continue
            first = _fold(text[s1:e1])
            limit = _LIMIT_CEILING_RX.search(first)
            if not limit:
                continue
            method = text[s2:e2]
            codes = sorted({m.group(1) for m in _TERMINAL_CODE_RX.finditer(method)})
            if not _METHOD_VERB_RX.search(_fold(method)) or len(codes) < 2:
                continue
            start = s1
            if pos > 0:
                s0, e0 = spans[pos - 1]
                prev = _fold(text[s0:e0])
                if (
                    s1 - e0 <= 3
                    and _UNIVERSAL_RX.search(prev)
                    and _MODAL_RX.search(prev)
                    and not _universal_frame_skip(prev)
                ):
                    start = s0  # agrupar la cláusula universal adyacente (d/e)
            span = text[start:e2]
            matched = _matched_tokens(question_tokens, (span,))
            out.append(_obligation(
                CLASS_RELATION_TABLE, "limit_method", idx, card, span, start,
                True, matched,
                {
                    "answer_gated": True,
                    "limit_value": float(limit.group(1).replace(",", ".")),
                    "terminal_codes": codes,
                },
            ))
    return out


# ruta de menú/pantalla con nombres «entre comillas angulares»
_UI_NAME_RX = re.compile(r"«([^«»\n]{2,60})»")
_UI_VERB_RX = re.compile(
    r"\b(vaya|acceda|seleccione|seleccionar|pulse|elija|desde el menu|"
    r"en la pantalla|a la pantalla)\b"
)


_MENU_NUMBER_RX = re.compile(r"^(\d{1,2})\s*:\s*(.+)$")


def _contested_menu_number(name: str, views) -> bool:
    """Un nombre de UI NUMERADO («7: Causa y Efecto») está CONTESTADO si el mismo
    nombre aparece con OTRO número en cualquier fragmento servido (revisiones
    distintas del menú): el número de acceso es un conflicto ya declarable por el
    conflict_guard — anexarlo lo re-afirmaría (fail-closed: se omite la forma
    numerada; la forma sin número sigue siendo anexable)."""
    m = _MENU_NUMBER_RX.match(_fold(name).strip())
    if not m:
        return False
    base = " ".join(m.group(2).split())
    if len(base) < 3:
        return False
    numbers: set[str] = set()
    rx = re.compile(rf"(\d{{1,2}})\s*:\s*{re.escape(base)}")
    for _idx, _card, text in views:
        numbers.update(match.group(1) for match in rx.finditer(_fold(text)))
    return len(numbers) >= 2


def _ui_path_obligations(question_tokens: set[str], views) -> list[dict[str, Any]]:
    """relation_table/ui_path: oración procedimental con ≥2 nombres de UI
    «entre angulares». Answer-gated: aplica solo si la respuesta ya nombra parte
    de la ruta (≥1 nombre presente) y le falta otra (≥1 ausente) — completar la
    ruta de acceso que la respuesta dejó a medias. Un nombre con número de menú
    CONTESTADO entre fragmentos servidos anula la obligación (fail-closed)."""
    out: list[dict[str, Any]] = []
    for idx, card, text in views:
        for s, e in _sentence_spans(text):
            sentence = text[s:e]
            names = [m.group(1) for m in _UI_NAME_RX.finditer(sentence)]
            if len(set(names)) < 2:
                continue
            if not _UI_VERB_RX.search(_fold(sentence)):
                continue
            if any(_contested_menu_number(name, views) for name in names):
                continue
            matched = _matched_tokens(question_tokens, (sentence,))
            out.append(_obligation(
                CLASS_RELATION_TABLE, "ui_path", idx, card, sentence, s,
                True, matched,
                {"answer_gated": True, "ui_names": sorted(set(names))},
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
    ledger.extend(_enum_alternative_obligations(question_tokens, views))
    ledger.extend(_limit_pair_obligations(question_tokens, views))
    ledger.extend(_limit_method_obligations(question_tokens, views))
    ledger.extend(_ui_path_obligations(question_tokens, views))
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

def _lax_match(a: str, b: str) -> bool:
    """Tolerancia morfológica SOLO para satisfacción/cobertura (jamás para la
    aplicabilidad — allí ampliaría el matching pregunta↔span): igualdad, plural
    es/en o prefijo compartido de ≥5 chars («asociar»≈«asocia», «inhibido»≈
    «inhibición»)."""
    if _token_match(a, b):
        return True
    return len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]


def _coverage(span: str, answer_tokens: set[str]) -> float:
    own_tokens = set(_content_tokens(span))
    if not own_tokens:
        return 1.0
    present = sum(
        1 for t in own_tokens if any(_lax_match(t, a) for a in answer_tokens)
    )
    return present / len(own_tokens)


def _specific_disclosure_line(answer_text: str, declared, enumerated) -> bool:
    """Disclosure ESPECÍFICO del conflicto: una misma línea de la respuesta trae
    el léxico de disclosure de la casa Y AMBOS valores. (El léxico a secas en
    cualquier parte de la respuesta —p.ej. una nota sobre OTRO hecho— no
    satisface: era el falso-satisfecho que ocultaba el conflicto.)"""
    if declared is None or enumerated is None:
        return False
    needed = {float(declared), float(enumerated)}
    for line in (answer_text or "").splitlines():
        folded = _fold(line)
        if not any(pat in folded for pat in _DISCLOSURE_PATTERNS):
            continue
        if needed <= _numbers_in(line):
            return True
    return False


def _key_in_text(key: str, folded_answer: str) -> bool:
    """La clave de una alternativa presente en la respuesta. Claves con dígitos:
    TODOS sus grupos de dígitos como token («de 01 a 30» ≈ «entre 01 y 30»);
    claves sin dígitos («--»): el token exacto con límites no alfanuméricos
    (jamás dentro de «---» de markdown)."""
    folded_key = _fold(key).strip()
    if not folded_key:
        return False
    digit_groups = re.findall(r"\d+", folded_key)
    if digit_groups:
        return all(
            re.search(rf"(?<!\d){re.escape(group)}(?!\d)", folded_answer)
            for group in digit_groups
        )
    pattern = rf"(?<![\w\-–]){re.escape(folded_key)}(?![\w\-–])"
    return re.search(pattern, folded_answer) is not None


def _alternative_covered(alt: dict, folded_answer: str,
                         answer_tokens: set[str]) -> bool:
    if not _key_in_text(str(alt.get("key") or ""), folded_answer):
        return False
    return _coverage(str(alt.get("description") or ""), answer_tokens) >= 0.5


def obligation_satisfied(ob: dict[str, Any], answer_text: str) -> bool:
    """¿La respuesta YA cubre la obligación? Las clases basadas en átomos de
    must_preserve delegan en su contrato ``atom_satisfied``, EXCEPTO el F-COUNT
    en conflicto: exige disclosure ESPECÍFICO (léxico + ambos valores en la
    misma línea), no el léxico de disclosure en cualquier parte."""
    if not isinstance(answer_text, str) or not answer_text.strip():
        return False
    meta = ob.get("meta") or {}
    kind = ob.get("kind")
    if kind == "declared_vs_enumerated":
        return _specific_disclosure_line(
            answer_text, meta.get("declared"), meta.get("enumerated")
        )
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
    answer_tokens = set(_content_tokens(clean))
    folded = _fold(clean)
    if kind == "enum_alternative":
        return _alternative_covered(
            {"key": meta.get("alt_key"), "description": meta.get("alt_description")},
            folded, answer_tokens,
        )
    if kind == "limit_method":
        return all(
            _key_in_text(code, folded) for code in meta.get("terminal_codes") or []
        )
    if kind == "limit_pair":
        # la relación son los VALORES norma↔restricción: cubierta si la
        # respuesta trae todos los números del par (la prosa exacta no se exige)
        own = {v for v in _numbers_in(ob.get("span_text") or "") if v not in (0.0, 1.0)}
        return own <= numbers
    if kind == "ui_path":
        return all(_fold(name) in folded for name in meta.get("ui_names") or [])
    # relation_table / universal_compound genéricos: números propios (excl. 0/1
    # por ubicuidad) presentes Y ≥80% de los tokens de contenido del span.
    span = ob.get("span_text") or ""
    own_numbers = {v for v in _numbers_in(span) if v not in (0.0, 1.0)}
    if not own_numbers <= numbers:
        return False
    return _coverage(span, answer_tokens) >= 0.8


def _answer_gate(ob: dict[str, Any], answer_text: str) -> bool:
    """Gate de aplicabilidad CONTRA LA RESPUESTA para los kinds de completación
    (``answer_gated``): la obligación solo actúa si la respuesta demostró usar
    exactamente esa unidad servida y dejó fuera este miembro.

      enum_alternative  todas las alternativas hermanas cubiertas MENOS esta
                        (≥2 cubiertas, hueco único) — completar la enumeración
      limit_method      la respuesta ya cita el número del límite
      ui_path           la respuesta ya nombra parte de la ruta (≥1 presente)
    """
    meta = ob.get("meta") or {}
    if not meta.get("answer_gated"):
        return True
    clean = _FRAG_CITE.sub(" ", answer_text or "")
    folded = _fold(clean)
    answer_tokens = set(_content_tokens(clean))
    kind = ob.get("kind")
    if kind == "enum_alternative":
        siblings = meta.get("siblings") or []
        own_key = str(meta.get("alt_key") or "")
        covered = [
            alt for alt in siblings
            if _alternative_covered(alt, folded, answer_tokens)
        ]
        uncovered = [
            alt for alt in siblings
            if not _alternative_covered(alt, folded, answer_tokens)
        ]
        return (
            len(covered) >= 2
            and len(uncovered) == 1
            and str(uncovered[0].get("key") or "") == own_key
        )
    if kind == "limit_method":
        return float(meta.get("limit_value") or 0) in _numbers_in(clean)
    if kind == "ui_path":
        names = meta.get("ui_names") or []
        present = [n for n in names if _fold(n) in folded]
        return 0 < len(present) < len(names)
    return True


# ─────────────────────────────── render ───────────────────────────────

_STRUCK_RX = re.compile(r"~~(.*?)~~")
_LETTER_RX = re.compile(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]")


def _apply_struck_ocr(text: str) -> str:
    """Segmentos TACHADOS por la extracción (``~~…~~``): un tachado de solo
    símbolos/dígitos conserva su contenido (el marcador es formato); el PRIMER
    tachado CON letras corta el display — es superficie que la propia extracción
    marcó como no fiable (feedback_7segment: jamás re-afirmar una transliteración
    dudosa; el hash del receipt sigue anclando el span original y el riesgo viaja
    declarado en ``seven_segment_risk``)."""
    if "~~" not in text:
        return text
    parts: list[str] = []
    pos: int | None = 0
    for m in _STRUCK_RX.finditer(text):
        if _LETTER_RX.search(m.group(1)):
            parts.append(text[pos:m.start()])
            pos = None
            break
        parts.append(text[pos:m.start()] + m.group(1))
        pos = m.end()
    if pos is not None:
        parts.append(text[pos:])
    return "".join(parts).strip()


def _display_span(span: str) -> str:
    text = _apply_struck_ocr(_strip_blockquote_markers(span).strip())
    return " ".join(text.split())


def _base_action(ob: dict[str, Any], action: str) -> dict[str, Any]:
    out = {
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
    # feedback_7segment: superficie de display en el span citado (o en su LÍNEA
    # contenedora, para alternativas de enumeración extraídas de una celda con
    # contexto de display) → riesgo DECLARADO en el receipt (el span viaja
    # verbatim; jamás se reinterpreta un código 7-seg).
    if has_seven_segment_pattern(ob.get("span_text") or "") or (
        (ob.get("meta") or {}).get("seven_segment_context")
    ):
        out["seven_segment_risk"] = True
    return out


def _display_parity_blocked(ob: dict[str, Any], answer_text: str) -> bool:
    """Paridad de display 7-seg para obligaciones basadas en átomos de must_preserve
    (contrato importado, no re-derivado): un átomo con ``seven_segment_risk`` solo es
    accionable si el borrador YA nombra sus tokens display (``display_parity_ok``) —
    el anexo no añade superficie OCR nueva. Las clases propias del contrato no pasan
    por aquí (declaran el riesgo en el receipt, ver ``_base_action``)."""
    atom = (ob.get("meta") or {}).get("atom")
    if not isinstance(atom, dict):
        return False
    if not (atom.get("meta") or {}).get("seven_segment_risk"):
        return False
    return not display_parity_ok(atom, answer_text)


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
        if not informative_span(span_b):
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
    display = _display_span(span)
    if len(_content_tokens(display, min_len=2)) < 2:
        return None  # display vaciado por tachado OCR → fail-closed
    line = f'- "{display}" {cite["label"]}'
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
        "skipped_display_parity": 0,
        "skipped_answer_gate": 0,
        "lexicon_version": LEXICON_VERSION,
    }
    if not answer_text.strip() or not served_cards:
        receipt["reason"] = "empty_answer_or_no_served_context"
        return {"text": answer_text, "actions": [], "receipt": receipt}
    views = _views(served_cards)
    view_map = {idx: text for idx, _card, text in views}
    card_map = {idx: card for idx, card, _text in views}
    ledger = build_obligation_ledger(question, served_cards)
    applicable = []
    for ob in ledger:
        if not ob["applicable"]:
            continue
        if not _answer_gate(ob, answer_text):
            receipt["skipped_answer_gate"] += 1
            continue
        applicable.append(ob)
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
        if _display_parity_blocked(ob, answer_text):
            receipt["skipped_display_parity"] += 1
            continue
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
