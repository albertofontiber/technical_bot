"""Source-preserving units and validators for bounded omission correction."""
from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from typing import Any

from .evidence_units_v2 import EvidenceUnitV2, build_header_aware_evidence_units


OMISSION_CORRECTION_CONTRACT = "post_answer_source_unit_omission_correction_v1"
MAX_SELECTED_PER_FRAGMENT = 8
_STOPWORDS = {
    "a", "al", "ante", "bajo", "como", "con", "contra", "de", "del", "desde",
    "donde", "el", "ella", "en", "entre", "es", "esta", "este", "la", "las",
    "lo", "los", "o", "para", "pero", "por", "que", "se", "sin", "sobre", "su",
    "sus", "un", "una", "y", "the", "of", "to", "and", "in", "is", "for",
}


def fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char)).casefold()
    return re.sub(r"[*_`~]+", "", value)


def units_by_fragment(chunks: list[dict[str, Any]]) -> dict[int, list[EvidenceUnitV2]]:
    output: dict[int, list[EvidenceUnitV2]] = {}
    for fragment, chunk in enumerate(chunks, 1):
        output[fragment] = build_header_aware_evidence_units(
            str(chunk.get("content") or ""),
            fragment_number=fragment,
            candidate_id=str(chunk.get("id") or chunk.get("chunk_id") or ""),
        )
    return output


def selector_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False, "required": ["unit_ids"],
        "properties": {"unit_ids": {"type": "array", "items": {"type": "string"}}},
    }


def validate_selected_ids(value: dict[str, Any], units: list[EvidenceUnitV2]) -> list[EvidenceUnitV2]:
    ids = value.get("unit_ids")
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError("unit_ids must be an array of strings")
    if len(ids) > MAX_SELECTED_PER_FRAGMENT or len(ids) != len(set(ids)):
        raise ValueError("invalid omission unit cardinality")
    by_id = {unit.unit_id: unit for unit in units}
    if not set(ids).issubset(by_id):
        raise ValueError("unknown omission unit id")
    return [by_id[unit_id] for unit_id in ids]


def render_verified_omissions(units: Iterable[EvidenceUnitV2]) -> str:
    rows = []
    seen: set[str] = set()
    for unit in units:
        if unit.unit_id in seen:
            continue
        seen.add(unit.unit_id)
        rows.append(
            f"[Unidad fuente omitida {unit.unit_id} | Fragmento original F{unit.fragment_number}]\n"
            f"{unit.content}"
        )
    return "\n\n---\n\n".join(rows)


def answer_citations(answer: str) -> list[int]:
    return [int(value) for value in re.findall(r"\[F(\d+)\]", answer or "")]


def invalid_citations(answer: str, fragment_count: int) -> list[int]:
    return sorted({value for value in answer_citations(answer) if not 1 <= value <= fragment_count})


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", fold(value))
        if len(token) > 2 and token not in _STOPWORDS
    }


def _critical_tokens(value: str) -> set[str]:
    folded = fold(value)
    return set(re.findall(r"(?<![a-z0-9])(?:[a-z]{1,5}[-.]?\d+[a-z0-9.-]*|\d+(?:[.,]\d+)?\s*(?:%|v|ma|a|s|min|ohm|ω)?)(?![a-z0-9])", folded))


def point_covered(answer: str, point: dict[str, Any]) -> bool:
    """Conservative local screening; semantic promotion uses independent judges."""
    folded_answer = fold(answer)
    critical = _critical_tokens(str(point.get("exact_quote") or ""))
    if any(token not in folded_answer for token in critical):
        return False
    expected = _tokens(str(point.get("claim") or ""))
    observed = _tokens(answer)
    recall = len(expected & observed) / max(1, len(expected))
    return recall >= 0.45


def prompt_payload(question: str, draft: str, units: list[EvidenceUnitV2]) -> str:
    return json.dumps(
        {
            "question": question,
            "draft_answer": draft,
            "source_units": [
                {"unit_id": unit.unit_id, "content": unit.content} for unit in units
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
