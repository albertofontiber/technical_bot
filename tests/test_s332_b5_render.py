"""s332 B5 (· s335c: sufijo→CABECERA) — render bot de las asunciones + obs del trace.

La mitad harness (rama F1, tabla) tiene sus tests propios; aquí se pinea la capa
BOT: la nota determinista de `marca_corregida` como CABECERA del answer (con la
cita de la pregunta BASE — la ventana que hace visible un rebuild rancio, R8;
s335c: Alberto adjudicó cabecera sobre su chat real — el control va ANTES del
contenido), la protección por ORDEN del estado (la nota jamás entra en el
excerpt/feedback) y la vista derivada `_asunciones_obs` (privacidad: `detectado`
jamás sale hacia el trace).
"""
from __future__ import annotations

from src.bot.telegram_bot import _asunciones_obs, _con_prefijo_asunciones
from src.orchestrator.contracts import Asuncion
from src.orchestrator.conversation_policy import TurnResolution, PolicyRoute


def _resolucion(asunciones=(), override=None):
    return TurnResolution(
        route=PolicyRoute.STANDALONE,
        query_for_retrieval="q",
        asunciones=asunciones,
        state_query_override=override,
    )


def test_cabecera_declara_marca_y_pregunta_base():
    res = _resolucion(
        asunciones=(Asuncion(kind="marca_corregida", detectado="Kidde",
                             asumido="Kidde", modo="reescrito"),),
        override="¿Qué centrales BQide tienes?",
    )
    out = _con_prefijo_asunciones("La respuesta.", res)
    assert out.startswith(
        "ℹ️ Respondo a tu pregunta anterior («¿Qué centrales BQide tienes?»)")
    assert "la marca es Kidde" in out
    assert out.endswith("\n\nLa respuesta.")   # el contenido queda intacto al final


def test_cabecera_fuzzy_y_corregida_combinadas():
    res = _resolucion(
        asunciones=(Asuncion(kind="marca_fuzzy", detectado="morlei",
                             asumido="Morley", modo="reescrito"),
                    Asuncion(kind="marca_corregida", detectado="Morley",
                             asumido="Morley", modo="reescrito")),
        override="¿Qué centrales de KIDDE tienes?",
    )
    out = _con_prefijo_asunciones("R.", res)
    assert out.index("Entiendo que te refieres a Morley") < out.index(
        "Respondo a tu pregunta anterior") < out.index("\n\nR.")


def test_orden_del_call_site_protege_el_estado():
    """La nota se aplica DESPUÉS de las escrituras de estado/feedback: el ORDEN
    es la protección de `last_answer_excerpt`/`last_response` (s332: «la nota es
    meta-conducta, no contenido para la anáfora») — este ancla lo pinna."""
    import inspect

    from src.bot import telegram_bot

    src = inspect.getsource(telegram_bot)
    idx_prefijo = src.index("answer = _con_prefijo_asunciones(answer, f1_resolution)")
    assert src.index('context.user_data["last_response"] = answer[:500]') < idx_prefijo
    assert src.index("_aplicar_estado(context.user_data, advance_working_state(") \
        < idx_prefijo


def test_cabecera_sin_asunciones_es_identidad():
    assert _con_prefijo_asunciones("Tal cual.", _resolucion()) == "Tal cual."


def test_cabecera_ignora_kinds_ajenos():
    res = _resolucion(asunciones=(Asuncion(kind="marca_asr", detectado="BQide",
                                           asumido="Kidde", modo="reescrito"),))
    # `marca_asr` se declara en la CONFIRMACIÓN de voz (pre-turno), no aquí.
    assert _con_prefijo_asunciones("R.", res) == "R."


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
