from pathlib import Path

import yaml

from scripts.s112_project_guided_synthesis_funnel import project_guided_synthesis_funnel


ROOT = Path(__file__).resolve().parents[1]


def _yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_projection_separates_comparable_funnel_from_corrected_work_queue():
    result = project_guided_synthesis_funnel(
        _yaml("evals/s100_factlevel_full.yaml"),
        _yaml("evals/s112_postchange_transition_contract_v1.yaml"),
        _yaml("evals/s112_guided_synthesis_manual_review_v1.yaml"),
        _yaml("evals/s112_synthesis_root_cause_audit_v1.yaml"),
    )
    assert result["stage_compatible_headline_histogram"] == {
        "OK": 110,
        "synthesis-miss": 11,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 6,
    }
    assert result["root_cause_corrected_work_queue"] == {
        "OK": 110,
        "synthesis-miss": 2,
        "rerank-miss": 1,
        "retrieval-miss": 1,
        "rest": 15,
    }
    assert result["validated_synthesis_delta_ok"] == 4
    assert result["candidate_ok_rate_percent"] == 86.61
    assert result["additional_ok_needed_for_95_percent"] == 11
    assert sum(result["stage_compatible_headline_histogram"].values()) == 129
    assert sum(result["root_cause_corrected_work_queue"].values()) == 129
