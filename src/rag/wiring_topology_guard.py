"""Guard determinista de topología de cableado (C' del diseño s286, hp018).

Clase que cubre (DEC-160c): instrucciones AFIRMATIVAS de topología de conexionado de
sirenas/salidas supervisadas inventadas por el writer cuando la fuente solo muestra el
conexionado como diagrama (la traza s286: 10/10 con «conecta las sirenas en serie» — serie
eléctrica real, rompe la supervisión y reparte la tensión).

Contrato (espejo de ``apply_answer_conflict_guard`` — sustitución de bloques + re-validación
whole-answer + escalada fail-closed; cero llamadas a modelo/red):

- SEGMENTACIÓN: los code-fences son bloques ATÓMICOS (se extraen antes de partir por líneas
  en blanco). Heading = ``^#{1,6}\\s`` o línea-negrita standalone; sección = hasta el siguiente
  heading de nivel <=; los stems de los headings se HEREDAN por la cadena completa de ancestros.
- SCOPE: bloques cuyo texto (o herencia de headings) contiene un stem de sirena/salida/NAC.
- DETECCIÓN en scope:
  (a) léxico de topología (bilingüe, residual declarado en el brief v3.1) sin negación en
      ventana de 4 tokens;
  (b) cadena de polaridad agnóstica al conector (−/negativo … +/positivo … siguiente/anterior
      en la misma frase);
  (c) fences: WHITELIST invertida — todo fence en scope es unsafe SALVO tabla markdown o
      contenido verbatim-normalizado presente en un chunk servido.
- SOPORTE: una aserción (a)/(b) solo se legitima si un fragmento [Fn] citado EN ESE BLOQUE
  ([Fn] = chunks[n-1]) contiene un término de topología sin negación y un stem de sirena.
- ACCIÓN: bloque unsafe → notice determinista (detector-clean POR CONTRATO, ver test);
  re-validación del resultado; si sigue unsafe → fail-closed de respuesta completa.

Flag: ``WIRING_TOPOLOGY_GUARD`` (default ON desde s319/DEC-210 — graduación del
lote Railway s286; off explícito = rollback sin deploy; parser ESTRICTO en el
lector, generator._guard_estricto). Posición: tras ``apply_answer_planner``
(generator) y ANTES de must_preserve → conflict_guard → EC, para que los appenders
re-validen sobre el texto ya guardado.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

WIRING_GUARD_CONTRACT = "wiring_topology_guard_s286_v1"

_STEMS = ("siren", "salida de sirena", "salidas de sirena", " nac ", "circuito de sirena")

_TOPOLOGY_TERMS = (
    "en serie",
    "en cadena",
    "encadena",
    "encadenar",
    "encadenando",
    "una tras otra",
    "uno tras otro",
    "en cascada",
    "daisy-chain",
    "daisy chain",
    "chained",
    "in series",
    "one after another",
)

_NEGATION_TOKENS = {"no", "nunca", "jamas", "not", "never", "evite", "evitar", "evita", "sin"}

_HEADING_MD = re.compile(r"^(#{1,6})\s+(.*)$")
_HEADING_BOLD = re.compile(r"^\*\*[^*]+\*\*:?\s*$")
_MD_TABLE_LINE = re.compile(r"^\|.*\|\s*$")
_CITATION = re.compile(r"\[F(\d+)\]")
_FENCE = re.compile(r"```[^\n]*\n.*?(?:```|\Z)", re.DOTALL)
# frase: conector −→+ con referencia de secuencia (agnóstico al conector: «al», «→», «con»…)
_POLARITY_CHAIN = re.compile(
    r"(?:−|\bnegativo\b|(?<![\w`])-(?![\w-]))[^.!?\n]{0,60}?"
    r"(?:\+|\bpositivo\b)[^.!?\n]{0,80}?"
    r"\b(?:siguiente|proxima|anterior|next)\b",
)


def _normalize(text: str) -> str:
    """casefold + sin acentos + markdown fuera + whitespace colapsado."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _has_stem(norm: str) -> bool:
    padded = f" {norm} "
    return any(s in padded for s in _STEMS)


def _topology_hits(norm: str) -> list[tuple[str, int]]:
    """Términos de topología SIN negación en ventana de 4 tokens previos."""
    hits: list[tuple[str, int]] = []
    for term in _TOPOLOGY_TERMS:
        for m in re.finditer(re.escape(term), norm):
            prev = norm[: m.start()].split()[-4:]
            if not any(tok in _NEGATION_TOKENS for tok in prev):
                hits.append((term, m.start()))
    return hits


def _chunk_supports_topology(chunk: dict) -> bool:
    norm = _normalize(str(chunk.get("content") or ""))
    return _has_stem(norm) and bool(_topology_hits(norm))


def _is_md_table(fence_body: str) -> bool:
    rows = [ln for ln in fence_body.splitlines() if _MD_TABLE_LINE.match(ln.strip())]
    return len(rows) >= 2


