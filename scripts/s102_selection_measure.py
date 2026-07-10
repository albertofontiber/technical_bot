#!/usr/bin/env python3
"""s102_selection_measure.py — A/B fact-level del bloque de SELECCIÓN (GENERATOR_SELECTION_BLOCK=on).

Diana (L4, ground s102): cat021 «necesito un 40/40, ¿qué modelo pido?» — los 4 facts llegan al
generador (reaches_gen=True ×4 en el full v3) pero el bot ASUME 40/40R y responde su código de
pedido; el gold espera la ENUMERACIÓN de variantes divergentes (I=IR3 · U=UV · M=Multi-IR/H2,
no intercambiables). Regla s79/s80: enumerar/clarify SOLO-si-diverge.

Diseño (clon del patrón s101_fidelity_measure):
- Población: cat021 (TARGET) + SENTINELS hp009 (family-genérico→answer directo, el otro lado de
  la regla — NO debe volverse clarify/enumeración), hp018 (mixto), cat022 (3/3 OK, MISMA familia
  40/40 con pregunta específica — no debe regresar), cat019 (4/4 OK control aleatorio) +
  cat013 (centinela CONDUCTUAL cross-brand: debe seguir admit-no-info — se guarda la respuesta
  para eyeball, sus facts no se juzgan: son identity/corpus-side).
- Pipe pineada por gold (retrieve→rerank top-10) compartida por ambos brazos → aísla GENERACIÓN.
- Brazo base ×1 gen · brazo selection ×2 gens (anti-varianza; conveyed-selection = en CUALQUIERA).
- Árbitro dual del instrumento (GPT-5.5 K=5 → Opus K=5). OJO ruido: la generación es
  no-determinista — el GO exige gains en cat021 CON margen y 0 regresiones estables en sentinels.
GO del lever = cat021 conveyed 0→≥2/4 sin regresión → dúo + gate antes de cualquier ship.

Uso: python scripts/s102_selection_measure.py
Salida: evals/s102_selection_measure.yaml
"""
from __future__ import annotations
import os

DEMO = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": "", "DIVERSIFY_TIEBREAK": "off",
        "GENERATOR_PROMPT_VARIANT": "base", "GENERATOR_SELECTION_BLOCK": "off"}
for _k, _v in DEMO.items():
    os.environ[_k] = _v

import sys
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
from src.rag import generator as _gen
from src.rag.generator import generate_answer

# (s102) El seam GENERATOR_SELECTION_BLOCK NO vive en src/ (lever NO-GO tal-cual-medido:
# target flaky — cat021 base 4/4 hoy — y regresión conductual hp009 answer→clarify):
# re-correr esta medición exige `git apply evals/s102_selection_seam.patch`. Sin el guard,
# el env se ignoraría en silencio y se "mediría" OFF-vs-OFF (clase s96-H3).
if not hasattr(_gen, "_selection_block_on"):

# (s103b) GUARD adicional: el bloque pasó a CODE-GATED por query (_SELECTION_INTENT). Este
# script mide ON-vs-OFF asumiendo que el bloque ENTRA al prompt del target; si el target no
# dispara el regex, ON==OFF en silencio (la clase s96-H3). Fail-fast:
from src.rag.generator import _is_selection_query as _isq  # noqa: E402
    raise RuntimeError("seam selection-block ausente en generator — aplica evals/s102_selection_seam.patch")
_SELECTION_BLOCK = _gen._SELECTION_BLOCK
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K
from scripts.factlevel_assessment import judge_conveyed_dual, _sha
from scripts.synthesis_miss_judge import judge_conveyed
from scripts.retrieval_miss_judge import core_facts, THRESH_FIRM
from scripts.gold_store import get as gs_get

assert RERANK_TOP_K == 10
OUT = ROOT / "evals" / "s102_selection_measure.yaml"

TARGET = "cat021"
SENTINELS = ["hp009", "hp018", "cat022", "cat019"]
BEHAVIORAL = ["cat013"]  # solo respuesta guardada para eyeball (cross-brand → admit-no-info)


