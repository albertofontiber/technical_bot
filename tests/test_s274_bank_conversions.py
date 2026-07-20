"""S274 (DEC-134): el banking de la conversión 0d6a es determinista, cierra sobre
insumos SHA-pineados (gate P1 + probe #4 + smoke candidato) y el closeout declara
la cadena P0→P4 con los 6 residuales exhaustos. Sin red, sin DB."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import scripts.s274_bank_conversions as mod

RESIDUAL_6 = {
    "obl_2f5d79e354b9", "obl_7bba8d03d496", "obl_a5d9fa1f9253",
    "obl_015f9b9aaa3a", "obl_b2043cd4379b", "obl_7aa723717412",
}


def test_banked_funnel_arithmetic() -> None:
    report = mod.build_projection()
    assert report["banked_funnel"] == {
        "denominator": 154,
        "ok": 146,
        "synthesis_miss": 6,
        "retrieval_miss": 2,
        "ok_pct": 94.81,
    }
    assert report["facts_moved_to_ok"] == 1
    assert report["official_atomic_kpi"] is None
    assert report["target"]["required_ok"] == 151
    assert report["target"]["conversions_needed"] == 5


def test_conversion_is_deployable_pair_and_live_state_is_honest() -> None:
    report = mod.build_projection()
    (conv,) = report["conversions_banked"]
    assert conv["obligation_id"] == "obl_0d6a30948dfd"
    assert conv["qid"] == "hp017"
    assert "A-C1" in conv["certificacion"] and "3/3" in conv["certificacion"]
    assert "PENDIENTE" in conv["estado_vivo"]  # sin recibo vivo aún (patrón DEC-131)
    assert set(mod.SHIP_PAIR) == {
        "COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER",
    }
    ship = report["ship_config_candidate"]
    assert set(ship["flags_on"]) == set(mod.SHIP_PAIR)
    assert "rollback" in ship["runbook"]


def test_residual_six_exhausted_partition() -> None:
    report = mod.build_projection()
    exhausted = report["remaining_synthesis_exhausted_in_annex_family"]
    assert set(exhausted) == RESIDUAL_6
    for oblid, row in exhausted.items():
        assert row["fix_probado"], oblid
        assert row["como_murio"], oblid
    # C2 murió en P1 (seed-270 reconfirmada), no en el probe
    assert "NO-GO en P1" in exhausted["obl_2f5d79e354b9"]["como_murio"]
    assert "OTRA familia" in report["strategic_declaration"]


def test_pin_drift_fails(monkeypatch) -> None:
    monkeypatch.setitem(
        mod.PINNED_SHA256_LF, "evals/s272_banked_funnel_v1.json", "0" * 64
    )
    with pytest.raises(ValueError, match="SHA drift"):
        mod.build_projection()


def test_banked_artifact_matches_projection() -> None:
    import json

    artifact = json.loads(
        Path("evals/s274_banked_funnel_v1.json").read_text(encoding="utf-8")
    )
    report = mod.build_projection()
    assert artifact["banked_funnel"] == report["banked_funnel"]
    assert artifact["schema"] == "s274_banked_funnel_v1"
    assert artifact["dec"] == "DEC-134"


def test_closeout_chain_and_budget() -> None:
    closeout = yaml.safe_load(
        Path("evals/s274_bloquesCD_closeout_v1.yaml").read_text(encoding="utf-8")
    )
    assert closeout["schema"] == "s274_bloquesCD_closeout_v1"
    assert closeout["dec"] == "DEC-134"
    phases = closeout["phases"]
    assert set(phases) == {
        "P0_build_flagoff", "P1_etapa1_v9", "P2_probe_consolidado",
        "P3_negcontrol_vivo", "P4_cierre_banking",
    }
    spent = sum(float(ph["cost_usd"]) for ph in phases.values())
    assert abs(spent - float(closeout["budget"]["spent_usd"])) < 1e-6
    assert spent <= float(closeout["budget"]["total_ceiling_usd"])
    assert closeout["banked_funnel"]["ok"] == 146
    assert closeout["banked_funnel"]["ok_pct"] == 94.81
    assert set(closeout["residual_synthesis_exhausted"]) == RESIDUAL_6
    assert "OTRA" in closeout["strategic_declaration"]
    for rel in closeout["outputs"]:
        assert Path(rel).exists(), rel
