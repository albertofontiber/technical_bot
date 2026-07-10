#!/usr/bin/env python3
"""s103_landing_bvg_gate.py — DISCRIMINANTE 2 (outcome) del landing v3.1: bvg K=3 old-vs-v3.

Clon del patrón s102_hyq_bvg_gate (path LIVE, K=3, juez GPT-5.5 canónico, mayoría-si-no-peor,
pairing-por-pool, regresiones LEÍDAS antes de declararse — DEC-092b) con los brazos del LANDING:
  ctrl  = pools del carve-out s102 (dump worktree@ae624cd, `evals/s103_pools_old.jsonl`)
  treat = pools v3.1 live (extensión acotada del aside), canal HYQ ON en AMBOS brazos.
El tratamiento es el LANDING (dónde aterriza el coste de la cuota), no el canal.
G3: se estampa la latencia del rerank por brazo (input 50 vs ≤60).

GATE = 0 regresiones REALES estables (leer respuestas de toda PASS→peor antes de declarar).
Coste ≈ $25-35 (≈31 golds con pool cambiado × 2 brazos × K=3 gens + juez).
Uso: python scripts/s103_landing_bvg_gate.py
Salida: evals/s103_landing_bvg_gate.json
"""
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
DEMO = {"CHUNKS_TABLE": "chunks_v2", "HYDE_ENABLED": "false", "ENUNCIADOS_MULTIVECTOR": "on",
        "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "add", "DIVERSIFY_TIEBREAK": "off",
        "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "GENERATOR_PROMPT_VARIANT": "fidelity"}
for k, v in DEMO.items():
    os.environ[k] = v
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)
for k, v in DEMO.items():
    os.environ[k] = v
import json  # noqa: E402
import subprocess  # noqa: E402
import yaml  # noqa: E402
import src.rag.generator as GEN  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from bvg_kmajority import _judge_one  # noqa: E402

assert R.HYQ_TABLE_ON is False and not R.HYQ_PILOT_FILE
assert os.environ["GENERATOR_PROMPT_VARIANT"] == "fidelity"

OUT = ROOT / "evals" / "s103_landing_bvg_gate.json"
# Misma población que el gate del ship del canal (s102): PASS/PARCIAL vigentes + rescatados.
PASS_POP = ["cat013", "cat014", "cat018", "cat021", "cat022", "hp001", "hp004", "hp015",
            "hp019", "hp020", "cat012", "cat020"]
PARCIAL = ["cat005", "cat009", "cat015", "cat023", "hp013", "cat019", "cat024", "hp007"]
RESCUED_FL = ["hp002", "hp006", "hp010"]
K = 3
ARMS = ("ctrl", "treat")


def _agg(vs):
    c = Counter(v for v in vs if v in ("PASS", "PARCIAL", "FALLO"))
    if not c:
        return "?"
    for v, n in c.items():
        if n >= 2:
            return v
    for v in ("FALLO", "PARCIAL", "PASS"):
        if c.get(v):
            return v
    return "?"


