-- S277: privacy-bounded, versioned runtime receipts for the production RAG path.
-- The trace lives on the existing consent-governed query_logs row, so retention,
-- deletion, RLS, and grants remain atomic with the query record. No index is
-- added: the initial use is bounded release verification, not JSONB search.

BEGIN;

DO $preconditions$
DECLARE
    role_name text;
    privilege_name text;
BEGIN
    IF to_regclass('public.query_logs') IS NULL THEN
        RAISE EXCEPTION 'required table public.query_logs is absent';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE oid = 'public.query_logs'::regclass
          AND relrowsecurity
          AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'query_logs must have RLS enabled and forced before rag_trace';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before rag_trace';
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
                'public.query_logs',
                privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected pre-migration % privilege for % on query_logs',
                    privilege_name, role_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                role_name,
                'public.query_logs',
                privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected pre-migration column % privilege for % on query_logs',
                    privilege_name, role_name;
            END IF;
        END LOOP;
    END LOOP;

    IF NOT has_table_privilege('service_role', 'public.query_logs', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.query_logs', 'INSERT')
       OR has_table_privilege('service_role', 'public.query_logs', 'UPDATE')
       OR has_table_privilege('service_role', 'public.query_logs', 'DELETE')
       OR has_table_privilege('service_role', 'public.query_logs', 'TRUNCATE')
       OR has_table_privilege('service_role', 'public.query_logs', 'REFERENCES')
       OR has_table_privilege('service_role', 'public.query_logs', 'TRIGGER')
       OR has_table_privilege('service_role', 'public.query_logs', 'MAINTAIN') THEN
        RAISE EXCEPTION 'unexpected pre-migration service_role privileges on query_logs';
    END IF;
    IF NOT has_any_column_privilege(
            'service_role', 'public.query_logs', 'SELECT'
       )
       OR NOT has_any_column_privilege(
            'service_role', 'public.query_logs', 'INSERT'
       )
       OR has_any_column_privilege(
            'service_role', 'public.query_logs', 'UPDATE'
       )
       OR has_any_column_privilege(
            'service_role', 'public.query_logs', 'REFERENCES'
       ) THEN
        RAISE EXCEPTION 'unexpected pre-migration service_role column privileges on query_logs';
    END IF;
END
$preconditions$;

ALTER TABLE public.query_logs
    ADD COLUMN IF NOT EXISTS rag_trace jsonb;

-- Recreate inside this explicit transaction. A same-named drifted constraint
-- can never be mistaken for the intended contract, and any failure restores
-- the previous state on rollback.
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
    ) NOT VALID;

ALTER TABLE public.query_logs
    VALIDATE CONSTRAINT query_logs_rag_trace_object_size_v1;

DO $postconditions$
DECLARE
    role_name text;
    privilege_name text;
BEGIN
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
        RAISE EXCEPTION 'query_logs.rag_trace must be nullable jsonb';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.query_logs'::regclass
          AND conname = 'query_logs_rag_trace_object_size_v1'
          AND contype = 'c'
          AND convalidated
    ) THEN
        RAISE EXCEPTION 'rag_trace constraint is missing or unvalidated';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role lost BYPASSRLS during rag_trace migration';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE oid = 'public.query_logs'::regclass
          AND relrowsecurity
          AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'rag_trace migration changed query_logs RLS invariants';
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
                'public.query_logs',
                privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected % privilege for % on query_logs',
                    privilege_name, role_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                role_name,
                'public.query_logs',
                privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected column % privilege for % on query_logs',
                    privilege_name, role_name;
            END IF;
        END LOOP;
    END LOOP;

    IF NOT has_table_privilege('service_role', 'public.query_logs', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.query_logs', 'INSERT')
       OR has_table_privilege('service_role', 'public.query_logs', 'UPDATE')
       OR has_table_privilege('service_role', 'public.query_logs', 'DELETE')
       OR has_table_privilege('service_role', 'public.query_logs', 'TRUNCATE')
       OR has_table_privilege('service_role', 'public.query_logs', 'REFERENCES')
       OR has_table_privilege('service_role', 'public.query_logs', 'TRIGGER')
       OR has_table_privilege('service_role', 'public.query_logs', 'MAINTAIN') THEN
        RAISE EXCEPTION 'rag_trace migration changed service_role privileges';
    END IF;
    IF NOT has_any_column_privilege(
            'service_role', 'public.query_logs', 'SELECT'
       )
       OR NOT has_any_column_privilege(
            'service_role', 'public.query_logs', 'INSERT'
       )
       OR has_any_column_privilege(
            'service_role', 'public.query_logs', 'UPDATE'
       )
       OR has_any_column_privilege(
            'service_role', 'public.query_logs', 'REFERENCES'
       ) THEN
        RAISE EXCEPTION 'rag_trace migration changed service_role column privileges';
    END IF;
END
$postconditions$;

COMMIT;
