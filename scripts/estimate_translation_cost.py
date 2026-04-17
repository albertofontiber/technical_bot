#!/usr/bin/env python3
"""Estimate cost + time to retranslate the EN-detected chunks and re-embed.

Also classifies docs into 'translatable' (prose manuals) vs 'skip' heuristics
(schematics, tables-only, very short) so we know what NOT to waste tokens on.
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


# Claude Sonnet 4 pricing (per 1M tokens) as of late 2025
SONNET_INPUT_PER_MTOK = 3.00
SONNET_OUTPUT_PER_MTOK = 15.00
# OpenAI text-embedding-3-small pricing
EMBEDDING_PER_MTOK = 0.020

# Chars-to-tokens ratio for technical content (mixed EN/ES): ~3 chars/token is
# conservative; 4 is optimistic. We use 3.5 as a middle estimate.
CHARS_PER_TOKEN = 3.5


def main() -> int:
    audit = json.loads((ROOT / "logs/language_audit.json").read_text(encoding="utf-8"))
    en_docs = [r for r in audit if r["detected_language"] == "en"]
    print(f"Loaded audit: {len(audit)} total, {len(en_docs)} detected as EN")

    # Subset with explicit EN marker in filename (high-confidence translation candidates)
    en_filename_re = re.compile(r"(?i)(?:^|[_\-\s\.])(?:eng|english|en|gb)(?:$|[_\-\s\.])")
    with_marker = [r for r in en_docs if en_filename_re.search(r["source_file"])]
    without_marker = [r for r in en_docs if r not in with_marker]
    print(f"  with EN filename marker: {len(with_marker)}")
    print(f"  without marker:          {len(without_marker)}")

    sup = get_supabase()
    url = f"{sup.url}/rest/v1/chunks"

    def fetch_stats_for(docs: list[dict]) -> dict:
        """Per-doc: n_chunks, total_chars, avg_chars."""
        stats = []
        for r in docs:
            sf = r["source_file"]
            resp = sup.client.get(url, headers=sup.headers, params={
                "select": "content",
                "source_file": f"eq.{sf}",
                "limit": "10000",
            })
            resp.raise_for_status()
            rows = resp.json()
            total = sum(len(row.get("content") or "") for row in rows)
            n = len(rows)
            stats.append({
                "source_file": sf,
                "manufacturer": r["manufacturer"],
                "confidence": r["confidence"],
                "n_chunks": n,
                "total_chars": total,
                "avg_chars": total // max(1, n),
            })
        return stats

    print()
    print("Fetching chunk stats for EN docs...")
    with_stats = fetch_stats_for(with_marker)
    without_stats = fetch_stats_for(without_marker)
    all_stats = with_stats + without_stats

    def cost_estimate(stats: list[dict], label: str) -> None:
        total_chunks = sum(s["n_chunks"] for s in stats)
        total_chars = sum(s["total_chars"] for s in stats)
        total_tokens = total_chars / CHARS_PER_TOKEN
        # Translation: input ~= total_tokens + prompt overhead (~300 tokens per call)
        # Output ~= total_tokens (1:1 roughly for ES translation of similar length)
        # We group chunks per doc for a single Sonnet call (chunks averaged ~2k chars each,
        # good for one call per chunk to stay within context and get clean output).
        # So chunks = number of Sonnet calls.
        prompt_overhead_tokens = 400  # TRANSLATION_PROMPT is ~400 tokens
        input_tokens = total_tokens + total_chunks * prompt_overhead_tokens
        output_tokens = total_tokens  # ES output length ~ EN input length (ES is ~15% longer actually)
        output_tokens *= 1.15
        embed_input_tokens = output_tokens  # re-embed the translated text
        cost_in = (input_tokens / 1e6) * SONNET_INPUT_PER_MTOK
        cost_out = (output_tokens / 1e6) * SONNET_OUTPUT_PER_MTOK
        cost_embed = (embed_input_tokens / 1e6) * EMBEDDING_PER_MTOK
        total_cost = cost_in + cost_out + cost_embed
        # Time: Sonnet ~3s per call (chunks of ~2k chars), + rate limiting. 82 docs * 20 chunks = 1640 calls * 3s = 82 min. With parallelism, less.
        est_time_min = total_chunks * 2 / 60  # 2s per translation call (with rate limiting)
        print(f"\n  [{label}]")
        print(f"    documents:    {len(stats)}")
        print(f"    total chunks: {total_chunks}")
        print(f"    total chars:  {total_chars:,}")
        print(f"    est tokens:   {int(total_tokens):,}")
        print(f"    cost — translation in:  ${cost_in:.2f}")
        print(f"    cost — translation out: ${cost_out:.2f}")
        print(f"    cost — re-embedding:    ${cost_embed:.4f}")
        print(f"    TOTAL cost:             ${total_cost:.2f}")
        print(f"    est time (no parallel): ~{est_time_min:.0f} min")

    cost_estimate(with_stats, "Subset E: 82 docs with explicit EN marker")
    cost_estimate(without_stats, "Subset other: 129 EN docs without marker")
    cost_estimate(all_stats, "Subset A: all 211 EN docs")

    # Skip-worthy candidates: very few chunks (likely schematics), very short total_chars
    print()
    print("Candidates to SKIP (schematic / tiny content, translation wouldn't help retrieval):")
    print(f"  {'chunks':>6s} {'chars':>7s}  {'mfr':<10s} {'source_file'}")
    print("-" * 90)
    skip_candidates = [s for s in all_stats if s["n_chunks"] <= 2 or s["total_chars"] < 500]
    for s in sorted(skip_candidates, key=lambda x: x["total_chars"]):
        print(f"  {s['n_chunks']:>6d} {s['total_chars']:>7d}  {s['manufacturer']:<10s} {s['source_file']}")
    print(f"  → {len(skip_candidates)} skip candidates "
          f"({sum(x['total_chars'] for x in skip_candidates):,} chars saved)")

    # Also worth sampling: 3 docs with highest chunk count to see what huge EN docs look like
    print()
    print("Top 10 EN docs by total_chars (biggest translation targets):")
    print(f"  {'chunks':>6s} {'chars':>8s}  {'mfr':<10s} {'source_file'}")
    print("-" * 90)
    for s in sorted(all_stats, key=lambda x: -x["total_chars"])[:10]:
        print(f"  {s['n_chunks']:>6d} {s['total_chars']:>8,d}  {s['manufacturer']:<10s} {s['source_file']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
