"""s274 — tests del runner P2 (probe consolidado C+D con brazos de ablación).

Cubren: brazos EXACTOS vs el prereg v2, gating P1 por-fix (skip / retirada de
flag), checkpoint por brazo×gold×réplica, monotonía + 0-diagramas-por-anexo,
agregación pareada vs A0 (conversiones, protegidas, conflictos, anclas con STOP
duro s104+s105) y preflight de coste por brazo bajo el techo $6. Sin red, sin DB.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


def _module():
    spec = importlib.util.spec_from_file_location(
        "s274_probe_ablation", "scripts/s274_probe_ablation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = _module()

PREREG = yaml.safe_load(
    Path("evals/s274_bloquesCD_prereg_v2.yaml").read_text(encoding="utf-8")
)
P2 = next(ph for ph in PREREG["phases"] if ph["id"] == "P2")


# ─────────────────────────── brazos vs prereg ───────────────────────────

def test_arms_match_prereg_exactly():
    assert set(M.ARMS) == set(P2["arms"])
    assert list(M.ARM_ORDER) == [
        "A0", "A-C1", "A-C2", "A-D1a", "A-D1b-det", "A-D1b-hyb", "A-D1c",
        "A-D2", "A-ALL-det", "A-ALL",
    ]
    assert M.COST_CEILING_USD == float(P2["cost_ceiling_usd"]) == 6.00


def test_arm_flag_sets():
    assert M.ARMS["A0"]["flags"] == ()
    assert set(M.ARMS["A-C1"]["flags"]) == {
        "COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER",
    }  # PAR DECLARADO (Fable-M1)
    assert M.ARMS["A-C2"]["flags"] == ("MP_SERVED_BINDING",)
    assert M.ARMS["A-D1a"]["flags"] == ("MP_DEFLINE_EQ",)
    assert M.ARMS["A-D1b-det"]["alias_of"] == "A0"
    assert M.ARMS["A-D1b-hyb"]["flags"] == ("MP_HYBRID_DETECT",)
    assert M.ARMS["A-D1c"]["flags"] == ("MP_STEM_BINDING",)
    assert M.ARMS["A-D2"]["flags"] == ("MP_DISTINCTIVE_TOKEN",)
    assert set(M.ARMS["A-ALL-det"]["flags"]) == set(M.ALL_FLAGS) - {
        "MP_HYBRID_DETECT"
    }  # lo shippeable sin Haiku
    assert set(M.ARMS["A-ALL"]["flags"]) == set(M.ALL_FLAGS)
    # hp017 fresco SOLO en A0/A-C1; A-ALL* reusa A-C1 (prereg v2.3)
    assert M.ARMS["A0"]["fresh"] == ("hp017",)
    assert M.ARMS["A-C1"]["fresh"] == ("hp017",)
    assert M.ARMS["A-ALL-det"]["reuse_fresh_from"] == "A-C1"
    assert M.ARMS["A-ALL"]["reuse_fresh_from"] == "A-C1"
    # el presupuesto Haiku de prod excluye hp011 (prereg: cat018/hp002/hp017)
    assert set(M.HYBRID_QIDS) == {"cat018", "hp002", "hp017"}


def test_candidates_match_prereg_confidence_table():
    declared = set(PREREG["honest_arithmetic"]["candidates_confidence"])
    assert {oblid for oblid, _q, _c in M.CANDIDATES} == declared
    checks = {oblid: check for oblid, _q, check in M.CANDIDATES}
    assert checks["obl_0d6a30948dfd"] == "merged_warning_block"


def test_generation_env_pins_visual_assets_off_and_contract_off():
    assert M.GENERATION_ENV["VISUAL_ASSETS_REGISTRY"] == "off"
    assert M.GENERATION_ENV["MUST_PRESERVE_CONTRACT"] == "off"


# ─────────────────────────── gating P1 por-fix ───────────────────────────

def _verdicts(**overrides: str) -> dict[str, str]:
    verdicts = {flag: "GO" for flag in M.ALL_FLAGS}
    verdicts.update(overrides)
    return verdicts


def test_p1_no_go_skips_single_fix_arm_and_strips_flag_from_all():
    verdicts = _verdicts(MP_SERVED_BINDING="NO_GO")
    assert M.arm_skipped_by_p1("A-C2", verdicts) is True
    assert M.arm_skipped_by_p1("A-D1a", verdicts) is False
    assert M.arm_skipped_by_p1("A-D1b-det", verdicts) is False  # alias jamás
    assert "MP_SERVED_BINDING" not in M.arm_effective_flags("A-ALL", verdicts)
    assert "MP_SERVED_BINDING" not in M.arm_effective_flags("A-ALL-det", verdicts)
    assert "MP_DEFLINE_EQ" in M.arm_effective_flags("A-ALL-det", verdicts)


def test_p1_pair_c1_dies_together():
    verdicts = _verdicts(MP_MANDATORY_VERB_TRIGGER="NO_GO")
    assert M.arm_skipped_by_p1("A-C1", verdicts) is True  # el PAR exige ambos


def test_p1_missing_gate_means_no_skip_in_preflight():
    assert M.arm_skipped_by_p1("A-C2", None) is False
    assert M.arm_effective_flags("A-ALL", None) == M.ARMS["A-ALL"]["flags"]


# ─────────────────────────── checkpoint / monotonía ───────────────────────────

def test_checkpoint_key_roundtrip():
    assert M.checkpoint_key("A-C1", "hp017", 2) == "A-C1|hp017|r2"


def test_appended_tail_and_no_new_diagrams():
    off = "Respuesta base [F1].\n"
    on = "Respuesta base [F1].\n\n---\n⚠️ **Información adicional del manual:**"
    assert M.appended_tail(off, on).startswith("\n\n---")
    M.assert_no_new_diagrams(off, on)  # no levanta
    with pytest.raises(RuntimeError, match="monoton"):
        M.appended_tail("Respuesta base [F1].", "Otra respuesta")
    with pytest.raises(RuntimeError, match="diagramas"):
        M.assert_no_new_diagrams(off, off + "\nDIAGRAMAS_RELEVANTES: [1]")


def test_anchor_norm_nfkd_fold():
    assert M.anchor_norm("Instrucción   de\nENTRADA") == "instruccion de entrada"
    assert M.anchors_in_answer(
        "Cubre la Instrucción de entrada del panel",
        {"hp017#1": "instruccion de entrada", "hp017#2": "editar configuracion"},
    ) == {"hp017#1": True, "hp017#2": False}


# ─────────────────────────── agregación pareada vs A0 ───────────────────────────

_PROT = sorted(M.PROTECTED_IDS)


def _items() -> dict:
    def obligations(qid: str, ids: list[str]) -> dict:
        return {
            "qid": qid,
            "obligations": [{"obligation_id": o} for o in ids],
            "conflicts": (
                [{"conflict_id": "conf_1"}] if qid == "hp002" else []
            ),
        }

    return {
        "cat018": obligations("cat018", ["obl_7bba8d03d496", "obl_015f9b9aaa3a"]),
        "hp002": obligations("hp002", ["obl_a5d9fa1f9253", _PROT[0]]),
        "hp011": obligations("hp011", ["obl_2f5d79e354b9", _PROT[1]]),
        "hp017": obligations(
            "hp017", ["obl_b2043cd4379b", "obl_7aa723717412", _PROT[2]]
        ),
    }


def _score(covered: list[str], unsafe: list[str] | None = None,
           merged: bool = False) -> dict:
    return {
        "covered_obligation_ids": covered,
        "unsafe_conflict_ids": unsafe or [],
        "merged_warning_block_covered": merged,
    }


def _rows_for_arm(arm: str, covered_by_qid: dict[str, list[str]],
                  answer_by_qid: dict[str, str] | None = None,
                  unsafe_by_qid: dict[str, list[str]] | None = None) -> list[dict]:
    rows = []
    protected_map = {"hp002": _PROT[0], "hp011": _PROT[1], "hp017": _PROT[2]}
    for qid in M.QIDS:
        covered = list(covered_by_qid.get(qid, []))
        if qid in protected_map and protected_map[qid] not in covered:
            covered.append(protected_map[qid])
        for rep in M.REPLICATES:
            rows.append({
                "arm": arm, "qid": qid, "replicate": rep,
                "draft_source": "stored_v3", "flags": [],
                "off_answer": "x", "cost_usd": 0.0,
                "on_answer": (answer_by_qid or {}).get(qid, "respuesta neutra"),
                "on_score": _score(
                    covered, (unsafe_by_qid or {}).get(qid),
                ),
                "off_score": _score([]),
            })
    return rows


_ANCHORS = {
    "cat018": {}, "hp002": {}, "hp017": {},
    "hp011": {"hp011#0:ABORT": "abort"},
}


def test_aggregate_detects_stable_conversion_vs_a0():
    scored = (
        _rows_for_arm("A0", {}, answer_by_qid={"hp011": "sin ancla aqui"})
        + _rows_for_arm(
            "A-C2", {"hp011": ["obl_2f5d79e354b9"]},
            answer_by_qid={"hp011": "incluye ABORT y la conversión"},
        )
    )
    out = M.aggregate(scored, _items(), _ANCHORS, None, 0.0)
    arm = out["per_arm"]["A-C2"]
    assert arm["stable_conversions"] == ["obl_2f5d79e354b9"]
    assert arm["damage_gates"]["pass"] is True
    # ganancia de ancla del anexo: REPORTADA informativa, jamás daño
    assert arm["anchors"]["gained_reported_informative"] == ["hp011#0:ABORT"]
    assert arm["anchors"]["lost"] == []
    assert out["per_arm"]["A-D1b-det"]["status"] == "alias_of_A0"
    assert out["per_arm"]["A-ALL"]["status"] == "skipped"
    assert out["banking"]["det_only_bankable"] == []


def test_aggregate_flags_protected_fall_and_anchor_loss_as_stop():
    a0 = _rows_for_arm("A0", {}, answer_by_qid={"hp011": "incluye ABORT"})
    arm_rows = _rows_for_arm("A-C2", {}, answer_by_qid={"hp011": "sin ancla"})
    for row in arm_rows:  # la protegida de hp011 cae en el brazo
        if row["qid"] == "hp011":
            row["on_score"]["covered_obligation_ids"] = []
    out = M.aggregate(a0 + arm_rows, _items(), _ANCHORS, None, 0.0)
    arm = out["per_arm"]["A-C2"]
    assert arm["protected_fallen"] == [_PROT[1]]
    assert arm["anchors"]["lost"] == ["hp011#0:ABORT"]
    assert arm["damage_gates"]["pass"] is False
    assert out["stop_rule_hits"] == [
        {"arm": "A-C2", "fixes_closed": ["MP_SERVED_BINDING"]}
    ]


def test_aggregate_new_stable_conflict_is_damage():
    a0 = _rows_for_arm("A0", {})
    arm_rows = _rows_for_arm(
        "A-D1a", {}, unsafe_by_qid={"hp002": ["conf_1"]}
    )
    out = M.aggregate(a0 + arm_rows, _items(), _ANCHORS, None, 0.0)
    arm = out["per_arm"]["A-D1a"]
    assert arm["new_stable_conflicts"] == ["conf_1"]
    assert arm["damage_gates"]["pass"] is False


def test_aggregate_requires_a0_base():
    with pytest.raises(RuntimeError, match="A0"):
        M.aggregate(_rows_for_arm("A-C2", {}), _items(), _ANCHORS, None, 0.0)


def test_stop_anchor_union_is_declared():
    assert set(M.STOP_ANCHOR_KEYS) == {
        "hp005#2:misma zona o subzona", "hp006#2:ISO-X", "hp006#0:Fallo de Tierra",
    }


# ─────────────────────────── retrieval invariante (A-C1) ───────────────────────────

def test_retrieval_invariant_allows_only_callout_field():
    base_chunks = [{"id": "c1", "content": "abc"}, {"id": "c2", "content": "def"}]
    same = [dict(c) for c in base_chunks]
    same[0]["mandatory_callout_cards"] = [{"start": 0, "end": 1}]
    ok = M.retrieval_invariant_report(base_chunks, same)
    assert ok["pass"] is True and ok["extra_fields"] == ["mandatory_callout_cards"]
    reordered = [base_chunks[1], base_chunks[0]]
    assert M.retrieval_invariant_report(base_chunks, reordered)["pass"] is False
    mutated = [dict(c) for c in base_chunks]
    mutated[1]["content"] = "otro"
    assert M.retrieval_invariant_report(base_chunks, mutated)["pass"] is False


# ─────────────────────────── preflight de coste ───────────────────────────

def test_per_arm_cost_estimate_under_ceiling(monkeypatch):
    monkeypatch.setattr(M, "estimate_fresh_cost", lambda rows, qid: 0.09)
    est = M.per_arm_cost_estimate({})
    assert set(est["per_arm"]) == set(M.ARMS)
    assert est["per_arm"]["A0"]["paid_calls"] == 3
    assert est["per_arm"]["A-C1"]["paid_calls"] == 3
    for arm in ("A-C2", "A-D1a", "A-D1c", "A-D2", "A-ALL-det", "A-D1b-det"):
        assert est["per_arm"][arm]["est_usd"] == 0.0
    # ≤2 llamadas Haiku/respuesta × 3 qids × 3 réplicas por brazo híbrido
    assert est["per_arm"]["A-D1b-hyb"]["haiku_calls_max"] == 18
    assert est["per_arm"]["A-ALL"]["haiku_calls_max"] == 18
    assert est["total_usd"] <= M.COST_CEILING_USD == est["ceiling_usd"]


def test_hybrid_cost_usd_prices():
    cost = M.hybrid_cost_usd({"input_tokens": 1_000_000, "output_tokens": 0})
    assert cost == 1.0  # Haiku 4.5 in
    assert M.hybrid_cost_usd({"output_tokens": 1_000_000}) == 5.0
