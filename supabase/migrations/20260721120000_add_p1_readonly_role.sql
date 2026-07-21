-- S277 P1: dedicated PostgREST role for the paid read-only release gate.
--
-- This migration provisions no password/JWT, acquires no fence lock and does not
-- grant the expensive corpus_fingerprint_v1() RPC.  The operator credential that
-- owns the SHARE fence remains separate from this runner role.  That persistent
-- fence connection may use direct db.<ref>:5432 or the sealed Supavisor session
-- endpoint aws-1-eu-north-1.pooler.supabase.com:5432, never :6543.
--
-- PostgreSQL privileges are additive: PUBLIC function privileges cannot be denied
-- to one role.  The P1 HTTP adapter must therefore retain its exact RPC allowlist;
-- this role supplies the independent table/RLS no-write boundary.

BEGIN;

DO $preflight$
DECLARE
    required_relation TEXT;
    required_function TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        RAISE EXCEPTION 'S277 p1_readonly requires the Supabase authenticator role';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        RAISE EXCEPTION 'S277 p1_readonly requires the Supabase postgres operator role';
    END IF;

    FOREACH required_relation IN ARRAY ARRAY[
        'public.chunks_v2',
        'public.chunks_v2_enunciados',
        'public.chunks_v2_hyq',
        'public.documents',
        'public.document_visual_assets'
    ] LOOP
        IF to_regclass(required_relation) IS NULL THEN
            RAISE EXCEPTION 'S277 p1_readonly missing relation %', required_relation;
        END IF;
    END LOOP;

    FOREACH required_function IN ARRAY ARRAY[
        'public.match_chunks_v2(public.vector,double precision,integer,text,text,text,boolean)',
        'public.search_chunks_text_v2(text,text,text,text,integer)',
        'public.match_chunks_v2_enunciados(public.vector,double precision,integer,text,text)',
        'public.match_hyq(public.vector,double precision,integer)'
    ] LOOP
        IF to_regprocedure(required_function) IS NULL THEN
            RAISE EXCEPTION 'S277 p1_readonly missing function %', required_function;
        END IF;
    END LOOP;
END
$preflight$;

DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'p1_readonly') THEN
        CREATE ROLE p1_readonly
            NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS;
    ELSE
        IF EXISTS (
            SELECT 1
            FROM pg_roles
            WHERE rolname = 'p1_readonly'
              AND (
                  rolsuper OR rolinherit OR rolcreaterole OR rolcreatedb
                  OR rolcanlogin OR rolreplication OR rolbypassrls
              )
        ) THEN
            RAISE EXCEPTION 'existing p1_readonly role has unsafe attributes';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_auth_members AS membership
            JOIN pg_roles AS member ON member.oid = membership.member
            WHERE member.rolname = 'p1_readonly'
        ) THEN
            RAISE EXCEPTION 'existing p1_readonly role is already a member of another role';
        END IF;
    END IF;
END
$role$;

-- PostgREST impersonates this role with SET LOCAL ROLE.  PostgreSQL does not
-- apply ALTER ROLE defaults at SET ROLE time, and setting
-- default_transaction_read_only inside an already-open transaction would not
-- make a VOLATILE POST RPC read-only.  The effective no-write boundary below
-- is therefore ACL/RLS + exact RPC/HTTP allowlisting, not a misleading GUC.
ALTER ROLE p1_readonly RESET default_transaction_read_only;
ALTER ROLE p1_readonly SET statement_timeout = '30s';

-- PostgreSQL 17 automatically grants a newly created role back to a
-- non-superuser CREATEROLE creator with ADMIN TRUE, SET FALSE and INHERIT
-- FALSE.  The fence connects as the hosted Supabase `postgres` operator and
-- must be able to reduce itself to p1_readonly for catalog capture.  Preserve
-- the unavoidable creator ADMIN option, disable inheritance and enable only
-- explicit SET ROLE.
GRANT p1_readonly TO postgres WITH INHERIT FALSE;
GRANT p1_readonly TO postgres WITH SET TRUE;
GRANT p1_readonly TO postgres WITH ADMIN TRUE;

GRANT p1_readonly TO authenticator WITH INHERIT FALSE;
GRANT p1_readonly TO authenticator WITH SET TRUE;
GRANT p1_readonly TO authenticator WITH ADMIN FALSE;

