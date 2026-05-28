#!/usr/bin/env python3
"""Construye el snapshot curado del catálogo de modelos desde CHUNKS_TABLE.

Es el paso offline del refactor "catálogo dinámico" (Fase 2). Lee los
product_model de chunks_v2, aplica un gate de curación CONSERVADOR (precisión
primero), y escribe:
  - data/model_catalog.json  → consumido en runtime por src/rag/catalog.py
  - resumen + excluidos-con-motivo por stdout = la revisión humana (estilo
    fix_b5: nada entra al runtime sin que se pueda auditar qué y por qué).

Regla de inclusión (v1):
  incluir si  (lo detecta HOY el MODEL_PATTERN estático del retriever)
          OR  (manufacturer conocido  AND  pasa el guard anti-ruido)
  El bucket manufacturer=unknown se DIFIERE (tarea de datos #6: limpiar
  atribución + product_model basura). La unión con el patrón estático
  garantiza CERO regresión sobre los modelos que el bot ya reconoce.

Uso (PowerShell):
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/build_model_catalog.py
Uso (bash):
    CHUNKS_TABLE=chunks_v2 python scripts/build_model_catalog.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# El patrón estático del retriever = seed/whitelist hand-tuned. Lo usamos para
# la unión (no regresión). Tras T3 pasará a llamarse SEED_MODEL_PATTERN.
from src.rag.retriever import MODEL_PATTERN  # noqa: E402

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.environ.get("CHUNKS_TABLE", "chunks")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
PAGE = 1000

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "model_catalog.json",
)

# --- Guard anti-ruido (genérico, NO por fabricante) ---------------------------
_MONTHS = {
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO",
    "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
    "ENE", "FEB", "MAR", "ABR", "JUN", "JUL", "AGO", "SEP", "SEPT", "OCT", "NOV", "DIC",
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
    "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
    "JAN", "APR", "AUG", "DEC",
}


def is_date_like(pm: str) -> bool:
    """MAYO-2023, JUNE-2020, JUNIO 2024..."""
    first = re.split(r"[- /]", pm.upper(), maxsplit=1)[0]
    return first in _MONTHS


def is_en_standard(pm: str) -> bool:
    """Normas EN (EN-54-16, EN 54-25) — no son productos."""
    return re.match(r"^EN[- ]?\d", pm.upper()) is not None


def is_risky_acronym(pm: str) -> bool:
    """Token alfabético corto, sin separador ni dígito (NAS, ACS, LDM, VIEW).
    Peligroso como detector (matchea texto común). Se excluye salvo que el
    patrón estático ya lo conozca (esos van por la rama de unión)."""
    return (
        " " not in pm and "-" not in pm and "/" not in pm
        and not any(c.isdigit() for c in pm)
        and len(pm) <= 4
    )


def fetch_all() -> list[dict]:
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


def pick_manufacturer(mfrs: set[str]) -> str:
    known = sorted(m for m in mfrs if m and m.lower() != "unknown")
    return known[0] if known else "unknown"


def build_mfr_words(all_mfrs: set[str]) -> set[str]:
    """Palabras-token de los nombres de fabricante (para cazar product_model
    que en realidad son etiquetas de marca: 'Spectrex', 'TG-NOTIFIER')."""
    words: set[str] = set()
    for m in all_mfrs:
        if not m or m.lower() == "unknown":
            continue
        for w in re.findall(r"[a-záéíóúñ]+", m.lower()):
            if len(w) >= 4:
                words.add(w)
    return words


def is_manufacturer_name(pm: str, mfr_words: set[str]) -> bool:
    """True si algún token alfabético del product_model es un nombre de marca."""
    tokens = re.findall(r"[a-záéíóúñ]+", pm.lower())
    return any(t in mfr_words for t in tokens)


def main() -> None:
    print(f"== build_model_catalog · tabla='{TABLE}' ==\n")
    rows = fetch_all()

    counts: Counter[str] = Counter()
    pm_to_mfrs: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        pm = (r.get("product_model") or "").strip()
        if not pm or pm.lower() == "unknown":
            continue
        counts[pm] += 1
        pm_to_mfrs[pm].add((r.get("manufacturer") or "unknown").strip())

    all_mfrs: set[str] = set()
    for s in pm_to_mfrs.values():
        all_mfrs |= s
    mfr_words = build_mfr_words(all_mfrs)

    included: list[dict] = []
    excluded: list[dict] = []
    for pm in sorted(counts):
        mfr = pick_manufacturer(pm_to_mfrs[pm])
        known_mfr = mfr != "unknown"
        cnt = counts[pm]
        detected_static = bool(MODEL_PATTERN.findall(pm))

        # Nombre de marca colado como product_model (junk) → fuera, aunque
        # tenga fabricante conocido o lo detecte el seed.
        if is_manufacturer_name(pm, mfr_words):
            excluded.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "reason": "manufacturer-name"})
            continue

        if detected_static:
            included.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "source": "static-pattern"})
            continue
        if not known_mfr:
            excluded.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "reason": "unknown-mfr (deferred #6)"})
            continue
        if is_date_like(pm):
            excluded.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "reason": "date-like"})
            continue
        if is_en_standard(pm):
            excluded.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "reason": "en-standard"})
            continue
        if is_risky_acronym(pm):
            excluded.append({"model": pm, "manufacturer": mfr,
                             "chunk_count": cnt, "reason": "risky-acronym"})
            continue
        included.append({"model": pm, "manufacturer": mfr,
                         "chunk_count": cnt, "source": "known-mfr"})

    # Orden estable: por nº de chunks desc para que el diff sea legible
    included.sort(key=lambda d: (-d["chunk_count"], d["model"]))
    excluded.sort(key=lambda d: (d["reason"], -d["chunk_count"], d["model"]))

    catalog = {
        "build": {
            "table": TABLE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_distinct": len(counts),
            "n_included": len(included),
            "n_excluded": len(excluded),
        },
        "models": included,
        "excluded": excluded,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    # --- Resumen / revisión humana por stdout ---
    inc_static = sum(1 for m in included if m["source"] == "static-pattern")
    inc_known = sum(1 for m in included if m["source"] == "known-mfr")
    by_mfr = Counter(m["manufacturer"] for m in included)
    by_reason = Counter(e["reason"] for e in excluded)

    print(f"INCLUIDOS .. {len(included)}  (static={inc_static}  known-mfr-nuevos={inc_known})")
    print(f"EXCLUIDOS .. {len(excluded)}")
    print(f"\nIncluidos por fabricante:")
    for m, n in by_mfr.most_common():
        print(f"  {m:<28} {n}")
    print(f"\nExcluidos por motivo:")
    for r, n in by_reason.most_common():
        print(f"  {r:<28} {n}")

    print(f"\nNuevos modelos known-mfr ganados (top 30 por chunks):")
    for m in [x for x in included if x["source"] == "known-mfr"][:30]:
        print(f"  {m['chunk_count']:>5}  {m['model']:<32} [{m['manufacturer']}]")

    print(f"\nExcluidos NO-unknown (revisar — ¿whitelist?):")
    for e in [x for x in excluded if not x["reason"].startswith("unknown")][:25]:
        print(f"  {e['chunk_count']:>5}  {e['model']!r:<34} {e['reason']}")

    print(f"\n-> {OUT_PATH}")


if __name__ == "__main__":
    main()
