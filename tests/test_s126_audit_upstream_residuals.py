from scripts.s126_audit_upstream_residuals import build_payload


def test_s126_population_and_reconciliation_are_exact():
    payload = build_payload()
    population = payload["population"]
    assert population["exact_count"] == 7
    assert population["reconciled_stage_histogram"] == {
        "retrieval-miss": 4,
        "source-contract-hold": 1,
        "synthesis-miss": 2,
    }
    assert len({row["claim_id"] for row in population["rows"]}) == 7
    assert all(row["bot_improvement_credit"] == 0 for row in population["rows"])


def test_s126_removes_opaque_rest_without_manufacturing_ok_credit():
    diagnostic = build_payload()["provisional_reconciled_diagnostic"]
    assert diagnostic == {
        "content_denominator": 157,
        "stage_histogram": {
            "OK": 111,
            "retrieval-miss": 4,
            "source-contract-hold": 1,
            "synthesis-miss": 14,
            "synthesis-not-measured": 27,
        },
        "rest_count": 0,
        "facts_moved_to_ok_due_to_bot_change": 0,
        "official_atomic_kpi": None,
    }


def test_s126_identity_and_doc_binding_findings_are_reproduced():
    findings = build_payload()["identity_and_metadata_findings"]
    assert findings["rp1r_governed_resolution"]["valid"] is True
    assert findings["rp1r_governed_resolution"]["resolved_ids"] == [
        "notifier:rp1r-supra"
    ]
    assert findings["midt190_has_sdx751_secondary_binding"] is True
    assert findings["midt190_binding_consequence"] == (
        "accepted_s97_binding_ported_after_frozen_context"
    )
