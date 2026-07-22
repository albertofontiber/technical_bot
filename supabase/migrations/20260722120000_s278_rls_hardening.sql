-- s278 — Gate de seguridad TECH_DEBT #29 (SEC-29 dúo r1; DEC-148 / diseño §0.3):
-- defensa en profundidad sobre la anon key. El Advisor confirmó en S277 RLS
-- deshabilitado en public.chunks_v2_enunciados (22.842 filas observadas) con
-- grants SELECT/INSERT para anon/authenticated, y grants explícitos pendientes de
-- anon/authenticated sobre create_hnsw_index() (DEC-140: 20260721120000 solo
-- revocó PUBLIC). El backend accede con service_role (BYPASSRLS), por lo que
-- habilitar RLS sin policies es INVARIANTE para el bot y default-deny para
-- anon/authenticated.
--
-- Forward-only e idempotente. NO crea policies (default-deny deliberado: hoy
-- ningún cliente anon es legítimo). NO usa FORCE ROW LEVEL SECURITY: las rutas
-- de mantenimiento del owner (postgres) siguen operativas; el objetivo es cerrar
-- la superficie anon, no bloquear la operación.
--
-- Interacción DECLARADA con p1_readonly (NOLOGIN/NOBYPASSRLS, 20260721120000):
-- tras esta migración sus SELECT sobre chunks_v2_enunciados / chunks_v2_hyq /
-- documents / document_visual_assets pasan a devolver 0 filas (default-deny
-- silencioso, no error) porque solo chunks_v2 y document_revision_lineages
-- tienen policy p1. P1 está en SAFE HOLD con 0 ejecución pagada; antes de la
-- próxima P1 harán falta policies SELECT explícitas bajo autorización separada.
-- Esta migración NO las crea a propósito (scope = cerrar #29).
--
-- Rollback espejo (restaura una EXPOSICIÓN — solo con visto explícito):
-- supabase/rollbacks/20260722120000_s278_rls_hardening.sql
--
-- ESTADO: PREPARADA, NO APLICADA. Runbook: evals/s278_rls_gate_plan_v1.md.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $precondition$
BEGIN
    -- La invarianza del bot depende de este atributo; si falta, el smoke NO
    -- sería invariante y la migración no debe aplicarse.
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 's278 RLS hardening requiere service_role con BYPASSRLS';
    END IF;

    -- La tabla confirmada expuesta debe existir: si no existe, este entorno no
    -- es el que describe #29 y hay que re-inventariar antes de aplicar.
    IF to_regclass('public.chunks_v2_enunciados') IS NULL THEN
        RAISE EXCEPTION 's278 RLS hardening: public.chunks_v2_enunciados ausente';
    END IF;
END
$precondition$;

-- Tablas public del esquema VERSIONADO sin RLS declarado (inventario del repo;
-- el inventario LIVE es el paso 1 del runbook — cualquier tabla live fuera de
-- esta lista se incorpora ANTES de aplicar). Excluidas por nacer/quedar ya con
-- RLS declarado: query_logs / feedback / user_consent (20260713164800,
-- ENABLE+FORCE), identity_resolve_shadow (20260702165425),
-- document_revision_lineages (20260722013000). ENABLE es idempotente; el guard
-- to_regclass tolera entornos donde una tabla legacy no exista.
DO $enable_rls$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'chunks',                  -- corpus legacy OpenAI-1536 (supabase_schema.sql)
        'chunks_v2',               -- corpus Voyage-1024 (migrations/006; live ya con
                                   -- RLS + policy p1 según 20260721120000 — no-op aquí)
        'chunks_v2_enunciados',    -- EXPOSICIÓN CONFIRMADA por el Advisor (#29)
        'chunks_v2_hyq',           -- surrogates question-side (migrations/013)
        'documents',               -- registro de documentos (migrations/001)
        'document_groups',         -- (migrations/001)
        'document_group_members',  -- (migrations/001)
        'document_visual_assets'   -- (migrations/014)
    ]
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name
            );
        END IF;
    END LOOP;
END
$enable_rls$;

-- Revocación de los grants que TECH_DEBT #29 CONFIRMA (scope deliberado: el
-- resto de tablas queda cubierto por el default-deny de RLS y se audita en el
-- inventario live del runbook). PUBLIC entra como cinturón; service_role y
-- p1_readonly conservan sus grants (esta sentencia no los nombra).
REVOKE ALL PRIVILEGES ON TABLE public.chunks_v2_enunciados
    FROM PUBLIC, anon, authenticated;

-- create_hnsw_index() es SECURITY DEFINER y no vive en el esquema versionado
-- (helper de mantenimiento observado live) → guard de existencia obligatorio.
DO $revoke_create_hnsw_index$
BEGIN
    IF to_regprocedure('public.create_hnsw_index()') IS NOT NULL THEN
        EXECUTE 'REVOKE ALL PRIVILEGES ON FUNCTION public.create_hnsw_index() '
                'FROM PUBLIC, anon, authenticated';
    END IF;
END
$revoke_create_hnsw_index$;

DO $postcondition$
DECLARE
    table_name text;
    role_name text;
    privilege_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'chunks', 'chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
        'documents', 'document_groups', 'document_group_members',
        'document_visual_assets'
    ]
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL
           AND NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = to_regclass(format('public.%I', table_name))
              AND relrowsecurity
        ) THEN
            RAISE EXCEPTION 'RLS no quedó habilitado en public.%', table_name;
        END IF;
    END LOOP;

    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        -- MAINTAIN existe desde PostgreSQL 17 (live confirmado PG17, DEC-139/140).
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ]
        LOOP
            IF has_table_privilege(
                role_name, 'public.chunks_v2_enunciados', privilege_name
            ) THEN
                RAISE EXCEPTION
                    'privilegio % inesperado de % sobre chunks_v2_enunciados',
                    privilege_name, role_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                role_name, 'public.chunks_v2_enunciados', privilege_name
            ) THEN
                RAISE EXCEPTION
                    'privilegio de columna % inesperado de % sobre chunks_v2_enunciados',
                    privilege_name, role_name;
            END IF;
        END LOOP;

        IF to_regprocedure('public.create_hnsw_index()') IS NOT NULL
           AND has_function_privilege(
               role_name, 'public.create_hnsw_index()', 'EXECUTE'
           ) THEN
            RAISE EXCEPTION
                '% conserva EXECUTE sobre create_hnsw_index()', role_name;
        END IF;
    END LOOP;
    -- service_role: invariante ya garantizada por BYPASSRLS (precondición).
END
$postcondition$;

-- PostgREST cachea esquema/ACL; el NOTIFY dentro de la transacción se entrega
-- al hacer COMMIT.
NOTIFY pgrst, 'reload schema';

COMMIT;
