"""s331 M3c-conducta — GENERATOR_NO_REASK sobre el canal `turn_identity` (G3 unit).

Dos sitios (Sol-2 r-v2): el PROMPT (`_assemble_system`) y las PLANTILLAS
deterministas sin-evidencia (la re-pregunta amnésica vivía también ahí, sin
pasar por el LLM). Dos niveles (Sol-2 r-v1): RESUELTO = no re-preguntar
identidad; MENCIÓN = reconocerla, confirmación dirigida PERMITIDA. Flag off o
identidad None ⇒ byte-idéntico a hoy (prompt Y plantillas). Sin red ni LLM:
el path sin-evidencia retorna ANTES de cualquier llamada.
"""
from __future__ import annotations

import pytest

from src.orchestrator.conversation_policy import TurnIdentity
from src.rag.generator import _assemble_system, generate_answer

TI_RESUELTO = TurnIdentity(resolved_models=("2X-AF1-FB-S",),
                           models_provenance="resolved_this_turn")
TI_MENCION = TurnIdentity(mention="EMA1224B4RW-XQ", mention_provenance="this_turn")
TI_MIXTO = TurnIdentity(resolved_models=("CAD-150",), models_provenance="carried",
                        mention="EMA1224B4RW-XQ", mention_provenance="this_turn",
                        route_cut=True)


@pytest.fixture(autouse=True)
def _sin_flags(monkeypatch):
    monkeypatch.delenv("GENERATOR_NO_REASK", raising=False)
    yield


# ---------------------------------------------------------------------------
# Sitio 1: el prompt
# ---------------------------------------------------------------------------
def test_prompt_resuelto_no_repregunta(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    sistema = _assemble_system("¿programación?", turn_identity=TI_RESUELTO)
    assert "NO vuelvas a preguntar qué modelo" in sistema
    assert "2X-AF1-FB-S" in sistema
    assert "declarando el alcance" in sistema


def test_prompt_mencion_reconoce_y_permite_confirmacion(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    sistema = _assemble_system("¿programación?", turn_identity=TI_MENCION)
    assert "«EMA1224B4RW-XQ»" in sistema
    assert "RECONÓCELO" in sistema
    assert "UNA confirmación dirigida" in sistema


def test_prompt_mixto_usa_nivel_mencion(monkeypatch):
    # Estado mixto (Sol-3 r-v2): la mención NUEVA manda sobre el carried.
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    sistema = _assemble_system("¿programación?", turn_identity=TI_MIXTO)
    assert "«EMA1224B4RW-XQ»" in sistema
    assert "CAD-150" in sistema                      # el contexto no se pierde


def test_prompt_flag_off_byte_identico():
    con = _assemble_system("¿programación?", turn_identity=TI_RESUELTO)
    sin = _assemble_system("¿programación?")
    assert con == sin                                # off (default) ⇒ ni un byte


def test_prompt_identidad_none_byte_identico(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    assert _assemble_system("¿programación?", turn_identity=None) == \
        _assemble_system("¿programación?")


def test_guard_estricto_revienta(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "quizas")
    with pytest.raises(RuntimeError, match="GENERATOR_NO_REASK"):
        _assemble_system("q", turn_identity=TI_RESUELTO)


# ---------------------------------------------------------------------------
# Sitio 2: las plantillas deterministas sin-evidencia (sin LLM)
# ---------------------------------------------------------------------------
def test_plantilla_mencion_reconoce_no_amnesia(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    out = generate_answer("¿programación?", [], available_models=["2X-AF1"],
                          turn_identity=TI_MENCION)
    assert "«EMA1224B4RW-XQ»" in out["answer"]
    assert "modelo concreto que estás usando" not in out["answer"]
    assert out["stop_reason"] is None                # sin llamada LLM


def test_plantilla_resuelto_decline_con_alcance(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    out = generate_answer("¿programación?", [], available_models=["2X-AF1"],
                          turn_identity=TI_RESUELTO)
    assert "2X-AF1-FB-S" in out["answer"]
    assert "modelo concreto que estás usando" not in out["answer"]


def test_plantilla_flag_off_historica_byte_identica():
    con_ti = generate_answer("¿programación?", [], available_models=["2X-AF1"],
                             turn_identity=TI_MENCION)
    sin_ti = generate_answer("¿programación?", [], available_models=["2X-AF1"])
    assert con_ti["answer"] == sin_ti["answer"]      # off ⇒ plantilla de hoy
    assert "¿Puedes indicarme el modelo concreto que estás usando?" \
        in sin_ti["answer"]


def test_plantilla_identidad_none_historica(monkeypatch):
    monkeypatch.setenv("GENERATOR_NO_REASK", "on")
    out = generate_answer("¿programación?", [], available_models=["2X-AF1"])
    assert "¿Puedes indicarme el modelo concreto que estás usando?" in out["answer"]
