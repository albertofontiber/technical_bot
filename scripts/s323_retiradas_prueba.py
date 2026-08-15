# -*- coding: utf-8 -*-
"""s323 — PUERTA A: prueba mecánica de artefacto, fila a fila (NO aplica nada aún).

Criterio (evals/s323_criterio_limpieza_candidates_v1.md, corregido tras el dúo r30):
una retirada exige (1) fragmento VERBATIM del corpus del que el extractor derivó el
término y que demuestra que es otra cosa, (2) cero apariciones como SUJETO en el texto
extraído, (3) búsqueda online que no lo encuentre como producto. Aquí se resuelven (1)
y (2) mecánicamente; las filas que las pasen quedan listadas para el chequeo (3).
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

qa = json.loads((ROOT / "evals" / "s322_e1b_revisar_qa_v1.json").read_text(encoding="utf-8"))
objetivo = [f for f in qa["secciones"]["0_bloque_retirar"]] + \
           [f for f in qa["secciones"]["1_individual"]
            if (f.get("llm") or {}).get("veredicto") == "RETIRAR"]
print(f"filas con veredicto RETIRAR: {len(objetivo)}")

# señales de SUJETO: titular markdown, fila de tabla de modelos, referencia comercial
RX_SUJETO = [
    (re.compile(r"^#{1,3}\s*[^\n]*\b{t}\b", re.I | re.M), "titular"),
    (re.compile(r"\|\s*{t}\s*\|", re.I), "fila de tabla"),
    (re.compile(r"\b(ref|mod|modelo|art)\.?\s*:?\s*{t}\b", re.I), "referencia comercial"),
]
# patrones de ARTEFACTO: el término nace de una medida/norma/frase
RX_ARTEFACTO = [
    (r"\d+\s*(mm|cm|m|km|v|vdc|vca|w|ma|a|hz|db|°c)\b", "medida/unidad"),
    (r"\b(hasta|max|máx|min|mín|up to)\b", "expresión de límite"),
    (r"\b(en|une|iec|iso|ul|vds)[\s-]?\d", "norma"),
    (r"\d{4}-(cpd|cpr)-", "certificación"),
]
filas = []
with abierto(timeout=30.0) as c:
    for f in objetivo:
        term = f["modelo"]
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "source_file,content",
                          "content": f"ilike.*{term}*", "limit": "12"})
        chunks = r.json() if r.status_code == 200 else []
        sujeto, artefacto = [], []
        for x in chunks:
            txt = x.get("content") or ""
            for rx, que in RX_SUJETO:
                if re.search(rx.pattern.replace("{t}", re.escape(term)), txt,
                             re.I | re.M):
                    sujeto.append({"doc": x["source_file"], "senal": que})
                    break
            i = txt.lower().find(term.lower())
            if i >= 0:
                ventana = txt[max(0, i - 90):i + 90]
                for pat, que in RX_ARTEFACTO:
                    if re.search(pat, ventana, re.I):
                        artefacto.append({"doc": x["source_file"], "clase": que,
                                          "fragmento": ventana.replace("\n", " ")})
                        break
        filas.append({"id": f["id"], "modelo": term, "marca": f.get("marca"),
                      "n_chunks_examinados": len(chunks),
                      "senales_sujeto": sujeto[:3],
                      "prueba_artefacto": artefacto[:2],
                      "puerta_a_mecanica": bool(artefacto) and not sujeto,
                      "razon_llm": (f.get("llm") or {}).get("razon", "")[:150]})

ok = [x for x in filas if x["puerta_a_mecanica"]]
no = [x for x in filas if not x["puerta_a_mecanica"]]
(ROOT / "evals" / "s323_retiradas_prueba_v1.json").write_text(
    json.dumps({"que_es": __doc__.strip().splitlines()[0],
                "total": len(filas), "pasan_puerta_a_mecanica": len(ok),
                "a_packet": len(no), "detalle": filas}, ensure_ascii=False, indent=1),
    encoding="utf-8")
print(f"pasan prueba mecánica (artefacto SIN señal de sujeto): {len(ok)}")
for x in ok:
    p = x["prueba_artefacto"][0]
    print(f"   {x['modelo']:<22} [{p['clase']}] …{p['fragmento'][:78]}…")
print(f"\nvan al packet (no pasan la puerta): {len(no)} → {[x['modelo'] for x in no]}")
