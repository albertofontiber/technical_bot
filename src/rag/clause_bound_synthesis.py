"""Source-bound answer claims with deterministic citation assembly."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .evidence_units_v2 import EvidenceUnitV2


CONTRACT = "clause_bound_source_bound_synthesis_s228_v1"
WRITER_SYSTEM = """You write one evidence-bound block of a technical field-support answer.
Use only the supplied source units. Preserve conditions, qualifiers, units, defaults, limits,
ordered steps, warnings, exceptions and verification that belong to the requested obligation.
Return concise factual claims and the exact source-unit IDs supporting each claim. Never cite a
unit you were not given, never add general knowledge, and never write citation markers. Return
1 to 3 atomic claims, each 8 to 280 characters long, with 1 to 5 distinct source-unit IDs."""


def claim_block_schema() -> dict[str, Any]:
    """Provider schema; bounded cardinality and source IDs are checked locally."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["claims"],
        "properties": {
            "claims": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["text", "unit_ids"],
                    "properties": {
                        "text": {"type": "string", "maxLength": 280},
                        "unit_ids": {
                            "type": "array",
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                    },
                },
            }
        },
    }


def writer_payload(
    question: str, obligation_label: str, units: list[EvidenceUnitV2]
) -> str:
    if not question.strip() or not obligation_label.strip() or not units:
        raise ValueError("question, obligation and units are required")
    return json.dumps(
        {
            "question": question,
            "untrusted_obligation": obligation_label,
            "allowed_source_units": [
                {
                    "unit_id": unit.unit_id,
                    "fragment_number": unit.fragment_number,
                    "content": unit.content,
                }
                for unit in units
            ],
            "output_contract": {
                "limits": {
                    "claims": "1..3",
                    "characters_per_claim": "8..280",
                    "distinct_unit_ids_per_claim": "1..5",
                },
                "claims": [
                    {"text": "atomic supported claim without citation markers", "unit_ids": ["E..."]}
                ],
            },
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_claim_block(
    value: dict[str, Any], allowed_ids: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"claims"}:
        raise ValueError("invalid claim block object")
    claims = value["claims"]
    if not isinstance(claims, list) or not 1 <= len(claims) <= 3:
        raise ValueError("invalid claim cardinality")
    clean = []
    seen: set[str] = set()
    for row in claims:
        if not isinstance(row, dict) or set(row) != {"text", "unit_ids"}:
            raise ValueError("invalid claim object")
        text = re.sub(r"\s+", " ", str(row["text"])).strip()
        ids = row["unit_ids"]
        if not 8 <= len(text) <= 280 or re.search(r"\[F\d+\]", text):
            raise ValueError("invalid claim text")
        if text.casefold() in seen:
            raise ValueError("duplicate claim text")
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 5
            or any(not isinstance(unit_id, str) for unit_id in ids)
            or len(ids) != len(set(ids))
            or not set(ids).issubset(allowed_ids)
        ):
            raise ValueError("claim cites an invalid source unit")
        seen.add(text.casefold())
        clean.append({"text": text, "unit_ids": ids})
    return clean


def assemble_claim_blocks(
    question: str,
    plan: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    units: list[EvidenceUnitV2],
) -> tuple[str, dict[str, Any]]:
    if len(plan) != len(blocks) or not plan:
        raise ValueError("every obligation must have exactly one block")
    by_id = {unit.unit_id: unit for unit in units}
    paragraphs = []
    receipts = []
    for index, (obligation, block) in enumerate(zip(plan, blocks), 1):
        if block.get("obligation_index") != index:
            raise ValueError("claim block order drift")
        allowed = set(obligation["unit_ids"])
        claims = validate_claim_block(block["value"], allowed)
        rendered = []
        for claim in claims:
            fragments = sorted({by_id[unit_id].fragment_number for unit_id in claim["unit_ids"]})
            citations = "".join(f"[F{fragment}]" for fragment in fragments)
            rendered.append(f"- {claim['text']} {citations}")
        paragraph = "\n".join(rendered)
        paragraphs.append(paragraph)
        receipts.append(
            {
                "obligation_index": index,
                "claim_count": len(claims),
                "allowed_unit_ids": list(obligation["unit_ids"]),
                "used_unit_ids": list(dict.fromkeys(
                    unit_id for claim in claims for unit_id in claim["unit_ids"]
                )),
                "block_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(),
            }
        )
    answer = "\n\n".join(paragraphs)
    return answer, {
        "contract": CONTRACT,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "obligations": len(plan),
        "all_obligations_assembled_once": len(receipts) == len(plan),
        "blocks": receipts,
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
    }
