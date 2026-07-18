#!/usr/bin/env python3
"""Thin adapter over the compact Sol+Fable gate for S212 overflow policy."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s211_review_rerun_gate as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402


BRIEF = ROOT / "evals/s212_frontier_overflow_gate_brief_v1.md"
OUTPUT = ROOT / "evals/s212_frontier_overflow_gate_reviews_v1.json"


def main() -> int:
    engine.BRIEF = BRIEF
    engine.OUTPUT = OUTPUT
    status = engine.main()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s212_frontier_overflow_gate_reviews_v1"
    payload["decision_scope"] = "DETERMINISTIC_FIRST_16_CAN_LOSE_RECALL_NOT_FALSE_GO"
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUTPUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
