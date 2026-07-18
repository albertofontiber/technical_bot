"""(S269 Track 2 · flag MUST_PRESERVE_CONTRACT=off|on, default off) Contrato de átomos
must-preserve con render por postcondición.

Diseño canónico: evals/s269_synthesis_portfolio_design_v1.md §1 (v2 dúo-adjudicado) sobre las
4 familias genéricas de evals/s243_synthesis_miss_causal_taxonomy_v1.yaml:

  F-RANGE     rangos acotados (valor+unidad+extremos+paso+scope juntos)
  F-BUNDLE    miembro↔cabecera-padre (headings markdown + schemas de definición en lista)
  F-MANDATORY léxico cerrado bilingüe de lenguaje obligatorio/peligro
  F-COUNT     conteo declarado vs miembros enumerados (inconsistencia → DISCLOSE)

Mecanismo (post-generación, pre-return, sobre los fragmentos SERVIDOS):
  detect_atoms → bind_atoms (exigibilidad: fragmento citado + el borrador toca el claim
  ancla) → attest_identity (el doc del fragmento pertenece a la identidad resuelta de la
  query vía el catálogo gobernado DEC-074/090; sin resolución → el anexo NO actúa,
  fail-closed del anexo / fail-open de la respuesta) → render_appendix (spans VERBATIM con
  cita [Fn], cap 4, disclosure ante contradicción numérica). Puro código, cero LLM.

Garantía real (dúo C3/F4): la monotonía garantiza no-borrado bajo el matcher; NO garantiza
ausencia de contradicción — por eso el chequeo de contradicción degrada a disclosure
("Nota: el manual también indica ...") y el gate de Etapa 2 cuenta conflictos nuevos.

Riesgo OCR declarado (§3.4, feedback_7segment): los patrones de display 7-segmentos
(tokens tipo ``r.I`` / ``t.A``) quedan FUERA del anexo automático.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from .catalog import _fold

logger = logging.getLogger(__name__)

Atom = dict[str, Any]

FAMILY_RANGE = "F-RANGE"
FAMILY_BUNDLE = "F-BUNDLE"
FAMILY_MANDATORY = "F-MANDATORY"
FAMILY_COUNT = "F-COUNT"
FAMILIES = (FAMILY_RANGE, FAMILY_BUNDLE, FAMILY_MANDATORY, FAMILY_COUNT)

APPENDIX_HEADER = "Información adicional del manual:"
APPENDIX_CAP = 4


def contract_enabled() -> bool:
    """Flag estricto default-off (patrón ``_strict_on_off`` de src/config.py). Se relee en
    runtime (patrón GENERATOR_PROMPT_VARIANT) para poder togglear A/B en un mismo proceso;
    con flag off el pipeline es byte-idéntico (apply devuelve el MISMO objeto respuesta)."""
    from ..config import _strict_on_off

    return _strict_on_off("MUST_PRESERVE_CONTRACT")


# ─────────────────────────── utilidades de texto ───────────────────────────

_STOPWORDS = {
    # es
    "para", "como", "este", "esta", "estos", "estas", "cual", "cuales", "cuando",
    "donde", "desde", "hasta", "entre", "tiene", "tienen", "sobre", "cada", "todos",
    "todas", "segun", "debe", "deben", "antes", "despues", "puede", "pueden", "solo",
    "tambien", "mismo", "misma", "siguiente", "siguientes", "manual", "seccion",
    # en
    "that", "this", "with", "from", "into", "have", "been", "than", "then", "when",
    "where", "which", "while", "must", "shall", "should", "will", "before", "after",
    "also", "each", "other", "only", "more", "less", "very", "same", "following",
}

_FRAG_CITE = re.compile(r"\[F\d{1,2}\]")
_WORD_RX = re.compile(r"[a-z0-9]+")


def _content_tokens(text: str, min_len: int = 3) -> list[str]:
    """Tokens de contenido folded (minúsculas sin acentos), sin stopwords ni dígitos puros."""
    out: list[str] = []
    for tok in _WORD_RX.findall(_fold(text or "")):
        if len(tok) < min_len or tok in _STOPWORDS or tok.isdigit():
            continue
        out.append(tok)
    return out


_COUNT_WORDS = {
    "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
}

_NUM_TOKEN = re.compile(r"\d+(?:[.,]\d+)?")


def _num_val(raw: str) -> float:
    return float(raw.replace(",", "."))


def _numbers_in(text: str) -> set[float]:
    """Valores numéricos del texto (dígitos, normalizados) + palabras-número uno..doce.
    Se excluyen 0 y 1 en la vía de BINDING por ubicuidad ("paso 1") — ver _binds."""
    vals = {_num_val(m) for m in _NUM_TOKEN.findall(text or "")}
    folded = _fold(text or "")
    for word, val in _COUNT_WORDS.items():
        if re.search(rf"\b{word}\b", folded):
            vals.add(float(val))
    return vals


def _line_spans(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    pos = 0
    for line in (text or "").split("\n"):
        out.append((pos, pos + len(line), line))
        pos += len(line) + 1
    return out


_SENT_BOUNDARY = re.compile(r"(?<=[.!?;])\s+")


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Spans (start, end) de oraciones: por línea y, dentro de línea, por puntuación
    final + espacio (los decimales "1,5"/"1.5" no parten porque no llevan espacio)."""
    spans: list[tuple[int, int]] = []
    for start, _end, line in _line_spans(text):
        offset = 0
        for m in _SENT_BOUNDARY.finditer(line):
            if line[offset:m.start()].strip():
                spans.append((start + offset, start + m.start()))
            offset = m.end()
        if line[offset:].strip():
            spans.append((start + offset, start + len(line.rstrip())))
    return spans


