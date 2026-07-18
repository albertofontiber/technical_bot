#!/usr/bin/env python3
"""Score sealed S220 outputs under a score-only frozen authorization."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.s219_score_omission_pilot as base  # noqa: E402
from src.rag.visual_gold import sealed_artifact, write_json  # noqa: E402


PREREG = ROOT / "evals/s221_s220_omission_score_prereg_v1.yaml"
GENERATION = ROOT / "evals/s220_omission_generation_result_v1.json"
RESULT = ROOT / "evals/s221_s220_omission_pilot_result_v1.json"


def main() -> int:
    base.PREREG = PREREG
    base.GENERATION = GENERATION
    base.RESULT = RESULT
    code = base.main()
    value = json.loads(RESULT.read_text(encoding="utf-8"))
    value.pop("result_sha256", None)
    value.pop("schema", None)
    value["status"] = str(value["status"]).replace("S219", "S221")
    value["scored_generation"] = "S220_COMPLETE_SCORE_NOT_OPENED"
    write_json(
        RESULT,
        sealed_artifact("s221_s220_omission_pilot_result_v1", value),
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
