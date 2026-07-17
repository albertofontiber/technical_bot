from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import s199_build_restored_margin_packet as builder
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
        "manufacturer_key": manufacturer.casefold(),
        "pair_key": (manufacturer.casefold(), f"model-{index}"),
        "source_file_key": f"source-{index}",
        "stratum": stratum,
        "quality": 100 - index,
        "tie": f"{index:04d}",
    }


def test_balanced_selector_prefers_fourteen_distinct_manufacturers() -> None:
    candidates = [
        *[_candidate("table", f"table-{index}", index) for index in range(7)],
        *[
            _candidate("prose", f"prose-{index}", 100 + index)
            for index in range(7)
        ],
    ]
    selected, mode = builder.select_balanced(candidates)
    assert len(selected) == 14
    assert mode["unique_manufacturers"] == 14
    assert mode["within_cohort_manufacturer_repeat_count"] == 0
    assert mode["fallback_used"] is False


def test_balanced_selector_uses_one_repeat_only_when_fourteen_are_impossible() -> None:
    candidates = [
        *[
            _candidate("table", f"manufacturer-{index}", index)
            for index in range(7)
        ],
        *[
            _candidate("prose", f"manufacturer-{index}", 100 + index)
            for index in range(6, 13)
        ],
    ]
    selected, mode = builder.select_balanced(candidates)
    assert len(selected) == 14
    assert mode["unique_manufacturers"] == 13
    assert mode["within_cohort_manufacturer_repeat_count"] == 1
    assert mode["fallback_used"] is True
    assert len({item["row"]["document_id"] for item in selected}) == 14


def test_balanced_selector_rejects_less_than_thirteen_manufacturers() -> None:
    candidates = [
        *[
            _candidate("table", f"manufacturer-{index}", index)
            for index in range(7)
        ],
        *[
            _candidate("prose", f"manufacturer-{index}", 100 + index)
            for index in range(5, 12)
        ],
    ]
    with pytest.raises(RuntimeError, match=">=13-manufacturer"):
        builder.select_balanced(candidates)


def test_versioned_packet_contract_when_present() -> None:
    path = ROOT / "evals/s199_restored_margin_source_packet_v1.json"
    if not path.exists():
        return
    packet = json.loads(path.read_text(encoding="utf-8"))
    body = dict(packet)
    assert body.pop("packet_sha256") == stable_sha(body)
    items = packet["items"]
    assert len(items) == 14
    assert sum(item["stratum"] == "table" for item in items) == 7
    assert sum(item["stratum"] == "prose" for item in items) == 7
    assert len({item["document_id"] for item in items}) == 14
    assert len({item["source_file"].strip().casefold() for item in items}) == 14
    assert (
        len(
            {
                (
                    item["manufacturer"].strip().casefold(),
                    item["product_model"].strip().casefold(),
                )
                for item in items
            }
        )
        == 14
    )
    assert packet["selection"]["unique_manufacturers"] in {13, 14}
    assert (
        packet["selection"][
            "question_gold_claim_facet_or_model_outcome_used_for_selection"
        ]
        is False
    )
    for key in (
        "prior_document_overlap",
        "prior_source_file_overlap",
        "prior_manufacturer_product_pair_overlap",
        "target_document_overlap",
        "target_chunk_overlap",
        "target_exact_content_overlap",
        "target_extraction_overlap",
    ):
        assert packet["selection"][key] == 0
    assert packet["read_receipt"]["database_writes"] == 0
    assert (
        packet["chunks_v3_lane"]["status"]
        == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
