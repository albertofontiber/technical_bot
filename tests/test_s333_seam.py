"""s333 B3 — seam `_correccion_seam` del transporte (espejo de `_intent_seam`)
+ el pin del contrato de threading (Sol-1 CRÍTICO de la ronda s333).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.bot import telegram_bot as tb


@pytest.fixture(autouse=True)
def _celda_limpia(monkeypatch):
    """La celda es a nivel PROCESO: cada test parte sin fn construida."""
    monkeypatch.setattr(tb, "_CORRECCION_FN_CELL", {})
    monkeypatch.delenv("F1_CORRECCION_LLM", raising=False)


def test_off_devuelve_none_y_estampa_off():
    obs: dict = {}
    assert tb._correccion_seam(obs) is None
    assert obs == {"status": "off", "decision": "none", "latency_ms": 0}


def test_valor_raro_revienta_ruidoso(monkeypatch):
    monkeypatch.setenv("F1_CORRECCION_LLM", "1")
    with pytest.raises(RuntimeError):
        tb._correccion_seam({})


def test_on_invoca_y_estampa(monkeypatch):
    monkeypatch.setenv("F1_CORRECCION_LLM", "on")
    import src.orchestrator.correccion_llm as cl

    def _fake_construir(api_key, model=None, timeout_s=6.0):  # noqa: ARG001
        def _fn(q, lq, marca):  # noqa: ARG001
            return "correccion"
        return _fn

    monkeypatch.setattr(cl, "construir_correccion_fn", _fake_construir)
    obs: dict = {}
    fn = tb._correccion_seam(obs)
    assert obs["status"] == "not_invoked"
    assert fn("sí, dije Kidde", "¿Qué centrales ID tienes?", "kidde") == "correccion"
    assert obs["status"] == "invoked" and obs["decision"] == "correccion"
    assert isinstance(obs["latency_ms"], int)


def test_decision_fuera_de_enum_estampa_fail_open(monkeypatch):
    monkeypatch.setenv("F1_CORRECCION_LLM", "on")
    import src.orchestrator.correccion_llm as cl
    monkeypatch.setattr(cl, "construir_correccion_fn",
                        lambda *a, **k: (lambda q, lq, m: "quiza"))
    obs: dict = {}
    fn = tb._correccion_seam(obs)
    fn("x", "y", "kidde")
    assert obs["decision"] == "fail_open"


def test_fallo_de_construccion_es_ruidoso_y_fail_open(monkeypatch):
    monkeypatch.setenv("F1_CORRECCION_LLM", "on")
    import src.orchestrator.correccion_llm as cl

    def _boom(*a, **k):
        raise RuntimeError("sin api key")

    monkeypatch.setattr(cl, "construir_correccion_fn", _boom)
    obs: dict = {}
    fn = tb._correccion_seam(obs)
    assert fn("x", "y", "kidde") is None
    assert obs["status"] == "construction_failed"
    # centinela cacheado: el segundo turno NO re-intenta construir
    assert tb._CORRECCION_FN_CELL["fn"] is False
    assert fn("x2", "y2", "kidde") is None


def test_pin_threading_con_cualquier_seam():
    """PIN del contrato Sol-1 (s333 §1): el resolve se mueve a `to_thread` cuando
    CUALQUIER seam LLM está activo. Es un tripwire de FUENTE a propósito (el e2e
    de conducta lo ejercita en el gate): si la condición pierde `_correccion_fn`,
    este test cae antes que el event loop en producción."""
    fuente = Path(tb.__file__).read_text(encoding="utf-8")
    assert "_intent_fn is not None or _correccion_fn is not None" in fuente
    idx_cond = fuente.index("_intent_fn is not None or _correccion_fn is not None")
    idx_thread = fuente.index("asyncio.to_thread", idx_cond)
    assert 0 < idx_thread - idx_cond < 600, "to_thread ya no sigue a la condición"
