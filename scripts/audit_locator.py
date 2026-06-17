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
