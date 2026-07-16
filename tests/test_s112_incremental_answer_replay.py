from scripts.s112_incremental_answer_replay import (
    assert_checkpoint_compatible,
    merge_support_packets,
    reusable_prior,
)


def test_reuses_only_complete_byte_equivalent_prompt():
    prior = {
        "qid": "q1",
        "question_sha256": "question",
        "serving_context_sha256": "context",
        "answer": "paid",
    }
    assert reusable_prior(
        prior,
        question_sha256="question",
        serving_context_sha256="context",
        system_prompt_sha256="system",
        prior_system_prompt_sha256="system",
    )["answer"] == "paid"
    assert reusable_prior(
        prior,
        question_sha256="changed",
        serving_context_sha256="context",
        system_prompt_sha256="system",
        prior_system_prompt_sha256="system",
    ) is None
    assert reusable_prior(
        prior,
        question_sha256="question",
        serving_context_sha256="changed",
        system_prompt_sha256="system",
        prior_system_prompt_sha256="system",
    ) is None
    assert reusable_prior(
        prior,
        question_sha256="question",
        serving_context_sha256="context",
        system_prompt_sha256="changed",
        prior_system_prompt_sha256="system",
    ) is None


def test_checkpoint_mismatch_refuses_repeat_spend():
    row = {
        "qid": "q1",
        "question_sha256": "question",
        "serving_context_sha256": "context",
        "system_prompt_sha256": "system",
    }
    assert_checkpoint_compatible(
        row,
        question_sha256="question",
        serving_context_sha256="context",
        system_prompt_sha256="system",
    )
    try:
        assert_checkpoint_compatible(
            row,
            question_sha256="question",
            serving_context_sha256="changed",
            system_prompt_sha256="system",
        )
    except RuntimeError as error:
        assert "refusing repeat spend" in str(error)
    else:
        raise AssertionError("stale checkpoint was accepted")


def test_s111_support_receipts_extend_existing_claim_packet():
    cohort = {
        "residual_rerank_claims": [
            {"claim_id": "claim", "qid": "q1", "support_any": [["old"]]}
        ]
    }
    served = {
        "claims": [
            {"claim_id": "claim", "qid": "q1", "support_any": [{"ids": ["new"]}]}
        ]
    }
    merged = merge_support_packets(cohort, served)
    assert merged == [
        {
            "claim_id": "claim",
            "qid": "q1",
            "support_any": [["new"], ["old"]],
        }
    ]
