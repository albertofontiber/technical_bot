#!/usr/bin/env python3
"""Score the completed S240 generation with the frozen S235 scoring contract."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s235_score_direct_clause_bound_ab as scorer  # noqa: E402

scorer.GENERATION = ROOT / "evals/s240_direct_clause_bound_generation_v1.json"
scorer.OUT = ROOT / "evals/s240_direct_clause_bound_ab_result_v1.json"


if __name__ == "__main__":
    raise SystemExit(scorer.main())
