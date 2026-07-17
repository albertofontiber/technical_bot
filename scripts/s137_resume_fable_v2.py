#!/usr/bin/env python3
"""Resume S137 after the bounded Fable v1 max-token truncation."""
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
DEFAULT_PREREG = ROOT / "evals/s137_fable_truncation_recovery_prereg_v2.yaml"
DEFAULT_PERMIT = ROOT / "evals/s137_fable_truncation_recovery_execution_permit_v2.yaml"


class RecoveryFailure(RuntimeError):
    pass


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    specs = {"design": prereg["design"], **prereg["frozen_inputs"]}
    for name, spec in specs.items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise RecoveryFailure(f"S137 v2 dependency drift: {name}")
    packet = base.load_json(root / prereg["frozen_inputs"]["public_packet"]["path"])
    mapping = base.load_json(root / prereg["frozen_inputs"]["private_mapping"]["path"])
    sol = base.load_json(root / prereg["frozen_inputs"]["valid_sol_response"]["path"])
    if packet["manifests"]["questions_sha256"] != prereg["invariants"]["packet_questions_sha256"]:
        raise RecoveryFailure("S137 v2 packet manifest drift")
    if len(packet["questions"]) != prereg["invariants"]["expected_question_count"]:
        raise RecoveryFailure("S137 v2 packet question-count drift")
    if mapping["packet_questions_sha256"] != packet["manifests"]["questions_sha256"]:
        raise RecoveryFailure("S137 v2 private mapping mismatch")
    v1.assert_public_packet_blind(packet)
    v1.validate_judgement(sol["judgement"], packet)
    if sol.get("status") != "VALIDATED" or sol.get("provider") != "openai":
        raise RecoveryFailure("S137 v2 Sol reuse input is not validated")
    failed = base.load_yaml(
        root / prereg["frozen_inputs"]["truncated_fable_receipt"]["path"]
    )
    if failed.get("status") != "TRUNCATED_NO_VALID_JUDGEMENT":
        raise RecoveryFailure("S137 v2 missing frozen truncation condition")


def cumulative_worst_case(prereg: dict[str, Any], fable_input_tokens: int) -> float:
    prior = prereg["budget"]
    pricing = prereg["pricing_usd_per_million_tokens"]
    model = prereg["model"]
    arbitration = prereg["optional_arbitration"]
    recovery = (
        fable_input_tokens * pricing["anthropic"]["input"]
        + model["max_output_tokens"] * pricing["anthropic"]["output"]
    ) / 1_000_000
    reserved_arbitration = (
        arbitration["max_counted_input_tokens"]
        * pricing["openai"]["input_conservative_cache_write"]
        + arbitration["max_output_tokens"] * pricing["openai"]["output"]
    ) / 1_000_000
    return round(
        prior["valid_sol_v1_conservative_actual_usd"]
        + prior["truncated_fable_v1_upper_bound_usd"]
        + recovery
        + reserved_arbitration,
        8,
    )


