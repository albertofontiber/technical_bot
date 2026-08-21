"""s331 M3b — precedencia de mención + gramática de confirmación (G0-f'/G0-g).

Cubre, con la composición REAL (`resolve_conversational_turn`) y flag
`F1_MENTION_PRECEDENCE=on` SIN `F1_RESOLVE_GOVERNED` (brazo C-solo, G1c):
  · corte-de-ruta (puerta 2) con SET del pending — modelos y `last_turn_at`
    INTACTOS (anti-resurrección S99), `last_query` guarda la pregunta;
  · POLARIDAD B1 (Sol-1 r-v6): «No, no es la 2X-AF1-S» JAMÁS bindea el modelo
    negado; «No, es la CAD-150» (la corrección común) SÍ bindea;
  · gramática regla 2: «sí» ⇒ familia gobernada (`pending_derived`) respondiendo
    la pregunta guardada; regla 4: cambio de tema limpia sin usar;
  · ciclo máximo 1 por construcción (CLEAR estructural en TODAS las salidas);
  · lock-step con el espejo MT-1b en AMBOS puntos de mutación (G0-f').
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.orchestrator.conversation_policy import PolicyRoute, WorkingState
from src.orchestrator.conversation_policy_impl import (
    advance_working_state,
    resolve_conversational_turn,
)

NOW = datetime(2026, 8, 20, 20, 0, 0, tzinfo=timezone.utc)


def _mirror():
    spec = importlib.util.spec_from_file_location(
        "mt_harness_m3b", Path(__file__).resolve().parent.parent
        / "scripts" / "test_multiturn_vs_gold.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _flags_c_solo(monkeypatch):
    monkeypatch.setenv("F1_MENTION_PRECEDENCE", "on")
    monkeypatch.delenv("F1_RESOLVE_GOVERNED", raising=False)   # brazo C-solo (G1c)
    monkeypatch.delenv("IDENTITY_RESOLVE", raising=False)
    yield


def _ws_in_window(**kw) -> WorkingState:
    base = dict(last_target_models=("CAD-150",),
                last_query="¿Cuántas zonas tiene la CAD-150?",
                last_turn_at=NOW - timedelta(minutes=5))
    base.update(kw)
    return WorkingState(**base)


def _ws_pending(mention="EMA1224B4RW-XQ", **kw) -> WorkingState:
    return _ws_in_window(pending_mention=mention, pending_at=NOW - timedelta(minutes=1),
                         last_query="¿Aguanta 8 sirenas la EMA1224B4RW-XQ?", **kw)


# ---------------------------------------------------------------------------
# Corte-de-ruta (puerta 2) + SET del pending
#
# NOTA DE SEMÁNTICA (medida en G0): la clase que corta ruta es «mención elegible
# con extracción VACÍA» — cuando la extracción pesca el prefijo de familia (el
# caso «2X-AF1-XQ2» → real=('2X-AF1',)), la rama A dispara ANTES con la familia,
# que ya impide el carry del producto viejo (el reconocimiento de la mención en
# ese camino es conducta de generación, M3c). El corte protege a las familias
# gobernadas SIN tag de corpus (altas recientes: EMA1224B4R/W, s324b §0.D).
# ---------------------------------------------------------------------------
def test_route_cut_clarify_y_set_del_pending():
    ws = _ws_in_window()
    res, ws2 = resolve_conversational_turn(
        "La EMA1224B4RW-XQ me da fallo de tierra.", ws, NOW)
    assert res.route is PolicyRoute.CLARIFY
    assert res.rationale == "mention_route_cut_clarify"
    assert "EMA1224B4RW-XQ" in (res.clarify_question or "")
    assert "EMA1224B4R/W" in (res.clarify_question or "")    # la familia gobernada
    assert res.turn_identity is not None and res.turn_identity.route_cut
    # SET: pending + last_query; modelos y ventana INTACTOS (S99)
    assert ws2.pending_mention == "EMA1224B4RW-XQ" and ws2.pending_at == NOW
    assert ws2.last_target_models == ws.last_target_models
    assert ws2.last_turn_at == ws.last_turn_at               # NO se refresca
    assert ws2.last_query == "La EMA1224B4RW-XQ me da fallo de tierra."


def test_prefijo_de_familia_extraible_gana_la_rama_A():
    # «2X-AF1-XQ2»: la extracción pesca la familia ⇒ A standalone con ('2X-AF1',)
    # — sin corte, sin carry del producto viejo, sin pending.
    ws = _ws_in_window()
    res, ws2 = resolve_conversational_turn(
        "La 2X-AF1-XQ2 me da fallo de tierra.", ws, NOW)
    assert res.route is PolicyRoute.STANDALONE
    assert res.rationale == "explicit_product"
    assert "2X-AF1" in (res.target_models or ())
    assert "CAD-150" not in (res.target_models or ())        # el viejo NO arrastra
    assert ws2.pending_mention is None


def test_mencion_igual_al_estado_no_corta():
    # La mención re-dice el producto del estado (normkey) ⇒ carry normal de hoy.
    ws = _ws_in_window(last_target_models=("2X-AF1",))
    res, _ = resolve_conversational_turn("¿Y la 2X-AF1 qué consumo tiene?", ws, NOW)
    assert res.route is not PolicyRoute.CLARIFY or "2X-AF1-XQ2" not in (
        res.clarify_question or "")


def test_mencion_sin_prefijo_gobernado_no_corta():
    ws = _ws_in_window()
    res, ws2 = resolve_conversational_turn("El TSR-9100 pita sin motivo.", ws, NOW)
    assert res.rationale != "mention_route_cut_clarify"
    assert ws2.pending_mention is None


# ---------------------------------------------------------------------------
# POLARIDAD B1 (Sol-1 r-v6) — la gramática con pending vivo
# ---------------------------------------------------------------------------
def test_polaridad_no_no_es_la_X_no_bindea():
    ws = _ws_pending()
    res, ws2 = resolve_conversational_turn("No, no es la 2X-AF1-S.", ws, NOW)
    assert res.route is PolicyRoute.CLARIFY
    assert res.rationale == "pending_negated_label_request"
    assert "2X-AF1-S" not in (res.target_models or ())       # JAMÁS el negado
    assert ws2.pending_mention is None                        # CLEAR (ciclo máx 1)


def test_polaridad_no_coma_es_la_Y_si_bindea():
    ws = _ws_pending()
    res, ws2 = resolve_conversational_turn("No, es la CAD-150.", ws, NOW)
    assert res.route is PolicyRoute.STANDALONE
    assert res.rationale == "explicit_product"
    assert "CAD-150" in (res.target_models or ())
    assert ws2.pending_mention is None                        # CONSUME


def test_afirmacion_procede_con_familia_pending_derived():
    ws = _ws_pending()
    res, ws2 = resolve_conversational_turn("Sí.", ws, NOW)
    assert res.route is PolicyRoute.STANDALONE
    assert res.rationale == "pending_confirmed_family"
    assert res.target_models == ("EMA1224B4R/W",)            # familia gobernada
    assert "¿Aguanta 8 sirenas" in res.query_for_retrieval   # la PREGUNTA guardada
    assert "(contexto: EMA1224B4R/W)" in res.query_for_retrieval
    ti = res.turn_identity
    assert ti is not None and ti.models_provenance == "pending_derived"
    assert ti.mention_provenance == "pending_carried"
    assert ws2.pending_mention is None
    assert ws2.last_target_models == ("EMA1224B4R/W",)


def test_cambio_de_tema_limpia_sin_usar():
    ws = _ws_pending()
    res, ws2 = resolve_conversational_turn(
        "¿Cada cuánto toca revisar los extintores?", ws, NOW)
    assert res.rationale not in ("pending_negated_label_request",
                                 "pending_confirmed_family")
    assert ws2.pending_mention is None


def test_ciclo_maximo_1_no_hay_segundo_label_request():
    # Tras la negación (pending limpiado), otro «no» YA NO re-entra en la gramática.
    ws = _ws_pending()
    res1, ws2 = resolve_conversational_turn("No, no es la 2X-AF1-S.", ws, NOW)
    assert res1.rationale == "pending_negated_label_request"
    res2, _ = resolve_conversational_turn("no", ws2, NOW + timedelta(seconds=30))
    assert res2.rationale != "pending_negated_label_request"


# ---------------------------------------------------------------------------
# Flag off = conducta de hoy byte-idéntica
# ---------------------------------------------------------------------------
def test_flag_off_sin_corte_ni_gramatica(monkeypatch):
    monkeypatch.delenv("F1_MENTION_PRECEDENCE", raising=False)
    ws = _ws_in_window()
    res, ws2 = resolve_conversational_turn(
        "La 2X-AF1-XQ2 me da fallo de tierra.", ws, NOW)
    assert res.rationale != "mention_route_cut_clarify"
    assert ws2.pending_mention is None


# ---------------------------------------------------------------------------
# Lock-step MT-1a↔MT-1b (G0-f'): AMBOS puntos de mutación
# ---------------------------------------------------------------------------
def test_lockstep_set_y_clear_espejados():
    mirror = _mirror()
    ws = _ws_in_window()
    res, _ = resolve_conversational_turn(
        "La 2X-AF1-XQ2 me da fallo de tierra.", ws, NOW)
    a = advance_working_state(ws, res, "La 2X-AF1-XQ2 me da fallo de tierra.",
                              None, NOW, None)
    b = mirror.update_working_state(ws, res, "La 2X-AF1-XQ2 me da fallo de tierra.",
                                    None, NOW, None)
    assert a == b                                            # SET espejado
    ws_p = _ws_pending()
    res2, _ = resolve_conversational_turn("Sí.", ws_p, NOW)
    a2 = advance_working_state(ws_p, res2, "Sí.", None, NOW, None)
    b2 = mirror.update_working_state(ws_p, res2, "Sí.", None, NOW, None)
    assert a2 == b2 and a2.pending_mention is None           # CONSUME espejado
    res3, _ = resolve_conversational_turn("No, no es la 2X-AF1-S.", ws_p, NOW)
    a3 = advance_working_state(ws_p, res3, "No, no es la 2X-AF1-S.", None, NOW, None)
    b3 = mirror.update_working_state(ws_p, res3, "No, no es la 2X-AF1-S.",
                                     None, NOW, None)
    assert a3 == b3 and a3.pending_mention is None           # CLEAR espejado
