from __future__ import annotations

from scripts import s137_finalize_v31 as finalizer


def test_frozen_finalisation_inputs_validate_and_trigger_arbitration() -> None:
    prereg = finalizer.base.load_yaml(finalizer.DEFAULT_PREREG)
    packet, mapping, sol, fable, disagreements = finalizer.validate_prereg(prereg)
    assert len(packet["questions"]) == 3
    assert len(mapping["questions"]) == 3
    assert sol["status"] == "VALIDATED"
    assert fable["status"] == "VALIDATED"
    assert disagreements


def test_finalisation_worst_case_includes_all_prior_costs() -> None:
    prereg = finalizer.base.load_yaml(finalizer.DEFAULT_PREREG)
    worst = finalizer.worst_case(
        prereg, prereg["arbitration"]["max_counted_input_tokens"]
    )
    assert worst == 4.7420475
    assert worst < prereg["budget"]["cumulative_internal_ceiling_usd"]
    assert worst > prereg["budget"]["cumulative_before_arbitration_usd"]

