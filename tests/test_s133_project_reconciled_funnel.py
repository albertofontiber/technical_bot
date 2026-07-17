import copy
import json
from pathlib import Path

import pytest
import yaml

from scripts.s133_project_reconciled_funnel import project_funnel


ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    s126 = json.loads(
        (ROOT / "evals/s126_upstream_residual_audit_v1.json").read_text(encoding="utf-8")
    )
    s133 = yaml.safe_load(
        (ROOT / "evals/s133_unmeasured_fact_adjudication_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    return s126, s133


def test_projection_closes_unmeasured_without_claiming_bot_improvement():
    s126, s133 = _inputs()
    payload = project_funnel(s126, s133)
    diagnostic = payload["reconciled_diagnostic"]
    assert diagnostic["content_denominator"] == 157
    assert diagnostic["stage_histogram"] == {
        "OK": 134,
        "retrieval-miss": 4,
        "source-contract-hold": 1,
        "synthesis-miss": 18,
    }
    assert diagnostic["ok_rate_percent"] == 85.35
    assert diagnostic["target_ok_for_95_percent"] == 150
    assert diagnostic["gap_to_95_percent"] == 16
    assert payload["bridge"]["facts_moved_to_ok_due_to_bot_change"] == 0


def test_projection_rejects_partial_or_incompatible_adjudication():
    s126, s133 = _inputs()
    partial = copy.deepcopy(s133)
    partial["rows"].pop()
    with pytest.raises(RuntimeError, match="histogram drift|exact unmeasured"):
        project_funnel(s126, partial)
