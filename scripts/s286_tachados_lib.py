"""s286 — tokenizador determinista de marcas `~~` (spec: evals/s286_tachados_design_v1_1.md §A+).

Regla adjudicada (Alberto, packet s285: ~~ = énfasis del PDF mal renderizado como tachado):
retirar los MARCADORES conservando el texto, sin tocar los usos LITERALES de tildes (arte
ASCII, subrayados-puntero). Determinista, por línea, idempotente.

Clasificación de un run de tildes:
- exactamente 2               → marcador toggle (abre/cierra énfasis)
- exactamente 4 FLANQUEADO    → cierre+apertura adyacentes (p.ej. ``del~~~~servicio``);
  flanqueado = carácter no-espacio a AMBOS lados. Un ``~~~~`` standalone es LITERAL.
- 3, o ≥5, o 4 no-flanqueado  → LITERAL intocable.

Emparejado: por línea, en orden; un marcador sin pareja queda HUÉRFANO (se conserva tal cual
y se reporta). El span de cada par se extrae para el manifest (eyeball anti falso-par).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_RUN = re.compile(r"~+")

# flags de eyeball del manifest (v1.1: anti falso-par)
SPAN_EYEBALL_LEN = 80
_SENTENCE_PUNCT = re.compile(r"[.;:!?]\s")


@dataclass
class LineResult:
    text: str
    pairs: list[str] = field(default_factory=list)      # spans des-marcados
    orphans: int = 0                                    # marcadores sin pareja (conservados)
    literals: int = 0                                   # runs literales conservados
    run4_literal: int = 0                               # run-4 standalone conservados


def _classify(line: str) -> list[tuple[int, int, str]]:
    """[(start, end, kind)] con kind ∈ {'marker','marker2','literal'}.

    'marker' = run-2 · 'marker2' = run-4 flanqueado (cuenta como DOS marcadores
    consecutivos: cierre+apertura) · 'literal' = resto.
    """
    out = []
    for m in _RUN.finditer(line):
        n = m.end() - m.start()
        if n == 2:
            out.append((m.start(), m.end(), "marker"))
        elif n == 4:
            before = line[m.start() - 1] if m.start() > 0 else " "
            after = line[m.end()] if m.end() < len(line) else " "
            if before.strip() and after.strip():
                out.append((m.start(), m.end(), "marker2"))
            else:
                out.append((m.start(), m.end(), "literal"))
        else:
            out.append((m.start(), m.end(), "literal"))
    return out


def strip_line(line: str) -> LineResult:
    runs = _classify(line)
    # expandir a lista de marcadores individuales con su posición
    markers: list[tuple[int, int]] = []  # (start, end) de cada marcador ~~
    literals = sum(1 for _, _, k in runs if k == "literal")
    run4_lit = sum(1 for s, e, k in runs if k == "literal" and e - s == 4)
    for s, e, k in runs:
        if k == "marker":
            markers.append((s, e))
        elif k == "marker2":
            markers.append((s, s + 2))
            markers.append((s + 2, e))

    pairs: list[tuple[int, int, int, int]] = []  # (open_s, open_e, close_s, close_e)
    stack: list[tuple[int, int]] = []
    for s, e in markers:
        if stack:
            os_, oe_ = stack.pop()
            pairs.append((os_, oe_, s, e))
        else:
            stack.append((s, e))
    orphans = len(stack)

    if not pairs:
        return LineResult(text=line, orphans=orphans, literals=literals,
                          run4_literal=run4_lit)

    drop: set[int] = set()
    spans: list[str] = []
    for os_, oe_, cs_, ce_ in pairs:
        drop.update(range(os_, oe_))
        drop.update(range(cs_, ce_))
        spans.append(line[oe_:cs_])
    text = "".join(ch for i, ch in enumerate(line) if i not in drop)
    return LineResult(text=text, pairs=spans, orphans=orphans, literals=literals,
                      run4_literal=run4_lit)


@dataclass
class StripResult:
    text: str
    pairs: list[str]
    orphans: int
    literals: int
    run4_literal: int
    changed: bool

    @property
    def eyeball_flags(self) -> list[str]:
        return [s for s in self.pairs
                if len(s) > SPAN_EYEBALL_LEN or _SENTENCE_PUNCT.search(s)]


def strip_content(content: str) -> StripResult:
    lines = content.split("\n")
    out_lines: list[str] = []
    pairs: list[str] = []
    orphans = literals = run4 = 0
    for ln in lines:
        r = strip_line(ln)
        out_lines.append(r.text)
        pairs.extend(r.pairs)
        orphans += r.orphans
        literals += r.literals
        run4 += r.run4_literal
    text = "\n".join(out_lines)
    return StripResult(text=text, pairs=pairs, orphans=orphans, literals=literals,
                       run4_literal=run4, changed=(text != content))
