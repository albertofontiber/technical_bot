from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import s267_review_kidde_pixel_gold as runner
from src.rag.visual_gold import normalized_text_sha


ROOT = Path(__file__).resolve().parents[1]


def test_s267_uses_exact_frontier_reciprocal_review_contract() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    assert prereg["models"] == {
        "principal": {"id": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "independent": {
            "id": "claude-fable-5",
            "adaptive_effort": "xhigh",
            "max_tokens": 16000,
        },
    }
    assert prereg["execution"] == {
        "reciprocal_review_calls": 8,
        "sol_review_calls": 4,
        "fable_review_calls": 4,
        "candidate_repair_or_merge": False,
        "support_mapping_calls": 0,
        "target_calls": 0,
    }
    assert prereg["transport"]["initial_post_retries"] == 0
    assert prereg["transport"]["poll_get_retries_max"] == 2
    assert prereg["transport"]["semantic_retries"] == 0


def test_s267_lineage_is_four_complete_valid_candidate_pairs() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    result, fable, sol = runner.verify_prereg(packet)
    assert result["valid_pair_ids"] == [row["canary_id"] for row in packet["items"]]
    assert len(fable["items"]) == len(sol["items"]) == 4
    assert all(
        row["validation_status"] == "VALID"
        for row in fable["items"] + sol["items"]
    )


def test_s267_call_plan_is_exactly_reciprocal_and_interleaved() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    identities = [
        runner._call_identity(provider, item)
        for provider, item in runner._call_plan(packet)
    ]
    assert len(identities) == 8
    for index, item in enumerate(packet["items"]):
        item_id = item["canary_id"]
        assert identities[index * 2:index * 2 + 2] == [
            ("sol", f"review:fable:{item_id}"),
            ("fable", f"review:sol:{item_id}"),
        ]


def test_s267_frozen_inputs_match_current_normalized_text() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]
