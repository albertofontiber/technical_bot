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

Riesgo OCR (v2, funnel del probe-1 s270): los patrones de display 7-segmentos (``r.I`` /
``t.A``) ya NO se excluyen en detección — se MARCAN (``seven_segment_risk``) y la exclusión
vive en la SELECCIÓN con paridad de superficie: el átomo con riesgo solo es anexable si el
borrador YA contiene sus tokens display (``r.i`` ≈ ``rI``); el anexo jamás introduce
superficie OCR que el borrador no sirva.

v2 (DEC-126; fixes GENÉRICOS derivados del funnel del probe-1, no de los golds):
  - selección priorizada del cap (seguridad primero) + cap por familia (anti-monopolio);
  - paridad de token display (arriba);
  - F-COUNT cross-fragmento (conteo↔enumeración partidos por el chunking, mismo documento,
    página igual/adyacente, cita doble) + enumeración ``label_run`` (pilas de etiquetas
    OCR) + tie de conteo por SECCIÓN (forward-reference bajo un heading);
  - F-BUNDLE acepta líneas de definición con separador guion (``**Campo** - descripción``);
  - ``apply_must_preserve_contract(..., detect_fn=...)`` inyecta el detector (brazo híbrido).

v4 (s271; GUARDS DE ACTIVACIÓN — los 3 bloqueadores de DEC-127b observados en la Etapa 3
viva, mecánicos y genéricos, SIN tocar el contrato de binding):
  1. dedup del render (hp001): dos átomos con span_text idéntico tras fold — o solapado
     ≥90% con el MISMO contenido numérico — anexan UNA sola vez.
  2. guard de contenido informativo (cat007): un span (o cualquier lado de un disclosure)
     cuyo contenido foldeado sin puntuación/pipes/whitespace quede vacío, o que sea una
     tabla de etiquetas-SIN-valores (celdas en blanco), NO se anexa; si era el
     lado-enumeración de un disclosure, el disclosure entero no dispara (mejor silencio
     que basura). Una tira de etiquetas CON texto (label_run OCR) SÍ es informativa.
  3. tie ESTRICTO del F-COUNT a distancia (hp001): la enumeración de un tie de sección o
     cross-fragmento no puede ser un crumb de navegación/menú (línea única con ``|`` y
     ≤4 tokens por celda sin valores numéricos) y debe compartir dominio con el conteo
     (sustantivo contado en la enumeración, o heading de la sección compartiendo ≥1 token
     con la oración del conteo; en cross: sustantivo o continuación de la MISMA sección a
     través del corte). El tie adyacente aplica también los guards de crumb/informativo.
"""
from __future__ import annotations

import difflib
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
# v2 (funnel probe-1 hp002: 13-14 átomos bound para 4 slots, RANGE monopolizaba y el
# callout MANDATORY core entraba 1/3): cap POR FAMILIA dentro del cap global.
APPENDIX_FAMILY_CAP = 2


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
    # palabras función de 2-3 letras (v3, fix post-seed-271): la lista original
    # asumía min_len=3 y las función cortas se colaban en los checks min_len=2
    # (binding v2 por miembro-token) y en el contexto procedimental — "de"/"el"/
    # "the" NO son tokens PROPIOS de ningún átomo. Solo función puras; los códigos
    # técnicos cortos ("PC", "LED", "bus") NO se tocan.
    "de", "el", "la", "en", "es", "al", "un", "se", "no", "si", "su", "lo", "le",
    "ya", "ha", "he", "va", "mi", "tu", "te", "me", "ni",
    "del", "los", "las", "una", "uno", "que", "con", "por", "son", "sus", "mas",
    "sin", "asi", "aun", "les", "nos",
    "of", "to", "in", "on", "at", "or", "as", "by", "is", "it", "an", "be", "do",
    "if", "so", "we", "us", "my", "up",
    "the", "and", "are", "for", "not", "its", "was", "has", "had", "but", "you",
    "per", "any", "all", "can", "may",
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


# Riesgo OCR 7-segmentos (feedback_7segment · spec v3 §A M9): formas de display tipo
# ``r.I`` / ``r.i`` / ``t.Fi`` / ``dr`` — códigos de 1-3 chars con punto interior o
# códigos cortos sueltos. (``t.Fi`` es ejemplo REAL del riesgo, no un display existente:
# al píxel es ``t.A`` — transliteración 7-seg confirmada en s269/DEC-125; el patrón debe
# seguir cazando la forma extraída.) La exclusión es CONTEXTUAL: solo aplica si el token aparece
# en contexto de display/parámetro ("el display muestra ..."), y NUNCA al inicio de
# línea/heading (``A.1 CARACTERÍSTICAS`` es numeración de sección, no un display —
# hallazgo 9 de Sol: la versión previa excluía ``A.1`` y no reconocía ``r.i``).
_SEVEN_SEG_TOKEN = re.compile(
    r"(?<![\w.])(?:[0-9A-Za-z]{1,2}\.){1,2}[0-9A-Za-z]{1,2}(?![\w.])"
)
# códigos cortos sin punto (``dr``): solo letras, 2 chars, y SOLO en contexto display
_SEVEN_SEG_BARE = re.compile(r"(?<![\w.])[A-Za-z]{2}(?![\w.])")
_SEVEN_SEG_BARE_STOP = {
    # palabras reales de 2 letras (es/en) que jamás son códigos de display
    "al", "de", "el", "en", "es", "ha", "he", "la", "le", "lo", "me", "mi", "ni",
    "no", "os", "se", "si", "su", "te", "tu", "un", "va", "ve", "ya", "yo",
    "am", "an", "as", "at", "be", "by", "do", "go", "if", "in", "is", "it", "my",
    "of", "on", "or", "so", "to", "up", "us", "we",
}
_DISPLAY_CONTEXT = re.compile(
    r"\b(display|pantalla|visor|visualiza(?:ra|n)?|muestra(?:n)?|mostrara(?:n)?|"
    r"indicador(?:es)?|parpadea(?:n)?|segmentos?|digitos?|codigo|codigos|"
    r"shows?|reads?|blinks?|blinking|flashes|flashing|code|codes|digits?)\b"
)


def _token_is_heading_numbering(text: str, start: int) -> bool:
    """El token abre la línea (o va tras ``#``/viñeta) ⇒ numeración de sección."""
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start]
    return re.fullmatch(r"\s*(?:#{1,6}\s+|[-•*·◦]\s+)?", prefix) is not None


def has_seven_segment_pattern(text: str) -> bool:
    """True si el texto contiene una forma de display 7-segmentos EN CONTEXTO de
    display/parámetro. Sin contexto de display (o en posición de heading/numeración
    de sección) NO hay riesgo — el token es identificador técnico normal."""
    text = text or ""
    if not _DISPLAY_CONTEXT.search(_fold(text)):
        return False
    for m in _SEVEN_SEG_TOKEN.finditer(text):
        tok = m.group()
        if all(c.isdigit() or c == "." for c in tok):
            continue  # decimal puro ("1.5")
        if _token_is_heading_numbering(text, m.start()):
            continue  # "A.1 JUMPERS": numeración de sección, no display
        return True
    for m in _SEVEN_SEG_BARE.finditer(text):
        tok = m.group()
        if _fold(tok) in _SEVEN_SEG_BARE_STOP:
            continue
        if _token_is_heading_numbering(text, m.start()):
            continue
        return True
    return False


