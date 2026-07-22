-- S277: least-privilege P1 access to the verified-lineage snapshot.
--
-- document_local_snapshot_v2 is SECURITY INVOKER.  The ephemeral P1 role
-- therefore needs the two lineage-registry columns read by the function and
-- EXECUTE on that exact signature.  It receives neither the registry's
-- evidence/notes columns nor any write capability.  RLS exposes verified
-- lineages only; the P1 HTTP guard separately denies direct table paths.

DO $precondition$
BEGIN
    IF pg_catalog.to_regrole('p1_readonly') IS NULL THEN
        RAISE EXCEPTION 'S277 document-local P1 ACL requires p1_readonly';
    END IF;
    IF pg_catalog.to_regprocedure(
        'public.document_local_snapshot_v2(jsonb,text,integer,integer)'
    ) IS NULL THEN
        RAISE EXCEPTION 'S277 document-local P1 ACL requires snapshot v2';
    END IF;
    IF pg_catalog.to_regclass(
        'public.document_revision_lineages'
    ) IS NULL THEN
        RAISE EXCEPTION 'S277 document-local P1 ACL requires lineage registry';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_catalog.pg_policy AS policy
        JOIN pg_catalog.pg_class AS relation
          ON relation.oid = policy.polrelid
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'public'
          AND relation.relname = 'document_revision_lineages'
          AND policy.polname = 'document_revision_lineages_p1_verified_select'
    ) THEN
        RAISE EXCEPTION 'S277 document-local P1 policy already exists';
    END IF;
END
$precondition$;

REVOKE ALL PRIVILEGES ON TABLE public.document_revision_lineages
FROM p1_readonly;
GRANT SELECT (id, authority_status)
ON public.document_revision_lineages
TO p1_readonly;

CREATE POLICY document_revision_lineages_p1_verified_select
ON public.document_revision_lineages
AS PERMISSIVE
FOR SELECT
TO p1_readonly
USING (authority_status = 'verified');

REVOKE ALL ON FUNCTION public.document_local_snapshot_v2(
    JSONB, TEXT, INTEGER, INTEGER
) FROM PUBLIC, anon, authenticated, p1_readonly;
GRANT EXECUTE ON FUNCTION public.document_local_snapshot_v2(
    JSONB, TEXT, INTEGER, INTEGER
) TO service_role, p1_readonly;

DO $postcondition$
BEGIN
    IF NOT pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'id',
        'SELECT'
    ) OR NOT pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'authority_status',
        'SELECT'
    ) OR pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'authority_contract',
        'SELECT'
    ) OR pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'authority_evidence_sha256',
        'SELECT'
    ) OR pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'created_at',
        'SELECT'
    ) OR pg_catalog.has_column_privilege(
        'p1_readonly',
        'public.document_revision_lineages',
        'notes',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'p1_readonly lineage-registry column ACL is unsafe';
    END IF;

    IF pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'SELECT'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'INSERT'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'UPDATE'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'DELETE'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'TRUNCATE'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'REFERENCES'
    ) OR pg_catalog.has_table_privilege(
        'p1_readonly', 'public.document_revision_lineages', 'TRIGGER'
    ) THEN
        RAISE EXCEPTION 'p1_readonly lineage-registry table ACL is unsafe';
    END IF;

    IF NOT pg_catalog.has_function_privilege(
        'p1_readonly',
        'public.document_local_snapshot_v2(jsonb,text,integer,integer)',
        'EXECUTE'
    ) OR NOT pg_catalog.has_function_privilege(
        'service_role',
        'public.document_local_snapshot_v2(jsonb,text,integer,integer)',
        'EXECUTE'
    ) OR pg_catalog.has_function_privilege(
        'anon',
        'public.document_local_snapshot_v2(jsonb,text,integer,integer)',
        'EXECUTE'
    ) OR pg_catalog.has_function_privilege(
        'authenticated',
        'public.document_local_snapshot_v2(jsonb,text,integer,integer)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'document_local_snapshot_v2 execution ACL is unsafe';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_policy AS policy
        JOIN pg_catalog.pg_class AS relation
          ON relation.oid = policy.polrelid
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'public'
          AND relation.relname = 'document_revision_lineages'
          AND policy.polname = 'document_revision_lineages_p1_verified_select'
          AND policy.polcmd = 'r'
          AND policy.polpermissive
          AND policy.polroles = ARRAY[
              (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = 'p1_readonly')
          ]
          AND pg_catalog.pg_get_expr(
              policy.polqual, policy.polrelid
          ) = '(authority_status = ''verified''::text)'
          AND policy.polwithcheck IS NULL
    ) THEN
        RAISE EXCEPTION 'p1_readonly verified-lineage RLS policy is unsafe';
    END IF;
END
$postcondition$;

NOTIFY pgrst, 'reload schema';
