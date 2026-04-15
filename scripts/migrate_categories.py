"""
Migrate existing Detnov chunks from old folder-based categories to the unified EN 54 taxonomy.

Old categories → New categories:
  Detección analógica     → Detectores puntuales  (+ protocol=analógico)
  Detección convencional  → Detectores puntuales  (+ protocol=convencional)
  Detección de gas        → Detectores puntuales
  Detección de monóxido   → Detectores puntuales
  Detectores especiales   → Detectores puntuales (or Detectores de aspiración/lineales)
  PA_VA Evacuación por voz → Sirenas y balizas
  Sistema de extinción    → Sistemas de extinción
  Accesorios              → Accesorios y cableado
  General                 → General (unchanged)

Also populates doc_type for existing chunks based on source_file patterns.

Usage:
    python scripts/migrate_categories.py              # Execute migration
    python scripts/migrate_categories.py --dry-run    # Preview changes only
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.supabase_client import get_supabase

# Category mapping
CATEGORY_MAP = {
    "Detección analógica": ("Detectores puntuales", "analógico"),
    "Detección convencional": ("Detectores puntuales", "convencional"),
    "Detección de gas": ("Detectores puntuales", ""),
    "Detección de monóxido": ("Detectores puntuales", ""),
    "PA_VA Evacuación por voz": ("Sirenas y balizas", ""),
    "Sistema de extinción": ("Sistemas de extinción", ""),
    "Accesorios": ("Accesorios y cableado", ""),
}

# Special cases for "Detectores especiales" subcategories
ESPECIALES_MAP = {
    "aspiración": "Detectores de aspiración",
    "lineal": "Detectores lineales",
    "firebeam": "Detectores lineales",
    "beam": "Detectores lineales",
    "vesda": "Detectores de aspiración",
    "asd": "Detectores de aspiración",
}


def detect_doc_type_from_source(source_file: str) -> str:
    """Detect doc_type from existing source_file field."""
    s = source_file.lower()
    if any(kw in s for kw in ["instalacion", "instalación", "installation", "instal"]):
        return "instalación"
    if any(kw in s for kw in ["usuario", "user", "programacion", "programación", "programming", "operating"]):
        return "usuario"
    if any(kw in s for kw in ["mantenimiento", "maintenance"]):
        return "mantenimiento"
    if any(kw in s for kw in ["quick", "qref", "guia rapida"]):
        return "guía_rápida"
    return ""


def migrate(dry_run: bool = False):
    supabase = get_supabase()

    # Fetch all distinct categories and counts
    headers = {
        "apikey": supabase.service_key,
        "Authorization": f"Bearer {supabase.service_key}",
    }

    # Get all chunks with pagination (PostgREST default limit is 1000)
    logger.info("Fetching all Detnov chunks...")
    chunks = []
    offset = 0
    page_size = 1000
    while True:
        resp = supabase.client.get(
            f"{supabase.url}/rest/v1/chunks",
            headers={**headers, "Range": f"{offset}-{offset + page_size - 1}"},
            params={
                "manufacturer": "eq.Detnov",
                "select": "id,category,source_file,product_model,protocol,doc_type",
                "order": "id",
            },
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        chunks.extend(batch)
        offset += len(batch)
        if len(batch) < page_size:
            break
    logger.info(f"Found {len(chunks)} Detnov chunks")

    # Count current categories
    cat_counts = {}
    for c in chunks:
        cat = c.get("category", "General")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    logger.info("Current categories:")
    for cat, count in sorted(cat_counts.items()):
        logger.info(f"  {cat}: {count}")

    # Plan updates
    updates = []
    for chunk in chunks:
        old_cat = chunk.get("category", "General")
        chunk_id = chunk["id"]
        source_file = chunk.get("source_file", "")
        patch = {}

        # Category migration
        if old_cat in CATEGORY_MAP:
            new_cat, protocol = CATEGORY_MAP[old_cat]
            patch["category"] = new_cat
            if protocol and not chunk.get("protocol"):
                patch["protocol"] = protocol
        elif old_cat.startswith("Detectores especiales"):
            # Check subcategory for aspiration/linear
            sub = old_cat.lower() + " " + source_file.lower()
            new_cat = "Detectores puntuales"  # default
            for kw, cat in ESPECIALES_MAP.items():
                if kw in sub:
                    new_cat = cat
                    break
            patch["category"] = new_cat

        # Doc type detection
        if not chunk.get("doc_type") and source_file:
            dt = detect_doc_type_from_source(source_file)
            if dt:
                patch["doc_type"] = dt

        if patch:
            updates.append((chunk_id, patch))

    # Summary
    new_cat_counts = {}
    for _, patch in updates:
        cat = patch.get("category", "unchanged")
        new_cat_counts[cat] = new_cat_counts.get(cat, 0) + 1
    logger.info(f"\nPlanned updates: {len(updates)} chunks")
    logger.info("New categories:")
    for cat, count in sorted(new_cat_counts.items()):
        logger.info(f"  {cat}: {count}")

    if dry_run:
        logger.info("\n[DRY RUN] No changes applied.")
        return

    # Apply updates in batches
    logger.info("\nApplying updates...")
    success = 0
    errors = 0

    for i, (chunk_id, patch) in enumerate(updates):
        try:
            resp = supabase.client.patch(
                f"{supabase.url}/rest/v1/chunks",
                headers={
                    **headers,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                params={"id": f"eq.{chunk_id}"},
                json=patch,
            )
            resp.raise_for_status()
            success += 1
        except Exception as e:
            logger.error(f"Failed to update chunk {chunk_id}: {e}")
            errors += 1

        if (i + 1) % 500 == 0:
            logger.info(f"  Progress: {i + 1}/{len(updates)}")

    logger.info(f"\nMigration complete: {success} updated, {errors} errors")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    migrate(dry_run=dry_run)
