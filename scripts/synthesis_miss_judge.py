#!/usr/bin/env python3
"""synthesis_miss_judge.py (s87) — instrumento de diagnóstico del CUELLO=SÍNTESIS.

Convierte el «103 SÍNTESIS» (hechos CORE soportados por un chunk del top-5 = *sintetizables*,
DEC-070/073) en FALLOS DE SÍNTESIS REALES (el hecho llega al generador pero la RESPUESTA no lo
transmite), con mecanismo. Diseño dúo-hardened (brief evals/s87_synthesis_instrument_brief.md):

  reaches_gen = support_ids(votos≥4, de DEF) ∩ fresh_ctx_ids(top5 post-RELEVANCE_THRESHOLD) ≠ ∅
  judge_B     = «¿la RESPUESTA afirma el HECHO (valor «{valor}» EN la relación «{texto}»)?» GPT-5.5 K=5
  clase       = NOT-IN-CTX (reaches_gen False) / SYNTH-OK (conveyed) / SYNTH-MISS (omitido)

Semilla = evals/s85_retrieval_miss_DEF.yaml (pins poblados: top5_ids/pool_pin/votes). Join hecho→texto
POR POSICIÓN (measure_gold itera core_facts en orden → DEF.facts[i] ↔ gold.core_facts[i]).

NADA en prod. reach≠PASS. Headline verdict-INDEPENDIENTE (omitted-in-answer); verdict = lente 2ª caveada.

Modos:
  python scripts/synthesis_miss_judge.py subset --qids hp007,cat007   # valida juez+coste
  python scripts/synthesis_miss_judge.py full
Salida: evals/s87_synthesis_<mode>.yaml (+ .partial.jsonl resumible) + manifest.
"""
from __future__ import annotations
import os
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("HYDE_ENABLED", "false")
import sys, json, time, hashlib, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"; os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import yaml
from openai import OpenAI
from src.rag.retriever import retrieve_chunks
from src.rag.reranker import rerank
from src.rag.generator import generate_answer, RELEVANCE_THRESHOLD
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K, LLM_MODEL, RERANKER_BACKEND
from scripts.retrieval_miss_judge import core_facts, load_dev

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
SEED = ROOT / "evals" / "s85_retrieval_miss_DEF.yaml"
JUDGE_MODEL = "gpt-5.5"
K = 5
THRESH_FIRM = 4          # ≥4/5 = CONVEYED firme (estricto: sobre-acreditar desinfla synthesis-miss)
THRESH_BAND = 3          # 2-3/5 = borderline (revisión manual)
VOTE_SUPPORT = 4         # votos≥4 en DEF = chunk-soporte del hecho

# ── juez_B: FACT-in-answer a nivel PROPOSICIÓN (cross-model finding 3: no valor-suelto) ──
JUDGE_SYS = (
    "Eres un evaluador EXPERTO en manuales técnicos de PCI. Decides, con rigor literal, si una "
    "RESPUESTA técnica AFIRMA un HECHO concreto. El hecho = un VALOR en una RELACIÓN específica "
    "(qué componente/condición/periodicidad). ES/EN mezclados y OCR imperfecto son normales: juzga "
    "el SIGNIFICADO. Eres ESTRICTO: el valor debe estar afirmado EN SU RELACIÓN, no suelto ni "
    "asociado a otra cosa. Marcar 'afirmado' cuando no lo está (o está en relación distinta) es el peor error."
)
JUDGE_USER = (
    "HECHO a verificar:\n"
    "  · VALOR: «{valor}»\n"
    "  · RELACIÓN (de qué trata el hecho): {texto}\n\n"
    "RESPUESTA del asistente:\n<<<\n{answer}\n>>>\n\n"
    "¿La RESPUESTA AFIRMA o IMPLICA DIRECTAMENTE el HECHO — es decir, transmite el VALOR «{valor}» "
    "EN esa RELACIÓN? Marca 'sí' SÓLO si el valor concreto aparece atribuido a la relación correcta "
    "(admite traducción ES↔EN, paráfrasis y OCR). Marca 'no' si: el valor no aparece, aparece pero "
    "en OTRA relación/condición/periodicidad/componente, la respuesta se escuda ('el manual no "
    "especifica…') o afirma un valor DISTINTO. Ante la duda, 'no'.\n"
    'Responde EXCLUSIVAMENTE JSON: {{"afirmado": true|false}}.'
)
_sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _judge_once(valor: str, texto: str, answer: str) -> int | None:
    """1 voto GPT-5.5 → 1 (afirmado) / 0 (no) / None (fallo de API tras retries = voto inválido)."""
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for attempt in range(4):
        try:
            resp = oai.chat.completions.create(
                model=JUDGE_MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": JUDGE_SYS},
                          {"role": "user", "content": JUDGE_USER.format(
                              valor=valor, texto=(texto or "")[:600], answer=(answer or "")[:6000])}],
            )
            out = json.loads(resp.choices[0].message.content.strip())
            return 1 if bool(out.get("afirmado")) else 0
        except Exception:
            time.sleep(2 ** attempt)
    return None


