"""S270 Etapa 2 (DEC-126): el runner del probe es determinista y testeable sin red.

Cubre: construcción de chunks servidos desde el freeze (paridad de filtro), el check de
disclosure pre-declarado (obl_872c), el merge-carrier (obl_0d6a), la lógica de estabilidad
(≥2/3) y el gate (conversión / regresión protegida / conflicto nuevo / stretch fuera del
gate). 0 llamadas de red; 0 DB.
"""
from __future__ import annotations

import json

import pytest
import yaml

import scripts.s270_etapa2_probe as probe


# ─────────────────────────── prereg ↔ runner ───────────────────────────

def test_gate_eligible_matches_prereg_and_excludes_stretch_and_demoted() -> None:
    prereg = yaml.safe_load(probe.PREREG.read_text(encoding="utf-8"))
    prereg_ids = {row["obligation_id"] for row in prereg["gate_eligible"]}
    runner_ids = {oblid for oblid, _qid, _check in probe.GATE_ELIGIBLE}
    assert runner_ids == prereg_ids
    assert len(runner_ids) == 8
    assert probe.STRETCH_ID not in runner_ids
    assert not runner_ids & set(probe.DEMOTED_IDS)
    assert prereg["stretch"]["obligation_id"] == probe.STRETCH_ID


# ─────────────────────────── chunks servidos desde el freeze ───────────────────────────

def _rows() -> list[dict]:
    return [
        {"id": "a", "similarity": 0.8, "content": "x"},          # pasa por similitud
        {"id": "b", "similarity": 0.1, "content": "y"},          # cae: baja y no validada
        {"id": "c", "content": "z"},                              # sin similarity: coverage validada
    ]


def test_served_chunks_reproduces_generator_filter() -> None:
    kept = probe.served_chunks(
        _rows(),
        validator=lambda row: row.get("id") == "c",
        threshold=0.4,
        compatibility_lane="compat_lane_v1",
    )
    assert [r["id"] for r in kept] == ["a", "c"]


def test_served_chunks_rejects_compatibility_lane_rows() -> None:
    rows = _rows() + [{"id": "d", "retrieval_lane": "compat_lane_v1"}]
    with pytest.raises(RuntimeError, match="compatibilidad"):
        probe.served_chunks(
            rows,
            validator=lambda row: False,
            threshold=0.4,
            compatibility_lane="compat_lane_v1",
        )


# ─────────────────────────── disclosure obl_872c (spec DEC-125 fila 8) ───────────────────────────

def test_disclosure_covered_requires_both_values_and_formula() -> None:
    positive = (
        "La prosa del manual declara seis tipos de retardo, pero la tabla recoge "
        "siete tipos de retardo distintos."
    )
    assert probe.disclosure_covered(positive) is True


def test_disclosure_not_covered_without_formula() -> None:
    answer = (
        "Hay seis tipos de retardo. Más adelante se enumeran siete tipos de retardo."
    )
    assert probe.disclosure_covered(answer) is False


def test_disclosure_not_covered_with_single_value() -> None:
    answer = "El manual también indica: se puede asignar uno de seis tipos de retardo."
    assert probe.disclosure_covered(answer) is False


# ─────────────────────────── merge-carrier obl_0d6a (DEC-125 filas 11/12) ───────────────────────────

def _hp017_item() -> dict:
    packet = json.loads(probe.SCORE_PACKET.read_text(encoding="utf-8"))
    return next(item for item in packet["items"] if item["qid"] == "hp017")


def test_merged_carrier_requires_both_warning_sentences() -> None:
    item = _hp017_item()
    both = (
        "Al programar reglas de causa-efecto evite las lógicas contradictorias. "
        "Es de vital importancia probar rigurosamente todas las reglas durante la "
        "puesta en marcha del sistema para verificar que no haya conflictos lógicos."
    )
    only_design = "Al programar reglas de causa-efecto evite las lógicas contradictorias."
    assert probe.merged_carrier_covered(both, item) is True
    assert probe.merged_carrier_covered(only_design, item) is False


# ─────────────────────────── estabilidad y gate ───────────────────────────

_CONF = "conf_26f63590494f"


