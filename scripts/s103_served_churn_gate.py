#!/usr/bin/env python3
"""s103_served_churn_gate.py — DISCRIMINANTE 1 del landing v3.1 (extensión acotada del aside).

El riesgo real de v3.1 no vive en el pool (nadie sale — mecánico) sino en el RERANKER: +10
chunks de input pueden cambiar el top-10 SERVIDO (F1 crítico del dúo). Ablación same-code:
por gold, un solo retrieve (v3.1, HYQ on) →
  A1, A2 = rerank(pool SIN aside) ×2  → null del no-determinismo del LLM-rerank (DEC-096)
  B      = rerank(pool CON aside)     → tratamiento
Métrica por gold: churn = |served(A1) \\ served(B)| − |served(A1) \\ served(A2)| (excedente
sobre el null, clip a ≥0). Gate: excedente total ≤ max(2, null total) — mismo estilo de
veredicto que el negcontrol — y lista de golds a LEER (patrón DEC-092b) si exceden.

Coste: 39 golds × 3 rerank-calls (Sonnet, strict). ~$5-8.
Uso: python scripts/s103_served_churn_gate.py
Salida: evals/s103_served_churn_gate.yaml
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off",
        "NEIGHBOR_WINDOW": "0"}
for k, v in BASE.items():
    os.environ[k] = v
import subprocess  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
import yaml  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from scripts.gold_store import dev  # noqa: E402

assert R.HYQ_TABLE_ON is False


def _served_ids(query, pool, models):
    out = rerank_chunks(query, [dict(c) for c in pool], target_models=models, strict=True)
    return [c.get("id") for c in out]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    golds = dev()
    rows, tot_null, tot_excess = [], 0, 0
    for g in golds:
        q = g["qid"]
        R.HYQ_TABLE_ON = True
        try:
            pool = R.retrieve_chunks(g["question"], top_k=50)
        finally:
            R.HYQ_TABLE_ON = False
        aside = [c for c in pool if c.get("_hyq_surrogate")]
        if not aside:
            rows.append({"qid": q, "fired": False})
            continue
        body = [c for c in pool if not c.get("_hyq_surrogate")]
        models = R.extract_product_models(g["question"])
        try:
            a1 = _served_ids(g["question"], body, models)
            a2 = _served_ids(g["question"], body, models)
            b = _served_ids(g["question"], pool, models)
        except Exception as e:
            rows.append({"qid": q, "fired": True, "error": str(e)[:120]})
            print(f"  ⚠ {q:8s} RERANK ERROR {str(e)[:80]}", flush=True)
            continue
        null = len(set(a1) - set(a2))
        treat = len(set(a1) - set(b))
        excess = max(0, treat - null)
        sur_served = sum(1 for i in b if i in {c.get("id") for c in aside})
        tot_null += null
        tot_excess += excess
        rows.append({"qid": q, "fired": True, "n_aside": len(aside), "null": null,
                     "treat": treat, "excess": excess, "surrogates_served": sur_served})
        flag = " ⚠" if excess > null else ""
        print(f"  {q:8s} aside={len(aside)} null={null} treat={treat} "
              f"excess={excess} sur_served={sur_served}{flag}", flush=True)
    fired = [r for r in rows if r.get("fired") and "error" not in r]
    assert fired, "canal no disparó en ningún gold — medición inválida (H3)"
    verdict = "PASA" if tot_excess <= max(2, tot_null) else "NO PASA"
    to_read = [r["qid"] for r in fired if r["excess"] > max(1, r["null"])]
    print(f"\n── SERVED-CHURN gate (v3.1 extensión, null-corrected) ──")
    print(f"  golds con canal: {len(fired)} · null total: {tot_null} · EXCESS total: {tot_excess}")
    print(f"  VEREDICTO: {'✅' if verdict == 'PASA' else '❌'} {verdict} "
          f"(umbral: excess ≤ max(2, null))")
    print(f"  golds a LEER (DEC-092b) si procede: {to_read}")
    yaml.safe_dump({"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                                        capture_output=True)
                              .stdout.decode().strip(),
                              "flags": {**BASE, "HYQ_TABLE": "on (call-time flip)"},
                              "rerank_model": "claude-sonnet-4-6 strict"},
                    "tot_null": tot_null, "tot_excess": tot_excess, "verdict": verdict,
                    "to_read": to_read, "rows": rows},
                   open(os.path.join(os.getcwd(), "evals", "s103_served_churn_gate.yaml"),
                        "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print("→ evals/s103_served_churn_gate.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
