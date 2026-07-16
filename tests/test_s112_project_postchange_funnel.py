import json
from pathlib import Path

import yaml

from scripts.s112_project_postchange_funnel import project_funnel


ROOT = Path(__file__).resolve().parents[1]


def test_projection_is_a_complete_partition_and_matches_preregistered_transitions():
    baseline = yaml.safe_load(
        (ROOT / "evals/s100_factlevel_full.yaml").read_text(encoding="utf-8")
    )
    contract = yaml.safe_load(
        (ROOT / "evals/s112_postchange_transition_contract_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    local_gate = json.loads(
        (ROOT / "evals/s112_answer_planner_local_replay_v1.json").read_text(
            encoding="utf-8"
        )
    )
    result = project_funnel(baseline, contract, local_gate)
    assert result["candidate_headline_histogram"] == {
        "OK": 106,
        "synthesis-miss": 15,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 6,
    }
    assert sum(result["candidate_headline_histogram"].values()) == 129
    assert result["transitions_applied"] == 21
    assert result["conservative_ok_rate_percent"] == 83.46
