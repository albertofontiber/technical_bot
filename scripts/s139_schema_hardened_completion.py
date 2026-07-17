#!/usr/bin/env python3
"""Complete S138 with a packet-specific closed output schema."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as files
from scripts import s137_blinded_chunks_semantic_adjudication as receipts
from scripts import s138_symmetric_semantic_mrr as s138


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s139_schema_hardened_completion_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s139_schema_hardened_completion_execution_permit_v1.yaml"


class S139Failure(RuntimeError):
    pass


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    for name, spec in {"design": prereg["design"], **prereg["frozen_inputs"]}.items():
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S139Failure(f"S139 frozen artifact drift: {name}")


def assessment_schema(evidence_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evidence_id", "relevance", "supported_claim", "redundant_with"],
        "properties": {
            "evidence_id": {"type": "string", "const": evidence_id},
            "relevance": {"type": "string", "enum": sorted(s138.RELEVANCE)},
            "supported_claim": {"type": "string"},
            "redundant_with": {"type": "array", "items": {"type": "string"}},
        },
    }


def evidence_set_schema(evidence_set: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = [row["evidence_id"] for row in evidence_set["evidence"]]
    assessment_schemas = [assessment_schema(evidence_id) for evidence_id in evidence_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "evidence_set_id",
            "answerability",
            "minimum_sufficient_evidence_ids",
            "evidence_assessments",
            "confidence",
            "rationale",
        ],
        "properties": {
            "evidence_set_id": {"type": "string", "const": evidence_set["evidence_set_id"]},
            "answerability": {"type": "string", "enum": sorted(s138.ANSWERABILITY)},
            "minimum_sufficient_evidence_ids": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_ids},
                "uniqueItems": True,
                "maxItems": len(evidence_ids),
            },
            "evidence_assessments": {
                "type": "array",
                "prefixItems": assessment_schemas,
                "minItems": len(assessment_schemas),
                "maxItems": len(assessment_schemas),
            },
            "confidence": {"type": "string", "enum": sorted(s138.CONFIDENCE)},
            "rationale": {"type": "string"},
        },
    }


def question_schema(question: dict[str, Any]) -> dict[str, Any]:
    set_schemas = [evidence_set_schema(row) for row in question["evidence_sets"]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["question_id", "set_judgements"],
        "properties": {
            "question_id": {"type": "string", "const": question["question_id"]},
            "set_judgements": {
                "type": "array",
                "prefixItems": set_schemas,
                "minItems": len(set_schemas),
                "maxItems": len(set_schemas),
            },
        },
    }


def hardened_schema(packet: dict[str, Any]) -> dict[str, Any]:
    question_schemas = [question_schema(row) for row in packet["questions"]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["judgements"],
        "properties": {
            "judgements": {
                "type": "array",
                "prefixItems": question_schemas,
                "minItems": len(question_schemas),
                "maxItems": len(question_schemas),
            }
        },
    }


def anthropic_output(schema: dict[str, Any], effort: str) -> dict[str, Any]:
    return {"effort": effort, "format": {"type": "json_schema", "schema": schema}}


def openai_text(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s139_schema_hardened_judgement",
            "schema": schema,
            "strict": True,
        },
        "verbosity": "low",
    }


def validate_permit(permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise S139Failure("S139 permit is not GO")
    for name in ("preregistration", "runner", "tests"):
        spec = permit[name]
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S139Failure(f"S139 permitted artifact drift: {name}")


def load_frozen(prereg: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    frozen = {
        name: files.load_json(root / spec["path"])
        for name, spec in prereg["frozen_inputs"].items()
        if name not in {"s138_prereg"}
    }
    packet = frozen["packet"]
    mapping = frozen["mapping"]
    s138.assert_blind(packet)
    sol = frozen["sol_valid"]
    q1 = frozen["fable_q1_valid"]
    q2 = frozen["fable_q2_valid"]
    invalid = frozen["fable_q3_invalid"]
    if sol.get("status") != "VALIDATED":
        raise S139Failure("S139 frozen Sol judgement is not validated")
    if any(row.get("status") != "VALIDATED" for row in (q1, q2)):
        raise S139Failure("S139 reusable Fable judgement is not validated")
    if invalid.get("status") != "PAID_INVALID_NO_RETRY":
        raise S139Failure("S139 q3 incident is not the frozen invalid response")
    s138.validate_judgement(sol["judgement"], packet)
    for receipt in (q1, q2):
        qids = {row["question_id"] for row in receipt["judgement"]["judgements"]}
        s138.validate_judgement(
            receipt["judgement"], s138.subset_packet(packet, qids), question_ids=qids
        )
    return {**frozen, "packet": packet, "mapping": mapping}


def incremental_worst(prereg: dict[str, Any], fable_input: int) -> float:
    prices = prereg["pricing_usd_per_million_tokens"]
    fable = prereg["models"]["independent_completion"]
    arb = prereg["models"]["arbitration"]
    return round(
        (
            fable_input * prices["anthropic"]["input"]
            + fable["max_output_tokens"] * prices["anthropic"]["output"]
            + arb["max_counted_input_tokens"] * prices["openai"]["input_conservative_cache_write"]
            + arb["max_output_tokens"] * prices["openai"]["output"]
        )
        / 1_000_000,
        8,
    )


def provider_exception_record(stage: str, exc: Exception) -> dict[str, Any]:
    return {
        "instrument": "s139_provider_exception_v1",
        "status": "FAILED_NO_RETRY_AUTHORIZED",
        "created_at": receipts.utc_now(),
        "stage": stage,
        "exception_type": type(exc).__name__,
        "http_status": getattr(exc, "status_code", None),
        "request_id": getattr(exc, "request_id", None),
        "message": str(exc),
        "authorization": {"retry": False, "production": False, "facts_moved_to_ok": 0},
    }


def execute(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_prereg(prereg, root=root)
    validate_permit(permit, root=root)
    frozen = load_frozen(prereg, root=root)
    packet = frozen["packet"]
    mapping = frozen["mapping"]
    q3id = prereg["completion_question_id"]
    q3_packet = s138.subset_packet(packet, {q3id})
    q3_schema = hardened_schema(q3_packet)

    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    secrets = dotenv_values(env_file)
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    openai_key = (
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    if not anthropic_key or not openai_key:
        raise S139Failure("S139 provider API key missing")
    anthropic_client = Anthropic(api_key=anthropic_key)
    openai_client = OpenAI(api_key=openai_key)
    fable_cfg = prereg["models"]["independent_completion"]
    prompt = s138.user_prompt(q3_packet)
    counted = anthropic_client.messages.count_tokens(
        model=fable_cfg["model"],
        system=s138.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": fable_cfg["thinking"]},
        output_config=anthropic_output(q3_schema, fable_cfg["effort"]),
    ).input_tokens
    if counted > fable_cfg["max_counted_input_tokens"]:
        raise S139Failure("S139 Fable input exceeds cap")
    incremental_reserved = incremental_worst(prereg, counted)
    total_reserved = (
        prereg["budget"]["known_s138_cost_before_s139_usd"]
        + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
        + incremental_reserved
    )
    preflight = {
        "instrument": "s139_paid_preflight_v1",
        "status": "GO" if total_reserved < prereg["budget"]["s138_internal_ceiling_usd"] else "NO_GO",
        "created_at": receipts.utc_now(),
        "fable_q3_input_tokens": counted,
        "s139_incremental_worst_case_usd": incremental_reserved,
        "s138_total_reserved_worst_case_usd": round(total_reserved, 8),
        "combined_with_s137_reserved_worst_case_usd": round(
            total_reserved + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
        ),
    }
    receipts._write(root / prereg["execution"]["paid_preflight"], preflight)
    if preflight["status"] != "GO":
        raise S139Failure("S139 preflight exceeds internal ceiling")

    try:
        response = anthropic_client.messages.create(
            model=fable_cfg["model"],
            max_tokens=fable_cfg["max_output_tokens"],
            system=s138.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": fable_cfg["thinking"]},
            output_config=anthropic_output(q3_schema, fable_cfg["effort"]),
        )
    except Exception as exc:
        receipts._write(
            root / prereg["execution"]["fable_q3"], provider_exception_record("fable_q3", exc)
        )
        raise
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    usage = response.usage.model_dump(mode="json")
    cost = receipts.anthropic_cost(usage, prereg["pricing_usd_per_million_tokens"]["anthropic"])
    try:
        if response.stop_reason == "max_tokens":
            raise S139Failure("S139 Fable q3 truncated; no retry authorised")
        judgement = s138.parse(raw_text, "S139 Fable q3")
        s138.validate_judgement(judgement, q3_packet, question_ids={q3id})
    except Exception as exc:
        receipts._write(
            root / prereg["execution"]["fable_q3"],
            s138.failure_record(
                provider="anthropic",
                model=fable_cfg["model"],
                response=response,
                packet=q3_packet,
                raw_output=raw_text,
                failure=str(exc),
                usage=usage,
                cost=cost,
            ),
        )
        raise
    q3_receipt = s138.response_record(
        provider="anthropic",
        model=fable_cfg["model"],
        response=response,
        packet=q3_packet,
        judgement=judgement,
        usage=usage,
        cost=cost,
    )
    receipts._write(root / prereg["execution"]["fable_q3"], q3_receipt)

    independent_receipts = [
        frozen["fable_q1_valid"],
        frozen["fable_q2_valid"],
        q3_receipt,
    ]
    combined_judgement = {
        "judgements": [
            row
            for receipt in independent_receipts
            for row in receipt["judgement"]["judgements"]
        ]
    }
    s138.validate_judgement(combined_judgement, packet)
    fable_combined = {
        "instrument": "s139_fable_atomic_combined_v1",
        "status": "VALIDATED",
        "provider": "anthropic",
        "model": fable_cfg["model"],
        "created_at": receipts.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": {
            "input_tokens": sum(row["usage"]["input_tokens"] for row in independent_receipts),
            "output_tokens": sum(row["usage"]["output_tokens"] for row in independent_receipts),
            "response_ids": [row["response_id"] for row in independent_receipts],
        },
        "conservative_cost_usd": round(
            sum(row["conservative_cost_usd"] for row in independent_receipts), 8
        ),
        "judgement": combined_judgement,
    }
    receipts._write(root / prereg["execution"]["fable_combined"], fable_combined)

    sol = frozen["sol_valid"]
    sol_ranks = s138.semantic_ranks(sol["judgement"], mapping)
    fable_ranks = s138.semantic_ranks(combined_judgement, mapping)
    disagreements = {qid for qid in sol_ranks if sol_ranks[qid] != fable_ranks[qid]}
    arbitration_receipt = None
    if disagreements:
        arb_cfg = prereg["models"]["arbitration"]
        arb_packet = s138.subset_packet(packet, disagreements)
        arb_schema = hardened_schema(arb_packet)
        arb_prompt = (
            "Independently resolve these blinded set judgements. Prior judgements A and B are "
            "advisory; re-read all raw evidence and return your own complete assessment.\n\n"
            + json.dumps(
                {
                    "questions": arb_packet["questions"],
                    "judgement_A": s138.subset_judgement(sol["judgement"], disagreements),
                    "judgement_B": s138.subset_judgement(combined_judgement, disagreements),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        arb_count = openai_client.responses.input_tokens.count(
            model=arb_cfg["model"],
            reasoning={"effort": arb_cfg["reasoning_effort"]},
            instructions=s138.SYSTEM_PROMPT,
            input=arb_prompt,
            text=openai_text(arb_schema),
        ).input_tokens
        if arb_count > arb_cfg["max_counted_input_tokens"]:
            raise S139Failure("S139 arbitration input exceeds cap")
        try:
            arb_response = openai_client.responses.create(
                model=arb_cfg["model"],
                reasoning={"effort": arb_cfg["reasoning_effort"]},
                instructions=s138.SYSTEM_PROMPT,
                input=arb_prompt,
                text=openai_text(arb_schema),
                max_output_tokens=arb_cfg["max_output_tokens"],
                store=False,
            )
        except Exception as exc:
            receipts._write(
                root / prereg["execution"]["arbitration"],
                provider_exception_record("sol_arbitration", exc),
            )
            raise
        raw_arb = arb_response.output_text
        arb_usage = arb_response.usage.model_dump(mode="json")
        arb_cost = receipts.conservative_openai_cost(
            arb_usage,
            {
                "cache_write": prereg["pricing_usd_per_million_tokens"]["openai"][
                    "input_conservative_cache_write"
                ],
                "output": prereg["pricing_usd_per_million_tokens"]["openai"]["output"],
            },
        )
        try:
            if arb_response.status != "completed":
                raise S139Failure("S139 arbitration incomplete; no retry authorised")
            arb_judgement = s138.parse(raw_arb, "S139 arbitration")
            s138.validate_judgement(
                arb_judgement, arb_packet, question_ids=disagreements
            )
        except Exception as exc:
            receipts._write(
                root / prereg["execution"]["arbitration"],
                s138.failure_record(
                    provider="openai",
                    model=arb_cfg["model"],
                    response=arb_response,
                    packet=arb_packet,
                    raw_output=raw_arb,
                    failure=str(exc),
                    usage=arb_usage,
                    cost=arb_cost,
                ),
            )
            raise
        arbitration_receipt = s138.response_record(
            provider="openai",
            model=arb_cfg["model"],
            response=arb_response,
            packet=arb_packet,
            judgement=arb_judgement,
            usage=arb_usage,
            cost=arb_cost,
        )
        receipts._write(root / prereg["execution"]["arbitration"], arbitration_receipt)

    s138_prereg = files.load_yaml(root / prereg["frozen_inputs"]["s138_prereg"]["path"])
    s135 = files.load_json(root / s138_prereg["frozen_inputs"]["s135_seed"]["path"])
    result = s138.aggregate(
        s138_prereg,
        packet,
        mapping,
        s135,
        sol,
        fable_combined,
        arbitration_receipt,
    )
    known_total = (
        prereg["budget"]["known_s138_cost_before_s139_usd"]
        + q3_receipt["conservative_cost_usd"]
        + (arbitration_receipt["conservative_cost_usd"] if arbitration_receipt else 0)
    )
    reserved_total = known_total + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
    result["instrument"] = "s139_schema_hardened_completion_v1"
    result["checks"]["actual_plus_unknown_reserve_below_internal_ceiling"] = (
        reserved_total < prereg["budget"]["s138_internal_ceiling_usd"]
    )
    result["status"] = "GO" if all(result["checks"].values()) else "NO_GO"
    result["cost"] = {
        "known_paid_model_responses": 5 + (1 if arbitration_receipt else 0),
        "known_actual_usd": round(known_total, 8),
        "failed_520_unknown_cost_reserve_usd": prereg["budget"][
            "failed_520_unknown_cost_reserve_usd"
        ],
        "known_plus_unknown_reserve_usd": round(reserved_total, 8),
        "combined_with_s137_reserved_usd": round(
            reserved_total + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
        ),
    }
    result["decision"] = (
        "GO_TO_CHUNKS_V3_SHADOW_PROMOTION_DECISION"
        if result["status"] == "GO"
        else "NO_GO_KEEP_CHUNKS_V3_OUT"
    )
    receipts._write(root / prereg["execution"]["aggregate"], result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--confirm-paid", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid:
        raise S139Failure("S139 execution requires --confirm-paid")
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    result = execute(
        files.load_yaml(prereg_path),
        files.load_yaml(permit_path),
        args.env_file.resolve(),
    )
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
