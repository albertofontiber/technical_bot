#!/usr/bin/env python3
"""Fix AC-220 — el Manual de Configuración ES de la PEARL estaba mal etiquetado.

Problema (verificado s36/DEC-005, aplicado s38): los 124 chunks de
'997-671-005-3_Configuration_ES' (Manual de configuración de la central Notifier
PEARL) tenían product_model='AC-220' — un código que NO corresponde a ningún
producto real (familia del bug B5: código de doc mal extraído como modelo).
Efecto: la ruta modelo/keyword del retriever (imatch 'PEARL') NO los recuperaba,
así que para "¿cómo se programa ... en la PEARL?" el manual de configuración
—donde vive la respuesta— era INVISIBLE (hp017 = over-admit, FALLO en s37).

Fix: product_model 'AC-220' -> 'Pearl' (misma forma que el manual hermano
997-669 Instal-Comm). Medido (HyDE-off, pool-15 determinista): los chunks del
manual de configuración pasan de 0 -> 9 en el pool de hp017 (rank 1); el bot
pasa de over-admitir a RESPONDER citando el manual correcto (causa-efecto,
Apéndice 5).

Alcance n=1 verificado: 'AC-220' solo existía en este source_file (124 chunks);
ningún producto real lo usa -> cero colateral.

Aplicado a producción (chunks_v2) el 2026-06-01 vía SQL directo. Este script es
el RECORD idempotente + re-runnable (p.ej. si se re-ingesta el corpus y el bug
B5 reaparece). Es idempotente: si ya está aplicado, no hace nada.

ROLLBACK:
    UPDATE chunks_v2 SET product_model='AC-220'
    WHERE source_file='997-671-005-3_Configuration_ES';

RAÍZ (fuera de alcance aquí): la causa está en la extracción de metadata B5
(asignó el código de doc como modelo). El fix definitivo es en el pipeline de
ingest (src/reingest/metadata.py / #9). Este script corrige el dato YA en prod.

Uso:
    python scripts/fix_ac220_product_model.py            # dry-run (estado actual)
    python scripts/fix_ac220_product_model.py --apply     # aplica el UPDATE
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.getenv("CHUNKS_TABLE", "chunks_v2")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

SOURCE_FILE = "997-671-005-3_Configuration_ES"
OLD = "AC-220"
NEW = "Pearl"


def _count(product_model: str) -> int:
    r = httpx.get(
        f"{URL}/rest/v1/{TABLE}",
        headers=H,
        params={
            "source_file": f"eq.{SOURCE_FILE}",
            "product_model": f"eq.{product_model}",
            "select": "id",
        },
        timeout=15.0,
    )
    r.raise_for_status()
    return len(r.json())


def main() -> int:
    apply = "--apply" in sys.argv
    n_old = _count(OLD)
    n_new = _count(NEW)
    print(f"Tabla {TABLE} | {SOURCE_FILE}")
    print(f"  product_model='{OLD}': {n_old} chunks")
    print(f"  product_model='{NEW}': {n_new} chunks")

    if n_old == 0:
        print("\nNada que corregir (ya aplicado o no presente).")
        return 0
    if not apply:
        print(f"\n[dry-run] Re-ejecuta con --apply para: '{OLD}' -> '{NEW}' ({n_old} chunks).")
        return 0

    r = httpx.patch(
        f"{URL}/rest/v1/{TABLE}",
        headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"},
        params={
            "source_file": f"eq.{SOURCE_FILE}",
            "product_model": f"eq.{OLD}",
        },
        json={"product_model": NEW},
        timeout=30.0,
    )
    r.raise_for_status()
    print(f"\nAplicado: {n_old} chunks '{OLD}' -> '{NEW}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
