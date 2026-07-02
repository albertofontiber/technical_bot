#!/usr/bin/env python3
"""s93_gate0_ctrl_overlap.py — control H9 del gate-0: solape del top-20 FTS con el
pool_pin de los 6 golds SIN miss (canal redundante vs chunks nuevos/desplazamiento).
Los ids del results.json son prefijos de 8 hex (transcritos del SQL); el match
contra pool_ids (uuids completos del testbed) es por prefijo — sin colisiones a 8 hex
en pools de <=50 (verificado: aborta si un prefijo matchea 2 uuids distintos)."""
import json
import sys

res = json.load(open("evals/s93_gate0_results.json", encoding="utf-8"))
tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
pools = {c["qid"]: c["pool_ids"] for c in tb["controls"]}

print(f"{'qid':8} {'celda':7} {'en_pool':>7} {'nuevos':>6}  (pool_n)")
for qid, cells in res["controles_top20"].items():
    if qid.startswith("_"):
        continue
    pool = pools[qid]
    for cell, ids in cells.items():
        if not isinstance(ids, list):
            continue
        hits = 0
        for p in ids:
            m = [u for u in pool if u.startswith(p)]
            assert len(m) <= 1, f"prefijo ambiguo {p} en {qid}"
            hits += bool(m)
        print(f"{qid:8} {cell:7} {hits:7} {len(ids)-hits:6}  ({len(pool)})")
