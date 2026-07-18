from __future__ import annotations

from scripts.s235_build_direct_clause_bound_ab_packets import build_packets
from scripts.s235_run_direct_clause_bound_ab import (
    _forbidden_score_keys,
    _units,
)
from src.rag.clause_bound_synthesis import WRITER_SYSTEM, claim_block_schema
from src.rag.frontier_visual_schemas import anthropic_compatible_schema
from src.rag.decomposed_evidence_planner_v2 import PLANNER_SYSTEM


def test_s235_packets_preserve_exact_frozen_population_and_isolation():
    generation, score = build_packets()

    assert generation["population"] == {
        "questions": 4,
        "qids": ["cat018", "hp002", "hp011", "hp017"],
        "chunks": 51,
    }
    assert score["population"]["obligations"] == 20
    assert score["population"]["genuine_synthesis_residuals"] == 12
    assert score["population"]["conflicts"] == 1
    assert not _forbidden_score_keys(generation)


def test_s235_generation_packet_builds_unique_bounded_evidence_units():
    generation, _ = build_packets()
    for item in generation["items"]:
        units = _units(item)
        assert units
        assert len(units) <= 500
        assert len({unit.unit_id for unit in units}) == len(units)


def test_claim_block_provider_schema_keeps_local_limits_but_strips_for_anthropic():
    local = claim_block_schema()
    provider = anthropic_compatible_schema(local)

    assert local["properties"]["claims"]["maxItems"] == 3
    assert "maxItems" not in provider["properties"]["claims"]
    claim = provider["properties"]["claims"]["items"]
    assert claim["additionalProperties"] is False
    assert set(claim["required"]) == {"text", "unit_ids"}


def test_anthropic_writer_prompt_carries_every_locally_enforced_limit():
    assert "1 to 3 atomic claims" in WRITER_SYSTEM
    assert "8 to 280 characters" in WRITER_SYSTEM
    assert "1 to 5 distinct source-unit IDs" in WRITER_SYSTEM


def test_s235_generation_geometry_contains_no_evaluator_answers():
    generation, score = build_packets()
    generation_qids = [item["qid"] for item in generation["items"]]
    score_qids = [item["qid"] for item in score["items"]]

    assert generation_qids == score_qids
    assert all("canonical_answer" not in item for item in generation["items"])
    assert all("obligations" not in item for item in generation["items"])
    assert all("conflicts" not in item for item in generation["items"])


def test_anthropic_planner_prompt_carries_every_locally_enforced_limit():
    assert "1 to 12 obligations" in PLANNER_SYSTEM
    assert "1 to 6 distinct unit" in PLANNER_SYSTEM
    assert "at most 18 distinct unit" in PLANNER_SYSTEM
    assert "do not enumerate facts merely" in PLANNER_SYSTEM
