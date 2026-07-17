from __future__ import annotations

from scripts import s137_resume_fable_v2 as recovery


def test_frozen_recovery_inputs_validate_without_model_calls() -> None:
    prereg = recovery.base.load_yaml(recovery.DEFAULT_PREREG)
    recovery.validate_prereg(prereg)


def test_cumulative_worst_case_includes_prior_truncation_and_arbitration() -> None:
    prereg = recovery.base.load_yaml(recovery.DEFAULT_PREREG)
    worst = recovery.cumulative_worst_case(
        prereg, prereg["model"]["expected_counted_input_tokens"]
    )
    assert worst == 4.2059375
    assert worst < prereg["budget"]["recovery_internal_cumulative_ceiling_usd"]
    assert worst > (
        prereg["budget"]["valid_sol_v1_conservative_actual_usd"]
        + prereg["budget"]["truncated_fable_v1_upper_bound_usd"]
    )


def test_reused_sol_receipt_is_valid_against_unchanged_packet() -> None:
    prereg = recovery.base.load_yaml(recovery.DEFAULT_PREREG)
    packet = recovery.base.load_json(
        recovery.ROOT / prereg["frozen_inputs"]["public_packet"]["path"]
    )
    sol = recovery.base.load_json(
        recovery.ROOT / prereg["frozen_inputs"]["valid_sol_response"]["path"]
    )
    recovery.v1.validate_judgement(sol["judgement"], packet)
    assert sol["packet_questions_sha256"] == packet["manifests"]["questions_sha256"]

