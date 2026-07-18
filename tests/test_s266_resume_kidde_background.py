from __future__ import annotations

import json
from pathlib import Path

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
        "transport_retries_max_per_http_operation": 2,
        "semantic_retries": 0,
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
