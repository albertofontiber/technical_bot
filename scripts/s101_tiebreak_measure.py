#!/usr/bin/env python3
"""s101_tiebreak_measure.py — re-medición del tie-break CON ancho-10 (la vía abierta de DEC-091b).

DEC-091 (s97): NO-GO al ship con top-5 servido — hp001 PASS→FALLO porque el pool re-barajado hizo
que el RERANKER tirara el chunk-respuesta ('candado→2222') del top-5. DEC-091b: el tie-break FUNCIONA
en retrieval (rescató hp012); "RE-MEDIBLE con ancho ON" = esta medición.

Brazos (aislado, HYQ off): OFF vs DIVERSIFY_TIEBREAK=cosine, ambos con flags demo (RERANK_TOP_K=10).
  1. Target: hp012 '4 lazos / 792' (muere en DIVERSIFY) → ¿flip a IN-POOL?
  2. CENTINELA hp001 (la regresión de s97, ahora medible a nivel-hecho): sus chunks-soporte
     ('2222' MI_372 p29 + 'candado' + '1111') deben seguir EN el top-10 SERVIDO con el flag ON.
  3. Control negativo null-corrected (patrón negcontrol2) sobre los 39.
Salida: evals/s101_tiebreak_measure.yaml
"""
import os
BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": ""}
for k, v in BASE.items():
    os.environ[k] = v
os.environ["DIVERSIFY_TIEBREAK"] = "off"
import sys, yaml
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
from src.rag import retriever as R
# (s102) El port del tie-break NO vive en src/ (lever CERRADO NO-GO, DEC-095): re-correr esta
# medición exige aplicar antes `git apply evals/s101_tiebreak_port.patch`. Sin este guard, el env
# se ignoraría en silencio y se "mediría" OFF-vs-OFF (clase s96-H3).
if not hasattr(R, "_tiebreak_on"):
    raise RuntimeError("port tie-break ausente en retriever — aplica evals/s101_tiebreak_port.patch")
from src.rag.reranker import rerank
from scripts.gold_store import dev, get as gs_get
from scripts.audit_locator import fact_match_score, SCORE_FLOOR

def _set(flag):
    os.environ["DIVERSIFY_TIEBREAK"] = flag   # _tiebreak_on() lee el env en runtime → mismo proceso OK

def _pool(q):
    return R.retrieve_chunks(q, top_k=50)

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    out = {"arms": "off vs cosine · RERANK_TOP_K=10 · HYQ off"}

    # ── 1) target hp012 (fact '4 lazos / 792', muere en DIVERSIFY) ──
    g12 = gs_get("hp012")
    f12 = next(f for f in g12["atomic_facts"] if (f.get("valor") or "").startswith("4 lazos"))
    def in_pool_hp12(flag):
        _set(flag)
        pool = _pool(g12["question"])
        hits = [c for c in pool if (fact_match_score(f12["valor"], f12.get("texto", ""),
                                                     c.get("content") or "") or 0) >= SCORE_FLOOR]
        return bool(hits), len(pool)
    off12, n_off = in_pool_hp12("off")
    on12, n_on = in_pool_hp12("cosine")
    print(f"hp012 «4 lazos / 792»: OFF in-pool={off12} → ON in-pool={on12} "
          f"{'✅ FLIP' if (not off12 and on12) else ('=' if off12 == on12 else '⚠')}")
    out["hp012"] = {"off_in_pool": bool(off12), "on_in_pool": bool(on12)}

    # ── 2) centinela hp001 (la regresión DEC-091): soporte servido en top-10 con ON ──
    g1 = gs_get("hp001")
    sentinels = [f for f in g1["atomic_facts"]
                 if (f.get("valor") or "") in ("2222", "1111", "candado")]
    sent = {}
    for flag in ("off", "cosine"):
        _set(flag)
        pool = _pool(g1["question"])
        top10 = rerank(g1["question"], pool, top_k=10, strict=True)
        served = [c for c in top10 if c.get("similarity", 0) >= 0.4]
        ok = {}
        for f in sentinels:
            hit = any((fact_match_score(f["valor"], f.get("texto", ""), c.get("content") or "") or 0)
                      >= SCORE_FLOOR for c in served)
            ok[f["valor"]] = bool(hit)
        sent[flag] = ok
    regressed = [v for v in sent["off"] if sent["off"][v] and not sent["cosine"][v]]
    print(f"hp001 centinelas servidos: OFF={sent['off']} → ON={sent['cosine']}")
    print(f"  regresión-DEC-091 re-aparece: {'❌ SÍ: ' + str(regressed) if regressed else '✅ NO'}")
    out["hp001_sentinels"] = {"off": sent["off"], "on": sent["cosine"], "regressed": regressed}

    # ── 3) control negativo null-corrected (39 dev) ──
    rows = []
    for g in dev():
        q = g["question"]
        _set("off"); offa = _pool(q); offb = _pool(q)
        _set("cosine"); on = _pool(q)
        offb_ids = {c.get("id") for c in offb}; on_ids = {c.get("id") for c in on}
        ids = [c.get("id") for c in offa]
        null_high = [i for i, cid in enumerate(ids) if cid not in offb_ids and i < 25]
        treat_high = [i for i, cid in enumerate(ids) if cid not in on_ids and i < 25]
        excess = [r for r in treat_high if r not in null_high]
        rows.append({"qid": g["qid"], "excess_high": excess, "null_high": null_high})
        if excess:
            print(f"  ⚠ {g['qid']:8s} EXCESS-HIGH ranks {excess} (null={null_high})")
    tot_null = sum(len(r["null_high"]) for r in rows)
    tot_excess = sum(len(r["excess_high"]) for r in rows)
    verdict = tot_excess <= max(2, tot_null)
    print(f"\n── CONTROL NEGATIVO tie-break (null-corrected) ──")
    print(f"  null={tot_null} · EXCESS={tot_excess} → {'✅ dentro del jitter' if verdict else '❌ daño real'}")
    out["negcontrol"] = {"tot_null": tot_null, "tot_excess": tot_excess,
                         "rows": [r for r in rows if r["excess_high"]]}
    yaml.safe_dump(out, open(os.path.join(os.getcwd(), "evals", "s101_tiebreak_measure.yaml"), "w",
                             encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print("→ s101_tiebreak_measure.yaml")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
