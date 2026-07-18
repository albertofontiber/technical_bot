#!/usr/bin/env python3
"""One bounded Sol xhigh + Fable design gate for S210; never retry."""
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


OUTPUT = ROOT / "evals/s210_frontier_design_decision_reviews_v1.json"
BRIEF = ROOT / "evals/s210_compact_design_review_brief_v1.md"
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _schema(model: str) -> dict[str, Any]:
    return {
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
                "maxItems": 6,
                "items": {"type": "string"},
            },
        },
        "required": ["reviewer", "verdict", "blocking_findings", "residual_risks"],
    }


def _openai_format(model: str) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s210_design_decision",
            "strict": True,
            "schema": _schema(model),
        }
    }


def _prompt(model: str) -> str:
    return (
        "Act as the final independent design gate. FAIL only for a concrete defect "
        "that can falsely produce local GO, leak target answers, break source-span "
        "binding, violate the cost/call boundary, or overstate this cohort. External "
        "validation and atomic fact review are deliberately later gates. Do not ask "
        "for style work, more cohorts, or another review round now. Keep the answer "
        f"under 600 words. reviewer must be exactly {model}.\n\n"
        + BRIEF.read_text(encoding="utf-8")
    )


def _validate(value: dict[str, Any], model: str) -> None:
    if set(value) != {"reviewer", "verdict", "blocking_findings", "residual_risks"}:
        raise ValueError("decision shape mismatch")
    if value["reviewer"] != model or value["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("decision identity or verdict mismatch")
    blockers = value["blocking_findings"]
    risks = value["residual_risks"]
    if not isinstance(blockers, list) or len(blockers) > 3:
        raise ValueError("blocking findings invalid")
    if not isinstance(risks, list) or len(risks) > 6:
        raise ValueError("residual risks invalid")
    if (value["verdict"] == "PASS") != (not blockers):
        raise ValueError("verdict/blocker inconsistency")
    if any(set(row) != {"id", "description", "required_fix"} for row in blockers):
        raise ValueError("blocking finding shape mismatch")


def _parse(raw: str, model: str) -> dict[str, Any]:
    try:
        value = parse_json(raw)
        _validate(value, model)
        return value
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "INVALID",
            "reason": str(exc),
            "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        }


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S210 design decision artifact already exists")
    missing = [key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    receipts: list[dict[str, Any]] = []
    decisions: dict[str, Any] = {}

    try:
        sol = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0).responses.create(
            model=SOL_MODEL,
            instructions="Return only the schema-conformant decision JSON.",
            input=_prompt(SOL_MODEL),
            reasoning={"effort": "xhigh"},
            text=_openai_format(SOL_MODEL),
            max_output_tokens=8000,
            store=False,
        )
        receipt = {
            "provider": "sol",
            "model": getattr(sol, "model", None),
            "status": getattr(sol, "status", None),
            "usage": usage_dict(sol),
        }
        receipts.append(receipt)
        raw = (sol.output_text or "").strip()
        decisions["sol"] = (
            _parse(raw, SOL_MODEL)
            if receipt["model"] == SOL_MODEL and receipt["status"] == "completed"
            else {"status": "INCOMPLETE"}
        )
    except Exception as exc:  # provider transport is recorded, never retried
        receipts.append({"provider": "sol", "model": SOL_MODEL, "status": "ERROR", "usage": {}})
        decisions["sol"] = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    try:
        fable = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
        ).messages.create(
            model=FABLE_MODEL,
            max_tokens=3000,
            system=(
                "Return only JSON with exactly reviewer, verdict, blocking_findings, "
                "and residual_risks. reviewer must be claude-fable-5."
            ),
            messages=[{"role": "user", "content": _prompt(FABLE_MODEL)}],
        )
        receipt = {
            "provider": "fable",
            "model": getattr(fable, "model", None),
            "status": getattr(fable, "stop_reason", None),
            "usage": usage_dict(fable),
        }
        receipts.append(receipt)
        raw = "\n".join(
            block.text for block in fable.content if getattr(block, "type", None) == "text"
        ).strip()
        decisions["fable"] = (
            _parse(raw, FABLE_MODEL)
            if receipt["model"] == FABLE_MODEL and receipt["status"] == "end_turn"
            else {"status": "INCOMPLETE"}
        )
    except Exception as exc:  # provider transport is recorded, never retried
        receipts.append({"provider": "fable", "model": FABLE_MODEL, "status": "ERROR", "usage": {}})
        decisions["fable"] = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    complete = all(
        decisions.get(key, {}).get("verdict") in {"PASS", "FAIL"}
        for key in ("sol", "fable")
    )
    artifact = sealed_artifact(
        "s210_frontier_design_decision_reviews_v1",
        {
            "status": "COMPLETE" if complete else "INCOMPLETE_NO_FURTHER_RETRY",
            "subject": BRIEF.relative_to(ROOT).as_posix(),
            "subject_sha256": hashlib.sha256(BRIEF.read_bytes()).hexdigest(),
            "decisions": decisions,
            "receipts": receipts,
            "conservative_cost_usd": conservative_cost(receipts, PRICES),
            "provider_retries": 0,
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