CREATE FUNCTION public.p1_runtime_identity_v1()
RETURNS JSONB
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = pg_catalog
AS $function$
    SELECT jsonb_build_object(
        'current_user', current_user,
        'transaction_read_only', current_setting('transaction_read_only'),
        'statement_timeout', current_setting('statement_timeout')
    );
$function$;

REVOKE ALL PRIVILEGES ON FUNCTION public.p1_runtime_identity_v1()
FROM PUBLIC, anon, authenticated, service_role, p1_readonly;
GRANT EXECUTE ON FUNCTION public.p1_runtime_identity_v1() TO p1_readonly;

REVOKE ALL PRIVILEGES ON SCHEMA public FROM p1_readonly;
GRANT USAGE ON SCHEMA public TO p1_readonly;

REVOKE ALL PRIVILEGES ON TABLE
    public.chunks_v2,
    public.chunks_v2_enunciados,
    public.chunks_v2_hyq,
    public.documents,
    public.document_visual_assets
FROM p1_readonly;

GRANT SELECT ON TABLE
    public.chunks_v2,
    public.chunks_v2_enunciados,
    public.chunks_v2_hyq,
    public.documents,
    public.document_visual_assets
TO p1_readonly;

REVOKE ALL PRIVILEGES ON FUNCTION public.match_chunks_v2(
    public.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, BOOLEAN
) FROM p1_readonly;
REVOKE ALL PRIVILEGES ON FUNCTION public.search_chunks_text_v2(
    TEXT, TEXT, TEXT, TEXT, INTEGER
) FROM p1_readonly;
REVOKE ALL PRIVILEGES ON FUNCTION public.match_chunks_v2_enunciados(
    public.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT
) FROM p1_readonly;
REVOKE ALL PRIVILEGES ON FUNCTION public.match_hyq(
    public.vector, DOUBLE PRECISION, INTEGER
) FROM p1_readonly;

GRANT EXECUTE ON FUNCTION public.match_chunks_v2(
    public.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, BOOLEAN
) TO p1_readonly;
GRANT EXECUTE ON FUNCTION public.search_chunks_text_v2(
    TEXT, TEXT, TEXT, TEXT, INTEGER
) TO p1_readonly;
GRANT EXECUTE ON FUNCTION public.match_chunks_v2_enunciados(
    public.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT
) TO p1_readonly;
GRANT EXECUTE ON FUNCTION public.match_hyq(
    public.vector, DOUBLE PRECISION, INTEGER
) TO p1_readonly;

-- A live preflight found this maintenance helper as SECURITY DEFINER with
-- PUBLIC EXECUTE.  Remove the inherited capability for all custom roles while
-- preserving any explicit grants already owned by trusted platform roles.
DO $revoke_public_security_definer$
BEGIN
    IF to_regprocedure('public.create_hnsw_index()') IS NOT NULL THEN
        EXECUTE 'REVOKE EXECUTE ON FUNCTION public.create_hnsw_index() FROM PUBLIC';
    END IF;
END
$revoke_public_security_definer$;

-- chunks_v2 already has RLS enabled in production and, before this migration,
-- has no policy for the new role.  The remaining four relations currently do
-- not use RLS; their explicit SELECT-only ACL is the read boundary.
CREATE POLICY chunks_v2_p1_readonly_select
ON public.chunks_v2
AS PERMISSIVE
FOR SELECT
TO p1_readonly
USING (true);

COMMENT ON ROLE p1_readonly IS
'S277 P1 NOLOGIN/NOBYPASSRLS ACL-constrained PostgREST role; JWT issuance and fence ownership are external.';

COMMENT ON FUNCTION public.p1_runtime_identity_v1() IS
'S277 P1 identity probe. transaction_read_only describes this GET transaction only; POST RPC safety is enforced by ACL/RLS plus the exact HTTP allowlist.';

DO $postcondition$
DECLARE
    relation_name TEXT;
