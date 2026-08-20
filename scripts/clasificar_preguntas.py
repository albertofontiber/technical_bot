# -*- coding: utf-8 -*-
"""Clasificador batch de preguntas (s326) — invocación manual con recibo.

Es el MISMO código que corre el seam del worker (`src/clasificacion.py`); este
script existe para las corridas que un humano decide: el backfill inicial tras
aplicar la 021, y la re-clasificación del histórico cuando la taxonomía sube de
versión (subir `version` en `config/taxonomia_preguntas.yaml` convierte todo
el histórico en pendiente — no hay modo «re-taxonomizar» aparte a propósito:
un solo camino, sin estados especiales).

Uso:
    python -m scripts.clasificar_preguntas --dry-run          # cuenta, no escribe
    python -m scripts.clasificar_preguntas --cap 500          # corrida real
    python -m scripts.clasificar_preguntas --receipt evals/s326_backfill_v1.json

Claves: SUPABASE_URL / SUPABASE_SERVICE_KEY (las del bot) y ANTHROPIC_API_KEY
(o ANTHROPIC_API_KEY_SCRIPTS, el nombre que usa el entorno cloud). Sin clave de
Anthropic clasifica SOLO por regla y cuenta el resto como `sin_llm` — corrida
honesta, no a medias en silencio.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clasificacion import (CAP_DEFECTO, MODELO_LLM,  # noqa: E402
                               Catalogo, ClasificacionNoDisponible,
                               correr_pendientes)
from src.rag.retriever import (classify_model_manufacturer,  # noqa: E402
                               get_manufacturers_by_docs,
                               resolve_manufacturer_alias)


def _catalogo() -> Catalogo:
    """El conocimiento de catálogo, inyectado (frontera raiz→rag: el módulo de
    clasificación no importa rag; sus llamadores sí pueden)."""
    return Catalogo(
        nombres=[nombre for nombre, _docs in get_manufacturers_by_docs()],
        marca_de_modelo=classify_model_manufacturer,
        resolver_alias=resolve_manufacturer_alias,
    )

#: Precios de Haiku 4.5 ($/MTok entrada, salida) para el coste ESTIMADO del
#: recibo. Estimación declarada, no contabilidad.
_PRECIO_ENTRADA = 1.00
_PRECIO_SALIDA = 5.00


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cap", type=int, default=CAP_DEFECTO,
                        help=f"máximo de filas a examinar (default {CAP_DEFECTO})")
    parser.add_argument("--dry-run", action="store_true",
                        help="clasifica pero NO escribe (recibo igual)")
    parser.add_argument("--modelo", default=MODELO_LLM,
                        help=f"modelo del LLM (default {MODELO_LLM})")
    parser.add_argument("--receipt", type=Path, default=None,
                        help="ruta donde volcar el recibo JSON")
    argumentos = parser.parse_args()

    api_key = (os.getenv("ANTHROPIC_API_KEY")
               or os.getenv("ANTHROPIC_API_KEY_SCRIPTS") or "")
    if not api_key:
        print("AVISO: sin ANTHROPIC_API_KEY — solo clasificación por regla; "
              "el resto quedará pendiente (sin_llm).")

    try:
        recibo = correr_pendientes(argumentos.cap, catalogo=_catalogo(),
                                   api_key=api_key or None,
                                   modelo=argumentos.modelo,
                                   dry_run=argumentos.dry_run)
    except ClasificacionNoDisponible as exc:
        print(f"NO DISPONIBLE: {exc}")
        print("¿Está aplicada migrations/021_query_clasificacion.sql y hay "
              "credenciales de Supabase en el entorno?")
        return 1

    recibo["coste_estimado_usd"] = round(
        recibo["tokens_entrada"] / 1e6 * _PRECIO_ENTRADA
        + recibo["tokens_salida"] / 1e6 * _PRECIO_SALIDA, 4)
    print(json.dumps(recibo, indent=2, ensure_ascii=False))
    if argumentos.receipt:
        argumentos.receipt.parent.mkdir(parents=True, exist_ok=True)
        argumentos.receipt.write_text(
            json.dumps(recibo, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"recibo → {argumentos.receipt}")
    if recibo["llm_fallos"]:
        print(f"AVISO: {recibo['llm_fallos']} fila(s) quedaron pendientes "
              f"(respuesta LLM inválida) — se reintentan en la próxima corrida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
