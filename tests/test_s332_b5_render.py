"""s332 B5 — render bot de las asunciones: sufijo del answer + obs del trace.

La mitad harness (rama F1, tabla) tiene sus tests propios; aquí se pinea la capa
BOT: el sufijo determinista de `marca_corregida` (con la cita de la pregunta
BASE — la ventana que hace visible un rebuild rancio, R8) y la vista derivada
`_asunciones_obs` (privacidad: `detectado` jamás sale hacia el trace).
"""
from __future__ import annotations

from src.bot.telegram_bot import _asunciones_obs, _con_sufijo_asunciones
from src.orchestrator.contracts import Asuncion
from src.orchestrator.conversation_policy import TurnResolution, PolicyRoute


def _resolucion(asunciones=(), override=None):
    return TurnResolution(
        route=PolicyRoute.STANDALONE,
        query_for_retrieval="q",
        asunciones=asunciones,
        state_query_override=override,
    )


def test_sufijo_declara_marca_y_pregunta_base():
    res = _resolucion(
        asunciones=(Asuncion(kind="marca_corregida", detectado="Kidde",
                             asumido="Kidde", modo="reescrito"),),
        override="¿Qué centrales BQide tienes?",
    )
    out = _con_sufijo_asunciones("La respuesta.", res)
    assert out.startswith("La respuesta.")
    assert "ℹ️ Respondo a tu pregunta anterior («¿Qué centrales BQide tienes?»)" in out
    assert "la marca es Kidde" in out


def test_sufijo_sin_asunciones_es_identidad():
    assert _con_sufijo_asunciones("Tal cual.", _resolucion()) == "Tal cual."


def test_sufijo_ignora_kinds_ajenos():
    res = _resolucion(asunciones=(Asuncion(kind="marca_asr", detectado="BQide",
                                           asumido="Kidde", modo="reescrito"),))
    # `marca_asr` se declara en la CONFIRMACIÓN de voz (pre-turno), no aquí.
    assert _con_sufijo_asunciones("R.", res) == "R."


def test_obs_off_cuando_ambos_levers_apagados(monkeypatch):
    monkeypatch.delenv("ASR_AVISOS", raising=False)
    monkeypatch.delenv("F1_MARCA_CORRECCION", raising=False)
    assert _asunciones_obs(None, ()) == {"status": "off"}


def test_obs_on_combina_fuentes_y_no_filtra_detectado(monkeypatch):
    monkeypatch.setenv("ASR_AVISOS", "on")
    monkeypatch.delenv("F1_MARCA_CORRECCION", raising=False)
    asr = (Asuncion(kind="marca_asr", detectado="ID", asumido="Kidde",
                    modo="aviso"),)
    res = _resolucion(asunciones=(Asuncion(kind="marca_corregida",
                                           detectado="Kidde", asumido="Kidde",
                                           modo="reescrito"),))
    obs = _asunciones_obs(res, asr)
    assert obs["status"] == "on"
    assert obs["items"] == [
        {"kind": "marca_asr", "modo": "aviso", "asumido": "Kidde"},
        {"kind": "marca_corregida", "modo": "reescrito", "asumido": "Kidde"},
    ]
    assert all("detectado" not in item for item in obs["items"])


def test_obs_del_trace_end_to_end_con_el_builder(monkeypatch):
    """El obs de B5 alimenta la sección B6 y valida en el sink — lock-step."""
    from src.rag.runtime_trace import build_rag_serving_trace, validate_rag_serving_trace

    monkeypatch.setenv("ASR_AVISOS", "on")
    obs = _asunciones_obs(None, (Asuncion(kind="marca_asr", detectado="BQide",
                                          asumido="Kidde", modo="reescrito"),))
    trace = build_rag_serving_trace(
        coverage_trace=None, served_chunks=[], must_preserve_trace=None,
        must_preserve_outcome=None, release_policy={"profile": "legacy"},
        transport_parts=1, asunciones_obs=obs)
    assert trace["asunciones"]["n"] == 1
    assert validate_rag_serving_trace(trace) == trace
