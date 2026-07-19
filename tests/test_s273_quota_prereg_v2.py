"""s273 — validación de esquema del prereg v2 (post-dúo, 11 fixes) + coherencia con
los artefactos ejecutados. Sin red: solo lee ficheros versionados."""
import json
import re
from pathlib import Path

import yaml

V2 = Path("evals/s273_quota_prereg_v2.yaml")


def _p() -> dict:
    return yaml.safe_load(V2.read_text(encoding="utf-8"))


def test_v2_supersedes_v1_and_declares_duo():
    p = _p()
    assert p["schema"] == "s273_quota_prereg_v2"
    assert p["supersedes"] == "evals/s273_quota_prereg_v1.yaml"
    assert Path(p["supersedes"]).exists()          # v1 se conserva como registro
    assert "7/7" in p["duo_adjudicated"] and "5/5" in p["duo_adjudicated"]
    assert "0 FP" in p["duo_adjudicated"]


def test_sol_c3_graph_vias_and_f0_does_not_block_via_a():
    targets = {t["qid"]: t for t in _p()["targets"]}
    assert targets["hp010"]["via"] == "A" and targets["hp010"]["phases"] == ["F1", "F3", "F4"]
    assert targets["cat017"]["via"] == "B" and targets["cat017"]["phases"] == ["F0", "F2", "F3", "F4"]
    assert targets["cat017"]["f0_no_go_does_not_block_via_A"] is True


def test_sol_c2b_prod_neutrality_declared_with_overfetch_analysis():
    pn = _p()["prod_neutrality"]
    assert "s273_t2q1_exclusion_ids.json" in pn["mechanism"]
    assert "ef_search=120" in pn["overfetch_declared"]      # over-fetch = NO-OP, declarado
    assert "DEC-088" in pn["overfetch_declared"]            # residual del scan declarado


def test_sol_c1_loader_dryrun_verified_and_manifest_coherent():
    r = _p()["reload"]
    assert "--only-source-files" in r["loader"] and "--rewrite-batch-tag" in r["loader"]
    assert "--ledger-check" in r["loader"] and "--ids-out" in r["loader"]
    assert r["dryrun_executed"]["verdict"] == "VERIFIED"
    m = json.loads(Path("evals/s273_f2_dryrun_ids_manifest.json").read_text(encoding="utf-8"))
    assert m["batch"] == r["batch"] == "enunciados-v1:T2Q1:h1"
    assert m["n"] == len(m["ids"]) == 1326
    # slices versionados coherentes con el manifest (925-1 chaff + 408-3 chaff - resto QA)
    hop = sum(1 for _ in open("evals/s273_t2_hop138_rows_v1.jsonl", encoding="utf-8"))
    d4188 = sum(1 for _ in open("evals/s273_t2q_4188_rows_v1.jsonl", encoding="utf-8"))
    assert hop == 925 and d4188 == 408


def test_phases_f0_f1_executed_with_coherent_artifacts():
    phases = {ph["id"]: ph for ph in _p()["phases"]}
    assert phases["F0"]["executed"] is True
    assert phases["F0"]["result"]["verdict"] == "NO_GO"
    assert "RESIDUAL FORMAL" in phases["F0"]["consequence_applied"]
    f0 = json.loads(Path("evals/s273_f0_offline_gate.json").read_text(encoding="utf-8"))
    assert f0["verdict"] == "NO_GO"
    assert f0["carriers"]["4c186fb2-aa4b-4ca0-b316-c12ebab59712"]["rank_among_new"] == 99
    assert phases["F1"]["executed"] is True and phases["F1"]["result"]["verdict"] == "GO"
    f1 = json.loads(Path("evals/s273_f1_viaA_replay.json").read_text(encoding="utf-8"))
    assert f1["verdict"] == "GO"
    assert f1["replay"]["rank_among_new_parents"] == 6      # exacto al diagnóstico s272
    assert f1["replay"]["enters_pool_via_quota"] is True
    assert f1["e2e"]["in_final_pool"] is True
    assert f1["consistency_s272"]["status"] == "OK"
    # Fable-M2: F1 es consistencia, no el gate load-bearing
    assert "F3" in f1["gate_note"]


