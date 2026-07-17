from __future__ import annotations

from copy import deepcopy

from src.rag.principal_visual_gold import principal_publication_gate


def _review():
    return {
        "reviews": [
            {
                "canary_id": "fresh-1",
                "verdict": "PASS",
                "question_fully_answerable": True,
                "question_duplicate": False,
                "topic_aligned": True,
                "gold_complete": True,
                "counterpart_materially_agrees": True,
                "material_disagreements": [],
                "unsupported_answer_claims": [],
                "blocking_issues": [],
                "nonblocking_notes": [],
                "fact_verdicts": [
                    {
                        "fact_id": "F01",
                        "supported": True,
                        "page_correct": True,
                        "answer_entails": True,
                        "notes": "",
                    }
                ],
            }
        ]
    }


def test_principal_publication_gate_ignores_counterpart_only_defect():
    principal = _review()
    counterpart = deepcopy(principal)
    counterpart["reviews"][0]["verdict"] = "FAIL"
    counterpart["reviews"][0]["gold_complete"] = False
    counterpart["reviews"][0]["blocking_issues"] = [
        "The non-final counterpart omits a warning."
    ]
    assert principal_publication_gate(principal, counterpart)


def test_principal_publication_gate_fails_final_or_material_disagreement():
    principal = _review()
    counterpart = _review()

    failed_principal = deepcopy(principal)
    failed_principal["reviews"][0]["verdict"] = "FAIL"
    failed_principal["reviews"][0]["gold_complete"] = False
    failed_principal["reviews"][0]["blocking_issues"] = ["Final gold incomplete."]
    assert not principal_publication_gate(failed_principal, counterpart)

    disagreement = deepcopy(counterpart)
    disagreement["reviews"][0]["counterpart_materially_agrees"] = False
    disagreement["reviews"][0]["material_disagreements"] = [
        "The candidates assign different terminals."
    ]
    assert not principal_publication_gate(principal, disagreement)


def test_principal_publication_gate_requires_counterpart_topic_alignment():
    counterpart = _review()
    counterpart["reviews"][0]["topic_aligned"] = False
    assert not principal_publication_gate(_review(), counterpart)
