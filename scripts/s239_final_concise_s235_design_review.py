#!/usr/bin/env python3
"""Final concise, parallel Sol/Fable design review for S235."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import dotenv_values
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s235_review_direct_clause_bound_ab_design import (  # noqa: E402
    DESIGN,
    FABLE,
    PRICES,
    SOL,
    schema,
    validate,
)
from src.rag.frontier_visual_schemas import anthropic_compatible_schema  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    parse_json,
    sealed_artifact,
    usage_dict,
    write_json,
)

PREREG = ROOT / "evals/s239_final_concise_s235_review_prereg_v1.yaml"
LEDGER = ROOT / "evals/s239_final_concise_s235_review_ledger_v1.json"
RESULT = ROOT / "evals/s235_design_frontier_reviews_v1.json"
POLL_SECONDS = 5
POLL_DEADLINE_SECONDS = 900
TERMINAL = {"completed", "failed", "cancelled", "incomplete"}
PRIOR_COST_USD = 25.36794


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_FINAL_CONCISE_REVIEW_NO_FURTHER_ROUNDS":
        raise ValueError("S239 final review is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S239 frozen input drift: {label}")
    if LEDGER.exists() or RESULT.exists():
        raise RuntimeError("S239 final review was already attempted")


def _prompt() -> str:
    return (
        "Review only the frozen experimental design below. The executable implementation "
        "has already passed 26 local contract tests; code-style suggestions are outside this "
        "review. PASS only if all eight structured checks are true and no concrete design "
        "defect can create a false GO. FAIL only for a causal, leakage, safety, overfit, "
        "transport, budget, or unsupported-credit blocker. If PASS, blocking_issues and "
        "minimum_changes MUST both be empty; put any nonblocking observation in rationale. "
        "Do not request broader research, code changes, or another review round.\n\n"
        + DESIGN.read_text(encoding="utf-8")
    )


def _fable_text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    _verify()
    secrets = dotenv_values(args.env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S239 provider credentials missing")
    prompt = _prompt()
    sol_client = OpenAI(api_key=openai_key, max_retries=0)
    fable_client = anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
    sol_response = sol_client.responses.create(
        model=SOL,
        background=True,
        store=True,
        instructions="Follow the user contract exactly. Return only JSON.",
        input=prompt,
        reasoning={"effort": "xhigh"},
        max_output_tokens=24000,
        text={
            "format": {
                "type": "json_schema",
                "name": "s239_final_concise_design_sol",
                "strict": True,
                "schema": schema(SOL),
            },
            "verbosity": "low",
        },
    )
    write_json(
        LEDGER,
        sealed_artifact(
            "s239_final_concise_s235_review_ledger_v1",
            {
                "status": "IN_PROGRESS",
                "sol_response_id": sol_response.id,
                "sol_submission_status": sol_response.status,
                "fable": None,
            },
        ),
    )

    def fable_call() -> Any:
        return fable_client.messages.create(
            model=FABLE,
            max_tokens=12000,
            system="Follow the user contract exactly. Return only JSON.",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": "xhigh",
                "format": {
                    "type": "json_schema",
                    "schema": anthropic_compatible_schema(schema(FABLE)),
                },
            },
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        fable_future = pool.submit(fable_call)
        polls = [str(sol_response.status)]
        started = time.monotonic()
        while sol_response.status not in TERMINAL:
            if time.monotonic() - started >= POLL_DEADLINE_SECONDS:
                raise TimeoutError("S239 Sol exceeded polling deadline")
            time.sleep(POLL_SECONDS)
            sol_response = sol_client.responses.retrieve(sol_response.id)
            polls.append(str(sol_response.status))
        fable_response = fable_future.result()

    raw_sol = (sol_response.output_text or "").strip()
    raw_fable = _fable_text(fable_response)
    calls = [
        {"provider": "sol", "usage": usage_dict(sol_response)},
        {"provider": "fable", "usage": usage_dict(fable_response)},
    ]
    current_cost = conservative_cost(calls, PRICES)
    write_json(
        LEDGER,
        sealed_artifact(
            "s239_final_concise_s235_review_ledger_v1",
            {
                "status": "COMPLETE_RESPONSES_RECEIVED",
                "sol": {
                    "response_id": sol_response.id,
                    "status": sol_response.status,
                    "model": sol_response.model,
                    "polls": polls,
                    "usage": usage_dict(sol_response),
                    "raw_output": raw_sol,
                },
                "fable": {
                    "response_id": fable_response.id,
                    "status": fable_response.stop_reason,
                    "model": fable_response.model,
                    "usage": usage_dict(fable_response),
                    "raw_output": raw_fable,
                },
                "prior_cost_usd": PRIOR_COST_USD,
                "current_cost_usd": current_cost,
                "cumulative_cost_usd": PRIOR_COST_USD + current_cost,
            },
        ),
    )
    if sol_response.status != "completed" or sol_response.model != SOL or not raw_sol:
        raise RuntimeError(f"S239 Sol incomplete: {sol_response.status}/{sol_response.model}")
    if fable_response.stop_reason != "end_turn" or fable_response.model != FABLE or not raw_fable:
        raise RuntimeError(
            f"S239 Fable incomplete: {fable_response.stop_reason}/{fable_response.model}"
        )
    sol_review = parse_json(raw_sol)
    fable_review = parse_json(raw_fable)
    sol_pass = validate(sol_review, SOL)
    fable_pass = validate(fable_review, FABLE)
    dual_pass = sol_pass and fable_pass
    write_json(
        RESULT,
        sealed_artifact(
            "s235_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE",
                "reviews": {"sol": sol_review, "fable": fable_review},
                "successful_review_calls": 2,
                "pre_inference_sync_transport_failures": 2,
                "prior_incomplete_sol_jobs": 2,
                "prior_incomplete_fable_calls": 1,
                "provider_sdk_retries": 0,
                "semantic_convergence_rounds": 0,
                "cumulative_cost_usd": PRIOR_COST_USD + current_cost,
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
