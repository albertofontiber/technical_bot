# -*- coding: utf-8 -*-
"""s322 #76 fase 2 — Censo de la DIANA de población: productos consumibles con
docs (catálogo ∩ doc_map) de Detnov y Kidde (el caso que manda). Solo lectura."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import load  # noqa: E402

cat = load()
con_docs: dict[str, list[str]] = {}
for dm in cat.doc_map:
    for e in dm.get("entries") or ():
        con_docs.setdefault(cat.follow_redirect(e["id"]), []).append(
            dm.get("source_file") or "")

diana = []
for pid, p in sorted(cat.products.items()):
    marca = pid.split(":")[0]
    if marca not in ("detnov", "kidde"):
        continue
    if p.get("estado") != "activo" or p.get("candidate"):
        continue
    docs = con_docs.get(pid, [])
    if not docs:
        continue
    diana.append({"id": pid, "canonical_model": p.get("canonical_model"),
                  "marca": marca, "docs": docs[:6], "n_docs": len(docs),
                  "pista_legacy": p.get("categoria"),
                  "ya_clasificado": bool(p.get("clasificacion"))})

por_marca = {}
for d in diana:
    por_marca[d["marca"]] = por_marca.get(d["marca"], 0) + 1
out = {"que_es": "Diana de población #76 fase 2: consumibles con docs, Detnov+Kidde.",
       "total": len(diana), "por_marca": por_marca, "detalle": diana}
destino = ROOT / "evals" / "s322_76_censo_diana_v1.json"
destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"total {len(diana)} · {por_marca}")
print(f"recibo -> {destino}")
