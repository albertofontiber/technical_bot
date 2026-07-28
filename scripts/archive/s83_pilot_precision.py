#!/usr/bin/env python3
"""s83_pilot_precision.py — precision/recall de Opus vs GPT contra el GROUND-TRUTH de Alberto.

Cierra el método (lo que el dúo pidió: precision, no solo acuerdo). Lee s83_pilot_groundtruth.yaml
(covered adjudicado) + s83_pilot_extraction.jsonl (opus_covered/gpt_covered). Reporta P/R por doc +
agregado, y separa el subconjunto CLEAN (status=clean, sin open) del fuzzy/boundary. Read-only.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GT = ROOT / "evals" / "s83_pilot_groundtruth.yaml"
JL = ROOT / "evals" / "s83_pilot_extraction.jsonl"


def norm(m: str) -> str:
    s = (m or "").upper().strip()
    for sym in ("™", "®", "©"):
        s = s.replace(sym, "")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def nset(xs):
    return {norm(x) for x in (xs or []) if norm(x)}


def pr(ext: set, gt: set, openv: set):
    tp = len(ext & gt)
    fp = len([x for x in ext if x not in gt and x not in openv])
    fn = len([x for x in gt if x not in ext])
    p = tp / (tp + fp) if (tp + fp) else 1.0
    r = tp / (tp + fn) if (tp + fn) else 1.0
    return tp, fp, fn, p, r


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    gt = yaml.safe_load(GT.read_text(encoding="utf-8"))
    gmap = {d["source_file"]: d for d in gt["docs"]}
    rows = {}
    d13 = d14 = None
    for line in JL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows[r["source_file"]] = r
        if r["source_file"] == "MIDT340":
            d13 = r
        if r["source_file"] == "MADT283":
            d14 = r

    agg = {"opus": [0, 0, 0], "gpt": [0, 0, 0]}
    aggc = {"opus": [0, 0, 0], "gpt": [0, 0, 0]}
    print(f"{'#':>2} {'doc':<34} {'st':<6} | {'Opus P/R':>11} | {'GPT P/R':>11}")
    print("-" * 78)
    for d in gt["docs"]:
        sf = d["source_file"]
        r = rows.get(sf)
        if not r:
            continue
        g = nset(d.get("covered"))
        op = nset(d.get("covered_open"))
        st = d.get("status", "")
        o = nset(r.get("opus_covered"))
        gp = nset(r.get("gpt_covered"))
        to, fo, no, po, ro = pr(o, g, op)
        tg, fg, ng, pg, rg = pr(gp, g, op)
        agg["opus"][0] += to; agg["opus"][1] += fo; agg["opus"][2] += no
        agg["gpt"][0] += tg; agg["gpt"][1] += fg; agg["gpt"][2] += ng
        if st == "clean":
            aggc["opus"][0] += to; aggc["opus"][1] += fo; aggc["opus"][2] += no
            aggc["gpt"][0] += tg; aggc["gpt"][1] += fg; aggc["gpt"][2] += ng
        print(f"{d['n']:>2} {sf[:34]:<34} {st:<6} | {po:.2f}/{ro:.2f}({to}/{fo}/{no}) "
              f"| {pg:.2f}/{rg:.2f}({tg}/{fg}/{ng})")

    def microp(a):
        tp, fp, fn = a
        return (tp / (tp + fp) if tp + fp else 1.0, tp / (tp + fn) if tp + fn else 1.0)
    print("-" * 78)
    op_all = microp(agg["opus"]); gp_all = microp(agg["gpt"])
    op_cl = microp(aggc["opus"]); gp_cl = microp(aggc["gpt"])
    print(f"AGREGADO (15)   Opus P/R = {op_all[0]:.2f}/{op_all[1]:.2f}   "
          f"GPT P/R = {gp_all[0]:.2f}/{gp_all[1]:.2f}")
    print(f"SOLO CLEAN      Opus P/R = {op_cl[0]:.2f}/{op_cl[1]:.2f}   "
          f"GPT P/R = {gp_cl[0]:.2f}/{gp_cl[1]:.2f}")
    print("(P/R por-doc: tp/fp/fn; open no penaliza)")

    # pruebas de fuego de v4
    print("\n--- doc 13 (MEGAFONIA): relations 'bundles' (VCC-1 ⊃ AMG-1?) ---")
    for lbl, res in (("Opus", (d13 or {}).get("opus", {})), ("GPT", (d13 or {}).get("gpt", {}))):
        bundles = [f"{x['source_model']}⊃{x['target_model']}"
                   for x in res.get("relations", []) if x.get("type") == "bundles"]
        print(f"  {lbl}: {len(res.get('relations', []))} rels; bundles={bundles[:6]}")
    print("\n--- doc 14 (OCR malo): source_quality ---")
    for lbl, res in (("Opus", (d14 or {}).get("opus", {})), ("GPT", (d14 or {}).get("gpt", {}))):
        print(f"  {lbl}: source_quality={res.get('source_quality')!r} covered={[m['model'] for m in res.get('covered_models', [])]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
