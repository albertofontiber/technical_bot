from scripts.s178_combined_source_contract_replay import _apply_receipts, _source_key


def _context(content="Life time 105 operations"):
    return {
        "id": "chunk-1",
        "content": content,
        "source_file": "manual.PDF",
        "page_number": 5,
    }


def _manifest():
    return {
        "receipts": [
            {
                "page_number": 5,
                "original_token": "105",
                "derived_token": "10<sup>5</sup>",
                "matched_anchors": ["life", "time", "operations"],
            }
        ]
    }


def test_combined_replay_applies_only_exact_source_page_and_anchors():
    contexts = [_context(), {**_context(), "id": "other", "page_number": 6}]
    derived, applied = _apply_receipts(
        contexts, {_source_key("manual.pdf"): _manifest()}
    )

    assert derived[0]["content"] == "Life time 10<sup>5</sup> operations"
    assert derived[1] == contexts[1]
    assert [row["context_id"] for row in applied] == ["chunk-1"]


def test_combined_replay_abstains_on_ambiguous_token_or_weak_anchors():
    contexts = [
        _context("Life time 105 operations and 105 cycles"),
        _context("Unrelated 105 value"),
    ]
    derived, applied = _apply_receipts(
        contexts, {_source_key("manual"): _manifest()}
    )

    assert derived == contexts
    assert applied == []
