"""Deterministic evidence enumeration with bounded per-chunk ID selection.

The contract removes two lossy stages from the S210/S212 experiment family:

* source evidence is enumerated locally and deterministically instead of being
  proposed by a model;
* relevant evidence competes only with units from its own source chunk instead
  of a question-wide candidate pool.

Models may select opaque IDs, but they cannot author, edit, or render evidence.
There is no parallel fallback lane.  Every rendered byte is reconstructed from
frozen source spans.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .evidence_units_v2 import build_header_aware_evidence_units
SHARDED_UNIT_SELECTOR_V1 = "sharded_unit_selector_s213_v1"
MAX_PRIMARY_ADDITIONS_PER_CHUNK = 4
MAX_VERIFIER_ADDITIONS_PER_CHUNK = 2
MAX_COMPILED_IDS = 32
MAX_COMPILED_CHARS = 12_000


@dataclass(frozen=True)
class ShardedEvidenceCandidate:
    evidence_id: str
    origin: str
    unit_kind: str
    fragment_number: int
    candidate_id: str
    source_spans: tuple[tuple[int, int], ...]
    content: str
    content_sha256: str
    def public_payload(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "content": self.content}


def build_sharded_candidates(
    question: str, chunks: list[dict[str, Any]]
) -> list[list[ShardedEvidenceCandidate]]:
    """Return a complete deterministic candidate shard for every served chunk."""
    if not str(question).strip():
        raise ValueError("question is empty")
    shards: list[list[ShardedEvidenceCandidate]] = []
    for fragment_number, chunk in enumerate(chunks, 1):
        source = str(chunk.get("content") or "")
        candidate_id = str(chunk.get("id") or chunk.get("candidate_id") or "").strip()
        if not source or not candidate_id:
            raise ValueError("source chunk identity is incomplete")
        units = build_header_aware_evidence_units(
            source,
            fragment_number=fragment_number,
            candidate_id=candidate_id,
        )
        shard = [
            ShardedEvidenceCandidate(
                evidence_id=unit.unit_id,
                origin="deterministic_header_aware_unit",
                unit_kind=unit.unit_kind,
                fragment_number=fragment_number,
                candidate_id=candidate_id,
                source_spans=unit.source_spans,
                content=unit.content,
                content_sha256=unit.content_sha256,
            )
            for unit in units
        ]
        if not shard:
            raise ValueError("deterministic source enumeration returned an empty shard")
        shards.append(shard)

    all_ids = [candidate.evidence_id for shard in shards for candidate in shard]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("evidence IDs are not unique across shards")
    return shards


def selection_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evidence_ids"],
        "properties": {
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
    }


def verification_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "missing_facets", "additional_evidence_ids"],
        "properties": {
            "status": {"type": "string", "enum": ["COMPLETE", "INCOMPLETE"]},
            "missing_facets": {"type": "array", "items": {"type": "string"}},
            "additional_evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }


def _validate_schema(value: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise ValueError(f"{label} schema violation: {errors[0].message}")


def selector_payload(
    question: str, candidates: list[ShardedEvidenceCandidate]
) -> str:
    return json.dumps(
        {
            "question": question,
            "fragment_number": candidates[0].fragment_number,
            "evidence_units": [row.public_payload() for row in candidates],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def verifier_payload(
    question: str,
    candidates: list[ShardedEvidenceCandidate],
    selected_ids: Iterable[str],
) -> str:
    return json.dumps(
        {
            "question": question,
            "fragment_number": candidates[0].fragment_number,
            "selected_evidence_ids": list(selected_ids),
            "evidence_units": [row.public_payload() for row in candidates],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_selection(
    value: dict[str, Any], candidates: list[ShardedEvidenceCandidate]
) -> tuple[str, ...]:
    _validate_schema(value, selection_schema(), "selection")
    ids = value["evidence_ids"]
    known = {row.evidence_id for row in candidates}
    if len(ids) > MAX_PRIMARY_ADDITIONS_PER_CHUNK:
        raise ValueError("primary per-chunk addition count violation")
    if len(ids) != len(set(ids)) or not set(ids).issubset(known):
        raise ValueError("primary selection contains duplicate or unknown IDs")
    return tuple(ids)


def validate_verification(
    value: dict[str, Any],
    candidates: list[ShardedEvidenceCandidate],
    selected_ids: Iterable[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    _validate_schema(value, verification_schema(), "verification")
    selected = set(selected_ids)
    ids = value["additional_evidence_ids"]
    facets = tuple(str(item).strip() for item in value["missing_facets"] if str(item).strip())
    known = {row.evidence_id for row in candidates}
    if len(ids) > MAX_VERIFIER_ADDITIONS_PER_CHUNK:
        raise ValueError("verifier per-chunk addition count violation")
    if len(ids) != len(set(ids)) or not set(ids).issubset(known) or set(ids) & selected:
        raise ValueError("verification contains duplicate, selected, or unknown IDs")
    if value["status"] == "COMPLETE" and (facets or ids):
        raise ValueError("complete verification cannot contain omissions")
    if value["status"] == "INCOMPLETE" and (not facets or not ids):
        raise ValueError("incomplete verification must identify facets and additions")
    return value["status"], facets, tuple(ids)


def compile_sharded_appendix(
    candidates: list[ShardedEvidenceCandidate], selected_ids: Iterable[str]
) -> tuple[str, list[dict[str, Any]]]:
    """Compile selected IDs from exact source-bound content and emit span receipts."""
    by_id = {row.evidence_id: row for row in candidates}
    ordered = tuple(selected_ids)
    if not ordered or len(ordered) > MAX_COMPILED_IDS:
        raise ValueError("compiled evidence ID count violation")
    if len(ordered) != len(set(ordered)):
        raise ValueError("compiled evidence contains duplicate IDs")
    if not set(ordered).issubset(by_id):
        raise ValueError("compiled evidence contains unknown IDs")

    blocks: list[str] = []
    receipts: list[dict[str, Any]] = []
    seen_spans: set[tuple[str, int, int]] = set()
    for evidence_id in ordered:
        row = by_id[evidence_id]
        marker = f"[F{row.fragment_number}]"
        blocks.append(f"- {marker} {row.content.strip()} {marker}")
        for span_index, (start, end) in enumerate(row.source_spans, 1):
            identity = (row.candidate_id, start, end)
            if identity in seen_spans:
                continue
            seen_spans.add(identity)
            receipt = asdict(row)
            receipt.update(
                {
                    "evidence_id": (
                        evidence_id
                        if len(row.source_spans) == 1
                        else f"{evidence_id}:span{span_index}"
                    ),
                    "source_start": start,
                    "source_end": end,
                }
            )
            receipt.pop("source_spans")
            receipts.append(receipt)
    appendix = (
        "### Evidencia adicional verificada\n\n"
        "Los siguientes puntos proceden literalmente de los fragmentos servidos y "
        "completan la respuesta anterior:\n\n"
        + "\n\n".join(blocks)
    )
    if len(appendix) > MAX_COMPILED_CHARS:
        raise ValueError("compiled evidence exceeds the character bound")
    return appendix, receipts
