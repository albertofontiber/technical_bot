#!/usr/bin/env python3
"""s102_hyq_bvg_gate.py — gate bvg de NO-REGRESIÓN del canal hyq-tabla (mecánica v2), pre-activación.

Patrón s102_fidelity_gate/DEC-092b (path LIVE, K=3, juez GPT-5.5 canónico, mayoría-si-no-peor)
con el TRATAMIENTO a nivel POOL (no generador):
  ctrl  = HYQ_TABLE off (demo actual)
  treat = HYQ_TABLE on  (tabla + family-parity nivel-fila + carve-out — gate flips 2/2 PASADO)
Ambos brazos con GENERATOR_PROMPT_VARIANT=fidelity (el estado shipped de la demo, DEC-098).

A diferencia del fidelity-gate, la pipe NO puede compartirse (el pool ES el tratamiento) →
el ruido del rerank (DEC-096b) entra en ambos brazos. Controles:
  · PAIRING POR POOL (precedente s63-R1): si el pool-50 ON es IDÉNTICO al OFF (el canal no
    disparó o no cambió nada), el brazo treat COMPARTE pipe y gens del ctrl → delta:=0 por
    diseño. Solo los golds con pool cambiado pagan doble y aportan señal.
  · Toda regresión PASS→no-PASS se VERIFICA leyendo las respuestas (DEC-092b) antes de
    declararla real; ambigua → replay OFF-vs-OFF del gold (norma DEC-096).
GATE = 0 regresiones REALES estables → paquete a Alberto para HYQ_TABLE=on en Railway.
Coste estimado (peor caso, 0 pools compartidos): 23×2 pipes + 138 gens + 138 juicios ≈ $10-15;
con pooles compartidos baja proporcionalmente.

Uso: python scripts/s102_hyq_bvg_gate.py
Salida: evals/s102_hyq_bvg_gate.json
"""
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
DEMO = {"CHUNKS_TABLE": "chunks_v2", "HYDE_ENABLED": "false", "ENUNCIADOS_MULTIVECTOR": "on",
        "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "add", "DIVERSIFY_TIEBREAK": "off",
        "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "GENERATOR_PROMPT_VARIANT": "fidelity"}
for k, v in DEMO.items():
    os.environ[k] = v
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)
for k, v in DEMO.items():
    os.environ[k] = v
import json  # noqa: E402
import yaml  # noqa: E402
import src.rag.generator as GEN  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from bvg_kmajority import _judge_one  # noqa: E402  (juez canónico reusado)

assert R.HYQ_TABLE_ON is False and not R.HYQ_PILOT_FILE
assert os.environ["GENERATOR_PROMPT_VARIANT"] == "fidelity"

OUT = ROOT / "evals" / "s102_hyq_bvg_gate.json"
# Misma población que el fidelity-gate (K5 vigente s99 + rescatados fact-level):
PASS_POP = ["cat013", "cat014", "cat018", "cat021", "cat022", "hp001", "hp004", "hp015",
            "hp019", "hp020", "cat012", "cat020"]
PARCIAL = ["cat005", "cat009", "cat015", "cat023", "hp013", "cat019", "cat024", "hp007"]
RESCUED_FL = ["hp002", "hp006", "hp010"]
K = 3
ARMS = ("ctrl", "treat")


def _pool(q, table_on: bool):
    R.HYQ_TABLE_ON = table_on
    try:
        return retrieve_chunks(q, top_k=50)
    finally:
        R.HYQ_TABLE_ON = False


