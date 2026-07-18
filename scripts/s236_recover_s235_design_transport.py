#!/usr/bin/env python3
"""Single transport replacement for S235's pre-inference Sol 520."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s235_review_direct_clause_bound_ab_design import (  # noqa: E402
    DESIGN,
    FABLE,
    PRICES,
    SOL,
    checkpoint_attempt,
    schema,
    validate,
)
from src.rag.frontier_visual_runtime_v2 import FrontierVisualRuntime  # noqa: E402
from src.rag.frontier_visual_schemas import anthropic_compatible_schema  # noqa: E402
from src.rag.visual_gold import conservative_cost, sealed_artifact, write_json  # noqa: E402

PREREG = ROOT / "evals/s236_s235_design_transport_recovery_prereg_v1.yaml"
ATTEMPTS = ROOT / "evals/s235_design_frontier_attempts_v1.json"
LEDGER = ROOT / "evals/s235_design_frontier_call_ledger_v1.json"
RESULT = ROOT / "evals/s235_design_frontier_reviews_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_SINGLE_TRANSPORT_REPLACEMENT":
        raise ValueError("S236 recovery is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S236 frozen input drift: {label}")
    attempts = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    if attempts != {
        "schema": "s235_design_frontier_attempts_v1",
        "attempts": [
            {"call_label": "s235_design:sol", "status": "STARTED_NO_RETRY"}
        ],
    }:
        raise ValueError("S236 prior attempt geometry drift")
    if LEDGER.exists() or RESULT.exists():
        raise RuntimeError("S236 found a prior provider response or result")


def _runtime(env_file: Path) -> FrontierVisualRuntime:
    secrets = dotenv_values(env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S236 provider credentials missing")
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
    _verify()
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
    checkpoint_attempt("s236_transport_replacement:sol")
    sol_review, _ = runtime.call_sol(
        [{"type": "input_text", "text": prompt}],
        "s236_transport_replacement:sol",
        output_schema=schema(SOL),
    )
    sol_pass = validate(sol_review, SOL)
    checkpoint_attempt("s236_design:fable")
    fable_review, _ = runtime.call_fable(
        [{"type": "text", "text": prompt}],
        8000,
        "s236_design:fable",
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
                "frontier_calls_with_responses": 2,
                "pre_inference_transport_failures": 1,
                "provider_retries": 0,
                "transport_replacements": 1,
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
