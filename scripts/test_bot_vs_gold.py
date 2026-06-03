#!/usr/bin/env python3
"""Test del bot con chunks_v2 vs gold answers (enfoque a — diagnóstico).

Para cada pregunta del eval:
  1. Corre el bot REAL con chunks_v2 (retrieve_chunks + generate_answer).
  2. Un judge cross-model (gpt-5.5, distinto del bot-Sonnet y del gold-Opus)
     compara la respuesta del bot con el gold answer (Capa A).
  3. Veredicto cualitativo (PASS/PARCIAL/FALLO) + diagnóstico accionable.

Objetivo NO es un score estadístico (SWAP ya decidido) sino encontrar DÓNDE
falla el bot — como destapó el fix B5 — para arreglarlo antes de producción.

Uso: python scripts/test_bot_vs_gold.py
Salida: evals/bot_vs_gold_results.yaml + resumen por consola.
"""
from __future__ import annotations

import os
# Forzar chunks_v2 ANTES de importar config/retriever (lee CHUNKS_TABLE del env).
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import json
import sys
from pathlib import Path

import yaml
from anthropic import Anthropic  # noqa: F401 (lo usa el generator vía su propio import)
from dotenv import load_dotenv
from openai import OpenAI

# .env con override (el sandbox puede tener vars vacías); NO pisa CHUNKS_TABLE
# porque no está en .env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-asegurar tras load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.retriever import retrieve_chunks       # noqa: E402
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402
from src.rag.generator import generate_answer        # noqa: E402
from src.config import (                              # noqa: E402
    CHUNKS_TABLE, CHUNKS_IS_V2, RETRIEVAL_TOP_K, RERANK_TOP_K,
)

# Reranker top-k overridable por env para A/B end-to-end (prod actual = 5).
RERANK_K = int(os.getenv("RERANK_K_OVERRIDE", str(RERANK_TOP_K)))
# Retrieve pool (candidatos pre-rerank) overridable para A/B #16 (prod = 15).
# #32 solo varió el generator-k (RERANK_K); ampliar el pool nunca se midió end-to-end.
RETRIEVE_K = int(os.getenv("RETRIEVE_K_OVERRIDE", str(RETRIEVAL_TOP_K)))

RERANKER = os.getenv("RERANKER", "llm")  # A/B Track A: llm (prod) | voyage (cross-encoder)
GOLD = "evals/gold_answers_v1.yaml"
OUTPUT = (f"evals/bot_vs_gold_results_k{RERANK_K}.yaml" if RERANKER == "llm"
          else f"evals/bot_vs_gold_results_k{RERANK_K}_{RERANKER}.yaml")
JUDGE_MODEL = "gpt-5.5"

_JUDGE_SYS = (
    "Eres un evaluador imparcial de un bot técnico de sistemas PCI (detección "
    "de incendios). Comparas la respuesta del BOT con una respuesta GOLD de "
    "referencia (escrita por un experto sobre el manual oficial). Eres estricto "
    "pero justo: lo que importa es si el bot ayudaría correctamente a un técnico."
)

_JUDGE_USER = (
    "PREGUNTA:\n{question}\n\n"
    "CONDUCTA ESPERADA: {expected}\n"
    "(answer = debe responder con contenido; ask_clarification = debe pedir "
    "aclaración; admit_no_info = debe admitir que no tiene la información, sin "
    "inventar)\n\n"
    "RESPUESTA GOLD (referencia correcta):\n{gold}\n\n"
    "RESPUESTA DEL BOT:\n{bot}\n\n"
    "Evalúa y responde SOLO con JSON válido (sin markdown):\n"
    "{{\n"
    '  "conducta_bot": "answer | ask_clarification | admit_no_info",\n'
    '  "veredicto": "PASS | PARCIAL | FALLO",\n'
    '  "diagnostico": "1-2 frases: qué acertó o qué falta/está mal/alucina"\n'
    "}}\n\n"
    "Criterio de veredicto:\n"
    "- PASS: contenido correcto y suficiente vs gold (o admite/clarifica "
    "correctamente cuando esa es la conducta esperada).\n"
    "- PARCIAL: correcto pero incompleto o impreciso.\n"
    "- FALLO: incorrecto, alucina, o admite no-info cuando el gold SÍ responde "
    "(o responde inventando cuando el gold admite no-info)."
)


