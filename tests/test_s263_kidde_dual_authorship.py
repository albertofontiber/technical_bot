from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import s263_run_kidde_dual_authorship as runner
from src.rag.frontier_visual_schemas import anthropic_compatible_schema, candidate_schema
from src.rag.visual_gold import normalized_text_sha


ROOT = Path(__file__).resolve().parents[1]


def test_s263_is_bounded_authorship_only() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    assert prereg["execution"] == {
        "order_per_item": ["fable", "sol"],
        "calls_max": 8,
        "calls_per_provider": 4,
        "provider_sdk_retries": 0,
        "semantic_retries": 0,
        "reciprocal_review_calls": 0,
        "support_mapping_calls": 0,
        "synthesis_calls": 0,
        "target_calls": 0,
    }
    assert runner.FABLE_MAX_TOKENS == 16000
    assert runner.MIN_VALID_PAIRS == 3


def test_s263_packet_is_external_and_unchanged() -> None:
    packet = json.loads(runner.PACKET.read_text(encoding="utf-8"))
    assert packet["packet_sha256"] == "8c8cd8e1410ae31f9961b0da83f5c6bb3ed759291623ae0bd3f8408ca917d234"
    assert packet["selection"]["source_overlap_with_official_gold"] == 0
    assert packet["selection"]["candidate_items"] == 4
    assert packet["selection"]["distinct_source_pdfs"] == 9
    assert sum(len(item["rendered_pages"]) for item in packet["items"]) == 18


def test_s263_prior_failure_is_exactly_one_fable_max_tokens() -> None:
    prior = runner._sealed(runner.PRIOR_RESULT)
    ledger = runner._sealed(runner.PRIOR_LEDGER)
    assert prior["status"] == "HOLD_S227_EXTERNAL_OR_INCOMPLETE"
    assert len(ledger["calls"]) == 1
    assert ledger["calls"][0]["model"] == "claude-fable-5"
    assert ledger["calls"][0]["status"] == "max_tokens"
    assert ledger["calls"][0]["usage"]["output_tokens"] == 8000


def test_s263_anthropic_schema_retains_shape_without_unsupported_limits() -> None:
    schema = anthropic_compatible_schema(candidate_schema("item"))
    encoded = json.dumps(schema, sort_keys=True)
    assert "maxItems" not in encoded
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "canary_id", "adequacy", "question", "expected_behavior",
        "gold_answer", "atomic_facts", "notes",
    }


def test_s263_frozen_inputs_match_current_normalized_text() -> None:
    prereg = yaml.safe_load(runner.PREREG.read_text(encoding="utf-8"))
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]
