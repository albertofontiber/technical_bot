"""s286 — extractor para la adjudicación ciega: imprime de cada respuesta blind los SEGMENTOS
relevantes al conexionado (bloques en scope-sirena por herencia de headings, TODOS los fences,
ventanas de tripwire léxico y de cadena-de-polaridad), con fallback --full <blind_id> para leer
una respuesta completa. Uso: python scripts/s286_hp018_ab_extract.py <desde> <hasta> [--full B012]
"""
from __future__ import annotations

import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from src.rag.wiring_topology_guard import _split_blocks, _normalize, _has_stem, _inherited_stem  # noqa: E402

TRIP = re.compile(r"en\s+serie|en\s+cadena|encadena|una\s+tras\s+otra|uno\s+tras\s+otro|daisy|cascada|in\s+series|chained", re.IGNORECASE)
POL = re.compile(r"(?:−|negativo|(?<![\w`])-(?![\w-]))[^.!?\n]{0,60}?(?:\+|positivo)[^.!?\n]{0,80}?(?:siguiente|proxima|próxima|anterior|next)", re.IGNORECASE)

rows = {json.loads(l)["blind_id"]: json.loads(l)
        for l in open("evals/s286_hp018_ab_blind_v1.jsonl", encoding="utf-8")}

if "--full" in sys.argv:
    bid = sys.argv[sys.argv.index("--full") + 1]
    r = rows[bid]
    print(f"=== {bid} · {r['qkey']} · FULL ===\n{r['answer']}")
    sys.exit(0)

a, b = int(sys.argv[1]), int(sys.argv[2])
for i in range(a, min(b, len(rows))):
    bid = f"B{i:03d}"
    r = rows[bid]
    ans = r["answer"] or ""
    blocks = _split_blocks(ans)
    segs = []
    for j, blk in enumerate(blocks):
        norm = _normalize(blk["text"])
        scoped = _has_stem(norm) or _inherited_stem(blocks, j)
        interesting = blk["is_fence"] or (scoped and (TRIP.search(norm) or POL.search(norm)
                      or "conect" in norm or "cablea" in norm or "polaridad" in norm
                      or "rfl" in norm or "final de linea" in norm))
        if interesting:
            segs.append(("FENCE" if blk["is_fence"] else "BLOQUE") + (" [scope-sirena]" if scoped else "")
                        + "\n" + blk["text"].strip()[:900])
    print(f"\n===== {bid} · {r['qkey']} · len={len(ans)} · segs={len(segs)} =====")
    if not segs:
        print("(sin segmentos de conexionado/fences — respuesta sin superficie de riesgo)")
    for s in segs[:6]:
        print("--- " + s)
