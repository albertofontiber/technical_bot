#!/usr/bin/env python3
"""Post-hoc analysis of logs/language_audit.json.

Three cuts:
  1. Cross-check detected language vs documents.language (the 7 rows populated
     by revision_parser.py). Did our content detector agree?
  2. Breakdown by manufacturer per detected language.
  3. For detected EN documents: are they concentrated in a specific manufacturer/
     category? Do filenames suggest they should have been translated? Sample the
     chunks to confirm text is actually English (not e.g. code-only schematics).
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


def main() -> int:
    audit = json.loads((ROOT / "logs/language_audit.json").read_text(encoding="utf-8"))
    print(f"Loaded {len(audit)} audit entries")
    by_sf = {r["source_file"]: r for r in audit}

    sup = get_supabase()

    # ===== CUT 1: cross-check with documents.language =====
    print()
    print("=" * 70)
    print("CUT 1: content detector vs documents.language (filename-based)")
    print("=" * 70)
    url = f"{sup.url}/rest/v1/documents"
    resp = sup.client.get(url, headers=sup.headers,
                          params={"select": "source_pdf_filename,language,manufacturer",
                                  "language": "not.is.null", "limit": "100"})
    resp.raise_for_status()
    filename_labeled = resp.json()
    print(f"documents with language set: {len(filename_labeled)}")
    print()
    print(f"{'source_pdf_filename':<55s} {'parser':<8s} {'content':<8s} match")
    print("-" * 90)
    matches = mismatches = missing = 0
    for row in filename_labeled:
        pdf_fn = row["source_pdf_filename"] or ""
        parser_lang = row["language"]
        stem = pdf_fn.rsplit(".", 1)[0]  # drop .pdf
        # audit keys are chunks.source_file which is Path(filename).stem
        content_row = by_sf.get(stem)
        if content_row is None:
            print(f"{pdf_fn[:55]:<55s} {parser_lang:<8s} {'MISSING':<8s} -")
            missing += 1
            continue
        content_lang = content_row["detected_language"]
        match = "OK" if parser_lang == content_lang else "DIFF"
        if match == "OK":
            matches += 1
        else:
            mismatches += 1
        print(f"{pdf_fn[:55]:<55s} {parser_lang:<8s} {content_lang:<8s} {match}")
    print()
    print(f"  matches: {matches}, mismatches: {mismatches}, missing: {missing}")

    # ===== CUT 2: manufacturer breakdown per language =====
    print()
    print("=" * 70)
    print("CUT 2: manufacturer × language breakdown")
    print("=" * 70)
    mfr_lang = Counter()
    for r in audit:
        mfr_lang[(r["manufacturer"], r["detected_language"])] += 1

    mfrs = sorted({m for m, _ in mfr_lang})
    langs = ["es", "en", "pt", "fr", "it", "unknown"]
    print(f"{'manufacturer':<20s}" + "".join(f"{l:>8s}" for l in langs) + f"{'total':>8s}")
    print("-" * (20 + 8 * (len(langs) + 1)))
    for mfr in mfrs:
        row_counts = [mfr_lang.get((mfr, l), 0) for l in langs]
        total = sum(row_counts)
        print(f"{mfr:<20s}" + "".join(f"{n:>8d}" for n in row_counts) + f"{total:>8d}")

    # ===== CUT 3: analyze the 211 EN documents =====
    print()
    print("=" * 70)
    print("CUT 3: documents detected as EN — should they have been translated?")
    print("=" * 70)
    en_docs = [r for r in audit if r["detected_language"] == "en"]
    print(f"Total EN-detected: {len(en_docs)}")
    by_conf = Counter(r["confidence"] for r in en_docs)
    print(f"  by confidence: {dict(by_conf)}")
    by_mfr = Counter(r["manufacturer"] for r in en_docs)
    print(f"  by manufacturer: {dict(by_mfr)}")
    print()

    # For each EN doc, fetch its doc_type from documents table and look at
    # filename heuristics (do they end in _Eng / _EN / English? or just happen to
    # have English content we didn't translate?)
    print("Sample of 15 EN-detected documents (for naked-eye inspection):")
    print(f"{'conf':<7s} {'mfr':<10s} {'tokens':>6s} {'ratio':>6s}  source_file")
    print("-" * 95)
    for r in en_docs[:15]:
        print(f"{r['confidence']:<7s} {r['manufacturer']:<10s} "
              f"{r['tokens_sampled']:>6d} {str(r['ratio']):>6s}  {r['source_file']}")

    # How many high-confidence EN docs have filenames suggesting they were
    # clearly English originals (good translation candidates we missed)?
    import re
    en_filename_markers = re.compile(r"(?i)(?:^|[_\-\s\.])(?:eng|english|en|gb)(?:$|[_\-\s\.])")
    clear_en_in_filename = [r for r in en_docs
                             if en_filename_markers.search(r["source_file"])]
    print()
    print(f"EN docs with explicit EN marker in filename: {len(clear_en_in_filename)}"
          " (these clearly should have been translated)")
    for r in clear_en_in_filename[:10]:
        print(f"  [{r['confidence']:<6s}] {r['source_file']}")
    if len(clear_en_in_filename) > 10:
        print(f"  ... and {len(clear_en_in_filename)-10} more")

    # ===== CUT 4 (bonus): PT validation — does "ends in P" heuristic hold? =====
    print()
    print("=" * 70)
    print("CUT 4 (bonus): Notifier 'P suffix' hypothesis for Portuguese")
    print("=" * 70)
    # Notifier docs ending in "P" (or "P " + digits)
    notifier_docs = [r for r in audit if r["manufacturer"] == "Notifier"]
    # Pattern: (MADT|MNDT|ETDT|BTDT|MPDT|MIDT|...) + digits + P at end
    p_suffix_re = re.compile(r"^(?:M|E|B)[A-Z]DT\d{2,}P$")
    p_suffix_docs = [r for r in notifier_docs if p_suffix_re.match(r["source_file"])]
    print(f"Notifier docs matching ^..DT\\d+P$: {len(p_suffix_docs)}")
    lang_breakdown = Counter(r["detected_language"] for r in p_suffix_docs)
    print(f"  detected languages: {dict(lang_breakdown)}")
    print()
    # Show any non-PT ones — those would break the hypothesis
    non_pt = [r for r in p_suffix_docs if r["detected_language"] != "pt"]
    if non_pt:
        print(f"  non-PT among P-suffix docs ({len(non_pt)}, hypothesis breakers):")
        for r in non_pt:
            print(f"    [{r['detected_language']:<3s} {r['confidence']:<6s}] {r['source_file']}")
    else:
        print("  hypothesis holds 100%.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