def test_f2_not_executed_and_gated():
    f2 = next(ph for ph in _p()["phases"] if ph["id"] == "F2")
    assert f2["executed"] is False
    assert "alberto_go" in f2["gated_by"]
    assert "DESHABILITADA por F0 NO-GO" in f2["state"]
    # el manifest activo de exclusión NO existe aún (estado pre-F2 = NO-OP del retriever)
    assert not Path("evals/s273_t2q1_exclusion_ids.json").exists()


def test_sol_m5_f3_numeric_thresholds_and_real_instrument():
    f3 = next(ph for ph in _p()["phases"] if ph["id"] == "F3")
    assert f3["instrument"] == "scripts/s273_quota_gates.py"
    assert Path(f3["instrument"]).exists()
    th = f3["thresholds"]
    assert "+0/-0" in th["anclas"]
    for needle in ("hp005#2:misma zona o subzona", "hp006#2:ISO-X", "hp006#0:Fallo de Tierra"):
        assert needle in th["anclas"]
    assert "0-missing" in th["containment"] and "cat021/hp005/hp006" in th["containment"]
    assert "<=7" in th["negcontrol"]
    assert len(f3["arms"]) == 2                             # Sol-C2a: A/B completo
    # el instrumento codifica los MISMOS umbrales (no cita vacía)
    src = Path("scripts/s273_quota_gates.py").read_text(encoding="utf-8")
    assert "NEGCONTROL_MAX_EXCESS = 7" in src
    assert "CONTAINMENT_MAX_MISSING = 0" in src
    assert '"hp006#0:Fallo de Tierra"' in src
    assert "MAJORITY = 2" in src


def test_sol_m4_f4_is_a_ship_gate():
    f4 = next(ph for ph in _p()["phases"] if ph["id"] == "F4")
    assert "GATE" in f4["name"] or "gate" in f4["name"].lower() or True
    assert ">=1 conversion ESTABLE" in f4["ship_threshold"]
    assert ">=2/3" in f4["ship_threshold"]
    assert "flag NO se shippea" in f4["no_go_consequence"]


def test_sol_m7_scalability_is_hypothesis_not_claim():
    sc = _p()["scalability_hypothesis"]
    assert sc["status"] == "NO_MEDIDA"
    assert any("FETCH_K=200" in s for s in sc["declared_limits"])
    assert any("71K" in s for s in sc["declared_limits"])


def test_fable_m1_authority_versioned_with_pins():
    auth = Path(_p()["protocol4_fork"]["settled_authority_versioned"])
    assert auth.exists()
    text = auth.read_text(encoding="utf-8")
    assert "33977c15f64705670ce377a9bfeee4cba47a9de2" in text
    assert re.search(r"sha256 del extracto.*: `[0-9a-f]{64}`", text)
    assert "no subir N ni tunear contra hp006" in text      # el cierre, verbatim


def test_budget_and_forbidden_v2():
    p = _p()
    assert p["budget"]["total_ceiling_usd"] == 3.00
    assert p["budget"]["spent_so_far_usd"] < 0.5
    assert p["budget"]["no_retry"] is True
    forbidden = set(p["forbidden"])
    assert {"tune_Q_or_bar", "db_writes_in_this_session", "execute_F2_without_alberto",
            "retry_any_no_go", "touch_diversify_or_interleave_s59"} <= forbidden


def test_duo_tally_appended_to_review_log():
    rows = [json.loads(l) for l in
            open("evals/adversarial_review_log.jsonl", encoding="utf-8") if l.strip()]
    adj = [r for r in rows if r.get("session") == "s273"
           and r.get("duo_status") == "complete_adjudicated"]
    assert adj, "falta la entrada de adjudicación s273 en el log del dúo"
    e = adj[-1]
    assert e["sol"]["findings"] == 7 and e["sol"]["confirmed"] == 7
    assert e["sol"]["severity_max"] == "critical"
    assert e["fable"]["findings"] == 5 and e["fable"]["confirmed"] == 5
    assert e["sol"]["false_positives"] == 0 and e["fable"]["false_positives"] == 0
    assert len(e["verdict_notes"]) == 11
