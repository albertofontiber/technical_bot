#!/usr/bin/env python3
"""Paso-0 del gate-0 s60 (lever de MERGE): sensibilidad del reranker LLM al ORDEN.

Pre-registro: evals/_s60_lever_design_FINAL.md §2 paso-0. Pregunta que responde:
¿el top-5 que elige el reranker cambia cuando SOLO cambia el orden de presentación
de los MISMOS candidatos? (mecanismo (i) del lever — el de alcance 39/39).

READ-ONLY: pools CONGELADOS del brazo s59 (`evals/s59_frozen_contexts.json`,
pool50_light = el orden real post-pipeline que vio el reranker en el A/B s59);
hidratación de content/metadata/embedding por id vía PostgREST (corpus congelado);
ninguna escritura a DB.

Diseño (una config, fijada PRE-DATOS — dos resoluciones operativas declaradas
que el FINAL v3 dejaba ambiguas, resueltas ANTES de correr):
  1. El FINAL §2 listaba "12 golds" con cat010 contado DOS veces (unánime y
     mover) = 11 únicos. Resolución: 12º gold = cat020 (el gold de ruido
     demostrado s59; un gold más con pool congelado, sin privilegio).
  2. Categoría por gold: INSENSIBLE (modal-a == modal-b), SENSIBLE (modales
     estables distintos), INESTABLE (algún lado sin modal 2/3). Para el
     criterio NO-GO, INESTABLE cuenta como NO-sensible (si el dado interno del
     reranker domina, el orden tampoco es palanca). NO-GO si NO-sensibles
     (INSENSIBLE+INESTABLE) >= 10/12 -> mecanismo (i) no opera -> re-dimensionar
     y re-presentar a Alberto (no muerte automática: (ii)/(iii) sin medir).

Órdenes comparados (mismos candidatos exactos):
  orden-a = pool50_light TAL CUAL (stamps + diversificadores = pipeline real);
  orden-b = coseno real re-computado (embed_query de la question vs embedding
            del chunk, uniforme para TODOS los candidatos), desc, tie-break id.

Réplicas: n=3 por orden (rerank LLM temp=0 pero no bit-determinista);
top-5 como frozenset de content-hash (composición); modal = >=2/3.
Paridad con el A/B: rerank_chunks(query, pool, top_k=5) SIN target_models
(bvg_kmajority.py:197). Si CUALQUIER llamada cae al fail-open interno del
reranker ("Reranking failed") la corrida ABORTA — el fail-open devuelve el
orden de entrada y contaminaría la medición con falsa sensibilidad.

Artefactos:
  evals/s60_step0_order_sensitivity.yaml  (config + por-gold + conteos + veredicto)
  evals/s60_step0_cosines.json            (cosenos por gold/id — reuso gate-0 V-A)

Uso:
  python scripts/s60_step0_order_sensitivity.py [--smoke]   # --smoke: cat020 n=1
"""
import hashlib
import json
import logging
import math
import os
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Forzar chunks_v2 ANTES de importar config (patrón test_bot_vs_gold.py:19-34).
os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-asegurar tras load_dotenv

import httpx  # noqa: E402
import yaml  # noqa: E402

from src.config import CHUNKS_TABLE, CHUNKS_IS_V2, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402
from src.rag.reranker import rerank_chunks, RERANK_MODEL  # noqa: E402

FROZEN = ROOT / "evals" / "s59_frozen_contexts.json"
OUT_YAML = ROOT / "evals" / "s60_step0_order_sensitivity.yaml"
OUT_COS = ROOT / "evals" / "s60_step0_cosines.json"

UNANIMES = ["cat010", "cat014", "cat015", "cat022", "hp015", "hp019"]
MOVERS = ["hp001", "cat012", "cat005", "cat009", "hp018"]  # cat010 ya en unánimes
EXTRA = ["cat020"]  # 12º (resolución pre-datos #1 del docstring)
GOLDS = UNANIMES + MOVERS + EXTRA

