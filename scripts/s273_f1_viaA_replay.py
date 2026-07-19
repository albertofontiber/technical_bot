#!/usr/bin/env python3
"""s273_f1_viaA_replay.py — F1 del prereg s273 (vía A, hp010): cuota-only sobre T1 vivo.

Dos partes (Fable-M2: la parte (i) es VERIFICACIÓN DE CONSISTENCIA — solo puede fallar por
drift del estado vivo vs el diagnóstico s272; el gate load-bearing del lever es F3):

  (i) CONSISTENCIA + replay determinista ($0 modelo, 1 embedding de query):
      re-probe del RPC de enunciados con embedding fresco de la query hp010; verificar
      contra los artefactos s272 pineados (evals/s273_s272_artifacts/) que la fila viva
      715ed152… sigue ahí con sim dentro de ±0.005; aplicar la mecánica REAL
      `_fuse_enunciados_quota` (importada del retriever, no re-implementada) sobre el
      pool vectorial re-probeado → ¿el parent p37 (155a90fe…) entra al pool-50?

  (ii) E2E con el seam ON (call-time flip, patrón s102_hyq_negcontrol_table):
      retrieve_chunks completo con ENUNCIADOS_QUOTA_ON=True → ¿p37 en el pool final?
      → 1 rerank LLM (~$0.05) → ¿p37 SERVIDO (top-10 con sim ≥ 0.4)? — INFORMATIVO,
      1 muestra, no-retry (DEC-096: el rerank no es determinista).

DB: GET/RPC read-only. Sin escrituras. Salida: evals/s273_f1_viaA_replay.json.
"""
import os

DEMO_FLAGS = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
              "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
              "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10", "RERANKER_BACKEND": "llm",
              "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
              "HYDE_ENABLED": "false", "DIVERSIFY_TIEBREAK": "off", "HYQ_PILOT_FILE": "",
              "GENERATOR_PROMPT_VARIANT": "fidelity", "HYQ_TABLE": "on",
              "GENERATOR_SELECTION_BLOCK": "on", "ENUNCIADOS_QUOTA_FUSION": "off"}
for k, v in DEMO_FLAGS.items():
    os.environ[k] = v
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=False)
for k, v in DEMO_FLAGS.items():
    os.environ[k] = v
import httpx  # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, RERANK_TOP_K  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402
from src.rag import retriever as RT  # noqa: E402
from src.rag.retriever import (ENUNCIADOS_FETCH_K, _fuse_enunciados_quota,  # noqa: E402
                               retrieve_chunks)
from src.rag.reranker import rerank  # noqa: E402

