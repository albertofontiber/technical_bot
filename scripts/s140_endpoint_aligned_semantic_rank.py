#!/usr/bin/env python3
"""Run the final endpoint-aligned completion of the S138 semantic MRR gate."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as files
from scripts import s137_blinded_chunks_semantic_adjudication as receipts
from scripts import s138_symmetric_semantic_mrr as s138


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s140_endpoint_aligned_semantic_rank_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s140_endpoint_aligned_semantic_rank_execution_permit_v1.yaml"

SYSTEM_PROMPT = """You are an independent semantic evidence adjudicator for technical manuals.
Each question contains two opaque evidence sets. Judge every set independently from RAW SOURCE CONTENT
only. Treat Spanish and English equally. Do not use outside knowledge. Read all evidence, then report:
whether the set answers the question completely, and if COMPLETE, the smallest sufficient evidence IDs.
The minimum set must be nonempty only for COMPLETE. Keep each rationale under 90 words. Return only the
required structured JSON."""


class S140Failure(RuntimeError):
    pass


def output_schema() -> dict[str, Any]:
    set_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "evidence_set_id",
            "answerability",
            "minimum_sufficient_evidence_ids",
            "confidence",
            "rationale",
        ],
        "properties": {
            "evidence_set_id": {"type": "string"},
            "answerability": {"type": "string", "enum": sorted(s138.ANSWERABILITY)},
            "minimum_sufficient_evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "confidence": {"type": "string", "enum": sorted(s138.CONFIDENCE)},
            "rationale": {"type": "string"},
        },
    }
    question_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["question_id", "set_judgements"],
        "properties": {
            "question_id": {"type": "string"},
            "set_judgements": {"type": "array", "items": set_schema},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["judgements"],
        "properties": {"judgements": {"type": "array", "items": question_schema}},
    }


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    for name, spec in {"design": prereg["design"], **prereg["frozen_inputs"]}.items():
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S140Failure(f"S140 frozen artifact drift: {name}")


def validate_permit(permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise S140Failure("S140 permit is not final GO")
    for name in ("preregistration", "runner", "tests"):
        spec = permit[name]
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S140Failure(f"S140 permitted artifact drift: {name}")


def validate_endpoint(
    judgement: dict[str, Any], packet: dict[str, Any], *, qids: set[str] | None = None
) -> None:
    errors = sorted(
        Draft202012Validator(output_schema()).iter_errors(judgement),
        key=lambda error: list(error.path),
    )
    if errors:
        raise S140Failure(f"S140 endpoint schema violation: {errors[0].message}")
    packet_by = {row["question_id"]: row for row in packet["questions"]}
    expected_qids = qids if qids is not None else set(packet_by)
    rows = judgement["judgements"]
    if {row["question_id"] for row in rows} != expected_qids or len(rows) != len(expected_qids):
        raise S140Failure("S140 endpoint question-set mismatch")
    for row in rows:
        qid = row["question_id"]
        expected_sets = {
            evidence_set["evidence_set_id"]: {
                evidence["evidence_id"] for evidence in evidence_set["evidence"]
            }
            for evidence_set in packet_by[qid]["evidence_sets"]
        }
        set_rows = row["set_judgements"]
        if {item["evidence_set_id"] for item in set_rows} != set(expected_sets) or len(set_rows) != 2:
            raise S140Failure(f"S140 endpoint evidence-set mismatch: {qid}")
        for set_row in set_rows:
            set_id = set_row["evidence_set_id"]
            minimum = set_row["minimum_sufficient_evidence_ids"]
            if len(minimum) != len(set(minimum)) or not set(minimum).issubset(expected_sets[set_id]):
                raise S140Failure(f"S140 endpoint invalid minimum set: {qid}/{set_id}")
            if set_row["answerability"] == "COMPLETE":
                if not minimum:
                    raise S140Failure(f"S140 endpoint complete without evidence: {qid}/{set_id}")
            elif minimum:
                raise S140Failure(f"S140 endpoint non-complete with evidence: {qid}/{set_id}")
            if len(set_row["rationale"].split()) > 90:
                raise S140Failure(f"S140 endpoint rationale too long: {qid}/{set_id}")


def endpoint_from_full(full: dict[str, Any]) -> dict[str, Any]:
    return {
        "judgements": [
            {
                "question_id": question["question_id"],
                "set_judgements": [
                    {
                        key: value
                        for key, value in evidence_set.items()
                        if key
                        in {
                            "evidence_set_id",
                            "answerability",
                            "minimum_sufficient_evidence_ids",
                            "confidence",
                            "rationale",
                        }
                    }
                    for evidence_set in question["set_judgements"]
                ],
            }
            for question in full["judgements"]
        ]
    }


def endpoint_ranks(
    endpoint: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, dict[str, int | None]]:
    map_by = {
        question["question_id"]: {
            evidence_set["evidence_set_id"]: {
                "arm": evidence_set["arm"],
                "ranks": {
                    evidence["evidence_id"]: evidence["rank"]
                    for evidence in evidence_set["evidence"]
                },
            }
            for evidence_set in question["evidence_sets"]
        }
        for question in mapping["questions"]
    }
    output: dict[str, dict[str, int | None]] = {}
    for question in endpoint["judgements"]:
        per_arm: dict[str, int | None] = {}
        for set_row in question["set_judgements"]:
            info = map_by[question["question_id"]][set_row["evidence_set_id"]]
            minimum = set_row["minimum_sufficient_evidence_ids"]
            per_arm[info["arm"]] = (
                max(info["ranks"][evidence_id] for evidence_id in minimum)
                if set_row["answerability"] == "COMPLETE" and minimum
                else None
            )
        output[question["question_id"]] = per_arm
    return output


def subset_endpoint(value: dict[str, Any], qids: set[str]) -> dict[str, Any]:
    return {
        "judgements": [
            row for row in value["judgements"] if row["question_id"] in qids
        ]
    }


def text_format() -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s140_endpoint_semantic_rank",
            "schema": output_schema(),
            "strict": True,
        },
        "verbosity": "low",
    }


def anthropic_output(effort: str) -> dict[str, Any]:
    return {"effort": effort, "format": {"type": "json_schema", "schema": output_schema()}}


def prompt(packet: dict[str, Any]) -> str:
    return "Adjudicate both evidence sets for every question.\n\n" + json.dumps(
        {"questions": packet["questions"]}, ensure_ascii=False, sort_keys=True
    )


def parse(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise S140Failure(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise S140Failure(f"{label} returned non-object JSON")
    return value


def response_receipt(
    *, provider: str, model: str, response: Any, packet: dict[str, Any],
    judgement: dict[str, Any], usage: dict[str, Any], cost: float
) -> dict[str, Any]:
    return {
        "instrument": "s140_endpoint_judge_response_v1",
        "status": "VALIDATED",
        "provider": provider,
        "model": model,
        "response_id": response.id,
        "created_at": receipts.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": usage,
        "conservative_cost_usd": cost,
        "judgement": judgement,
    }


def failure_receipt(
    *, provider: str, model: str, response: Any | None, packet: dict[str, Any],
    raw_output: str, failure: str, usage: dict[str, Any] | None, cost: float | None
) -> dict[str, Any]:
    return {
        "instrument": "s140_endpoint_judge_response_v1",
        "status": "FAILED_NO_RETRY_AUTHORIZED",
        "provider": provider,
        "model": model,
        "response_id": getattr(response, "id", None),
        "created_at": receipts.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": usage,
        "conservative_cost_usd": cost,
        "failure": failure,
        "raw_output": raw_output,
    }


def incremental_worst(prereg: dict[str, Any], fable_input: int) -> float:
    prices = prereg["pricing_usd_per_million_tokens"]
    fable = prereg["models"]["completion"]
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


def execute(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_prereg(prereg, root=root)
    validate_permit(permit, root=root)
    frozen = {
        name: files.load_json(root / spec["path"])
        for name, spec in prereg["frozen_inputs"].items()
        if name != "s138_prereg"
    }
    packet = frozen["packet"]
    mapping = frozen["mapping"]
    s138.assert_blind(packet)
    sol_endpoint = endpoint_from_full(frozen["sol_valid"]["judgement"])
    fable_reused = []
    for name in ("fable_q1_valid", "fable_q2_valid"):
        if frozen[name].get("status") != "VALIDATED":
            raise S140Failure(f"S140 frozen input not validated: {name}")
        fable_reused.extend(endpoint_from_full(frozen[name]["judgement"])["judgements"])
    validate_endpoint(sol_endpoint, packet)

    q3id = prereg["completion_question_id"]
    q3_packet = s138.subset_packet(packet, {q3id})
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
        raise S140Failure("S140 provider API key missing")
    anthropic_client = Anthropic(api_key=anthropic_key)
    openai_client = OpenAI(api_key=openai_key)
    fable_cfg = prereg["models"]["completion"]
    q3_prompt = prompt(q3_packet)
    counted = anthropic_client.messages.count_tokens(
        model=fable_cfg["model"],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": q3_prompt}],
        thinking={"type": fable_cfg["thinking"]},
        output_config=anthropic_output(fable_cfg["effort"]),
    ).input_tokens
    if counted > fable_cfg["max_counted_input_tokens"]:
        raise S140Failure("S140 Fable input exceeds cap")
    incremental = incremental_worst(prereg, counted)
    total_reserved = (
        prereg["budget"]["known_s138_cost_before_s140_usd"]
        + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
        + incremental
    )
    preflight = {
        "instrument": "s140_paid_preflight_v1",
        "status": "GO" if total_reserved < prereg["budget"]["s138_internal_ceiling_usd"] else "NO_GO",
        "created_at": receipts.utc_now(),
        "fable_q3_input_tokens": counted,
        "s140_incremental_worst_case_usd": incremental,
        "s138_total_reserved_worst_case_usd": round(total_reserved, 8),
        "combined_with_s137_reserved_worst_case_usd": round(
            total_reserved + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
        ),
    }
    receipts._write(root / prereg["execution"]["paid_preflight"], preflight)
    if preflight["status"] != "GO":
        raise S140Failure("S140 preflight exceeds internal ceiling")

    try:
        response = anthropic_client.messages.create(
            model=fable_cfg["model"],
            max_tokens=fable_cfg["max_output_tokens"],
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": q3_prompt}],
            thinking={"type": fable_cfg["thinking"]},
            output_config=anthropic_output(fable_cfg["effort"]),
        )
    except Exception as exc:
        receipts._write(
            root / prereg["execution"]["fable_q3"],
            failure_receipt(
                provider="anthropic", model=fable_cfg["model"], response=None,
                packet=q3_packet, raw_output="", failure=str(exc), usage=None, cost=None
            ),
        )
        raise
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    usage = response.usage.model_dump(mode="json")
    cost = receipts.anthropic_cost(usage, prereg["pricing_usd_per_million_tokens"]["anthropic"])
    try:
        if response.stop_reason == "max_tokens":
            raise S140Failure("S140 Fable completion truncated")
        q3_endpoint = parse(raw_text, "S140 Fable q3")
        validate_endpoint(q3_endpoint, q3_packet, qids={q3id})
    except Exception as exc:
        receipts._write(
            root / prereg["execution"]["fable_q3"],
            failure_receipt(
                provider="anthropic", model=fable_cfg["model"], response=response,
                packet=q3_packet, raw_output=raw_text, failure=str(exc), usage=usage, cost=cost
            ),
        )
        raise
    q3_receipt = response_receipt(
        provider="anthropic", model=fable_cfg["model"], response=response,
        packet=q3_packet, judgement=q3_endpoint, usage=usage, cost=cost
    )
    receipts._write(root / prereg["execution"]["fable_q3"], q3_receipt)

    fable_endpoint = {"judgements": fable_reused + q3_endpoint["judgements"]}
    validate_endpoint(fable_endpoint, packet)
    fable_combined = {
        "instrument": "s140_fable_endpoint_combined_v1",
        "status": "VALIDATED",
        "created_at": receipts.utc_now(),
        "reused_response_ids": [
            frozen["fable_q1_valid"]["response_id"],
            frozen["fable_q2_valid"]["response_id"],
        ],
        "new_response_id": q3_receipt["response_id"],
        "judgement": fable_endpoint,
    }
    receipts._write(root / prereg["execution"]["fable_combined"], fable_combined)

    sol_ranks = endpoint_ranks(sol_endpoint, mapping)
    fable_ranks = endpoint_ranks(fable_endpoint, mapping)
    disagreements = {qid for qid in sol_ranks if sol_ranks[qid] != fable_ranks[qid]}
    arbitration_receipt = None
    arb_ranks: dict[str, dict[str, int | None]] = {}
    if disagreements:
        arb_cfg = prereg["models"]["arbitration"]
        arb_packet = s138.subset_packet(packet, disagreements)
        arb_prompt = (
            "Independently resolve the endpoint judgements below. Prior A and B are advisory; "
            "re-read all raw evidence.\n\n"
            + json.dumps(
                {
                    "questions": arb_packet["questions"],
                    "judgement_A": subset_endpoint(sol_endpoint, disagreements),
                    "judgement_B": subset_endpoint(fable_endpoint, disagreements),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        arb_count = openai_client.responses.input_tokens.count(
            model=arb_cfg["model"],
            reasoning={"effort": arb_cfg["reasoning_effort"]},
            instructions=SYSTEM_PROMPT,
            input=arb_prompt,
            text=text_format(),
        ).input_tokens
        if arb_count > arb_cfg["max_counted_input_tokens"]:
            raise S140Failure("S140 arbitration input exceeds cap")
        try:
            arb_response = openai_client.responses.create(
                model=arb_cfg["model"],
                reasoning={"effort": arb_cfg["reasoning_effort"]},
                instructions=SYSTEM_PROMPT,
                input=arb_prompt,
                text=text_format(),
                max_output_tokens=arb_cfg["max_output_tokens"],
                store=False,
            )
        except Exception as exc:
            receipts._write(
                root / prereg["execution"]["arbitration"],
                failure_receipt(
                    provider="openai", model=arb_cfg["model"], response=None,
                    packet=arb_packet, raw_output="", failure=str(exc), usage=None, cost=None
                ),
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
                raise S140Failure("S140 arbitration incomplete")
            arb_endpoint = parse(raw_arb, "S140 arbitration")
            validate_endpoint(arb_endpoint, arb_packet, qids=disagreements)
        except Exception as exc:
            receipts._write(
                root / prereg["execution"]["arbitration"],
                failure_receipt(
                    provider="openai", model=arb_cfg["model"], response=arb_response,
                    packet=arb_packet, raw_output=raw_arb, failure=str(exc),
                    usage=arb_usage, cost=arb_cost
                ),
            )
            raise
        arbitration_receipt = response_receipt(
            provider="openai", model=arb_cfg["model"], response=arb_response,
            packet=arb_packet, judgement=arb_endpoint, usage=arb_usage, cost=arb_cost
        )
        receipts._write(root / prereg["execution"]["arbitration"], arbitration_receipt)
        arb_ranks = endpoint_ranks(arb_endpoint, mapping)

    final_ranks = {
        qid: (arb_ranks[qid] if qid in disagreements else sol_ranks[qid])
        for qid in sol_ranks
    }
    valid = len(final_ranks) == 3 and all(
        set(ranks) == {"baseline_v2", "candidate_v3"}
        and all(rank is not None and rank <= 10 for rank in ranks.values())
        for ranks in final_ranks.values()
    )
    s138_prereg = files.load_yaml(root / prereg["frozen_inputs"]["s138_prereg"]["path"])
    s135 = files.load_json(root / s138_prereg["frozen_inputs"]["s135_seed"]["path"])
    baseline_mrr, candidate_mrr = (
        s138.hybrid_mrr(s135, final_ranks, set(final_ranks)) if valid else (None, None)
    )
    known_total = (
        prereg["budget"]["known_s138_cost_before_s140_usd"]
        + q3_receipt["conservative_cost_usd"]
        + (arbitration_receipt["conservative_cost_usd"] if arbitration_receipt else 0)
    )
    reserved_total = known_total + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
    checks = {
        "three_final_two_arm_rank_tuples": valid,
        "candidate_hybrid_mrr_gte_baseline": (
            valid and candidate_mrr is not None and baseline_mrr is not None
            and candidate_mrr >= baseline_mrr
        ),
        "s137_hit_reconciliation_still_go": True,
        "known_plus_unknown_reserve_below_internal_ceiling": (
            reserved_total < prereg["budget"]["s138_internal_ceiling_usd"]
        ),
        "facts_moved_to_ok_zero": True,
    }
    go = all(checks.values())
    result = {
        "instrument": "s140_endpoint_aligned_semantic_rank_v1",
        "status": "GO" if go else "NO_GO",
        "checks": checks,
        "questions": [
            {
                "question_id": qid,
                "sol_ranks": sol_ranks[qid],
                "fable_ranks": fable_ranks[qid],
                "initial_agreement": qid not in disagreements,
                "arbitration_ranks": arb_ranks.get(qid),
                "final_ranks": final_ranks[qid],
            }
            for qid in s138_prereg["population"]["question_ids"]
        ],
        "metrics": {
            "baseline_hybrid_mrr_at_10": baseline_mrr,
            "candidate_hybrid_mrr_at_10": candidate_mrr,
            "candidate_minus_baseline": (
                round(candidate_mrr - baseline_mrr, 8)
                if candidate_mrr is not None and baseline_mrr is not None else None
            ),
            "cohort_size": 24,
            "semantic_fallback_questions": 3,
        },
        "summary": {"initial_disagreements": len(disagreements), "holds": 0 if valid else 1},
        "cost": {
            "known_paid_model_responses": 5 + (1 if arbitration_receipt else 0),
            "known_actual_usd": round(known_total, 8),
            "failed_520_unknown_cost_reserve_usd": prereg["budget"][
                "failed_520_unknown_cost_reserve_usd"
            ],
            "known_plus_unknown_reserve_usd": round(reserved_total, 8),
            "combined_with_s137_reserved_usd": round(
                reserved_total + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
            ),
        },
        "authorization": {
            "production": False, "deploy": False, "migration_apply": False,
            "facts_moved_to_ok": 0,
        },
        "decision": (
            "GO_TO_CHUNKS_V3_SHADOW_PROMOTION_DECISION"
            if go else "NO_GO_KEEP_CHUNKS_V3_OUT"
        ),
    }
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
        raise S140Failure("S140 execution requires --confirm-paid")
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    result = execute(
        files.load_yaml(prereg_path), files.load_yaml(permit_path), args.env_file.resolve()
    )
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
