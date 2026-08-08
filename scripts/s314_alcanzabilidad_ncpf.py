#!/usr/bin/env python3
"""s314 — ¿Es ALCANZABLE el manual NC-PFx recién ingestado desde preguntas reales?

Gemela de s303_alcanzabilidad_es_en.py para el lote Casmar/Kidde etapa 1: el gap
nació de una pregunta ORGÁNICA de Alberto («¿no tienes el manual de instalación o
programación del NC-PF2?») — meter el manual en el corpus no prueba que sirva;
hay que medir si el canal lo trae ante esa pregunta.

Qué mide: para cada pregunta, corre el retrieval de producción (flags-demo) y
comprueba si algún chunk del documento objetivo (por source_file) aparece en el
POOL y en la EVIDENCIA tras rerank. No llama al generador (coste ~0).

Uso:  python scripts/s314_alcanzabilidad_ncpf.py
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

# (token del source_file objetivo, pregunta)
CASOS = [
    ("mi_kidde_nc_pfx", "¿cómo se instala la central NC-PF2?"),
    ("mi_kidde_nc_pfx", "¿cómo programo un retardo de sirenas en la central NC-PF2?"),
    ("mi_kidde_nc_pfx", "conexión de las zonas de detección en la NC-PF4"),
    ("g_uso_kidde_nc_pfx", "¿cómo silencio la sirena en la central NC-PF2?"),
    ("g_inst_kidde_nc_pfx", "guía de instalación de la NC-PF8"),
]


def _fuente(ch: dict) -> str:
    return str(ch.get("source_file") or ch.get("document_id") or "?")


def main() -> None:
    filas = []
    for objetivo, pregunta in CASOS:
        pool = retrieve_chunks(pregunta)
        modelos = extract_product_models(pregunta)
        evidencia = rerank_chunks(pregunta, list(pool), target_models=modelos or None)
        en_pool = [c for c in pool if objetivo in _fuente(c).lower()]
        en_evid = [c for c in evidencia if objetivo in _fuente(c).lower()]
        filas.append({"pregunta": pregunta, "objetivo": objetivo,
                      "modelos_detectados": modelos,
                      "pool": len(en_pool), "pool_total": len(pool),
                      "evidencia": len(en_evid), "evidencia_total": len(evidencia)})
        print(f"{'✓' if en_evid else ('~' if en_pool else '✗')} "
              f"pool {len(en_pool)}/{len(pool)} · evidencia {len(en_evid)}/{len(evidencia)} "
              f"· modelos={modelos} · {pregunta}")

    servidas = sum(1 for f in filas if f["evidencia"])
    en_pool_n = sum(1 for f in filas if f["pool"])
    print(f"\nRESUMEN: {servidas}/{len(filas)} llegan a EVIDENCIA, {en_pool_n}/{len(filas)} al POOL")
    out = {"ts": datetime.now(timezone.utc).isoformat(), "flags": "DEMO_FLAGS",
           "casos": filas, "servidas": servidas, "en_pool": en_pool_n}
    ruta = "evals/s314_alcanzabilidad_ncpf_v1.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Recibo: {ruta}")


if __name__ == "__main__":
    main()
