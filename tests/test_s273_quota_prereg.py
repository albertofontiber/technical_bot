"""s273 — validación de esquema del prereg de la CUOTA del canal enunciados (Bloque B).

El prereg (evals/s273_quota_prereg_v1.yaml) es SOLO diseño pre-registrado: estos tests
validan que el contrato está bien formado y que sus invariantes anti-overfit/anti-gasto
(Q congelado, no-retry, techo $3, escrituras DB solo en F2 gateada, SHAs pineados) están
DECLARADOS antes de que el dúo revise y de que exista una sola línea de build.
No ejecutan ninguna fase, no llaman a ningún modelo, no tocan DB.
"""
import re
from pathlib import Path

import yaml

PREREG_PATH = Path("evals/s273_quota_prereg_v1.yaml")
DESIGN_PATH = Path("evals/s273_quota_design_v1.md")
DIAGNOSIS_PATH = Path("evals/s273_retrieval2_diagnosis_v1.md")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _prereg() -> dict:
    return yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))


def test_files_exist_and_prereg_parses():
    assert DESIGN_PATH.exists(), "el doc de diseño referenciado debe estar versionado"
    assert DIAGNOSIS_PATH.exists(), "el insumo canónico (diagnóstico s272) debe estar versionado"
    p = _prereg()
    assert p["schema"] == "s273_quota_prereg_v1"
    assert p["status"] == "preregistered_not_built"
    assert p["design_doc"] == "evals/s273_quota_design_v1.md"
    assert p["diagnosis_input"] == "evals/s273_retrieval2_diagnosis_v1.md"


def test_protocol4_fork_is_declared_with_discrepancy():
    fork = _prereg()["protocol4_fork"]
    # la visibilidad ES el control: cita del brief + registro del repo + adjudicación
    assert "DEC-103" in fork["settled_cited_by_brief"]
    assert "DEC-102" in fork["settled_in_repo"]
    assert fork["discrepancy_declared_for_adjudication"] is True
    constraints = set(fork["inherited_constraints"])
    assert {"q_frozen_before_f1", "no_tuning_q_against_gold",
            "no_raising_n_dianas", "no_retry"} <= constraints


def test_targets_are_the_two_adjudicated_core_misses():
    targets = {t["qid"]: t for t in _prereg()["targets"]}
    assert set(targets) == {"cat017", "hp010"}
    cat = targets["cat017"]
    assert cat["depends_on_reload"] is True
    cat_chunks = {c["chunk_id"] for c in cat["carrier_chunks"]}
    assert "5bb83899-9d94-4fdd-8d42-24a670a036c5" in cat_chunks   # carrier adjudicado HOP-138-9ES p5
    assert "4c186fb2-aa4b-4ca0-b316-c12ebab59712" in cat_chunks   # 2º carrier 4188-1125-ES p17
    hp = targets["hp010"]
    assert hp["depends_on_reload"] is False                        # su fila ya está VIVA en tabla
    assert hp["carrier_chunks"][0]["chunk_id"] == "155a90fe-8c3f-484e-a617-7637fe29b547"
    row = hp["live_enunciado_row"]
    assert row["rank_among_new_parents"] == 6                      # la justificación de Q=6


def test_mechanics_mirror_hyq_with_frozen_hyperparams():
    m = _prereg()["mechanics"]
    assert m["flag"] == "ENUNCIADOS_QUOTA_FUSION"
    hp = m["hyperparams"]
    # Q=6 = mínimo que admite el rank-6-de-nuevos de hp010 (derivado del diagnóstico, no barrido)
    assert hp["ENUNCIADOS_QUOTA"] == 6
    # barra 0.40 = RELEVANCE_THRESHOLD, constante YA existente — verificada contra el código real
    assert hp["ENUNCIADOS_MIN_SIM"] == 0.40
    gen_src = Path("src/rag/generator.py").read_text(encoding="utf-8")
    assert re.search(r"^RELEVANCE_THRESHOLD\s*=\s*0\.4\b", gen_src, re.M), \
        "la justificación de la barra (RELEVANCE_THRESHOLD=0.4) dejó de ser cierta en el código"
    assert hp["frozen_before_phase"] == "F1"
    unchanged = " ".join(m["unchanged"])
    assert "diversify_interleave_s59" in unchanged                 # contrato: NO se toca
    assert "hyq_channel_mechanics_DEC099" in unchanged
    # la interacción de los dos carve-outs (el punto delicado del build) está declarada
    assert any("reales[:top_k-|E|-|H|]" in s for s in m["steps"])


