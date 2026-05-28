"""Etapa B3/B4 del pipeline de re-ingesta — chunking estructural + diagramas.

B3 — chunking guiado por la estructura markdown que produce LlamaParse:
  - Los headers markdown (#, ##, ###...) son cortes BLANDOS: marcan el límite
    preferente, pero una sección minúscula se acumula con la siguiente hasta
    alcanzar el tamaño objetivo. Un corte duro por header daría decenas de
    chunks inservibles en spec-sheets y catálogos densos en cabeceras.
  - Un header de nivel igual o superior al de la sección en curso SÍ fuerza el
    corte cuando el chunk ya tiene cuerpo suficiente — no se mezclan dos
    secciones de primer nivel.
  - Tablas y bloques de código NUNCA se parten — son unidades atómicas (el PoC
    demostró que partir una tabla la vuelve inservible).
  - `section_path` reconstruye la jerarquía parent-child ('H1 > H2 > H3') como
    el ancestro común de las secciones que cubre el chunk.
  - `page_number` viene del JSON de extracción (fiable) — habilita el deep-link.

B4 — detección de diagramas de flujo (tarea #12, doble vía): LlamaParse en modo
agéntico renderiza los flowcharts como fences ```mermaid. Un chunk que contiene
un fence mermaid se marca `is_flow_diagram=True` — el VLM alucina en esos
diagramas, así que el texto es orientativo y la imagen de la página se adjunta
a la respuesta del técnico.

Uso:
    from src.reingest.chunk import chunk_document
    chunks = chunk_document(extraction_record)   # list[Chunk]
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import uuid4

# --- Parámetros de tamaño ----------------------------------------------------
# Objetivo de chunk ~3000 chars (~750 tokens) — granularidad fina para precisión
# de retrieval. Techo duro 7000: deja margen bajo el límite de 8000 del embedder
# una vez añadido el blurb de contexto (B7, ~300-600 chars).
TARGET_CHARS = 3000
MAX_CHARS = 7000
# Por debajo de MIN un chunk aporta poco contexto: ni fuerza corte ni sobrevive
# suelto (se fusiona con el vecino). Por debajo de NOISE es ruido (bordes de
# tabla sueltos, números de página) y se descarta.
MIN_CHARS = 450
NOISE_CHARS = 15

_HEADING = re.compile(r"(#{1,6})\s+(.*)")
_LIST_ITEM = re.compile(r"(\d+[.)]|[-*+])\s")
# Fila separadora de tabla markdown: | --- | :--: | ...
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|[\s:|-]*$")
_SENTENCE_END = re.compile(r"(?<=[.;:])\s+")
_NON_MEANINGFUL = re.compile(r"[\s#|>*_`\-]+")


@dataclass
class Chunk:
    """Un chunk de la Etapa B. B3/B4 rellenan estructura; B5/B7/B8 el resto.

    El `id` se genera cliente-side (no en la DB) para que B6 (dedup) pueda
    fijar `duplicate_of` con un id conocido antes del INSERT — un único INSERT,
    sin segunda pasada de UPDATE.
    """
    content: str
    section_title: str | None
    section_path: str | None
    page_number: int | None
    chunk_index: int
    id: str = field(default_factory=lambda: str(uuid4()))
    is_flow_diagram: bool = False
    confidence: float | None = None
    has_diagram: bool = False
    # Rellenado por etapas posteriores del pipeline:
    language: str | None = None          # B1
    source_file: str | None = None       # B5
    product_model: str | None = None     # B5
    manufacturer: str | None = None      # B5 — marca real (datasheet)
    distributor: str | None = None       # B5 — canal de distribución (si difiere)
    protocol: str | None = None          # B5
    doc_type: str | None = None          # B5
    category: str | None = None          # B5
    content_type: str | None = None      # B5
    context: str | None = None           # B7
    embedding: list[float] | None = None # B8
    duplicate_of: str | None = None      # B6


@dataclass
class _Block:
    """Unidad sintáctica del markdown. `atomic` = no se puede partir."""
    kind: str               # heading | paragraph | list | table | code | mermaid
    text: str
    page: int | None
    level: int = 0          # solo headings
    title: str = ""         # solo headings
    path: tuple = ()        # pila de headers (nivel, título) vigente

    @property
    def atomic(self) -> bool:
        return self.kind in ("table", "code", "mermaid")


def _starts_block(line: str) -> bool:
    """¿Esta línea inicia un bloque que no sea párrafo?"""
    s = line.strip()
    return bool(
        _HEADING.match(s)
        or s.startswith("```")
        or "|" in line
        or _LIST_ITEM.match(s)
    )


def parse_blocks(md: str, page: int | None) -> list[_Block]:
    """Parsea el markdown de una página en bloques sintácticos."""
    lines = md.split("\n")
    blocks: list[_Block] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # --- Heading ---
        m = _HEADING.match(stripped)
        if m:
            blocks.append(_Block("heading", stripped, page,
                                 level=len(m.group(1)), title=m.group(2).strip()))
            i += 1
            continue

        # --- Code / mermaid fence ---
        if stripped.startswith("```"):
            fence_lang = stripped[3:].strip().lower()
            buf = [line]
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            if i < n:
                buf.append(lines[i])
                i += 1
            kind = "mermaid" if fence_lang.startswith("mermaid") else "code"
            blocks.append(_Block(kind, "\n".join(buf), page))
            continue

        # --- Table: run de líneas con '|' que contenga una fila separadora ---
        if "|" in line:
            buf = []
            j = i
            while j < n and "|" in lines[j] and lines[j].strip():
                buf.append(lines[j])
                j += 1
            if any(_TABLE_SEP.match(b) for b in buf):
                blocks.append(_Block("table", "\n".join(buf), page))
                i = j
                continue
            # Sin fila separadora: no es una tabla, cae a párrafo abajo.

        # --- List ---
        if _LIST_ITEM.match(stripped):
            buf = []
            while i < n:
                cur = lines[i]
                if not cur.strip():
                    break
                if _LIST_ITEM.match(cur.strip()) or cur.startswith((" ", "\t")):
                    buf.append(cur)
                    i += 1
                else:
                    break
            blocks.append(_Block("list", "\n".join(buf), page))
            continue

        # --- Paragraph ---
        buf = []
        while i < n and lines[i].strip() and not _starts_block(lines[i]):
            buf.append(lines[i])
            i += 1
        if buf:
            blocks.append(_Block("paragraph", "\n".join(buf), page))
        else:
            # Línea que disparó _starts_block pero no encajó (p.ej. '|' suelto):
            # absorberla como párrafo de una línea para no entrar en bucle.
            blocks.append(_Block("paragraph", line, page))
            i += 1

    return blocks


def _flatten(pages: list[dict]) -> list[_Block]:
    """Pasa 1 — aplana todas las páginas en bloques, cada uno con su `path`.

    La pila de headers persiste entre páginas: una sección que cruza un salto
    de página conserva su `section_path`.
    """
    stack: list[tuple[int, str]] = []
    out: list[_Block] = []
    for p in pages:
        md = p.get("md") or p.get("text") or ""
        if not md.strip():
            continue
        page = p.get("page")
        for b in parse_blocks(md, page):
            if b.kind == "heading":
                while stack and stack[-1][0] >= b.level:
                    stack.pop()
                # Evita re-apilar un running-header repetido idéntico.
                if not (stack and stack[-1][1] == b.title):
                    stack.append((b.level, b.title))
            b.path = tuple(stack)
            out.append(b)
    return out


def _split_oversized(block: _Block, ceiling: int) -> list[str]:
    """Parte un bloque partible (párrafo/lista) que excede el techo.

    Párrafos por frase; listas por ítem. Los bloques atómicos no llegan aquí.
    """
    units = block.text.split("\n") if block.kind == "list" \
        else _SENTENCE_END.split(block.text)
    pieces: list[str] = []
    cur = ""
    for u in units:
        if cur and len(cur) + len(u) + 1 > ceiling:
            pieces.append(cur.strip())
            cur = u
        elif cur:
            cur = f"{cur}\n{u}" if block.kind == "list" else f"{cur} {u}"
        else:
            cur = u
    if cur.strip():
        pieces.append(cur.strip())
    return pieces


def _common_path(blocks: list[_Block]) -> tuple:
    """Ancestro común de los `path` de los bloques — el section_path del chunk."""
    paths = [b.path for b in blocks if b.path]
    if not paths:
        return ()
    common: list[tuple[int, str]] = []
    for tier in zip(*paths):
        if len(set(tier)) == 1:
            common.append(tier[0])
        else:
            break
    return tuple(common)


def _make_chunk(buf: list[_Block], index: int) -> Chunk | None:
    """Convierte un buffer de bloques en un Chunk."""
    text = "\n\n".join(b.text for b in buf).strip()
    if not text:
        return None
    path = _common_path(buf)
    first_page = next((b.page for b in buf if b.page is not None), None)
    return Chunk(
        content=text,
        section_title=path[-1][1] if path else None,
        section_path=" > ".join(t for _, t in path) if path else None,
        page_number=first_page,
        chunk_index=index,
        is_flow_diagram=any(b.kind == "mermaid" for b in buf),
    )


def chunk_document(extraction_record: dict) -> list[Chunk]:
    """Trocea un documento extraído en chunks (B3) y marca los flowcharts (B4)."""
    pages = extraction_record.get("result", {}).get("pages", [])

    has_image_pages: set[int] = set()
    page_confidence: dict[int, float] = {}
    for p in pages:
        pn = p.get("page")
        if pn is None:
            continue
        if p.get("images"):
            has_image_pages.add(pn)
        if p.get("confidence") is not None:
            page_confidence[pn] = p["confidence"]

    blocks = _flatten(pages)

    chunks: list[Chunk] = []
    buf: list[_Block] = []
    buf_anchor = 99  # nivel de header más somero presente en el buffer

    def cur_size() -> int:
        return sum(len(b.text) for b in buf)

    def flush():
        nonlocal buf, buf_anchor
        if buf:
            ch = _make_chunk(buf, len(chunks))
            if ch is not None:
                chunks.append(ch)
        buf = []
        buf_anchor = 99

    for b in blocks:
        if b.kind == "heading":
            if buf and b.level <= buf_anchor:
                # Header más somero = se sube en la jerarquía = límite real
                # (cambio de sección de primer nivel): corta SIEMPRE, aunque el
                # chunk sea diminuto — si no, se fusionarían dos ramas distintas
                # y el chunk perdería su ancestro común (section_path nulo).
                # Header del mismo nivel (hermano): corta solo si ya hay cuerpo,
                # para que las secciones minúsculas se acumulen.
                if b.level < buf_anchor or cur_size() >= MIN_CHARS:
                    flush()
            if not buf:
                buf_anchor = b.level
            else:
                buf_anchor = min(buf_anchor, b.level)
            buf.append(b)
            continue

        # --- Bloque de contenido ---
        if not buf:
            buf_anchor = len(b.path) or 1

        # Bloque partible que por sí solo supera el techo → trocearlo.
        if not b.atomic and len(b.text) > MAX_CHARS:
            flush()
            for piece in _split_oversized(b, MAX_CHARS):
                buf = [_Block(b.kind, piece, b.page, path=b.path)]
                flush()
            continue

        # Añadirlo excedería el objetivo y el chunk ya tiene cuerpo → cortar.
        if buf and cur_size() + len(b.text) > TARGET_CHARS and cur_size() >= MIN_CHARS:
            flush()
            buf_anchor = len(b.path) or 1

        buf.append(b)

        if cur_size() >= TARGET_CHARS:
            flush()

    flush()

    chunks = _cleanup(chunks)

    # Confianza por chunk + has_diagram + re-numerar chunk_index tras la limpieza.
    for idx, ch in enumerate(chunks):
        ch.chunk_index = idx
        if ch.page_number is not None:
            ch.confidence = page_confidence.get(ch.page_number)
            ch.has_diagram = ch.page_number in has_image_pages
    return chunks


def _meaningful_len(content: str) -> int:
    """Longitud del contenido descontando whitespace y sintaxis markdown."""
    return len(_NON_MEANINGFUL.sub("", content))


def _cleanup(chunks: list[Chunk]) -> list[Chunk]:
    """Descarta chunks-ruido y fusiona los sub-MIN sobrantes con el vecino previo.

    Tras el packing acumulativo apenas quedan chunks pequeños, pero un tramo
    final corto o el resto de un bloque atómico grande pueden dejar alguno. Un
    chunk de diagrama de flujo nunca se fusiona — debe quedar aislado (doble vía).
    """
    out: list[Chunk] = []
    for ch in chunks:
        if _meaningful_len(ch.content) < NOISE_CHARS:
            continue
        if (out and len(ch.content) < MIN_CHARS
                and not ch.is_flow_diagram and not out[-1].is_flow_diagram
                and len(out[-1].content) + len(ch.content) <= MAX_CHARS):
            prev = out[-1]
            prev.content = f"{prev.content}\n\n{ch.content}"
            prev.has_diagram = prev.has_diagram or ch.has_diagram
        else:
            out.append(ch)
    return out
