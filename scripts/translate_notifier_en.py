"""
Translate Notifier English-only PDFs to Spanish using Claude Sonnet.
Saves translated text files alongside originals for review before ingestion.

Usage:
    python scripts/translate_notifier_en.py                  # Translate all
    python scripts/translate_notifier_en.py --dry-run        # Count pages without translating
    python scripts/translate_notifier_en.py --single FILE    # Translate one file
    python scripts/translate_notifier_en.py --resume         # Resume from checkpoint
"""

import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pdf_parser import parse_pdf, get_page_combined_text
from src.ingestion.translator import translate_text, should_translate

EN_DIR = Path(__file__).parent.parent / "Manuales_Notifier" / "EN_unico"
OUTPUT_DIR = Path(__file__).parent.parent / "Manuales_Notifier" / "ES_traducido"
CHECKPOINT_FILE = OUTPUT_DIR / "_translate_checkpoint.json"


def load_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def save_checkpoint(completed: set):
    CHECKPOINT_FILE.write_text(
        json.dumps({"completed": sorted(completed)}, indent=2),
        encoding="utf-8",
    )


def translate_pdf(pdf_path: Path, output_dir: Path, dry_run: bool = False) -> dict:
    """Parse a PDF and translate its pages to Spanish.

    Returns dict with stats: pages_total, pages_translated, output_file.
    """
    parsed = parse_pdf(pdf_path)
    total_pages = parsed.total_pages

    if dry_run:
        # Count how many pages need translation
        en_pages = sum(
            1 for p in parsed.pages
            if p.full_text and should_translate(p.full_text)
        )
        return {"pages_total": total_pages, "pages_translated": en_pages, "output_file": None}

    # Translate each page
    translated_pages = []
    translated_count = 0

    for i, page in enumerate(parsed.pages):
        page_text = get_page_combined_text(page)

        if page_text and should_translate(page_text):
            translated = translate_text(page_text)
            translated_count += 1
        else:
            translated = page_text  # Keep as-is (already Spanish, or empty)

        translated_pages.append(f"--- Página {i + 1} ---\n{translated}")

        if (i + 1) % 10 == 0:
            logger.info(f"    Page {i + 1}/{total_pages}")

    # Save translated text
    output_file = output_dir / f"{pdf_path.stem}_ES.txt"
    output_file.write_text("\n\n".join(translated_pages), encoding="utf-8")

    return {
        "pages_total": total_pages,
        "pages_translated": translated_count,
        "output_file": output_file.name,
    }


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    resume = "--resume" in args

    # Single file mode
    if "--single" in args:
        idx = args.index("--single")
        if idx + 1 >= len(args):
            print("Error: --single requires a filename")
            sys.exit(1)
        single_file = args[idx + 1]
        pdf_path = EN_DIR / single_file
        if not pdf_path.exists():
            print(f"Error: {pdf_path} not found")
            sys.exit(1)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Translating: {pdf_path.name}")
        stats = translate_pdf(pdf_path, OUTPUT_DIR, dry_run=dry_run)
        logger.info(f"  Pages: {stats['pages_total']}, Translated: {stats['pages_translated']}")
        if stats["output_file"]:
            logger.info(f"  Output: {stats['output_file']}")
        return

    # Full batch mode
    if not EN_DIR.exists():
        print(f"Error: {EN_DIR} not found")
        sys.exit(1)

    pdfs = sorted(EN_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdfs)} English PDFs to translate")

    if dry_run:
        logger.info("DRY RUN — counting pages only")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    completed = load_checkpoint() if resume else set()
    if resume and completed:
        logger.info(f"Resuming: {len(completed)} already translated")

    total_pages = 0
    total_translated = 0
    errors = []

    try:
        for i, pdf_path in enumerate(pdfs):
            if pdf_path.name in completed:
                logger.info(f"[{i+1}/{len(pdfs)}] SKIP (checkpoint): {pdf_path.name}")
                continue

            logger.info(f"[{i+1}/{len(pdfs)}] {pdf_path.name}")

            try:
                stats = translate_pdf(pdf_path, OUTPUT_DIR, dry_run=dry_run)
                total_pages += stats["pages_total"]
                total_translated += stats["pages_translated"]

                if not dry_run:
                    completed.add(pdf_path.name)
                    if (i + 1) % 5 == 0:
                        save_checkpoint(completed)

                logger.info(f"  Pages: {stats['pages_total']}, Translated: {stats['pages_translated']}")

            except Exception as e:
                logger.error(f"  ERROR: {e}")
                errors.append((pdf_path.name, str(e)))

    except KeyboardInterrupt:
        logger.info("\nInterrupted. Saving checkpoint...")
    finally:
        if not dry_run and completed:
            save_checkpoint(completed)

    logger.info(f"\n{'='*50}")
    logger.info(f"TRANSLATION {'DRY RUN ' if dry_run else ''}COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total pages scanned: {total_pages}")
    logger.info(f"Pages translated: {total_translated}")
    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for name, err in errors:
            logger.error(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
