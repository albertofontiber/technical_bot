from __future__ import annotations

import hashlib
import json

import pytest

from scripts.s194_decomposed_evidence_planner_gate import (
    _chunks_v3_lane,
    compile_append,
    score_selection,
    validate_plan,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _units():
    source = (
        "Antes de intervenir, desconecte la alimentación y verifique el aislamiento. "
        + "Mantenga bloqueados los controles remotos durante la prueba. " * 6
        + "\n\nDespués del reinicio, compruebe que la tensión sea 24 V y registre el resultado. "
        + "Confirme también el estado normal de todos los indicadores. " * 6
    )
    return source, build_header_aware_evidence_units(
        source, fragment_number=1, candidate_id="chunk-1", max_chars=400, overlap_chars=0
    )


def test_validate_plan_preserves_obligation_order_and_deduplicates_across_rows():
    _source, units = _units()
    ids = [unit.unit_id for unit in units]
    value = {
        "obligations": [
            {"label": "aislar", "unit_ids": [ids[0]]},
            {"label": "verificar", "unit_ids": [ids[0], ids[-1]]},
        ]
    }
    plan, selected = validate_plan(value, set(ids))
    assert [row["label"] for row in plan] == ["aislar", "verificar"]
    assert selected == list(dict.fromkeys([ids[0], ids[0], ids[-1]]))


@pytest.mark.parametrize(
    "value",
    [
        {"obligations": [{"label": "", "unit_ids": ["known"]}]},
        {"obligations": [{"label": "x", "unit_ids": []}]},
        {"obligations": [{"label": "x", "unit_ids": ["unknown"]}]},
        {"obligations": [{"label": "x", "unit_ids": ["known", "known"]}]},
    ],
)
def test_validate_plan_fails_closed(value):
    with pytest.raises(ValueError):
        validate_plan(value, {"known"})


def test_compile_append_is_exact_additive_and_deterministic():
    source, units = _units()
    selected = [unit.unit_id for unit in units]
    first, receipt = compile_append("Respuesta base.", units, selected)
    second, second_receipt = compile_append("Respuesta base.", units, selected)
    assert first == second
    assert receipt == second_receipt
    assert first.startswith("Respuesta base.")
    assert all(unit.content in first for unit in units)
    assert first.count("[F1]") == len(units)
    assert receipt["baseline_is_exact_prefix"]
    assert receipt["append_sha256"] == hashlib.sha256(
        first.split("Información adicional verificada del manual:\n\n", 1)[1].encode(
            "utf-8"
        )
    ).hexdigest()
    assert source


def test_score_selection_requires_all_support_units_for_a_point():
    source, units = _units()
    assert len(units) >= 2
    item = {
        "excerpt": source,
        "answer_points": [
            {
                "claim": "aislar y verificar",
                "support_unit_ids": [units[0].unit_id, units[-1].unit_id],
            }
        ],
    }
    partial = score_selection(item, units, [units[0].unit_id])
    complete = score_selection(
        item, units, [units[0].unit_id, units[-1].unit_id]
    )
    assert partial["points_covered"] == 0
    assert not partial["complete"]
    assert complete["points_covered"] == 1
    assert complete["complete"]
    assert complete["compiler_exact"]
    assert complete["compiler_deterministic"]


def test_frozen_source_packet_is_fresh_balanced_and_read_only():
    payload = json.loads(
        open("evals/s194_fresh_source_packet_v1.json", encoding="utf-8").read()
    )
    selection = payload["selection"]
    assert payload["status"] == "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY"
    assert selection["items"] == selection["manufacturers"] == 14
    assert selection["unique_documents"] == 14
    assert selection["table"] == selection["prose"] == 7
    assert selection["source_table"] == "chunks_v2"
    assert selection["prior_document_overlap"] == 0
    assert selection["target_document_overlap"] == 0
    assert selection["target_chunk_overlap"] == 0
    assert selection["development_product_pair_overlap"] == 0
    assert payload["read_receipt"]["rows"] == 25090
    assert payload["read_receipt"]["database_writes"] == 0
    for row in payload["items"]:
        assert row["excerpt_sha256"] == hashlib.sha256(
            row["excerpt"].encode("utf-8")
        ).hexdigest()
        units = build_header_aware_evidence_units(
            row["excerpt"], fragment_number=1, candidate_id=row["item_id"]
        )
        assert row["evidence_unit_manifest"] == [
            {
                "unit_id": unit.unit_id,
                "unit_kind": unit.unit_kind,
                "source_spans": [list(span) for span in unit.source_spans],
                "content_sha256": unit.content_sha256,
            }
            for unit in units
        ]


def test_chunks_v3_remains_an_explicit_unchanged_no_go_lane():
    lane = _chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["baseline"]["chunks_v2_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_mrr"] < lane["baseline"]["chunks_v2_mrr"]
    assert lane["changed_by_s194"] is False
    assert lane["per_question_patching"] is False
