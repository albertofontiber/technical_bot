import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from s108_reconcile_failure_stages import reconcile  # noqa: E402


def test_reconciliation_preserves_frozen_baseline_and_partitions_retrieval_queue():
    payload = reconcile()
    gate = payload["gate"]

    assert gate["frozen_non_ok_rows"] == 36
    assert gate["baseline_counts"] == {
        "corpus-gap": 2,
        "meta-ref": 2,
        "rerank-miss": 14,
        "retrieval-miss": 7,
        "synthesis-miss": 11,
    }
    assert gate["retrieval_measurement_replay_ready"] == 2
    assert gate["retrieval_structural_r2_precondition_ready"] == 3
    assert gate["retrieval_structural_exploratory_discoveries"] == 1
    assert gate["retrieval_doc_scoped_hyq_unique_resolutions"] == 1
    assert gate["retrieval_doc_scoped_hyq_supported_facts"] == 3
    assert gate["retrieval_still_unresolved"] == 0
    assert gate["retrieval_stage_accounted_facts"] == 7
    assert gate["cached_synthesis_successes"] == 1
    assert gate["official_ok_baseline"] == "93/127 unchanged"
    assert gate["official_ok_uplift"] == 0
    assert gate["model_calls"] == 0
    assert gate["database_writes"] == 0
    assert gate["interpretation"] == (
        "GO_RETRIEVAL_7_OF_7_PRECONDITIONS_TO_DOWNSTREAM_GATES"
    )


def test_reconciliation_records_evidence_without_promoting_candidates_to_ok():
    payload = reconcile()
    rows = {row["key"]: row for row in payload["rows"]}

    for key in ("cat007#3:2 A / 0,5 A", "cat007#4:10^5"):
        row = rows[key]
        assert row["candidate_status"] == "measurement_replay_ready"
        assert row["next_lane"] == "bounded_frozen_judge_replay"
        assert row["evidence"][0]["same_family_recovered_ids"]
        assert row["evidence"][0]["recovered_served_ids"]
        assert row["evidence"][0]["answer_value_present"] is True
        assert row["evidence"][0]["cross_family_admitted_ids"] == []

    assert rows["hp011#2:05 a 295 seg"]["candidate_status"] == (
        "r2_precondition_ready_cached_synthesis_miss"
    )
    assert rows["hp014#3:35"]["candidate_status"] == (
        "cached_synthesis_success_pending_protected_regression"
    )
    assert rows["hp017#1:instruccion de entrada"]["candidate_status"] == (
        "r2_precondition_ready_cached_synthesis_miss"
    )
    assert rows["hp012#3:4 lazos / 792"]["candidate_status"] == (
        "doc_scoped_hyq_retrieval_precondition"
    )
    assert rows["hp012#3:4 lazos / 792"]["evidence"][0][
        "same_family_supporting_ids"
    ] == ["b162a7eb-50bd-4b0f-88f7-40ad855c6c94"]
    assert rows["hp013#1:PWR-R"]["candidate_status"] == (
        "exploratory_structural_retrieval_precondition"
    )
    hp013_evidence = rows["hp013#1:PWR-R"]["evidence"][0]
    assert hp013_evidence["confirmatory"] is False
    assert hp013_evidence["same_family_supporting_ids"] == [
        "2365dfaa-45e5-4c65-9328-194441e375c9"
    ]
