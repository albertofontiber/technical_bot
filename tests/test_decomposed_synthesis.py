import pytest

from src.rag.decomposed_synthesis import (
    assemble_blocks,
    decomposition_payload,
    decomposition_schema,
    focused_query,
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
