"""Deterministic, source-bound highlights for relation-complete source spans.

S245 is an ephemeral pre-answer representation.  It does not select documents,
write claims, persist a relation store, or mutate a completed answer.  Every
highlight is reconstructable from Python ``str`` code-point offsets into the
exact fragment that the writer already receives.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


RELATION_COMPLETE_HIGHLIGHT_CONTRACT = "s245_relation_complete_highlight_v1"
JOINER = "\n\n"
MAX_ATOM_CHARS = 900
MAX_ATOMS_PER_FRAGMENT = 48
MAX_ATOMS_PER_REQUEST = 96


class HighlightLimitError(ValueError):
    """The input cannot be highlighted without violating the frozen limits."""


@dataclass(frozen=True)
class RelationCompleteHighlight:
    atom_id: str
    fragment_number: int
    candidate_id: str
    reason_labels: tuple[str, ...]
    source_spans: tuple[tuple[int, int], ...]
    content: str
    content_sha256: str


_CONDITION = re.compile(
    r"\b(?:if|when|whenever|until|unless|before|after|once|only\s+(?:if|when|after)|"
    r"si|cuando|hasta\s+que|a\s+menos\s+que|antes\s+de|despu[eé]s\s+de|"
    r"una\s+vez|solo\s+(?:si|cuando|despu[eé]s))\b",
    re.IGNORECASE,
)
_MANDATORY = re.compile(
    r"\b(?:must|shall|required|requirement|do\s+not|never|warning|caution|danger|"
    r"verify|check|test(?:ing|ed)?|commission(?:ing|ed)?|prerequisite|isolate|"
    r"debe(?:r[aá])?|obligatori[oa]s?|requerid[oa]s?|requisito|no\s+debe|nunca|"
    r"advertencia|precauci[oó]n|peligro|verificar|comprobar|prueba|probar|ensay|"
    r"puesta\s+en\s+marcha|aislar|a[ií]sle)\b",
    re.IGNORECASE,
)
_UNIT = re.compile(
    r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:%|±\s*\d+(?:[.,]\d+)?\s*%|"
    r"ms|s|sec(?:ond)?s?|seg(?:undo)?s?|min(?:ute)?s?|h(?:ours?|oras?)?|"
    r"mA|A|V(?:ac|dc|ca|cc)?|kV|W|kW|Ω|ohm(?:s)?|kΩ|kohm(?:s)?|"
    r"Hz|kHz|dB|mm|cm|m|km|°C|ºC|Ah|kWh|bar|psi)\b",
    re.IGNORECASE,
)
_RANGE_OR_TOLERANCE = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s*(?:-|–|—|to|a|hasta)\s*\d+(?:[.,]\d+)?\b|"
    r"[<>]=?\s*\d|\b(?:minimum|maximum|minimo|mínimo|maximo|máximo|"
    r"at\s+least|at\s+most|al\s+menos|como\s+m[aá]ximo|up\s+to|hasta)\b|±)",
    re.IGNORECASE,
)
_COUNT = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"un[ao]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b",
    re.IGNORECASE,
)
_DEFINITION = re.compile(r"^\s*(?:[*+-]\s*)?(?:\*\*)?[^:\n]{1,80}:(?:\*\*)?\s+\S")
_BULLET = re.compile(r"^\s*(?:[*+-]|\d+[.)]|[a-zA-Z][.)])\s+\S")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_TABLE_DIVIDER = re.compile(
    r"^\s*\|?(?:\s*:?-{3,}:?\s*\|){1,}\s*:?-{3,}:?\s*\|?\s*$"
)


def _nonblank_spans(content: str) -> list[tuple[int, int]]:
    return [
        match.span(1)
        for match in re.finditer(
            r"(?s)(?:^|\n\s*\n)(\s*\S.*?)(?=\n\s*\n|$)", content
        )
        if match.group(1).strip()
    ]


def _line_spans(content: str) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for match in re.finditer(r"(?m)^.*(?:\n|$)", content):
        start, end = match.span()
        while end > start and content[end - 1] in "\r\n":
            end -= 1
        if content[start:end].strip():
            output.append((start, end))
    return output


def _sentence_spans(content: str, start: int, end: int) -> list[tuple[int, int]]:
    """Conservative sentence spans that retain punctuation and source offsets."""
    raw = content[start:end]
    boundaries = [0]
    for match in re.finditer(r"(?:[.!?](?:[\"')\]]*)\s+|\n+)", raw):
        boundaries.append(match.end())
    boundaries.append(len(raw))
    spans: list[tuple[int, int]] = []
    for left, right in zip(boundaries, boundaries[1:]):
        absolute_start, absolute_end = start + left, start + right
        while absolute_start < absolute_end and content[absolute_start].isspace():
            absolute_start += 1
        while absolute_end > absolute_start and content[absolute_end - 1].isspace():
            absolute_end -= 1
        if absolute_start < absolute_end:
            spans.append((absolute_start, absolute_end))
    return spans


def _markdown_table_pairs(
    content: str,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    lines = _line_spans(content)
    output: list[tuple[tuple[int, int], tuple[int, int]]] = []
    index = 0
    while index < len(lines) - 2:
        header_span, divider_span = lines[index], lines[index + 1]
        header = content[slice(*header_span)]
        divider = content[slice(*divider_span)]
        if header.count("|") < 2 or not _TABLE_DIVIDER.match(divider):
            index += 1
            continue
        cursor = index + 2
        while cursor < len(lines):
            row_span = lines[cursor]
            if content[slice(*row_span)].count("|") < 2:
                break
            output.append((header_span, row_span))
            cursor += 1
        index = max(cursor, index + 1)
    return output


def _signal_labels(text: str, *, structured: bool = False) -> set[str]:
    labels: set[str] = set()
    if _UNIT.search(text) or _RANGE_OR_TOLERANCE.search(text):
        labels.add("numeric_bundle")
    if _CONDITION.search(text):
        labels.add("condition_dependency")
    if _MANDATORY.search(text):
        labels.add("mandatory_safety_verification")
    if _COUNT.search(text):
        labels.add("enumeration_cardinality")
    if structured or _DEFINITION.search(text):
        labels.add("structured_member")
    return labels


def _content_for_spans(content: str, spans: tuple[tuple[int, int], ...]) -> str:
    return JOINER.join(content[slice(*span)] for span in spans)


def _make_highlight(
    content: str,
    *,
    fragment_number: int,
    candidate_id: str,
    source_spans: tuple[tuple[int, int], ...],
    reason_labels: set[str],
) -> RelationCompleteHighlight:
    rendered = _content_for_spans(content, source_spans)
    if len(rendered) > MAX_ATOM_CHARS:
        raise HighlightLimitError("relation-complete atom exceeds character limit")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    identity_material = ":".join(
        [
            RELATION_COMPLETE_HIGHLIGHT_CONTRACT,
            str(fragment_number),
            candidate_id,
            ";".join(f"{start}-{end}" for start, end in source_spans),
            digest,
        ]
    )
    identity = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()[:12]
    return RelationCompleteHighlight(
        atom_id=f"A_{identity}",
        fragment_number=fragment_number,
        candidate_id=candidate_id,
        reason_labels=tuple(sorted(reason_labels)),
        source_spans=source_spans,
        content=rendered,
        content_sha256=digest,
    )


def _bounded_sentence_windows(
    content: str, span: tuple[int, int]
) -> list[tuple[tuple[int, int], set[str]]]:
    sentences = _sentence_spans(content, *span)
    output: list[tuple[tuple[int, int], set[str]]] = []
    for index, sentence in enumerate(sentences):
        labels = _signal_labels(content[slice(*sentence)])
        if not labels:
            continue
        best = sentence
        # Preserve adjacent qualifier clauses when the complete window remains
        # bounded.  This is source-form driven, not question- or gold-driven.
        for right in range(index + 1, min(len(sentences), index + 3)):
            candidate = (sentence[0], sentences[right][1])
            if candidate[1] - candidate[0] > MAX_ATOM_CHARS:
                break
            candidate_labels = _signal_labels(content[slice(*candidate)])
            if candidate_labels.intersection(
                {"condition_dependency", "mandatory_safety_verification"}
            ):
                best = candidate
                labels.update(candidate_labels)
        output.append((best, labels))
    return output


def build_relation_complete_highlights(
    content: str,
    *,
    fragment_number: int,
    candidate_id: str,
) -> list[RelationCompleteHighlight]:
    """Extract bounded, exact relation spans from one already-served fragment."""
    if fragment_number < 1 or not candidate_id:
        raise ValueError("fragment_number and candidate_id are required")

    specs: list[tuple[tuple[tuple[int, int], ...], set[str]]] = []
    table_spans: set[tuple[int, int]] = set()
    for header_span, row_span in _markdown_table_pairs(content):
        spans = (header_span, row_span)
        rendered = _content_for_spans(content, spans)
        labels = _signal_labels(rendered, structured=True)
        if len(rendered) <= MAX_ATOM_CHARS:
            specs.append((spans, labels))
            table_spans.update(spans)

    paragraphs = _nonblank_spans(content)
    for index, paragraph_span in enumerate(paragraphs):
        paragraph = content[slice(*paragraph_span)]
        if paragraph_span in table_spans or _TABLE_DIVIDER.match(paragraph):
            continue
        lines = paragraph.splitlines()
        is_list = sum(bool(_BULLET.match(line)) for line in lines) >= 1
        is_heading = bool(_HEADING.match(paragraph))
        labels = _signal_labels(paragraph, structured=is_list)

        if is_heading:
            continue
        if labels and len(paragraph) <= MAX_ATOM_CHARS:
            spans: tuple[tuple[int, int], ...] = (paragraph_span,)
            # Bind a short source heading to its structured child without
            # copying or normalizing either span.
            if is_list and index > 0:
                parent_span = paragraphs[index - 1]
                parent = content[slice(*parent_span)]
                if _HEADING.match(parent) and len(parent) + len(paragraph) + len(JOINER) <= MAX_ATOM_CHARS:
                    spans = (parent_span, paragraph_span)
            specs.append((spans, labels))
            continue
        if labels:
            for sentence_span, sentence_labels in _bounded_sentence_windows(
                content, paragraph_span
            ):
                specs.append(((sentence_span,), sentence_labels))

    # Merge duplicate span identities while retaining all source-form reasons.
    merged: dict[tuple[tuple[int, int], ...], set[str]] = {}
    for spans, labels in specs:
        if not labels:
            continue
        merged.setdefault(spans, set()).update(labels)
    ordered = sorted(merged.items(), key=lambda row: (row[0][0], row[0]))
    if len(ordered) > MAX_ATOMS_PER_FRAGMENT:
        raise HighlightLimitError("fragment exceeds highlight cardinality limit")
    return [
        _make_highlight(
            content,
            fragment_number=fragment_number,
            candidate_id=candidate_id,
            source_spans=spans,
            reason_labels=labels,
        )
        for spans, labels in ordered
    ]


def reconstruct_highlight_content(
    source: str, highlight: RelationCompleteHighlight
) -> str:
    return _content_for_spans(source, highlight.source_spans)


def validate_request_highlight_count(
    highlights_by_fragment: list[list[RelationCompleteHighlight]],
) -> None:
    if sum(map(len, highlights_by_fragment)) > MAX_ATOMS_PER_REQUEST:
        raise HighlightLimitError("request exceeds highlight cardinality limit")


def render_inline_highlights(
    source: str, highlights: list[RelationCompleteHighlight]
) -> str:
    """Insert deterministic markers without changing any original source byte."""
    boundaries: dict[int, list[tuple[str, str]]] = {}
    for highlight in highlights:
        for part, (start, end) in enumerate(highlight.source_spans, 1):
            if not 0 <= start < end <= len(source):
                raise ValueError("highlight span is outside source")
            tag = f"{highlight.atom_id}:{part}/{len(highlight.source_spans)}"
            boundaries.setdefault(start, []).append(("start", tag))
            boundaries.setdefault(end, []).append(("end", tag))
    if not boundaries:
        return source

    output: list[str] = []
    active: set[str] = set()
    cursor = 0
    for boundary in sorted(boundaries):
        if boundary > cursor:
            raw = source[cursor:boundary]
            if active:
                ids = ",".join(sorted(active))
                output.append(f'<s245 ids="{ids}">{raw}</s245>')
            else:
                output.append(raw)
        events = boundaries[boundary]
        for kind, tag in sorted(events, key=lambda item: item[0] != "end"):
            if kind == "end":
                active.discard(tag)
        for kind, tag in sorted(events, key=lambda item: item[0] != "start"):
            if kind == "start":
                active.add(tag)
        cursor = boundary
    if cursor < len(source):
        raw = source[cursor:]
        if active:
            ids = ",".join(sorted(active))
            output.append(f'<s245 ids="{ids}">{raw}</s245>')
        else:
            output.append(raw)
    if active:
        raise ValueError("unclosed highlight span")
    return "".join(output)


def strip_inline_highlights(rendered: str) -> str:
    """Test/validation helper proving markers are the only rendered mutation."""
    return re.sub(r"</?s245(?:\s+ids=\"[A-Za-z0-9_:,./-]+\")?>", "", rendered)

