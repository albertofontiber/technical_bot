-- ============================================================================
-- s306 — Vista de salud del canal de retrieval (TECH_DEBT #63b)
-- ============================================================================
-- POR QUÉ. En s303 un 500 transitorio del RPC de enunciados bajó el pool de 34 a
-- 23 chunks (−32%) y NINGUNA métrica lo registró: el fail-open es la decisión
-- correcta de disponibilidad, pero era invisible. Desde s306 el código registra
-- cada fail-open de canal en `rag_trace.retrieval.channel_failures` (tokens de
-- allowlist, sin prosa ni ids). Esta vista lo agrega para responder: ¿cuántos
-- turnos respondieron con el pool DEGRADADO, y qué canal falla?
--
-- DEPENDENCIA: s301 aplicada (columna `route` + patrón de vistas). Aditiva pura:
-- no toca tablas ni vistas existentes — sin carrera de deploy en ningún orden
-- (código-primero: la vista aún no existe y nadie la consulta; SQL-primero: la
-- vista devuelve 0 degradados hasta que el código nuevo escriba la sección).
--
-- Distinción que la vista PRESERVA (el corazón de #63): «sin medida» ≠ «sano».
-- Las filas pre-s306 no tienen la sección `retrieval` → cuentan en turnos_rag
-- pero NO en turnos_con_medida; solo un turno CON medida y lista vacía es sano.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. La vista (patrón s301: security_invoker + agregados puros)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.salud_canal_retrieval_v1
WITH (security_invoker = true) AS
SELECT
    date_trunc('day', created_at)::date AS dia,
    COUNT(*) AS turnos_rag,
    COUNT(*) FILTER (
        WHERE rag_trace IS NOT NULL AND rag_trace ? 'retrieval'
    ) AS turnos_con_medida,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(
            rag_trace -> 'retrieval' -> 'channel_failures'
        ) > 0
    ) AS turnos_degradados,
    -- Por canal (containment sobre la lista de objetos; tokens de la allowlist
    -- del código — runtime_trace._ALLOWED_CHANNELS):
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "VECTOR"}]'
    ) AS fallos_vector,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "ENUNCIADOS"}]'
    ) AS fallos_enunciados,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "HYQ_TABLE"}]'
    ) AS fallos_hyq_table,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "HYQ_HYDRATE"}]'
    ) AS fallos_hyq_hydrate
FROM public.query_logs
WHERE COALESCE(route, 'rag') = 'rag'   -- los shortcuts no hacen retrieval
GROUP BY 1;

-- ----------------------------------------------------------------------------
-- 2. Permisos (espejo exacto de s301: API pública a cero, operador vía service)
-- ----------------------------------------------------------------------------
REVOKE ALL PRIVILEGES ON public.salud_canal_retrieval_v1
    FROM anon, authenticated;
GRANT SELECT ON public.salud_canal_retrieval_v1 TO service_role;

-- ----------------------------------------------------------------------------
-- 3. Postcondiciones (fallan la transacción entera si algo quedó a medias)
-- ----------------------------------------------------------------------------
DO $s306_post$
BEGIN
    -- 3.1 La vista existe y es security_invoker (sin él perforaría la RLS de
    --     query_logs leyendo como owner — lección s301).
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'salud_canal_retrieval_v1'
          AND c.relkind = 'v'
          AND 'security_invoker=true' = ANY(c.reloptions)
    ) THEN
        RAISE EXCEPTION 's306: salud_canal_retrieval_v1 no existe o no es security_invoker';
    END IF;

    -- 3.2 API pública a cero.
    IF EXISTS (
        SELECT 1 FROM information_schema.role_table_grants
        WHERE table_schema = 'public'
          AND table_name = 'salud_canal_retrieval_v1'
          AND grantee IN ('anon', 'authenticated')
    ) THEN
        RAISE EXCEPTION 's306: la vista quedó expuesta a la API pública';
    END IF;

    -- 3.3 La vista es consultable (una fila de prueba no hace falta: basta que
    --     el planner la acepte — un typo en el JSON path rompería aquí, no en
    --     el primer vistazo de Alberto).
    PERFORM * FROM public.salud_canal_retrieval_v1 LIMIT 0;
END;
$s306_post$;

COMMIT;
