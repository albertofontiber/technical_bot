from scripts.s167_author_quote_transport_attribution import build, token_coverage


def test_s167_attribution_never_grants_posthoc_credit():
    source = {
        "items": [
            {
                "item_id": "i1",
                "stratum": "table",
                "excerpt": "| A | B |\n| --- | --- |\n| 1 | 2 |",
            }
        ]
    }
    receipts = {
        "receipts": [
            {
                "item_id": "i1",
                "validation_error": "not exact",
                "raw_text": '{"eligible":true,"answer_points":[{"exact_quote":"A B"}]}',
            }
        ]
    }
    result = build(source, receipts, {"status": "NO_GO", "cost": {"total_usd": 0.1}})
    assert result["population"]["failed_exact_quote_points"] == 1
    assert result["decision"]["s167_credit"] is False
    assert result["decision"]["same_cohort_retry"] is False
    assert result["decision"]["source_unit_id_bound_gold_successor"] is True


def test_s167_token_coverage_is_diagnostic_only():
    assert token_coverage("configure output 5", "Configure the output to 5 V") == 1.0
