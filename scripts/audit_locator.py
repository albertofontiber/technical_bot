#!/usr/bin/env python3
"""audit_locator.py — localizador de citas GRADO-AUDIT (instrumento de medición, NO prod).

Problema (s79, cazado por el dúo): los probes de diagnóstico usaban
`strict_match.chunk_has_quote_strict`, que para localizar QUÉ chunk lleva una cita del gold:
  - en citas numéricas hace `all(a in nc)` con `in` CRUDO → '24' machea '240', '2222' machea
    CUALQUIER chunk con 2222 (otra clave/part-number) → FALSO-POSITIVO (chunk equivocado);
  - en prosa cae a `quote_overlap>=0.8` → falla con re-OCR/wording → FALSO-NEGATIVO (falso corpus-gap).

Este módulo NO toca el matcher de producción. Es un instrumento para el AUDIT de NO-PASS, con 3 reglas
que el dúo especificó:
  1. FRONTERA de dígito/palabra: anchors vía `anchor_present` (no `in` crudo) → mata el FP numérico.
  2. ATADO a (source_file, product_model) del gold: una cita solo cuenta si el chunk es del manual/
     producto del gold → mata el "chunk ajeno" (la clave 2222 de OTRO producto).
  3. PROSA robusta: containment de tokens distintivos (no overlap-0.8) → tolera OCR/acentos sin FN.

Salida: dado el texto de una cita + los chunks del source_file del gold, devuelve el/los chunk(s) que
la contienen con un score 0..1 (y el ID, para rastrearlo por el pipeline sin re-machear).

Leaf module: stdlib + strict_match (que es leaf). Sin stack RAG.
"""
from __future__ import annotations

import re

from strict_match import norm_ocr, distinctive, anchor_present

# Umbrales (calibrados/validados en los 5 golds conocidos — ver test_audit_locator.py).
TOKEN_FLOOR_PROSE = 0.55      # citas sin anchors: fracción de tokens distintivos presentes
TOKEN_FLOOR_ANCHORED = 0.35   # citas con anchors: soporte de prosa mínimo (anti "mismo número, otro hecho")
SCORE_FLOOR = 0.55            # score mínimo para declarar "presente / localizado"
MIN_TOKEN_LEN = 4             # tokens de contenido (descarta ruido corto)

# Stopwords ES+EN frecuentes — no son "distintivas" de un hecho.
_STOP = {
    "para", "como", "esta", "este", "esto", "estos", "estas", "cada", "todo", "toda",
    "todos", "todas", "desde", "hasta", "sobre", "entre", "donde", "cuando", "porque",
    "pero", "tras", "segun", "según", "puede", "deben", "debe", "tiene", "tienen",
    "the", "and", "for", "that", "with", "this", "from", "have", "has", "are", "was",
    "which", "must", "shall", "into", "their", "they", "como", "una", "uno", "unos",
    "unas", "del", "los", "las", "que", "con", "por", "sin", "mas", "más",
}


def _content_tokens(s: str) -> list[str]:
    """Tokens distintivos de contenido: len>=MIN_TOKEN_LEN, no stopword, OCR-normalizados."""
    return [t for t in re.findall(r"[a-z0-9]+", norm_ocr(s))
            if len(t) >= MIN_TOKEN_LEN and t not in _STOP]


def token_containment(quote: str, content: str) -> float:
    """Fracción de tokens DISTINTIVOS del quote presentes en el content (robusto a OCR)."""
    qt = set(_content_tokens(quote))
    if not qt:
        return 0.0
    ct = set(_content_tokens(content))
    return len(qt & ct) / len(qt)


def anchor_coverage(quote: str, content: str) -> float | None:
    """Fracción de anchors (números>=2díg / códigos) presentes con FRONTERA (anchor_present).
    None si la cita no tiene anchors (es prosa pura)."""
    anchors = distinctive(quote)
    if not anchors:
        return None
    nc = norm_ocr(content)
    return sum(1 for a in anchors if anchor_present(a, nc)) / len(anchors)


