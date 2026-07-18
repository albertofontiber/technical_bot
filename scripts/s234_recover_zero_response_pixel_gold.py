#!/usr/bin/env python3
"""Single exact S234 recovery after S233 returned zero model responses."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s233_run_fresh_kidde_pixel_gold as base  # noqa: E402
from src.rag.visual_gold import write_json


ROOT = base.ROOT


def _rename(value):
    if isinstance(value, dict):
        return {key: _rename(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rename(item) for item in value]
    if isinstance(value, str):
        return value.replace("S217", "S234").replace("s217", "s234")
    return value


def _checkpoint_attempt(label: str) -> None:
    body = {"schema": "s234_frontier_attempts_v1", "attempts": []}
    if base.ATTEMPTS.exists():
        body = json.loads(base.ATTEMPTS.read_text(encoding="utf-8"))
    body["attempts"].append({"call_label": label, "status": "STARTED_NO_RETRY"})
    write_json(base.ATTEMPTS, body)


base.PREREG = ROOT / "evals/s234_zero_response_pixel_gold_recovery_prereg_v1.yaml"
base.ATTEMPTS = ROOT / "evals/s234_frontier_attempts_v1.json"
base.LEDGER = ROOT / "evals/s234_frontier_call_ledger_v1.json"
base.SOL_GENERATIONS = ROOT / "evals/s234_kidde_sol_generations_v1.json"
base.FABLE_GENERATIONS = ROOT / "evals/s234_kidde_fable_generations_v1.json"
base.SOL_REVIEWS = ROOT / "evals/s234_kidde_sol_reviews_of_fable_v1.json"
base.FABLE_REVIEWS = ROOT / "evals/s234_kidde_fable_reviews_of_sol_v1.json"
base.PIXEL_GOLD = ROOT / "evals/s234_kidde_pixel_gold_v1.json"
base.SOL_MAPPINGS = ROOT / "evals/s234_kidde_sol_support_mappings_v1.json"
base.FABLE_SUPPORT_REVIEWS = ROOT / "evals/s234_kidde_fable_support_reviews_v1.json"
base.SUPPORTED_GOLD = ROOT / "evals/s234_kidde_supported_gold_v1.json"
base.RESULT = ROOT / "evals/s234_kidde_pixel_gold_result_v1.json"
base._rename = _rename
base._checkpoint_attempt = _checkpoint_attempt


if __name__ == "__main__":
    raise SystemExit(base.main())