def _items() -> dict[str, dict]:
    def item(qid: str, oblids: list[str], conflicts: list[str]) -> dict:
        return {
            "qid": qid,
            "fragment_count": 13,
            "obligations": [{"obligation_id": o} for o in oblids],
            "conflicts": [{"conflict_id": c} for c in conflicts],
        }

    return {
        "cat018": item("cat018", ["obl_7bba8d03d496", "obl_015f9b9aaa3a", "obl_5784f16b1a11"], []),
        "hp002": item("hp002", ["obl_b6f6211be439", "obl_a5d9fa1f9253", "obl_07eee3300535", "obl_0db2b9f2842a"], []),
        "hp011": item("hp011", ["obl_2f5d79e354b9", "obl_161564ff41bf", "obl_05482a6b3f0e"], []),
        "hp017": item("hp017", ["obl_b2043cd4379b", "obl_7aa723717412", "obl_16637b935bd4", "obl_0d6a30948dfd", "obl_872c35fb41d7"], [_CONF]),
    }


_PROTECTED = {
    "obl_5784f16b1a11": "cat018",
    "obl_0db2b9f2842a": "hp002",
    "obl_05482a6b3f0e": "hp011",
}


def _score(covered: list[str], unsafe: list[str] = (), merged: bool = False,
           disclosure: bool = False) -> dict:
    return {
        "covered_obligation_ids": sorted(covered),
        "unsafe_conflict_ids": sorted(unsafe),
        "invalid_citations": [],
        "merged_warning_block_covered": merged,
        "disclosure_covered": disclosure,
    }


def _replicas(off_by_qid: dict, on_by_qid: dict) -> list[dict]:
    rows = []
    for qid in probe.QIDS:
        for rep in probe.REPLICATES:
            rows.append(
                {
                    "qid": qid,
                    "replicate": rep,
                    "off_score": off_by_qid.get(qid, [_score([])] * 3)[rep - 1],
                    "on_score": on_by_qid.get(qid, [_score([])] * 3)[rep - 1],
                }
            )
    return rows


_BASE_PROTECTED_OFF = {
    "cat018": [_score(["obl_5784f16b1a11"])] * 3,
    "hp002": [_score(["obl_0db2b9f2842a"])] * 3,
    "hp011": [_score(["obl_05482a6b3f0e"])] * 3,
}
_BASE_PROTECTED_ON = _BASE_PROTECTED_OFF


def test_aggregate_go_with_one_stable_conversion() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["cat018"] = [_score(["obl_5784f16b1a11", "obl_7bba8d03d496"])] * 3
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert out["stable_conversions"] == ["obl_7bba8d03d496"]
    assert out["stable_protected_regressions"] == []
    assert out["new_stable_conflicts"] == []
    assert out["gate_verdict"] == "GO"
    assert out["requires_human_read"] is False


def test_aggregate_unstable_conversion_does_not_count() -> None:
    on = dict(_BASE_PROTECTED_ON)
    # cubierta solo 1/3 en ON → inestable
    on["cat018"] = [
        _score(["obl_5784f16b1a11", "obl_7bba8d03d496"]),
        _score(["obl_5784f16b1a11"]),
        _score(["obl_5784f16b1a11"]),
    ]
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert out["stable_conversions"] == []
    assert out["gate_verdict"] == "NO_GO"


def test_aggregate_protected_regression_blocks_gate_and_flags_human_read() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["cat018"] = [_score(["obl_5784f16b1a11", "obl_7bba8d03d496"])] * 3  # gana la conversión…
    on["hp002"] = [_score([])] * 3                          # …pero pierde la protegida
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert "obl_7bba8d03d496" in out["stable_conversions"]
    assert out["stable_protected_regressions"] == ["obl_0db2b9f2842a"]
    assert out["gate_verdict"] == "NO_GO"
    assert out["requires_human_read"] is True


def test_aggregate_new_stable_conflict_blocks_gate() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["cat018"] = [_score(["obl_5784f16b1a11", "obl_7bba8d03d496"])] * 3
    on["hp017"] = [_score([], unsafe=[_CONF]), _score([], unsafe=[_CONF]), _score([])]
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert out["new_stable_conflicts"] == [_CONF]
    assert out["gate_verdict"] == "NO_GO"
    assert out["conflict_flags_for_human_read"]


def test_aggregate_preexisting_conflict_in_both_arms_is_not_new() -> None:
    off = dict(_BASE_PROTECTED_OFF)
    on = dict(_BASE_PROTECTED_ON)
    off["hp017"] = [_score([], unsafe=[_CONF])] * 3
    on["hp017"] = [_score([], unsafe=[_CONF])] * 3
    on["cat018"] = [_score(["obl_5784f16b1a11", "obl_7bba8d03d496"])] * 3
    out = probe.aggregate(_replicas(off, on), _items(), _PROTECTED, actual_cost=1.0)
    assert out["new_stable_conflicts"] == []
    # pero sigue listado para lectura humana (DEC-092b)
    assert out["conflict_flags_for_human_read"]
    assert out["requires_human_read"] is True
    assert out["gate_verdict"] == "GO"


