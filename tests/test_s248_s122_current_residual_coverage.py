from scripts.s248_audit_s122_current_residual_coverage import build_report


def test_s122_does_not_cover_current_residuals() -> None:
    report = build_report()
    assert report["measurement"] == {
        "residual_plan_coverage": 1,
        "residual_enforced_coverage": 0,
        "fail_closed_questions": 1,
        "canonical_answers_changed": 1,
    }
    assert report["candidate_gate_passed"] is False
    by_qid = {row["qid"]: row for row in report["rows"]}
    assert by_qid["hp017"]["enforcement_action"] == "fail_closed"
    assert by_qid["hp017"]["residual_enforced_hits"] == []

