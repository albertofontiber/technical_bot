# -*- coding: utf-8 -*-
"""s324e — Conducta (a) ante marca↔producto errónea: CORREGIR Y RESPONDER.

DEC-224 §B (Alberto: el bot corrige y responde en el mismo turno) con el alcance
adjudicado en DEC-226: **solo si hay UNA marca y UN modelo** que no casan. Con
varios modelos o varias marcas el bot responde COMO HOY, sin emparejar — corregir
mal es peor que no corregir; la opción (b) (emparejar por proximidad) queda anotada
como mejora futura y NO se implementa.

Qué fija este fichero, por piezas:
  · `TurnPlan.preambulo` — campo TIPADO del plan (no un `fallback_ruta` genérico) y
    el gate de alcance (a) con el lever `MISMATCH_ANSWER` entrando por `Meta`;
  · `runtime_trace.mismatch_corrected` — sección acotada del trace + su validador;
  · F1 `resolve_conversational_turn(..., resolved_model=)` — el modelo servido es el
    que resolvió el plan, no el que F1 re-detecta (crítico de Sol sobre la v2);
  · **byte-equivalencia con el flag OFF**: mismo plan y mismo trace que antes de
    s324e, en toda la cascada.

El test de INTEGRACIÓN (`test_integracion_*`) compone las cuatro piezas en el mismo
orden en que lo hará el transporte, con adapters CONGELADOS: es la especificación
ejecutable del diff pendiente de `telegram_bot._process_query` (que esta sesión NO
aplica — el fichero está ocupado por otro agente).
"""

import json
import os
from datetime import datetime, timezone

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.flags import mismatch_answer_activo
from src.orchestrator import replay_adapters, run_turn
from src.orchestrator.conversation_policy import WorkingState
from src.orchestrator.conversation_policy_impl import resolve_conversational_turn
from src.orchestrator.telegram_adapter import build_turn_request
from src.orchestrator.turn_plan import (
    Hecho,
    Meta,
    Preambulo,
    TurnPlan,
    marcas_mencionadas,
    plan_turn,
    plan_turn_hechos,
    preambulo_mismatch,
    texto_preambulo,
)
from src.rag.runtime_trace import (
    build_rag_serving_trace,
    validate_rag_serving_trace,
)

# --- mundo congelado (mismos dobles que la suite de equivalencia s316e) --------
_MARCA_DE_MODELO = {"ASD535": "Securiton", "ADW535": "Securiton",
                    "CAD-250": "Detnov"}
_SERVIDAS = {"detnov", "morley", "notifier", "securiton"}
_MARCAS_DB = ["Detnov", "Morley", "Notifier", "Securiton"]

_MISMATCH = "¿cuál es la sensibilidad del ASD535 de Detnov?"


@pytest.fixture
def det(monkeypatch):
    """Detector de modelos congelado: el plan lo consume vía `_retriever`."""
    import src.rag.retriever as retriever

    def _det(q):
        return [m for m in ("ASD535", "ADW535", "CAD-250") if m in q]

    monkeypatch.setattr(retriever, "extract_product_models", _det)
    return _det


def _hechos(texto, meta=Meta(), estado=()):
    """Shell MECÁNICO de los hechos, calcado de `telegram_bot._resolver_hechos`:
    resuelve EXACTAMENTE lo que el plan declara, sin mirar el texto."""
    out = {}
    for h in plan_turn_hechos(texto, estado, meta):
        if h.tipo == "marca_de_modelo":
            out[h] = _MARCA_DE_MODELO.get(h.arg.upper())
        elif h.tipo == "marca_servida":
            out[h] = h.arg.lower() in _SERVIDAS
        elif h.tipo == "lexico_marcas":
            out[h] = list(_MARCAS_DB)
    return out


def _plan(texto, *, lever=False, estado=()):
    meta = Meta(mismatch_answer=lever)
    return plan_turn(texto, estado, meta, _hechos(texto, meta, estado))


# --- el preámbulo como DATO ---------------------------------------------------


