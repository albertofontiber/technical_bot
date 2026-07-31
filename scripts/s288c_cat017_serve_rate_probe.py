"""s288c — probe serve-rate judge-free de cat017#4 (mandato dúo r1: H2 sub-agente + Gate-5 Sol).

Pregunta única: ¿con qué frecuencia entra un portador del hecho CLSS (`b7633e98…` p.5 o
`ae86bacb…` guía de licencias, el 2º portador que P1 metió al pool) en el top-K del reranker
por la RUTA HARNESS EXACTA? Sin juez, sin coverage, sin generación: la clase en disputa es
rerank-miss y `in_topk` solo necesita retrieve+rerank (dúo r1, H2).

Paridad de ruta por construcción: importa `_eval_strict_rerank` del instrumento (el import
pinea DEMO_FLAGS) y llama `retrieve_chunks`/`rerank` con los MISMOS parámetros que
`factlevel_assessment.run_pipeline` (:366-378): `target_models=None`, tops de src.config.
La pregunta se lee del artefacto canónico rep1 (misma string que consumió el instrumento).

Regla de decisión PRE-REGISTRADA (dúo r1): 0/N → miss ESTABLE (la pieza 3 elige mecanismo);
≥1/N → clase FRONTERA-DE-COLA (la pieza 3 pierde justificación; residual declarado).
Coste ≈ N × (1 embedding + 1 rerank LLM); N=6 < $1.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.factlevel_assessment import _eval_strict_rerank          # pinea DEMO_FLAGS
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K
from src.rag.retriever import retrieve_chunks

QID = "cat017"
TARGETS = ("b7633e98", "ae86bacb")     # prefijos de id de los 2 portadores del hecho
SENTINEL = "f0dc41c3"                  # soporte de cat017#0/#1 — no debe salir del top-K
ARTIFACT = ROOT / "evals" / "s100_factlevel_smoke_v31_cat017_head_rep1.yaml"
OUT = ROOT / "evals" / "s288c_cat017_serve_rate_probe_v1.json"


def _question() -> str:
    import yaml
    rows = yaml.safe_load(ARTIFACT.read_text(encoding="utf-8"))["per_gold"]
    row = next(r for r in rows if r["qid"] == QID)
    q = str(row["question"]).strip()
    assert q, "pregunta vacía en el artefacto canónico"
    return q


def _rank_of(prefix: str, rows: list[dict]) -> int | None:
    for i, row in enumerate(rows):
        if str(row.get("id", "")).startswith(prefix):
            return i
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=6)
    args = parser.parse_args()

    question = _question()
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    reps = []
    for n in range(args.reps):
        pool = retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)
        topk = _eval_strict_rerank(question, pool, top_k=RERANK_TOP_K,
                                   target_models=None)
        reps.append({
            "rep": n + 1,
            "pool_n": len(pool),
            "pool_rank": {t: _rank_of(t, pool) for t in TARGETS},
            "topk_ids": [str(r.get("id", ""))[:8] for r in topk],
            "carrier_in_topk": any(_rank_of(t, topk) is not None for t in TARGETS),
            "sentinel_in_topk": _rank_of(SENTINEL, topk) is not None,
        })
        served = [t for t in TARGETS if _rank_of(t, topk) is not None]
        print(f"rep {n+1}: pool={len(pool)} carrier_topk={served or 'NO'} "
              f"sentinel={'OK' if reps[-1]['sentinel_in_topk'] else 'PERDIDO'}")

    serve_count = sum(r["carrier_in_topk"] for r in reps)
    verdict = "FRONTERA" if serve_count else "MISS-ESTABLE"
    receipt = {
        "probe": "s288c_cat017_serve_rate_v1",
        "qid": QID,
        "git_commit": git,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "route": "retrieve_chunks+_eval_strict_rerank (DEMO_FLAGS pineados por import; "
                 "target_models=None; espejo factlevel_assessment.py:366-378)",
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "rerank_top_k": RERANK_TOP_K,
        "targets": list(TARGETS),
        "reps": reps,
        "serve_count": serve_count,
        "n": args.reps,
        "verdict": verdict,
        "decision_rule": "0/N => miss estable (mecanismo procede); >=1/N => frontera "
                         "(pieza 3 pierde justificacion)",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nserve-rate: {serve_count}/{args.reps} -> {verdict}\n-> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
