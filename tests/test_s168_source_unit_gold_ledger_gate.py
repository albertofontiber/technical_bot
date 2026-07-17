import pytest

from scripts.s165_answer_archetype_ledger import FACETS
from scripts.s168_source_unit_gold_ledger_gate import score_selection, validate_author_item
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _source_and_units():
    source = {
        "item_id": "s168_src_01", "stratum": "prose", "manufacturer": "Maker",
        "product_model": "P1", "document_id": "doc", "chunk_id": "chunk",
        "excerpt_sha256": "a" * 64,
        "excerpt": "## Setup\n\nBefore connecting, select Safe mode.\n\nVerify the green LED.",
    }
    units = build_header_aware_evidence_units(
        source["excerpt"], fragment_number=1, candidate_id=source["item_id"]
    )
    return source, units


def test_s168_gold_accepts_known_many_to_many_source_ids():
    source, units = _source_and_units()
    unit_id = units[-1].unit_id
    item = validate_author_item({
        "item_id": source["item_id"], "eligible": True, "question": "How do I verify setup?",
        "answer_points": [
            {"claim": "set mode", "facet": FACETS[1], "support_unit_ids": [unit_id]},
            {"claim": "verify", "facet": FACETS[7], "support_unit_ids": [unit_id]},
        ],
    }, source, units)
    assert item["answer_points"][0]["support_unit_ids"] == [unit_id]
    assert item["answer_points"][1]["support_unit_ids"] == [unit_id]


def test_s168_gold_rejects_unknown_ids():
    source, units = _source_and_units()
    with pytest.raises(ValueError, match="unknown"):
        validate_author_item({
            "item_id": source["item_id"], "eligible": True, "question": "How?",
            "answer_points": [
                {"claim": "a", "facet": FACETS[0], "support_unit_ids": ["unknown"]},
                {"claim": "b", "facet": FACETS[1], "support_unit_ids": [units[0].unit_id]},
            ],
        }, source, units)


def test_s168_scoring_requires_all_gold_support_ids():
    source, units = _source_and_units()
    ids = [unit.unit_id for unit in units[-2:]]
    item = validate_author_item({
        "item_id": source["item_id"], "eligible": True, "question": "How?",
        "answer_points": [
            {"claim": "both", "facet": FACETS[0], "support_unit_ids": ids},
            {"claim": "last", "facet": FACETS[7], "support_unit_ids": [ids[-1]]},
        ],
    }, source, units)
    partial = score_selection(item, units, {FACETS[7]: [ids[-1]]}, [ids[-1]])
    assert partial["claims_covered"] == 1
    assert partial["complete"] is False
    full = score_selection(item, units, {FACETS[0]: ids, FACETS[7]: [ids[-1]]}, ids)
    assert full["claims_covered"] == 2
    assert full["complete"] is True
