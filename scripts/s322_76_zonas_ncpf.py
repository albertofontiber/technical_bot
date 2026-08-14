# -*- coding: utf-8 -*-
"""s322 #76 — ZONAS de las centrales convencionales NC-PF (Kidde), cita verbatim.

Regla de dominio (Alberto 14-ago): toda central lleva su dato de capacidad.
En las CONVENCIONALES ese dato son ZONAS, no lazos analógicos — modelarlas
como `lazos` mentiría (conceptos distintos); clave nueva `zonas` en el esquema
(misma forma {base, max}, misma semántica de capacidad «hasta N»).

Cada producto lleva una lista de citas CANDIDATAS (los sufijos -SC comparten
manual de familia y su fila vive en la tabla de modelos); se escribe la
primera que verifique VERBATIM contra el contenido completo de un doc mapeado
al producto. Ninguna verifica → se reporta, no se escribe.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

# (n_zonas, [citas candidatas en orden de preferencia])
DIANAS = {
    "kidde:nc-pf2": (2, ["Central de incendios convencional, 2 zonas"]),
    "kidde:nc-pf2-sc": (2, ["Central de alarma de incendio convencional de dos zonas"]),
    "kidde:nc-pf4": (4, ["Central de incendios convencional, 4 zonas"]),
    "kidde:nc-pf4-sc": (4, ["Central de alarma de incendio convencional de cuatro zonas"]),
    "kidde:nc-pf8": (8, ["Central de incendios convencional, 8 zonas"]),
    "kidde:nc-pf8-sc": (8, ["Central de alarma de incendio convencional de ocho zonas",
                            "Interfaz de usuario en centrales de ocho zonas"]),
}

censo = {d["id"]: d for d in json.loads(
    (ROOT / "evals" / "s322_76_censo_diana_v1.json")
    .read_text(encoding="utf-8"))["detalle"]}

contenido: dict[str, str] = {}


def _doc_completo(client, sf: str) -> str:
    if sf not in contenido:
        trozos, offset = [], 0
        while True:
            r = client.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                           params={"select": "content", "source_file": f"eq.{sf}",
                                   "order": "chunk_index.asc",
                                   "offset": str(offset), "limit": "100"})
            r.raise_for_status()
            lote = r.json()
            trozos.extend((x.get("content") or "") for x in lote)
            if len(lote) < 100:
                break
            offset += 100
        contenido[sf] = "\n".join(trozos)
    return contenido[sf]


filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
por_id = {r["id"]: r for r in filas}
escritas, saltadas = [], []

with abierto(timeout=30.0) as client:
    for pid, (n, candidatas) in DIANAS.items():
        fila = por_id.get(pid)
        if fila is None or not fila.get("clasificacion"):
            saltadas.append({"id": pid, "motivo": "ausente o sin clasificacion"})
            continue
        at = fila.setdefault("atributos", {})
        if at.get("zonas"):
            saltadas.append({"id": pid, "motivo": "zonas ya ancladas"})
            continue
        anclada = None
        for cita in candidatas:
            for sf in censo[pid]["docs"]:
                if cita in _doc_completo(client, sf):
                    anclada = {"base": n, "max": n, "doc": sf, "cita": cita}
                    break
            if anclada:
                break
        if not anclada:
            saltadas.append({"id": pid, "motivo": "ninguna cita candidata "
                                                  "verifica en sus docs"})
            continue
        at["zonas"] = [anclada]
        escritas.append({"id": pid, "zonas": [anclada]})

write_jsonl("products", filas)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_zonas_ncpf_v1.json").write_text(
    json.dumps({"que_es": ("Zonas NC-PF (convencionales Kidde), citas verbatim "
                           "verificadas contra doc completo. Regla de dominio "
                           "Alberto 14-ago: central ⇒ dato de capacidad; en "
                           "convencionales son ZONAS. Reversible."),
                "utc": utc, "escritas": escritas, "saltadas": saltadas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"escritas {len(escritas)} · saltadas {len(saltadas)}")
for s in saltadas:
    print("  saltada:", s["id"], "→", s["motivo"])