QID = "hp010"
TARGET_PARENT = "155a90fe-8c3f-484e-a617-7637fe29b547"    # DXc-config p37 (CORE hp010#1)
LIVE_ROW = "715ed152-ebb3-59fb-94fb-3d9b7e2e0bcc"         # fila viva medida s272 sim 0.4268
S272 = ROOT / "evals" / "s273_s272_artifacts"
SIM_TOL = 0.005
RELEVANCE_THRESHOLD = 0.4   # generator.py (served floor); no importamos el generator
OUT = ROOT / "evals" / "s273_f1_viaA_replay.json"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
     "Content-Type": "application/json"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    assert RT.ENUNCIADOS_QUOTA_ON is False, "el flag de proceso debe arrancar OFF"
    sys.path.insert(0, str(ROOT / "scripts"))
    from gold_store import dev  # noqa: E402
    gold = next(g for g in dev() if g["qid"] == QID)
    q = gold["question"]
    s272_phase3 = json.load(open(S272 / "phase3_probe_out.json", encoding="utf-8"))
    ref_hit = (s272_phase3.get("hp010_enun_hits") or [{}])[0]

    q_emb = embed_query(q)
    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2", headers=H,
                        json={"query_embedding": q_emb, "match_threshold": 0.3,
                              "match_count": 50, "filter_product": None,
                              "filter_category": None, "filter_manufacturer": None})
        r.raise_for_status()
        real50 = r.json()
        r2 = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2_enunciados", headers=H,
                         json={"query_embedding": q_emb, "match_threshold": 0.3,
                               "match_count": ENUNCIADOS_FETCH_K,
                               "filter_product": None, "filter_manufacturer": None})
        r2.raise_for_status()
        e_rows = r2.json()

    # (i) consistencia vs s272 (drift-check; tolerancia pre-registrada)
    live = next((s for s in e_rows if str(s.get("id")) == LIVE_ROW), None)
    drift = None
    if live is None:
        consistency = "FAIL_row_missing"
    else:
        drift = abs(float(live.get("similarity") or 0) - float(ref_hit.get("sim") or 0))
        consistency = "OK" if drift <= SIM_TOL else f"FAIL_drift_{drift:.4f}"

    by_parent: dict = {}
    for s in e_rows:
        pid = s.get("parent_id")
        if pid and (pid not in by_parent
                    or (s.get("similarity") or 0) > (by_parent[pid].get("similarity") or 0)):
            by_parent[pid] = s
    have_real = {c.get("id") for c in real50}
    new_parents_sorted = sorted(
        [s for pid, s in by_parent.items() if pid not in have_real],
        key=lambda c: c.get("similarity") or 0, reverse=True)
    target_rank_new = next((i + 1 for i, s in enumerate(new_parents_sorted)
                            if s.get("parent_id") == TARGET_PARENT), None)
    fused = _fuse_enunciados_quota(real50, by_parent, 50)   # la mecánica REAL, no un espejo
    replay_in_pool = any(c.get("parent_id") == TARGET_PARENT and c.get("_enun_quota")
                         for c in fused)

    # (ii) e2e con el seam ON a call-time
    RT.ENUNCIADOS_QUOTA_ON = True
    try:
        pool = retrieve_chunks(q, top_k=50)
    finally:
        RT.ENUNCIADOS_QUOTA_ON = False
    pool_ids = [c.get("id") for c in pool]
    e2e_in_pool = TARGET_PARENT in pool_ids
    pool_rank = (pool_ids.index(TARGET_PARENT) + 1) if e2e_in_pool else None
    served = None
    topk_rank = None
    if e2e_in_pool:
        topk = rerank(q, pool, top_k=RERANK_TOP_K, strict=True)     # 1 muestra, no-retry
        tids = [c.get("id") for c in topk]
        topk_rank = (tids.index(TARGET_PARENT) + 1) if TARGET_PARENT in tids else None
        served = any(c.get("id") == TARGET_PARENT
                     and (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD for c in topk)

    def _git(args):
        return subprocess.run(["git"] + args, capture_output=True,
                              cwd=ROOT).stdout.decode().strip()
    verdict = "GO" if (replay_in_pool and e2e_in_pool) else "NO_GO"
    out = {
        "phase": "F1_viaA", "prereg": "evals/s273_quota_prereg_v2.yaml", "qid": QID,
        "stamp": {"git_sha": _git(["rev-parse", "HEAD"]),
                  "git_dirty_src": _git(["status", "--porcelain", "--", "src/"]),
                  "flags": {**DEMO_FLAGS, "ENUNCIADOS_QUOTA_FUSION": "on (call-time flip)"},
                  "quota": RT.ENUNCIADOS_QUOTA, "min_sim": RT.ENUNCIADOS_MIN_SIM,
                  "sim_tolerance": SIM_TOL},
        "consistency_s272": {"status": consistency, "live_row": LIVE_ROW,
                             "sim_fresh": (float(live.get("similarity") or 0)
                                           if live else None),
                             "sim_s272": ref_hit.get("sim"), "drift": drift},
        "replay": {"target_parent": TARGET_PARENT,
                   "rank_among_new_parents": target_rank_new,
                   "n_new_parents": len(new_parents_sorted),
                   "enters_pool_via_quota": replay_in_pool},
        "e2e": {"in_final_pool": e2e_in_pool, "pool_rank": pool_rank,
                "n_pool": len(pool),
                "n_enun_quota_in_pool": sum(1 for c in pool if c.get("_enun_quota")),
                "rerank_topk_rank": topk_rank,
                "served": served,
                "served_note": "informativo, 1 muestra, no-retry (DEC-096)"},
        "verdict": verdict,
        "gate_note": "F1 es verificación de consistencia + entrada-al-pool; "
                     "el gate load-bearing del lever es F3 (Fable-M2)",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[F1/víaA] consistency={consistency} · replay_in_pool={replay_in_pool} "
          f"(rank_new={target_rank_new}) · e2e_in_pool={e2e_in_pool} "
          f"(pool_rank={pool_rank}) · topk_rank={topk_rank} · served={served}")
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
