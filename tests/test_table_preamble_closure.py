from __future__ import annotations

import copy

from src.rag.table_preamble_closure import (
    LANE,
    begins_with_markdown_table,
    contains_markdown_table,
    matching_preamble_span,
    normalize_heading,
    select_table_preambles,
)


EXTRACTION = "a" * 64


def _row(row_id: str, index: int, content: str, **overrides):
    row = {
        "id": row_id,
        "document_id": "doc-1",
        "extraction_sha256": EXTRACTION,
        "chunk_index": index,
        "content": content,
        "section_title": "Table 2: Wiring Terminal Designations",
        "source_file": "manual-a",
        "language": "en",
    }
    row.update(overrides)
    return row


def test_markdown_table_detection_is_strict():
    assert begins_with_markdown_table("| A | B |\n| --- | :---: |\n| 1 | 2 |")
    assert begins_with_markdown_table("| A | B |\n| - | ---- |\n| 1 | 2 |")
    assert not begins_with_markdown_table("Introduction\n\n| A | B |\n| --- | --- |")
    assert not begins_with_markdown_table("| A | B |\n| values | only |")
    assert contains_markdown_table("Intro\n| A | B |\n| --- | --- |\n| 1 | 2 |")
    assert not contains_markdown_table("Intro\n| value | only |")


def test_heading_normalization_is_format_only():
    assert normalize_heading("**Tabla 2:** Designaciones") == "tabla 2 designaciones"
    assert normalize_heading("Table 2 - Wiring") != normalize_heading("Table 3 - Wiring")


def test_selects_exact_predecessor_heading_tail_with_receipt():
    preamble = (
        "## Fitting the Terminal Blocks\nInstructions unrelated to the table.\n\n"
        "### Table 2: Wiring Terminal Designations\n"
        "(Note - Terminals marked CH2 only exist on 2 channel models)"
    )
    seed = _row(
        "table",
        10,
        "| No. | Function | Channel |\n| --- | --- | --- |\n| 8 | Alarm | CH2 |",
    )
    predecessor = _row("preamble", 9, preamble)
    seeds_before = copy.deepcopy([seed])
    candidates_before = copy.deepcopy([predecessor])

    selected, trace = select_table_preambles([seed], [predecessor])

    assert [seed] == seeds_before
    assert [predecessor] == candidates_before
    assert trace["selected_ids"] == ["preamble"]
    assert selected[0]["retrieval_lane"] == LANE
    card = selected[0]["coverage_cards"][0]
    assert card["quote"].startswith("### Table 2")
    assert "Instructions unrelated" not in card["quote"]
    assert preamble[card["start"] : card["end"]] == card["quote"]


def test_rejects_wrong_identity_adjacency_heading_and_non_table_seed():
    seed = _row("table", 10, "| A | B |\n| --- | --- |\n| 1 | 2 |")
    valid_content = "### Table 2: Wiring Terminal Designations\nNote"
    invalid = [
        _row("wrong-doc", 9, valid_content, document_id="doc-2"),
        _row("wrong-blob", 9, valid_content, extraction_sha256="b" * 64),
        _row("wrong-gap", 8, valid_content),
        _row("wrong-heading", 9, "### Table 3: Relays\nNote"),
    ]
    selected, _ = select_table_preambles([seed], invalid)
    assert selected == []

    prose_seed = _row("prose", 10, "This is prose, not a table.")
    selected, _ = select_table_preambles(
        [prose_seed], [_row("candidate", 9, valid_content)]
    )
    assert selected == []


def test_rejects_ambiguous_or_oversized_preamble():
    seed = _row("table", 10, "| A | B |\n| --- | --- |\n| 1 | 2 |")
    content = "### Table 2: Wiring Terminal Designations\n" + ("x" * 1200)
    assert matching_preamble_span(content, seed["section_title"]) is None

    a = _row("a", 9, "### Table 2: Wiring Terminal Designations\nA")
    b = _row("b", 9, "### Table 2: Wiring Terminal Designations\nB")
    selected, _ = select_table_preambles([seed], [a, b])
    assert selected == []


def test_v2_rejects_predecessor_tail_that_already_contains_a_table():
    seed = _row("table", 10, "| C | D |\n| --- | --- |\n| 3 | 4 |")
    predecessor = _row(
        "cross-table",
        9,
        "### Table 2: Wiring Terminal Designations\n"
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        "Explanatory prose before another split table.",
    )
    selected, trace = select_table_preambles([seed], [predecessor])
    assert selected == []
    assert trace["cross_table_rejected_rows"] == 1


def test_v3_rejects_extracted_table_with_one_hyphen_delimiter_cell():
    seed = _row("table", 10, "| C | D |\n| --- | --- |\n| 3 | 4 |")
    predecessor = _row(
        "extracted-cross-table",
        9,
        "### Table 2: Wiring Terminal Designations\n"
        "| System | | Loop | 1 / 2 |\n"
        "| --- | - | ---- | ----- |\n"
        "| Date | | Technician | |",
    )
    selected, trace = select_table_preambles([seed], [predecessor])
    assert selected == []
    assert trace["cross_table_rejected_rows"] == 1


def test_span_uses_final_matching_heading_and_is_deterministic():
    seed = _row("table", 10, "| A | B |\n| --- | --- |\n| 1 | 2 |")
    content = (
        "### Table 2: Wiring Terminal Designations\nold\n"
        "### Intervening Section\ntext\n"
        "### Table 2: Wiring Terminal Designations\ncurrent note"
    )
    predecessor = _row("preamble", 9, content)
    first, first_trace = select_table_preambles([seed], [predecessor])
    second, second_trace = select_table_preambles([seed], [predecessor])
    assert first == second
    assert first_trace == second_trace
    assert first[0]["coverage_cards"][0]["quote"].endswith("current note")
    assert "old" not in first[0]["coverage_cards"][0]["quote"]


def test_caps_two_preambles_in_seed_order():
    seeds = []
    candidates = []
    for ordinal in range(3):
        seeds.append(
            _row(
                f"seed-{ordinal}",
                ordinal * 2 + 1,
                "| A | B |\n| --- | --- |\n| 1 | 2 |",
                document_id=f"doc-{ordinal}",
            )
        )
        candidates.append(
            _row(
                f"candidate-{ordinal}",
                ordinal * 2,
                "### Table 2: Wiring Terminal Designations\nNote",
                document_id=f"doc-{ordinal}",
            )
        )
    selected, _ = select_table_preambles(seeds, candidates)
    assert [row["id"] for row in selected] == ["candidate-0", "candidate-1"]
