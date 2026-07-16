import json
from pathlib import Path

from scripts.s114_procedure_bundle_replay import build_payload


ROOT = Path(__file__).resolve().parents[1]


def test_s114_shadow_replay_recovers_three_retrieval_misses_without_touching_holds():
    frozen = json.loads(
        (ROOT / "evals/s114_procedure_bundle_replay_v1.json").read_text(encoding="utf-8")
    )
    data = build_payload()
    assert data == frozen
    gate = data["gate"]
    assert gate["interpretation"] == "GO_LOCAL_KNOWN_COHORT_SHADOW"
    assert gate["target_recovered_count"] == 3
    assert all(gate["target_recovered"].values())
    assert all(gate["protected_evaluation_holds_unchanged"].values())
    assert gate["questions_with_shadow_appends"] == 3
    assert gate["product_scoped_non_target_controls"] == 5
    assert gate["selected_product_scoped_non_target_controls"] == 0
    assert gate["max_selected_per_question"] == 1
    assert gate["all_source_span_receipts_verified"]
    assert gate["model_calls"] == gate["database_writes"] == 0
