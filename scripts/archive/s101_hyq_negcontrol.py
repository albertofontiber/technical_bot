#!/usr/bin/env python3
"""s101_hyq_negcontrol.py — control negativo full-dev(39) del piloto hyq (addendum §4), judge-free.

Para CADA gold dev: pool-50 OFF vs ON (la cuota desplaza la cola del canal vectorial). Señales de daño:
  - displaced_high: un chunk que en OFF estaba en el TOP-25 del pool sale del pool en ON (load-bearing
    probable → riesgo real; el desplazamiento esperado es cola 40-50 del canal vectorial).
  - n_displaced por gold (magnitud del churn).
El check con juez (¿algún hecho OK pierde su soporte?) corre con el assessment full cuando toque el
ship-gate; ESTE control es el gate del PILOTO (mecanismo).
"""
import os
NPZ = os.path.join(os.getcwd(), "evals", "s101_hyq_embeddings.npz")
BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false"}
for k, v in BASE.items():
    os.environ[k] = v
os.environ["HYQ_PILOT_FILE"] = NPZ          # proceso ON; el OFF se simula quitando el flag ANTES de importar? NO:
# el flag se lee a IMPORT-time → un solo proceso no puede medir ambos brazos con fidelidad de import.
# Truco fiel: importamos con flag ON y para el brazo OFF monkeypatcheamos HYQ_PILOT_FILE="" en el módulo.
import sys, yaml
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
os.environ["HYQ_PILOT_FILE"] = NPZ
from src.rag import retriever as R
from scripts.gold_store import dev

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    golds = dev()
    rows = []
    tot_disp = tot_high = 0
    for g in golds:
        q = g["question"]
        R.HYQ_PILOT_FILE = ""                      # brazo OFF (monkeypatch del módulo, mismo proceso)
        off = R.retrieve_chunks(q, top_k=50)
        R.HYQ_PILOT_FILE = NPZ                     # brazo ON
        on = R.retrieve_chunks(q, top_k=50)
        off_ids = [c.get("id") for c in off]
        on_ids = {c.get("id") for c in on}
        displaced = [i for i, cid in enumerate(off_ids) if cid not in on_ids]
        high = [i for i in displaced if i < 25]    # rank OFF < 25 = load-bearing probable
        n_hyq = sum(1 for c in on if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        tot_disp += len(displaced); tot_high += len(high)
        rows.append({"qid": g["qid"], "n_displaced": len(displaced), "displaced_high_ranks": high,
                     "n_hyq_on": n_hyq})
        if high:
            print(f"  ⚠ {g['qid']:8s} desplaza {len(displaced)} (HIGH: ranks {high}) hyq_on={n_hyq}")
    n_affected = sum(1 for r in rows if r["n_displaced"])
    n_high_golds = sum(1 for r in rows if r["displaced_high_ranks"])
    print(f"\n── CONTROL NEGATIVO (39 dev, judge-free) ──")
    print(f"  golds con desplazamiento: {n_affected}/39 · total chunks desplazados: {tot_disp}")
    print(f"  golds con desplazamiento HIGH (rank<25): {n_high_golds} · chunks HIGH: {tot_high}")
    print(f"  VEREDICTO: {'✅ churn de cola (esperado)' if n_high_golds == 0 else '❌ desplaza load-bearing — revisar'}")
    out = os.path.join(os.getcwd(), "evals", "s101_hyq_negcontrol.yaml")
    yaml.safe_dump({"n_affected": n_affected, "tot_displaced": tot_disp,
                    "n_high_golds": n_high_golds, "rows": rows}, open(out, "w", encoding="utf-8"),
                   allow_unicode=True, sort_keys=False)
    print(f"→ s101_hyq_negcontrol.yaml")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
