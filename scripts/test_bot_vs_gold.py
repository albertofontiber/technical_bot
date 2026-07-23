#!/usr/bin/env python3
"""Test del bot con chunks_v2 vs gold answers (enfoque a — diagnóstico).

Para cada pregunta del eval:
  1. Corre el seam RAG servido con chunks_v2 (retrieve + rerank + coverage +
     generate). El reranker es estricto para que una avería de evaluación no se
     confunda con el fail-open de disponibilidad de producción.
  2. Un judge cross-model (gpt-5.5, distinto del bot-Sonnet y del gold-Opus)
     compara la respuesta del bot con el gold answer (Capa A).
  3. Veredicto cualitativo (PASS/PARCIAL/FALLO) + diagnóstico accionable.

Objetivo NO es un score estadístico (SWAP ya decidido) sino encontrar DÓNDE
falla el bot — como destapó el fix B5 — para arreglarlo antes de producción.

Uso: python scripts/test_bot_vs_gold.py
Salida: evals/bot_vs_gold_serving_seam_v1_*_<profile>_k*.yaml + resumen.
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

# El entorno de proceso es la autoridad del release profile y de los controles
# del harness; .env sólo rellena credenciales/valores ausentes.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-asegurar tras load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.retriever import retrieve_chunks       # noqa: E402
from src.rag.reranker import rerank                  # noqa: E402
from src.config import (                              # noqa: E402
    CHUNKS_TABLE, CHUNKS_IS_V2, RETRIEVAL_TOP_K, RERANK_TOP_K, RERANKER_BACKEND,
    COVERAGE_RELEASE_POLICY, validate_config,
)
from src.rag.generator import generate_answer        # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import (      # noqa: E402
    observe_structural_neighbor_shadow,
)

# Reranker top-k overridable por env para A/B end-to-end (prod actual = 5).
RERANK_K = int(os.getenv("RERANK_K_OVERRIDE", str(RERANK_TOP_K)))
# Retrieve pool (candidatos pre-rerank) overridable. Prod = RETRIEVAL_TOP_K = 50
# (retrieve-wide, shipped s44 — config.py:41; el "15" histórico indujo un FP del
# cross-model en s58: este comentario es lo único que algunos revisores ven).
RETRIEVE_K = int(os.getenv("RETRIEVE_K_OVERRIDE", str(RETRIEVAL_TOP_K)))

# s61: el flag local `RERANKER` se RETIRÓ — el backend lo gobierna el canónico
# RERANKER_BACKEND (src/config.py), el mismo que prod y bvg_kmajority. Si el flag
# legacy sigue seteado en el entorno, abortamos: una corrida con flag viejo y
# silencioso etiquetaría mal su artefacto.
_legacy = os.getenv("RERANKER")
if _legacy is not None and _legacy != RERANKER_BACKEND:
    sys.exit(f"RERANKER={_legacy} es el flag RETIRADO (s61) — usa RERANKER_BACKEND")
RERANKER = RERANKER_BACKEND  # naming local histórico; fuente única: config
GOLD = "evals/gold_answers_v1.yaml"
HARNESS_VARIANT = "serving_seam_v1_historical_single_turn_inputs"
OUTPUT = (
    f"evals/bot_vs_gold_{HARNESS_VARIANT}_{COVERAGE_RELEASE_POLICY.profile}_k{RERANK_K}.yaml"
    if RERANKER == "llm"
    else (
        f"evals/bot_vs_gold_{HARNESS_VARIANT}_"
        f"{COVERAGE_RELEASE_POLICY.profile}_k{RERANK_K}_{RERANKER}.yaml"
    )
)
OUTPUT = os.getenv("OUTPUT_OVERRIDE", OUTPUT)  # smoke dirigido sin pisar el artefacto del run completo
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
    "(answer = responde con contenido + cita; answer-con-conflicto = surfacea AMBAS "
    "variantes de mercado/idioma en conflicto, sin elegir ganador; clarify = pide "
    "aclaración cuando hay productos/variantes distintos y no se especifica cuál; "
    "admit = admite que el corpus NO lo cubre, sin inventar; refuse-inference = NO "
    "infiere lo no documentado (compatibilidad cross-marca, '¿debería?'): surfacea "
    "los hechos documentados por-producto por separado y redirige al fabricante, sin "
    "afirmar NI negar la inferencia)\n\n"
    "RESPUESTA GOLD (referencia correcta):\n{gold}\n\n"
    "RESPUESTA DEL BOT:\n{bot}\n\n"
    "Evalúa y responde SOLO con JSON válido (sin markdown):\n"
    "{{\n"
    '  "conducta_bot": "answer | answer-con-conflicto | clarify | admit | refuse-inference",\n'
    '  "veredicto": "PASS | PARCIAL | FALLO",\n'
    '  "diagnostico": "1-2 frases: qué acertó o qué falta/está mal/alucina"\n'
    "}}\n\n"
    "Criterio de veredicto:\n"
    "- PASS: contenido correcto y suficiente vs gold (o admite / clarifica / "
    "surfacea-sin-inferir correctamente cuando esa es la conducta esperada).\n"
    "- PARCIAL: correcto pero incompleto o impreciso.\n"
    "- FALLO: incorrecto, alucina, admite no-info cuando el gold SÍ responde, "
    "responde inventando cuando el gold admite no-info, o INFIERE lo no documentado "
    "(p.ej. afirma o niega compatibilidad cross-marca) cuando el gold pide "
    "refuse-inference."
)


def _eval_strict_rerank(query: str, chunks: list[dict], **kwargs):
    return rerank(query, chunks, strict=True, **kwargs)


def run_bot(query: str) -> dict:
    # Cruza el seam de serving para medir el release profile sin reescribir la
    # serie histórica de inputs: target_models/available_models siguen en None
    # y K admite overrides. No replica shortcuts, contexto conversacional ni
    # transporte del handler. El reranker es estricto para que una avería de
    # eval no se confunda con disponibilidad (s61 §4).

    pipeline = execute_rag_turn(
        query=query,
        query_for_retrieval=query,
        target_models=None,
        available_models=None,
        retrieval_top_k=RETRIEVE_K,
        rerank_top_k=RERANK_K,
        adapters=RagServingAdapters(
            retrieve=retrieve_chunks,
            rerank=_eval_strict_rerank,
            observe_structural_shadow=observe_structural_neighbor_shadow,
            generate=generate_answer,
        ),
    )
    chunks = pipeline["chunks"]
    res = pipeline["generation"]
    answer = res.get("answer") if isinstance(res, dict) else str(res)
    sources = sorted({c.get("source_file") for c in chunks if c.get("source_file")})
    return {
        "answer": answer,
        "n_chunks": len(chunks),
        "sources": sources,
        "coverage_status": pipeline["coverage_trace"].get("status"),
        "coverage_appended_rows": len(
            pipeline["coverage_trace"].get("appended_ids") or []
        ),
        "harness_variant": HARNESS_VARIANT,
    }


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

    validate_config(require_telegram=False, production=True)
    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"
    print(
        f"Tabla activa: {CHUNKS_TABLE} (Voyage 1024) | retrieve={RETRIEVE_K} "
        f"rerank_k={RERANK_K} | reranker={RERANKER} | "
        f"release_profile={COVERAGE_RELEASE_POLICY.profile}\n"
    )

    gold_rows = {r["qid"]: r for r in yaml.safe_load(open(GOLD, encoding="utf-8"))}
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # GATE de procedencia (TECH_DEBT #33): solo se puntúan golds cuyo ground-truth
    # está VERIFICADO contra la fuente (render+cross-model / match literal). El resto
    # queda en cuarentena explícita — un ruler no fiable produce veredictos no fiables
    # (lección s30). SCORE_ALL=1 los puntúa todos marcándolos UNVERIFIED (diagnóstico).
    score_all = os.getenv("SCORE_ALL") == "1"
    # EMBARGO del held-out (DEC-023): excluido por defecto. Este harness lee el YAML directo
    # (no pasa por gold_store.verified, donde vive el embargo de la puerta), así que el filtro
    # se replica aquí. La corrida final ÚNICA del A/B pasa INCLUDE_HELDOUT=1; el resto del
    # tiempo el held-out NO se inspecciona para tunear el lever (disciplina).
    include_heldout = os.getenv("INCLUDE_HELDOUT") == "1"

    def _estado(g: dict) -> str:
        return (g.get("_provenance") or {}).get("estado", "pendiente")

    def _split(g: dict) -> str:
        return g.get("split") or "dev"

    embargoed = [q for q in sorted(gold_rows)
                 if not include_heldout and _split(gold_rows[q]) == "held-out"]
    scored = [q for q in sorted(gold_rows)
              if (score_all or _estado(gold_rows[q]) == "verificado")
              and q not in embargoed]
    quarantined = [q for q in sorted(gold_rows) if q not in scored and q not in embargoed]
    # Filtro opcional a un subconjunto de qids (smoke dirigido; no toca el gate de procedencia).
    only = {q.strip() for q in os.getenv("ONLY_QIDS", "").split(",") if q.strip()}
    if only:
        scored = [q for q in scored if q in only]
        quarantined = [q for q in quarantined if q in only]
        embargoed = [q for q in embargoed if q in only]
    print(f"Golds VERIFICADOS (puntuados): {len(scored)}/{len(gold_rows)} | "
          f"cuarentena (sin puntuar): {len(quarantined)}")
    if embargoed:
        print(f"  EMBARGO held-out (excluidos; INCLUDE_HELDOUT=1 para la corrida final): "
              f"{len(embargoed)} → {', '.join(embargoed)}")
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
            "coverage_status": bot["coverage_status"],
            "coverage_appended_rows": bot["coverage_appended_rows"],
            "release_profile": COVERAGE_RELEASE_POLICY.profile,
            "harness_variant": bot["harness_variant"],
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
