#!/usr/bin/env python3
"""One-shot structured Sol/Fable review of the S230 design."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    normalized_text_sha,
    sealed_artifact,
    write_json,
)


DESIGN = ROOT / "evals/s230_fresh_clause_bound_design_v1.md"
PREREG = ROOT / "evals/s230_fresh_clause_bound_prereg_v1.yaml"
LEDGER = ROOT / "evals/s230_design_frontier_call_ledger_v1.json"
ATTEMPTS = ROOT / "evals/s230_design_frontier_attempts_v1.json"
RESULT = ROOT / "evals/s230_design_frontier_reviews_v1.json"
SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
CHECKS = (
    "freshness_honest",
    "pixel_gold_honest",
    "transport_fail_closed",
    "clause_bound_causal_test",
    "no_overfit",
    "target_closed",
    "budget_bounded",
)


def schema(model: str) -> dict[str, Any]:
    checks = {
        "type": "object",
        "additionalProperties": False,
        "required": list(CHECKS),
        "properties": {name: {"type": "boolean"} for name in CHECKS},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "reviewer_model",
            "verdict",
            "checks",
            "blocking_issues",
            "minimum_changes",
            "rationale",
        ],
        "properties": {
            "reviewer_model": {"type": "string", "enum": [model]},
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "checks": checks,
            "blocking_issues": {"type": "array", "items": {"type": "string"}},
            "minimum_changes": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
    }


def validate(review: dict[str, Any], model: str) -> bool:
    if review.get("reviewer_model") != model:
        raise ValueError("reviewer model mismatch")
    if review.get("verdict") not in {"PASS", "FAIL"}:
        raise ValueError("invalid verdict")
    checks = review.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(CHECKS):
        raise ValueError("design checks incomplete")
    if any(not isinstance(checks[name], bool) for name in CHECKS):
        raise ValueError("design check is not boolean")
    for field in ("blocking_issues", "minimum_changes"):
        if not isinstance(review.get(field), list) or any(
            not isinstance(value, str) for value in review[field]
        ):
            raise ValueError(f"invalid {field}")
        if len(review[field]) > 5:
            raise ValueError(f"{field} exceeds local cardinality limit")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        raise ValueError("missing rationale")
    passes = all(checks.values()) and not review["blocking_issues"] and not review["minimum_changes"]
    if (review["verdict"] == "PASS") != passes:
        raise ValueError("verdict contradicts structured checks")
    return passes


def checkpoint_attempt(label: str) -> None:
    body = {"schema": "s230_design_frontier_attempts_v1", "attempts": []}
    if ATTEMPTS.exists():
        body = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    body["attempts"].append({"call_label": label, "status": "STARTED_NO_RETRY"})
    write_json(ATTEMPTS, body)


def runtime(env_file: Path) -> FrontierVisualRuntime:
    secrets = dotenv_values(env_file)
    openai_key = str(secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = str(secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S230 provider credential missing")
    return FrontierVisualRuntime(
        ledger_path=LEDGER,
        ledger_schema="s230_design_frontier_call_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
    )


def verify_prereg() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S230 prereg is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S230 frozen input drift: {label}")
    return prereg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    verify_prereg()
    existing = [path.name for path in (LEDGER, ATTEMPTS, RESULT) if path.exists()]
    if existing:
        raise RuntimeError(f"S230 design review artifacts already exist: {existing}")
    prompt = (
        "Review this single bounded design. PASS only if every structured check is true. "
        "FAIL only for a concrete false-GO, contamination, unsupported-credit, transport, "
        "or budget blocker. Do not request convergence, broader research, or another round.\n\n"
        + DESIGN.read_text(encoding="utf-8")
    )
    rt = runtime(args.env_file)
    checkpoint_attempt("design:sol")
    sol_review, _ = rt.call_sol(
        [{"type": "input_text", "text": prompt}],
        "design:sol",
        output_schema=schema(SOL),
    )
    sol_pass = validate(sol_review, SOL)
    checkpoint_attempt("design:fable")
    fable_review, _ = rt.call_fable(
        [{"type": "text", "text": prompt}],
        5000,
        "design:fable",
        output_schema=schema(FABLE),
    )
    fable_pass = validate(fable_review, FABLE)
    ledger = rt.seal_complete(2)
    dual = sol_pass and fable_pass
    write_json(
        RESULT,
        sealed_artifact(
            "s230_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual else "NO_GO_NO_RETRY",
                "reviews": {"sol": sol_review, "fable": fable_review},
                "frontier_calls": 2,
                "provider_retries": 0,
                "cost_usd": conservative_cost(ledger["calls"], PRICES),
                "next_authorized_step": "pixel_gold" if dual else "close_s230",
                "target_calls": 0,
                "facts_moved_to_ok": 0,
                "production_default_changed": False,
                "chunks_v2": "ACTIVE_READ_ONLY",
                "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
    )
    print(json.dumps({"status": "DUAL_PASS" if dual else "NO_GO_NO_RETRY"}, indent=2))
    return 0 if dual else 2


if __name__ == "__main__":
    raise SystemExit(main())
