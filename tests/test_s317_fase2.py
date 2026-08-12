# -*- coding: utf-8 -*-
"""s317 — #72 FASE 2 (dúo r15): paralelización determinista del retrieval +
reintentos opt-in de solo-lectura + canales CONTENT/DIVERSIFY en la traza.

La suite corre con RETRIEVAL_PARALLEL=off y HTTP_RETRIES=off (conftest): estos
tests encienden cada mecanismo EXPLÍCITAMENTE y verifican su contrato."""
from __future__ import annotations

import httpx
import pytest

from src import http_pool
from src.rag import retriever


# --- 2a: ejecutor determinista ------------------------------------------------

def _tarea(valor, canal="CONTENT", boost=None):
    return (lambda: [{"id": valor, "similarity": 0.5}], boost, canal)


def test_orden_determinista_bajo_finalizacion_invertida(monkeypatch):
    """La PARIDAD de composición exige extensión en orden de LISTA aunque las
    tareas terminen en orden inverso (gate 1 pre-registrado del dúo r15)."""
    import time as _t
    monkeypatch.setenv("RETRIEVAL_PARALLEL", "on")
    demoras = {"a": 0.15, "b": 0.05, "c": 0.0}

    def lenta(nombre):
        def thunk():
            _t.sleep(demoras[nombre])
            return [{"id": nombre, "similarity": 0.5}]
        return (thunk, None, "CONTENT")

    salida = retriever._ejecutar_tareas_modelo([lenta("a"), lenta("b"), lenta("c")])
    assert [c["id"] for c in salida] == ["a", "b", "c"]


def test_parallel_off_no_construye_executor(monkeypatch):
    """RETRIEVAL_PARALLEL=off = el bucle secuencial de hoy, sin executor."""
    monkeypatch.setenv("RETRIEVAL_PARALLEL", "off")

    def bomba(*a, **k):
        raise AssertionError("executor construido con el kill-switch en off")

    monkeypatch.setattr(retriever, "ThreadPoolExecutor", bomba)
    salida = retriever._ejecutar_tareas_modelo([_tarea("x"), _tarea("y")])
    assert [c["id"] for c in salida] == ["x", "y"]