# Riesgo OCR 7-segmentos (feedback_7segment): tokens cortos con puntos tipo ``r.I`` /
# ``t.A`` / ``F.1``. Exige mayúscula o mezcla dígito+letra para NO cazar abreviaturas
# minúsculas ("p.ej") ni decimales puros ("1.5").
_SEVEN_SEG_TOKEN = re.compile(
    r"(?<![\w.])(?:[0-9A-Za-z]{1,2}\.){1,2}[0-9A-Za-z]{1,2}(?![\w.])"
)


def has_seven_segment_pattern(text: str) -> bool:
    for m in _SEVEN_SEG_TOKEN.finditer(text or ""):
        tok = m.group()
        if all(c.isdigit() or c == "." for c in tok):
            continue  # decimal puro
        if any(c.isupper() for c in tok) or (
            any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)
        ):
            return True
    return False


# ─────────────────────────────── F-RANGE ───────────────────────────────
# NOTA (diseño §1.1): el sub-caso de QUALIFIER SEMÁNTICO (p.ej. "los valores medidos se
# almacenan como valores NOMINALES de referencia al 100%") NO es detectable por estructura
# numérica y queda declarado como LLM-assist futuro (Haiku, barato, solo si el determinista
# no dispara). TODO(s269 §1.1): brazo LLM-assist del qualifier semántico — NO implementado
# aquí a propósito; este módulo es 100% determinista.

_UNITS = [
    "%", "°c", "ºc", "°f", "ºf",
    "segundos", "segundo", "seg", "ms", "milisegundos", "s",
    "minutos", "minuto", "min", "horas", "hora", "h",
    "voltios", "vcc", "vdc", "vca", "vac", "kv", "mv", "v",
    "amperios", "ma", "a", "ohmios", "ohms", "ohmio", "ohm", "ω", "kω", "kohm",
    "vatios", "kw", "w", "va", "khz", "hz", "db", "dba",
    "mm", "cm", "km", "m", "metros", "metro",
    "mbar", "bar", "kpa", "pa", "litros", "lpm", "l/min",
]
_UNIT_ALT = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
_NUM = r"\d+(?:[.,]\d+)?"

# "de X a Y [unidad]" / "entre X y Y" / "from X to Y"
_RX_DE_A = re.compile(
    rf"\b(?:de|desde|from|entre|between)\s+({_NUM})\s*({_UNIT_ALT})?"
    rf"\s+(?:a|hasta|y|to|and)\s+({_NUM})\s*({_UNIT_ALT})?(?![a-z0-9])",
    re.IGNORECASE,
)
# "X–Y unidad" (unidad OBLIGATORIA: sin ella un código de modelo tipo CAD-150-8 dispararía)
_RX_DASH = re.compile(
    rf"\b({_NUM})\s*[–—-]\s*({_NUM})\s*({_UNIT_ALT})(?![a-z0-9])", re.IGNORECASE
)
# tolerancia simétrica "±X %"
_RX_PM = re.compile(
    rf"(?:±|\+/-|\+/−)\s*({_NUM})\s*({_UNIT_ALT})?(?![a-z0-9])", re.IGNORECASE
)
# paso: "intervalos de X" / "en pasos de X" / "in steps of X"
_RX_STEP = re.compile(
    rf"\b(?:intervalos?\s+de|(?:en\s+)?pasos?\s+de|incrementos?\s+de|"
    rf"in\s+steps?\s+of|steps?\s+of|increments?\s+of)\s+({_NUM})\s*({_UNIT_ALT})?(?![a-z0-9])",
    re.IGNORECASE,
)
# scope adyacente: identificadores de configuración ("posiciones A11 a C32") en la oración
_RX_SCOPE_ID = re.compile(r"\b[A-Z]{1,3}\d{1,3}\b")
_RX_SCOPE_WORD = re.compile(
    r"\b(posici[oó]n(?:es)?|switch(?:es)?|dip|selector(?:es)?|"
    r"microinterruptor(?:es)?|jumpers?|puentes?)\b",
    re.IGNORECASE,
)