def citation_score(quote: str, content: str) -> float:
    """Confianza 0..1 de que `content` contiene la cita del gold.

    - Cita de PROSA pura (sin anchors): score = token_containment (robusto a OCR).
    - Cita CON anchors: MEZCLA de cobertura-de-anchors (con frontera de dígito) y soporte de
      prosa. NO exige cov==1 (un nº de sección "3.1.1.5" del gold puede no estar en el cuerpo del
      chunk → eso re-introduciría el FN). PERO exige soporte de prosa mínimo
      (containment >= TOKEN_FLOOR_ANCHORED) → mata el "mismo número, hecho ajeno" (la clave 2222
      de otro contexto): números presentes sin la prosa del hecho = NO es el chunk.
    """
    cov = anchor_coverage(quote, content)
    tc = token_containment(quote, content)
    if cov is None:                          # prosa pura
        return tc
    if tc < TOKEN_FLOOR_ANCHORED:            # anchors presentes pero sin contexto del hecho -> ajeno
        return 0.0
    return 0.5 * cov + 0.5 * tc              # mezcla anclada: ambos contribuyen


def citation_present(quote: str, content: str) -> bool:
    return citation_score(quote, content) >= SCORE_FLOOR


def missing_distinctive(quote: str, content: str) -> list[str]:
    """Tokens distintivos del quote AUSENTES del content. Señal de INFERENCIA/paráfrasis del gold:
    si el hecho se localiza (valor documentado presente) pero faltan términos del enunciado, esos
    términos pueden ser etiqueta inferida por el autor (p.ej. 'failsafe'/'desenergiza' en cat007)."""
    return sorted(set(_content_tokens(quote)) - set(_content_tokens(content)))


def _source_match(chunk_sf: str | None, gold_sources: list[str]) -> bool:
    """Match robusto de source_file: el del chunk (a veces truncado/sin .pdf) contra los del gold.
    Containment en cualquier dirección, OCR-normalizado."""
    if not chunk_sf:
        return False
    c = norm_ocr(chunk_sf)
    for g in gold_sources:
        ng = norm_ocr(g).removesuffix(".pdf")
        if ng and (ng in c or c in ng):
            return True
        # match por el código de manual (primer token alfanumérico largo, p.ej. 55315008)
        gtok = re.findall(r"[a-z0-9]{5,}", ng)
        if gtok and gtok[0] in c:
            return True
    return False


def locate(quote: str, chunks: list[dict], gold_sources: list[str] | None = None,
           require_source: bool = True) -> list[dict]:
    """Localiza la cita entre `chunks`. Devuelve [{id, score, source_file, product_model}, ...]
    ordenados por score desc, solo los que pasan SCORE_FLOOR.

    Si `gold_sources` y require_source: SOLO considera chunks cuyo source_file machee la fuente
    del gold (regla 2 — mata el chunk ajeno). require_source=False = búsqueda libre (diagnóstico).
    """
    out = []
    for c in chunks:
        if require_source and gold_sources:
            if not _source_match(c.get("source_file"), gold_sources):
                continue
        s = citation_score(quote, c.get("content") or "")
        if s >= SCORE_FLOOR:
            out.append({"id": c.get("id"), "score": round(s, 3),
                        "source_file": c.get("source_file"),
                        "product_model": c.get("product_model")})
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


# --- s81: predicado grado-audit a NIVEL DE HECHO (DEC-061 + dúo #9 r1/r2/r3) --------------
# fact_match_score EXIGE el VALOR distintivo del hecho (nº anclable / código) en el chunk + usa el
# texto como CONTEXTO que desambigua → mata el FP 'prosa del enunciado sin el dato' (crít dúo r3) y
# el FN del token-corto (NC-C-NA, dúo r1). La CONFIANZA del bucket sale del SCORE (no a priori, r2).
# `measurable` segrega los valores no-verificables léxicamente (single-digit '1 A'/'4 circuitos',
# frases sin tokens) → NO se bucketizan (ni falso CORPUS-GAP ni falso SINTESIS); candidatos al juez
# semántico (diferido). Leaf, testeable; DEC-061(e)(ii).
_GENERIC_CODES = {"1a", "2a"}  # códigos demasiado genéricos para anchor (1 A / 2 A amperaje)


