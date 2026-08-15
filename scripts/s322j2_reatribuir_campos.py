# -*- coding: utf-8 -*-
"""s322j-2 — CORRECCIÓN de mi propio arreglo s322j.

s322j anotó la re-atribución en un campo NUEVO (`atribucion_corregida_s322j`)
pero dejó intacto el campo que el verificador (y el packet) leen de verdad —
por eso el re-censo seguía marcando las 38. Anotar no es corregir.

Esto corrige EL CAMPO REAL de cada bolsa, conservando el valor anterior para
trazabilidad (`atribucion_previa_s322j`):
  · e1b_encoger/bloque      -> evidencia.document_id  (+ source_file)
  · g1_triage/0a_alta       -> documento.id
  · e1b_qa/0_bloque_*       -> provenance_doc  (nombre de documento)
Solo toca recibos de evals/. Nada de catálogo, DB ni snapshot.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
import os
from src.http_pool import abierto

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

FICHEROS = {
    "s322f_e1b_confirmar_encoger_v1.json": [("detalle", "bloque")],
    "s322g_e1_candidatos_triage_v1.json": [("seccion_0a_alta_en_bloque",)],
    "s322_e1b_revisar_qa_v1.json": [("secciones", "0_bloque_confirmar"),
                                    ("secciones", "0_bloque_retirar")],
}


def _get(d, ruta):
    for k in ruta:
        d = d[k]
    return d


nombres: dict[str, str] = {}
with abierto(timeout=30.0) as c:
    def nombre_de(doc_id):
        if doc_id not in nombres:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "source_file",
                              "document_id": f"eq.{doc_id}", "limit": "1"})
            j = r.json() if r.status_code == 200 else []
            nombres[doc_id] = j[0]["source_file"] if j else None
        return nombres[doc_id]

    tocadas = []
    for fichero, rutas in FICHEROS.items():
        p = ROOT / "evals" / fichero
        rec = json.loads(p.read_text(encoding="utf-8"))
        for ruta in rutas:
            for fila in _get(rec, ruta):
                corr = fila.get("atribucion_corregida_s322j")
                if not corr:
                    continue
                did = corr.get("ahora_document_id")
                sf = corr.get("ahora_source_file") or (nombre_de(did) if did else None)
                if "evidencia" in fila and isinstance(fila["evidencia"], dict):
                    fila["atribucion_previa_s322j"] = dict(fila["evidencia"])
                    if did:
                        fila["evidencia"]["document_id"] = did
                    if sf:
                        fila["evidencia"]["source_file"] = sf
                    fila["evidencias_extra"] = []   # no re-apuntar al doc viejo
                elif isinstance(fila.get("documento"), dict):
                    fila["atribucion_previa_s322j"] = dict(fila["documento"])
                    if did:
                        fila["documento"]["id"] = did
                    if sf:
                        fila["documento"]["source_file"] = sf
                elif "provenance_doc" in fila:
                    fila["atribucion_previa_s322j"] = fila.get("provenance_doc")
                    if sf:
                        fila["provenance_doc"] = sf
                tocadas.append({"fichero": fichero, "id": fila.get("id"),
                                "doc": sf or did})
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")

(ROOT / "evals" / "s322j2_reatribucion_campos_v1.json").write_text(
    json.dumps({"que_es": __doc__.strip().splitlines()[0],
                "corregidas": len(tocadas), "detalle": tocadas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"campos de atribución corregidos: {len(tocadas)}")
