#!/usr/bin/env python3
"""S274 Etapa 1 v9 — harness de mutaciones para los fixes Bloques C/D (prereg
evals/s274_bloquesCD_prereg_v2.yaml §P1; sucesor del s271 v8 seed-276 GO).

Extiende el harness v7/v8 (que se importa y reusa: builders, templates, mutadores,
evaluadores) con las CLASES NUEVAS POR-FIX del prereg P1, todas derivadas de los
DIAGNÓSTICOS s274 (serving-view diag + funnel N=3), jamás de los textos gold:

  defline_eq       (D1a, MP_DEFLINE_EQ) esquema de definición con ``=`` espaciado
                   re-renderizado desde el átomo REAL → detecta con flag ON (recall);
                   con flag OFF 0 detección (byte-idéntico); asignaciones de config
                   ``label = <número>`` NO anexan sobre borrador limpio (FP=0).
  f_relation       (D1b det-side, MP_HYBRID_DETECT) el VALIDADOR en código de la
                   familia F-RELATION: acepta cláusulas ancladas (número-con-unidad /
                   cabeza de definición) — shape + mecanismo sobre borradores
                   qualifier_loss/definition_loss; rechaza títulos y prosa sin ancla
                   (FP=0); con flag OFF rechaza todo. El SCORING del brazo híbrido
                   (propuestas Haiku) queda en PREFLIGHT — lo paga el orquestador.
  served_uncited   (C2, MP_SERVED_BINDING) fragmento SERVIDO-NO-CITADO con borrador
                   limpio → 0 anexos (re-mide la clase seed-270 de clean-FP con el
                   umbral REFORZADO ≥3); recall del positivo REPORTADO (no gatea —
                   el umbral reforzado compra precisión a costa de recall, declarado).
  distinctive      (D2, MP_DISTINCTIVE_TOKEN) ventana con 1 token propio GENÉRICO
                   (re-clase seed-271) NO liga (FP=0); 1 token DISTINTIVO (dígito /
                   acrónimo en superficie) liga con flag ON y NO con flag OFF.
  stem             (D1c, MP_STEM_BINDING) variante de plural es/en de un token propio
                   + un 2º token exacto → liga con flag ON, no con OFF; la variante
                   SOLA (clase seed-271 vía stem) sigue sin ligar (FP=0).
  verb_trigger     (Fable-M1, MP_MANDATORY_VERB_TRIGGER) cláusula imperativa con
                   gatillo-VERBO (``evite``) pasa la whitelist con flag ON y no con
                   OFF; gatillo-SUSTANTIVO sin verbo finito JAMÁS pasa (FP=0). La
                   clase heading_only y el clean MANDATORY se re-gatean en los
                   heredados (que corren con el flag ON).
  callout          (C1, COVERAGE_MANDATORY_CALLOUT) chunk de coverage sintético desde
                   el fragmento real: chunk LIMPIO (sin gatillos fuera de la card)
                   → 0 cards espurias (FP=0); con gatillo aislado ≤600 fuera de la
                   card → card presente, receipt exacto, clase propia, ≤600,
                   local_semantic_validated=False; con flag OFF el campo no existe.

Población FRESCA seed=277 con exclusiones ACUMULADAS de TODAS las cohortes previas
(v1 + seed-270..276). Los gates v8 heredados corren ÍNTEGROS con los 4 flags
deterministas del bloque C/D activos (MP_DEFLINE_EQ · MP_STEM_BINDING ·
MP_DISTINCTIVE_TOKEN · MP_MANDATORY_VERB_TRIGGER = la config candidata a ship en la
ruta del harness; MP_SERVED_BINDING/MP_HYBRID_DETECT/COVERAGE_MANDATORY_CALLOUT son
no-op en esta ruta y se miden en sus clases propias): un heredado en NO-GO mata el
bloque D ENTERO; cada clase nueva gatea SOLO su fix (independencia por-fix).

El clean-FP de los fixes de binding (C2/D1c/D2/verb-trigger) se re-mide DOS veces:
en su clase propia (arriba) y en el clean heredado (que corre flags-on) — el fix no
se compra con ruido en silencio.

Uso:
  python scripts/s274_mutation_harness_v9.py --build-cohort   # GET-only, $0
  python scripts/s274_mutation_harness_v9.py --freeze         # prereg v9
  python scripts/s274_mutation_harness_v9.py --run            # brazo det ($0)
  python scripts/s274_mutation_harness_v9.py --run --hybrid   # PREFLIGHT (0 pagos)
  python scripts/s274_mutation_harness_v9.py --gate           # veredicto por-fix
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag import must_preserve as mp  # noqa: E402
from src.rag import post_rerank_coverage as prc  # noqa: E402
from src.rag.mp_lexicon import mandatory_triggers, sentence_spans  # noqa: E402
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H7 = _load("s271_mutation_harness_v7", "scripts/s271_mutation_harness_v7.py")
H5 = H7.H5
H = H7.H  # harness s269 base (run_mechanism ya rebindado a la selección v2)

EVALS = ROOT / "evals"
COHORT_PATH = EVALS / "s274_mutation_cohort_v9.jsonl"
BUILD_REPORT_PATH = EVALS / "s274_mutation_cohort_v9_build.json"
PREREG_PATH = EVALS / "s274_stage1_v9_prereg_v1.yaml"
RESULTS_DET_PATH = EVALS / "s274_stage1_v9_results_det_c277.jsonl"
GATE_OUT_PATH = EVALS / "s274_stage1_v9_gate_v1.yaml"

SEED = 277

# ─────────────────────────── flags por-fix (prereg v2) ───────────────────────────

FLAG_NAMES = (
    "COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING", "MP_DEFLINE_EQ",
    "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
    "MP_MANDATORY_VERB_TRIGGER",
)
# Config candidata para la ruta del harness: los 4 flags que CAMBIAN la conducta
# determinista de must_preserve (detección/whitelist/binding). Los otros 3 son
# no-op en run_mechanism (C2 solo actúa en apply sobre no-citados; el híbrido exige
# cliente; la card vive en la lane de coverage) y se miden en sus clases propias.
DET_FLAGS_ON = (
    "MP_DEFLINE_EQ", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
    "MP_MANDATORY_VERB_TRIGGER",
)


@contextmanager
def mp_flags(*on: str):
    """Contexto de flags estricto: TODOS los flags s274 limpios salvo los pedidos."""
    unknown = set(on) - set(FLAG_NAMES)
    if unknown:
        raise ValueError(f"flags desconocidos: {sorted(unknown)}")
    prev = {name: os.environ.get(name) for name in FLAG_NAMES}
    try:
        for name in FLAG_NAMES:
            os.environ.pop(name, None)
        for name in on:
            os.environ[name] = "on"
        yield
    finally:
        for name, val in prev.items():
            if val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = val


# ─────────────────────────── medidas / gates ───────────────────────────

INHERITED_MEASURES = frozenset({
    "mutation", "clean", "display", "cross_count", "grounding", "disclosure2",
    "cross", "attestation", "dup_span", "dup_control", "empty_enum", "ui_dump",
    "navcrumb", "heading_only",
})
NEW_MEASURES = frozenset({
    "defline_eq", "f_relation", "served_uncited", "distinctive", "stem",
    "verb_trigger", "callout",
})

V9_GATES = {
    # D1a — MP_DEFLINE_EQ
    "defline_eq_recall_min": 0.80,
    "defline_eq_off_detect_fp_max": 0,
    "defline_eq_assignment_fp_max": 0,
    # D1b det-side — MP_HYBRID_DETECT (validador F-RELATION en código)
    "f_relation_shape_recall_min": 0.80,
    "f_relation_mechanism_recall_min": 0.80,
    "f_relation_defhead_recall_min": 0.80,
    "f_relation_title_fp_max": 0,
    "f_relation_prose_fp_max": 0,
    "f_relation_off_fp_max": 0,
    # C2 — MP_SERVED_BINDING (re-clase seed-270 con umbral reforzado)
    "served_uncited_clean_fp_max": 0,
    # D2 — MP_DISTINCTIVE_TOKEN (re-clase seed-271 = 0)
    "distinctive_generic_fp_max": 0,
    "distinctive_positive_recall_min": 0.80,
    "distinctive_off_fp_max": 0,
    # D1c — MP_STEM_BINDING
    "stem_positive_recall_min": 0.80,
    "stem_single_token_fp_max": 0,
    "stem_off_fp_max": 0,
    # Fable-M1 — MP_MANDATORY_VERB_TRIGGER
    "verb_trigger_recall_min": 0.80,
    "verb_trigger_noun_fp_max": 0,
    "verb_trigger_off_fp_max": 0,
    # C1 — COVERAGE_MANDATORY_CALLOUT
    "callout_spurious_fp_max": 0,
    "callout_invalid_card_fp_max": 0,
    "callout_positive_recall_min": 0.80,
    "callout_off_fp_max": 0,
}
# gates heredados ÍNTEGROS (v8 = H7.GATES incluye v5/v6/v7/v8) + clases nuevas
GATES = dict(H7.GATES) | V9_GATES

# Mapa fix → checks propios (gate POR-FIX independiente: un NO-GO mata SOLO su fix;
# los heredados en NO-GO matan el bloque D entero — prereg v2 §P1.gate).
FIX_CHECKS = {
    "MP_DEFLINE_EQ": (
        "defline_eq_recall", "defline_eq_off_detect_fp", "defline_eq_assignment_fp",
    ),
    "MP_HYBRID_DETECT": (
        "f_relation_shape_recall", "f_relation_mechanism_recall",
        "f_relation_defhead_recall", "f_relation_title_fp", "f_relation_prose_fp",
        "f_relation_off_fp",
    ),
    "MP_SERVED_BINDING": ("served_uncited_clean_fp",),
    "MP_DISTINCTIVE_TOKEN": (
        "distinctive_generic_fp", "distinctive_positive_recall", "distinctive_off_fp",
    ),
    "MP_STEM_BINDING": (
        "stem_positive_recall", "stem_single_token_fp", "stem_off_fp",
    ),
    "MP_MANDATORY_VERB_TRIGGER": (
        "verb_trigger_recall", "verb_trigger_noun_fp", "verb_trigger_off_fp",
    ),
    "COVERAGE_MANDATORY_CALLOUT": (
        "callout_spurious_fp", "callout_invalid_card_fp",
        "callout_positive_recall", "callout_off_fp",
    ),
}
# verb-trigger además referencia los checks heredados que su spec cita
# (heading_only 0 FP + clean MANDATORY íntegro — corren con el flag ON).
VT_INHERITED_REFS = ("heading_only_fp", "clean_annex_quality_fp")
BLOCK_D_FIXES = (
    "MP_DEFLINE_EQ", "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
)

TEMPLATES_V9_VERSION = "s274_v9_templates_v1"
TEMPLATES_V9 = {
    "defline_eq_line": "{label} = {desc}",
    "defline_assign_line": "{label} = {value}",
    "defline_clean_draft": (
        "Según el manual, los campos {l1} y {l2} se configuran juntos [F1]."
    ),
    "relation_qualifier_draft": (
        "Según el manual, el valor configurado es {num} {unit} [F1]."
    ),
    "relation_defhead_draft": (
        "Según el manual, la {label} se aplica al procesar la regla [F1]."
    ),
    "token_window": "El {token} aparece indicado en el documento [F1].",
    "stem_window": "El manual menciona {variant} junto a {second} [F1].",
    "verb_trigger_clause": (
        "Al configurar {t1} y {t2} evite los ajustes contradictorios durante la "
        "puesta en marcha."
    ),
    "noun_trigger_clause": (
        "Advertencia importante sobre {t1} y {t2} del equipo instalado en la sala "
        "técnica."
    ),
}


def templates_sha256_v9() -> str:
    blob = json.dumps(
        {"version": TEMPLATES_V9_VERSION, "templates": TEMPLATES_V9},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ─────────────────────────── build cohorte v9 (seed 277) ───────────────────────────

def prior_cohort_paths() -> list[tuple[str, Path]]:
    """TODAS las cohortes previas (v1 + seed-270..276) — exclusiones acumuladas."""
    return [
        ("v1_cohort_docs_exclusion", H.COHORT_V1_PATH),
        ("seed270_cohort_docs_exclusion", H.COHORT_SEED270_PATH),
        ("seed271_cohort_docs_exclusion", H.COHORT_SEED271_PATH),
        ("seed272_cohort_docs_exclusion", H.COHORT_PATH),          # cohorte v4
        ("seed273_cohort_docs_exclusion", H5.COHORT_SEED273_PATH),  # cohorte v5
        ("seed274_cohort_docs_exclusion", H5.COHORT_PATH),          # cohorte v6
        ("seed275_cohort_docs_exclusion", H7.COHORT_V7_PATH),       # cohorte v7
        ("seed276_cohort_docs_exclusion", H7.COHORT_PATH),          # cohorte v8
    ]


def build_cohort() -> int:
    import httpx

    v1 = H._load_v1_builder()
    rng = random.Random(SEED)
    table = os.environ.get("CHUNKS_TABLE", "chunks_v2")

    prior = []
    for label, path in prior_cohort_paths():
        docs = sorted({r["document_id"] for r in H.load_jsonl(path)})
        if not docs:
            raise RuntimeError(f"cohorte previa vacía/ausente: {path.name}")
        prior.append((label, path, docs))

    with mp_flags():  # pre-screen con el detector de PROD (flags s274 OFF)
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
            print(f"  excluidos: {len(excluded & set(corpus))} | "
                  f"elegibles: {len(eligible)}")

            doc_order = v1.stratified_doc_order(eligible, rng)
            pools = {f: [] for f in H.FAMILIES}
            per_doc_family: dict[tuple[str, str], int] = {}
            docs_used: list[str] = []
            fragments_screened = 0

            def buckets_full() -> bool:
                return all(
                    len(pools[f]) >= H.TARGET_PER_FAMILY for f in H.FAMILIES
                )

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
        "schema": "s274_mutation_cohort_v9_build_v1",
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
    print(f"Cohorte v9: {COHORT_PATH.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"Composición: {composition}")
    return 0


# ─────────────────────────── helpers de las clases nuevas ───────────────────────────

_SPACED_DASH_RX = re.compile(r"\s[-–—]\s")


def _defline_pairs_from_span(span: str) -> list[tuple[str, str]]:
    """Pares (label, desc) de las líneas de definición ``:``/guion del span REAL,
    filtrados para que el re-render ``label = desc`` sea OFF-inerte (sin ``:``/``=``/
    guion espaciado residual que re-dispare _DEFLINE con flag off) y con desc
    textual (≥3 letras — whitelist-compatible)."""
    pairs: list[tuple[str, str]] = []
    for line in (span or "").splitlines():
        m = mp._DEFLINE.match(line)
        if not m:
            continue
        label = (m.group(1) or "").strip().strip("*").strip()
        desc = (m.group(2) or "").strip().strip("*").strip()
        if not label or not desc:
            continue
        if any(ch in label for ch in ":=") or "=" in desc or ":" in desc:
            continue
        if _SPACED_DASH_RX.search(desc) or _SPACED_DASH_RX.search(label):
            continue
        if not mp._LABEL_TOKEN_RX.search(desc):
            continue
        # FIX DE INSTRUMENTO declarado (1ª pasada c277: 1 fp_off): la línea
        # re-renderizada se testea DIRECTAMENTE contra los parsers flag-off — una
        # etiqueta con marcador de lista numerada («2. **+ y −») re-formaba un run
        # de _BULLET sin necesitar el separador '='. Off-inercia por construcción.
        rendered = TEMPLATES_V9["defline_eq_line"].format(label=label, desc=desc)
        if mp._BULLET.match(rendered) or mp._DEFLINE.match(rendered):
            continue
        pairs.append((label, desc))
    return pairs


def evaluate_defline_eq_rows(row: dict) -> list[dict]:
    """defline_eq (D1a): esquema ``label = desc`` re-renderizado desde el átomo
    F-BUNDLE real → bundle detectado con flag ON (recall) / 0 con OFF; asignación
    ``label = <número>`` no anexa sobre borrador limpio (FP render-level)."""
    if row["familia"] != mp.FAMILY_BUNDLE:
        return []
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    pairs = _defline_pairs_from_span(row["atom"].get("span_text") or "")
    if len(pairs) < 2:
        return [base | {
            "key": f"{row['fragment_id']}|defline_eq",
            "measure": "defline_eq", "puntuable": False,
            "skip_reason": "no_defline_pairs",
        }]
    header = ((row["atom"].get("meta") or {}).get("header") or "").strip()
    lines = ([f"## {header}"] if header else [])
    lines += [
        TEMPLATES_V9["defline_eq_line"].format(label=l, desc=d) for l, d in pairs
    ]
    eq_text = "\n".join(lines)
    labels_fold = {mp._fold(l) for l, _d in pairs}

    def _bundles(text: str) -> list[dict]:
        return [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_BUNDLE]

    with mp_flags("MP_DEFLINE_EQ"):
        bundles_on = _bundles(eq_text)
        detected = any(
            len({mp._fold(x) for x in (a["meta"].get("members") or [])}
                & labels_fold) >= 2
            for a in bundles_on
        )
        assign_text = "\n".join(
            TEMPLATES_V9["defline_assign_line"].format(label=l, value=i + 2)
            for i, (l, _d) in enumerate(pairs)
        )
        atoms_assign = mp.detect_atoms(assign_text)
        draft = TEMPLATES_V9["defline_clean_draft"].format(
            l1=pairs[0][0], l2=pairs[1][0]
        )
        appendix, _ = H5.run_mechanism_v2(atoms_assign, draft, {1}, 1)
        fp_assignment = bool(appendix)
    with mp_flags():
        fp_off = bool(_bundles(eq_text))
    return [
        base | {
            "key": f"{row['fragment_id']}|defline_eq|on",
            "measure": "defline_eq", "variant_label": "eq_on",
            "puntuable": True, "detected": detected,
        },
        base | {
            "key": f"{row['fragment_id']}|defline_eq|off",
            "measure": "defline_eq", "variant_label": "eq_off",
            "puntuable": True, "fp_off_detect": fp_off,
        },
        base | {
            "key": f"{row['fragment_id']}|defline_eq|assignment",
            "measure": "defline_eq", "variant_label": "assignment",
            "puntuable": True, "fp_assignment": fp_assignment,
        },
    ]


def _relation_qualifier_candidate(texto: str) -> tuple[str, str, str] | None:
    """(oración, num, unit): 1ª oración-cláusula de una línea con número-con-unidad
    (valor ∉ {0,1}) que pasa la vara de whitelist — candidata F-RELATION."""
    for s, e in sentence_spans(texto):
        sent = texto[s:e]
        if "\n" in sent or len(sent) > 400:
            continue
        m_ok = None
        for m in mp._RX_NUM_UNIT.finditer(sent):
            if mp._num_val(m.group(1)) not in (0.0, 1.0):
                m_ok = m
                break
        if m_ok is None:
            continue
        if not mp._clause_form(mp._strip_markup(sent)):
            continue
        return sent, m_ok.group(1), m_ok.group(2)
    return None


def _relation_defhead_candidate(texto: str) -> str | None:
    """Línea ``Etiqueta de ≥2 tokens: definición-cláusula`` SIN número-con-unidad —
    candidata definicional (anatomía obl_7aa7/b2043, forma genérica)."""
    for _s, _e, line in mp._line_spans(texto):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = mp._DEFLINE.match(line)
        if not m:
            continue
        label = (m.group(1) or "").strip()
        if len(mp._content_tokens(label, min_len=2)) < 2:
            continue
        if mp._RX_NUM_UNIT.search(line):
            continue
        if not mp._clause_form(mp._strip_markup(line)):
            continue
        span = line.rstrip()
        if span and span in texto:
            return span
    return None


def _relation_prose_candidate(texto: str) -> str | None:
    """Oración-cláusula SIN ancla (sin número-con-unidad, <2 tokens distintivos,
    sin cabeza de definición) — control negativo de shape."""
    for s, e in sentence_spans(texto):
        sent = texto[s:e]
        if "\n" in sent or len(sent) > 300:
            continue
        if mp._RX_NUM_UNIT.search(sent):
            continue
        if not mp._clause_form(mp._strip_markup(sent)):
            continue
        distinct = [
            t for t in set(mp._content_tokens(sent, min_len=2))
            if mp._distinctive_token(t, sent)
        ]
        if len(distinct) >= 2 or mp._relation_defhead(sent):
            continue
        return sent
    return None


def evaluate_f_relation_rows(row: dict) -> list[dict]:
    """f_relation (D1b, lado determinista del contrato): shape del validador en
    código + mecanismo sobre borradores qualifier_loss/definition_loss + controles
    título/prosa/flag-off. El brazo híbrido (propuestas Haiku) queda en PREFLIGHT."""
    texto = row["texto"]
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    results: list[dict] = []
    cand = _relation_qualifier_candidate(texto)
    dhead = _relation_defhead_candidate(texto)
    prose = _relation_prose_candidate(texto)
    heading = next(
        (
            line.rstrip() for _s, _e, line in mp._line_spans(texto)
            if line.lstrip().startswith("#") and len(line.strip()) > 4
        ),
        None,
    )
    if cand is None and dhead is None:
        return [base | {
            "key": f"{row['fragment_id']}|f_relation",
            "measure": "f_relation", "puntuable": False,
            "skip_reason": "no_relation_candidate",
        }]
    with mp_flags("MP_HYBRID_DETECT"):
        if cand is not None:
            sent, num, unit = cand
            atom = mp._atom_from_verbatim_span("F-RELATION", sent, texto)
            results.append(base | {
                "key": f"{row['fragment_id']}|f_relation|shape",
                "measure": "f_relation", "variant_label": "shape",
                "puntuable": True, "detected": atom is not None,
            })
            if atom is not None:
                draft = TEMPLATES_V9["relation_qualifier_draft"].format(
                    num=num, unit=unit
                )
                catom = copy.deepcopy(atom)
                catom.setdefault("meta", {})["fragment_number"] = 1
                window = mp.citation_window(draft, 1)
                appendix = ""
                if window.strip() and mp.atom_exigible_in(catom, window) and (
                    not mp.atom_satisfied(catom, draft)
                ):
                    appendix = mp.render_appendix([catom], draft)
                results.append(base | {
                    "key": f"{row['fragment_id']}|f_relation|qualifier_loss",
                    "measure": "f_relation", "variant_label": "qualifier_loss",
                    "puntuable": True, "detected": sent in appendix,
                })
        if dhead is not None:
            atom = mp._atom_from_verbatim_span("F-RELATION", dhead, texto)
            detected = False
            if atom is not None:
                m = mp._DEFLINE.match(dhead)
                label = (m.group(1) or "").strip() if m else ""
                draft = TEMPLATES_V9["relation_defhead_draft"].format(label=label)
                catom = copy.deepcopy(atom)
                catom.setdefault("meta", {})["fragment_number"] = 1
                window = mp.citation_window(draft, 1)
                if window.strip() and mp.atom_exigible_in(catom, window) and (
                    not mp.atom_satisfied(catom, draft)
                ):
                    detected = dhead in mp.render_appendix([catom], draft)
            results.append(base | {
                "key": f"{row['fragment_id']}|f_relation|definition_loss",
                "measure": "f_relation", "variant_label": "definition_loss",
                "puntuable": True, "detected": detected,
                "shape_accepted": atom is not None,
            })
        if heading is not None and heading in texto:
            results.append(base | {
                "key": f"{row['fragment_id']}|f_relation|title",
                "measure": "f_relation", "variant_label": "title",
                "puntuable": True,
                "fp_title": mp._atom_from_verbatim_span(
                    "F-RELATION", heading, texto
                ) is not None,
            })
        if prose is not None:
            results.append(base | {
                "key": f"{row['fragment_id']}|f_relation|prose",
                "measure": "f_relation", "variant_label": "prose",
                "puntuable": True,
                "fp_prose": mp._atom_from_verbatim_span(
                    "F-RELATION", prose, texto
                ) is not None,
            })
    with mp_flags():
        off_span = cand[0] if cand is not None else dhead
        results.append(base | {
            "key": f"{row['fragment_id']}|f_relation|off",
            "measure": "f_relation", "variant_label": "off",
            "puntuable": True,
            "fp_off": mp._atom_from_verbatim_span(
                "F-RELATION", off_span, texto
            ) is not None,
        })
    return results


def evaluate_served_uncited_rows(row: dict) -> list[dict]:
    """served_uncited (C2): el fragmento del átomo se trata como SERVIDO-NO-CITADO
    (fragmento 2; el borrador cita [F1]). Clean: claim que restata el átomo → 0
    anexos (re-clase seed-270, umbral reforzado). Positivo (REPORTADO, no gatea):
    claim mutado → el target anexa con cita [F2]."""
    mutations = H.generate_mutations(row)
    if not mutations:
        return []
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    results: list[dict] = []
    with mp_flags("MP_SERVED_BINDING"):
        atoms = mp.detect_atoms(row["texto"])
        draft_clean = H.render_draft(mutations[0]["claim_clean"], 0)
        missing: list[dict] = []
        for atom in atoms:
            catom = copy.deepcopy(atom)
            if not mp._served_uncited_exigible(catom, draft_clean):
                continue
            if mp.atom_satisfied(catom, draft_clean):
                continue
            catom.setdefault("meta", {})["fragment_number"] = 2
            missing.append(catom)
        appendix = mp.render_appendix(missing, draft_clean)
        results.append(base | {
            "key": f"{row['fragment_id']}|served_uncited|clean",
            "measure": "served_uncited", "variant_label": "clean",
            "puntuable": True,
            "fp_clean": bool(appendix),
            "appended_families": sorted({
                str(a.get("family")) for a in mp._select_for_appendix(
                    missing, draft_clean
                )
            }) if appendix else [],
        })
        target = H._locate_target(atoms, row["atom"])
        if target is not None and mp.atom_good_form(target):
            draft_mut = H.render_draft(mutations[0]["claim_mut"], 0)
            catom = copy.deepcopy(target)
            exigible = mp._served_uncited_exigible(catom, draft_mut)
            detected = False
            if exigible and not mp.atom_satisfied(catom, draft_mut):
                catom.setdefault("meta", {})["fragment_number"] = 2
                ap = mp.render_appendix([catom], draft_mut)
                span = (row["atom"].get("span_text") or "").strip()
                detected = bool(ap) and span in ap and "[F2]" in ap
            results.append(base | {
                "key": f"{row['fragment_id']}|served_uncited|positive",
                "measure": "served_uncited", "variant_label": "positive",
                "puntuable": True, "detected": detected,
                "reinforced_exigible": exigible,
            })
    return results


def _own_token_sets(target: dict) -> tuple[set[str], str] | None:
    """(tokens PROPIOS, modo) según el contrato de la familia (espejo de
    atom_exigible_in): BUNDLE → header∪members (min_len=2, ventana min_len=2);
    MANDATORY → contexto procedimental (ventana min_len=3)."""
    meta = target.get("meta") or {}
    if target.get("family") == mp.FAMILY_BUNDLE:
        propio = set(mp._content_tokens(meta.get("header") or "", min_len=2))
        for label in meta.get("members") or []:
            propio.update(mp._content_tokens(label, min_len=2))
        return propio, "short"
    if target.get("family") == mp.FAMILY_MANDATORY:
        return set(meta.get("procedural_context_tokens") or []), "long"
    return None


def _window_matched(propio: set[str], window: str, mode: str) -> set[str]:
    clean = mp._FRAG_CITE.sub(" ", window)
    tokens = set(mp._content_tokens(clean, min_len=2 if mode == "short" else 3))
    return {t for t in propio if t in tokens}


def evaluate_distinctive_rows(row: dict) -> list[dict]:
    """distinctive (D2): ventana de 1 token propio GENÉRICO no liga (re-clase
    seed-271, FP=0); 1 token DISTINTIVO (dígito / acrónimo en superficie) liga con
    flag ON y NO con flag OFF."""
    if row["familia"] not in (mp.FAMILY_BUNDLE, mp.FAMILY_MANDATORY):
        return []
    with mp_flags("MP_DISTINCTIVE_TOKEN"):
        atoms = mp.detect_atoms(row["texto"])
    target = H._locate_target(atoms, row["atom"])
    if target is None:
        return []
    sets = _own_token_sets(target)
    if sets is None:
        return []
    propio, mode = sets
    span = target.get("span_text") or ""
    acronyms = {mp._fold(m.group()) for m in mp._ACRONYM_RX.finditer(span)}
    distinctive = sorted(
        t for t in propio if mp._HAS_DIGIT_RX.search(t) or t in acronyms
    )
    generic = sorted(
        t for t in propio
        if t.isalpha() and len(t) >= 4 and t not in distinctive
    )
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }

    def _solo_window(tok: str) -> str | None:
        w = TEMPLATES_V9["token_window"].format(token=tok)
        return w if _window_matched(propio, w, mode) == {tok} else None

    results: list[dict] = []
    g_window = next(
        (w for t in generic if (w := _solo_window(t)) is not None), None
    )
    if g_window is not None:
        with mp_flags("MP_DISTINCTIVE_TOKEN"):
            results.append(base | {
                "key": f"{row['fragment_id']}|distinctive|generic",
                "measure": "distinctive", "variant_label": "generic",
                "puntuable": True,
                "fp_generic": mp.atom_exigible_in(target, g_window),
            })
    d_window = next(
        (w for t in distinctive if (w := _solo_window(t)) is not None), None
    )
    if d_window is not None:
        with mp_flags("MP_DISTINCTIVE_TOKEN"):
            on_exigible = mp.atom_exigible_in(target, d_window)
        with mp_flags():
            off_exigible = mp.atom_exigible_in(target, d_window)
        results.append(base | {
            "key": f"{row['fragment_id']}|distinctive|positive",
            "measure": "distinctive", "variant_label": "positive",
            "puntuable": True, "detected": on_exigible,
        })
        results.append(base | {
            "key": f"{row['fragment_id']}|distinctive|off",
            "measure": "distinctive", "variant_label": "off",
            "puntuable": True, "fp_off": off_exigible,
        })
    if not results:
        results.append(base | {
            "key": f"{row['fragment_id']}|distinctive",
            "measure": "distinctive", "puntuable": False,
            "skip_reason": "no_solo_window_token",
        })
    return results


def _plural_variant(token: str) -> str:
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token + "s"


def evaluate_stem_rows(row: dict) -> list[dict]:
    """stem (D1c): variante de plural de un token propio + 2º token exacto → liga
    SOLO con el flag; la variante SOLA (seed-271 vía stem) sigue sin ligar."""
    if row["familia"] not in (mp.FAMILY_BUNDLE, mp.FAMILY_MANDATORY):
        return []
    with mp_flags("MP_STEM_BINDING"):
        atoms = mp.detect_atoms(row["texto"])
    target = H._locate_target(atoms, row["atom"])
    if target is None:
        return []
    sets = _own_token_sets(target)
    if sets is None:
        return []
    propio, mode = sets
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    alpha = sorted(t for t in propio if t.isalpha() and len(t) >= 4)
    pick = None
    for t in alpha:
        variant = _plural_variant(t)
        if variant == t or variant in propio:
            continue
        for t2 in alpha:
            if t2 == t:
                continue
            window = TEMPLATES_V9["stem_window"].format(variant=variant, second=t2)
            if _window_matched(propio, window, mode) != {t2}:
                continue
            pick = (t, variant, t2, window)
            break
        if pick:
            break
    if pick is None:
        return [base | {
            "key": f"{row['fragment_id']}|stem",
            "measure": "stem", "puntuable": False,
            "skip_reason": "no_stem_pair",
        }]
    _t, variant, _t2, window = pick
    with mp_flags():
        if mp.atom_exigible_in(target, window):
            return [base | {
                "key": f"{row['fragment_id']}|stem",
                "measure": "stem", "puntuable": False,
                "skip_reason": "off_already_binds",
            }]
    with mp_flags("MP_STEM_BINDING"):
        on_exigible = mp.atom_exigible_in(target, window)
        solo = TEMPLATES_V9["token_window"].format(token=variant)
        fp_single = (
            not _window_matched(propio, solo, mode)
            and mp.atom_exigible_in(target, solo)
        )
    with mp_flags():
        off_exigible = mp.atom_exigible_in(target, window)
    return [
        base | {
            "key": f"{row['fragment_id']}|stem|positive",
            "measure": "stem", "variant_label": "positive",
            "puntuable": True, "detected": on_exigible,
        },
        base | {
            "key": f"{row['fragment_id']}|stem|single",
            "measure": "stem", "variant_label": "single",
            "puntuable": True, "fp_single": fp_single,
        },
        base | {
            "key": f"{row['fragment_id']}|stem|off",
            "measure": "stem", "variant_label": "off",
            "puntuable": True, "fp_off": off_exigible,
        },
    ]


def _verb_trigger_pair(row: dict) -> tuple[str, str] | None:
    banned = set(mp._FINITE_VERB_SET) | set(mp._MANDATORY_TERMS)
    picks = [
        t for t in (row["atom"].get("anchor_tokens") or [])
        if t.isalpha() and len(t) >= 4 and t not in banned
        and "evit" not in t and t not in H._UNIT_SURFACE_FORMS
    ]
    if len(picks) < 2:
        return None
    return picks[0], picks[1]


def evaluate_verb_trigger_rows(row: dict) -> list[dict]:
    """verb_trigger (Fable-M1): cláusula imperativa con gatillo-VERBO pasa la
    whitelist con flag ON y no con OFF; gatillo-SUSTANTIVO sin verbo finito jamás."""
    pair = _verb_trigger_pair(row)
    if pair is None:
        return []
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }
    clause = TEMPLATES_V9["verb_trigger_clause"].format(t1=pair[0], t2=pair[1])
    noun_clause = TEMPLATES_V9["noun_trigger_clause"].format(
        t1=pair[0], t2=pair[1]
    )
    atom = {"family": mp.FAMILY_MANDATORY, "span_text": clause, "meta": {}}
    noun_atom = {
        "family": mp.FAMILY_MANDATORY, "span_text": noun_clause, "meta": {},
    }
    with mp_flags():
        if mp.atom_good_form(atom):
            # colisión: algún token elegido ES verbo finito → el caso no aísla
            return [base | {
                "key": f"{row['fragment_id']}|verb_trigger",
                "measure": "verb_trigger", "puntuable": False,
                "skip_reason": "finite_verb_collision",
            }]
        fp_off = False  # por construcción (guard anterior)
    with mp_flags("MP_MANDATORY_VERB_TRIGGER"):
        detected = mp.atom_good_form(atom)
        fp_noun = mp.atom_good_form(noun_atom)
    return [
        base | {
            "key": f"{row['fragment_id']}|verb_trigger|on",
            "measure": "verb_trigger", "variant_label": "on",
            "puntuable": True, "detected": detected,
        },
        base | {
            "key": f"{row['fragment_id']}|verb_trigger|off",
            "measure": "verb_trigger", "variant_label": "off",
            "puntuable": True, "fp_off": fp_off,
        },
        base | {
            "key": f"{row['fragment_id']}|verb_trigger|noun",
            "measure": "verb_trigger", "variant_label": "noun",
            "puntuable": True, "fp_noun": fp_noun,
        },
    ]


def _coverage_chunk_for(row: dict) -> dict | None:
    """Chunk de coverage sintético desde el fragmento REAL: card del selector =
    primera oración; el resto del contenido queda fuera de la vista servida
    (estructura espejo del hallazgo C1, material del corpus fresco)."""
    content = row["texto"]
    spans = sentence_spans(content)
    if not spans:
        return None
    start, end = spans[0]
    if end - start < 10 or end >= len(content):
        return None
    row_id = f"v9-{row['fragment_id']}"
    return {
        "id": row_id,
        "content": content,
        "source_file": row.get("source_file") or "manual.pdf",
        "retrieval_lane": STRUCTURAL_LANE,
        "structural_neighbor_validated": True,
        "local_semantic_validated": True,
        "coverage_cards": [{
            "candidate_id": row_id,
            "start": start,
            "end": end,
            "quote": content[start:end],
            "exact_source_span_validated": True,
        }],
    }


def evaluate_callout_rows(row: dict) -> list[dict]:
    """callout (C1): chunk de coverage LIMPIO (sin gatillos fuera de la card) → 0
    cards espurias; gatillo AISLADO ≤600 fuera de la card → card válida (receipt
    exacto, clase propia, ≤600, sin validación semántica heredada); flag OFF → el
    campo no existe."""
    chunk = _coverage_chunk_for(row)
    if chunk is None:
        return []
    content = chunk["content"]
    # los spans SERVIDOS reales (con la expansión de fila lógica) definen "fuera"
    served = prc._build_served_coverage_cards(chunk)
    covered = [(int(c["start"]), int(c["end"])) for c in served]
    spans = sentence_spans(content)
    outside = [
        (s, e) for s, e in spans
        if not any(s < c_end and c_start < e for c_start, c_end in covered)
        and mandatory_triggers(content[s:e])
    ]
    base = {
        "fragment_id": row["fragment_id"], "familia": row["familia"],
        "document_id": row["document_id"],
    }

    def _isolated(idx: int) -> bool:
        s, e = outside[idx]
        if idx > 0 and not prc._CALLOUT_GAP_ALNUM.search(
            content[outside[idx - 1][1]:s]
        ):
            return False
        if idx + 1 < len(outside) and not prc._CALLOUT_GAP_ALNUM.search(
            content[e:outside[idx + 1][0]]
        ):
            return False
        return True

    positive_expected = any(
        (e - s) <= prc.MAX_MANDATORY_CALLOUT_CHARS and _isolated(i)
        for i, (s, e) in enumerate(outside)
    )
    with mp_flags("COVERAGE_MANDATORY_CALLOUT"):
        attested = prc._attest(dict(chunk))
        cards = (attested or {}).get("mandatory_callout_cards") or []
        receipt_ok = bool(cards) and prc.has_exact_mandatory_callout_receipt(
            attested
        )
    with mp_flags():
        attested_off = prc._attest(dict(chunk))
        fp_off = bool((attested_off or {}).get("mandatory_callout_cards"))
    if attested is None:
        return [base | {
            "key": f"{row['fragment_id']}|callout",
            "measure": "callout", "puntuable": False,
            "skip_reason": "attest_failed",
        }]
    results: list[dict] = []
    if not outside:
        results.append(base | {
            "key": f"{row['fragment_id']}|callout|clean",
            "measure": "callout", "variant_label": "clean",
            "puntuable": True, "fp_spurious": bool(cards),
        })
    else:
        valid = True
        if cards:
            c0 = cards[0]
            valid = (
                len(cards) == 1
                and c0.get("card_class") == prc.MANDATORY_CALLOUT_CARD_CLASS
                and c0.get("local_semantic_validated") is False
                and (int(c0["end"]) - int(c0["start"]))
                <= prc.MAX_MANDATORY_CALLOUT_CHARS
                and receipt_ok
                and bool(mandatory_triggers(str(c0.get("quote") or "")))
            )
        results.append(base | {
            "key": f"{row['fragment_id']}|callout|with_triggers",
            "measure": "callout", "variant_label": "with_triggers",
            "puntuable": positive_expected,
            "detected": bool(cards) if positive_expected else None,
            "fp_invalid": bool(cards) and not valid,
            **({} if positive_expected else {
                "skip_reason": "no_isolated_group_bound",
            }),
        })
    results.append(base | {
        "key": f"{row['fragment_id']}|callout|off",
        "measure": "callout", "variant_label": "off",
        "puntuable": True, "fp_off": fp_off,
    })
    return results


# ───────────────── cross_count v9 (fix de instrumento declarado) ─────────────────

def evaluate_cross_count_rows_v9(row: dict) -> list[dict]:
    """cross_count con DOS fixes de INSTRUMENTO declarados sobre el evaluador v5
    (1ª pasada c277: 9/12; las 3 causas diagnosticadas y flag-INDEPENDIENTES —
    no las causan los fixes C/D):

    (a) el evaluador v5 puntuaba SOLO ``cross[0]`` y la población fresca produce
        >1 átomo cross por split (par hermano / 2ª oración de conteo del mismo
        par): el mecanismo real (apply) procesa TODOS los átomos bound — aquí se
        puntúa el éxito de CUALQUIER átomo cross del TARGET del row
        (declared_n + noun), misma clase que el fix seed-272 «el guard evaluaba
        el borrador completo y no la ventana»;
    (b) un par cross con riesgo 7-seg no puede anexar sin paridad de display en
        el borrador — exclusión POR DISEÑO del contrato v2 (display_parity_ok),
        no miss: se re-etiqueta skip declarado (patrón dup_span v7: «la vía
        display se mide en su medida propia»). El mecanismo NO se toca."""
    results: list[dict] = []
    if row["familia"] != mp.FAMILY_COUNT:
        return results
    atom = row["atom"]
    meta = atom.get("meta") or {}
    if meta.get("cross_fragment"):
        return results
    text = row["texto"]
    enum_span = str(meta.get("enum_span_text") or "")
    b_start = text.find(enum_span) if enum_span else -1
    if b_start <= 0:
        return results
    frag_a, frag_b = text[:b_start], text[b_start:]
    if not frag_a.strip() or not frag_b.strip():
        return results
    base = {
        "fragment_id": row["fragment_id"],
        "familia": "F-COUNT-CROSS",
        "document_id": row["document_id"],
    }
    declared = meta.get("declared_n")
    noun = str(meta.get("noun") or "elementos")
    noun_fold = mp._fold(noun)
    claim = H5.TEMPLATES_V5_EXTRA["cross_count_claim"].format(
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
        key = f"{row['fragment_id']}|cross_count|{label}"
        if not adjacent:
            results.append(base | {
                "key": key, "measure": "cross_count", "variant_label": label,
                "puntuable": True, "detected": None, "dual_cite": None,
                "fp_far_page": bool(cross),
            })
            continue
        matching = [
            c for c in cross
            if (c.get("meta") or {}).get("declared_n") == declared
            and mp._fold(str((c.get("meta") or {}).get("noun") or "")) == noun_fold
        ]
        window = mp.citation_window(draft, 1)
        detected = dual = False
        for c0 in matching:
            c = copy.deepcopy(c0)
            if window.strip() and mp.atom_exigible_in(c, window) and not (
                mp.atom_satisfied(c, draft)
            ):
                c.setdefault("meta", {})["fragment_number"] = 1
                appendix = mp.render_appendix([c], draft)
                if appendix:
                    detected = True
                    dual = "[F1]" in appendix and "[F2]" in appendix
                    break
        if not detected and matching and all(
            (c.get("meta") or {}).get("seven_segment_risk")
            and not mp.display_parity_ok(c, draft)
            for c in matching
        ):
            results.append(base | {
                "key": key, "measure": "cross_count", "variant_label": label,
                "puntuable": False, "skip_reason": "display_parity_by_design",
            })
            continue
        if not detected and matching and all(
            not mp.atom_good_form(c) for c in matching
        ):
            results.append(base | {
                "key": key, "measure": "cross_count", "variant_label": label,
                "puntuable": False, "skip_reason": "whitelist_bad_form_target",
            })
            continue
        results.append(base | {
            "key": key, "measure": "cross_count", "variant_label": label,
            "puntuable": True,
            "detected": detected, "dual_cite": dual,
            "matching_cross_atoms": len(matching),
        })
    return results


# ─────────────────────────── brazo det ───────────────────────────

def _relabel_whitelist_skip(result: dict) -> dict:
    """Fila cuyo átomo target no pasa la whitelist → skip DECLARADO (v8)."""
    return {
        **result, "puntuable": False, "detected": None,
        "skip_reason": "whitelist_bad_form_target",
    }


def run_arm(hybrid: bool, execute: bool) -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["freeze"]
    if H.sha256_file(COHORT_PATH) != frozen["cohort_sha256"]:
        raise RuntimeError("freeze roto: cohorte v9 ≠ prereg")
    for rel, key in (
        ("src/rag/must_preserve.py", "must_preserve_sha256"),
        ("src/rag/post_rerank_coverage.py", "post_rerank_coverage_sha256"),
        ("src/rag/mp_lexicon.py", "mp_lexicon_sha256"),
    ):
        if H.sha256_file(ROOT / rel) != frozen[key]:
            raise RuntimeError(f"freeze roto: {rel} ≠ prereg")
    if templates_sha256_v9() != frozen["templates_v9_sha256"]:
        raise RuntimeError("freeze roto: templates v9 ≠ prereg")
    rows = H.load_jsonl(COHORT_PATH)
    print(f"Cohorte v9 verificada (freeze OK): {len(rows)} filas")

    if hybrid:
        estimate = H._hybrid_cost_estimate(rows)
        budget = float(prereg["hybrid"]["budget_usd_max"])
        print(f"Brazo HÍBRIDO — estimación: {json.dumps(estimate)} (techo ${budget})")
        print("PREFLIGHT (0 llamadas pagadas). El scoring del brazo híbrido de "
              "F-RELATION lo ejecuta el orquestador (prereg v2 §P1).")
        if execute:
            raise RuntimeError(
                "brazo híbrido pagado NO habilitado en este runner (solo preflight)"
            )
        return 0

    with mp_flags(*DET_FLAGS_ON):
        atoms_by_fragment = {
            r["fragment_id"]: mp.detect_atoms(r["texto"]) for r in rows
        }
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
            # ── suite HEREDADA v8 ÍNTEGRA, con la config det candidata (flags ON) ──
            with mp_flags(*DET_FLAGS_ON):
                atoms = atoms_by_fragment[row["fragment_id"]]
                target = H._locate_target(atoms, row["atom"])
                target_good = target is not None and mp.atom_good_form(target)
                for result in H.evaluate_fragment_rows(row, atoms):
                    if (result.get("measure") == "mutation"
                            and result.get("puntuable") and not target_good):
                        result = _relabel_whitelist_skip(result)
                    if result.get("measure") == "clean" and result.get("puntuable"):
                        mutations = H.generate_mutations(row)
                        claim = mutations[0]["claim_clean"] if mutations else None
                        if claim is not None:
                            draft = H.render_draft(claim, result["variant"])
                            _appendix, appended = H5.run_mechanism_v2(
                                atoms, draft, {1}, 1
                            )
                            reasons = H5._clean_quality_fp(
                                appended, row["texto"], draft
                            )
                            result["fp_quality"] = bool(reasons)
                            result["fp_quality_reasons"] = reasons
                            result["enrichment_appends"] = (
                                len(appended) if not reasons else 0
                            )
                    emit(result)
                for result in H7.evaluate_display_rows_v7(row, atoms):
                    if result.get("puntuable") and not target_good:
                        result = _relabel_whitelist_skip(result)
                    emit(result)
                for result in evaluate_cross_count_rows_v9(row):
                    if (result.get("variant_label") == "adjacent"
                            and result.get("puntuable") and not target_good):
                        result = _relabel_whitelist_skip(result)
                    emit(result)
                for result in H5.evaluate_grounding_rows(row):
                    emit(result)
                for result in H5.evaluate_disclosure_rows(row, atoms):
                    if result.get("puntuable") and not target_good:
                        result = _relabel_whitelist_skip(result)
                    emit(result)
                for result in H7.evaluate_dup_span_rows(row, atoms):
                    emit(result)
                for result in H7.evaluate_empty_enum_rows(row, atoms):
                    emit(result)
                for result in H7.evaluate_navcrumb_rows(row):
                    emit(result)
                for result in H7.evaluate_heading_only_rows(row, atoms):
                    emit(result)
            # ── clases nuevas por-fix (cada una gestiona SUS flags) ──
            for result in evaluate_defline_eq_rows(row):
                emit(result)
            for result in evaluate_f_relation_rows(row):
                emit(result)
            for result in evaluate_served_uncited_rows(row):
                emit(result)
            for result in evaluate_distinctive_rows(row):
                emit(result)
            for result in evaluate_stem_rows(row):
                emit(result)
            for result in evaluate_verb_trigger_rows(row):
                emit(result)
            for result in evaluate_callout_rows(row):
                emit(result)
        with mp_flags(*DET_FLAGS_ON):
            for result in H.evaluate_cross_rows(rows, atoms_by_fragment):
                emit(result)
            for result in H.evaluate_attestation_rows(rows, atoms_by_fragment):
                emit(result)
            for result in H7.evaluate_dup_control_rows(rows, atoms_by_fragment):
                emit(result)
    print(f"Resultados (det): {RESULTS_DET_PATH.relative_to(ROOT)} (+{written})")
    return 0


# ─────────────────────────── gate por-fix ───────────────────────────

def _rate(rows, pred_num, pred_den):
    num = [r for r in rows if pred_num(r)]
    den = [r for r in rows if pred_den(r)]
    return (len(num) / len(den)) if den else None, len(num), len(den)


def inherited_checks(rows: list[dict], gates: dict) -> tuple[dict, dict, bool]:
    """Checks heredados v8 ÍNTEGROS (portados del gate v7/v8) sobre las filas de
    las medidas heredadas EXCLUSIVAMENTE (coverage = salud de instrumento de esa
    suite, sin mezclar las clases nuevas)."""
    rows = [r for r in rows if r.get("measure") in INHERITED_MEASURES]

    def rate(pn, pd):
        return _rate(rows, pn, pd)

    families: dict = {}
    ok = True
    for fam in H.FAMILIES:
        r, n, d = rate(
            lambda x, f=fam: x.get("measure") == "mutation" and x.get("puntuable")
            and x.get("detected") and x["familia"] == f,
            lambda x, f=fam: x.get("measure") == "mutation" and x.get("puntuable")
            and x["familia"] == f,
        )
        passed = r is not None and r >= gates["mutation_recall_min_per_family"]
        families[fam] = {"recall": r, "detected": n, "scored": d, "pass": passed}
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
    all_rows = [r for r in rows if "puntuable" in r]
    scored = [r for r in all_rows if r.get("puntuable")]
    instrument_rows = [
        r for r in all_rows
        if not str(r.get("skip_reason") or "").startswith("whitelist_bad_form")
    ]
    coverage = len(scored) / len(instrument_rows) if instrument_rows else None
    wl_total = sum(whitelist_skips.values())
    whitelist_silence_share = wl_total / len(all_rows) if all_rows else None
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
    ok = ok and all(c["pass"] for c in checks.values())
    return families, checks, ok


def new_fix_checks(rows: list[dict], gates: dict) -> dict:
    """Checks de las clases nuevas por-fix sobre SUS filas."""
    rows = [r for r in rows if r.get("measure") in NEW_MEASURES]

    def rate(measure: str, variant: str, flag: str = "detected"):
        return _rate(
            rows,
            lambda x: x.get("measure") == measure and x.get("puntuable")
            and x.get("variant_label") == variant and x.get(flag),
            lambda x: x.get("measure") == measure and x.get("puntuable")
            and x.get("variant_label") == variant,
        )

    def fp_count(measure: str, variant: str, flag: str) -> int:
        return len([
            r for r in rows if r.get("measure") == measure
            and r.get("variant_label") == variant and r.get(flag)
        ])

    def recall_check(measure, variant, gate_key, flag="detected"):
        r, n, d = rate(measure, variant, flag)
        return {"value": r, "n": n, "d": d,
                "pass": d == 0 or (r or 0) >= gates[gate_key]}

    def fp_check(measure, variant, flag, gate_key):
        n = fp_count(measure, variant, flag)
        return {"value": n, "pass": n <= gates[gate_key]}

    checks = {
        "defline_eq_recall": recall_check(
            "defline_eq", "eq_on", "defline_eq_recall_min"
        ),
        "defline_eq_off_detect_fp": fp_check(
            "defline_eq", "eq_off", "fp_off_detect", "defline_eq_off_detect_fp_max"
        ),
        "defline_eq_assignment_fp": fp_check(
            "defline_eq", "assignment", "fp_assignment",
            "defline_eq_assignment_fp_max"
        ),
        "f_relation_shape_recall": recall_check(
            "f_relation", "shape", "f_relation_shape_recall_min"
        ),
        "f_relation_mechanism_recall": recall_check(
            "f_relation", "qualifier_loss", "f_relation_mechanism_recall_min"
        ),
        "f_relation_defhead_recall": recall_check(
            "f_relation", "definition_loss", "f_relation_defhead_recall_min"
        ),
        "f_relation_title_fp": fp_check(
            "f_relation", "title", "fp_title", "f_relation_title_fp_max"
        ),
        "f_relation_prose_fp": fp_check(
            "f_relation", "prose", "fp_prose", "f_relation_prose_fp_max"
        ),
        "f_relation_off_fp": fp_check(
            "f_relation", "off", "fp_off", "f_relation_off_fp_max"
        ),
        "served_uncited_clean_fp": fp_check(
            "served_uncited", "clean", "fp_clean", "served_uncited_clean_fp_max"
        ),
        "served_uncited_positive_recall_reported": (lambda rr: {
            "value": rr[0], "n": rr[1], "d": rr[2], "pass": True,
        })(rate("served_uncited", "positive")),
        "distinctive_generic_fp": fp_check(
            "distinctive", "generic", "fp_generic", "distinctive_generic_fp_max"
        ),
        "distinctive_positive_recall": recall_check(
            "distinctive", "positive", "distinctive_positive_recall_min"
        ),
        "distinctive_off_fp": fp_check(
            "distinctive", "off", "fp_off", "distinctive_off_fp_max"
        ),
        "stem_positive_recall": recall_check(
            "stem", "positive", "stem_positive_recall_min"
        ),
        "stem_single_token_fp": fp_check(
            "stem", "single", "fp_single", "stem_single_token_fp_max"
        ),
        "stem_off_fp": fp_check("stem", "off", "fp_off", "stem_off_fp_max"),
        "verb_trigger_recall": recall_check(
            "verb_trigger", "on", "verb_trigger_recall_min"
        ),
        "verb_trigger_noun_fp": fp_check(
            "verb_trigger", "noun", "fp_noun", "verb_trigger_noun_fp_max"
        ),
        "verb_trigger_off_fp": fp_check(
            "verb_trigger", "off", "fp_off", "verb_trigger_off_fp_max"
        ),
        "callout_spurious_fp": fp_check(
            "callout", "clean", "fp_spurious", "callout_spurious_fp_max"
        ),
        "callout_invalid_card_fp": fp_check(
            "callout", "with_triggers", "fp_invalid", "callout_invalid_card_fp_max"
        ),
        "callout_positive_recall": recall_check(
            "callout", "with_triggers", "callout_positive_recall_min"
        ),
        "callout_off_fp": fp_check(
            "callout", "off", "fp_off", "callout_off_fp_max"
        ),
    }
    return checks


def per_fix_verdicts(inherited_ok: bool, inherited: dict, checks: dict) -> dict:
    """GO por-fix independiente: un NO-GO mata SOLO su fix; los heredados en NO-GO
    matan el bloque D entero (prereg v2 §P1.gate). verb-trigger referencia además
    los checks heredados que su spec cita (corren con el flag ON)."""
    out: dict = {}
    for fix, names in FIX_CHECKS.items():
        fix_checks = {name: checks[name] for name in names}
        own_ok = all(c["pass"] for c in fix_checks.values())
        killed = fix in BLOCK_D_FIXES and not inherited_ok
        refs = {}
        if fix == "MP_MANDATORY_VERB_TRIGGER":
            refs = {name: inherited[name] for name in VT_INHERITED_REFS}
            own_ok = own_ok and all(c["pass"] for c in refs.values())
        out[fix] = {
            "checks": fix_checks,
            **({"inherited_refs": refs} if refs else {}),
            "killed_by_inherited_no_go": killed,
            "verdict": "GO" if (own_ok and not killed) else "NO_GO",
        }
    return out


def gate() -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["freeze"]
    for rel, key in (
        ("src/rag/must_preserve.py", "must_preserve_sha256"),
        ("src/rag/post_rerank_coverage.py", "post_rerank_coverage_sha256"),
        ("src/rag/mp_lexicon.py", "mp_lexicon_sha256"),
    ):
        if H.sha256_file(ROOT / rel) != frozen[key]:
            raise RuntimeError(f"gate: {rel} ≠ prereg")
    rows = H.load_jsonl(RESULTS_DET_PATH)
    gates = prereg["gates"]
    families, checks_inh, inherited_ok = inherited_checks(rows, gates)
    checks_new = new_fix_checks(rows, gates)
    fixes = per_fix_verdicts(inherited_ok, checks_inh, checks_new)
    verdict = {
        "schema": "s274_stage1_v9_gate_v1",
        "created_utc": H._now(),
        "arm": "det",
        "seed": SEED,
        "inherited": {
            "measured_with_flags_on": list(DET_FLAGS_ON),
            "families": families,
            "checks": checks_inh,
            "verdict": "GO" if inherited_ok else "NO_GO",
            "no_go_kills_block_d": sorted(BLOCK_D_FIXES),
        },
        "new_checks": checks_new,
        "per_fix": fixes,
        "hybrid_arm": "PREFLIGHT_ONLY (scoring F-RELATION híbrido lo paga el "
                      "orquestador; prereg v2 §P1)",
        "verdict_by_fix": {fix: fixes[fix]["verdict"] for fix in sorted(fixes)},
    }
    all_go = inherited_ok and all(
        f["verdict"] == "GO" for f in fixes.values()
    )
    verdict["verdict"] = "GO" if all_go else "PARTIAL_OR_NO_GO"
    GATE_OUT_PATH.write_text(
        yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(yaml.safe_dump(
        {
            "inherited": verdict["inherited"]["verdict"],
            "families": {f: v["recall"] for f, v in families.items()},
            "per_fix": verdict["verdict_by_fix"],
            "verdict": verdict["verdict"],
        },
        allow_unicode=True, sort_keys=False,
    ))
    print(f"Gate: {GATE_OUT_PATH.relative_to(ROOT)}")
    return 0 if all_go else 2


# ─────────────────────────── freeze (prereg v9) ───────────────────────────

def freeze() -> int:
    if not COHORT_PATH.exists():
        raise RuntimeError("cohorte v9 no construida: --build-cohort primero")
    rows = H.load_jsonl(COHORT_PATH)
    build = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    prereg = {
        "schema": "s274_stage1_v9_prereg_v1",
        "status": "FROZEN_BEFORE_RUN",
        "created_utc": H._now(),
        "predecessor": (
            "evals/s271_stage1_v8_gate_v1.yaml (seed-276, GO) — este v9 valida los "
            "fixes Bloques C/D de evals/s274_bloquesCD_prereg_v2.yaml §P1"
        ),
        "mechanism": (
            "must_preserve v5 + fixes s274 flag-gated (7 flags por-fix, default "
            "off). Heredados v8 ÍNTEGROS medidos con la config det candidata "
            f"({'+'.join(DET_FLAGS_ON)} ON); clases nuevas POR-FIX con su flag "
            "aislado + controles flag-off"
        ),
        "seed": SEED,
        "gates": dict(GATES),
        "gates_provenance": (
            "heredados ÍNTEGROS del prereg v8 (un fix no se compra con recall; "
            "NO-GO heredado mata el bloque D entero) + clases nuevas por-fix del "
            "prereg s274 v2 §P1: defline_eq (D1a) · f_relation det-side (D1b) · "
            "served_uncited=re-clase seed-270 (C2) · distinctive=re-clase "
            "seed-271 (D2) · stem (D1c) · verb_trigger (Fable-M1) · callout (C1)"
        ),
        "fix_checks": {k: list(v) for k, v in FIX_CHECKS.items()},
        "block_d_fixes": list(BLOCK_D_FIXES),
        "freeze": {
            "must_preserve_sha256": H.sha256_file(ROOT / "src/rag/must_preserve.py"),
            "post_rerank_coverage_sha256": H.sha256_file(
                ROOT / "src/rag/post_rerank_coverage.py"
            ),
            "mp_lexicon_sha256": H.sha256_file(ROOT / "src/rag/mp_lexicon.py"),
            "harness_v9_sha256": H.sha256_file(
                ROOT / "scripts/s274_mutation_harness_v9.py"
            ),
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
            "templates_v9_sha256": templates_sha256_v9(),
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
            "budget_usd_max": 2.50,
            "prices_usd_per_mtok": {"input": H.HYBRID_PRICE_IN,
                                    "output": H.HYBRID_PRICE_OUT},
            "no_retry": True,
            "status": "PREFLIGHT_ONLY_THIS_RUNNER",
        },
        "honest_declarations": [
            "NOVENA población fresca (seed-277); exclusiones ACUMULADAS de TODAS "
            "las cohortes previas: v1 + seed-270..276 (8 cohortes). Las medidas "
            "previas quedan como evidencia versionada.",
            "Los heredados v8 corren con los 4 flags DETERMINISTAS del bloque C/D "
            "activos (la config candidata en la ruta del harness): el clean-FP "
            "heredado re-mide el ruido de TODOS los fixes de binding a la vez — "
            "un fallo heredado mata el bloque D entero, sin atribución fina "
            "(prereg v2 §P1.gate).",
            "El pre-screen de la cohorte usa el detector de PROD (flags s274 OFF): "
            "los átomos-target son los del mecanismo vigente; los átomos NUEVOS "
            "que MP_DEFLINE_EQ detecte de más se miden en su clase propia, no "
            "inflan el denominador heredado. Deriva de target flag-on↔flag-off se "
            "reporta como target_atom_drift (no puntuable).",
            "Las clases nuevas usan TEMPLATES genéricos + material del átomo REAL "
            "del fragmento fresco (re-render '='-schema, ventanas de 1 token, "
            "cláusulas imperativas sintéticas) — jamás los textos gold; los casos "
            "pineados de los tests salen de los diagnósticos s274.",
            "served_uncited re-mide EXACTAMENTE la clase de control seed-270 "
            "(clean-FP de hermanos) bajo el umbral reforzado ≥3 de C2 (Fable-M2); "
            "el recall del positivo se REPORTA sin gatear — el umbral reforzado "
            "compra precisión a costa de recall, por diseño.",
            "distinctive re-mide EXACTAMENTE la clase seed-271 (1 token genérico "
            "ubicuo) → FP=0 exigido; el criterio catálogo de D2 NO se usa en las "
            "ventanas del harness (solo dígito/acrónimo) para que el veredicto no "
            "dependa de la disponibilidad del catálogo en el runner.",
            "callout usa chunks de coverage SINTÉTICOS (card = 1ª oración del "
            "fragmento real); el recall positivo se acota a gatillos AISLADOS "
            "≤600 (cota inferior independiente del algoritmo de merge — evita "
            "circularidad instrumento↔mecanismo); los grupos >600 omitidos son "
            "DISEÑO, no miss.",
            "f_relation valida el LADO DETERMINISTA del contrato D1b (shape en "
            "código + binding + render); la tasa de PROPUESTA de Haiku bajo el "
            "prompt con F-RELATION no es medible sin brazo pagado — queda en "
            "PREFLIGHT y la paga el orquestador (prereg v2 §P1).",
            "ITERACIÓN DE INSTRUMENTO DECLARADA (post 1ª pasada c277, re-medida "
            "sobre la MISMA cohorte seed-277; el mecanismo NO se toca): "
            "(1) cross_count 9/12 — las 3 causas diagnosticadas y "
            "flag-INDEPENDIENTES (idénticas con los flags C/D off): el evaluador "
            "v5 puntuaba SOLO cross[0] y la población fresca produce >1 átomo "
            "cross por split (misma clase que el artefacto seed-272), y 2 pares "
            "con riesgo 7-seg no pueden anexar sin paridad de display en el "
            "borrador (exclusión POR DISEÑO v2 → skip declarado "
            "display_parity_by_design, patrón dup_span v7) — fix del EVALUADOR "
            "(evaluate_cross_count_rows_v9: éxito de CUALQUIER átomo cross del "
            "target declared_n+noun); (2) defline_eq 1 fp_off — una etiqueta con "
            "marcador de lista numerada re-formaba un run _BULLET con flag off: "
            "la línea re-renderizada ahora se testea DIRECTAMENTE contra los "
            "parsers flag-off (off-inercia por construcción). La 1ª pasada queda "
            "declarada aquí (results re-generados: el fichero c277 contiene solo "
            "la pasada re-medida).",
            "RESULTADO NO tocado por la iteración de instrumento: "
            "served_uncited_clean_fp=24 en la 1ª pasada son anexos de HERMANOS "
            "genuinos bajo el umbral reforzado ≥3 de C2 (verificado por-fila: "
            "26 hermanos / 1 target) — la clase seed-270 re-medida FALLA su gate "
            "FP=0 y C2 (MP_SERVED_BINDING) queda NO-GO por su propia clase, no "
            "por artefacto.",
            "El brazo determinista es $0 y es el que gatea.",
        ],
        "gate_runner": "scripts/s274_mutation_harness_v9.py --gate",
        "gate_output": str(GATE_OUT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    PREREG_PATH.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Prereg v9 congelado: {PREREG_PATH.relative_to(ROOT)}")
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
