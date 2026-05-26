#!/usr/bin/env python3
"""Re-aplica B5 (metadata.py) sobre todos los docs ya en chunks_v2 y actualiza
`product_model` / `manufacturer` / `distributor` donde el detector mejorado
encuentre algo distinto.

Solo metadata: NO toca content, embeddings, ni nada más. Las columnas
afectadas son ortogonales a la búsqueda vectorial — no requiere re-embedding.

Idempotente: re-correr no hace nada si B5 no cambia. Reporta cambios.

Uso:
    python scripts/update_product_models_v2.py --dry-run   # solo reporta
    python scripts/update_product_models_v2.py             # aplica UPDATEs
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from src.config import PROJECT_DIR  # carga .env
from src.ingestion.supabase_client import SupabaseHTTP
from src.reingest.metadata import detect_document_metadata

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("update_product_models_v2")

STORE = "data/extraction/agent_anthropic-sonnet-45"


def build_text_sample(record: dict, max_chars: int = 4000) -> str:
    """Texto representativo del doc para B5 — concatena los markdowns de las
    primeras páginas hasta max_chars (mismo enfoque que el pipeline usa)."""
    parts = []
    total = 0
    for p in record.get("result", {}).get("pages", []):
        md = p.get("md") or p.get("text") or ""
        if not md.strip():
            continue
        parts.append(md)
        total += len(md)
        if total >= max_chars:
            break
    return " ".join(parts)[:max_chars]


def get_current_metadata(sb: SupabaseHTTP, sha: str) -> dict | None:
    """Lee el metadata actual de chunks_v2 para este extraction_sha256."""
    H = {"apikey": sb.service_key, "Authorization": f"Bearer {sb.service_key}"}
    r = httpx.get(f"{sb.url}/rest/v1/chunks_v2", headers=H, params={
        "select": "product_model,manufacturer,distributor",
        "extraction_sha256": f"eq.{sha}",
        "limit": "1",
    }, timeout=15)
    r.raise_for_status()
    rows = r.json()
    return rows[0] if rows else None


def update_metadata(sb: SupabaseHTTP, sha: str, meta: dict) -> int:
    """UPDATE chunks_v2 SET ... WHERE extraction_sha256 = sha. Devuelve nº filas."""
    H = {**{"apikey": sb.service_key, "Authorization": f"Bearer {sb.service_key}",
            "Content-Type": "application/json", "Prefer": "count=exact"}}
    r = httpx.patch(f"{sb.url}/rest/v1/chunks_v2", headers=H,
                    params={"extraction_sha256": f"eq.{sha}"},
                    json=meta, timeout=30)
    r.raise_for_status()
    # Range header: "0-N/total" — extract count
    cr = r.headers.get("Content-Range", "")
    if "/" in cr:
        return int(cr.split("/")[1])
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="solo reporta cambios sin aplicar UPDATE")
    args = ap.parse_args()

    sb = SupabaseHTTP()
    files = sorted(glob.glob(os.path.join(STORE, "*.json")))
    # Filtrar a los <sha>.json (no _failures.json etc.)
    files = [f for f in files if len(os.path.basename(f)) == 69]
    logger.info("docs extraidos: %d", len(files))

    t0 = time.time()
    stats = Counter()
    examples: list[str] = []
    rows_changed = 0

    for i, fn in enumerate(files):
        sha = os.path.basename(fn)[:-5]
        try:
            with open(fn, encoding="utf-8") as f:
                record = json.load(f)
        except Exception as e:
            logger.warning("no se pudo cargar %s: %s", sha[:12], e)
            stats["load_error"] += 1
            continue

        current = get_current_metadata(sb, sha)
        if not current:
            stats["not_in_chunks_v2"] += 1
            continue

        sample = build_text_sample(record)
        meta = detect_document_metadata(record["source_path"], sample)

        new_pm = meta.product_model
        new_mfr = meta.manufacturer
        new_dis = meta.distributor
        cur_pm = current.get("product_model")
        cur_mfr = current.get("manufacturer")
        cur_dis = current.get("distributor")

        if new_pm == cur_pm and new_mfr == cur_mfr and new_dis == cur_dis:
            stats["unchanged"] += 1
            continue

        # Categorizar el tipo de cambio
        if cur_pm is None and new_pm is not None:
            stats["null_to_attributed"] += 1
        elif cur_pm is not None and new_pm is None:
            stats["attributed_to_null"] += 1  # regresión — vigilar
        else:
            stats["changed"] += 1

        if len(examples) < 15:
            examples.append(
                f"  {os.path.basename(record['source_path'])[:45]:47s} "
                f"{cur_pm}/{cur_mfr}/{cur_dis or '-'} -> "
                f"{new_pm}/{new_mfr}/{new_dis or '-'}"
            )

        if not args.dry_run:
            update = {"product_model": new_pm,
                      "manufacturer": new_mfr,
                      "distributor": new_dis}
            try:
                n = update_metadata(sb, sha, update)
                rows_changed += n
            except Exception as e:
                logger.warning("UPDATE falló %s: %s", sha[:12], e)
                stats["update_error"] += 1

        if (i + 1) % 100 == 0:
            logger.info("[%d/%d] procesados", i + 1, len(files))

    print()
    print("=" * 60)
    print(f"UPDATE PRODUCT MODELS V2  ({'DRY-RUN' if args.dry_run else 'APLICADO'})")
    print(f"  tiempo:             {time.time() - t0:.0f}s")
    print(f"  docs analizados:    {len(files)}")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {k:20s} {v:>5d}")
    if not args.dry_run:
        print(f"  CHUNKS actualizados en chunks_v2: {rows_changed}")
    print()
    print("=== ejemplos de cambios ===")
    for ex in examples:
        print(ex)


if __name__ == "__main__":
    main()
