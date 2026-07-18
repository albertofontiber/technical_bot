#!/usr/bin/env python3
"""Final bounded Frontier decision card for S209; no follow-up rounds."""
from __future__ import annotations

import hashlib
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


OUTPUT = ROOT / "evals/s209_frontier_decision_card_reviews_v1.json"
BRIEF = ROOT / "evals/s209_compact_design_review_brief_v1.md"
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _format(model: str) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s209_design_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "reviewer": {"type": "string", "enum": [model]},
                    "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
                    "blocking_findings": {
                        "type": "array",
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "required_fix": {"type": "string"},
                            },
                            "required": ["id", "description", "required_fix"],
                        },
                    },
                    "residual_risks": {
                        "type": "array",
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "reviewer",
                    "verdict",
                    "blocking_findings",
                    "residual_risks",
                ],
            },
        }
    }


def _prompt(model: str) -> str:
    brief = BRIEF.read_text(encoding="utf-8")
    return (
        "You are the final independent design gate. Review only whether this "
        "bounded experiment can validly decide if the planner may advance to a "
        "separate target A/B. Do not request style work, more cohorts, another "
        "review round, or external validation as a prerequisite. FAIL only for "
        "a concrete design defect that can falsely produce GO or violate the "
        "stated isolation. Keep the entire answer under 500 words. The reviewer "
        f"field must be exactly {model}.\n\n{brief}"
    )


def _validate(value: dict[str, Any], model: str) -> None:
    if set(value) != {
        "reviewer",
        "verdict",
        "blocking_findings",
        "residual_risks",
    }:
        raise ValueError("decision shape mismatch")
    if value["reviewer"] != model or value["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("decision identity or verdict mismatch")
    blockers = value["blocking_findings"]
    if not isinstance(blockers, list) or len(blockers) > 3:
        raise ValueError("blocking findings invalid")
    if value["verdict"] == "PASS" and blockers:
        raise ValueError("PASS cannot contain blocking findings")
    if value["verdict"] == "FAIL" and not blockers:
        raise ValueError("FAIL must contain a blocking finding")
    for row in blockers:
        if set(row) != {"id", "description", "required_fix"}:
            raise ValueError("blocking finding shape mismatch")
    risks = value["residual_risks"]
    if not isinstance(risks, list) or len(risks) > 3:
        raise ValueError("residual risks invalid")


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S209 decision-card artifact already exists")
    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    receipts: list[dict[str, Any]] = []
    decisions: dict[str, Any] = {}

    sol = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0).responses.create(
        model=SOL_MODEL,
        instructions="Return only the schema-conformant decision JSON.",
        input=_prompt(SOL_MODEL),
        reasoning={"effort": "xhigh"},
        text=_format(SOL_MODEL),
        max_output_tokens=16000,
        store=False,
    )
    sol_receipt = {
        "provider": "sol",
        "model": getattr(sol, "model", None),
        "status": getattr(sol, "status", None),
        "usage": usage_dict(sol),
    }
    receipts.append(sol_receipt)
    sol_raw = (sol.output_text or "").strip()
    if sol_receipt["model"] == SOL_MODEL and sol_receipt["status"] == "completed":
        try:
            decisions["sol"] = parse_json(sol_raw)
            _validate(decisions["sol"], SOL_MODEL)
        except (ValueError, json.JSONDecodeError) as exc:
            decisions["sol"] = {
                "status": "INVALID",
                "reason": str(exc),
                "raw_sha256": hashlib.sha256(sol_raw.encode()).hexdigest(),
            }
    else:
        decisions["sol"] = {"status": "INCOMPLETE"}

    fable = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    ).messages.create(
        model=FABLE_MODEL,
        max_tokens=2500,
        system=(
            "Return only JSON with exactly reviewer, verdict, blocking_findings, "
            "and residual_risks. The reviewer value must be claude-fable-5."
        ),
        messages=[{"role": "user", "content": _prompt(FABLE_MODEL)}],
    )
    fable_receipt = {
        "provider": "fable",
        "model": getattr(fable, "model", None),
        "status": getattr(fable, "stop_reason", None),
        "usage": usage_dict(fable),
    }
    receipts.append(fable_receipt)
    fable_raw = "\n".join(
        block.text
        for block in fable.content
        if getattr(block, "type", None) == "text"
    ).strip()
    if (
        fable_receipt["model"] == FABLE_MODEL
        and fable_receipt["status"] == "end_turn"
    ):
        try:
            decisions["fable"] = parse_json(fable_raw)
            _validate(decisions["fable"], FABLE_MODEL)
        except (ValueError, json.JSONDecodeError) as exc:
            decisions["fable"] = {
                "status": "INVALID",
                "reason": str(exc),
                "raw_sha256": hashlib.sha256(fable_raw.encode()).hexdigest(),
                "raw_text": fable_raw,
            }
    else:
        decisions["fable"] = {"status": "INCOMPLETE"}

    complete = all(
        decisions.get(key, {}).get("verdict") in {"PASS", "FAIL"}
        for key in ("sol", "fable")
    )
    artifact = sealed_artifact(
        "s209_frontier_decision_card_reviews_v1",
        {
            "status": "COMPLETE" if complete else "INCOMPLETE_NO_FURTHER_RETRY",
            "subject": BRIEF.relative_to(ROOT).as_posix(),
            "decisions": decisions,
            "receipts": receipts,
            "conservative_cost_usd": conservative_cost(receipts, PRICES),
            "same_subject_retry": False,
            "further_design_review_calls": False,
        },
    )
    write_json(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "sol_verdict": decisions.get("sol", {}).get("verdict"),
                "fable_verdict": decisions.get("fable", {}).get("verdict"),
                "cost": artifact["conservative_cost_usd"],
            },
            indent=2,
        )
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
