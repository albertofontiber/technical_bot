#!/usr/bin/env python3
"""Run the bounded S192 Terra direct-writer causal control."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s156_frontier_synthesis_ceiling import build_prompt
from src.rag.omission_correction import invalid_citations, point_covered


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
DEFAULT_PREREG = ROOT / "evals/s192_terra_direct_writer_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s192_terra_direct_writer_execution_permit_v1.yaml"
DEFAULT_RECEIPTS = ROOT / "evals/s192_terra_direct_writer_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s192_terra_direct_writer_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def runtime_chunk(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["chunk_id"],
        "content": item["excerpt"],
        "product_model": item["product_model"],
        "source_file": item["source_file"],
        "section_title": item["section_title"],
        "content_type": "specification" if item["stratum"] == "table" else "general",
        "similarity": 1.0,
        "page_number": item["page_number"],
        "document_revision": None,
        "document_revision_date": None,
        "has_diagram": False,
        "diagram_url": None,
    }


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S192 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_NO_RETRY":
        raise RuntimeError("S192 paid execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S192 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S192 permitted artifact drift: {spec['path']}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from openai import OpenAI

    if DEFAULT_RECEIPTS.exists() or DEFAULT_RESULT.exists():
        raise RuntimeError("S192 checkpoint exists; retries are forbidden")
    key = (dotenv_values(env_file).get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S192 OPENAI_API_KEY missing")
    client = OpenAI(api_key=key)
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    items = cohort["items"]
    if len(items) != 14 or any(
        key in item for item in items for key in ("answer_points", "exact_quote")
    ):
        raise RuntimeError("S192 generation cohort contains gold or has drifted")

    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    jobs: list[dict[str, Any]] = []
    counted_total = 0
    for item in items:
        chunk = runtime_chunk(item)
        system, prompt = build_prompt(
            {"question": item["question"], "context": [chunk]}
        )
        counted = client.responses.input_tokens.count(
            model=model["id"],
            reasoning={"effort": model["reasoning_effort"]},
            instructions=system,
            input=prompt,
        ).input_tokens
        counted_total += counted
        jobs.append(
            {"item": item, "system": system, "prompt": prompt, "counted": counted}
        )
    worst = (
        counted_total * prices["input"]
        + len(jobs) * model["max_output_tokens"] * prices["output"]
    ) / 1_000_000
    if worst >= prereg["budget"]["internal_ceiling_usd"]:
        raise RuntimeError(f"S192 preflight ${worst:.4f} exceeds internal budget")

    receipts: list[dict[str, Any]] = []
    actual = 0.0
    for job in jobs:
        started = time.perf_counter()
        response = client.responses.create(
            model=model["id"],
            reasoning={"effort": model["reasoning_effort"]},
            instructions=job["system"],
            input=job["prompt"],
            max_output_tokens=model["max_output_tokens"],
            store=False,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        answer = response.output_text
        usage = response.usage.model_dump(mode="json")
        call_cost = (
            usage.get("input_tokens", 0) * prices["input"]
            + usage.get("output_tokens", 0) * prices["output"]
        ) / 1_000_000
        actual += call_cost
        receipts.append(
            {
                "item_id": job["item"]["item_id"],
                "response_id": response.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": response.status,
                "incomplete_details": (
                    response.incomplete_details.model_dump(mode="json")
                    if response.incomplete_details
                    else None
                ),
                "counted_input_tokens": job["counted"],
                "usage": usage,
                "cost_usd": round(call_cost, 8),
                "latency_ms": latency_ms,
                "answer": answer,
                "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            }
        )
        write_json(
            DEFAULT_RECEIPTS,
            {
                "instrument": "s192_terra_direct_writer_receipts_v1",
                "status": "IN_PROGRESS",
                "model": model["id"],
                "receipts": receipts,
            },
        )
        print(
            f"{len(receipts)}/14 {job['item']['item_id']}: "
            f"status={response.status} cost=${call_cost:.4f}",
            flush=True,
        )
    checkpoint = {
        "instrument": "s192_terra_direct_writer_receipts_v1",
        "status": "PAID_CHECKPOINT_COMPLETE",
        "model": model["id"],
        "reasoning_effort": model["reasoning_effort"],
        "receipts": receipts,
        "cost": {
            "actual_usd": round(actual, 8),
            "worst_case_preflight_usd": round(worst, 8),
        },
    }
    write_json(DEFAULT_RECEIPTS, checkpoint)

    # Gold and baseline are deliberately unavailable until every output is checkpointed.
    gold = {
        row["item_id"]: row
        for row in json.loads(GOLD.read_text(encoding="utf-8"))["items"]
        if row.get("eligible")
    }
    baseline = {
        row["item_id"]: row
        for row in json.loads(BASELINE.read_text(encoding="utf-8"))["receipts"]
    }
    baseline_points = candidate_points = regressions = invalid = 0
    baseline_complete = candidate_complete = incomplete = 0
    rows = []
    for receipt in receipts:
        item_id = receipt["item_id"]
        base_answer = baseline[item_id]["answer"]
        answer = receipt["answer"]
        point_rows = []
        item_baseline = item_candidate = 0
        for point in gold[item_id]["answer_points"]:
            before = point_covered(base_answer, point)
            after = point_covered(answer, point)
            baseline_points += int(before)
            candidate_points += int(after)
            item_baseline += int(before)
            item_candidate += int(after)
            regressions += int(before and not after)
            point_rows.append(
                {"claim": point["claim"], "baseline": before, "candidate": after}
            )
        total = len(gold[item_id]["answer_points"])
        baseline_complete += int(item_baseline == total)
        candidate_complete += int(item_candidate == total)
        bad = invalid_citations(answer, 1)
        invalid += len(bad)
        incomplete += int(receipt["status"] != "completed")
        rows.append(
            {
                "item_id": item_id,
                "stratum": gold[item_id]["stratum"],
                "answer_points": total,
                "baseline_points_covered": item_baseline,
                "candidate_points_covered": item_candidate,
                "regressed_points": sum(
                    int(row["baseline"] and not row["candidate"])
                    for row in point_rows
                ),
                "invalid_citations": bad,
                "points": point_rows,
            }
        )
    gain = candidate_points - baseline_points
    complete_gain = candidate_complete - baseline_complete
    checks = {
        "all_14_calls_complete": len(receipts) == 14 and incomplete == 0,
        "point_gain_gte_4": gain >= 4,
        "complete_question_gain_gte_2": complete_gain >= 2,
        "regressed_points_zero": regressions == 0,
        "invalid_citations_zero": invalid == 0,
        "actual_cost_below_ceiling": actual < prereg["budget"]["internal_ceiling_usd"],
    }
    passed = all(checks.values())
    result = {
        "instrument": "s192_terra_direct_writer_v1",
        "status": "GO_TO_FRESH_MODEL_ROUTING_GATE" if passed else "NO_GO_DIRECT_MODEL_SWAP",
        "population": {
            "questions": 14,
            "manufacturers": 14,
            "table": 7,
            "prose": 7,
            "answer_points": 37,
            "target_question_overlap": 0,
        },
        "measurement": {
            "baseline_points": baseline_points,
            "candidate_points": candidate_points,
            "point_gain": gain,
            "baseline_questions_complete": baseline_complete,
            "candidate_questions_complete": candidate_complete,
            "complete_question_gain": complete_gain,
            "regressed_points": regressions,
            "invalid_citations": invalid,
            "incomplete_calls": incomplete,
            "median_latency_ms": sorted(row["latency_ms"] for row in receipts)[7],
        },
        "checks": checks,
        "rows": rows,
        "cost": checkpoint["cost"],
        "decision": {
            "same_cohort_tuning": False,
            "reasoning_escalation": False,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "passing_action": "fresh_model_routing_and_operational_cost_latency_gate",
            "failing_action": "close_direct_swap_and_test_id_planner_deterministic_renderer",
        },
    }
    write_json(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    args = parser.parse_args()
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file)
    print(
        json.dumps(
            {"status": result["status"], "measurement": result["measurement"], "cost": result["cost"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

