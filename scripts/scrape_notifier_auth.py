"""
Authenticated scraper for Notifier private clients area (notifier.es).

Logs in via Joomla's /acceso-clientes form (credentials from .env:
NOTIFIER_USER, NOTIFIER_PASSWORD) and crawls the private manuals index at
/index.php/documentos/manuales/... . Structure mirrors the public scraper
(alphaindex -> categories -> Descargar links) but under a different URL path
and with session cookies.

Usage:
    python scripts/scrape_notifier_auth.py --dry-run    # list only
    python scripts/scrape_notifier_auth.py              # download
    python scripts/scrape_notifier_auth.py --letter a   # only letter 'a'
    python scripts/scrape_notifier_auth.py --resume     # resume checkpoint
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://www.notifier.es"
LOGIN_PAGE = f"{BASE_URL}/index.php/acceso-clientes"
LOGIN_POST = f"{BASE_URL}/index.php/acceso-clientes?task=user.login"

# Sections to crawl. Each section has the same Joomla pattern:
#   /index.php/documentos/{section}/alphaindex/{letter}  -> letter page
#   /index.php/documentos/{section}/category/{slug}      -> category page
# Letter pages may contain categories (manuales, manuales-descatalogados),
# documents directly (comunicaciones-tecnicas), or both. We handle all cases.
SECTIONS = [
    "manuales",
    "manuales-descatalogados",
    "comunicaciones-tecnicas",
    # guias-tecnicas: empty section (0 docs), skipped
]

OUTPUT_DIR = ROOT / "Manuales_Notifier_Privado"
CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint.json"

LETTERS = list("abcdefghijklmnopqrstuvwxyz") + ["other"]

EXCLUDE_KEYWORDS = [
    "catálogo", "catalogo",
    "certificado",
    "hoja técnica", "hoja tecnica",
    "ficha técnica", "ficha tecnica",
    "formulario",
]

REQUEST_DELAY = 1.5


def login(client: httpx.Client) -> None:
    """Perform Joomla login. Raises on failure."""
    user = os.getenv("NOTIFIER_USER")
    pw = os.getenv("NOTIFIER_PASSWORD")
    if not user or not pw:
        raise RuntimeError("NOTIFIER_USER / NOTIFIER_PASSWORD missing in .env")

    r = client.get(LOGIN_PAGE)
    r.raise_for_status()
    # Joomla CSRF: 32-hex-char input name, value="1"
    m_csrf = re.search(r'name="([a-f0-9]{32})"\s+value="1"', r.text)
    if not m_csrf:
        raise RuntimeError("Could not find Joomla CSRF token on login page")
    csrf = m_csrf.group(1)
    m_ret = re.search(r'name="return"\s+value="([^"]+)"', r.text)
    ret = m_ret.group(1) if m_ret else ""

    data = {
        "username": user,
        "password": pw,
        "remember": "yes",
        "return": ret,
        csrf: "1",
    }
    rp = client.post(LOGIN_POST, data=data)
    rp.raise_for_status()

    if client.cookies.get("joomla_user_state") != "logged_in":
        raise RuntimeError("Login failed (no joomla_user_state cookie)")
    logger.info("Login OK (joomla_user_state=logged_in)")


def _fetch_letter_page(client: httpx.Client, section: str, letter: str) -> str | None:
    url = f"{BASE_URL}/index.php/documentos/{section}/alphaindex/{letter}"
    resp = client.get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def get_categories_from_page(page_text: str, section: str) -> list[dict]:
    """Extract category links from a page (letter page or section root)."""
    pattern = re.compile(
        rf'href="(/index\.php/documentos/{re.escape(section)}/category/[^"]+)"[^>]*>\s*([^<]+)\s*</a>'
    )
    results = []
    seen = set()
    for path, name in pattern.findall(page_text):
        slug = path.split("/")[-1]
        if slug in seen:
            continue
        seen.add(slug)
        results.append({"name": name.strip(), "slug": slug, "url": f"{BASE_URL}{path}"})
    return results


def extract_documents_from_page(page_text: str) -> list[dict]:
    """Extract Descargar-linked documents from any page (category or letter)."""
    documents = []
    for match in re.finditer(r"Descargar", page_text):
        pos = match.start()
        start = max(0, pos - 500)
        snippet = page_text[start:pos + 20]
        href_matches = re.findall(r'href="([^"]*task=callelement[^"]*)"', snippet)
        if not href_matches:
            continue
        href = html.unescape(href_matches[-1])
        download_url = f"{BASE_URL}{href}" if href.startswith("/") else href
        title_match = re.search(
            r'<(?:h[2-6]|strong)[^>]*>\s*\n?\s*([^<]+?)\s*</(?:h[2-6]|strong)>',
            snippet,
        )
        title = title_match.group(1).strip() if title_match else "Unknown"
        documents.append({"title": title, "download_url": download_url})

    # dedup by URL
    seen = set()
    out = []
    for d in documents:
        if d["download_url"] in seen:
            continue
        seen.add(d["download_url"])
        out.append(d)
    return out


def get_documents_for_category(client: httpx.Client, category_url: str) -> list[dict]:
    resp = client.get(category_url)
    resp.raise_for_status()
    return extract_documents_from_page(resp.text)


def should_download(title: str) -> bool:
    t = title.lower()
    return not any(k in t for k in EXCLUDE_KEYWORDS)


def download_pdf(client: httpx.Client, url: str, output_dir: Path) -> str | None:
    try:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "pdf" not in ct and resp.content[:4] != b"%PDF":
            logger.warning(f"  Not a PDF (content-type: {ct}), skipping")
            return None
        cd = resp.headers.get("content-disposition", "")
        fm = re.search(r'filename="([^"]+)"', cd)
        if fm:
            filename = fm.group(1)
        else:
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(url).query)
            filename = f"notifier_priv_{params.get('item_id', ['unknown'])[0]}.pdf"
        filename = filename.replace("/", "_").replace("\\", "_")
        filepath = output_dir / filename
        if filepath.exists():
            stem, suffix = filepath.stem, filepath.suffix
            i = 1
            while filepath.exists():
                filepath = output_dir / f"{stem}_{i}{suffix}"
                i += 1
        filepath.write_bytes(resp.content)
        return filepath.name
    except Exception as e:
        logger.error(f"  Download failed: {e}")
        return None


def load_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        return set(json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8")).get("downloaded_urls", []))
    return set()


def save_checkpoint(urls: set) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"downloaded_urls": sorted(urls)}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    resume = "--resume" in args

    target_letters = LETTERS
    if "--letter" in args:
        idx = args.index("--letter")
        if idx + 1 < len(args):
            target_letters = [args[idx + 1].lower()]

    if dry_run:
        logger.info("DRY RUN — listing only")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = load_checkpoint() if resume else set()
    if resume and downloaded:
        logger.info(f"Resuming: {len(downloaded)} URLs already downloaded")

    client = httpx.Client(
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        login(client)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        client.close()
        return 1

    total_found = 0
    total_downloaded = 0
    total_excluded = 0
    total_skipped_cp = 0
    all_titles: list[dict] = []  # for dry-run dedup report
    errors: list[str] = []

    def handle_doc(doc: dict, section: str, source_ctx: str) -> None:
        """Apply exclusion / checkpoint / dry-run / download to one document."""
        nonlocal total_found, total_downloaded, total_excluded, total_skipped_cp
        total_found += 1
        title = doc["title"]
        if not should_download(title):
            logger.info(f"    EXCLUDED: {title}")
            total_excluded += 1
            return
        if doc["download_url"] in downloaded:
            logger.info(f"    ALREADY DOWNLOADED: {title}")
            total_skipped_cp += 1
            return
        all_titles.append({
            "section": section,
            "source": source_ctx,
            "title": title,
            "url": doc["download_url"],
        })
        if dry_run:
            logger.info(f"    WOULD DOWNLOAD: {title}")
            total_downloaded += 1
        else:
            logger.info(f"    Downloading: {title}")
            time.sleep(REQUEST_DELAY)
            fn = download_pdf(client, doc["download_url"], OUTPUT_DIR)
            if fn:
                logger.info(f"      Saved: {fn}")
                total_downloaded += 1
                downloaded.add(doc["download_url"])
                if total_downloaded % 10 == 0:
                    save_checkpoint(downloaded)
            else:
                errors.append(f"download:{title}")

    try:
        for section in SECTIONS:
            logger.info(f"\n{'#'*60}\n# SECTION: {section}\n{'#'*60}")
            for letter in target_letters:
                logger.info(f"\n{'='*50}\n[{section}] Letter: {letter.upper()}\n{'='*50}")
                try:
                    page_text = _fetch_letter_page(client, section, letter)
                except Exception as e:
                    logger.error(f"  Failed letter {letter}: {e}")
                    errors.append(f"{section}/letter:{letter} - {e}")
                    continue
                if page_text is None:
                    logger.info(f"  (404 — no such letter in section)")
                    time.sleep(REQUEST_DELAY)
                    continue

                # Case A: letter page has documents directly (e.g. comunicaciones-tecnicas)
                direct_docs = extract_documents_from_page(page_text)
                if direct_docs:
                    logger.info(f"  Direct documents on letter page: {len(direct_docs)}")
                    for doc in direct_docs:
                        handle_doc(doc, section, f"letter:{letter}")

                # Case B: letter page has categories → visit each
                cats = get_categories_from_page(page_text, section)
                logger.info(f"  Found {len(cats)} categories")
                time.sleep(REQUEST_DELAY)

                for cat in cats:
                    logger.info(f"\n  Category: {cat['name']}")
                    try:
                        docs = get_documents_for_category(client, cat["url"])
                    except Exception as e:
                        logger.error(f"    Failed category {cat['name']}: {e}")
                        errors.append(f"{section}/category:{cat['name']} - {e}")
                        time.sleep(REQUEST_DELAY)
                        continue
                    logger.info(f"    Documents found: {len(docs)}")
                    for doc in docs:
                        handle_doc(doc, section, f"category:{cat['slug']}")
                    time.sleep(REQUEST_DELAY)
    except KeyboardInterrupt:
        logger.info("\nInterrupted. Saving checkpoint...")
    finally:
        if not dry_run and downloaded:
            save_checkpoint(downloaded)
        # In dry-run mode, dump all discovered titles to a JSON for diffing
        if dry_run and all_titles:
            dump_path = OUTPUT_DIR / "_dryrun_titles.json"
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            dump_path.write_text(
                json.dumps(all_titles, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"Dry-run titles written to {dump_path}")
        client.close()

    logger.info(f"\n{'='*50}\nSCRAPING COMPLETE\n{'='*50}")
    logger.info(f"Total documents found: {total_found}")
    logger.info(f"Downloaded: {total_downloaded}")
    logger.info(f"Excluded: {total_excluded}")
    if resume:
        logger.info(f"Skipped (checkpoint): {total_skipped_cp}")
    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for e in errors[:20]:
            logger.error(f"  - {e}")

    return 0 if not errors else 0  # errors don't fail the run


if __name__ == "__main__":
    sys.exit(main())