def _agg(vs):
    c = Counter(v for v in vs if v in ("PASS", "PARCIAL", "FALLO"))
    if not c:
        return "?"
    for v, n in c.items():
        if n >= 2:
            return v
    for v in ("FALLO", "PARCIAL", "PASS"):   # sin mayoría → peor-gana (regla bvg, anti-optimista)
        if c.get(v):
            return v
    return "?"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    golds = {g["qid"]: g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))}
    qids = [q for q in PASS_POP + PARCIAL + RESCUED_FL if q in golds]
    print(f"gate bvg hyq: {len(qids)} golds × 2 brazos × K={K} (pairing por pool, juez canónico)", flush=True)

    # 1) pools por brazo + pairing (pool idéntico → treat comparte pipe y gens)
    pre, shared = {}, {}
    n_hyq_fired = 0
    for qid in qids:
        q = golds[qid]["question"]
        pool_off = _pool(q, False)
        pool_on = _pool(q, True)
        ids_off = [c.get("id") for c in pool_off]
        ids_on = [c.get("id") for c in pool_on]
        n_hyq = sum(1 for c in pool_on if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        n_hyq_fired += bool(n_hyq)
        shared[qid] = ids_off == ids_on
        tm = extract_product_models(q) or None
        pre[qid] = {"ctrl": rerank_chunks(q, pool_off, top_k=10, target_models=tm)}
        pre[qid]["treat"] = (pre[qid]["ctrl"] if shared[qid]
                             else rerank_chunks(q, pool_on, top_k=10, target_models=tm))
        print(f"  pipe {qid}: pool {'IDÉNTICO (paired, delta:=0)' if shared[qid] else 'CAMBIADO'}"
              f" · hyq_on={n_hyq}", flush=True)
    # H3 observabilidad: el canal debe disparar en ALGÚN gold del set
    assert n_hyq_fired > 0, "hyq-table no disparó en ningún gold — flag/RPC roto, gate inválido"

    # 2) generar K por brazo (golds paired: treat copia las gens del ctrl — delta 0 por diseño)
    gens = {qid: {a: [] for a in ARMS} for qid in qids}
    for qid in qids:
        for _ in range(K):
            r = GEN.generate_answer(golds[qid]["question"], pre[qid]["ctrl"], available_models=None)
            gens[qid]["ctrl"].append({"answer": r.get("answer") or "", "stop": r.get("stop_reason"),
                                      "len": len(r.get("answer") or "")})
        if shared[qid]:
            gens[qid]["treat"] = gens[qid]["ctrl"]
        else:
            for _ in range(K):
                r = GEN.generate_answer(golds[qid]["question"], pre[qid]["treat"], available_models=None)
                gens[qid]["treat"].append({"answer": r.get("answer") or "", "stop": r.get("stop_reason"),
                                           "len": len(r.get("answer") or "")})
        print(f"  gens {qid} ({'paired' if shared[qid] else '2 brazos'})", flush=True)

    # 3) juez canónico (paralelo; golds paired: juzgar solo ctrl y copiar)
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
                verdicts[(qid, "treat", i)] = verdicts.get((qid, "ctrl", i), "?")

    # 4) agregar + reportar
    rows, regr, gains, trunc = [], [], [], []
    for qid in qids:
        cell = {a: _agg([verdicts.get((qid, a, i), "?") for i in range(K)]) for a in ARMS}
        for a in ARMS:
            if any(x["stop"] == "max_tokens" for x in gens[qid][a]):
                trunc.append((qid, a))
        lc = sum(x["len"] for x in gens[qid]["ctrl"]) / K
        lt = sum(x["len"] for x in gens[qid]["treat"]) / K
        row = {"qid": qid,
               "pop": ("PASS" if qid in PASS_POP else "PARCIAL" if qid in PARCIAL else "RESCUED_FL"),
               "pool_paired": bool(shared[qid]),
               "ctrl": cell["ctrl"], "treat": cell["treat"],
               "len_ctrl": int(lc), "len_treat": int(lt),
               "dlen_pct": int((lt - lc) / max(lc, 1) * 100),
               "answers_treat": [x["answer"] for x in gens[qid]["treat"]],
               "answers_ctrl": [x["answer"] for x in gens[qid]["ctrl"]]}
        rows.append(row)
        if row["ctrl"] == "PASS" and row["treat"] != "PASS":
            regr.append({k: row[k] for k in ("qid", "pop", "ctrl", "treat", "pool_paired")})
        if row["ctrl"] != "PASS" and row["treat"] == "PASS":
            gains.append(row["qid"])
    n_paired = sum(1 for q in qids if shared[q])
    json.dump({"design": "ctrl=HYQ off vs treat=HYQ_TABLE on (v2) · fidelity ambos · K=3 · "
                         "pairing por pool (s63-R1) · juez canónico",
               "n_paired": n_paired, "rows": rows, "regresiones_a_verificar": regr,
               "gains": gains, "truncados": trunc},
              OUT.open("w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n=== GATE bvg hyq (ctrl=off vs treat=tabla-v2; paired {n_paired}/{len(qids)}) ===")
    print(f"{'gold':8} {'pop':10} {'pair':5} {'ctrl':8} {'treat':8} {'Δlen%':>6}")
    for r in rows:
        flag = ("  ⚠REGRESA(verificar)" if any(x["qid"] == r["qid"] for x in regr)
                else ("  ✓+PASS" if r["qid"] in gains else ""))
        print(f"{r['qid']:8} {r['pop']:10} {'=' if r['pool_paired'] else '≠':5} "
              f"{r['ctrl']:8} {r['treat']:8} {r['dlen_pct']:>5}%{flag}")
    print(f"\nREGRESIONES a VERIFICAR leyendo respuestas (DEC-092b): {[r['qid'] for r in regr] or 'NINGUNA'}")
    print(f"GAINS PASS: {gains or 'ninguno'} · TRUNCADOS: {trunc or 'ninguno'}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
