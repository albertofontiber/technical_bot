#!/usr/bin/env python3
"""s102_toc_measure.py — L2c: demote de páginas de ÍNDICE en el rerank (RERANK_DEMOTE_TOC).

Evidencia (full v3 + mapa fase-2): cat017#4·CLSS = rerank-miss con best_pool_rank=10 y el único
lex-hit SERVIDO era el ÍNDICE de HOP-138-8ES p.2 (títulos de sección sin contenido) — un índice
matchea léxicamente la query pero jamás la responde, y roba el slot servido al chunk-respuesta.

Fases (gateadas — no gastar rerank sin eyeball previo de la heurística):
  scan    → pool-50 por gold dev; lista TODO candidato que _is_toc_page marca (src/página/preview)
            para eyeball de PRECISIÓN + cachea pools a evals/s102_toc_pools.json.
  measure → sobre los pools CACHEADOS: rerank OFF vs ON en dos fases secuenciales (mismo pool;
            sin jitter de RETRIEVAL). OJO (S1 dúo s102, refutado por los propios datos): el
            LLM-rerank NO es determinista ni a temperature=0 — cat001/cat011 con 0 TOCs en pool
            (input idéntico ambos brazos) cambiaron 2 slots cada uno ⇒ el churn ON-vs-OFF
            contiene RUIDO BASE y la atribución de una loss individual al lever no es limpia.
            Soporte por-fact con el proxy léxico L1 (fact_match_score ≥ SCORE_FLOOR, sin
            family-filter: el ruido cross-family pega IGUAL en ambos brazos). GO del mecanismo
            (mandato s101): GAIN en facts rerank-miss sin LOSS en facts con soporte servido —
            proxy léxico servido, NO el bucket end-to-end del instrumento (F3 cross-model).
Salida: evals/s102_toc_measure.yaml
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": "", "RERANK_DEMOTE_TOC": "off"}
for k, v in BASE.items():
    os.environ[k] = v

import json
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v

from scripts.audit_locator import SCORE_FLOOR, fact_match_score
from scripts.gold_store import dev
from scripts.toc_heuristic import is_toc_page as _is_toc_page
from src.rag import retriever as R
from src.rag import reranker as _rr
from src.rag.reranker import rerank

# (s102) El seam RERANK_DEMOTE_TOC NO vive en src/ (lever NO-GO: 0 gains, 1 loss real
# hp011#3, churn 11/39 — evals/s102_toc_measure.yaml): re-correr `measure` exige aplicar
# antes `git apply evals/s102_toc_seam.patch`. Sin este guard, el env se ignoraría en
# silencio y se "mediría" OFF-vs-OFF (clase s96-H3). `scan` no necesita el seam.
def _require_seam():
    if not hasattr(_rr, "_demote_toc_on"):
        raise RuntimeError("seam demote-TOC ausente en reranker — aplica evals/s102_toc_seam.patch")
    # F5 cross-model s102: existir el parser no basta (un stub pasaría) — el DISPATCHER debe
    # consultarlo de verdad, o se "mediría" OFF-vs-OFF (clase s96-H3).
    import inspect
    if "_demote_toc_on(" not in inspect.getsource(_rr.rerank):
        raise RuntimeError("el dispatcher rerank() no consulta _demote_toc_on — patch parcial/stale")

POOLS_PATH = os.path.join("evals", "s102_toc_pools.json")
OUT_PATH = os.path.join("evals", "s102_toc_measure.yaml")
TOP_K = 10


def _pool(q: str) -> list[dict]:
    return R.retrieve_chunks(q, top_k=50)


def _sanitize(c: dict) -> dict:
    return {k: v for k, v in c.items()
            if isinstance(v, (str, int, float, bool, type(None), list, dict))}


def scan() -> None:
    golds = dev()
    print(f"scan: {len(golds)} golds dev — pool-50 + heurística TOC", flush=True)
    pools: dict[str, list[dict]] = {}

    def one(g):
        return g["qid"], [_sanitize(c) for c in _pool(g["question"])]

    with ThreadPoolExecutor(max_workers=4) as ex:
        for qid, pool in ex.map(one, golds):
            pools[qid] = pool
            print(f"  [{qid}] pool={len(pool)}", flush=True)

    flagged = []
    for qid, pool in pools.items():
        for rank, c in enumerate(pool):
            if _is_toc_page(c.get("content") or ""):
                flagged.append({
                    "qid": qid, "pool_rank": rank, "id": c.get("id"),
                    "src": c.get("source_file"), "page": c.get("page_number"),
                    "preview": (c.get("content") or "")[:110].replace("\n", " ⏎ "),
                })
    with open(POOLS_PATH, "w", encoding="utf-8") as f:
        json.dump(pools, f, ensure_ascii=False, default=str)
    print(f"\n── {len(flagged)} candidatos marcados TOC en los pools "
          f"(eyeball TODOS antes de measure) ──", flush=True)
    seen_chunk = set()
    for x in flagged:
        dup = " (repetido)" if x["id"] in seen_chunk else ""
        seen_chunk.add(x["id"])
        print(f"  [{x['qid']}] rank={x['pool_rank']:>2} {x['src']} p.{x['page']}{dup}\n"
              f"      {x['preview']}", flush=True)
    print(f"\npools → {POOLS_PATH}", flush=True)


def _support_in(fact: dict, chunks: list[dict]) -> list[str]:
    valor, texto = fact.get("valor") or "", fact.get("texto") or ""
    out = []
    for c in chunks:
        score = fact_match_score(valor, texto, c.get("content") or "") or 0
        if score >= SCORE_FLOOR:
            out.append(c.get("id"))
    return out


def measure() -> None:
    _require_seam()
    with open(POOLS_PATH, encoding="utf-8") as f:
        pools = json.load(f)
    golds = {g["qid"]: g for g in dev()}
    print(f"measure: {len(pools)} pools cacheados — rerank OFF vs ON (2 fases)", flush=True)

    served: dict[str, dict[str, list[dict]]] = {"off": {}, "on": {}}
    for arm in ("off", "on"):
        os.environ["RERANK_DEMOTE_TOC"] = arm  # entre fases, nunca dentro de threads (race)

        def one(item):
            qid, pool = item
            q = golds[qid]["question"]
            return qid, rerank(q, [dict(c) for c in pool], top_k=TOP_K, strict=True)

        with ThreadPoolExecutor(max_workers=4) as ex:
            for qid, out in ex.map(one, sorted(pools.items())):
                served[arm][qid] = out
                print(f"  [{arm}] {qid} served={len(out)}", flush=True)

    gains, losses, rows = [], [], []
    for qid, pool in sorted(pools.items()):
        g = golds[qid]
        toc_in_pool = [c.get("id") for c in pool if _is_toc_page(c.get("content") or "")]
        s_off, s_on = served["off"][qid], served["on"][qid]
        for i, fact in enumerate(g.get("atomic_facts") or []):
            if (fact.get("tipo") or "core") == "supplementary":
                continue
            sup_pool = _support_in(fact, pool)
            if not sup_pool:
                continue  # sin soporte léxico en pool-50: el rerank no puede moverlo
            off_ids = _support_in(fact, s_off)
            on_ids = _support_in(fact, s_on)
            if bool(off_ids) != bool(on_ids):
                row = {"key": f"{qid}#{i}:{fact.get('valor')}", "sup_pool_n": len(sup_pool),
                       "off_served": off_ids, "on_served": on_ids,
                       "direction": "GAIN" if on_ids else "LOSS"}
                (gains if on_ids else losses).append(row["key"])
                rows.append(row)
        rows.append({"qid": qid, "toc_in_pool_n": len(toc_in_pool),
                     "toc_served_off": [c.get("id") for c in s_off
                                        if _is_toc_page(c.get("content") or "")],
                     "served_off": [c.get("id") for c in s_off],
                     "served_on": [c.get("id") for c in s_on]})

    result = {"lever": "L2c demote-TOC rerank (RERANK_DEMOTE_TOC)",
              "proxy": "soporte léxico L1 (fact_match_score>=FLOOR, sin family-filter; "
                       "mismo pool ambos brazos => delta = solo el lever)",
              "gains": gains, "losses": losses, "detail": rows}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(result, f, allow_unicode=True, sort_keys=False, width=110)
    print(f"\n== GAINS {len(gains)}: {gains}", flush=True)
    print(f"== LOSSES {len(losses)}: {losses}", flush=True)
    print(f"→ {OUT_PATH}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "scan":
        scan()
    elif mode == "measure":
        measure()
    else:
        print("uso: s102_toc_measure.py scan|measure")
        sys.exit(2)
