"""
Authenticated scraper for Morley-IAS private clients area (morley-ias.es).

Logs in via Joomla's /index.php/cb-login form (credentials from .env:
MORLEY_USER, MORLEY_PASSWORD) and crawls the private manuals index at
/index.php/documentos/<section>/alphaindex/<letter> under session cookies.

Site structure confirmed (probes 2026-04-23):
  - Login page: https://www.morley-ias.es/index.php/cb-login
  - Login form: Joomla com_users / task=user.login with 32-hex CSRF token
    (value="1"), "return" field, SourceCoast sclogin wrapper.
  - Private sections that redirect (303) to cb-login without auth:
      /index.php/documentos/manuales/
      /index.php/documentos/manuales-descatalogados/
      /index.php/documentos/comunicaciones-tecnicas/
      /index.php/documentos/guias-tecnicas/
  - PDF links on public Morley pages use direct hrefs like
      /documentacion/morley/manuales/<filename>.pdf
    The private area MAY use the same scheme or MAY wrap them behind a
    Joomla callelement task (as Notifier does). This script supports both.

Usage:
    python scripts/scrape_morley_auth.py --dry-run    # list only
    python scripts/scrape_morley_auth.py              # download
    python scripts/scrape_morley_auth.py --letter a   # only letter 'a'
    python scripts/scrape_morley_auth.py --resume     # resume checkpoint
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
from urllib.parse import quote, urlparse, parse_qs

import httpx
from dotenv import load_dotenv

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://www.morley-ias.es"
LOGIN_PAGE = f"{BASE_URL}/index.php/cb-login"
LOGIN_POST = f"{BASE_URL}/index.php/cb-login"  # form posts to same URL

# Sections to crawl. Same Joomla pattern as Notifier:
#   /index.php/documentos/{section}/alphaindex/{letter}  -> letter page
#   /index.php/documentos/{section}/category/{slug}      -> category page
#
# SKIPPED sections (23 abril 2026, per Alberto):
#   - comunicaciones-tecnicas: dry-run found 31 "hits" but manual browser
#     check confirmed the section renders but no PDFs are actually downloadable
#     (empty placeholders). Not worth the scraping cost.
#   - guias-tecnicas: all 27 letters return 404 under auth — empty section.
#
# The "Guía Técnica" FAQ-style troubleshooting docs (170 PDFs under
# /documentacion/guias/) are NOT part of this scraper — they live in the
# "Guia Tecnica Morley.xlsx" index Alberto placed in the repo root. Handled
# by a separate script (see scripts/download_morley_guias.py, TBD).
SECTIONS = [
    "manuales",
    "manuales-descatalogados",
]

OUTPUT_DIR = ROOT / "Manuales_Morley_Privado"
CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint.json"

LETTERS = list("abcdefghijklmnopqrstuvwxyz") + ["other"]

EXCLUDE_KEYWORDS = [
    "catálogo", "catalogo",
    "certificado",
    "hoja técnica", "hoja tecnica",
    "ficha técnica", "ficha tecnica",
    "formulario",
]

# Portuguese / French / Italian duplicates — reused from download_morley.py
SKIP_FILES = {
    "MNDT1310P.pdf", "MNDT1311P.pdf",
    "DXc_Product manual_Portuguese.pdf", "DXc_Manual de utilizador.pdf",
    "0034-033-01 Guide F5000 PT.pdf", "0034-034-01 Manual F5000 PT.pdf",
    "Manual SIMEI-HLSI_FR-PT.pdf", "HLSI-MA-103_01_Itac.pdf",
    "MIE-MI-591P.pdf", "MIEMI580P.pdf",
}

REQUEST_DELAY = 1.5
MAX_BACKOFF_RETRIES = 4


def _get_with_backoff(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """GET with exponential backoff on 429 / 503."""
    delay = REQUEST_DELAY
    for attempt in range(MAX_BACKOFF_RETRIES):
        resp = client.get(url, **kwargs)
        if resp.status_code in (429, 503):
            wait = delay * (2 ** attempt)
            logger.warning(f"  {resp.status_code} on {url} — backing off {wait:.1f}s")
            time.sleep(wait)
            continue
        return resp
    return resp  # last response, even if still throttled


def login(client: httpx.Client) -> None:
    """Perform Joomla login. Raises on failure."""
    user = os.getenv("MORLEY_USER")
    pw = os.getenv("MORLEY_PASSWORD")
    if not user or not pw:
        raise RuntimeError("MORLEY_USER / MORLEY_PASSWORD missing in .env")

    r = client.get(LOGIN_PAGE)
    r.raise_for_status()

    # Narrow to the sclogin form to avoid pulling CSRF from another module.
    form_match = re.search(
        r'<form[^>]*sclogin[^>]*>.*?</form>', r.text, re.DOTALL | re.IGNORECASE
    )
    form_html = form_match.group(0) if form_match else r.text

    # Joomla CSRF: 32-hex-char input name, value="1"
    m_csrf = re.search(r'name="([a-f0-9]{32})"\s+value="1"', form_html)
    if not m_csrf:
        raise RuntimeError("Could not find Joomla CSRF token on login page")
    csrf = m_csrf.group(1)

    m_ret = re.search(r'name="return"\s+value="([^"]+)"', form_html)
    ret = m_ret.group(1) if m_ret else ""

    m_mod = re.search(r'name="mod_id"\s+value="([^"]+)"', form_html)
    mod_id = m_mod.group(1) if m_mod else "112"

    data = {
        "username": user,
        "password": pw,
        "remember": "yes",
        "Submit": "",
        "option": "com_users",
        "task": "user.login",
        "return": ret,
        "mod_id": mod_id,
        csrf: "1",
    }
    rp = client.post(LOGIN_POST, data=data)
    rp.raise_for_status()

    if client.cookies.get("joomla_user_state") != "logged_in":
        # Heuristic fallback: a successful login usually removes the sclogin
        # form and shows a logout link.
        probe = client.get(f"{BASE_URL}/index.php/documentos/manuales", follow_redirects=False)
        if probe.status_code == 303 or "cb-login" in probe.headers.get("location", ""):
            raise RuntimeError("Login failed (still redirecting to cb-login)")
    logger.info("Login OK")


def _fetch_letter_page(client: httpx.Client, section: str, letter: str) -> str | None:
    url = f"{BASE_URL}/index.php/documentos/{section}/alphaindex/{letter}"
    resp = _get_with_backoff(client, url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def get_categories_from_page(page_text: str, section: str) -> list[dict]:
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
    """Extract downloadable PDFs. Supports:
      (a) direct /documentacion/morley/.../*.pdf links (like download_morley.py)
      (b) Descargar buttons with task=callelement (like Notifier)
    """
    documents = []

    # (a) Direct PDF hrefs
    for m in re.finditer(r'href="([^"]+\.pdf)"', page_text, re.IGNORECASE):
        href = html.unescape(m.group(1))
        fname = href.split("/")[-1]
        if fname in SKIP_FILES:
            continue
        # Try to recover a title from surrounding h2/h3/strong
        pos = m.start()
        start = max(0, pos - 600)
        snippet = page_text[start:pos + 50]
        title_match = re.search(
            r'<(?:h[2-6]|strong)[^>]*>\s*([^<]+?)\s*</(?:h[2-6]|strong)>',
            snippet,
        )
        title = title_match.group(1).strip() if title_match else fname
        download_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        documents.append({"title": title, "download_url": download_url, "filename": fname})

    # (b) Joomla callelement Descargar pattern (Notifier-style)
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
        documents.append({"title": title, "download_url": download_url, "filename": None})

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
    resp = _get_with_backoff(client, category_url)
    resp.raise_for_status()
    return extract_documents_from_page(resp.text)


def should_download(title: str, filename: str | None) -> bool:
    if filename and filename in SKIP_FILES:
        return False
    t = title.lower()
    return not any(k in t for k in EXCLUDE_KEYWORDS)


def download_pdf(client: httpx.Client, url: str, output_dir: Path) -> str | None:
    try:
        # URL-encode path segments but keep slashes (matches download_morley.py)
        parsed = urlparse(url)
        if parsed.path.lower().endswith(".pdf"):
            encoded_path = "/".join(quote(p, safe="") for p in parsed.path.split("/"))
            url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
            if parsed.query:
                url += f"?{parsed.query}"
        resp = _get_with_backoff(client, url, follow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "pdf" not in ct and resp.content[:4] != b"%PDF":
            logger.warning(f"  Not a PDF (content-type: {ct}), skipping")
            return None

        # Filename resolution
        cd = resp.headers.get("content-disposition", "")
        fm = re.search(r'filename="([^"]+)"', cd)
        if fm:
            filename = fm.group(1)
        elif parsed.path.lower().endswith(".pdf"):
            filename = parsed.path.split("/")[-1]
        else:
            params = parse_qs(parsed.query)
            filename = f"morley_priv_{params.get('item_id', ['unknown'])[0]}.pdf"
        filename = filename.replace("/", "_").replace("\\", "_")

        if filename in SKIP_FILES:
            logger.info(f"  SKIP_FILES blocklist: {filename}")
            return None

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
    all_titles: list[dict] = []
    errors: list[str] = []
    per_letter_counts: dict[str, int] = {}

    def handle_doc(doc: dict, section: str, source_ctx: str, letter: str) -> None:
        nonlocal total_found, total_downloaded, total_excluded, total_skipped_cp
        total_found += 1
        title = doc["title"]
        fname = doc.get("filename")
        if not should_download(title, fname):
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
            "letter": letter,
            "title": title,
            "url": doc["download_url"],
        })
        per_letter_counts[letter] = per_letter_counts.get(letter, 0) + 1
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

                direct_docs = extract_documents_from_page(page_text)
                if direct_docs:
                    logger.info(f"  Direct documents on letter page: {len(direct_docs)}")
                    for doc in direct_docs:
                        handle_doc(doc, section, f"letter:{letter}", letter)

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
                        handle_doc(doc, section, f"category:{cat['slug']}", letter)
                    time.sleep(REQUEST_DELAY)
    except KeyboardInterrupt:
        logger.info("\nInterrupted. Saving checkpoint...")
    finally:
        if not dry_run and downloaded:
            save_checkpoint(downloaded)
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
    logger.info(f"Unique discovered (post-exclude, post-checkpoint): {len(all_titles)}")
    logger.info(f"Would-download / Downloaded: {total_downloaded}")
    logger.info(f"Excluded: {total_excluded}")
    if resume:
        logger.info(f"Skipped (checkpoint): {total_skipped_cp}")
    if per_letter_counts:
        logger.info("Per-letter discovered:")
        for l in sorted(per_letter_counts):
            logger.info(f"  {l}: {per_letter_counts[l]}")
    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for e in errors[:20]:
            logger.error(f"  - {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
