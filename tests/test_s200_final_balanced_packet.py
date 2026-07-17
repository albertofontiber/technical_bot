from __future__ import annotations

import json
from pathlib import Path

from scripts import s200_build_final_balanced_packet as builder
from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def _candidate(stratum: str, manufacturer: str, index: int) -> dict:
    return {
        "row": {
            "id": f"chunk-{index}",
            "document_id": f"doc-{index}",
            "manufacturer": manufacturer,
            "product_model": f"model-{index}",
        },
        "manufacturer_key": manufacturer,
        "pair_key": (manufacturer, f"model-{index}"),
        "source_file_key": f"source-{index}",
        "stratum": stratum,
        "quality": 1000 - index,
        "tie": f"{index:04d}",
    }


def test_selector_covers_and_balances_ten_manufacturers() -> None:
    candidates = []
    index = 0
    for stratum in ("table", "prose"):
        for manufacturer_index in range(10):
            for _ in range(3):
                candidates.append(
                    _candidate(stratum, f"m{manufacturer_index}", index)
                )
                index += 1
    selected, balance = builder.select_final_balanced(candidates)
    assert len(selected) == 24
    assert sum(item["stratum"] == "table" for item in selected) == 12
    assert sum(item["stratum"] == "prose" for item in selected) == 12
    assert balance["covered_manufacturers"] == 10
    assert balance["available_manufacturers"] == 10
    assert balance["max_items_per_manufacturer"] - balance["min_items_per_manufacturer"] <= 1
    assert len({item["row"]["document_id"] for item in selected}) == 24


def test_versioned_packet_contract_when_present() -> None:
    path = ROOT / "evals/s200_final_balanced_source_packet_v1.json"
    if not path.exists():
        return
    packet = json.loads(path.read_text(encoding="utf-8"))
    body = dict(packet)
    assert body.pop("packet_sha256") == stable_sha(body)
    items = packet["items"]
    selection = packet["selection"]
    assert len(items) == 24
    assert selection["table"] == 12
    assert selection["prose"] == 12
    assert selection["covered_manufacturers"] == selection["available_manufacturers"]
    assert selection["covered_manufacturers"] == 10
    assert len({item["document_id"] for item in items}) == 24
    assert len({item["source_file"].strip().casefold() for item in items}) == 24
    assert len(
        {
            (item["manufacturer"].strip().casefold(), item["product_model"].strip().casefold())
            for item in items
        }
    ) == 24
    for key in (
        "prior_document_overlap",
        "prior_source_file_overlap",
        "prior_manufacturer_product_pair_overlap",
        "target_document_overlap",
        "target_chunk_overlap",
        "target_exact_content_overlap",
        "target_extraction_overlap",
    ):
        assert selection[key] == 0
    assert selection["question_gold_claim_facet_or_model_outcome_used_for_selection"] is False
    assert packet["read_receipt"]["database_writes"] == 0
    assert packet["chunks_v3_lane"]["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
