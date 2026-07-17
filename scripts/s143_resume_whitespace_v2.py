#!/usr/bin/env python3
"""Finish S143 with unique whitespace alignment and no question retries."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s143_agentic_evidence_planner as v1
from scripts.s142_recover_sealed_cohort import exact_whitespace_alignment


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s143_agentic_evidence_planner_prereg_v2.yaml"
DEFAULT_PERMIT = ROOT / "evals/s143_agentic_evidence_planner_execution_permit_v2.yaml"
DEFAULT_OUT = ROOT / "evals/s143_agentic_evidence_planner_v2.json"
DEFAULT_RECEIPTS = ROOT / "evals/s143_agentic_evidence_planner_receipts_v2.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_RESUME":
        raise RuntimeError("S143 v2 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S143 v2 paid execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S143 v2 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S143 v2 permitted artifact drift: {label}")
    return prereg


def aligned_quotes(value: dict[str, Any], source: str, prereg: dict[str, Any]) -> tuple[list[str], int]:
    errors = list(Draft202012Validator(v1.schema()).iter_errors(value))
    if errors:
        raise RuntimeError(f"S143 v2 schema violation: {errors[0].message}")
    limits = prereg["validation"]
    rows = value["quotes"]
    if not (limits["quotes_per_question_min"] <= len(rows) <= limits["quotes_per_question_max"]):
        raise RuntimeError("S143 v2 quote-count violation")
    quotes = []
    repaired = 0
    for row in rows:
        quote = row["exact_quote"]
        if row["fragment_number"] != 1 or len(quote) > limits["quote_max_chars"]:
            raise RuntimeError("S143 v2 quote boundary violation")
        aligned = quote if quote in source else exact_whitespace_alignment(quote, source)
        if aligned is None:
            raise RuntimeError("S143 v2 unalignable quote")
        repaired += int(aligned != quote)
        if aligned not in quotes:
            quotes.append(aligned)
    if not quotes:
        raise RuntimeError("S143 v2 empty deduplicated packet")
    return quotes, repaired


def execute(
    prereg: dict[str, Any], env_file: Path, receipts_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if receipts_path.exists():
        raise RuntimeError("S143 v2 receipt checkpoint exists; retry is forbidden")
    cohort = json.loads((ROOT / prereg["frozen_inputs"]["challenge_cohort"]["path"]).read_text(encoding="utf-8"))
    packet = json.loads((ROOT / prereg["frozen_inputs"]["source_packet"]["path"]).read_text(encoding="utf-8"))
    prior = json.loads((ROOT / prereg["frozen_inputs"]["prior_receipts"]["path"]).read_text(encoding="utf-8"))
    packet_by = {row["item_id"]: row for row in packet["items"]}
    eligible = [row for row in cohort["items"] if row["eligible"]]
    eligible_by = {row["item_id"]: row for row in eligible}
    prior_by = {row["item_id"]: row for row in prior["receipts"]}
    if len(prior_by) != 4 or not set(prior_by).issubset(eligible_by):
        raise RuntimeError("S143 v2 prior receipt population drift")

    validated: dict[str, list[str]] = {}
    whitespace_repairs = 0
    prior_cost = 0.0
    for item_id, receipt in prior_by.items():
        source = packet_by[item_id]["excerpt"]
        quotes, repaired = aligned_quotes(json.loads(receipt["raw_text"]), source, prereg)
        validated[item_id] = quotes
        whitespace_repairs += repaired
        prior_cost += receipt["conservative_cost_usd"]

    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    model = prereg["model"]
    remaining = [row for row in eligible if row["item_id"] not in prior_by]
    if len(remaining) != model["new_calls"]:
        raise RuntimeError("S143 v2 remaining call population drift")
    prompts = []
    counted_total = 0
    for item in remaining:
        source = packet_by[item["item_id"]]["excerpt"]
        prompt = json.dumps(
            {"question": item["question"], "fragments": [{"fragment_number": 1, "content": source}]},
            ensure_ascii=False,
            sort_keys=True,
        )
        counted = client.messages.count_tokens(
            model=model["id"],
            system=v1.SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": v1.schema()}},
        ).input_tokens
        counted_total += counted
        prompts.append((item, source, prompt, counted))
    if counted_total > model["max_new_counted_input_tokens"]:
        raise RuntimeError("S143 v2 counted input exceeds cap")
    budget = prereg["budget"]
    worst_new = (
        counted_total * budget["conservative_input_usd_per_million"]
        + len(prompts) * model["max_output_tokens_per_call"] * budget["conservative_output_usd_per_million"]
    ) / 1_000_000
    if prior_cost + worst_new >= budget["cumulative_internal_ceiling_usd"]:
        raise RuntimeError("S143 v2 cumulative worst-case exceeds cap")

    new_receipts = []
    new_cost = 0.0
    for item, source, prompt, counted in prompts:
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["max_output_tokens_per_call"],
            system=v1.SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": v1.schema()}},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage.model_dump(mode="json")
        cost = (
            usage.get("input_tokens", 0) * budget["conservative_input_usd_per_million"]
            + usage.get("output_tokens", 0) * budget["conservative_output_usd_per_million"]
        ) / 1_000_000
        receipt = {
            "item_id": item["item_id"],
            "response_id": response.id,
            "stop_reason": response.stop_reason,
            "counted_input_tokens": counted,
            "usage": usage,
            "conservative_cost_usd": round(cost, 8),
            "raw_text": text,
            "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        new_receipts.append(receipt)
        receipts_path.write_text(
            json.dumps(
                {
                    "instrument": "s143_agentic_evidence_planner_receipts_v2",
                    "status": "IN_PROGRESS",
                    "model": model["id"],
                    "receipts": new_receipts,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        quotes, repaired = aligned_quotes(json.loads(text), source, prereg)
        validated[item["item_id"]] = quotes
        whitespace_repairs += repaired
        new_cost += cost

    claims_total = claims_covered = quotes_total = useful_quotes = positive = 0
    rows = []
    for item in eligible:
        quotes = validated[item["item_id"]]
        claim_hits = [any(claim["exact_quote"] in quote for quote in quotes) for claim in item["claims"]]
        quote_hits = [any(claim["exact_quote"] in quote for claim in item["claims"]) for quote in quotes]
        claims_total += len(claim_hits)
        claims_covered += sum(claim_hits)
        quotes_total += len(quote_hits)
        useful_quotes += sum(quote_hits)
        positive += int(any(claim_hits))
        rows.append(
            {
                "item_id": item["item_id"],
                "claims": len(claim_hits),
                "claims_covered": sum(claim_hits),
                "quotes": len(quote_hits),
                "useful_quotes": sum(quote_hits),
                "quote_receipts": [
                    {"sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(), "chars": len(quote)}
                    for quote in quotes
                ],
            }
        )
    recall = claims_covered / claims_total
    precision = useful_quotes / quotes_total
    gate = prereg["validation"]
    total_cost = prior_cost + new_cost
    go = (
        recall >= gate["claim_recall_min"]
        and precision >= gate["quote_precision_min"]
        and positive >= gate["positive_questions_min"]
        and total_cost < budget["cumulative_internal_ceiling_usd"]
    )
    body = {
        "instrument": "s143_agentic_evidence_planner_v2",
        "status": "GO_TO_FRESH_INDEPENDENT_IMPLEMENTATION" if go else "NO_GO",
        "transport": {
            "prior_receipts_reused": len(prior_by),
            "new_calls": len(new_receipts),
            "question_retries": 0,
            "unique_whitespace_repairs": whitespace_repairs,
        },
        "result": {
            "eligible_questions": len(eligible),
            "positive_questions": positive,
            "claims_total": claims_total,
            "claims_covered": claims_covered,
            "claim_recall": round(recall, 8),
            "quotes_total": quotes_total,
            "useful_quotes": useful_quotes,
            "quote_precision": round(precision, 8),
        },
        "cost": {
            "prior_conservative_usd": round(prior_cost, 8),
            "new_conservative_usd": round(new_cost, 8),
            "total_conservative_usd": round(total_cost, 8),
            "new_worst_case_preflight_usd": round(worst_new, 8),
            "cumulative_internal_ceiling_usd": budget["cumulative_internal_ceiling_usd"],
        },
        "rows": rows,
        "decision": {
            "fresh_independent_implementation": "GO" if go else "NO_GO",
            "production": "NO_GO",
            "facts_moved_to_ok": 0,
        },
    }
    receipt_packet = {
        "instrument": "s143_agentic_evidence_planner_receipts_v2",
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model["id"],
        "receipts": new_receipts,
    }
    return {**body, "result_sha256": stable_sha(body)}, receipt_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    prereg = validate_authorization(args.prereg, args.permit)
    result, receipts = execute(prereg, args.env_file, args.receipts)
    args.receipts.write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["transport"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
