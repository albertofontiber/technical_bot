#!/usr/bin/env python3
"""s83_canon_merge.py - PASO 1 de reduccion de conflicts (s83).

Re-clasifica los 1014 docs comparando los covered sets por IDENTIDAD (model + canonical_model + aliases),
no por el texto crudo del 'model'. Muchos 'conflicts' son el MISMO producto etiquetado distinto
(BASE ECO1000 == ECO1000; nombre descriptivo vs part-number) -> colapsan a agree/superset.

Dos covered-models (uno de Opus, otro de GPT) son el MISMO producto si sus key-sets normalizados
(model, canonical_model, aliases) INTERSECTAN. Read-only. Reporta delta + escribe el residual.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "evals" / "s83_full_extraction.jsonl"
RESID = ROOT / "evals" / "s83_conflicts_residual.jsonl"
REMERGED = ROOT / "evals" / "s83_full_extraction_merged.jsonl"


def norm(m: str) -> str:
    s = (m or "").upper().strip()
    for sym in ("™", "®", "©", "�"):
        s = s.replace(sym, "")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def keyset(m: dict) -> set:
    ks = set()
    for v in (m.get("model"), m.get("canonical_model")):
        if v and norm(v):
            ks.add(norm(v))
    for a in (m.get("aliases") or []):
        if a and norm(a):
            ks.add(norm(a))
    return ks


def covered_objs(res):
    if not isinstance(res, dict) or res.get("_error"):
        return None
    return res.get("covered_models", []) or []


def reclassify(o_objs, g_objs):
    if o_objs is None or g_objs is None:
        return "error", 0, 0
    o_keys = [keyset(m) for m in o_objs]
    g_keys = [keyset(m) for m in g_objs]
    o_un = sum(1 for ok in o_keys if not any(ok & gk for gk in g_keys))
    g_un = sum(1 for gk in g_keys if not any(gk & ok for ok in o_keys))
    if o_un == 0 and g_un == 0:
        cls = "agree"
    elif o_un == 0 or g_un == 0:
        cls = "superset"
    else:
        cls = "conflict"
    return cls, o_un, g_un


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rows = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    old = Counter(r["class"] for r in rows)
    new = Counter()
    transitions = Counter()
    resid = []
    with REMERGED.open("w", encoding="utf-8") as fh:
        for r in rows:
            cls, o_un, g_un = reclassify(covered_objs(r.get("opus")), covered_objs(r.get("gpt")))
            transitions[(r["class"], cls)] += 1
            new[cls] += 1
            r["class_canon"] = cls
            r["unmatched"] = [o_un, g_un]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if cls == "conflict":
                resid.append({"source_file": r["source_file"],
                              "opus_covered": r.get("opus_covered"),
                              "gpt_covered": r.get("gpt_covered"),
                              "unmatched": [o_un, g_un]})
    RESID.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in resid), encoding="utf-8")

    n = len(rows)
    print(f"docs: {n}")
    print(f"ANTES (texto crudo):  agree {old['agree']} | superset {old['superset']} | "
          f"conflict {old['conflict']} | error {old['error']}")
    print(f"DESPUES (canon+alias): agree {new['agree']} | superset {new['superset']} | "
          f"conflict {new['conflict']} | error {new['error']}")
    collapsed = old["conflict"] - new["conflict"]
    print(f"\n-> conflicts: {old['conflict']} -> {new['conflict']}  (colapsaron {collapsed}, "
          f"{100*collapsed/max(old['conflict'],1):.0f}%)")
    print("\nTransiciones desde 'conflict':")
    for (a, b), c in sorted(transitions.items()):
        if a == "conflict":
            print(f"  conflict -> {b}: {c}")
    print(f"\n-> residual conflicts: {RESID}  ({len(resid)} docs)")
    print(f"-> {REMERGED} (1014 con class_canon)")
    # muestra de residuales
    print("\nMuestra de residuales (los que aun necesitan ojo/judge):")
    for x in resid[:12]:
        print(f"  {x['source_file'][:42]:42} O={x['opus_covered']} G={x['gpt_covered']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
