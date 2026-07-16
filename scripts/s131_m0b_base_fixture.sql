\set ON_ERROR_STOP on

-- Minimal Supabase-shaped fixture for S131 M0b on a disposable database.
-- It contains no production data and intentionally omits API services.
CREATE ROLE anon NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE ROLE authenticated NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE ROLE service_role NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION BYPASSRLS;

CREATE SCHEMA extensions;
CREATE EXTENSION vector WITH SCHEMA extensions;
CREATE EXTENSION unaccent;

CREATE TEXT SEARCH CONFIGURATION public.spanish_unaccent
    (COPY = pg_catalog.spanish);
ALTER TEXT SEARCH CONFIGURATION public.spanish_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH public.unaccent, pg_catalog.spanish_stem;

CREATE TABLE public.documents (
    id UUID PRIMARY KEY,
    source_pdf_sha256 TEXT,
    status TEXT NOT NULL
);
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE TABLE public.chunks_v2 (
    id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    document_id UUID REFERENCES public.documents(id),
    extraction_sha256 TEXT NOT NULL,
    chunk_index INTEGER,
    content TEXT NOT NULL,
    context TEXT,
    embedding extensions.vector(1024),
    search_vector TSVECTOR,
    language TEXT,
    section_title TEXT,
    section_path TEXT,
    content_type TEXT,
    is_flow_diagram BOOLEAN NOT NULL DEFAULT FALSE,
    confidence REAL,
    product_model TEXT,
    manufacturer TEXT,
    distributor TEXT,
    protocol TEXT,
    doc_type TEXT,
    category TEXT,
    has_diagram BOOLEAN NOT NULL DEFAULT FALSE,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    duplicate_of UUID REFERENCES public.chunks_v2(id),
    parent_id UUID REFERENCES public.chunks_v2(id),
    ingest_batch TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);

COMMENT ON TABLE public.chunks_v2 IS
'S131 disposable empty antecedent; no production chunks.';
