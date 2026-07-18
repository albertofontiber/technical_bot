from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.s215_run_kidde_multisource_continuation import (
    ITEM_IDS,
    _s214_inputs,
    verify_prereg,
)
from src.rag.visual_gold import normalized_text_sha, stable_sha


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json"
PREREG = ROOT / "evals/s215_kidde_multisource_continuation_prereg_v1.yaml"
S214_LEDGER = ROOT / "evals/s214_frontier_call_ledger_v1.json"
S214_CLOSURE = ROOT / "evals/s214_kidde_multisource_incomplete_closure_v1.json"


def _sealed(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_s215_membership_is_the_exact_nonsemantic_s214_remainder():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    ledger = _sealed(S214_LEDGER)
    closure = _sealed(S214_CLOSURE)
    attempted = [
        row["call_label"].removeprefix("generate:")
        for row in ledger["calls"]
        if row["provider"] == "fable"
    ]
    packet_order = [item["canary_id"] for item in packet["items"]]
    derived = tuple(item_id for item_id in packet_order if item_id not in attempted)
    assert attempted == ["kidde_nc_capacity_tradeoffs"]
    assert derived == ITEM_IDS
    assert tuple(closure["unattempted_items"]) == ITEM_IDS
    inherited, _ = _s214_inputs(packet)
    assert tuple(candidate["canary_id"] for candidate in inherited) == ITEM_IDS


def test_s215_prereg_freezes_exact_models_geometry_and_zero_credit():
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    verify_prereg(packet, require_design_gate=False)
    assert prereg["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert prereg["models"] == {
        "principal": {"id": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "independent": {"id": "claude-fable-5"},
    }
    assert prereg["cohort"]["mandatory_item_ids"] == list(ITEM_IDS)
    assert prereg["cohort"]["membership_uses_candidate_semantics"] is False
    assert prereg["execution"]["frontier_paid_calls_max"] == 15
    assert prereg["execution"]["fable_authorship_max_tokens"] == 12_000
    assert prereg["execution"]["provider_retries"] == 0
    assert prereg["execution"]["same_item_retry"] is False
    assert prereg["validation"]["required_support_validated_items"] == 3
    assert prereg["validation"]["partial_publication"] is False
    assert prereg["validation"]["official_fact_credit"] == 0
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s215_closed_lines_remain_explicit():
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    assert prereg["closed_lines"] == {
        "chunks_v2": "ACTIVE_READ_ONLY",
        "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "s214_attempted_fable_item_retry": "FORBIDDEN",
        "railway_merge_gate": False,
    }
