#!/usr/bin/env python3
"""s103_displacement_compare.py — compara los dos brazos del probe displacement-landing
(OLD = carve-out s102 @HEAD · FIX = eviction v2.1 working tree) y emite el veredicto
contra el gate pre-declarado (evals/s103_displacement_landing_design.md §Gate).

Uso: python scripts/s103_displacement_compare.py evals/s103_displacement_probe_old.json \
        evals/s103_displacement_probe_fix.json
Salida: evals/s103_displacement_gate.json + resumen por stdout.
"""
import json
import os
import sys


def main(old_path, fix_path):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    old = json.load(open(old_path, encoding="utf-8"))
    fix = json.load(open(fix_path, encoding="utf-8"))
    o_rows = {r["qid"]: r for r in old["rows"]}
    f_rows = {r["qid"]: r for r in fix["rows"]}
    qids = sorted(set(o_rows) & set(f_rows))

    # ── Gate 1: chunks diana ─────────────────────────────────────────────
    diana = {}
    for qid in qids:
        for k, v_fix in (f_rows[qid].get("diana") or {}).items():
            diana[f"{qid}·{k}"] = {"old": (o_rows[qid].get("diana") or {}).get(k),
                                   "fix": v_fix}

    # ── Gate 2a: transición de anclaje per-fact (corpus-amplio, 39 golds) ─
    gained, lost = [], []
    n_facts = 0
    for qid in qids:
        oa = o_rows[qid].get("facts_anchor_in_pool") or {}
        fa = f_rows[qid].get("facts_anchor_in_pool") or {}
        for key in sorted(set(oa) & set(fa)):
            n_facts += 1
            if not oa[key] and fa[key]:
                gained.append(key)
            elif oa[key] and not fa[key]:
                lost.append(key)

    # ── Gate 2b: served_ids v2.2 de los golds ganados, contenidos en el pool ─
    served = {}
    for qid in qids:
        missing_fix = f_rows[qid].get("served_v22_in_pool")
        if missing_fix is None:
            continue
        served[qid] = {"missing_fix": missing_fix,
                       "missing_old": o_rows[qid].get("served_v22_in_pool")}

    # ── Gate 3b: proxy de trim (n_hyq por gold, old vs fix) ──────────────
    trim = []
    for qid in qids:
        no, nf = o_rows[qid]["n_hyq_surrogate"], f_rows[qid]["n_hyq_surrogate"]
        if nf < no:
            trim.append({"qid": qid, "old": no, "fix": nf})

    out = {"stamps": {"old": old["stamp"], "fix": fix["stamp"]},
           "gate1_diana": diana,
           "gate2a_anchor_transition": {"n_facts": n_facts, "gained": gained, "lost": lost},
           "gate2b_served_gained_golds": served,
           "gate3b_trim_proxy": {"golds_with_fewer_hyq": trim,
                                 "trim_rate": f"{len(trim)}/{len(qids)}"}}
    path = os.path.join(os.getcwd(), "evals", "s103_displacement_gate.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("── GATE displacement-landing (OLD @%s vs FIX dirty=%s) ──" % (
        old["stamp"]["git_sha"][:7], bool(fix["stamp"]["git_dirty_src"])))
    print("\n[1] DIANA (desplazados s102 → deben volver):")
    for k, v in diana.items():
        flag = "✅ RECUPERADO" if (v["fix"] and not v["old"]) else (
               "❌ sigue fuera" if not v["fix"] else "= ya estaba")
        print(f"   {k:28s} old={v['old']} fix={v['fix']}  {flag}")
    print(f"\n[2a] Transición de anclaje per-fact ({n_facts} facts anchorables):")
    print(f"   GANADOS ({len(gained)}): {gained}")
    print(f"   PERDIDOS ({len(lost)}): {lost}")
    print("\n[2b] served_ids v2.2 de golds GANADOS ausentes del pool (fix vs old):")
    for qid, v in served.items():
        mark = "⚠" if v["missing_fix"] and v["missing_fix"] != v["missing_old"] else "·"
        print(f"   {mark} {qid}: fix_missing={len(v['missing_fix'])} old_missing={len(v['missing_old'])}")
    print(f"\n[3b] Trim-proxy: {len(trim)} golds con MENOS surrogates bajo fix "
          f"({[t['qid'] for t in trim]})")
    print(f"\n→ {path}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "evals/s103_displacement_probe_old.json"
    b = sys.argv[2] if len(sys.argv) > 2 else "evals/s103_displacement_probe_fix.json"
    raise SystemExit(main(a, b))
