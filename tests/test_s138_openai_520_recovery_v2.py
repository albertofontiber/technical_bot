from __future__ import annotations

import pytest

from scripts import s138_openai_520_recovery_v2 as recovery


def prereg() -> dict:
    return {
        "execution": {
            name: f"evals/{name}.json"
            for name in (
                "sol_response",
                "fable_q1",
                "fable_q2",
                "fable_q3",
                "fable_combined",
                "arbitration_response",
                "aggregate",
            )
        }
    }


def test_clean_resume_accepts_absent_outputs(tmp_path) -> None:
    recovery.require_clean_resume(prereg(), root=tmp_path)


def test_clean_resume_rejects_any_partial_output(tmp_path) -> None:
    output = tmp_path / "evals/sol_response.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(recovery.RecoveryFailure, match="partial/completed"):
        recovery.require_clean_resume(prereg(), root=tmp_path)


def test_exception_receipt_is_terminal_and_sanitized() -> None:
    class ProviderError(Exception):
        status_code = 520
        request_id = "request-test"

    exc = ProviderError("provider unavailable")
    receipt = recovery.exception_receipt(exc)
    assert receipt["status"] == "RECOVERY_FAILED_NO_FURTHER_RETRY_AUTHORIZED"
    assert receipt["http_status"] == 520
    assert receipt["authorization"]["further_retry"] is False
