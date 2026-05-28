#!/usr/bin/env python3
"""Audit del catálogo de product_model en la tabla activa (CHUNKS_TABLE).

SOLO LECTURA. Cuantifica el gap de cobertura entre el MODEL_PATTERN hardcoded
(src/rag/retriever.py) y los product_model que realmente existen en el corpus.
Es el Paso 0 del refactor "catálogo dinámico" (Fase 2): la viabilidad del
catálogo depende de la calidad del dato en product_model.

Salida:
  - nº de chunks, nº de product_model distintos, nº "unknown"/vacío
  - distintos por fabricante
  - cuántos product_model reconocería el MODEL_PATTERN actual vs no (= el gap)
  - muestra de los NO reconocidos (los productos hoy invisibles al retriever)
  - heurística de "forma sospechosa" (descriptivos / sin dígitos) para estimar
    cuánta curación necesitaría un catálogo construido a ciegas

Uso (PowerShell):
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/audit_product_model_catalog.py
Uso (bash):
    CHUNKS_TABLE=chunks_v2 python scripts/audit_product_model_catalog.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.rag.retriever import extract_product_models  # noqa: E402

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.environ.get("CHUNKS_TABLE", "chunks")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

PAGE = 1000


def fetch_all() -> list[dict]:
    """Pagina todas las filas (product_model, manufacturer). Order=id para
    paginación estable (evita el bug de truncado por insertion-order)."""
    rows: list[dict] = []
    offset = 0
    while True:
        resp = httpx.get(
            f"{URL}/rest/v1/{TABLE}",
            headers=H,
            params={
                "select": "product_model,manufacturer",
                "order": "id",
                "limit": str(PAGE),
                "offset": str(offset),
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows


def looks_suspicious(pm: str) -> bool:
    """Heurística genérica (no por fabricante) de 'no parece un código de modelo':
    contiene espacios (probable descriptivo) o no tiene ningún dígito."""
    if " " in pm.strip():
        return True
    if not any(ch.isdigit() for ch in pm):
        return True
    return False


def main() -> None:
    print(f"== Audit product_model catalog · tabla='{TABLE}' ==\n")
    rows = fetch_all()
    total = len(rows)

    pm_counts: Counter[str] = Counter()
    pm_to_mfrs: dict[str, set[str]] = defaultdict(set)
    empty = 0
    for r in rows:
        pm = (r.get("product_model") or "").strip()
        mfr = (r.get("manufacturer") or "unknown").strip()
        if not pm or pm.lower() == "unknown":
            empty += 1
            continue
        pm_counts[pm] += 1
        pm_to_mfrs[pm].add(mfr)

    distinct = sorted(pm_counts)
    print(f"chunks totales ............ {total}")
    print(f"chunks sin modelo/unknown . {empty} ({empty/total:.1%})")
    print(f"product_model distintos ... {len(distinct)}\n")

    # Distintos por fabricante (un modelo puede aparecer en >1 mfr → se cuenta en cada uno)
    by_mfr: Counter[str] = Counter()
    for pm in distinct:
        for m in pm_to_mfrs[pm]:
            by_mfr[m] += 1
    print("Modelos distintos por fabricante:")
    for m, n in by_mfr.most_common():
        print(f"  {m:<28} {n}")
    print()

    # Cobertura del MODEL_PATTERN actual: ¿lo detectaría como query?
    detected = [pm for pm in distinct if extract_product_models(pm)]
    undetected = [pm for pm in distinct if not extract_product_models(pm)]
    cov = len(detected) / len(distinct) if distinct else 0
    det_chunks = sum(pm_counts[pm] for pm in detected)
    und_chunks = sum(pm_counts[pm] for pm in undetected)
    indexed = det_chunks + und_chunks
    print("Cobertura del MODEL_PATTERN hardcoded (sobre product_model):")
    print(f"  detectados ... {len(detected):>4}/{len(distinct)} modelos ({cov:.1%})")
    print(f"  NO detectados  {len(undetected):>4}/{len(distinct)} modelos  <-- gap")
    if indexed:
        print(f"  por volumen de chunks: detectados {det_chunks} ({det_chunks/indexed:.1%}) · "
              f"invisibles {und_chunks} ({und_chunks/indexed:.1%})")
    print()

    # Calidad del dato: cuántos NO-detectados parecen ruido vs modelos reales
    susp = [pm for pm in undetected if looks_suspicious(pm)]
    clean_gap = [pm for pm in undetected if not looks_suspicious(pm)]
    print("Calidad del dato entre los NO detectados:")
    print(f"  forma sospechosa (descriptivo / sin dígitos) . {len(susp)}")
    print(f"  forma de modelo plausible (gap real) ......... {len(clean_gap)}")
    print()

    print("Top 40 NO detectados con forma de modelo (por nº de chunks) — gap real:")
    for pm in sorted(clean_gap, key=lambda x: pm_counts[x], reverse=True)[:40]:
        mfrs = ",".join(sorted(pm_to_mfrs[pm]))
        print(f"  {pm_counts[pm]:>5}  {pm:<32} [{mfrs}]")
    print()

    print("Muestra 20 'sospechosos' (¿ruido en product_model?):")
    for pm in sorted(susp, key=lambda x: pm_counts[x], reverse=True)[:20]:
        mfrs = ",".join(sorted(pm_to_mfrs[pm]))
        print(f"  {pm_counts[pm]:>5}  {pm!r:<40} [{mfrs}]")


if __name__ == "__main__":
    main()
