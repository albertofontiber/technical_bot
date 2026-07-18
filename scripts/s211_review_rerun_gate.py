#!/usr/bin/env python3
"""One compact Sol xhigh + Fable rerun-integrity decision for S211."""
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


BRIEF = ROOT / "evals/s211_frontier_rerun_gate_brief_v1.md"
OUTPUT = ROOT / "evals/s211_frontier_rerun_gate_reviews_v1.json"
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
                "maxItems": 2,
                "items": {"type": "string"},
            },
        },
        "required": ["reviewer", "verdict", "blocking_findings"],
    }


def _prompt(model: str) -> str:
    return (
        "Return one independent bounded decision. FAIL only for a concrete defect "
        "that can falsely produce diagnostic GO or violate the stated isolation. "
        "Do not request style work, more cohorts, external validation, or another "
        "review round at this gate. Return exactly reviewer, verdict, and at most "
        f"two blocking_findings; reviewer must be {model}.\n\n"
        + BRIEF.read_text(encoding="utf-8")
    )


def _validate(value: dict[str, Any], model: str) -> None:
    if set(value) != {"reviewer", "verdict", "blocking_findings"}:
        raise ValueError("decision shape mismatch")
    if value["reviewer"] != model or value["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("decision identity mismatch")
    blockers = value["blocking_findings"]
    if not isinstance(blockers, list) or len(blockers) > 2:
        raise ValueError("blocking findings invalid")
    if any(not isinstance(item, str) or not item.strip() for item in blockers):
        raise ValueError("blocking finding invalid")
    if (value["verdict"] == "PASS") != (not blockers):
        raise ValueError("verdict/blocker mismatch")


def _parse(raw: str, model: str) -> dict[str, Any]:
    try:
        value = parse_json(raw)
        _validate(value, model)
        return value
    except (ValueError, json.JSONDecodeError) as exc:
        return {"status": "INVALID", "reason": str(exc)}


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S211 rerun review already exists")
    missing = [key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    decisions: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []
    raw_text: dict[str, str] = {}

    try:
        response = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0).responses.create(
            model=SOL_MODEL,
            instructions="Return only the schema-conformant decision JSON.",
            input=_prompt(SOL_MODEL),
            reasoning={"effort": "xhigh"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "s211_rerun_integrity_decision",
                    "strict": True,
                    "schema": _schema(SOL_MODEL),
                }
            },
            max_output_tokens=6000,
            store=False,
        )
        receipt = {
            "provider": "sol",
            "model": getattr(response, "model", None),
            "status": getattr(response, "status", None),
            "usage": usage_dict(response),
        }
        receipts.append(receipt)
        raw_text["sol"] = (response.output_text or "").strip()
        decisions["sol"] = (
            _parse(raw_text["sol"], SOL_MODEL)
            if receipt["model"] == SOL_MODEL and receipt["status"] == "completed"
            else {"status": "INCOMPLETE"}
        )
    except Exception as exc:
        receipts.append({"provider": "sol", "model": SOL_MODEL, "status": "ERROR", "usage": {}})
        decisions["sol"] = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    try:
        response = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
        ).messages.create(
            model=FABLE_MODEL,
            max_tokens=1200,
            system=(
                "Return exactly one JSON object with reviewer, verdict, and "
                "blocking_findings. No markdown, risks, analysis, or extra keys."
            ),
            messages=[{"role": "user", "content": _prompt(FABLE_MODEL)}],
        )
        receipt = {
            "provider": "fable",
            "model": getattr(response, "model", None),
            "status": getattr(response, "stop_reason", None),
            "usage": usage_dict(response),
        }
        receipts.append(receipt)
        raw_text["fable"] = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        decisions["fable"] = (
            _parse(raw_text["fable"], FABLE_MODEL)
            if receipt["model"] == FABLE_MODEL and receipt["status"] == "end_turn"
            else {"status": "INCOMPLETE"}
        )
    except Exception as exc:
        receipts.append({"provider": "fable", "model": FABLE_MODEL, "status": "ERROR", "usage": {}})
        decisions["fable"] = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    complete = all(
        decisions.get(key, {}).get("verdict") in {"PASS", "FAIL"}
        for key in ("sol", "fable")
    )
    artifact = sealed_artifact(
        "s211_frontier_rerun_gate_reviews_v1",
        {
            "status": "COMPLETE" if complete else "INCOMPLETE_FINAL",
            "subject": BRIEF.relative_to(ROOT).as_posix(),
            "subject_sha256": hashlib.sha256(BRIEF.read_bytes()).hexdigest(),
            "decisions": decisions,
            "receipts": receipts,
            "raw_text": raw_text,
            "conservative_cost_usd": conservative_cost(receipts, PRICES),
            "provider_retries": 0,
            "further_rerun_review_calls": False,
        },
    )
    write_json(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "sol": decisions.get("sol", {}).get("verdict"),
                "fable": decisions.get("fable", {}).get("verdict"),
                "cost": artifact["conservative_cost_usd"],
            }
        )
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
