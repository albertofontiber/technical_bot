-- ============================================================================
-- PENDIENTE DE APLICAR (Alberto, SQL Editor). IDEMPOTENTE: re-ejecutarla es seguro.
-- No depende de la cola RGPD (s295→s299): toca observabilidad, no datos personales
-- nuevos — todas las vistas son AGREGADAS (conteos y percentiles, ni ids ni prosa).
-- ============================================================================
-- s301 — «dashboard» SIN app (frente 6, decisión de Alberto 6-ago; DEC-162f sigue
-- vigente: nada de Grafana/web hasta técnicos y volumen). Tres piezas:
--
--   1. `query_logs.route` (TECH_DEBT #31, trigger (a) disparado: Alberto pidió métricas
--      de uso). Los shortcuts del bot (saludo/gracias/adiós/catálogo/mismatch) retornaban
--      SIN loggear: «¿qué fabricantes tienes?» no existía en query_logs. El código ya
--      envía `route` en cada log (con fallback de compatibilidad si esta migración aún
--      no está aplicada). Filas históricas: NULL = pre-s301 (todas eran RAG o error; las
--      vistas usan COALESCE(route,'rag') y lo declaran).
--   2. Las 2 vistas de salud EXISTENTES, ahora VERSIONADAS: vivían solo en el bootstrap
--      (nunca en una migración) — un entorno levantado por la cola no las tenía.
--   3. Tres vistas nuevas para las preguntas de Alberto: cuánto feedback y de qué signo
--      (`bot_feedback_semanal`), POR QUÉ es negativo (`bot_motivos_negativos` — el dato
--      existía y CERO herramientas lo leían), y uso por canal (`bot_uso_por_canal`).
--
-- El «front» es el dashboard de Supabase sobre estas vistas: cero infraestructura nueva.
-- RGPD: agregados puros — la prosa del 👎 se CUENTA aquí, no se muestra (la prosa viaja
-- por el export seudonimizado de review_logs, que es su canal).

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. La ruta de cada respuesta
-- ---------------------------------------------------------------------------
ALTER TABLE public.query_logs ADD COLUMN IF NOT EXISTS route TEXT;

DO $s301_route_check$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'query_logs_route_check'
           AND conrelid = 'public.query_logs'::regclass
    ) THEN
        ALTER TABLE public.query_logs
            ADD CONSTRAINT query_logs_route_check
            CHECK (route IS NULL OR route IN (
                'rag',                    -- el pipeline completo (default del código)
                'catalog_shortcut',       -- «¿qué fabricantes/modelos tienes?»
                'greeting', 'thanks', 'bye',
                'manufacturer_mismatch',  -- modelo de OTRO fabricante
                'manufacturer_no_model'   -- fabricante sin manuales en corpus
            ));
    END IF;
END
$s301_route_check$;

-- ---------------------------------------------------------------------------
-- 2. Las vistas de salud existentes, versionadas (idénticas al bootstrap)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.bot_health_daily
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
FROM public.query_logs
GROUP BY created_at::date, bot_version;

CREATE OR REPLACE VIEW public.bot_health_semanal
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
FROM public.query_logs
GROUP BY date_trunc('week', created_at)::date;

-- ---------------------------------------------------------------------------
-- 3. Las vistas nuevas: feedback, motivos y uso por canal — AGREGADOS puros
-- ---------------------------------------------------------------------------
-- ¿Cuánto feedback llega y de qué signo? Los dos canales, lado a lado: el voto con
-- teclado (answer_feedback) y el texto espontáneo (feedback).
CREATE OR REPLACE VIEW public.bot_feedback_semanal
WITH (security_invoker = true) AS
SELECT
    COALESCE(v.semana, f.semana) AS semana,
    COALESCE(v.votos_up, 0)        AS votos_up,
    COALESCE(v.votos_down, 0)      AS votos_down,
    COALESCE(v.con_motivo, 0)      AS votos_down_con_motivo,
    COALESCE(v.con_comentario, 0)  AS votos_con_comentario,
    COALESCE(v.marcados_utiles, 0) AS marcados_utiles,
    COALESCE(f.mensajes, 0)        AS feedback_libre
