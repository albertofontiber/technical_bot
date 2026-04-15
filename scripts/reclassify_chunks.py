#!/usr/bin/env python3
"""
Reclassify content_type for all existing chunks using the improved classifier.
Fixes chunks where specification sections were misclassified as wiring/general/procedure.

Usage:
    py -3.14 -X utf8 scripts/reclassify_chunks.py --dry-run    # Preview changes
    py -3.14 -X utf8 scripts/reclassify_chunks.py               # Apply changes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.chunker import classify_content_type

HEADERS_READ = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}
HEADERS_WRITE = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def fetch_all_chunks():
    """Fetch id, content, and current content_type for all chunks."""
    all_chunks = []
    offset = 0
    batch_size = 500

    while True:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=HEADERS_READ,
            params={
                "select": "id,content,content_type,product_model",
                "order": "created_at.asc",
                "offset": str(offset),
                "limit": str(batch_size),
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_chunks.extend(batch)
        offset += len(batch)
        if len(batch) < batch_size:
            break

    return all_chunks


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("RECLASSIFY CONTENT TYPES")
    if dry_run:
        print("[DRY RUN]")
    print("=" * 60)

    print("\n1. Fetching all chunks...")
    chunks = fetch_all_chunks()
    print(f"   Total chunks: {len(chunks)}")

    # Count current distribution
    old_dist = {}
    for c in chunks:
        t = c["content_type"]
        old_dist[t] = old_dist.get(t, 0) + 1
    print("\n   Current distribution:")
    for t, count in sorted(old_dist.items(), key=lambda x: -x[1]):
        print(f"     {t:20s}: {count:5d}")

    print("\n2. Reclassifying...")
    changes = []
    for c in chunks:
        new_type = classify_content_type(c["content"])
        if new_type != c["content_type"]:
            changes.append({
                "id": c["id"],
                "old": c["content_type"],
                "new": new_type,
                "model": c.get("product_model", "?"),
            })

    print(f"   Chunks to reclassify: {len(changes)} / {len(chunks)}")

    # Show change summary
    change_summary = {}
    for ch in changes:
        key = f"{ch['old']} → {ch['new']}"
        change_summary[key] = change_summary.get(key, 0) + 1
    print("\n   Change breakdown:")
    for key, count in sorted(change_summary.items(), key=lambda x: -x[1]):
        print(f"     {key:40s}: {count:5d}")

    # Show new distribution
    new_dist = dict(old_dist)
    for ch in changes:
        new_dist[ch["old"]] -= 1
        new_dist[ch["new"]] = new_dist.get(ch["new"], 0) + 1
    print("\n   New distribution:")
    for t, count in sorted(new_dist.items(), key=lambda x: -x[1]):
        print(f"     {t:20s}: {count:5d}")

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(changes)} chunks. Exiting.")
        return

    # Apply changes
    print(f"\n3. Applying {len(changes)} changes...")
    errors = 0
    for i, ch in enumerate(changes):
        try:
            resp = httpx.patch(
                f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{ch['id']}",
                headers=HEADERS_WRITE,
                json={"content_type": ch["new"]},
                timeout=15.0,
            )
            resp.raise_for_status()
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"   Error: {e}")

        if (i + 1) % 500 == 0:
            print(f"   Updated {i + 1} / {len(changes)}")

    print(f"\n{'=' * 60}")
    print(f"RECLASSIFICATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Updated: {len(changes) - errors} / {len(changes)}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