def _detect_range(text: str) -> list[Atom]:
    atoms: list[Atom] = []
    for s_start, s_end in _sentence_spans(text):
        sentence = text[s_start:s_end]
        matches: list[dict[str, Any]] = []
        for m in _RX_DE_A.finditer(sentence):
            matches.append({
                "lower": _num_val(m.group(1)), "upper": _num_val(m.group(3)),
                "unit": (m.group(4) or m.group(2) or "").lower() or None,
            })
        for m in _RX_DASH.finditer(sentence):
            matches.append({
                "lower": _num_val(m.group(1)), "upper": _num_val(m.group(2)),
                "unit": m.group(3).lower(),
            })
        for m in _RX_PM.finditer(sentence):
            matches.append({
                "lower": None, "upper": None, "tolerance": _num_val(m.group(1)),
                "unit": (m.group(2) or "").lower() or None,
            })
        if not matches:
            continue
        if has_seven_segment_pattern(sentence):
            # Exclusión del anexo automático (riesgo OCR/display declarado §3.4).
            continue
        step_m = _RX_STEP.search(sentence)
        scope_ids = _RX_SCOPE_ID.findall(sentence)
        scope_word = _RX_SCOPE_WORD.search(sentence)
        scope = scope_ids if (scope_word or len(scope_ids) >= 2) else []
        for info in matches:
            meta = {
                "lower": info.get("lower"), "upper": info.get("upper"),
                "unit": info.get("unit"),
                "tolerance": info.get("tolerance"),
                "step": _num_val(step_m.group(1)) if step_m else None,
                "step_unit": (step_m.group(2) or "").lower() or None if step_m else None,
                "scope": scope,
            }
            anchors = _content_tokens(sentence)
            for key in ("lower", "upper", "step", "tolerance"):
                if meta.get(key) is not None:
                    anchors.append(_format_num(meta[key]))
            atoms.append({
                "family": FAMILY_RANGE,
                "span_start": s_start, "span_end": s_end,
                "span_text": text[s_start:s_end],
                "anchor_tokens": _dedup(anchors),
                "meta": meta,
            })
    return atoms


def _format_num(val: float) -> str:
    return str(int(val)) if float(val).is_integer() else str(val)


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


# ─────────────────────────────── F-BUNDLE ───────────────────────────────
# Parser PROPIO de headings markdown + schemas de definición en lista. NO usa
# evidence_units_v2: esa infraestructura solo empareja cabecera+fila de TABLAS y no cubre
# pestañas/listas/schemas (hallazgo M6 del dúo, diseño §1.1).

_HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
_DEFLINE = re.compile(
    r"^\s*(?:[-•*·◦]\s*)?\**([A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9][^:\n]{0,60}?)\**\s*:\s+(\S.*)$"
)
_BULLET = re.compile(r"^\s*(?:[-•*·◦]|\d{1,2}[.)])\s+(\S.*)$")


