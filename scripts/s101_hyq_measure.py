#!/usr/bin/env python3
"""s101_hyq_measure.py — medición del piloto hyq (prereg s99 + addendum s101).

MÉTRICA PINEADA (addendum §2): "chunk-valor en el POOL-50, same-family" = bucket RETRIEVAL del
instrumento canónico. El flip que cuenta = etapa RECALL→IN-POOL en el deathpoint, con el flag ON.
NO mide top-k (eso sería rerank) ni PASS.

Brazos: OFF (baseline = evals/s101_deathpoint.yaml, ya medido) vs ON (HYQ_PILOT_FILE seteado AQUÍ).
Tratamiento ESTAMPADO (addendum §3): path + sha256 del .npz + n_preguntas.
Targets: los RECALL del deathpoint (+hp014, cuyo doc NO está cubierto — control de expectativa: no-flip).
El control negativo full-dev(39) corre APARTE cuando el full v2 dé el baseline de chunks-soporte.

Uso: python scripts/s101_hyq_measure.py
Salida: evals/s101_hyq_measure.yaml
"""
from __future__ import annotations
import os, hashlib
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
NPZ = ROOT / "evals" / "s101_hyq_embeddings.npz"

DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
    "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
    "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800", "HYDE_ENABLED": "false",
    # TRATAMIENTO (este script ES el brazo ON):
    "HYQ_PILOT_FILE": str(NPZ),
}
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

import sys, json
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import yaml
from src.rag.retriever import retrieve_chunks, HYQ_PILOT_FILE
from scripts.audit_retrieval_funnel import target_servable, fetch_manual_chunks, doc_tokens
from scripts.audit_locator import fact_match_score, SCORE_FLOOR
from scripts.retrieval_miss_famtie import gold_family, fam_norm, _pm_by_ids
from scripts.retrieval_miss_judge import judge_fact, supported_ids, THRESH_FIRM
from scripts.retrieval_miss_diagnose import diagnose_miss
from scripts.gold_store import get as gs_get

for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v
assert HYQ_PILOT_FILE == str(NPZ), "el retriever NO ve el flag — import-order roto"

