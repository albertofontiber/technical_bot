import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s170_transport_attribution_forbids_same_cohort_and_third_iteration():
    value = json.loads((ROOT / "evals/s170_relation_store_transport_attribution_v1.json").read_text(encoding="utf-8"))
    assert value["decision"]["s170_credit"] is False
    assert value["decision"]["same_cohort_retry"] is False
    assert value["decision"]["different_existing_development_cohort"] == "S147"
    assert value["decision"]["third_transport_iteration_if_successor_fails"] is False
    assert value["population"]["selector_calls"] == 0
