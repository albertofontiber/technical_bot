#!/usr/bin/env python3
"""Investigate the 4 mega-docs flagged as EN with suspiciously high chunk counts.

For each doc:
  1. Get precise chunk count (HEAD count=exact, no 1000-row cap).
  2. Peek at the raw PDF: first page, middle page, last page — is the text ES, EN, or mixed?
  3. Sample DB chunks at 10 positions — what language is each?
  4. Compare: PDF reality vs what landed in chunks.

Conclusion per doc: was the ES content dropped (→ re-ingest), or is the PDF
genuinely EN-only (→ translate)?
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

import fitz  # noqa: E402
from src.ingestion.supabase_client import get_supabase  # noqa: E402
# Reuse the content-based language detector we built
from scripts.audit_chunk_languages import tokenize, detect  # noqa: E402


TARGETS = [
    ("D1058-1_NFXI-WS-WSF",                         "Manuales_Notifier/MIXED"),
    ("D1056-1_NFXI-BS-BSF",                         "Manuales_Notifier/MIXED"),
    ("I56-3836-006_FAAST_XM_8100E_ML",              "Manuales_Notifier/EN_unico"),
    ("170020 21122011 TARJETAS IDIOMAS EXTINCION SUPRA REV A", "Manuales_Notifier/ES"),
]


def precise_chunk_count(sup, source_file: str) -> int:
    url = f"{sup.url}/rest/v1/chunks"
    r = sup.client.head(
        url,
        headers={**sup.headers, "Prefer": "count=exact"},
        params={"source_file": f"eq.{source_file}", "limit": "1"},
    )
    return int(r.headers.get("content-range", "0-0/0").split("/")[-1])


def sample_chunks_at_positions(sup, source_file: str, n: int = 10) -> list[dict]:
    """Fetch ~n chunks evenly spaced by page_number."""
    url = f"{sup.url}/rest/v1/chunks"
    # First: get the page range
    r = sup.client.get(url, headers=sup.headers, params={
        "select": "page_number",
        "source_file": f"eq.{source_file}",
        "order": "page_number.asc", "limit": "1",
    })
    r.raise_for_status()
    first = r.json()
    if not first:
        return []
    r = sup.client.get(url, headers=sup.headers, params={
        "select": "page_number",
        "source_file": f"eq.{source_file}",
        "order": "page_number.desc", "limit": "1",
    })
    r.raise_for_status()
    last = r.json()
    p_min, p_max = first[0]["page_number"] or 1, last[0]["page_number"] or 1

    # Pick n page numbers evenly spaced
    if p_max == p_min:
        target_pages = [p_min]
    else:
        step = max(1, (p_max - p_min) // (n - 1))
        target_pages = list(range(p_min, p_max + 1, step))[:n]

    # Fetch one chunk per target page
    samples = []
    for pg in target_pages:
        r = sup.client.get(url, headers=sup.headers, params={
            "select": "id,page_number,content",
            "source_file": f"eq.{source_file}",
            "page_number": f"eq.{pg}",
            "limit": "1",
        })
        r.raise_for_status()
        rows = r.json()
        if rows:
            samples.append(rows[0])
    return samples


def peek_pdf(pdf_path: Path, positions: tuple[str, ...] = ("first", "mid", "last")) -> dict:
    """Open the PDF and extract text from first, middle, last pages."""
    doc = fitz.open(str(pdf_path))
    try:
        n = len(doc)
        out = {"total_pages": n, "pages": {}}
        if n == 0:
            return out
        page_map = {"first": 0, "mid": n // 2, "last": n - 1}
        for pos in positions:
            idx = page_map[pos]
            text = doc[idx].get_text("text").strip()
            out["pages"][pos] = {"page_idx": idx, "text": text, "n_chars": len(text)}
        return out
    finally:
        doc.close()


def main() -> int:
    sup = get_supabase()

    for sf, rel_dir in TARGETS:
        print("=" * 80)
        print(f"DOC: {sf}")
        print(f"Folder hint: {rel_dir}")
        print("=" * 80)

        # Precise count
        n_chunks = precise_chunk_count(sup, sf)
        print(f"Precise chunk count in DB: {n_chunks}")

        # Locate PDF
        pdf_path = ROOT / rel_dir / f"{sf}.pdf"
        if not pdf_path.exists():
            # Try .PDF
            pdf_path = ROOT / rel_dir / f"{sf}.PDF"
        print(f"PDF path: {pdf_path} — exists: {pdf_path.exists()}")

        if pdf_path.exists():
            peek = peek_pdf(pdf_path)
            print(f"PDF total pages: {peek['total_pages']}")
            for pos, data in peek["pages"].items():
                txt = data["text"]
                tokens = tokenize(txt)
                lang, conf, _ = detect(tokens)
                snippet = re.sub(r"\s+", " ", txt)[:300]
                print(f"\n  [PDF {pos} page idx {data['page_idx']}] chars={data['n_chars']}  lang={lang}/{conf}")
                print(f"  snippet: {snippet}...")

        # Sample DB chunks
        print()
        print(f"  --- DB chunk samples (10 positions across pages) ---")
        samples = sample_chunks_at_positions(sup, sf, n=10)
        lang_hits = {}
        for s in samples:
            content = s.get("content") or ""
            tokens = tokenize(content)
            lang, conf, _ = detect(tokens)
            lang_hits.setdefault((lang, conf), 0)
            lang_hits[(lang, conf)] += 1
            snippet = re.sub(r"\s+", " ", content)[:150]
            print(f"  [chunk p{s.get('page_number')}] {lang}/{conf}: {snippet}...")

        print()
        print(f"  DB chunk language distribution (n={len(samples)}): "
              f"{dict(sorted(lang_hits.items(), key=lambda x: -x[1]))}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
