"""s274 — validación de esquema del prereg Bloques C/D v2 (post-dúo) + coherencia con
los diagnósticos committeados. v1 se conserva como registro pre-dúo (solo existencia:
sus SHA-pins describen el árbol ANTERIOR al build P0, por diseño). Sin red, sin DB."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

PREREG_V1 = Path("evals/s274_bloquesCD_prereg_v1.yaml")
PREREG = Path("evals/s274_bloquesCD_prereg_v2.yaml")
DESIGN = Path("evals/s274_bloquesCD_design_v1.md")
DIAG_C1 = Path("evals/s274_serving_view_diag_v1.json")
DIAG_D1_V2 = Path("evals/s274_hybrid_funnel_diag_v2.json")

CANDIDATES = {
    "obl_0d6a30948dfd", "obl_7bba8d03d496", "obl_2f5d79e354b9",
    "obl_a5d9fa1f9253", "obl_b2043cd4379b", "obl_7aa723717412",
    "obl_015f9b9aaa3a",
}
FLAGS = {
    "COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING", "MP_DEFLINE_EQ",
    "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
    "MP_MANDATORY_VERB_TRIGGER",
}


def _prereg() -> dict:
    return yaml.safe_load(PREREG.read_text(encoding="utf-8"))


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def test_schema_supersedes_v1_and_declares_duo():
    p = _prereg()
    assert p["schema"] == "s274_bloquesCD_prereg_v2"
    assert p["supersedes"] == "evals/s274_bloquesCD_prereg_v1.yaml"
    assert PREREG_V1.exists()  # v1 se conserva como registro
    assert p["status"] == "preregistered_p0_built_flagoff"
    duo = p["duo_adjudicated"]
    assert "7" in duo["sol"] and "2 criticos" in duo["sol"] and "0 FP" in duo["sol"]
    assert "5" in duo["fable"] and "0 FP" in duo["fable"]
    assert duo["severity_max"] == "critical"
    assert Path(p["design_doc"]) == DESIGN and DESIGN.exists()
    assert "PARTE 2" in DESIGN.read_text(encoding="utf-8")


def test_sha_pins_match_working_tree():
    pins = _prereg()["frozen_inputs_sha256_lf"]
    assert len(pins) == 11
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
    frag = diag["fragment"]
    assert frag["raw_chars"] == 2864 and frag["served_chars"] == 1037
    assert frag["coverage_cards_spans"] == [[675, 1032], [419, 673], [1694, 2052]]


def test_d1_funnel_n3_stable_and_overage_declared():
    diag = json.loads(DIAG_D1_V2.read_text(encoding="utf-8"))
    assert diag["schema"] == "s274_hybrid_funnel_diag_v2"
    assert diag["mode"] == "execute"
    assert diag["design"]["replicate_ids"] == [1, 2, 3]  # Fable-M3: N=3, no N=1
    fates = [p.get("fate") for p in diag["proposals"]]
    assert len(fates) == 248
    assert fates.count("rejected_shape") == 195           # dominante y estable
    s = diag["target_summary"]["obl_015f9b9aaa3a"]
    assert s["proposal_fates"] == ["rejected_shape"]
    assert all(
        s["by_replicate"][f"r{r}"]["proposals"] == 2 for r in (1, 2, 3)
    )  # propuesto 2x/replica, muerto en shape 6/6
    # sobrecoste declarado en el prereg (autorizacion 0.25, real 0.2650)
    assert diag["actual_cost_usd"] == 0.265044
    assert "0.015" in _prereg()["diagnostics_basis"]["d1_hybrid_funnel_n3"][
        "cost_overage_declared"
    ]


def test_flags_inventory_and_candidate_coverage():
    p = _prereg()
    assert set(p["flags"]) == FLAGS
    conf = p["honest_arithmetic"]["candidates_confidence"]
    assert set(conf) == CANDIDATES
    # Fable-M1: 0d6a condicionada al PAR card+verb-trigger, declarado
    assert "CONDICIONADA" in conf["obl_0d6a30948dfd"]
    # correccion v2.2: b2043 ya no se declara co-beneficiado por C1
    assert "BAJA" in conf["obl_b2043cd4379b"]
    assert "NO cubre su span" in conf["obl_b2043cd4379b"]
    assert "NO se alcanza" in p["honest_arithmetic"]["statement"]


def test_probe_arms_ablation_and_deployable_banking():
    p2 = next(ph for ph in _prereg()["phases"] if ph["id"] == "P2")
    arms = p2["arms"]
    assert {"A0", "A-C1", "A-C2", "A-D1a", "A-D1b-hyb", "A-D1c", "A-D2",
            "A-ALL-det", "A-ALL"} <= set(arms)
    assert "PAR DECLARADO" in arms["A-C1"]                 # card+verb-trigger juntos
    assert "desplegable" in p2["banking_rule"].lower()     # Sol-C1
    assert "VISUAL_ASSETS_REGISTRY=off" in p2["gates"]["diagrams"]   # Sol-M5
    assert "identicos OFF/ON" in p2["gates"]["retrieval_invariante"]
    assert "union s104+s105" in p2["gates"]["anclas"]
    assert "STOP" in p2["stop_rule"]


def test_settled_levers_include_c2_seed270_mapping():
    s = _prereg()["settled_levers_touched"]
    assert "36 clean-FP" in s["binding_relaxation"]["settled"]
    c2 = s["served_binding_c2_vs_seed270"]                 # Fable-M2
    assert "36/158" in c2["settled"]
    assert ">=3" in c2["today"] and "served_not_cited" in c2["today"]
    assert "DEC-132b" in s["quota_enunciados_bloqueB"]["settled"]


def test_d2_catalog_anchor_is_file_line_specific():
    notes = _prereg()["build_notes"]["d2_catalog_anchor"]
    assert "scripts/catalog_store.py" in notes
    assert "l.79-81" in notes and "l.94" in notes
    assert "catalog_resolver.py" in notes
    # el ancla describe el codigo real
    store = Path("scripts/catalog_store.py").read_text(encoding="utf-8")
    assert "_by_canonical" in store and "_by_alias" in store


def test_phases_p0_done_and_budget_within_ceiling():
    p = _prereg()
    phases = {ph["id"]: ph for ph in p["phases"]}
    assert phases["P0"]["status"] == "DONE_THIS_SESSION"
    assert phases["P0"]["cost_usd_actual"] == 0.2650
    ceilings = sum(
        float(ph.get("cost_ceiling_usd", 0.0)) for ph in p["phases"]
    )
    assert abs(ceilings - float(p["budget"]["phase_ceilings_sum_usd"])) < 1e-9
    assert ceilings + p["budget"]["spent_p0_usd"] <= float(p["budget"]["total_ceiling_usd"])
    assert all(ph["db_writes"] == 0 for ph in p["phases"])
    assert p["budget"]["no_retry"] is True


def test_probe_accounting_number_four_no_fifth_and_paired_contemporaneous():
    acc = _prereg()["probe_accounting"]
    assert acc["probe_number"] == 4
    assert "sin probe #5" in acc["anti_overfit"]
    assert "CONTEMPORANEOS" in acc["anti_overfit"]
    text = PREREG.read_text(encoding="utf-8")
    assert "referencia congelada" in text                  # leccion v3 Bloque B
