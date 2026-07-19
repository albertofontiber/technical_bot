#!/usr/bin/env python3
"""s273_quota_gates.py — instrumento REAL del gate F3 del prereg s273 (Sol-M5/M6).

Tres modos (todos GET/RPC read-only; $0 modelo — solo embeddings de query):

  probe <label> --flag off|on [--k 3] [--limit N]
      K pasadas sobre los 39 golds dev (ruta harness, retrieve_chunks top-50, flip del
      seam a call-time — patrón s102_hyq_negcontrol_table). Por pasada y gold: pool-ids,
      anclas léxicas per-fact (evals/s100_factlevel_full.yaml, patrón s103_displacement_probe),
      dianas (cat022/hp018 heredadas s103 + carriers s273 cat017/hp010), nº filas _enun_quota,
      y served-containment v2.2 de los golds GANADOS. → evals/s273_quota_probe_<label>.json

  compare <old.json> <fix.json>
      Matriz de transición de anclas con K-mayoría (presente = ≥2/3) + gates numéricos
      HEREDADOS (DEC-102 + s105): anclas +0/−0 (STOP si CUALQUIER pérdida; STOP duro
      explícito en la unión s104+s105: hp005#2 · hp006#2:ISO-X · hp006#0:Fallo de Tierra),
      containment 0-missing (vigilancia explícita cat021/hp005/hp006 — s105), dianas.
      → evals/s273_f3_inherited_gates.json

  negcontrol [--limit N]
      Por gold: OFF_a, OFF_b (null de jitter), ON → EXCESS-HIGH = desplazamiento
      (OFF_a→ON) por encima del null (OFF_a→OFF_b) en rank<25 (clon del patrón
      s102_hyq_negcontrol_table). Gate: ≤7 golds EXCESS (herencia DEC-101/102).
      → evals/s273_quota_negcontrol.json

Escalada famtie (solo si algo dispara raro): scripts/retrieval_miss_famtie.py (39 diana).
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "DIVERSIFY_TIEBREAK": "off", "HYQ_PILOT_FILE": "",
        "HYQ_TABLE": "on", "ENUNCIADOS_QUOTA_FUSION": "off"}
for k, v in BASE.items():
    os.environ[k] = v
import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import unicodedata  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=False)
for k, v in BASE.items():
    os.environ[k] = v
import yaml  # noqa: E402
from src.rag import retriever as R  # noqa: E402

assert R.ENUNCIADOS_QUOTA_ON is False and R.HYQ_TABLE_ON is True

K_DEFAULT = 3
MAJORITY = 2                      # presente = ≥2 de 3 (pre-declarado, prereg v2)
NEGCONTROL_MAX_EXCESS = 7         # herencia DEC-101/102 ("negcontrol 6≤7")
CONTAINMENT_MAX_MISSING = 0       # herencia DEC-102 gate2b
# STOP duro: unión de las anclas perdidas en los DOS NO-GO (s104 artefactos + s105 PLAN)
STOP_ANCHOR_KEYS = ["hp005#2:misma zona o subzona", "hp006#2:ISO-X",
                    "hp006#0:Fallo de Tierra"]
CONTAINMENT_WATCH = ["cat021", "hp005", "hp006"]          # served-containment del NO-GO s105
# Dianas: heredadas s103 (cat022/hp018) + carriers s273 (parent-chunks en pool)
DIANA_SRCPAGE = {"cat022": [("MNDT723", 58), ("MNDT723", 10), ("MNDT722", 14)],
                 "hp018": [("MIEMI530", 21)]}
DIANA_CHUNKS = {"cat017": ["5bb83899-9d94-4fdd-8d42-24a670a036c5"],
                "hp010": ["155a90fe-8c3f-484e-a617-7637fe29b547"]}
GAINED_GOLDS = ["cat016", "cat020", "cat021", "hp001", "hp002", "hp005", "hp006",
                "hp011", "hp015"]
FACTLEVEL = ROOT / "evals" / "s100_factlevel_full.yaml"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _anchor_norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def _pool(q: str, quota_on: bool) -> list[dict]:
    R.ENUNCIADOS_QUOTA_ON = quota_on            # flip a call-time (patrón s102)
    try:
        return R.retrieve_chunks(q, top_k=50)
    finally:
        R.ENUNCIADOS_QUOTA_ON = False


def _git(args):
    return subprocess.run(["git"] + args, capture_output=True, cwd=ROOT).stdout.decode().strip()


def _stamp(extra: dict) -> dict:
    return {"git_sha": _git(["rev-parse", "HEAD"]),
            "git_dirty_src": _git(["status", "--porcelain", "--", "src/"]),
            "flags": BASE, "quota": R.ENUNCIADOS_QUOTA, "min_sim": R.ENUNCIADOS_MIN_SIM,
            "top_k": 50, **extra}


def _golds(limit: int):
    from gold_store import dev
    golds = dev()
    if limit:
        golds = golds[:limit]
    return golds


def cmd_probe(label: str, flag_on: bool, k: int, limit: int) -> int:
    fl = yaml.safe_load(open(FACTLEVEL, encoding="utf-8"))
    per_gold = {g["qid"]: g for g in fl["per_gold"]}
    golds = _golds(limit)
    runs = []
    for run_i in range(k):
        rows = []
        for g in golds:
            qid = g["qid"]
            pool = _pool(g["question"], flag_on)
            ids = [c.get("id") for c in pool]
            srcpage = [(_norm(c.get("source_file") or ""), c.get("page_number")) for c in pool]
            blob = " \n ".join(_anchor_norm(c.get("content") or "") for c in pool)
            facts_anchor = {}
            for f in per_gold.get(qid, {}).get("facts", []):
                if not f.get("lexically_anchorable"):
                    continue
                a = _anchor_norm(f.get("valor") or "")
                if len(a) < 2:
                    continue
                facts_anchor[f["key"]] = a in blob
            diana = {}
            for (src, page) in DIANA_SRCPAGE.get(qid, []):
                diana[f"{src}:p{page}"] = any(src in s and str(p) == str(page)
                                              for (s, p) in srcpage)
            for cid in DIANA_CHUNKS.get(qid, []):
                diana[cid] = cid in ids
            served_v22 = per_gold.get(qid, {}).get("served_ids") or []
            rows.append({"qid": qid, "n_pool": len(pool), "pool_ids": ids,
                         "n_enun_quota": sum(1 for c in pool if c.get("_enun_quota")),
                         "n_enun_boosted": sum(1 for c in pool if c.get("_enunciado_boosted")),
                         "facts_anchor_in_pool": facts_anchor, "diana": diana,
                         "served_v22_missing": (sorted(set(served_v22) - set(ids))
                                                if qid in GAINED_GOLDS else None)})
            print(f"  [{label} k={run_i + 1}] {qid:8s} pool={len(pool):2d} "
                  f"eq={rows[-1]['n_enun_quota']} "
                  f"anchors={sum(facts_anchor.values())}/{len(facts_anchor)}", flush=True)
        runs.append(rows)
    out = {"stamp": _stamp({"arm": label, "flag_on": flag_on, "k": k,
                            "n_golds": len(golds)}), "runs": runs}
    path = ROOT / "evals" / f"s273_quota_probe_{label}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {path}")
    return 0


def _majority(runs: list, qid: str, key: str, field: str) -> bool | None:
    vals = []
    for rows in runs:
        row = next((r for r in rows if r["qid"] == qid), None)
        if row is None:
            return None
        v = row[field].get(key)
        if v is None:
            return None
        vals.append(bool(v))
    return sum(vals) >= MAJORITY


def cmd_compare(old_path: str, fix_path: str) -> int:
    old = json.load(open(old_path, encoding="utf-8"))
    fix = json.load(open(fix_path, encoding="utf-8"))
    qids = [r["qid"] for r in old["runs"][0]]
    all_keys = {}
    for rows in old["runs"] + fix["runs"]:
        for r in rows:
            for kk in r["facts_anchor_in_pool"]:
                all_keys.setdefault(r["qid"], set()).add(kk)
    gained, lost = [], []
    for qid in qids:
        for kk in sorted(all_keys.get(qid, [])):
            o = _majority(old["runs"], qid, kk, "facts_anchor_in_pool")
            f = _majority(fix["runs"], qid, kk, "facts_anchor_in_pool")
            if o is False and f is True:
                gained.append(kk)
            elif o is True and f is False:
                lost.append(kk)
    stop_hits = [kk for kk in lost if kk in STOP_ANCHOR_KEYS]
    # containment (K-mayoría de missing por gold en el brazo fix)
    containment_missing = {}
    for qid in GAINED_GOLDS:
        per_run = []
        for rows in fix["runs"]:
            row = next((r for r in rows if r["qid"] == qid), None)
            per_run.append(set(row["served_v22_missing"] or []) if row else set())
        if per_run:
            miss = set.union(*[set(), *per_run])
            stable = {m for m in miss
                      if sum(1 for s in per_run if m in s) >= MAJORITY}
            if stable:
                containment_missing[qid] = sorted(stable)
    n_containment = sum(len(v) for v in containment_missing.values())
    watch_hit = {q: containment_missing.get(q, []) for q in CONTAINMENT_WATCH
                 if containment_missing.get(q)}
    # dianas (K-mayoría en fix)
    diana = {}
    for qid in qids:
        keys = set()
        for rows in fix["runs"]:
            row = next((r for r in rows if r["qid"] == qid), None)
            if row:
                keys |= set(row["diana"])
        for kk in sorted(keys):
            diana[f"{qid}·{kk}"] = _majority(fix["runs"], qid, kk, "diana")

    gates = {
        "anclas": {"gained": gained, "lost": lost, "stop_anchor_hits": stop_hits,
                   "threshold": "lost == 0 (herencia +0/−0)", "pass": not lost},
        "containment": {"missing": containment_missing, "n_missing": n_containment,
                        "watch_cat021_hp005_hp006": watch_hit,
                        "threshold": f"missing <= {CONTAINMENT_MAX_MISSING}",
                        "pass": n_containment <= CONTAINMENT_MAX_MISSING},
        "diana": diana,
    }
    verdict = "PASS" if (gates["anclas"]["pass"] and gates["containment"]["pass"]) else "STOP"
    out = {"stamp_old": old["stamp"], "stamp_fix": fix["stamp"],
           "majority": f"{MAJORITY}/{old['stamp']['k']}", "gates": gates,
           "verdict": verdict,
           "stop_consequence": (None if verdict == "PASS" else
                                "rollback F2 por batch exacto + lever NO-GO documentado")}
    path = ROOT / "evals" / "s273_f3_inherited_gates.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[F3] verdict={verdict} · gained={len(gained)} lost={len(lost)} "
          f"stop_hits={stop_hits} containment_missing={n_containment}")
    print(f"→ {path}")
    return 0 if verdict == "PASS" else 1


def cmd_negcontrol(limit: int) -> int:
    def _high_displaced(base, other_ids):
        ids = [c.get("id") for c in base]
        return [cid for i, cid in enumerate(ids) if cid not in other_ids and i < 25]
    rows = []
    excess = 0
    for g in _golds(limit):
        q = g["question"]
        offa = _pool(q, False); offb = _pool(q, False); on = _pool(q, True)
        offb_ids = {c.get("id") for c in offb}; on_ids = {c.get("id") for c in on}
        null_high = _high_displaced(offa, offb_ids)
        treat_high = _high_displaced(offa, on_ids)
        is_excess = len(treat_high) > len(null_high)
        excess += 1 if is_excess else 0
        rows.append({"qid": g["qid"], "null_high": len(null_high),
                     "treat_high": len(treat_high), "excess": is_excess})
        print(f"  {g['qid']:8s} null={len(null_high)} treat={len(treat_high)}"
              f"{'  EXCESS' if is_excess else ''}", flush=True)
    verdict = "PASS" if excess <= NEGCONTROL_MAX_EXCESS else "STOP"
    out = {"stamp": _stamp({"mode": "negcontrol"}), "rows": rows,
           "excess_golds": excess, "threshold": NEGCONTROL_MAX_EXCESS, "verdict": verdict}
    path = ROOT / "evals" / "s273_quota_negcontrol.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[negcontrol] EXCESS-HIGH={excess} ≤{NEGCONTROL_MAX_EXCESS} → {verdict}")
    print(f"→ {path}")
    return 0 if verdict == "PASS" else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("label")
    p.add_argument("--flag", choices=["off", "on"], required=True)
    p.add_argument("--k", type=int, default=K_DEFAULT)
    p.add_argument("--limit", type=int, default=0)
    c = sub.add_parser("compare")
    c.add_argument("old"); c.add_argument("fix")
    n = sub.add_parser("negcontrol")
    n.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "probe":
        return cmd_probe(a.label, a.flag == "on", a.k, a.limit)
    if a.cmd == "compare":
        return cmd_compare(a.old, a.fix)
    return cmd_negcontrol(a.limit)


if __name__ == "__main__":
    raise SystemExit(main())
