#!/usr/bin/env python3
"""Minimal final Fable verdict after one lost local parse and one zero-call 400."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import anthropic


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s210_review_design_decision_card import (  # noqa: E402
    BRIEF,
    FABLE_MODEL,
    PRICES,
    _prompt,
)
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    parse_json,
    sealed_artifact,
    usage_dict,
    write_json,
)


ORIGINAL = ROOT / "evals/s210_frontier_design_decision_reviews_v1.json"
ZERO_CALL_REPAIR = ROOT / "evals/s210_fable_design_decision_format_repair_v1.json"
OUTPUT = ROOT / "evals/s210_fable_final_design_verdict_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate(value: dict) -> None:
    if set(value) != {"reviewer", "verdict", "blocking_findings"}:
        raise ValueError("minimal verdict shape mismatch")
    if value["reviewer"] != FABLE_MODEL or value["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("minimal verdict identity mismatch")
    blockers = value["blocking_findings"]
    if not isinstance(blockers, list) or len(blockers) > 2:
        raise ValueError("minimal blocker list invalid")
    if any(not isinstance(item, str) or not item.strip() for item in blockers):
        raise ValueError("minimal blocker invalid")
    if (value["verdict"] == "PASS") != (not blockers):
        raise ValueError("minimal verdict/blocker inconsistency")


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S210 final Fable verdict already exists")
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    repair = json.loads(ZERO_CALL_REPAIR.read_text(encoding="utf-8"))
    if original.get("decisions", {}).get("fable", {}).get("reason") != "residual risks invalid":
        raise RuntimeError("S210 original local parse failure drift")
    if repair.get("decision") != {
        "status": "TRANSPORT_ERROR",
        "error_type": "BadRequestError",
    } or repair.get("conservative_cost_usd") != 0.0:
        raise RuntimeError("S210 zero-call schema rejection drift")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("missing ANTHROPIC_API_KEY")

    raw = ""
    receipt = {"provider": "fable", "model": FABLE_MODEL, "status": "ERROR", "usage": {}}
    decision: dict = {"status": "INCOMPLETE"}
    try:
        response = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
        ).messages.create(
            model=FABLE_MODEL,
            max_tokens=1200,
            system=(
                "Return exactly one JSON object with keys reviewer, verdict, and "
                "blocking_findings. No markdown, analysis, risks, or extra keys. "
                "reviewer is claude-fable-5; verdict is PASS or FAIL; blocking_findings "
                "is an array of at most two short strings and must be empty for PASS."
            ),
            messages=[{"role": "user", "content": _prompt(FABLE_MODEL)}],
        )
        receipt = {
            "provider": "fable",
            "model": getattr(response, "model", None),
            "status": getattr(response, "stop_reason", None),
            "usage": usage_dict(response),
        }
        raw = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        if receipt["model"] == FABLE_MODEL and receipt["status"] == "end_turn":
            try:
                decision = parse_json(raw)
                _validate(decision)
            except (ValueError, json.JSONDecodeError) as exc:
                decision = {"status": "INVALID", "reason": str(exc)}
        else:
            decision = {"status": "INCOMPLETE"}
    except Exception as exc:
        decision = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    valid = decision.get("verdict") in {"PASS", "FAIL"}
    artifact = sealed_artifact(
        "s210_fable_final_design_verdict_v1",
        {
            "status": "COMPLETE" if valid else "INCOMPLETE_FINAL",
            "subject": BRIEF.relative_to(ROOT).as_posix(),
            "subject_sha256": file_sha(BRIEF),
            "original_review_sha256": file_sha(ORIGINAL),
            "zero_call_repair_sha256": file_sha(ZERO_CALL_REPAIR),
            "decision": decision,
            "receipt": receipt,
            "raw_text": raw,
            "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "conservative_cost_usd": conservative_cost([receipt], PRICES),
            "provider_retries": 0,
            "further_design_review_calls": False,
        },
    )
    write_json(OUTPUT, artifact)
    print(json.dumps({"status": artifact["status"], "verdict": decision.get("verdict")}))
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
