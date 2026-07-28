#!/usr/bin/env python3
"""s282 QA-s83 — v2 RE-GATING by write-operation cohort (dúo r1 adjudication).

The dúo focal round r1 (``evals/s282_qa_s83_duo_r1_adjudication_v1.yaml``) RECHAZÓ
the v1 titular ("879 aplicables tal cual") as a T2 gate. The v1 instrument is kept
as TRIAGE; this v2 re-gates every s83 source_file by its **write operation** so the
auto-apply cohort is honest and recall-safe. It applies the 9 confirmed findings:

  1  CALIBRACION-NO-AUTORIZA   -> LQAS n=59/0-defect sample of the surviving
                                  auto-apply cohort, materialised for hand-verify.
  2  DETERMINISTA-NO-RECALL-SAFE -> corroborated via ALL-models (not primary) LEAVES
                                  auto-apply (to adjudicate); exact stays primary-vs-primary.
  3  FAMILIA-NO-IMPLEMENTADA   -> family cohort: pm CONSERVED (governed label), never
                                  replace; only advisory-axis fill; per-row write_op.
  4  COLISION-T3               -> rows overlapping the T3 packet are EXCLUDED (T3 owns
                                  them); cross-consistency check emitted.
  5  AUTO_CLEAN-CONFLATES      -> per-row write_op {corroborate_noop | fill_language_doctype
                                  | replace_pm | adjudicate | excluded_t3 | unmapped};
                                  disjoint -> adjudicate (replace on Haiku's word alone banned);
                                  language mismatches NOT auto-filled (advisory).
  6  S83-EMPTY-INFLADO         -> s83_empty leaves the applicable count.
  7  JUEZ-FABRICA              -> the judge is ONLY a safe-direction CONFLICT triage: it can
                                  PULL a row out of auto-apply, never ADD one in.
  8  CACHE-DEBIL               -> cache key = sha(source_file+prompt+model+content_sample+s83 record).
  9  COBERTURA-JUEZ-FINA       -> triage-only limitation; no auto-apply flows through the judge.

READ-ONLY, SELECT-only DB (PostgREST GET). Zero writes, zero paid model calls (the
judge is NOT re-run — the existing v1 cache is reused; $0). The deterministic
re-gating runs 2x byte-identical (asserted). Outputs restricted to this lane's
territory (``scripts/s282_qa_s83_*`` / ``evals/s282_qa_s83_*``). NO commits.

Usage:
  python scripts/s282_qa_s83_regate.py                      # re-gate + LQAS sample + content dump ($0)
  python scripts/s282_qa_s83_regate.py --report --lqas-verdict PASS
                                                            # build report_v2 (numbers from JSON v2)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -- import the v1 instrument as a module (reuse its deterministic derivation) ---
_spec = importlib.util.spec_from_file_location(
    "s282_qa_s83_instrument", ROOT / "scripts/s282_qa_s83_instrument.py")
inst = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
_spec.loader.exec_module(inst)                         # type: ignore[union-attr]

import src.rag.document_local_coverage as dlc  # noqa: E402

# -- static inputs --------------------------------------------------------------
T3_RESULT = ROOT / "evals/s281_h0t3_retag_packet_result_v1.json"
V1_RESULT = ROOT / "evals/s282_qa_s83_result_v1.json"
V1_CACHE = ROOT / "evals/s282_qa_s83_llm_cache_v1.jsonl"
CAL_CACHE = ROOT / "evals/s282_qa_s83_llm_cache_cal.jsonl"
LQAS_N = 59            # <5% defect @ 95% conf, accept-on-0 (batch_attested_v1)
LQAS_SEED = 282        # fixed seed -> deterministic stratified sample

# write_op cohort taxonomy (the 6 values)
WRITE_OPS = ["corroborate_noop", "fill_language_doctype", "replace_pm",
             "adjudicate", "excluded_t3", "unmapped"]
AUTO_APPLY = {"corroborate_noop", "fill_language_doctype"}


def _load_t3_overlap() -> tuple[set[str], list[dict[str, Any]]]:
    t3 = json.loads(T3_RESULT.read_text(encoding="utf-8"))
    recs = t3["census"]["records"]
    stems = {dlc.canonical_blob_stem(r["source_file"]) for r in recs} | {
        r["source_file"] for r in recs}
    return stems, recs


def _load_v1_cache() -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if V1_CACHE.exists():
        for line in V1_CACHE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                d = json.loads(line)
                cache[d["source_file"]] = d
    return cache


def _subrel(r: dict[str, Any]) -> str:
    rel = r["pm_relation"]
    if rel == "corroborated":
        return "corrob_prim" if "primario s83 (exacto)" in r.get("pm_note", "") else "corrob_allmodels"
    return rel


def _in_t3(sf: str, t3_stems: set[str]) -> bool:
    return sf in t3_stems or dlc.canonical_blob_stem(sf) in t3_stems


def _conf(r: dict[str, Any]) -> str:
    return str(r["s83"].get("s83_confidence"))


def assign_write_op(r: dict[str, Any], t3_stems: set[str],
                    judge_conflict_sfs: set[str]) -> tuple[str, str]:
    """Return (write_op, note). Priority: T3 > unmapped > pm-cohort; then judge safe-pull."""
    sf = r["source_file"]
    if _in_t3(sf, t3_stems):
        return "excluded_t3", "solape con el packet T3 — T3 es el dueño de este source_file"
    rel = _subrel(r)
    if rel == "no-active-doc":
        return "unmapped", "s83 source_file sin documento activo en DB"
    if rel == "corrob_prim":
        if _conf(r) == "low":
            return "adjudicate", "corroborado exacto pero s83_confidence=low -> Alberto"
        wo, note = "corroborate_noop", "doc-level pm == primario s83 (exacto) -> pm es NO-OP; fill advisory"
    elif rel == "corrob_allmodels":
        return "adjudicate", "corroborado solo via ALL-models (no primario) — no recall-safe (finding S2)"
    elif rel == "family":
        wo, note = "fill_language_doctype", "pm familia/variante gobernada -> CONSERVAR pm; solo fill advisory"
    elif rel == "disjoint":
        return "adjudicate", "pm DISJUNTO — replace requeriria adjudicacion (Haiku solo prohibido)"
    elif rel == "s83_generic":
        return "adjudicate", "s83 da descripcion generica no-modelo -> Alberto"
    elif rel == "s83_empty":
        return "adjudicate", "s83 no aporta modelo (unmapped-like) -> sale del conteo aplicable"
    elif rel == "doc_noise":
        return "adjudicate", "doc-level pm es ruido de filename; s83 sin corroborar -> Alberto (no auto-fill)"
    elif rel == "docs_disagree":
        return "adjudicate", "documentos activos discrepan en product_model -> Alberto"
    else:
        return "adjudicate", f"pm_relation={rel} no auto-aplicable"

    # judge safe-pull (finding 7): a CONFLICT triage can ONLY remove from auto-apply
    if wo in AUTO_APPLY and sf in judge_conflict_sfs:
        return "adjudicate", note + " | PERO el juez-triage marco CONFLICT -> sacado del auto-apply (direccion segura)"
    return wo, note


def fill_plan(r: dict[str, Any]) -> dict[str, Any]:
    """Per-axis fill decision (fill-only; never overwrite a contradicted value).

    LQAS (s282, this lane) found that s83 ``languages`` arrays over-include secondary
    languages: they tag 'en' whenever English tokens (product/UI/chemical names) appear
    even in a Spanish-authored doc (defect: MADT609/NAP-100). So the language fill is
    SPLIT: SINGLETON (one language) -> auto-apply (reliable primary); MULTI (>1) ->
    ADVISORY (Alberto/content-verify before applying). doc_type fill stays auto.
    """
    lf = r.get("language_flag")
    df = r.get("doc_type_flag")
    langs = r["s83"].get("languages") or []
    lang_fill_singleton = lf == "fill-singleton"                       # exactly one lang, DB empty
    lang_fill_multi = lf == "fill-multi"                               # >1 lang -> advisory (over-call risk)
    dtype_fill = df == "fill"                                          # DB empty, s83 provides
    return {
        "language_fill_singleton": lang_fill_singleton,               # AUTO
        "language_fill_multi_advisory": lang_fill_multi,              # ADVISORY (not auto)
        "language_value": langs if (lang_fill_singleton or lang_fill_multi) else None,
        "language_contradict": lf == "contradict",                    # -> advisory, NOT filled
        "doc_type_fill": dtype_fill,                                  # AUTO
        "doc_type_value": r["s83"].get("doc_type") if dtype_fill else None,
        "doc_type_differ": df == "differ",                            # -> advisory, NOT filled
    }


def t3_consistency(r: dict[str, Any], t3_rec: dict[str, Any]) -> dict[str, Any]:
    """Cross-check: does s83's proposal point the same way as T3's candidate?"""
    s83_cores = {inst._nk(x) for x in r["s83"].get("primary_models", []) if inst._nk(x)}
    s83_cores |= {inst._nk(x) for x in r["s83"].get("all_models", []) if inst._nk(x)}
    cand = t3_rec.get("candidate") or t3_rec.get("composite_candidate") or {}
    t3_models: list[str] = []
    if isinstance(cand, dict):
        for k in ("product_model", "models", "canonical_model", "model"):
            v = cand.get(k)
            if isinstance(v, list):
                t3_models += [str(x) for x in v]
            elif v:
                t3_models.append(str(v))
    elif isinstance(cand, list):
        t3_models += [str(x) for x in cand]
    t3_cores = {inst._nk(x) for x in t3_models if inst._nk(x)}
    if not s83_cores or not t3_cores:
        agree = "indeterminado"
    elif s83_cores & t3_cores:
        agree = "consistente"
    else:
        agree = "divergente"
    return {"t3_confidence": t3_rec.get("confidence"), "t3_candidate_models": sorted(t3_cores),
            "s83_cores": sorted(s83_cores), "direction": agree}


def cache_key_v2(rec: dict[str, Any], content_sample: list[dict[str, Any]]) -> str:
    """Finding 8: sha(source_file + prompt + model + content_sample + s83 record)."""
    prompt = inst._judge_prompt(rec, content_sample)
    payload = {
        "source_file": rec["source_file"], "model": inst.JUDGE_MODEL, "prompt": prompt,
        "content_sample": content_sample, "s83": rec.get("s83"),
    }
    return inst._stable_sha256(payload)


# -- deterministic re-gating (2x byte-identical) --------------------------------
def regate(records: list[dict[str, Any]], t3_stems: set[str],
           judge_conflict_sfs: set[str]) -> list[dict[str, Any]]:
    out = []
    for r in sorted(records, key=lambda x: x["source_file"]):
        wo, note = assign_write_op(r, t3_stems, judge_conflict_sfs)
        row = {
            "source_file": r["source_file"], "write_op": wo, "write_op_note": note,
            "pm_relation": r["pm_relation"], "subrel": _subrel(r),
            "s83_confidence": _conf(r),
            "doc_level_pm": r.get("document", {}).get("product_model"),
            "s83_primaries": r["s83"].get("primary_models"),
            "brand": inst._brand_of(r),
            "language_flag": r.get("language_flag"), "doc_type_flag": r.get("doc_type_flag"),
            "fill_plan": fill_plan(r) if wo in AUTO_APPLY else None,
        }
        out.append(row)
    return out


def _brand_stratified_sample(auto_rows: list[dict[str, Any]], n: int, seed: int) -> list[str]:
    """Deterministic stratified-by-brand sample of source_files (largest-remainder alloc)."""
    by_brand: dict[str, list[str]] = {}
    for r in sorted(auto_rows, key=lambda x: x["source_file"]):
        by_brand.setdefault(r["brand"], []).append(r["source_file"])
    total = sum(len(v) for v in by_brand.values())
    # largest-remainder allocation of n across brands proportional to size
    raw = {b: n * len(v) / total for b, v in by_brand.items()}
    alloc = {b: int(raw[b]) for b in by_brand}
    rem = n - sum(alloc.values())
    for b, _ in sorted(by_brand.items(), key=lambda kv: (-(raw[kv[0]] - int(raw[kv[0]])), kv[0]))[:rem]:
        alloc[b] += 1
    rng = random.Random(seed)
    picked: list[str] = []
    for b in sorted(by_brand.keys()):
        pool = sorted(by_brand[b])
        k = min(alloc.get(b, 0), len(pool))
        picked += sorted(rng.sample(pool, k)) if k else []
    return sorted(picked)


def build_report(payload: dict[str, Any], lqas_verdict: str, lqas_defects: list[str]) -> str:
    L: list[str] = []
    A = L.append
    cohorts = payload["write_op_distribution"]
    total = payload["n_source_files"]
    auto = cohorts.get("corroborate_noop", 0) + cohorts.get("fill_language_doctype", 0)

    A("# s282 QA-s83 — RE-GATING v2 por operación de escritura (dúo r1 ADJUDICADO)")
    A("")
    A("**El titular v1 «879 aplicables tal cual» MUERE.** El dúo focal r1 "
      "(`evals/s282_qa_s83_duo_r1_adjudication_v1.yaml`) lo RECHAZÓ como puerta del Tramo 2; "
      "el instrumento v1 se conserva como TRIAGE. Este v2 re-gatea cada `source_file` por su "
      "**operación de escritura** (`write_op`), recall-safe, aplicando los 9 hallazgos confirmados. "
      "READ-ONLY (PostgREST GET), 0 escrituras, 0 llamadas de modelo de pago (el juez NO se re-corre; "
      "se reusa el cache v1). Derivación determinista 2× byte-idéntica.")
    A("")
    fc = payload["freeze_contract"]
    A("## Freeze-contract")
    A("")
    A(f"- commit HEAD: `{fc['commit_head']}` (dirty: {fc['worktree_dirty']})")
    A(f"- corpus: chunks_v2={payload['corpus_fingerprint']['chunks_v2']['count']} · "
      f"documents={payload['corpus_fingerprint']['documents']['count']} · sha `{payload['corpus_fingerprint']['sha256'][:16]}`")
    A(f"- **re-gating determinista 2×: {'IDÉNTICO' if payload['deterministic_2x'] else 'DIVERGE'}** "
      f"(`{payload['regate_sha256_pass1'][:16]}` == `{payload['regate_sha256_pass2'][:16]}`)")
    A(f"- s83 modelos sha-LF `{fc['s83_models']['sha256_lf'][:16]}` · v1 cache reusado (0 llamadas nuevas)")
    A(f"- generado {fc['generated_utc']}")
    A("")

    A("## 1. Cohortes de OPERACIÓN DE ESCRITURA (recuento honesto v2)")
    A("")
    A(f"De {total} `source_file` s83. El **auto-apply** (SQL fill-only propuesto) = "
      f"`corroborate_noop` + `fill_language_doctype` = **{auto}** (NO 879). Todo lo demás → Alberto "
      "o fuera de alcance.")
    A("")
    A("| write_op | n | qué se escribiría | destino |")
    A("|---|---:|---|---|")
    desc = {
        "corroborate_noop": ("pm ya corroborado exacto (NO-OP) + fill `language`/`doc_type` vacíos", "**AUTO-APPLY**"),
        "fill_language_doctype": ("pm familia CONSERVADO (nunca replace) + fill `language`/`doc_type` vacíos", "**AUTO-APPLY**"),
        "replace_pm": ("reemplazo de pm — PROHIBIDO con sola palabra del juez (finding 5)", "vacío por diseño → adjudicate"),
        "adjudicate": ("pm en disputa/ruido/genérico/vía-all-models/low-conf/s83-vacío", "[ALBERTO]"),
        "excluded_t3": ("solape con packet T3 — T3 es el dueño", "excluido (T3)"),
        "unmapped": ("sin documento activo en DB", "fuera de alcance T2"),
    }
    for wo in WRITE_OPS:
        n = cohorts.get(wo, 0)
        d, dest = desc[wo]
        A(f"| `{wo}` | {n} | {d} | {dest} |")
    A(f"| **TOTAL** | **{total}** | | |")
    A("")
    A("### 1b. Desglose del `adjudicate` por relación pm (transparencia)")
    A("")
    A("| sub-relación pm | n | por qué a Alberto |")
    A("|---|---:|---|")
    subd = {
        "doc_noise": "doc-level pm = ruido de filename; s83 sin corroboración independiente",
        "disjoint": "pm DISJUNTO (candidato a conflicto real)",
        "s83_generic": "s83 da descripción genérica, no un modelo",
        "s83_empty": "s83 no aporta modelo (unmapped-like; sale del conteo aplicable — finding 6)",
        "corrob_allmodels": "corroborado solo vía ALL-models, no primario (no recall-safe — finding 2)",
        "corrob_prim": "corroborado exacto pero s83_confidence=low",
        "judge_pull": "sacado del auto-apply por el juez-triage CONFLICT (dirección segura — finding 7)",
    }
    for k, cnt in payload["adjudicate_breakdown"].items():
        A(f"| `{k}` | {cnt} | {subd.get(k, '')} |")
    A("")

    A("## 2. LQAS — muestra n=59, aceptación 0-defectos (batch_attested_v1)")
    A("")
    A(f"Muestra determinista (seed {LQAS_SEED}, estratificada por marca) de la cohorte auto-apply "
      f"({auto}). Estándar: 0 defectos ⇒ tasa real < 5% con 95% de confianza. **Verificada A MANO "
      "leyendo contenido real de chunks (SELECT), fila a fila** — artefacto "
      "`evals/s282_qa_s83_lqas_sample_v1.md`.")
    A("")
    verdict_line = {
        "PASS": f"**RESULTADO LQAS: PASA (0 defectos / {LQAS_N}).** La cohorte auto-apply "
                f"({auto}) queda ACEPTADA a <5% defecto (95% conf.) para la firma de Alberto.",
        "FAIL": f"**RESULTADO LQAS: RECHAZO ({len(lqas_defects)} defecto(s) / {LQAS_N}).** "
                "La cohorte NO pasa; se re-tría a adjudicación. Defectos: " + "; ".join(lqas_defects),
        "FAIL_RESCOPE": (
            f"**RESULTADO LQAS (cohorte AS-SCOPED = pm-noop + doc_type + language COMPLETO): NO PASA "
            f"el listón 0-defectos — {len(lqas_defects)} defecto / {LQAS_N}.** Desglose por eje: "
            "`product_model` (noop/conservado) **0/59** · `doc_type` (fill) **0/59** · `language` (fill) "
            f"**{len(lqas_defects)}/59**. Defecto: " + "; ".join(lqas_defects) + ". "
            "**Causa raíz:** el array `languages` de s83 over-incluye idiomas secundarios (tag 'en' cuando "
            "aparecen tokens ingleses — nombres de producto/UI/nomenclatura química — en un doc redactado en "
            "español). **REMEDIO recall-safe (aplicado a la PROPUESTA, no a DB):** `language` fill-MULTI → "
            "ADVISORY (Alberto/verificar-contenido); auto-apply = `pm-noop` + `doc_type` + `language`-SINGLETON. "
            "Esos tres ejes fueron **0-defecto en esta muestra** → fuerte evidencia; un re-draw LQAS "
            "confirmatorio sobre la cohorte re-scoped es el paso previo a la firma."),
        "PENDIENTE": "**RESULTADO LQAS: PENDIENTE de verificación manual.**",
    }.get(lqas_verdict, "**RESULTADO LQAS: ?**")
    A(verdict_line)
    A("")
    A("Muestra por marca (asignación largest-remainder):")
    A("")
    A("| marca | auto-apply | muestreados |")
    A("|---|---:|---:|")
    for b, tot in sorted(payload["lqas_brand_alloc"].items(), key=lambda kv: -kv[1][0]):
        A(f"| {b} | {tot[0]} | {tot[1]} |")
    A(f"| **TOTAL** | **{auto}** | **{sum(v[1] for v in payload['lqas_brand_alloc'].values())}** |")
    A("")

    A("## 3. Packet de CONFLICTOS para Alberto")
    A("")
    A(f"Unión de: juez-triage CONFLICT (no-T3) + pm-DISJUNTO (no-T3) + corroborado-vía-all-models "
      f"(no-T3) = **{payload['conflict_packet']['n_union']}** `source_file`. El juez es solo TRIAGE "
      "(dirección segura); nada se aplica; reversible.")
    A("")
    A(f"- juez-triage CONFLICT (no-T3): {payload['conflict_packet']['n_judge_conflict']}")
    A(f"- pm-DISJUNTO deterministas (no-T3): {payload['conflict_packet']['n_disjoint']}")
    A(f"- corroborado-vía-all-models (no-T3): {payload['conflict_packet']['n_allmodels']}")
    A("")
    A("Detalle completo (source_file · s83 · doc-pm · juez · relación) en "
      "`evals/s282_qa_s83_result_v2.json` (`conflict_packet.rows`). Los 89 del juez v1 se listan en "
      "`report_v1.md §3`; 2 de ellos caen en T3 (owned).")
    A("")

    A("## 4. Colisión T3 — check de consistencia cruzada (finding 4)")
    A("")
    tc = payload["t3_consistency"]
    A(f"Los **{tc['n']}** `source_file` que solapan con el packet T3 se EXCLUYEN (T3 es el dueño). "
      f"Chequeo de dirección s83↔T3: consistente={tc['consistente']} · divergente={tc['divergente']} · "
      f"indeterminado={tc['indeterminado']}. (El dúo estimó 24; el recuento real es {tc['n']} — TODOS "
      "los 28 source_files del census T3 mapean a un registro s83.)")
    A("")
    if tc["divergent_rows"]:
        A("Divergencias s83 vs T3 (para que Alberto sepa que ahí las dos fuentes no coinciden):")
        A("")
        A("| source_file | s83 cores | T3 candidato | T3 conf |")
        A("|---|---|---|---|")
        for d in tc["divergent_rows"]:
            A(f"| `{d['source_file'][:40]}` | {d['s83_cores'][:4]} | {d['t3_candidate_models'][:4]} | {d['t3_confidence']} |")
        A("")

    A("## 5. Fill plan del auto-apply (fill-only, reversible) — SQL propuesto §6")
    A("")
    fpl = payload["fill_summary"]
    A(f"- **AUTO** `doc_type` (DB vacío, s83 aporta): **{fpl['doc_type_fills']}** filas (0-defecto en LQAS)")
    A(f"- **AUTO** `language`-SINGLETON (un idioma, DB vacío): **{fpl['language_fills_singleton_auto']}** filas "
      "(0-defecto en LQAS)")
    A(f"- **ADVISORY** `language`-MULTI (>1 idioma, DB vacío): **{fpl['language_fills_multi_advisory']}** filas "
      "→ NO auto-apply (over-call de idioma detectado por LQAS: NAP-100). Alberto/verificar-contenido.")
    A(f"- `language` contradicho en DB (NO se rellena → advisory, finding 5): {fpl['language_contradict_in_auto']}")
    A(f"- `doc_type` distinto en DB (NO se rellena → advisory): {fpl['doc_type_differ_in_auto']}")
    A("")
    A("Regla de fill (finding 5 + regla 2 del lote, endurecida por el LQAS de esta lane): SOLO donde el eje "
      "esté vacío-en-DB sin contradicción; JAMÁS overwrite. `product_model` NUNCA se escribe en auto-apply "
      "(corroborate_noop = NO-OP; family = conservar). `language`-MULTI se degrada a ADVISORY porque el LQAS "
      "cazó que s83 over-incluye idiomas secundarios.")
    A("")

    A("## 6. PROPUESTA SQL del Tramo 2 (SOLO auto-apply · fill-only · por lotes por marca) — NO aplicada")
    A("")
    A("Ningún SQL se ejecuta aquí (READ-ONLY). Plantilla reversible, por marca, gateada por la firma "
      "LQAS de Alberto. `language`/`doc_type` se guardan como el array/valor s83; el `WHERE` exige que "
      "el campo esté hoy NULL (nunca overwrite). Reversible: `SET language=NULL` / `doc_type=NULL` para "
      "los `id` del lote.")
    A("")
    A("```sql")
    A("-- Ejemplo (marca=Notifier). Aplicar SOLO tras firma LQAS. Uno por marca.")
    A("-- Fuente de valores: evals/s282_qa_s83_result_v2.json (write_op in {corroborate_noop,fill_language_doctype})")
    A("-- AUTO = doc_type (todas) + language SOLO cuando el fill_plan es language_fill_singleton.")
    A("UPDATE documents d SET")
    A("  doc_type = COALESCE(d.doc_type, :s83_doc_type),        -- fill-only; NULL-guard")
    A("  language = COALESCE(d.language, :s83_language_singleton) -- SOLO singleton; multi=advisory")
    A("WHERE d.id = :document_id")
    A("  AND (d.doc_type IS NULL OR d.language IS NULL);        -- nunca overwrite")
    A("-- product_model: NO se toca (corroborate_noop = NO-OP; family = etiqueta gobernada conservada).")
    A("-- language-MULTI (>1 idioma): NO en el UPDATE — va al packet advisory para Alberto.")
    A("```")
    A("")
    A("El instrumento puede emitir el lote materializado por marca (id + valores) desde el JSON v2 "
      "cuando Alberto dé el GO; aquí se deja como propuesta.")
    A("")

    A("## 7. Honestidad — qué cambió vs v1 y qué NO juzga esto")
    A("")
    A("- **879 → auto-apply real = %d.** El 879 fusionaba corroboración exacta con AUTO_CLEAN del juez "
      "sobre WEAK (doc_noise/family/disjoint). El juez ya NO otorga auto-apply (finding 7/9)." % auto)
    A("- **`product_model` nunca se auto-escribe.** Solo `language`/`doc_type` vacíos, fill-only, reversible.")
    A("- **doc_noise (%d) → adjudicate**, no auto-apply: sin corroboración independiente de la identidad "
      "s83, el fill no es de fiar (recall-safe)." % payload["adjudicate_breakdown"].get("doc_noise", 0))
    A("- **La firma sigue siendo de Alberto.** El LQAS acota la tasa de defecto (<5%/95%), no la lleva a 0; "
      "es el mismo trade-off del contrato `batch_attested_v1`.")
    A("- **El juez es triage, no oráculo** (finding 7): solo saca filas del auto-apply o alimenta el packet "
      "de conflictos; nunca añade una fila al auto-apply.")
    A("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="build report_v2 from result_v2.json")
    ap.add_argument("--lqas-verdict", default="PENDIENTE",
                    choices=["PASS", "FAIL", "FAIL_RESCOPE", "PENDIENTE"])
    ap.add_argument("--lqas-defects", default="", help="';'-joined defect notes when FAIL")
    args = ap.parse_args(argv)

    result_path = ROOT / "evals/s282_qa_s83_result_v2.json"
    report_path = ROOT / "evals/s282_qa_s83_report_v2.md"

    if args.report:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        defects = [d for d in args.lqas_defects.split(";") if d.strip()]
        report_path.write_text(build_report(payload, args.lqas_verdict, defects), encoding="utf-8")
        print(f"report: {report_path} (lqas={args.lqas_verdict})")
        return 0

    # -- deterministic re-derivation (reuse v1 instrument) --
    inst._init_http()
    contract = inst.freeze_contract()
    fp_before = inst.corpus_fingerprint()
    s83 = inst._load_s83()
    inst._ORIG_SFS = sorted({str(json.loads(l)["source_file"])
                             for l in inst.S83_DOC_MODELS.read_text(encoding="utf-8").splitlines() if l.strip()})
    catalog = inst._load_catalog()
    documents = inst._get_all("documents", inst.DOC_SELECT, order="id.asc")
    chunks = inst._get_all("chunks_v2", "source_file,document_id", order="id.asc")
    chunk_map = inst._chunk_srcfile_to_docids(chunks)
    docmap_rows = [json.loads(l) for l in (inst.CATALOG_DIR / "doc_map.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    docmap_sf_to_docid: dict[str, list[str]] = {}
    for r in docmap_rows:
        if r.get("source_file") and r.get("document_id"):
            docmap_sf_to_docid.setdefault(str(r["source_file"]), []).append(str(r["document_id"]))

    canon = inst.derive(s83, documents, chunk_map, docmap_sf_to_docid, catalog)
    records = canon["records"]

    t3_stems, t3_recs = _load_t3_overlap()
    t3_by_stem: dict[str, dict[str, Any]] = {}
    for tr in t3_recs:
        t3_by_stem[dlc.canonical_blob_stem(tr["source_file"])] = tr
        t3_by_stem[tr["source_file"]] = tr

    v1_cache = _load_v1_cache()
    judge_conflict_sfs = {sf for sf, j in v1_cache.items() if j.get("verdict") == "CONFLICT"}

    # 2x deterministic re-gating
    rg1 = regate(records, t3_stems, judge_conflict_sfs)
    rg2 = regate(records, t3_stems, judge_conflict_sfs)
    sha1 = inst._stable_sha256(rg1)
    sha2 = inst._stable_sha256(rg2)
    deterministic = sha1 == sha2

    from collections import Counter
    wo_dist = Counter(r["write_op"] for r in rg1)

    # adjudicate breakdown (by subrel + judge_pull)
    adj_break: dict[str, int] = {}
    for r in rg1:
        if r["write_op"] != "adjudicate":
            continue
        note = r["write_op_note"]
        if "juez-triage marco CONFLICT" in note:
            key = "judge_pull"
        elif r["subrel"] == "corrob_prim":
            key = "corrob_prim"
        else:
            key = r["subrel"]
        adj_break[key] = adj_break.get(key, 0) + 1

    # auto-apply rows + fill summary
    auto_rows = [r for r in rg1 if r["write_op"] in AUTO_APPLY]
    fp = {"language_fills_singleton_auto": sum(1 for r in auto_rows if r["fill_plan"]["language_fill_singleton"]),
          "language_fills_multi_advisory": sum(1 for r in auto_rows if r["fill_plan"]["language_fill_multi_advisory"]),
          "doc_type_fills": sum(1 for r in auto_rows if r["fill_plan"]["doc_type_fill"]),
          "language_contradict_in_auto": sum(1 for r in auto_rows if r["fill_plan"]["language_contradict"]),
          "doc_type_differ_in_auto": sum(1 for r in auto_rows if r["fill_plan"]["doc_type_differ"])}

    # LQAS sample
    sample_sfs = _brand_stratified_sample(auto_rows, LQAS_N, LQAS_SEED)
    by_brand_auto = Counter(r["brand"] for r in auto_rows)
    by_brand_samp = Counter(next(r["brand"] for r in auto_rows if r["source_file"] == sf) for sf in sample_sfs)
    lqas_brand_alloc = {b: [by_brand_auto[b], by_brand_samp.get(b, 0)] for b in by_brand_auto}

    # fetch content for the sample (SELECT, read-only) for hand-verification
    rec_by_sf = {r["source_file"]: r for r in records}
    sample_dump = []
    for sf in sample_sfs:
        content = inst._fetch_content_sample(sf)
        rg = next(r for r in rg1 if r["source_file"] == sf)
        sample_dump.append({
            "source_file": sf, "write_op": rg["write_op"], "brand": rg["brand"],
            "doc_level_pm": rg["doc_level_pm"], "s83_primaries": rg["s83_primaries"],
            "s83_languages": rec_by_sf[sf]["s83"].get("languages"),
            "s83_doc_type": rec_by_sf[sf]["s83"].get("doc_type"),
            "fill_plan": rg["fill_plan"], "content": content,
        })

    # conflict packet
    def in_t3(sf): return _in_t3(sf, t3_stems)
    judge_conf_not_t3 = [sf for sf in judge_conflict_sfs if not in_t3(sf)]
    disjoint_not_t3 = [r["source_file"] for r in rg1 if r["subrel"] == "disjoint" and not in_t3(r["source_file"])]
    allmodels_not_t3 = [r["source_file"] for r in rg1 if r["subrel"] == "corrob_allmodels" and not in_t3(r["source_file"])]
    conf_union = sorted(set(judge_conf_not_t3) | set(disjoint_not_t3) | set(allmodels_not_t3))
    conflict_rows = []
    for sf in conf_union:
        rg = next(r for r in rg1 if r["source_file"] == sf)
        j = v1_cache.get(sf, {})
        conflict_rows.append({
            "source_file": sf, "subrel": rg["subrel"], "doc_level_pm": rg["doc_level_pm"],
            "s83_primaries": rg["s83_primaries"], "judge_verdict": j.get("verdict"),
            "judge_pm_call": j.get("product_model_call"), "judge_reason": j.get("reason"),
        })

    # T3 consistency
    t3_rows = []
    for r in records:
        if not in_t3(r["source_file"]):
            continue
        tr = t3_by_stem.get(r["source_file"]) or t3_by_stem.get(dlc.canonical_blob_stem(r["source_file"]))
        if tr:
            tc = t3_consistency(r, tr)
            t3_rows.append({"source_file": r["source_file"], **tc})
    t3_summary = {
        "n": len(t3_rows),
        "consistente": sum(1 for x in t3_rows if x["direction"] == "consistente"),
        "divergente": sum(1 for x in t3_rows if x["direction"] == "divergente"),
        "indeterminado": sum(1 for x in t3_rows if x["direction"] == "indeterminado"),
        "divergent_rows": [x for x in t3_rows if x["direction"] == "divergente"],
        "all_rows": t3_rows,
    }

    # cache v2 rekey (finding 8) — NO new LLM calls
    cache_v2_path = ROOT / "evals/s282_qa_s83_llm_cache_v2.jsonl"
    n_rekey = 0
    with cache_v2_path.open("w", encoding="utf-8") as fh:
        for sf, entry in sorted(v1_cache.items()):
            rec = rec_by_sf.get(sf)
            content = entry.get("content_sample")
            if rec is None or content is None:
                continue
            key = cache_key_v2(rec, content)
            fh.write(json.dumps({"cache_key": key, **entry}, ensure_ascii=False) + "\n")
            n_rekey += 1

    fp_after = inst.corpus_fingerprint()
    payload = {
        "schema": "s282_qa_s83_regate_v2",
        "authority": "DEVELOPMENT_QA_READ_ONLY_SELECT_ONLY_ZERO_WRITES_ZERO_PAID_MODEL",
        "freeze_contract": contract, "corpus_fingerprint": fp_after,
        "deterministic_2x": deterministic and fp_before["sha256"] == fp_after["sha256"],
        "regate_sha256_pass1": sha1, "regate_sha256_pass2": sha2,
        "n_source_files": len(rg1),
        "write_op_distribution": dict(wo_dist),
        "auto_apply_n": len(auto_rows),
        "adjudicate_breakdown": dict(sorted(adj_break.items(), key=lambda kv: -kv[1])),
        "fill_summary": fp,
        "lqas": {"n": LQAS_N, "seed": LQAS_SEED, "sample_source_files": sample_sfs},
        "lqas_brand_alloc": lqas_brand_alloc,
        "conflict_packet": {
            "n_union": len(conf_union), "n_judge_conflict": len(judge_conf_not_t3),
            "n_disjoint": len(disjoint_not_t3), "n_allmodels": len(allmodels_not_t3),
            "rows": conflict_rows,
        },
        "t3_consistency": t3_summary,
        "cache_v2": {"path": str(cache_v2_path.relative_to(ROOT)), "n_rekeyed": n_rekey,
                     "key_formula": "sha256(source_file+prompt+model+content_sample+s83_record)"},
        "records": rg1,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    (ROOT / "evals/s282_qa_s83_lqas_content_v2.json").write_text(
        json.dumps(sample_dump, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")

    print(f"deterministic_2x={payload['deterministic_2x']} sha={sha1[:16]}")
    print(f"write_op: {dict(wo_dist)}")
    print(f"auto_apply={len(auto_rows)}  adjudicate_breakdown={payload['adjudicate_breakdown']}")
    print(f"fill_summary={fp}")
    print(f"LQAS sample n={len(sample_sfs)} (seed {LQAS_SEED}); content dumped -> lqas_content_v2.json")
    print(f"conflict_packet union={len(conf_union)}  T3 overlap={t3_summary['n']} (div={t3_summary['divergente']})")
    print(f"cache_v2 rekeyed={n_rekey}")
    print(f"result: {result_path}")
    return 0 if payload["deterministic_2x"] else 2


if __name__ == "__main__":
    sys.exit(main())
