#!/usr/bin/env python3
"""s324c_replay_congelado.py — REPLAY sobre COMPOSICIÓN CONGELADA de los «flips» de etapa 3.

Pregunta del dúo r33 (Sol, s324b): los 4 hechos que la sonda de alcanzabilidad dio por
ALCANZABLE con la BASE ya en 5/5 en varias reps (`cat001#3`, `cat008#3`, `cat016#1`,
`hp005#3`) tenían `conveyed_yes 0` en el FULL 16-ago. Antes de etiquetarlos «inestabilidad
de síntesis» hay que separar dos mecanismos que la sonda NO distingue (DEC-173: base y
oráculo son generaciones independientes en `serve`, y el recibo no guarda la composición):

  · «varía con la MISMA vista»  → SÍNTESIS (la generación no es determinista dada la vista)
  · «varía porque cambia LO SERVIDO» → SERVING (DEC-097: composición servida estocástica ×
     generación estable dada la composición; DEC-096b rerank no determinista a temp=0)

Diseño (reutiliza el mecanismo de «captura congelada» de s289 — DEC-168 G-1/G-3:
composición congelada + `gen_answer_only` N veces sobre la MISMA composición):

  brazo CONGELADO  UN turno real por el seam (`execute_rag_turn`, mismos adapters que el
                   brazo base de `s293_reachability_probe.run_turn`: `_capture_retrieve`,
                   `_eval_strict_rerank`, shadow, generate) → la vista que recibe el
                   generador (prefijo + appends de coverage, TAL CUAL entra en
                   `generate_answer`) se CONGELA (deepcopy + ids + orden + hashes) y la
                   rep0 se genera DENTRO del seam; las reps 1..N-1 se generan FUERA con
                   `generate_answer(question, deepcopy(vista))` — el mismo callee que
                   `gen_answer_only` de s289 (se llama directo para conservar usage/stop).
  brazo FRESCO     N turnos independientes por el seam (retrieval+rerank+coverage+gen
                   nuevos cada vez) = exactamente el brazo base de la sonda.
  juez             `judge_conveyed21` (GPT-5.5, K=5) y `THRESH_FIRM=4` del instrumento —
                   la MISMA vara, sin tocar.

Clasificación por hecho (pre-declarada en el encargo):
  (a) SINTESIS_INESTABLE  con la MISMA vista los firmes varían: 0 < firmes < N
  (b) ESTABLE_OK          N/N firmes con la misma vista y N/N también en fresco
  (c) SERVING             congelado estable (0/N o N/N) pero el brazo fresco (vista variable)
                          da OTRO resultado
  ESTABLE_MISS            0/N congelado y 0/N fresco (no está en la lista: se declara)
  Además se dice si las vistas frescas fueron REALMENTE distintas de la congelada
  (hash de ids+orden y hash de la vista servida): un «SERVING» con vistas idénticas no cuadra
  y se marca NO_CUADRA.

NO diseña levers. Solo mide y registra.

Uso:
  python scripts/s324c_replay_congelado.py [--facts cat001#3,cat008#3,cat016#1,hp005#3]
        [--n-frozen 5] [--n-fresh 3] [--force] [--md-only]
Salidas (ÚNICAS): evals/s324c_replay_congelado_flips_v1.json + .md
El JSON se escribe tras CADA hecho (resumible; lección §5.3 de s321: un SystemExit tardío
tiraba las reps anteriores de la sonda). Logs → stdout (redirigir al scratchpad).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

# Importar el instrumento fija DEMO_FLAGS en import-time (freeze-contract) ANTES del
# pipeline y carga el .env (misma secuencia que la sonda s293).
import scripts.factlevel_assessment as FA  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.generator import admitted_evidence_rows  # noqa: E402
from src.rag.post_rerank_coverage import coverage_context_content  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402

FULL_16AGO = ROOT / "evals" / "s100_factlevel_full_v3_20260816.yaml"
RECEIPT_PROBE = ROOT / "evals" / "s100_factlevel_full_v32_full_20260801.yaml"  # el que lee la sonda
OUT_JSON = ROOT / "evals" / "s324c_replay_congelado_flips_v1.json"
OUT_MD = ROOT / "evals" / "s324c_replay_congelado_flips_v1.md"
FACTS_DEFAULT = ["cat001#3", "cat008#3", "cat016#1", "hp005#3"]

# Precios USD por 1M tokens. Sonnet 4.6 = tarifa first-party Anthropic (skill claude-api,
# caché 2026-06-24). GPT-5.5 = tabla Standard de developers.openai.com/api/docs/pricing
# (leída 16-ago-2026: <272K contexto, $5.00 in / $30.00 out; cached in $0.50). Los TOKENS
# se miden en cada llamada; el USD se recalcula con `--recost` si cambia una tarifa.
PRICES_USD_PER_M = {
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0, "src": "anthropic first-party (skill claude-api)"},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "src": "anthropic first-party (skill claude-api)"},
    "claude-opus-4-8": {"in": 5.0, "out": 25.0, "src": "anthropic first-party (skill claude-api)"},
    "gpt-5.5": {"in": 5.0, "out": 30.0, "src": "developers.openai.com/api/docs/pricing (Standard, <272K) leído 16-ago-2026"},
}


# ───────────────────────── medidor de uso (observación pura, no toca la vara) ─────────────────────────
class UsageMeter:
    """Envuelve `Messages.create` (anthropic) y `Completions.create` (openai) SOLO para leer
    `usage` de cada respuesta. No altera argumentos ni respuestas. Fase etiquetada por el
    hilo principal (turn = retrieval+rerank+coverage · generate · judge)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.phase = "init"
        self.rows: list[dict] = []
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        import anthropic.resources.messages as am
        import openai.resources.chat.completions as oc

        meter = self
        orig_a = am.Messages.create

        def a_create(this, *args, **kwargs):
            t0 = time.time()
            resp = orig_a(this, *args, **kwargs)
            u = getattr(resp, "usage", None)
            meter._add("anthropic", kwargs.get("model"),
                       getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0,
                       (getattr(u, "cache_read_input_tokens", 0) or 0),
                       (getattr(u, "cache_creation_input_tokens", 0) or 0), time.time() - t0)
            return resp

        orig_o = oc.Completions.create

        def o_create(this, *args, **kwargs):
            t0 = time.time()
            resp = orig_o(this, *args, **kwargs)
            u = getattr(resp, "usage", None)
            meter._add("openai", kwargs.get("model"),
                       getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0,
                       0, 0, time.time() - t0)
            return resp

        am.Messages.create = a_create
        oc.Completions.create = o_create
        self._installed = True

    def _add(self, provider, model, tin, tout, cache_read, cache_write, secs) -> None:
        with self.lock:
            self.rows.append({"provider": provider, "model": model, "phase": self.phase,
                              "in": int(tin), "out": int(tout), "cache_read": int(cache_read),
                              "cache_write": int(cache_write), "secs": round(secs, 2)})

    def snapshot(self) -> int:
        with self.lock:
            return len(self.rows)

    def summary(self, since: int = 0) -> dict:
        with self.lock:
            rows = self.rows[since:]
        agg: dict[str, dict] = {}
        for r in rows:
            key = f"{r['model']}|{r['phase']}"
            a = agg.setdefault(key, {"model": r["model"], "phase": r["phase"], "calls": 0,
                                     "in": 0, "out": 0, "cache_read": 0, "cache_write": 0})
            a["calls"] += 1
            a["in"] += r["in"]
            a["out"] += r["out"]
            a["cache_read"] += r["cache_read"]
            a["cache_write"] += r["cache_write"]
        return {"n_calls": len(rows), "by_model_phase": sorted(agg.values(), key=lambda x: (x["model"] or "", x["phase"]))}


