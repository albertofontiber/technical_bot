#!/usr/bin/env python3
"""Run the final question-atomic Fable recovery for S137."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as base
from scripts import s137_blinded_chunks_semantic_adjudication as v1
from scripts import s137_resume_fable_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s137_fable_atomic_recovery_prereg_v3.yaml"
DEFAULT_PERMIT = ROOT / "evals/s137_fable_atomic_recovery_execution_permit_v3.yaml"


class AtomicFailure(RuntimeError):
    pass


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    specs = {"design": prereg["design"], **prereg["frozen_inputs"]}
    for name, spec in specs.items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise AtomicFailure(f"S137 v3 dependency drift: {name}")
    packet = base.load_json(root / prereg["frozen_inputs"]["public_packet"]["path"])
    mapping = base.load_json(root / prereg["frozen_inputs"]["private_mapping"]["path"])
    sol = base.load_json(root / prereg["frozen_inputs"]["valid_sol_response"]["path"])
    invalid = base.load_json(root / prereg["frozen_inputs"]["invalid_fable_v2"]["path"])
    if invalid.get("status") != "INVALID_NO_VALID_JUDGEMENT":
        raise AtomicFailure("S137 v3 invalid-v2 trigger drift")
    expected = [row["question_id"] for row in prereg["atomic_questions"]]
    observed = [row["question_id"] for row in packet["questions"]]
    if observed != expected:
        raise AtomicFailure("S137 v3 atomic question order drift")
    if packet["manifests"]["questions_sha256"] != prereg["invariants"]["packet_questions_sha256"]:
        raise AtomicFailure("S137 v3 packet manifest drift")
    if mapping["packet_questions_sha256"] != packet["manifests"]["questions_sha256"]:
        raise AtomicFailure("S137 v3 mapping mismatch")
    v1.assert_public_packet_blind(packet)
    v1.validate_judgement(sol["judgement"], packet)


def cumulative_worst_case(prereg: dict[str, Any], counted_inputs: list[int]) -> float:
    if len(counted_inputs) != len(prereg["atomic_questions"]):
        raise AtomicFailure("S137 v3 token-count cardinality mismatch")
    prices = prereg["pricing_usd_per_million_tokens"]
    model = prereg["model"]
    arbitration = prereg["optional_arbitration"]
    atomic = (
        sum(counted_inputs) * prices["anthropic"]["input"]
        + len(counted_inputs)
        * model["max_output_tokens_per_question"]
        * prices["anthropic"]["output"]
    ) / 1_000_000
    reserved_arbitration = (
        arbitration["max_counted_input_tokens"]
        * prices["openai"]["input_conservative_cache_write"]
        + arbitration["max_output_tokens"] * prices["openai"]["output"]
    ) / 1_000_000
    return round(
        prereg["budget"]["cumulative_prior_usd"] + atomic + reserved_arbitration,
        8,
    )


def validate_permit(prereg: dict[str, Any], permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_FABLE_ATOMIC_FINAL":
        raise AtomicFailure("S137 v3 execution permit is not GO")
    for name in ("preregistration", "runner", "tests"):
        spec = permit[name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise AtomicFailure(f"S137 v3 permitted artifact drift: {name}")
    if (
        permit["cumulative_external_usd_ceiling"]
        != prereg["budget"]["atomic_internal_cumulative_ceiling_usd"]
    ):
        raise AtomicFailure("S137 v3 permit ceiling drift")


def subset_packet(packet: dict[str, Any], question_id: str) -> dict[str, Any]:
    subset = v1._subset_packet(packet, {question_id})
    if len(subset["questions"]) != 1:
        raise AtomicFailure(f"S137 v3 missing atomic question: {question_id}")
    return subset


def atomic_response(
    client: Any, prereg: dict[str, Any], packet: dict[str, Any]
) -> tuple[Any, str]:
    model = prereg["model"]
    response = client.messages.create(
        model=model["model"],
        max_tokens=model["max_output_tokens_per_question"],
        system=v1.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": v1.user_prompt(packet)}],
        thinking={"type": model["thinking"]},
        output_config=v1._anthropic_output_config(model["effort"]),
    )
    texts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]
    return response, "".join(texts)


def persist_atomic(
    path: Path,
    prereg: dict[str, Any],
    packet: dict[str, Any],
    question_id: str,
    response: Any,
    text: str,
) -> dict[str, Any]:
    usage = response.usage.model_dump(mode="json")
    cost = v1.anthropic_cost(usage, prereg["pricing_usd_per_million_tokens"]["anthropic"])
    base_record = {
        "instrument": "s137_fable_atomic_response_v3",
        "provider": "anthropic",
        "model": prereg["model"]["model"],
        "response_id": response.id,
        "created_at": v1.utc_now(),
        "question_id": question_id,
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "stop_reason": response.stop_reason,
        "usage": usage,
        "conservative_cost_usd": cost,
    }
    if response.stop_reason == "max_tokens":
        record = {
            **base_record,
            "status": "TRUNCATED_NO_VALID_JUDGEMENT",
            "raw_partial_text": text,
        }
        v1._write(path, record)
        raise AtomicFailure(f"atomic Fable truncation; no retry authorised: {question_id}")
    try:
        judgement = v1._parse_json(text, f"atomic Fable {question_id}")
        v1.validate_judgement(judgement, packet, question_ids={question_id})
    except Exception:
        record = {
            **base_record,
            "status": "INVALID_NO_VALID_JUDGEMENT",
            "raw_text": text,
        }
        v1._write(path, record)
        raise
    record = {**base_record, "status": "VALIDATED", "judgement": judgement}
    v1._write(path, record)
    return record


def combine_atomic(
    prereg: dict[str, Any], packet: dict[str, Any], receipts: list[dict[str, Any]]
) -> dict[str, Any]:
    judgements = []
    for receipt in receipts:
        judgements.extend(receipt["judgement"]["judgements"])
    combined_judgement = {"judgements": judgements}
    v1.validate_judgement(combined_judgement, packet)
    usage = {
        "input_tokens": sum(row["usage"]["input_tokens"] for row in receipts),
        "output_tokens": sum(row["usage"]["output_tokens"] for row in receipts),
        "atomic_response_ids": [row["response_id"] for row in receipts],
    }
    return {
        "instrument": "s137_fable_atomic_combined_v3",
        "status": "VALIDATED",
        "provider": "anthropic",
        "model": prereg["model"]["model"],
        "created_at": v1.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": usage,
        "conservative_cost_usd": round(
            sum(row["conservative_cost_usd"] for row in receipts), 8
        ),
        "judgement": combined_judgement,
    }


def execute(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_prereg(prereg, root=root)
    validate_permit(prereg, permit, root=root)
    packet = base.load_json(root / prereg["frozen_inputs"]["public_packet"]["path"])
    mapping = base.load_json(root / prereg["frozen_inputs"]["private_mapping"]["path"])
    sol = base.load_json(root / prereg["frozen_inputs"]["valid_sol_response"]["path"])

    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    secrets = dotenv_values(env_file)
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not anthropic_key or not openai_key:
        raise AtomicFailure("provider API key missing")
    anthropic_client = Anthropic(api_key=anthropic_key)
    model = prereg["model"]
    subsets = [subset_packet(packet, row["question_id"]) for row in prereg["atomic_questions"]]
    counted_inputs = []
    for subset in subsets:
        count = anthropic_client.messages.count_tokens(
            model=model["model"],
            system=v1.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": v1.user_prompt(subset)}],
            thinking={"type": model["thinking"]},
            output_config=v1._anthropic_output_config(model["effort"]),
        ).input_tokens
        counted_inputs.append(count)
    if any(count > model["max_counted_input_tokens_per_question"] for count in counted_inputs):
        raise AtomicFailure("S137 v3 atomic input exceeds per-question cap")
    if sum(counted_inputs) > model["max_counted_input_tokens_total"]:
        raise AtomicFailure("S137 v3 atomic input exceeds total cap")
    worst = cumulative_worst_case(prereg, counted_inputs)
    ceiling = prereg["budget"]["atomic_internal_cumulative_ceiling_usd"]
    preflight = {
        "instrument": "s137_paid_preflight_v3",
        "status": "GO" if worst < ceiling else "NO_GO",
        "created_at": v1.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "fable_atomic_counted_input_tokens": counted_inputs,
        "fable_atomic_counted_input_tokens_total": sum(counted_inputs),
        "cumulative_worst_case_usd_including_all_prior_attempts_and_arbitration": worst,
        "internal_ceiling_usd": ceiling,
        "user_ceiling_usd": prereg["budget"]["user_authorized_ceiling_usd"],
    }
    v1._write(root / prereg["execution"]["paid_preflight"], preflight)
    if worst >= ceiling:
        raise AtomicFailure("S137 v3 cumulative worst case exceeds ceiling")

    receipts = []
    for row, subset in zip(prereg["atomic_questions"], subsets, strict=True):
        response, text = atomic_response(anthropic_client, prereg, subset)
        receipt = persist_atomic(
            root / row["output"],
            prereg,
            subset,
            row["question_id"],
            response,
            text,
        )
        receipts.append(receipt)
    fable = combine_atomic(prereg, packet, receipts)
    v1._write(root / prereg["execution"]["combined_fable_response"], fable)

    prior_non_sol = (
        prereg["budget"]["truncated_fable_v1_upper_bound_usd"]
        + prereg["budget"]["invalid_fable_v2_actual_usd"]
    )
    cumulative_so_far = (
        sol["conservative_cost_usd"]
        + prior_non_sol
        + fable["conservative_cost_usd"]
    )
    arbitration = v2._persist_arbitration(
        OpenAI(api_key=openai_key),
        prereg,
        packet,
        mapping,
        sol,
        fable,
        cumulative_so_far,
    )
    aggregate = v1.build_aggregate(packet, mapping, sol, fable, arbitration)
    current_calls_cost = aggregate["cost"]["conservative_actual_usd"]
    cumulative = round(current_calls_cost + prior_non_sol, 8)
    aggregate["instrument"] = "s137_blinded_chunks_semantic_adjudication_v3"
    aggregate["claim"] = "semantic_adjudication_with_final_question_atomic_fable_transport"
    aggregate["cost"].update(
        {
            "truncated_fable_v1_upper_bound_usd": prereg["budget"]["truncated_fable_v1_upper_bound_usd"],
            "invalid_fable_v2_actual_usd": prereg["budget"]["invalid_fable_v2_actual_usd"],
            "cumulative_conservative_usd": cumulative,
        }
    )
    aggregate["checks"]["actual_cost_below_internal_ceiling"] = cumulative < ceiling
    go = all(aggregate["checks"].values())
    aggregate["status"] = "GO" if go else "NO_GO"
    aggregate["decision"] = (
        "GO_TO_RECONCILE_S135_PROMOTION_GATE"
        if go
        else "NO_GO_KEEP_CHUNKS_V3_OUT_OF_PRODUCTION"
    )
    v1._write(root / prereg["execution"]["aggregate"], aggregate)
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--confirm-paid-atomic", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_atomic:
        raise AtomicFailure("paid atomic execution requires --confirm-paid-atomic")
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    result = execute(
        base.load_yaml(prereg_path),
        base.load_yaml(permit_path),
        args.env_file.resolve(),
    )
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