def test_aggregate_stretch_never_counts_toward_gate() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["hp011"] = [_score(["obl_05482a6b3f0e", probe.STRETCH_ID])] * 3
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert out["stable_conversions"] == []              # el stretch no convierte el gate
    assert out["stretch"]["on_covered"] == 3
    assert out["stretch"]["off_covered"] == 0
    assert out["stretch"]["counts_toward_gate"] is False
    assert out["gate_verdict"] == "NO_GO"               # sin conversión eligible no hay GO


def test_aggregate_merged_and_disclosure_checks_feed_the_gate() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["hp017"] = [_score([], merged=True, disclosure=True)] * 3
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED, actual_cost=1.0
    )
    assert set(out["stable_conversions"]) == {probe.MERGED_ID, probe.DISCLOSURE_ID}
    assert out["gate_verdict"] == "GO"


def test_aggregate_cost_ceiling_check() -> None:
    on = dict(_BASE_PROTECTED_ON)
    on["cat018"] = [_score(["obl_5784f16b1a11", "obl_7bba8d03d496"])] * 3
    out = probe.aggregate(
        _replicas(_BASE_PROTECTED_OFF, on), _items(), _PROTECTED,
        actual_cost=probe.COST_CEILING_USD + 0.01,
    )
    assert out["checks"]["cost_below_ceiling"] is False
    assert out["gate_verdict"] == "NO_GO"


def test_cost_usd_uses_pinned_pricing() -> None:
    assert probe.cost_usd(1_000_000, 1_000_000) == pytest.approx(18.0)
    assert probe.cost_usd(10_000, 3_500) == pytest.approx(0.0825)


# ─────────────────────────── probe v2 (wrapper, DEC-126) ───────────────────────────

def test_probe_v2_wrapper_rebinds_y_prereg_coherente() -> None:
    saved = {
        k: getattr(probe, k)
        for k in ("PREREG", "REPLICAS", "OUT", "RESULT_SCHEMA", "RUNNER_KEY",
                  "RUNNER_FILE", "run_replicate", "preflight")
    }
    try:
        import scripts.s270_etapa2_probe_v2 as v2  # noqa: F401

        assert probe.PREREG.name == "s270_etapa2_probe_v2_prereg_v1.yaml"
        assert probe.RESULT_SCHEMA == "s270_etapa2_probe_v2_result_v1"
        assert probe.RUNNER_KEY == "scripts/s270_etapa2_probe_v2.py"
        assert probe.run_replicate is v2.run_replicate_v2
        prereg = yaml.safe_load(probe.PREREG.read_text(encoding="utf-8"))
        assert prereg["probe_number"] == 2
        assert prereg["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
        # el pin registrado es un sha valido (snapshot HISTORICO del mecanismo v2;
        # el fichero vivo ya evoluciono a v3 — el pin vivo lo verifica el prereg v3)
        pin = prereg["frozen_inputs_sha256_lf_normalized"]["src/rag/must_preserve.py"]
        assert len(pin) == 64
        assert probe.runner_pin_status(prereg) == "MATCH"
    finally:
        for k, v in saved.items():
            setattr(probe, k, v)


def test_probe_v3_wrapper_rebinds_y_prereg_coherente() -> None:
    saved = {
        k: getattr(probe, k)
        for k in ("PREREG", "REPLICAS", "OUT", "RESULT_SCHEMA", "RUNNER_KEY",
                  "RUNNER_FILE", "run_replicate", "preflight")
    }
    try:
        import scripts.s270_etapa2_probe_v3 as v3  # noqa: F401

        assert probe.PREREG.name == "s270_etapa2_probe_v3_prereg_v1.yaml"
        assert probe.RESULT_SCHEMA == "s270_etapa2_probe_v3_result_v1"
        assert probe.run_replicate is v3.run_replicate_v3
        prereg = yaml.safe_load(probe.PREREG.read_text(encoding="utf-8"))
        assert prereg["probe_number"] == 3
        # el pin del mecanismo v3 SI coincide con el fichero vivo
        assert (
            prereg["frozen_inputs_sha256_lf_normalized"]["src/rag/must_preserve.py"]
            == probe.normalized_sha(probe.ROOT / "src/rag/must_preserve.py")
        )
        assert probe.runner_pin_status(prereg) == "MATCH"
    finally:
        for k, v in saved.items():
            setattr(probe, k, v)
