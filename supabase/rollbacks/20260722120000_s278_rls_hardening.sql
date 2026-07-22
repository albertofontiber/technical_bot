-- ROLLBACK MANUAL SOLO. Supabase no aplica ficheros de este directorio.
--
-- *** ADVERTENCIA: este rollback RESTAURA UNA EXPOSICIÓN CONFIRMADA (#29) ***
-- Vuelve a dejar public.chunks_v2_enunciados legible/escribible por
-- anon/authenticated y re-otorga EXECUTE sobre create_hnsw_index() (SECURITY
-- DEFINER). Ejecutar SOLO con visto explícito de Alberto y motivo documentado
-- (p. ej. rotura del bot atribuida al gate — NO esperada: service_role tiene
-- BYPASSRLS y el smoke debe ser invariante).
--
-- Espejo de supabase/migrations/20260722120000_s278_rls_hardening.sql, con dos
-- desviaciones deliberadas del espejo literal:
--   1. chunks_v2 NO se toca: su RLS estaba habilitado en producción ANTES de la
--      migración (20260721120000 lo documenta y le creó policy p1); deshabilitarlo
--      dejaría el sistema POR DEBAJO del estado pre-migración.
--   2. Solo se restauran los grants CONFIRMADOS por TECH_DEBT #29 (SELECT/INSERT
--      a anon/authenticated en chunks_v2_enunciados; EXECUTE a anon/authenticated
--      en create_hnsw_index()). NO se re-otorga nada a PUBLIC: la revocación de
--      PUBLIC sobre create_hnsw_index() precede a esta migración (20260721120000,
--      aplicada — DEC-140). Si el inventario live del paso 1 del runbook
--      (evals/s278_rls_gate_plan_v1.md) registró grants o estados RLS distintos,
--      AJUSTAR este fichero contra ese receipt antes de ejecutar.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $disable_rls$
DECLARE
    table_name text;
BEGIN
    -- Lista de la migración MENOS chunks_v2 (ver desviación 1 en el header).
    FOREACH table_name IN ARRAY ARRAY[
        'chunks',
        'chunks_v2_enunciados',
        'chunks_v2_hyq',
        'documents',
        'document_groups',
        'document_group_members',
        'document_visual_assets'
    ]
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', table_name
            );
        END IF;
    END LOOP;
END
$disable_rls$;

-- Restaura la EXPOSICIÓN confirmada (ver advertencia del header).
GRANT SELECT, INSERT ON TABLE public.chunks_v2_enunciados TO anon, authenticated;

DO $regrant_create_hnsw_index$
BEGIN
    IF to_regprocedure('public.create_hnsw_index()') IS NOT NULL THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION public.create_hnsw_index() '
                'TO anon, authenticated';
    END IF;
END
$regrant_create_hnsw_index$;

DO $postcondition$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'chunks', 'chunks_v2_enunciados', 'chunks_v2_hyq', 'documents',
        'document_groups', 'document_group_members', 'document_visual_assets'
    ]
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL
           AND EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = to_regclass(format('public.%I', table_name))
              AND relrowsecurity
        ) THEN
            RAISE EXCEPTION 'rollback s278: RLS sigue habilitado en public.%',
                table_name;
        END IF;
    END LOOP;

    IF NOT has_table_privilege('anon', 'public.chunks_v2_enunciados', 'SELECT')
       OR NOT has_table_privilege('anon', 'public.chunks_v2_enunciados', 'INSERT')
       OR NOT has_table_privilege(
           'authenticated', 'public.chunks_v2_enunciados', 'SELECT'
       )
       OR NOT has_table_privilege(
           'authenticated', 'public.chunks_v2_enunciados', 'INSERT'
       ) THEN
        RAISE EXCEPTION
            'rollback s278: grants confirmados no restaurados en chunks_v2_enunciados';
    END IF;
END
$postcondition$;

NOTIFY pgrst, 'reload schema';

COMMIT;
