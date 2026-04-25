"""Replace search_chunks_text RPC to use search_vector (post-migration-003).

The original RPC computed to_tsvector('spanish', content) inline on every
query — ignoring the GIN index, the spanish_unaccent config, and the
section_title weight added in migration 003. This rewrite uses the
weighted search_vector column directly.
"""
from __future__ import annotations
import os
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2

DB_URL = os.environ["DATABASE_URL"]

RPC_4ARG = """
CREATE OR REPLACE FUNCTION public.search_chunks_text(
    search_query text,
    filter_product text DEFAULT NULL,
    filter_manufacturer text DEFAULT NULL,
    match_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid, content text, product_model text, category text,
    section_title text, content_type text, manufacturer text,
    protocol text, doc_type text, has_diagram boolean, diagram_url text,
    source_file text, page_number integer
)
LANGUAGE sql STABLE AS $$
    SELECT c.id, c.content, c.product_model, c.category, c.section_title,
           c.content_type, c.manufacturer, c.protocol, c.doc_type,
           c.has_diagram, c.diagram_url, c.source_file, c.page_number
    FROM chunks c
    WHERE c.search_vector @@ plainto_tsquery('public.spanish_unaccent', search_query)
      AND (filter_product IS NULL OR c.product_model = filter_product)
      AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY ts_rank(c.search_vector, plainto_tsquery('public.spanish_unaccent', search_query)) DESC
    LIMIT match_limit;
$$;
"""

RPC_5ARG = """
CREATE OR REPLACE FUNCTION public.search_chunks_text(
    search_query text,
    filter_product text DEFAULT NULL,
    filter_manufacturer text DEFAULT NULL,
    filter_category text DEFAULT NULL,
    match_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid, content text, product_model text, category text,
    section_title text, content_type text, manufacturer text,
    protocol text, doc_type text, has_diagram boolean, diagram_url text,
    source_file text, page_number integer
)
LANGUAGE sql STABLE AS $$
    SELECT c.id, c.content, c.product_model, c.category, c.section_title,
           c.content_type, c.manufacturer, c.protocol, c.doc_type,
           c.has_diagram, c.diagram_url, c.source_file, c.page_number
    FROM chunks c
    WHERE c.search_vector @@ plainto_tsquery('public.spanish_unaccent', search_query)
      AND (filter_product IS NULL OR c.product_model = filter_product)
      AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
      AND (filter_category IS NULL OR c.category = filter_category)
    ORDER BY ts_rank(c.search_vector, plainto_tsquery('public.spanish_unaccent', search_query)) DESC
    LIMIT match_limit;
$$;
"""


def main() -> int:
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(RPC_4ARG)
        print("  ✓ search_chunks_text (4-arg) → usa search_vector + spanish_unaccent + ts_rank")

        cur.execute(RPC_5ARG)
        print("  ✓ search_chunks_text (5-arg) reemplazada")

        # Verify hp001 chunks rank #1/#2 with this new RPC
        cur.execute(
            """
            SELECT c.id, LEFT(c.section_title, 60) AS title,
                   ts_rank(c.search_vector,
                       plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) AS rank
            FROM chunks c
            WHERE c.search_vector @@ plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')
              AND c.product_model = 'CAD-250'
            ORDER BY ts_rank(c.search_vector,
                plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) DESC
            LIMIT 5;
            """
        )
        print("\n=== Top-5 (CAD-250) por ts_rank weighted ===")
        for r in cur.fetchall():
            print(f"  id={r[0]}  rank={r[2]:.4f}  title={r[1]}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
