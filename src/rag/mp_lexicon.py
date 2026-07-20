"""(S274, higiene del dúo — punto 10) Léxico MANDATORY + segmentación de texto en
módulo NEUTRO, sin dependencias de must_preserve ni de post_rerank_coverage.

Motivo: la card de callout-MANDATORY (C1, `COVERAGE_MANDATORY_CALLOUT`) necesita el
léxico cerrado en la lane de coverage; importarlo desde `must_preserve` crearía
bidireccionalidad (must_preserve ya importa `post_rerank_coverage` lazy en
`_chunk_text`). Este módulo solo depende de `catalog._fold` + `re`.

El léxico es el CERRADO bilingüe validado en Etapa-1 (DEC-122/130): "antes de"/"before"
JAMÁS como gatillo solo (hallazgo F8 del dúo s269) — solo colocados con "debe(n)"/"must"
en la MISMA oración.
"""
from __future__ import annotations

import re

from .catalog import _fold

# ─────────────────────────── segmentación de texto ───────────────────────────

_SENT_BOUNDARY = re.compile(r"(?<=[.!?;])\s+")


def line_spans(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    pos = 0
    for line in (text or "").split("\n"):
        out.append((pos, pos + len(line), line))
        pos += len(line) + 1
    return out


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Spans (start, end) de oraciones: por línea y, dentro de línea, por puntuación
    final + espacio (los decimales "1,5"/"1.5" no parten porque no llevan espacio)."""
    spans: list[tuple[int, int]] = []
    for start, _end, line in line_spans(text):
        offset = 0
        for m in _SENT_BOUNDARY.finditer(line):
            if line[offset:m.start()].strip():
                spans.append((start + offset, start + m.start()))
            offset = m.end()
        if line[offset:].strip():
            spans.append((start + offset, start + len(line.rstrip())))
    return spans


# ─────────────────────────── léxico MANDATORY cerrado ───────────────────────────

MANDATORY_TERMS = (
    # es (formas foldeadas: sin acentos)
    "imprescindible", "obligatorio", "obligatoria", "obligatorios", "obligatorias",
    "nunca", "jamas", "advertencia", "atencion", "peligro", "evite", "eviten",
    # en
    "mandatory", "never", "warning", "caution", "danger",
)
MANDATORY_PHRASES = (
    "de vital importancia", "es vital", "en ningun caso", "must not", "it is essential",
)
# Gatillos que son VERBO CONJUGADO por sí mismos (imperativo/subjuntivo del propio
# léxico). Base del flag MP_MANDATORY_VERB_TRIGGER (Fable-M1 s274): en la whitelist de
# forma-buena, un gatillo-verbo cuenta como el verbo conjugado de SU cláusula; los
# gatillos-sustantivo (advertencia/atención/peligro) JAMÁS — una cabecera sola sigue
# sin pasar.
MANDATORY_VERB_TRIGGERS = frozenset({"evite", "eviten"})


def trigger_present(trigger: str, folded: str) -> bool:
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


def mandatory_triggers(sentence: str) -> list[str]:
    folded = _fold(sentence)
    triggers = [
        term for term in (*MANDATORY_TERMS, *MANDATORY_PHRASES)
        if trigger_present(term, folded)
    ]
    # co-ocurrencias: "debe(n) ... antes de" / "before ... must"
    for compound in ("debe(n)+antes de", "must+before"):
        if trigger_present(compound, folded):
            triggers.append(compound)
    return triggers
