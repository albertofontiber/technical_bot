import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_s164_gate_closes_generic_omission_correction_without_target_probe():
    gate = yaml.safe_load(
        (ROOT / "evals/s164_legacy_heldout_omission_canary_gate_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    result = json.loads(
        (ROOT / "evals/s164_legacy_heldout_omission_canary_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "NO_GO_GENERIC_POST_ANSWER_OMISSION_CORRECTION"
    assert result["metrics"]["point_gain"] == 0
    assert gate["local_semantic_attribution"]["semantic_point_gain"] == 0
    assert gate["local_semantic_attribution"]["selected_fragment_numbers"] == [4]
    assert gate["local_semantic_attribution"]["selected_units_from_query_aligned_fragments"] == 0
    assert gate["decision"]["larger_legacy_heldout_test"] == "forbidden"
    assert gate["decision"]["target_probe"] == "forbidden"
    assert gate["decision"]["facts_moved_to_ok"] == 0
