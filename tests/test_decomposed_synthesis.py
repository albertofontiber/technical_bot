import json
from pathlib import Path

import pytest

from scripts.s216_run_decomposed_synthesis_screen import (
    AGGREGATE_OUTPUT_BUDGET,
    _writer_schedule,
)
from scripts.s216_review_decomposed_synthesis_screen import schema as review_schema

from src.rag.decomposed_synthesis import (
    assemble_blocks,
    decomposition_payload,
    decomposition_schema,
    focused_query,
    has_source_citation,
    invalid_citations,
    validate_decomposition,
)


def test_provider_schema_keeps_cardinality_in_local_validation():
    serialized = str(decomposition_schema())
    assert "maxItems" not in serialized
    assert "minItems" not in serialized
    assert "maxLength" not in serialized


def test_decomposer_payload_contains_only_the_untrusted_question():
    assert decomposition_payload("  Pregunta técnica  ") == (
        '{"untrusted_question":"Pregunta técnica"}'
    )


def test_decomposition_requires_ordered_unique_focuses():
    value = {
        "focuses": [
            {"focus_id": "focus_1", "question": "¿Qué valor se configura?"},
            {"focus_id": "focus_2", "question": "¿Cómo se verifica el resultado?"},
        ]
    }
    assert validate_decomposition(value) == value["focuses"]

    value["focuses"][1]["focus_id"] = "focus_3"
    with pytest.raises(ValueError, match="contiguous"):
        validate_decomposition(value)


def test_focused_query_preserves_original_scope_and_limits_the_block():
    query = focused_query(
        "En la Central X, ¿qué valor y cómo se verifica?",
        "En la Central X, ¿qué valor se configura?",
    )
    assert "Consulta original" in query
    assert "Central X" in query
    assert "Responde únicamente esta parte" in query


def test_assembler_is_ordered_and_lossless():
    focuses = [
        {"focus_id": "focus_1", "question": "¿Qué valor se configura?"},
        {"focus_id": "focus_2", "question": "¿Cómo se verifica?"},
    ]
    answer, receipt = assemble_blocks(
        "Pregunta original",
        focuses,
        [
            {"focus_id": "focus_1", "answer": "Valor exacto [F1]."},
            {"focus_id": "focus_2", "answer": "Verificación exacta [F2]."},
        ],
    )
    assert answer.count("Valor exacto [F1].") == 1
    assert answer.count("Verificación exacta [F2].") == 1
    assert "¿Qué valor se configura?" not in answer
    assert "¿Cómo se verifica?" not in answer
    assert "## Parte 1" in answer and "## Parte 2" in answer
    assert answer.index("Valor exacto") < answer.index("Verificación exacta")
    assert receipt["all_focuses_assembled_once"] is True
    assert receipt["focus_count"] == 2


def test_assembler_rejects_missing_or_reordered_blocks():
    focuses = [
        {"focus_id": "focus_1", "question": "Primera parte técnica"},
        {"focus_id": "focus_2", "question": "Segunda parte técnica"},
    ]
    with pytest.raises(ValueError, match="ordered focus plan"):
        assemble_blocks(
            "Pregunta",
            focuses,
            [{"focus_id": "focus_2", "answer": "Respuesta [F1]"}],
        )


def test_invalid_citations_are_checked_against_original_fragment_count():
    assert invalid_citations("Dato [F1], otro [F3] y error [F4].", 3) == [4]
    assert has_source_citation("Dato [F1].") is True
    assert has_source_citation("Dato sin cita.") is False


def test_writer_schedule_equalizes_aggregate_output_budget_and_is_symmetric():
    rows = [{"item_id": "q1", "question": "Pregunta original", "context": []}]
    plans = {
        "q1": [
            {"focus_id": "focus_1", "question": "Primera parte técnica"},
            {"focus_id": "focus_2", "question": "Segunda parte técnica"},
            {"focus_id": "focus_3", "question": "Tercera parte técnica"},
        ]
    }
    jobs = _writer_schedule(rows, plans)
    assert jobs[0]["arm"] == "control" and jobs[0]["replicate"] == 1
    assert jobs[-1]["arm"] == "control" and jobs[-1]["replicate"] == 2
    for replicate in (1, 2):
        treatment = [
            row
            for row in jobs
            if row["arm"] == "treatment" and row["replicate"] == replicate
        ]
        assert sum(row["max_tokens"] for row in treatment) <= AGGREGATE_OUTPUT_BUDGET
    assert all(
        row["max_tokens"] == AGGREGATE_OUTPUT_BUDGET
        for row in jobs
        if row["arm"] == "control"
    )


def test_semantic_review_schema_uses_provider_compatible_local_cardinality():
    serialized = str(review_schema())
    assert "maxItems" not in serialized
    assert "minItems" not in serialized


def test_screen_packet_is_score_free_multichunk_and_target_closed():
    root = Path(__file__).resolve().parents[1]
    packet = json.loads(
        (root / "evals/s216_synthesis_screen_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert packet["population"] == {
        "questions": 49,
        "single_source_development": 14,
        "protected_multichunk": 35,
        "target_questions": 0,
        "multi_context_rows": 376,
    }
    assert all(
        row["item_id"] not in {"cat018", "hp002", "hp011", "hp017"}
        for row in packet["rows"]
    )
    assert all(
        key not in row
        for row in packet["rows"]
        for key in ("facts", "answer_points", "gold", "answer")
    )
    assert all(
        len(row["context"]) >= 2
        for row in packet["rows"]
        if row["role"] == "protected_multichunk"
    )
