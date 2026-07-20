"""s274 — tests del harness Etapa-1 v9 (P1 del prereg Bloques C/D v2).

Cubren: esquema de gates (heredados v8 ÍNTEGROS + clases nuevas por-fix),
exclusiones acumuladas de TODAS las cohortes previas, evaluadores nuevos sobre
fixtures sintéticas (derivadas de los DIAGNÓSTICOS s274, no de los golds),
independencia del gate por-fix y regla bloque-D. Sin red, sin DB.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


def _module():
    spec = importlib.util.spec_from_file_location(
        "s274_mutation_harness_v9", "scripts/s274_mutation_harness_v9.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = _module()
mp = M.mp

FLAGS = {
    "COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING", "MP_DEFLINE_EQ",
    "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
    "MP_MANDATORY_VERB_TRIGGER",
}


def _row(texto: str, familia: str, atom: dict, fragment_id: str = "frag-1") -> dict:
    return {
        "fragment_id": fragment_id,
        "document_id": "doc-1",
        "source_file": "manual.pdf",
        "familia": familia,
        "texto": texto,
        "atom": atom,
    }


def _detected_atom(texto: str, familia: str) -> dict:
    with M.mp_flags():
        atoms = [a for a in mp.detect_atoms(texto) if a["family"] == familia]
    assert atoms, f"fixture sin átomo {familia}"
    return atoms[0]


# ─────────────────────────── esquema / contrato ───────────────────────────

def test_seed_gates_and_accumulated_exclusions():
    assert M.SEED == 277
    # heredados v8 ÍNTEGROS (mismo dict) + clases nuevas
    for key, value in M.H7.GATES.items():
        assert M.GATES[key] == value, key
    assert set(M.V9_GATES) <= set(M.GATES)
    assert set(M.FIX_CHECKS) == FLAGS
    assert set(M.BLOCK_D_FIXES) == {
        "MP_DEFLINE_EQ", "MP_HYBRID_DETECT", "MP_STEM_BINDING",
        "MP_DISTINCTIVE_TOKEN",
    }
    # TODAS las cohortes previas: v1 + seed-270..276 (8 exclusiones)
    prior = M.prior_cohort_paths()
    assert len(prior) == 8
    labels = [label for label, _p in prior]
    assert labels[0] == "v1_cohort_docs_exclusion"
    assert [l.split("_")[0] for l in labels[1:]] == [
        f"seed{n}" for n in range(270, 277)
    ]
    for _label, path in prior:
        assert Path(path).exists(), path


def test_det_flags_on_config_and_flag_context():
    assert set(M.DET_FLAGS_ON) == {
        "MP_DEFLINE_EQ", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
        "MP_MANDATORY_VERB_TRIGGER",
    }
    import os

    os.environ["MP_DEFLINE_EQ"] = "on"
    try:
        with M.mp_flags("MP_STEM_BINDING"):
            assert os.environ.get("MP_STEM_BINDING") == "on"
            assert "MP_DEFLINE_EQ" not in os.environ  # contexto estricto
        assert os.environ.get("MP_DEFLINE_EQ") == "on"  # restaurado
    finally:
        os.environ.pop("MP_DEFLINE_EQ", None)


# ─────────────────────────── defline_eq (D1a) ───────────────────────────

_BUNDLE_TEXT = (
    "## Opciones de zona\n"
    "**Zona**: número de zona asignada al punto\n"
    "**Retardo**: tiempo de espera antes de la alarma\n"
)


def test_defline_eq_rows_recall_off_control_and_assignment_fp():
    atom = _detected_atom(_BUNDLE_TEXT, mp.FAMILY_BUNDLE)
    row = _row(_BUNDLE_TEXT, mp.FAMILY_BUNDLE, atom)
    results = {r["variant_label"]: r for r in M.evaluate_defline_eq_rows(row)}
    assert results["eq_on"]["detected"] is True
    assert results["eq_off"]["fp_off_detect"] is False  # byte-idéntico off
    assert results["assignment"]["fp_assignment"] is False  # whitelist bloquea


def test_defline_eq_skips_without_pairs():
    atom = {"span_text": "una línea sin definiciones", "meta": {"header": ""}}
    row = _row("texto", mp.FAMILY_BUNDLE, atom)
    results = M.evaluate_defline_eq_rows(row)
    assert len(results) == 1
    assert results[0]["puntuable"] is False
    assert results[0]["skip_reason"] == "no_defline_pairs"


# ─────────────────────────── f_relation (D1b det-side) ───────────────────────────

_REL_TEXT = (
    "## 7.6 Mantenimiento\n"
    "El caudal medido se almacena como valor de referencia de 300 s durante la "
    "puesta en marcha del equipo.\n"
    "La programación de las reglas ofrece un conjunto claro de comportamientos "
    "para los equipos conectados.\n"
    "Instrucción de salida: esta parte de la regla solo puede procesarse cuando "
    "se cumplen todas las condiciones de entrada.\n"
)


def test_f_relation_shape_mechanism_and_controls():
    row = _row(_REL_TEXT, mp.FAMILY_RANGE, {"span_text": "", "meta": {}})
    results = {r["variant_label"]: r for r in M.evaluate_f_relation_rows(row)
               if r.get("variant_label")}
    assert results["shape"]["detected"] is True
    assert results["qualifier_loss"]["detected"] is True
    assert results["definition_loss"]["detected"] is True
    assert results["title"]["fp_title"] is False       # un título jamás pasa
    assert results["prose"]["fp_prose"] is False       # prosa sin ancla jamás
    assert results["off"]["fp_off"] is False           # flag off → familia muerta


def test_f_relation_skip_without_candidates():
    texto = "Línea corta.\nOtra línea sin números ni cláusulas largas."
    row = _row(texto, mp.FAMILY_RANGE, {"span_text": "", "meta": {}})
    results = M.evaluate_f_relation_rows(row)
    assert len(results) == 1
    assert results[0]["skip_reason"] == "no_relation_candidate"


# ─────────────────────────── served_uncited (C2) ───────────────────────────

_RANGE_TEXT = (
    "El retardo de disparo puede ajustarse de 5 a 30 segundos en la posición "
    "A11 del selector de la central.\n"
)


def test_served_uncited_clean_fp_zero_and_positive_cites_f2():
    atom = _detected_atom(_RANGE_TEXT, mp.FAMILY_RANGE)
    row = _row(_RANGE_TEXT, mp.FAMILY_RANGE, atom)
    results = {r["variant_label"]: r for r in M.evaluate_served_uncited_rows(row)}
    assert results["clean"]["fp_clean"] is False   # re-clase seed-270 = 0
    assert results["positive"]["reinforced_exigible"] is True
    assert results["positive"]["detected"] is True  # anexa con cita [F2]


# ─────────────────────────── distinctive (D2) ───────────────────────────

_CBE_TEXT = (
    "## Programmazione\n"
    "**Zona**: campo de zona del punto seleccionado en la central\n"
    "**CBE**: ecuación de control por eventos del punto\n"
)


def test_distinctive_generic_fp_and_acronym_positive():
    atom = _detected_atom(_CBE_TEXT, mp.FAMILY_BUNDLE)
    row = _row(_CBE_TEXT, mp.FAMILY_BUNDLE, atom)
    results = {r["variant_label"]: r for r in M.evaluate_distinctive_rows(row)}
    assert results["generic"]["fp_generic"] is False   # re-clase seed-271 = 0
    assert results["positive"]["detected"] is True     # acrónimo liga con flag
    assert results["off"]["fp_off"] is False           # sin flag no liga


def test_distinctive_skips_other_families():
    atom = _detected_atom(_RANGE_TEXT, mp.FAMILY_RANGE)
    row = _row(_RANGE_TEXT, mp.FAMILY_RANGE, atom)
    assert M.evaluate_distinctive_rows(row) == []


# ─────────────────────────── stem (D1c) ───────────────────────────

_STEM_TEXT = (
    "## Valores nominales\n"
    "**Valores nominales**: referencia del flujo registrado en el reset\n"
    "**Umbral inferior**: límite del flujo permitido por la central\n"
)


def test_stem_positive_single_and_off():
    atom = _detected_atom(_STEM_TEXT, mp.FAMILY_BUNDLE)
    row = _row(_STEM_TEXT, mp.FAMILY_BUNDLE, atom)
    results = {r["variant_label"]: r for r in M.evaluate_stem_rows(row)}
    assert results["positive"]["detected"] is True  # stem paga el 2º token
    assert results["single"]["fp_single"] is False  # seed-271 vía stem = 0
    assert results["off"]["fp_off"] is False        # sin flag, match exacto solo


def test_plural_variant_roundtrip():
    assert M._plural_variant("valores") == "valor"
    assert M._plural_variant("umbral") == "umbrals"
    assert M._plural_variant("lazos") == "lazo"


# ─────────────────────────── verb_trigger (Fable-M1) ───────────────────────────

def test_verb_trigger_on_off_and_noun_fp():
    atom = {
        "span_text": "",
        "anchor_tokens": ["retardo", "disparo", "selector"],
        "meta": {},
    }
    row = _row("texto", mp.FAMILY_MANDATORY, atom)
    results = {r["variant_label"]: r for r in M.evaluate_verb_trigger_rows(row)}
    assert results["on"]["detected"] is True    # 'evite' cuenta como verbo con flag
    assert results["off"]["fp_off"] is False    # sin flag la cláusula no pasa
    assert results["noun"]["fp_noun"] is False  # gatillo-sustantivo jamás


def test_verb_trigger_skips_without_anchor_pair():
    atom = {"span_text": "", "anchor_tokens": ["ab"], "meta": {}}
    row = _row("texto", mp.FAMILY_MANDATORY, atom)
    assert M.evaluate_verb_trigger_rows(row) == []


# ─────────────────────────── callout (C1) ───────────────────────────

_CALLOUT_TEXT = (
    "La programación de reglas define el comportamiento de las salidas del "
    "sistema en la central.\n\n"
    "Texto intermedio del manual sin términos de seguridad en esta sección.\n\n"
    "Al programar las reglas evite las combinaciones contradictorias entre las "
    "salidas del sistema.\n"
)
_CLEAN_TEXT = (
    "La programación de reglas define el comportamiento de las salidas del "
    "sistema en la central.\n\n"
    "Texto intermedio del manual sin términos de seguridad en esta sección.\n\n"
    "El resto del capítulo describe los menús de configuración disponibles.\n"
)


def test_callout_positive_card_valid_and_off_control():
    atom = {"span_text": "", "meta": {}}
    row = _row(_CALLOUT_TEXT, mp.FAMILY_MANDATORY, atom)
    results = {r["variant_label"]: r for r in M.evaluate_callout_rows(row)}
    positive = results["with_triggers"]
    assert positive["puntuable"] is True
    assert positive["detected"] is True
    assert positive["fp_invalid"] is False
    assert results["off"]["fp_off"] is False  # flag off → el campo no existe


def test_callout_clean_chunk_zero_spurious_cards():
    atom = {"span_text": "", "meta": {}}
    row = _row(_CLEAN_TEXT, mp.FAMILY_MANDATORY, atom)
    results = {r["variant_label"]: r for r in M.evaluate_callout_rows(row)}
    assert results["clean"]["fp_spurious"] is False
    assert results["off"]["fp_off"] is False


# ─────────────────────────── gate por-fix ───────────────────────────

def _all_pass_checks() -> dict:
    names = {n for check_names in M.FIX_CHECKS.values() for n in check_names}
    return {name: {"pass": True} for name in names}


def _inherited_pass() -> dict:
    return {name: {"pass": True} for name in M.VT_INHERITED_REFS}


def test_per_fix_verdicts_independent_no_go():
    checks = _all_pass_checks()
    checks["served_uncited_clean_fp"] = {"pass": False}
    fixes = M.per_fix_verdicts(True, _inherited_pass(), checks)
    assert fixes["MP_SERVED_BINDING"]["verdict"] == "NO_GO"
    for fix in FLAGS - {"MP_SERVED_BINDING"}:
        assert fixes[fix]["verdict"] == "GO", fix


def test_inherited_no_go_kills_block_d_only():
    fixes = M.per_fix_verdicts(False, _inherited_pass(), _all_pass_checks())
    for fix in M.BLOCK_D_FIXES:
        assert fixes[fix]["verdict"] == "NO_GO"
        assert fixes[fix]["killed_by_inherited_no_go"] is True
    for fix in ("COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING",
                "MP_MANDATORY_VERB_TRIGGER"):
        assert fixes[fix]["verdict"] == "GO"


def test_verb_trigger_verdict_references_inherited_checks():
    inherited = _inherited_pass()
    inherited["heading_only_fp"] = {"pass": False}
    fixes = M.per_fix_verdicts(True, inherited, _all_pass_checks())
    assert fixes["MP_MANDATORY_VERB_TRIGGER"]["verdict"] == "NO_GO"
    assert fixes["MP_DEFLINE_EQ"]["verdict"] == "GO"


def test_new_fix_checks_computes_from_rows():
    rows = [
        {"measure": "defline_eq", "variant_label": "eq_on", "puntuable": True,
         "detected": True},
        {"measure": "defline_eq", "variant_label": "eq_on", "puntuable": True,
         "detected": False},
        {"measure": "defline_eq", "variant_label": "assignment",
         "puntuable": True, "fp_assignment": True},
        {"measure": "served_uncited", "variant_label": "clean",
         "puntuable": True, "fp_clean": False},
    ]
    checks = M.new_fix_checks(rows, M.GATES)
    assert checks["defline_eq_recall"]["value"] == 0.5
    assert checks["defline_eq_recall"]["pass"] is False
    assert checks["defline_eq_assignment_fp"]["value"] == 1
    assert checks["defline_eq_assignment_fp"]["pass"] is False
    assert checks["served_uncited_clean_fp"]["pass"] is True
    # denominador vacío → pass (mismo patrón d==0 del gate v8)
    assert checks["stem_positive_recall"]["pass"] is True


def test_inherited_checks_ignore_new_measure_rows():
    rows = [
        {"measure": "clean", "puntuable": True, "fp_quality": False,
         "familia": "F-RANGE", "variant": 0},
        {"measure": "served_uncited", "variant_label": "clean",
         "puntuable": False, "skip_reason": "x"},
    ]
    _families, checks, _ok = M.inherited_checks(rows, M.GATES)
    # coverage de instrumento SOLO sobre la suite heredada
    assert checks["coverage"]["value"] == 1.0


# ─────────────────────────── artefactos committeados ───────────────────────────

def test_committed_prereg_and_gate_artifacts():
    prereg = yaml.safe_load(
        Path("evals/s274_stage1_v9_prereg_v1.yaml").read_text(encoding="utf-8")
    )
    assert prereg["schema"] == "s274_stage1_v9_prereg_v1"
    assert prereg["status"] == "FROZEN_BEFORE_RUN"
    assert prereg["seed"] == 277
    assert set(prereg["fix_checks"]) == FLAGS
    for key in M.H7.GATES:  # heredados ÍNTEGROS en el prereg
        assert prereg["gates"][key] == M.H7.GATES[key]
    gate = yaml.safe_load(
        Path("evals/s274_stage1_v9_gate_v1.yaml").read_text(encoding="utf-8")
    )
    assert gate["schema"] == "s274_stage1_v9_gate_v1"
    assert set(gate["verdict_by_fix"]) == FLAGS
    assert set(gate["per_fix"]) == FLAGS
    assert gate["inherited"]["verdict"] in ("GO", "NO_GO")
    assert gate["inherited"]["measured_with_flags_on"] == list(M.DET_FLAGS_ON)
