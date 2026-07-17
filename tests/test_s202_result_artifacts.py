from __future__ import annotations

import json

from scripts.s165_answer_archetype_ledger import stable_sha


def test_s202_result_and_diagnosis_are_sealed_contract_no_go():
    result = json.loads(
        open("evals/s202_real_question_gold_gate_v1.json", encoding="utf-8").read()
    )
    result_body = dict(result)
    result_sha = result_body.pop("result_sha256")
    assert stable_sha(result_body) == result_sha
    assert result["status"] == "NO_GO_DUAL_GOLD"
    assert result["measurement"] == {
        "author_calls": 12,
        "validator_calls": 12,
        "invalid_author_outputs": 0,
        "invalid_validator_outputs": 7,
        "semantic_disagreements": 0,
        "supported_points": 13,
        "total_points": 43,
    }
    assert result["decision"]["planner_opened"] is False
    assert result["decision"]["target_probe_opened"] is False
    assert result["decision"]["diagnostic_facts_moved_to_ok"] == 0
    assert result["cost"]["total_usd"] == 1.258906

    author = json.loads(
        open("evals/s202_gold_author_receipts_v1.json", encoding="utf-8").read()
    )
    validator = json.loads(
        open("evals/s202_gold_validator_receipts_v1.json", encoding="utf-8").read()
    )
    assert author["status"] == validator["status"] == "PAID_CHECKPOINT_COMPLETE"
    assert len(author["receipts"]) == len(validator["receipts"]) == 12
    assert author["invalid_outputs"] == 0
    errors = [row["validation_error"] for row in validator["receipts"]]
    assert errors.count("validator agrees but omits author support set") == 6
    assert errors.count("unknown ID inside validator support set") == 1

    diagnosis = json.loads(
        open("evals/s202_real_question_gold_diagnosis_v1.json", encoding="utf-8").read()
    )
    diagnosis_body = dict(diagnosis)
    diagnosis_sha = diagnosis_body.pop("result_sha256")
    assert stable_sha(diagnosis_body) == diagnosis_sha
    assert diagnosis["status"] == "CLOSED_CONTRACT_NO_GO"
    assert diagnosis["interpretation"]["dual_gold_semantics_measured"] is False
    assert diagnosis["decision"]["same_cohort_retry"] is False
    assert diagnosis["population_after_close"][
        "s100_questions_remaining_after_s201_s202_and_prior_exclusions"
    ] == 4
    assert diagnosis["chunks_v3_lane"]["status"] == (
        "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
