-- s286 — DDL para Alberto (paste en Supabase SQL editor): tabla answer_feedback
-- (feedback 1-tap 👍/👎) + vistas de salud. Espejo exacto de lo añadido a
-- supabase_schema.sql en el mismo commit (convención sync). ROLLBACK al final.
--
-- Diseño (brief v2 post-dúo, GO-BUILD r2):
--   · FK ON DELETE CASCADE → el borrado RGPD documentado (DELETE FROM
--     query_logs WHERE telegram_user_id = X) sigue funcionando sin pasos extra.
--   · UNIQUE (query_log_id, telegram_user_id) → taps idempotentes; el upsert
--     last-wins permite el toggle 👍→👎.
--   · Hardening OBLIGATORIO patrón 20260713164800 (ENABLE+FORCE RLS, REVOKE,
--     grant mínimo con UPDATE para el upsert, postcondiciones que ABORTAN).

BEGIN;

CREATE TABLE IF NOT EXISTS answer_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('up', 'down')),
    comment TEXT,                -- Fase 2: «¿qué faltó?» opcional en 👎
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (query_log_id, telegram_user_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_feedback_created
ON answer_feedback (created_at DESC);

DO $answer_feedback_boundary$
DECLARE
    role_name text;
    privilege_name text;
    expected_service_privileges text[] := ARRAY['SELECT', 'INSERT', 'UPDATE'];
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before hardening';
    END IF;

    ALTER TABLE public.answer_feedback ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.answer_feedback FORCE ROW LEVEL SECURITY;
    REVOKE ALL PRIVILEGES ON TABLE public.answer_feedback
        FROM PUBLIC, anon, authenticated, service_role;
    -- UPDATE: el upsert last-wins del veredicto lo necesita (precedente:
    -- user_consent, cuyo /accept repetido también upsertea).
    GRANT SELECT, INSERT, UPDATE ON TABLE public.answer_feedback TO service_role;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('public.answer_feedback')
          AND relrowsecurity AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'personal-data RLS invariant failed for answer_feedback';
    END IF;

    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ]
        LOOP
            IF has_table_privilege(
                role_name, 'public.answer_feedback', privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected % privilege for % on answer_feedback',
                    privilege_name, role_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                role_name, 'public.answer_feedback', privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected column % privilege for % on answer_feedback',
                    privilege_name, role_name;
            END IF;
        END LOOP;
    END LOOP;

    FOREACH privilege_name IN ARRAY ARRAY[
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
        'REFERENCES', 'TRIGGER', 'MAINTAIN'
    ]
    LOOP
        IF has_table_privilege(
            'service_role', 'public.answer_feedback', privilege_name
        ) IS DISTINCT FROM (privilege_name = ANY(expected_service_privileges)) THEN
            RAISE EXCEPTION 'unexpected service_role % privilege on answer_feedback',
                privilege_name;
        END IF;
    END LOOP;
END
$answer_feedback_boundary$;

-- Vistas de salud (s286). security_invoker: corren con los privilegios del
-- CALLER → el FORCE-RLS de query_logs sigue aplicando (anon = permission
-- denied, no bypass de definer). Predicados ESTÁTICOS solamente; la exclusión
-- dogfooding (INTERNAL_TELEGRAM_IDS) vive SOLO en scripts/bot_health_report.py
-- (fuente única, dúo r2). % no-info = HEURÍSTICA declarada (prefijos comunes
-- de la prosa admit-no-info del LLM); errores_transporte = el fallback fijo
-- del transporte. response_time_ms = latencia de PIPELINE (pre-envío).
CREATE OR REPLACE VIEW bot_health_daily
WITH (security_invoker = true) AS
SELECT
    created_at::date AS dia,
    bot_version,
    COUNT(*) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS consultas_rag,
    COUNT(DISTINCT telegram_user_id) FILTER (
        WHERE source <> 'error'
    ) AS usuarios_unicos,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS latencia_pipeline_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS latencia_pipeline_p95_ms,
    COUNT(*) FILTER (
        WHERE source <> 'error'
          AND category IS DISTINCT FROM 'direct'
          AND (response ILIKE 'No tengo información%'
               OR response ILIKE 'No dispongo%')
    ) AS no_info_heuristica,
    COUNT(*) FILTER (
        WHERE response LIKE 'No he podido generar una respuesta completa%'
    ) AS errores_transporte,
    COUNT(*) FILTER (WHERE source = 'error') AS filas_error
FROM query_logs
GROUP BY created_at::date, bot_version;

CREATE OR REPLACE VIEW bot_health_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    COUNT(*) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS consultas_rag,
    COUNT(DISTINCT telegram_user_id) FILTER (
        WHERE source <> 'error'
    ) AS usuarios_unicos,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS latencia_pipeline_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
    ) AS latencia_pipeline_p95_ms,
    COUNT(*) FILTER (
        WHERE source <> 'error'
          AND category IS DISTINCT FROM 'direct'
          AND (response ILIKE 'No tengo información%'
               OR response ILIKE 'No dispongo%')
    ) AS no_info_heuristica,
    COUNT(*) FILTER (
        WHERE response LIKE 'No he podido generar una respuesta completa%'
    ) AS errores_transporte,
    COUNT(*) FILTER (WHERE source = 'error') AS filas_error
FROM query_logs
GROUP BY date_trunc('week', created_at)::date;

REVOKE ALL PRIVILEGES ON bot_health_daily FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON bot_health_semanal FROM PUBLIC, anon, authenticated;
GRANT SELECT ON bot_health_daily TO service_role;
GRANT SELECT ON bot_health_semanal TO service_role;

COMMIT;

-- Verificación rápida post-paste (debe devolver: t | t en la primera; 2 filas
-- con relkind 'v' en la segunda):
--   SELECT relrowsecurity, relforcerowsecurity FROM pg_class
--     WHERE oid = 'public.answer_feedback'::regclass;
--   SELECT relname, relkind FROM pg_class
--     WHERE relname IN ('bot_health_daily', 'bot_health_semanal');

-- =========================== ROLLBACK ===========================
-- (pegar SOLO si hay que revertir; el orden importa por dependencias)
--   DROP VIEW IF EXISTS bot_health_semanal;
--   DROP VIEW IF EXISTS bot_health_daily;
--   DROP TABLE IF EXISTS answer_feedback;
