"""Preflight del ejecutor v3 (S269): 0 llamadas, 0 red, plan alineado al prereg."""

import httpx
import openai
import pytest

from scripts.s269_visual_utility_executor_v3 import (
    FROZEN_POSITIVE_BAND,
    preflight,
    preregistered_band,
)


def _forbid_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("cliente de red construido durante el preflight")

    # El preflight no debe construir NINGÚN cliente: ni HTTP ni OpenAI.
    monkeypatch.setattr(httpx, "Client", _boom)
    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    monkeypatch.setattr(openai, "OpenAI", _boom)


def test_preflight_cero_llamadas_y_plan_alineado(monkeypatch):
    _forbid_network(monkeypatch)
    plan = preflight()

    assert plan["items"] == 80
    assert plan["per_group"] == {"expected_control": 40, "expected_technical": 40}
    assert plan["batches"] == 8
    assert plan["batch_size"] == 10  # batches heredados del ejecutor v1/v2
    assert plan["model"] == "gpt-5.6-luna"
    assert plan["reasoning_effort"] == "none"
    assert plan["max_retries"] == 0  # no-retry, contrato S191
    assert plan["preregistered_positive_band"] == list(FROZEN_POSITIVE_BAND) == [28, 44]
    assert plan["paid_calls_made"] == 0
    assert len(plan["items_preview"]) == 80

    estimate = plan["estimate"]
    # Precios Luna congelados ($1/$6 por Mtok) y estimación por-item MEDIDA.
    assert estimate["pricing_usd_per_million_tokens"] == {"input": 1.0, "output": 6.0}
    assert estimate["basis"] == "s191_luna_receipts_v2_measured"
    # 60 items midieron $0.04029 → 80 items deben rondar $0.05, muy bajo el budget.
    assert 0.03 < estimate["estimated_cost_usd"] < 0.2
    assert estimate["estimated_cost_usd"] < estimate["budget_max_usd"] == 2.0


def test_banda_anti_tamper(tmp_path):
    # Banda distinta de la congelada (p.ej. la vieja [10,30] de S191) → ABORT.
    movida = tmp_path / "prereg_movida.yaml"
    movida.write_text(
        "trigger:\n  preregistered_positive_range: [10, 30]\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="no se mueve"):
        preregistered_band(movida)

    # Sin banda parseable → ABORT.
    vacia = tmp_path / "prereg_vacia.yaml"
    vacia.write_text("instrument: x\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="parseable"):
        preregistered_band(vacia)

    # Banda idéntica a la congelada → OK.
    ok = tmp_path / "prereg_ok.yaml"
    ok.write_text(
        "trigger:\n  preregistered_positive_range: [28, 44]\n", encoding="utf-8"
    )
    assert preregistered_band(ok) == FROZEN_POSITIVE_BAND
