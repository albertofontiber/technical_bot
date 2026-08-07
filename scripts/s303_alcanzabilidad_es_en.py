#!/usr/bin/env python3
"""s303 — ¿Es ALCANZABLE un documento en INGLÉS desde una pregunta en ESPAÑOL?

Por qué existe. s303 ingirió 2 manuales que solo existen en inglés (997-412 Sinóptico
IDR-M · 997-415 actualización del panel ID50). El corpus es ES-dominante y los técnicos
preguntan en español; el hueco de vocabulario ES↔EN es un lever MEDIDO del proyecto
(DEC-085). Así que meterlos en el corpus no prueba que sirvan: hay que medir si el canal
los trae ante una pregunta real, en vez de asumirlo.

Qué mide. Para cada pregunta (en español, y su gemela en inglés como CONTROL), corre el
retrieval de producción y comprueba si el documento objetivo aparece en el POOL y, después
del rerank, en la EVIDENCIA SERVIDA — que es lo que ve el generador. La pareja ES/EN aísla
la variable idioma: si el documento sale con la pregunta inglesa pero no con la española,
el fallo es de vocabulario, no de contenido ni de ingesta.

Qué NO mide. Ni PASS ni calidad de respuesta: no llama al generador (coste ~0).

Uso:  python scripts/s303_alcanzabilidad_es_en.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

from scripts.factlevel_assessment import DEMO_FLAGS, _assert_demo_flags  # noqa: E402

_assert_demo_flags()

from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402

# (documento objetivo, pregunta ES, pregunta EN de control)
CASOS = [
    ("997-415",
     "¿cómo actualizo el software del panel ID50?",
     "how do I upgrade the ID50 single loop panel software?"),
    ("997-415",
     "procedimiento de actualización de firmware en una central de un solo lazo ID50",
     "single loop panel firmware upgrade procedure ID50"),
    ("997-412",
     "¿cómo se instala y pone en marcha el sinóptico IDR-M?",
     "how to install and commission the IDR-M mimic?"),
    ("997-412",
     "conexionado y puesta en marcha del panel repetidor sinóptico IDR-M",
     "IDR-M mimic wiring and commissioning"),
]


def _fuente(ch: dict) -> str:
    return str(ch.get("source_file") or ch.get("document_id") or "?")


def _sonda(pregunta: str, objetivo: str) -> dict:
    pool = retrieve_chunks(pregunta)
    modelos = extract_product_models(pregunta)
    servida = rerank_chunks(pregunta, list(pool), target_models=modelos or None)
    en_pool = [i for i, ch in enumerate(pool) if objetivo.lower() in _fuente(ch).lower()]
    en_servida = [i for i, ch in enumerate(servida)
                  if objetivo.lower() in _fuente(ch).lower()]
    return {"pool_size": len(pool), "servida_size": len(servida),
            "modelos_detectados": modelos,
            "en_pool": en_pool, "en_servida": en_servida}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("s303 — alcanzabilidad ES→documento EN (los 2 manuales recién ingeridos)")
    print(f"chunks: {os.environ.get('CHUNKS_TABLE', '(default)')}\n")

    filas = []
    for objetivo, q_es, q_en in CASOS:
        r_es = _sonda(q_es, objetivo)
        r_en = _sonda(q_en, objetivo)
        filas.append({"objetivo": objetivo, "pregunta_es": q_es, "pregunta_en": q_en,
                      "es": r_es, "en": r_en})
        print(f"── {objetivo} ──")
        print(f"   ES «{q_es}»")
        print(f"      pool={r_es['pool_size']:3d} · en_pool={r_es['en_pool'] or 'NO'} "
              f"· SERVIDA={r_es['en_servida'] or 'NO'} · modelos={r_es['modelos_detectados']}")
        print(f"   EN «{q_en}»")
        print(f"      pool={r_en['pool_size']:3d} · en_pool={r_en['en_pool'] or 'NO'} "
              f"· SERVIDA={r_en['en_servida'] or 'NO'} · modelos={r_en['modelos_detectados']}")

    servido_es = sum(1 for f in filas if f["es"]["en_servida"])
    servido_en = sum(1 for f in filas if f["en"]["en_servida"])
    pool_es = sum(1 for f in filas if f["es"]["en_pool"])
    print("\n--- veredicto ---")
    print(f"servido con pregunta ES : {servido_es}/{len(filas)}  (en pool: {pool_es}/{len(filas)})")
    print(f"servido con pregunta EN : {servido_en}/{len(filas)}")
    if servido_es == len(filas):
        print("=> ALCANZABLE en español: la ingesta paga sin trabajo extra.")
    elif servido_es == 0 and servido_en > 0:
        print("=> HUECO DE IDIOMA CONFIRMADO: el documento solo se alcanza preguntando en")
        print("   inglés. Ingerirlo NO basta — necesita el mecanismo que DEC-085 midió que")
        print("   paga (extracción→enunciados) o un puente de vocabulario ES↔EN.")
    elif servido_es == 0 and servido_en == 0:
        print("=> NO ALCANZABLE en NINGÚN idioma: el problema no es el idioma. Sospechar")
        print("   de la identidad/metadatos del documento (product_model) o del chunking.")
    else:
        print("=> PARCIAL: alcanzable en unas formulaciones y no en otras. Detalle arriba.")

    destino = "evals/s303_alcanzabilidad_es_en_v1.json"
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump({"probe": "s303_alcanzabilidad_es_en_v1",
                   "ts": datetime.now(timezone.utc).isoformat(),
                   "chunks_table": os.environ.get("CHUNKS_TABLE"),
                   "servido_es": servido_es, "servido_en": servido_en,
                   "casos": filas}, fh, ensure_ascii=False, indent=2)
    print(f"\nrecibo: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