def judge_conveyed(valor: str, texto: str, answer: str, workers: int = 6) -> dict:
    """K votos → {'yes': n, 'n_fail': m}. conveyed firme = yes≥THRESH_FIRM."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = [f.result() for f in [pool.submit(_judge_once, valor, texto, answer) for _ in range(K)]]
    yes = sum(1 for v in votes if v == 1)
    n_fail = sum(1 for v in votes if v is None)
    return {"yes": yes, "n_fail": n_fail}


# ── semilla DEF: por gold, hechos SÍNTESIS (by_target) con su texto (join por POSICIÓN) + support_ids ──
def load_seed() -> dict:
    dev = {g["qid"]: g for g in load_dev()}
    def_data = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    res = def_data["reps"][0]["results"]
    seed = {}
    for r in res:
        qid = r["qid"]
        gold = dev[qid]
        cf = core_facts(gold)
        assert len(cf) == len(r["facts"]), f"{qid}: DEF facts {len(r['facts'])} != core_facts {len(cf)}"
        synth = []
        for gf, df in zip(cf, r["facts"]):
            if df["bucket_target"] != "SINTESIS":
                continue
            support = sorted([cid for cid, v in (df.get("votes") or {}).items() if v >= VOTE_SUPPORT])
            synth.append({"valor": df["valor"], "texto": (gf.get("texto") or "").strip(),
                          "support_ids": support, "in_top5_target": df.get("in_top5_target")})
        if synth:
            seed[qid] = {"gold": gold, "synth": synth, "def_top5_ids": r.get("top5_ids") or []}
    return seed


# ── generación FIEL a prod + captura del contexto POST-umbral (dúo CRÍTICO) ──
def run_pipeline(question: str) -> dict:
    """retrieve(50) → rerank(top5, strict=True) → generate. Devuelve answer + fresh_ctx_ids
    (chunks que sobreviven similarity≥RELEVANCE_THRESHOLD = los que VE el generador, generator.py:402)
    + fresh_top5_ids (para QA de solape con DEF)."""
    pool = retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)
    top5 = rerank(question, pool, top_k=RERANK_TOP_K, strict=True)
    fresh_top5_ids = [c.get("id") for c in top5]
    ctx_ids = [c.get("id") for c in top5 if c.get("similarity", 0) >= RELEVANCE_THRESHOLD]
    res = generate_answer(question, top5)   # available_models=None (contrato de fidelidad, harness:107)
    return {"answer": res.get("answer", ""), "fresh_ctx_ids": ctx_ids,
            "fresh_top5_ids": fresh_top5_ids, "pool_n": len(pool)}


def classify(reaches_gen: bool, yes: int) -> str:
    if not reaches_gen:
        return "NOT-IN-CTX"
    if yes >= THRESH_FIRM:
        return "SYNTH-OK"
    return "SYNTH-MISS"


def measure_gold(qid: str, s: dict, workers: int) -> dict:
    gold = s["gold"]
    pipe = run_pipeline(gold["question"])
    ctx = set(pipe["fresh_ctx_ids"])
    facts_out = []
    for f in s["synth"]:
        reaches = bool(set(f["support_ids"]) & ctx)
        j = judge_conveyed(f["valor"], f["texto"], pipe["answer"], workers=workers)
        facts_out.append({
            "valor": f["valor"], "texto": f["texto"],
            "reaches_gen": reaches, "yes": j["yes"], "n_fail": j["n_fail"],
            "borderline": THRESH_BAND <= j["yes"] < THRESH_FIRM,
            "clase": classify(reaches, j["yes"]),
            "support_ids": f["support_ids"],
        })
    overlap = len(set(pipe["fresh_top5_ids"]) & set(s["def_top5_ids"]))
    return {"qid": qid, "answer": pipe["answer"], "pool_n": pipe["pool_n"],
            "fresh_ctx_ids": pipe["fresh_ctx_ids"], "fresh_top5_ids": pipe["fresh_top5_ids"],
            "def_top5_ids": s["def_top5_ids"], "top5_overlap": f"{overlap}/5",
            "facts": facts_out}


def manifest(extra: dict) -> dict:
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"instrument": "synthesis_miss_judge", "judge_model": JUDGE_MODEL, "K": K,
            "thresh_firm": THRESH_FIRM, "vote_support": VOTE_SUPPORT,
            "relevance_threshold": RELEVANCE_THRESHOLD, "gen_model": LLM_MODEL,
            "reranker": RERANKER_BACKEND, "retrieval_top_k": RETRIEVAL_TOP_K, "rerank_top_k": RERANK_TOP_K,
            "judge_sys_sha": _sha(JUDGE_SYS), "judge_user_sha": _sha(JUDGE_USER),
            "chunks_table": os.environ["CHUNKS_TABLE"], "hyde": os.environ["HYDE_ENABLED"],
            "seed": "s85_retrieval_miss_DEF.yaml", "git_commit": commit, **extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["subset", "full"])
    ap.add_argument("--qids", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    seed = load_seed()
    if args.qids:
        qids = [q.strip() for q in args.qids.split(",") if q.strip()]
    else:
        qids = sorted(seed)
    qids = [q for q in qids if q in seed]
    print(f"[{args.mode}] {len(qids)} golds con SÍNTESIS | K={K} firm={THRESH_FIRM} "
          f"reranker={RERANKER_BACKEND} thr={RELEVANCE_THRESHOLD}", flush=True)

    out_name = args.out or f"s87_synthesis_{args.mode}.yaml"
    partial = ROOT / "evals" / (out_name + ".partial.jsonl")
    done = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            nf = sum(f.get("n_fail", 0) for f in rec["result"]["facts"])
            if nf == 0:
                done[rec["qid"]] = rec["result"]
        print(f"[resume] {len(done)} golds limpios cargados", flush=True)

    results = []
    for qid in qids:
        if qid in done:
            r = done[qid]
        else:
            r = measure_gold(qid, seed[qid], workers=args.workers)
            with partial.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"qid": qid, "result": r}, ensure_ascii=False) + "\n")
        results.append(r)
        cc = Counter(f["clase"] for f in r["facts"])
        nf = sum(f.get("n_fail", 0) for f in r["facts"])
        print(f"  {qid}: {dict(cc)} overlap={r['top5_overlap']}"
              f"{' n_fail='+str(nf) if nf else ''}", flush=True)

    agg = Counter(f["clase"] for r in results for f in r["facts"])
    n_border = sum(1 for r in results for f in r["facts"] if f["borderline"])
    print(f"\nAGG clase: {dict(agg)} | borderline(2-3/5)={n_border} | "
          f"SYNTH-MISS(omitted-in-answer)={agg.get('SYNTH-MISS', 0)}", flush=True)

    out = ROOT / "evals" / out_name
    out.write_text(yaml.safe_dump(
        {"manifest": manifest({"mode": args.mode, "qids": qids}),
         "agg": dict(agg), "n_borderline": n_border, "results": results},
        allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[written] {out}")


if __name__ == "__main__":
    main()