def _detect_bundle(text: str) -> list[Atom]:
    lines = _line_spans(text)
    atoms: list[Atom] = []
    heading: str | None = None
    heading_span: tuple[int, int] | None = None
    heading_adjacent = False  # solo blancos entre el heading y el run actual
    run: list[dict[str, Any]] = []
    run_def_count = 0

    def flush() -> None:
        nonlocal run, run_def_count
        if len(run) >= 2 and (heading or run_def_count >= 2):
            span_start = run[0]["start"]
            span_end = run[-1]["end"]
            if heading and heading_span and heading_adjacent:
                span_start = heading_span[0]
            members = [r["label"] for r in run]
            anchors = _content_tokens(heading or "")
            for r in run:
                anchors.extend(_content_tokens(r["label"], min_len=2)[:3])
                anchors.extend(_content_tokens(r.get("desc") or "")[:2])
            atoms.append({
                "family": FAMILY_BUNDLE,
                "span_start": span_start, "span_end": span_end,
                "span_text": text[span_start:span_end],
                "anchor_tokens": _dedup(anchors),
                "meta": {
                    "header": heading or "",
                    "members": members,
                    "member_count": len(members),
                    "seven_segment_risk": has_seven_segment_pattern(
                        text[span_start:span_end]
                    ),
                },
            })
        run = []
        run_def_count = 0

    blanks_in_run = 0
    for start, end, line in lines:
        h = _HEADING.match(line)
        if h:
            flush()
            heading = h.group(2).strip()
            heading_span = (start, end)
            heading_adjacent = True
            blanks_in_run = 0
            continue
        if not line.strip():
            if run:
                blanks_in_run += 1
                if blanks_in_run > 1:
                    flush()
                    blanks_in_run = 0
            continue
        d = _DEFLINE.match(line)
        b = _BULLET.match(line)
        if d:
            run.append({"start": start, "end": end,
                        "label": d.group(1).strip(), "desc": d.group(2).strip()})
            run_def_count += 1
            blanks_in_run = 0
            continue
        if b:
            item = b.group(1).strip()
            label = " ".join(item.split()[:4])
            run.append({"start": start, "end": end, "label": label, "desc": item})
            blanks_in_run = 0
            continue
        # línea de prosa: cierra el run y rompe la adyacencia heading↔run
        flush()
        heading_adjacent = False
        blanks_in_run = 0
    flush()
    return atoms


# ────────────────────────────── F-MANDATORY ──────────────────────────────
# Léxico CERRADO bilingüe (diseño §1.1). "antes de"/"before" NUNCA como gatillo solo
# (hallazgo F8 del dúo: frecuencia altísima → FP masivo): solo cuentan colocados con un
# término obligatorio ("debe(n)"/"must") en la MISMA oración.

_MANDATORY_TERMS = (
    # es (formas foldeadas: sin acentos)
    "imprescindible", "obligatorio", "obligatoria", "obligatorios", "obligatorias",
    "nunca", "jamas", "advertencia", "atencion", "peligro", "evite", "eviten",
    # en
    "mandatory", "never", "warning", "caution", "danger",
)
_MANDATORY_PHRASES = (
    "de vital importancia", "es vital", "en ningun caso", "must not", "it is essential",
)


def _trigger_present(trigger: str, folded: str) -> bool:
    """Un gatillo del léxico está presente en un texto YA foldeado."""
    if trigger == "debe(n)+antes de":
        return bool(re.search(r"\bdebe(n)?\b", folded)) and "antes de" in folded
    if trigger == "must+before":
        return bool(
            re.search(r"\bmust\b", folded) and re.search(r"\bbefore\b", folded)
        )
    if " " in trigger:
        return trigger in folded
    return bool(re.search(rf"\b{trigger}\b", folded))


def _mandatory_triggers(sentence: str) -> list[str]:
    folded = _fold(sentence)
    triggers = [
        term for term in (*_MANDATORY_TERMS, *_MANDATORY_PHRASES)
        if _trigger_present(term, folded)
    ]
    # co-ocurrencias: "debe(n) ... antes de" / "before ... must"
    for compound in ("debe(n)+antes de", "must+before"):
        if _trigger_present(compound, folded):
            triggers.append(compound)
    return triggers


def _detect_mandatory(text: str) -> list[Atom]:
    atoms: list[Atom] = []
    for s_start, s_end in _sentence_spans(text):
        sentence = text[s_start:s_end]
        triggers = _mandatory_triggers(sentence)
        if not triggers:
            continue
        atoms.append({
            "family": FAMILY_MANDATORY,
            "span_start": s_start, "span_end": s_end,
            "span_text": sentence,
            "anchor_tokens": _dedup(_content_tokens(sentence)),
            "meta": {
                "triggers": triggers,
                "seven_segment_risk": has_seven_segment_pattern(sentence),
            },
        })
    return atoms


# ─────────────────────────────── F-COUNT ───────────────────────────────

_RX_COUNT = re.compile(
    r"\b(uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce"
    r"|[1-9]|1[0-2])\s+([a-záéíóúñü]{3,}s)\b",
    re.IGNORECASE,
)
_ITEM_LINE = re.compile(r"^\s*(?:[-•*·◦]|\d{1,2}[.)])\s+\S")
_PIPE_SEP = re.compile(r"^[\s|:\-]+$")

