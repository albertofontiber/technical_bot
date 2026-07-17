from __future__ import annotations

from scripts.s146_build_fresh_source_packet import build_packet, prior_exclusion_contract


def test_s135_exclusion_contract_is_small_sealed_and_complete() -> None:
    document_ids, source_sha256 = prior_exclusion_contract()
    assert len(document_ids) == 36
    assert source_sha256 == "9bfc52bc356447209bde018d6410c1bc7cb56d5ad5ad769987e1f5c885521c55"


def test_fresh_source_packet_is_deterministic_stratified_and_disjoint() -> None:
    first = build_packet()
    second = build_packet()
    assert first == second
    assert first["selection"]["question_or_gold_used_for_selection"] is False
    assert len(first["items"]) == 14
    assert len({row["manufacturer"] for row in first["items"]}) == 14
    assert {row["stratum"] for row in first["items"]} == {"table", "prose"}
    assert sum(row["stratum"] == "table" for row in first["items"]) == 7
    assert len({row["document_id"] for row in first["items"]}) == 14
    assert all(row["excerpt_sha256"] for row in first["items"])