METER = UsageMeter()


def cost_of(summary: dict) -> dict:
    total = 0.0
    assumed = False
    by_model: dict[str, dict] = {}
    for a in summary["by_model_phase"]:
        p = PRICES_USD_PER_M.get(a["model"] or "")
        if p is None:
            by_model.setdefault(a["model"], {"usd": None, "in": 0, "out": 0, "calls": 0, "price": "DESCONOCIDO"})
            b = by_model[a["model"]]
            b["in"] += a["in"]; b["out"] += a["out"]; b["calls"] += a["calls"]
            continue
        usd = a["in"] / 1e6 * p["in"] + a["out"] / 1e6 * p["out"]
        b = by_model.setdefault(a["model"], {"usd": 0.0, "in": 0, "out": 0, "calls": 0, "price": p["src"]})
        b["usd"] += usd; b["in"] += a["in"]; b["out"] += a["out"]; b["calls"] += a["calls"]
        total += usd
        if "SUPUESTO" in p["src"]:
            assumed = True
    for b in by_model.values():
        if b["usd"] is not None:
            b["usd"] = round(b["usd"], 4)
    return {"usd_total": round(total, 4), "usd_incluye_precio_supuesto": assumed, "by_model": by_model}


# ───────────────────────── utilidades ─────────────────────────
def _sha(text: str, n: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sello_freeze() -> dict:
    """Sello PARCIAL (mismo espíritu que la sonda) + huella del corpus AL INICIO y AL FINAL
    (`FA.corpus_fingerprint`), porque el hub muta la DB en la misma rama durante la
    medición (s321 §7)."""
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
                 "funcion": "scripts.factlevel_assessment.judge_conveyed21 (primario, sin dual)"},
        "INSTRUMENT_VERSION": FA.INSTRUMENT_VERSION,
        "DEMO_FLAGS": dict(FA.DEMO_FLAGS),
        "sello_no_cubre": ["config física del índice", "versión de embeddings", "seeds",
                           "closure del código", "mutaciones in-place del corpus (solo count+max_created_at)"],
    }


