from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import s266_resume_kidde_background as runner
from src.rag.visual_gold import normalized_text_sha


ROOT = Path(__file__).resolve().parents[1]


def test_s266_uses_resumable_background_transport() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    assert prereg["transport"] == {
        "sol_background": True,
        "store": False,
        "response_id_checkpointed": True,
        "polling_resumable": True,
        "x_client_request_id": True,
        "initial_post_retries": 0,
        "poll_get_retries_max": 2,
        "semantic_retries": 0,
        "stage_restart_reconstructs_from_sealed_ledger": True,
        "ambiguous_nonresumable_post_fails_closed": True,
        "poll_interval_seconds": 2,
        "poll_timeout_seconds": 1800,
    }
    assert prereg["execution"]["new_calls_max"] == 5
    assert prereg["execution"]["new_calls_sol"] == 3
    assert prereg["execution"]["new_calls_fable"] == 2
    assert prereg["execution"]["target_calls"] == 0


def test_s266_carries_exactly_three_valid_candidates() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    _s263, _s264, fable, sol = runner.verify_prereg(packet)
    assert len(fable["items"]) == 2
    assert len(sol["items"]) == 1
    assert all(row["validation_status"] == "VALID" for row in fable["items"] + sol["items"])
    assert fable["items"][0]["canary_id"] == sol["items"][0]["canary_id"]


def test_s266_frozen_inputs_match_current_normalized_text() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]


class _LedgerRuntime:
    def __init__(self, calls):
        self.calls = calls

    def load_ledger(self):
        return {"calls": self.calls}


def _patch_resume_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runner, "ATTEMPTS", tmp_path / "attempts.json")
    monkeypatch.setattr(runner, "FABLE_GENERATIONS", tmp_path / "fable.json")
    monkeypatch.setattr(runner, "SOL_GENERATIONS", tmp_path / "sol.json")
    monkeypatch.setattr(runner, "BACKGROUND_STATES", tmp_path / "states")


def _attempts(*identities):
    return {
        "attempts": [
            {"provider": provider, "call_label": label, "semantic_attempt": 1}
            for provider, label in identities
        ]
    }


def test_s266_reconstructs_completed_call_from_sealed_ledger(
    tmp_path, monkeypatch
) -> None:
    _patch_resume_paths(monkeypatch, tmp_path)
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    prior_fable = json.loads(runner.S264_FABLE.read_text(encoding="utf-8"))
    prior_sol = json.loads(runner.S264_SOL.read_text(encoding="utf-8"))
    item_id = packet["items"][1]["canary_id"]
    receipt = {
        "provider": "sol",
        "call_label": f"generate:{item_id}",
        "model": runner.SOL,
        "status": "completed",
        "raw_output": json.dumps(
            prior_fable["items"][1]["candidate"], ensure_ascii=False
        ),
    }
    runner._checkpoint(
        runner.ATTEMPTS,
        "s266_kidde_background_attempts_v1",
        _attempts(("sol", f"generate:{item_id}")),
    )

    rows, valid, completed = runner._reconstruct_resume_state(
        packet, _LedgerRuntime([receipt]), prior_fable, prior_sol
    )

    assert completed == 1
    assert rows["sol"][-1]["receipt"] == receipt
    assert item_id in valid["sol"]


def test_s266_fails_closed_on_ambiguous_fable_post(tmp_path, monkeypatch) -> None:
    _patch_resume_paths(monkeypatch, tmp_path)
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    prior_fable = json.loads(runner.S264_FABLE.read_text(encoding="utf-8"))
    prior_sol = json.loads(runner.S264_SOL.read_text(encoding="utf-8"))
    sol_label = f"generate:{packet['items'][1]['canary_id']}"
    fable_label = f"generate:{packet['items'][2]['canary_id']}"
    receipt = {
        "provider": "sol",
        "call_label": sol_label,
        "model": runner.SOL,
        "status": "completed",
        "raw_output": json.dumps(
            prior_fable["items"][1]["candidate"], ensure_ascii=False
        ),
    }
    runner._checkpoint(
        runner.ATTEMPTS,
        "s266_kidde_background_attempts_v1",
        _attempts(("sol", sol_label), ("fable", fable_label)),
    )

    with pytest.raises(RuntimeError, match="ambiguous non-resumable"):
        runner._reconstruct_resume_state(
            packet, _LedgerRuntime([receipt]), prior_fable, prior_sol
        )
