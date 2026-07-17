from __future__ import annotations

from scripts.s146_build_fresh_source_packet import build_packet


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
