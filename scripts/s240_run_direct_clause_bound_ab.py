#!/usr/bin/env python3
"""Run S235's frozen A/B protocol with S240's provider/local planner parity fix."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s235_run_direct_clause_bound_ab as experiment  # noqa: E402

experiment.PREREG = ROOT / "evals/s240_direct_clause_bound_ab_prereg_v1.yaml"
experiment.PERMIT = ROOT / "evals/s240_direct_clause_bound_ab_execution_permit_v1.yaml"
experiment.OUT = ROOT / "evals/s240_direct_clause_bound_generation_v1.json"
experiment.LEDGER = ROOT / "evals/s240_direct_clause_bound_call_ledger_v1.json"


if __name__ == "__main__":
    raise SystemExit(experiment.main())

