#!/usr/bin/env python3
"""strict_match.py — matcher ESTRICTO de hechos (canonical, PR#15).

Hogar único del matcher estricto: ¿aparece el VALOR distintivo de un quote/hecho
(números >=2 dígitos, códigos de modelo; OCR-normalizado) en un texto dado? Quotes
de prosa pura (sin valores) → overlap alto + ancla contigua.

Leaf module: SOLO stdlib (re, unicodedata). Sin imports del stack RAG → importable
desde el scorer offline (atomic_scorer.py) y desde el eval de retrieval
(retrieval_eval.py), sin arrastrar Supabase/embeddings.

Historia: nació en retrieval_eval.py (s29, recall determinista); extraído aquí (s32)
para que el scorer atómico del ruler reuse EXACTAMENTE el mismo matcher (RULER_DESIGN §3),
sin duplicar la lógica.
"""
from __future__ import annotations

import re
import unicodedata

WINDOW = 25  # longitud mínima de substring distintivo del quote
OVERLAP_THRESHOLD = 0.6  # token-overlap mínimo (matcher fuzzy/legacy)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def _toks(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", norm(s)))


def quote_overlap(quote: str, content: str) -> float:
    """Fracción de tokens del quote presentes en el content (match fuzzy)."""
    qt = _toks(quote)
    return len(qt & _toks(content)) / len(qt) if qt else 0.0


def chunk_has_quote(content: str, quote: str) -> bool:
    """Substring exacto (barato/preciso) O token-overlap >= umbral (tolera la
    reescritura/OCR entre el gold-quote de Opus y el chunk de LlamaParse — el
    substring estricto daba falsos 'no recuperado', p.ej. hp020 a 76-87% overlap)."""
    nc, nq = norm(content), norm(quote)
    if not nq:
        return False
    if len(nq) <= WINDOW:
        if nq in nc:
            return True
    else:
        for i in range(0, len(nq) - WINDOW + 1, 5):
            if nq[i:i + WINDOW] in nc:
                return True
    return quote_overlap(quote, content) >= OVERLAP_THRESHOLD


# --- Matcher ESTRICTO (specific-fact presence) ---------------------------------
# El fuzzy de arriba (substring O overlap>=0.6) SOBREESTIMA recall en preguntas de
# spec: cuenta números/términos compartidos como "fact presente" (hp019 daba 4/4
# fuzzy pero la tabla de valores no estaba recuperada). El estricto exige que los
# VALORES distintivos del quote (números de >=2 dígitos, códigos de modelo)
# aparezcan TODOS en el chunk (OCR-normalizado: guiones –/—/− → -, "+ 60"→"+60").
# Quotes de prosa pura (sin valores) → overlap alto (0.8) + ancla contigua.
_DASHES = {0x2013: "-", 0x2014: "-", 0x2212: "-", 0x2010: "-", 0x2011: "-"}


def norm_ocr(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.translate(_DASHES).replace("º", "°")
    s = re.sub(r"(?<=[+\-\d])\s+(?=\d)", "", s)  # "+ 60"->"+60", "1 000"->"1000"
    return " ".join(s.split())


# (?<!\d): un +/- PEGADO a un dígito previo es OPERADOR (separador de rango "110-230" o
# suma SIN espacios "99+99"), NO signo → captura el número SIN signo (230, 99). El signo se
# conserva solo si NO va precedido de dígito: negativo real "-10"/"+55", y la suma CON
# espacios "99 + 99" (norm_ocr la deja como "99 +99"). Sin esto, distinctive("110-230")→
# "-230", que fallaba la frontera de dígito de _anchor_present (atomic_scorer) Y de
# _value_on_page (locate_fact) → falso-miss (s40, cat005 5/6→6/6, 19 golds intactos).
# Efecto colateral ACOTADO (1/134 hechos = solo cat001 "159+159/99+99"): soltar el signo de
# una suma sin espacios relaja `all(anchor in chunk)` en los instrumentos de retrieval
# (audit_retrieval_funnel/retrieval_eval), NO en prod ni en el scoring de golds. Ver DEC-011.
_NUM = re.compile(r"(?<!\d)[+\-]?\d[\d.,]*")
_MODEL = re.compile(r"\b[a-z]{2,}-?\d{2,}[a-z]*\b")


def distinctive(quote: str) -> set[str]:
    """Valores que identifican el fact: números de >=2 dígitos + códigos de modelo."""
    q = norm_ocr(quote)
    nums = {n.strip(".,") for n in _NUM.findall(q) if len(re.findall(r"\d", n)) >= 2}
    return nums | set(_MODEL.findall(q))


def anchor_present(anchor: str, text: str) -> bool:
    """¿aparece `anchor` como número/token COMPLETO en `text` (ya norm_ocr'd)?

    Frontera de presencia del matcher estricto. CANÓNICA desde s46 (DEC-019/F0#2):
    antes la frontera vivía SOLO en el scorer atómico (match_fact) y estaba AUSENTE
    aquí y en audit_retrieval_funnel, que usaban substring crudo → '99'∈'990'/'1993'
    inflaba SÍNTESIS en el funnel (artefacto cazado en s45). Dos políticas:
      - Numérico ("24", "+60", "295") → frontera de DÍGITO: casa "24" en "24V"/
        "24 °C" pero NO en "240"/"1240" (corrige '40'∈'240' de PR#15, hp003 s32).
      - Código de modelo ("afp1010") → frontera de PALABRA: token completo.
    NOTA: chunk_has_quote_strict (recall, live stack) conserva A PROPÓSITO el `in`
    crudo sobre haystacks grandes — su frontera es otra decisión (F0#6, A/B recall).
    `text` debe venir ya normalizado (norm_ocr); el anchor se escapa para la regex.

    LÍMITE CONOCIDO (deuda s46, DEC-019/F0#2): la frontera de DÍGITO no bloquea el
    separador de millar/decimal español → "792" casa en "13.792" y "159" en "2.159"
    (FP raro). Se mantiene `\\d` y NO `[\\d.,]` porque `[\\d.,]` introduce FN COMUNES,
    verificado: bloquea "295" en "295, 300" (coma de lista) y en "295." (punto de fin
    de frase). El gate usa anchors FUERTES (≥2 anchors / código / ≥3 díg), que diluyen
    el FP de millar. Frontera compuesta (bloquear solo díg–puntuación–díg) = mejora
    futura; cambia el scoring de golds → exige re-baseline (ver TECH_DEBT).
    """
    bound = r"\d" if re.fullmatch(r"[+\-]?\d[\d.,]*", anchor) else r"\w"
    return re.search(rf"(?<!{bound}){re.escape(anchor)}(?!{bound})", text) is not None


def chunk_has_quote_strict(content: str, quote: str) -> bool:
    nc = norm_ocr(content)
    anchors = distinctive(quote)
    if anchors:
        return all(a in nc for a in anchors)
    nq = norm_ocr(quote)
    if len(nq) > WINDOW and any(nq[i:i + WINDOW] in nc
                                for i in range(0, len(nq) - WINDOW + 1, 5)):
        return True
    return quote_overlap(quote, content) >= 0.8
