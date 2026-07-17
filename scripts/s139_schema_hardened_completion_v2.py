#!/usr/bin/env python3
"""Run S139 with provider-compatible exact keyed structured output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as files
from scripts import s139_schema_hardened_completion as base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERMIT = ROOT / "evals/s139_schema_hardened_completion_execution_permit_v2.yaml"
_ACTIVE_PACKET: dict[str, Any] | None = None


class S139V2Failure(RuntimeError):
    pass


def assessment_value_schema(evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["relevance", "supported_claim", "redundant_with"],
        "properties": {
            "relevance": {"type": "string", "enum": sorted(base.s138.RELEVANCE)},
            "supported_claim": {"type": "string"},
            "redundant_with": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_ids},
            },
        },
    }


def set_value_schema(evidence_set: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = [row["evidence_id"] for row in evidence_set["evidence"]]
    evidence_properties = {
        evidence_id: assessment_value_schema(evidence_ids) for evidence_id in evidence_ids
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "answerability",
            "minimum_sufficient_evidence_ids",
            "evidence_by_id",
            "confidence",
            "rationale",
        ],
        "properties": {
            "answerability": {"type": "string", "enum": sorted(base.s138.ANSWERABILITY)},
            "minimum_sufficient_evidence_ids": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_ids},
            },
            "evidence_by_id": {
                "type": "object",
                "additionalProperties": False,
                "required": evidence_ids,
                "properties": evidence_properties,
            },
            "confidence": {"type": "string", "enum": sorted(base.s138.CONFIDENCE)},
            "rationale": {"type": "string"},
        },
    }


def question_value_schema(question: dict[str, Any]) -> dict[str, Any]:
    set_ids = [row["evidence_set_id"] for row in question["evidence_sets"]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sets_by_id"],
        "properties": {
            "sets_by_id": {
                "type": "object",
                "additionalProperties": False,
                "required": set_ids,
                "properties": {
                    row["evidence_set_id"]: set_value_schema(row)
                    for row in question["evidence_sets"]
                },
            }
        },
    }


def hardened_schema(packet: dict[str, Any]) -> dict[str, Any]:
    qids = [row["question_id"] for row in packet["questions"]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions_by_id"],
        "properties": {
            "questions_by_id": {
                "type": "object",
                "additionalProperties": False,
                "required": qids,
                "properties": {
                    row["question_id"]: question_value_schema(row)
                    for row in packet["questions"]
                },
            }
        },
    }


def keyed_to_standard(value: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    questions = value.get("questions_by_id")
    if not isinstance(questions, dict):
        raise S139V2Failure("S139 v2 output has no questions_by_id object")
    judgements: list[dict[str, Any]] = []
    for question in packet["questions"]:
        qid = question["question_id"]
        question_value = questions[qid]
        set_values = question_value["sets_by_id"]
        set_judgements: list[dict[str, Any]] = []
        for evidence_set in question["evidence_sets"]:
            set_id = evidence_set["evidence_set_id"]
            set_value = set_values[set_id]
            assessments = []
            for evidence in evidence_set["evidence"]:
                evidence_id = evidence["evidence_id"]
                assessments.append(
                    {
                        "evidence_id": evidence_id,
                        **set_value["evidence_by_id"][evidence_id],
                    }
                )
            set_judgements.append(
                {
                    "evidence_set_id": set_id,
                    "answerability": set_value["answerability"],
                    "minimum_sufficient_evidence_ids": set_value[
                        "minimum_sufficient_evidence_ids"
                    ],
                    "evidence_assessments": assessments,
                    "confidence": set_value["confidence"],
                    "rationale": set_value["rationale"],
                }
            )
        judgements.append({"question_id": qid, "set_judgements": set_judgements})
    return {"judgements": judgements}


def parse_keyed(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise S139V2Failure(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise S139V2Failure(f"{label} returned non-object JSON")
    if _ACTIVE_PACKET is None:
        raise S139V2Failure("S139 v2 packet context is not initialized")
    qids = set(value.get("questions_by_id", {}))
    subset = base.s138.subset_packet(_ACTIVE_PACKET, qids)
    if not qids or len(subset["questions"]) != len(qids):
        raise S139V2Failure(f"{label} returned unknown question IDs")
    return keyed_to_standard(value, subset)


def validate_v2_permit(permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise S139V2Failure("S139 v2 permit is not GO")
    if permit.get("schema_version") != "exact_keyed_objects_v2":
        raise S139V2Failure("S139 v2 schema version mismatch")
    for name in (
        "design_addendum",
        "schema_failure_receipt",
        "preregistration",
        "base_runner",
        "runner",
        "tests",
    ):
        spec = permit[name]
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S139V2Failure(f"S139 v2 permitted artifact drift: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--confirm-paid", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid:
        raise S139V2Failure("S139 v2 execution requires --confirm-paid")
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    permit = files.load_yaml(permit_path)
    validate_v2_permit(permit)
    prereg = files.load_yaml(ROOT / permit["preregistration"]["path"])
    base.validate_prereg(prereg)

    global _ACTIVE_PACKET
    _ACTIVE_PACKET = files.load_json(ROOT / prereg["frozen_inputs"]["packet"]["path"])
    base.hardened_schema = hardened_schema
    base.s138.parse = parse_keyed
    result = base.execute(prereg, permit, args.env_file.resolve())
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
