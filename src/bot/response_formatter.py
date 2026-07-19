"""Safe, deterministic presentation of generated answers in Telegram.

The RAG generator deliberately produces a small Markdown subset because it is
readable in logs and evaluation artefacts.  Telegram's legacy ``Markdown``
parser accepts a different, brittle subset: model names, evidence locators and
electrical notation can accidentally become markup and make the whole message
fail to send.  This module is the presentation boundary between those two
formats.

Only presentation is changed here.  No technical statement, evidence locator
or source citation is created or removed.
"""

from __future__ import annotations

import html
import re


TELEGRAM_TEXT_LIMIT = 4096
# Leave room for any transport-side accounting differences while remaining
# comfortably below Telegram's documented text limit.
DEFAULT_MESSAGE_LIMIT = 4000
_SEPARATOR = "─" * 20

_TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
_HORIZONTAL_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
# s272 (feedback vivo ASD535): el generador emite ``**Fuente:** X`` — el ``**`` de
# cierre quedaba DESPUÉS de los dos puntos y el patrón viejo lo dejaba como ``**``
# literal en Telegram. Se aceptan las tres colocaciones del énfasis.
_SOURCE_RE = re.compile(
    r"^\s*(?:\*\*)?(Fuentes?|Sources?)(?::\s*\*\*|\*\*\s*:|\s*:)\s*(.*)$",
    re.IGNORECASE,
)
_INLINE_RE = re.compile(
    r"`([^`\n]+)`|\*\*(.+?)\*\*",
    re.DOTALL,
)
# Emojis ESTRUCTURALES, sobrios (s272): ⚠️ avisos, 🔧 pasos de procedimiento,
# 📄 fuentes, ℹ️ notas — nada decorativo por frase.
_SOURCE_EMOJI = "📄"
_STEP_EMOJI = "🔧"
_WARNING_WORD_RE = re.compile(
    r"\b(?:advertencia|atenci[oó]n|peligro|precauci[oó]n|importante|aviso|"
    r"warning|caution|danger|important)\b",
    re.IGNORECASE,
)
# Cabecera de sección en MAYÚSCULAS con dos puntos finales ("CABLEADO:") — el
# generador la emite a veces en vez de ``##``; se renderiza en negrita con línea
# en blanco antes (mismo tratamiento que un heading).
_CAPS_SECTION_RE = re.compile(
    r"^\s*([A-ZÁÉÍÓÚÑÜ0-9][A-ZÁÉÍÓÚÑÜ0-9 /()\-.]{2,58}):\s*$"
)
_UPPER_LETTER_RE = re.compile(r"[A-ZÁÉÍÓÚÑÜ]")
# Cabecera de paso: línea COMPLETA en negrita que empieza por número ("**1. Leer
# el valor de flujo actual**") — señal estructural de procedimiento.
_STEP_BOLD_RE = re.compile(r"^\s*\*\*\s*(\d{1,2}[.)]\s+[^*\n]+?)\s*\*\*\s*$")
_STEP_NUMBER_RE = re.compile(r"^\d{1,2}[.)]\s")
# Span citado del anexo must-preserve que arrastra el marcador blockquote de la
# fuente (respuestas históricas ya almacenadas): `"> Para evitar..."` → `"Para...`.
# Mismo guard conservador que en el render: nunca ante dígito/operador.
_QUOTED_BLOCKQUOTE_RE = re.compile(r"^(\"?)(?:>\s*)+(?=[^\W\d_]|[\"'*¡¿(])")


def _split_markdown_row(row: str) -> list[str]:
    """Split a pipe table row without losing escaped pipes or inline code."""
    body = row.strip()[1:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False

    for character in body:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "`":
            in_code = not in_code
            current.append(character)
        elif character == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)

    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        not cell or _TABLE_SEPARATOR_CELL_RE.fullmatch(cell.strip())
        for cell in cells
    )


