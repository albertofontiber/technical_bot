from scripts.s169_synthesis_architecture_review import OPTIONS, build_packet, validate_review


def test_s169_packet_exposes_decision_evidence_without_targets():
    packet = build_packet()
    assert packet["current_funnel"]["synthesis_miss"] == 12
    assert packet["current_funnel"]["retrieval_miss"] == 4
    assert len(packet["options"]) == 5
    assert "target_questions" not in packet


def test_s169_review_requires_all_options_once():
    value = {
        "generic_ledger_verdict": "STOP",
        "recommended_option": OPTIONS[1],
        "option_assessments": [
            {"option_id": option, "verdict": "GO" if option == OPTIONS[1] else "NO_GO", "rationale": "bounded", "primary_risk": "risk"}
            for option in OPTIONS
        ],
        "minimum_experiment": {
            "scope": "local", "manufacturers_min": 10, "documents_min": 10,
            "paid_calls_max": 20, "success_criteria": ["recall"], "kill_criteria": ["under coverage"],
        },
        "findings": [],
        "rationale": "Stop and test the structurally distinct option.",
    }
    validate_review(value)
