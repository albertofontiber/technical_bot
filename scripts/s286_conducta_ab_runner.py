"""s286 — A/B de los levers de conducta (c)(d)(e): direct-first · listing-gate · followups-off.

Batería congelada: 6 preguntas × 2 brazos × K=2 = 24 gens. Brazos:
  base    = flags de conducta en default (followups on, direct-first off, listing-gate off)
  tratado = GENERATOR_DIRECT_FIRST=on + GENERATOR_FOLLOWUPS=off + VISUAL_ASSETS_LISTING_GATE=on
Paridad release completa en ambos. Métricas (adjudicación posterior): primera-frase-responde,
coletilla presente, diagrams adjuntados en preguntas de listado, contenido técnico intacto.
Salida incremental reanudable: evals/s286_conducta_ab_runs_v1.jsonl
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for k, v in (("CHUNKS_TABLE", "chunks_v2"), ("HYQ_TABLE", "on"),
             ("VISUAL_ASSETS_REGISTRY", "on"),
             ("COVERAGE_RELEASE_PROFILE", "coverage_c1_v4"),
             ("IDENTITY_RESOLVE", "on"), ("IDENTITY_RESOLVE_POLICY", "replace"),
             ("MUST_PRESERVE_CONTRACT", "on")):
    os.environ.setdefault(k, v)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gold_store  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from src.config import RETRIEVAL_TOP_K as RETRIEVE_K, RERANK_TOP_K as RERANK_K  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402

_G = {g["qid"]: g for g in gold_store.load()}
BATERIA = {
    "hp009": _G["hp009"]["question"],                       # direct-first target (lede-burial)
    "hp004": _G["hp004"]["question"],                       # multi-rama (R2: ambas sin pedir confirmación)
    "L1": "¿Qué dispositivos de detección por aspiración tiene Notifier?",   # 5.1 dogfooding
    "L2": "¿Qué productos Detnov tienes?",                                    # 5.1/#9 dogfooding
    "T1": _G["hp017"]["question"],                          # control técnico (retardos C&E)
    "T2": "En la central Morley ZX, ¿qué resistencias lleva una entrada monitorizada y cómo se conecta un contacto externo?",
}
BRAZOS = {
    "base": {},
    "tratado": {"GENERATOR_DIRECT_FIRST": "on", "GENERATOR_FOLLOWUPS": "off",
                "VISUAL_ASSETS_LISTING_GATE": "on"},
}
FLAG_KEYS = ("GENERATOR_DIRECT_FIRST", "GENERATOR_FOLLOWUPS", "VISUAL_ASSETS_LISTING_GATE")
K = 2
DEST = os.path.join(ROOT, "evals", "s286_conducta_ab_runs_v1.jsonl")


def _strict_rerank(query, chunks, **kw):
    return rerank(query, chunks, strict=True, **kw)


def run_bot(query: str) -> dict:
    return execute_rag_turn(
        query=query, query_for_retrieval=query,
        target_models=None, available_models=None,
        retrieval_top_k=RETRIEVE_K, rerank_top_k=RERANK_K,
        adapters=RagServingAdapters(
            retrieve=retrieve_chunks, rerank=_strict_rerank,
            observe_structural_shadow=observe_structural_neighbor_shadow,
            generate=generate_answer,
        ),
    )


def main() -> None:
    done = set()
    if os.path.exists(DEST):
        for line in open(DEST, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("job_id") and "error" not in r:
                done.add(r["job_id"])
    jobs = [f"{b}:{q}:{k}" for q in BATERIA for b in BRAZOS for k in range(K)]
    todo = [j for j in jobs if j not in done]
    print(f"jobs {len(jobs)} · pendientes {len(todo)}")
    for n, jid in enumerate(todo):
        brazo, qkey, _k = jid.split(":")
        for k in FLAG_KEYS:
            os.environ.pop(k, None)
        os.environ.update(BRAZOS[brazo])
        t0 = time.time()
        try:
            p = run_bot(BATERIA[qkey])
            res = p["generation"]
            answer = res.get("answer") if isinstance(res, dict) else str(res)
            row = {"job_id": jid, "brazo": brazo, "qkey": qkey,
                   "secs": round(time.time() - t0, 1), "answer": answer,
                   "diagrams": (res or {}).get("diagrams") if isinstance(res, dict) else None,
                   "sources": sorted({c.get("source_file") for c in p["chunks"] if c.get("source_file")})}
        except Exception as exc:
            row = {"job_id": jid, "error": str(exc)[:300]}
        with open(DEST, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[{n+1}/{len(todo)}] {jid} · {row.get('secs')}s" + (" ERROR" if "error" in row else ""))
    print("A/B conducta COMPLETO →", DEST)


if __name__ == "__main__":
    main()
