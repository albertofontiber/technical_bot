#!/usr/bin/env python3
"""s101_fidelity_measure.py — A/B fact-level del prompt de completitud (GENERATOR_PROMPT_VARIANT=fidelity).

MÉTRICA NUEVA vs DEC-051 (que midió este seam en PASS holístico → NO-GO Δ_net=0, pre-NOCAT):
aquí = conveyed A NIVEL-HECHO con el árbitro dual del instrumento canónico (GPT-5.5 K=5 → si miss,
Opus 4.8 K=5). El "settled" de DEC-051 tiene métrica PASS → NO zanja fact-level (Protocolo 4).

Diseño:
- Población: los golds con synthesis-miss del full v2 (evals/s100_factlevel_full.yaml).
- Por gold: UNA pipe pineada (retrieve→rerank(top-10)) compartida por ambos brazos → aísla GENERACIÓN.
- Brazo base ×1 gen · brazo fidelity ×2 gens (anti-varianza: hp013-EEPROM demostró omisión intermitente;
  miss-fidelity = miss en AMBAS gens, espejo del stability del instrumento).
- Se juzgan TODOS los core-facts del gold en cada respuesta (rescate Y regresión, mismos umbrales).
- GUARDIA de invención: los `contradicted` no deben SUBIR en fidelity (el bloque tiene anti-sobre-alcance).
- Flags demo exportados; HYQ off; tiebreak off. smoke = 3 golds primero (coste).

GO del lever = reducción del bucket synthesis-miss (rescued>regressed con margen) → luego dúo + gate
bvg antes de cualquier ship (esta noche NO se shipea nada).

Uso: python scripts/s101_fidelity_measure.py {smoke|full}
Salida: evals/s101_fidelity_measure.yaml (+ tratamiento estampado)
"""
from __future__ import annotations
import os

DEMO = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": "", "DIVERSIFY_TIEBREAK": "off"}
for _k, _v in DEMO.items():
    os.environ[_k] = _v
os.environ["GENERATOR_PROMPT_VARIANT"] = "base"

import sys, json, time, hashlib
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
for _k, _v in DEMO.items():
    os.environ[_k] = _v

import yaml
from src.rag.retriever import retrieve_chunks
from src.rag.reranker import rerank
from src.rag.generator import generate_answer, RELEVANCE_THRESHOLD, _assemble_system, _FIDELITY_BLOCK
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K
from scripts.factlevel_assessment import judge_conveyed_dual, _sha
from scripts.synthesis_miss_judge import judge_conveyed
from scripts.retrieval_miss_judge import core_facts, THRESH_FIRM
from scripts.gold_store import get as gs_get

assert RERANK_TOP_K == 10
FULL = ROOT / "evals" / "s100_factlevel_full.yaml"
OUT = ROOT / "evals" / "s101_fidelity_measure.yaml"


def conveyed_dual_verdict(valor, texto, answer, workers=6) -> bool:
    """Árbitro IDÉNTICO al instrumento: GPT K=5; si <4 → Opus K=5; conveyed si cualquiera >=4."""
    c = judge_conveyed(valor, texto, answer, workers=workers)
    if c.get("n_fail", 0) >= 5:
        raise RuntimeError("juez primario muerto")
    if c["yes"] >= THRESH_FIRM:
        return True
    d = judge_conveyed_dual(valor, texto, answer, workers=workers)
    return d["yes"] >= THRESH_FIRM


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    full = yaml.safe_load(FULL.read_text(encoding="utf-8"))
    # golds con >=1 synthesis-miss en el full v2 (la población del lever)
    pop = []
    for r in full["per_gold"]:
        misses = [f["valor"] for f in r["facts"] if f.get("clase") == "synthesis-miss"]
        if misses:
            pop.append((r["qid"], set(misses)))
    if mode == "smoke":
        pop = pop[:3]
    print(f"{mode}: {len(pop)} golds con synth-miss · brazo fidelity ×2 gens · árbitro dual")
    print(f"  fidelity_block_sha={_sha(_FIDELITY_BLOCK)}")
    est_facts = sum(len(core_facts(gs_get(q))) for q, _ in pop)
    print(f"  ~{est_facts} facts × 3 respuestas × K5 (+duales) ≈ {est_facts*3*5*0.004*1.6:.0f}$ aprox")

    results = []
    for qid, miss_set in pop:
        g = gs_get(qid)
        pool = retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        topk = rerank(g["question"], pool, top_k=RERANK_TOP_K, strict=True)
        os.environ["GENERATOR_PROMPT_VARIANT"] = "base"
        ans_base = generate_answer(g["question"], topk).get("answer", "")
        os.environ["GENERATOR_PROMPT_VARIANT"] = "fidelity"
        ans_f1 = generate_answer(g["question"], topk).get("answer", "")
        ans_f2 = generate_answer(g["question"], topk).get("answer", "")
        os.environ["GENERATOR_PROMPT_VARIANT"] = "base"

        gold_rows = []
        for f in core_facts(g):
            valor = f.get("valor", ""); texto = (f.get("texto") or "").strip()
            b = conveyed_dual_verdict(valor, texto, ans_base)
            f1 = conveyed_dual_verdict(valor, texto, ans_f1)
            f2 = f1 if f1 else conveyed_dual_verdict(valor, texto, ans_f2)  # fid-conveyed si CUALQUIER gen
            fid = f1 or f2
            status = ("rescued" if (not b and fid) else
                      "regressed" if (b and not fid) else
                      "still-miss" if (not b and not fid) else "ok-both")
            gold_rows.append({"valor": valor, "base": b, "fidelity": fid, "status": status,
                              "was_miss_fullv2": valor in miss_set})
        results.append({"qid": qid, "facts": gold_rows,
                        "len_base": len(ans_base), "len_fid": len(ans_f1)})
        resc = sum(1 for x in gold_rows if x["status"] == "rescued")
        regr = sum(1 for x in gold_rows if x["status"] == "regressed")
        print(f"  [{qid}] rescued={resc} regressed={regr} "
              f"still-miss={sum(1 for x in gold_rows if x['status']=='still-miss')} "
              f"len {results[-1]['len_base']}→{results[-1]['len_fid']}")

    agg = {"rescued": 0, "regressed": 0, "still-miss": 0, "ok-both": 0}
    for r in results:
        for x in r["facts"]:
            agg[x["status"]] += 1
    print(f"\n── A/B fidelity fact-level ── {agg}")
    print(f"  NETO synthesis-miss: {agg['rescued']} rescatados − {agg['regressed']} regresiones")
    OUT.write_text(yaml.safe_dump({
        "treatment": {"seam": "GENERATOR_PROMPT_VARIANT=fidelity (s69, dúo-hardened)",
                      "block_sha": _sha(_FIDELITY_BLOCK), "gens_fidelity": 2,
                      "metric": "conveyed fact-level árbitro dual (≠ DEC-051 PASS)"},
        "demo_flags": DEMO, "mode": mode, "aggregate": agg, "results": results,
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"→ {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
