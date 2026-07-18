#!/usr/bin/env python3
"""One-shot Frontier review of the proposed S209 planner holdout."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    parse_json,
    sealed_artifact,
    usage_dict,
    write_json,
)


OUTPUT = ROOT / "evals" / "s209_fresh_planner_design_reviews_v1.json"
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
REVIEW_FILES = (
    "evals/s209_fresh_planner_holdout_design_v1.md",
    "evals/s209_kidde_predicate_selection_receipt_v1.json",
    "evals/s209_pixel_inspection_receipts_v1.json",
    "src/rag/planner_support_review.py",
    "scripts/s209_build_fresh_planner_holdout.py",
    "scripts/s209_run_fresh_planner_holdout.py",
    "tests/test_s209_fresh_planner_holdout.py",
)


def prompt() -> str:
    sources = []
    for name in REVIEW_FILES:
        sources.append(
            f"\n===== {name} =====\n{(ROOT / name).read_text(encoding='utf-8')}"
        )
    return """Critically review this proposed planner-holdout design and code before preregistration.
The user prioritises fast progress toward 98% facts OK without overfitting.
This is a ONE-SHOT review: identify only concrete defects that could invalidate
pixel grounding, independence, freshness, GO/HOLD/NO-GO semantics, auditability,
budget/call bounds or downstream isolation. Do not request style cleanups or a
second review round. Do not rewrite code.

Return ONLY JSON:
{"reviewer":"exact model id","verdict":"PASS or FAIL","findings":[
 {"id":"...","severity":"critical|major|minor","file":"...",
  "description":"...","required_fix":"..."}],"residual_risks":["..."]}
""" + "".join(sources)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fable-after-sol-incomplete", action="store_true")
    parser.add_argument("--record-both-incomplete", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists():
        raise RuntimeError("S209 design review artifact already exists")
    if args.record_both_incomplete:
        receipts = [
            {
                "provider": "sol",
                "model": SOL_MODEL,
                "status": "incomplete",
                "usage": {
                    "input_tokens": 16577,
                    "output_tokens": 6000,
                    "total_tokens": 22577,
                },
            },
            {
                "provider": "fable",
                "model": FABLE_MODEL,
                "status": "max_tokens",
                "usage": {
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "input_tokens": 28176,
                    "output_tokens": 5000,
                },
            },
        ]
        reviews = {
            "sol": {
                "reviewer": SOL_MODEL,
                "verdict": "INCOMPLETE",
                "findings": [],
                "residual_risks": ["No final JSON after output allowance."],
            },
            "fable": {
                "reviewer": FABLE_MODEL,
                "verdict": "INCOMPLETE",
                "findings": [],
                "residual_risks": ["No final JSON after max_tokens."],
            },
        }
        artifact = sealed_artifact(
            "s209_fresh_planner_design_reviews_v1",
            {
                "status": "BOTH_FRONTIER_REVIEWS_INCOMPLETE_NO_RETRY",
                "reviewed_files": list(REVIEW_FILES),
                "reviews": reviews,
                "receipts": receipts,
                "conservative_cost_usd": conservative_cost(receipts, PRICES),
                "same_subject_retry": False,
                "interpretation": (
                    "Both exact model pins were reached; neither emitted a final "
                    "review. This is incomplete, not unavailable."
                ),
            },
        )
        write_json(OUTPUT, artifact)
        print(json.dumps({"status": artifact["status"], "cost": artifact["conservative_cost_usd"]}, indent=2))
        return 0

    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    review_prompt = prompt()

    if args.fable_after_sol_incomplete:
        # Exact receipt emitted by the one prior no-retry Sol call.  It reached
        # the model pin but spent the output allowance on reasoning and emitted
        # no final JSON.  This recovery path never invokes Sol again.
        sol_receipt = {
            "provider": "sol",
            "model": SOL_MODEL,
            "status": "incomplete",
            "usage": {
                "input_tokens": 16577,
                "output_tokens": 6000,
                "total_tokens": 22577,
            },
        }
        sol_review = {
            "reviewer": SOL_MODEL,
            "verdict": "INCOMPLETE",
            "findings": [],
            "residual_risks": [
                "No final review JSON: output token allowance exhausted in reasoning."
            ],
        }
    else:
        sol_response = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"], max_retries=0
        ).responses.create(
            model=SOL_MODEL,
            instructions="Return only the requested JSON.",
            input=review_prompt,
            reasoning={"effort": "xhigh"},
            max_output_tokens=6000,
            store=False,
        )
        sol_raw = (sol_response.output_text or "").strip()
        sol_receipt = {
            "provider": "sol",
            "model": getattr(sol_response, "model", None),
            "status": getattr(sol_response, "status", None),
            "usage": usage_dict(sol_response),
        }
        if sol_receipt["model"] != SOL_MODEL or sol_receipt["status"] != "completed":
            raise RuntimeError(f"Sol review incomplete: {sol_receipt}")
        sol_review = parse_json(sol_raw)

    fable_response = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    ).messages.create(
        model=FABLE_MODEL,
        max_tokens=5000,
        system="Return only the requested JSON.",
        messages=[{"role": "user", "content": review_prompt}],
    )
    fable_raw = "\n".join(
        block.text
        for block in fable_response.content
        if getattr(block, "type", None) == "text"
    ).strip()
    fable_receipt = {
        "provider": "fable",
        "model": getattr(fable_response, "model", None),
        "status": getattr(fable_response, "stop_reason", None),
        "usage": usage_dict(fable_response),
    }
    if (
        fable_receipt["model"] != FABLE_MODEL
        or fable_receipt["status"] != "end_turn"
    ):
        raise RuntimeError(f"Fable review incomplete: {fable_receipt}")
    fable_review = parse_json(fable_raw)

    receipts = [sol_receipt, fable_receipt]
    artifact = sealed_artifact(
        "s209_fresh_planner_design_reviews_v1",
        {
            "status": (
                "SOL_INCOMPLETE_FABLE_COMPLETE"
                if args.fable_after_sol_incomplete
                else "COMPLETE"
            ),
            "reviewed_files": list(REVIEW_FILES),
            "reviews": {"sol": sol_review, "fable": fable_review},
            "receipts": receipts,
            "conservative_cost_usd": conservative_cost(receipts, PRICES),
            "same_subject_retry": False,
        },
    )
    write_json(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "sol_verdict": sol_review.get("verdict"),
                "fable_verdict": fable_review.get("verdict"),
                "cost": artifact["conservative_cost_usd"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
