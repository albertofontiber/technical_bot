#!/usr/bin/env python3
"""s273_f0_offline_gate.py — F0 del prereg s273 (vía B, cat017): gate offline PRE-carga.

¿Los enunciados h1 QA-passed del doc carrier (HOP-138-9ES, slice versionado
evals/s273_t2_hop138_rows_v1.jsonl, 925 filas del dump T2 @33977c1) cruzarían el corte
de la fusión por cuota (Q=6, barra 0.40) para la query cat017, SIN tocar la DB?

Simulación fiel a la mecánica de `_fuse_enunciados_quota` (src/rag/retriever.py):
  1. embedding de la query cat017 (Voyage query-mode, 1 llamada);
  2. pool REAL: RPC match_chunks_v2 top-50 (read-only) → `have_real` (los parents que
     NO contarían como nuevos);
  3. filas VIVAS del canal: RPC match_chunks_v2_enunciados fetch-200 (read-only);
  4. filas del DUMP: embedir offline los 925 textos con la receta PINEADA del loader
     (D8: context\\n\\ncontent, document-mode) → cos contra la query (~$0.01);
  5. unión vivas+dump → colapso keep-max por parent → candidatos NUEVOS con sim ≥ 0.40
     → top-Q=6 → GO ⇔ algún parent carrier de cat017 entra en la cuota.

GO  → F2 (recarga acotada, la corre Alberto) queda habilitada para este doc.
NO-GO → cat017#2 RESIDUAL formal (prereg v2 §F0); la vía A (hp010) NO se bloquea.

DB: GET/RPC read-only. Coste: ~$0.01 embeddings. No-retry. Salida:
evals/s273_f0_offline_gate.json (config-stamp + ranks + veredicto).
"""
import os

DEMO_FLAGS = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
              "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
              "HYQ_TABLE": "on", "HYDE_ENABLED": "false", "HYQ_PILOT_FILE": ""}
for k, v in DEMO_FLAGS.items():
    os.environ[k] = v
import json  # noqa: E402
import math  # noqa: E402
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
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402
from src.reingest.embed import embed  # noqa: E402
from src.rag.retriever import (ENUNCIADOS_FETCH_K, ENUNCIADOS_MIN_SIM,  # noqa: E402
                               ENUNCIADOS_QUOTA)

QID = "cat017"
SLICES = [ROOT / "evals" / "s273_t2_hop138_rows_v1.jsonl",      # HOP-138-9ES (dump T2 @33977c1)
          ROOT / "evals" / "s273_t2q_4188_rows_v1.jsonl"]        # 4188-1125-ES (pase T2Q h1, brazo condicional F0)
OUT = ROOT / "evals" / "s273_f0_offline_gate.json"
# carriers verbatim adjudicados (diagnóstico s272 §1a); solo el 1º está en este doc
CARRIER_PARENTS = {"5bb83899-9d94-4fdd-8d42-24a670a036c5": "HOP-138-9ES p5 (adjudicado)",
                   "4c186fb2-aa4b-4ca0-b316-c12ebab59712": "4188-1125-ES p17 (2º carrier)"}
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
     "Content-Type": "application/json"}


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.path.insert(0, str(ROOT / "scripts"))
    from gold_store import dev  # noqa: E402
    gold = next(g for g in dev() if g["qid"] == QID)
    q = gold["question"]
    q_emb = embed_query(q)

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2", headers=H,
                        json={"query_embedding": q_emb, "match_threshold": 0.3,
                              "match_count": 50, "filter_product": None,
                              "filter_category": None, "filter_manufacturer": None})
        r.raise_for_status()
        have_real = {c.get("id") for c in r.json()}
        r2 = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2_enunciados", headers=H,
                         json={"query_embedding": q_emb, "match_threshold": 0.3,
                               "match_count": ENUNCIADOS_FETCH_K,
                               "filter_product": None, "filter_manufacturer": None})
        r2.raise_for_status()
        live_rows = [{"parent_id": s.get("parent_id"), "sim": float(s.get("similarity") or 0),
                      "id": s.get("id"), "origin": "live"} for s in r2.json()]

    dump_rows = []
    for sl in SLICES:
        dump_rows += [json.loads(l) for l in open(sl, encoding="utf-8") if l.strip()]
    dump_rows = [d for d in dump_rows if not d.get("chaff")]
    texts = [(f"{d['context']}\n\n{d['content']}" if d.get("context") else d["content"])
             for d in dump_rows]
    embs = []
    for j in range(0, len(texts), 100):
        embs.extend(embed(texts[j:j + 100], "document"))
    sim_rows = [{"parent_id": d["parent_id"], "sim": _cos(q_emb, e), "id": d["id"],
                 "origin": "dump"} for d, e in zip(dump_rows, embs)]

    by_parent: dict = {}
    for s in live_rows + sim_rows:
        pid = s["parent_id"]
        if pid and (pid not in by_parent or s["sim"] > by_parent[pid]["sim"]):
            by_parent[pid] = s
    new_cands = [s for pid, s in by_parent.items()
                 if pid not in have_real and s["sim"] >= ENUNCIADOS_MIN_SIM]
    new_cands.sort(key=lambda s: s["sim"], reverse=True)
    quota = new_cands[:ENUNCIADOS_QUOTA]
    quota_pids = [s["parent_id"] for s in quota]
    carrier_ranks = {}
    for pid in CARRIER_PARENTS:
        rank = next((i + 1 for i, s in enumerate(new_cands) if s["parent_id"] == pid), None)
        best = by_parent.get(pid)
        carrier_ranks[pid] = {"label": CARRIER_PARENTS[pid],
                              "best_sim": best["sim"] if best else None,
                              "origin": best["origin"] if best else None,
                              "rank_among_new": rank,
                              "in_quota": pid in quota_pids,
                              "in_real_top50": pid in have_real}
    go = any(v["in_quota"] for v in carrier_ranks.values())

    def _git(args):
        return subprocess.run(["git"] + args, capture_output=True,
                              cwd=ROOT).stdout.decode().strip()
    out = {
        "phase": "F0", "prereg": "evals/s273_quota_prereg_v2.yaml", "qid": QID,
        "stamp": {"git_sha": _git(["rev-parse", "HEAD"]),
                  "git_dirty_src": _git(["status", "--porcelain", "--", "src/"]),
                  "flags": DEMO_FLAGS, "quota": ENUNCIADOS_QUOTA,
                  "min_sim": ENUNCIADOS_MIN_SIM, "fetch_k": ENUNCIADOS_FETCH_K},
        "inputs": {"slices": [s.name for s in SLICES], "n_dump_rows": len(dump_rows),
                   "n_live_rows": len(live_rows), "n_real_top50": len(have_real)},
        "simulation": {"n_parents_union": len(by_parent),
                       "n_new_cands_over_bar": len(new_cands),
                       "quota_top": [{"parent_id": s["parent_id"], "sim": round(s["sim"], 4),
                                      "origin": s["origin"]} for s in quota],
                       "new_cands_top15": [{"parent_id": s["parent_id"],
                                            "sim": round(s["sim"], 4), "origin": s["origin"]}
                                           for s in new_cands[:15]]},
        "carriers": carrier_ranks,
        "verdict": "GO" if go else "NO_GO",
        "no_go_consequence": (None if go else
                              "cat017#2 RESIDUAL formal (prereg v2 F0); la vía A sigue"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[F0] verdict={out['verdict']} · carriers={json.dumps(carrier_ranks)[:300]}")
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