def test_preambulo_rechaza_texto_libre_y_tipos_desconocidos():
    """Espejo de `Hecho`: los campos son TOKENS, no texto. Es la frontera que
    impide que la consulta del técnico acabe en el trace persistido."""
    with pytest.raises(ValueError):
        Preambulo(tipo="lo_que_sea", modelo="ASD535", marca_real="Securiton",
                  marca_mencionada="Detnov")
    for malo in ("Securiton\ny algo más", "S" * 41,
                 "Securiton AG división de incendios", "¿de quién es?",
                 "Securiton ", " Securiton", "System  Sensor"):
        with pytest.raises(ValueError):
            Preambulo(tipo="mismatch_corrected", modelo="ASD535",
                      marca_real=malo, marca_mencionada="Detnov")


def test_preambulo_mismatch_es_fail_closed_no_revienta_el_turno():
    """`marca_real` viene de la DB y NO está acotada por ningún regex. Un nombre
    imposible degrada a None (⇒ la ruta `mismatch` de hoy), jamás a una excepción
    en el camino servido."""
    assert preambulo_mismatch("ASD535", "Securiton", "Detnov") is not None
    assert preambulo_mismatch("ASD535", "S" * 60, "Detnov") is None
    assert preambulo_mismatch("ASD535", "Securiton\nAG", "Detnov") is None


def test_texto_del_preambulo_es_el_que_lee_el_tecnico():
    """PIN del texto servido. Sobrio, sin regañar, corrige el dato y sigue; texto
    PLANO (sin marcado) porque se antepone a una respuesta que se renderiza como
    HTML y que puede caer al transporte plano."""
    p = Preambulo(tipo="mismatch_corrected", modelo="ASD535",
                  marca_real="Securiton", marca_mencionada="Detnov")
    assert texto_preambulo(p) == (
        "El ASD535 es de Securiton, no de Detnov. "
        "Sobre el ASD535 de Securiton:"
    )
    assert "*" not in texto_preambulo(p) and "_" not in texto_preambulo(p)


def test_marcas_mencionadas_cuenta_marcas_distintas():
    assert marcas_mencionadas("el ASD535 de Detnov") == {"detnov"}
    assert marcas_mencionadas("Detnov y detnov") == {"detnov"}
    assert marcas_mencionadas("¿Detnov o Kidde?") == {"detnov", "kidde"}
    assert marcas_mencionadas("sin marcas aquí") == set()


# --- el gate de alcance (a) en el PLAN ---------------------------------------


def test_lever_off_el_plan_es_el_de_hoy_byte_a_byte(det):
    """OFF (default) ⇒ ruta `mismatch` con sus datos y su log de atajo: el plan
    ENTERO idéntico al de antes de s324e."""
    plan = _plan(_MISMATCH)
    assert plan == TurnPlan(
        ruta="mismatch", log_consulta=True,
        datos={"modelo": "ASD535", "marca_real": "Securiton",
               "marca_mencionada": "Detnov"},
    )
    assert plan.preambulo is None


def test_una_marca_un_modelo_corrige_y_responde(det):
    """El caso de los 👎 reales: marca equivocada, aparato correcto ⇒ preámbulo +
    ruta conversacional (RAG). Sin `log_consulta`: la fila la escribe la ruta RAG
    (UNA fila con la respuesta compuesta), no un atajo."""
    plan = _plan(_MISMATCH, lever=True)
    assert plan.ruta == "conversacional"
    assert plan.typing is True
    assert plan.log_consulta is False
    assert plan.preambulo == Preambulo(
        tipo="mismatch_corrected", modelo="ASD535",
        marca_real="Securiton", marca_mencionada="Detnov")


def test_marca_correcta_no_lleva_preambulo(det):
    """Control limpio: la marca casa ⇒ la cascada sigue como siempre."""
    plan = _plan("¿cuál es la sensibilidad del ASD535 de Securiton?", lever=True)
    assert plan.ruta == "conversacional"
    assert plan.preambulo is None


