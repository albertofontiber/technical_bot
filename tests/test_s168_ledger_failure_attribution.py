import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s168_attribution_preserves_no_go_and_counterfactual_cannot_pass():
    value = json.loads(
        (ROOT / "evals/s168_ledger_failure_attribution_v1.json").read_text(encoding="utf-8")
    )
    assert value["status"] == "SEMANTIC_NO_GO_NOT_EXPLAINED_BY_TRANSPORT"
    assert value["decision"]["s168_credit"] is False
    assert value["decision"]["same_cohort_retry"] is False
    assert value["invalid_selector_counterfactual"]["claim_recall_if_only_cardinality_cap_ignored"] < 0.90
    assert value["invalid_selector_counterfactual"]["question_complete_rate_upper_bound_if_only_invalid_row_recovered"] < 0.75
