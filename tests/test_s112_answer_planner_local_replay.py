from scripts.s112_answer_planner_local_replay import (
    protected_fact_present,
    semantic_adjudication,
)


def test_protected_match_normalizes_number_words_without_model_call():
    fact = {
        "valor": "seis tipos de retardo",
        "texto": "Hay seis tipos de retardo de salida",
    }
    present, method = protected_fact_present(
        fact, "Dentro de la regla hay 6 tipos de retardo disponibles."
    )
    assert present is True
    assert "number_word_normalization" in method


def test_semantic_review_is_bound_to_exact_answer_hash():
    review = {
        "adjudications": [
            {
                "qid": "q1",
                "fact_key": "q1#0:value",
                "answer_sha256": "abc",
                "verdict": "pass",
            }
        ]
    }
    assert semantic_adjudication(
        review, qid="q1", fact_key="q1#0:value", answer_sha256="abc"
    )
    assert semantic_adjudication(
        review, qid="q1", fact_key="q1#0:value", answer_sha256="changed"
    ) is None