def validate_permit(prereg: dict[str, Any], permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_FABLE_RECOVERY_ONCE":
        raise RecoveryFailure("S137 v2 execution permit is not GO")
    for name in ("preregistration", "runner", "tests"):
        spec = permit[name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise RecoveryFailure(f"S137 v2 permitted artifact drift: {name}")
    if (
        permit["cumulative_external_usd_ceiling"]
        != prereg["budget"]["recovery_internal_cumulative_ceiling_usd"]
    ):
        raise RecoveryFailure("S137 v2 permit ceiling drift")


def _fable_response(
    client: Any, prereg: dict[str, Any], packet: dict[str, Any]
) -> tuple[Any, str]:
    model = prereg["model"]
    response = client.messages.create(
        model=model["model"],
        max_tokens=model["max_output_tokens"],
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


def _persist_fable_receipt(
    path: Path,
    prereg: dict[str, Any],
    packet: dict[str, Any],
    response: Any,
    text: str,
) -> dict[str, Any]:
    usage = response.usage.model_dump(mode="json")
    cost = v1.anthropic_cost(usage, prereg["pricing_usd_per_million_tokens"]["anthropic"])
    base_record = {
        "instrument": "s137_fable_recovery_response_v2",
        "provider": "anthropic",
        "model": prereg["model"]["model"],
        "response_id": response.id,
        "created_at": v1.utc_now(),
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
        raise RecoveryFailure("Fable v2 truncated; receipt persisted; no retry authorised")
    try:
        judgement = v1._parse_json(text, "Fable v2")
        v1.validate_judgement(judgement, packet)
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


def _persist_arbitration(
    client: Any,
    prereg: dict[str, Any],
    packet: dict[str, Any],
    mapping: dict[str, Any],
    sol: dict[str, Any],
    fable: dict[str, Any],
    cumulative_so_far: float,
) -> dict[str, Any] | None:
    sol_terminal = v1.terminal_decisions(sol["judgement"], mapping)
    fable_terminal = v1.terminal_decisions(fable["judgement"], mapping)
    disagreements = {
        qid for qid in sol_terminal if sol_terminal[qid] != fable_terminal[qid]
    }
    if not disagreements:
        return None
    cfg = prereg["optional_arbitration"]
    subset = v1._subset_packet(packet, disagreements)
    prompt = v1.arbitration_prompt(
        subset,
        v1._subset_judgement(sol["judgement"], disagreements),
        v1._subset_judgement(fable["judgement"], disagreements),
    )
    counted = client.responses.input_tokens.count(
        model=cfg["model"],
        reasoning={"effort": cfg["reasoning_effort"]},
        instructions=v1.SYSTEM_PROMPT,
        input=prompt,
        text=v1._openai_format(),
    ).input_tokens
    if counted > cfg["max_counted_input_tokens"]:
        raise RecoveryFailure("S137 v2 arbitration input exceeds cap")
    prices = prereg["pricing_usd_per_million_tokens"]["openai"]
    reserved = (
        counted * prices["input_conservative_cache_write"]
        + cfg["max_output_tokens"] * prices["output"]
    ) / 1_000_000
    ceiling = prereg["budget"]["recovery_internal_cumulative_ceiling_usd"]
    if cumulative_so_far + reserved >= ceiling:
        raise RecoveryFailure("S137 v2 arbitration would exceed cumulative ceiling")
    response, text = v1._openai_call(client, cfg, prompt)
    judgement = v1._parse_json(text, "S137 v2 arbitration")
    v1.validate_judgement(judgement, subset, question_ids=disagreements)
    usage = response.usage.model_dump(mode="json")
    record = v1._response_record(
        provider="openai",
        model=cfg["model"],
        packet=subset,
        response=response,
        judgement=judgement,
        usage=usage,
        cost=v1.conservative_openai_cost(
            usage,
            {
                "cache_write": prices["input_conservative_cache_write"],
                "output": prices["output"],
            },
        ),
    )
    v1._write(ROOT / prereg["execution"]["arbitration_response"], record)
    return record


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
        raise RecoveryFailure("provider API key missing")
    anthropic_client = Anthropic(api_key=anthropic_key)
    model = prereg["model"]
    prompt = v1.user_prompt(packet)
    counted = anthropic_client.messages.count_tokens(
        model=model["model"],
        system=v1.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": model["thinking"]},
        output_config=v1._anthropic_output_config(model["effort"]),
    ).input_tokens
    if counted != model["expected_counted_input_tokens"]:
        raise RecoveryFailure("Fable v2 input changed from frozen v1 count")
    if counted > model["max_counted_input_tokens"]:
        raise RecoveryFailure("Fable v2 input exceeds cap")
    worst = cumulative_worst_case(prereg, counted)
    ceiling = prereg["budget"]["recovery_internal_cumulative_ceiling_usd"]
    preflight = {
        "instrument": "s137_paid_preflight_v2",
        "status": "GO" if worst < ceiling else "NO_GO",
        "created_at": v1.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "fable_counted_input_tokens": counted,
        "cumulative_worst_case_usd_including_prior_attempts_and_arbitration": worst,
        "internal_ceiling_usd": ceiling,
        "user_ceiling_usd": prereg["budget"]["user_authorized_ceiling_usd"],
    }
    v1._write(root / prereg["execution"]["paid_preflight"], preflight)
    if worst >= ceiling:
        raise RecoveryFailure("S137 v2 cumulative worst case exceeds ceiling")

    response, text = _fable_response(anthropic_client, prereg, packet)
    fable = _persist_fable_receipt(
        root / prereg["execution"]["fable_response"],
        prereg,
        packet,
        response,
        text,
    )
    prior_upper = prereg["budget"]["truncated_fable_v1_upper_bound_usd"]
    cumulative_so_far = (
        sol["conservative_cost_usd"] + prior_upper + fable["conservative_cost_usd"]
    )
    arbitration = _persist_arbitration(
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
    cumulative = round(current_calls_cost + prior_upper, 8)
    aggregate["instrument"] = "s137_blinded_chunks_semantic_adjudication_v2"
    aggregate["claim"] = "v1_semantic_adjudication_with_versioned_fable_transport_recovery"
    aggregate["cost"].update(
        {
            "prior_truncated_fable_v1_upper_bound_usd": prior_upper,
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
    parser.add_argument("--confirm-paid-recovery", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_recovery:
        raise RecoveryFailure("paid recovery requires --confirm-paid-recovery")
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