def load_targets(fact_keys: list[str]) -> list[dict]:
    """Pregunta/valor/texto del FULL 16-ago (el que motiva el encargo) + cruce con el recibo
    que lee la sonda (1-ago) — se exige IGUALDAD (defecto §5.1 de s321 verificado aquí)."""
    full16 = yaml.safe_load(open(FULL_16AGO, encoding="utf-8"))
    full01 = yaml.safe_load(open(RECEIPT_PROBE, encoding="utf-8"))
    by16 = {g["qid"]: g for g in full16["per_gold"]}
    by01 = {g["qid"]: g for g in full01["per_gold"]}
    out = []
    for fk in fact_keys:
        qid = fk.split("#")[0]
        g16, g01 = by16[qid], by01[qid]
        f16 = [f for f in g16["facts"] if f["key"].startswith(fk)][0]
        f01 = [f for f in g01["facts"] if f["key"].startswith(fk)][0]
        assert (g16["question"], f16["valor"], f16.get("texto")) == (g01["question"], f01["valor"], f01.get("texto")), \
            f"{fk}: pregunta/valor/texto difieren entre FULL 16-ago y el recibo de la sonda (1-ago)"
        out.append({
            "qid": qid, "fact_prefix": fk, "fact_key": f16["key"], "valor": f16["valor"],
            "texto": (f16.get("texto") or "").strip(), "question": g16["question"],
            "full_16ago": {
                "clase": f16.get("clase"), "conveyed_yes": f16.get("conveyed_yes"),
                "stability": f16.get("stability"), "in_topk": f16.get("in_topk"),
                "submotivo": f16.get("submotivo"),
                "served_ids8": [str(s)[:8] for s in (g16.get("served_ids") or [])],
                "n_pool": len(g16.get("pool_ids") or []),
                "git_commit": full16["manifest"].get("git_commit"),
                "corpus": full16["manifest"].get("corpus"),
            },
            "full_01ago": {"clase": f01.get("clase"), "conveyed_yes": f01.get("conveyed_yes"),
                           "stability": f01.get("stability"),
                           "served_ids8": [str(s)[:8] for s in (g01.get("served_ids") or [])]},
        })
    return out


