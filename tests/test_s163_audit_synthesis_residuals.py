from scripts.s163_audit_synthesis_residuals import run


def test_s163_reconciles_one_stale_carry_and_twelve_real_residuals():
    result = run()
    assert result["population"] == {
        "questions": 4,
        "relations": 13,
        "covered_in_current_frozen_answers": 1,
        "genuine_synthesis_residuals": 12,
        "diagnostic_categories": {
            "fully_covered": 1,
            "partial_relation": 6,
            "relation_omitted": 5,
            "internal_cardinality_contradiction": 1,
        },
    }
    assert result["measurement_bridge"]["stale_rows"] == [
        {"qid": "hp011", "kind": "default_latched_faults"}
    ]
    assert result["measurement_bridge"]["bot_improvement_credit"] == 0
    assert result["diagnostic_projection"]["stage_histogram"] == {
        "OK": 140,
        "retrieval-miss": 4,
        "document-extraction-hold": 1,
        "synthesis-miss": 12,
    }


def test_s163_cardinality_contradiction_is_not_counted_as_covered():
    result = run()
    row = next(
        row
        for row in result["rows"]
        if row["qid"] == "hp017" and row["kind"] == "option_family_cardinality"
    )
    assert row["covered"] is False
    assert row["diagnostic_category"] == "internal_cardinality_contradiction"
    assert row["source_fragment_cited"] is True
