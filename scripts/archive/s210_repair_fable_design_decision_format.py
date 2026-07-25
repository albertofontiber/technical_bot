#!/usr/bin/env python3
"""One schema-enforced Fable re-emission after the S210 local format rejection."""
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
    _parse,
    _prompt,
    _schema,
)
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    sealed_artifact,
    usage_dict,
    write_json,
)


ORIGINAL = ROOT / "evals/s210_frontier_design_decision_reviews_v1.json"
OUTPUT = ROOT / "evals/s210_fable_design_decision_format_repair_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("S210 Fable format-repair artifact already exists")
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    expected = {
        "status": "INVALID",
        "reason": "residual risks invalid",
    }
    observed = original.get("decisions", {}).get("fable", {})
    if any(observed.get(key) != value for key, value in expected.items()):
        raise RuntimeError("S210 does not have the exact eligible local format rejection")
    if original.get("decisions", {}).get("sol", {}).get("verdict") != "PASS":
        raise RuntimeError("S210 principal review is not PASS")
    if original.get("subject_sha256") != file_sha(BRIEF):
        raise RuntimeError("S210 compact brief drift")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("missing ANTHROPIC_API_KEY")

    receipt = {"provider": "fable", "model": FABLE_MODEL, "status": "ERROR", "usage": {}}
    decision = {"status": "INCOMPLETE"}
    try:
        response = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
        ).messages.create(
            model=FABLE_MODEL,
            max_tokens=3000,
            system=(
                "Return only the JSON object required by the supplied schema. "
                "Do not add markdown or more than six residual risks."
            ),
            messages=[{"role": "user", "content": _prompt(FABLE_MODEL)}],
            output_config={
                "format": {"type": "json_schema", "schema": _schema(FABLE_MODEL)}
            },
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
        decision = (
            _parse(raw, FABLE_MODEL)
            if receipt["model"] == FABLE_MODEL and receipt["status"] == "end_turn"
            else {"status": "INCOMPLETE"}
        )
    except Exception as exc:
        decision = {"status": "TRANSPORT_ERROR", "error_type": type(exc).__name__}

    valid = decision.get("verdict") in {"PASS", "FAIL"}
    artifact = sealed_artifact(
        "s210_fable_design_decision_format_repair_v1",
        {
            "status": "COMPLETE" if valid else "INCOMPLETE_FINAL",
            "original_review_sha256": file_sha(ORIGINAL),
            "subject": BRIEF.relative_to(ROOT).as_posix(),
            "subject_sha256": file_sha(BRIEF),
            "eligibility": "LOCAL_MAX_ITEMS_REJECTION_ONLY",
            "decision": decision,
            "receipt": receipt,
            "conservative_cost_usd": conservative_cost([receipt], PRICES),
            "provider_retries": 0,
            "format_repair_calls": 1,
            "further_design_review_calls": False,
        },
    )
    write_json(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "fable_verdict": decision.get("verdict"),
                "cost": artifact["conservative_cost_usd"],
            },
            indent=2,
        )
    )
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
