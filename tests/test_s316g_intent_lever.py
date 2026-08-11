# -*- coding: utf-8 -*-
"""s316g — Lever INTENT_LLM (DEC-203): contratos del seam, la exención y el vocabulario.

Lo que fija:
  · OFF byte-idéntico: `intent=None` produce EXACTAMENTE la resolución de hoy;
  · las cuatro salidas del clasificador (compat / switch / basura / excepción);
  · la exención de misma-marca por palabra PRIMARIA — con un fabricante MULTI-PALABRA
    (el hallazgo verificado de Fable r10: `classify` devuelve «Argus Security» y el
    token es «argus»; 8/26 fabricantes son multi-palabra);
  · `_MARCAS_AMBIGUAS` no dispara el juicio (la clase FUEGO);
  · el parser del transporte (contrato {compat,switch,None});
  · la guarda de colisión de BRAND_TOKENS con el vocabulario del dominio — el espejo
    para la política del test que la guardia de transporte ya tenía.
"""

import os
from datetime import datetime, timezone

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator.conversation_policy import WorkingState
from src.orchestrator.conversation_policy_impl import (
    BRAND_TOKENS,
    DeterministicConversationPolicy,
)

_NOW = datetime.now(timezone.utc)


def _resolver(query, ws, intent=None):
    return DeterministicConversationPolicy().resolve(
        query=query, turn_models=[], available_models=None,
        working_state=ws, now=_NOW, rewrite=None, intent=intent)


def _ws(*modelos):
    return WorkingState(last_target_models=tuple(modelos), last_query="x",
                        last_turn_at=_NOW)


def test_off_es_byte_identico_a_hoy():
    r = _resolver("¿y en Morley cómo se hace el reset?", _ws("NC-PF2"))
    assert r.route.value == "carry_forward"
    assert "brand_compatibility_in_window" in r.rationale


@pytest.mark.parametrize("veredicto,ruta,rationale", [
    ("compat", "carry_forward", "brand_compat_confirmed_llm"),
    ("switch", "standalone", "new_brand_topic_switch_llm"),
    ("GARBAGE", "carry_forward", "brand_compat_failopen_llm"),
])
def test_salidas_del_clasificador(veredicto, ruta, rationale):
    r = _resolver("¿y en Morley qué tal?", _ws("NC-PF2"), intent=lambda q, w: veredicto)
    assert r.route.value == ruta and rationale in r.rationale
    if veredicto == "switch":
        assert r.target_models == ()


def test_excepcion_del_clasificador_es_failopen():
    def boom(q, w):
        raise RuntimeError("red caída")

    r = _resolver("¿y en Morley qué tal?", _ws("NC-PF2"), intent=boom)
    assert r.route.value == "carry_forward"
    assert "brand_compat_failopen_llm" in r.rationale


def test_exencion_misma_marca_multipalabra_no_paga_llm(monkeypatch):
    """Estado cuyo modelo clasifica a «Argus Security» + token «argus» en la consulta:
    la comparación por palabra PRIMARIA exime SIN llamar al LLM. (La comparación
    directa nombre-completo == token fallaba: Fable r10, verificado.)"""
    import src.rag.retriever as retriever

    monkeypatch.setattr(retriever, "classify_model_manufacturer",
                        lambda m: "Argus Security" if m == "VEGA-X" else None)
    llamadas = {"n": 0}

    def espia(q, w):
        llamadas["n"] += 1
        return "switch"

    r = _resolver("¿y argus tiene más sirenas?", _ws("VEGA-X"), intent=espia)
    assert llamadas["n"] == 0, "pagó LLM en una pregunta de la MISMA marca"
    assert r.route.value == "carry_forward"
    assert "brand_compatibility_in_window" in r.rationale


