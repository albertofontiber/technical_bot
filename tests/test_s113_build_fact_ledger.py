import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_s113_partial_ledger_is_complete_and_rest_is_explicit():
    ledger = json.loads((ROOT / "evals/s113_fact_ledger_v1.json").read_text(encoding="utf-8"))
    rest = yaml.safe_load((ROOT / "evals/s113_rest_decomposition_v1.yaml").read_text(encoding="utf-8"))
    summary = ledger["summary"]
    assert summary["fact_rows"] == 129
    assert summary["stage_compatible_partial_headline"] == {
        "OK": 106,
        "synthesis-miss": 13,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 8,
    }
    assert summary["root_cause_corrected_partial_work_queue"] == {
        "OK": 106,
        "synthesis-miss": 4,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 17,
    }
    assert sum(rest["histogram"].values()) == rest["total"] == 17
    assert rest["histogram"]["evidence-partial-hold"] == 5
