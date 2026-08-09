-- ============================================================================
-- s315 — (A) documents.source_url para la leyenda con links (punto 6 de Alberto)
--        (B) vista de latencia por etapa (punto 1 de Alberto, prioridad 2)
-- ============================================================================
-- POR QUÉ (A). La leyenda de fuentes (SOURCE_LEGEND, s294) da manual·sección·página
-- pero el técnico no puede ABRIR el manual: `documents` no guarda la URL de origen.
-- Los manifiestos de harvest SÍ la tienen (Casmar s314: url+sha256 por PDF;
-- notifier.es/morley-ias.es públicos). Columna nullable → el render es aditivo:
-- sin URL la línea queda byte-idéntica a hoy (src/rag/source_legend.py).
-- Backfill: scripts/s315_backfill_source_urls.py (join por source_pdf_sha256,
-- recibo JSON, reversible).
--
-- POR QUÉ (B). p50=34,5s / p95=57,6s (n=52, 60 días) y CERO atribución por etapa:
-- rag_trace no llevaba timings. Desde s315 el código escribe
-- `rag_trace.timings.{retrieve,rerank,coverage,generate}_ms` (tri-estado
-- `measured`, patrón s306). Esta vista agrega para responder: ¿dónde se van los
-- segundos? Las filas pre-s315 no tienen la sección → cuentan en turnos_rag pero
-- NO en turnos_con_medida («sin medida» ≠ «rápido»).
--
-- DEPENDENCIAS: 20260720095702 (rag_trace) + s301 (route) aplicadas en producción
-- (verificado vía MCP s315: la columna y las vistas existen). Aditiva pura: sin
-- carrera de deploy en ningún orden (código-primero: la sección timings se
-- persiste y nadie la agrega; SQL-primero: la vista da 0 con-medida hasta que el
-- código nuevo escriba).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. (A) Columna de URL de origen
-- ----------------------------------------------------------------------------
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS source_url text;
COMMENT ON COLUMN public.documents.source_url IS
    's315: URL pública del PDF de origen (portal del fabricante/distribuidor). '
    'NULL = sin URL pública conocida (p.ej. PDFs de OneDrive) → la leyenda no '
    'emite link. Backfill por sha256: scripts/s315_backfill_source_urls.py.';

-- ----------------------------------------------------------------------------
-- 2. (B) La vista (patrón s301/s306: security_invoker + agregados puros)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.salud_latencia_etapas_v1
WITH (security_invoker = true) AS
SELECT
    date_trunc('day', created_at)::date AS dia,
    COUNT(*) AS turnos_rag,
    COUNT(*) FILTER (
        WHERE (rag_trace -> 'timings' ->> 'measured') = 'true'
    ) AS turnos_con_medida,
    ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 0)
        AS total_p50_ms,
    ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 0)
        AS total_p95_ms,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (rag_trace -> 'timings' ->> 'retrieve_ms')::int
    ) FILTER (WHERE (rag_trace -> 'timings' ->> 'measured') = 'true')::numeric, 0)
        AS retrieve_p50_ms,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (rag_trace -> 'timings' ->> 'rerank_ms')::int
    ) FILTER (WHERE (rag_trace -> 'timings' ->> 'measured') = 'true')::numeric, 0)
        AS rerank_p50_ms,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (rag_trace -> 'timings' ->> 'coverage_ms')::int
    ) FILTER (WHERE (rag_trace -> 'timings' ->> 'measured') = 'true')::numeric, 0)
        AS coverage_p50_ms,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (rag_trace -> 'timings' ->> 'generate_ms')::int
    ) FILTER (WHERE (rag_trace -> 'timings' ->> 'measured') = 'true')::numeric, 0)
        AS generate_p50_ms,
    -- El «resto» por turno (formatter + log + F1 + overhead del handler): total
    -- menos la suma de etapas medidas. Si crece, el coste está FUERA del pipeline.
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY response_time_ms
            - (rag_trace -> 'timings' ->> 'retrieve_ms')::int
            - (rag_trace -> 'timings' ->> 'rerank_ms')::int
            - (rag_trace -> 'timings' ->> 'coverage_ms')::int
            - (rag_trace -> 'timings' ->> 'generate_ms')::int
    ) FILTER (WHERE (rag_trace -> 'timings' ->> 'measured') = 'true')::numeric, 0)
        AS resto_p50_ms
FROM public.query_logs
-- Mismo filtro que s301/s306: filas de error sin route heredarían 'rag' por el
-- COALESCE y contaminarían el denominador.
WHERE COALESCE(route, 'rag') = 'rag' AND source <> 'error'
GROUP BY 1;

-- ----------------------------------------------------------------------------
-- 3. Permisos (espejo exacto de s301/s306: API pública a cero)
-- ----------------------------------------------------------------------------
REVOKE ALL PRIVILEGES ON public.salud_latencia_etapas_v1
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.salud_latencia_etapas_v1 TO service_role;

-- ----------------------------------------------------------------------------
-- 4. Postcondiciones (fallan la transacción entera si algo quedó a medias)
-- ----------------------------------------------------------------------------
DO $s315_post$
BEGIN
    -- 4.1 La columna existe.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'documents'
          AND column_name = 'source_url'
    ) THEN
        RAISE EXCEPTION 's315: documents.source_url no existe';
    END IF;

    -- 4.2 La vista existe y es security_invoker (sin él perforaría la RLS de
    --     query_logs leyendo como owner — lección s301).
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'salud_latencia_etapas_v1'
          AND c.relkind = 'v'
          AND 'security_invoker=true' = ANY(c.reloptions)
    ) THEN
        RAISE EXCEPTION 's315: salud_latencia_etapas_v1 no existe o no es security_invoker';
    END IF;

    -- 4.3 API pública a cero.
    IF EXISTS (
        SELECT 1 FROM information_schema.role_table_grants
        WHERE table_schema = 'public'
          AND table_name = 'salud_latencia_etapas_v1'
          AND grantee IN ('anon', 'authenticated', 'PUBLIC')
    ) THEN
        RAISE EXCEPTION 's315: la vista quedó expuesta a la API pública';
    END IF;

    -- 4.4 La vista es consultable (un typo en el JSON path rompe aquí).
    PERFORM * FROM public.salud_latencia_etapas_v1 LIMIT 0;
END;
$s315_post$;

COMMIT;