def test_multi_modelo_no_se_corrige_es_la_decision_a(det):
    """DEC-226 (a): con más de un modelo NO se empareja — se responde como hoy."""
    texto = "¿el ASD535 y el ADW535 de Detnov son compatibles?"
    plan = _plan(texto, lever=True)
    assert plan.preambulo is None
    assert plan.ruta == "mismatch"
    assert plan == _plan(texto)          # idéntico al plan con el lever apagado


def test_multi_marca_no_se_corrige(det):
    """La otra mitad del alcance (a): dos marcas ⇒ ningún emparejamiento."""
    texto = "¿el ASD535 es de Detnov o de Kidde?"
    plan = _plan(texto, lever=True)
    assert plan.preambulo is None
    assert plan.ruta == "mismatch"


def test_marca_real_no_tokenizable_degrada_a_la_conducta_de_hoy(det, monkeypatch):
    """Fail-closed del LEVER, no del turno: si el nombre de la DB no valida como
    token, se sirve la ruta `mismatch` de siempre en vez de reventar."""
    monkeypatch.setitem(_MARCA_DE_MODELO, "ASD535", "Securiton " + "X" * 60)
    plan = _plan(_MISMATCH, lever=True)
    assert plan.ruta == "mismatch"
    assert plan.preambulo is None


_CENSO_RUTAS = [
    "hola",
    "gracias",
    "adiós",
    "¿qué productos tienes?",
    _MISMATCH,
    "¿cómo se conecta el detector de Kidde?",
    "dame el listado de productos de Detnov",
    "eso no es correcto, el manual dice otra cosa",
    "¿cuál es la tensión del lazo?",
    "¿cuál es la sensibilidad del CAD-250 de Detnov?",
]


@pytest.mark.parametrize("texto", _CENSO_RUTAS)
def test_byte_equivalencia_con_el_lever_apagado(texto, det):
    """El contrato del cableado: con OFF, `plan_turn` devuelve para TODA la cascada
    exactamente lo que devolvía antes de existir el campo — el default de `Meta` y
    el False explícito son el mismo plan, y ninguno lleva preámbulo."""
    meta_defecto = Meta()
    meta_off = Meta(mismatch_answer=False)
    hechos = _hechos(texto, meta_defecto)
    plan_defecto = plan_turn(texto, (), meta_defecto, hechos)
    plan_off = plan_turn(texto, (), meta_off, hechos)
    assert plan_defecto == plan_off
    assert plan_defecto.preambulo is None
    assert plan_turn_hechos(texto, (), meta_defecto) == \
        plan_turn_hechos(texto, (), meta_off)


# --- el lever ----------------------------------------------------------------


def test_flag_mismatch_answer_default_off_y_parser_estricto(monkeypatch):
    monkeypatch.delenv("MISMATCH_ANSWER", raising=False)
    assert mismatch_answer_activo() is False
    monkeypatch.setenv("MISMATCH_ANSWER", "on")
    assert mismatch_answer_activo() is True
    monkeypatch.setenv("MISMATCH_ANSWER", "OFF")
    assert mismatch_answer_activo() is False
    monkeypatch.setenv("MISMATCH_ANSWER", "true")
    with pytest.raises(RuntimeError):
        mismatch_answer_activo()


# --- la sección del trace -----------------------------------------------------


def _trace(**overrides):
    base = dict(
        coverage_trace={},
        served_chunks=[],
        must_preserve_trace=None,
        must_preserve_outcome=None,
        release_policy={"profile": "legacy"},
        transport_parts=1,
    )
    base.update(overrides)
    return build_rag_serving_trace(**base)


_CLAVES_HISTORICAS = {"schema", "release_profile", "coverage", "must_preserve",
                      "retrieval", "timings", "intent", "transport"}