def run_bot(query: str) -> dict:
    # Replica el pipeline de producción: retrieve → rerank(top-k) → generate.
    chunks = retrieve_chunks(query, top_k=RETRIEVE_K)
    chunks = (rerank_chunks_voyage(query, chunks, top_k=RERANK_K) if RERANKER == "voyage"
              else rerank_chunks(query, chunks, top_k=RERANK_K))
    res = generate_answer(query, chunks)
    answer = res.get("answer") if isinstance(res, dict) else str(res)
    sources = sorted({c.get("source_file") for c in chunks if c.get("source_file")})
    return {"answer": answer, "n_chunks": len(chunks), "sources": sources}


def judge(client: OpenAI, question: str, expected: str, gold: str, bot: str) -> dict:
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": _JUDGE_SYS},
            {"role": "user", "content": _JUDGE_USER.format(
                question=question, expected=expected,
                gold=(gold or "")[:3000], bot=(bot or "")[:3000])},
        ],
    )
    txt = resp.choices[0].message.content.strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(txt)
    except Exception as e:
        return {"conducta_bot": "?", "veredicto": "?",
                "diagnostico": f"(parse error: {e}) {txt[:200]}"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"
    print(f"Tabla activa: {CHUNKS_TABLE} (Voyage 1024) | retrieve={RETRIEVE_K} rerank_k={RERANK_K} | reranker={RERANKER}\n")

    gold_rows = {r["qid"]: r for r in yaml.safe_load(open(GOLD, encoding="utf-8"))}
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # GATE de procedencia (TECH_DEBT #33): solo se puntúan golds cuyo ground-truth
    # está VERIFICADO contra la fuente (render+cross-model / match literal). El resto
    # queda en cuarentena explícita — un ruler no fiable produce veredictos no fiables
    # (lección s30). SCORE_ALL=1 los puntúa todos marcándolos UNVERIFIED (diagnóstico).
    score_all = os.getenv("SCORE_ALL") == "1"

    def _estado(g: dict) -> str:
        return (g.get("_provenance") or {}).get("estado", "pendiente")

    scored = [q for q in sorted(gold_rows)
              if score_all or _estado(gold_rows[q]) == "verificado"]
    quarantined = [q for q in sorted(gold_rows) if q not in scored]
    print(f"Golds VERIFICADOS (puntuados): {len(scored)}/{len(gold_rows)} | "
          f"cuarentena (sin puntuar): {len(quarantined)}")
    if quarantined:
        print("  cuarentena: " + ", ".join(
            f"{q}[{_estado(gold_rows[q])}]" for q in quarantined))
    if score_all and quarantined:
        print("  (SCORE_ALL=1: se puntúan IGUAL, marcados UNVERIFIED — no fiable)")
    if not scored:
        print("\nNada que puntuar: ningún gold con _provenance.estado=verificado.")
        return 0
    print()

    results = []
    for qid in scored:
        g = gold_rows[qid]
        q = g["question"]
        expected = g.get("conducta_esperada", "answer")
        print(f"=== {qid} ===")
        bot = run_bot(q)
        verdict = judge(oai, q, expected, g.get("gold_answer", ""), bot["answer"])
        row = {
            "qid": qid, "question": q,
            "gold_estado": _estado(g),
            "conducta_esperada": expected,
            "conducta_bot": verdict.get("conducta_bot"),
            "veredicto": verdict.get("veredicto"),
            "diagnostico": verdict.get("diagnostico"),
            "bot_sources": bot["sources"],
            "bot_answer": bot["answer"],
        }
        results.append(row)
        print(f"  esperada={expected} | bot={verdict.get('conducta_bot')} "
              f"| {verdict.get('veredicto')}")
        print(f"  {verdict.get('diagnostico')}")
        print(f"  fuentes: {bot['sources'][:4]}\n")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(results, f, allow_unicode=True, sort_keys=False)

    # Resumen
    from collections import Counter
    cc = Counter(r["veredicto"] for r in results)
    print("=" * 60)
    print("RESUMEN:", dict(cc))
    print("FALLOS / PARCIALES (accionables):")
    for r in results:
        if r["veredicto"] in ("FALLO", "PARCIAL", "?"):
            print(f"  [{r['veredicto']}] {r['qid']} ({r['conducta_esperada']}"
                  f"→{r['conducta_bot']}): {r['diagnostico']}")
    print(f"\nDetalle en {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
