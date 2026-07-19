"""s274 — validación de esquema del prereg Bloques C/D + coherencia con los
diagnósticos committeados. Sin red, sin DB: solo lee ficheros versionados."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

PREREG = Path("evals/s274_bloquesCD_prereg_v1.yaml")
DESIGN = Path("evals/s274_bloquesCD_design_v1.md")
DIAG_C1 = Path("evals/s274_serving_view_diag_v1.json")
DIAG_D1 = Path("evals/s274_hybrid_funnel_diag_v1.json")

CANDIDATES = {
    "obl_0d6a30948dfd", "obl_7bba8d03d496", "obl_2f5d79e354b9",
    "obl_a5d9fa1f9253", "obl_b2043cd4379b", "obl_7aa723717412",
    "obl_015f9b9aaa3a",
}


def _prereg() -> dict:
    return yaml.safe_load(PREREG.read_text(encoding="utf-8"))


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def test_schema_and_status_not_executed():
    p = _prereg()
    assert p["schema"] == "s274_bloquesCD_prereg_v1"
    assert p["status"] == "preregistered_not_executed"
    assert p["execution_requires"] == "duo_protocolo3_then_alberto_go"
    assert Path(p["design_doc"]) == DESIGN and DESIGN.exists()


def test_sha_pins_match_working_tree():
    pins = _prereg()["frozen_inputs_sha256_lf"]
    assert len(pins) == 8
    for rel, expected in pins.items():
        path = Path(rel)
        assert path.exists(), rel
        assert _sha256_lf(path) == expected, f"drift en {rel}"


def test_c1_diagnostic_verdict_all_pass():
    diag = json.loads(DIAG_C1.read_text(encoding="utf-8"))
    assert diag["schema"] == "s274_serving_view_diag_v1"
    v = diag["verdict"]
    assert v["all_pass"] is True
    assert v["serving_view_truncation_confirmed"] is True
    assert v["served_view_blind"] is True
    assert v["binding_would_hold_all_replicas"] is True
    # hallazgo que refina DEC-131: b2043 comparte causa serving-view
    assert v["b2043_shares_serving_view_cause"] is True
    frag = diag["fragment"]
    assert frag["raw_chars"] == 2864 and frag["served_chars"] == 1037
    assert frag["coverage_cards_spans"] == [[675, 1032], [419, 673], [1694, 2052]]


def test_d1_diagnostic_funnel_executed_and_within_budget():
    diag = json.loads(DIAG_D1.read_text(encoding="utf-8"))
    assert diag["schema"] == "s274_hybrid_funnel_diag_v1"
    assert diag["mode"] == "execute"
    assert diag["actual_cost_usd"] <= 0.10          # techo autorizado de la sesión
    assert diag["database_reads"] == 0 and diag["database_writes"] == 0
    fates = [p.get("fate") for p in diag["proposals"]]
    assert len(fates) == 80
    assert fates.count("rejected_shape") == 62      # causa dominante medida
    # obl_015f: el contenido diana SE PROPONE y muere en shape (no en grounding)
    s = diag["target_summary"]["obl_015f9b9aaa3a"]
    assert s["proposals_target_relevant"] == 2
    assert s["proposal_fates"] == ["rejected_shape"]


def test_mechanisms_cover_the_seven_candidates_with_flags_off():
    p = _prereg()
    mech = p["mechanisms"]
    covered: set[str] = set()
    for m in mech.values():
        covered.update(m.get("targets") or ([m["target"]] if "target" in m else []))
    assert covered == CANDIDATES
    assert mech["C1"]["flag"] == "COVERAGE_MANDATORY_CALLOUT"
    assert p["honest_arithmetic"]["needed"] == 6
    conf = p["honest_arithmetic"]["candidates_confidence"]
    assert set(conf) == CANDIDATES
    assert conf["obl_0d6a30948dfd"] == "alta"
    assert conf["obl_015f9b9aaa3a"] == "baja"       # residual probable DECLARADO


def test_probe_accounting_declares_number_four_and_no_fifth():
    acc = _prereg()["probe_accounting"]
    assert acc["probe_number"] == 4
    assert set(acc["prior_probes"]) == {"v1", "v2", "v3"}
    assert "sin probe #5" in acc["anti_overfit"]
    assert "seed nueva" in acc["anti_overfit"]


def test_settled_levers_cited_with_metrics():
    s = _prereg()["settled_levers_touched"]
    assert "36 clean-FP" in s["binding_relaxation"]["settled"]
    assert "14 FP" in s["binding_relaxation"]["settled"]
    assert "DEC-132b" in s["quota_enunciados_bloqueB"]["settled"]
    assert "3/3->0/3" in s["quota_enunciados_bloqueB"]["settled"]
    assert "v8" in s["must_preserve_stage1"]["today"]


def test_phases_gated_budget_within_ceiling_and_db_readonly():
    p = _prereg()
    phases = p["phases"]
    assert [ph["id"] for ph in phases] == ["P0", "P1", "P2", "P3", "P4"]
    total = sum(float(ph["cost_ceiling_usd"]) for ph in phases)
    assert abs(total - float(p["budget"]["phase_ceilings_sum_usd"])) < 1e-9
    assert total <= float(p["budget"]["total_ceiling_usd"]) == 15.00
    assert all(ph["db_writes"] == 0 for ph in phases)
    assert p["budget"]["no_retry"] is True
    p2 = phases[2]
    assert "PAREADA" in p2["procedure"] or "pareada" in p2["procedure"].lower()
    assert "STOP" in p2["stop_rule"]
    assert "union s104+s105" in p2["gates"]["anclas"]


def test_paired_contemporaneous_no_frozen_reference():
    """Lección v3 del Bloque B: los gates de daño son pareados contemporáneos."""
    text = PREREG.read_text(encoding="utf-8")
    assert "CONTEMPORANEOS" in text or "contemporaneo" in text.lower()
    assert "referencia congelada" in text  # declarada como prohibida