N_REPLICAS = 3
TOP_K = 5
NO_GO_THRESHOLD = 10  # NO-sensibles >= 10/12 -> NO-GO mecanismo (i)

HYDRATE_COLS = (
    "id,content,product_model,section_title,content_type,"
    "has_diagram,diagram_url,embedding"
)

# --- detección de fail-open del reranker (contaminaría la medición) ---
_rerank_errors: list[str] = []
_err_lock = threading.Lock()


class _FailOpenDetector(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if "Reranking failed" in record.getMessage():
            with _err_lock:
                _rerank_errors.append(record.getMessage())


logging.getLogger("src.rag.reranker").addHandler(_FailOpenDetector())


def hydrate(ids: list[str]) -> dict[str, dict]:
    """Trae content/metadata/embedding de los ids (read-only, un GET)."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    rows: list[dict] = []
    # lotes de 40 ids para no rozar límites de URL
    for i in range(0, len(ids), 40):
        batch = ids[i : i + 40]
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=headers,
                params={"id": f"in.({','.join(batch)})", "select": HYDRATE_COLS},
            )
            resp.raise_for_status()
        rows.extend(resp.json())
    by_id = {r["id"]: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        sys.exit(f"ABORT: {len(missing)} ids del pool congelado no están en {CHUNKS_TABLE}: {missing[:3]}")
    for r in rows:
        emb = r.get("embedding")
        if emb is None:
            sys.exit(f"ABORT: embedding NULL en chunk {r['id']}")
        if isinstance(emb, str):
            r["embedding"] = json.loads(emb)
    return by_id


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def chash(c: dict) -> str:
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def top5_signature(chunks: list[dict]) -> frozenset:
    return frozenset(chash(c) for c in chunks[:TOP_K])


def modal(signatures: list[frozenset]) -> frozenset | None:
    sig, count = Counter(signatures).most_common(1)[0]
    return sig if count >= 2 else None


def describe(sig: frozenset, pool: list[dict]) -> list[str]:
    """Firma -> lista legible (source_file pN) en orden estable."""
    by_hash = {}
    for c in pool:
        by_hash.setdefault(chash(c), f"{(c.get('source_file') or '?')[:40]} p{c.get('page_number')}")
    return sorted(by_hash.get(h, h) for h in sig)


def run_gold(qid: str, frozen: dict, n_replicas: int) -> tuple[dict, dict]:
    g = frozen[qid]
    query = g["question"]
    pool_light = g["pool50_light"]
    ids = [c["id"] for c in pool_light]
    by_id = hydrate(ids)

    # orden-a: pool tal cual (pipeline real); hidratado manteniendo el orden
    order_a = [{**by_id[c["id"]], "similarity": c.get("similarity")} for c in pool_light]

    # orden-b: coseno real uniforme, desc, tie-break id
    q_emb = embed_query(query)
    cos_by_id = {c["id"]: cosine(q_emb, by_id[c["id"]]["embedding"]) for c in pool_light}
    order_b = sorted(order_a, key=lambda c: (-cos_by_id[c["id"]], c["id"]))
    for c in order_b:
        c = dict(c)  # no mutar order_a

    # el reranker no debe ver el campo embedding (no existe en el path real)
    strip = lambda c: {k: v for k, v in c.items() if k != "embedding"}  # noqa: E731
    arm_a = [strip(c) for c in order_a]
    arm_b = [strip(c) for c in order_b]

    def replicas(arm: list[dict]) -> list[frozenset]:
        sigs = []
        for _ in range(n_replicas):
            out = rerank_chunks(query, arm, top_k=TOP_K)
            sigs.append(top5_signature(out))
        return sigs

    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(replicas, arm_a)
        fb = pool.submit(replicas, arm_b)
        sigs_a, sigs_b = fa.result(), fb.result()

    mod_a, mod_b = modal(sigs_a), modal(sigs_b)
    if mod_a is None or mod_b is None:
        category = "INESTABLE"
    elif mod_a == mod_b:
        category = "INSENSIBLE"
    else:
        category = "SENSIBLE"

    result = {
        "qid": qid,
        "n_candidates": len(ids),
        "category": category,
        "modal_a": describe(mod_a, arm_a) if mod_a else None,
        "modal_b": describe(mod_b, arm_a) if mod_b else None,
        "votes_a": [sorted(s) for s in sigs_a],
        "votes_b": [sorted(s) for s in sigs_b],
        "overlap_modal": (len(mod_a & mod_b) if (mod_a and mod_b) else None),
    }
    return result, {qid: cos_by_id}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"

    smoke = "--smoke" in sys.argv
    golds = ["cat020"] if smoke else GOLDS
    n_replicas = 1 if smoke else N_REPLICAS

    frozen = json.load(open(FROZEN, encoding="utf-8"))
    print(f"paso-0 s60 | golds={len(golds)} n={n_replicas} reranker={RERANK_MODEL} tabla={CHUNKS_TABLE}")

    results, cosines = [], {}
    for qid in golds:  # secuencial por gold; paralelo intra-gold (2 brazos)
        r, cos = run_gold(qid, frozen, n_replicas)
        results.append(r)
        cosines.update(cos)
        print(f"  {qid}: {r['category']} (candidatos={r['n_candidates']}, overlap_modal={r['overlap_modal']})")

    if _rerank_errors:
        sys.exit(f"ABORT: {len(_rerank_errors)} fail-open del reranker durante la corrida — medición contaminada, re-correr")

    if smoke:
        print("SMOKE OK (sin artefactos)")
        return 0

    by_cat = Counter(r["category"] for r in results)
    no_sensibles = by_cat["INSENSIBLE"] + by_cat["INESTABLE"]
    verdict = "NO-GO mecanismo (i)" if no_sensibles >= NO_GO_THRESHOLD else "GO (mecanismo existe)"
    group = lambda qs: Counter(r["category"] for r in results if r["qid"] in qs)  # noqa: E731

    out = {
        "meta": {
            "at": datetime.now().isoformat(timespec="seconds"),
            "design": "evals/_s60_lever_design_FINAL.md §2 paso-0",
            "preregistered_resolutions": [
                "12º gold = cat020 (corrige doble-conteo de cat010 en el FINAL)",
                "INESTABLE cuenta como NO-sensible para el umbral NO-GO",
            ],
            "config": {
                "rerank_model": RERANK_MODEL, "n_replicas": N_REPLICAS, "top_k": TOP_K,
                "no_go_threshold": f">={NO_GO_THRESHOLD}/12 NO-sensibles",
                "orden_a": "pool50_light s59 tal cual (pipeline real)",
                "orden_b": "coseno re-computado uniforme desc, tie-break id",
                "paridad": "rerank_chunks sin target_models (bvg_kmajority.py:197)",
            },
            "golds": {"unanimes": UNANIMES, "movers": MOVERS, "extra": EXTRA},
        },
        "results": results,
        "tally": {
            "SENSIBLE": by_cat["SENSIBLE"], "INSENSIBLE": by_cat["INSENSIBLE"],
            "INESTABLE": by_cat["INESTABLE"], "no_sensibles": no_sensibles,
            "por_grupo": {
                "unanimes": dict(group(UNANIMES)),
                "movers": dict(group(MOVERS)),
                "extra": dict(group(EXTRA)),
            },
        },
        "verdict": verdict,
    }
    OUT_YAML.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    OUT_COS.write_text(json.dumps(cosines, indent=1), encoding="utf-8")
    print(f"\nTALLY: {dict(by_cat)} -> no_sensibles={no_sensibles}/12")
    print(f"VEREDICTO: {verdict}")
    print(f"artefactos: {OUT_YAML.name}, {OUT_COS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
