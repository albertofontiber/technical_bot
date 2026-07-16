from collections import Counter

from scripts.s114_audit_extraction_fidelity import (
    TARGETS,
    keep_best_receipt,
    notation_signals,
    target_matches,
    target_matches_by_field,
)


def _row(content: str, **kwargs):
    return {
        "content": content,
        "context": kwargs.pop("context", ""),
        "section_title": kwargs.pop("section_title", ""),
        "product_model": kwargs.pop("product_model", ""),
        "source_file": kwargs.pop("source_file", ""),
        "has_diagram": kwargs.pop("has_diagram", False),
        "diagram_url": kwargs.pop("diagram_url", None),
        **kwargs,
    }


def test_collapsed_power_is_candidate_only_in_technical_life_context():
    risky = _row("Minimum contact life: 105 operations")
    unrelated = _row("Catalogue code 105")
    assert "collapsed_power_candidate" in {name for name, _ in notation_signals(risky)}
    assert "collapsed_power_candidate" not in {name for name, _ in notation_signals(unrelated)}


def test_collapsed_power_table_relation_survives_markdown_cells():
    row = _row("| Life Time | 105 | | Operations |")
    assert "collapsed_power_candidate" in {name for name, _ in notation_signals(row)}


def test_explicit_power_and_split_unit_are_distinct_signals():
    row = _row("Life 10^5 operations\n| Resistance | 47 | kohm |")
    signals = {name for name, _ in notation_signals(row)}
    assert "explicit_scientific_notation" in signals
    assert "split_numeric_unit_cell" in signals


def test_numeric_visual_without_receipt_is_review_candidate():
    row = _row("| Table | value |\n| --- | --- |\n| x | 25 |", has_diagram=True)
    assert "numeric_page_image_without_render_receipt" in {
        name for name, _ in notation_signals(row)
    }


def test_target_scope_and_relations_are_recorded_without_entailment_claim():
    row = _row(
        "A CLIP licence is required per loop.",
        product_model="INSPIRE E10",
    )
    matches = target_matches(row, TARGETS["cat017"])
    assert set(matches) == {"clip", "licence", "loop", "per_loop_quantifier"}


def test_spanish_one_licence_per_loop_circuit_is_recognized():
    row = _row(
        "Se requiere una licencia para cada circuito de lazo CLIP.",
        product_model="INSPIRE E10",
    )
    assert set(target_matches(row, TARGETS["cat017"])) == {
        "clip",
        "licence",
        "loop",
        "per_loop_quantifier",
    }


def test_asd_variables_require_exact_identifier_boundaries():
    row = _row("Read V01 and V02 for airflow.", product_model="ASD535")
    matches = target_matches(row, TARGETS["hp002"])
    assert {"v01", "v02", "airflow"} <= set(matches)


def test_match_names_are_counted_not_match_objects():
    row = _row("Read V01 and V02 for airflow.", product_model="ASD535")
    matches = target_matches(row, TARGETS["hp002"])
    counts = Counter()
    counts.update(matches.keys())
    assert counts == {"v01": 1, "v02": 1, "airflow": 1}


def test_collapsed_power_requires_nearby_context_not_anywhere_in_long_chunk():
    row = _row("Catalogue 105 " + "x" * 400 + " contact life operations")
    assert "collapsed_power_candidate" not in {
        name for name, _ in notation_signals(row)
    }


def test_best_target_receipts_prefer_more_complete_signal_bundles():
    receipts = []
    keep_best_receipt(
        receipts, {"id": "one", "signals": ["clip"], "content_signals": ["clip"]}, limit=2
    )
    keep_best_receipt(
        receipts,
        {
            "id": "three",
            "signals": ["clip", "licence", "loop"],
            "content_signals": ["clip", "licence", "loop"],
        },
        limit=2,
    )
    keep_best_receipt(
        receipts,
        {"id": "two", "signals": ["clip", "loop"], "content_signals": ["clip", "loop"]},
        limit=2,
    )
    assert [row["id"] for row in receipts] == ["three", "two"]


def test_retrieval_context_is_not_counted_as_source_evidence():
    row = _row(
        "The extracted content only discusses airflow.",
        context="Read V01 and V02.",
        product_model="ASD535",
    )
    matches = target_matches_by_field(row, TARGETS["hp002"])
    assert set(matches["content"]) == {"airflow"}
    assert set(matches["context"]) == {"v01", "v02"}


def test_absolute_impossibility_pattern_rejects_unrelated_negative_sentence():
    unrelated = _row(
        "Verify that there are no cuts in the line. A zone supports 32 detectors.",
        product_model="CCD-103",
    )
    explicit = _row(
        "It is impossible to disable an individual detector from this panel.",
        product_model="CCD-103",
    )
    assert "explicit_impossibility" not in target_matches(unrelated, TARGETS["hp015"])
    assert "explicit_impossibility" in target_matches(explicit, TARGETS["hp015"])
