from __future__ import annotations

from scripts import s137_fable_atomic_v3 as atomic


def test_frozen_atomic_inputs_validate_without_model_calls() -> None:
    prereg = atomic.base.load_yaml(atomic.DEFAULT_PREREG)
    atomic.validate_prereg(prereg)


def test_atomic_subsets_cover_every_question_and_evidence_once() -> None:
    prereg = atomic.base.load_yaml(atomic.DEFAULT_PREREG)
    packet = atomic.base.load_json(
        atomic.ROOT / prereg["frozen_inputs"]["public_packet"]["path"]
    )
    subsets = [
        atomic.subset_packet(packet, row["question_id"])
        for row in prereg["atomic_questions"]
    ]
    observed = [subset["questions"][0]["question_id"] for subset in subsets]
    assert observed == [row["question_id"] for row in prereg["atomic_questions"]]
    assert sum(len(subset["questions"][0]["evidence"]) for subset in subsets) == 47


def test_atomic_worst_case_accounts_for_all_prior_calls_and_arbitration() -> None:
    prereg = atomic.base.load_yaml(atomic.DEFAULT_PREREG)
    worst = atomic.cumulative_worst_case(prereg, [50_000, 50_000, 50_000])
    assert worst == 6.7446875
    assert worst < prereg["budget"]["atomic_internal_cumulative_ceiling_usd"]
    assert worst > prereg["budget"]["cumulative_prior_usd"]

