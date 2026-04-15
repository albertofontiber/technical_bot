"""
Scraper for Notifier (Honeywell) PCI manuals from notifier.es.

Crawls the alphabetical index, enters each product category,
and downloads all PDF documents (excluding catalogs, certificates, etc.).

Usage:
    python scripts/scrape_notifier.py                  # Full download
    python scripts/scrape_notifier.py --dry-run        # List PDFs without downloading
    python scripts/scrape_notifier.py --letter a       # Only process letter 'a'
    python scripts/scrape_notifier.py --resume         # Resume from checkpoint
"""

import html
import json
import logging
import re
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.notifier.es"
INDEX_URL = f"{BASE_URL}/index.php/producto/alphaindex/manuales"
OUTPUT_DIR = Path(__file__).parent.parent / "Manuales_Notifier"
CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint.json"

# Letters in the alphabetical index (a-z + "other" for #)
LETTERS = list("abcdefghijklmnopqrstuvwxyz") + ["other"]

# Document titles containing these keywords are EXCLUDED
EXCLUDE_KEYWORDS = [
    "catálogo", "catalogo",
    "certificado",
    "hoja técnica", "hoja tecnica",
    "ficha técnica", "ficha tecnica",
    "formulario",
]

# Delay between HTTP requests (seconds) — be respectful to the server
REQUEST_DELAY = 1.5


def get_categories_for_letter(client: httpx.Client, letter: str) -> list[dict]:
    """Fetch all product categories for a given letter."""
    url = f"{INDEX_URL}/{letter}"
    resp = client.get(url)
    resp.raise_for_status()

    categories = re.findall(
        r'<a[^>]*href="(/index\.php/producto/category/[^"]+)"[^>]*>\s*([^<]+)\s*</a>',
        resp.text,
    )

    results = []
    seen_slugs = set()
    for path, name in categories:
        slug = path.split("/")[-1]
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            results.append({
                "name": name.strip(),
                "slug": slug,
                "url": f"{BASE_URL}{path}",
            })

    return results


def get_documents_for_category(client: httpx.Client, category_url: str) -> list[dict]:
    """Fetch all downloadable documents for a product category page."""
    resp = client.get(category_url)
    resp.raise_for_status()

    page_text = resp.text

    # Find all blocks: title text near a "Descargar" link
    # Pattern: <h3/h4> with title, then some HTML, then <a href="...">Descargar</a>
    documents = []

    # Find all Descargar links with their surrounding context
    for match in re.finditer(r'Descargar', page_text):
        pos = match.start()
        # Look backwards up to 500 chars for the href
        start = max(0, pos - 500)
        snippet = page_text[start:pos + 20]

        # Extract the href
        href_matches = re.findall(r'href="([^"]*task=callelement[^"]*)"', snippet)
        if not href_matches:
            continue

        href = html.unescape(href_matches[-1])
        download_url = f"{BASE_URL}{href}" if href.startswith("/") else href

        # Extract the document title (look for heading or strong text before the link)
        title_match = re.search(
            r'<(?:h[2-6]|strong)[^>]*>\s*\n?\s*([^<]+?)\s*</(?:h[2-6]|strong)>',
            snippet,
        )
        title = title_match.group(1).strip() if title_match else "Unknown"

        documents.append({
            "title": title,
            "download_url": download_url,
        })

    # Deduplicate by download URL (same link can appear multiple times)
    seen_urls = set()
    unique_docs = []
    for doc in documents:
        if doc["download_url"] not in seen_urls:
            seen_urls.add(doc["download_url"])
            unique_docs.append(doc)

    return unique_docs


def should_download(title: str) -> bool:
    """Check if a document should be downloaded based on its title."""
    title_lower = title.lower()
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in title_lower:
            return False
    return True


def download_pdf(client: httpx.Client, url: str, output_dir: Path) -> str | None:
    """Download a PDF and save it using the filename from Content-Disposition.

    Returns the saved filename, or None on failure.
    """
    try:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()

        # Check it's actually a PDF
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type and not resp.content[:4] == b"%PDF":
            logger.warning(f"  Not a PDF (content-type: {content_type}), skipping")
            return None

        # Get filename from Content-Disposition header
        content_disp = resp.headers.get("content-disposition", "")
        filename_match = re.search(r'filename="([^"]+)"', content_disp)

        if filename_match:
            filename = filename_match.group(1)
        else:
            # Fallback: generate filename from URL params
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(url).query)
            item_id = params.get("item_id", ["unknown"])[0]
            filename = f"notifier_doc_{item_id}.pdf"

        # Sanitize filename
        filename = filename.replace("/", "_").replace("\\", "_")

        # Avoid overwriting: add suffix if file exists
        filepath = output_dir / filename
        if filepath.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while filepath.exists():
                filepath = output_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        filepath.write_bytes(resp.content)
        return filepath.name

    except Exception as e:
        logger.error(f"  Download failed: {e}")
        return None


