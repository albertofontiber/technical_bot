#!/usr/bin/env python3
"""s101_deathpoint.py — death-point MECE de los retrieval-miss/corpus-FN del assessment s100.

Fase 1 upstream (mandato s100b): antes de diseñar levers, localizar la ETAPA REAL donde muere cada
hecho (RECALL/MERGE/MODEL-FILTER/DIVERSIFY/LANGUAGE/DEPTH) con `retrieve_chunks(_trace=...)` sobre el
pipeline de la DEMO (flags exportados). Reusa `diagnose_miss` de retrieval_miss_diagnose (s85·B1,
dúo-hardened) alimentado con los facts FRESCOS de evals/s100_factlevel_full.yaml (no el DEF bit-rotted).

val_chunks (donde vive el dato, same-family):
  - fact anclable  → léxico `fact_match_score >= SCORE_FLOOR` sobre los chunks del manual (barato, determinista)
  - no-anclable    → juez GPT-5.5 K=5 sobre manual acotado/ordenado (patrón SEM_CORPUS_BOUND)

Salida: evals/s101_deathpoint.yaml + tabla. GO de lever = reducción del bucket (mandato), medida después.
"""
from __future__ import annotations
import os

DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
    "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
    "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800", "HYDE_ENABLED": "false",
}
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

import sys, json
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import yaml
from src.rag.retriever import retrieve_chunks
from scripts.audit_retrieval_funnel import target_servable, fetch_manual_chunks, doc_tokens
from scripts.audit_locator import fact_match_score, SCORE_FLOOR
from scripts.retrieval_miss_famtie import gold_family, fam_norm, _pm_by_ids
from scripts.retrieval_miss_judge import judge_fact, supported_ids, THRESH_FIRM
from scripts.retrieval_miss_diagnose import diagnose_miss

for _k, _v in DEMO_FLAGS.items():          # re-assert tras imports (legacy load_dotenv override=True)
    os.environ[_k] = _v
from src.config import RERANK_TOP_K
assert RERANK_TOP_K == 10, "pipeline fantasma: RERANK_TOP_K != demo(10)"

SEM_BOUND = 40
FULL = ROOT / "evals" / "s100_factlevel_full.yaml"
OUT = ROOT / "evals" / "s101_deathpoint.yaml"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    d = yaml.safe_load(FULL.read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in d["per_gold"]}

    # universo = retrieval-miss + corpus-gap (estos últimos = FN verificados a mano s100)
    misses = []
    for r in d["per_gold"]:
        for f in r["facts"]:
            if f.get("clase") in ("retrieval-miss", "corpus-gap"):
                misses.append({"qid": r["qid"], "valor": f["valor"], "texto": f.get("texto", ""),
                               "anchorable": bool(f.get("lexically_anchorable", True)),
                               "clase_s100": f["clase"]})
    print(f"{len(misses)} facts upstream (retrieval-miss + corpus-FN)")

    results = []
    cache_manual: dict[str, list] = {}
    for m in misses:
        g = golds[m["qid"]]
        qid = m["qid"]
        if qid not in cache_manual:
            # manual objetivo + familia del gold (mismos mecanismos que el assessment)
            gold_yaml = None
            try:
                from scripts.gold_store import get as gs_get
                gold_yaml = gs_get(qid)
            except Exception:
                pass
            prov = (gold_yaml or {}).get("_provenance") or {}
            fuente = prov.get("fuente", "")
            servable, srv = target_servable(gold_yaml or {"citations": [], "_provenance": {}})
            targets = srv["target_tokens"]
            manual = fetch_manual_chunks(targets) if targets else []
            gfam = gold_family(doc_tokens(fuente), targets, fuente)
            pm = {c.get("id"): c.get("product_model") for c in manual}
            missing = [cid for cid, v in pm.items() if v in (None, "")]
            if missing:
                pm.update(_pm_by_ids(missing))
            fam_manual = [c for c in manual if not gfam or fam_norm(pm.get(c.get("id"), "")) in gfam]
            cache_manual[qid] = fam_manual or manual   # fallback declarado si familia no filtra
        fam_manual = cache_manual[qid]

        # val_chunks: dónde vive el dato
        if m["anchorable"]:
            val_chunks = [c for c in fam_manual
                          if (fact_match_score(m["valor"], m["texto"], c.get("content") or "") or 0) >= SCORE_FLOOR]
        else:
            ordered = sorted(fam_manual, key=lambda c: (c.get("page_number") is None, c.get("page_number") or 0))
            v = judge_fact(m["valor"], m["texto"], ordered[:SEM_BOUND], workers=6)
            sup = supported_ids(v, THRESH_FIRM)
            val_chunks = [c for c in ordered[:SEM_BOUND] if c.get("id") in sup]

        # pool actual (para el motivo within-doc) — 1 retrieve fresco
        pool = retrieve_chunks(g["question"], top_k=50)
        pin = [{"id": c.get("id"), "src": c.get("source_file")} for c in pool]

        diag = diagnose_miss({"question": g["question"]},
                             {"qid": qid, "valor": m["valor"], "gold_family": None},
                             pin, val_chunks, k=3)
        diag["clase_s100"] = m["clase_s100"]
        diag["n_val_chunks"] = len(val_chunks)
        diag["val_srcs"] = sorted({f"{c.get('source_file','')[:24]}#p{c.get('page_number')}" for c in val_chunks})[:4]
        results.append(diag)
        print(f"  {qid:8s} «{m['valor'][:30]:30s}» etapa={diag['etapa']:14s} motivos={','.join(diag['motivos']) or '-'} "
              f"val_chunks={len(val_chunks)} jitter={diag['jitter']}")

    from collections import Counter
    etapas = Counter(r["etapa"] for r in results)
    print("\n── DISTRIBUCIÓN de etapa-de-fallo ──")
    for e, n in etapas.most_common():
        print(f"  {e:16s} {n}")
    OUT.write_text(yaml.safe_dump({"demo_flags": DEMO_FLAGS, "n": len(results),
                                   "etapas": dict(etapas), "results": results},
                                  allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
