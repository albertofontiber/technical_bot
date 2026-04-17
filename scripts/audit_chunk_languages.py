#!/usr/bin/env python3
"""Detect the dominant language of every source_file by sampling chunk content.

Approach: for each distinct source_file in `chunks`, fetch up to 3 chunks,
concatenate the text, count function-word hits per language, and pick the
winner. Output goes to logs/language_audit.json with one entry per source_file.

Why content-based and not filename-based:
  The filename-based detector in src/ingestion/revision_parser.py only matches
  explicit tokens (_pt_, _eng_, _ita_, ...). It misses the Notifier España
  convention where a trailing `P` (e.g. MADT236P, MNDT1003P) signals Portuguese
  without a separator. We need ground-truth from the actual content to decide
  whether to extend the filename rules, and content detection is also the
  fallback for documents where the filename carries no language hint at all.

Scoring:
  - For each language L, count total hits of L's top-20 function words in the
    concatenated sample. Normalize by number of tokens.
  - Winner = language with highest normalized score.
  - Confidence tag:
       high   — winner_score / second_score >= 2.0
       medium — ratio in [1.3, 2.0)
       low    — ratio < 1.3 (ambiguous / short text)
       none   — winner_score is 0 (no function words matched; schematic/image)

Usage:
    python scripts/audit_chunk_languages.py                  # all source_files
    python scripts/audit_chunk_languages.py --limit 20       # sample run
    python scripts/audit_chunk_languages.py --manufacturer Notifier
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


# High-frequency function words per language. Kept to ~20 each to limit noise.
# Deliberately excluded: words that are identical across multiple languages
# (e.g. "a" appears in ES/PT/IT/FR — excluded or low-weight).
FUNCTION_WORDS = {
    "es": {
        "el", "la", "de", "que", "y", "en", "un", "los", "se", "con",
        "por", "para", "del", "las", "es", "una", "al", "lo", "como", "pero",
        "sus", "le", "ha", "este", "esta", "son", "más",
    },
    "en": {
        "the", "of", "and", "to", "in", "is", "that", "for", "it", "with",
        "as", "was", "on", "be", "by", "are", "this", "from", "or", "an",
        "which", "have", "has", "been", "will", "not", "at",
    },
    "pt": {
        "de", "que", "do", "da", "em", "para", "não", "com", "por", "os",
        "uma", "na", "mais", "dos", "são", "ou", "das", "no", "se", "ao",
        "como", "mas", "foi", "ser", "pelo", "pela", "está",
    },
    "it": {
        "il", "di", "che", "la", "in", "un", "non", "per", "è", "una",
        "sono", "con", "si", "su", "da", "come", "al", "lo", "le", "ma",
        "anche", "questo", "nel", "della", "del", "gli", "ha",
    },
    "fr": {
        "le", "de", "la", "et", "à", "un", "les", "des", "en", "du",
        "est", "que", "pour", "une", "dans", "il", "au", "avec", "sur", "ne",
        "par", "pas", "plus", "ou", "son", "être", "ce",
    },
}

# Words that overlap across multiple languages — we down-weight or
# track them separately to avoid false positives.
# e.g. "de" is in ES+PT+FR+IT, "la" is in ES+FR+IT, "in" is EN+IT.
# We keep them in each language's set but pick the winner by the
# language-specific strong markers below first.
STRONG_MARKERS = {
    "es": {"el", "que", "los", "se", "por", "para", "del", "las", "una", "como", "pero", "este", "esta"},
    "en": {"the", "of", "and", "to", "is", "that", "for", "with", "as", "was", "on", "by", "are", "this", "from", "or"},
    "pt": {"que", "do", "da", "não", "os", "uma", "na", "dos", "são", "das", "no", "ao", "mas", "foi", "pelo", "pela", "está"},
    "it": {"il", "che", "per", "è", "una", "sono", "come", "lo", "le", "anche", "questo", "nel", "della"},
    "fr": {"le", "et", "à", "les", "des", "du", "est", "que", "pour", "une", "dans", "au", "avec", "pas"},
}

_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase tokens; strip markers like [CONTENIDO VISUAL] and [TABLA EXTRAÍDA]."""
    # Drop our own markers so they don't pollute the word count
    text = text.replace("[CONTENIDO VISUAL]", " ").replace("[TABLA EXTRAÍDA]", " ")
    text = text.replace("[TABLA EXTRAIDA]", " ")
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def score_language(tokens: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    """Return (all_word_hits, strong_marker_hits) per language."""
    c = Counter(tokens)
    all_hits = {lang: sum(c[w] for w in FUNCTION_WORDS[lang]) for lang in FUNCTION_WORDS}
    strong_hits = {lang: sum(c[w] for w in STRONG_MARKERS[lang]) for lang in STRONG_MARKERS}
    return all_hits, strong_hits


def detect(tokens: list[str]) -> tuple[str, str, dict]:
    """Return (language, confidence, detail).

    Rule of thumb:
      - Use STRONG_MARKERS as primary signal (disambiguates words shared across langs).
      - Confidence based on ratio winner/runner-up on strong markers.
    """
    if not tokens:
        return "unknown", "none", {"reason": "empty tokens", "tokens": 0}

    all_hits, strong_hits = score_language(tokens)
    total_tokens = len(tokens)
    strong_ranked = sorted(strong_hits.items(), key=lambda x: -x[1])
    winner_lang, winner_score = strong_ranked[0]
    runner_lang, runner_score = strong_ranked[1]

    if winner_score == 0:
        # No strong markers. Fall back to full word set. If still zero → unknown.
        full_ranked = sorted(all_hits.items(), key=lambda x: -x[1])
        w_lang, w_score = full_ranked[0]
        r_lang, r_score = full_ranked[1]
        if w_score == 0:
            return "unknown", "none", {
                "reason": "no function words matched", "tokens": total_tokens,
                "strong_hits": strong_hits, "all_hits": all_hits,
            }
        ratio = (w_score + 1) / (r_score + 1)
        conf = "low" if ratio < 1.5 else "medium"
        return w_lang, conf, {
            "reason": "fallback to full word set (no strong markers)",
            "tokens": total_tokens, "strong_hits": strong_hits, "all_hits": all_hits,
            "ratio": round(ratio, 2),
        }

    ratio = (winner_score + 1) / (runner_score + 1)
    if ratio >= 2.0:
        conf = "high"
    elif ratio >= 1.3:
        conf = "medium"
    else:
        conf = "low"

    # Extra safeguard: if total strong markers are very few relative to text,
    # downgrade confidence.
    marker_density = winner_score / max(1, total_tokens)
    if marker_density < 0.01 and conf == "high":
        conf = "medium"

    return winner_lang, conf, {
        "tokens": total_tokens,
        "strong_hits": strong_hits,
        "all_hits": all_hits,
        "ratio": round(ratio, 2),
        "marker_density": round(marker_density, 4),
    }


def fetch_source_files(sup, manufacturer: str | None) -> list[dict]:
    """Return list of {source_file, manufacturer} distinct pairs."""
    url = f"{sup.url}/rest/v1/chunks"
    seen: dict[str, str] = {}
    offset = 0
    while True:
        params = {
            "select": "source_file,manufacturer",
            "limit": "1000",
            "offset": str(offset),
            "order": "id",
        }
        if manufacturer:
            params["manufacturer"] = f"eq.{manufacturer}"
        resp = sup.client.get(url, headers=sup.headers, params=params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for r in rows:
            sf = r["source_file"]
            if sf not in seen:
                seen[sf] = r.get("manufacturer")
        if len(rows) < 1000:
            break
        offset += 1000
    return [{"source_file": sf, "manufacturer": m} for sf, m in seen.items()]


def fetch_sample_chunks(sup, source_file: str, n: int = 3, min_len: int = 200) -> list[str]:
    """Fetch up to n chunks for this source_file, preferring longer content."""
    url = f"{sup.url}/rest/v1/chunks"
    params = {
        "select": "content,page_number",
        "source_file": f"eq.{source_file}",
        "order": "page_number.asc",
        "limit": "30",
    }
    resp = sup.client.get(url, headers=sup.headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    usable = [r for r in rows if r.get("content") and len(r["content"]) >= min_len]
    if not usable:
        usable = [r for r in rows if r.get("content")]
    if not usable:
        return []
    if len(usable) >= n:
        idxs = [0, len(usable) // 2, len(usable) - 1][:n]
    else:
        idxs = list(range(len(usable)))
    return [usable[i]["content"] for i in idxs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--manufacturer", type=str, default=None)
    ap.add_argument("--output", type=str, default="logs/language_audit.json")
    args = ap.parse_args()

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sup = get_supabase()

    print("Fetching list of source_files...")
    files = fetch_source_files(sup, args.manufacturer)
    print(f"  {len(files)} distinct source_files")
    if args.limit:
        files = files[: args.limit]
        print(f"  --limit {args.limit}: processing first {len(files)} only")
    print()

    results: list[dict] = []
    t0 = time.time()
    for i, f in enumerate(files, 1):
        sf = f["source_file"]
        mfr = f["manufacturer"] or "unknown"
        samples = fetch_sample_chunks(sup, sf, n=3)
        text = "\n".join(samples)
        tokens = tokenize(text)
        lang, conf, detail = detect(tokens)
        results.append({
            "source_file": sf,
            "manufacturer": mfr,
            "detected_language": lang,
            "confidence": conf,
            "tokens_sampled": len(tokens),
            "strong_hits": detail.get("strong_hits"),
            "ratio": detail.get("ratio"),
            "reason": detail.get("reason"),
        })
        if i % 25 == 0 or i == len(files):
            elapsed = time.time() - t0
            print(f"  [{i}/{len(files)}] elapsed={elapsed:.1f}s")

    print()
    print(f"Done in {time.time()-t0:.1f}s")

    # Summary
    by_lang: Counter[tuple[str, str]] = Counter()  # (language, confidence)
    for r in results:
        by_lang[(r["detected_language"], r["confidence"])] += 1
    print()
    print(f"{'language':<10s} {'confidence':<10s} {'count':>6s}")
    print("-" * 30)
    for (lang, conf), n in sorted(by_lang.items(), key=lambda x: (-x[1],)):
        print(f"{lang:<10s} {conf:<10s} {n:>6d}")

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print()
    print(f"Written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