def short_codes(valor: str) -> list[str]:
    """Códigos/siglas ESTRUCTURALES del valor que distinctive()/_content_tokens NO captan
    (NC-C-NA, PWR-R, ISO-X, 6K8): separador (.-/) o dígito, contienen letra, >=3 alnum (dúo r2:
    >=3 evita 'r.1'/secciones cortas). anchor_present (frontera) los recupera sin el FP del `in`
    crudo. El guard estructural excluye palabras de prosa."""
    out = []
    for t in re.findall(r"[a-z0-9][a-z0-9.\-/]*[a-z0-9]", norm_ocr(valor or "")):
        alnum = re.sub(r"[^a-z0-9]", "", t)
        structural = bool(re.search(r"[.\-/]", t)) or bool(re.search(r"\d", t))
        if structural and re.search(r"[a-z]", t) and 3 <= len(alnum) <= 8 and alnum not in _GENERIC_CODES:
            out.append(t)
    return out


def measurable(valor: str, texto: str = "") -> bool:
    """¿El VALOR del hecho es verificable LÉXICAMENTE? (corrección dúo r3 — antes se medía el texto,
    que marcaba presente '1 A' por la prosa del enunciado sin el dato):
      - datum ANCLABLE (nº≥2díg / código / short_code): 47 kohm, NC-C-NA, 105 → se EXIGE el dato.
      - prosa pura SIN dígito (claim verbal): 'bucle cerrado', 'Retorno' → se matchea el claim.
    NO-medible (→ candidato al juez semántico, diferido): valor con dígito pero SIN nº anclable
    ('1 A', '4 circuitos' — single-digit NO se ancla por riesgo FP) o frase sin tokens ('una vez al
    año'). El funnel NO los bucketiza (evita falso CORPUS-GAP y falso SINTESIS-por-prosa)."""
    v = valor or ""
    if distinctive(v) or short_codes(v):
        return True
    if re.search(r"\d", v):
        return False
    return len(_content_tokens(v)) >= 1


def fact_match_score(valor: str, texto: str, content: str) -> "float | None":
    """Score 0..1 de presencia del HECHO (su VALOR distintivo + contexto) en `content`; None si el
    valor es no-medible. EXIGE el datum del valor cuando lo tiene (cov>0 obligatorio → mata el FP
    'prosa del enunciado sin el valor', crít dúo r3); el texto da el contexto que desambigua (mata el
    FP 'mismo nº, hecho ajeno'). Valor-prosa (sin dígito) → citation_score del claim."""
    v = valor or ""
    pin = distinctive(v) | set(short_codes(v))
    if pin:
        nc = norm_ocr(content or "")
        cov = sum(1 for a in pin if anchor_present(a, nc)) / len(pin)
        if cov == 0:
            return 0.0
        return 0.5 * cov + 0.5 * token_containment((texto + " " + v).strip(), content)
    if re.search(r"\d", v):
        return None  # dígito no-anclable (1 A / 4 circuitos) → no-medible (coherente con measurable)
    if _content_tokens(v):
        return citation_score((texto + " " + v).strip() if texto else v, content)
    return None


_UNIT_QUANTITY_RE = re.compile(
    r"(?<!\d)([+\-]?\d+(?:[.,]\d+)?)\s*(?:\|\s*)?"
    r"(kohm|ohm|ma|vac|vdc|kw|hz|seg|sec|min|a|v|w|s)\b",
    re.I,
)
_SCIENTIFIC_NOTATION_RE = re.compile(r"(?<!\d)(\d+)\s*\^\s*(\d+)(?!\d)")


