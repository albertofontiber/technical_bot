#!/usr/bin/env python3
"""Run the frozen S210 scorer over a complete fresh S211 result matrix."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_score_query_evidence_compiler as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402


PREFLIGHT = ROOT / "evals/s211_query_evidence_compiler_preflight_v1.json"
RECEIPTS = ROOT / "evals/s211_query_evidence_compiler_receipts_v1.json"
OUT = ROOT / "evals/s211_query_evidence_compiler_score_v1.json"


def main() -> int:
    engine.PREFLIGHT = PREFLIGHT
    engine.RECEIPTS = RECEIPTS
    engine.OUT = OUT
    status = engine.main()
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s211_query_evidence_compiler_score_v1"
    payload["lineage"] = {
        "scorer": "S210_FROZEN_GATE",
        "s210_partial_result_scored": False,
        "fresh_generalization_evidence": False,
    }
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
