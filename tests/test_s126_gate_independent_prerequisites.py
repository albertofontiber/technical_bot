from scripts.s126_gate_independent_prerequisites import build_payload


def test_s126_independent_prerequisite_gate_is_inconclusive_not_go():
    payload = build_payload()
    assert payload["gate"] == "INCONCLUSIVE_NOT_GO"
    assert payload["checks"] == {
        "positive_opportunities_at_least_two": True,
        "positive_manufacturers_at_least_two": False,
        "both_facets_exercised": False,
        "zero_scanner_false_positives": False,
    }
    assert payload["authorization"]["procedure_prerequisite_serving_integration"] is False
    assert payload["authorization"]["known_cohort_retrieval_credit"] == 2
    assert payload["authorization"]["facts_moved_to_ok"] == 0


def test_s126_independent_prerequisite_gate_reports_exact_limitations():
    applicability = build_payload()["applicability"]
    assert applicability == {
        "positive_opportunities": 5,
        "positive_manufacturers": ["Hochiki"],
        "access_positive_opportunities": 5,
        "quantified_entitlement_positive_opportunities": 0,
        "scanner_false_positives": 1,
    }