DEATHPOINT = ROOT / "evals" / "s101_deathpoint.yaml"
OUT = ROOT / "evals" / "s101_hyq_measure.yaml"
SEM_BOUND = 40


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    dp = yaml.safe_load(DEATHPOINT.read_text(encoding="utf-8"))
    targets = [r for r in dp["results"] if r["etapa"] in ("RECALL",)]
    targets += [r for r in dp["results"] if r["qid"] == "hp014"]   # control de expectativa (doc sin cobertura)
    npz_sha = hashlib.sha256(NPZ.read_bytes()).hexdigest()[:16]
    import numpy as np
    nq = int(np.load(NPZ, allow_pickle=True)["embeddings"].shape[0])
    print(f"brazo ON · HYQ_PILOT_FILE={NPZ.name} sha={npz_sha} n_preguntas={nq}")
    print(f"{len(targets)} targets (RECALL×{len(targets)-1} + hp014 control-expectativa)\n")

    results = []
    for t in targets:
        qid = t["qid"]
        g = gs_get(qid)
        # fact original (valor+texto) — el deathpoint solo guarda valor
        fact = next((f for f in (g.get("atomic_facts") or []) if (f.get("valor") or "") == t["valor"]), {})
        texto = (fact.get("texto") or "").strip()
        prov = g.get("_provenance") or {}
        fuente = prov.get("fuente", "")
        servable, srv = target_servable(g)
        tgts = srv["target_tokens"]
        manual = fetch_manual_chunks(tgts) if tgts else []
        gfam = gold_family(doc_tokens(fuente), tgts, fuente)
        pm = {c.get("id"): c.get("product_model") for c in manual}
        missing = [cid for cid, v in pm.items() if v in (None, "")]
        if missing:
            pm.update(_pm_by_ids(missing))
        fam_manual = [c for c in manual if not gfam or fam_norm(pm.get(c.get("id"), "")) in gfam] or manual
        # val_chunks (mismo criterio que el deathpoint): léxico primero; fallback semántico si vacío
        val_chunks = [c for c in fam_manual
                      if (fact_match_score(t["valor"], texto, c.get("content") or "") or 0) >= SCORE_FLOOR]
        if not val_chunks:
            ordered = sorted(fam_manual, key=lambda c: (c.get("page_number") is None, c.get("page_number") or 0))
            v = judge_fact(t["valor"], texto, ordered[:SEM_BOUND], workers=6)
            val_chunks = [c for c in ordered[:SEM_BOUND] if c.get("id") in supported_ids(v, THRESH_FIRM)]

        pool = retrieve_chunks(g["question"], top_k=50)
        n_hyq_in_pool = sum(1 for c in pool if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        pin = [{"id": c.get("id"), "src": c.get("source_file")} for c in pool]
        diag = diagnose_miss({"question": g["question"]},
                             {"qid": qid, "valor": t["valor"], "gold_family": None},
                             pin, val_chunks, k=3)
        # traceability: ¿qué pregunta metió al padre? (el pool ON trae _hyq_question)
        val_ids = {c.get("id") for c in val_chunks}
        hyq_won = [{"id": c.get("id")[:12], "q": (c.get("_hyq_question") or "")[:110]}
                   for c in pool if c.get("id") in val_ids and (c.get("_hyq_surrogate") or c.get("_hyq_boosted"))]
        # FLIP = el chunk-valor está en el POOL-50 final (métrica pineada) — SOLO IN-POOL cuenta.
        # NO_VAL_CHUNKS = medición INVÁLIDA este run (val_chunks vacío), jamás un flip (fix regla-C).
        flip = t["etapa"] == "RECALL" and diag["etapa"] == "IN-POOL"
        invalid = diag["etapa"] in ("NO_VAL_CHUNKS", "RETRIEVE_ERROR")
        results.append({"qid": qid, "valor": t["valor"], "etapa_OFF": t["etapa"], "etapa_ON": diag["etapa"],
                        "flip": bool(flip), "invalid_run": bool(invalid),
                        "hyq_question_won": hyq_won, "n_val_chunks": len(val_chunks),
                        "n_hyq_in_pool": n_hyq_in_pool})
        mark = "✅ FLIP" if flip else ("=" if diag["etapa"] == t["etapa"] else f"→{diag['etapa']}")
        print(f"  {qid:8s} «{t['valor'][:26]:26s}» OFF={t['etapa']:14s} ON={diag['etapa']:14s} {mark}"
              + (f"  [{hyq_won[0]['q'][:60]}…]" if hyq_won else ""))

    # H3 observabilidad: el canal DEBE haber disparado (0 en todo el run = OFF-silencioso-medido-como-ON)
    assert any(r["n_hyq_in_pool"] > 0 for r in results), \
        "hyq NO disparó en NINGÚN target — flag/npz roto, medición inválida (false NO-GO)"
    n_flip = sum(1 for r in results if r["flip"])
    n_recall = sum(1 for r in results if r["etapa_OFF"] == "RECALL")
    cat016 = next((r for r in results if r["qid"] == "cat016"), None)
    print(f"\n── VEREDICTO piloto (métrica pineada: pool-50 same-family) ──")
    print(f"  flips RECALL→pool: {n_flip}/{n_recall}")
    print(f"  GATE prereg (cat016 DEBE flipear): {'✅' if cat016 and cat016['flip'] else '❌ NO-GO'}")
    OUT.write_text(yaml.safe_dump({
        "treatment": {"hyq_file": str(NPZ), "npz_sha256_16": npz_sha, "n_questions": nq},
        "demo_flags": DEMO_FLAGS, "n_flips": n_flip, "n_recall_targets": n_recall,
        "gate_cat016": bool(cat016 and cat016["flip"]), "results": results,
        "nota": "control negativo full-dev(39) corre APARTE con el baseline del full v2 (addendum §4)",
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"→ {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
