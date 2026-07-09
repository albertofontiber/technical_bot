#!/usr/bin/env python3
"""s103_displacement_probe.py — gate judge-free del lever «displacement-landing» (diseño
v2.1, evals/s103_displacement_landing_design.md).

Corre la ruta HARNESS con flags-demo y HYQ_TABLE=on (flip a call-time, patrón
s102_hyq_negcontrol_table) sobre los 39 golds dev y emite, POR BRAZO (este script se corre
una vez en el working tree = FIX y una vez en un worktree de HEAD = OLD, mismo día, misma DB):

  · pool-50 por gold: ids + (source_norm, page) + n_hyq_surrogate/boosted (proxy de trim);
  · membresía de los chunks DIANA (cat022: MNDT723 p58/p10, MNDT722 p14; hp018: MIE-MI-530
    p21 — los desplazados verificados en s102);
  · anclaje LÉXICO per-fact (valor de cada fact anchorable de evals/s100_factlevel_full.yaml
    contenido en algún chunk del pool) — para la matriz de transición OLD→FIX corpus-amplio
    (predicado propio CONSISTENTE entre brazos; NO pretende paridad con el L1 del assessment);
  · contención de los served_ids v2.2 de los golds GANADOS en el pool del brazo.

Config-stamp exhaustivo (dúo r2): flags + git SHA + dirty + CHUNKS_TABLE.

Uso:  python scripts/s103_displacement_probe.py <etiqueta-brazo>   (p.ej. fix | old)
Salida: evals/s103_displacement_probe_<etiqueta>.json
La comparación OLD-vs-FIX la hace scripts/s103_displacement_compare.py.
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "GENERATOR_PROMPT_VARIANT": "fidelity",
        "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off", "NEIGHBOR_WINDOW": "0"}
for k, v in BASE.items():
    os.environ[k] = v
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import unicodedata  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
import yaml  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from scripts.gold_store import dev  # noqa: E402

assert R.HYQ_TABLE_ON is False and not R.HYQ_PILOT_FILE

# Chunks DIANA (desplazados verificados con probe en s102 — fila v2.2 del scoreboard).
DIANA = {"cat022": [("MNDT723", 58), ("MNDT723", 10), ("MNDT722", 14)],
         "hp018": [("MIEMI530", 21)]}

# Golds de los 12 hechos GANADOS v3→v2.2 (evals/s103_transition_matrix.json).
GAINED_GOLDS = ["cat016", "cat020", "cat021", "hp001", "hp002", "hp005", "hp006",
                "hp011", "hp015"]

FACTLEVEL = os.path.join(os.getcwd(), "evals", "s100_factlevel_full.yaml")


def _norm(s: str) -> str:
    """Normalización para matching de source_file (MN-DT-722 → MNDT722) y anclas."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _anchor_norm(s: str) -> str:
    """Ancla léxica del valor de un fact: minúsculas sin acentos, espacios colapsados."""
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def _pool(q: str) -> list[dict]:
    R.HYQ_TABLE_ON = True
    try:
        return R.retrieve_chunks(q, top_k=50)
    finally:
        R.HYQ_TABLE_ON = False


def _git(args):
    return subprocess.run(["git"] + args, capture_output=True).stdout.decode().strip()


def main(arm: str):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fl = yaml.safe_load(open(FACTLEVEL, encoding="utf-8"))
    per_gold = {g["qid"]: g for g in fl["per_gold"]}
    golds = dev()
    lim = int(os.getenv("PROBE_LIMIT", "0") or "0")
    if lim:                       # smoke barato antes del full (feedback_cost_discipline)
        keep = {"cat022", "hp018", "cat016"}
        golds = ([g for g in golds if g["qid"] in keep] + golds)[:max(lim, 3)]
        seen_q = set()
        golds = [g for g in golds if not (g["qid"] in seen_q or seen_q.add(g["qid"]))]
    rows = []
    for g in golds:
        qid = g["qid"]
        pool = _pool(g["question"])
        ids = [c.get("id") for c in pool]
        srcpage = [[_norm(c.get("source_file") or ""), c.get("page_number")] for c in pool]
        blob = " \n ".join(_anchor_norm(c.get("content") or "") for c in pool)
        n_sur = sum(1 for c in pool if c.get("_hyq_surrogate"))
        n_boo = sum(1 for c in pool if c.get("_hyq_boosted"))
        diana_hits = {}
        for (src, page) in DIANA.get(qid, []):
            diana_hits[f"{src}:p{page}"] = any(
                src in s and str(p) == str(page) for (s, p) in srcpage)
        facts_anchor = {}
        for f in per_gold.get(qid, {}).get("facts", []):
            if not f.get("lexically_anchorable"):
                continue
            a = _anchor_norm(f.get("valor") or "")
            if len(a) < 2:
                continue
            facts_anchor[f["key"]] = a in blob
        served_v22 = per_gold.get(qid, {}).get("served_ids") or []
        rows.append({"qid": qid, "n_pool": len(pool), "pool_ids": ids,
                     "n_hyq_surrogate": n_sur, "n_hyq_boosted": n_boo,
                     "diana": diana_hits, "facts_anchor_in_pool": facts_anchor,
                     "served_v22_in_pool": (sorted(set(served_v22) - set(ids))
                                            if qid in GAINED_GOLDS else None)})
        d = "".join("D" if v else "x" for v in diana_hits.values())
        print(f"  {qid:8s} pool={len(pool):2d} hyq_s={n_sur:2d} hyq_b={n_boo:2d} "
              f"anchors={sum(facts_anchor.values())}/{len(facts_anchor)} {d}", flush=True)

    stamp = {"arm": arm, "git_sha": _git(["rev-parse", "HEAD"]),
             "git_dirty_src": _git(["status", "--porcelain", "--", "src/"]),
             "flags": {**BASE, "HYQ_TABLE": "on (call-time flip)"},
             "top_k": 50, "n_golds": len(rows)}
    out = {"stamp": stamp, "rows": rows}
    path = os.path.join(os.getcwd(), "evals", f"s103_displacement_probe_{arm}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot_sur = sum(r["n_hyq_surrogate"] for r in rows)
    fired = sum(1 for r in rows if r["n_hyq_surrogate"] or r["n_hyq_boosted"])
    assert fired > 0, "hyq no disparó en ningún gold — flag/RPC roto, medición inválida (H3)"
    print(f"\n[{arm}] golds={len(rows)} · canal disparó en {fired} · surrogates total={tot_sur}")
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "fix"))