_COUNT_WINDOW = 300  # chars entre el conteo declarado y el inicio de la enumeración


def _is_pipe_row(line: str) -> bool:
    return line.count("|") >= 2 and bool(line.strip())


def _enumeration_blocks(text: str) -> list[tuple[int, int, int, str]]:
    """Bloques (start, end, n_miembros, kind): listas con viñetas/numeradas, filas de
    tabla, o UNA línea de columnas separadas por ``|``."""
    lines = _line_spans(text)
    blocks: list[tuple[int, int, int, str]] = []
    i = 0
    while i < len(lines):
        start, _end, line = lines[i]
        if _is_pipe_row(line):
            j = i
            data_rows: list[int] = []
            has_sep = False
            while j < len(lines) and _is_pipe_row(lines[j][2]):
                if _PIPE_SEP.match(lines[j][2]):
                    has_sep = True
                else:
                    data_rows.append(j)
                j += 1
            if len(data_rows) >= 2:
                # con separador tras la primera fila ⇒ fila 1 = cabecera
                count = len(data_rows) - 1 if has_sep else len(data_rows)
                blocks.append((start, lines[j - 1][1], count, "table_rows"))
            elif len(data_rows) == 1:
                cells = [c for c in lines[data_rows[0]][2].split("|") if c.strip()]
                if len(cells) >= 2:
                    blocks.append((start, lines[j - 1][1], len(cells), "pipe_columns"))
            i = j
            continue
        if _ITEM_LINE.match(line):
            j = i
            items = 0
            last = i
            blanks = 0
            while j < len(lines):
                l = lines[j][2]
                if _ITEM_LINE.match(l):
                    items += 1
                    last = j
                    blanks = 0
                    j += 1
                    continue
                if not l.strip() and blanks == 0:
                    blanks = 1
                    j += 1
                    continue
                break
            if items >= 2:
                blocks.append((start, lines[last][1], items, "list_items"))
            i = j
            continue
        i += 1
    return blocks


_ALPHA_RX = re.compile(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]")
# el número precedido por estas palabras es una REFERENCIA o FRECUENCIA, no un conteo
_COUNT_REF_WORD = re.compile(
    r"\b(tabla|table|figura|figure|fig|secci[oó]n|section|cap[ií]tulo|chapter|"
    r"p[aá]gina|page|apartado|paso|step|nota|note|cada|every|each)\s*$",
    re.IGNORECASE,
)
# sustantivos de tiempo: "5 minutos" es duración, no cardinalidad de miembros
_COUNT_TIME_NOUN = re.compile(
    r"(segundos|minutos|horas|dias|semanas|meses|anos|seconds|minutes|hours|"
    r"days|weeks|months|years)"
)


def _count_match_excluded(text: str, m: re.Match) -> bool:
    """Contextos donde un número NO es un conteo declarado: numeración de sección
    ("1.1 JUMPERS", "# 8 CARACTERÍSTICAS"), celdas de tabla, o número precedido por
    otro número+punto (cadenas de numeración)."""
    line_start = text.rfind("\n", 0, m.start()) + 1
    line_end = text.find("\n", line_start)
    line = text[line_start: line_end if line_end != -1 else len(text)]
    if re.match(r"\s*#{1,6}\s", line):
        return True  # heading markdown
    if line.count("|") >= 2:
        return True  # fila de tabla: el número es dato de celda
    prev = text[max(0, m.start() - 3): m.start()]
    if re.search(r"\d[.)]\s*$", prev):
        return True  # "1.1 X" / "8.2 X" — numeración, no cardinalidad
    context = text[max(0, m.start() - 14): m.start()]
    if _COUNT_REF_WORD.search(context):
        return True  # "tabla 1 ...", "cada 6 meses": referencia/frecuencia, no conteo
    if _COUNT_TIME_NOUN.fullmatch(_fold(m.group(2))):
        return True  # duración ("5 minutos"), no cardinalidad de miembros
    return False


