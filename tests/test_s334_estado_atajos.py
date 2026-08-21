"""s334 §3 (R8) — las rutas terminales de atajo CON contenido refrescan el estado
conversacional vía la transición de respuesta compartida, y el pending se consume.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.bot import telegram_bot as tb
from src.orchestrator.conversation_policy import WorkingState
from src.orchestrator.conversation_policy_impl import (
    advance_after_shortcut,
    estado_atajos_enabled,
)

NOW = datetime(2026, 8, 21, 14, 0, 0, tzinfo=timezone.utc)


class _Ctx:
    def __init__(self, ws=None):
        self.user_data = {}
        if ws is not None:
            self.user_data["mt_working_state"] = ws


def test_transicion_delegada_semantica_de_respuesta():
    ws = WorkingState(last_target_models=("2X-AF1",), last_query="vieja",
                      last_turn_at=NOW - timedelta(minutes=50),
                      available_models=("2X-AF1", "2X-AF2"),
                      pending_mention="XYZ-1", pending_at=NOW - timedelta(minutes=1))
    ws2 = advance_after_shortcut(ws, "¿Qué centrales de KIDDE tienes?", "listado…", NOW)
    assert ws2.last_query == "¿Qué centrales de KIDDE tienes?"
    assert ws2.last_target_models == ()            # el atajo no bindea
    assert ws2.last_turn_at == NOW                 # turno respondido de verdad (S99 ok)
    assert ws2.pending_mention is None and ws2.pending_at is None  # ciclo máx 1
    assert ws2.available_models == ("2X-AF1", "2X-AF2")            # heredado, declarado
    assert ws2.last_answer_excerpt == "listado…"


def test_refresco_flag_on(monkeypatch):
    monkeypatch.setenv("F1_ESTADO_ATAJOS", "on")
    ctx = _Ctx(WorkingState(pending_mention="XYZ-1", pending_at=NOW))
    tb._refrescar_estado_atajo(ctx, "¿Qué centrales de KIDDE tienes?", "listado")
    ws = ctx.user_data["mt_working_state"]
    assert ws.last_query == "¿Qué centrales de KIDDE tienes?"
    assert ws.pending_mention is None


def test_refresco_flag_off_es_noop(monkeypatch):
    monkeypatch.delenv("F1_ESTADO_ATAJOS", raising=False)
    ws0 = WorkingState(last_query="vieja", last_turn_at=NOW)
    ctx = _Ctx(ws0)
    tb._refrescar_estado_atajo(ctx, "¿Qué centrales de KIDDE tienes?", "listado")
    assert ctx.user_data["mt_working_state"] is ws0   # byte-idéntico: ni se toca


def test_refresco_sin_estado_previo_crea_estado(monkeypatch):
    monkeypatch.setenv("F1_ESTADO_ATAJOS", "on")
    ctx = _Ctx()
    tb._refrescar_estado_atajo(ctx, "¿fabricantes?", "lista")
    assert ctx.user_data["mt_working_state"].last_query == "¿fabricantes?"


def test_refresco_es_fail_open(monkeypatch):
    monkeypatch.setenv("F1_ESTADO_ATAJOS", "on")

    class _Rota:
        user_data = None                              # user_data inválido

    tb._refrescar_estado_atajo(_Rota(), "q", "r")     # no revienta


def test_valor_raro_del_flag_revienta(monkeypatch):
    monkeypatch.setenv("F1_ESTADO_ATAJOS", "1")
    with pytest.raises(RuntimeError):
        estado_atajos_enabled()


def test_los_5_call_sites_del_dispatcher():
    """Pin de FUENTE: las 5 rutas con contenido llaman al refresco (4 puntos de
    código — fabricantes/catalogo comparten bloque) y las cortesías NO."""
    fuente = (tb.__file__ and open(tb.__file__, encoding="utf-8").read()) or ""
    cuerpo = fuente.split("async def _ejecutar_plan", 1)[1].split("async def ", 1)[0]
    assert cuerpo.count("_refrescar_estado_atajo(") == 4
    cortesias = cuerpo.split('if ruta == "cortesia_saludo"', 1)[1].split('if ruta in (', 1)[0]
    assert "_refrescar_estado_atajo" not in cortesias
