# -*- coding: utf-8 -*-
"""s333 B1-B2 — la RED de la RED: clasificador LLM tras la plantilla de corrección.

Arquitectura (spec v2 §1): la plantilla cerrada de s332/s332b se queda como
FAST-PATH ($0, 0 ms) y el clasificador entra SOLO en su miss, sobre la población
acotada de v2 §2. El contrato que fijan estos casos:

  · `correccion=None` (flag `F1_CORRECCION_LLM` off, modo contrato, $0) ⇒ camino
    BYTE-IDÉNTICO a hoy (`new_brand_no_state`);
  · la rama LLM vive DENTRO del guard de `F1_MARCA_CORRECCION` (dependencia
    declarada v2 §2.1): con la determinista apagada, ni se consulta;
  · decisión `"correccion"` ⇒ la MISMA resolución servida que el rebuild
    determinista (rebuild + `Asuncion` + `state_query_override`), cambiando SOLO el
    `rationale` — atribución de MECANISMO, no de conducta;
  · `"nuevo"` / None / excepción ⇒ la cascada de hoy, sin tocar nada (fail-open con
    DIRECCIÓN);
  · las guardas de población NO pagan LLM: fast-path primero, una sola marca
    no-ambigua, sin modelos bindeados (la rama COMPAT/SWITCH shipped intacta) y sin
    código de modelo en el turno (guarda Fable-1, v2 §1);
  · el módulo del clasificador es UNA fuente (prompt + parser + constructor) con
    parser estricto, fail-open total y config atestada.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.orchestrator.conversation_policy import PolicyRoute, WorkingState
from src.orchestrator.conversation_policy_impl import resolve_conversational_turn
from src.orchestrator.correccion_llm import (
    CORRECCION_MODEL,
    PROMPT,
    construir_correccion_fn,
    parse_decision,
)

NOW = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
PREGUNTA_BASE = "¿Qué centrales BQide tienes?"
# El fraseo de la verificación DEC-099 (v1 §1.F): NO está en el léxico gobernado —
# es justo la cola que el clasificador recoge y la plantilla no.
NO_TABULADA = "que no hombre, que es Kidde"


@pytest.fixture(autouse=True)
def _flags_aislados(monkeypatch):
    """Brazo limpio: el único lever de entorno de este fichero es
    `F1_MARCA_CORRECCION` (el de la rama LLM no se lee en la política — llega
    inyectado como callable desde el transporte)."""
    for var in ("F1_MARCA_CORRECCION", "F1_MENTION_PRECEDENCE",
                "F1_RESOLVE_GOVERNED", "IDENTITY_RESOLVE"):
        monkeypatch.delenv(var, raising=False)
    yield


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("F1_MARCA_CORRECCION", "on")
    yield


def _ws(**kw) -> WorkingState:
    """Estado de la mañana-Kidde: la pregunta quedó guardada, SIN modelos (el turno
    corrupto no bindeó ninguno — es justo la clase que la red recupera)."""
    base = dict(last_query=PREGUNTA_BASE, last_turn_at=NOW - timedelta(seconds=60))
    base.update(kw)
    return WorkingState(**base)


def _explota():
    """(fn, registro) — el clasificador que NO debía invocarse. La política envuelve
    la llamada en fail-open, así que la excepción NO basta: el contador ES la
    aserción (sin él, una guarda ausente daría verde vacuo)."""
    registro = {"n": 0}

    def _boom(query, last_query, marca):
        registro["n"] += 1
        raise AssertionError("el clasificador no debía invocarse en este turno")

    return _boom, registro


# ─────────────────────────── 1 · parser ESTRICTO (contrato del enum)
def test_parse_decision_es_estricto():
    assert parse_decision("CORRECCION") == "correccion"
    assert parse_decision("NUEVO") == "nuevo"
    assert parse_decision(" correccion. ") == "correccion"      # puntuación final
    assert parse_decision("nuevo!") == "nuevo"
    for basura in ("CORRECCION porque...", "CORRIGE", "AMBOS", "", None, "NUEVO?"):
        assert parse_decision(basura) is None, basura


# ─────────────────────────── 2 · dispara donde la plantilla NO llega
def test_fraseo_no_tabulado_dispara_por_el_clasificador(flag_on):
    res, _ = resolve_conversational_turn(
        NO_TABULADA, _ws(), NOW, correccion=lambda q, lq, m: "correccion")
    assert res.route is PolicyRoute.STANDALONE
    assert res.rationale == "brand_correction_llm"
    assert PREGUNTA_BASE in res.query_for_retrieval
    assert "la marca es Kidde" in res.query_for_retrieval   # grafía del usuario
    assert res.target_models == ()
    assert res.state_query_override == PREGUNTA_BASE
    assert len(res.asunciones) == 1
    asuncion = res.asunciones[0]
    assert asuncion.kind == "marca_corregida"
    assert asuncion.modo == "reescrito"
    assert asuncion.asumido == "Kidde"


def test_lo_servido_es_identico_al_rebuild_salvo_el_rationale(flag_on):
    """La atribución de MECANISMO no puede cambiar la CONDUCTA servida (criterio
    byte de los gates): las dos vías construyen la misma resolución."""
    por_llm, _ = resolve_conversational_turn(
        "me refería a Kidde", _ws(), NOW, correccion=lambda q, lq, m: "correccion")
    por_plantilla, _ = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    assert por_plantilla.rationale == "brand_correction_rebuild"
    assert por_llm.query_for_retrieval == por_plantilla.query_for_retrieval
    assert por_llm.asunciones == por_plantilla.asunciones
    assert por_llm.state_query_override == por_plantilla.state_query_override
    assert por_llm.route is por_plantilla.route


# ─────────────────────────── 3 · "nuevo" / None ⇒ cascada de hoy
@pytest.mark.parametrize("decision", ["nuevo", None])
def test_nuevo_y_none_siguen_la_cascada(flag_on, decision):
    res, _ = resolve_conversational_turn(
        NO_TABULADA, _ws(), NOW, correccion=lambda q, lq, m: decision)
    assert res.rationale == "new_brand_no_state"
    assert res.query_for_retrieval == NO_TABULADA
    assert res.asunciones == ()
    assert res.state_query_override is None


def test_excepcion_del_clasificador_es_failopen(flag_on):
    def _revienta(query, last_query, marca):
        raise RuntimeError("red caída")

    res, _ = resolve_conversational_turn(
        NO_TABULADA, _ws(), NOW, correccion=_revienta)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


# ─────────────────────────── 4 · flag OFF (sin fn) = conducta de HOY
def test_sin_clasificador_es_byte_identico(flag_on):
    res, _ = resolve_conversational_turn(NO_TABULADA, _ws(), NOW, correccion=None)
    assert res.rationale == "new_brand_no_state"
    assert res.query_for_retrieval == NO_TABULADA
    assert res.asunciones == ()
    assert res.state_query_override is None


def test_la_rama_llm_vive_dentro_del_guard_determinista():
    """Dependencia DECLARADA (v2 §2.1): con `F1_MARCA_CORRECCION` off, apagar la
    plantilla apaga TAMBIÉN la red — sin interlock extra y sin pagar LLM."""
    fn, registro = _explota()
    res, _ = resolve_conversational_turn(NO_TABULADA, _ws(), NOW, correccion=fn)
    assert registro["n"] == 0
    assert res.rationale == "new_brand_no_state"


# ─────────────────────────── 5 · fast-path primero: la plantilla no paga LLM
def test_plantilla_que_casa_no_consulta_al_clasificador(flag_on):
    fn, registro = _explota()
    res, _ = resolve_conversational_turn("me refería a Kidde", _ws(), NOW,
                                         correccion=fn)
    assert res.rationale == "brand_correction_rebuild"
    assert registro["n"] == 0, "pagó LLM en un turno que el fast-path ya cubría"


# ─────────────────────────── 6 · guarda Fable-1: marca + código NO resuelto
def test_guarda_de_model_token_conserva_la_conducta_de_hoy(flag_on):
    """v2 §1: «no, era la Kidde XY-9999» (código destrozado, sin resolver) sigue en
    `new_brand_switch_model_token` — reescribirlo como corrección PERDERÍA el código
    que el usuario acaba de dar."""
    fn, registro = _explota()
    res, _ = resolve_conversational_turn("no, era la Kidde XY-9999", _ws(), NOW,
                                         correccion=fn)
    assert res.rationale == "new_brand_switch_model_token"
    assert registro["n"] == 0


def test_codigo_que_SI_resuelve_lo_gana_la_rama_a(flag_on):
    """Desviación VERIFICADA de la spec (que citaba «2X-AF9999» como caso de la
    guarda): el detector sí liga un prefijo de ese código (`2X-A`), así que la rama
    A —producto explícito— retorna ANTES y la de corrección ni se evalúa. La clase
    de la guarda es la del test anterior; esta se pinea para que la precedencia
    quede declarada y no se lea como el mismo mecanismo."""
    fn, registro = _explota()
    res, _ = resolve_conversational_turn("no, era la Kidde 2X-AF9999", _ws(), NOW,
                                         correccion=fn)
    assert res.rationale == "explicit_product"
    assert res.target_models == ("2X-A",)
    assert registro["n"] == 0


# ─────────────────────────── 7 · guarda multi-marca (sin rebuild unívoco)
def test_dos_marcas_no_consultan_al_clasificador(flag_on):
    fn, registro = _explota()
    res, _ = resolve_conversational_turn("dije Kidde o Notifier", _ws(), NOW,
                                         correccion=fn)
    assert registro["n"] == 0
    assert res.rationale == "new_brand_no_state"


# ─────────────────────────── 8 · guarda in-window: COMPAT/SWITCH intacta
def test_con_modelos_bindeados_no_consulta_al_clasificador(flag_on):
    """v2 §2.5: con producto en curso manda la rama in-window (el lever INTENT_LLM
    shipped) — cero interferencia y cero doble llamada en el mismo turno."""
    fn, registro = _explota()
    ws = _ws(last_target_models=("CAD-150",))
    res, _ = resolve_conversational_turn(NO_TABULADA, ws, NOW, correccion=fn)
    assert registro["n"] == 0
    assert res.route is PolicyRoute.CARRY_FORWARD
    assert "brand_compatibility_in_window" in res.rationale


# ─────────────────────────── 9 · minimización: qué viaja EXACTAMENTE
def test_el_clasificador_recibe_query_last_query_y_token_de_marca(flag_on):
    """v2 §3: viaja SOLO lo que el prompt usa — la query, la pregunta anterior y el
    token GOBERNADO de la marca (nunca el WorkingState entero, nunca el excerpt de
    la respuesta previa)."""
    visto: dict = {}

    def _graba(query, last_query, marca):
        visto.update(query=query, last_query=last_query, marca=marca)
        return "nuevo"

    resolve_conversational_turn(NO_TABULADA, _ws(), NOW, correccion=_graba)
    assert visto == {"query": NO_TABULADA, "last_query": PREGUNTA_BASE,
                     "marca": "kidde"}


# ─────────────────────────── 10 · el constructor: config atestada y fail-open
class _ClienteFake:
    """Cliente anthropic de mentira: registra su construcción y devuelve (o revienta
    con) lo que el test declare."""

    construcciones: list = []
    respuesta = None
    revienta = False
    ultimo_payload: dict = {}

    def __init__(self, **kwargs):
        type(self).construcciones.append(kwargs)
        self.messages = self

    def create(self, **kwargs):
        type(self).ultimo_payload = kwargs
        if type(self).revienta:
            raise RuntimeError("red caída")
        return type(self).respuesta


@pytest.fixture
def cliente_fake(monkeypatch):
    import anthropic

    _ClienteFake.construcciones = []
    _ClienteFake.respuesta = None
    _ClienteFake.revienta = False
    _ClienteFake.ultimo_payload = {}
    monkeypatch.setattr(anthropic, "Anthropic", _ClienteFake)
    return _ClienteFake


def test_config_atestada_coincide_con_el_cliente_construido(cliente_fake):
    """La atestación no es decorativa: es lo que el e2e del flip lee para probar que
    el fn servido lleva la config de producción (timeout 6 s, max_retries=0)."""
    fn = construir_correccion_fn("sk-falsa")
    assert fn.config == {"model": CORRECCION_MODEL, "timeout_s": 6.0,
                         "max_retries": 0}
    assert CORRECCION_MODEL == "claude-sonnet-4-6"
    assert len(cliente_fake.construcciones) == 1
    construccion = cliente_fake.construcciones[0]
    assert construccion["timeout"] == 6.0
    assert construccion["max_retries"] == 0        # el default (2) haría 6 s ≈ 19 s
    assert fn.ultima is None                       # aún no juzgó nada


def test_fallo_del_cliente_es_failopen_total_y_deja_ultima(cliente_fake):
    cliente_fake.revienta = True
    fn = construir_correccion_fn("sk-falsa")
    assert fn("que es Kidde", PREGUNTA_BASE, "kidde") is None
    assert fn.ultima["decision"] is None
    assert isinstance(fn.ultima["ms"], int) and fn.ultima["ms"] >= 0


def test_camino_feliz_manda_los_tres_campos_del_prompt(cliente_fake):
    """Un placeholder sin rellenar reventaría el `.format` y el fail-open lo
    tragaría EN SILENCIO (siempre None): el payload se inspecciona."""
    cliente_fake.respuesta = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="CORRECCION")])
    fn = construir_correccion_fn("sk-falsa")
    assert fn(NO_TABULADA, PREGUNTA_BASE, "kidde") == "correccion"
    payload = cliente_fake.ultimo_payload
    assert payload["model"] == CORRECCION_MODEL
    assert payload["temperature"] == 0 and payload["max_tokens"] == 4
    contenido = payload["messages"][0]["content"]
    assert NO_TABULADA in contenido and PREGUNTA_BASE in contenido
    assert "«kidde»" in contenido
    assert "{" not in contenido                    # sin placeholders sin rellenar
    assert fn.ultima["decision"] == "correccion"


def test_el_prompt_declara_las_tres_variables_y_la_salida():
    assert "{last_query}" in PROMPT and "{q}" in PROMPT and "{marca}" in PROMPT
    assert PROMPT.rstrip().endswith("Responde EXACTAMENTE una palabra: "
                                    "CORRECCION o NUEVO.")