def test_trace_sin_correccion_es_byte_identico_al_de_antes():
    """La sección es OPCIONAL a propósito: sin corrección (lever OFF incluido) el
    trace no gana ni una clave — la byte-equivalencia también aquí."""
    for obs in (None, {}, {"modelo": "ASD535"}):
        trace = _trace(mismatch_obs=obs)
        assert set(trace) == _CLAVES_HISTORICAS, obs
        assert "mismatch" not in json.dumps(trace)
        assert validate_rag_serving_trace(trace) == trace


def test_trace_registra_la_correccion_con_tokens_acotados():
    trace = _trace(mismatch_obs={"modelo": "ASD535", "marca_real": "Securiton",
                                 "marca_mencionada": "Detnov"})
    assert trace["mismatch_corrected"] == {
        "modelo": "ASD535", "marca_real": "Securiton",
        "marca_mencionada": "Detnov",
    }
    assert validate_rag_serving_trace(trace) == trace


def test_trace_jamas_cruza_texto_libre_del_tecnico():
    """El vector real: colar la consulta como si fuera un token. La sección entera
    desaparece — no degrada a placeholder ni descarta el trace completo."""
    privado = "¿cuál es la sensibilidad del ASD535? mi teléfono es 600123456"
    for roto in (
        {"modelo": privado, "marca_real": "Securiton", "marca_mencionada": "Detnov"},
        {"modelo": "ASD535", "marca_real": "S" * 60, "marca_mencionada": "Detnov"},
        {"modelo": "ASD535", "marca_real": "Secu\nriton", "marca_mencionada": "D"},
        {"modelo": "ASD535", "marca_real": "Securiton"},          # a medias
        {"modelo": "ASD535", "marca_real": "Securiton", "marca_mencionada": 7},
        # espaciado sin normalizar: el mismo fabricante con dos formas haría
        # mentir al recuento de correcciones por marca
        {"modelo": "ASD535", "marca_real": "System  Sensor",
         "marca_mencionada": "Detnov"},
    ):
        trace = _trace(mismatch_obs=roto)
        assert "mismatch_corrected" not in trace, roto
        assert privado not in json.dumps(trace)
        assert validate_rag_serving_trace(trace) == trace


def test_validador_del_sink_cierra_la_seccion():
    """Defensa en profundidad: un caller que se salte el builder no puede persistir
    una sección nula, a medias, con clave extra ni con texto libre."""
    trace = _trace(mismatch_obs={"modelo": "ASD535", "marca_real": "Securiton",
                                 "marca_mencionada": "Detnov"})
    for roto in (
        None,
        {},
        {"modelo": "ASD535", "marca_real": "Securiton"},
        {"modelo": "ASD535", "marca_real": "Securiton",
         "marca_mencionada": "Detnov", "query": "PRIVADO"},
        {"modelo": "ASD535", "marca_real": "Securiton",
         "marca_mencionada": "texto libre del técnico ¿vale?"},
    ):
        mutado = dict(trace)
        mutado["mismatch_corrected"] = roto
        assert validate_rag_serving_trace(mutado) is None, roto


# --- F1: el modelo servido es el que resolvió el plan -------------------------


def test_f1_usa_el_modelo_resuelto_en_vez_de_re_detectar(monkeypatch):
    """El crítico de Sol sobre la v2: F1 re-resolvía DESPUÉS del override y el
    trabajo del plan se perdía. Con `resolved_model` el detector ni se llama."""
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    import src.orchestrator.conversation_policy_impl as impl

    llamadas = []

    def _detector_espia(query):
        llamadas.append(query)
        return ["OTRO-999"], None

    monkeypatch.setattr(impl, "detect_turn_signals", _detector_espia)
    ahora = datetime.now(timezone.utc)

    resolucion, _ = resolve_conversational_turn(
        _MISMATCH, WorkingState(), ahora, resolved_model="ASD535")
    assert resolucion.target_models == ("ASD535",)
    assert resolucion.available_models is None
    assert llamadas == []

    # sin el parámetro, la conducta de hoy: re-detecta (y sirve lo que detecte)
    resolucion_hoy, _ = resolve_conversational_turn(
        _MISMATCH, WorkingState(), ahora)
    assert resolucion_hoy.target_models == ("OTRO-999",)
    assert llamadas == [_MISMATCH]