def convert_tables(text: str) -> str:
    """Convert Markdown tables to lossless field lists for a narrow screen.

    Every non-empty data cell is retained.  A malformed row with more cells
    than headers is rendered without inventing a label instead of silently
    dropping the extra value.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    result: list[str] = []
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            result.append(lines[index])
            index += 1
            continue

        raw_rows: list[list[str]] = []
        while index < len(lines):
            candidate = lines[index].strip()
            if not (candidate.startswith("|") and candidate.endswith("|")):
                break
            cells = _split_markdown_row(candidate)
            if not _is_table_separator(cells):
                raw_rows.append(cells)
            index += 1

        if not raw_rows:
            continue
        if len(raw_rows) == 1:
            values = [value for value in raw_rows[0] if value]
            if values:
                result.append("• " + " · ".join(values))
            continue

        headers, data_rows = raw_rows[0], raw_rows[1:]
        for row in data_rows:
            fields: list[str] = []
            for cell_index, value in enumerate(row):
                if not value:
                    continue
                header = headers[cell_index] if cell_index < len(headers) else ""
                fields.append(f"{header}: {value}" if header else value)
            if fields:
                result.append("• " + " · ".join(fields))

    return "\n".join(result)


def _render_inline(text: str) -> str:
    """Render the supported inline subset while escaping all raw HTML."""
    rendered: list[str] = []
    cursor = 0
    for match in _INLINE_RE.finditer(text):
        rendered.append(html.escape(text[cursor : match.start()], quote=False))
        if match.group(1) is not None:
            rendered.append(f"<code>{html.escape(match.group(1), quote=False)}</code>")
        else:
            rendered.append(f"<b>{html.escape(match.group(2), quote=False)}</b>")
        cursor = match.end()
    rendered.append(html.escape(text[cursor:], quote=False))
    return "".join(rendered)


def format_for_telegram(text: str) -> str:
    """Render generator Markdown as Telegram-safe HTML.

    The output contains only tags supported by Telegram and all model/manual
    text is escaped.  Evidence locators such as ``[F3]`` remain plain text.
    """
    normalized = convert_tables(text)
    output: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def append_section(rendered_line: str) -> None:
        """Section boundaries always get a preceding blank line (s272: los saltos
        de sección deben sobrevivir al render, feedback vivo ASD535)."""
        if output and output[-1].strip():
            output.append("")
        output.append(rendered_line)

    for line in normalized.split("\n"):
        if line.strip().startswith("```"):
            if in_code:
                output.append(
                    "<pre>" + html.escape("\n".join(code_lines), quote=False) + "</pre>"
                )
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            title = heading.group(1)
            step = _STEP_EMOJI + " " if _STEP_NUMBER_RE.match(title) else ""
            append_section(f"{step}<b>{html.escape(title, quote=False)}</b>")
            continue
        if _HORIZONTAL_RULE_RE.match(line):
            append_section(_SEPARATOR)
            continue
        if line.lstrip().startswith(">"):
            note = re.sub(r"^(?:>\s*)+", "", line.lstrip())
            if note.startswith(("⚠️", "ℹ️", "⚠", "🔧", "📄")):
                # La nota ya trae su propio emoji estructural — no duplicar.
                output.append(_render_inline(note))
                continue
            prefix = "⚠️" if _WARNING_WORD_RE.search(note) else "ℹ️"
            output.append(f"{prefix} {_render_inline(note)}")
            continue
        source = _SOURCE_RE.match(line)
        if source:
            output.append(
                f"{_SOURCE_EMOJI} <b>{html.escape(source.group(1), quote=False)}:</b> "
                f"{_render_inline(source.group(2))}"
            )
            continue
        step_bold = _STEP_BOLD_RE.match(line)
        if step_bold:
            append_section(
                f"{_STEP_EMOJI} <b>{html.escape(step_bold.group(1), quote=False)}</b>"
            )
            continue
        caps = _CAPS_SECTION_RE.match(line)
        if caps and len(_UPPER_LETTER_RE.findall(caps.group(1))) >= 3:
            append_section(f"<b>{html.escape(caps.group(1), quote=False)}:</b>")
            continue

        # Markdown list markers are presentation syntax, so replace them with
        # a narrow-screen bullet while keeping the complete item text.
        bullet = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        if bullet:
            item = _QUOTED_BLOCKQUOTE_RE.sub(r"\1", bullet.group(2))
            output.append(f"{bullet.group(1)}• {_render_inline(item)}")
        else:
            output.append(_render_inline(line))

    # A malformed/unclosed fence must not discard the remainder of an answer.
    if in_code:
        output.append("<pre>" + html.escape("\n".join(code_lines), quote=False) + "</pre>")

    return "\n".join(output).strip()


def _markdown_blocks(text: str) -> list[str]:
    """Split on blank lines, but never inside a fenced code block."""
    blocks: list[str] = []
    current: list[str] = []
    in_code = False

    for line in convert_tables(text).split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
        if not line.strip() and not in_code:
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _split_source_line(line: str, source_limit: int) -> list[str]:
    """Split an exceptional oversized line without changing its characters."""
    pieces: list[str] = []
    remainder = line
    while len(remainder) > source_limit:
        boundary = remainder.rfind(" ", 0, source_limit + 1)
        if boundary <= 0:
            boundary = source_limit
        pieces.append(remainder[:boundary])
        remainder = remainder[boundary:]
        if remainder.startswith(" "):
            remainder = remainder[1:]
    if remainder:
        pieces.append(remainder)
    return pieces


def _render_block_parts(block: str, max_length: int) -> list[str]:
    rendered = format_for_telegram(block)
    if len(rendered) <= max_length:
        return [rendered]

    # Escaping can expand one source character to five HTML characters.  This
    # conservative bound guarantees independently rendered lines fit.  This is
    # only exercised for unusually large paragraphs or diagrams.
    source_limit = max(1, max_length // 6)
    source_lines = block.split("\n")
    pieces: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_code() -> None:
        nonlocal code_lines
        if not code_lines:
            return
        code_text = "\n".join(code_lines)
        for code_piece in _split_source_line(code_text, source_limit):
            pieces.append(
                "<pre>" + html.escape(code_piece, quote=False) + "</pre>"
            )
        code_lines = []

    for source_line in source_lines:
        if source_line.strip().startswith("```"):
            if in_code:
                flush_code()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(source_line)
            continue
        for source_piece in _split_source_line(source_line, source_limit):
            piece = format_for_telegram(source_piece)
            if piece:
                pieces.append(piece)
    flush_code()
    return pieces


def format_telegram_messages(
    text: str, max_length: int = DEFAULT_MESSAGE_LIMIT
) -> list[str]:
    """Return complete, independently valid Telegram HTML messages."""
    if max_length <= 0 or max_length > TELEGRAM_TEXT_LIMIT:
        raise ValueError(
            f"max_length must be between 1 and {TELEGRAM_TEXT_LIMIT}, got {max_length}"
        )

    rendered_blocks: list[str] = []
    for block in _markdown_blocks(text):
        rendered_blocks.extend(_render_block_parts(block, max_length))

    messages: list[str] = []
    current = ""
    for block in rendered_blocks:
        if not block:
            continue
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= max_length:
            current = candidate
            continue
        if current:
            messages.append(current)
        current = block
    if current:
        messages.append(current)
    return messages


def telegram_html_to_plain(text: str) -> str:
    """Lossless plain-text fallback for HTML rejected by the transport."""
    without_tags = re.sub(r"</?(?:b|i|code|pre)>", "", text)
    return html.unescape(without_tags)
