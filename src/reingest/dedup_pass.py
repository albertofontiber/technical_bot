"""Pase POST-INDEX del dedup semántico (B6) sobre `chunks_v2`.

Por qué este pase existe — y por qué el dedup que ejecuta el pipeline dentro
de `process_file` NO es suficiente:

  `process_file` llama a `mark_duplicates(kept)` con los chunks de UN solo
  archivo extraído. El plan §Fase 1 decisión 2 pide dedup "intra-producto"
  — un producto puede vivir en varios PDFs (típicamente Manual_ES.pdf y
  Manual_EN.pdf del mismo producto). El dedup intra-archivo nunca compara
  esas dos versiones entre sí, así que la pareja "prefiere ES, marca EN"
  no se activa y los chunks ES/EN equivalentes coexisten sin marcar.

  Este pase corrige ese gap: opera sobre `chunks_v2` ya indexado, agrupa por
  `product_model` (varios archivos del mismo producto = un grupo) y aplica
  `dedup.mark_duplicates`. La lógica de mark_duplicates ya estaba bien — el
  bug era que se le pasaba el input equivocado.

Propiedades:
  - **Idempotente.** Solo carga chunks con `duplicate_of IS NULL`; re-ejecutar
    nunca re-marca ni revierte.
  - **No destructivo.** Solo UPDATE de la columna `duplicate_of` (un falso
    positivo se revierte poniendo el campo a NULL, sin re-indexar).
  - **Re-ejecutable a cualquier escala.** Pagina chunks_v2 sin asumir tamaño.

Pre-requisito del SWAP — el GATE de recall sobre `chunks_v2` debe medirse con
el dedup ya aplicado.

Uso:
    python -m src.reingest.dedup_pass
    python -m src.reingest.dedup_pass --threshold 0.96
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from ..ingestion.supabase_client import SupabaseHTTP
from .dedup import mark_duplicates, DEFAULT_THRESHOLD

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reingest.dedup_pass")

# PostgREST cap por respuesta; chunks_v2 con embedding(1024) son ~4 KB cada uno,
# 1000 chunks ≈ 4 MB JSON — cómodo.
PAGE_SIZE = 1000


@dataclass
class _ChunkRef:
    """Vista mínima de un chunk en `chunks_v2` — solo los campos que dedup mira.

    Es duck-compatible con la firma que `dedup.mark_duplicates` espera
    (`id`, `embedding`, `product_model`, `source_file`, `language`, `content`,
    `chunk_index`, `duplicate_of`), así que reutilizamos la función tal cual.
    """
    id: str
    product_model: str | None
    source_file: str | None
    language: str | None
    content: str
    chunk_index: int
    embedding: list[float]
    duplicate_of: str | None = None


def _parse_embedding(value) -> list[float] | None:
    """pgvector devuelve embeddings como string `'[0.1,0.2,...]'` por PostgREST."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [float(x) for x in value.strip("[]").split(",")]
    return None


def _fetch_all(sb: SupabaseHTTP) -> list[_ChunkRef]:
    """Pagina chunks_v2 cargando solo los aún sin marcar."""
    out: list[_ChunkRef] = []
    headers = {"apikey": sb.service_key,
               "Authorization": f"Bearer {sb.service_key}"}
    offset = 0
    while True:
        params = {
            "select": ("id,product_model,source_file,language,content,"
                       "chunk_index,embedding"),
            "duplicate_of": "is.null",
            "order": "id",
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
        }
        r = httpx.get(f"{sb.url}/rest/v1/chunks_v2",
                      headers=headers, params=params, timeout=120)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for row in rows:
            emb = _parse_embedding(row.get("embedding"))
            if emb is None:
                continue  # chunk sin embedding (no debería pasar) — saltar
            out.append(_ChunkRef(
                id=row["id"],
                product_model=row.get("product_model"),
                source_file=row.get("source_file"),
                language=row.get("language"),
                content=row.get("content") or "",
                chunk_index=row.get("chunk_index") or 0,
                embedding=emb,
            ))
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if (offset // PAGE_SIZE) % 10 == 0:
            logger.info("  cargados %d chunks...", len(out))
    return out


def _write_marks(sb: SupabaseHTTP, chunks: list[_ChunkRef]) -> int:
    """UPDATE `duplicate_of` para los chunks recién marcados."""
    n = 0
    for ch in chunks:
        if ch.duplicate_of is None:
            continue
        sb.update_row("chunks_v2", ch.id, {"duplicate_of": ch.duplicate_of})
        n += 1
        if n % 200 == 0:
            logger.info("  %d marcas escritas...", n)
    return n


def run_dedup_pass(threshold: float = DEFAULT_THRESHOLD,
                   supabase: SupabaseHTTP | None = None) -> dict:
    """Ejecuta el dedup intra-producto sobre todo `chunks_v2`. Devuelve resumen.

    Reutiliza `dedup.mark_duplicates` — la lógica está bien, solo cambiamos
    el input (toda la tabla en lugar de chunks de un archivo).
    """
    sb = supabase or SupabaseHTTP()
    t0 = time.time()

    logger.info("Cargando chunks_v2 (duplicate_of IS NULL)...")
    chunks = _fetch_all(sb)
    logger.info("Cargados %d chunks sin marcar", len(chunks))

    n_marked = mark_duplicates(chunks, threshold=threshold)
    logger.info("mark_duplicates marcó %d chunks como duplicados", n_marked)

    n_written = _write_marks(sb, chunks)
    logger.info("UPDATEs escritos: %d", n_written)

    return {
        "chunks_inspected": len(chunks),
        "marked_duplicates": n_marked,
        "updates_written": n_written,
        "threshold": threshold,
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="B6 post-index — dedup intra-producto sobre chunks_v2")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help="umbral de coseno (default 0.94; calibrar inspeccionando pares)")
    args = ap.parse_args()
    result = run_dedup_pass(threshold=args.threshold)
    print()
    print("=" * 60)
    print("B6 POST-INDEX DEDUP")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