BEGIN
    IF (
        SELECT count(*)
        FROM pg_auth_members AS membership
        JOIN pg_roles AS granted_role
          ON granted_role.oid = membership.roleid
        WHERE granted_role.rolname = 'p1_readonly'
    ) <> 2 THEN
        RAISE EXCEPTION 'p1_readonly membership set is unsafe';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_auth_members AS membership
        JOIN pg_roles AS granted_role
          ON granted_role.oid = membership.roleid
        JOIN pg_roles AS member_role
          ON member_role.oid = membership.member
        WHERE granted_role.rolname = 'p1_readonly'
          AND member_role.rolname = 'authenticator'
          AND membership.set_option
          AND NOT membership.inherit_option
          AND NOT membership.admin_option
    ) THEN
        RAISE EXCEPTION 'authenticator membership options are unsafe';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_auth_members AS membership
        JOIN pg_roles AS granted_role
          ON granted_role.oid = membership.roleid
        JOIN pg_roles AS member_role
          ON member_role.oid = membership.member
        WHERE granted_role.rolname = 'p1_readonly'
          AND member_role.rolname = 'postgres'
          AND membership.set_option
          AND NOT membership.inherit_option
          AND membership.admin_option
    ) THEN
        RAISE EXCEPTION 'postgres operator membership options are unsafe';
    END IF;

    FOREACH relation_name IN ARRAY ARRAY[
        'public.chunks_v2',
        'public.chunks_v2_enunciados',
        'public.chunks_v2_hyq',
        'public.documents',
        'public.document_visual_assets'
    ] LOOP
        IF NOT has_table_privilege('p1_readonly', relation_name, 'SELECT')
           OR has_table_privilege('p1_readonly', relation_name, 'INSERT')
           OR has_table_privilege('p1_readonly', relation_name, 'UPDATE')
           OR has_table_privilege('p1_readonly', relation_name, 'DELETE')
           OR has_table_privilege('p1_readonly', relation_name, 'TRUNCATE')
           OR has_table_privilege('p1_readonly', relation_name, 'REFERENCES')
           OR has_table_privilege('p1_readonly', relation_name, 'TRIGGER') THEN
            RAISE EXCEPTION 'unsafe p1_readonly table privileges on %', relation_name;
        END IF;
    END LOOP;

    IF has_function_privilege(
        'p1_readonly', 'public.corpus_fingerprint_v1()', 'EXECUTE'
    ) THEN
        -- The function currently has no PUBLIC EXECUTE grant.  If that changes,
        -- the effective privilege check catches it and the migration rolls back.
        RAISE EXCEPTION 'p1_readonly must not execute corpus_fingerprint_v1()';
    END IF;

    IF NOT has_function_privilege(
        'p1_readonly', 'public.p1_runtime_identity_v1()', 'EXECUTE'
    ) OR has_function_privilege(
        'anon', 'public.p1_runtime_identity_v1()', 'EXECUTE'
    ) OR has_function_privilege(
        'authenticated', 'public.p1_runtime_identity_v1()', 'EXECUTE'
    ) OR has_function_privilege(
        'service_role', 'public.p1_runtime_identity_v1()', 'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'p1_runtime_identity_v1() ACL is not isolated';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles AS role
        JOIN pg_db_role_setting AS setting ON setting.setrole = role.oid
        WHERE role.rolname = 'p1_readonly'
          AND setting.setdatabase = 0
          AND setting.setconfig @> ARRAY['statement_timeout=30s']
          AND NOT setting.setconfig @> ARRAY['default_transaction_read_only=on']
    ) THEN
        RAISE EXCEPTION 'p1_readonly safety settings are missing';
    END IF;

    IF has_schema_privilege('p1_readonly', 'public', 'CREATE') THEN
        RAISE EXCEPTION 'p1_readonly must not CREATE in schema public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_proc AS proc
        JOIN pg_namespace AS namespace
          ON namespace.oid = proc.pronamespace
        WHERE namespace.nspname = 'public'
          AND proc.prosecdef
          AND has_function_privilege(
              'p1_readonly', proc.oid, 'EXECUTE'
          )
    ) THEN
        RAISE EXCEPTION 'p1_readonly can execute a SECURITY DEFINER function';
    END IF;
END
$postcondition$;

-- PostgREST caches role settings; make the timeout visible to the Client API
-- after this transaction commits.
NOTIFY pgrst, 'reload config';

COMMIT;