# --- integración con adapters congelados: el turno completo -------------------


def _turno_servido(texto, *, lever, det_fixture):
    """Compone las cuatro piezas EN EL MISMO ORDEN que hará el transporte:
    plan → (preámbulo + modelo resuelto) → F1 → orquestador con adapters
    congelados → trace. Devuelve (plan, respuesta compuesta, trace, turn)."""
    plan = _plan(texto, lever=lever)
    if plan.ruta != "conversacional":
        return plan, None, None, None
    pre = plan.preambulo
    resolucion, _ = resolve_conversational_turn(
        texto, WorkingState(), datetime.now(timezone.utc),
        resolved_model=(pre.modelo if pre else None))
    request = build_turn_request(
        source="text",
        query=resolucion.query_for_retrieval,
        query_for_retrieval=resolucion.query_for_retrieval,
        target_models=resolucion.target_models,
        available_models=resolucion.available_models,
        update_id=1, chat_id=2,
    )
    turn = run_turn(request, replay_adapters(
        retrieved=[{"id": "c1", "content": "Sensibilidad 0,05 %/m.",
                    "similarity": 0.9, "product_model": "ASD535"}],
        generate=lambda q, chunks, **k: {
            "answer": "La sensibilidad es 0,05 %/m.", "diagrams": []},
    ))
    respuesta = turn.answer
    if pre is not None:
        respuesta = f"{texto_preambulo(pre)}\n\n{respuesta}"
    trace = _trace(mismatch_obs=(
        {"modelo": pre.modelo, "marca_real": pre.marca_real,
         "marca_mencionada": pre.marca_mencionada} if pre else None))
    return plan, respuesta, trace, turn


def test_integracion_corrige_responde_y_sirve_el_modelo_resuelto(det):
    """Marca errónea + un solo modelo, lever ON: el técnico ve UNA respuesta que
    empieza corrigiendo; el modelo que llega a retrieval es el resuelto; y la fila
    de `query_logs` lleva la sección del trace (ruta `rag`, sin ruta nueva)."""
    plan, respuesta, trace, turn = _turno_servido(_MISMATCH, lever=True,
                                                  det_fixture=det)
    assert plan.preambulo is not None
    assert respuesta == (
        "El ASD535 es de Securiton, no de Detnov. Sobre el ASD535 de Securiton:"
        "\n\nLa sensibilidad es 0,05 %/m."
    )
    assert turn.plan.target_models == ("ASD535",)
    assert trace["mismatch_corrected"]["marca_real"] == "Securiton"
    assert validate_rag_serving_trace(trace) == trace


def test_integracion_marca_correcta_sirve_igual_sin_preambulo(det):
    plan, respuesta, trace, turn = _turno_servido(
        "¿cuál es la sensibilidad del ASD535 de Securiton?", lever=True,
        det_fixture=det)
    assert plan.preambulo is None
    assert respuesta == "La sensibilidad es 0,05 %/m."
    assert turn.plan.target_models == ("ASD535",)
    assert "mismatch_corrected" not in trace


def test_integracion_multi_modelo_responde_como_hoy(det):
    """Decisión (a): con dos modelos no se empareja — el turno ni siquiera llega a
    la ruta conversacional, se sirve el `mismatch` de siempre."""
    plan, respuesta, trace, _ = _turno_servido(
        "¿el ASD535 y el ADW535 de Detnov son compatibles?", lever=True,
        det_fixture=det)
    assert plan.ruta == "mismatch" and plan.preambulo is None
    assert respuesta is None and trace is None


def test_integracion_lever_off_es_la_conducta_de_hoy(det):
    plan, respuesta, trace, _ = _turno_servido(_MISMATCH, lever=False,
                                               det_fixture=det)
    assert plan.ruta == "mismatch" and plan.preambulo is None
    assert respuesta is None and trace is None
