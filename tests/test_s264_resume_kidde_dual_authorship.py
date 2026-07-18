from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import s264_resume_kidde_dual_authorship as runner
from src.rag.visual_gold import normalized_text_sha


ROOT = Path(__file__).resolve().parents[1]


def test_s264_is_transport_only_and_bounded() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    assert prereg["recovery_delta"] == {
        "cause": "openai_http_520_retryable_no_response",
        "carried_candidate": "kidde_2xa_installation_operation_boundaries_fable",
        "missing_call_first": "kidde_2xa_installation_operation_boundaries_sol",
        "prompt_or_packet_changed": False,
        "schema_changed": False,
        "semantic_feedback_used": False,
        "partial_output_used": False,
    }
    assert prereg["execution"]["new_calls_max"] == 7
    assert prereg["execution"]["new_calls_fable"] == 3
    assert prereg["execution"]["new_calls_sol"] == 4
    assert prereg["execution"]["semantic_retries"] == 0
    assert prereg["execution"]["target_calls"] == 0


def test_s264_exact_prior_is_one_valid_fable_then_sol_520() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    ledger, fable = runner.verify_prereg(packet)
    assert len(ledger["calls"]) == 1
    assert ledger["calls"][0]["provider"] == "fable"
    assert ledger["calls"][0]["status"] == "end_turn"
    assert len(fable["items"]) == 1
    assert fable["items"][0]["validation_status"] == "VALID"
    result = runner._sealed(runner.S263_RESULT)
    assert result["frontier_calls"] == 1
    assert "Error code: 520" in result["reason"]


def test_s264_preserves_independent_packet() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    assert packet["selection"]["source_overlap_with_official_gold"] == 0
    assert packet["selection"]["candidate_items"] == 4
    assert packet["selection"]["distinct_source_pdfs"] == 9
    assert sum(len(item["rendered_pages"]) for item in packet["items"]) == 18


def test_s264_frozen_inputs_match_current_normalized_text() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]
