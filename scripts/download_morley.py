"""Download all Morley-IAS manuals from morley-ias.es"""

import httpx
import re
import string
import time
from pathlib import Path
from urllib.parse import quote

BASE_URL = "https://www.morley-ias.es"
INDEX_URL = f"{BASE_URL}/index.php/component/zoo/alphaindex/manuales/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "Manuales_Morley"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Portuguese, French, Italian duplicates to skip
SKIP_FILES = {
    "MNDT1310P.pdf", "MNDT1311P.pdf",
    "DXc_Product manual_Portuguese.pdf", "DXc_Manual de utilizador.pdf",
    "0034-033-01 Guide F5000 PT.pdf", "0034-034-01 Manual F5000 PT.pdf",
    "Manual SIMEI-HLSI_FR-PT.pdf", "HLSI-MA-103_01_Itac.pdf",
    "MIE-MI-591P.pdf", "MIEMI580P.pdf",
}


def discover_pdfs() -> list[str]:
    """Scrape all alphabet pages to find PDF links."""
    chars = list(string.ascii_lowercase) + ["other"]
    all_pdfs = []

    with httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS) as client:
        for char in chars:
            try:
                resp = client.get(f"{INDEX_URL}{char}")
                if resp.status_code != 200:
                    continue
                pdfs = re.findall(
                    r'href="(/documentacion/morley/manuales/[^"]+\.pdf)"',
                    resp.text,
                    re.IGNORECASE,
                )
                for p in pdfs:
                    fname = p.split("/")[-1]
                    if fname not in SKIP_FILES:
                        all_pdfs.append(p)
                if pdfs:
                    print(f"  {char.upper()}: {len(pdfs)} PDFs found")
            except Exception as e:
                print(f"  {char.upper()}: Error - {e}")

    # Deduplicate preserving order
    seen = set()
    unique = []
    for p in all_pdfs:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return unique


def download_pdfs(pdf_paths: list[str]) -> tuple[int, int]:
    """Download all PDFs to OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0

    with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for i, path in enumerate(pdf_paths, 1):
            fname = path.split("/")[-1]
            dest = OUTPUT_DIR / fname

            if dest.exists() and dest.stat().st_size > 1000:
                print(f"  [{i:2d}/{len(pdf_paths)}] SKIP (exists): {fname}")
                ok += 1
                continue

            try:
                # URL-encode the path but keep slashes
                encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
                url = f"{BASE_URL}{encoded_path}"
                resp = client.get(url)

                if resp.status_code == 200 and len(resp.content) > 500:
                    dest.write_bytes(resp.content)
                    size_kb = len(resp.content) / 1024
                    print(f"  [{i:2d}/{len(pdf_paths)}] OK ({size_kb:.0f}KB): {fname}")
                    ok += 1
                else:
                    print(f"  [{i:2d}/{len(pdf_paths)}] FAIL (status={resp.status_code}, size={len(resp.content)}): {fname}")
                    fail += 1
            except Exception as e:
                print(f"  [{i:2d}/{len(pdf_paths)}] FAIL ({e}): {fname}")
                fail += 1

            time.sleep(0.3)  # Be polite

    return ok, fail


def main():
    print("=== Morley-IAS Manual Downloader ===\n")
    print("Discovering PDFs...")
    pdfs = discover_pdfs()
    print(f"\nFound {len(pdfs)} unique PDFs to download.\n")

    print("Downloading...")
    ok, fail = download_pdfs(pdfs)
    print(f"\n=== Done: {ok} OK, {fail} failed ===")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