def conveyed_dual_verdict(valor, texto, answer, workers=6) -> bool:
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
    qids = [TARGET] + SENTINELS + BEHAVIORAL
    print(f"A/B selection-block · target={TARGET} · sentinels={SENTINELS} · behavioral={BEHAVIORAL}")
    print(f"  block_sha={_sha(_SELECTION_BLOCK)}")

    results = []
    for qid in qids:
        g = gs_get(qid)
        pool = retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        topk = rerank(g["question"], pool, top_k=RERANK_TOP_K, strict=True)
        os.environ["GENERATOR_SELECTION_BLOCK"] = "off"
        ans_base = generate_answer(g["question"], topk).get("answer", "")
        os.environ["GENERATOR_SELECTION_BLOCK"] = "on"
        ans_s1 = generate_answer(g["question"], topk).get("answer", "")
        ans_s2 = generate_answer(g["question"], topk).get("answer", "")
        os.environ["GENERATOR_SELECTION_BLOCK"] = "off"

        if qid == TARGET:
            assert _isq(g["question"]), (
                f"{qid}: el target NO dispara _SELECTION_INTENT — con el gate en codigo, "
                "ON==OFF en silencio (s96-H3); revisa el regex o el target antes de medir")
        row = {"qid": qid, "role": ("target" if qid == TARGET else
                                    "behavioral" if qid in BEHAVIORAL else "sentinel"),
               # X2 cross-model: reportar AMBAS gens del brazo tratado (len de una sola infla
               # narrativas de colapso). X4: serializar los served-ids para poder separar
               # rerank-noise vs serving-composition (DEC-096) en re-runs.
               "len_base": len(ans_base), "len_sel": len(ans_s1), "len_sel2": len(ans_s2),
               "served_ids": [c.get("id") for c in topk],
               "answer_base": ans_base, "answer_sel": ans_s1, "answer_sel2": ans_s2}
        if qid not in BEHAVIORAL:
            gold_rows = []
            for f in core_facts(g):
                valor = f.get("valor", ""); texto = (f.get("texto") or "").strip()
                b = conveyed_dual_verdict(valor, texto, ans_base)
                s1 = conveyed_dual_verdict(valor, texto, ans_s1)
                sel = s1 or conveyed_dual_verdict(valor, texto, ans_s2)
                status = ("rescued" if (not b and sel) else
                          "regressed" if (b and not sel) else
                          "still-miss" if (not b and not sel) else "ok-both")
                gold_rows.append({"valor": valor, "base": b, "selection": sel, "status": status})
            row["facts"] = gold_rows
            resc = sum(1 for x in gold_rows if x["status"] == "rescued")
            regr = sum(1 for x in gold_rows if x["status"] == "regressed")
            print(f"  [{qid}·{row['role']}] rescued={resc} regressed={regr} "
                  f"ok-both={sum(1 for x in gold_rows if x['status']=='ok-both')} "
                  f"still-miss={sum(1 for x in gold_rows if x['status']=='still-miss')} "
                  f"len {row['len_base']}→{row['len_sel']}", flush=True)
        else:
            print(f"  [{qid}·behavioral] respuestas guardadas para eyeball "
                  f"(len {row['len_base']}→{row['len_sel']})", flush=True)
        results.append(row)

    agg = {"rescued": 0, "regressed": 0, "still-miss": 0, "ok-both": 0}
    tgt = {"rescued": 0, "regressed": 0}
    for r in results:
        for x in r.get("facts", []):
            agg[x["status"]] += 1
            if r["qid"] == TARGET and x["status"] in tgt:
                tgt[x["status"]] += 1
    print(f"\n── A/B selection fact-level ── {agg}")
    print(f"  TARGET {TARGET}: rescued={tgt['rescued']} regressed={tgt['regressed']} (GO si ≥2 y 0 reg. sentinels)")
    OUT.write_text(yaml.safe_dump({
        "treatment": {"seam": "GENERATOR_SELECTION_BLOCK=on (s102/L4)",
                      "block_sha": _sha(_SELECTION_BLOCK), "gens_selection": 2,
                      "metric": "conveyed fact-level árbitro dual; GO=cat021 ≥2/4 sin regresión sentinels"},
        "demo_flags": DEMO, "aggregate": agg, "results": results,
    }, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    print(f"→ {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
