from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.evidence_units import build_evidence_units


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "evals/s142_independent_obligation_cohort_v1.json"
PACKET = ROOT / "evals/s142_independent_source_packet_v1.json"


def test_burned_challenge_claims_are_all_representable_by_exact_units():
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    packet_by = {row["item_id"]: row for row in packet["items"]}
    covered = total = 0
    for item in (row for row in cohort["items"] if row["eligible"]):
        source = packet_by[item["item_id"]]["excerpt"]
        units = build_evidence_units(
            source, fragment_number=1, candidate_id=item["item_id"]
        )
        assert len(units) <= 50
        for claim in item["claims"]:
            total += 1
            matched = any(claim["exact_quote"] in unit.content for unit in units)
            covered += int(matched)
            assert matched, item["item_id"]
    assert (covered, total) == (14, 14)


def test_unit_ids_and_spans_are_deterministic_and_source_bound():
    source = "Heading\n\nFirst technical paragraph.\n\n| A | B |\n| 1 | 2 |\n"
    first = build_evidence_units(source, fragment_number=2, candidate_id="chunk-a")
    second = build_evidence_units(source, fragment_number=2, candidate_id="chunk-a")
    assert first == second
    assert len({row.unit_id for row in first}) == len(first)
    for row in first:
        assert source[row.source_start : row.source_end] == row.content
    changed = build_evidence_units(source, fragment_number=2, candidate_id="chunk-b")
    assert [row.unit_id for row in first] != [row.unit_id for row in changed]


def test_invalid_window_contract_fails_closed():
    with pytest.raises(ValueError):
        build_evidence_units("source", fragment_number=1, candidate_id="a", max_chars=100)
