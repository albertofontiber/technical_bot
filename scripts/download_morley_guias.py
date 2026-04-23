"""Download the 170 Morley-IAS troubleshooting guides indexed in
`Guia Tecnica Morley.xlsx`.

These are FAQ-style PDFs at URL pattern:
    https://www.morley-ias.es/documentacion/guias/<slug>.pdf

The Excel has 5 columns per row:
    MARCA | FAMILIA | SUBFAMILIA | EQUIPO | NOMBRE DEL ARCHIVO

where the last column is a hyperlink to the PDF. We download each file to
`Manuales_Morley_Guias/` and write a JSON sidecar with the row metadata so
the ingestion pipeline can later set `content_type="troubleshooting"` and
the correct `product_model` from the EQUIPO column.

Usage:
    python scripts/download_morley_guias.py              # download everything
    python scripts/download_morley_guias.py --dry-run    # list only
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import httpx
import openpyxl

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = ROOT / "Guia Tecnica Morley.xlsx"
OUTPUT_DIR = ROOT / "Manuales_Morley_Guias"
METADATA_SIDECAR = OUTPUT_DIR / "_metadata.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_DELAY = 0.5


def read_index() -> list[dict]:
    """Read the Excel and return a list of {marca, familia, subfamilia,
    equipo, titulo, url, filename} dicts."""
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found at {EXCEL_PATH}")

    wb = openpyxl.load_workbook(str(EXCEL_PATH), data_only=False)
    ws = wb.active  # first sheet — Sheet1

    entries = []
    # Skip header row (row 1). Data starts at row 2.
    for row in ws.iter_rows(min_row=2, values_only=False):
        title_cell = row[4]
        if not title_cell.hyperlink:
            continue
        url = str(title_cell.hyperlink.target)
        if not url.lower().endswith(".pdf"):
            continue
        filename = url.rsplit("/", 1)[-1]
        # URL decoding: the Excel hyperlinks may contain %20 etc — keep as-is;
        # filename is derived from the URL tail, will be written verbatim.
        entries.append({
            "marca": str(row[0].value or "").strip(),
            "familia": str(row[1].value or "").strip(),
            "subfamilia": str(row[2].value or "").strip(),
            "equipo": str(row[3].value or "").strip(),
            "titulo": str(title_cell.value or "").strip(),
            "url": url,
            "filename": filename,
        })
    return entries


def sanitize_filename(name: str) -> str:
    """URL-decoded, filesystem-safe filename."""
    from urllib.parse import unquote
    # Decode %20 → space; also strip characters illegal on Windows.
    decoded = unquote(name)
    # Replace Windows-illegal chars. Keep accents / spaces / parentheses.
    return re.sub(r'[<>:"/\\|?*]', "_", decoded)


def download_all(entries: list[dict], dry_run: bool) -> dict:
    """Download each PDF and return a stats dict."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"total": len(entries), "ok": 0, "skipped": 0, "failed": 0, "failures": []}
    downloaded_metadata = []

    if dry_run:
        for i, e in enumerate(entries, 1):
            logger.info("[%d/%d] DRY-RUN would download: %s → %s",
                        i, len(entries), e["url"], sanitize_filename(e["filename"]))
        return stats

    with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for i, e in enumerate(entries, 1):
            safe_name = sanitize_filename(e["filename"])
            dest = OUTPUT_DIR / safe_name

            if dest.exists() and dest.stat().st_size > 1000:
                logger.info("[%d/%d] SKIP (exists): %s", i, len(entries), safe_name)
                stats["skipped"] += 1
                downloaded_metadata.append({**e, "local_filename": safe_name,
                                             "size_bytes": dest.stat().st_size})
                continue

            try:
                resp = client.get(e["url"])
                if resp.status_code == 200 and len(resp.content) > 500:
                    dest.write_bytes(resp.content)
                    logger.info("[%d/%d] OK (%dKB): %s",
                                i, len(entries), len(resp.content) // 1024, safe_name)
                    stats["ok"] += 1
                    downloaded_metadata.append({**e, "local_filename": safe_name,
                                                 "size_bytes": len(resp.content)})
                else:
                    logger.warning("[%d/%d] FAIL (status=%d, size=%d): %s",
                                    i, len(entries), resp.status_code, len(resp.content), safe_name)
                    stats["failed"] += 1
                    stats["failures"].append({"url": e["url"], "reason": f"status={resp.status_code}"})
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%d/%d] FAIL (%s): %s", i, len(entries), exc, safe_name)
                stats["failed"] += 1
                stats["failures"].append({"url": e["url"], "reason": str(exc)})

            time.sleep(REQUEST_DELAY)

    # Sidecar metadata file for the ingestion pipeline.
    METADATA_SIDECAR.write_text(
        json.dumps(downloaded_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote metadata sidecar: %s (%d entries)",
                METADATA_SIDECAR, len(downloaded_metadata))

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="List only; don't download")
    args = ap.parse_args()

    logger.info("Reading %s", EXCEL_PATH)
    entries = read_index()
    logger.info("Found %d PDF entries", len(entries))

    # Summarise distribution.
    from collections import Counter
    familias = Counter(e["familia"] for e in entries)
    equipos = Counter(e["equipo"] for e in entries)
    logger.info("Familias: %s", dict(familias))
    logger.info("Top 10 equipos: %s", equipos.most_common(10))

    stats = download_all(entries, dry_run=args.dry_run)
    logger.info("=== Summary ===")
    logger.info("Total: %d | OK: %d | Skipped: %d | Failed: %d",
                stats["total"], stats["ok"], stats["skipped"], stats["failed"])
    if stats["failures"]:
        logger.info("First 5 failures: %s", stats["failures"][:5])

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
