import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_s114_ledger_reclassifies_partial_evidence_without_inventing_ok_gain():
    ledger = json.loads((ROOT / "evals/s114_fact_ledger_v1.json").read_text(encoding="utf-8"))
    rest = yaml.safe_load((ROOT / "evals/s114_rest_decomposition_v1.yaml").read_text(encoding="utf-8"))
    assert ledger["summary"]["stage_compatible_partial_headline"] == {
        "OK": 106,
        "synthesis-miss": 13,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 8,
    }
    assert ledger["summary"]["root_cause_corrected_partial_work_queue"] == {
        "OK": 106,
        "synthesis-miss": 4,
        "rerank-miss": 1,
        "retrieval-miss": 4,
        "rest": 14,
    }
    assert rest["histogram"].get("evidence-partial-hold", 0) == 0
    assert rest["histogram"]["atomicity-and-absence-inference-hold"] == 2
    assert rest["actionable_rows"] == 8
    assert rest["evaluation_contract_rows"] == 6
