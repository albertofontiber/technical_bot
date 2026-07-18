#!/usr/bin/env python3
"""One compact Sol xhigh + Fable decision on the S214 execution design."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s211_review_rerun_gate as engine  # noqa: E402
from src.rag.visual_gold import normalized_text_sha, stable_sha  # noqa: E402


BRIEF = ROOT / "evals/s214_frontier_design_gate_brief_v1.md"
OUTPUT = ROOT / "evals/s214_frontier_design_gate_reviews_v1.json"


def main() -> int:
    engine.BRIEF = BRIEF
    engine.OUTPUT = OUTPUT
    status = engine.main()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s214_frontier_design_gate_reviews_v1"
    payload["decision_scope"] = "S214_FRESH_MULTISOURCE_GOLD_EXECUTION_ONLY"
    payload["subject_normalized_sha256"] = normalized_text_sha(BRIEF)
    payload["principal_reviewer"] = {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }
    payload["independent_reviewer"] = {"model": "claude-fable-5"}
    payload["further_design_review_calls"] = False
    body = payload
    OUTPUT.write_text(
        json.dumps({**body, "result_sha256": stable_sha(body)}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