def test_estado_sin_marca_resoluble_no_juzga(monkeypatch):
    import src.rag.retriever as retriever

    monkeypatch.setattr(retriever, "classify_model_manufacturer", lambda m: None)
    llamadas = {"n": 0}

    def espia(q, w):
        llamadas["n"] += 1
        return "switch"

    r = _resolver("¿y en Morley qué tal?", _ws("MODELO-RARO"), intent=espia)
    assert llamadas["n"] == 0                 # sin base de comparación: no se juzga
    assert r.route.value == "carry_forward"   # conducta de hoy (fail-open declarado)


def test_parser_del_transporte_es_estricto():
    from src.orchestrator.intent_llm import parse_decision

    assert parse_decision("COMPAT") == "compat"
    assert parse_decision("switch.") == "switch"
    assert parse_decision(" SWITCH! ") == "switch"
    for basura in ("COMPATIBLE", "COMPAT porque...", "", None, "AMBOS"):
        assert parse_decision(basura) is None


def test_brand_tokens_no_colisiona_con_el_dominio():
    """El espejo para la política del test de colisión de la guardia (s316b): si una
    config futura mete una marca llamada «fuego»/«alarma»/«central» en BRAND_TOKENS,
    la rama B pagaría LLM en follow-ups normales y un switch erróneo borraría estado.
    CI rompe y obliga a declararla conscientemente."""
    from src.orchestrator.turn_plan import _MARCAS_AMBIGUAS, _VOCABULARIO_DOMINIO

    colisiones = {b for b in BRAND_TOKENS
                  if b in _VOCABULARIO_DOMINIO and b not in _MARCAS_AMBIGUAS}
    assert not colisiones, (
        f"BRAND_TOKENS contiene vocabulario del dominio sin declarar: {colisiones} — "
        "añádelas a _MARCAS_AMBIGUAS (turn_plan) con su porqué, o renombra el token")


def test_flag_off_no_construye_cliente(monkeypatch):
    """Sin INTENT_LLM en el entorno, _process_query no debe ni importar el módulo del
    clasificador (patrón perezoso del rewriter): el flag OFF es $0 y byte-inerte."""
    monkeypatch.delenv("INTENT_LLM", raising=False)
    import src.bot.telegram_bot as bot
    import inspect

    fuente = inspect.getsource(bot._process_query)
    assert 'os.getenv("INTENT_LLM"' in fuente          # el gate del flag existe
    assert "construir_intent_fn" in fuente             # y la construcción es local/lazy


# --- ronda 11 (Sol C1 + Fable M1): paridad gate<->serving y el guion ----------
def test_marca_mixta_llega_al_clasificador():
    """El caso congelado «los Detnov fallan, dime el de Morley» (SWITCH en el gate)
    DEBE llegar al LLM en serving: con any() quedaba exento por la marca propia y el
    gate medía un camino que el serving se saltaba (Sol r11, verificado)."""
    llamadas = {"n": 0}

    def espia(q, w):
        llamadas["n"] += 1
        return "switch"

    r = _resolver("los Detnov me dan problemas, mejor dime cómo va el de Morley",
                  _ws("CAD-250"), intent=espia)
    assert llamadas["n"] == 1 and r.route.value == "standalone"
    assert "new_brand_topic_switch_llm" in r.rationale


def test_pepperl_fuchs_exime_pese_al_guion(monkeypatch):
    """(Fable r11, probado) El único fabricante con GUION: split()[0] daba
    'pepperl-fuchs' vs token 'pepperl' y NO eximía — un switch erróneo borraba
    estado de la MISMA marca. La tokenización es ahora la de _config_brand_tokens."""
    import src.rag.retriever as retriever

    monkeypatch.setattr(retriever, "classify_model_manufacturer",
                        lambda m: "Pepperl-Fuchs")
    llamadas = {"n": 0}

    def espia(q, w):
        llamadas["n"] += 1
        return "switch"

    r = _resolver("¿y pepperl tiene más barreras?", _ws("Z728"), intent=espia)
    assert llamadas["n"] == 0, "pagó LLM en la misma marca (guion)"
    assert r.route.value == "carry_forward"
