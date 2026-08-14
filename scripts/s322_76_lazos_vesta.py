# -*- coding: utf-8 -*-
"""s322 #76 — Lazos (y tecnología CAD-250) de la familia VESTA, con cita VERBATIM.

Alberto (14-ago): «la CAD-171 y CAD-201 sí deberían tener informados lazos» y
«la CAD-250 es ampliable hasta 32 lazos con módulos (no verás CAD-250-32)».
La población no las cazó por MUESTREO (las frases viven en la sección
Arquitectura, chunks #10-17; el pase leía los primeros) — no porque el corpus
no las ancle. Este script escribe SOLO esas filas, cada valor con su cita
verbatim VERIFICADA contra el contenido real del doc antes de escribir
(fallo de verificación = se aborta, jamás se escribe sin ancla).

La ampliación modular queda como entrada multi-fuente {base, max}: la CAD-250
lleva {8,8} del manual de instalación (dotación de serie) + {1,32} del MC-380
(«soporta hasta 32 lazos en un único NODO») — la semántica de capacidad
adjudicada («N lazos» = «hasta N») hace que salga para 4/8/16/32.
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

MI716 = "Manual_CAD-171-MI-716-es"
MI715 = "Manual_CAD-201-MI-715-es"
MC380_26 = "CAD-250_Manual-Configuracion-MC-380-es-2026-c"
MC380 = "CAD-250-MC-380-es"
MI372 = "Manual instalacion CAD-250 (MI_372_es_2024 e)"

# Cada entrada: cita EXACTA (substring del doc; se verifica abajo). En citas
# de CAPACIDAD («hasta N») donde el doc no declara dotación de serie, `base`
# se OMITE (r28 Sol M2: un suelo inventado sería un hecho falso); el filtro
# solo usa max (semántica «hasta N»).
LAZOS = {
    "detnov:cad-171": [
        {"base": 2, "max": 2, "doc": MI716,
         "cita": "La central CAD-171 dispone de las siguientes prestaciones:\n\n**2** lazos."}],
    "detnov:cad-201": [
        {"base": 2, "max": 8, "doc": MC380_26,
         "cita": "la versión de 2 lazos ampliable a 8 lazos CAD-201"}],
    "detnov:cad-201-plus": [
        {"max": 8, "doc": MI715,
         "cita": "Hasta **8** lazos y **2000** dispositivos (250 por lazo)."}],
    "detnov:cad-250": [
        {"base": 8, "max": 8, "doc": MI372,
         "cita": "**8** lazos y **2000** dispositivos (250 por lazo)."},
        {"max": 32, "doc": MC380,
         "cita": "El sistema CAD-250 soporta hasta 32 lazos en un único NODO"}],
}
LAZOS["detnov:cad-250-p"] = LAZOS["detnov:cad-250"]   # mismos docs mapeados

TEC_250 = {"valor": "analogica", "doc": MI372,
           "cita": ("La CAD-250 es una central analógica con características "
                    "de configuración y funcionales avanzadas")}
TECNOLOGIA = {"detnov:cad-250": TEC_250, "detnov:cad-250-p": TEC_250}

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
    # 1) VERIFICAR todas las citas ANTES de tocar nada (todo-o-nada)
    for pid, entradas in LAZOS.items():
        for e in entradas:
            if e["cita"] not in _doc_completo(client, e["doc"]):
                sys.exit(f"ABORT: cita no verbatim en {e['doc']} para {pid}: "
                         f"{e['cita'][:60]!r}")
    for pid, t in TECNOLOGIA.items():
        if t["cita"] not in _doc_completo(client, t["doc"]):
            sys.exit(f"ABORT: cita tecnologia no verbatim para {pid}")
    print("citas: todas verbatim ✔")

    # 2) escribir (solo donde falta; nunca pisar un ancla existente)
    for pid, entradas in LAZOS.items():
        fila = por_id.get(pid)
        if fila is None or not fila.get("clasificacion"):
            saltadas.append({"id": pid, "motivo": "ausente o sin clasificacion"})
            continue
        at = fila.setdefault("atributos", {})
        if at.get("lazos"):
            saltadas.append({"id": pid, "motivo": "lazos ya anclados"})
        else:
            at["lazos"] = entradas
            escritas.append({"id": pid, "lazos": entradas})
        t = TECNOLOGIA.get(pid)
        if t and not at.get("tecnologia"):
            at["tecnologia"] = [t]
            escritas.append({"id": pid, "tecnologia": t})

write_jsonl("products", filas)   # valida el conjunto entero
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_lazos_vesta_v1.json").write_text(
    json.dumps({"que_es": ("Lazos VESTA (CAD-171/201/201-PLUS/250/250-P) + tecnologia "
                           "CAD-250, citas verbatim verificadas contra el doc completo. "
                           "Origen: Alberto 14-ago (171/201 deben llevar lazos; 250 "
                           "ampliable a 32 con módulos, CAD-250-32 no existe como modelo). "
                           "Reversible: quitar las entradas listadas."),
                "utc": utc, "escritas": escritas, "saltadas": saltadas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"escritas {len(escritas)} · saltadas {len(saltadas)} — catálogo validado")
