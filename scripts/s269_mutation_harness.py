#!/usr/bin/env python3
"""S269 Etapa 1 v3 — harness de MUTACIONES con gold mecánico (spec:
evals/s269_stage1_v3_mutation_spec_v1.md §B; sucesor del NO_GO v1).

El gold es MECÁNICO POR CONSTRUCCIÓN (patrón S249, sin etiquetadores modelo): un
mutador determinista redacta un borrador sintético que restata el claim del átomo
CON una omisión conocida (receipt exacto de lo eliminado) + cita [Fn] real; el
mecanismo must-preserve debe restaurar EXACTAMENTE el span mutado (match verbatim).

Cohorte FRESCA seed=271 (binding v2 adjudicado post-seed-270), MISMA mecánica de
exclusiones v1 (import del builder v1) + exclusión de los docs de las cohortes
v1 y seed-270.
Pre-screen declarado: detector DETERMINISTA (subset del híbrido, $0) — el sesgo de
selección se controla porque el gold es mecánico y el gate mide sobre mutaciones,
no sobre prevalencia.

Medidas (spec §B):
  mutation_recall   por familia: átomo detectado + appendix restaura el span verbatim
  clean_noise       borrador SIN mutar → FP por FAMILIA del átomo anexado
                    (RBC: FP=0; MANDATORY: FP = duplicado o no-procedimental)
  cross_binding     borrador cita A pero habla de B → 0 anexos de A (control C2)
  attestation_block fragmento fuera del doc_map de la identidad → 0 anexos

Brazos: determinista-solo ($0) · híbrido (--hybrid; Haiku con grounding verbatim,
preflight por defecto, --execute gasta, techo leído del prereg). Checkpoint
resumible por clave de fila.

Uso:
  python scripts/s269_mutation_harness.py --build-cohort      # GET-only, $0
  python scripts/s269_mutation_harness.py --freeze            # escribe el prereg v2 (binding v2)
  python scripts/s269_mutation_harness.py --run               # brazo det ($0)
  python scripts/s269_mutation_harness.py --run --hybrid              # preflight
  python scripts/s269_mutation_harness.py --run --hybrid --execute    # Haiku
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola Windows cp1252

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag import must_preserve as mp  # noqa: E402

EVALS = ROOT / "evals"
COHORT_V1_PATH = EVALS / "s269_structural_cohort_v1.jsonl"
# cohorte seed-270 (1ª medida, binding v1): queda como EVIDENCIA; sus docs se
# EXCLUYEN de la cohorte fresca (el refinamiento de contrato post-seed-270 se
# valida en población nueva, adjudicación del coordinador)
COHORT_SEED270_PATH = EVALS / "s269_mutation_cohort_v2.jsonl"
COHORT_PATH = EVALS / "s269_mutation_cohort_v3.jsonl"
BUILD_REPORT_PATH = EVALS / "s269_mutation_cohort_v3_build.json"
PREREG_PATH = EVALS / "s269_stage1_v3_prereg_v2.yaml"
RESULTS_DET_PATH = EVALS / "s269_stage1_v3_results_det_c271.jsonl"
RESULTS_HYBRID_PATH = EVALS / "s269_stage1_v3_results_hybrid_c271.jsonl"
HYBRID_CACHE_PATH = EVALS / "s269_stage1_v3_hybrid_proposals_c271.jsonl"
HYBRID_RECEIPTS_PATH = EVALS / "s269_stage1_v3_hybrid_receipts_c271.json"

SEED = 271
TARGET_PER_FAMILY = 30
TARGET_DOCS = 40
MAX_DOCS = 80
PER_DOC_FAMILY_CAP = 4
MIN_FRAGMENT_CHARS = 200
CROSS_MAX_PAIRS = 30
ATTEST_ROWS = 10

# precios USD/M tokens (Haiku 4.5, tarifa vigente — misma que s269_label v1)
HYBRID_PRICE_IN = 1.0
HYBRID_PRICE_OUT = 5.0

FAMILIES = list(mp.FAMILIES)


# ─────────────────────────── templates (freeze C4) ───────────────────────────
# El claim se ensambla con builders deterministas (código de ESTE fichero, cuyo
# sha se pinea entero); las 2 variantes de fraseo por mutación salen de estos
# wrappers. templates_sha256 = sha del JSON canónico de este registro.

TEMPLATES_VERSION = "s269_v3_templates_v3"
TEMPLATES = {
    "wrappers": [
        "Según el manual, {claim} [F{n}].",
        "La documentación técnica indica que {claim} [F{n}].",
    ],
    # gancho de binding: el borrador real de un writer NOMBRA el parámetro; los
    # templates lo emulan con 2 anchors del átomo (v1→v2 de templates: sin este
    # contexto, mutaciones tipo drop_upper con lower∈{0,1} quedaban sin gancho)
    "anchor_context": "para {a1} y {a2}, {core}",
    "range_core": "el parámetro admite valores de {lo} a {hi}{unit}",
    "range_core_lower_only": "el parámetro admite valores a partir de {lo}{unit}",
    "range_core_tolerance": "el parámetro admite una desviación de ±{tol}{unit}",
    "range_step": ", en pasos de {step}{unit}",
    "range_scope_pair": ", en las posiciones {a} a {b}",
    "range_scope_single": ", en la posición {a}",
    "bundle_full": "la sección {header} define los campos: {members}",
    "bundle_no_header": "los campos {members} se definen juntos en la misma sección",
    "bundle_schema": "los campos {members} forman el esquema de la regla",
    # binding v2: los borradores mandatory emulan una respuesta que DA el
    # procedimiento del fragmento (s243: el callout es adyacente a ese procedimiento)
    "mandatory_full": (
        'siga el procedimiento sobre {p1} y {p2}; la fuente recoge además esta '
        'indicación literal: "{span}"'
    ),
    "mandatory_dropped": (
        "para {p1} y {p2}, siga los pasos del procedimiento descritos en la fuente"
    ),
    "count_clean": (
        "se declaran {declared} {noun}, pero el manual también indica {enumerated} "
        "elementos en la enumeración"
    ),
    "count_alter": "el equipo dispone de {enumerated} {noun}",
    "count_drop_enum": "el manual indica {declared} {noun} disponibles",
    "cross_number_hook": "Otro parámetro documentado es {value} [F{n}].",
    "cross_anchor_hook": "También se documentan {a1} y {a2} [F{n}].",
}


def templates_sha256() -> str:
    blob = json.dumps(
        {"version": TEMPLATES_VERSION, "templates": TEMPLATES},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    # Normalización CRLF->LF (precedente s198): el freeze sobrevive a checkouts
    # Windows con autocrlf.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ─────────────────────────── build de la cohorte v2 ───────────────────────────

def _load_v1_builder():
    """Importa el builder v1 para reusar LITERALMENTE su mecánica de exclusiones
    (spec §B: "misma mecánica de exclusión v1")."""
    spec = importlib.util.spec_from_file_location(
        "s269_build_structural_cohort", ROOT / "scripts/s269_build_structural_cohort.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_cohort() -> int:
    import httpx

    v1 = _load_v1_builder()
    rng = random.Random(SEED)
    import os
    table = os.environ.get("CHUNKS_TABLE", "chunks_v2")

    v1_rows = load_jsonl(COHORT_V1_PATH)
    v1_docs = sorted({r["document_id"] for r in v1_rows})
    if not v1_docs:
        raise RuntimeError("cohorte v1 no encontrada: la exclusión de sus docs es obligatoria")
    seed270_rows = load_jsonl(COHORT_SEED270_PATH)
    seed270_docs = sorted({r["document_id"] for r in seed270_rows})
    if not seed270_docs:
        raise RuntimeError(
            "cohorte seed-270 no encontrada: sus docs deben excluirse (población fresca)"
        )

    with httpx.Client(timeout=30.0) as client:
        print("Inventario del corpus (GET paginado)...")
        corpus = v1.fetch_corpus_docs(client, table)
        print(f"  docs servibles: {len(corpus)}")
        print("Exclusiones (mecánica v1 + docs de la cohorte v1)...")
        excluded, manifest = v1.build_exclusions(corpus)
        for label, path, docs in (
            ("v1_cohort_docs_exclusion", COHORT_V1_PATH, v1_docs),
            ("seed270_cohort_docs_exclusion", COHORT_SEED270_PATH, seed270_docs),
        ):
            extra = {d for d in docs if d in corpus and d not in excluded}
            excluded |= set(docs)
            manifest.append({
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "method": label,
                "sha256": sha256_file(path),
                "corpus_docs_matched": len([d for d in docs if d in corpus]),
                "docs_not_already_excluded": len(extra),
            })
        eligible = {d: r for d, r in corpus.items() if d not in excluded}
        print(f"  excluidos: {len(excluded & set(corpus))} | elegibles: {len(eligible)}")

        doc_order = v1.stratified_doc_order(eligible, rng)
        pools: dict[str, list[dict]] = {f: [] for f in FAMILIES}
        per_doc_family: dict[tuple[str, str], int] = {}
        docs_used: list[str] = []
        fragments_screened = 0

        def buckets_full() -> bool:
            return all(len(pools[f]) >= TARGET_PER_FAMILY for f in FAMILIES)

        for did in doc_order:
            if len(docs_used) >= MAX_DOCS or (
                len(docs_used) >= TARGET_DOCS and buckets_full()
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
                    if per_doc_family.get(key, 0) >= PER_DOC_FAMILY_CAP:
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
                        "sha256": sha256_text(frag["content"]),
                        "atom": target,
                    })

    chosen: dict[str, dict] = {}
    composition: dict[str, int] = {}
    for fam in FAMILIES:
        pool = [r for r in pools[fam] if r["fragment_id"] not in chosen]
        rng.shuffle(pool)
        picked = pool[:TARGET_PER_FAMILY]
        for r in picked:
            chosen[r["fragment_id"]] = r
        composition[fam] = len(picked)

    rows = sorted(chosen.values(), key=lambda r: (r["familia"], r["fragment_id"]))
    with COHORT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "schema": "s269_mutation_cohort_v3_build_v1",
        "created_utc": _now(),
        "seed": SEED,
        "chunks_table": table,
        "corpus_docs_servibles": len(corpus),
        "excluded_docs": len(excluded & set(corpus)),
        "eligible_docs": len(eligible),
        "docs_sampled": len(docs_used),
        "fragments_screened": fragments_screened,
        "composition": composition,
        "rows": len(rows),
        "prescreen": (
            "detector DETERMINISTA (subset del híbrido, $0); el sesgo de selección "
            "se controla porque el gold es mecánico y el gate mide sobre mutaciones"
        ),
        "exclusion_manifest": manifest,
        "cohort_sha256": sha256_file(COHORT_PATH),
    }
    BUILD_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\nCohorte v3: {COHORT_PATH.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"Composición: {composition}")
    print(f"Build report: {BUILD_REPORT_PATH.relative_to(ROOT)}")
    return 0


# ─────────────────────── mutadores deterministas + receipts ───────────────────────

def _fmt(v) -> str:
    return mp._format_num(float(v))


_UNIT_SURFACE_FORMS = (
    {u.lower() for u in mp._UNITS}
    | set(mp._UNIT_SYNONYMS.keys())
    | set(mp._UNIT_SYNONYMS.values())
)


def _atom_context_anchors(atom: dict, exclude: set[str] = frozenset()) -> tuple | None:
    """2 tokens de contexto del átomo para que el claim sintético NOMBRE el
    parámetro (gancho de binding): alfabéticos, ≥4 chars, ni unidades ni tokens
    excluidos (p.ej. los que la mutación elimina)."""
    picks = [
        t for t in (atom.get("anchor_tokens") or [])
        if t.isalpha() and len(t) >= 4
        and t not in _UNIT_SURFACE_FORMS and t not in exclude
    ]
    if len(picks) < 2:
        return None
    return picks[0], picks[1]


def _with_context(atom: dict, core: str, exclude: set[str] = frozenset()) -> str:
    pair = _atom_context_anchors(atom, exclude)
    if pair is None:
        return core
    return TEMPLATES["anchor_context"].format(a1=pair[0], a2=pair[1], core=core)


def _range_claim(meta: dict, mutation: str | None) -> str:
    unit = (meta.get("unit") or "")
    unit_txt = "" if mutation == "drop_unit" or not unit else f" {unit}"
    lo, hi, tol = meta.get("lower"), meta.get("upper"), meta.get("tolerance")
    if mutation == "drop_upper":
        core = TEMPLATES["range_core_lower_only"].format(lo=_fmt(lo), unit=unit_txt)
    elif lo is None and tol is not None:
        core = TEMPLATES["range_core_tolerance"].format(tol=_fmt(tol), unit=unit_txt)
    else:
        core = TEMPLATES["range_core"].format(lo=_fmt(lo), hi=_fmt(hi), unit=unit_txt)
    step = meta.get("step")
    if step is not None and mutation != "drop_step":
        core += TEMPLATES["range_step"].format(step=_fmt(step), unit=unit_txt)
    scope = meta.get("scope") or []
    if scope and mutation != "drop_scope":
        if len(scope) >= 2:
            core += TEMPLATES["range_scope_pair"].format(a=scope[0], b=scope[-1])
        else:
            core += TEMPLATES["range_scope_single"].format(a=scope[0])
    return core


def _bundle_members_text(members: list[str], drop: str | None) -> str:
    kept = [m for m in members if m != drop]
    return "; ".join(kept)


def _bundle_claim(meta: dict, mutation: str | None, dropped_member: str | None) -> str:
    header = (meta.get("header") or "").strip()
    members = _bundle_members_text(meta.get("members") or [], dropped_member)
    if mutation == "drop_header" or not header:
        tpl = "bundle_no_header" if mutation == "drop_header" else "bundle_schema"
        return TEMPLATES[tpl].format(members=members)
    return TEMPLATES["bundle_full"].format(header=header, members=members)


def _mandatory_proc_pair(atom: dict) -> tuple[str, str] | None:
    """2 tokens PROCEDIMENTALES del fragmento (binding v2): el borrador emula una
    respuesta que da el procedimiento. Se excluyen los términos del léxico
    obligatorio (el mutado no debe re-introducir fuerza obligatoria)."""
    meta = atom.get("meta") or {}
    trigger_words: set[str] = set(mp._MANDATORY_TERMS)
    for t in meta.get("triggers") or []:
        trigger_words.update(t.replace("(n)", "").replace("+", " ").split())
    picks = [
        t for t in (meta.get("procedural_context_tokens") or [])
        if t.isalpha() and len(t) >= 4 and t not in trigger_words
    ]
    if len(picks) < 2:
        return None
    return picks[0], picks[1]


def generate_mutations(row: dict) -> list[dict]:
    """Instancias de mutación aplicables al átomo target (determinista, span-level,
    con receipt exacto de lo eliminado). NO usa el mecanismo bajo test para decidir
    aplicabilidad — solo la estructura del átomo (anti-circularidad)."""
    atom = row["atom"]
    fam = atom["family"]
    meta = atom.get("meta") or {}
    out: list[dict] = []

    def add(kind: str, claim_clean: str, claim_mut: str, removed: str,
            removed_tokens: list[str]) -> None:
        out.append({
            "mutation": kind,
            "claim_clean": claim_clean,
            "claim_mut": claim_mut,
            "removed_text": removed,
            "removed_tokens": removed_tokens,
        })

    if fam == mp.FAMILY_RANGE:
        clean = _with_context(atom, _range_claim(meta, None))
        if meta.get("lower") is not None and meta.get("upper") is not None:
            add("drop_upper", clean,
                _with_context(atom, _range_claim(meta, "drop_upper")),
                _fmt(meta["upper"]), [_fmt(meta["upper"])])
        if meta.get("step") is not None:
            add("drop_step", clean,
                _with_context(atom, _range_claim(meta, "drop_step")),
                _fmt(meta["step"]), [_fmt(meta["step"])])
        if meta.get("unit"):
            add("drop_unit", clean,
                _with_context(atom, _range_claim(meta, "drop_unit")),
                str(meta["unit"]), [str(meta["unit"]).lower()])
        if meta.get("scope"):
            add("drop_scope", clean,
                _with_context(atom, _range_claim(meta, "drop_scope")),
                " ".join(meta["scope"]), [s.lower() for s in meta["scope"]])
    elif fam == mp.FAMILY_BUNDLE:
        members = meta.get("members") or []
        clean = _bundle_claim(meta, None, None)
        if len(members) >= 2:
            # miembro a quitar: el último cuyos tokens no re-aparecen en el resto
            for cand in reversed(members):
                cand_tokens = set(mp._content_tokens(cand, min_len=2))
                rest = _bundle_claim(meta, None, cand)
                rest_tokens = set(mp._content_tokens(rest, min_len=2))
                if cand_tokens and cand_tokens.isdisjoint(rest_tokens):
                    add("drop_member", clean, rest, cand, sorted(cand_tokens))
                    break
        header = (meta.get("header") or "").strip()
        span_folded = mp._fold(atom.get("span_text") or "")
        # drop_header solo si la cabecera VIVE en el span (receipt restaurable
        # verbatim; una cabecera no-adyacente no forma parte del span del átomo)
        if header and mp._fold(header) in span_folded:
            add("drop_header", clean, _bundle_claim(meta, "drop_header", None),
                header, mp._content_tokens(header))
    elif fam == mp.FAMILY_MANDATORY:
        pair = _mandatory_proc_pair(atom)
        if pair is not None:
            span = (atom.get("span_text") or "").strip()
            clean = TEMPLATES["mandatory_full"].format(p1=pair[0], p2=pair[1], span=span)
            mut = TEMPLATES["mandatory_dropped"].format(p1=pair[0], p2=pair[1])
            trigger_tokens = sorted({
                w for t in (meta.get("triggers") or [])
                for w in t.replace("(n)", "").replace("+", " ").split()
            })
            add("drop_clause", clean, mut, span, trigger_tokens)
    elif fam == mp.FAMILY_COUNT:
        declared, enumerated = meta.get("declared_n"), meta.get("enumerated_n")
        noun = str(meta.get("noun") or "elementos")
        exclude = set(mp._COUNT_WORDS)
        if declared is not None and enumerated is not None:
            clean = _with_context(atom, TEMPLATES["count_clean"].format(
                declared=declared, noun=noun, enumerated=enumerated
            ), exclude)
            add("alter_count", clean,
                _with_context(atom, TEMPLATES["count_alter"].format(
                    enumerated=enumerated, noun=noun), exclude),
                str(declared), [str(declared)])
            add("drop_enumeration", clean,
                _with_context(atom, TEMPLATES["count_drop_enum"].format(
                    declared=declared, noun=noun), exclude),
                str(enumerated), [str(enumerated)])
    return out


def render_draft(claim: str, variant: int, fragment_number: int = 1) -> str:
    return TEMPLATES["wrappers"][variant].format(claim=claim, n=fragment_number)


def _collision_guard(mutation: dict, draft_mut: str) -> str | None:
    """Guard INDEPENDIENTE del mecanismo: lo eliminado no debe re-aparecer en el
    borrador mutado por otro campo (p.ej. paso == extremo inferior). Devuelve la
    razón de skip o None si la fila es puntuable."""
    folded = mp._fold(draft_mut)
    draft_tokens = set(mp._content_tokens(draft_mut, min_len=2))
    kind = mutation["mutation"]
    for tok in mutation["removed_tokens"]:
        tok_f = mp._fold(tok)
        if kind in ("drop_upper", "drop_step", "alter_count", "drop_enumeration"):
            import re as _re
            if _re.search(rf"(?<![0-9]){_re.escape(tok_f)}(?![0-9])", folded):
                return f"collision_guard:{tok}"
        elif kind == "drop_unit":
            import re as _re
            if _re.search(rf"\b{_re.escape(tok_f)}\b", folded):
                return f"collision_guard:{tok}"
        else:  # drop_scope / drop_member / drop_header / drop_clause
            if tok_f in draft_tokens or (len(tok_f) > 3 and tok_f in folded):
                return f"collision_guard:{tok}"
    return None


def _has_binding_hook(atom: dict, draft: str) -> bool:
    """Guard de generación (harness-side, declarado): el borrador mutado debe
    conservar presencia PARCIAL del átomo según el contrato de binding v2
    (mp.atom_exigible_in). Un template sin gancho mediría un artefacto del
    template, no al mecanismo — la vía binding se mide en clean/cross."""
    return mp.atom_exigible_in(atom, draft)


# ─────────────────────────── mecanismo bajo test ───────────────────────────

def run_mechanism(atoms: list[dict], draft: str, cited: set[int],
                  fragment_number: int) -> tuple[str, list[dict]]:
    """detect→bind→satisfied→render con la MISMA API pública que usa el generador
    (attestation se mide en su medida propia). Devuelve (appendix, átomos
    efectivamente ANEXADOS post-cap) para el scoring por-átomo del gate."""
    atoms = [copy.deepcopy(a) for a in atoms]
    bound = mp.bind_atoms(atoms, draft, cited, fragment_number)
    missing = []
    for atom in bound:
        if not mp.atom_satisfied(atom, draft):
            atom.setdefault("meta", {})["fragment_number"] = fragment_number
            missing.append(atom)
    appendix = mp.render_appendix(missing, draft)
    appended = mp._select_for_appendix(missing) if appendix else []
    return appendix, appended


def _locate_target(atoms: list[dict], target: dict) -> dict | None:
    for a in atoms:
        if (a["family"] == target["family"]
                and a["span_start"] == target["span_start"]
                and a["span_end"] == target["span_end"]):
            return a
    return None


# ─────────────────────────── evaluación por fila ───────────────────────────

def evaluate_fragment_rows(row: dict, atoms: list[dict]) -> list[dict]:
    """Filas de resultado (mutation + clean) para un fragmento de la cohorte."""
    results: list[dict] = []
    target = _locate_target(atoms, row["atom"])
    base = {
        "fragment_id": row["fragment_id"],
        "familia": row["familia"],
        "document_id": row["document_id"],
    }
    if target is None:
        results.append(base | {
            "key": f"{row['fragment_id']}|target_drift",
            "measure": "mutation",
            "puntuable": False,
            "skip_reason": "target_atom_drift",
        })
        return results

    span = (row["atom"].get("span_text") or "").strip()
    mutations = generate_mutations(row)
    if not mutations:
        results.append(base | {
            "key": f"{row['fragment_id']}|no_mutation_applicable",
            "measure": "mutation",
            "puntuable": False,
            "skip_reason": "no_mutation_applicable",
        })

    for mutation in mutations:
        for variant in range(2):
            key = f"{row['fragment_id']}|mutation|{mutation['mutation']}|v{variant}"
            draft = render_draft(mutation["claim_mut"], variant)
            skip = _collision_guard(mutation, draft)
            if skip is None and not _has_binding_hook(target, draft):
                skip = "binding_guard:template_sin_gancho"
            if skip is not None:
                results.append(base | {
                    "key": key, "measure": "mutation",
                    "mutation": mutation["mutation"], "variant": variant,
                    "puntuable": False, "skip_reason": skip,
                })
                continue
            appendix, _appended = run_mechanism(atoms, draft, {1}, 1)
            # receipt: el span verbatim manda; lo eliminado se exige en el anexo
            # (fold-insensible) SOLO si vive literalmente en el span — valores
            # derivados (conteo enumerado, cabecera no-adyacente) no son literales
            span_f = mp._fold(span)
            removed_f = mp._fold(mutation["removed_text"])
            removed_check = (
                removed_f in mp._fold(appendix)
                if removed_f and removed_f in span_f else True
            )
            detected = bool(appendix) and span in appendix and removed_check
            results.append(base | {
                "key": key, "measure": "mutation",
                "mutation": mutation["mutation"], "variant": variant,
                "puntuable": True,
                "detected": detected,
                "appendix_len": len(appendix),
                "receipt": {
                    "removed_text": mutation["removed_text"],
                    "span_text": span,
                },
            })
        # clean_noise: mismo claim SIN mutar (átomo presente) → 0 anexos
    for variant in range(2):
        claim_clean = mutations[0]["claim_clean"] if mutations else None
        if claim_clean is None:
            continue
        key = f"{row['fragment_id']}|clean|v{variant}"
        draft = render_draft(claim_clean, variant)
        appendix, appended = run_mechanism(atoms, draft, {1}, 1)
        # detalle POR ÁTOMO anexado (gate v2, clean por-familia): para MANDATORY
        # se registra el solape procedimental en la VENTANA y si es duplicado —
        # FP mandatory = duplicado o no-procedimental (conducta objetivo si no)
        window = mp.citation_window(draft, 1)
        window_tokens = set(mp._content_tokens(mp._FRAG_CITE.sub(" ", window)))
        appended_detail = []
        for a in appended:
            d = {"family": a["family"]}
            if a["family"] == mp.FAMILY_MANDATORY:
                proc = set((a.get("meta") or {}).get("procedural_context_tokens") or [])
                d["proc_overlap"] = len(proc & window_tokens)
                d["duplicate"] = bool(mp.atom_satisfied(a, draft))
            appended_detail.append(d)
        results.append(base | {
            "key": key, "measure": "clean", "variant": variant,
            "puntuable": True,
            "fp": bool(appendix),
            "appended": appended_detail,
            "appendix_len": len(appendix),
        })
    return results


def _cross_hook(atom: dict) -> str | None:
    """Oración-hook con material PROPIO del átomo A (binding v2) para colocarla
    junto a [F2]: bajo C2 no debe hacer exigible a A vía la ventana de [F1]."""
    fam = atom["family"]
    meta = atom.get("meta") or {}
    if fam in (mp.FAMILY_RANGE, mp.FAMILY_COUNT):
        keys = (("lower", "upper", "step", "tolerance") if fam == mp.FAMILY_RANGE
                else ("declared_n", "enumerated_n"))
        own = sorted({
            float(meta[k]) for k in keys if meta.get(k) is not None
        } - {0.0, 1.0})
        if own:
            return TEMPLATES["cross_number_hook"].format(value=_fmt(own[0]), n=2)
        scope = meta.get("scope") or []
        if len(scope) >= 2:
            return TEMPLATES["cross_anchor_hook"].format(a1=scope[0], a2=scope[-1], n=2)
        return None
    if fam == mp.FAMILY_BUNDLE:
        pool = list(mp._content_tokens(meta.get("header") or ""))
        for label in meta.get("members") or []:
            toks = mp._content_tokens(label, min_len=2)
            if toks:
                pool.append(toks[0])
        if len(pool) >= 2:
            return TEMPLATES["cross_anchor_hook"].format(a1=pool[0], a2=pool[1], n=2)
        return None
    if fam == mp.FAMILY_MANDATORY:
        proc = [
            t for t in (meta.get("procedural_context_tokens") or [])
            if t.isalpha() and len(t) >= 4
        ]
        if len(proc) >= 2:
            return TEMPLATES["cross_anchor_hook"].format(a1=proc[0], a2=proc[1], n=2)
        return None
    return None


def _pair_is_safe(atoms_a: list[dict], b_sentence: str) -> bool:
    """Ningún átomo de A puede ser exigible (binding v2) contra la oración-claim
    de B (los hooks de A van SOLO junto a [F2]): sin esto el par no aísla C2."""
    return all(not mp.atom_exigible_in(a, b_sentence) for a in atoms_a)


def _clean_claim_for(row: dict) -> str | None:
    mutations = generate_mutations(row)
    return mutations[0]["claim_clean"] if mutations else None


def evaluate_cross_rows(rows: list[dict], atoms_by_fragment: dict) -> list[dict]:
    """cross_binding (control C2): el borrador cita al fragmento A [F1] pero habla
    del fragmento B; los hooks de A aparecen SOLO junto a [F2] → 0 anexos de A."""
    results: list[dict] = []
    ordered = sorted(rows, key=lambda r: (r["familia"], r["fragment_id"]))
    used_pairs = 0
    for i, row_a in enumerate(ordered):
        if used_pairs >= CROSS_MAX_PAIRS:
            break
        atoms_a = atoms_by_fragment[row_a["fragment_id"]]
        target_a = _locate_target(atoms_a, row_a["atom"])
        if target_a is None:
            continue
        hook = _cross_hook(target_a)
        if hook is None:
            continue
        pair = None
        for j in range(1, len(ordered)):
            row_b = ordered[(i + j) % len(ordered)]
            if row_b["familia"] == row_a["familia"]:
                continue
            claim_b = _clean_claim_for(row_b)
            if claim_b is None:
                continue
            b_sentence = render_draft(claim_b, 0, fragment_number=1)
            if _pair_is_safe(atoms_a, b_sentence):
                pair = (row_b, b_sentence)
                break
        if pair is None:
            results.append({
                "key": f"{row_a['fragment_id']}|cross|unpaired",
                "measure": "cross", "familia": row_a["familia"],
                "fragment_id": row_a["fragment_id"],
                "puntuable": False, "skip_reason": "no_safe_pair",
            })
            continue
        row_b, b_sentence = pair
        draft = f"{b_sentence} {hook}"
        appendix, _appended = run_mechanism(atoms_a, draft, {1, 2}, 1)
        results.append({
            "key": f"{row_a['fragment_id']}|cross|{row_b['fragment_id']}",
            "measure": "cross", "familia": row_a["familia"],
            "fragment_id": row_a["fragment_id"],
            "partner_fragment_id": row_b["fragment_id"],
            "puntuable": True,
            "fp": bool(appendix),
            "appendix_len": len(appendix),
        })
        used_pairs += 1
    return results


def evaluate_attestation_rows(rows: list[dict], atoms_by_fragment: dict) -> list[dict]:
    """attestation_block: el doc del fragmento NO pertenece al doc_map de la
    identidad resuelta → attest fail-closed → 0 anexos (con control positivo)."""
    results: list[dict] = []
    ordered = sorted(rows, key=lambda r: r["fragment_id"])[:ATTEST_ROWS]
    for row in ordered:
        atoms = atoms_by_fragment[row["fragment_id"]]
        mutations = generate_mutations(row)
        if not mutations:
            continue
        draft = render_draft(mutations[0]["claim_mut"], 0)
        catalog = SimpleNamespace(
            doc_map=[{
                "document_id": row["document_id"],
                "entries": [{"id": "s269:v3:identity-a"}],
            }],
            follow_redirect=lambda x: x,
        )
        positive = mp.attest_identity(
            row["document_id"], {"s269:v3:identity-a"}, catalog
        )
        blocked = mp.attest_identity(
            row["document_id"], {"s269:v3:identity-b"}, catalog
        )
        appendix = "" if not blocked else run_mechanism(atoms, draft, {1}, 1)[0]
        results.append({
            "key": f"{row['fragment_id']}|attestation",
            "measure": "attestation", "familia": row["familia"],
            "fragment_id": row["fragment_id"],
            "puntuable": True,
            "attest_positive_control": bool(positive),
            "attest_blocked": not blocked,
            "appends": len(appendix.splitlines()) - 1 if appendix else 0,
        })
    return results


# ─────────────────────────── brazos (det / híbrido) ───────────────────────────

def _hybrid_cost_estimate(rows: list[dict]) -> dict:
    prompt_tokens = len(mp._HYBRID_PROMPT) / 4
    tokens_in = sum(prompt_tokens + len(r["texto"]) / 4 for r in rows)
    tokens_out = 350 * len(rows)
    cost = tokens_in / 1e6 * HYBRID_PRICE_IN + tokens_out / 1e6 * HYBRID_PRICE_OUT
    return {
        "fragments": len(rows),
        "est_input_tokens": int(tokens_in),
        "est_output_tokens": int(tokens_out),
        "est_cost_usd": round(cost, 2),
    }


def _hybrid_atoms(rows: list[dict], budget_usd: float) -> tuple[dict, dict]:
    """1 llamada Haiku por fragmento (cacheada, resumible, no-retry) → átomos
    híbridos VALIDADOS por código. Devuelve (atoms_by_fragment, receipts)."""
    import os
    import anthropic

    cache = {r["fragment_id"]: r for r in load_jsonl(HYBRID_CACHE_PATH)}
    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    )
    usage: dict = {}
    atoms_by_fragment: dict[str, list[dict]] = {}
    errors = 0
    with HYBRID_CACHE_PATH.open("a", encoding="utf-8", newline="\n") as out:
        for i, row in enumerate(rows, 1):
            cached = cache.get(row["fragment_id"])
            if cached is not None and cached.get("sha256") == row["sha256"]:
                atoms_by_fragment[row["fragment_id"]] = cached["atoms"]
                continue
            cost = (usage.get("input_tokens", 0) / 1e6 * HYBRID_PRICE_IN
                    + usage.get("output_tokens", 0) / 1e6 * HYBRID_PRICE_OUT)
            if cost >= budget_usd:
                raise RuntimeError(
                    f"TECHO DE PRESUPUESTO alcanzado (${cost:.2f} >= ${budget_usd}) "
                    f"en el fragmento {i}/{len(rows)} — reanudar tras revisar"
                )
            try:
                atoms = mp.detect_atoms_hybrid(
                    row["texto"], client=client, usage=usage
                )
            except Exception as exc:  # no-retry: fallback det-solo declarado
                errors += 1
                atoms = mp.detect_atoms(row["texto"])
                print(f"  [WARN] Haiku falló en {row['fragment_id']}: "
                      f"{str(exc)[:120]} → det-solo para este fragmento")
            atoms_by_fragment[row["fragment_id"]] = atoms
            out.write(json.dumps({
                "fragment_id": row["fragment_id"], "sha256": row["sha256"],
                "atoms": atoms,
            }, ensure_ascii=False, sort_keys=True) + "\n")
            out.flush()
            if i % 20 == 0:
                print(f"  híbrido {i}/{len(rows)}")
    cost = (usage.get("input_tokens", 0) / 1e6 * HYBRID_PRICE_IN
            + usage.get("output_tokens", 0) / 1e6 * HYBRID_PRICE_OUT)
    receipts = {
        "instrument": "s269_mutation_harness --hybrid --execute",
        "created_utc": _now(),
        "model": mp.HYBRID_DETECTOR_MODEL,
        "usage": usage,
        "haiku_errors_fallback_det": errors,
        "total_cost_usd": round(cost, 4),
        "budget_usd_max": budget_usd,
        "no_retry": True,
    }
    return atoms_by_fragment, receipts


def run_arm(hybrid: bool, execute: bool) -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["freeze"]
    if sha256_file(COHORT_PATH) != frozen["cohort_sha256"]:
        raise RuntimeError("freeze roto: cohorte v3 ≠ prereg")
    if sha256_file(ROOT / "src/rag/must_preserve.py") != frozen["must_preserve_sha256"]:
        raise RuntimeError("freeze roto: must_preserve.py ≠ prereg")
    if templates_sha256() != frozen["templates_sha256"]:
        raise RuntimeError("freeze roto: templates ≠ prereg")
    rows = load_jsonl(COHORT_PATH)
    print(f"Cohorte v3 verificada (freeze OK): {len(rows)} filas")

    if hybrid:
        budget = float(prereg["hybrid"]["budget_usd_max"])
        estimate = _hybrid_cost_estimate(rows)
        print(f"Brazo HÍBRIDO — estimación: {json.dumps(estimate)} "
              f"(techo del prereg: ${budget})")
        if estimate["est_cost_usd"] > budget:
            print("ESTIMACIÓN > TECHO — no ejecutar sin revisar el prereg")
            return 1
        if not execute:
            print("\nPREFLIGHT (0 llamadas pagadas). Para ejecutar:")
            print("  python scripts/s269_mutation_harness.py --run --hybrid --execute")
            return 0
        atoms_by_fragment, receipts = _hybrid_atoms(rows, budget)
        HYBRID_RECEIPTS_PATH.write_text(
            json.dumps(receipts, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        results_path = RESULTS_HYBRID_PATH
        arm = "hybrid"
        print(f"Receipts: {HYBRID_RECEIPTS_PATH.relative_to(ROOT)} "
              f"(${receipts['total_cost_usd']})")
    else:
        atoms_by_fragment = {
            r["fragment_id"]: mp.detect_atoms(r["texto"]) for r in rows
        }
        results_path = RESULTS_DET_PATH
        arm = "det"

    done = {r["key"] for r in load_jsonl(results_path)}
    written = 0
    with results_path.open("a", encoding="utf-8", newline="\n") as out:
        def emit(result: dict) -> None:
            nonlocal written
            if result["key"] in done:
                return
            result["arm"] = arm
            out.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
            out.flush()
            written += 1

        for row in rows:
            for result in evaluate_fragment_rows(
                row, atoms_by_fragment[row["fragment_id"]]
            ):
                emit(result)
        for result in evaluate_cross_rows(rows, atoms_by_fragment):
            emit(result)
        for result in evaluate_attestation_rows(rows, atoms_by_fragment):
            emit(result)

    print(f"Resultados ({arm}): {results_path.relative_to(ROOT)} "
          f"(+{written} filas nuevas; checkpoint resumible)")
    print("Siguiente paso: python scripts/s269_stage1_v3_gate.py")
    return 0


# ─────────────────────────── freeze (prereg C4) ───────────────────────────

def freeze() -> int:
    if not COHORT_PATH.exists():
        raise RuntimeError("cohorte v3 no construida: corre --build-cohort primero")
    rows = load_jsonl(COHORT_PATH)
    build = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    prereg = {
        "schema": "s269_stage1_v3_prereg_v2",
        "status": "FROZEN_BEFORE_RUN",
        "created_utc": _now(),
        "spec_ref": "evals/s269_stage1_v3_mutation_spec_v1.md",
        "design_ref": "evals/s269_synthesis_portfolio_design_v1.md §1 (v2 dúo-adjudicado)",
        "predecessor": (
            "evals/s269_stage1_gate_v1.yaml (NO_GO v1, gold de modelo no fiable) + "
            "evals/s269_stage1_nogo_diagnosis_v1.md; MEDIDA seed-270 (binding v1): "
            "evals/s269_stage1_v3_prereg.yaml + evals/s269_stage1_v3_gate_v1.yaml + "
            "evals/s269_stage1_v3_results_det.jsonl — queda como EVIDENCIA, no se "
            "re-usa para el veredicto"
        ),
        "binding_contract": (
            "v2 (adjudicación del coordinador post-seed-270): presencia PARCIAL por "
            "familia para F-RANGE/F-BUNDLE/F-COUNT (≥1 token/número PROPIO del átomo "
            "en la ventana de cita; el solape genérico de anchors ya no liga) y "
            "contrato propio para F-MANDATORY (exigible con ≥2 tokens de contexto "
            "PROCEDIMENTAL del fragmento en la ventana; supresión de duplicados vía "
            "atom_satisfied; cap 4 intacto). Motivación taxonomy-derived s243: 11/12 "
            "misses = pérdida parcial dentro de estructura TOCADA + callouts "
            "obligatorios adyacentes a procedimientos que la respuesta da. Ver "
            "docstring de src/rag/must_preserve.py::atom_exigible_in"
        ),
        "gold": (
            "MECÁNICO POR CONSTRUCCIÓN (patrón S249, precedente in-repo precisión "
            "1.0/FP 0): mutación determinista con receipt exacto; sin etiquetadores "
            "modelo en el path del gold"
        ),
        "seed": SEED,
        "gates": {
            "mutation_recall_min_per_family": 0.80,
            "clean_noise_fp_max_rbc": 0,
            "clean_noise_mandatory_fp_max": 0,
            "cross_binding_fp_max": 0,
            "attestation_block_appends_max": 0,
            "coverage_min": 0.90,
            "clean_noise_definition": (
                "POR FAMILIA del átomo anexado: para F-RANGE/F-BUNDLE/F-COUNT todo "
                "anexo sobre borrador limpio es FP (=0). Para F-MANDATORY el FP se "
                "define como anexo DUPLICADO o NO-PROCEDIMENTAL (proc_overlap<2 en "
                "la ventana): anexar un callout obligatorio genuino no-duplicado "
                "junto a un procedimiento del fragmento citado NO es ruido — es la "
                "CONDUCTA OBJETIVO del contrato (s243 mandatory_safety_omission: el "
                "miss canónico es exactamente la respuesta que da el procedimiento "
                "y omite el callout adyacente); esos anexos se reportan aparte como "
                "mandatory_conduct_appends"
            ),
            "scoring": (
                "por MUTACIÓN individual (átomo), no booleano de familia (C1); "
                "cobertura = filas puntuables / filas generadas; las filas no "
                "puntuables se listan en el gate"
            ),
        },
        "freeze": {
            "must_preserve_sha256": sha256_file(ROOT / "src/rag/must_preserve.py"),
            "harness_sha256": sha256_file(ROOT / "scripts/s269_mutation_harness.py"),
            "templates_sha256": templates_sha256(),
            "templates_version": TEMPLATES_VERSION,
            "cohort_path": "evals/s269_mutation_cohort_v2.jsonl",
            "cohort_rows": len(rows),
            "cohort_sha256": sha256_file(COHORT_PATH),
            "build_report_sha256": sha256_file(BUILD_REPORT_PATH),
            "note": (
                "C4: el gate ABORTA si cualquiera de estos sha difiere (sha con "
                "normalización CRLF->LF, precedente s198)"
            ),
        },
        "cohort_composition": build["composition"],
        "population": {
            "corpus_docs_servibles": build["corpus_docs_servibles"],
            "excluded_docs": build["excluded_docs"],
            "eligible_docs": build["eligible_docs"],
            "docs_sampled": build["docs_sampled"],
            "fragments_screened": build["fragments_screened"],
        },
        "arms": {
            "det_only": "detector determinista puro ($0)",
            "hybrid": (
                "det + Haiku structured-output plano con grounding verbatim "
                "(validador código; --hybrid --execute)"
            ),
        },
        "hybrid": {
            "model": mp.HYBRID_DETECTOR_MODEL,
            "budget_usd_max": 4.0,
            "prices_usd_per_mtok": {"input": HYBRID_PRICE_IN, "output": HYBRID_PRICE_OUT},
            "no_retry": True,
            "runner": "scripts/s269_mutation_harness.py --run --hybrid (preflight "
                      "default; --execute gasta)",
        },
        "honest_declarations": [
            "REFINAMIENTO DE CONTRATO DECLARADO (adjudicación del coordinador): los "
            "36 clean-FP de seed-270 (todos anexos de átomos hermanos ligados por "
            "solape genérico de anchors) motivaron RE-EXAMINAR el contrato de "
            "binding. El refinamiento (presencia parcial / contexto procedimental) "
            "es TAXONOMY-DERIVED (s243), NO un ajuste contra los 36 ejemplos, y se "
            "valida en esta población FRESCA seed-271 (docs v1 + seed-270 "
            "excluidos). seed-270 queda como evidencia; no se re-usa para el "
            "veredicto.",
            "TUNING DESDE V1 DECLARADO: el léxico/patrones del detector se ajustaron "
            "con los misses de la cohorte v1 (diagnóstico) — población fresca en "
            "cada medida desde entonces.",
            "PREVALENCIA NO MEDIDA: el harness condiciona a mutación; no estima la "
            "prevalencia/ubicuidad de las familias en el corpus.",
            "SALUD DE FAMILIAS s243 = SUPUESTO de diseño, no hecho medido por este "
            "instrumento.",
            "PRE-SCREEN DETERMINISTA: la cohorte se pre-filtra con el detector "
            "determinista (subset del híbrido, $0); sesgo de selección controlado "
            "porque el gold es mecánico y el gate mide sobre mutaciones.",
            "COLISIONES: mutaciones cuyo valor eliminado re-aparece en el borrador "
            "por otro campo se excluyen con un guard independiente del mecanismo y "
            "se listan (no entran en el denominador de recall).",
            "clean_noise corre con TODOS los átomos del fragmento; el scoring es "
            "POR FAMILIA del átomo anexado (ver gates.clean_noise_definition).",
            "BINDING GUARD: mutaciones cuyo borrador template pierde la presencia "
            "parcial del átomo (contrato v2) se listan como no-puntuables "
            "(artefacto del template, no del mecanismo); la vía binding se mide en "
            "clean/cross.",
            "ITERACIÓN DE IMPLEMENTACIÓN DECLARADA (post 1ª pasada seed-271): la "
            "primera medida del contrato v2 dio 42 clean-FP RBC, TODOS bundles "
            "ligados por palabras FUNCIÓN de 2-3 letras ('de'/'el'/'the') — "
            "_STOPWORDS solo cubría palabras ≥4 letras porque asumía min_len=3. "
            "Fix de LÉXICO raíz (función cortas añadidas a _STOPWORDS): es "
            "implementación del contrato ('token PROPIO' no incluye preposiciones), "
            "no ajuste del contrato ni por-fila. Se re-congeló y re-midió sobre la "
            "misma cohorte seed-271; la 1ª pasada queda en el historial git.",
        ],
        "gate_runner": (
            "scripts/s269_stage1_v3_gate.py — umbrales LEÍDOS del prereg (única "
            "fuente) + constante espejo anti-tamper (M7); veredicto POR BRAZO"
        ),
        "gate_output": "evals/s269_stage1_v3_gate_v2.yaml",
    }
    PREREG_PATH.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Prereg v2 (binding v2) congelado: {PREREG_PATH.relative_to(ROOT)}")
    for k, v in prereg["freeze"].items():
        if k.endswith("sha256"):
            print(f"  {k}: {v[:16]}…")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-cohort", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--execute", action="store_true",
                        help="brazo híbrido: ejecuta las llamadas Haiku PAGADAS")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    if args.build_cohort:
        return build_cohort()
    if args.freeze:
        return freeze()
    if args.run:
        return run_arm(hybrid=args.hybrid, execute=args.execute)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
