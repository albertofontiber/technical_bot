"""Header-aware, source-bound evidence units for bounded model selection.

The v1 contract exposed exact contiguous spans.  That is safe for prose, but a
single table row can be meaningless without its column headers.  V2 keeps the
same source-bound property while allowing a composite unit made only from
verified source spans: table header plus table row.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.rag.evidence_units import build_evidence_units


EVIDENCE_UNIT_CONTRACT_V2 = "evidence_units_s146_header_aware_v2"
_JOINER = "\n\n"


@dataclass(frozen=True)
class EvidenceUnitV2:
    unit_id: str
    fragment_number: int
    candidate_id: str
    unit_kind: str
    source_spans: tuple[tuple[int, int], ...]
    content: str
    content_sha256: str


def _paragraph_spans(content: str) -> list[tuple[int, int]]:
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


def _fixed_columns(line: str) -> tuple[int, ...]:
    """Return starts of fields separated by at least two literal spaces."""
    output: list[int] = []
    cursor = 0
    for part in re.split(r" {2,}", line.rstrip("\r\n")):
        if part:
            offset = line.find(part, cursor)
            if offset >= 0:
                output.append(offset)
                cursor = offset + len(part)
        cursor += 2
    return tuple(output) if len(output) >= 2 else ()


def _matches_columns(block: str, columns: tuple[int, ...]) -> bool:
    for line in block.splitlines():
        starts = _fixed_columns(line)
        aligned = sum(any(abs(start - column) <= 3 for column in columns) for start in starts)
        if aligned >= 2:
            return True
    return False


def _fixed_width_table_pairs(content: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    paragraphs = _paragraph_spans(content)
    output: list[tuple[tuple[int, int], tuple[int, int]]] = []
    index = 0
    while index < len(paragraphs) - 2:
        header_span = paragraphs[index]
        header = content[slice(*header_span)]
        columns = max(
            (_fixed_columns(line) for line in header.splitlines()),
            key=len,
            default=(),
        )
        if len(columns) < 3:
            index += 1
            continue
        rows: list[tuple[int, int]] = []
        cursor = index + 1
        while cursor < len(paragraphs) and len(rows) < 24:
            row_span = paragraphs[cursor]
            if not _matches_columns(content[slice(*row_span)], columns):
                break
            rows.append(row_span)
            cursor += 1
        if len(rows) >= 2:
            output.extend((header_span, row_span) for row_span in rows)
            index = cursor
        else:
            index += 1
    return output


def _markdown_table_pairs(content: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    lines = _line_spans(content)
    output: list[tuple[tuple[int, int], tuple[int, int]]] = []
    index = 0
    separator = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|){1,}\s*:?-{3,}:?\s*\|?\s*$")
    while index < len(lines) - 2:
        header_span, separator_span = lines[index], lines[index + 1]
        header = content[slice(*header_span)]
        divider = content[slice(*separator_span)]
        if header.count("|") < 2 or not separator.match(divider):
            index += 1
            continue
        cursor = index + 2
        rows: list[tuple[int, int]] = []
        while cursor < len(lines):
            row_span = lines[cursor]
            if content[slice(*row_span)].count("|") < 2:
                break
            rows.append(row_span)
            cursor += 1
        output.extend((header_span, row_span) for row_span in rows[:24])
        index = max(cursor, index + 1)
    return output


def _make_unit(
    content: str,
    *,
    fragment_number: int,
    candidate_id: str,
    unit_kind: str,
    source_spans: tuple[tuple[int, int], ...],
    ordinal: int,
) -> EvidenceUnitV2:
    rendered = _JOINER.join(content[slice(*span)] for span in source_spans)
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    identity_material = ":".join(
        [
            str(fragment_number),
            candidate_id,
            unit_kind,
            ";".join(f"{start}-{end}" for start, end in source_spans),
            digest,
        ]
    )
    identity = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()[:10]
    return EvidenceUnitV2(
        unit_id=f"E{ordinal:03d}_{identity}",
        fragment_number=fragment_number,
        candidate_id=candidate_id,
        unit_kind=unit_kind,
        source_spans=source_spans,
        content=rendered,
        content_sha256=digest,
    )


def build_header_aware_evidence_units(
    content: str,
    *,
    fragment_number: int,
    candidate_id: str,
    max_chars: int = 1200,
    overlap_chars: int = 300,
) -> list[EvidenceUnitV2]:
    """Build deterministic prose units plus source-bound header/row composites."""
    pairs = _markdown_table_pairs(content) + _fixed_width_table_pairs(content)
    pairs = sorted(set(pairs), key=lambda pair: (pair[1], pair[0]))
    contextual_row_spans = {row for _, row in pairs}

    specs: list[tuple[str, tuple[tuple[int, int], ...]]] = []
    for unit in build_evidence_units(
        content,
        fragment_number=fragment_number,
        candidate_id=candidate_id,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    ):
        span = (unit.source_start, unit.source_end)
        if span not in contextual_row_spans:
            specs.append(("contiguous", (span,)))
    specs.extend(("table_row_with_header", (header, row)) for header, row in pairs)

    unique: list[tuple[str, tuple[tuple[int, int], ...]]] = []
    seen: set[tuple[str, tuple[tuple[int, int], ...]]] = set()
    for spec in specs:
        if spec not in seen:
            seen.add(spec)
            unique.append(spec)
    return [
        _make_unit(
            content,
            fragment_number=fragment_number,
            candidate_id=candidate_id,
            unit_kind=kind,
            source_spans=spans,
            ordinal=index,
        )
        for index, (kind, spans) in enumerate(unique, 1)
    ]


def reconstruct_unit_content(source: str, unit: EvidenceUnitV2) -> str:
    """Reconstruct a unit only from its immutable source spans."""
    return _JOINER.join(source[slice(*span)] for span in unit.source_spans)
