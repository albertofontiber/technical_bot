from scripts.s112_freeze_synthesis_contexts import synthesis_rows


def test_synthesis_rows_preserves_served_order_and_applies_transition():
    baseline = {
        "per_gold": [
            {
                "qid": "q1",
                "question": "question",
                "answer": "answer",
                "served_ids": ["b", "a"],
                "facts": [
                    {"key": "q1#0:x", "clase": "retrieval-miss"},
                    {"key": "q1#1:y", "clase": "OK"},
                ],
            }
        ]
    }
    contract = {
        "transitions": {"q1#0:x": {"candidate": "synthesis-miss", "evidence": "e"}}
    }
    rows = synthesis_rows(baseline, contract, {"a": {"id": "a"}, "b": {"id": "b"}})
    assert [chunk["id"] for chunk in rows[0]["served_context"]] == ["b", "a"]
    assert [fact["key"] for fact in rows[0]["synthesis_facts"]] == ["q1#0:x"]


def test_latest_context_override_takes_precedence_over_baseline_and_appends():
    baseline = {
        "per_gold": [
            {
                "qid": "q1",
                "question": "question",
                "answer": "answer",
                "served_ids": ["old"],
                "facts": [{"key": "q1#0:x", "clase": "synthesis-miss"}],
            }
        ]
    }
    rows = synthesis_rows(
        baseline,
        {"transitions": {}},
        {"old": {"id": "old"}},
        context_overrides={"q1": [{"id": "latest"}]},
        context_appends={"q1": [{"id": "append"}]},
    )
    assert [row["id"] for row in rows[0]["served_context"]] == ["latest"]
