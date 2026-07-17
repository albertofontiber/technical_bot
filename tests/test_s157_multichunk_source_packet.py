import pytest

from scripts.s157_build_multichunk_source_packet import build_packet, stable_sha


@pytest.fixture(scope="module")
def packet():
    return build_packet()


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
