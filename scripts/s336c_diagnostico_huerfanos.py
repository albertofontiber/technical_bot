#!/usr/bin/env python
"""s336c — ¿QUÉ bloquea a cada manual huérfano? Una herramienta por bucket.

Nace de una pregunta de Alberto («con una clave de Gemini podríamos rascar los
manuales que ahora no conseguimos») y de que la sonda multimodal que monté para
contestarla estaba midiendo otra cosa. Consume el recibo de `s336b` (que lee el
PDF original de cada huérfano) y le añade las dos capas que faltaban:

  1. **¿cita el CANÓNICO?** — no «algún token». R19: que el token esté en el
     texto no es producto-hood; `NAS`, `TG`, `RHistorico.exe` o «modelo
     antideflagrante» pasan la cita y no identifican nada. El canónico es el
     string que indexa el detector, así que es el único que zanja.
  2. **¿está también en `chunks_v2`?** — sin esto, «está en el PDF» invita a
     concluir «lo perdimos al extraer», que es falso en 48 de 49 casos: el dato
     YA está en el corpus y lo que falta es promover el candidate.

El punto de todo esto: **decidir la herramienta correcta por bucket**, y en
particular medir cuántos huérfanos puede pagar de verdad un lector multimodal.
NADA se aplica.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CENSO = ROOT / "evals/s336b_censo_pdf_huerfanos.json"
EVID = ROOT / "evals/s334_huerfanos_evidencia_v1.json"
SALIDA = ROOT / "evals/s336c_diagnostico_huerfanos.json"
TABLA = "chunks_v2"

_spec = importlib.util.spec_from_file_location(
    "s336b", ROOT / "scripts/s336b_censo_pdf_huerfanos.py")
_s336b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s336b)
cita = _s336b.cita

#: Qué herramienta paga cada bucket. El orden es el de decisión.
HERRAMIENTA = {
    "REDIRECT_PENDIENTE_R21":  "adjudicación de Alberto (R21: resolver H o G nunca es mecánico)",
    "PROMOVIBLE":              "promoción con cita verificada (R4) — el dato ya está en chunks",
    "EXTRACCION_LO_PERDIO":    "re-extracción: está en el PDF y NO en chunks",
    "SOLO_NUMERO_DE_REFERENCIA": "adjudicación R4: ¿vale el nº de referencia del fabricante como cita?",
    "CANONICO_DIGIT_ONLY":     "irreducible: el detector excluye los digit-only a propósito",
    "NI_CANONICO_NI_REFERENCIA": "el manual no nombra su producto: ningún lector lo cambia",
    "LECTOR_MULTIMODAL":       "PDF escaneado: AQUÍ, y sólo aquí, manda un lector multimodal / OCR",
    "SIN_PDF":                 "no hay PDF que leer",
}


def texto_en_chunks(c: httpx.Client, did: str) -> str | None:
    out, desde = [], 0
    while True:
        # `order` explícito: sin él PostgREST no garantiza orden estable entre
        # rangos y la paginación salta filas (mismo bug que en s336b/s336g).
        r = c.get(f"{SB}/{TABLA}", headers={**H, "Range-Unit": "items",
                  "Range": f"{desde}-{desde+499}"},
                  params={"select": "content", "document_id": f"eq.{did}",
                          "order": "id"})
        # 200 **y 206**: PostgREST devuelve 206 cuando el rango trunca.
        if r.status_code not in (200, 206):
            return None
        j = r.json()
        out += [x.get("content") or "" for x in j]
        if len(j) < 500:
            return "\n".join(out)
        desde += 500


def main() -> int:
    if not CENSO.exists():
        print(f"falta {CENSO}: corre antes `scripts/s336b_censo_pdf_huerfanos.py`")
        return 2
    censo = json.loads(CENSO.read_text("utf-8"))
    ev = json.loads(EVID.read_text("utf-8"))
    clase = {it["id"]: it.get("clase") for l in ev["lotes"].values() for it in l["ids"]}
    cat = cs.load()

    filas = []
    with httpx.Client(timeout=180) as c:
        for f in censo["filas"]:
            canon = [cat.products[i]["canonical_model"] for i in f["ids"] if i in cat.products]
            citados = set(f.get("tokens_citados", []))
            canon_citado = [x for x in canon if x in citados]
            detectable = [x for x in canon_citado if re.search(r"[A-Za-z]", x)]
            # nº de referencia: sin letras, ≥5 dígitos, y ANCLADO también en el
            # nombre del fichero (doble ancla — R8 dice que el fichero miente solo)
            refs = [t for t in citados if not re.search(r"[A-Za-z]", t)
                    and len(re.sub(r"\D", "", t)) >= 5
                    and re.sub(r"\D", "", t) in re.sub(r"\D", "", f["source_file"])]

            if f["veredicto"] == "SIN_PDF":
                b = "SIN_PDF"
            elif f["veredicto"] == "PDF_SIN_TEXTO":
                b = "LECTOR_MULTIMODAL"
            elif f["veredicto"] == "LECTURA_FALLIDA":
                b = "LECTOR_MULTIMODAL"
            elif detectable:
                t = texto_en_chunks(c, f["document_id"])
                en_chunks = bool(t) and any(cita(t, x) for x in detectable)
                if any(i.startswith("unresolved:") for i in f["ids"]):
                    b = "REDIRECT_PENDIENTE_R21"
                else:
                    b = "PROMOVIBLE" if en_chunks else "EXTRACCION_LO_PERDIO"
                f["en_chunks"] = en_chunks
            elif canon_citado:
                b = "CANONICO_DIGIT_ONLY"
            elif refs:
                b = "SOLO_NUMERO_DE_REFERENCIA"
                f["referencias"] = refs
            else:
                b = "NI_CANONICO_NI_REFERENCIA"
            f["bucket"] = b
            f["canonicos"] = canon
            f["canonico_citado"] = canon_citado
            f["clases_evidencia"] = sorted({clase.get(i) or "sin_clase" for i in f["ids"]})
            filas.append(f)

    cuenta = Counter(f["bucket"] for f in filas)
    print(f"=== QUÉ BLOQUEA A CADA UNO DE LOS {len(filas)} HUÉRFANOS ===\n")
    for k in HERRAMIENTA:
        if cuenta.get(k):
            print(f"  {cuenta[k]:3d}  {k:28s} {HERRAMIENTA[k]}")
    resto = {k: v for k, v in cuenta.items() if k not in HERRAMIENTA}
    if resto:
        print(f"  sin clasificar: {resto}")
    mm = cuenta.get("LECTOR_MULTIMODAL", 0)
    print(f"\n  → un lector multimodal (Gemini/Claude/GPT) paga {mm} de {len(filas)} "
          f"huérfanos ({100*mm//max(len(filas),1)}%).")
    print(f"  → {cuenta.get('REDIRECT_PENDIENTE_R21',0) + cuenta.get('SOLO_NUMERO_DE_REFERENCIA',0)} "
          f"esperan una ADJUDICACIÓN, no una herramienta.")

    SALIDA.write_text(json.dumps(
        {"que_es": "s336c · diagnóstico por bucket de los manuales huérfanos: qué "
                   "herramienta paga cada uno. Consume el recibo de s336b (lectura del "
                   "PDF original) y añade ¿cita el CANÓNICO? y ¿está en chunks_v2? "
                   "NADA aplicado.",
         "tabla_chunks": TABLA, "n": len(filas),
         "buckets": dict(cuenta), "herramienta_por_bucket": HERRAMIENTA,
         "filas": filas}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
