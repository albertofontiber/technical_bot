import json
from pathlib import Path

import pytest

from src.rag.reference_edge_coverage import (
    select_reference_edge_coverage,
    verify_reference_edge_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
EXTRACTION = "a" * 64


def _row(
    row_id,
    content,
    *,
    section="",
    index=0,
    document="doc-1",
    extraction=EXTRACTION,
):
    return {
        "id": row_id,
        "content": content,
        "manufacturer": "Vendor",
        "product_model": "Panel-X",
        "document_id": document,
        "extraction_sha256": extraction,
        "section_title": section,
        "chunk_index": index,
    }


@pytest.mark.parametrize("section", ["7.6.1", "8.4.2"])
def test_split_heading_and_table_body_resolve_after_section_renumbering(section):
    served = [_row("s", f"To diagnose airflow, see section {section}.", index=2)]
    anchor = _row(
        "a", f"## {section} Reading airflow\n\nGeneral introduction.", section=f"{section} Reading airflow", index=10
    )
    body = _row(
        "b",
        "| Action | Display | Meaning |\n"
        "| Press OK | X11 | Select and diagnose the airflow pipe I measurement |\n"
        "| Press UP | Y22 | Select and diagnose the airflow pipe II measurement |",
        section=f"{section} Reading airflow",
        index=11,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I diagnose the airflow?", served, [anchor, body]
    )
    assert [row["id"] for row in selected] == ["b"]
    assert trace["reason"] == "selected"
    assert selected[0]["section_anchor_receipt"]["candidate_id"] == "a"
    quotes = [card["quote"] for card in selected[0]["coverage_cards"]]
    assert any("X11" in quote for quote in quotes)
    assert any("Y22" in quote for quote in quotes)
    assert all("\n" not in quote for quote in quotes)
    assert verify_reference_edge_receipt(anchor, selected[0]["section_anchor_receipt"])
    assert all(verify_reference_edge_receipt(body, card) for card in selected[0]["coverage_cards"])


def test_same_number_in_table_of_contents_is_rejected():
    served = [_row("s", "For speaker wiring see chapter 4.4.", index=1)]
    toc = _row(
        "toc",
        "## 4.4 Speaker wiring\n"
        "4.4 Speaker wiring ................ 36\n"
        "4.5 Backup amplifier .............. 37\n"
        "4.6 Inputs ........................ 38\n",
        section="4.4 Speaker wiring................36",
        index=5,
    )
    selected, _ = select_reference_edge_coverage(
        "How do I connect the speaker wiring?", served, [toc]
    )
    assert selected == []


def test_duplicate_compatible_body_headings_fail_closed():
    served = [_row("s", "For airflow see section 2.1.", index=1)]
    anchor1 = _row("a1", "## 2.1 Airflow\nIntro", section="2.1 Airflow", index=10)
    anchor2 = _row("a2", "## 2.1 Airflow\nMore", section="2.1 Airflow", index=11)
    body = _row(
        "b", "| Press | Z10 | airflow value |", section="2.1 Airflow", index=12
    )
    selected, _ = select_reference_edge_coverage(
        "How do I diagnose airflow?", served, [anchor1, anchor2, body]
    )
    assert selected == []


def test_incompatible_intervening_heading_breaks_cluster():
    served = [_row("s", "For airflow see section 2.1.", index=1)]
    anchor = _row("a", "## 2.1 Airflow\nIntro", section="2.1 Airflow", index=10)
    incompatible = _row("x", "## 2.2 Battery\nText", section="2.2 Battery", index=11)
    body = _row(
        "b", "| Press | Z10 | airflow value |", section="2.1 Airflow", index=12
    )
    selected, _ = select_reference_edge_coverage(
        "How do I diagnose airflow?", served, [anchor, incompatible, body]
    )
    assert selected == []


def test_same_reference_with_different_object_is_rejected():
    served = [_row("s", "To configure the pump see section 3.1.", index=1)]
    target = _row(
        "t",
        "## 3.1 Pump\n\nPress OK to configure the ventilation fan.",
        section="3.1 Pump",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "How do I configure the water pump?", served, [target]
    )
    assert selected == []


def test_already_served_numeric_atom_is_not_readded():
    served = [
        _row(
            "s",
            "The GPI input is active at 5 to 30 V. See section 5.5.9 for GPI input options.",
            index=1,
        )
    ]
    target = _row(
        "t",
        "## 5.5.9 GPI input options\n\nThe GPI input is active at 5 to 30 V.",
        section="5.5.9 GPI input options",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "What voltage makes the GPI input active?", served, [target]
    )
    assert selected == []


def test_extra_title_words_do_not_make_served_signal_novel():
    served = [
        _row(
            "s",
            "The GPI input threshold is 5 to 30 V. See section 5.5.9 for GPI input options.",
            index=1,
        )
    ]
    target = _row(
        "t",
        "## 5.5.9 GPI input options and configuration details\n\n"
        "For the configurable GPI input, the threshold remains 5 to 30 V.",
        section="5.5.9 GPI input options and configuration details",
        index=2,
    )
    selected, trace = select_reference_edge_coverage(
        "What voltage threshold makes the GPI input active?", served, [target]
    )
    assert selected == []
    assert trace["edge_traces"][0]["terminal_reason"] == "no_novel_atom"


def test_product_codes_in_prose_do_not_make_repeated_action_novel():
    served = [
        _row(
            "s",
            "Configure the WiFi IP settings as described in section 4.2.",
            index=1,
        )
    ]
    target = _row(
        "t",
        "## 4.2 WiFi IP settings\n\n"
        "Configure the same IP settings for the MODEL-X WiFi device.",
        section="4.2 WiFi IP settings",
        index=2,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I configure the WiFi IP settings?", served, [target]
    )
    assert selected == []
    assert trace["edge_traces"][0]["terminal_reason"] == "no_novel_atom"


def test_candidate_bytes_stop_before_incompatible_heading_in_same_chunk():
    served = [_row("s", "To configure the water pump see section 3.1.", index=1)]
    target = _row(
        "t",
        "## 3.1 Pump\n\nGeneral pump information.\n\n"
        "## 3.2 Ventilation\n\nPress OK to configure the water pump from this later section.",
        section="3.1 Pump",
        index=2,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I configure the water pump?", served, [target]
    )
    assert selected == []
    assert trace["edge_traces"][0]["terminal_reason"] == "no_bounded_atomic_unit"


def test_generic_reference_clause_is_evaluated_as_fallback():
    served = [_row("s", "For more information, see section 4.2.", index=1)]
    target = _row(
        "t",
        "## 4.2 Speaker output wiring\n\n"
        "Connect the speaker output terminals and verify the output wiring polarity.",
        section="4.2 Speaker output wiring",
        index=2,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I connect the speaker output wiring?", served, [target]
    )
    assert [row["id"] for row in selected] == ["t"]
    assert trace["edge_traces"][0]["alignment_tier"] == "generic"
    assert trace["potential_reference_edges"] == 1
    assert trace["potential_not_selected_edge_indexes"] == []


def test_query_aligned_reference_outranks_generic_reference():
    served = [
        _row("s1", "For more information, see section 3.1.", index=1),
        _row("s2", "For speaker output wiring, see section 4.2.", index=2),
    ]
    generic = _row(
        "g",
        "## 3.1 General test\n\n"
        "Press OK and connect the speaker output wiring during the general test procedure.",
        section="3.1 General test",
        index=3,
    )
    aligned = _row(
        "a",
        "## 4.2 Speaker output wiring\n\n"
        "Connect the speaker output terminals and verify the speaker wiring polarity.",
        section="4.2 Speaker output wiring",
        index=4,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I connect the speaker output wiring?", served, [generic, aligned]
    )
    assert [row["id"] for row in selected] == ["a"]
    assert {edge["alignment_tier"] for edge in trace["edge_traces"]} == {
        "generic",
        "query_aligned",
    }


def test_generic_reference_requires_query_bound_section_title():
    served = [_row("s", "For more information, see section 5.5.4.", index=1)]
    target = _row(
        "t",
        "## 5.5.4 WiFi options\n\n"
        "Press OK to connect the current user through the existing WiFi network.",
        section="5.5.4 WiFi options",
        index=2,
    )
    selected, trace = select_reference_edge_coverage(
        "How do I access a superior user level after connecting?", served, [target]
    )
    assert selected == []
    assert trace["edge_traces"][0]["terminal_reason"] == (
        "generic_section_not_query_bound"
    )


def test_identity_requires_explicit_pair_but_accepts_descriptive_table_row():
    served = [_row("s", "For the model reference see section 1.2.", index=1)]
    loose = _row(
        "loose",
        "## 1.2 Models\n\nModel reference: ZX10 for the pump controller.",
        section="1.2 Models",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "Which model reference should I order?", served, [loose]
    )
    assert selected == []

    table = _row(
        "table",
        "## 1.2 Models\n\n| Model reference | ZX10 | Pump controller compatible option |",
        section="1.2 Models",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "Which model reference should I order?", served, [table]
    )
    assert [row["id"] for row in selected] == ["table"]


def test_diagnostic_relation_requires_observable_in_same_unit():
    served = [_row("s", "For airflow fault diagnosis see section 6.4.", index=1)]
    relation_only = _row(
        "r",
        "## 6.4 Airflow fault\n\nThe fault means low airflow in the aspiration pipe.",
        section="6.4 Airflow fault",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "What does fault code X11 mean for airflow?", served, [relation_only]
    )
    assert selected == []

    observable = _row(
        "o",
        "## 6.4 Airflow fault\n\nFault code X11 means low airflow in the aspiration pipe.",
        section="6.4 Airflow fault",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "What does fault code X11 mean for airflow?", served, [observable]
    )
    assert [row["id"] for row in selected] == ["o"]


def test_overlong_multiline_unit_splits_only_at_line_boundaries():
    served = [_row("s", "To configure the water pump see section 3.1.", index=1)]
    line = "Press OK to configure the water pump and verify the pump status carefully. " * 4
    target = _row(
        "t",
        "## 3.1 Pump\n\n" + "\n".join([line, line.replace("OK", "UP"), line]),
        section="3.1 Pump",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "How do I configure the water pump?", served, [target]
    )
    assert [row["id"] for row in selected] == ["t"]
    assert all(len(card["quote"]) <= 720 for card in selected[0]["coverage_cards"])


def test_explicit_subsection_beyond_first_card_is_located_exactly():
    served = [_row("s", "To disable a zone see section 2.2.7(e).", index=1)]
    content = (
        "## 2.2.7 Zone selection\n\n"
        + "General selection information. " * 40
        + "\n\n(e) Disabled zone\nPress OK to disable the selected zone."
    )
    target = _row("t", content, section="2.2.7 Zone selection", index=2)
    selected, _ = select_reference_edge_coverage(
        "How do I disable the selected zone?", served, [target]
    )
    assert [row["id"] for row in selected] == ["t"]
    assert selected[0]["reference_edge"]["subsection"] == "e"
    quote = "\n".join(card["quote"] for card in selected[0]["coverage_cards"])
    assert "Disabled zone" in quote
    assert "Press OK" in quote


def test_receipts_fail_on_tampering_and_missing_provenance():
    served = [_row("s", "For airflow see section 2.1.", index=1)]
    target = _row(
        "t",
        "## 2.1 Airflow\n\nPress OK to read and confirm the current airflow measurement.",
        section="2.1 Airflow",
        index=2,
    )
    selected, _ = select_reference_edge_coverage(
        "How do I read airflow?", served, [target]
    )
    receipt = selected[0]["coverage_cards"][0]
    assert verify_reference_edge_receipt(target, receipt)
    assert not verify_reference_edge_receipt(target, dict(receipt, quote="tampered"))
    assert not verify_reference_edge_receipt(target, dict(receipt, facet="wrong"))
    assert not verify_reference_edge_receipt(target, dict(receipt, end=receipt["start"]))
    assert not verify_reference_edge_receipt(dict(target, document_id=""), receipt)
    assert not verify_reference_edge_receipt(dict(target, extraction_sha256="abc"), receipt)


def test_actual_hp002_preserves_v01_v02_with_sibling_anchor():
    contexts = json.loads(
        (ROOT / "evals/s113_full_contexts_freeze_v1.json").read_text(encoding="utf-8")
    )["rows"]
    corpus = json.loads(
        (ROOT / "evals/s114_five_product_corpus_slice_v1.json").read_text(encoding="utf-8")
    )["rows"]
    frozen = next(row for row in contexts if row["qid"] == "hp002")
    selected, _ = select_reference_edge_coverage(
        frozen["question"], frozen["context"], corpus
    )
    assert [row["id"] for row in selected] == [
        "a64c168c-c927-4f8b-a179-e465e6df3976"
    ]
    quote = "\n".join(card["quote"] for card in selected[0]["coverage_cards"])
    assert "V01" in quote and "V02" in quote
