"""Deterministic, immutable evidence units for model-assisted selection."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


EVIDENCE_UNIT_CONTRACT_V1 = "evidence_units_s144_v1"


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    fragment_number: int
    candidate_id: str
    source_start: int
    source_end: int
    content: str
    content_sha256: str


def _nonempty_paragraphs(content: str) -> list[tuple[int, int]]:
    return [
        match.span(1)
        for match in re.finditer(
            r"(?s)(?:^|\n\s*\n)(\s*\S.*?)(?=\n\s*\n|$)", content
        )
        if match.group(1).strip()
    ]


def _line_spans(content: str, start: int, end: int) -> list[tuple[int, int]]:
    output = []
    for match in re.finditer(r"(?m)^.*(?:\n|$)", content[start:end]):
        raw_start, raw_end = start + match.start(), start + match.end()
        if content[raw_start:raw_end].strip():
            output.append((raw_start, raw_end))
    return output


def _windows(content: str, *, max_chars: int, overlap_chars: int) -> list[tuple[int, int]]:
    if not content:
        return []
    output = []
    start = 0
    while start < len(content):
        tentative_end = min(len(content), start + max_chars)
        end = tentative_end
        if tentative_end < len(content):
            boundary = max(
                content.rfind("\n", start + max_chars // 2, tentative_end),
                content.rfind(". ", start + max_chars // 2, tentative_end),
            )
            if boundary > start:
                end = boundary + (1 if content[boundary] == "\n" else 2)
        if content[start:end].strip():
            output.append((start, end))
        if end >= len(content):
            break
        next_start = max(start + 1, end - overlap_chars)
        boundary = content.find("\n", next_start, min(len(content), next_start + 160))
        start = boundary + 1 if boundary >= 0 else next_start
    return output


def build_evidence_units(
    content: str,
    *,
    fragment_number: int,
    candidate_id: str,
    max_chars: int = 1200,
    overlap_chars: int = 300,
) -> list[EvidenceUnit]:
    """Return bounded exact spans; IDs commit to source identity and bytes."""
    if max_chars < 400 or not (0 <= overlap_chars < max_chars // 2):
        raise ValueError("invalid evidence-unit window contract")
    spans: set[tuple[int, int]] = set(_windows(
        content, max_chars=max_chars, overlap_chars=overlap_chars
    ))
    precise_chars = max_chars // 2
    for start, end in _nonempty_paragraphs(content):
        if end - start <= precise_chars:
            spans.add((start, end))
        elif end - start > max_chars:
            for line_start, line_end in _line_spans(content, start, end):
                if line_end - line_start <= precise_chars:
                    spans.add((line_start, line_end))
    output = []
    for index, (start, end) in enumerate(sorted(spans), 1):
        raw = content[start:end]
        if not raw.strip():
            continue
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        identity = hashlib.sha256(
            f"{fragment_number}:{candidate_id}:{start}:{end}:{digest}".encode("utf-8")
        ).hexdigest()[:10]
        output.append(
            EvidenceUnit(
                unit_id=f"E{index:03d}_{identity}",
                fragment_number=fragment_number,
                candidate_id=candidate_id,
                source_start=start,
                source_end=end,
                content=raw,
                content_sha256=digest,
            )
        )
    return output
