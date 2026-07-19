#!/usr/bin/env python3
"""S270 Etapa 1 v5 — harness de mutaciones para el MECANISMO v2 (DEC-126; sucesor de
s269_mutation_harness seed-272).

Extiende el harness s269 (que se importa y reusa: builders v1, templates, mutadores,
evaluadores) con los TIPOS NUEVOS del mecanismo v2, todos derivados del funnel del
probe-1 (jamás de los textos gold):

  display_token      átomo con riesgo 7-seg: el borrador CONTIENE el token display
                     (paridad) → debe anexar; borrador SIN el token → 0 anexos
                     (no se añade superficie OCR nueva).
  cross_count        par conteo↔enumeración partido en 2 fragmentos sintéticos del
                     mismo doc/página (split mecánico del fragmento real por el
                     inicio de su enumeración) → átomo cross con cita doble.
  composite (híbrido) SOLO en el brazo --hybrid (preflight por defecto; el brazo
                     determinista $0 lo declara fuera).

Población FRESCA seed=273 con exclusiones ACUMULADAS (cohortes v1 + seed-270 +
seed-271 + seed-272). Gates heredados del prereg v3 + clean-noise re-specced a la
opción (a) de DEC-126: el anexo hermano etiquetado es ENRIQUECIMIENTO permitido; FP
solo si viola CALIDAD del anexo — span no-verbatim del fragmento, cap global/familia
violado, o MANDATORY duplicado/no-procedimental.

Uso:
  python scripts/s270_mutation_harness_v5.py --build-cohort   # GET-only, $0
  python scripts/s270_mutation_harness_v5.py --freeze         # prereg v4
  python scripts/s270_mutation_harness_v5.py --run            # brazo det ($0)
  python scripts/s270_mutation_harness_v5.py --gate           # veredicto
  python scripts/s270_mutation_harness_v5.py --run --hybrid   # preflight (0 pagos)
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import random
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag import must_preserve as mp  # noqa: E402


def _load_s269():
    spec = importlib.util.spec_from_file_location(
        "s269_mutation_harness", ROOT / "scripts/s269_mutation_harness.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = _load_s269()

EVALS = ROOT / "evals"
COHORT_PATH = EVALS / "s270_mutation_cohort_v5.jsonl"
BUILD_REPORT_PATH = EVALS / "s270_mutation_cohort_v5_build.json"
PREREG_PATH = EVALS / "s270_stage1_v5_prereg_v1.yaml"
RESULTS_DET_PATH = EVALS / "s270_stage1_v5_results_det_c273.jsonl"
RESULTS_HYBRID_PATH = EVALS / "s270_stage1_v5_results_hybrid_c273.jsonl"
GATE_OUT_PATH = EVALS / "s270_stage1_v5_gate_v1.yaml"

SEED = 273
# gates heredados del prereg v3 (s269_stage1_v3_prereg_v3.yaml) + tipos nuevos
GATES = {
    "mutation_recall_min_per_family": 0.80,
    "display_recall_min": 0.80,
    "display_no_new_surface_fp_max": 0,
    "cross_count_recall_min": 0.80,
    "clean_annex_quality_fp_max": 0,   # re-spec opción-a (DEC-126)
    "cross_binding_fp_max": 0,
    "attestation_block_appends_max": 0,
    "coverage_min": 0.90,
}

TEMPLATES_V5_EXTRA = {
    "display_hook": "El display de la central muestra {token} durante la operación.",
    "cross_count_claim": "el equipo declara {declared} {noun} en su documentación",
}


def run_mechanism_v2(atoms, draft, cited, fragment_number):
    """run_mechanism con la firma v2 de selección (draft en _select_for_appendix)."""
    atoms = [copy.deepcopy(a) for a in atoms]
    bound = mp.bind_atoms(atoms, draft, cited, fragment_number)
    missing = []
    for atom in bound:
        if not mp.atom_satisfied(atom, draft):
            atom.setdefault("meta", {})["fragment_number"] = fragment_number
            missing.append(atom)
    appendix = mp.render_appendix(missing, draft)
    appended = mp._select_for_appendix(missing, draft) if appendix else []
    return appendix, appended


H.run_mechanism = run_mechanism_v2  # el harness s269 usa la selección v2


# ─────────────────────────── build cohorte v5 (seed 273) ───────────────────────────

def build_cohort() -> int:
    import os

    import httpx

    v1 = H._load_v1_builder()
    rng = random.Random(SEED)
    table = os.environ.get("CHUNKS_TABLE", "chunks_v2")

    prior = []
    for label, path in (
        ("v1_cohort_docs_exclusion", H.COHORT_V1_PATH),
        ("seed270_cohort_docs_exclusion", H.COHORT_SEED270_PATH),
        ("seed271_cohort_docs_exclusion", H.COHORT_SEED271_PATH),
        ("seed272_cohort_docs_exclusion", H.COHORT_PATH),  # cohorte v4 (seed-272)
    ):
        docs = sorted({r["document_id"] for r in H.load_jsonl(path)})
        if not docs:
            raise RuntimeError(f"cohorte previa vacía/ausente: {path.name}")
        prior.append((label, path, docs))

    with httpx.Client(timeout=30.0) as client:
        print("Inventario del corpus (GET paginado)...")
        corpus = v1.fetch_corpus_docs(client, table)
        print(f"  docs servibles: {len(corpus)}")
        excluded, manifest = v1.build_exclusions(corpus)
        for label, path, docs in prior:
            extra = {d for d in docs if d in corpus and d not in excluded}
            excluded |= set(docs)
            manifest.append({
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "method": label,
                "sha256": H.sha256_file(path),
                "corpus_docs_matched": len([d for d in docs if d in corpus]),
                "docs_not_already_excluded": len(extra),
            })
        eligible = {d: r for d, r in corpus.items() if d not in excluded}
        print(f"  excluidos: {len(excluded & set(corpus))} | elegibles: {len(eligible)}")

        doc_order = v1.stratified_doc_order(eligible, rng)
        pools = {f: [] for f in H.FAMILIES}
        per_doc_family: dict[tuple[str, str], int] = {}
        docs_used: list[str] = []
        fragments_screened = 0
        pages_by_fragment: dict[str, object] = {}

        def buckets_full() -> bool:
            return all(len(pools[f]) >= H.TARGET_PER_FAMILY for f in H.FAMILIES)

        for did in doc_order:
            if len(docs_used) >= H.MAX_DOCS or (
                len(docs_used) >= H.TARGET_DOCS and buckets_full()
            ):
                break
            fragments = v1.fetch_doc_fragments(client, table, did)
            if not fragments:
                continue
            docs_used.append(did)
            for frag in fragments:
                fragments_screened += 1
                atoms = mp.detect_atoms(frag["content"])
                fired = sorted({a["family"] for a in atoms})
                if not fired:
                    continue
                for fam in fired:
                    key = (did, fam)
                    if per_doc_family.get(key, 0) >= H.PER_DOC_FAMILY_CAP:
                        continue
                    target = next(a for a in atoms if a["family"] == fam)
                    per_doc_family[key] = per_doc_family.get(key, 0) + 1
                    pools[fam].append({
                        "fragment_id": frag["id"],
                        "document_id": did,
                        "source_file": frag.get("source_file") or "",
                        "fabricante": eligible[did]["manufacturer"],
                        "familia": fam,
                        "texto": frag["content"],
                        "page_number": frag.get("page_number"),
                        "sha256": H.sha256_text(frag["content"]),
                        "atom": target,
                    })

    chosen: dict[str, dict] = {}
    composition: dict[str, int] = {}
    for fam in H.FAMILIES:
        pool = [r for r in pools[fam] if r["fragment_id"] not in chosen]
        rng.shuffle(pool)
        picked = pool[:H.TARGET_PER_FAMILY]
        for r in picked:
            chosen[r["fragment_id"]] = r
        composition[fam] = len(picked)

    rows = sorted(chosen.values(), key=lambda r: (r["familia"], r["fragment_id"]))
    with COHORT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "schema": "s270_mutation_cohort_v5_build_v1",
        "created_utc": H._now(),
        "seed": SEED,
        "chunks_table": table,
        "corpus_docs_servibles": len(corpus),
        "excluded_docs": len(excluded & set(corpus)),
        "eligible_docs": len(eligible),
        "docs_sampled": len(docs_used),
        "fragments_screened": fragments_screened,
        "composition": composition,
        "rows": len(rows),
        "exclusion_manifest": manifest,
        "cohort_sha256": H.sha256_file(COHORT_PATH),
    }
    BUILD_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"Cohorte v5: {COHORT_PATH.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"Composición: {composition}")
    return 0


# ─────────────────────────── medidas v5 nuevas ───────────────────────────

def evaluate_display_rows(row: dict, atoms: list[dict]) -> list[dict]:
    """display_token (v2): átomo con riesgo 7-seg — con el token display EN el
    borrador debe anexar (recall); sin el token, 0 anexos de ese átomo (paridad)."""
    results: list[dict] = []
    target = H._locate_target(atoms, row["atom"])
    if target is None or not (target.get("meta") or {}).get("seven_segment_risk"):
        return results
    tokens = sorted(mp.seven_segment_tokens(target.get("span_text") or ""))
    if not tokens:
        return results
    mutations = H.generate_mutations(row)
    if not mutations:
        return results
    base = {
        "fragment_id": row["fragment_id"],
        "familia": row["familia"],
        "document_id": row["document_id"],
    }
    span = (row["atom"].get("span_text") or "").strip()
    claim = mutations[0]["claim_mut"]
    # ITERACIÓN DE INSTRUMENTO DECLARADA (1ª pasada c273, en git): el hook inyectaba
    # SOLO tokens[0] y la paridad exige TODOS los tokens display del span (span con
    # rs/tx/rx → miss de instrumento, no del mecanismo). El hook lleva TODOS.
    hook = TEMPLATES_V5_EXTRA["display_hook"].format(token=", ".join(tokens))
    for with_token, label in ((True, "with_token"), (False, "without_token")):
        draft = H.render_draft(claim, 0)
        if with_token:
            draft = f"{draft} {hook}"
        if not mp.atom_exigible_in(target, draft):
            results.append(base | {
                "key": f"{row['fragment_id']}|display|{label}",
                "measure": "display", "variant_label": label,
                "puntuable": False, "skip_reason": "binding_guard",
            })
            continue
        appendix, appended = run_mechanism_v2(atoms, draft, {1}, 1)
        target_in = span in appendix
        results.append(base | {
            "key": f"{row['fragment_id']}|display|{label}",
            "measure": "display", "variant_label": label,
            "puntuable": True,
            "detected": target_in if with_token else None,
            "fp_new_surface": (target_in if not with_token else None),
            "appendix_len": len(appendix),
        })
    return results


def evaluate_cross_count_rows(row: dict) -> list[dict]:
    """cross_count (v2): split mecánico del fragmento real por el inicio de su
    enumeración → 2 pseudo-fragmentos del mismo doc/página; el mecanismo debe
    formar el átomo cross y anexarlo con cita doble. Control: página no adyacente."""
    results: list[dict] = []
    if row["familia"] != mp.FAMILY_COUNT:
        return results
    atom = row["atom"]
    meta = atom.get("meta") or {}
    if meta.get("cross_fragment"):
        return results
    text = row["texto"]
    blocks = mp._enumeration_blocks(text)
    block = next(
        (b for b in blocks if atom["span_start"] < b[0] <= atom["span_end"]), None
    )
    if block is None:
        return results
    b_start = block[0]
    frag_a = text[:b_start]
    frag_b = text[b_start:]
    if not frag_a.strip() or not frag_b.strip():
        return results
    base = {
        "fragment_id": row["fragment_id"],
        "familia": "F-COUNT-CROSS",
        "document_id": row["document_id"],
    }
    declared = meta.get("declared_n")
    noun = str(meta.get("noun") or "elementos")
    claim = TEMPLATES_V5_EXTRA["cross_count_claim"].format(
        declared=declared, noun=noun
    )
    draft = H.render_draft(claim, 0)
    for adjacent, label in ((True, "adjacent"), (False, "far_page")):
        fragments = [
            {"fragment_number": 1, "text": frag_a,
             "document_id": row["document_id"], "page_number": 10},
            {"fragment_number": 2, "text": frag_b,
             "document_id": row["document_id"],
             "page_number": 10 if adjacent else 40},
        ]
        cross = mp.detect_cross_fragment_count_atoms(fragments)
        detected = False
        dual_cite = False
        if adjacent and cross:
            catom = copy.deepcopy(cross[0])
            window = mp.citation_window(draft, 1)
            if window.strip() and mp.atom_exigible_in(catom, window) and not (
                mp.atom_satisfied(catom, draft)
            ):
                catom.setdefault("meta", {})["fragment_number"] = 1
                appendix = mp.render_appendix([catom], draft)
                detected = bool(appendix)
                dual_cite = "[F1]" in appendix and "[F2]" in appendix
        results.append(base | {
            "key": f"{row['fragment_id']}|cross_count|{label}",
            "measure": "cross_count", "variant_label": label,
            "puntuable": True,
            "detected": detected if adjacent else None,
            "dual_cite": dual_cite if adjacent else None,
            "fp_far_page": (bool(cross) if not adjacent else None),
        })
    return results


def _clean_quality_fp(appended: list[dict], texto: str, draft: str) -> list[str]:
    """Re-spec opción-a (DEC-126): FP de CALIDAD del anexo — span no-verbatim del
    fragmento, cap global/por-familia violado, o MANDATORY duplicado. El anexo
    hermano verbatim+attestado+dentro-de-cap es enriquecimiento etiquetado."""
    reasons: list[str] = []
    if len(appended) > mp.APPENDIX_CAP:
        reasons.append("cap_global")
    fam_counts: dict[str, int] = {}
    for a in appended:
        fam = str(a.get("family"))
        fam_counts[fam] = fam_counts.get(fam, 0) + 1
        span = str(a.get("span_text") or "")
        meta = a.get("meta") or {}
        if meta.get("cross_fragment"):
            continue  # verbatim de 2 fragmentos; medido en cross_count
        if span and span not in texto:
            reasons.append(f"non_verbatim:{span[:30]}")
        if fam == mp.FAMILY_MANDATORY and mp.atom_satisfied(a, draft):
            reasons.append("mandatory_duplicate")
    for fam, n in fam_counts.items():
        if n > mp.APPENDIX_FAMILY_CAP:
            reasons.append(f"cap_familia:{fam}")
    return reasons


# ─────────────────────────── brazo det/híbrido ───────────────────────────

def run_arm(hybrid: bool, execute: bool) -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["freeze"]
    if H.sha256_file(COHORT_PATH) != frozen["cohort_sha256"]:
        raise RuntimeError("freeze roto: cohorte v5 ≠ prereg")
    if H.sha256_file(ROOT / "src/rag/must_preserve.py") != frozen["must_preserve_sha256"]:
        raise RuntimeError("freeze roto: must_preserve.py ≠ prereg")
    rows = H.load_jsonl(COHORT_PATH)
    print(f"Cohorte v5 verificada (freeze OK): {len(rows)} filas")

    if hybrid:
        estimate = H._hybrid_cost_estimate(rows)
        budget = float(prereg["hybrid"]["budget_usd_max"])
        print(f"Brazo HÍBRIDO — estimación: {json.dumps(estimate)} (techo ${budget})")
        if not execute:
            print("PREFLIGHT (0 llamadas pagadas). El brazo híbrido (composites) se "
                  "ejecuta con --run --hybrid --execute cuando el orquestador lo pague.")
            return 0
        raise RuntimeError(
            "brazo híbrido pagado NO habilitado en esta sesión (solo preflight)"
        )

    atoms_by_fragment = {r["fragment_id"]: mp.detect_atoms(r["texto"]) for r in rows}
    done = {r["key"] for r in H.load_jsonl(RESULTS_DET_PATH)}
    written = 0
    with RESULTS_DET_PATH.open("a", encoding="utf-8", newline="\n") as out:
        def emit(result: dict) -> None:
            nonlocal written
            if result["key"] in done:
                return
            result["arm"] = "det"
            out.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
            out.flush()
            written += 1

        for row in rows:
            atoms = atoms_by_fragment[row["fragment_id"]]
            for result in H.evaluate_fragment_rows(row, atoms):
                # re-spec opción-a: recalificar los clean con FP de CALIDAD
                if result.get("measure") == "clean" and result.get("puntuable"):
                    mutations = H.generate_mutations(row)
                    claim = mutations[0]["claim_clean"] if mutations else None
                    if claim is not None:
                        draft = H.render_draft(claim, result["variant"])
                        _appendix, appended = run_mechanism_v2(
                            atoms, draft, {1}, 1
                        )
                        reasons = _clean_quality_fp(appended, row["texto"], draft)
                        result["fp_quality"] = bool(reasons)
                        result["fp_quality_reasons"] = reasons
                        result["enrichment_appends"] = (
                            len(appended) if not reasons else 0
                        )
                emit(result)
            for result in evaluate_display_rows(row, atoms):
                emit(result)
            for result in evaluate_cross_count_rows(row):
                emit(result)
        for result in H.evaluate_cross_rows(rows, atoms_by_fragment):
            emit(result)
        for result in H.evaluate_attestation_rows(rows, atoms_by_fragment):
            emit(result)
    print(f"Resultados (det): {RESULTS_DET_PATH.relative_to(ROOT)} (+{written})")
    return 0


# ─────────────────────────── gate ───────────────────────────

def gate() -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if H.sha256_file(ROOT / "src/rag/must_preserve.py") != (
        prereg["freeze"]["must_preserve_sha256"]
    ):
        raise RuntimeError("gate: must_preserve.py ≠ prereg")
    rows = H.load_jsonl(RESULTS_DET_PATH)
    gates = prereg["gates"]

    def rate(pred_num, pred_den):
        num = [r for r in rows if pred_num(r)]
        den = [r for r in rows if pred_den(r)]
        return (len(num) / len(den)) if den else None, len(num), len(den)

    verdict: dict = {"schema": "s270_stage1_v5_gate_v1", "created_utc": H._now(),
                     "arm": "det", "families": {}, "checks": {}}
    ok = True
    for fam in H.FAMILIES:
        r, n, d = rate(
            lambda x, f=fam: x.get("measure") == "mutation" and x.get("puntuable")
            and x.get("detected") and x["familia"] == f,
            lambda x, f=fam: x.get("measure") == "mutation" and x.get("puntuable")
            and x["familia"] == f,
        )
        passed = r is not None and r >= gates["mutation_recall_min_per_family"]
        verdict["families"][fam] = {"recall": r, "detected": n, "scored": d,
                                    "pass": passed}
        ok = ok and (passed or d == 0)
    disp_r, disp_n, disp_d = rate(
        lambda x: x.get("measure") == "display" and x.get("puntuable")
        and x.get("variant_label") == "with_token" and x.get("detected"),
        lambda x: x.get("measure") == "display" and x.get("puntuable")
        and x.get("variant_label") == "with_token",
    )
    disp_fp = len([
        r for r in rows if r.get("measure") == "display"
        and r.get("variant_label") == "without_token" and r.get("fp_new_surface")
    ])
    cross_r, cross_n, cross_d = rate(
        lambda x: x.get("measure") == "cross_count"
        and x.get("variant_label") == "adjacent" and x.get("detected")
        and x.get("dual_cite"),
        lambda x: x.get("measure") == "cross_count"
        and x.get("variant_label") == "adjacent",
    )
    cross_far_fp = len([
        r for r in rows if r.get("measure") == "cross_count"
        and r.get("variant_label") == "far_page" and r.get("fp_far_page")
    ])
    clean_fp = len([r for r in rows if r.get("measure") == "clean"
                    and r.get("fp_quality")])
    enrichment = sum(r.get("enrichment_appends", 0) for r in rows
                     if r.get("measure") == "clean")
    crossb_fp = len([r for r in rows if r.get("measure") == "cross" and r.get("fp")])
    attest_appends = sum(r.get("appends", 0) for r in rows
                         if r.get("measure") == "attestation")
    scored = [r for r in rows if r.get("puntuable")]
    coverage = (
        len(scored) / len([r for r in rows if "puntuable" in r])
        if rows else None
    )
    checks = {
        "display_recall": {"value": disp_r, "n": disp_n, "d": disp_d,
                           "pass": disp_d == 0 or (disp_r or 0) >= gates["display_recall_min"]},
        "display_no_new_surface_fp": {"value": disp_fp,
                                      "pass": disp_fp <= gates["display_no_new_surface_fp_max"]},
        "cross_count_recall": {"value": cross_r, "n": cross_n, "d": cross_d,
                               "pass": cross_d == 0 or (cross_r or 0) >= gates["cross_count_recall_min"]},
        "cross_count_far_page_fp": {"value": cross_far_fp, "pass": cross_far_fp == 0},
        "clean_annex_quality_fp": {"value": clean_fp,
                                   "pass": clean_fp <= gates["clean_annex_quality_fp_max"]},
        "enrichment_appends_reported": {"value": enrichment, "pass": True},
        "cross_binding_fp": {"value": crossb_fp,
                             "pass": crossb_fp <= gates["cross_binding_fp_max"]},
        "attestation_block_appends": {"value": attest_appends,
                                      "pass": attest_appends <= gates["attestation_block_appends_max"]},
        "coverage": {"value": coverage,
                     "pass": coverage is not None and coverage >= gates["coverage_min"]},
    }
    verdict["checks"] = checks
    ok = ok and all(c["pass"] for c in checks.values())
    verdict["verdict"] = "GO" if ok else "NO_GO"
    GATE_OUT_PATH.write_text(
        yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(yaml.safe_dump(
        {"verdict": verdict["verdict"],
         "families": {f: v["recall"] for f, v in verdict["families"].items()},
         "checks": {k: c["pass"] for k, c in checks.items()}},
        allow_unicode=True, sort_keys=False))
    print(f"Gate: {GATE_OUT_PATH.relative_to(ROOT)}")
    return 0 if ok else 2


# ─────────────────────────── freeze (prereg v4) ───────────────────────────

def freeze() -> int:
    if not COHORT_PATH.exists():
        raise RuntimeError("cohorte v5 no construida: --build-cohort primero")
    rows = H.load_jsonl(COHORT_PATH)
    build = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    prereg = {
        "schema": "s270_stage1_v5_prereg_v1",
        "status": "FROZEN_BEFORE_RUN",
        "created_utc": H._now(),
        "predecessor": "evals/s269_stage1_v3_prereg_v3.yaml (seed-272, 4/4 GO)",
        "mechanism": "must_preserve v2 (DEC-126; fixes derivados del funnel del probe-1 s270)",
        "seed": SEED,
        "gates": dict(GATES),
        "gates_provenance": (
            "heredados del prereg v3 + tipos nuevos v2 (display/cross_count) + "
            "clean-noise re-specced a opción-a DEC-126: FP = violación de CALIDAD "
            "del anexo (no-verbatim / cap global o por-familia / MANDATORY "
            "duplicado); el anexo hermano verbatim dentro de cap es enriquecimiento "
            "etiquetado y se REPORTA (enrichment_appends), no penaliza"
        ),
        "new_measures": {
            "display": "token display en borrador → anexa; sin token → 0 anexos",
            "cross_count": "split mecánico conteo|enumeración en 2 pseudo-fragmentos "
                           "mismo doc/página → átomo cross con cita doble; control "
                           "far_page = 0 átomos",
            "composite_hybrid": "SOLO brazo --hybrid (preflight en esta sesión; "
                                "ejecución pagada la decide el orquestador)",
        },
        "freeze": {
            "must_preserve_sha256": H.sha256_file(ROOT / "src/rag/must_preserve.py"),
            "harness_v5_sha256": H.sha256_file(
                ROOT / "scripts/s270_mutation_harness_v5.py"
            ),
            "s269_harness_sha256": H.sha256_file(
                ROOT / "scripts/s269_mutation_harness.py"
            ),
            "templates_sha256": H.templates_sha256(),
            "cohort_path": str(COHORT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "cohort_rows": len(rows),
            "cohort_sha256": H.sha256_file(COHORT_PATH),
            "build_report_sha256": H.sha256_file(BUILD_REPORT_PATH),
        },
        "cohort_composition": build["composition"],
        "population": {
            "corpus_docs_servibles": build["corpus_docs_servibles"],
            "excluded_docs": build["excluded_docs"],
            "eligible_docs": build["eligible_docs"],
            "docs_sampled": build["docs_sampled"],
            "fragments_screened": build["fragments_screened"],
        },
        "hybrid": {
            "model": mp.HYBRID_DETECTOR_MODEL,
            "budget_usd_max": 4.0,
            "prices_usd_per_mtok": {"input": H.HYBRID_PRICE_IN,
                                    "output": H.HYBRID_PRICE_OUT},
            "no_retry": True,
            "status": "PREFLIGHT_ONLY_THIS_SESSION",
        },
        "honest_declarations": [
            "CUARTA población fresca (seed-273); exclusiones ACUMULADAS: cohorte v1 "
            "+ seed-270 + seed-271 + seed-272. Las medidas previas quedan como "
            "evidencia versionada.",
            "Los fixes v2 derivan del FUNNEL del probe-1 (trazas/fragmentos "
            "SERVIDOS), no de los textos gold; este harness los valida en población "
            "fresca ANTES del probe v2.",
            "cross_count usa SPLITS SINTÉTICOS de fragmentos reales (el split "
            "mecánico emula el corte de chunking); la prevalencia real de pares "
            "cross no se mide.",
            "El brazo híbrido (composites) queda en PREFLIGHT: el determinista es "
            "$0 y es el que gatea; la ejecución pagada del híbrido la decide el "
            "orquestador.",
            "ITERACIÓN DE INSTRUMENTO DECLARADA (post 1ª pasada c273, commit "
            "9cfc422): el hook de display inyectaba SOLO el primer token y la "
            "paridad exige TODOS los tokens del span (rs/tx/rx) → 1 miss de "
            "instrumento (3/4). Fix del TEMPLATE (todos los tokens), SIN tocar el "
            "mecanismo; re-medido sobre la MISMA cohorte seed-273; la 1ª pasada "
            "queda en el historial git.",
        ],
        "gate_runner": "scripts/s270_mutation_harness_v5.py --gate",
        "gate_output": str(GATE_OUT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    PREREG_PATH.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Prereg v5 congelado: {PREREG_PATH.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-cohort", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    if args.build_cohort:
        return build_cohort()
    if args.freeze:
        return freeze()
    if args.run:
        return run_arm(hybrid=args.hybrid, execute=args.execute)
    if args.gate:
        return gate()
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
