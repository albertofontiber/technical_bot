"""Run migration 003 via direct Postgres (drop index → bulk UPDATE → recreate).

GIN incremental index rebuild on each UPDATE row is the bottleneck. Dropping
the search_vector index before bulk UPDATE + bulk CREATE INDEX after is
standard Postgres technique — typically 10-50× faster on large tables.

Idempotent: re-running replays all steps safely.
"""
from __future__ import annotations
import os
import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2

DB_URL = os.environ["DATABASE_URL"]

REPLACE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION public.chunks_search_vector_update()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.section_title, '')), 'A') ||
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.content, '')), 'B');
  RETURN NEW;
END;
$$;
"""

UPDATE_REMAINING = r"""
UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE search_vector::text !~ ':\d+[A-D]';
"""

DROP_INDEX = "DROP INDEX IF EXISTS idx_chunks_search_vector;"
CREATE_INDEX = "CREATE INDEX idx_chunks_search_vector ON chunks USING gin (search_vector);"

VALIDATION_SQL = {
    "C.1 hp001 target chunks (deben tener rank > 0)": """
        SELECT id, LEFT(section_title, 60) AS title_preview,
               ts_rank(search_vector,
                   plainto_tsquery('public.spanish_unaccent', 'ajustes avanzado')) AS rank
        FROM chunks
        WHERE id IN (
            '267d9584-1fa9-4a69-aad0-7166f66b5432',
            'b7476847-be0b-4552-91ed-bcb8d0d097d5'
        );
    """,
    "C.2 hits_after (ajustes avanzado en CAD-250)": """
        SELECT COUNT(*) AS hits_after
        FROM chunks
        WHERE source_file LIKE '%CAD-250%'
          AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'ajustes avanzado');
    """,
    "C.3 top-5 CAD-250 por ts_rank 'menú programación avanzada'": """
        SELECT
            ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector,
                plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) DESC) AS pos,
            id, LEFT(COALESCE(section_title, ''), 60) AS title_preview,
            ts_rank(search_vector,
                plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) AS rank
        FROM chunks
        WHERE source_file LIKE '%CAD-250%'
        ORDER BY ts_rank(search_vector,
            plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) DESC
        LIMIT 5;
    """,
    "C.4 no-regression (queries históricas)": """
        SELECT
            (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%'
             AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'menú')) AS menu,
            (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%'
             AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'configuración')) AS configuracion,
            (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%'
             AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'avanzado')) AS avanzado;
    """,
}


def step(label: str, cur, sql: str, timed: bool = True) -> None:
    print(f"\n▶ {label}", flush=True)
    t0 = time.time()
    cur.execute(sql)
    if timed:
        print(f"  elapsed: {time.time() - t0:.1f}s", flush=True)


def main() -> int:
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            # Diagnostic: how many still need weights
            cur.execute(r"""
                SELECT COUNT(*) FILTER (WHERE search_vector::text !~ ':\d+[A-D]') AS needs_update,
                       COUNT(*) AS total FROM chunks
            """)
            needs, total = cur.fetchone()
            print(f"Total chunks: {total:,}  ·  Needs weighted update: {needs:,} ({100*needs/total:.1f}%)", flush=True)

            # 1. Replace trigger function (so future INSERTs get weighted)
            step("1. Replace trigger function (weighted)", cur, REPLACE_TRIGGER_FUNCTION, timed=False)
            print("  ✓ trigger function replaced", flush=True)

            # 2. Drop GIN index (speeds up bulk UPDATE ~10-50×)
            step("2. DROP INDEX idx_chunks_search_vector", cur, DROP_INDEX)
            print("  ✓ GIN index dropped (will be recreated at end)", flush=True)

            # 3. Bulk UPDATE with SET LOCAL statement_timeout=0 (pooler default is 2min)
            print("\n▶ 3. Bulk UPDATE remaining rows (tsvector only, no index update)", flush=True)
            cur.execute("BEGIN")
            cur.execute("SET LOCAL statement_timeout = 0")
            t0 = time.time()
            cur.execute(UPDATE_REMAINING)
            rows = cur.rowcount
            elapsed = time.time() - t0
            cur.execute("COMMIT")
            print(f"  rows updated: {rows:,}  elapsed: {elapsed:.1f}s  (rate: {rows/max(elapsed,0.1):.0f} rows/s)", flush=True)

            # 4. Recreate GIN index (bulk build much faster than row-by-row)
            print("\n▶ 4. CREATE INDEX idx_chunks_search_vector (bulk)", flush=True)
            cur.execute("BEGIN")
            cur.execute("SET LOCAL statement_timeout = 0")
            t0 = time.time()
            cur.execute(CREATE_INDEX)
            elapsed = time.time() - t0
            cur.execute("COMMIT")
            print(f"  GIN index rebuilt  elapsed: {elapsed:.1f}s", flush=True)

            # 5. Validation (FASE C)
            print("\n" + "=" * 70, flush=True)
            print("FASE C — VALIDACIÓN", flush=True)
            print("=" * 70, flush=True)
            for label, sql in VALIDATION_SQL.items():
                print(f"\n--- {label} ---", flush=True)
                cur.execute(sql)
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
                widths = [max(len(str(r[i])) for r in rows + [cols]) for i in range(len(cols))]
                print("  " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)), flush=True)
                print("  " + "-+-".join("-" * w for w in widths), flush=True)
                for r in rows:
                    print("  " + " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)), flush=True)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