def seven_segment_tokens(text: str) -> set[str]:
    """Tokens display 7-seg del texto EN CONTEXTO de display (mismas reglas que
    ``has_seven_segment_pattern``), normalizados: foldeados y SIN puntos
    (``r.i`` → ``ri``). Vacío si no hay contexto de display."""
    text = text or ""
    out: set[str] = set()
    if not _DISPLAY_CONTEXT.search(_fold(text)):
        return out
    for m in _SEVEN_SEG_TOKEN.finditer(text):
        tok = m.group()
        if all(c.isdigit() or c == "." for c in tok):
            continue
        if _token_is_heading_numbering(text, m.start()):
            continue
        out.add(_fold(tok).replace(".", ""))
    for m in _SEVEN_SEG_BARE.finditer(text):
        tok = m.group()
        if _fold(tok) in _SEVEN_SEG_BARE_STOP:
            continue
        if _token_is_heading_numbering(text, m.start()):
            continue
        out.add(_fold(tok))
    return out


def _display_token_in_draft(token: str, folded_draft: str) -> bool:
    """``r.i`` ≈ ``rI`` ≈ ``r.I``: el token normalizado presente en el borrador con
    puntos OPCIONALES entre caracteres y límites no alfanuméricos."""
    pattern = r"\.?".join(re.escape(ch) for ch in token)
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", folded_draft) is not None


