#!/usr/bin/env python3
"""s102_hyq_table_gate.py — gate de pre-activación del ship hyq (D2): la TABLA debe reproducir
los flips del piloto.

Clon de `s101_hyq_measure.py` con el brazo = `HYQ_TABLE=on` (RPC match_hyq sobre chunks_v2_hyq,
migración 013) en vez del npz in-process. MISMA métrica pineada (addendum s101 §2): flip =
etapa RECALL→IN-POOL en el pool-50 same-family del deathpoint. El pool-50 no pasa por el
LLM-rerank → este gate NO necesita control OFF-vs-OFF (norma DEC-096 aplica a famtie/bvg, que
corren aparte).

GATE (plan s102): los flips OBSERVADOS del piloto (flip=true en `evals/s101_hyq_measure.yaml`
— cat016 · hp018) deben reproducirse vía tabla. El índice corpus-wide (76k preguntas vs ~5k
del piloto) añade COMPETENCIA por la cuota — eso es exactamente lo que este gate mide.
Flips NUEVOS (targets que el piloto no flipeó) se reportan como bonus, no son gate.

Uso: python scripts/s102_hyq_table_gate.py
Salida: evals/s102_hyq_table_gate.yaml
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()

DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
    "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
    "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800", "HYDE_ENABLED": "false",
    "GENERATOR_PROMPT_VARIANT": "fidelity",   # DEC-098 shipped — el gate corre la demo real
    # TRATAMIENTO (este script ES el brazo tabla):
    "HYQ_TABLE": "on",
    "HYQ_PILOT_FILE": "",                     # npz APAGADO — un solo backend por brazo
}
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

import sys, inspect  # noqa: E402
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=False)

import yaml  # noqa: E402
from src.rag import retriever as _rt  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from scripts.audit_retrieval_funnel import target_servable, fetch_manual_chunks, doc_tokens  # noqa: E402
from scripts.audit_locator import fact_match_score, SCORE_FLOOR  # noqa: E402
from scripts.retrieval_miss_famtie import gold_family, fam_norm, _pm_by_ids  # noqa: E402
from scripts.retrieval_miss_judge import judge_fact, supported_ids, THRESH_FIRM  # noqa: E402
from scripts.retrieval_miss_diagnose import diagnose_miss  # noqa: E402
from scripts.gold_store import get as gs_get  # noqa: E402

for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v
# Guard seam-a-código (patrón s102): el flag debe estar ON *y* el dispatcher debe CONSULTARLO
# — un stub que no se llama pasaría el env-check y mediría OFF-como-ON (false NO-GO).
# (fix cross-model: el flag es import-time — HYQ_TABLE_ON, no la función por-request.)
assert _rt.HYQ_TABLE_ON is True, "HYQ_TABLE=on no visible — import-order roto"
assert "HYQ_TABLE_ON" in inspect.getsource(_rt.vector_search), \
    "vector_search NO consulta HYQ_TABLE_ON — seam no cableado"

DEATHPOINT = ROOT / "evals" / "s101_deathpoint.yaml"
PILOT_YAML = ROOT / "evals" / "s101_hyq_measure.yaml"
OUT = ROOT / "evals" / "s102_hyq_table_gate.yaml"
SEM_BOUND = 40


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    dp = yaml.safe_load(DEATHPOINT.read_text(encoding="utf-8"))
    targets = [r for r in dp["results"] if r["etapa"] in ("RECALL",)]
    targets += [r for r in dp["results"] if r["qid"] == "hp014"]   # control de expectativa (doc sin cobertura)
    pilot = yaml.safe_load(PILOT_YAML.read_text(encoding="utf-8"))
    pilot_flip = {(r["qid"], r["valor"]): bool(r.get("flip")) for r in pilot["results"]}
    must = [(q, v) for (q, v), f in pilot_flip.items() if f]
    # (fix dúo s102 #9) sin flips-a-reproducir el gate pasaría VACUO — hoy must debe ser
    # {cat016·autobusqueda, hp018·6K8}; un yaml regenerado sin flips invalida el gate.
    assert must, "0 flips en el yaml del piloto — gate vacuo, medición inválida"
    print(f"brazo TABLA (HYQ_TABLE=on · RPC match_hyq · quota={_rt.HYQ_PILOT_QUOTA} "
          f"· min_cos={_rt.HYQ_PILOT_MIN_COS})")
    print(f"{len(targets)} targets · GATE = reproducir {len(must)} flips del piloto: {must}\n")

    results = []
    for t in targets:
        qid = t["qid"]
        g = gs_get(qid)
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
        val_chunks = [c for c in fam_manual
                      if (fact_match_score(t["valor"], texto, c.get("content") or "") or 0) >= SCORE_FLOOR]
        if not val_chunks:
            ordered = sorted(fam_manual, key=lambda c: (c.get("page_number") is None, c.get("page_number") or 0))
            v = judge_fact(t["valor"], texto, ordered[:SEM_BOUND], workers=6)
            val_chunks = [c for c in ordered[:SEM_BOUND] if c.get("id") in supported_ids(v, THRESH_FIRM)]

        pool = retrieve_chunks(g["question"], top_k=50)
        # OJO (nit #8 dúo r2): cuenta surrogates (cuota ≤10) + _hyq_boosted (hits REALES
        # cuya sim subió una pregunta) → puede superar la cuota; no es violación.
        n_hyq_in_pool = sum(1 for c in pool if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        pin = [{"id": c.get("id"), "src": c.get("source_file")} for c in pool]
        diag = diagnose_miss({"question": g["question"]},
                             {"qid": qid, "valor": t["valor"], "gold_family": None},
                             pin, val_chunks, k=3)
        val_ids = {c.get("id") for c in val_chunks}
        hyq_won = [{"id": c.get("id")[:12], "q": (c.get("_hyq_question") or "")[:110]}
                   for c in pool if c.get("id") in val_ids and (c.get("_hyq_surrogate") or c.get("_hyq_boosted"))]
        # ATRIBUCIÓN al canal (fix cross-model, crítico): flip = IN-POOL **y** el chunk-valor
        # entró/subió por una pregunta hyq (_hyq_surrogate/_hyq_boosted). Sin la atribución,
        # un flip por deriva de otro canal/corpus daría false-PASS de la tabla.
        flip_pool = t["etapa"] == "RECALL" and diag["etapa"] == "IN-POOL"
        flip = flip_pool and len(hyq_won) > 0
        invalid = diag["etapa"] in ("NO_VAL_CHUNKS", "RETRIEVE_ERROR")
        results.append({"qid": qid, "valor": t["valor"], "etapa_OFF": t["etapa"], "etapa_ON": diag["etapa"],
                        "flip": bool(flip), "flip_unattributed": bool(flip_pool and not hyq_won),
                        "invalid_run": bool(invalid),
                        "pilot_flip": pilot_flip.get((qid, t["valor"])),
                        "hyq_question_won": hyq_won, "n_val_chunks": len(val_chunks),
                        "n_hyq_in_pool": n_hyq_in_pool})
        mark = ("✅ FLIP" if flip else ("⚠ POOL-sin-hyq" if flip_pool
                else ("=" if diag["etapa"] == t["etapa"] else f"→{diag['etapa']}")))
        print(f"  {qid:8s} «{t['valor'][:26]:26s}» OFF={t['etapa']:14s} ON={diag['etapa']:14s} {mark}"
              f"  pilot={'F' if pilot_flip.get((qid, t['valor'])) else '·'}"
              + (f"  [{hyq_won[0]['q'][:55]}…]" if hyq_won else ""))

    # H3 observabilidad: el canal DEBE haber disparado en el run (0 = OFF-silencioso-medido-como-ON)
    assert any(r["n_hyq_in_pool"] > 0 for r in results), \
        "hyq-table NO disparó en NINGÚN target — flag/RPC/tabla rotos, medición inválida (false NO-GO)"
    by_key = {(r["qid"], r["valor"]): r for r in results}
    reproduced = {f"{q}·{v}": bool(by_key.get((q, v), {}).get("flip")) for q, v in must}
    new_flips = [f"{r['qid']}·{r['valor']}" for r in results if r["flip"] and not r["pilot_flip"]]
    unattrib = [f"{r['qid']}·{r['valor']}" for r in results if r.get("flip_unattributed")]
    lost = [k for k, ok in reproduced.items() if not ok]
    gate_pass = not lost
    print(f"\n── GATE tabla (reproducción de flips del piloto, ATRIBUIDOS a hyq) ──")
    print(f"  reproducidos: {sum(reproduced.values())}/{len(must)}"
          + (f" · PERDIDOS: {lost}" if lost else ""))
    print(f"  flips nuevos (bonus corpus-wide, no-gate): {new_flips or 'ninguno'}")
    print(f"  in-pool SIN atribución hyq (no cuentan como flip): {unattrib or 'ninguno'}")
    print(f"  VEREDICTO: {'✅ PASA' if gate_pass else '❌ NO PASA'}")
    OUT.write_text(yaml.safe_dump({
        "treatment": {"backend": "chunks_v2_hyq/match_hyq (migración 013)",
                      "quota": _rt.HYQ_PILOT_QUOTA, "min_cos": _rt.HYQ_PILOT_MIN_COS},
        "demo_flags": DEMO_FLAGS, "gate_must_reproduce": [f"{q}·{v}" for q, v in must],
        "reproduced": reproduced, "new_flips": new_flips, "flips_unattributed": unattrib,
        "gate_pass": bool(gate_pass),
        "results": results,
        "nota": "famtie/bvg no-regresión (con control OFF-vs-OFF, DEC-096) corre APARTE; "
                "la activación en Railway queda gateada al GO de Alberto.",
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"→ {OUT.name}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
