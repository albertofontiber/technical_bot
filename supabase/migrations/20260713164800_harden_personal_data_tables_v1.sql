-- S107: close the inherited public-access gap on the three tables that hold
-- technician identity, queries, responses, feedback, or consent state.
--
-- Runtime access is deliberately narrow:
--   query_logs:  service_role SELECT + INSERT
--   feedback:    service_role SELECT + INSERT
--   user_consent: service_role SELECT + INSERT + UPDATE (required by upsert)
-- RGPD deletion remains an explicit owner/postgres operation, as documented in
-- docs/DG_DEPLOYMENT.md. No evaluator receives a database credential here.

DO $preconditions$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['query_logs', 'feedback', 'user_consent']
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NULL THEN
            RAISE EXCEPTION 'required table public.% is absent', table_name;
        END IF;
    END LOOP;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before hardening';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns AS c
        WHERE c.table_schema = 'public'
          AND c.table_name = 'query_logs'
          AND c.column_name = 'query'
          AND c.is_nullable = 'NO'
    ) THEN
        RAISE EXCEPTION 'query_logs.query contract is absent';
    END IF;
END
$preconditions$;

ALTER TABLE public.query_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback FORCE ROW LEVEL SECURITY;
ALTER TABLE public.user_consent ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_consent FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.query_logs
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON TABLE public.feedback
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON TABLE public.user_consent
    FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT, INSERT ON TABLE public.query_logs TO service_role;
GRANT SELECT, INSERT ON TABLE public.feedback TO service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.user_consent TO service_role;

DO $postconditions$
DECLARE
    table_name text;
    role_name text;
    privilege_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['query_logs', 'feedback', 'user_consent']
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = format('public.%I', table_name)::regclass
              AND relrowsecurity
              AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'RLS is not enabled and forced on public.%', table_name;
        END IF;

        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
        LOOP
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                'REFERENCES', 'TRIGGER'
            ]
            LOOP
                IF has_table_privilege(
                    role_name,
                    format('public.%I', table_name),
                    privilege_name
                ) THEN
                    RAISE EXCEPTION 'unexpected % privilege for % on public.%',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;

    IF NOT has_table_privilege('service_role', 'public.query_logs', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.query_logs', 'INSERT')
       OR has_table_privilege('service_role', 'public.query_logs', 'UPDATE')
       OR has_table_privilege('service_role', 'public.query_logs', 'DELETE') THEN
        RAISE EXCEPTION 'unexpected service_role privileges on public.query_logs';
    END IF;

    IF NOT has_table_privilege('service_role', 'public.feedback', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.feedback', 'INSERT')
       OR has_table_privilege('service_role', 'public.feedback', 'UPDATE')
       OR has_table_privilege('service_role', 'public.feedback', 'DELETE') THEN
        RAISE EXCEPTION 'unexpected service_role privileges on public.feedback';
    END IF;

    IF NOT has_table_privilege('service_role', 'public.user_consent', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.user_consent', 'INSERT')
       OR NOT has_table_privilege('service_role', 'public.user_consent', 'UPDATE')
       OR has_table_privilege('service_role', 'public.user_consent', 'DELETE') THEN
        RAISE EXCEPTION 'unexpected service_role privileges on public.user_consent';
    END IF;
END
$postconditions$;
