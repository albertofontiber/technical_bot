# -*- coding: utf-8 -*-
"""s322 #76 — Vuelca muestras de contenido de los 30 del mini-GT (15 Detnov +
15 Kidde, muestreo determinista por stride) para el etiquetado MANUAL previo a
la pasada LLM (r27 Sol M3: el GT se etiqueta ANTES, leyendo docs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

censo = json.loads((ROOT / "evals" / "s322_76_censo_diana_v1.json")
                   .read_text(encoding="utf-8"))["detalle"]
detnov = [d for d in censo if d["marca"] == "detnov"]
kidde = [d for d in censo if d["marca"] == "kidde"]


def _muestra(lista, n):
    paso = max(1, len(lista) // n)
    return lista[::paso][:n]

gt = _muestra(detnov, 15) + _muestra(kidde, 15)
salida = []
with abierto(timeout=30.0) as c:
    for d in gt:
        trozos = []
        for sf in d["docs"][:2]:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content",
                              "source_file": f"eq.{sf}",
                              "order": "chunk_index.asc", "limit": "2"})
            r.raise_for_status()
            trozos.extend((x.get("content") or "")[:700] for x in r.json())
        salida.append({"id": d["id"], "canonical": d["canonical_model"],
                       "pista_legacy": d.get("pista_legacy"),
                       "docs": d["docs"][:2],
                       "muestra": "\n···\n".join(trozos)[:2200]})

destino = ROOT / "evals" / "s322_76_gt_muestras_v1.json"
destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                   encoding="utf-8")
print(f"{len(salida)} productos volcados -> {destino}")