def display_parity_ok(atom: Atom, draft_answer: str) -> bool:
    """Paridad de superficie OCR (v2, funnel probe-1 hp011: la exclusión total
    mataba los átomos r.i/t.A que el propio borrador ya nombraba como ``rI``): un
    átomo con riesgo 7-seg es anexable SOLO si TODOS sus tokens display ya
    aparecen en el borrador — el anexo no añade superficie OCR nueva. Sin tokens
    extraíbles → conservador: no anexable."""
    tokens = seven_segment_tokens(atom.get("span_text") or "")
    if not tokens:
        return False
    folded = _fold(draft_answer or "")
    return all(_display_token_in_draft(tok, folded) for tok in tokens)


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
        # v2: el riesgo 7-seg ya no excluye en detección — se MARCA y la exclusión
        # (con paridad de display) vive en la selección del anexo.
        risk = has_seven_segment_pattern(sentence)
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
                "seven_segment_risk": risk,
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
# v2 (funnel probe-1 cat018 F3: ``**Zona** - número de zona asignada`` → 0 átomos): el
# separador de definición acepta ``:`` O guion RODEADO de espacios (`` - ``/`` – ``/`` — ``)
# — patrón markdown genérico de listas de definición; sin espacios alrededor el guion
# de palabras compuestas (``auto-reset``) NO separa.
_DEFLINE = re.compile(
    r"^\s*(?:[-•*·◦]\s*)?\**([A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9][^:\n]{0,60}?)\**\s*"
    r"(?::\s+|[-–—]\s+)(\S.*)$"
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


# ────────────────────────────── contexto procedimental ──────────────────────────────
# Binding v2 (s243): los mandatory_safety_omission de la taxonomía son callouts
# obligatorios ADYACENTES A PROCEDIMIENTOS que la respuesta da. La exigibilidad de un
# F-MANDATORY se ancla al contexto PROCEDIMENTAL de su fragmento (pasos numerados /
# líneas imperativas), extraído determinista con léxico cerrado bilingüe.

_PROCEDURAL_VERBS = (
    # es (formas foldeadas)
    "pulse", "pulsar", "presione", "presionar", "seleccione", "seleccionar",
    "conecte", "conectar", "desconecte", "desconectar", "retire", "retirar",
    "coloque", "colocar", "gire", "girar", "ajuste", "ajustar", "verifique",
    "verificar", "compruebe", "comprobar", "instale", "instalar", "alimente",
    "mantenga", "mantener", "introduzca", "introducir", "abra", "abrir", "cierre",
    "cerrar", "monte", "montar", "utilice", "utilizar", "use", "usar", "aisle",
    "aislar", "rearme", "rearmar", "corte", "cortar", "espere", "esperar",
    # en
    "press", "select", "connect", "disconnect", "remove", "insert", "turn",
    "adjust", "verify", "check", "install", "hold", "open", "close", "mount",
    "set", "ensure", "wait", "isolate", "reset", "apply", "replace",
)
_PROCEDURAL_VERB_RX = re.compile(
    r"\b(" + "|".join(_PROCEDURAL_VERBS) + r")\b"
)
_STEP_LINE_RX = re.compile(r"^\s*(?:\d{1,2}[.)]|[-•*·◦])\s+\S")


def procedural_context_tokens(fragment_text: str) -> list[str]:
    """Tokens de contenido de las líneas PROCEDIMENTALES del fragmento (pasos
    numerados/viñetas o líneas con verbo imperativo del léxico). Determinista."""
    tokens: list[str] = []
    for _start, _end, line in _line_spans(fragment_text or ""):
        if not line.strip():
            continue
        if _STEP_LINE_RX.match(line) or _PROCEDURAL_VERB_RX.search(_fold(line)):
            tokens.extend(_content_tokens(line))
    return _dedup(tokens)


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
    proc_tokens: list[str] | None = None  # lazy: solo si hay algún átomo
    for s_start, s_end in _sentence_spans(text):
        sentence = text[s_start:s_end]
        triggers = _mandatory_triggers(sentence)
        if not triggers:
            continue
        if proc_tokens is None:
            proc_tokens = procedural_context_tokens(text)
        atoms.append({
            "family": FAMILY_MANDATORY,
            "span_start": s_start, "span_end": s_end,
            "span_text": sentence,
            "anchor_tokens": _dedup(_content_tokens(sentence)),
            "meta": {
                "triggers": triggers,
                # binding v2: la exigibilidad del callout se ancla al contexto
                # PROCEDIMENTAL de su fragmento (s243: callouts adyacentes a
                # procedimientos que la respuesta da)
                "procedural_context_tokens": proc_tokens,
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


def _is_bare_label_line(line: str) -> bool:
    """Línea de PILA DE ETIQUETAS (v2, funnel probe-1: enumeraciones OCR sin viñetas
    ni pipes — cabeceras de columna aplanadas): corta (≤40 chars), ≤4 tokens, con
    letra, sin viñeta/pipe/heading y sin ``:`` final."""
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return False
    if stripped.endswith(":") or stripped.startswith("#"):
        return False
    if _is_pipe_row(line) or _ITEM_LINE.match(line) or _PIPE_SEP.match(line):
        return False
    if len(stripped.split()) > 4:
        return False
    return bool(_ALPHA_RX.search(stripped))


def _enumeration_blocks(text: str) -> list[tuple[int, int, int, str]]:
    """Bloques (start, end, n_miembros, kind): listas con viñetas/numeradas, filas de
    tabla, UNA línea de columnas separadas por ``|``, o pilas de etiquetas OCR
    (``label_run``, v2: ≥3 líneas-etiqueta consecutivas; miembros = etiquetas
    DISTINTAS foldeadas)."""
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
        if _is_bare_label_line(line):
            j = i
            labels: list[str] = []
            while j < len(lines) and _is_bare_label_line(lines[j][2]):
                labels.append(_fold(lines[j][2].strip()))
                j += 1
            if len(labels) >= 3:
                blocks.append((start, lines[j - 1][1], len(set(labels)), "label_run"))
                i = j
                continue
            i = j if j > i else i + 1
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


def _heading_positions(text: str) -> list[int]:
    return [
        start for start, _end, line in _line_spans(text)
        if line.lstrip().startswith("#")
    ]


# ─────────── guards de activación v4 (s271; bloqueadores 2 y 3 de DEC-127b) ───────────

_ALNUM_RX = re.compile(r"[a-z0-9]")


def _blank_celled_row(line: str) -> bool:
    """Fila de tabla con celdas EN BLANCO: ≥2 celdas y ≤1 no vacía (``| T1 |   |``)."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return len(cells) >= 2 and sum(1 for c in cells if c) <= 1


def informative_span(text: str) -> bool:
    """Guard de contenido informativo (bloqueador 2, cat007): False si el contenido
    foldeado sin puntuación/pipes/whitespace queda vacío, o si el span es una tabla de
    etiquetas-SIN-valores (todas las filas de datos con celdas en blanco). Una tira de
    etiquetas CON texto (label_run OCR, p.ej. tipos de retardo) SÍ es informativa — el
    guard distingue etiquetas-con-texto de celdas-en-blanco."""
    if not _ALNUM_RX.search(_fold(text or "")):
        return False
    lines = [line for line in (text or "").splitlines() if line.strip()]
    data_rows = [
        line for line in lines if _is_pipe_row(line) and not _PIPE_SEP.match(line)
    ]
    if (
        data_rows
        and all(_is_pipe_row(line) or _PIPE_SEP.match(line) for line in lines)
        and all(_blank_celled_row(line) for line in data_rows)
    ):
        return False
    return True


def _nav_crumb_line(line: str) -> bool:
    """Heurística GENÉRICA de crumb de navegación/menú (bloqueador 3, hp001
    ``Sistema | Otros | Reiniciar``): línea única con separadores ``|`` y ≤4 tokens
    por celda, sin valores numéricos en ninguna celda."""
    if not _is_pipe_row(line) or _PIPE_SEP.match(line):
        return False
    cells = [c.strip() for c in line.strip().strip("|").split("|") if c.strip()]
    if len(cells) < 2:
        return False
    for cell in cells:
        tokens = cell.split()
        if len(tokens) > 4 or any(ch.isdigit() for ch in cell):
            return False
    return True


def _block_is_nav_crumb(text: str, block: tuple[int, int, int, str]) -> bool:
    start, end, _n, kind = block
    if kind != "pipe_columns":
        return False  # crumb = UNA línea de columnas; tablas/listas/label_run no
    data = [
        line for _s, _e, line in _line_spans(text[start:end])
        if line.strip() and _is_pipe_row(line) and not _PIPE_SEP.match(line)
    ]
    return len(data) == 1 and _nav_crumb_line(data[0])


def _pipe_data_rows(text: str, block: tuple[int, int, int, str]) -> list[str]:
    return [
        line for _s, _e, line in _line_spans(text[block[0]:block[1]])
        if line.strip() and _is_pipe_row(line) and not _PIPE_SEP.match(line)
    ]


def _block_is_value_row(text: str, block: tuple[int, int, int, str]) -> bool:
    """Fila CLAVE-VALOR de screenshot/tabla (residual del review adversarial s271:
    ``Lazos | 2 | 4`` escapaba al crumb por el dígito y el sustantivo la endosaba):
    línea única de columnas con ≥1 celda PURAMENTE numérica — son valores de un
    campo, no una enumeración de MIEMBROS."""
    if block[3] != "pipe_columns":
        return False
    data = _pipe_data_rows(text, block)
    if len(data) != 1:
        return False
    cells = [c.strip() for c in data[0].strip().strip("|").split("|") if c.strip()]
    return any(re.fullmatch(r"[\d.,\s]+", c) for c in cells)


def _count_block_disqualified(text: str, block: tuple[int, int, int, str]) -> bool:
    """Screen común de la enumeración candidata de un tie F-COUNT (cualquier tie):
    crumb de navegación/menú, contenido no informativo (celdas en blanco), o fila
    clave-valor — ninguna es una enumeración de miembros."""
    return (
        _block_is_nav_crumb(text, block)
        or not informative_span(text[block[0]:block[1]])
        or _block_is_value_row(text, block)
    )


def _noun_stem(noun: str) -> str:
    folded = _fold(noun or "").strip()
    if folded.endswith("es") and len(folded) > 4:
        return folded[:-2]
    if folded.endswith("s") and len(folded) > 3:
        return folded[:-1]
    return folded


def _noun_tie(noun: str, block_text: str) -> bool:
    """El sustantivo del conteo (plural-tolerante: ``lazos``≈``lazo``) aparece en la
    enumeración — dominio compartido conteo↔enumeración."""
    stem = _noun_stem(noun)
    if len(stem) < 3:
        return False
    return any(
        tok == stem or (tok.startswith(stem) and len(tok) <= len(stem) + 2)
        for tok in _content_tokens(block_text, min_len=2)
    )


def _heading_text_above(text: str, pos: int) -> str | None:
    best: str | None = None
    for start, _end, line in _line_spans(text):
        if start > pos:
            break
        if line.lstrip().startswith("#"):
            best = line.lstrip().lstrip("#").strip()
    return best


def _distant_tie_ok(text: str, m: re.Match, sentence: str,
                    block: tuple[int, int, int, str]) -> bool:
    """Tie ESTRICTO de un par conteo↔enumeración NO adyacente (bloqueador 3): la
    enumeración (a) no es un crumb de navegación/menú, (b) es informativa, y (c)
    comparte dominio con el conteo — sustantivo contado presente en la enumeración, o
    heading gobernante de la sección compartiendo ≥1 token de contenido con la oración
    del conteo. Si el candidato falla, NO se escanea más lejos (conservador)."""
    block_text = text[block[0]:block[1]]
    if _count_block_disqualified(text, block):
        return False
    if _noun_tie(m.group(2), block_text):
        return True
    heading = _heading_text_above(text, m.start())
    if not heading:
        return False
    return bool(set(_content_tokens(heading)) & set(_content_tokens(sentence)))


def _detect_count(text: str) -> list[Atom]:
    atoms: list[Atom] = []
    blocks = _enumeration_blocks(text)
    sentences = _sentence_spans(text)
    headings = _heading_positions(text)
    for m in _RX_COUNT.finditer(text):
        raw = m.group(1).lower()
        declared = _COUNT_WORDS.get(_fold(raw)) or (int(raw) if raw.isdigit() else None)
        if declared is None:
            continue
        if _count_match_excluded(text, m):
            continue
        s_start = next(
            (s for s, e in sentences if s <= m.start() < e), m.start()
        )
        s_end_sentence = next(
            (e for s, e in sentences if s <= m.start() < e), m.end()
        )
        sentence_text = text[s_start:s_end_sentence]
        tie = "adjacent"
        block = next(
            (b for b in blocks if m.end() <= b[0] <= m.end() + _COUNT_WINDOW), None
        )
        if block is not None:
            # ADYACENCIA: el conteo declarado debe INTRODUCIR la enumeración — sin líneas
            # de prosa intermedias entre la línea del conteo y el bloque (un conteo y una
            # enumeración no relacionados a <300 chars no forman átomo).
            gap_lines = text[m.end():block[0]].split("\n")[1:]
            if any(len(_ALPHA_RX.findall(g)) >= 3 for g in gap_lines):
                block = None
        if block is not None and _count_block_disqualified(text, block):
            # v4 (bloqueadores 2/3 + residual del review): un crumb de navegación,
            # una tabla de celdas en blanco o una fila clave-valor no es una
            # enumeración de miembros — tampoco adyacente.
            block = None
            candidate_rejected = True
        else:
            candidate_rejected = False
        if block is None and not candidate_rejected:
            # Tie por SECCIÓN (v2, funnel probe-1: "seis tipos ... como se explica a
            # continuación" + enumeración tras párrafos explicativos): el conteo vive
            # bajo un heading y la PRIMERA enumeración posterior de la misma sección
            # (sin heading intermedio) es la suya, a cualquier distancia. v4: el
            # candidato debe pasar el tie ESTRICTO (_distant_tie_ok); si falla NO se
            # escanea más lejos (conservador — mejor silencio que un par incoherente).
            has_heading_above = any(h <= m.start() for h in headings)
            if has_heading_above:
                candidate = next((b for b in blocks if b[0] > m.end()), None)
                if candidate is not None and not any(
                    m.end() < h < candidate[0] for h in headings
                ) and _distant_tie_ok(text, m, sentence_text, candidate):
                    block = candidate
                    tie = "section"
        if block is None:
            continue
        b_start, b_end, enumerated, kind = block
        if enumerated == declared:
            continue  # conteo consistente: no hay átomo (conducta DISCLOSE solo ante conflicto)
        # v3 (funnel probe-2): span = ORACIÓN del conteo; la enumeración viaja
        # explícita en meta.enum_span_text para el disclosure de DOS LADOS (el span
        # conteo→bloque cortaba el run cuando el bloque se partía).
        span_start, span_end = s_start, s_end_sentence
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
                "tie": tie,
                "noun": m.group(2),
                "enum_span_text": text[b_start:b_end],
                "seven_segment_risk": has_seven_segment_pattern(
                    text[span_start:span_end]
                ) or has_seven_segment_pattern(text[b_start:b_end]),
            },
        })
    return atoms


# ────────────────────── F-COUNT cross-fragmento (v2) ──────────────────────

_CROSS_HEAD_WINDOW = 600  # la enumeración debe EMPEZAR en la cabeza del fragmento par


def detect_cross_fragment_count_atoms(fragments: list[dict]) -> list[Atom]:
    """v2 (funnel probe-1 hp017/obl_872c: el par conteo↔enumeración quedó partido por
    el chunking). Contrato conservador: conteo declarado en el fragmento i SIN
    enumeración propia (ni adyacente ni de sección) + fragmento j del MISMO
    ``document_id`` con página igual o adyacente cuya PRIMERA enumeración empieza en
    los primeros 600 chars (semántica de continuación) → si ``enumerated != declared``,
    átomo F-COUNT con spans de AMBOS fragmentos y cita doble.

    ``fragments``: dicts {fragment_number, text, document_id, page_number}. Puro y
    determinista; la attestation/binding los aplica el caller (apply)."""
    by_number = {int(f["fragment_number"]): f for f in fragments}
    atoms: list[Atom] = []
    for i in sorted(by_number):
        frag = by_number[i]
        text = str(frag.get("text") or "")
        if not text.strip():
            continue
        doc = str(frag.get("document_id") or "")
        if not doc:
            continue
        intra = _detect_count(text)
        intra_spans = [(a["span_start"], a["span_end"]) for a in intra]
        blocks_i = _enumeration_blocks(text)
        sentences = _sentence_spans(text)
        for m in _RX_COUNT.finditer(text):
            raw = m.group(1).lower()
            declared = _COUNT_WORDS.get(_fold(raw)) or (
                int(raw) if raw.isdigit() else None
            )
            if declared is None or _count_match_excluded(text, m):
                continue
            if any(s <= m.start() < e for s, e in intra_spans):
                continue  # ya ligado intra (adyacente o sección): no cross
            if any(
                m.end() <= b[0] <= m.end() + _COUNT_WINDOW for b in blocks_i
            ) or any(b[0] > m.end() for b in blocks_i):
                continue  # hay enumeración posterior en el PROPIO fragmento
            page_i = frag.get("page_number")
            partner = None
            for j in sorted(by_number):
                if j == i:
                    continue
                cand = by_number[j]
                if str(cand.get("document_id") or "") != doc:
                    continue
                page_j = cand.get("page_number")
                if page_i is None or page_j is None:
                    continue
                try:
                    if abs(int(page_i) - int(page_j)) > 1:
                        continue
                except (TypeError, ValueError):
                    continue
                text_j = str(cand.get("text") or "")
                block = next(
                    (
                        b for b in _enumeration_blocks(text_j)
                        if b[0] <= _CROSS_HEAD_WINDOW
                    ),
                    None,
                )
                if block is None:
                    continue
                # v4 (bloqueador 3, tie estricto cross): la enumeración par no puede
                # ser crumb de navegación, celdas-en-blanco ni fila clave-valor, y
                # debe compartir dominio con el conteo — sustantivo contado en la
                # enumeración, o continuación de la MISMA sección a través del corte
                # de chunking (sin heading tras el conteo en el fragmento i NI antes
                # de la enumeración en el fragmento j).
                block_text = text_j[block[0]:block[1]]
                if _count_block_disqualified(text_j, block):
                    continue
                if not _noun_tie(m.group(2), block_text):
                    if any(h > m.end() for h in _heading_positions(text)) or any(
                        h < block[0] for h in _heading_positions(text_j)
                    ):
                        continue
                partner = (j, text_j, block)
                break
            if partner is None:
                continue
            j, text_j, (b_start, b_end, enumerated, kind) = partner
            if enumerated == declared:
                continue  # consistente entre fragmentos: sin átomo (DISCLOSE solo ante conflicto)
            s_start = next(
                (s for s, e in sentences if s <= m.start() < e), m.start()
            )
            s_end = next(
                (e for s, e in sentences if s <= m.start() < e), m.end()
            )
            count_span = text[s_start:s_end]
            enum_span = text_j[b_start:b_end]
            anchors = _content_tokens(count_span)
            anchors.extend([str(declared), str(enumerated), _fold(m.group(2))])
            atoms.append({
                "family": FAMILY_COUNT,
                "span_start": s_start, "span_end": s_end,
                "span_text": count_span,
                "anchor_tokens": _dedup(anchors),
                "meta": {
                    "declared_n": declared,
                    "enumerated_n": enumerated,
                    "conflict": True,
                    "enumeration_kind": kind,
                    "tie": "cross_fragment",
                    "cross_fragment": True,
                    "count_fragment_number": i,
                    "enum_fragment_number": j,
                    "enum_span_text": enum_span,
                    "noun": m.group(2),
                    "seven_segment_risk": (
                        has_seven_segment_pattern(count_span)
                        or has_seven_segment_pattern(enum_span)
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


# ───────────────────────── detector híbrido (spec v3 §B) ─────────────────────────
# Fast-path determinista (detect_atoms, se conserva) + brazo Haiku que PROPONE átomos
# con span VERBATIM obligatorio. El validador es CÓDIGO: cualquier span no-verbatim
# (span ∉ fragmento) o sin el shape de su familia se DESCARTA. El render/binding/
# attestation no cambian (la postcondición sigue siendo código). Sin cliente →
# solo determinista (los tests no tocan red).

HYBRID_DETECTOR_MODEL = "claude-haiku-4-5-20251001"
_HYBRID_SLOTS = 8
_HYBRID_MAX_TOKENS = 1500

_HYBRID_PROMPT = """Eres un extractor de átomos estructurales de manuales técnicos PCI. Te doy UN \
fragmento (español o inglés). Propón hasta 8 átomos, cada uno con su familia y un span \
COPIADO VERBATIM del fragmento (carácter a carácter, sin reescribir nada — un span que no \
sea substring exacto del fragmento se descarta).

Familias válidas (usa exactamente estas etiquetas):
- F-RANGE: restricción numérica acotada — ambos extremos con su unidad (p. ej. "de 05 a \
295 segundos", "–10 °C a +55 °C", "470Ω a 1K"), opcionalmente paso o ámbito (posiciones \
de switch). Un número suelto NO es un átomo.
- F-BUNDLE: cabecera/pestaña/regla con sus campos miembro definidos juntos (heading + \
líneas "Etiqueta: definición", lista de miembros o filas de tabla). El span debe incluir \
cabecera Y miembros.
- F-MANDATORY: oración con fuerza de obligación/prohibición/peligro (imprescindible, \
obligatorio, nunca, advertencia, atención, peligro, evite, deberá, asegúrese; mandatory, \
must, never, warning, caution, danger). "antes de"/"before" solo NO cuenta.
- F-COUNT: conteo declarado de opciones/miembros que NO cuadra con lo enumerado al lado. \
El span debe incluir el conteo declarado Y la enumeración. Conteo consistente NO es átomo.

Usa la herramienta proponer_atomos: atom_N_family + atom_N_span ("" en los huecos sin usar).

FRAGMENTO:
<<<FRAGMENT>>>"""


def hybrid_proposal_schema() -> dict:
    """Transporte PLANO (patrón rectangular src/rag/source_unit_gold.py): solo strings,
    sin arrays/enums/refs — compatible con el dialecto de tool-use de Anthropic. La
    validación de identidad/shape vive en código, no en el schema."""
    props: dict = {}
    required: list[str] = []
    for i in range(1, _HYBRID_SLOTS + 1):
        props[f"atom_{i}_family"] = {"type": "string"}
        props[f"atom_{i}_span"] = {"type": "string"}
        required.extend([f"atom_{i}_family", f"atom_{i}_span"])
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": props,
    }


def _hybrid_range_atom(span: str, start: int) -> Atom | None:
    """Shape F-RANGE para un span verbatim que el regex determinista NO cubre
    (cadenas de desigualdad, notación compacta — diagnóstico v1): ≥2 números con
    ≥1 unidad, o una tolerancia ±. Sin unidad → descarte."""
    nums = sorted({_num_val(m) for m in _NUM_TOKEN.findall(span)})
    pm = _RX_PM.search(span)
    if len(nums) < 2 and not pm:
        return None
    unit_m = _RX_NUM_UNIT.search(span)
    if unit_m is None:
        return None
    step_m = _RX_STEP.search(span)
    scope_ids = _RX_SCOPE_ID.findall(span)
    scope = scope_ids if (_RX_SCOPE_WORD.search(span) or len(scope_ids) >= 2) else []
    meta = {
        "lower": nums[0] if len(nums) >= 2 else None,
        "upper": nums[-1] if len(nums) >= 2 else None,
        "unit": unit_m.group(2).lower(),
        "tolerance": _num_val(pm.group(1)) if pm else None,
        "step": _num_val(step_m.group(1)) if step_m else None,
        "step_unit": (step_m.group(2) or "").lower() or None if step_m else None,
        "scope": scope,
        # v2: riesgo display MARCADO (la exclusión con paridad vive en la selección)
        "seven_segment_risk": has_seven_segment_pattern(span),
    }
    anchors = _content_tokens(span)
    for key in ("lower", "upper", "step", "tolerance"):
        if meta.get(key) is not None:
            anchors.append(_format_num(meta[key]))
    return {
        "family": FAMILY_RANGE,
        "span_start": start, "span_end": start + len(span),
        "span_text": span,
        "anchor_tokens": _dedup(anchors),
        "meta": meta,
    }


def _shift_atom(atom: Atom, offset: int) -> Atom:
    atom = dict(atom)
    atom["span_start"] += offset
    atom["span_end"] += offset
    return atom


def _atom_from_verbatim_span(family: str, span: str, fragment_text: str) -> Atom | None:
    """Valida el SHAPE de familia de un span verbatim propuesto por el modelo y lo
    convierte en Atom con meta consistente (los sub-detectores deterministas corren
    SOBRE el span). Sin shape → None (descarte)."""
    start = fragment_text.find(span)
    if start < 0:
        return None
    if family == FAMILY_RANGE:
        sub = _detect_range(span)
        atom = _shift_atom(sub[0], start) if sub else _hybrid_range_atom(span, start)
    elif family == FAMILY_BUNDLE:
        sub = _detect_bundle(span)
        atom = _shift_atom(sub[0], start) if sub else None
    elif family == FAMILY_MANDATORY:
        triggers = _mandatory_triggers(span)
        if not triggers:
            return None
        atom = {
            "family": FAMILY_MANDATORY,
            "span_start": start, "span_end": start + len(span),
            "span_text": span,
            "anchor_tokens": _dedup(_content_tokens(span)),
            "meta": {
                "triggers": triggers,
                # binding v2: contexto procedimental del FRAGMENTO completo
                "procedural_context_tokens": procedural_context_tokens(fragment_text),
                "seven_segment_risk": has_seven_segment_pattern(span),
            },
        }
    elif family == FAMILY_COUNT:
        sub = _detect_count(span)
        atom = _shift_atom(sub[0], start) if sub else None
    else:
        return None
    if atom is not None:
        atom.setdefault("meta", {})["origin"] = "hybrid"
    return atom


def _overlaps_same_family(atom: Atom, existing: list[Atom]) -> bool:
    return any(
        a["family"] == atom["family"]
        and a["span_start"] < atom["span_end"]
        and atom["span_start"] < a["span_end"]
        for a in existing
    )


def _fold_ws(text: str) -> tuple[str, list[int]]:
    """Fold char-a-char con mapa de índices: minúsculas, sin acentos combinantes,
    espacios/saltos colapsados a UN espacio. Devuelve (texto_foldeado, idx_map)."""
    import unicodedata

    out: list[str] = []
    idx: list[int] = []
    prev_space = False
    for i, ch in enumerate(text or ""):
        if ch.isspace():
            if prev_space or not out:
                continue
            out.append(" ")
            idx.append(i)
            prev_space = True
            continue
        decomposed = unicodedata.normalize("NFKD", ch)
        base = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
        if not base:
            base = ch.lower()
        for c in base:
            out.append(c)
            idx.append(i)
        prev_space = False
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def ground_hybrid_span(fragment_text: str, span: str) -> str | None:
    """Grounding FOLD-TOLERANTE (v3, funnel probe-2: Haiku re-espacia/parafrasea
    levemente y el match exacto descartaba todo): localiza el span en el fragmento
    tras fold (minúsculas + sin acentos + espacios colapsados) y devuelve el
    SUBSTRING EXACTO del fragmento (jamás el texto de Haiku). None si no ancla."""
    span = (span or "").strip()
    if not span:
        return None
    if span in (fragment_text or ""):
        return span
    folded_span, _ = _fold_ws(span)
    if not folded_span:
        return None
    folded_frag, idx = _fold_ws(fragment_text or "")
    pos = folded_frag.find(folded_span)
    if pos < 0:
        return None
    start = idx[pos]
    end = idx[pos + len(folded_span) - 1] + 1
    return fragment_text[start:end]


def detect_atoms_hybrid(
    fragment_text: str,
    client=None,
    model: str = HYBRID_DETECTOR_MODEL,
    usage: dict | None = None,
    stats: dict | None = None,
) -> list[Atom]:
    """Detector híbrido: determinista + propuesta Haiku validada por código.

    - ``client=None`` → SOLO determinista (idéntico a detect_atoms; los tests no
      tocan red). El caller construye el cliente con ``max_retries=0`` (no-retry).
    - Con cliente: 1 llamada tool-use forzado (structured output PLANO). Cada átomo
      propuesto debe citar un span VERBATIM del fragmento y pasar el shape-check de
      su familia; lo demás se descarta. Los átomos híbridos NUNCA reemplazan a los
      deterministas (dedup por solape misma-familia).
    - ``usage``: dict opcional donde se acumulan input_tokens/output_tokens/calls.
    """
    det = detect_atoms(fragment_text)
    if client is None or not fragment_text or not fragment_text.strip():
        return det
    response = client.messages.create(
        model=model,
        max_tokens=_HYBRID_MAX_TOKENS,
        temperature=0,
        tools=[{
            "name": "proponer_atomos",
            "description": "Registra los átomos estructurales propuestos (span verbatim).",
            "input_schema": hybrid_proposal_schema(),
        }],
        tool_choice={"type": "tool", "name": "proponer_atomos"},
        messages=[{
            "role": "user",
            "content": _HYBRID_PROMPT.replace("<<<FRAGMENT>>>", fragment_text),
        }],
    )
    if usage is not None:
        usage["input_tokens"] = usage.get("input_tokens", 0) + (
            getattr(response.usage, "input_tokens", 0) or 0
        )
        usage["output_tokens"] = usage.get("output_tokens", 0) + (
            getattr(response.usage, "output_tokens", 0) or 0
        )
        usage["calls"] = usage.get("calls", 0) + 1
    tool_use = next(b for b in response.content if b.type == "tool_use")
    payload = dict(tool_use.input)
    atoms = list(det)

    def _count(key: str) -> None:
        if stats is not None:
            stats[key] = stats.get(key, 0) + 1

    for i in range(1, _HYBRID_SLOTS + 1):
        family = str(payload.get(f"atom_{i}_family") or "").strip().upper()
        span = str(payload.get(f"atom_{i}_span") or "").strip()
        if not family and not span:
            continue
        _count("proposals")
        if family not in FAMILIES or not span:
            _count("rejected_family_or_empty")
            continue
        # v3: grounding FOLD-TOLERANTE — el texto anexable sigue siendo el substring
        # EXACTO del fragmento (ground_hybrid_span), jamás el texto de Haiku.
        grounded = ground_hybrid_span(fragment_text, span)
        if grounded is None:
            _count("rejected_grounding")
            continue
        if grounded != span:
            _count("accepted_fold_relocated")
        atom = _atom_from_verbatim_span(family, grounded, fragment_text)
        if atom is None:
            _count("rejected_shape")
            continue  # sin shape de su familia → descarte
        if _overlaps_same_family(atom, atoms):
            _count("rejected_overlap")
            continue
        _count("accepted")
        atoms.append(atom)
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


def citation_window(draft_answer: str, fragment_id) -> str:
    """Texto ADYACENTE a la(s) cita(s) [Fn] de ESE fragmento (C2, dúo-Sol crítico 2):
    la unión de las oraciones/líneas del borrador que llevan la cita literal
    ``[F{fragment_id}]``. Cadena vacía si la cita no es localizable."""
    draft = draft_answer or ""
    token = f"[F{int(fragment_id)}]"
    if token not in draft:
        return ""
    parts: list[str] = []
    for s_start, s_end in _sentence_spans(draft):
        if token in draft[s_start:s_end]:
            parts.append(draft[s_start:s_end])
    return " ".join(parts)


def atom_exigible_in(atom: Atom, text: str) -> bool:
    """Binding v2 — PRESENCIA PARCIAL por familia (motivación s243: 11/12
    synthesis-miss son pérdida parcial DENTRO de una estructura que la respuesta ya
    tocó — qualifier/miembro/cardinalidad podados al redactar; el 12º es
    selection-loss, fuera de este contrato). El solape genérico de anchors del
    fragmento YA NO liga (seed-270: 36/158 clean-FP eran átomos hermanos ligados por
    ≥2 anchors compartidos — evidencia, no set de tuning; este contrato se valida en
    cohorte fresca).

    F-RANGE   el texto contiene ≥1 número PROPIO del átomo (extremos/paso/tolerancia,
              excl. 0/1) o un id de scope — tocó ese rango y lo dejó incompleto.
    F-BUNDLE  el texto contiene ≥2 tokens PROPIOS del átomo (miembros∪cabecera; p.ej.
              1 token de miembro + 1 de la cabecera) — apriete adjudicado tras
              seed-271: con ≥1 token, UNA palabra técnica ubicua de un miembro
              ("sistema", "ajuste") ligaba bundles ajenos al claim (14/14 FP
              residuales); ≥2 tokens es el paralelo del criterio número-o-2-tokens
              del resto de familias y sigue cubriendo bundle_member_loss (la
              respuesta que cubre unos miembros nombra ≥2 tokens del schema).
    F-COUNT   el texto contiene el conteo declarado/enumerado (excl. 0/1) o el
              sustantivo contado.
    F-MANDATORY contrato propio (mandatory_safety_omission = callout obligatorio
              adyacente a un PROCEDIMIENTO que la respuesta da): exigible si el texto
              comparte ≥2 tokens con el contexto procedimental del fragmento
              (meta.procedural_context_tokens, extraído al detectar). La supresión de
              duplicados la da atom_satisfied (cláusula ya presente → jamás anexar).
    """
    clean = _FRAG_CITE.sub(" ", text or "")
    tokens = set(_content_tokens(clean))
    tokens_short = set(_content_tokens(clean, min_len=2))
    numbers = {v for v in _numbers_in(clean) if v not in (0.0, 1.0)}
    folded = _fold(clean)
    family = atom.get("family")
    meta = atom.get("meta") or {}
    if family == FAMILY_RANGE:
        own = {
            float(meta[k]) for k in ("lower", "upper", "step", "tolerance")
            if meta.get(k) is not None
        } - {0.0, 1.0}
        if own & numbers:
            return True
        return any(_fold(s) in folded for s in meta.get("scope") or [])
    if family == FAMILY_BUNDLE:
        propio = set(_content_tokens(meta.get("header") or "", min_len=2))
        for label in meta.get("members") or []:
            propio.update(_content_tokens(label, min_len=2))
        return len({t for t in propio if t in tokens_short}) >= 2
    if family == FAMILY_COUNT:
        own = {
            float(n) for n in (meta.get("declared_n"), meta.get("enumerated_n"))
            if n is not None
        } - {0.0, 1.0}
        if own & numbers:
            return True
        noun_tokens = _content_tokens(str(meta.get("noun") or ""), min_len=2)
        return any(t in tokens_short for t in noun_tokens)
    if family == FAMILY_MANDATORY:
        proc = set(meta.get("procedural_context_tokens") or [])
        return len(proc & tokens) >= 2
    return False


def bind_atoms(
    atoms: list[Atom],
    draft_answer: str,
    cited_fragment_ids: set,
    fragment_id,
) -> list[Atom]:
    """Exigibilidad (diseño §1.2 + C2 claim-proximity + binding v2, conservador: en
    duda NO exigible): el fragmento está CITADO en el borrador Y el texto ADYACENTE a
    la cita [Fn] de ESE fragmento (no toda la respuesta — crítico C2 del dúo) muestra
    PRESENCIA PARCIAL del átomo según su contrato de familia (atom_exigible_in;
    motivación s243 en su docstring). Sin cita localizable → no exigible."""
    if fragment_id not in set(cited_fragment_ids or set()):
        return []
    window = citation_window(draft_answer, fragment_id)
    if not window.strip():
        return []  # cita no localizable → conservador: nada exigible
    return [atom for atom in atoms if atom_exigible_in(atom, window)]


# Disclosure explícito de fuente inconsistente (guard s243 / C3): la ÚNICA forma de
# satisfacer un F-COUNT en conflicto es reconocer el conflicto, nunca la mera presencia
# de los números (crítico 3 de Sol: los números presentes evitaban justo el disclosure).
_DISCLOSURE_PATTERNS = (
    "el manual tambien indica", "el manual tambien senala", "el manual tambien recoge",
    "la fuente tambien indica", "tambien indica el manual", "el manual declara",
    "aunque el manual", "la fuente es inconsistente", "conteo inconsistente",
    "the manual also states", "the manual also indicates", "the source also states",
    "the manual is inconsistent",
)


def _disclosure_present(folded_text: str) -> bool:
    return any(pat in folded_text for pat in _DISCLOSURE_PATTERNS)


def _range_unit_satisfied(meta: dict, needed: set[float], clean_draft: str) -> bool:
    """La unidad del átomo debe aparecer PAREADA con alguno de sus números en el
    borrador (``30 V``), no basta el número pelado (C3: "quitar unidad" es mutación
    detectable). Sin unidad en el átomo no se exige."""
    unit = (meta.get("unit") or "").lower()
    if not unit:
        return True
    canon = _UNIT_SYNONYMS.get(unit, unit)
    pairs = _num_unit_pairs(clean_draft)
    return any(u == canon and v in needed for v, u in pairs)


def atom_satisfied(atom: Atom, draft_answer: str) -> bool:
    """¿El borrador ya conserva el átomo COMPLETO? (C3, crítico 3 de Sol)

    F-RANGE     extremos+paso+tolerancia Y unidad pareada Y tokens de scope presentes.
    F-COUNT     con ``conflict=True`` JAMÁS se satisface por presencia de números —
                solo por disclosure explícito ("el manual también indica ...").
    F-BUNDLE    todos los miembros Y la cabecera padre presentes.
    F-MANDATORY sin cambio (ya exigía trigger + anchors).
    """
    clean = _FRAG_CITE.sub(" ", draft_answer or "")
    draft_tokens = set(_content_tokens(clean))
    draft_numbers = _numbers_in(clean)
    dfold = _fold(clean)
    family = atom.get("family")
    meta = atom.get("meta") or {}
    if family == FAMILY_RANGE:
        needed = {
            float(meta[k]) for k in ("lower", "upper", "step", "tolerance")
            if meta.get(k) is not None
        }
        if not needed or not needed <= draft_numbers:
            return False
        if not _range_unit_satisfied(meta, needed, clean):
            return False
        for scope_id in meta.get("scope") or []:
            if _fold(scope_id) not in dfold:
                return False
        return True
    if family == FAMILY_COUNT:
        if meta.get("conflict"):
            return _disclosure_present(dfold)
        return {float(meta["declared_n"]), float(meta["enumerated_n"])} <= draft_numbers
    if family == FAMILY_BUNDLE:
        header_tokens = _content_tokens(meta.get("header") or "")
        if header_tokens and not set(header_tokens) <= draft_tokens:
            return False  # el bundle exige la cabecera padre, no solo los miembros
        members = meta.get("members") or []
        if not members:
            return True
        # min_len=2 en AMBOS lados (v3): con draft_tokens a min_len=3 un miembro
        # cuyo único token es de 2 chars ("PC") era insatisfacible por construcción
        draft_tokens_short = set(_content_tokens(clean, min_len=2))
        for label in members:
            toks = _content_tokens(label, min_len=2)
            if not toks:
                continue
            if not any(t in draft_tokens_short for t in toks):
                return False
        return True
    if family == FAMILY_MANDATORY:
        triggers = meta.get("triggers") or []
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


def _near_duplicate_span(a: str, b: str) -> bool:
    """Dedup del render (v4, bloqueador 1 de DEC-127b — hp001: la misma nota dos
    veces): dos spans YA FOLDEADOS son duplicados si son idénticos, o si solapan
    ≥90% (SequenceMatcher) con el MISMO contenido numérico Y el MISMO set de tokens
    de contenido — un token distinto ("sirena" vs "fuente") o un número distinto =
    hecho técnico distinto, se conservan ambos (apriete del review adversarial s271:
    el ratio solo, sin igualdad de contenido, colapsaba advertencias hermanas)."""
    if not a or not b:
        return False
    if a == b:
        return True
    if _numbers_in(a) != _numbers_in(b):
        return False
    if set(_content_tokens(a, min_len=2)) != set(_content_tokens(b, min_len=2)):
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.90


def _selection_priority(atom: Atom) -> int:
    """Orden pre-declarado del cap (v2, funnel probe-1 hp002): (0) F-MANDATORY —
    seguridad primero, el rationale original de la familia s243; (1) F-COUNT en
    conflicto — disclosure de fuente inconsistente; (2) resto."""
    family = atom.get("family")
    if family == FAMILY_MANDATORY:
        return 0
    if family == FAMILY_COUNT and (atom.get("meta") or {}).get("conflict"):
        return 1
    return 2


def _binding_strength(atom: Atom, draft_answer: str) -> int:
    """Fuerza de binding para el desempate del cap: nº de tokens PROPIOS del átomo
    (min_len=2) + números propios (excl. 0/1) compartidos con el borrador."""
    clean = _FRAG_CITE.sub(" ", draft_answer or "")
    draft_tokens = set(_content_tokens(clean, min_len=2))
    draft_numbers = {v for v in _numbers_in(clean) if v not in (0.0, 1.0)}
    own_tokens = set(_content_tokens(atom.get("span_text") or "", min_len=2))
    own_numbers = {v for v in _atom_numbers(atom) if v not in (0.0, 1.0)}
    return len(own_tokens & draft_tokens) + len(own_numbers & draft_numbers)


def _select_for_appendix(
    missing_atoms: list[Atom], draft_answer: str
) -> list[Atom]:
    """Selección v2 del cap (orden PRE-DECLARADO, funnel probe-1 hp002
    cap-competition — los RANGE monopolizaban los 4 slots y el callout MANDATORY
    core entraba 1/3):

      1º  F-MANDATORY (seguridad primero — rationale original de la familia);
      2º  F-COUNT en conflicto (disclosure de fuente inconsistente);
      3º  resto por FUERZA DE BINDING (tokens+números del átomo compartidos con el
          borrador, desc; empate → orden de llegada);
      cap global 4 + cap POR FAMILIA 2 (anti-monopolio RANGE).

    Exclusión 7-seg v2 por PARIDAD de display: el átomo con riesgo entra SOLO si el
    borrador ya contiene sus tokens display (``display_parity_ok``).

    v4 (s271, bloqueadores 1/2 de DEC-127b): (a) guard de contenido informativo —
    ningún lado del anexo puede ser vacío/celdas-en-blanco; si el lado-enumeración de
    un disclosure no es informativo, el disclosure ENTERO no dispara; (b) dedup del
    render — dos átomos con span idéntico tras fold (o solapado ≥90% con el mismo
    contenido numérico) anexan una sola vez."""
    eligible = []
    for a in missing_atoms:
        meta = a.get("meta") or {}
        if meta.get("seven_segment_risk") and not display_parity_ok(a, draft_answer):
            continue
        if not informative_span(a.get("span_text") or ""):
            continue
        if meta.get("conflict") and meta.get("enum_span_text") is not None and (
            not informative_span(str(meta.get("enum_span_text")))
        ):
            continue  # disclosure con lado-enumeración no informativo: no dispara
        eligible.append(a)
    ordered = sorted(
        enumerate(eligible),
        key=lambda pair: (
            _selection_priority(pair[1]),
            -_binding_strength(pair[1], draft_answer),
            pair[0],
        ),
    )
    selected: list[Atom] = []
    selected_keys: list[str] = []
    per_family: dict[str, int] = {}
    for _idx, atom in ordered:
        if len(selected) >= APPENDIX_CAP:
            break
        key = _fold_ws(atom.get("span_text") or "")[0]
        if any(_near_duplicate_span(key, prev) for prev in selected_keys):
            continue  # v4 dedup (bloqueador 1, hp001): mismo span → una sola vez
        family = str(atom.get("family"))
        if per_family.get(family, 0) >= APPENDIX_FAMILY_CAP:
            continue
        per_family[family] = per_family.get(family, 0) + 1
        selected_keys.append(key)
        selected.append(atom)
    return selected


def render_appendix(missing_atoms: list[Atom], draft_answer: str) -> str:
    """Sección "Información adicional del manual:" (SIN "verificada" — el span verbatim
    hereda la EXTRACCIÓN, no el píxel; dúo M5). Spans VERBATIM con cita [Fn]; selección
    v2 priorizada (ver ``_select_for_appendix``): MANDATORY → COUNT-conflicto → resto
    por fuerza de binding, cap global 4 + cap por familia 2. Los átomos cross-fragmento
    citan AMBOS fragmentos (conteo y enumeración). Puro código, cero LLM."""
    selected = _select_for_appendix(missing_atoms, draft_answer)
    if not selected:
        return ""
    lines = [APPENDIX_HEADER]
    for atom in selected:
        meta = atom.get("meta") or {}
        fragment_number = meta.get("fragment_number")
        cite = f" [F{fragment_number}]" if fragment_number else ""
        span = (atom.get("span_text") or "").strip()
        if meta.get("conflict") and meta.get("enum_span_text"):
            # v3: disclosure de DOS LADOS SIEMPRE — conteo declarado + enumeración
            # verbatim (sopa OCR incluida), cada lado con su cita ([Fi]·[Fj] si es
            # cross; misma cita dos veces si es intra).
            count_cite = f" [F{meta.get('count_fragment_number') or fragment_number}]"
            enum_cite = f" [F{meta.get('enum_fragment_number') or fragment_number}]"
            enum_span = str(meta.get("enum_span_text") or "").strip()
            lines.append(
                f'- Nota: el manual también indica: "{span}"{count_cite} · '
                f'"{enum_span}"{enum_cite}'
            )
        elif _contradicts(atom, draft_answer):
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
    query: str,
    chunks: list[dict],
    draft_answer: str,
    *,
    detect_fn=None,
) -> tuple[str, dict | None]:
    """Punto de entrada único del generador (post-generación, pre-return).

    off → devuelve el MISMO objeto respuesta y trace None (byte-idéntico).
    on  → detecta+binde+attesta sobre los fragmentos SERVIDOS y anexa si procede.
    El caller envuelve en try/except (fail-open total).

    ``detect_fn`` (v2): detector inyectable por fragmento (default ``detect_atoms``;
    el brazo híbrido del probe inyecta ``detect_atoms_hybrid`` con cliente). La etapa
    F-COUNT cross-fragmento (v2) corre sobre los fragmentos SERVIDOS y ATTESTADOS y
    exige que el fragmento del conteo o el de la enumeración esté CITADO."""
    if not contract_enabled():
        return draft_answer, None
    detect = detect_fn if detect_fn is not None else detect_atoms
    trace: dict[str, Any] = {
        "schema": "must_preserve_contract_v2",
        "identity_resolved": False,
        "cited_fragments": [],
        "atoms_detected": 0,
        "atoms_bound": 0,
        "atoms_missing": 0,
        "atoms_appended": 0,
        "cross_atoms_detected": 0,
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
    attested: dict[int, dict] = {}
    for idx, chunk in enumerate(chunks or [], start=1):
        if attest_identity(chunk.get("document_id"), resolved, catalog):
            attested[idx] = chunk
    missing: list[Atom] = []
    for idx, chunk in attested.items():
        if idx not in cited:
            continue
        atoms = detect(_chunk_text(chunk))
        trace["atoms_detected"] += len(atoms)
        bound = bind_atoms(atoms, draft_answer, cited, idx)
        trace["atoms_bound"] += len(bound)
        for atom in bound:
            if not atom_satisfied(atom, draft_answer):
                atom.setdefault("meta", {})["fragment_number"] = idx
                missing.append(atom)
    # v2: F-COUNT cross-fragmento sobre los fragmentos SERVIDOS y ATTESTADOS
    cross_atoms = detect_cross_fragment_count_atoms([
        {
            "fragment_number": idx,
            "text": _chunk_text(chunk),
            "document_id": chunk.get("document_id"),
            "page_number": chunk.get("page_number"),
        }
        for idx, chunk in attested.items()
    ])
    trace["cross_atoms_detected"] = len(cross_atoms)
    for atom in cross_atoms:
        meta = atom.get("meta") or {}
        count_idx = meta.get("count_fragment_number")
        enum_idx = meta.get("enum_fragment_number")
        primary = next(
            (idx for idx in (count_idx, enum_idx) if idx in cited), None
        )
        if primary is None:
            continue  # ninguno de los dos citado → no exigible (conservador)
        window = citation_window(draft_answer, primary)
        if not window.strip() or not atom_exigible_in(atom, window):
            continue
        trace["atoms_bound"] += 1
        if not atom_satisfied(atom, draft_answer):
            atom.setdefault("meta", {})["fragment_number"] = count_idx
            missing.append(atom)
    trace["atoms_missing"] = len(missing)
    appendix = render_appendix(missing, draft_answer)
    if not appendix:
        return draft_answer, trace
    trace["atoms_appended"] = len(_select_for_appendix(missing, draft_answer))
    trace["appendix_appended"] = True
    return draft_answer.rstrip() + "\n\n" + appendix, trace
