import pytest

from src.rag.generator import (
    _append_required_coverage_evidence,
    _coverage_obligations_block,
)


def _chunk(chunk_id="c1", content="La resistencia máxima es 35 ohmios."):
    return {"id": chunk_id, "content": content}


def test_coverage_block_requires_exact_span_and_matching_fragment():
    block = _coverage_obligations_block(
        [
            {
                "fragment_number": 1,
                "candidate_id": "c1",
                "quote": "La resistencia máxima es 35 ohmios.",
                "exact_source_span_validated": True,
            }
        ],
        [_chunk()],
    )
    assert "[F1]" in block
    assert "35 ohmios" in block


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_id": "wrong"},
        {"fragment_number": 2},
        {"quote": "La resistencia máxima es 99 ohmios."},
        {"exact_source_span_validated": False},
    ],
)
def test_coverage_block_fails_closed(change):
    obligation = {
        "fragment_number": 1,
        "candidate_id": "c1",
        "quote": "La resistencia máxima es 35 ohmios.",
        "exact_source_span_validated": True,
    }
    obligation.update(change)
    with pytest.raises(ValueError):
        _coverage_obligations_block([obligation], [_chunk()])


def test_required_coverage_block_is_explicitly_mandatory():
    block = _coverage_obligations_block(
        [
            {
                "fragment_number": 1,
                "candidate_id": "c1",
                "quote": "La resistencia máxima es 35 ohmios.",
                "exact_source_span_validated": True,
                "required": True,
            }
        ],
        [_chunk(content="La resistencia máxima es 35 ohmios.")],
    )
    assert "COBERTURA OBLIGATORIA" in block
    assert "TODOS" in block


def test_required_coverage_appendix_normalizes_table_without_adding_facts():
    answer = _append_required_coverage_evidence(
        "Respuesta principal.",
        [
            {
                "fragment_number": 1,
                "candidate_id": "c1",
                "quote": "| 3 | PWR-R |\n|---|---|\n| 4 | 0 V |",
                "exact_source_span_validated": True,
                "required": True,
            }
        ],
    )
    assert "Evidencia documental de cobertura" in answer
    assert "[F1]" in answer
    assert "PWR-R" in answer
    assert "|" not in answer


def test_required_coverage_appendix_normalizes_html_line_breaks():
    answer = _append_required_coverage_evidence(
        "Respuesta.",
        [
            {
                "fragment_number": 2,
                "quote": "Resistencia 6K8.<br/>Carga máxima 1A.",
                "required": True,
            }
        ],
    )
    assert "6K8.; Carga máxima 1A." in answer
    assert "<br" not in answer


def test_required_and_advisory_obligations_cannot_be_mixed():
    obligations = [
        {
            "fragment_number": 1,
            "candidate_id": "c1",
            "quote": "uno",
            "exact_source_span_validated": True,
            "required": True,
        },
        {
            "fragment_number": 2,
            "candidate_id": "c2",
            "quote": "dos",
            "exact_source_span_validated": True,
        },
    ]
    with pytest.raises(ValueError):
        _coverage_obligations_block(
            obligations,
            [_chunk("c1", "uno"), _chunk("c2", "dos")],
        )
