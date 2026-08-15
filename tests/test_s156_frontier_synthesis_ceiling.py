import json
import os

import pytest

from scripts.s156_frontier_synthesis_ceiling import (
    FREEZE,
    QIDS,
    _citations,
    build_prompt,
    score_answer,
)


def test_citation_parser_is_exact():
    assert _citations("dato [F1], otro [F12]; no [F0x]") == [1, 12]


@pytest.fixture(autouse=True)
def _contener_runtime_env():
    """`build_prompt()` llama a `_configure_runtime()`, que hace `os.environ.update(RUNTIME_ENV)`:
    muta el entorno GLOBAL del proceso como efecto colateral de construir un prompt. Por CLI eso es
    deliberado (fija el runtime antes de medir); dentro de pytest se ESCAPA al resto de la sesion.

    Cazado en s321: dejaba `GENERATOR_INCLUDE_CONTEXT='0'` puesta, y `factlevel_assessment:206` la
    guarda con `assert not os.getenv(...)` ⇒ todo test posterior que importara ese instrumento
    reventaba. Pero se escapaban las CINCO de RUNTIME_ENV — tambien `ANSWER_OBLIGATION_PLANNER` y
    `GENERATOR_SELECTION_BLOCK`, que cambian conducta de generacion para cualquier test que corriera
    despues. Se contiene aqui, en el borde, sin tocar el harness.
    """
    from scripts.s156_frontier_synthesis_ceiling import RUNTIME_ENV
    previo = {k: os.environ.get(k) for k in RUNTIME_ENV}
    try:
        yield
    finally:
        for k, v in previo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_prompt_preserves_question_and_all_fragment_headers():
    row = {
        "question": "¿Qué debo comprobar?",
        "context": [
            {"id": "a", "content": "Valor 1.", "product_model": "M1", "similarity": 0.9},
            {"id": "b", "content": "Valor 2.", "product_model": "M1", "similarity": 0.8},
        ],
    }
    system, prompt = build_prompt(row)
    assert system
    assert "¿Qué debo comprobar?" in prompt
    assert "[Fragmento 1" in prompt and "[Fragmento 2" in prompt
    assert "Valor 1." in prompt and "Valor 2." in prompt


def test_target_population_is_frozen():
    assert QIDS == ("cat018", "hp002", "hp011", "hp017")


def test_invalid_citations_are_detected():
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {row["qid"]: row for row in payload["rows"]}
    result = score_answer("cat018", "No consta [F999].", frozen)
    assert result["relations"] == 2
    assert result["covered"] == 0
    assert result["invalid_citations"] == [999]
