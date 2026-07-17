import json

import pytest

from scripts.s191_visual_utility_executor import is_positive, parse_labels


def _row(item_id="i1", **overrides):
    row = {
        "item_id": item_id,
        "technical_utility": "useful",
        "visual_role": "wiring",
        "confidence": "high",
        "has_legible_technical_visual": True,
        "reason": "Legible wiring diagram",
    }
    row.update(overrides)
    return row


def test_parser_accepts_fenced_json_and_preserves_expected_order():
    raw = "```json\n" + json.dumps([_row("i2"), _row("i1")]) + "\n```"
    assert [row["item_id"] for row in parse_labels(raw, ["i1", "i2"])] == [
        "i1",
        "i2",
    ]


def test_parser_rejects_open_vocabulary_and_long_reason():
    with pytest.raises(ValueError):
        parse_labels(json.dumps([_row(visual_role="schematic")]), ["i1"])
    with pytest.raises(ValueError):
        parse_labels(json.dumps([_row(reason="word " * 13)]), ["i1"])


def test_positive_policy_is_strict_intersection():
    assert is_positive(_row())
    assert not is_positive(_row(confidence="medium"))
    assert not is_positive(_row(visual_role="product_photo"))
    assert not is_positive(_row(has_legible_technical_visual=False))
