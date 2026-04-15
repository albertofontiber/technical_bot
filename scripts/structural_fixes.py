"""
Structural fixes for the chunks database:
1. Delete junk chunks (revision history, index pages, covers, very short content)
2. Fix remaining product_model = "unknown" where possible
3. Fix chunks with zero-vector embeddings (re-embed them)

Usage:
    py -3.14 -X utf8 scripts/structural_fixes.py [--dry-run]
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.embedder import embed_texts


HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

HEADERS_COUNT = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Prefer": "count=exact",
}

CLIENT = httpx.Client(timeout=30.0)


def count_chunks():
    r = CLIENT.get(f"{SUPABASE_URL}/rest/v1/chunks?select=id&limit=1", headers=HEADERS_COUNT)
    return r.headers.get("content-range", "?")


def delete_by_filter(filter_param: str, label: str, dry_run: bool):
    """Delete chunks matching a PostgREST filter."""
    # First count
    r = CLIENT.get(
        f"{SUPABASE_URL}/rest/v1/chunks?{filter_param}&select=id",
        headers={**HEADERS, "Prefer": "count=exact"},
    )
    count = len(r.json()) if r.status_code == 200 else 0

    if count == 0:
        print(f"  {label}: 0 chunks (skip)")
        return 0

    if dry_run:
        print(f"  {label}: {count} chunks (would delete)")
        return count

    r2 = CLIENT.delete(
        f"{SUPABASE_URL}/rest/v1/chunks?{filter_param}",
        headers=HEADERS,
    )
    print(f"  {label}: {count} chunks deleted (status {r2.status_code})")
    return count


def step1_delete_junk(dry_run: bool):
    """Delete low-quality chunks that add noise to search results."""
    print("\n" + "=" * 60)
    print("STEP 1: Delete junk chunks")
    print("=" * 60)

    total_deleted = 0

    # Revision history pages
    total_deleted += delete_by_filter(
        "content=ilike.*Control de  revisiones*",
        "Revision history pages", dry_run
    )

    # Pages that are mostly "Primera edición" / revision metadata
    total_deleted += delete_by_filter(
        "content=ilike.*Primera edición*&content=not.ilike.*instalación*&content=not.ilike.*conexión*",
        "Edition metadata (no technical content)", dry_run
    )

    # English-only leftovers (section titles in English that slipped through language filter)
    total_deleted += delete_by_filter(
        "section_title=ilike.*REFERNCE REGULATION*",
        "REFERNCE REGULATION (English)", dry_run
    )
    total_deleted += delete_by_filter(
        "section_title=ilike.*Negative at  rest*",
        "Negative at rest (English)", dry_run
    )

    # Very short chunks (< 50 chars of real content after stripping whitespace)
    # These are usually just headers or page numbers
    r = CLIENT.get(
        f"{SUPABASE_URL}/rest/v1/chunks?select=id,content&limit=5000",
        headers={**HEADERS, "Prefer": ""},
    )
    if r.status_code == 200:
        short_ids = []
        for row in r.json():
            content = row.get("content", "").strip()
            # Remove repeated underscores, dashes, whitespace
            clean = re.sub(r'[_\-\s]+', ' ', content).strip()
            if len(clean) < 50:
                short_ids.append(row["id"])

        if short_ids:
            if dry_run:
                print(f"  Very short chunks (< 50 chars): {len(short_ids)} chunks (would delete)")
            else:
                for chunk_id in short_ids:
                    CLIENT.delete(
                        f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{chunk_id}",
                        headers=HEADERS,
                    )
                print(f"  Very short chunks (< 50 chars): {len(short_ids)} chunks deleted")
            total_deleted += len(short_ids)

    print(f"\n  Total junk removed: {total_deleted}")
    return total_deleted


def step2_fix_unknown_models(dry_run: bool):
    """Fix product_model for chunks that can be identified from source_file."""
    print("\n" + "=" * 60)
    print("STEP 2: Fix unknown product models")
    print("=" * 60)

    # Get all unknown chunks with their source files
    all_unknown = []
    offset = 0
    while True:
        r = CLIENT.get(
            f"{SUPABASE_URL}/rest/v1/chunks?product_model=eq.unknown&select=id,source_file,content&offset={offset}&limit=500",
            headers={**HEADERS, "Prefer": ""},
        )
        batch = r.json()
        if not batch:
            break
        all_unknown.extend(batch)
        offset += len(batch)
        if len(batch) < 500:
            break

    print(f"  Total unknown chunks: {len(all_unknown)}")

    if not all_unknown:
        return

    # Import the detect function with the fixed regex
    from src.ingestion.chunker import detect_product_model

    fixes = {}  # model -> list of ids
    still_unknown = 0

    for chunk in all_unknown:
        source = chunk.get("source_file", "")
        content = chunk.get("content", "")
        model = detect_product_model(content[:2000], source)
        if model != "unknown":
            if model not in fixes:
                fixes[model] = []
            fixes[model].append(chunk["id"])
        else:
            still_unknown += 1

    print(f"  Can fix: {sum(len(ids) for ids in fixes.values())} chunks across {len(fixes)} models")
    print(f"  Still unknown: {still_unknown}")

    if dry_run:
        for model, ids in sorted(fixes.items()):
            print(f"    {model}: {len(ids)} chunks")
        return

    for model, ids in fixes.items():
        for chunk_id in ids:
            CLIENT.patch(
                f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{chunk_id}",
                headers=HEADERS,
                json={"product_model": model},
            )
        print(f"    Fixed {model}: {len(ids)} chunks")


def step3_fix_zero_embeddings(dry_run: bool):
    """Re-embed chunks that have zero-vector embeddings (from rate limit failures)."""
    print("\n" + "=" * 60)
    print("STEP 3: Fix zero-vector embeddings")
    print("=" * 60)

    # Find chunks where embedding is all zeros
    # We can detect this by checking if the first component is 0
    # Using RPC or a custom query
    r = CLIENT.get(
        f"{SUPABASE_URL}/rest/v1/chunks?select=id,content,product_model,category,section_title,content_type&limit=5000",
        headers={**HEADERS, "Prefer": ""},
    )
    all_chunks = r.json()

    # We need to check embeddings - fetch them separately
    zero_chunks = []
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_ids = [c["id"] for c in all_chunks[i:i + batch_size]]
        ids_filter = ",".join(f'"{id}"' for id in batch_ids)

        r2 = CLIENT.get(
            f"{SUPABASE_URL}/rest/v1/chunks?id=in.({','.join(batch_ids)})&select=id,embedding&limit={batch_size}",
            headers={**HEADERS, "Prefer": ""},
        )
        if r2.status_code != 200:
            continue

        for row in r2.json():
            emb = row.get("embedding")
            if emb and isinstance(emb, str) and emb.startswith("[0,0,0,0"):
                zero_chunks.append(row["id"])

    print(f"  Chunks with zero embeddings: {len(zero_chunks)}")

    if not zero_chunks or dry_run:
        return

    # Re-embed these chunks
    # Build enriched text for each
    from scripts.re_embed import build_enriched_text

    chunks_to_fix = [c for c in all_chunks if c["id"] in set(zero_chunks)]
    texts = [build_enriched_text(c) for c in chunks_to_fix]

    print(f"  Re-embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts)

    for chunk, embedding in zip(chunks_to_fix, embeddings):
        # Skip if embedding is still zero (another rate limit)
        if all(v == 0.0 for v in embedding[:10]):
            continue
        CLIENT.patch(
            f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{chunk['id']}",
            headers=HEADERS,
            json={"embedding": embedding},
        )

    print(f"  Re-embedded {len(chunks_to_fix)} chunks")


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("STRUCTURAL FIXES FOR CHUNKS DATABASE")
    if dry_run:
        print("[DRY RUN MODE]")
    print("=" * 60)

    print(f"\nTotal chunks before: {count_chunks()}")

    step1_delete_junk(dry_run)
    step2_fix_unknown_models(dry_run)

    if not dry_run:
        print(f"\nTotal chunks after cleanup: {count_chunks()}")

    # Step 3 is slower (API calls for re-embedding), run separately if needed
    if "--fix-embeddings" in sys.argv:
        step3_fix_zero_embeddings(dry_run)


if __name__ == "__main__":
    main()