def _fence_verbatim_in_served(fence_body: str, chunks: list[dict]) -> bool:
    needle = _normalize(fence_body)
    if not needle:
        return True  # fence vacío: nada que inventar
    return any(needle in _normalize(str(c.get("content") or "")) for c in chunks)


def _split_blocks(answer: str) -> list[dict]:
    """Fences atómicos primero; el resto se parte por líneas en blanco.

    Cada bloque: {text, is_fence, heading_level|None}. heading_level: 1-6 para ``#``,
    7 para línea-negrita standalone (pseudo-heading del writer).
    """
    blocks: list[dict] = []
    pos = 0
    for m in _FENCE.finditer(answer):
        before = answer[pos : m.start()]
        blocks.extend(_split_prose(before))
        blocks.append({"text": m.group(0), "is_fence": True, "heading_level": None})
        pos = m.end()
    blocks.extend(_split_prose(answer[pos:]))
    return blocks


def _split_prose(text: str) -> list[dict]:
    out: list[dict] = []
    for raw in re.split(r"\n\s*\n", text):
        if not raw.strip():
            continue
        level = None
        first = raw.strip().splitlines()[0]
        md = _HEADING_MD.match(first)
        if md:
            level = len(md.group(1))
        elif _HEADING_BOLD.match(first):
            level = 7
        out.append({"text": raw, "is_fence": False, "heading_level": level})
    return out


def _inherited_stem(blocks: list[dict], index: int) -> bool:
    """¿Algún heading ANCESTRO (cadena completa) del bloque lleva stem?"""
    level_floor = 99
    for j in range(index, -1, -1):
        b = blocks[j]
        lvl = b.get("heading_level")
        if lvl is not None and lvl < level_floor:
            if _has_stem(_normalize(b["text"])):
                return True
            level_floor = lvl
    return False


_NOTICE = (
    "⚠️ Conexionado de las sirenas: la fuente citada muestra este detalle en un DIAGRAMA "
    "que no puede transcribirse con fiabilidad a pasos de texto. Antes de cablear, consulta "
    "la figura del manual citado en esta respuesta (respeta la resistencia final de línea y "
    "la polaridad exactas que muestra el diagrama)."
)

_FAIL_CLOSED = (
    "No puedo ofrecer una instrucción de conexionado segura para las salidas de sirena con "
    "la evidencia validada: el detalle vive en un diagrama del manual. Consulta la figura "
    "del documento citado antes de actuar."
)


def _scan(answer: str, chunks: list[dict]) -> tuple[list[dict], list[int]]:
    blocks = _split_blocks(answer)
    unsafe: list[int] = []
    for i, b in enumerate(blocks):
        norm = _normalize(b["text"])
        in_scope = _has_stem(norm) or _inherited_stem(blocks, i)
        if not in_scope:
            continue
        if b["is_fence"]:
            body = re.sub(r"^```[^\n]*\n?|```$", "", b["text"].strip())
            if not _is_md_table(body) and not _fence_verbatim_in_served(body, chunks):
                unsafe.append(i)
            continue
        hits = _topology_hits(norm)
        chain = bool(_POLARITY_CHAIN.search(norm))
        if not hits and not chain:
            continue
        cited = [int(n) for n in _CITATION.findall(b["text"])]
        supported = any(
            0 < n <= len(chunks) and _chunk_supports_topology(chunks[n - 1]) for n in cited
        )
        if not supported:
            unsafe.append(i)
    return blocks, unsafe


def apply_wiring_topology_guard(
    chunks: list[dict],
    answer: str,
    *,
    contract_version: str = WIRING_GUARD_CONTRACT,
) -> tuple[str, dict[str, Any]]:
    """Devuelve (respuesta_segura, traza). Determinista, sin llamadas externas."""
    if not isinstance(answer, str):
        raise TypeError("wiring topology guard requires a string answer")
    if contract_version != WIRING_GUARD_CONTRACT:
        raise ValueError(f"unsupported wiring guard contract: {contract_version}")

    blocks, unsafe = _scan(answer, chunks)
    trace: dict[str, Any] = {
        "contract": WIRING_GUARD_CONTRACT,
        "blocks_scanned": len(blocks),
        "unsafe_blocks": len(unsafe),
        "action": "noop",
    }
    if not unsafe:
        trace["output_answer_sha256"] = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        return answer, trace

    parts = [b["text"] for b in blocks]
    notice_done = False
    for i in unsafe:
        parts[i] = "" if notice_done else _NOTICE
        notice_done = True
    revised = "\n\n".join(p for p in parts if p.strip())
    action = "surgical_repair"

    _, still_unsafe = _scan(revised, chunks)
    if still_unsafe:
        revised = _FAIL_CLOSED
        action = "fail_closed"
        _, still_unsafe = _scan(revised, chunks)
        if still_unsafe:  # pragma: no cover - invariante (la plantilla es detector-clean)
            raise RuntimeError("wiring topology guard could not establish a safe output")

    trace.update(
        action=action,
        output_answer_sha256=hashlib.sha256(revised.encode("utf-8")).hexdigest(),
    )
    return revised, trace
