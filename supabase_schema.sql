-- Technical Bot PCI - Supabase Schema
-- Run this in the Supabase SQL Editor to set up the database
-- This is the FULL schema — safe to run on a fresh database (all IF NOT EXISTS)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    content_type TEXT,  -- procedure, specification, troubleshooting, wiring, general
    manufacturer TEXT,  -- e.g. Detnov, Notifier, Honeywell (must be set explicitly)
    has_diagram BOOLEAN DEFAULT FALSE,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity search index (increase lists for >100K chunks)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indexes for metadata filtering
CREATE INDEX IF NOT EXISTS idx_chunks_product_model ON chunks (product_model);
CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks (category);
CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks (content_type);
CREATE INDEX IF NOT EXISTS idx_chunks_manufacturer ON chunks (manufacturer);

-- RPC function for vector similarity search with manufacturer filter
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    content_type TEXT,
    has_diagram BOOLEAN,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    manufacturer TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.product_model,
        c.category,
        c.section_title,
        c.content_type,
        c.has_diagram,
        c.diagram_url,
        c.source_file,
        c.page_number,
        c.manufacturer,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE
        1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Keep creation and hardening of all personal-data tables in one transaction.
-- On a fresh bootstrap, a failed postcondition cannot leave an exposed table
-- committed by an autocommit client.
BEGIN;

-- Query logs for analytics and improvement
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    query TEXT NOT NULL,
    source TEXT DEFAULT 'text',  -- 'text' or 'voice'
    transcription TEXT,          -- original transcription if voice
    product_models TEXT[],       -- models detected in query
    category TEXT,               -- category detected
    chunks_used INTEGER DEFAULT 0,
    response TEXT,               -- full response sent (truncated to 4096 chars, Telegram limit)
    response_length INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    bot_version TEXT,            -- git short hash or tag of code that generated this row
    rag_trace JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS rag_trace JSONB;
-- One DO statement is atomic even when this bootstrap is run with autocommit:
-- a failed ADD rolls the DROP back instead of leaving the table unbounded.
DO $rag_trace_constraint$
BEGIN
    ALTER TABLE public.query_logs
        DROP CONSTRAINT IF EXISTS query_logs_rag_trace_object_size_v1;
    ALTER TABLE public.query_logs
        ADD CONSTRAINT query_logs_rag_trace_object_size_v1
        CHECK (
            rag_trace IS NULL
            OR (
                jsonb_typeof(rag_trace) = 'object'
                AND octet_length(rag_trace::text) <= 8192
            )
        );
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'query_logs'
          AND column_name = 'rag_trace'
          AND data_type = 'jsonb'
          AND is_nullable = 'YES'
          AND column_default IS NULL
          AND is_identity = 'NO'
          AND is_generated = 'NEVER'
    ) THEN
        RAISE EXCEPTION 'query_logs.rag_trace must be plain nullable jsonb';
    END IF;
END
$rag_trace_constraint$;

CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_user ON query_logs (telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_bot_version ON query_logs (bot_version);

-- Feedback from technicians
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    feedback_text TEXT NOT NULL,
    previous_query TEXT,         -- the query they're giving feedback on
    previous_response TEXT,      -- the response they're correcting
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback (created_at DESC);

-- RGPD consent tracking (one row per user who accepted terms via /accept)
CREATE TABLE IF NOT EXISTS user_consent (
    telegram_user_id BIGINT PRIMARY KEY,
    display_name TEXT,           -- optional, user-provided in /accept
    terms_version TEXT NOT NULL, -- e.g. "v1" — bump if terms change
    accepted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ       -- NULL while consent is active
);

CREATE INDEX IF NOT EXISTS idx_user_consent_active
ON user_consent (telegram_user_id)
WHERE revoked_at IS NULL;

-- Personal-data boundary for a fresh bootstrap. Keep this in sync with
-- 20260713164800_harden_personal_data_tables_v1.sql. One DO statement makes
-- all RLS/grant changes and their postconditions atomic under autocommit.
DO $personal_data_boundary$
DECLARE
    table_name text;
    role_name text;
    privilege_name text;
    expected_service_privileges text[];
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before hardening';
    END IF;

    FOREACH table_name IN ARRAY ARRAY['query_logs', 'feedback', 'user_consent']
    LOOP
        EXECUTE format(
            'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name
        );
        EXECUTE format(
            'ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name
        );
        EXECUTE format(
            'REVOKE ALL PRIVILEGES ON TABLE public.%I '
            'FROM PUBLIC, anon, authenticated, service_role',
            table_name
        );
    END LOOP;

    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.query_logs TO service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.feedback TO service_role';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.user_consent TO service_role';

    FOREACH table_name IN ARRAY ARRAY['query_logs', 'feedback', 'user_consent']
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = to_regclass(format('public.%I', table_name))
              AND relrowsecurity
              AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'personal-data RLS invariant failed for %', table_name;
        END IF;

        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
        LOOP
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                'REFERENCES', 'TRIGGER', 'MAINTAIN'
            ]
            LOOP
                IF has_table_privilege(
                    role_name,
                    format('public.%I', table_name),
                    privilege_name
                ) THEN
                    RAISE EXCEPTION 'unexpected % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
            ]
            LOOP
                IF has_any_column_privilege(
                    role_name,
                    format('public.%I', table_name),
                    privilege_name
                ) THEN
                    RAISE EXCEPTION 'unexpected column % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
        END LOOP;

        IF table_name = 'user_consent' THEN
            expected_service_privileges := ARRAY['SELECT', 'INSERT', 'UPDATE'];
        ELSE
            expected_service_privileges := ARRAY['SELECT', 'INSERT'];
        END IF;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ]
        LOOP
            IF has_table_privilege(
                'service_role',
                format('public.%I', table_name),
                privilege_name
            ) IS DISTINCT FROM (privilege_name = ANY(expected_service_privileges)) THEN
                RAISE EXCEPTION 'unexpected service_role % privilege on %',
                    privilege_name, table_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                'service_role',
                format('public.%I', table_name),
                privilege_name
            ) IS DISTINCT FROM (privilege_name = ANY(expected_service_privileges)) THEN
                RAISE EXCEPTION 'unexpected service_role column % privilege on %',
                    privilege_name, table_name;
            END IF;
        END LOOP;
    END LOOP;
END
$personal_data_boundary$;

COMMIT;

-- Create storage bucket for manual images
-- Note: Run this via Supabase dashboard:
-- Create bucket "manual-images" with public access
