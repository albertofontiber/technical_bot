"""s331 Fase-1 — observabilidad (B5 sección tri-estado · B9 direct/1 acoplado) y
refresher de presencia single-flight.

La sección `turn_identity` es REQUERIDA con tri-estado (patrón `intent`, Sol-5
r-v6: opcional confundiría «flag off» con «on sin evento»); la vista es DERIVADA
— jamás el string de la mención (Sol-2 r-v5). El shape `direct_route_trace_v1`
solo valida en filas clarify/decline y el RAG solo en filas rag (B9: un builder
RAG no puede esquivar `exact_keys` emitiendo direct/1).
"""
from __future__ import annotations

import pytest

from src.orchestrator.conversation_policy import TurnIdentity
from src.rag import catalog_resolver as CR
from src.rag.runtime_trace import (
    DIRECT_TRACE_SCHEMA,
    _turn_identity_section,
    build_direct_route_trace,
    build_rag_serving_trace,
    validate_rag_serving_trace,
)


def _trace(**kw):
    base = dict(coverage_trace=None, served_chunks=[], must_preserve_trace=None,
                must_preserve_outcome=None, release_policy={}, transport_parts=1)
    base.update(kw)
    return build_rag_serving_trace(**base)


# ---------------------------------------------------------------------------
# Sección tri-estado (B5)
# ---------------------------------------------------------------------------
def test_seccion_not_wired_por_defecto():
    s = _turn_identity_section(None)
    assert s == {"status": "not_wired", "models_provenance": "none",
                 "mention_provenance": "none", "mention_detected": False,
                 "route_cut": False, "presence": "none"}


def test_seccion_off_neutraliza_campos():
    s = _turn_identity_section({"status": "off", "route_cut": True,
                                "mention_provenance": "this_turn"})
    assert s["status"] == "off" and not s["route_cut"]
    assert s["mention_provenance"] == "none"


def test_seccion_on_deriva_y_cierra_coherencia():
    s = _turn_identity_section({"status": "on", "models_provenance": "carried",
                                "mention_provenance": "this_turn",
                                "route_cut": True, "presence": "vigente"})
    assert s["mention_detected"] is True and s["route_cut"] is True
    # route_cut sin mención de ESTE turno se fuerza a False (invariante):
    s2 = _turn_identity_section({"status": "on", "route_cut": True,
                                 "mention_provenance": "pending_carried"})
    assert s2["route_cut"] is False


def test_builder_incluye_seccion_requerida_y_valida():
    t = _trace()
    assert t["turn_identity"]["status"] == "not_wired"
    assert validate_rag_serving_trace(t, route="rag") is not None
    t2 = _trace(turn_identity_obs={"status": "on", "presence": "stale"})
    v = validate_rag_serving_trace(t2, route="rag")
    assert v is not None and v["turn_identity"]["presence"] == "stale"


def test_validador_rechaza_trace_sin_seccion():
    t = _trace()
    del t["turn_identity"]
    assert validate_rag_serving_trace(t) is None


def test_privacidad_jamas_la_mencion():
    t = _trace(turn_identity_obs={"status": "on", "mention": "SN-SECRETO-99",
                                  "mention_provenance": "this_turn"})
    import json
    assert "SN-SECRETO-99" not in json.dumps(t)


# ---------------------------------------------------------------------------
# direct/1 + acople de route (B9)
# ---------------------------------------------------------------------------
def test_direct_valida_solo_en_rutas_directas():
    d = build_direct_route_trace("clarify", {"status": "on", "route_cut": True,
                                             "mention_provenance": "this_turn"})
    assert validate_rag_serving_trace(d, route="clarify") is not None
    assert validate_rag_serving_trace(d, route="rag") is None      # B9
    assert validate_rag_serving_trace(d, route="decline") is None  # route ≠ fila


def test_rag_shape_no_valida_en_fila_clarify():
    assert validate_rag_serving_trace(_trace(), route="clarify") is None


def test_direct_route_invalida_revienta_en_builder():
    with pytest.raises(ValueError):
        build_direct_route_trace("rag", None)


def test_direct_seccion_manipulada_se_rechaza():
    d = build_direct_route_trace("clarify", {"status": "on"})
    d["turn_identity"]["mention"] = "colado"
    assert validate_rag_serving_trace(d, route="clarify") is None
    assert d["schema"] == DIRECT_TRACE_SCHEMA


# ---------------------------------------------------------------------------
# Obs del bot (vista derivada) — sin red
# ---------------------------------------------------------------------------
def test_obs_off_por_defecto(monkeypatch):
    monkeypatch.delenv("F1_RESOLVE_GOVERNED", raising=False)
    monkeypatch.delenv("F1_MENTION_PRECEDENCE", raising=False)
    from src.bot.telegram_bot import _turn_identity_obs
    assert _turn_identity_obs(None) == {"status": "off"}


def test_obs_on_deriva_sin_mencion(monkeypatch):
    monkeypatch.setenv("F1_MENTION_PRECEDENCE", "on")
    monkeypatch.delenv("F1_RESOLVE_GOVERNED", raising=False)
    from src.bot.telegram_bot import _turn_identity_obs
    ti = TurnIdentity(mention="EMA1224B4RW-XQ", mention_provenance="this_turn",
                      route_cut=True)
    obs = _turn_identity_obs(ti)
    assert obs["status"] == "on" and obs["route_cut"] is True
    assert obs["mention_provenance"] == "this_turn"
    assert "mention" not in obs                       # la vista NO lleva el string
    assert obs["presence"] in ("vigente", "stale", "cold")


# ---------------------------------------------------------------------------
# Refresher de presencia single-flight
# ---------------------------------------------------------------------------
def test_refresh_presence_puebla_y_peek_vigente(monkeypatch):
    monkeypatch.setattr(CR, "_load_presence",
                        lambda: (frozenset({"x1"}), ("fp", "1")))
    monkeypatch.setattr(CR, "_presence", None)
    assert CR.refresh_presence() == "refreshed"
    import time as _t
    elements, estado = CR._presence_peek(_t.monotonic())
    assert estado == "vigente" and elements == frozenset({"x1"})


def test_refresh_presence_single_flight(monkeypatch):
    monkeypatch.setattr(CR, "_load_presence",
                        lambda: (frozenset({"x1"}), ("fp", "1")))
    assert CR._presence_refresh_lock.acquire(blocking=False)
    try:
        assert CR.refresh_presence() == "in_progress"  # coalescido, no espera
    finally:
        CR._presence_refresh_lock.release()


def test_refresh_presence_failed_conserva(monkeypatch):
    def _boom():
        raise OSError("db caída")
    monkeypatch.setattr(CR, "_load_presence", _boom)
    prev = {"elements": frozenset({"prev"}), "at": 0.0, "fp": ("f", "0"),
            "fp_at": 0.0}
    monkeypatch.setattr(CR, "_presence", prev)
    assert CR.refresh_presence() == "failed"
    assert CR._presence is prev                       # el set previo sigue ahí