def _detect_count(text: str) -> list[Atom]:
    atoms: list[Atom] = []
    blocks = _enumeration_blocks(text)
    sentences = _sentence_spans(text)
    for m in _RX_COUNT.finditer(text):
        raw = m.group(1).lower()
        declared = _COUNT_WORDS.get(_fold(raw)) or (int(raw) if raw.isdigit() else None)
        if declared is None:
            continue
        if _count_match_excluded(text, m):
            continue
        block = next(
            (b for b in blocks if m.end() <= b[0] <= m.end() + _COUNT_WINDOW), None
        )
        if block is None:
            continue
        b_start, b_end, enumerated, kind = block
        # ADYACENCIA: el conteo declarado debe INTRODUCIR la enumeración — sin líneas de
        # prosa intermedias entre la línea del conteo y el bloque (un conteo y una
        # enumeración no relacionados a <300 chars no forman átomo).
        gap_lines = text[m.end():b_start].split("\n")[1:]
        if any(len(_ALPHA_RX.findall(g)) >= 3 for g in gap_lines):
            continue
        if enumerated == declared:
            continue  # conteo consistente: no hay átomo (conducta DISCLOSE solo ante conflicto)
        s_start = next(
            (s for s, e in sentences if s <= m.start() < e), m.start()
        )
        span_start, span_end = s_start, b_end
        anchors = _content_tokens(text[s_start:m.end()])
        anchors.extend([str(declared), str(enumerated), _fold(m.group(2))])
        atoms.append({
            "family": FAMILY_COUNT,
            "span_start": span_start, "span_end": span_end,
            "span_text": text[span_start:span_end],
            "anchor_tokens": _dedup(anchors),
            "meta": {
                "declared_n": declared,
                "enumerated_n": enumerated,
                "conflict": True,
                "enumeration_kind": kind,
                "noun": m.group(2),
                "seven_segment_risk": has_seven_segment_pattern(
                    text[span_start:span_end]
                ),
            },
        })
    return atoms


# ─────────────────────────────── API pública ───────────────────────────────

def detect_atoms(fragment_text: str) -> list[Atom]:
    """Detectores deterministas de las 4 familias sobre el texto de UN fragmento."""
    if not fragment_text or not fragment_text.strip():
        return []
    atoms = (
        _detect_range(fragment_text)
        + _detect_bundle(fragment_text)
        + _detect_mandatory(fragment_text)
        + _detect_count(fragment_text)
    )
    atoms.sort(key=lambda a: (a["span_start"], a["family"]))
    return atoms


def _atom_numbers(atom: Atom) -> set[float]:
    meta = atom.get("meta") or {}
    vals: set[float] = set()
    for key in ("lower", "upper", "step", "tolerance", "declared_n", "enumerated_n"):
        v = meta.get(key)
        if v is not None:
            vals.add(float(v))
    vals |= _numbers_in(atom.get("span_text") or "")
    return vals


def bind_atoms(
    atoms: list[Atom],
    draft_answer: str,
    cited_fragment_ids: set,
    fragment_id,
) -> list[Atom]:
    """Exigibilidad (diseño §1.2, conservador: en duda NO exigible): el fragmento está
    CITADO en el borrador Y el borrador toca el claim ancla del átomo — comparte un número
    exacto (se excluyen 0/1 por ubicuidad), o ≥2 anchor_tokens no-stopword, o la entidad
    completa del heading."""
    if fragment_id not in set(cited_fragment_ids or set()):
        return []
    clean = _FRAG_CITE.sub(" ", draft_answer or "")
    draft_tokens = set(_content_tokens(clean))
    draft_numbers = {v for v in _numbers_in(clean) if v not in (0.0, 1.0)}
    bound: list[Atom] = []
    for atom in atoms:
        atom_numbers = {v for v in _atom_numbers(atom) if v not in (0.0, 1.0)}
        if atom_numbers & draft_numbers:
            bound.append(atom)
            continue
        anchors = {
            t for t in (atom.get("anchor_tokens") or [])
            if not t.isdigit() and t not in _STOPWORDS and len(t) >= 3
        }
        if len(anchors & draft_tokens) >= 2:
            bound.append(atom)
            continue
        header_tokens = _content_tokens((atom.get("meta") or {}).get("header") or "")
        if header_tokens and set(header_tokens) <= draft_tokens:
            bound.append(atom)
    return bound


