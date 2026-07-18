#!/usr/bin/env python3
"""One-shot compact Frontier review for the S209 mechanism decision."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

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


OUTPUT = ROOT / "evals/s209_compact_frontier_design_reviews_v1.json"
BRIEF = ROOT / "evals/s209_compact_design_review_brief_v1.md"
CONTRACT = ROOT / "src/rag/planner_support_review.py"
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _prompt() -> str:
    return (
        BRIEF.read_text(encoding="utf-8")
        + "\n\n===== EXACT V4 CONTRACT =====\n"
        + CONTRACT.read_text(encoding="utf-8")
    )


def _validate(review: dict[str, Any], model: str) -> None:
    if set(review) != {"reviewer", "verdict", "findings", "residual_risks"}:
        raise ValueError("review shape mismatch")
    if review["reviewer"] != model or review["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("reviewer identity or verdict mismatch")
    if not isinstance(review["findings"], list) or not isinstance(
        review["residual_risks"], list
    ):
        raise ValueError("review arrays missing")
    for finding in review["findings"]:
        if set(finding) != {"id", "severity", "description", "required_fix"}:
            raise ValueError("finding shape mismatch")
        if finding["severity"] not in {"critical", "major"}:
            raise ValueError("finding severity mismatch")


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S209 compact design review artifact already exists")
    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    prompt = _prompt()
    reviews: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []

    sol = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0).responses.create(
        model=SOL_MODEL,
        instructions="Return only the requested JSON. Be concise.",
        input=prompt,
        reasoning={"effort": "xhigh"},
        max_output_tokens=6000,
        store=False,
    )
    sol_receipt = {
        "provider": "sol",
        "model": getattr(sol, "model", None),
        "status": getattr(sol, "status", None),
        "usage": usage_dict(sol),
    }
    receipts.append(sol_receipt)
    if sol_receipt["model"] == SOL_MODEL and sol_receipt["status"] == "completed":
        try:
            reviews["sol"] = parse_json((sol.output_text or "").strip())
            _validate(reviews["sol"], SOL_MODEL)
        except (ValueError, json.JSONDecodeError) as exc:
            reviews["sol"] = {"status": "INVALID", "reason": str(exc)}
    else:
        reviews["sol"] = {"status": "INCOMPLETE"}

    fable = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    ).messages.create(
        model=FABLE_MODEL,
        max_tokens=4000,
        system="Return only the requested JSON. Be concise.",
        messages=[{"role": "user", "content": prompt}],
    )
    fable_receipt = {
        "provider": "fable",
        "model": getattr(fable, "model", None),
        "status": getattr(fable, "stop_reason", None),
        "usage": usage_dict(fable),
    }
    receipts.append(fable_receipt)
    if (
        fable_receipt["model"] == FABLE_MODEL
        and fable_receipt["status"] == "end_turn"
    ):
        raw = "\n".join(
            block.text
            for block in fable.content
            if getattr(block, "type", None) == "text"
        ).strip()
        try:
            reviews["fable"] = parse_json(raw)
            _validate(reviews["fable"], FABLE_MODEL)
        except (ValueError, json.JSONDecodeError) as exc:
            reviews["fable"] = {"status": "INVALID", "reason": str(exc)}
    else:
        reviews["fable"] = {"status": "INCOMPLETE"}

    complete = all(
        isinstance(reviews.get(key), dict)
        and reviews[key].get("verdict") in {"PASS", "FAIL"}
        for key in ("sol", "fable")
    )
    artifact = sealed_artifact(
        "s209_compact_frontier_design_reviews_v1",
        {
            "status": "COMPLETE" if complete else "INCOMPLETE_NO_RETRY",
            "subject": [
                BRIEF.relative_to(ROOT).as_posix(),
                CONTRACT.relative_to(ROOT).as_posix(),
            ],
            "reviews": reviews,
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
                "sol_verdict": reviews.get("sol", {}).get("verdict"),
                "fable_verdict": reviews.get("fable", {}).get("verdict"),
                "cost": artifact["conservative_cost_usd"],
            },
            indent=2,
        )
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
