#!/usr/bin/env python3
"""T13 — GATE de retrieval: ¿chunks_v2 (Voyage 1024) supera a chunks (OpenAI 1536)?

Mide retrieval recall del corpus nuevo vs viejo sobre el gold humano-revisado
(`evals/gate_relevant_chunks.json`, output del merge T12). Métricas:
  - Hit@5 (primaria)   — ¿al menos un relevante en top-5?
  - Recall@5/@15       — % de relevantes recuperados
  - MRR@15             — 1/rank del primer relevante

Configuraciones evaluadas (sin HyDE — plan Sesión 26):
  - vec_old:  match_chunks (1536-d OpenAI) sobre chunks
  - vec_new:  match_chunks_v2 (1024-d Voyage) sobre chunks_v2
  - hyb_old:  RRF(vec_old, fts_old)
  - hyb_new:  RRF(vec_new, fts_new)

Verdict piso 1 (plan §B): SWAP si delta_Hit@5 (new - old) tiene IC95 bootstrap
estrictamente positivo. Piso 2 (gate_judge.py) decide calidad final.

Output:
  - evals/gate_results.json — números brutos por pregunta + agregado
  - stdout: tabla resumen + verdict piso 1

Uso: python scripts/gate.py [--limit N] [--bootstrap 5000]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Iterable

import httpx
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.embedder import embed_query as embed_openai_1536
from src.reingest.embed import embed as _voyage_embed_batch  # 1024-d Voyage adapter
from scripts.identify_relevant_chunks import (
    detect_product_models, extract_search_keywords,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("gate")

GOLD_PATH = Path("evals/gate_relevant_chunks.json")
EVAL_YAML = Path("evals/baseline_v1.yaml")
OUT_JSON = Path("evals/gate_results.json")

TOP_K_RETRIEVE = 15  # cap del retrieve para todas las configs
RRF_K = 60           # constante estándar de Reciprocal Rank Fusion
BOOTSTRAP_ITERS = 5000
RNG_SEED = 42

WORKERS = 6          # paralelismo de embedding+rpc por pregunta
HTTP_TIMEOUT = 30.0

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def embed_voyage_1024(text: str) -> list[float]:
    """Embedding query con Voyage `voyage-4-large` 1024-d, consistente con el
    pipeline de re-ingesta (`src/reingest/embed.py`)."""
    vecs = _voyage_embed_batch([text], input_type="query")
    return vecs[0]


# ---------------------------------------------------------------------------
# RPC retrieval
# ---------------------------------------------------------------------------

def rpc_match_chunks(client: httpx.Client, embedding: list[float],
                     k: int, table_version: str,
                     filter_product: str | None = None) -> list[dict]:
    """Llama a match_chunks (old) o match_chunks_v2 (new). Devuelve top-k.
    `filter_product` aplica el filtro de producto en la RPC — el retriever de
    producción siempre lo aplica cuando los modelos son detectables, sin él
    el retrieval trae chunks de manuales temáticamente similares de otros
    productos (caso hp002: ASD531/MIDT732/MIDT731 en vez de ASD535).
    """
    rpc = "match_chunks_v2" if table_version == "v2" else "match_chunks"
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.0,
        "match_count": k,
        "filter_product": filter_product,
    }
    resp = client.post(f"{SUPABASE_URL}/rest/v1/rpc/{rpc}",
                       headers=HEADERS, json=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    rows = resp.json() or []
    return rows


def rpc_search_text(client: httpx.Client, query_text: str,
                    k: int, table_version: str,
                    filter_product: str | None = None) -> list[dict]:
    """Llama a search_chunks_text (old) o search_chunks_text_v2 (new)."""
    rpc = "search_chunks_text_v2" if table_version == "v2" else "search_chunks_text"
    payload = {
        "search_query": query_text,
        "filter_product": filter_product,
        "filter_manufacturer": None,
        "filter_category": None,
        "match_limit": k,
    }
    resp = client.post(f"{SUPABASE_URL}/rest/v1/rpc/{rpc}",
                       headers=HEADERS, json=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json() or []


def rrf_fuse(lists: list[list[dict]], k_const: int = RRF_K,
             top_k: int = TOP_K_RETRIEVE) -> list[dict]:
    """Reciprocal Rank Fusion: score(d) = sum(1 / (k_const + rank_i)).
    Devuelve top_k dicts con id+source_file+page_number según RRF score."""
    scores: dict[str, float] = defaultdict(float)
    rows_by_id: dict[str, dict] = {}
    for lst in lists:
        for rank, row in enumerate(lst, start=1):
            cid = row["id"]
            scores[cid] += 1.0 / (k_const + rank)
            rows_by_id.setdefault(cid, row)
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
    return [rows_by_id[cid] for cid, _ in ranked]


# ---------------------------------------------------------------------------
# Métricas IR — match doble (sesión 26)
#
# STRICT: match por chunk_id (comparable solo dentro de la misma tabla
#         chunks_v2 — para vec_new vs hyb_new).
# LOOSE:  match por (source_file, page_number) — granularidad de página.
#         Necesario para cross-tabla porque chunks viejo (OpenAI 1536) y
#         chunks_v2 (Voyage 1024) tienen IDs distintos tras re-chunking.
#         Práctica establecida en benchmarks IR (BEIR, MTEB) cuando los
#         chunk_ids no son comparables.
# ---------------------------------------------------------------------------

def hit_at_k(retrieved: list, relevant: set, k: int) -> int:
    """1 si al menos un relevant aparece en top-k. Genérico — funciona con
    chunk_ids (str) o tuplas (source_file, page)."""
    return int(any(item in relevant for item in retrieved[:k]))


def recall_at_k(retrieved: list, relevant: set, k: int) -> float:
    """|retrieved_top_k ∩ relevant| / |relevant|."""
    if not relevant:
        return float("nan")
    hits = len({item for item in retrieved[:k] if item in relevant})
    return hits / len(relevant)


def mrr_at_k(retrieved: list, relevant: set, k: int) -> float:
    """1/rank del primer relevant en top-k; 0 si no aparece."""
    for rank, item in enumerate(retrieved[:k], start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


METRIC_FNS = {
    "hit@5":     lambda r, g: hit_at_k(r, g, 5),
    "recall@5":  lambda r, g: recall_at_k(r, g, 5),
    "recall@15": lambda r, g: recall_at_k(r, g, 15),
    "mrr@15":    lambda r, g: mrr_at_k(r, g, 15),
}


# ---------------------------------------------------------------------------
# Bootstrap CI95
# ---------------------------------------------------------------------------

def bootstrap_ci95(values: np.ndarray, iters: int = BOOTSTRAP_ITERS,
                   rng: np.random.Generator | None = None) -> tuple[float, float, float]:
    """Devuelve (mean, ci_low, ci_high) por resampling con reemplazo."""
    if rng is None:
        rng = np.random.default_rng(RNG_SEED)
    values = values[~np.isnan(values)]  # drop NaNs (preguntas sin relevantes)
    if len(values) == 0:
        return (float("nan"), float("nan"), float("nan"))
    n = len(values)
    idx = rng.integers(0, n, size=(iters, n))
    samples = values[idx]
    means = samples.mean(axis=1)
    return (values.mean(), np.percentile(means, 2.5), np.percentile(means, 97.5))


def bootstrap_delta_ci95(values_a: np.ndarray, values_b: np.ndarray,
                          iters: int = BOOTSTRAP_ITERS,
                          rng: np.random.Generator | None = None
                          ) -> tuple[float, float, float]:
    """Delta paired bootstrap (B - A): los pares por pregunta son consistentes."""
    if rng is None:
        rng = np.random.default_rng(RNG_SEED + 1)
    mask = ~(np.isnan(values_a) | np.isnan(values_b))
    a = values_a[mask]
    b = values_b[mask]
    if len(a) == 0:
        return (float("nan"), float("nan"), float("nan"))
    n = len(a)
    idx = rng.integers(0, n, size=(iters, n))
    deltas = (b[idx] - a[idx]).mean(axis=1)
    return ((b - a).mean(), np.percentile(deltas, 2.5), np.percentile(deltas, 97.5))


# ---------------------------------------------------------------------------
# Pipeline por pregunta
# ---------------------------------------------------------------------------

@dataclass
class QResult:
    qid: str
    question: str
    relevant_ids: set[str]
    retrieved: dict[str, list[str]] = field(default_factory=dict)  # config → [chunk_id]
    metrics: dict[str, dict[str, float]] = field(default_factory=dict)


def retrieve_all_configs(qid: str, question: str, models: list[str],
                          keywords: list[str], top_k: int) -> dict[str, list[dict]]:
    """Ejecuta las 4 configuraciones y devuelve top-k rows.

    Si hay 1 modelo → filter_product aplicado en RPC.
    Si hay N>1 modelos → N queries por config + unión (preserva ranking por similarity).
    Esto replica lo que hace el retriever de producción.
    """
    out: dict[str, list[dict]] = {}
    # Default si no hay modelos detectables: sin filtro
    products = [m for m in (models or [None]) if m] or [None]

    with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
        # 1. Embeddings (2 calls externos, paralelo)
        with ThreadPoolExecutor(max_workers=2) as ex:
            emb_1536_fut = ex.submit(embed_openai_1536, question)
            emb_1024_fut = ex.submit(embed_voyage_1024, question)
            emb_1536 = emb_1536_fut.result()
            emb_1024 = emb_1024_fut.result()
        # 2. Para cada producto: 4 RPCs paralelas. Luego unión cross-producto.
        search_text = " ".join(keywords) if keywords else question

        def gather(rpc_fn, *args, **kwargs):
            """Ejecuta la rpc por cada producto y devuelve la unión ordenada por
            sim/rank (preservando duplicados naturales tratados en RRF/dedup)."""
            results: list[dict] = []
            seen_ids = set()
            for prod in products:
                rows = rpc_fn(*args, filter_product=prod, **kwargs)
                for r in rows:
                    if r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    results.append(r)
            # Re-ordenar por similarity descendente (vector) o rank (fts)
            sort_key = "similarity" if "similarity" in (results[0] if results else {}) else "rank"
            results.sort(key=lambda r: -r.get(sort_key, 0.0))
            return results[:top_k]

        with ThreadPoolExecutor(max_workers=4) as ex:
            f_vec_old = ex.submit(gather, rpc_match_chunks, client, emb_1536, top_k, "old")
            f_vec_new = ex.submit(gather, rpc_match_chunks, client, emb_1024, top_k, "v2")
            f_fts_old = ex.submit(gather, rpc_search_text, client, search_text, top_k, "old")
            f_fts_new = ex.submit(gather, rpc_search_text, client, search_text, top_k, "v2")
            rows_vec_old = f_vec_old.result()
            rows_vec_new = f_vec_new.result()
            rows_fts_old = f_fts_old.result()
            rows_fts_new = f_fts_new.result()
        out["vec_old"] = rows_vec_old[:top_k]
        out["vec_new"] = rows_vec_new[:top_k]
        out["hyb_old"] = rrf_fuse([rows_vec_old, rows_fts_old], top_k=top_k)
        out["hyb_new"] = rrf_fuse([rows_vec_new, rows_fts_new], top_k=top_k)
    return out


def extract_ids(rows: list[dict]) -> list[str]:
    """Para STRICT match: lista de chunk_ids en orden de retrieval."""
    return [r["id"] for r in rows]


def extract_pages(rows: list[dict]) -> list[tuple]:
    """Para LOOSE match: lista de (source_file, page_number) en orden de retrieval."""
    return [(r.get("source_file"), r.get("page_number")) for r in rows]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compute_metrics_for_config(rows: list[dict], relevant_ids: set,
                                relevant_pages: set) -> dict:
    """Calcula todas las métricas en ambas granularidades para una config."""
    ids = extract_ids(rows)
    pages = extract_pages(rows)
    out = {}
    for m, fn in METRIC_FNS.items():
        out[f"{m}_strict"] = fn(ids, relevant_ids)
        out[f"{m}_loose"] = fn(pages, relevant_pages)
    return out


def main(limit: int | None, bootstrap_iters: int):
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    import yaml
    eval_yaml = yaml.safe_load(EVAL_YAML.read_text(encoding="utf-8"))
    questions_by_id = {q["id"]: q for q in eval_yaml["questions"]}

    # Seleccionar preguntas: hp* answer-type con relevant_chunks > 0
    selected = []
    for qid, q in gold["questions"].items():
        if not qid.startswith("hp"):
            continue
        if q.get("expected_behavior") != "answer":
            continue
        if len(q.get("relevant_chunks") or []) == 0:
            continue
        selected.append(qid)
    if limit:
        selected = selected[:limit]

    print(f"\nGATE — {len(selected)} preguntas hp* answer con relevant_chunks > 0")
    print(f"Match doble: STRICT (chunk_id, mismas tablas) + LOOSE (source_file, page)\n")

    results: list[QResult] = []
    t0 = time.time()
    for qid in selected:
        q_yaml = questions_by_id.get(qid, {})
        q_gold = gold["questions"][qid]
        question = q_gold["question"]
        relevant_chunks = q_gold["relevant_chunks"]
        relevant_ids = {c["id"] for c in relevant_chunks}
        relevant_pages = {(c.get("source_file"), c.get("page_number"))
                          for c in relevant_chunks}
        models = detect_product_models(q_yaml)
        keywords = extract_search_keywords(q_yaml)
        logger.info(f"  {qid}: {len(relevant_ids)} relevant, {len(relevant_pages)} unique pages")
        retrieved = retrieve_all_configs(qid, question, models, keywords, TOP_K_RETRIEVE)
        metrics = {}
        for cfg, rows in retrieved.items():
            metrics[cfg] = compute_metrics_for_config(rows, relevant_ids, relevant_pages)
        results.append(QResult(qid=qid, question=question,
                                relevant_ids=relevant_ids,
                                retrieved={cfg: extract_ids(rs) for cfg, rs in retrieved.items()},
                                metrics=metrics))
    elapsed = time.time() - t0
    print(f"\nRetrieval ejecutado en {elapsed:.1f}s\n")

    # Agregado por config y métrica (en ambas granularidades)
    configs = ["vec_old", "vec_new", "hyb_old", "hyb_new"]
    all_metrics = [f"{m}_{g}" for m in METRIC_FNS for g in ("strict", "loose")]
    agg: dict[str, dict[str, np.ndarray]] = {cfg: {} for cfg in configs}
    for cfg in configs:
        for m in all_metrics:
            vals = np.array([r.metrics[cfg][m] for r in results], dtype=float)
            agg[cfg][m] = vals

    # ----- Reporte LOOSE (comparación cross-tabla principal) -----
    print("=" * 88)
    print("MÉTRICAS LOOSE — match por (source_file, page_number)")
    print("Granularidad principal para comparar chunks (viejo) vs chunks_v2 (nuevo)")
    print("=" * 88)
    print(f"{'config':<10} | {'hit@5':>16} | {'recall@5':>16} | {'recall@15':>16} | {'mrr@15':>16}")
    print("-" * 88)
    for cfg in configs:
        cells = []
        for m in METRIC_FNS:
            mean_, lo, hi = bootstrap_ci95(agg[cfg][f"{m}_loose"], bootstrap_iters)
            cells.append(f"{mean_:.3f}[{lo:.2f},{hi:.2f}]")
        print(f"{cfg:<10} | " + " | ".join(f"{c:>16}" for c in cells))

    # ----- Reporte STRICT (solo informativo dentro chunks_v2) -----
    print("\n" + "=" * 88)
    print("MÉTRICAS STRICT — match por chunk_id (sólo válido dentro de chunks_v2)")
    print("vec_old/hyb_old ≈ 0 esperado (IDs de chunks viejo no están en gold de chunks_v2)")
    print("=" * 88)
    print(f"{'config':<10} | {'hit@5':>16} | {'recall@5':>16} | {'recall@15':>16} | {'mrr@15':>16}")
    print("-" * 88)
    for cfg in configs:
        cells = []
        for m in METRIC_FNS:
            mean_, lo, hi = bootstrap_ci95(agg[cfg][f"{m}_strict"], bootstrap_iters)
            cells.append(f"{mean_:.3f}[{lo:.2f},{hi:.2f}]")
        print(f"{cfg:<10} | " + " | ".join(f"{c:>16}" for c in cells))

    # ----- Deltas cross-tabla (LOOSE) -----
    print("\n" + "=" * 88)
    print("DELTAS (new - old) — LOOSE, paired bootstrap por pregunta")
    print("=" * 88)
    delta_summary = {}
    for pair_label, a_cfg, b_cfg in [("vec", "vec_old", "vec_new"),
                                      ("hyb", "hyb_old", "hyb_new")]:
        print(f"\n  {pair_label}:")
        delta_summary[pair_label] = {}
        for m in METRIC_FNS:
            d_mean, d_lo, d_hi = bootstrap_delta_ci95(
                agg[a_cfg][f"{m}_loose"], agg[b_cfg][f"{m}_loose"], bootstrap_iters)
            if d_lo > 0:
                sig = "✓ POSITIVO SIGNIFICATIVO"
            elif d_hi < 0:
                sig = "✗ NEGATIVO SIGNIFICATIVO"
            else:
                sig = "~ NO SIGNIFICATIVO (IC95 cruza 0)"
            print(f"    {m:>10}: Δ={d_mean:+.3f} IC95=[{d_lo:+.3f}, {d_hi:+.3f}]  {sig}")
            delta_summary[pair_label][m] = {
                "delta": d_mean, "ci_low": d_lo, "ci_high": d_hi}

    # ----- Verdict piso 1 — Hit@5 LOOSE como métrica primaria -----
    primary = "hit@5"
    print(f"\n{'=' * 88}")
    print(f"VERDICT PISO 1 (criterio: delta_{primary}_loose IC95 estrictamente positivo)")
    print("=" * 88)
    verdicts = {}
    for pair_label in ["vec", "hyb"]:
        d = delta_summary[pair_label][primary]
        passes = d["ci_low"] > 0
        verdict = "PASS" if passes else "NO PASS"
        verdicts[pair_label] = verdict
        print(f"  {pair_label}: Δ_{primary}={d['delta']:+.3f} IC95=[{d['ci_low']:+.3f},{d['ci_high']:+.3f}]  → {verdict}")
    print("=" * 88)

    # ----- Persistir -----
    out_data = {
        "version": "2.0",  # bumped: match doble strict+loose
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "top_k_retrieve": TOP_K_RETRIEVE,
            "rrf_k": RRF_K,
            "bootstrap_iters": bootstrap_iters,
            "include_hyde": False,
            "embedding_old": "text-embedding-3-small (1536)",
            "embedding_new": "voyage-4-large (1024)",
            "match_strict": "chunk_id (sólo dentro chunks_v2)",
            "match_loose":  "(source_file, page_number) (cross-tabla)",
        },
        "questions_evaluated": selected,
        "n_questions": len(selected),
        "elapsed_s": round(elapsed, 1),
        "per_question": [
            {
                "qid": r.qid,
                "question": r.question,
                "n_relevant": len(r.relevant_ids),
                "retrieved_top5": {cfg: ids[:5] for cfg, ids in r.retrieved.items()},
                "metrics": r.metrics,
            } for r in results
        ],
        "aggregate": {
            cfg: {
                m: {
                    "mean": float(np.nanmean(agg[cfg][m])),
                } for m in all_metrics
            } for cfg in configs
        },
        "deltas_loose": delta_summary,
        "verdict_floor1": verdicts,
    }
    OUT_JSON.write_text(json.dumps(out_data, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\nResultados persistidos en {OUT_JSON}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None,
                   help="Limita a las primeras N preguntas (debug)")
    p.add_argument("--bootstrap", type=int, default=BOOTSTRAP_ITERS,
                   help=f"Iters de bootstrap (default {BOOTSTRAP_ITERS})")
    args = p.parse_args()
    main(limit=args.limit, bootstrap_iters=args.bootstrap)
