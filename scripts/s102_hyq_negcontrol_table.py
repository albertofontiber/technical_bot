#!/usr/bin/env python3
"""s102_hyq_negcontrol_table.py — control negativo del canal hyq-TABLA (mecánica v2).

Clon de s101_hyq_negcontrol2 (null de jitter, fix regla-C del v1) con el brazo ON =
`HYQ_TABLE` (RPC match_hyq + family-parity nivel-fila + carve-out) en vez del npz. Es la
pieza "famtie-side" de la no-regresión pre-activación (norma DEC-096: todo A/B de pool
con control OFF-vs-OFF): por gold dev → OFF_a, OFF_b (null) y ON; señal = desplazamiento
(OFF_a→ON) EXCEDENTE sobre el null (OFF_a→OFF_b), solo HIGH (rank final <25).

Uso: python scripts/s102_hyq_negcontrol_table.py
Salida: evals/s102_hyq_negcontrol_table.yaml
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off"}
for k, v in BASE.items():
    os.environ[k] = v
import sys, yaml
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
from src.rag import retriever as R
from scripts.gold_store import dev

assert R.HYQ_TABLE_ON is False and not R.HYQ_PILOT_FILE


def _pool(q, table_on: bool):
    R.HYQ_TABLE_ON = table_on          # el seam lee el global a call-time (import-time flag)
    try:
        return R.retrieve_chunks(q, top_k=50)
    finally:
        R.HYQ_TABLE_ON = False


def _high_displaced(base, other_ids):
    ids = [c.get("id") for c in base]
    return [i for i, cid in enumerate(ids) if cid not in other_ids and i < 25]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rows = []
    excess_golds = 0
    golds = dev()
    print(f"{len(golds)} golds dev · brazo ON = HYQ_TABLE (v2: family-parity + carve-out)\n")
    for g in golds:
        q = g["question"]
        offa = _pool(q, False); offb = _pool(q, False); on = _pool(q, True)
        offb_ids = {c.get("id") for c in offb}; on_ids = {c.get("id") for c in on}
        null_high = _high_displaced(offa, offb_ids)      # jitter puro
        treat_high = _high_displaced(offa, on_ids)       # jitter + cuota
        excess = [r for r in treat_high if r not in null_high]
        n_hyq = sum(1 for c in on if c.get("_hyq_surrogate") or c.get("_hyq_boosted"))
        rows.append({"qid": g["qid"], "null_high": null_high, "treat_high": treat_high,
                     "excess_high": excess, "n_hyq_on": n_hyq})
        if excess and n_hyq:
            excess_golds += 1
            print(f"  ⚠ {g['qid']:8s} EXCESS-HIGH ranks {excess} (null={null_high}) hyq_on={n_hyq}", flush=True)
    tot_null = sum(len(r["null_high"]) for r in rows)
    tot_excess = sum(len(r["excess_high"]) for r in rows if r["n_hyq_on"])
    n_fired = sum(1 for r in rows if r["n_hyq_on"])
    # H3 observabilidad (lección s96): 0 disparos en TODO el run = OFF-medido-como-ON
    assert n_fired > 0, "hyq-table no disparó en ningún gold — flag/RPC roto, medición inválida"
    print(f"\n── CONTROL NEGATIVO tabla-v2 (null-corrected) ──")
    print(f"  canal disparó en {n_fired}/{len(rows)} golds")
    print(f"  null (jitter OFF-vs-OFF) HIGH total: {tot_null}")
    print(f"  EXCESS HIGH atribuible a la cuota (solo golds con hyq_on>0): {tot_excess} en {excess_golds} golds")
    print(f"  VEREDICTO: {'✅ dentro del jitter' if tot_excess <= max(2, tot_null) else '❌ excede el null — daño real'}")
    yaml.safe_dump({"arm_on": "HYQ_TABLE v2 (family-parity + carve-out)",
                    "n_golds": len(rows), "n_fired": n_fired,
                    "tot_null_high": tot_null, "tot_excess_high": tot_excess,
                    "excess_golds": excess_golds, "rows": rows},
                   open(os.path.join(os.getcwd(), "evals", "s102_hyq_negcontrol_table.yaml"), "w",
                        encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print("→ s102_hyq_negcontrol_table.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
