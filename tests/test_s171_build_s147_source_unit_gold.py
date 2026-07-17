import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s171_gold_is_zero_cost_and_matches_prior_mappability():
    value = json.loads((ROOT / "evals/s171_s147_source_unit_gold_v1.json").read_text(encoding="utf-8"))
    assert value["population"]["items"] == 14
    assert value["population"]["eligible_items"] == 14
    assert value["population"]["original_answer_points"] == 37
    assert value["population"]["mapped_answer_points"] == 37
    assert value["population"]["unmapped_answer_points"] == 0
    assert value["population"]["model_calls"] == 0
    assert all(point["support_unit_receipts"] for item in value["items"] for point in item["answer_points"])
