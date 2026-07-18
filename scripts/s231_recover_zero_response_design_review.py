#!/usr/bin/env python3
"""Single frozen recovery after the zero-response S230 OpenAI 520."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s230_review_fresh_clause_bound_design as base


base.PREREG = base.ROOT / "evals/s231_zero_response_recovery_prereg_v1.yaml"
base.LEDGER = base.ROOT / "evals/s231_design_frontier_call_ledger_v1.json"
base.ATTEMPTS = base.ROOT / "evals/s231_design_frontier_attempts_v1.json"
base.RESULT = base.ROOT / "evals/s231_design_frontier_reviews_v1.json"


if __name__ == "__main__":
    raise SystemExit(base.main())
