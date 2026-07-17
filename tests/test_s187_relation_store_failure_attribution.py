from scripts.s187_relation_store_failure_attribution import build


def test_relation_store_failure_attribution_is_mece_and_frozen():
    result = build()
    assert result["extraction_oracle"]["claims_covered"] == 34
    assert result["frozen_selector"]["claims_covered"] == 28
    assert result["miss_attribution"] == {
        "extraction_limited_claims": 3,
        "selector_limited_claims": 6,
        "total_missed_claims": 9,
    }
    assert result["decision"]["target_probe"] is False
    assert result["decision"]["facts_moved_to_ok"] == 0
