#!/usr/bin/env python3
"""s324d_estabilidad_sintesis.py — ¿cuánto de los «no OK» del FULL es RUIDO de N=1?

Contexto. El FULL de factlevel (`scripts/factlevel_assessment.py {smoke|full}`) etiqueta cada
hecho con UNA sola generación por gold (N=1). El replay congelado de s324c
(`evals/s324c_replay_congelado_flips_v1.md`) demostró sobre 4 hechos que **con la vista de
contexto IDÉNTICA la respuesta varía** (firmes 3/5, 1/5, 2/5, 4/5): la varianza dominante es de
SÍNTESIS, no de serving. Consecuencia: parte de los «no OK» del FULL podrían ser RUIDO de una
sola muestra y no defectos estables. Esta sonda MIDE cuánto.

Método (reutiliza el mecanismo YA existente, no inventa uno):
  · un turno real por el seam (`execute_rag_turn` con los adapters del brazo base de la sonda
    s293 / de `FA.run_pipeline`); la vista que recibe `generate_answer` (prefijo + appends de
    coverage) se CONGELA (deepcopy + ids + orden + hashes);
  · **N=5** respuestas sobre esa MISMA vista: rep0 dentro del seam; reps 1..4 con el mismo
    callee que `FA.gen_answer_only` (s289/DEC-168), llamado directo para conservar usage/stop;
  · cada respuesta se juzga con el juez canónico `FA.judge_conveyed21` (GPT-5.5, K=5) y
    `FA.THRESH_FIRM` INTACTO. La vara no se toca: es una MEDICIÓN, no un experimento de mejora.

AGRUPACIÓN POR GOLD (qid). La generación es por-gold, no por-hecho: el FULL juzga TODOS los
hechos de un gold contra UNA misma respuesta. Por eso se congela UNA vista por qid y las 5
respuestas se juzgan para CADA hecho-diana de ese gold. No baja N (sigue 5); baja el coste.

Clases (pre-declaradas, sobre el brazo congelado con N=5):
  ESTABLE_MISS  0/5 firmes  → defecto real (el FULL acertó al marcarlo no-OK)
  INESTABLE     0<firmes<5  → el FULL lo etiqueta por azar de una sola muestra
  ESTABLE_OK    5/5 firmes  → el FULL lo marcó no-OK por mala suerte de la muestra

Universo. Los hechos «no-OK» del FULL más reciente (`evals/s100_factlevel_full_v3_20260816.yaml`,
40 golds) = los que tienen `conveyed_yes` por debajo de `THRESH_FIRM` (=4). Son 15: 12 de clase
terminal `synthesis-miss` (consenso de miss primario+dual) y 3 que el dual-judge rescató a `OK`
(`judge_disagreement`). Prioridad de medición: (1) los 12 de síntesis, primero los «servido y
omitido» (submotivo `omitted`); (2) el resto de síntesis; (3) los 3 rescatados por el dual.

ASIMETRÍA DE VARA declarada (no se corrige: la vara es la del encargo). Aquí «firme» = juez
PRIMARIO ≥4/5, igual que en s324c. En el FULL un hecho es no-OK sólo si el primario da miss Y
el dual (Opus 4.8) tampoco lo da por firme. Como OK_FULL(rep) ⊇ firme_primario(rep), un
ESTABLE_MISS medido aquí podría ser INESTABLE bajo la regla completa del FULL ⇒ el recuento de
ESTABLE_MISS es una COTA SUPERIOR del defecto estable y la fracción de ruido una COTA INFERIOR.

Uso:
  python scripts/s324d_estabilidad_sintesis.py [--limit N] [--presupuesto 25]
        [--n 5] [--facts cat001#3,...] [--force] [--md-only] [--recost] [--dry-run]
Salidas (ÚNICAS): evals/s324d_estabilidad_sintesis_v1.json + .md
El JSON se escribe tras CADA gold (resumible: no re-mide lo ya hecho). Un fallo a mitad deja
recibo PARCIAL con lo medido (patrón de `scripts/s293_reachability_probe.py`).
NO cambia el juez, ni los prompts, ni los flags. NO escribe en Supabase. NO diseña levers.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

# Importar el instrumento fija DEMO_FLAGS en import-time (freeze-contract) ANTES del pipeline y
# carga el .env — misma secuencia que la sonda s293 y el replay s324c.
import scripts.factlevel_assessment as FA  # noqa: E402
from scripts.usage_meter import METER, PRICES_USD_PER_M, cost_of  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.generator import admitted_evidence_rows  # noqa: E402
from src.rag.post_rerank_coverage import coverage_context_content  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402

FULL = ROOT / "evals" / "s100_factlevel_full_v3_20260816.yaml"
OUT_JSON = ROOT / "evals" / "s324d_estabilidad_sintesis_v1.json"
OUT_MD = ROOT / "evals" / "s324d_estabilidad_sintesis_v1.md"
PRESUPUESTO_DEFAULT = 25.0
# Estimación conservadora del coste del PRIMER gold (después se usa el coste real medido para
# decidir si cabe el siguiente): 6 llamadas Sonnet + n_facts×5×5 llamadas de juez.
COSTE_ESTIMADO_BASE = 0.45
COSTE_ESTIMADO_POR_HECHO = 0.60


def _sha(text: str, n: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sello_freeze() -> dict:
    """Sello PARCIAL (mismo espíritu que la sonda s293 y el replay s324c). El corpus se huella
    aparte, al INICIO y al FINAL (y por gold), porque hoy mutó: re-ingesta de
    HLSI-TI-007_VSN-4REL + retag de `documents.product_model` en 55 docs."""
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, cwd=ROOT).stdout.decode().strip()
    dirty = subprocess.run(["git", "status", "--short"], capture_output=True, cwd=ROOT).stdout.decode().strip().splitlines()
    return {
        "git_sha": git_sha,
        "git_dirty": dirty,
        "CHUNKS_TABLE": FA.CHUNKS_TABLE,
        "RETRIEVAL_TOP_K": FA.RETRIEVAL_TOP_K,
        "RERANK_TOP_K": FA.RERANK_TOP_K,
        "RERANKER_BACKEND": FA.RERANKER_BACKEND,
        "MERGE_STRATEGY": FA.MERGE_STRATEGY,
        "LLM_MAX_TOKENS": FA.LLM_MAX_TOKENS,
        "LLM_MODEL": FA.LLM_MODEL,
        "GENERATOR_PROMPT_VARIANT": os.getenv("GENERATOR_PROMPT_VARIANT"),
        "juez": {"model": FA.JUDGE_MODEL, "K": FA.K, "THRESH_FIRM": FA.THRESH_FIRM,
                 "funcion": "scripts.factlevel_assessment.judge_conveyed21 (PRIMARIO, sin dual — ver "
                            "«asimetría de vara» en el docstring)"},
        "INSTRUMENT_VERSION": FA.INSTRUMENT_VERSION,
        "DEMO_FLAGS": dict(FA.DEMO_FLAGS),
        "sello_no_cubre": ["config física del índice", "versión de embeddings", "seeds",
                            "closure del código", "mutaciones in-place del corpus (solo count+max_created_at)"],
    }


# ───────────────────────── universo: los no-OK del FULL ─────────────────────────
def _submotivo_str(f: dict) -> str | None:
    sm = f.get("submotivo")
    if isinstance(sm, dict):
        return sm.get("submotivo")
    return sm


def prioridad(f: dict) -> int:
    """(1) síntesis + `omitted` («servido y omitido»); (2) resto de síntesis; (3) rescatados por el dual."""
    if f["clase_full"] == "synthesis-miss":
        return 0 if f["submotivo"] == "omitted" else 1
    return 2


def universo_no_ok() -> list[dict]:
    doc = yaml.safe_load(open(FULL, encoding="utf-8"))
    # cruce con el gold-dev VIVO: si una pregunta/valor/texto se editó desde el FULL, se DECLARA
    # (no se aborta: la medición sigue sobre lo que el FULL midió, que es lo que se audita).
    try:
        from scripts.retrieval_miss_judge import load_dev, core_facts
        dev = {g["qid"]: {"question": g.get("question"),
                          "valores": {(f.get("valor") or "") for f in core_facts(g)}}
               for g in load_dev()}
    except Exception as exc:                                            # noqa: BLE001
        dev = {}
        print(f"(aviso) no se pudo cargar el gold-dev vivo para el cruce: {type(exc).__name__}: {exc}", flush=True)
    out = []
    for g in doc["per_gold"]:
        for f in g.get("facts") or []:
            cy = f.get("conveyed_yes")
            if cy is None or cy >= FA.THRESH_FIRM:
                continue
            gd = dev.get(g["qid"]) or {}
            deriva = []
            if gd and gd.get("question") != g["question"]:
                deriva.append("question")
            if gd and f["valor"] not in gd["valores"]:
                deriva.append("valor")
            out.append({
                "qid": g["qid"], "fact_key": f["key"],
                "fact_prefix": f["key"].split(":")[0],
                "valor": f["valor"], "texto": (f.get("texto") or "").strip(),
                "question": g["question"],
                "clase_full": f.get("clase"), "conveyed_yes": cy,
                "conveyed_yes_judge2": f.get("conveyed_yes_judge2"),
                "judge_disagreement": bool(f.get("judge_disagreement")),
                "stability_full": f.get("stability"),
                "submotivo": _submotivo_str(f), "in_topk": f.get("in_topk"),
                "served_ids8_full": [str(s)[:8] for s in (g.get("served_ids") or [])],
                "deriva_vs_gold_dev": deriva,
            })
    out.sort(key=lambda f: (prioridad(f), f["qid"], f["fact_prefix"]))
    return out


def agrupar_por_gold(facts: list[dict]) -> list[dict]:
    """Un turno + una vista congelada por QID (la generación es por-gold, como en el FULL)."""
    grupos: dict[str, dict] = {}
    for f in facts:
        g = grupos.setdefault(f["qid"], {"qid": f["qid"], "question": f["question"], "facts": []})
        g["facts"].append(f)
    orden = sorted(grupos.values(), key=lambda g: min(prioridad(f) for f in g["facts"]))
    return orden


# ───────────────────────── captura de la vista congelada ─────────────────────────
def composition_record(view: list[dict], n_prefix: int | None) -> dict:
    """ids + orden + hashes de la vista TAL COMO la ve el generador (idéntico a s324c):
    `served_sha` = hash de `coverage_context_content(chunk)` (el excerpt que entra al prompt);
    `hdr_sha` = campos que el generador imprime en la cabecera; `hash_view` = hash del conjunto
    ordenado (proxy del user_message, sin system prompt); `hash_ids` = identidad+orden."""
    admitted = {str(r.get("id") or "") for r in admitted_evidence_rows(view)}
    rows = []
    for i, c in enumerate(view, start=1):
        served = coverage_context_content(c)
        cid = str(c.get("id") or "")
        hdr = json.dumps([c.get("product_model"), c.get("section_title"), c.get("content_type"),
                          round(float(c.get("similarity") or 0.0), 2), c.get("source_file"),
                          c.get("document_revision"), c.get("document_revision_date"),
                          bool(c.get("has_diagram") and c.get("diagram_url"))], ensure_ascii=False)
        rows.append({
            "pos": i, "id": cid, "id8": cid[:8], "en_prefijo": (n_prefix is not None and i <= n_prefix),
            "retrieval_lane": c.get("retrieval_lane"), "admitida": cid in admitted,
            "similarity": round(float(c.get("similarity") or 0.0), 6),
            "source_file": c.get("source_file"), "chunk_index": c.get("chunk_index"),
            "page_number": c.get("page_number"), "product_model": c.get("product_model"),
            "section_title": (c.get("section_title") or "")[:120],
            "content_sha": _sha(str(c.get("content") or "")), "served_sha": _sha(served),
            "served_chars": len(served), "hdr_sha": _sha(hdr),
        })
    hash_ids = _sha(json.dumps([r["id"] for r in rows]), 16)
    hash_view = _sha(json.dumps([[r["id"], r["hdr_sha"], r["served_sha"], r["admitida"]] for r in rows]), 16)
    return {"n_rows": len(rows), "n_prefix": n_prefix, "n_admitidas": len(admitted),
            "hash_ids": hash_ids, "hash_view": hash_view, "ids8": [r["id8"] for r in rows], "rows": rows}


def run_turn_capturing(question: str) -> dict:
    """UN turno por el seam con los adapters del harness (`FA._capture_retrieve`,
    `FA._eval_strict_rerank`, shadow, generate) — espejo de `FA.run_pipeline` y del brazo base de
    la sonda s293. Congela (deepcopy) la vista que recibe el generador. Retry 1× si el coverage
    hace fail-open (`status=error`), la regla canónica de `FA.run_pipeline`."""
    captured: dict = {}

    def generate(query, chunks, available_models=None):
        rows = [dict(c) for c in chunks]
        captured["view"] = copy.deepcopy(rows)      # vista EXACTA que entra a generate_answer
        METER.phase = "generate"
        t0 = time.time()
        try:
            gen = FA.generate_answer(query, rows, available_models=available_models)
        finally:
            METER.phase = "turn"
        captured["gen"] = gen
        captured["gen_secs"] = round(time.time() - t0, 1)
        return gen

    retried = False
    t0 = time.time()
    for _ in range(2):
        METER.phase = "turn"
        pipeline = execute_rag_turn(
            query=question, query_for_retrieval=question, target_models=None, available_models=None,
            retrieval_top_k=RETRIEVAL_TOP_K, rerank_top_k=RERANK_TOP_K,
            adapters=RagServingAdapters(retrieve=FA._capture_retrieve, rerank=FA._eval_strict_rerank,
                                        observe_structural_shadow=observe_structural_neighbor_shadow,
                                        generate=generate),
        )
        trace = pipeline.get("coverage_trace") or {}
        if trace.get("status") != "error":
            break
        retried = True
    METER.phase = "idle"
    gen = captured.get("gen") or {}
    view = captured.get("view") or []
    return {
        "answer": gen.get("answer", ""),
        "gen_meta": {"stop_reason": gen.get("stop_reason"), "input_tokens": gen.get("input_tokens"),
                     "output_tokens": gen.get("output_tokens"), "secs": captured.get("gen_secs")},
        "view": view,
        "composition": composition_record(view, pipeline.get("reranked_rows")),
        "coverage_status": trace.get("status"), "coverage_retry": retried,
        "coverage_appended_ids8": [str(x)[:8] for x in (trace.get("appended_ids") or [])],
        "pool_ids8": [str(c.get("id") or "")[:8] for c in FA._CAPTURED_POOL],
        "retrieval_health": pipeline.get("retrieval_health"),
        "stage_timings": pipeline.get("stage_timings"),
        "turn_secs": round(time.time() - t0, 1),
    }


def gen_from_view(question: str, view: list[dict]) -> dict:
    """Generación FUERA del seam sobre la vista congelada. Mismo callee que
    `FA.gen_answer_only(question, deepcopy(view))` (s289 G-3), llamado directo para conservar
    stop_reason/usage. `available_models=None` como en la ruta harness."""
    METER.phase = "generate"
    t0 = time.time()
    try:
        gen = FA.generate_answer(question, copy.deepcopy(view), available_models=None)
    finally:
        METER.phase = "idle"
    return {"answer": gen.get("answer", ""),
            "gen_meta": {"stop_reason": gen.get("stop_reason"), "input_tokens": gen.get("input_tokens"),
                         "output_tokens": gen.get("output_tokens"), "secs": round(time.time() - t0, 1)}}


def judge(valor: str, texto: str, answer: str) -> dict:
    METER.phase = "judge"
    try:
        v = FA.judge_conveyed21(valor, texto, answer)
    finally:
        METER.phase = "idle"
    return {"yes": v["yes"], "n_fail": v["n_fail"], "firm": v["yes"] >= FA.THRESH_FIRM}


def clasificar(firmes: int, n: int) -> tuple[str, str]:
    if firmes == 0:
        return "ESTABLE_MISS", f"0/{n} firmes con la MISMA vista congelada: defecto estable (el FULL acertó)"
    if firmes == n:
        return "ESTABLE_OK", f"{n}/{n} firmes con la MISMA vista: el FULL lo marcó no-OK por mala suerte de la muestra"
    return "INESTABLE", f"{firmes}/{n} firmes con la MISMA vista: la etiqueta del FULL (N=1) sale al azar"


# ───────────────────────── medición de un gold ─────────────────────────
def medir_gold(grupo: dict, n: int) -> dict:
    qid, question, facts = grupo["qid"], grupo["question"], grupo["facts"]
    since = METER.snapshot()
    started = now_iso()
    corpus_ini = FA.corpus_fingerprint()
    print(f"\n=== {qid} · {len(facts)} hecho(s) · N={n} · {started}", flush=True)

    cap = run_turn_capturing(question)
    comp = cap["composition"]
    print(f"  vista congelada: {comp['n_rows']} filas (prefijo {comp['n_prefix']}, admitidas "
          f"{comp['n_admitidas']}) hash_ids={comp['hash_ids']} hash_view={comp['hash_view']} "
          f"coverage={cap['coverage_status']} retry={cap['coverage_retry']} ({cap['turn_secs']}s)", flush=True)

    gens = [{"rep": 0, "en_seam": True, "answer": cap["answer"], "gen_meta": cap["gen_meta"]}]
    for i in range(1, n):
        g = gen_from_view(question, cap["view"])
        gens.append({"rep": i, "en_seam": False, **g})
        print(f"  rep{i}: gen {g['gen_meta']['secs']}s stop={g['gen_meta']['stop_reason']} "
              f"out={g['gen_meta']['output_tokens']}", flush=True)

    hechos_out = []
    for f in facts:
        votos, firmes, n_fail = [], 0, 0
        for g in gens:
            j = judge(f["valor"], f["texto"], g["answer"])
            votos.append(j)
            firmes += int(j["firm"])
            n_fail += j["n_fail"]
        clase, motivo = clasificar(firmes, len(gens))
        print(f"  {f['fact_prefix']} «{f['valor'][:38]}»: votos {[v['yes'] for v in votos]} → "
              f"firmes {firmes}/{len(gens)} ⇒ {clase}", flush=True)
        hechos_out.append({**f, "n": len(gens), "firmes": firmes,
                           "yes": [v["yes"] for v in votos],
                           "juez_n_fail_total": n_fail,
                           "clase_s324d": clase, "clase_motivo": motivo})

    usage = METER.summary(since)
    coste = cost_of(usage, PRICES_USD_PER_M)
    corpus_fin = FA.corpus_fingerprint()
    print(f"  ⇒ {qid}: ${coste['usd_total']:.2f} ({usage['n_calls']} llamadas) · {now_iso()}", flush=True)
    return {
        "qid": qid, "question": question,
        "started_at": started, "finished_at": now_iso(),
        "corpus_al_empezar": corpus_ini, "corpus_al_terminar": corpus_fin,
        "vista_congelada": {
            "composition": comp, "coverage_status": cap["coverage_status"],
            "coverage_retry": cap["coverage_retry"], "coverage_appended_ids8": cap["coverage_appended_ids8"],
            "pool_ids8": cap["pool_ids8"], "retrieval_health": cap["retrieval_health"],
            "stage_timings": cap["stage_timings"], "turn_secs": cap["turn_secs"],
            "filas": cap["view"],
        },
        "generaciones": gens,
        "hechos": hechos_out,
        "uso": usage, "coste": coste,
    }


# ───────────────────────── persistencia ─────────────────────────
def load_doc() -> dict | None:
    if OUT_JSON.exists():
        try:
            return json.load(open(OUT_JSON, encoding="utf-8"))
        except Exception:
            return None
    return None


def save_doc(doc: dict) -> None:
    agg: dict[str, dict] = {}
    n_calls = 0
    for g in doc["golds"]:
        n_calls += g["uso"]["n_calls"]
        for a in g["uso"]["by_model_phase"]:
            key = f"{a['model']}|{a['phase']}"
            b = agg.setdefault(key, {"model": a["model"], "phase": a["phase"], "calls": 0, "in": 0,
                                     "out": 0, "cache_read": 0, "cache_write": 0})
            for k in ("calls", "in", "out", "cache_read", "cache_write"):
                b[k] += a[k]
    doc["uso_total"] = {"n_calls": n_calls,
                        "by_model_phase": sorted(agg.values(), key=lambda x: (x["model"] or "", x["phase"]))}
    doc["coste_total"] = cost_of(doc["uso_total"], PRICES_USD_PER_M)
    # «medido» se deriva de los DATOS (hay filas de usage reales), no del estado del medidor al
    # escribir: `--md-only`/`--recost` no instalan el medidor y no deben degradar un recibo ya
    # medido a «NO MEDIDO» (Sol r34: «$0» y «no medido» no son lo mismo).
    doc["coste_medido"] = doc["uso_total"]["n_calls"] > 0 or METER.disponible()
    recuento: dict[str, list[str]] = {}
    for g in doc["golds"]:
        for f in g["hechos"]:
            recuento.setdefault(f["clase_s324d"], []).append(f["fact_prefix"])
    doc["recuento"] = recuento
    medidos = {f["fact_prefix"] for g in doc["golds"] for f in g["hechos"]}
    doc["cobertura"] = {
        "n_no_ok_en_el_FULL": len(doc["universo"]),
        "n_medidos": len(medidos),
        "medidos": sorted(medidos),
        "sin_medir": [f["fact_prefix"] for f in doc["universo"] if f["fact_prefix"] not in medidos],
    }
    tmp = OUT_JSON.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, OUT_JSON)


# ───────────────────────── informe MD (≤700 palabras) ─────────────────────────
def write_md(doc: dict) -> None:
    s = doc["sello_freeze_PARCIAL"]
    tot = doc["coste_total"]
    cob = doc["cobertura"]
    rec = doc["recuento"]
    hechos = [f for g in doc["golds"] for f in g["hechos"]]
    by_qid = {g["qid"]: g for g in doc["golds"]}
    n_est_miss, n_inest, n_est_ok = (len(rec.get(k, [])) for k in ("ESTABLE_MISS", "INESTABLE", "ESTABLE_OK"))
    n_med = len(hechos)
    ruido = n_inest + n_est_ok
    pct = (lambda k: f"{k / n_med:.0%}" if n_med else "n/a")
    corpus_muto = doc["corpus_inicio"].get("count") != doc["corpus_fin"].get("count")
    L = [
        "# s324d · ¿Cuánto de los «no OK» del FULL es RUIDO de N=1? (estabilidad de SÍNTESIS)",
        "",
        f"> JSON `evals/s324d_estabilidad_sintesis_v1.json` · "
        f"`scripts/s324d_estabilidad_sintesis.py` · git `{s['git_sha'][:8]}` · corpus "
        f"{doc['corpus_inicio'].get('count')}→{doc['corpus_fin'].get('count')} filas "
        f"({'MUTÓ durante la medición' if corpus_muto else 'sin cambio'}) · juez `judge_conveyed21` GPT-5.5 K=5, "
        f"`THRESH_FIRM={FA.THRESH_FIRM}` (vara INTACTA) · `{s['LLM_MODEL']}`/`{s['GENERATOR_PROMPT_VARIANT']}`. "
        f"**Solo medición; ningún lever ni cambio de pipeline.**",
        "",
        "**Pregunta.** El FULL etiqueta cada hecho con UNA generación. s324c mostró en 4 hechos que con la vista "
        "IDÉNTICA la respuesta varía. ¿Cuánto de los «no OK» es ruido de muestreo?",
        "",
        "**Método.** Universo = hechos del FULL 16-ago con `conveyed_yes < THRESH_FIRM` "
        f"({cob['n_no_ok_en_el_FULL']}: 12 `synthesis-miss` + 3 rescatados por el dual-judge). Por GOLD: un turno "
        "real por el seam; la vista que entra a `generate_answer` se CONGELA y se generan **N=5** respuestas sobre "
        "ella (rep0 en el seam; reps 1-4 = `gen_answer_only`, DEC-168). Cada respuesta se juzga para CADA "
        "hecho-diana del gold — igual que el FULL. **ESTABLE_MISS**=0/5 firmes · **INESTABLE**=0<firmes<5 · "
        "**ESTABLE_OK**=5/5.",
        "",
        "| hecho | valor | FULL `conv`·`stability`·submotivo | vista: filas(pref)·`hash_view` | votos | firmes | "
        "clase | $gold |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in sorted(hechos, key=lambda x: (prioridad(x), x["fact_prefix"])):
        g = by_qid[f["qid"]]
        c = g["vista_congelada"]["composition"]
        # OJO: nada de `|` dentro de una celda (parte la tabla). Separador interno = `·`.
        j2 = f"·dual{f['conveyed_yes_judge2']}" if f.get("conveyed_yes_judge2") is not None else ""
        L.append(
            f"| `{f['fact_prefix']}` | {f['valor'][:18]} | {f['conveyed_yes']}{j2}·"
            f"{f.get('stability_full') or ('rescatado' if f['clase_full'] == 'OK' else '—')}·"
            f"{f.get('submotivo') or '—'} | {c['n_rows']}({c['n_prefix']})·`{c['hash_view'][:8]}` | "
            f"{','.join(str(y) for y in f['yes'])} | **{f['firmes']}/{f['n']}** | **{f['clase_s324d']}** | "
            f"{g['coste']['usd_total']:.2f} |"
        )
    # cruce automático con el `stability` del propio FULL (K_STAB=3 reps desde la composición
    # servida, adjudicadas primario+dual): ¿coincide su etiqueta con lo medido aquí con N=5?
    sm = [f for f in hechos if f["clase_full"] == "synthesis-miss"]
    conc = sum(1 for f in sm if (f.get("stability_full") == "stable-miss") == (f["clase_s324d"] == "ESTABLE_MISS"))
    flip_est = [f["fact_prefix"] for f in sm
                if f.get("stability_full") == "stable-miss" and f["clase_s324d"] != "ESTABLE_MISS"]
    L += [
        "",
        "## Recuento por clase",
        "",
        f"- **ESTABLE_MISS (defecto real): {n_est_miss}/{n_med}**"
        + (" — " + ", ".join(f"`{x}`" for x in rec["ESTABLE_MISS"]) if rec.get("ESTABLE_MISS") else "") + ".",
        f"- **INESTABLE (el FULL etiqueta al azar): {n_inest}/{n_med}**"
        + (" — " + ", ".join(f"`{x}`" for x in rec["INESTABLE"]) if rec.get("INESTABLE") else "") + ".",
        f"- **ESTABLE_OK (no-OK por mala suerte): {n_est_ok}/{n_med}**"
        + (" — " + ", ".join(f"`{x}`" for x in rec["ESTABLE_OK"]) if rec.get("ESTABLE_OK") else "") + ".",
        "",
        "## La cifra",
        "",
        f"**De los {n_med} hechos no-OK medidos (de {cob['n_no_ok_en_el_FULL']} no-OK del FULL): "
        f"{n_est_miss} son DEFECTO ESTABLE ({pct(n_est_miss)}) y {ruido} son RUIDO DE MUESTREO "
        f"({pct(ruido)}).**",
        "",
        f"- Cruce con el `stability` del propio FULL (3 reps, primario+dual): coincide en {conc}/{len(sm)} de los "
        f"`synthesis-miss`" + (f"; declarados `stable-miss` allí y NO estables aquí: "
                               + ", ".join(f"`{x}`" for x in flip_est) + "." if flip_est else "."),
    ]
    for o in doc.get("observaciones") or []:
        L.append(f"- {o}")
    L += [
        "",
        "## Alcance",
        "",
        f"- Medidos **{cob['n_medidos']}/{cob['n_no_ok_en_el_FULL']}**."
        + (f" SIN MEDIR: {', '.join('`' + x + '`' for x in cob['sin_medir'])}." if cob["sin_medir"] else " Cobertura total.")
        + " Fuera de alcance por diseño: las clases upstream (`retrieval-miss`, `rerank-miss`, `corpus-gap`), "
          "sin `conveyed_yes`.",
    ]
    for x in doc.get("no_pude") or []:
        L.append(f"- {x}")
    L += [
        "",
        "## Coste real (`scripts/usage_meter.py`)",
        "",
        (f"- **${tot['usd_total']:.2f}** en {doc['uso_total']['n_calls']} llamadas: "
         + " · ".join(f"`{m}` {b['calls']}× ({b['in']:,} in/{b['out']:,} out) ${b['usd']:.2f}"
                      for m, b in tot["by_model"].items() if b["usd"] is not None)
         + f". Presupuesto duro ${doc['config']['presupuesto']:.0f}; tarifas/M $3/$15 y "
           f"${PRICES_USD_PER_M['gpt-5.5']['in']:.0f}/${PRICES_USD_PER_M['gpt-5.5']['out']:.0f}; embeddings/REST no "
           f"medidos.") if doc.get("coste_medido") else "- Coste NO MEDIDO (ningún SDK quedó envuelto).",
        "",
        "## Caveats",
        "",
        "- **Asimetría de vara (declarada):** «firme» aquí = juez PRIMARIO ≥4/5, como en s324c; el FULL además "
        "rescata con el dual (Opus 4.8). Como `OK_FULL(rep) ⊇ firme_primario(rep)`, **ESTABLE_MISS es COTA SUPERIOR "
        "del defecto estable, y el ruido COTA INFERIOR**.",
        "- N=5 no prueba determinismo: con probabilidad real p=0,2 un hecho sale 0/5 el 33% de las veces. Las clases "
        "extremas son estimaciones.",
        f"- Sello PARCIAL. `hash_view` = cabecera + excerpt servido. Votos no válidos del juez: "
        f"{sum(f['juez_n_fail_total'] for f in hechos)}. La vista de HOY no es la del FULL 16-ago (hoy cambiaron "
        f"corpus y `product_model`): mide estabilidad de síntesis, no reproduce el turno del FULL.",
    ]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


# ───────────────────────── main ─────────────────────────
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="medir como MUCHO N hechos-diana (orden de prioridad)")
    ap.add_argument("--presupuesto", type=float, default=PRESUPUESTO_DEFAULT, help="tope duro en USD")
    ap.add_argument("--n", type=int, default=5, help="reps sobre la MISMA vista congelada (N=5 por diseño)")
    ap.add_argument("--facts", default="", help="lista explícita de fact_prefix (coma) en vez del universo")
    ap.add_argument("--force", action="store_true", help="re-medir golds ya presentes en el JSON")
    ap.add_argument("--md-only", action="store_true", help="solo regenerar el MD desde el JSON")
    ap.add_argument("--recost", action="store_true", help="recalcular USD desde los tokens guardados (no gasta)")
    ap.add_argument("--dry-run", action="store_true", help="listar el plan y salir (no gasta)")
    args = ap.parse_args()

    doc = load_doc()
    if args.md_only or args.recost:
        if not doc:
            raise SystemExit("no hay JSON del que regenerar")
        if args.recost:
            for g in doc["golds"]:
                g["coste"] = cost_of(g["uso"], PRICES_USD_PER_M)
            doc["precios_usd_por_M"] = PRICES_USD_PER_M
        save_doc(doc)
        write_md(doc)
        print(f"regenerado: {OUT_MD} (total ${doc['coste_total']['usd_total']})")
        return 0

    universo = universo_no_ok()
    seleccion = universo
    if args.facts:
        pedidos = {x.strip() for x in args.facts.split(",") if x.strip()}
        seleccion = [f for f in universo if f["fact_prefix"] in pedidos]
    if args.limit:
        seleccion = seleccion[: args.limit]
    grupos = agrupar_por_gold(seleccion)

    print(f"universo no-OK (conveyed_yes < {FA.THRESH_FIRM}): {len(universo)} hechos · seleccionados "
          f"{len(seleccion)} en {len(grupos)} golds · presupuesto ${args.presupuesto:.2f}", flush=True)
    for g in grupos:
        print(f"  {g['qid']}: " + ", ".join(f"{f['fact_prefix']}[{f['clase_full']}/{f['submotivo']}]"
                                            for f in g["facts"]), flush=True)
    deriva = [f for f in universo if f["deriva_vs_gold_dev"]]
    if deriva:
        print(f"  (aviso) {len(deriva)} hechos con deriva vs el gold-dev vivo: "
              + ", ".join(f"{f['fact_prefix']}{f['deriva_vs_gold_dev']}" for f in deriva), flush=True)
    if args.dry_run:
        return 0

    METER.install()
    if not METER.disponible():
        print("(aviso) el medidor de uso no envolvió ningún SDK: el coste se declarará NO MEDIDO", flush=True)

    if not doc:
        doc = {
            "sonda": "s324d_estabilidad_sintesis_v1",
            "pregunta": ("de los hechos no-OK del FULL (conveyed_yes < THRESH_FIRM), ¿qué fracción es RUIDO de "
                         "una sola muestra (N=1) y qué fracción es defecto estable?"),
            "reutiliza": [
                "scripts/s324c_replay_congelado.py (captura de la vista congelada + N gens sobre ella)",
                "scripts/s289_order_fixes_directed.py (gen_answer_only N veces sobre la MISMA composición, DEC-168 G-3)",
                "scripts/s293_reachability_probe.py (seam+adapters+juez canónico; recibo PARCIAL)",
                "scripts/usage_meter.py (coste real por llamada)",
            ],
            "sello_freeze_PARCIAL": sello_freeze(),
            "corpus_inicio": FA.corpus_fingerprint(),
            "corpus_fin": {},
            "fuente_universo": str(FULL.relative_to(ROOT)),
            "universo": universo,
            "config": {"n": args.n, "presupuesto": args.presupuesto,
                       "vara": {"juez": FA.JUDGE_MODEL, "K": FA.K, "THRESH_FIRM": FA.THRESH_FIRM,
                                "dual_judge": False,
                                "nota": "asimetría declarada: el FULL exige consenso primario+dual para no-OK"}},
            "precios_usd_por_M": PRICES_USD_PER_M,
            "golds": [],
            "no_pude": [],
            "observaciones": [],
        }
    else:
        doc.setdefault("sello_freeze_PARCIAL_reanudacion", []).append(sello_freeze())
        doc["universo"] = universo
    print(f"sello: git {doc['sello_freeze_PARCIAL']['git_sha'][:8]} · corpus inicio {doc['corpus_inicio']}", flush=True)

    gasto_previo = (cost_of(doc.get("uso_total") or {"n_calls": 0, "by_model_phase": []},
                            PRICES_USD_PER_M)["usd_total"] if doc["golds"] else 0.0)

    def estimar(n_facts: int) -> float:
        """Coste esperado del siguiente gold: parte FIJA (turno + N gens, fases turn/generate) +
        parte por HECHO (juez), ambas medidas de los golds ya hechos; +15% de margen. Sin datos
        aún, la estimación conservadora del encabezado."""
        if not doc["golds"]:
            return COSTE_ESTIMADO_BASE + COSTE_ESTIMADO_POR_HECHO * n_facts
        fijo = juez = 0.0
        n_h = 0
        for g in doc["golds"]:
            c = cost_of({"n_calls": 0, "by_model_phase": [a for a in g["uso"]["by_model_phase"]
                                                          if a["phase"] != "judge"]}, PRICES_USD_PER_M)
            j = cost_of({"n_calls": 0, "by_model_phase": [a for a in g["uso"]["by_model_phase"]
                                                          if a["phase"] == "judge"]}, PRICES_USD_PER_M)
            fijo += c["usd_total"]
            juez += j["usd_total"]
            n_h += len(g["hechos"])
        return 1.15 * (fijo / len(doc["golds"]) + (juez / max(1, n_h)) * n_facts)

    for grupo in grupos:
        if any(g["qid"] == grupo["qid"] for g in doc["golds"]) and not args.force:
            print(f"(skip) {grupo['qid']} ya medido", flush=True)
            continue
        gasto = gasto_previo + cost_of(METER.summary(0), PRICES_USD_PER_M)["usd_total"]
        est = estimar(len(grupo["facts"]))
        if gasto + est > args.presupuesto:
            msg = (f"PRESUPUESTO: parado antes de `{grupo['qid']}` — gasto ${gasto:.2f} + estimado ${est:.2f} > "
                   f"${args.presupuesto:.2f}")
            print(msg, flush=True)
            doc["no_pude"].append(msg)
            break
        try:
            entry = medir_gold(grupo, args.n)
        except Exception as exc:                                        # noqa: BLE001 — recibo PARCIAL
            msg = f"{grupo['qid']}: FALLÓ {type(exc).__name__}: {str(exc)[:300]}"
            print(f"  !! {msg}", flush=True)
            doc["no_pude"].append(msg)
            doc["corpus_fin"] = FA.corpus_fingerprint()
            doc["estado"] = "PARCIAL"
            save_doc(doc)
            continue
        doc["golds"] = [g for g in doc["golds"] if g["qid"] != grupo["qid"]] + [entry]
        doc["corpus_fin"] = FA.corpus_fingerprint()
        save_doc(doc)
        acum = gasto_previo + cost_of(METER.summary(0), PRICES_USD_PER_M)["usd_total"]
        print(f"  guardado ({OUT_JSON.stat().st_size/1e6:.2f} MB) · acumulado ${acum:.2f} / ${args.presupuesto:.2f}",
              flush=True)

    doc["corpus_fin"] = FA.corpus_fingerprint()
    save_doc(doc)                       # calcula doc["cobertura"] con lo realmente medido
    doc["estado"] = "PARCIAL" if (doc["cobertura"]["sin_medir"] or doc["no_pude"]) else "COMPLETO"
    save_doc(doc)
    write_md(doc)
    print(f"\nTOTAL: ${doc['coste_total']['usd_total']} · {doc['uso_total']['n_calls']} llamadas · "
          f"recuento { {k: len(v) for k, v in doc['recuento'].items()} } · estado {doc['estado']}")
    print(f"-> {OUT_JSON}\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