FROM (
    SELECT date_trunc('week', created_at)::date AS semana,
           COUNT(*) FILTER (WHERE verdict = 'up')        AS votos_up,
           COUNT(*) FILTER (WHERE verdict = 'down')      AS votos_down,
           COUNT(*) FILTER (WHERE verdict = 'down'
                              AND reason_class IS NOT NULL) AS con_motivo,
           COUNT(*) FILTER (WHERE comment IS NOT NULL)   AS con_comentario,
           COUNT(*) FILTER (WHERE utilidad IS NOT NULL
                              AND utilidad <> 'ninguna') AS marcados_utiles
      FROM public.answer_feedback
     GROUP BY 1
) v
FULL JOIN (
    SELECT date_trunc('week', created_at)::date AS semana,
           COUNT(*) AS mensajes
      FROM public.feedback
     GROUP BY 1
) f USING (semana);

-- ¿POR QUÉ es negativo? El desglose del motivo del 👎 — la columna que nadie leía.
CREATE OR REPLACE VIEW public.bot_motivos_negativos
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    COALESCE(reason_class, '(sin motivo)') AS motivo,
    COUNT(*) AS votos
FROM public.answer_feedback
WHERE verdict = 'down'
GROUP BY 1, 2;

-- ¿Por dónde entra el uso? NULL histórico = pre-s301 (solo existían RAG y error).
CREATE OR REPLACE VIEW public.bot_uso_por_canal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    CASE WHEN source = 'error' THEN 'error'
         ELSE COALESCE(route, 'rag') END AS canal,
    COUNT(*) AS consultas,
    COUNT(DISTINCT telegram_user_id) AS personas
FROM public.query_logs
GROUP BY 1, 2;

-- Mismo perímetro que las vistas de salud: NADA para la API anónima; lectura solo del
-- operador (postgres) y del bot si algún día la necesita.
REVOKE ALL PRIVILEGES ON public.bot_feedback_semanal,
                         public.bot_motivos_negativos,
                         public.bot_uso_por_canal
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.bot_feedback_semanal,
                public.bot_motivos_negativos,
                public.bot_uso_por_canal
    TO service_role;

-- ---------------------------------------------------------------------------
-- 4. Postcondiciones
-- ---------------------------------------------------------------------------
DO $s301_post$
DECLARE
    vista TEXT;
    rol TEXT;
BEGIN
    -- 4.1 La columna y su taxonomía cerrada.
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'query_logs_route_check'
           AND conrelid = 'public.query_logs'::regclass
    ) THEN
        RAISE EXCEPTION 's301: falta el CHECK de la taxonomia de route';
    END IF;

    -- 4.2 Las 5 vistas existen, con security_invoker (sin él, una vista sobre
    -- query_logs leería con los privilegios del OWNER y perforaría la RLS).
    FOREACH vista IN ARRAY ARRAY[
        'bot_health_daily', 'bot_health_semanal', 'bot_feedback_semanal',
        'bot_motivos_negativos', 'bot_uso_por_canal'
    ] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
             WHERE oid = to_regclass(format('public.%I', vista))
               AND relkind = 'v'
               AND 'security_invoker=true' = ANY(reloptions)
        ) THEN
            RAISE EXCEPTION 's301: la vista % no existe o no es security_invoker', vista;
        END IF;
        FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF has_table_privilege(rol, format('public.%I', vista), 'SELECT') THEN
                RAISE EXCEPTION 's301: % puede leer la vista %', rol, vista;
            END IF;
        END LOOP;
    END LOOP;
END
$s301_post$;

COMMIT;

-- ---------------------------------------------------------------------------
-- CAMBIO ACOMPAÑANTE EN `supabase_schema.sql` (bootstrap = estado FINAL, DEC-180)
-- ---------------------------------------------------------------------------
-- route (columna + CHECK) y las 3 vistas nuevas con sus grants, junto a las 2 de salud.
--
-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   DROP VIEW IF EXISTS public.bot_feedback_semanal, public.bot_motivos_negativos,
--                       public.bot_uso_por_canal;
--   ALTER TABLE public.query_logs DROP CONSTRAINT IF EXISTS query_logs_route_check;
--   ALTER TABLE public.query_logs DROP COLUMN IF EXISTS route;
--     (el código tolera la ausencia: fallback de compatibilidad en log_query)
