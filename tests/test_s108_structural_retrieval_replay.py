import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from s108_structural_retrieval_replay import (  # noqa: E402
    _same_family,
    evaluate_retrieval_facts,
)


def test_family_matching_is_normalized_but_not_cross_product():
    assert _same_family("FAAST LT-200", ["LT-200"])
    assert _same_family("RP1R-SUPRA", ["RP1R SUPRA"])
    assert not _same_family("ASD11", ["FAAST LT-200", "LT-200"])


def test_fact_evaluation_happens_on_selected_rows_and_excludes_cross_family():
    baseline = [
        {
            "qid": "q1",
            "gold_families": ["ADW535"],
            "facts": [
                {
                    "key": "q1#0:PWR-R",
                    "valor": "PWR-R",
                    "texto": "PWR-R es la entrada de alimentacion redundante",
                    "clase": "retrieval-miss",
                },
                {
                    "key": "q1#1:EEPROM",
                    "valor": "EEPROM",
                    "texto": "memoria de configuracion",
                    "clase": "rerank-miss",
                },
            ],
        }
    ]
    selections = [
        {
            "qid": "q1",
            "selected": [
                {
                    "id": "same-family",
                    "rank": 1,
                    "product_model": "ADW535",
                    "content": "PWR-R = entrada de alimentacion redundante",
                    "content_sha256": "same",
                },
                {
                    "id": "cross-family",
                    "rank": 2,
                    "product_model": "OTHER",
                    "content": "PWR-R = entrada de alimentacion redundante",
                    "content_sha256": "cross",
                },
            ],
        }
    ]

    evaluated = evaluate_retrieval_facts(baseline, selections)

    assert len(evaluated) == 1
    assert evaluated[0]["structural_retrieval_precondition"] is True
    assert evaluated[0]["same_family_supporting_ids"] == ["same-family"]
    assert {row["chunk_id"] for row in evaluated[0]["matching_candidates"]} == {
        "same-family",
        "cross-family",
    }
