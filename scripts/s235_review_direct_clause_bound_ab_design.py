#!/usr/bin/env python3
"""One-shot Sol 5.6 xhigh and Fable 5 review of the direct S235 A/B."""
from __future__ import annotations

import argparse
import hashlib
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

from src.rag.frontier_visual_runtime_v2 import FrontierVisualRuntime  # noqa: E402
from src.rag.frontier_visual_schemas import anthropic_compatible_schema  # noqa: E402
from src.rag.visual_gold import conservative_cost, sealed_artifact, write_json  # noqa: E402

DESIGN = ROOT / "evals/s235_direct_clause_bound_ab_design_v1.md"
PREREG = ROOT / "evals/s235_direct_clause_bound_ab_prereg_v1.yaml"
LEDGER = ROOT / "evals/s235_design_frontier_call_ledger_v1.json"
ATTEMPTS = ROOT / "evals/s235_design_frontier_attempts_v1.json"
RESULT = ROOT / "evals/s235_design_frontier_reviews_v1.json"
SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
CHECKS = (
    "direct_target_use_justified",
    "paired_causal_design",
    "generation_score_isolated",
    "same_writer_and_equal_budget",
    "safety_and_regression_gate",
    "no_overfit_or_unsupported_credit",
    "transport_and_cost_bounded",
    "best_practice_aligned",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if review.get("reviewer_model") != model or review.get("verdict") not in {
        "PASS",
        "FAIL",
    }:
        raise ValueError("S235 reviewer identity or verdict mismatch")
    checks = review.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(CHECKS):
        raise ValueError("S235 design review checks incomplete")
    if any(not isinstance(checks[name], bool) for name in CHECKS):
        raise ValueError("S235 design review check is not boolean")
    for field in ("blocking_issues", "minimum_changes"):
        if not isinstance(review.get(field), list) or any(
            not isinstance(value, str) for value in review[field]
        ):
            raise ValueError(f"invalid S235 {field}")
        if len(review[field]) > 5:
            raise ValueError(f"S235 {field} exceeds local limit")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        raise ValueError("S235 review rationale missing")
    passes = (
        all(checks.values())
        and not review["blocking_issues"]
        and not review["minimum_changes"]
    )
    if (review["verdict"] == "PASS") != passes:
        raise ValueError("S235 verdict contradicts structured review")
    return passes


def checkpoint_attempt(label: str) -> None:
    value = {"schema": "s235_design_frontier_attempts_v1", "attempts": []}
    if ATTEMPTS.exists():
        value = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    value["attempts"].append({"call_label": label, "status": "STARTED_NO_RETRY"})
    write_json(ATTEMPTS, value)


def verify_prereg() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S235 preregistration is not frozen")
    for label, spec in prereg["frozen_design_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S235 frozen design input drift: {label}")
    return prereg


def _runtime(env_file: Path) -> FrontierVisualRuntime:
    secrets = dotenv_values(env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S235 provider credentials missing")
    return FrontierVisualRuntime(
        ledger_path=LEDGER,
        ledger_schema="s235_design_frontier_call_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    verify_prereg()
    existing = [path.name for path in (LEDGER, ATTEMPTS, RESULT) if path.exists()]
    if existing:
        raise RuntimeError(f"S235 design review artifacts already exist: {existing}")
    code = "\n\n".join(
        f"## FILE: {path.relative_to(ROOT).as_posix()}\n{path.read_text(encoding='utf-8')}"
        for path in (
            DESIGN,
            ROOT / "scripts/s235_run_direct_clause_bound_ab.py",
            ROOT / "scripts/s235_score_direct_clause_bound_ab.py",
            ROOT / "src/rag/clause_bound_synthesis.py",
        )
    )
    prompt = (
        "Adversarially review this one-shot direct experiment. PASS only if every "
        "structured check is true and the executable design cannot create a false GO. "
        "The 12 target misses are already frozen; using them now is intentional, and no "
        "new gold is requested. Treat stylistic improvements as nonblocking. FAIL only "
        "for a concrete causal, leakage, safety, overfit, transport, budget, or unsupported-"
        "credit blocker. Do not request broader research or a convergence round.\n\n" + code
    )
    runtime = _runtime(args.env_file)
    checkpoint_attempt("s235_design:sol")
    sol_review, _ = runtime.call_sol(
        [{"type": "input_text", "text": prompt}],
        "s235_design:sol",
        output_schema=schema(SOL),
    )
    sol_pass = validate(sol_review, SOL)
    checkpoint_attempt("s235_design:fable")
    fable_review, _ = runtime.call_fable(
        [{"type": "text", "text": prompt}],
        8000,
        "s235_design:fable",
        output_schema=anthropic_compatible_schema(schema(FABLE)),
    )
    fable_pass = validate(fable_review, FABLE)
    ledger = runtime.seal_complete(2)
    dual_pass = sol_pass and fable_pass
    write_json(
        RESULT,
        sealed_artifact(
            "s235_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE",
                "reviews": {"sol": sol_review, "fable": fable_review},
                "frontier_calls": 2,
                "provider_retries": 0,
                "semantic_convergence_rounds": 0,
                "cost_usd": conservative_cost(ledger["calls"], PRICES),
                "next_authorized_step": "direct_ab" if dual_pass else "close_s235",
                "official_fact_credit": 0,
                "production_default_changed": False,
                "chunks_v2": "ACTIVE_READ_ONLY",
                "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
    )
    print(json.dumps({"status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE"}, indent=2))
    return 0 if dual_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
