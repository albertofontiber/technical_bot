#!/usr/bin/env python3
"""Finalize S137 with the already-triggered, single Sol arbitration."""
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s137_arbitration_resume_prereg_v31.yaml"
DEFAULT_PERMIT = ROOT / "evals/s137_arbitration_resume_execution_permit_v31.yaml"


class FinalizeFailure(RuntimeError):
    pass


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], set[str]
]:
    specs = {"design": prereg["design"], **prereg["frozen_inputs"]}
    for name, spec in specs.items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise FinalizeFailure(f"S137 v3.1 dependency drift: {name}")
    packet = base.load_json(root / prereg["frozen_inputs"]["public_packet"]["path"])
    mapping = base.load_json(root / prereg["frozen_inputs"]["private_mapping"]["path"])
    sol = base.load_json(root / prereg["frozen_inputs"]["valid_sol_response"]["path"])
    fable = base.load_json(root / prereg["frozen_inputs"]["fable_combined"]["path"])
    if packet["manifests"]["questions_sha256"] != prereg["invariants"]["packet_questions_sha256"]:
        raise FinalizeFailure("S137 v3.1 packet manifest drift")
    v1.assert_public_packet_blind(packet)
    v1.validate_judgement(sol["judgement"], packet)
    v1.validate_judgement(fable["judgement"], packet)
    if sol.get("status") != "VALIDATED" or fable.get("status") != "VALIDATED":
        raise FinalizeFailure("S137 v3.1 requires two validated judge inputs")
    sol_terminal = v1.terminal_decisions(sol["judgement"], mapping)
    fable_terminal = v1.terminal_decisions(fable["judgement"], mapping)
    disagreements = {
        qid for qid in sol_terminal if sol_terminal[qid] != fable_terminal[qid]
    }
    if not disagreements:
        raise FinalizeFailure("S137 v3.1 arbitration trigger is no longer present")
    return packet, mapping, sol, fable, disagreements


def worst_case(prereg: dict[str, Any], input_tokens: int) -> float:
    pricing = prereg["pricing_usd_per_million_tokens"]["openai"]
    cfg = prereg["arbitration"]
    arbitration = (
        input_tokens * pricing["input_conservative_cache_write"]
        + cfg["max_output_tokens"] * pricing["output"]
    ) / 1_000_000
    return round(prereg["budget"]["cumulative_before_arbitration_usd"] + arbitration, 8)


def validate_permit(prereg: dict[str, Any], permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_SOL_ARBITRATION_ONCE":
        raise FinalizeFailure("S137 v3.1 execution permit is not GO")
    for name in ("preregistration", "runner", "tests"):
        spec = permit[name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise FinalizeFailure(f"S137 v3.1 permitted artifact drift: {name}")
    if (
        permit["cumulative_external_usd_ceiling"]
        != prereg["budget"]["cumulative_internal_ceiling_usd"]
    ):
        raise FinalizeFailure("S137 v3.1 permit ceiling drift")


def persist_arbitration(
    path: Path,
    prereg: dict[str, Any],
    subset: dict[str, Any],
    disagreements: set[str],
    response: Any,
) -> dict[str, Any]:
    usage = response.usage.model_dump(mode="json")
    prices = prereg["pricing_usd_per_million_tokens"]["openai"]
    cost = v1.conservative_openai_cost(
        usage,
        {
            "cache_write": prices["input_conservative_cache_write"],
            "output": prices["output"],
        },
    )
    base_record = {
        "instrument": "s137_sol_arbitration_response_v31",
        "provider": "openai",
        "model": prereg["arbitration"]["model"],
        "response_id": response.id,
        "created_at": v1.utc_now(),
        "packet_questions_sha256": subset["manifests"]["questions_sha256"],
        "question_ids": sorted(disagreements),
        "response_status": response.status,
        "usage": usage,
        "conservative_cost_usd": cost,
    }
    text = response.output_text
    if response.status != "completed":
        record = {
            **base_record,
            "status": "INCOMPLETE_NO_VALID_JUDGEMENT",
            "incomplete_details": (
                response.incomplete_details.model_dump(mode="json")
                if response.incomplete_details
                else None
            ),
            "raw_partial_text": text,
        }
        v1._write(path, record)
        raise FinalizeFailure("S137 v3.1 arbitration incomplete; no retry authorised")
    try:
        judgement = v1._parse_json(text, "S137 v3.1 arbitration")
        v1.validate_judgement(judgement, subset, question_ids=disagreements)
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


def execute(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    packet, mapping, sol, fable, disagreements = validate_prereg(prereg, root=root)
    validate_permit(prereg, permit, root=root)
    subset = v1._subset_packet(packet, disagreements)
    prompt = v1.arbitration_prompt(
        subset,
        v1._subset_judgement(sol["judgement"], disagreements),
        v1._subset_judgement(fable["judgement"], disagreements),
    )

    from dotenv import dotenv_values
    from openai import OpenAI

    secrets = dotenv_values(env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not openai_key:
        raise FinalizeFailure("OpenAI API key missing")
    client = OpenAI(api_key=openai_key)
    cfg = prereg["arbitration"]
    counted = client.responses.input_tokens.count(
        model=cfg["model"],
        reasoning={"effort": cfg["reasoning_effort"]},
        instructions=v1.SYSTEM_PROMPT,
        input=prompt,
        text=v1._openai_format(),
    ).input_tokens
    if counted > cfg["max_counted_input_tokens"]:
        raise FinalizeFailure("S137 v3.1 arbitration input exceeds cap")
    cumulative_worst = worst_case(prereg, counted)
    ceiling = prereg["budget"]["cumulative_internal_ceiling_usd"]
    preflight = {
        "instrument": "s137_paid_preflight_v31",
        "status": "GO" if cumulative_worst < ceiling else "NO_GO",
        "created_at": v1.utc_now(),
        "disagreement_question_ids": sorted(disagreements),
        "arbitration_counted_input_tokens": counted,
        "cumulative_worst_case_usd": cumulative_worst,
        "internal_ceiling_usd": ceiling,
        "user_ceiling_usd": prereg["budget"]["user_authorized_ceiling_usd"],
    }
    v1._write(root / prereg["execution"]["paid_preflight"], preflight)
    if cumulative_worst >= ceiling:
        raise FinalizeFailure("S137 v3.1 cumulative worst case exceeds ceiling")

    response = client.responses.create(
        model=cfg["model"],
        reasoning={"effort": cfg["reasoning_effort"]},
        instructions=v1.SYSTEM_PROMPT,
        input=prompt,
        text=v1._openai_format(),
        max_output_tokens=cfg["max_output_tokens"],
        store=False,
    )
    arbitration = persist_arbitration(
        root / prereg["execution"]["arbitration_response"],
        prereg,
        subset,
        disagreements,
        response,
    )
    aggregate = v1.build_aggregate(packet, mapping, sol, fable, arbitration)
    prior_non_current = (
        prereg["budget"]["truncated_fable_v1_upper_bound_usd"]
        + prereg["budget"]["invalid_fable_v2_actual_usd"]
    )
    cumulative = round(
        aggregate["cost"]["conservative_actual_usd"] + prior_non_current, 8
    )
    aggregate["instrument"] = "s137_blinded_chunks_semantic_adjudication_v31"
    aggregate["claim"] = "final_blinded_semantic_adjudication_after_versioned_transport_recovery"
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
    parser.add_argument("--confirm-paid-arbitration", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_arbitration:
        raise FinalizeFailure("paid arbitration requires --confirm-paid-arbitration")
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