def _unit_quantities(value: str) -> set[str]:
    """Return canonical numeric-unit pairs, including one-digit values."""
    return {
        number.replace(",", ".") + unit.lower()
        for number, unit in _UNIT_QUANTITY_RE.findall(norm_ocr(value or ""))
    }


def decimal_notation_bridge(value: str, content: str) -> bool:
    """Detect the same decimal written with the opposite separator."""
    normal_content = norm_ocr(content or "")
    for number in re.findall(r"[+\-]?\d+[.,]\d+", norm_ocr(value or "")):
        alternate = number.translate(str.maketrans({",": ".", ".": ","}))
        original_hit = re.search(rf"(?<!\d){re.escape(number)}(?!\d)", normal_content)
        alternate_hit = re.search(rf"(?<!\d){re.escape(alternate)}(?!\d)", normal_content)
        if alternate_hit and not original_hit:
            return True
    return False


def collapsed_superscript_bridge(value: str, content: str) -> bool:
    """Detect extraction loss such as rendered ``10^5`` becoming ``105``.

    This never grants support by itself.  It only makes a same-family source
    candidate visible to the semantic support judge, which must still bind the
    value to the correct attribute and context.
    """
    normal_content = norm_ocr(content or "")
    for base, exponent in _SCIENTIFIC_NOTATION_RE.findall(value or ""):
        collapsed = base + exponent
        if re.search(rf"(?<!\d){re.escape(collapsed)}(?!\d)", normal_content):
            return True
    return False


def _representation_context_overlap(text: str, content: str) -> bool:
    """Require an attribute/context tie in addition to a reformatted value.

    Four-character stems deliberately bridge close ES/EN technical cognates
    (``contacto/contact`` and ``operaciones/operations``) while rejecting an
    unrelated occurrence of a short collapsed number such as catalogue 105.
    """
    expected = {token[:4] for token in _content_tokens(text) if len(token) >= 4}
    observed = {token[:4] for token in _content_tokens(content) if len(token) >= 4}
    return bool(expected & observed)


def support_candidate_priority(
    valor: str,
    texto: str,
    content: str,
    same_family: bool,
) -> "tuple[int, float] | None":
    """Select bounded candidates for semantic re-adjudication.

    The normal calibrated fact score remains the primary lane.  A narrow
    same-family bridge admits candidates only for known representation changes:
    decimal comma/point or a lost superscript.  The bridge is candidate recall,
    never an automatic support verdict.
    """
    score = fact_match_score(valor, texto, content)
    required_quantities = _unit_quantities(valor)
    quantities_complete = required_quantities <= _unit_quantities(content)
    decimal_bridge = decimal_notation_bridge(valor, content)
    superscript_bridge = collapsed_superscript_bridge(valor, content)
    bridge = bool(
        same_family
        and quantities_complete
        and _representation_context_overlap(texto, content)
        and (decimal_bridge or superscript_bridge)
    )
    if not bridge and (score is None or score < SCORE_FLOOR):
        return None
    return (int(bridge), float(score or 0.0))


def support_l1_guard_allows(
    valor: str,
    texto: str,
    content: str,
    same_family: bool,
) -> bool:
    """Preserve already-adjudicated support across representation changes.

    The caller has already obtained semantic support votes.  This secondary
    lexical guard rejects collisions, but must not erase a same-family support
    solely because Markdown cells split a quantity or extraction flattened a
    superscript.  A representation bridge never creates support on its own.
    """
    score = fact_match_score(valor, texto, content)
    if score is not None and score >= SCORE_FLOOR - 0.15:
        return True
    priority = support_candidate_priority(
        valor, texto, content, same_family=same_family
    )
    return bool(priority is not None and priority[0] == 1)


def fact_present(valor: str, texto: str, content: str) -> "bool | None":
    """¿`content` contiene el hecho? True/False, o None si el valor es no-medible léxicamente."""
    s = fact_match_score(valor, texto, content)
    return None if s is None else s >= SCORE_FLOOR
