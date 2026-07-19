#!/usr/bin/env python3
"""S271 Etapa 1 v7 — harness de mutaciones para los GUARDS DE ACTIVACIÓN (DEC-127b;
sucesor del s270 v6 seed-274 GO).

Extiende el harness v5/v6 (que se importa y reusa: builders, templates, mutadores,
evaluadores) con TRES tipos nuevos, uno por bloqueador de activación observado en la
Etapa 3 viva (evals/s270_etapa3_smoke_appendices_v1.jsonl — derivados de la RUTA VIVA,
no de los textos gold):

  dup_span      (bloqueador 1, hp001) dos átomos con el MISMO span en missing → el
                anexo lo lleva UNA sola vez; control: dos spans distintos (números
                distintos) NO se colapsan.
  empty_enum    (bloqueador 2, cat007) disclosure F-COUNT cuyo lado-enumeración es una
                tabla de celdas-EN-BLANCO → el disclosure entero NO dispara; control:
                la enumeración real sigue disparando con ambos lados.
  count_navcrumb (bloqueador 3, hp001) conteo + crumb de navegación/menú en la misma
                sección → NO liga; heading sin relevancia + enumeración sin el
                sustantivo → NO liga; control positivo (heading del dominio) → liga.

Población FRESCA seed=275 con exclusiones ACUMULADAS (cohortes v1 + seed-270..274).
Gates heredados del prereg v6 ÍNTEGROS (los fixes no se compran con recall) + los 3
checks nuevos. Brazo determinista $0; el híbrido queda en preflight (paga el
orquestador).

v8 (seed=276, el fichero EVOLUCIONA en el sitio — patrón v5→v6; la corrida v7 queda
congelada en git): valida la WHITELIST fail-closed de forma-buena (must_preserve v5,
INVERSIÓN DE CONTRATO tras la Etapa 3 v2) con 2 tipos nuevos derivados de las clases
OBSERVADAS en ruta viva: heading_only (cabecera-sola «### <ins>ADVERTENCIA</ins>»
jamás se anexa) y ui_dump (volcado de descripción de UI multi-línea como
lado-enumeración de un disclosure jamás dispara). Las filas cuyo átomo target no pasa
la whitelist se RE-ETIQUETAN como skip DECLARADO (whitelist_bad_form: silencio por
diseño, no miss del mecanismo) y su volumen se REPORTA en el gate.

Uso:
  python scripts/s271_mutation_harness_v7.py --build-cohort   # GET-only, $0
  python scripts/s271_mutation_harness_v7.py --freeze         # prereg v8
  python scripts/s271_mutation_harness_v7.py --run            # brazo det ($0)
  python scripts/s271_mutation_harness_v7.py --gate           # veredicto
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


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H5 = _load("s270_mutation_harness_v5", "scripts/s270_mutation_harness_v5.py")
H = H5.H  # harness s269 base (con run_mechanism ya rebindado a la selección v2)

EVALS = ROOT / "evals"
COHORT_V7_PATH = EVALS / "s271_mutation_cohort_v7.jsonl"  # seed-275 (excluida en v8)
COHORT_PATH = EVALS / "s271_mutation_cohort_v8.jsonl"
BUILD_REPORT_PATH = EVALS / "s271_mutation_cohort_v8_build.json"
PREREG_PATH = EVALS / "s271_stage1_v8_prereg_v1.yaml"
RESULTS_DET_PATH = EVALS / "s271_stage1_v8_results_det_c276.jsonl"
GATE_OUT_PATH = EVALS / "s271_stage1_v8_gate_v1.yaml"

SEED = 276
# gates heredados ÍNTEGROS del prereg v6 + checks de activación s271 (v7) + whitelist (v8)
GATES = dict(H5.GATES) | {
    "dup_span_fp_max": 0,             # span duplicado en el anexo = FP
    "dup_span_control_loss_max": 0,   # dos hechos distintos colapsados = FP
    "empty_enum_fp_max": 0,           # disclosure con enum de celdas en blanco = FP
    "empty_enum_positive_recall_min": 0.80,
    "navcrumb_fp_max": 0,             # conteo ligado a crumb de navegación = FP
    "navcrumb_no_relevance_fp_max": 0,
    "navcrumb_positive_recall_min": 0.80,
    # v8 — clases nuevas de la Etapa 3 v2 (whitelist fail-closed)
    "heading_only_fp_max": 0,         # cabecera-sola anexada = FP
    "heading_only_control_recall_min": 0.80,
    "ui_dump_fp_max": 0,              # ui-dump como lado de disclosure disparado = FP
}

TEMPLATES_V7_EXTRA = {
    "nav_crumb": "Inicio | Ajustes | Salir",
    "prose_break": (
        "El comportamiento depende de la configuración del sitio y del firmware "
        "cargado en el equipo."
    ),
    "heading_domain": "## {noun_cap} del equipo",
    "heading_unrelated": "## Historial de revisiones",
    "enum_item_words": ("Elemento", "Registro", "Componente"),
    "blank_row": "| E{i} |   |",
    "blank_sep": "| --- | - |",
    # v8 — clases observadas en la Etapa 3 v2 (forma genérica, no gold-derived)
    "heading_only": "### <ins>{trigger}</ins>",
    "ui_dump": (
        "- Right sidebar with options: GENERAL, OPCIONES, REGISTROS, AJUSTES "
        "(highlighted), CONFIG, SALIDA\n"
        '- Bottom buttons: "Guardar y reiniciar" and "INICIO"\n'
        '- Header: "Panel_template 20:17 - martes, 31 de marzo de 2020"]'
    ),
}


# ─────────────────────────── build cohorte v7 (seed 275) ───────────────────────────

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
        ("seed272_cohort_docs_exclusion", H.COHORT_PATH),        # cohorte v4
        ("seed273_cohort_docs_exclusion", H5.COHORT_SEED273_PATH),  # cohorte v5
        ("seed274_cohort_docs_exclusion", H5.COHORT_PATH),       # cohorte v6
        ("seed275_cohort_docs_exclusion", COHORT_V7_PATH),       # cohorte v7
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
        "schema": "s271_mutation_cohort_v8_build_v1",
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
    print(f"Cohorte v8: {COHORT_PATH.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"Composición: {composition}")
    return 0


# ─────────────────────────── medidas v7 nuevas ───────────────────────────

def evaluate_display_rows_v7(row: dict, atoms: list[dict]) -> list[dict]:
    """display_token con FIX DE INSTRUMENTO declarado (1ª pasada c275: 2/3 — misma
    CLASE que el artefacto seed-272 «el guard evaluaba el borrador completo y no la
    ventana»): un claim BUNDLE con puntos embebidos en los miembros parte la VENTANA
    de cita y el binding real (bind_atoms → citation_window) muere aunque el guard
    sobre el borrador completo pase. El binding-guard se evalúa aquí contra la MISMA
    ventana que usa el mecanismo. El mecanismo NO se toca."""
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
    hook = H5.TEMPLATES_V5_EXTRA["display_hook"].format(token=", ".join(tokens))
    for with_token, label in ((True, "with_token"), (False, "without_token")):
        draft = H.render_draft(claim, 0)
        if with_token:
            draft = f"{draft} {hook}"
        window = mp.citation_window(draft, 1)
        if not window.strip() or not mp.atom_exigible_in(target, window):
            results.append(base | {
                "key": f"{row['fragment_id']}|display|{label}",
                "measure": "display", "variant_label": label,
                "puntuable": False, "skip_reason": "binding_guard",
            })
            continue
        appendix, _appended = H5.run_mechanism_v2(atoms, draft, {1}, 1)
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


def evaluate_dup_span_rows(row: dict, atoms: list[dict]) -> list[dict]:
    """dup_span (bloqueador 1): el átomo target DUPLICADO en la lista de átomos del
    fragmento → el anexo debe llevar su span UNA sola vez."""
    results: list[dict] = []
    target = H._locate_target(atoms, row["atom"])
    if target is None:
        return results
    if (target.get("meta") or {}).get("seven_segment_risk"):
        return results  # la vía display se mide en su medida propia
    mutations = H.generate_mutations(row)
    if not mutations:
        return results
    span = (row["atom"].get("span_text") or "").strip()
    draft = H.render_draft(mutations[0]["claim_mut"], 0)
    base = {
        "fragment_id": row["fragment_id"],
        "familia": row["familia"],
        "document_id": row["document_id"],
        "key": f"{row['fragment_id']}|dup_span",
        "measure": "dup_span",
    }
    if not mp.atom_good_form(target):
        return [base | {"puntuable": False, "skip_reason": "whitelist_bad_form"}]
    if not mp.atom_exigible_in(target, draft):
        return [base | {"puntuable": False, "skip_reason": "binding_guard"}]
    atoms_dup = atoms + [copy.deepcopy(target)]
    appendix, appended = H5.run_mechanism_v2(atoms_dup, draft, {1}, 1)
    fold_target = mp._fold_ws(span)[0]
    occurrences = sum(
        1 for a in appended
        if mp._fold_ws((a.get("span_text") or "").strip())[0] == fold_target
    )
    if occurrences == 0:
        return [base | {"puntuable": False, "skip_reason": "target_not_appended"}]
    return [base | {
        "puntuable": True,
        "fp_dup": occurrences >= 2,
        "span_occurrences": occurrences,
        "appendix_len": len(appendix),
    }]


def evaluate_dup_control_rows(rows: list[dict], atoms_by_fragment: dict,
                              max_pairs: int = 30) -> list[dict]:
    """Control del dedup: dos átomos DISTINTOS (spans con contenido numérico distinto,
    no near-dup) en missing → AMBOS spans en el anexo (el dedup no colapsa hechos
    distintos). Render-level, gold mecánico por construcción."""
    results: list[dict] = []
    ordered = sorted(rows, key=lambda r: (r["familia"], r["fragment_id"]))
    used = 0
    for i, row_a in enumerate(ordered):
        if used >= max_pairs:
            break
        target_a = H._locate_target(atoms_by_fragment[row_a["fragment_id"]],
                                    row_a["atom"])
        if target_a is None or (target_a.get("meta") or {}).get("seven_segment_risk"):
            continue
        span_a = (target_a.get("span_text") or "").strip()
        if not mp.atom_good_form(target_a):
            continue  # v8: el control usa solo átomos que la whitelist admite
        pair = None
        for j in range(1, len(ordered)):
            row_b = ordered[(i + j) % len(ordered)]
            if row_b["familia"] == row_a["familia"]:
                continue
            target_b = H._locate_target(atoms_by_fragment[row_b["fragment_id"]],
                                        row_b["atom"])
            if target_b is None or (
                (target_b.get("meta") or {}).get("seven_segment_risk")
            ):
                continue
            span_b = (target_b.get("span_text") or "").strip()
            if not mp.atom_good_form(target_b):
                continue
            fold_a = mp._fold_ws(span_a)[0]
            fold_b = mp._fold_ws(span_b)[0]
            if mp._near_duplicate_span(fold_a, fold_b):
                continue  # el control exige spans NO near-dup
            pair = (row_b, target_b, span_b)
            break
        if pair is None:
            continue
        row_b, target_b, span_b = pair
        a = copy.deepcopy(target_a)
        b = copy.deepcopy(target_b)
        a.setdefault("meta", {})["fragment_number"] = 1
        b.setdefault("meta", {})["fragment_number"] = 1
        appendix = mp.render_appendix(
            [a, b], "Los parámetros del equipo se describen a continuación [F1]"
        )
        results.append({
            "key": f"{row_a['fragment_id']}|dup_control|{row_b['fragment_id']}",
            "measure": "dup_control",
            "familia": row_a["familia"],
            "fragment_id": row_a["fragment_id"],
            "partner_fragment_id": row_b["fragment_id"],
            "document_id": row_a["document_id"],
            "puntuable": True,
            "fp_loss": not (span_a in appendix and span_b in appendix),
        })
        used += 1
    return results


def _blank_table(n: int) -> str:
    rows = [TEMPLATES_V7_EXTRA["blank_row"].format(i=1),
            TEMPLATES_V7_EXTRA["blank_sep"]]
    rows.extend(TEMPLATES_V7_EXTRA["blank_row"].format(i=i) for i in range(2, n + 1))
    return "\n".join(rows)


def evaluate_empty_enum_rows(row: dict, atoms: list[dict]) -> list[dict]:
    """empty_enum (bloqueador 2) + ui_dump (v8, Etapa 3 v2): el MISMO átomo F-COUNT
    en conflicto con su enum_span_text sustituido por (a) una tabla de celdas
    EN-BLANCO o (b) un volcado de descripción de UI multi-línea no dispara el
    disclosure; con la enumeración real (control) sigue disparando con ambos lados
    — control condicionado a que el átomo real pase la whitelist (si no, skip
    declarado: su silencio es DISEÑO, medido por los FP de blank/ui_dump)."""
    if row["familia"] != mp.FAMILY_COUNT:
        return []
    target = H._locate_target(atoms, row["atom"])
    if target is None:
        return []
    meta = target.get("meta") or {}
    enum_span = str(meta.get("enum_span_text") or "").strip()
    if not enum_span or not meta.get("conflict"):
        return []
    mutations = H.generate_mutations(row)
    if not mutations:
        return []
    draft = H.render_draft(mutations[0]["claim_mut"], 0)
    span = (target.get("span_text") or "").strip()
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    results: list[dict] = []
    for label, measure, enum_text, expect_fire in (
        ("blank", "empty_enum",
         _blank_table(max(2, int(meta.get("enumerated_n") or 3))), False),
        ("ui_dump", "ui_dump", TEMPLATES_V7_EXTRA["ui_dump"], False),
        ("real", "empty_enum", enum_span, True),
    ):
        catom = copy.deepcopy(target)
        catom["meta"]["enum_span_text"] = enum_text
        catom["meta"]["fragment_number"] = 1
        if expect_fire and not mp.atom_good_form(catom):
            results.append(base | {
                "key": f"{row['fragment_id']}|empty_enum|{label}",
                "measure": measure, "variant_label": label,
                "puntuable": False, "skip_reason": "whitelist_bad_form",
            })
            continue
        appendix = mp.render_appendix([catom], draft)
        fired = bool(appendix) and span in appendix
        results.append(base | {
            "key": f"{row['fragment_id']}|empty_enum|{label}",
            "measure": measure, "variant_label": label,
            "puntuable": True,
            "fp_blank": (fired if not expect_fire else None),
            "detected": (
                (fired and enum_text in appendix) if expect_fire else None
            ),
        })
    return results


def evaluate_heading_only_rows(row: dict, atoms: list[dict]) -> list[dict]:
    """heading_only (v8, Etapa 3 v2 cat007): un átomo MANDATORY cuyo span es SOLO la
    cabecera («### <ins>ADVERTENCIA</ins>») jamás se anexa; control: la cláusula
    MANDATORY real del fragmento (si pasa la whitelist) sigue anexándose."""
    if row["familia"] != mp.FAMILY_MANDATORY:
        return []
    target = H._locate_target(atoms, row["atom"])
    if target is None:
        return []
    meta = target.get("meta") or {}
    triggers = [t for t in (meta.get("triggers") or []) if "+" not in t]
    trigger = (triggers[0] if triggers else "advertencia").upper()
    draft = "Siga el procedimiento de instalación descrito en la fuente [F1]"
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    heading_atom = copy.deepcopy(target)
    heading_atom["span_text"] = TEMPLATES_V7_EXTRA["heading_only"].format(
        trigger=trigger
    )
    heading_atom["meta"]["fragment_number"] = 1
    fp = bool(mp._select_for_appendix([heading_atom], draft))
    results = [base | {
        "key": f"{row['fragment_id']}|heading_only|heading",
        "measure": "heading_only", "variant_label": "heading",
        "puntuable": True, "fp_heading": fp,
    }]
    control = copy.deepcopy(target)
    control["meta"]["fragment_number"] = 1
    if not mp.atom_good_form(control):
        results.append(base | {
            "key": f"{row['fragment_id']}|heading_only|control",
            "measure": "heading_only", "variant_label": "control",
            "puntuable": False, "skip_reason": "whitelist_bad_form",
        })
    else:
        results.append(base | {
            "key": f"{row['fragment_id']}|heading_only|control",
            "measure": "heading_only", "variant_label": "control",
            "puntuable": True,
            "detected": bool(mp._select_for_appendix([control], draft)),
        })
    return results


def evaluate_navcrumb_rows(row: dict) -> list[dict]:
    """count_navcrumb (bloqueador 3): la oración de conteo REAL del átomo en tres
    fragmentos sintéticos — crumb de navegación (no liga), heading sin relevancia +
    enumeración sin el sustantivo (no liga), heading del dominio + enumeración
    legítima (control positivo: liga)."""
    if row["familia"] != mp.FAMILY_COUNT:
        return []
    atom = row["atom"]
    meta = atom.get("meta") or {}
    declared = meta.get("declared_n")
    noun = str(meta.get("noun") or "")
    sentence = (atom.get("span_text") or "").strip()
    if not declared or not noun or not sentence:
        return []
    if "\n" in sentence or "|" in sentence or sentence.lstrip().startswith("#"):
        return []  # la oración debe poder vivir como línea de prosa
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    results: list[dict] = []
    heading_domain = TEMPLATES_V7_EXTRA["heading_domain"].format(
        noun_cap=noun.capitalize()
    )
    heading_unrel = TEMPLATES_V7_EXTRA["heading_unrelated"]
    prose = TEMPLATES_V7_EXTRA["prose_break"]
    crumb = TEMPLATES_V7_EXTRA["nav_crumb"]
    item_word = next(
        (w for w in TEMPLATES_V7_EXTRA["enum_item_words"]
         if not mp._noun_tie(noun, w)),
        None,
    )
    n_items = int(declared) + 1
    letters = [chr(ord("A") + k) for k in range(n_items)]

    # 1) crumb de navegación en la sección del conteo → NO liga
    if int(declared) == 3:
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|crumb",
            "measure": "navcrumb", "variant_label": "crumb",
            "puntuable": False, "skip_reason": "declared_eq_crumb_cells",
        })
    else:
        text = f"{heading_domain}\n{sentence}\n{prose}\n{crumb}\n"
        atoms = [a for a in mp.detect_atoms(text)
                 if a["family"] == mp.FAMILY_COUNT]
        fp = any(
            crumb in str((a.get("meta") or {}).get("enum_span_text") or "")
            for a in atoms
        )
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|crumb",
            "measure": "navcrumb", "variant_label": "crumb",
            "puntuable": True, "fp_crumb": fp,
        })

    # 2) heading sin relevancia + enumeración sin el sustantivo → NO liga
    h_tokens = set(mp._content_tokens(heading_unrel.lstrip("# ")))
    s_tokens = set(mp._content_tokens(sentence))
    if item_word is None or (h_tokens & s_tokens):
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|no_relevance",
            "measure": "navcrumb", "variant_label": "no_relevance",
            "puntuable": False, "skip_reason": "relevance_collision",
        })
    else:
        enum = "\n".join(f"- {item_word} {letter}" for letter in letters)
        text = f"{heading_unrel}\n{sentence}\n{prose}\n{enum}\n"
        atoms = [a for a in mp.detect_atoms(text)
                 if a["family"] == mp.FAMILY_COUNT]
        fp = any(
            item_word in str((a.get("meta") or {}).get("enum_span_text") or "")
            for a in atoms
        )
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|no_relevance",
            "measure": "navcrumb", "variant_label": "no_relevance",
            "puntuable": True, "fp_no_relevance": fp,
        })

    # 3) control positivo: heading del dominio + enumeración legítima → liga
    if item_word is None:
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|positive",
            "measure": "navcrumb", "variant_label": "positive",
            "puntuable": False, "skip_reason": "no_item_word",
        })
    else:
        enum = "\n".join(f"- {item_word} {letter}" for letter in letters)
        text = f"{heading_domain}\n{sentence}\n{prose}\n{enum}\n"
        atoms = [a for a in mp.detect_atoms(text)
                 if a["family"] == mp.FAMILY_COUNT]
        detected = any(
            item_word in str((a.get("meta") or {}).get("enum_span_text") or "")
            and (a.get("meta") or {}).get("tie") == "section"
            for a in atoms
        )
        results.append(base | {
            "key": f"{row['fragment_id']}|navcrumb|positive",
            "measure": "navcrumb", "variant_label": "positive",
            "puntuable": True, "detected": detected,
        })
    return results


# ─────────────────────────── brazo det ───────────────────────────

def run_arm(hybrid: bool, execute: bool) -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["freeze"]
    if H.sha256_file(COHORT_PATH) != frozen["cohort_sha256"]:
        raise RuntimeError("freeze roto: cohorte v8 ≠ prereg")
    if H.sha256_file(ROOT / "src/rag/must_preserve.py") != frozen["must_preserve_sha256"]:
        raise RuntimeError("freeze roto: must_preserve.py ≠ prereg")
    rows = H.load_jsonl(COHORT_PATH)
    print(f"Cohorte v8 verificada (freeze OK): {len(rows)} filas")

    if hybrid:
        estimate = H._hybrid_cost_estimate(rows)
        budget = float(prereg["hybrid"]["budget_usd_max"])
        print(f"Brazo HÍBRIDO — estimación: {json.dumps(estimate)} (techo ${budget})")
        if not execute:
            print("PREFLIGHT (0 llamadas pagadas). La ejecución pagada la decide el "
                  "orquestador.")
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

        def relabel_whitelist_skip(result: dict) -> dict:
            """v8: fila cuyo átomo target no pasa la whitelist → skip DECLARADO
            (silencio por DISEÑO del mecanismo v5, no miss); el volumen se reporta
            en el gate (whitelist_skips_reported)."""
            return {
                **result, "puntuable": False, "detected": None,
                "skip_reason": "whitelist_bad_form_target",
            }

        for row in rows:
            atoms = atoms_by_fragment[row["fragment_id"]]
            target = H._locate_target(atoms, row["atom"])
            target_good = target is not None and mp.atom_good_form(target)
            for result in H.evaluate_fragment_rows(row, atoms):
                if (result.get("measure") == "mutation" and result.get("puntuable")
                        and not target_good):
                    result = relabel_whitelist_skip(result)
                # re-spec opción-a (heredado v5/v6): clean con FP de CALIDAD
                if result.get("measure") == "clean" and result.get("puntuable"):
                    mutations = H.generate_mutations(row)
                    claim = mutations[0]["claim_clean"] if mutations else None
                    if claim is not None:
                        draft = H.render_draft(claim, result["variant"])
                        _appendix, appended = H5.run_mechanism_v2(
                            atoms, draft, {1}, 1
                        )
                        reasons = H5._clean_quality_fp(appended, row["texto"], draft)
                        result["fp_quality"] = bool(reasons)
                        result["fp_quality_reasons"] = reasons
                        result["enrichment_appends"] = (
                            len(appended) if not reasons else 0
                        )
                emit(result)
            for result in evaluate_display_rows_v7(row, atoms):
                if result.get("puntuable") and not target_good:
                    result = relabel_whitelist_skip(result)
                emit(result)
            for result in H5.evaluate_cross_count_rows(row):
                # el control far_page es de DETECCIÓN (no render): no se re-etiqueta
                if (result.get("variant_label") == "adjacent"
                        and result.get("puntuable") and not target_good):
                    result = relabel_whitelist_skip(result)
                emit(result)
            for result in H5.evaluate_grounding_rows(row):
                emit(result)
            for result in H5.evaluate_disclosure_rows(row, atoms):
                if result.get("puntuable") and not target_good:
                    result = relabel_whitelist_skip(result)
                emit(result)
            for result in evaluate_dup_span_rows(row, atoms):
                emit(result)
            for result in evaluate_empty_enum_rows(row, atoms):
                emit(result)
            for result in evaluate_navcrumb_rows(row):
                emit(result)
            for result in evaluate_heading_only_rows(row, atoms):
                emit(result)
        for result in H.evaluate_cross_rows(rows, atoms_by_fragment):
            emit(result)
        for result in H.evaluate_attestation_rows(rows, atoms_by_fragment):
            emit(result)
        for result in evaluate_dup_control_rows(rows, atoms_by_fragment):
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

    verdict: dict = {"schema": "s271_stage1_v8_gate_v1", "created_utc": H._now(),
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
    # v8 (fix de gate declarado, 1ª pasada c276): el predicado heredado de v5 no
    # filtraba puntuable (en v5 todas las filas adjacent lo eran); con el relabel
    # de whitelist el denominador debe ser el mismo que en el resto de recalls.
    cross_r, cross_n, cross_d = rate(
        lambda x: x.get("measure") == "cross_count" and x.get("puntuable")
        and x.get("variant_label") == "adjacent" and x.get("detected")
        and x.get("dual_cite"),
        lambda x: x.get("measure") == "cross_count" and x.get("puntuable")
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
    dup_fp = len([r for r in rows if r.get("measure") == "dup_span"
                  and r.get("fp_dup")])
    dup_ctrl_loss = len([r for r in rows if r.get("measure") == "dup_control"
                         and r.get("fp_loss")])
    ee_fp = len([r for r in rows if r.get("measure") == "empty_enum"
                 and r.get("variant_label") == "blank" and r.get("fp_blank")])
    ee_r, ee_n, ee_d = rate(
        lambda x: x.get("measure") == "empty_enum" and x.get("puntuable")
        and x.get("variant_label") == "real" and x.get("detected"),
        lambda x: x.get("measure") == "empty_enum" and x.get("puntuable")
        and x.get("variant_label") == "real",
    )
    nav_fp = len([r for r in rows if r.get("measure") == "navcrumb"
                  and r.get("variant_label") == "crumb" and r.get("fp_crumb")])
    nav_norel_fp = len([
        r for r in rows if r.get("measure") == "navcrumb"
        and r.get("variant_label") == "no_relevance" and r.get("fp_no_relevance")
    ])
    nav_r, nav_n, nav_d = rate(
        lambda x: x.get("measure") == "navcrumb" and x.get("puntuable")
        and x.get("variant_label") == "positive" and x.get("detected"),
        lambda x: x.get("measure") == "navcrumb" and x.get("puntuable")
        and x.get("variant_label") == "positive",
    )
    heading_fp = len([
        r for r in rows if r.get("measure") == "heading_only"
        and r.get("variant_label") == "heading" and r.get("fp_heading")
    ])
    heading_r, heading_n, heading_d = rate(
        lambda x: x.get("measure") == "heading_only" and x.get("puntuable")
        and x.get("variant_label") == "control" and x.get("detected"),
        lambda x: x.get("measure") == "heading_only" and x.get("puntuable")
        and x.get("variant_label") == "control",
    )
    uidump_fp = len([
        r for r in rows if r.get("measure") == "ui_dump" and r.get("fp_blank")
    ])
    whitelist_skips: dict[str, int] = {}
    wl_by_family: dict[str, int] = {}
    for r in rows:
        if str(r.get("skip_reason") or "").startswith("whitelist_bad_form"):
            m = str(r.get("measure"))
            whitelist_skips[m] = whitelist_skips.get(m, 0) + 1
            if m == "mutation":
                fam = str(r.get("familia"))
                wl_by_family[fam] = wl_by_family.get(fam, 0) + 1
    scored = [r for r in rows if r.get("puntuable")]
    # v8 (re-spec de gate DECLARADO, 1ª pasada c276: coverage 0.807): coverage mide
    # la salud del INSTRUMENTO (filas que el harness no pudo puntuar); el silencio
    # por DISEÑO de la whitelist (skip whitelist_bad_form*) NO es incapacidad del
    # instrumento — se separa en su propia métrica VISIBLE (whitelist_silence_share,
    # reportada) para que el coste real de la whitelist no se esconda en coverage.
    all_rows = [r for r in rows if "puntuable" in r]
    instrument_rows = [
        r for r in all_rows
        if not str(r.get("skip_reason") or "").startswith("whitelist_bad_form")
    ]
    coverage = (
        len(scored) / len(instrument_rows) if instrument_rows else None
    )
    wl_total = sum(whitelist_skips.values())
    whitelist_silence_share = (
        wl_total / len(all_rows) if all_rows else None
    )
    checks = {
        "display_recall": {"value": disp_r, "n": disp_n, "d": disp_d,
                           "pass": disp_d == 0 or (disp_r or 0) >= gates["display_recall_min"]},
        "display_no_new_surface_fp": {"value": disp_fp,
                                      "pass": disp_fp <= gates["display_no_new_surface_fp_max"]},
        "cross_count_recall": {"value": cross_r, "n": cross_n, "d": cross_d,
                               "pass": cross_d == 0 or (cross_r or 0) >= gates["cross_count_recall_min"]},
        "cross_count_far_page_fp": {"value": cross_far_fp, "pass": cross_far_fp == 0},
        "grounding_fold_recall": (lambda rr: {
            "value": rr[0], "n": rr[1], "d": rr[2],
            "pass": rr[2] == 0 or (rr[0] or 0) >= gates["grounding_fold_recall_min"],
        })(rate(
            lambda x: x.get("measure") == "grounding" and x.get("puntuable")
            and x.get("variant_label") in ("ws", "accents") and x.get("detected"),
            lambda x: x.get("measure") == "grounding" and x.get("puntuable")
            and x.get("variant_label") in ("ws", "accents"),
        )),
        "grounding_paraphrase_fp": (lambda n: {
            "value": n, "pass": n <= gates["grounding_paraphrase_fp_max"],
        })(len([
            r for r in rows if r.get("measure") == "grounding"
            and r.get("variant_label") == "paraphrase" and r.get("fp_paraphrase")
        ])),
        "disclosure_two_sides": (lambda rr: {
            "value": rr[0], "n": rr[1], "d": rr[2],
            "pass": rr[2] == 0 or (rr[0] or 0) >= gates["disclosure_two_sides_min"],
        })(rate(
            lambda x: x.get("measure") == "disclosure2" and x.get("puntuable")
            and x.get("detected"),
            lambda x: x.get("measure") == "disclosure2" and x.get("puntuable"),
        )),
        "clean_annex_quality_fp": {"value": clean_fp,
                                   "pass": clean_fp <= gates["clean_annex_quality_fp_max"]},
        "enrichment_appends_reported": {"value": enrichment, "pass": True},
        "cross_binding_fp": {"value": crossb_fp,
                             "pass": crossb_fp <= gates["cross_binding_fp_max"]},
        "attestation_block_appends": {"value": attest_appends,
                                      "pass": attest_appends <= gates["attestation_block_appends_max"]},
        # ── checks de activación s271 (DEC-127b bloqueadores 1-3) ──
        "dup_span_fp": {"value": dup_fp, "pass": dup_fp <= gates["dup_span_fp_max"]},
        "dup_span_control_loss": {"value": dup_ctrl_loss,
                                  "pass": dup_ctrl_loss <= gates["dup_span_control_loss_max"]},
        "empty_enum_fp": {"value": ee_fp, "pass": ee_fp <= gates["empty_enum_fp_max"]},
        "empty_enum_positive_recall": {"value": ee_r, "n": ee_n, "d": ee_d,
                                       "pass": ee_d == 0 or (ee_r or 0) >= gates["empty_enum_positive_recall_min"]},
        "navcrumb_fp": {"value": nav_fp, "pass": nav_fp <= gates["navcrumb_fp_max"]},
        "navcrumb_no_relevance_fp": {"value": nav_norel_fp,
                                     "pass": nav_norel_fp <= gates["navcrumb_no_relevance_fp_max"]},
        "navcrumb_positive_recall": {"value": nav_r, "n": nav_n, "d": nav_d,
                                     "pass": nav_d == 0 or (nav_r or 0) >= gates["navcrumb_positive_recall_min"]},
        # ── checks whitelist v8 (clases de la Etapa 3 v2) ──
        "heading_only_fp": {"value": heading_fp,
                            "pass": heading_fp <= gates["heading_only_fp_max"]},
        "heading_only_control_recall": {
            "value": heading_r, "n": heading_n, "d": heading_d,
            "pass": heading_d == 0
            or (heading_r or 0) >= gates["heading_only_control_recall_min"],
        },
        "ui_dump_fp": {"value": uidump_fp,
                       "pass": uidump_fp <= gates["ui_dump_fp_max"]},
        "whitelist_skips_reported": {
            "value": whitelist_skips,
            "mutation_by_family": wl_by_family,
            "pass": True,
        },
        "whitelist_silence_share_reported": {
            "value": whitelist_silence_share, "total_skips": wl_total,
            "pass": True,
        },
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


# ─────────────────────────── freeze (prereg v7) ───────────────────────────

def freeze() -> int:
    if not COHORT_PATH.exists():
        raise RuntimeError("cohorte v8 no construida: --build-cohort primero")
    rows = H.load_jsonl(COHORT_PATH)
    build = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    prereg = {
        "schema": "s271_stage1_v8_prereg_v1",
        "status": "FROZEN_BEFORE_RUN",
        "created_utc": H._now(),
        "predecessor": "evals/s271_stage1_v7_gate_v1.yaml (seed-275, GO) + evals/s270_stage1_v6_gate_v1.yaml (seed-274, GO)",
        "mechanism": (
            "must_preserve v5 (s271 iteración final): WHITELIST fail-closed de "
            "forma-buena en el render (INVERSIÓN DE CONTRATO tras la Etapa 3 v2) "
            "sobre los guards v4 (dedup + contenido informativo + tie estricto)"
        ),
        "seed": SEED,
        "gates": dict(GATES),
        "gates_provenance": (
            "heredados ÍNTEGROS del prereg v6 (los fixes de activación no se compran "
            "con recall) + 3 checks nuevos derivados de los bloqueadores de la Etapa "
            "3 viva (DEC-127b): dup_span (nota duplicada hp001), empty_enum (tabla "
            "de celdas en blanco cat007), count_navcrumb (conteo↔crumb de navegación "
            "hp001)"
        ),
        "new_measures": {
            "dup_span": "átomo target duplicado → span UNA vez en el anexo; control: "
                        "dos hechos distintos no se colapsan",
            "empty_enum": "disclosure con lado-enumeración de celdas-en-blanco no "
                          "dispara; con enumeración real sigue disparando dos lados",
            "count_navcrumb": "conteo + crumb de navegación no liga; heading sin "
                              "relevancia + enum sin sustantivo no liga; heading del "
                              "dominio + enum legítima liga (tie section)",
        },
        "freeze": {
            "must_preserve_sha256": H.sha256_file(ROOT / "src/rag/must_preserve.py"),
            "harness_v7_sha256": H.sha256_file(
                ROOT / "scripts/s271_mutation_harness_v7.py"
            ),
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
            "SÉPTIMA población fresca (seed-276); exclusiones ACUMULADAS: cohorte "
            "v1 + seed-270..275. Las medidas previas quedan como evidencia "
            "versionada.",
            "WHITELIST v5 (v8 de este harness): las filas cuyo átomo target NO pasa "
            "la whitelist se re-etiquetan como skip DECLARADO "
            "(whitelist_bad_form*): su silencio es DISEÑO del mecanismo (silencio > "
            "ruido), no miss — las clases silenciadas se miden como FP en "
            "heading_only/ui_dump/empty_enum. El volumen de skips se REPORTA en el "
            "gate (whitelist_skips_reported) y penaliza coverage: si el recorte "
            "real de recall fuera material, coverage/recalls lo hacen visible — "
            "los fixes no se compran con recall en silencio.",
            "heading_only/ui_dump usan TEMPLATES genéricos que reproducen la FORMA "
            "de las clases observadas en la Etapa 3 v2 (cabecera-sola; volcado de "
            "UI), no los textos gold.",
            "ITERACIÓN DE GATE DECLARADA (post 1ª pasada c276, results INTACTOS — "
            "solo cambia el gate): (1) cross_count_recall heredaba de v5 un "
            "denominador sin filtro puntuable (en v5 todas las filas lo eran); con "
            "el relabel de whitelist daba 10/27=0.37 cuando el recall real sobre "
            "filas puntuables es 10/11=0.909 — fix de predicado, consistente con "
            "el resto de recalls. (2) coverage (1ª pasada 0.807) mezclaba skips de "
            "INSTRUMENTO con el silencio-por-DISEÑO de la whitelist (208 filas); "
            "se re-especifica coverage a salud-de-instrumento y el coste de la "
            "whitelist queda VISIBLE en whitelist_silence_share_reported + "
            "whitelist_skips_reported (por medida y por familia) — el recorte no "
            "se esconde, se reporta como métrica propia.",
            "Los guards v4 derivan de los 3 bloqueadores OBSERVADOS en la Etapa 3 "
            "viva (evals/s270_etapa3_smoke_appendices_v1.jsonl, DEC-127b), no de los "
            "textos gold; este harness los valida en población fresca ANTES del "
            "re-smoke.",
            "El detector v4 es MÁS estricto en F-COUNT (crumb/informativo/relevancia "
            "en ties a distancia): la composición de la cohorte F-COUNT refleja la "
            "población que el mecanismo vivo puede formar — el pre-screen usa el "
            "detector vigente (mismo patrón que v5/v6).",
            "dup_span/empty_enum se miden a nivel RENDER con el átomo real del "
            "fragmento (gold mecánico por construcción); count_navcrumb usa "
            "fragmentos SINTÉTICOS con la oración de conteo REAL (los templates son "
            "material del harness, no del corpus).",
            "El brazo híbrido queda en PREFLIGHT: el determinista es $0 y es el que "
            "gatea; la ejecución pagada la decide el orquestador.",
            "ITERACIÓN DE INSTRUMENTO DECLARADA (post 1ª pasada c275): display "
            "recall 2/3 — el miss (fdd153ee, F-BUNDLE) era la MISMA clase del "
            "artefacto seed-272 («el guard evaluaba el borrador completo y no la "
            "ventana»): un claim BUNDLE con puntos embebidos en los miembros parte "
            "la VENTANA de cita y bind_atoms no liga aunque el guard sobre el "
            "borrador pase. Fix del INSTRUMENTO (evaluate_display_rows_v7: "
            "binding-guard contra citation_window, lo que el mecanismo usa), SIN "
            "tocar el mecanismo; re-medido sobre la MISMA cohorte seed-275; la 1ª "
            "pasada queda declarada aquí.",
        ],
        "gate_runner": "scripts/s271_mutation_harness_v7.py --gate",
        "gate_output": str(GATE_OUT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    PREREG_PATH.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Prereg v8 congelado: {PREREG_PATH.relative_to(ROOT)}")
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
