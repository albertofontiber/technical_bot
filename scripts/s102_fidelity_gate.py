#!/usr/bin/env python3
"""s102_fidelity_gate.py — gate bvg de NO-REGRESIÓN del fidelity-block (D6, Alberto OK 8-jul).

El fact-level ya midió +3/0 (evals/s101_fidelity_measure.yaml); este gate añade el eje PASS
holístico ANTES del ship a demo (patrón s99_width_noregr/DEC-092b: vara justa = path LIVE
servido-a-síntesis, K=3, juez GPT-5.5 canónico reusado, mayoría-si-no-peor-gana).

Brazos (misma pipe top-10@3500 por gold, rerank UNA vez compartido → aísla GENERACIÓN):
  ctrl  = GENERATOR_PROMPT_VARIANT=base   (demo actual)
  treat = GENERATOR_PROMPT_VARIANT=fidelity
Población (del K5 vigente s99 + rescatados fact-level):
  PASS-población (12): regresión = ctrl PASS → treat ≠PASS. REGLA DEC-092b: toda "regresión"
  se VERIFICA leyendo las respuestas antes de declararla real (el juez confunde más-info-correcta
  con dilución). PARCIAL (8) + rescued-fact-level (hp002/hp006/hp010): upside a nivel PASS.
Eje invención: descansa en el fact-level (contradicted no subió, 0 regresiones, bloque con
anti-sobre-alcance) — este gate NO lo re-mide.
GATE = 0 regresiones REALES estables → ship (Railway GENERATOR_PROMPT_VARIANT=fidelity).
Coste estimado: 23 golds × 2 brazos × K=3 = 138 gens Sonnet + 138 juicios GPT ≈ $8-12.

Uso: python scripts/s102_fidelity_gate.py
Salida: evals/s102_fidelity_gate.json
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
        "HYQ_PILOT_FILE": "", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "GENERATOR_PROMPT_VARIANT": "base"}
for k, v in DEMO.items():
    os.environ[k] = v
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)
for k, v in DEMO.items():
    os.environ[k] = v
import json  # noqa: E402
import yaml  # noqa: E402
import src.rag.generator as GEN  # noqa: E402
from src.rag.retriever import retrieve_chunks, extract_product_models  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from bvg_kmajority import _judge_one  # noqa: E402  (juez canónico reusado)

OUT = ROOT / "evals" / "s102_fidelity_gate.json"
# Del K5 vigente (evals/s99_width_noregr_K5.json@980fa60, brazo treat = demo actual t10@3500):
PASS_POP = ["cat013", "cat014", "cat018", "cat021", "cat022", "hp001", "hp004", "hp015",
            "hp019", "hp020", "cat012", "cat020"]
PARCIAL = ["cat005", "cat009", "cat015", "cat023", "hp013", "cat019", "cat024", "hp007"]
RESCUED_FL = ["hp002", "hp006", "hp010"]   # los +3 del fact-level (upside a nivel PASS)
K = 3
ARMS = ("ctrl", "treat")


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
    print(f"gate fidelity: {len(qids)} golds × 2 brazos × K={K} (juez canónico)", flush=True)

    # 1) pipe LIVE una vez por gold (compartida por brazos)
    pre = {}
    for qid in qids:
        q = golds[qid]["question"]
        pool = retrieve_chunks(q, top_k=50)
        tm = extract_product_models(q) or None
        pre[qid] = rerank_chunks(q, pool, top_k=10, target_models=tm)
        print(f"  pipe {qid} (top-{len(pre[qid])})", flush=True)

    # 2) generar K por brazo (flag por env, leído en runtime por _assemble_system)
    gens = {qid: {a: [] for a in ARMS} for qid in qids}
    for arm, variant in (("ctrl", "base"), ("treat", "fidelity")):
        os.environ["GENERATOR_PROMPT_VARIANT"] = variant
        for qid in qids:
            for _ in range(K):
                r = GEN.generate_answer(golds[qid]["question"], pre[qid], available_models=None)
                gens[qid][arm].append({"answer": r.get("answer") or "", "stop": r.get("stop_reason"),
                                       "len": len(r.get("answer") or "")})
        print(f"  generado brazo {arm} ({variant})", flush=True)
    os.environ["GENERATOR_PROMPT_VARIANT"] = "base"

    # 3) juez canónico (paralelo)
    tasks = []
    for qid in qids:
        g = golds[qid]
        for arm in ARMS:
            for i, gg in enumerate(gens[qid][arm]):
                tasks.append(((qid, arm, i), g["question"], g.get("conducta_esperada", "answer"),
                              g.get("gold_answer", ""), gg["answer"]))
    verdicts = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_judge_one, (t[0], 0, t[1], t[2], t[3], t[4])): t[0] for t in tasks}
        for fut in as_completed(futs):
            key, _, row = fut.result()
            verdicts[key] = row.get("veredicto", "?")

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
               "ctrl": cell["ctrl"], "treat": cell["treat"],
               "len_ctrl": int(lc), "len_treat": int(lt),
               "dlen_pct": int((lt - lc) / max(lc, 1) * 100),
               "answers_treat": [x["answer"] for x in gens[qid]["treat"]],
               "answers_ctrl": [x["answer"] for x in gens[qid]["ctrl"]]}
        rows.append(row)
        if row["ctrl"] == "PASS" and row["treat"] != "PASS":
            regr.append({k: row[k] for k in ("qid", "pop", "ctrl", "treat")})
        if row["ctrl"] != "PASS" and row["treat"] == "PASS":
            gains.append(row["qid"])
    json.dump({"design": "ctrl=base vs treat=fidelity · pipe compartida t10@3500 · K=3 · juez canónico",
               "rows": rows, "regresiones_a_verificar": regr, "gains": gains, "truncados": trunc},
              OUT.open("w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== GATE fidelity (ctrl=base vs treat=fidelity, ambos t10@3500) ===")
    print(f"{'gold':8} {'pop':10} {'ctrl':8} {'treat':8} {'Δlen%':>6}")
    for r in rows:
        flag = ("  ⚠REGRESA(verificar)" if any(x["qid"] == r["qid"] for x in regr)
                else ("  ✓+PASS" if r["qid"] in gains else ""))
        print(f"{r['qid']:8} {r['pop']:10} {r['ctrl']:8} {r['treat']:8} {r['dlen_pct']:>5}%{flag}")
    print(f"\nREGRESIONES a VERIFICAR leyendo respuestas (DEC-092b): {[r['qid'] for r in regr] or 'NINGUNA'}")
    print(f"GAINS PASS: {gains or 'ninguno'} · TRUNCADOS: {trunc or 'ninguno'}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
