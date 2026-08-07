#!/usr/bin/env python3
"""s304 — ¿Llega la identidad ADJUDICADA al momento de responder?

El hallazgo que lo motiva (pregunta de Alberto, s303). El `doc_map.jsonl` dice que
`CAD-250_Manual-Configuracion-MC-380-es-2026-c` cubre `detnov:cad-171` como **primary**
(revisión c: «Adaptación para CAD-171 y CAD-201»). Pero sus **136 chunks, sin excepción,
llevan `product_model = CAD-250`**. Y el generador lee el CHUNK, no el mapa
(`generator.py:704` → `chunk.get("product_model")`). Consecuencia real y medida: ante
«¿cómo accedo al menú avanzado de la CAD-171?», el bot tuvo delante el párrafo correcto
pero etiquetado con OTRO modelo, y —razonablemente— no quiso trasladarlo.

Es decir: la adjudicación de identidad que costó sesiones (s83, s91, s278…) puede estar
muriendo en la frontera entre el catálogo y lo que se sirve.

Qué mide (y qué NO). Para cada documento del `doc_map` con identidad adjudicada, compara
los ids del mapa contra los `product_model` DISTINTOS de sus chunks en `chunks_v2`, y
clasifica:
  · OK          — todo id primario del mapa aparece en los product_model del documento;
  · HUÉRFANO    — el documento tiene ids primarios que NINGÚN chunk refleja (la clase del
                  MC-380: el bot no puede saber que ese manual cubre esa central);
  · SIN CHUNKS  — el documento está en el mapa pero no en `chunks_v2` (fuera de alcance).
NO mide impacto en respuestas: dimensiona la brecha, no la traduce a PASS.

Uso:  python scripts/s304_identidad_propagacion.py
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

DOC_MAP = os.path.join("data", "catalog", "doc_map.jsonl")
TABLA = os.environ.get("CHUNKS_TABLE", "chunks_v2")
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def _norm(s: str) -> str:
    """Compara identificadores tolerando prefijo de fabricante y separadores.

    `detnov:cad-171` y `CAD-171` son el MISMO modelo; `CAD-250-P` y `CAD-250` NO lo son
    (variantes distintas), así que solo se normaliza mayúsculas y separadores — no se
    poda ningún sufijo (la lección de los `_NN` del cruce s303: podar fabrica falsos
    positivos que ESCONDEN la brecha que buscamos).
    """
    s = s.split(":")[-1]
    return re.sub(r"[\s_]+", "-", s.strip().lower())


def _product_models_por_documento() -> dict[str, set[str]]:
    """`source_file` → conjunto de `product_model` distintos, paginando el REST."""
    salida: dict[str, set[str]] = collections.defaultdict(set)
    offset, page = 0, 1000
    with httpx.Client(timeout=60.0) as cli:
        while True:
            r = cli.get(f"{SUPABASE_URL}/rest/v1/{TABLA}", headers=_H,
                        params={"select": "source_file,product_model",
                                "limit": str(page), "offset": str(offset)})
            r.raise_for_status()
            filas = r.json()
            for f in filas:
                if f.get("source_file"):
                    salida[f["source_file"]].add(f.get("product_model") or "(sin modelo)")
            if len(filas) < page:
                break
            offset += page
            print(f"  ...{offset} filas", flush=True)
    return salida


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("s304 — propagación de identidad: doc_map (adjudicado) vs product_model (servido)")
    print(f"tabla: {TABLA}\n")

    mapa: dict[str, list[dict]] = {}
    with open(DOC_MAP, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            d = json.loads(linea)
            if d.get("source_file"):
                mapa[d["source_file"]] = d.get("entries") or []
    print(f"doc_map: {len(mapa)} documentos con identidad adjudicada")

    print("leyendo product_model de la base...")
    modelos = _product_models_por_documento()
    print(f"corpus:  {len(modelos)} documentos con chunks\n")

    ok, huerfanos, sin_chunks = [], [], []
    for fuente, entradas in mapa.items():
        primarios = [e["id"] for e in entradas if e.get("role") == "primary"]
        if not primarios:
            continue
        if fuente not in modelos:
            sin_chunks.append({"source_file": fuente, "primarios": primarios})
            continue
        servidos = {_norm(m) for m in modelos[fuente]}
        faltan = [p for p in primarios if _norm(p) not in servidos]
        fila = {"source_file": fuente, "primarios": primarios,
                "product_models_en_chunks": sorted(modelos[fuente]),
                "primarios_NO_reflejados": faltan,
                "n_modelos_chunk": len(modelos[fuente])}
        (huerfanos if faltan else ok).append(fila)

    con_identidad = len(ok) + len(huerfanos)
    print("--- resultado ---")
    print(f"documentos con identidad primaria y chunks : {con_identidad}")
    print(f"  OK (todo primario se refleja en chunks)  : {len(ok)}")
    print(f"  HUÉRFANOS (algún primario invisible)     : {len(huerfanos)}"
          + (f"  = {100*len(huerfanos)/con_identidad:.1f}%" if con_identidad else ""))
    print(f"  en el mapa pero sin chunks               : {len(sin_chunks)}")

    ids_perdidos = sum(len(h["primarios_NO_reflejados"]) for h in huerfanos)
    print(f"\nidentidades primarias que NO llegan al generador: {ids_perdidos}")

    print("\n--- los 15 peores (más identidades perdidas) ---")
    for h in sorted(huerfanos, key=lambda x: -len(x["primarios_NO_reflejados"]))[:15]:
        print(f"  {h['source_file'][:58]:58s}")
        print(f"      chunks dicen: {h['product_models_en_chunks']}")
        print(f"      NO llegan   : {h['primarios_NO_reflejados']}")

    destino = "evals/s304_identidad_propagacion_v1.json"
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump({"probe": "s304_identidad_propagacion_v1",
                   "ts": datetime.now(timezone.utc).isoformat(),
                   "tabla": TABLA,
                   "resumen": {"con_identidad_y_chunks": con_identidad,
                               "ok": len(ok), "huerfanos": len(huerfanos),
                               "sin_chunks": len(sin_chunks),
                               "identidades_primarias_perdidas": ids_perdidos},
                   "huerfanos": huerfanos, "sin_chunks": sin_chunks},
                  fh, ensure_ascii=False, indent=2)
    print(f"\nrecibo: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
