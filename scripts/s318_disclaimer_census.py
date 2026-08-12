# -*- coding: utf-8 -*-
"""s318/#71 — CENSO del boilerplate de responsabilidad legal en el corpus.

¿Cuántos chunks/documentos llevan cláusulas de exención de responsabilidad
(la clase que el apéndice de obligaciones citó como si fuera técnica — caso
KGS bcn-3100017 p.4)? Población ANTES de diseñar (Protocolo 2): si son 2
documentos, el frame es un parche con disfraz; si son decenas, es clase.

Solo lectura. Patrones = clase RESPONSABILIDAD (v1 a conciencia NO incluye
garantía/warranty: «la garantía se anula si se abre la carcasa» SÍ carga
contenido técnico útil — queda declarado como límite, no como olvido).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# Clase RESPONSABILIDAD, bilingüe (el corpus es ES/EN/PT/multi).
PATRONES = [
    "no se hará responsable", "no se hace responsable", "no nos hacemos responsables",
    "no será responsable", "no es responsable de", "declina toda responsabilidad",
    "no asume ninguna responsabilidad", "no asume responsabilidad",
    "queda excluida la responsabilidad", "en ningún caso será responsable",
    "en ningún caso se hará responsable", "exime de toda responsabilidad",
    "shall not be liable", "assumes no liability", "assumes no responsibility",
    "no liability", "not be held liable", "disclaims all liability",
    "in no event shall", "não se responsabiliza", "não será responsável",
]

por_doc: dict[str, dict] = defaultdict(lambda: {"chunks": set(), "patrones": set()})
total_chunks: set[str] = set()

with abierto(timeout=30.0) as client:
    for patron in PATRONES:
        off = 0
        while True:
            r = client.get(
                f"{SUPABASE_URL}/rest/v1/chunks_v2",
                headers=H,
                params={"select": "id,source_file,chunk_index",
                        "content": f"ilike.*{patron}*",
                        "order": "id.asc", "offset": str(off), "limit": "1000"})
            r.raise_for_status()
            filas = r.json()
            for f in filas:
                sf = f.get("source_file") or "?"
                por_doc[sf]["chunks"].add(f["id"])
                por_doc[sf]["patrones"].add(patron)
                total_chunks.add(f["id"])
            if len(filas) < 1000:
                break
            off += 1000

resumen = {
    "documentos_con_boilerplate": len(por_doc),
    "chunks_con_boilerplate": len(total_chunks),
    "por_documento": {
        sf: {"chunks": len(d["chunks"]), "patrones": sorted(d["patrones"])[:4]}
        for sf, d in sorted(por_doc.items(),
                            key=lambda kv: -len(kv[1]["chunks"]))
    },
    "patrones_usados": PATRONES,
}
out = ROOT / "evals" / "s318_disclaimer_census_v1.json"
out.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"documentos con boilerplate de responsabilidad: {len(por_doc)}")
print(f"chunks: {len(total_chunks)}")
for sf, d in list(sorted(por_doc.items(), key=lambda kv: -len(kv[1]['chunks'])))[:12]:
    print(f"  {len(d['chunks']):3d}  {sf}")
print(f"recibo -> {out}")
