import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s168_sealed_packet_is_document_and_target_independent():
    result = json.loads(
        (ROOT / "evals/s168_source_unit_gold_packet_v1.json").read_text(encoding="utf-8")
    )
    assert result["selection"]["items"] == 14
    assert result["selection"]["manufacturers"] == 14
    assert result["selection"]["unique_documents"] == 14
    assert result["selection"]["table"] == 7
    assert result["selection"]["prose"] == 7
    assert result["selection"]["prior_document_overlap"] == 0
    assert result["selection"]["target_document_overlap"] == 0
    assert result["selection"]["target_chunk_overlap"] == 0
    assert result["selection"]["development_product_pair_overlap"] == 0


def test_s168_documents_do_not_overlap_s167_documents():
    s167 = json.loads(
        (ROOT / "evals/s167_independent_ledger_source_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    s168 = json.loads(
        (ROOT / "evals/s168_source_unit_gold_packet_v1.json").read_text(encoding="utf-8")
    )
    assert {row["document_id"] for row in s167["items"]}.isdisjoint(
        {row["document_id"] for row in s168["items"]}
    )
