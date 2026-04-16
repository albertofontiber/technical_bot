#!/usr/bin/env python3
"""Finish migration 001 backfill via direct Postgres connection.

The PostgREST API and Supabase SQL Editor both impose timeouts (~30-60s
HTTP + statement_timeout) that make it impractical to backfill the
remaining ~26k chunks via batched UPDATEs from the SQL Editor.

This script connects directly to Postgres using psycopg2 + DATABASE_URL,
sets a generous statement_timeout, and runs the UPDATE in batches with
per-batch commit so progress is durable even if interrupted.

Requires:
    pip install psycopg2-binary
    DATABASE_URL in .env (postgresql://postgres:PASS@host:5432/postgres)

Usage:
    python scripts/migrations/002_finish_backfill_direct.py
    python scripts/migrations/002_finish_backfill_direct.py --batch-size 2000
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed.")
    print("  Install with: pip install psycopg2-binary")
    sys.exit(1)


# Two passes:
#   Pass 1: exact match between chunks.source_file and documents.source_pdf_filename
#   Pass 2: match after stripping .pdf from documents.source_pdf_filename
PASSES = [
    (
        "exact match",
        """
        UPDATE chunks c
        SET document_id = d.id
        FROM documents d
        WHERE c.document_id IS NULL
          AND c.source_file = d.source_pdf_filename
          AND c.id IN (
            SELECT c2.id FROM chunks c2
            WHERE c2.document_id IS NULL
            LIMIT %s
          );
        """,
    ),
    (
        "match with .pdf stripped",
        """
        UPDATE chunks c
        SET document_id = d.id
        FROM documents d
        WHERE c.document_id IS NULL
          AND c.source_file = REPLACE(d.source_pdf_filename, '.pdf', '')
          AND c.id IN (
            SELECT c2.id FROM chunks c2
            WHERE c2.document_id IS NULL
            LIMIT %s
          );
        """,
    ),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-size", type=int, default=2000,
                   help="Rows per batch (default 2000). Lower if you hit timeouts.")
    p.add_argument("--statement-timeout", type=int, default=600,
                   help="Postgres statement_timeout in seconds (default 600).")
    args = p.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        print("  Add a line like: DATABASE_URL=postgresql://postgres:PASS@host:5432/postgres")
        print("  Get it from Supabase → Settings → Database → Connection string → URI")
        return 1

    print(f"Connecting to Postgres directly...", flush=True)
    print(f"  batch size: {args.batch_size}", flush=True)
    print(f"  statement_timeout: {args.statement_timeout}s", flush=True)
    print(f"  host: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'unknown'}", flush=True)
    print("Opening TCP+TLS+auth handshake...", flush=True)

    t0 = time.time()
    conn = psycopg2.connect(db_url, connect_timeout=30)
    print(f"  connected in {time.time()-t0:.1f}s", flush=True)
    conn.autocommit = False  # explicit per-batch commits
    cur = conn.cursor()

    # Increase statement_timeout for this session
    print("Setting statement_timeout...", flush=True)
    t0 = time.time()
    cur.execute(f"SET statement_timeout = '{args.statement_timeout}s';")
    conn.commit()
    print(f"  done in {time.time()-t0:.1f}s", flush=True)

    # Quick sanity query first
    print("Running sanity SELECT 1...", flush=True)
    t0 = time.time()
    cur.execute("SELECT 1;")
    cur.fetchone()
    print(f"  done in {time.time()-t0:.1f}s", flush=True)

    # Initial count — uses the partial index, should be fast
    print("Counting NULL chunks (uses partial index)...", flush=True)
    t0 = time.time()
    cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id IS NULL;")
    initial_null = cur.fetchone()[0]
    print(f"  done in {time.time()-t0:.1f}s", flush=True)
    print(f"Chunks with NULL document_id at start: {initial_null:,}", flush=True)
    print(flush=True)

    total_updated = 0
    start_time = time.time()

    for pass_name, sql in PASSES:
        print(f"=== Pass: {pass_name} ===")
        pass_updated = 0
        batch_num = 0
        while True:
            batch_num += 1
            batch_start = time.time()
            try:
                cur.execute(sql, (args.batch_size,))
                rows = cur.rowcount
                conn.commit()
            except psycopg2.errors.QueryCanceled:
                conn.rollback()
                print(f"  batch {batch_num}: TIMEOUT — try a smaller --batch-size")
                return 1
            except Exception as e:
                conn.rollback()
                print(f"  batch {batch_num}: ERROR {type(e).__name__}: {e}")
                return 1

            elapsed = time.time() - batch_start
            if rows == 0:
                print(f"  batch {batch_num}: 0 rows (pass complete)")
                break
            pass_updated += rows
            total_updated += rows
            print(f"  batch {batch_num}: {rows:,} rows in {elapsed:.1f}s "
                  f"(pass total {pass_updated:,}, grand total {total_updated:,})")

        print(f"  pass total: {pass_updated:,} rows linked")
        print()

    # Final count
    cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id IS NULL;")
    final_null = cur.fetchone()[0]
    elapsed_total = time.time() - start_time

    print("=" * 60)
    print(f"Done in {elapsed_total:.1f}s")
    print(f"  Chunks linked this run:     {total_updated:,}")
    print(f"  Chunks NULL before:         {initial_null:,}")
    print(f"  Chunks NULL after:          {final_null:,}")
    if final_null == 0:
        print("\n✅ Backfill complete. All chunks have document_id.")
        print("\nYou can now drop the temporary index:")
        print("  DROP INDEX idx_chunks_null_docid;")
    else:
        print(f"\n⚠️  {final_null:,} chunks still have NULL document_id.")
        print("  These likely have source_file values with no matching document.")
        print("  Investigate with:")
        print("    SELECT DISTINCT source_file FROM chunks WHERE document_id IS NULL LIMIT 20;")

    cur.close()
    conn.close()
    return 0 if final_null == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
