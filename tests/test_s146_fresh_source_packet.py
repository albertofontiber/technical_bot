from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.s146_build_fresh_source_packet import (
    SNAPSHOT,
    build_packet,
    prior_exclusion_contract,
    stable_sha,
)


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PACKET = ROOT / "evals/s146_fresh_source_packet_v1.json"


def _frozen_packet() -> dict:
    return json.loads(FROZEN_PACKET.read_text(encoding="utf-8"))


def test_s135_exclusion_contract_is_small_sealed_and_complete() -> None:
    document_ids, source_sha256 = prior_exclusion_contract()
    assert len(document_ids) == 36
    assert source_sha256 == "9bfc52bc356447209bde018d6410c1bc7cb56d5ad5ad769987e1f5c885521c55"


def test_frozen_source_packet_is_stratified_disjoint_and_receipted() -> None:
    packet = _frozen_packet()
    body = {key: value for key, value in packet.items() if key != "packet_sha256"}
    assert packet["packet_sha256"] == stable_sha(body)
    assert packet["selection"]["question_or_gold_used_for_selection"] is False
    assert len(packet["items"]) == 14
    assert len({row["manufacturer"] for row in packet["items"]}) == 14
    assert {row["stratum"] for row in packet["items"]} == {"table", "prose"}
    assert sum(row["stratum"] == "table" for row in packet["items"]) == 7
    assert len({row["document_id"] for row in packet["items"]}) == 14
    assert all(row["excerpt_sha256"] for row in packet["items"])


@pytest.mark.skipif(
    not SNAPSHOT.exists(),
    reason="full S117 corpus snapshot is an external regeneration fixture",
)
def test_full_snapshot_regeneration_is_deterministic_and_matches_frozen() -> None:
    first = build_packet()
    second = build_packet()
    assert first == second == _frozen_packet()
