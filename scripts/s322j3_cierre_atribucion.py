# -*- coding: utf-8 -*-
"""s322j-3 — cierre de las 2 filas que sobrevivieron a s322j/s322j-2.

Causas distintas, ambas mecánicas (y ambas fallos MÍOS, no del censo):
 · kidde:standard-display-module — el censo solo traía `source_file` (sin
   document_id), y s322j-2 solo escribía el id `if did:` → se quedó el viejo.
   Fix: resolver el document_id desde el source_file y escribirlo.
 · kidde:ke-dm3110r-kit — hay DOS filas con ese id en la misma sección y
   s322j usó `next(...)`: corrigió la primera y dejó la segunda intacta.
   Fix: aplicar la corrección a TODAS las filas con ese id.
"""
from __future__ import annotations
import json, sys
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
hechas = []

with abierto(timeout=30.0) as c:
    # (1) resolver id desde source_file
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "document_id", "source_file": "eq.9-30441-62576-es",
                      "limit": "1"})
    did = (r.json() or [{}])[0].get("document_id")
    assert did, "no se pudo resolver el document_id de 9-30441-62576-es"
    p = ROOT / "evals" / "s322f_e1b_confirmar_encoger_v1.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for f in d["detalle"]["bloque"]:
        if f["id"] == "kidde:standard-display-module":
            f["evidencia"]["document_id"] = did
            f["evidencia"]["source_file"] = "9-30441-62576-es"
            f["evidencias_extra"] = []
            hechas.append({"id": f["id"], "fix": "id resuelto desde source_file",
                           "doc": did})
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

# (2) TODAS las filas con el id duplicado
p = ROOT / "evals" / "s322g_e1_candidatos_triage_v1.json"
d = json.loads(p.read_text(encoding="utf-8"))
modelo = next((f for f in d["seccion_0a_alta_en_bloque"]
               if f["id"] == "kidde:ke-dm3110r-kit"
               and f.get("atribucion_corregida_s322j")), None)
assert modelo, "no hay fila modelo ya corregida de la que copiar"
for f in d["seccion_0a_alta_en_bloque"]:
    if f["id"] == "kidde:ke-dm3110r-kit" and not f.get("atribucion_corregida_s322j"):
        f["atribucion_previa_s322j"] = dict(f.get("documento") or {})
        f["documento"] = dict(modelo["documento"])
        f["atribucion_corregida_s322j"] = dict(modelo["atribucion_corregida_s322j"])
        f["nota_s322j3"] = "fila DUPLICADA del mismo id: s322j solo corrigió la primera"
        hechas.append({"id": f["id"], "fix": "fila duplicada corregida",
                       "doc": (modelo["documento"] or {}).get("id")})
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

(ROOT / "evals" / "s322j3_cierre_atribucion_v1.json").write_text(
    json.dumps({"que_es": __doc__.strip().splitlines()[0], "hechas": hechas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"cerradas {len(hechas)}: {[h['fix'] for h in hechas]}")
