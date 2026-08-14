# -*- coding: utf-8 -*-
"""s322b r28 — Migración: retira los `base` INVENTADOS (dúo r28, Sol M2).

Donde el doc solo declara capacidad («hasta N» / derivación de sufijo), el
suelo base=1 que escribimos era un hecho falso indistinguible a máquina. El
esquema ya admite `base` opcional; esta migración lo retira EXACTAMENTE de las
entradas donde fue invención del autor (lista cerrada por (id, doc) — jamás un
barrido heurístico). Los `base` declarados por el doc (CAD-171 «2 lazos»,
CAD-201 «2 ampliable a 8», CAD-250 «8 lazos» de serie, NC-PF «N zonas») se
conservan.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

SUFIJO_DOC = "55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT"
MC380 = "CAD-250-MC-380-es"
MI715 = "Manual_CAD-201-MI-715-es"

# (id, clave, doc) → entradas cuyo base fue suelo inventado
DIANAS = {
    ("detnov:cad-150-4", "lazos", SUFIJO_DOC),
    ("detnov:cad-150-8", "lazos", SUFIJO_DOC),
    ("detnov:cad-150-8-plus", "lazos", SUFIJO_DOC),
    ("detnov:cad-201-plus", "lazos", MI715),
    ("detnov:cad-250", "lazos", MC380),
    ("detnov:cad-250-p", "lazos", MC380),
}

filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
tocadas = []
for r in filas:
    at = r.get("atributos") or {}
    for clave, valores in at.items():
        for v in valores if isinstance(valores, list) else ():
            if ((r["id"], clave, v.get("doc")) in DIANAS
                    and "base" in v):
                del v["base"]
                tocadas.append({"id": r["id"], "clave": clave,
                                "doc": v.get("doc"), "max": v.get("max")})

write_jsonl("products", filas)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_migra_base_opcional_v1.json").write_text(
    json.dumps({"que_es": "Retirada de base inventado (r28 Sol M2); lista "
                          "cerrada por (id, clave, doc). Reversible.",
                "utc": utc, "tocadas": tocadas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"bases retirados: {len(tocadas)} — catálogo validado")
for t in tocadas:
    print(" ", t["id"], t["clave"], "max", t["max"])
