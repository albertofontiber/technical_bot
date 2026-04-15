"""
Update category, protocol, and doc_type metadata for existing Notifier chunks.

Re-detects metadata using the improved pipeline (multi-page text, expanded keywords)
and updates the Supabase rows without regenerating embeddings.

Usage:
    python scripts/update_notifier_metadata.py              # Execute
    python scripts/update_notifier_metadata.py --dry-run    # Preview only
"""

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.chunker import (
    detect_category, detect_manufacturer, detect_protocol, detect_doc_type,
)
from src.ingestion.supabase_client import get_supabase


def update_metadata(base_dir: str, dry_run: bool = False):
    supabase = get_supabase()
    headers = {
        "apikey": supabase.service_key,
        "Authorization": f"Bearer {supabase.service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    # Get all distinct source_files for Notifier
    logger.info("Fetching distinct Notifier source files from DB...")
    all_sources = set()
    offset = 0
    while True:
        resp = supabase.client.get(
            f"{supabase.url}/rest/v1/chunks",
            headers={"apikey": supabase.service_key, "Authorization": f"Bearer {supabase.service_key}",
                      "Range": f"{offset}-{offset+999}"},
            params={"manufacturer": "eq.Notifier", "select": "source_file", "order": "id"},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for r in batch:
            all_sources.add(r["source_file"])
        offset += len(batch)
        if len(batch) < 1000:
            break

    logger.info(f"Found {len(all_sources)} distinct source files")

    # Build source_file -> PDF path mapping
    pdf_map = {}
    for f in os.listdir(base_dir):
        if f.endswith(".pdf"):
            stem = Path(f).stem
            pdf_map[stem] = os.path.join(base_dir, f)

    # Detect metadata for each source file
    updates = {}
    not_found = []

    for source_file in sorted(all_sources):
        if source_file not in pdf_map:
            not_found.append(source_file)
            continue

        pdf_path = pdf_map[source_file]
        try:
            parsed = parse_pdf(pdf_path)
            multi_page_text = " ".join(
                p.full_text for p in parsed.pages[:5] if p.full_text
            )
            first_page_text = parsed.pages[0].full_text if parsed.pages else ""

            manufacturer = detect_manufacturer(pdf_path, first_page_text)
            category = detect_category(pdf_path, multi_page_text, manufacturer)
            protocol = detect_protocol(multi_page_text, pdf_path)
            doc_type = detect_doc_type(pdf_path)

            updates[source_file] = {
                "category": category,
                "protocol": protocol or None,
                "doc_type": doc_type or None,
            }
        except Exception as e:
            logger.error(f"Failed to parse {source_file}: {e}")

    # Summary
    from collections import Counter
    cat_counts = Counter(u["category"] for u in updates.values())
    logger.info(f"\nMetadata detected for {len(updates)} source files:")
    logger.info("Categories:")
    for k, v in sorted(cat_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {k}: {v}")

    if not_found:
        logger.warning(f"\n{len(not_found)} source files not found as PDFs (skipped):")
        for nf in not_found[:10]:
            logger.warning(f"  {nf}")

    if dry_run:
        logger.info("\n[DRY RUN] No changes applied.")
        return

    # Apply updates
    logger.info(f"\nApplying updates to {len(updates)} source files...")
    success = 0
    errors = 0

    for i, (source_file, patch) in enumerate(updates.items()):
        try:
            resp = supabase.client.patch(
                f"{supabase.url}/rest/v1/chunks",
                headers=headers,
                params={"source_file": f"eq.{source_file}"},
                json=patch,
            )
            resp.raise_for_status()
            success += 1
        except Exception as e:
            logger.error(f"Failed to update {source_file}: {e}")
            errors += 1

        if (i + 1) % 50 == 0:
            logger.info(f"  Progress: {i + 1}/{len(updates)}")

    logger.info(f"\nUpdate complete: {success} source files updated, {errors} errors")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    update_metadata("Manuales_Notifier/ES", dry_run=dry_run)
