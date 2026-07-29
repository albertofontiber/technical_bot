"""s286 — Runner del A/B factorial PRE-REGISTRADO del guard hp018 (brief v3.1 §A/B).

CONGELADO (ninguna libertad post-hoc): 7 textos literales (P0-P3 principal, C1-C4 controles),
K=5 principal / K=3 controles, 4 celdas factoriales, orden intercalado-aleatorizado con seed
fija, misma batería en TODAS las celdas (off/off se RE-CORRE — la traza previa no es celda).

Celdas: off_off · a_only (ANTI_DIAGRAM_INVENTION) · c_only (WIRING_TOPOLOGY_GUARD) · a_c.
Paridad release: CHUNKS_TABLE=chunks_v2 + HYQ_TABLE=on + VISUAL_ASSETS_REGISTRY=on (DEC-157).

Salida (incremental, reanudable tras corte): evals/s286_hp018_ab_runs_v1.jsonl
  - primera línea: freeze stamp (git HEAD, flags, modelo, seed, textos, K, corpus count).
  - una línea por generación: job_id, celda, qkey, k, answer, wiring_guard, diagrams,
    sources, served, secs. Reanudación: los job_id ya presentes se saltan.
Tras completar: python scripts/s286_hp018_guard_ab_blind.py genera el paquete de adjudicación
ciego-a-metadatos.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("HYQ_TABLE", "on")
os.environ.setdefault("VISUAL_ASSETS_REGISTRY", "on")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gold_store  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from src.config import RETRIEVAL_TOP_K as RETRIEVE_K, RERANK_TOP_K as RERANK_K, LLM_MODEL  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402

SEED = 286
K_PRINCIPAL, K_CONTROL = 5, 3
DEST = os.path.join(ROOT, "evals", "s286_hp018_ab_runs_v1.jsonl")

_G = {g["qid"]: g for g in gold_store.load()}
BATERIA = {
    # principal (target 0/20 aserciones-no-soportadas por celda de tratamiento)
    "P0": "¿Cómo se conecta una sirena convencional en las salidas de sirena de la Morley ZXe?",
    "P1": "¿Cómo cableo las sirenas en una central Morley ZX5e? ¿Qué tengo que poner al final de la línea?",
    "P2": "Instalación de sirenas convencionales en la ZX2e de Morley: conexionado de las salidas de sirena paso a paso",
    "P3": "En una ZXe, ¿las sirenas de las salidas A y B llevan alguna resistencia o diodo? ¿Cómo se conectan?",
    # controles de sobre-supresión (target 0 supresiones en celdas con C')
    "C1": _G["hp009"]["question"],
    "C2": _G["hp003"]["question"],
    "C3": "En la central Morley ZX, ¿qué resistencias lleva una entrada monitorizada y cómo se conecta un contacto externo?",
    "C4": "¿Cómo se conecta el interface en serie SIB-2048 para los anunciadores LCD-80 en una AM2020?",
}
CELDAS = {
    "off_off": {},
    "a_only": {"ANTI_DIAGRAM_INVENTION": "on"},
    "c_only": {"WIRING_TOPOLOGY_GUARD": "on"},
    "a_c": {"ANTI_DIAGRAM_INVENTION": "on", "WIRING_TOPOLOGY_GUARD": "on"},
}
FLAG_KEYS = ("ANTI_DIAGRAM_INVENTION", "WIRING_TOPOLOGY_GUARD")


def _strict_rerank(query, chunks, **kw):
    return rerank(query, chunks, strict=True, **kw)


def run_bot(query: str) -> dict:
    return execute_rag_turn(
        query=query,
        query_for_retrieval=query,
        target_models=None,
        available_models=None,
        retrieval_top_k=RETRIEVE_K,
        rerank_top_k=RERANK_K,
        adapters=RagServingAdapters(
            retrieve=retrieve_chunks,
            rerank=_strict_rerank,
            observe_structural_shadow=observe_structural_neighbor_shadow,
            generate=generate_answer,
        ),
    )


def jobs() -> list[dict]:
    out = []
    for qkey in BATERIA:
        k_n = K_PRINCIPAL if qkey.startswith("P") else K_CONTROL
        for celda in CELDAS:
            for k in range(k_n):
                out.append({"job_id": f"{celda}:{qkey}:{k}", "celda": celda, "qkey": qkey, "k": k})
    rnd = random.Random(SEED)
    rnd.shuffle(out)  # intercalado-aleatorizado entre celdas, seed estampada
    return out


def main() -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          cwd=ROOT).stdout.strip()
    done: set[str] = set()
    if os.path.exists(DEST):
        for line in open(DEST, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("job_id"):
                done.add(r["job_id"])
    else:
        stamp = {
            "freeze": {
                "git_head": head, "seed": SEED, "k": {"principal": K_PRINCIPAL, "control": K_CONTROL},
                "modelo": LLM_MODEL, "retrieve_k": RETRIEVE_K, "rerank_k": RERANK_K,
                "env": {k: os.environ.get(k) for k in ("CHUNKS_TABLE", "HYQ_TABLE", "VISUAL_ASSETS_REGISTRY")},
                "bateria_sha256": hashlib.sha256(
                    json.dumps(BATERIA, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "bateria": BATERIA, "celdas": {c: f for c, f in CELDAS.items()},
            }
        }
        with open(DEST, "w", encoding="utf-8") as f:
            f.write(json.dumps(stamp, ensure_ascii=False) + "\n")

    todo = [j for j in jobs() if j["job_id"] not in done]
    print(f"jobs totales {sum(1 for _ in jobs())} · hechos {len(done)} · pendientes {len(todo)}")

    for n, j in enumerate(todo):
        for k in FLAG_KEYS:
            os.environ.pop(k, None)
        os.environ.update(CELDAS[j["celda"]])
        t0 = time.time()
        try:
            p = run_bot(BATERIA[j["qkey"]])
            res = p["generation"]
            answer = res.get("answer") if isinstance(res, dict) else str(res)
            row = {
                **j,
                "secs": round(time.time() - t0, 1),
                "answer": answer,
                "wiring_guard": (res or {}).get("wiring_guard") if isinstance(res, dict) else None,
                "diagrams": (res or {}).get("diagrams") if isinstance(res, dict) else None,
                "sources": sorted({c.get("source_file") for c in p["chunks"] if c.get("source_file")}),
                "served": [{"id": c.get("id"), "source_file": c.get("source_file"),
                            "page": c.get("page_number")} for c in p["chunks"]],
            }
        except Exception as exc:  # una corrida caída no tira el A/B; se reintenta al reanudar
            row = {**j, "error": str(exc)[:400], "secs": round(time.time() - t0, 1)}
        with open(DEST, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[{n+1}/{len(todo)}] {j['job_id']} · {row.get('secs')}s"
              + (" · ERROR" if "error" in row else ""))

    print("A/B COMPLETO →", DEST)


if __name__ == "__main__":
    main()