def load_checkpoint() -> set:
    """Load set of already-downloaded URLs from checkpoint file."""
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("downloaded_urls", []))
    return set()


def save_checkpoint(downloaded_urls: set):
    """Save checkpoint with downloaded URLs."""
    CHECKPOINT_FILE.write_text(
        json.dumps({"downloaded_urls": sorted(downloaded_urls)}, indent=2),
        encoding="utf-8",
    )


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    resume = "--resume" in args

    # Filter to specific letter(s)
    target_letters = LETTERS
    if "--letter" in args:
        idx = args.index("--letter")
        if idx + 1 < len(args):
            letter = args[idx + 1].lower()
            target_letters = [letter]

    if dry_run:
        logger.info("DRY RUN MODE — listing documents without downloading")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load checkpoint if resuming
    downloaded_urls = load_checkpoint() if resume else set()
    if resume and downloaded_urls:
        logger.info(f"Resuming: {len(downloaded_urls)} URLs already downloaded")

    client = httpx.Client(timeout=60.0, follow_redirects=True)

    total_found = 0
    total_downloaded = 0
    total_skipped_excluded = 0
    total_skipped_checkpoint = 0
    errors = []

    try:
        for letter in target_letters:
            logger.info(f"\n{'='*50}")
            logger.info(f"Letter: {letter.upper()}")
            logger.info(f"{'='*50}")

            try:
                categories = get_categories_for_letter(client, letter)
            except Exception as e:
                logger.error(f"  Failed to fetch letter {letter}: {e}")
                errors.append(f"letter:{letter} - {e}")
                continue

            logger.info(f"  Found {len(categories)} categories")
            time.sleep(REQUEST_DELAY)

            for cat in categories:
                logger.info(f"\n  Category: {cat['name']}")

                try:
                    documents = get_documents_for_category(client, cat["url"])
                except Exception as e:
                    logger.error(f"    Failed to fetch category {cat['name']}: {e}")
                    errors.append(f"category:{cat['name']} - {e}")
                    time.sleep(REQUEST_DELAY)
                    continue

                logger.info(f"    Documents found: {len(documents)}")

                for doc in documents:
                    total_found += 1
                    title = doc["title"]

                    # Check exclusion filter
                    if not should_download(title):
                        logger.info(f"    EXCLUDED: {title}")
                        total_skipped_excluded += 1
                        continue

                    # Check checkpoint
                    if doc["download_url"] in downloaded_urls:
                        logger.info(f"    ALREADY DOWNLOADED: {title}")
                        total_skipped_checkpoint += 1
                        continue

                    if dry_run:
                        logger.info(f"    WOULD DOWNLOAD: {title}")
                        total_downloaded += 1
                    else:
                        logger.info(f"    Downloading: {title}")
                        time.sleep(REQUEST_DELAY)
                        filename = download_pdf(client, doc["download_url"], OUTPUT_DIR)
                        if filename:
                            logger.info(f"      Saved: {filename}")
                            total_downloaded += 1
                            downloaded_urls.add(doc["download_url"])
                            # Save checkpoint periodically
                            if total_downloaded % 10 == 0:
                                save_checkpoint(downloaded_urls)
                        else:
                            errors.append(f"download:{title}")

                time.sleep(REQUEST_DELAY)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Saving checkpoint...")
    finally:
        if not dry_run and downloaded_urls:
            save_checkpoint(downloaded_urls)
        client.close()

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"SCRAPING COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total documents found: {total_found}")
    logger.info(f"Downloaded: {total_downloaded}")
    logger.info(f"Excluded (catalogs/certs/etc): {total_skipped_excluded}")
    if resume:
        logger.info(f"Skipped (checkpoint): {total_skipped_checkpoint}")
    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for err in errors:
            logger.error(f"  - {err}")


if __name__ == "__main__":
    main()