def test_una_sola_tarea_no_paga_executor(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_PARALLEL", "on")
    monkeypatch.setattr(retriever, "ThreadPoolExecutor",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    salida = retriever._ejecutar_tareas_modelo([_tarea("solo")])
    assert [c["id"] for c in salida] == ["solo"]


def test_boost_y_canal_por_tarea(monkeypatch):
    """El boost se aplica SOLO donde la tarea lo declara (None = intacto) y el
    tag de canal es el de la tarea — la semántica exacta de los bucles de hoy."""
    monkeypatch.setenv("RETRIEVAL_PARALLEL", "on")
    salida = retriever._ejecutar_tareas_modelo([
        _tarea("kw", canal="CONTENT", boost=None),
        _tarea("syn", canal="TARGETED", boost=0.85),
    ])
    por_id = {c["id"]: c for c in salida}
    assert por_id["kw"]["similarity"] == 0.5
    assert por_id["syn"]["similarity"] == 0.85
    assert por_id["kw"]["_channel"] == "CONTENT"
    assert por_id["syn"]["_channel"] == "TARGETED"


def test_excepcion_de_tarea_propaga_como_en_secuencial(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_PARALLEL", "on")

    def rota():
        raise RuntimeError("canal roto")

    with pytest.raises(RuntimeError):
        retriever._ejecutar_tareas_modelo([_tarea("ok"), (rota, None, "CONTENT")])


# --- 2b: reintentos opt-in en el shim ----------------------------------------

class _ClienteFalla:
    """Fake con la forma que intercepta el kill-switch (with + get)."""

    def __init__(self, guion):
        self._guion = guion          # lista de excepciones o respuestas
        self.llamadas = 0

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def get(self, url, **kwargs):
        self.llamadas += 1
        paso = self._guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        return paso


def _con_fake(monkeypatch, guion):
    fake = _ClienteFalla(guion)
    monkeypatch.setattr(http_pool.httpx, "Client", lambda **k: fake)
    monkeypatch.setattr(http_pool.time, "sleep", lambda s: None)
    return fake


def test_retry_transporte_reintenta_una_vez(monkeypatch):
    monkeypatch.setenv("HTTP_RETRIES", "on")
    fake = _con_fake(monkeypatch, [httpx.ConnectError("boom"), "resp"])
    with http_pool.abierto(timeout=1.0, reintentos=1) as c:
        assert c.get("http://x") == "resp"
    assert fake.llamadas == 2


def test_pooltimeout_no_se_reintenta(monkeypatch):
    """(Fable r15 F2) PoolTimeout es backpressure LOCAL: reintentarlo amplifica
    carga justo bajo saturación — queda EXCLUIDO del set reintentable."""
    monkeypatch.setenv("HTTP_RETRIES", "on")
    fake = _con_fake(monkeypatch, [httpx.PoolTimeout("saturado")])
    with pytest.raises(httpx.PoolTimeout):
        with http_pool.abierto(timeout=1.0, reintentos=1) as c:
            c.get("http://x")
    assert fake.llamadas == 1


def test_respuesta_http_no_se_reintenta(monkeypatch):
    """El shim reintenta RED, jamás respuestas: un 500 es del sitio."""
    monkeypatch.setenv("HTTP_RETRIES", "on")

    class _Resp500:
        status_code = 500

    fake = _con_fake(monkeypatch, [_Resp500()])
    with http_pool.abierto(timeout=1.0, reintentos=1) as c:
        assert c.get("http://x").status_code == 500
    assert fake.llamadas == 1


def test_agotado_propaga_la_excepcion_original(monkeypatch):
    monkeypatch.setenv("HTTP_RETRIES", "on")
    fake = _con_fake(monkeypatch, [httpx.ConnectError("a"), httpx.ConnectError("b")])
    with pytest.raises(httpx.ConnectError):
        with http_pool.abierto(timeout=1.0, reintentos=1) as c:
            c.get("http://x")
    assert fake.llamadas == 2      # 1 + 1 reintento, no más


def test_kill_switch_retries_off(monkeypatch):
    monkeypatch.setenv("HTTP_RETRIES", "off")
    fake = _con_fake(monkeypatch, [httpx.ConnectError("boom")])
    with pytest.raises(httpx.ConnectError):
        with http_pool.abierto(timeout=1.0, reintentos=1) as c:
            c.get("http://x")
    assert fake.llamadas == 1


def test_default_sin_reintentos(monkeypatch):
    """Sitio sin opt-in = byte-idéntico a hoy aunque el flag global esté on."""
    monkeypatch.setenv("HTTP_RETRIES", "on")
    fake = _con_fake(monkeypatch, [httpx.ConnectError("boom")])
    with pytest.raises(httpx.ConnectError):
        with http_pool.abierto(timeout=1.0) as c:
            c.get("http://x")
    assert fake.llamadas == 1


# --- M5: canales CONTENT / DIVERSIFY en la traza ------------------------------

def test_content_fail_open_registra_canal(monkeypatch):
    monkeypatch.setattr(http_pool.httpx, "Client",
                        lambda **k: _ClienteFalla([httpx.ConnectError("net")]))
    trace: dict = {}
    rows = retriever.content_search("especificaciones", limit=3,
                                    product_model="NC-PF2", _trace=trace)
    assert rows == []
    fallos = trace.get("channel_failures") or []
    assert fallos and fallos[0]["channel"] == "CONTENT"


def test_diversify_fail_open_registra_canal(monkeypatch):
    guion = [httpx.ConnectError(f"net{i}") for i in range(8)]
    monkeypatch.setattr(http_pool.httpx, "Client",
                        lambda **k: _ClienteFalla(list(guion)))
    trace: dict = {}
    rows = retriever._fetch_top_chunks_by_source_file(
        "manual.pdf", "cómo se conecta la sirena", limit=2, _trace=trace)
    assert rows == []
    fallos = trace.get("channel_failures") or []
    assert fallos
    assert {f["channel"] for f in fallos} == {"DIVERSIFY"}


def test_trace_persiste_canales_nuevos():
    from src.rag.runtime_trace import (
        build_rag_serving_trace,
        validate_rag_serving_trace,
    )
    trace = build_rag_serving_trace(
        coverage_trace={}, served_chunks=[], must_preserve_trace=None,
        must_preserve_outcome=None, release_policy={"profile": "off"},
        transport_parts=1,
        retrieval_health={"channel_failures": [
            {"channel": "CONTENT", "error_type": "ConnectError"},
            {"channel": "DIVERSIFY", "error_type": "ReadTimeout"},
        ]},
    )
    validado = validate_rag_serving_trace(trace)
    assert validado is not None
    canales = [f["channel"] for f in validado["retrieval"]["channel_failures"]]
    assert canales == ["CONTENT", "DIVERSIFY"]