def test_phases_are_gated_in_order_with_db_write_only_in_f2():
    p = _prereg()
    phases = p["phases"]
    assert [ph["id"] for ph in phases] == ["F0", "F1", "F2", "F3", "F4"]
    by_id = {ph["id"]: ph for ph in phases}
    for pid in ("F0", "F1", "F3", "F4"):
        assert by_id[pid]["db_writes"] == 0, f"{pid} no puede escribir en DB"
    f2 = by_id["F2"]
    assert set(f2["depends_on"]) == {"F0_go", "F1_go"}
    assert set(f2["authorization_required"]) == {"duo_go", "alberto_go"}
    # F1 no depende de F0: hp010 no necesita recarga
    assert by_id["F1"]["depends_on"] == []
    # F0 decide ANTES de recargar y su NO-GO declara residual formal
    assert "residual" in by_id["F0"]["no_go_consequence"].lower()
    # F1: el criterio primario es entrada-al-pool; servido es informativo (rerank no determinista)
    assert "no-retry" in by_id["F1"]["served_check"]
    assert "Q NO se sube" in by_id["F1"]["no_go_consequence"]


def test_inherited_gates_from_dec102_are_present():
    f3 = next(ph for ph in _prereg()["phases"] if ph["id"] == "F3")
    gates = f3["gates"]
    assert set(gates) == {"anclas", "containment", "negcontrol", "famtie"}
    assert "hp005#2" in gates["anclas"] and "hp006#2" in gates["anclas"]
    assert "K=3" in f3["runs"] or "x K=3" in f3["runs"]
    assert "rollback" in f3["no_go_consequence"].lower()


def test_budget_ceiling_and_no_retry():
    p = _prereg()
    assert p["budget"]["total_ceiling_usd"] == 3.00
    assert p["budget"]["no_retry"] is True
    assert p["budget"]["stop_on_ceiling"] is True
    per_phase = sum(ph["cost_ceiling_usd"] for ph in p["phases"])
    assert per_phase <= p["budget"]["total_ceiling_usd"], \
        f"la suma de techos por fase ({per_phase}) excede el techo total"


def test_pins_are_full_shas_and_artifacts_are_frozen():
    inputs = _prereg()["inputs"]
    assert _HEX40.match(inputs["code_pin"]["origin_main_sha"])
    assert inputs["code_pin"]["origin_main_sha"].startswith("5774a6c")
    assert _HEX40.match(inputs["code_pin"]["diagnosis_commit_sha"])
    frozen = inputs["frozen_artifacts"]
    assert set(frozen) == {"phase1_get_out.json", "phase2_trace_out.json",
                           "phase3_probe_out.json", "phase4_probe_out.json",
                           "phase4b_out.json"}
    for name, sha in frozen.items():
        assert _HEX64.match(str(sha)), f"sha256 inválido para {name}"
    assert inputs["sim_tolerance"] == 0.005
    assert inputs["seeds"] == {"sampling_seed": 0, "llm_temperature": 0}
    assert inputs["config_stamp_required"] is True


def test_reload_is_bounded_reversible_and_ledger_pinned():
    r = _prereg()["reload"]
    assert r["scope"] == "max_2_documents"
    assert r["batch"] == "enunciados-v1:T2Q1:h1"
    assert "DELETE por ingest_batch" in r["rollback"]
    docs = {d["key"]: d for d in r["docs"]}
    hop = docs["HOP-138-9ES issue 5_11-2025_In"]
    assert hop["insertables"] == 925 and hop["vintage"] == "h1"
    assert _HEX64.match(hop["ledger_sha"])
    # el sha pineado coincide con el ledger versionado (no se recarga otra cosa)
    ledger = Path("evals/enunciados_ledger.json").read_text(encoding="utf-8")
    assert hop["ledger_sha"] in ledger
    doc4188 = docs["4188-1125-ES issue 5_11-2025_Li"]
    assert doc4188["in_ledger"] is False and doc4188["conditional_on"] == "f0_hop_no_go"
    assert r["resulting_scale_rows_approx"] < 71202                # jamás re-acercarse al NO-GO DEC-102


def test_forbidden_list_covers_the_overfit_and_spend_vectors():
    forbidden = set(_prereg()["forbidden"])
    assert {"tune_Q_or_bar_after_F1_starts", "raise_N_dianas_to_search_gains",
            "author_enunciados_looking_at_golds", "touch_diversify_or_interleave_s59",
            "retry_any_no_go", "db_writes_outside_F2",
            "ship_flag_without_alberto_go"} <= forbidden


def test_design_doc_declares_fork_visibly_in_header():
    text = DESIGN_PATH.read_text(encoding="utf-8")
    header = text[:6000]  # el fork debe estar en cabecera, no enterrado
    assert "fork de Protocolo 4" in header
    assert "DEC-103 (s105)" in header            # la cita del brief, visible
    assert "DEC-102" in header                    # el registro del repo, visible
    assert "71.202" in header
    assert "21.995" in header
    # contrato de Protocolo 2 completo en el doc
    for section in ("Recomendación", "Alternativas", "Gaps / riesgos",
                    "estructural", "escalable"):
        assert section in text, f"sección de Protocolo 2 ausente: {section}"