def atom_satisfied(atom: Atom, draft_answer: str) -> bool:
    """¿El borrador ya conserva el átomo? Determina qué átomos exigibles van al anexo."""
    clean = _FRAG_CITE.sub(" ", draft_answer or "")
    draft_tokens = set(_content_tokens(clean))
    draft_numbers = _numbers_in(clean)
    family = atom.get("family")
    meta = atom.get("meta") or {}
    if family == FAMILY_RANGE:
        needed = {
            float(meta[k]) for k in ("lower", "upper", "step", "tolerance")
            if meta.get(k) is not None
        }
        return bool(needed) and needed <= draft_numbers
    if family == FAMILY_COUNT:
        return {float(meta["declared_n"]), float(meta["enumerated_n"])} <= draft_numbers
    if family == FAMILY_BUNDLE:
        members = meta.get("members") or []
        if not members:
            return True
        for label in members:
            toks = _content_tokens(label, min_len=2)
            if not toks:
                continue
            if not any(t in draft_tokens for t in toks):
                return False
        return True
    if family == FAMILY_MANDATORY:
        triggers = meta.get("triggers") or []
        dfold = _fold(clean)
        trigger_present = any(_trigger_present(trg, dfold) for trg in triggers)
        anchors = {
            t for t in (atom.get("anchor_tokens") or [])
            if not t.isdigit() and len(t) >= 3
        }
        overlap = len(anchors & draft_tokens)
        return trigger_present and overlap >= min(2, len(anchors))
    return True


# ───────────────────────── attestation de identidad ─────────────────────────

def _query_resolved_ids(query: str) -> set[str]:
    """Misma fuente que IDENTITY_RESOLVE: catálogo gobernado vía catalog_resolver.
    Solo registros con expand=True aportan identidad (clarify/candidate/unknown NO)."""
    try:
        from . import catalog_resolver

        res = catalog_resolver.resolve_query(query)
    except Exception as exc:
        logger.warning(f"must_preserve: resolución de identidad no disponible ({exc})")
        return set()
    ids: set[str] = set()
    for rec in res.get("records") or []:
        if rec.get("expand"):
            ids.update(str(i) for i in rec.get("ids") or [])
    return ids


def _load_catalog():
    try:
        from . import catalog_resolver

        catalog_resolver._ensure()
        return catalog_resolver._cat
    except Exception as exc:
        logger.warning(f"must_preserve: catálogo no cargable ({exc})")
        return None


def attest_identity(fragment_doc_id, resolved_models, catalog=None) -> bool:
    """El documento del fragmento pertenece al doc_map de la identidad resuelta de la
    query (catálogo DEC-074/090). Fail-CLOSED del anexo: sin doc_id, sin resolución o
    sin catálogo → False (la respuesta sigue intacta; solo el anexo no actúa).
    Barrera anti-S164: restringirse al fragmento citado NO basta — el writer puede citar
    el manual equivocado y el contrato lo amplificaría (diseño §1.2)."""
    if not fragment_doc_id or not resolved_models:
        return False
    cat = catalog if catalog is not None else _load_catalog()
    if cat is None:
        return False
    try:
        doc_ids: set[str] = set()
        for dm in cat.doc_map:
            if str(dm.get("document_id") or "") != str(fragment_doc_id):
                continue
            for entry in dm.get("entries") or []:
                eid = entry.get("id")
                if eid:
                    doc_ids.add(cat.follow_redirect(str(eid)))
        if not doc_ids:
            return False
        resolved = {cat.follow_redirect(str(m)) for m in resolved_models}
        return bool(doc_ids & resolved)
    except Exception as exc:
        logger.warning(f"must_preserve: attestation fail-closed ({exc})")
        return False


# ─────────────────────────────── render ───────────────────────────────

_RX_NUM_UNIT = re.compile(rf"({_NUM})\s*({_UNIT_ALT})(?![a-z0-9])", re.IGNORECASE)
_UNIT_SYNONYMS = {
    "segundos": "s", "segundo": "s", "seg": "s", "milisegundos": "ms",
    "minutos": "min", "minuto": "min", "horas": "h", "hora": "h",
    "voltios": "v", "vcc": "v", "vdc": "v", "vca": "v", "vac": "v",
    "amperios": "a", "ohmios": "ω", "ohms": "ω", "ohmio": "ω", "ohm": "ω",
    "kohm": "kω", "vatios": "w", "metros": "m", "metro": "m", "litros": "l",
    "ºc": "°c", "ºf": "°f",
}


def _num_unit_pairs(text: str) -> set[tuple[float, str]]:
    pairs: set[tuple[float, str]] = set()
    for m in _RX_NUM_UNIT.finditer(text or ""):
        unit = m.group(2).lower()
        pairs.add((_num_val(m.group(1)), _UNIT_SYNONYMS.get(unit, unit)))
    return pairs