def sonda_s324b(qid: str, fact_prefix: str) -> dict | None:
    path = ROOT / "evals" / f"s293_reachability_{qid}_{fact_prefix.replace('#', '_')}.json"
    if not path.exists():
        return None
    d = json.load(open(path, encoding="utf-8"))
    return {"mode": d.get("mode"), "base_yes": [r["base_yes"] for r in d["reps"]],
            "oracle_yes": [r["oracle_yes"] for r in d["reps"]],
            "veredicto": (d.get("veredicto") or {}).get("veredicto"),
            "git_sha": (d.get("sello_freeze_PARCIAL") or {}).get("git_sha")}


def composition_record(view: list[dict], n_prefix: int | None) -> dict:
    """ids + orden + hashes de la vista TAL COMO la ve el generador. `served_sha` = hash de
    `coverage_context_content(chunk)` (los excerpts que entran al prompt); `hdr_sha` = hash de
    los campos que el generador imprime en la cabecera del fragmento. `hash_view` = hash del
    conjunto ordenado (proxy del user_message, sin el system prompt). `hash_ids` = solo
    identidad+orden."""
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
    """Espejo del brazo base de `s293_reachability_probe.run_turn(question, [])`: mismo seam,
    mismos adapters, generación DENTRO del seam. Además congela (deepcopy) la vista que
    recibe el generador y devuelve usage/stop_reason. Retry 1× si coverage fail-open
    (`status=error`, la regla canónica de `FA.run_pipeline`; la sonda no reintentaba)."""
    captured: dict = {}

    def generate(query, chunks, available_models=None):
        rows = [dict(c) for c in chunks]           # como la sonda
        captured["view"] = copy.deepcopy(rows)     # vista EXACTA que entra a generate_answer
        captured["available_models"] = available_models
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
    for attempt in range(2):
        METER.phase = "turn"
        t0 = time.time()
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
    gen = captured.get("gen") or {}
    view = captured.get("view") or []
    n_prefix = pipeline.get("reranked_rows")
    return {
        "answer": gen.get("answer", ""),
        "gen_meta": {"stop_reason": gen.get("stop_reason"), "input_tokens": gen.get("input_tokens"),
                     "output_tokens": gen.get("output_tokens"), "secs": captured.get("gen_secs")},
        "view": view,
        "composition": composition_record(view, n_prefix),
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


def classify(frozen_firms: list[bool], fresh_firms: list[bool], fresh_same_view: list[bool],
             fresh_same_ids: list[bool]) -> tuple[str, str]:
    n_fz, k_fz = len(frozen_firms), sum(frozen_firms)
    n_fr, k_fr = len(fresh_firms), sum(fresh_firms)
    views_vary = any(not s for s in fresh_same_view)
    ids_vary = any(not s for s in fresh_same_ids)
    if 0 < k_fz < n_fz:
        return "SINTESIS_INESTABLE", (f"con la MISMA vista congelada firmes {k_fz}/{n_fz} (0<k<N): la generación "
                                      f"varía sin que cambie lo servido; fresco {k_fr}/{n_fr}")
    frozen_all = (k_fz == n_fz)
    if frozen_all and k_fr == n_fr:
        return "ESTABLE_OK", f"N/N firme con vista congelada ({k_fz}/{n_fz}) y N/N fresco ({k_fr}/{n_fr})"
    if (not frozen_all) and k_fr == 0:
        return "ESTABLE_MISS", (f"0/N con vista congelada y 0/N fresco — estable en miss (clase no listada en el "
                                f"encargo, se declara)")
    # congelado estable pero fresco cambia
    if views_vary:
        return "SERVING", (f"congelado estable ({k_fz}/{n_fz}) pero fresco {k_fr}/{n_fr} y las vistas frescas "
                           f"difieren de la congelada (hash_view distinto en {sum(not s for s in fresh_same_view)}/{n_fr}; "
                           f"ids/orden distintos en {sum(not s for s in fresh_same_ids)}/{n_fr}): el cambio va con lo servido")
    return "NO_CUADRA", (f"congelado estable ({k_fz}/{n_fz}) pero fresco {k_fr}/{n_fr} CON vistas frescas idénticas a la "
                         f"congelada (hash_view igual): no es serving; con más N sería síntesis-inestable")


def diff_ids(a: list[str], b: list[str]) -> dict:
    sa, sb = set(a), set(b)
    return {"gained": [x for x in b if x not in sa], "lost": [x for x in a if x not in sb],
            "same_set": sa == sb, "same_order": a == b}


def measure_fact(t: dict, n_frozen: int, n_fresh: int) -> dict:
    qid, fk, valor, texto, question = t["qid"], t["fact_prefix"], t["valor"], t["texto"], t["question"]
    since = METER.snapshot()
    started = now_iso()
    print(f"\n=== {fk} · «{valor}» · N_congelado={n_frozen} N_fresco={n_fresh} · {started}", flush=True)

    # ── brazo CONGELADO: captura UNA vez + rep0 dentro del seam ──
    cap = run_turn_capturing(question)
    frozen_view = cap["view"]
    comp = cap["composition"]
    print(f"  captura: {comp['n_rows']} filas (prefijo {comp['n_prefix']}, admitidas {comp['n_admitidas']}) "
          f"hash_ids={comp['hash_ids']} hash_view={comp['hash_view']} coverage={cap['coverage_status']} "
          f"retry={cap['coverage_retry']} ({cap['turn_secs']}s)", flush=True)
    frozen_gens = [{"rep": 0, "en_seam": True, "answer": cap["answer"], "gen_meta": cap["gen_meta"]}]
    for i in range(1, n_frozen):
        g = gen_from_view(question, frozen_view)
        frozen_gens.append({"rep": i, "en_seam": False, **g})
        print(f"  congelado rep{i}: gen {g['gen_meta']['secs']}s stop={g['gen_meta']['stop_reason']} "
              f"out={g['gen_meta']['output_tokens']}", flush=True)
    for g in frozen_gens:
        g["judge"] = judge(valor, texto, g["answer"])
        print(f"  congelado rep{g['rep']}: juez {g['judge']['yes']}/5 (fail {g['judge']['n_fail']}) "
              f"→ {'FIRME' if g['judge']['firm'] else 'no'}", flush=True)
    frozen_firms = [g["judge"]["firm"] for g in frozen_gens]

    # ── brazo FRESCO: N turnos independientes (= brazo base de la sonda) ──
    fresh_turns = []
    for i in range(n_fresh):
        r = run_turn_capturing(question)
        c = r["composition"]
        entry = {
            "rep": i, "answer": r["answer"], "gen_meta": r["gen_meta"], "composition": c,
            "coverage_status": r["coverage_status"], "coverage_retry": r["coverage_retry"],
            "coverage_appended_ids8": r["coverage_appended_ids8"], "pool_ids8": r["pool_ids8"],
            "same_view_as_frozen": c["hash_view"] == comp["hash_view"],
            "same_ids_as_frozen": c["hash_ids"] == comp["hash_ids"],
            "diff_vs_frozen": diff_ids(comp["ids8"], c["ids8"]),
            "turn_secs": r["turn_secs"], "stage_timings": r["stage_timings"],
        }
        entry["judge"] = judge(valor, texto, r["answer"])
        fresh_turns.append(entry)
        print(f"  fresco rep{i}: {c['n_rows']} filas hash_ids={c['hash_ids']} hash_view={c['hash_view']} "
              f"same_ids={entry['same_ids_as_frozen']} same_view={entry['same_view_as_frozen']} "
              f"juez {entry['judge']['yes']}/5 → {'FIRME' if entry['judge']['firm'] else 'no'} "
              f"({r['turn_secs']}s)", flush=True)
    fresh_firms = [e["judge"]["firm"] for e in fresh_turns]

    clase, motivo = classify(frozen_firms, fresh_firms,
                             [e["same_view_as_frozen"] for e in fresh_turns],
                             [e["same_ids_as_frozen"] for e in fresh_turns])
    usage = METER.summary(since)
    cost = cost_of(usage)
    finished = now_iso()
    print(f"  ⇒ {fk}: congelado {sum(frozen_firms)}/{len(frozen_firms)} · fresco {sum(fresh_firms)}/{len(fresh_firms)} "
          f"· clase {clase} · ${cost['usd_total']} ({usage['n_calls']} llamadas) · {finished}", flush=True)

    # la vista congelada COMPLETA (filas tal cual entraron al generador) se guarda para replays futuros
    return {
        "qid": qid, "fact_prefix": fk, "fact_key": t["fact_key"], "valor": valor, "texto": texto,
        "question": question,
        "contexto": {"full_16ago": t["full_16ago"], "full_01ago": t["full_01ago"],
                     "sonda_s324b": sonda_s324b(qid, fk)},
        "started_at": started, "finished_at": finished,
        "congelado": {
            "captura": {"composition": comp, "coverage_status": cap["coverage_status"],
                        "coverage_retry": cap["coverage_retry"],
                        "coverage_appended_ids8": cap["coverage_appended_ids8"],
                        "pool_ids8": cap["pool_ids8"], "retrieval_health": cap["retrieval_health"],
                        "stage_timings": cap["stage_timings"], "turn_secs": cap["turn_secs"],
                        "vista_congelada_filas": frozen_view},
            "n": len(frozen_gens), "firmes": sum(frozen_firms),
            "yes": [g["judge"]["yes"] for g in frozen_gens],
            "gens": frozen_gens,
        },
        "fresco": {"n": len(fresh_turns), "firmes": sum(fresh_firms),
                   "yes": [e["judge"]["yes"] for e in fresh_turns],
                   "n_same_view_as_frozen": sum(e["same_view_as_frozen"] for e in fresh_turns),
                   "n_same_ids_as_frozen": sum(e["same_ids_as_frozen"] for e in fresh_turns),
                   "turns": fresh_turns},
        "clase": clase, "clase_motivo": motivo,
        "uso": usage, "coste": cost,
    }


# ───────────────────────── informe MD (≤600 palabras) ─────────────────────────
def write_md(doc: dict) -> None:
    facts = doc["hechos"]
    tot = doc["coste_total"]
    s = doc["sello_freeze_PARCIAL"]
    notas = doc.get("notas_por_hecho") or {}
    NL = chr(10)
    lines = [
        "# s324c · Replay sobre COMPOSICIÓN CONGELADA de los 4 «flips» de etapa 3 (encargo dúo r33)",
        "",
        f"> JSON `evals/s324c_replay_congelado_flips_v1.json` (respuestas, juicios, vistas congeladas) · "
        f"`scripts/s324c_replay_congelado.py` · git `{s['git_sha'][:8]}` · corpus {doc['corpus_inicio'].get('count')} filas "
        f"(sin cambio) · juez `judge_conveyed21` GPT-5.5 K=5, `THRESH_FIRM=4` (vara intacta) · "
        f"`{s['LLM_MODEL']}`/`{s['GENERATOR_PROMPT_VARIANT']}`. **Solo medición; ningún lever.**",
        "",
        "**Método.** Por hecho: (1) un turno real por el seam (adapters del brazo base de la sonda s293); la vista que "
        "recibe `generate_answer` (prefijo + coverage) se CONGELA (ids, orden, hashes, filas) y se generan **N=5** "
        "respuestas sobre ella (rep0 en el seam; reps 1-4 = `gen_answer_only` de s289/DEC-168); (2) **N=3** turnos frescos "
        "independientes (= brazo base de la sonda). Misma vara. Clases pre-declaradas: SINTESIS_INESTABLE (0<firmes<N, misma "
        "vista) · SERVING (congelado estable, fresco cambia con vistas distintas) · ESTABLE_OK · ESTABLE_MISS · NO_CUADRA.",
        "",
        "| hecho (`valor`) | FULL 16-ago / sonda base | vista congelada: filas (prefijo) · `hash_view` | firmes/N congelado (votos) | firmes/N fresco (votos) | vistas ≠ | clase | coste |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in facts:
        c = f["congelado"]["captura"]["composition"]
        fr = f["fresco"]
        sb = (f["contexto"].get("sonda_s324b") or {})
        f16 = f["contexto"]["full_16ago"]
        lines.append(
            f"| `{f['fact_prefix']}` (`{f['valor']}`) | conveyed {f16.get('conveyed_yes')} `{f16.get('stability')}` / base {sb.get('base_yes')} | "
            f"{c['n_rows']} ({c['n_prefix']}) · `{c['hash_view']}` | **{f['congelado']['firmes']}/{f['congelado']['n']}** {f['congelado']['yes']} | "
            f"**{fr['firmes']}/{fr['n']}** {fr['yes']} | {fr['n'] - fr['n_same_view_as_frozen']}/{fr['n']} | **{f['clase']}** | ${f['coste']['usd_total']:.2f} |"
        )
    lines += ["", "## Lectura por hecho (qué falta en las reps no firmes)", ""]
    for f in facts:
        lines.append(f"- **`{f['fact_prefix']}`**: {notas.get(f['fact_prefix'], '')}")
    lines += ["", "## Recuento y lectura transversal", ""]
    for k, v in doc.get("recuento", {}).items():
        lines.append(f"- **{k}: {len(v)}/{len(facts)}** — {', '.join(f'`{x}`' for x in v)}.")
    for o in doc.get("observaciones_transversales") or []:
        lines.append(f"- {o}")
    lines += [
        "",
        "## Coste real (medido por llamada)",
        "",
        f"- **${tot['usd_total']:.2f}** en {doc['uso_total']['n_calls']} llamadas: "
        + " · ".join(f"`{m}` {b['calls']}× ({b['in']:,} in / {b['out']:,} out) ${b['usd']:.2f}"
                     for m, b in tot["by_model"].items() if b["usd"] is not None)
        + f". Tarifas por M: Sonnet 4.6 $3/$15; GPT-5.5 ${PRICES_USD_PER_M['gpt-5.5']['in']}/${PRICES_USD_PER_M['gpt-5.5']['out']} "
        f"(developers.openai.com/api/docs/pricing, 16-ago); embeddings/REST no medidos (centavos).",
        "",
        "## Caveats",
        "",
        "- Sello PARCIAL (el hub muta en la misma rama; corpus sin cambio). `hash_view` = cabecera + excerpt servido (proxy del "
        "user_message). rep0 congelada en el seam, reps 1-4 fuera sobre deepcopy previo. N pequeño (5/3): un 5/5 o 0/5 no "
        "prueba determinismo. Votos no válidos del juez (`n_fail`): 0.",
    ]
    if doc.get("no_pude"):
        lines += ["", "## Qué NO se pudo hacer", ""] + [f"- {x}" for x in doc["no_pude"]]
    OUT_MD.write_text(NL.join(lines) + NL, encoding="utf-8")


def load_doc() -> dict | None:
    if OUT_JSON.exists():
        try:
            return json.load(open(OUT_JSON, encoding="utf-8"))
        except Exception:
            return None
    return None


def save_doc(doc: dict) -> None:
    facts = doc["hechos"]
    # totales recalculados desde los hechos presentes (resumible)
    agg: dict[str, dict] = {}
    n_calls = 0
    for f in facts:
        n_calls += f["uso"]["n_calls"]
        for a in f["uso"]["by_model_phase"]:
            key = f"{a['model']}|{a['phase']}"
            b = agg.setdefault(key, {"model": a["model"], "phase": a["phase"], "calls": 0, "in": 0, "out": 0,
                                     "cache_read": 0, "cache_write": 0})
            for k in ("calls", "in", "out", "cache_read", "cache_write"):
                b[k] += a[k]
    doc["uso_total"] = {"n_calls": n_calls, "by_model_phase": sorted(agg.values(), key=lambda x: (x["model"] or "", x["phase"]))}
    doc["coste_total"] = cost_of(doc["uso_total"])
    doc["recuento"] = {}
    for f in facts:
        doc["recuento"].setdefault(f["clase"], []).append(f["fact_prefix"])
    tmp = OUT_JSON.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, OUT_JSON)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default=",".join(FACTS_DEFAULT))
    ap.add_argument("--n-frozen", type=int, default=5)
    ap.add_argument("--n-fresh", type=int, default=3)
    ap.add_argument("--force", action="store_true", help="re-medir hechos ya presentes en el JSON")
    ap.add_argument("--md-only", action="store_true", help="solo regenerar el MD desde el JSON")
    ap.add_argument("--recost", action="store_true",
                    help="recalcular USD por hecho y total desde los tokens guardados con PRICES_USD_PER_M actual, "
                         "guardar y regenerar el MD (no gasta)")
    args = ap.parse_args()

    doc = load_doc()
    if args.recost:
        if not doc:
            raise SystemExit("no hay JSON que re-costear")
        for f in doc["hechos"]:
            f["coste"] = cost_of(f["uso"])
        doc["precios_usd_por_M"] = PRICES_USD_PER_M
        save_doc(doc)
        write_md(doc)
        print(f"re-costeado con {PRICES_USD_PER_M['gpt-5.5']} → total ${doc['coste_total']['usd_total']}")
        return 0
    if args.md_only:
        if not doc:
            raise SystemExit("no hay JSON del que regenerar el MD")
        write_md(doc)
        print(f"MD regenerado: {OUT_MD}")
        return 0

    fact_keys = [x.strip() for x in args.facts.split(",") if x.strip()]
    targets = load_targets(fact_keys)
    METER.install()

    if not doc:
        doc = {
            "probe": "s324c_replay_congelado_v1",
            "encargo": ("dúo r33 (Sol, s324b): replay sobre composición congelada para separar «varía con la misma "
                        "vista» (síntesis) de «varía porque cambia lo servido» (serving) en los 4 flips ALCANZABLE"),
            "reutiliza": ["scripts/s289_order_fixes_directed.py (captura congelada + gen_answer_only N veces, DEC-168 G-3)",
                          "scripts/s293_reachability_probe.py run_turn (brazo base: seam + adapters + juez)"],
            "sello_freeze_PARCIAL": sello_freeze(),
            "corpus_inicio": FA.corpus_fingerprint(),
            "corpus_fin": {},
            "fuentes": {"pregunta_valor_texto": str(FULL_16AGO.relative_to(ROOT)),
                        "verificado_igual_a": str(RECEIPT_PROBE.relative_to(ROOT))},
            "config": {"n_frozen": args.n_frozen, "n_fresh": args.n_fresh},
            "precios_usd_por_M": PRICES_USD_PER_M,
            "hechos": [],
            "no_pude": [],
        }
    else:
        doc.setdefault("sello_freeze_PARCIAL_reanudacion", []).append(sello_freeze())
    done = {f["fact_prefix"] for f in doc["hechos"]}
    print(f"sello: git {doc['sello_freeze_PARCIAL']['git_sha'][:8]} · corpus inicio {doc['corpus_inicio']}", flush=True)
    for t in targets:
        if t["fact_prefix"] in done and not args.force:
            print(f"(skip) {t['fact_prefix']} ya medido", flush=True)
            continue
        try:
            entry = measure_fact(t, args.n_frozen, args.n_fresh)
        except Exception as exc:  # noqa: BLE001 — se registra y se sigue con el siguiente hecho
            print(f"  !! {t['fact_prefix']} FALLÓ: {type(exc).__name__}: {exc}", flush=True)
            doc["no_pude"].append(f"{t['fact_prefix']}: {type(exc).__name__}: {str(exc)[:300]}")
            save_doc(doc)
            continue
        doc["hechos"] = [f for f in doc["hechos"] if f["fact_prefix"] != t["fact_prefix"]] + [entry]
        doc["hechos"].sort(key=lambda f: FACTS_DEFAULT.index(f["fact_prefix"]) if f["fact_prefix"] in FACTS_DEFAULT else 99)
        doc["corpus_fin"] = FA.corpus_fingerprint()
        save_doc(doc)
        print(f"  guardado {OUT_JSON.name} ({OUT_JSON.stat().st_size/1e6:.2f} MB)", flush=True)
    doc["corpus_fin"] = FA.corpus_fingerprint()
    save_doc(doc)
    write_md(doc)
    print(f"\nTOTAL: ${doc['coste_total']['usd_total']} · {doc['uso_total']['n_calls']} llamadas · recuento {doc['recuento']}")
    print(f"-> {OUT_JSON}\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
