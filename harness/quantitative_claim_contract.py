"""Detect source-bound quantitative claims that a cited answer states partially."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from .relation_complete_highlights import build_relation_complete_highlights


QUANTITATIVE_CLAIM_CONTRACT = "s249_partial_quantitative_claim_v1"

_UNIT = (
    r"%|ms|s|sec(?:ond)?s?|seg(?:undo)?s?|min(?:ute)?s?|h(?:ours?|oras?)?|"
    r"mA|A|V(?:ac|dc|ca|cc)?|kV|W|kW|Ω|Ω|ohm(?:s)?|kΩ|kohm(?:s)?|"
    r"Hz|kHz|dB|mm|cm|m|km|°C|ºC|Ah|kWh|bar|psi"
)
_RANGE = re.compile(
    rf"(?<![\w.])(?P<left>[<>≤≥]?\s*[±+-]?\d+(?:[.,]\d+)?)\s*"
    rf"(?:-|–|—|to|a|hasta)\s*"
    rf"(?P<right>[<>≤≥]?\s*[±+-]?\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT})(?!\w)",
    re.IGNORECASE,
)
_VALUE = re.compile(
    rf"(?<![\w.])(?P<value>[<>≤≥]?\s*[±+-]?\d+(?:[.,]\d+)?)\s*"
    rf"(?P<unit>{_UNIT})(?!\w)",
    re.IGNORECASE,
)
_CONFIG_RANGE = re.compile(
    r"(?<!\w)(?P<left>[A-Z]{1,3}\d{1,3})\s*(?:-|–|—|to|a|hasta)\s*"
    r"(?P<right>[A-Z]{1,3}\d{1,3})(?!\w)",
    re.IGNORECASE,
)
_CITATION = re.compile(r"\[F(?P<number>\d+)]", re.IGNORECASE)
_WORD = re.compile(r"[a-záéíóúüñ]{3,}", re.IGNORECASE)
_STOP = {
    "para", "como", "cuando", "desde", "hasta", "entre", "sobre", "cada",
    "with", "from", "when", "then", "than", "into", "that", "this", "the",
    "una", "uno", "unos", "unas", "del", "las", "los", "por", "con", "sin",
    "and", "for", "are", "was", "were", "all", "any", "value", "valor",
}


@dataclass(frozen=True)
class QuantitativeField:
    canonical: str
    source_start: int
    source_end: int
    raw: str


@dataclass(frozen=True)
class PartialQuantitativeClaim:
    finding_id: str
    fragment_number: int
    atom_id: str
    answer_segment: str
    present_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    shared_anchors: tuple[str, ...]
    source_spans: tuple[tuple[int, int], ...]
    source_content: str


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _canonical_value(value: str, unit: str) -> str:
    number = re.sub(r"\s+", "", value).replace(",", ".")
    normalized_unit = _fold(unit).replace("ω", "ohm").replace("Ω", "ohm")
    return f"{number}{normalized_unit}"


def extract_quantitative_fields(text: str) -> tuple[QuantitativeField, ...]:
    """Return technical fields; dates, pages, revisions and bare IDs are absent."""
    fields: list[QuantitativeField] = []
    occupied: list[tuple[int, int]] = []

    def add(canonical: str, start: int, end: int) -> None:
        if canonical and all(not (start < right and end > left) for left, right in occupied):
            fields.append(QuantitativeField(canonical, start, end, text[start:end]))
            occupied.append((start, end))

    for match in _CONFIG_RANGE.finditer(text):
        left = _fold(match.group("left"))
        right = _fold(match.group("right"))
        add(f"config:{left}", match.start("left"), match.end("left"))
        add(f"config:{right}", match.start("right"), match.end("right"))
    for match in _RANGE.finditer(text):
        unit = match.group("unit")
        add(
            _canonical_value(match.group("left"), unit),
            match.start("left"),
            match.end("left"),
        )
        add(
            _canonical_value(match.group("right"), unit),
            match.start("right"),
            match.end("right"),
        )
    for match in _VALUE.finditer(text):
        add(
            _canonical_value(match.group("value"), match.group("unit")),
            match.start(),
            match.end(),
        )
    return tuple(sorted(fields, key=lambda row: (row.source_start, row.source_end)))


def _anchors(text: str) -> set[str]:
    return {
        word
        for raw in _WORD.findall(_fold(text))
        if (word := _fold(raw)) not in _STOP and not any(char.isdigit() for char in word)
    }


def _answer_segments(answer: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(
            r"(?s)(?:^|\n\s*\n)(\s*\S.*?)(?=\n\s*\n|$)", answer
        )
        if match.group(1).strip()
    ]


def _field_present(field: QuantitativeField, answer_fields: tuple[QuantitativeField, ...]) -> bool:
    return any(candidate.canonical == field.canonical for candidate in answer_fields)


def find_partial_quantitative_claims(
    answer: str, fragments: list[dict]
) -> list[PartialQuantitativeClaim]:
    findings: list[PartialQuantitativeClaim] = []
    for segment in _answer_segments(answer):
        cited = {int(match.group("number")) for match in _CITATION.finditer(segment)}
        if not cited:
            continue
        answer_fields = extract_quantitative_fields(segment)
        if not answer_fields:
            continue
        answer_anchors = _anchors(segment)
        for fragment_number in sorted(cited):
            if not 1 <= fragment_number <= len(fragments):
                continue
            fragment = fragments[fragment_number - 1]
            source = str(fragment.get("content") or "")
            candidate_id = str(fragment.get("id") or fragment.get("candidate_id") or "")
            if not source or not candidate_id:
                continue
            for atom in build_relation_complete_highlights(
                source,
                fragment_number=fragment_number,
                candidate_id=candidate_id,
            ):
                if "numeric_bundle" not in atom.reason_labels:
                    continue
                source_fields = extract_quantitative_fields(atom.content)
                unique = {field.canonical for field in source_fields}
                if len(unique) < 2:
                    continue
                present = tuple(
                    sorted({
                        field.canonical
                        for field in source_fields
                        if _field_present(field, answer_fields)
                    })
                )
                if not present:
                    continue
                missing = tuple(sorted(unique - set(present)))
                if not missing:
                    continue
                shared = tuple(sorted(answer_anchors & _anchors(atom.content)))
                if len(shared) < 2:
                    continue
                material = "|".join(
                    [QUANTITATIVE_CLAIM_CONTRACT, atom.atom_id, *present, *missing]
                )
                finding_id = "Q_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
                findings.append(
                    PartialQuantitativeClaim(
                        finding_id=finding_id,
                        fragment_number=fragment_number,
                        atom_id=atom.atom_id,
                        answer_segment=segment,
                        present_fields=present,
                        missing_fields=missing,
                        shared_anchors=shared,
                        source_spans=atom.source_spans,
                        source_content=atom.content,
                    )
                )
    unique_findings: dict[tuple[int, str, tuple[str, ...]], PartialQuantitativeClaim] = {}
    for finding in findings:
        key = (finding.fragment_number, finding.atom_id, finding.missing_fields)
        unique_findings.setdefault(key, finding)
    return list(unique_findings.values())