def _contradicts(atom: Atom, draft_answer: str) -> bool:
    """Proxy determinista de "mismo predicado, valor distinto": misma UNIDAD con número
    distinto en el borrador. Un F-COUNT en conflicto siempre se DISCLOSEA (guard s243:
    fuente inconsistente nunca se resuelve en silencio)."""
    if (atom.get("meta") or {}).get("conflict"):
        return True
    span_pairs = _num_unit_pairs(atom.get("span_text") or "")
    if not span_pairs:
        return False
    draft_pairs = _num_unit_pairs(_FRAG_CITE.sub(" ", draft_answer or ""))
    for value, unit in span_pairs:
        draft_values = {dv for dv, du in draft_pairs if du == unit}
        if draft_values and value not in draft_values:
            return True
    return False


def _select_for_appendix(missing_atoms: list[Atom]) -> list[Atom]:
    """Cap 4 + exclusión de spans con riesgo 7-segmentos del anexo automático."""
    selected = [
        a for a in missing_atoms
        if not (a.get("meta") or {}).get("seven_segment_risk")
    ]
    return selected[:APPENDIX_CAP]


def render_appendix(missing_atoms: list[Atom], draft_answer: str) -> str:
    """Sección "Información adicional del manual:" (SIN "verificada" — el span verbatim
    hereda la EXTRACCIÓN, no el píxel; dúo M5). Spans VERBATIM con cita [Fn], cap 4.
    Puro código, cero LLM."""
    selected = _select_for_appendix(missing_atoms)
    if not selected:
        return ""
    lines = [APPENDIX_HEADER]
    for atom in selected:
        fragment_number = (atom.get("meta") or {}).get("fragment_number")
        cite = f" [F{fragment_number}]" if fragment_number else ""
        span = (atom.get("span_text") or "").strip()
        if _contradicts(atom, draft_answer):
            lines.append(f'- Nota: el manual también indica: "{span}"{cite}')
        else:
            lines.append(f'- "{span}"{cite}')
    return "\n".join(lines)


# ─────────────────────────────── orquestación ───────────────────────────────

def cited_fragment_numbers(draft_answer: str) -> set[int]:
    return {int(m) for m in re.findall(r"\[F(\d{1,2})\]", draft_answer or "")}


def _chunk_text(chunk: dict) -> str:
    """El MISMO contenido que el generador sirve en el prompt (paridad de vista)."""
    try:
        from .post_rerank_coverage import coverage_context_content

        return coverage_context_content(chunk) or ""
    except Exception:
        return str(chunk.get("content") or "")


def apply_must_preserve_contract(
    query: str, chunks: list[dict], draft_answer: str
) -> tuple[str, dict | None]:
    """Punto de entrada único del generador (post-generación, pre-return).

    off → devuelve el MISMO objeto respuesta y trace None (byte-idéntico).
    on  → detecta+binde+attesta sobre los fragmentos SERVIDOS y anexa si procede.
    El caller envuelve en try/except (fail-open total)."""
    if not contract_enabled():
        return draft_answer, None
    trace: dict[str, Any] = {
        "schema": "must_preserve_contract_v1",
        "identity_resolved": False,
        "cited_fragments": [],
        "atoms_detected": 0,
        "atoms_bound": 0,
        "atoms_missing": 0,
        "atoms_appended": 0,
        "appendix_appended": False,
    }
    resolved = _query_resolved_ids(query)
    if not resolved:
        # Sin identidad resuelta el anexo NO actúa (fail-closed del anexo,
        # fail-open de la respuesta — diseño §1.2).
        trace["reason"] = "identity_unresolved"
        return draft_answer, trace
    trace["identity_resolved"] = True
    trace["resolved_ids"] = sorted(resolved)
    cited = cited_fragment_numbers(draft_answer)
    trace["cited_fragments"] = sorted(cited)
    catalog = _load_catalog()
    missing: list[Atom] = []
    for idx, chunk in enumerate(chunks or [], start=1):
        if idx not in cited:
            continue
        if not attest_identity(chunk.get("document_id"), resolved, catalog):
            continue
        atoms = detect_atoms(_chunk_text(chunk))
        trace["atoms_detected"] += len(atoms)
        bound = bind_atoms(atoms, draft_answer, cited, idx)
        trace["atoms_bound"] += len(bound)
        for atom in bound:
            if not atom_satisfied(atom, draft_answer):
                atom.setdefault("meta", {})["fragment_number"] = idx
                missing.append(atom)
    trace["atoms_missing"] = len(missing)
    appendix = render_appendix(missing, draft_answer)
    if not appendix:
        return draft_answer, trace
    trace["atoms_appended"] = len(_select_for_appendix(missing))
    trace["appendix_appended"] = True
    return draft_answer.rstrip() + "\n\n" + appendix, trace
