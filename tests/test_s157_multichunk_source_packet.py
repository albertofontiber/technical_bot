import json
from pathlib import Path

import pytest

from scripts.s157_build_multichunk_source_packet import SNAPSHOT, build_packet, stable_sha


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PACKET = ROOT / "evals/s157_multichunk_source_packet_v1.json"


@pytest.fixture(scope="module")
def packet():
    return json.loads(FROZEN_PACKET.read_text(encoding="utf-8"))


@pytest.mark.skipif(
    not SNAPSHOT.exists(),
    reason="full S117 corpus snapshot is an external regeneration fixture",
)
def test_full_snapshot_regeneration_matches_frozen(packet):
    assert build_packet() == packet


def test_packet_has_stable_identity_and_is_source_first(packet):
    assert packet["selection"]["question_or_gold_used_for_selection"] is False
    assert packet["packet_sha256"] == stable_sha({k: v for k, v in packet.items() if k != "packet_sha256"})


def test_population_and_lineage_are_exact(packet):
    assert len(packet["items"]) == 12
    assert len({row["manufacturer"] for row in packet["items"]}) == 12
    assert len({row["document_id"] for row in packet["items"]}) == 12
    for item in packet["items"]:
        assert len(item["chunks"]) == 3
        assert [row["fragment_number"] for row in item["chunks"]] == [1, 2, 3]
        assert len({row["chunk_id"] for row in item["chunks"]}) == 3
        indices = [row["chunk_index"] for row in item["chunks"]]
        assert indices == sorted(indices)
        assert indices[-1] - indices[0] <= 4


def test_exclusions_are_closed(packet):
    assert packet["selection"]["target_document_overlap"] == 0
    assert packet["selection"]["s146_s147_overlap"] == 0
