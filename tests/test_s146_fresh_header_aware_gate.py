from __future__ import annotations

from scripts.s146_fresh_header_aware_gate import (
    _repair_unique_whitespace_quote,
    author_schema,
    selector_schema,
)


def test_unique_whitespace_repair_is_exact_and_fails_closed_on_ambiguity() -> None:
    source = "Header\n\nTarget   value\n\nOther"
    exact, changed = _repair_unique_whitespace_quote(source, "Target value")
    assert (exact, changed) == ("Target   value", True)
    assert _repair_unique_whitespace_quote("Target value / Target value", "Target value") == (
        "Target value",
        False,
    )
    assert _repair_unique_whitespace_quote("A X B / A Y B", "A B") == (None, False)


def test_paid_schemas_are_strict() -> None:
    assert author_schema()["additionalProperties"] is False
    assert selector_schema()["additionalProperties"] is False
    assert selector_schema()["properties"]["unit_ids"]["items"]["type"] == "string"
