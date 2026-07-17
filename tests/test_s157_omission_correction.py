import pytest

from src.rag.omission_correction import (
    answer_citations,
    invalid_citations,
    point_covered,
    prompt_payload,
    render_verified_omissions,
    units_by_fragment,
    validate_selected_ids,
)


def _chunks():
    return [
        {"id": "a", "content": "Antes del mantenimiento, desconecte la zona.\n\nValor: 300 s."},
        {"id": "b", "content": "| Estado | Valor |\n| --- | --- |\n| Alarma | 120 % |"},
    ]


def test_units_and_rendering_preserve_original_source():
    grouped = units_by_fragment(_chunks())
    assert set(grouped) == {1, 2}
    selected = [grouped[1][0], grouped[2][-1]]
    rendered = render_verified_omissions(selected)
    assert "Fragmento original F1" in rendered and "Fragmento original F2" in rendered
    assert selected[0].content in rendered and selected[1].content in rendered


def test_selection_is_bounded_unique_and_known():
    units = units_by_fragment(_chunks())[1]
    assert validate_selected_ids({"unit_ids": [units[0].unit_id]}, units) == [units[0]]
    with pytest.raises(ValueError):
        validate_selected_ids({"unit_ids": ["unknown"]}, units)
    with pytest.raises(ValueError):
        validate_selected_ids({"unit_ids": [units[0].unit_id] * 2}, units)


def test_citations_fail_closed():
    assert answer_citations("Uno [F1], dos [F2].") == [1, 2]
    assert invalid_citations("[F0] [F2] [F4]", 3) == [0, 4]


def test_local_point_proxy_handles_markdown_and_critical_values():
    point = {"claim": "El retardo máximo es de 300 segundos", "exact_quote": "300 s"}
    assert point_covered("El **retardo máximo** es **300 s** [F1].", point)
    assert not point_covered("El retardo máximo no consta [F1].", point)


def test_selector_payload_contains_no_gold():
    units = units_by_fragment(_chunks())[1]
    payload = prompt_payload("¿Qué hago?", "Borrador", units)
    assert "answer_points" not in payload and "exact_quote" not in payload
    assert "Borrador" in payload and units[0].unit_id in payload