RANK = {"PASS": 2, "PARCIAL": 1, "FALLO": 0, "?": -1}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    golds = {g["qid"]: g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))}
    old_pools: dict[str, list] = {}
    with open(ROOT / "evals" / "s103_pools_old.jsonl", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if "qid" in row:
                old_pools[row["qid"]] = row["chunks"]
    qids = [q for q in PASS_POP + PARCIAL + RESCUED_FL if q in golds and q in old_pools]
    print(f"gate bvg landing v3.1: {len(qids)} golds × 2 brazos × K={K} "
          f"(ctrl=old-pools dump · treat=v3.1 live · HYQ ON ambos)", flush=True)

    pre, shared, lat = {}, {}, {"ctrl": [], "treat": []}
    n_fired = 0
    for qid in qids:
        q = golds[qid]["question"]
        pool_old = old_pools[qid]
        R.HYQ_TABLE_ON = True
        try:
            pool_v3 = retrieve_chunks(q, top_k=50)
        finally:
            R.HYQ_TABLE_ON = False
        n_hyq = sum(1 for c in pool_v3 if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        n_fired += bool(n_hyq)
        shared[qid] = [c.get("id") for c in pool_old] == [c.get("id") for c in pool_v3]
        tm = extract_product_models(q) or None
        t0 = time.perf_counter()
        pre[qid] = {"ctrl": rerank_chunks(q, [dict(c) for c in pool_old], top_k=10,
                                          target_models=tm)}
        lat["ctrl"].append(time.perf_counter() - t0)
        if shared[qid]:
            pre[qid]["treat"] = pre[qid]["ctrl"]
        else:
            t0 = time.perf_counter()
            pre[qid]["treat"] = rerank_chunks(q, [dict(c) for c in pool_v3], top_k=10,
                                              target_models=tm)
            lat["treat"].append(time.perf_counter() - t0)
        print(f"  pipe {qid}: {'IDÉNTICO (paired)' if shared[qid] else 'CAMBIADO'} · "
              f"hyq_on={n_hyq} · pool_v3={len(pool_v3)}", flush=True)
    assert n_fired > 0, "hyq no disparó en ningún gold — gate inválido (H3)"

    gens = {qid: {a: [] for a in ARMS} for qid in qids}
    for qid in qids:
        for _ in range(K):
            r = GEN.generate_answer(golds[qid]["question"], pre[qid]["ctrl"], available_models=None)
            gens[qid]["ctrl"].append({"answer": r.get("answer") or "", "len": len(r.get("answer") or "")})
        if shared[qid]:
            gens[qid]["treat"] = gens[qid]["ctrl"]
        else:
            for _ in range(K):
                r = GEN.generate_answer(golds[qid]["question"], pre[qid]["treat"], available_models=None)
                gens[qid]["treat"].append({"answer": r.get("answer") or "", "len": len(r.get("answer") or "")})
        print(f"  gens {qid} ({'paired' if shared[qid] else '2 brazos'})", flush=True)

    tasks = []
    for qid in qids:
        g = golds[qid]
        arms = ("ctrl",) if shared[qid] else ARMS
        for arm in arms:
            for i, gg in enumerate(gens[qid][arm]):
                tasks.append(((qid, arm, i), g["question"], g.get("conducta_esperada", "answer"),
                              g.get("gold_answer", ""), gg["answer"]))
    verdicts = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_judge_one, (t[0], 0, t[1], t[2], t[3], t[4])): t[0] for t in tasks}
        for fut in as_completed(futs):
            key, _, row = fut.result()
            verdicts[key] = row.get("veredicto", "?")
    for qid in qids:
        if shared[qid]:
            for i in range(K):
                verdicts[(qid, "treat", i)] = verdicts[(qid, "ctrl", i)]

    rows, regressions, gains = [], [], []
    for qid in qids:
        vc = _agg([verdicts.get((qid, "ctrl", i), "?") for i in range(K)])
        vt = _agg([verdicts.get((qid, "treat", i), "?") for i in range(K)])
        rows.append({"qid": qid, "shared": shared[qid], "ctrl": vc, "treat": vt,
                     "k_ctrl": [verdicts.get((qid, "ctrl", i), "?") for i in range(K)],
                     "k_treat": [verdicts.get((qid, "treat", i), "?") for i in range(K)],
                     "answers_treat": [g["answer"][:600] for g in gens[qid]["treat"]],
                     "answers_ctrl": [g["answer"][:600] for g in gens[qid]["ctrl"]]})
        if RANK[vt] < RANK[vc]:
            regressions.append({"qid": qid, "ctrl": vc, "treat": vt})
        elif RANK[vt] > RANK[vc]:
            gains.append({"qid": qid, "ctrl": vc, "treat": vt})
        m = "⬇ REGRESIÓN (leer)" if RANK[vt] < RANK[vc] else ("⬆ GAIN" if RANK[vt] > RANK[vc] else "=")
        print(f"  {qid:8s} ctrl={vc:8s} treat={vt:8s} {m}", flush=True)

    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731
    print(f"\n── BVG landing v3.1 (old-vs-v3, K={K}, mayoría-si-no-peor) ──")
    print(f"  regresiones (a LEER antes de declarar): {[r['qid'] for r in regressions]}")
    print(f"  gains: {[r['qid'] for r in gains]}")
    print(f"  latencia rerank mediana: ctrl={med(lat['ctrl']):.2f}s treat={med(lat['treat']):.2f}s"
          if lat["treat"] else "  latencia: sin brazos treat separados")
    json.dump({"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                                   capture_output=True).stdout.decode().strip(),
                         "flags": {**DEMO, "HYQ_TABLE": "on (ambos brazos, call-time)"},
                         "ctrl_pools": "evals/s103_pools_old.jsonl (worktree@ae624cd)"},
               "rows": rows, "regressions": regressions, "gains": gains,
               "lat_rerank_median_s": {"ctrl": med(lat["ctrl"]), "treat": med(lat["treat"])}},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
