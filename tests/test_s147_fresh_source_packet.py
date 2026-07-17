from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s147_packet_is_stratified_and_disjoint_from_s146() -> None:
    current = json.loads(
        (ROOT / "evals/s147_fresh_source_packet_v1.json").read_text(encoding="utf-8")
    )
    prior = json.loads(
        (ROOT / "evals/s146_fresh_source_packet_v1.json").read_text(encoding="utf-8")
    )
    assert current["status"] == "SEALED_SOURCE_FIRST"
    assert len(current["items"]) == 14
    assert len({row["manufacturer"] for row in current["items"]}) == 14
    assert sum(row["stratum"] == "table" for row in current["items"]) == 7
    assert sum(row["stratum"] == "prose" for row in current["items"]) == 7
    assert not ({row["document_id"] for row in current["items"]} & {row["document_id"] for row in prior["items"]})
    assert current["selection"]["question_or_gold_used_for_selection"] is False
