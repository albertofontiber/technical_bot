#!/usr/bin/env python3
"""s303 — La sonda que CLASIFICA el único fallo orgánico: ¿retrieval o síntesis?

Contexto. El bot falló la ruta al menú AVANZADO de la CAD-171 (DEC-176, `query_logs`
2-ago 16:05Z): teniendo AVANZADO en la evidencia servida, encabezó con la ruta de GENERAL.
Se archivó como fallo de SELECCIÓN, clase `hp011#2` — que DEC-173 midió NO ALCANZABLE
(oráculo K=5, 0/5→0/5).

Lo que s302 cambió. El recibo daba por AUSENTE la «Guía Avanzada de Configuración». Es
FALSO: `CAD-250_Manual-Configuracion-MC-380-es-2026-c` está ingestado, mapeado a
`detnov:cad-171` en `doc_map.jsonl`, y su §5.4 (p.29) documenta literalmente
«AJUSTES (Menú principal) > AVANZADO (Submenú)» con sus 3 pestañas. Así que el caso puede
tener una capa MÁS, nunca medida: **¿estaba ese contenido en el pool?**

Qué decide esta sonda (y qué NO).
  · Si el MC-380 NO entra en el pool  ⇒ el caso es (también) RETRIEVAL-MISS de documento
    vecino en la misma familia, y el NO-GO de `hp011#2` NO le aplica sin más — aquel se
    midió con la evidencia ideal de OTRO hecho. Familia de lever: doc-local / vecino
    estructural (s104/s107), que ya está construida y default-off.
  · Si SÍ entra y el bot igualmente respondió GENERAL ⇒ es SÍNTESIS/SELECCIÓN pura, con
    la evidencia correcta delante: refuerza el techo y cierra la puerta a retrieval.
  · NO mide PASS ni calidad de respuesta. NO llama al generador: cero coste de generación.
    Solo embedding + consulta a `chunks_v2` (céntimos).

Honestidad de la réplica: se replica la CONFIGURACIÓN de producción vía DEMO_FLAGS (la
misma fuente que el assessment estandarizado), no el momento exacto de la consulta — el
corpus pudo cambiar desde el 2-ago. Se estampa el conteo de chunks del MC-380 vivos hoy
para que la comparación sea auditable.

Uso:  python scripts/s303_cad171_pool_probe.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# La MISMA configuración que la demo (fuente única: el assessment estandarizado). Se
# importa el dict, no se re-declara: un segundo juego de flags mediría otra stack.
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

from scripts.factlevel_assessment import DEMO_FLAGS, _assert_demo_flags  # noqa: E402

_assert_demo_flags()

from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402

# La consulta LITERAL del fallo orgánico (recibo s294, verificada contra query_logs).
CONSULTA = "¿cómo puedo acceder al menú de configuración avanzada de la CAD-171?"

# El documento que s302 destapó: contiene la ruta pedida en su §5.4 (p.29).
DOC_OBJETIVO = "CAD-250_Manual-Configuracion-MC-380"
# El manual que SÍ se sirvió aquel día (los 3 diagramas de navegación).
DOC_SERVIDO = "Manual_CAD-171-MI-716"

# Marcadores del contenido que la respuesta correcta necesitaba.
MARCADORES = ("AVANZADO", "SISTEMA", "REINICIAR")


def _fuente(chunk: dict) -> str:
    return str(chunk.get("source_file") or chunk.get("document_id") or "?")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("s303 — sonda de clasificación del fallo orgánico (DEC-176)")
    print(f"consulta: {CONSULTA}")
    print(f"config:   DEMO_FLAGS ({len(DEMO_FLAGS)} flags, misma fuente que el assessment)")
    print(f"chunks:   {os.environ.get('CHUNKS_TABLE', '(default)')}\n")

    pool = retrieve_chunks(CONSULTA)
    print(f"POOL (retrieval): {len(pool)} chunks")

    # LA ETAPA QUE FALTABA. El pool NO es la evidencia servida: el rerank recorta antes de
    # generar. Preguntar solo por el pool responde «era recuperable», que NO es la pregunta
    # — la pregunta es si el bot lo tuvo DELANTE.
    modelos = extract_product_models(CONSULTA)
    servida = rerank_chunks(CONSULTA, list(pool), target_models=modelos or None)
    print(f"SERVIDA (post-rerank): {len(servida)} chunks · modelos={modelos}\n")

    objetivo, servido = [], []
    for i, ch in enumerate(pool):
        fuente = _fuente(ch)
        if DOC_OBJETIVO.lower() in fuente.lower():
            objetivo.append((i, ch))
        if DOC_SERVIDO.lower() in fuente.lower():
            servido.append((i, ch))

    print("--- ranking del pool (fuente · página · similitud) ---")
    for i, ch in enumerate(pool):
        marca = ""
        if DOC_OBJETIVO.lower() in _fuente(ch).lower():
            marca = "  <<< MC-380 (el que documenta AVANZADO)"
        elif DOC_SERVIDO.lower() in _fuente(ch).lower():
            marca = "  <-- MI-716 (el servido aquel día)"
        sim = ch.get("similarity")
        sim_txt = f"{sim:.4f}" if isinstance(sim, (int, float)) else "-"
        print(f"{i:3d}. {_fuente(ch)[:58]:58s} p.{str(ch.get('page_number') or '-'):>4s} "
              f"sim={sim_txt}{marca}")

    def _con_detalle(filas):
        return [(i, ch) for i, ch in enumerate(filas)
                if all(m.lower() in str(ch.get("content", "")).lower() for m in MARCADORES)]

    con_detalle = _con_detalle(pool)              # recuperable
    detalle_servido = _con_detalle(servida)       # DELANTE del generador — lo que decide
    objetivo_servido = [(i, ch) for i, ch in enumerate(servida)
                        if DOC_OBJETIVO.lower() in _fuente(ch).lower()]

    print("\n--- evidencia SERVIDA (post-rerank: lo que ve el generador) ---")
    for i, ch in enumerate(servida):
        marca = ""
        if DOC_OBJETIVO.lower() in _fuente(ch).lower():
            marca = "  <<< MC-380"
        if any(i == j for j, _ in detalle_servido):
            marca += "  ***EL DETALLE DEL §5.4***"
        print(f"{i:3d}. {_fuente(ch)[:58]:58s} p.{str(ch.get('page_number') or '-'):>4s}{marca}")

    print("\n--- veredicto ---")
    print(f"chunks del MC-380 en el pool : {len(objetivo)}"
          + (f"  (posiciones {[i for i, _ in objetivo]})" if objetivo else ""))
    print(f"chunks del MI-716 en el pool : {len(servido)}"
          + (f"  (posiciones {[i for i, _ in servido]})" if servido else ""))
    print(f"chunks con AVANZADO+SISTEMA+REINICIAR (el detalle del §5.4): {len(con_detalle)}"
          + (f"  (posiciones {[i for i, _ in con_detalle]})" if con_detalle else ""))

    print(f"chunks del MC-380 SERVIDOS   : {len(objetivo_servido)}"
          + (f"  (posiciones {[i for i, _ in objetivo_servido]})" if objetivo_servido else ""))
    print(f"detalle del §5.4 SERVIDO     : {len(detalle_servido)}"
          + (f"  (posiciones {[i for i, _ in detalle_servido]})" if detalle_servido else ""))

    if not objetivo:
        veredicto = "RETRIEVAL_MISS"
        print("\n=> RETRIEVAL-MISS de documento vecino: el MC-380 NO entra ni en el pool.")
        print("   Familia de lever: doc-local / vecino estructural (s104/s107).")
    elif con_detalle and not detalle_servido:
        veredicto = "RERANK_DROP"
        print("\n=> RERANK-DROP — la clase que NADIE había medido aquí: el detalle del §5.4")
        print("   ERA recuperable (está en el pool) pero el RERANK lo tira antes de generar.")
        print("   NO es techo de síntesis (el modelo nunca lo vio) NI retrieval-miss (el")
        print("   canal lo trajo). Familia: rerank / cobertura post-rerank — justo donde")
        print("   vive el trabajo doc-local de s104/s107, hoy default-off.")
    elif detalle_servido:
        veredicto = "SINTESIS"
        print("\n=> SÍNTESIS/SELECCIÓN pura: el detalle del §5.4 estaba DELANTE del generador")
        print("   y aun así respondió el elemento vecino. Refuerza el techo.")
    else:
        veredicto = "MIXTO"
        print("\n=> MIXTO: el MC-380 entra pero ningún chunk trae el detalle completo del")
        print("   §5.4 — el corte de chunking puede estar partiendo la tabla.")

    recibo = {
        "probe": "s303_cad171_pool_v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "consulta": CONSULTA,
        "chunks_table": os.environ.get("CHUNKS_TABLE"),
        "veredicto": veredicto,
        "pool_size": len(pool),
        "servida_size": len(servida),
        "mc380_en_pool": [i for i, _ in objetivo],
        "mi716_en_pool": [i for i, _ in servido],
        "chunks_con_detalle_5_4_en_pool": [i for i, _ in con_detalle],
        "mc380_servidos": [i for i, _ in objetivo_servido],
        "detalle_5_4_servido": [i for i, _ in detalle_servido],
        "servida": [
            {"rank": i, "source_file": _fuente(ch), "page": ch.get("page_number"),
             "content_head": str(ch.get("content", ""))[:180]}
            for i, ch in enumerate(servida)
        ],
        "pool": [
            {"rank": i, "source_file": _fuente(ch), "page": ch.get("page_number"),
             "similarity": ch.get("similarity"),
             "content_head": str(ch.get("content", ""))[:180]}
            for i, ch in enumerate(pool)
        ],
    }
    destino = "evals/s303_cad171_pool_probe_v1.json"
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(recibo, fh, ensure_ascii=False, indent=2)
    print(f"\nrecibo: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
