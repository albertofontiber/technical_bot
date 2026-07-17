from scripts.s167_independent_answer_ledger_gate import (
    _population_checks,
    score_selection,
    validate_author_item,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _source():
    excerpt = "## Ajuste\n\nAntes de conectar, seleccione Modo Seguro.\n\nVerifique el LED verde al finalizar."
    return {
        "item_id": "s167_src_01",
        "stratum": "prose",
        "manufacturer": "Maker",
        "product_model": "P1",
        "document_id": "doc1",
        "chunk_id": "chunk1",
        "excerpt": excerpt,
        "excerpt_sha256": "a" * 64,
    }


def test_s167_author_requires_multiple_exact_distinct_points():
    source = _source()
    item, repairs = validate_author_item(
        {
            "item_id": "s167_src_01",
            "eligible": True,
            "question": "¿Cómo configuro y verifico el P1?",
            "answer_points": [
                {"claim": "prerequisite", "exact_quote": "Antes de conectar, seleccione Modo Seguro."},
                {"claim": "verification", "exact_quote": "Verifique el LED verde al finalizar."},
            ],
        },
        source,
    )
    assert repairs == 0
    assert len(item["answer_points"]) == 2


def test_s167_score_uses_stable_union_units_for_claim_recall_and_precision():
    source = _source()
    item, _ = validate_author_item(
        {
            "item_id": "s167_src_01",
            "eligible": True,
            "question": "¿Cómo configuro y verifico el P1?",
            "answer_points": [
                {"claim": "prerequisite", "exact_quote": "Antes de conectar, seleccione Modo Seguro."},
                {"claim": "verification", "exact_quote": "Verifique el LED verde al finalizar."},
            ],
        },
        source,
    )
    units = build_header_aware_evidence_units(
        source["excerpt"], fragment_number=1, candidate_id="s167_src_01"
    )
    selected = [unit.unit_id for unit in units if "Antes de conectar" in unit.content or "Verifique" in unit.content]
    score = score_selection(item, units, selected)
    assert score["claims_covered"] == 2
    assert score["complete"] is True
    assert score["useful_units"] == score["selected_units"]


def test_s167_population_gate_is_frozen_and_stratified():
    items = []
    for index in range(12):
        items.append(
            {
                "eligible": True,
                "manufacturer": f"M{index}",
                "stratum": "table" if index < 6 else "prose",
                "answer_points": [{}, {}],
            }
        )
    checks = _population_checks(
        items,
        {
            "eligible_questions_min": 12,
            "eligible_manufacturers_min": 12,
            "table_questions_min": 5,
            "prose_questions_min": 5,
            "answer_points_min": 24,
        },
    )
    assert all(checks.values())
