#!/usr/bin/env python3
"""s101_hyq_negcontrol2.py — control negativo CON NULL de jitter (fix regla-C del v1).

El v1 confundió jitter run-a-run (golds con hyq_on=0 'desplazando') con efecto de la cuota.
v2: por gold → OFF_a, OFF_b (null de jitter) y ON. Señal = desplazamiento(OFF_a→ON) EXCEDENTE
sobre desplazamiento(OFF_a→OFF_b), y solo cuenta HIGH (rank final <25).
"""
import os
NPZ = os.path.join(os.getcwd(), "evals", "s101_hyq_embeddings.npz")
BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false"}
for k, v in BASE.items():
    os.environ[k] = v
os.environ["HYQ_PILOT_FILE"] = NPZ
import sys, yaml
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
os.environ["HYQ_PILOT_FILE"] = NPZ
from src.rag import retriever as R
from scripts.gold_store import dev

def _pool(q, flag):
    R.HYQ_PILOT_FILE = flag
    return R.retrieve_chunks(q, top_k=50)

def _high_displaced(base, other_ids):
    ids = [c.get("id") for c in base]
    return [i for i, cid in enumerate(ids) if cid not in other_ids and i < 25]

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rows = []
    excess_golds = 0
    for g in dev():
        q = g["question"]
        offa = _pool(q, ""); offb = _pool(q, ""); on = _pool(q, NPZ)
        offb_ids = {c.get("id") for c in offb}; on_ids = {c.get("id") for c in on}
        null_high = _high_displaced(offa, offb_ids)      # jitter puro
        treat_high = _high_displaced(offa, on_ids)       # jitter + cuota
        excess = [r for r in treat_high if r not in null_high]
        n_hyq = sum(1 for c in on if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        rows.append({"qid": g["qid"], "null_high": null_high, "treat_high": treat_high,
                     "excess_high": excess, "n_hyq_on": n_hyq})
        if excess and n_hyq:
            excess_golds += 1
            print(f"  ⚠ {g['qid']:8s} EXCESS-HIGH ranks {excess} (null={null_high}) hyq_on={n_hyq}")
    tot_null = sum(len(r["null_high"]) for r in rows)
    tot_excess = sum(len(r["excess_high"]) for r in rows if r["n_hyq_on"])
    print(f"\n── CONTROL NEGATIVO v2 (null-corrected) ──")
    print(f"  null (jitter OFF-vs-OFF) HIGH total: {tot_null}")
    print(f"  EXCESS HIGH atribuible a la cuota (solo golds con hyq_on>0): {tot_excess} en {excess_golds} golds")
    print(f"  VEREDICTO: {'✅ dentro del jitter' if tot_excess <= max(2, tot_null) else '❌ excede el null — daño real'}")
    yaml.safe_dump({"tot_null_high": tot_null, "tot_excess_high": tot_excess,
                    "excess_golds": excess_golds, "rows": rows},
                   open(os.path.join(os.getcwd(), "evals", "s101_hyq_negcontrol2.yaml"), "w",
                        encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print("→ s101_hyq_negcontrol2.yaml")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
