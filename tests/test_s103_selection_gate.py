"""Tests del bloque de selección CODE-GATED (s103b, fork DEC-097 ejecutado).

La garantía central es POR CONSTRUCCIÓN y se prueba a $0 sin LLM (DEC-015: el aislamiento
no se prueba con output): el bloque solo entra al prompt cuando la query dispara el regex
`_SELECTION_INTENT`; para toda pregunta de especificación/avería/config el prompt es
BYTE-IDÉNTICO al de flag-off — la clase hp009 (clarify-en-vez-de-answer, medida 2/3→3/3 en
las variantes prompt-gated) no puede regresar por este bloque.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.generator import (  # noqa: E402
    _SELECTION_BLOCK,
    _assemble_system,
    _is_selection_query,
    _selection_block_on,
)

Q_SELECCION = ("Necesito un detector de llama SharpEye «40/40» (Spectrex / Notifier) "
               "para una instalación; ¿qué modelo pido?")
Q_SPEC = ("¿Qué resistencia de final de línea llevan las salidas de sirena de la "
          "central Morley ZXe?")  # clase hp009/hp018: spec de equipo nombrado
Q_CONSUMO = "¿Cuál es el consumo en alarma de la sirena analógica de zócalo Detnov MAD-472?"
Q_CONEXION = "¿Cómo se conecta una sirena convencional en las salidas de sirena de la ZXe?"


def test_regex_dispara_en_seleccion_y_no_en_spec():
    assert _is_selection_query(Q_SELECCION)
    assert not _is_selection_query(Q_SPEC)
    assert not _is_selection_query(Q_CONSUMO)
    assert not _is_selection_query(Q_CONEXION)


def test_regex_negativos_fraseo_tecnico_real():
    """(F2 dúo s103b, EJECUTADO por el sub-agente) Fraseo canónico de avería/config/
    identificación que NO debe disparar el bloque — «¿cuál pongo?» es EL fraseo de
    resistencias/jumpers/DIP en español."""
    negativos = [
        "Las salidas de sirena de la ZXe piden resistencia final de línea, ¿cuál pongo?",
        "El jumper JP2 de la CAD-150, ¿cuál pongo para NC?",
        "¿Qué modelo va instalado en el lazo 2 según el esquema?",
        "¿Cuál necesito, la de 4k7 o la de 10k?",
        "¿Cuál uso para el lazo, cable trenzado o apantallado?",
    ]
    for q in negativos:
        assert not _is_selection_query(q), q


def test_regex_positivos_seleccion_con_relleno():
    """Selección legítima con palabras intercaladas entre «modelo» y el verbo (el miss
    que el dúo cazó) — el gap acotado debe cubrirlo."""
    positivos = [
        "¿Qué modelo de detector de la serie 40/40 pido para hidrógeno?",
        "¿Qué central me recomiendas para 4 lazos?",
        "Voy a ampliar la instalación, ¿cuál me recomiendas?",
    ]
    for q in positivos:
        assert _is_selection_query(q), q


def test_flag_off_prompt_identico(monkeypatch):
    monkeypatch.delenv("GENERATOR_SELECTION_BLOCK", raising=False)
    assert _SELECTION_BLOCK not in _assemble_system(Q_SELECCION)


def test_flag_on_solo_entra_en_seleccion(monkeypatch):
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "on")
    assert _assemble_system(Q_SELECCION).endswith(_SELECTION_BLOCK)
    # POR CONSTRUCCIÓN: spec/avería/config → prompt byte-idéntico a flag-off
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "on")
    with_flag = _assemble_system(Q_SPEC)
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "off")
    without_flag = _assemble_system(Q_SPEC)
    assert with_flag == without_flag


def test_flag_on_sin_query_no_inyecta(monkeypatch):
    """Callers legacy sin query (None) jamás reciben el bloque — fail-safe."""
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "on")
    assert _SELECTION_BLOCK not in _assemble_system(None)
    assert _SELECTION_BLOCK not in _assemble_system()


def test_compone_con_fidelity(monkeypatch):
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "on")
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "fidelity")
    s = _assemble_system(Q_SELECCION)
    from src.rag.generator import _FIDELITY_BLOCK, SYSTEM_PROMPT
    assert s == SYSTEM_PROMPT + _FIDELITY_BLOCK + _SELECTION_BLOCK


def test_flag_parser_fail_fast(monkeypatch):
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "0")
    assert _selection_block_on() is False
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "on")
    assert _selection_block_on() is True
    monkeypatch.setenv("GENERATOR_SELECTION_BLOCK", "typo")
    with pytest.raises(RuntimeError):
        _selection_block_on()
