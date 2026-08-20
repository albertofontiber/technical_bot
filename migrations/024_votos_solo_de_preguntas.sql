-- ============================================================================
-- 024 — `bot_preguntas_por_usuario_semanal`: los VOTOS también se filtran por
--       `es_pregunta` (s327, hallazgo Sol del dúo).
--       ✅ APLICADA EN PRODUCCIÓN el 20-ago-2026 (conector Supabase). NO se
--          edita: lo que haga falta va en una migración nueva.
--
-- EL DEFECTO, en una línea: la 023 filtró `consultas` con el eje nuevo pero
-- dejó `votos_up`/`votos_down` contando TODO, así que una vista presentada como
-- «preguntas por persona» sumaba el feedback dado sobre mensajes que no son
-- preguntas. Refutaba la afirmación general de que las vistas de análisis
-- excluyen las no-preguntas — y una métrica que dice una cosa y cuenta otra es
-- peor que no tenerla.
--
-- Es CREATE OR REPLACE sin tocar nombres ni orden de columnas (42P16, la
-- lección de la 023), así que no hay que recrear permisos ni dependencias.
--
-- ⚠️ La 023 NO se edita (está aplicada): lo que haga falta va en una migración
--    nueva. Este fichero es exactamente eso.
-- ============================================================================

DO $s327b_preflight$
BEGIN
    IF to_regclass('public.bot_preguntas_por_usuario_semanal') IS NULL THEN
        RAISE EXCEPTION '024: aplica ANTES migrations/023_es_pregunta.sql';
    END IF;
END
$s327b_preflight$;

CREATE OR REPLACE VIEW public.bot_preguntas_por_usuario_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    COALESCE(ba.nota, 'sin alta (histórico)') AS quien,
    COUNT(*) FILTER (WHERE COALESCE(qc.es_pregunta, TRUE)) AS consultas,
    -- Los votos, SOLO los emitidos sobre preguntas: misma población que
    -- `consultas`, o la tabla mezcla dos universos en la misma fila.
    COUNT(*) FILTER (WHERE af.verdict = 'up'
                       AND COALESCE(qc.es_pregunta, TRUE))   AS votos_up,
    COUNT(*) FILTER (WHERE af.verdict = 'down'
                       AND COALESCE(qc.es_pregunta, TRUE))   AS votos_down,
    COUNT(*) FILTER (WHERE NOT COALESCE(qc.es_pregunta, TRUE)) AS otros_mensajes
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE ql.source <> 'error'
GROUP BY 1, 2;

NOTIFY pgrst, 'reload schema';

-- FRAGILIDAD DECLARADA de la postcondición de abajo (hallazgo Fable s327):
-- cuenta OCURRENCIAS de la palabra `es_pregunta` en la definición de la vista,
-- así que un alias o un comentario futuro con esa palabra la satisfaría sin
-- filtrar nada. Se deja porque ya cumplió su función al aplicar y porque lo que
-- de verdad protege el invariante es el gate contra Postgres real
-- (`tests/test_s327_clasificacion_pg.py::test_los_votos_de_una_no_pregunta_no_cuentan`,
-- con control negativo ejecutado), que mide el EFECTO y no el texto.
DO $s327b_postcondiciones$
DECLARE
    definicion TEXT;
BEGIN
    SELECT pg_get_viewdef('public.bot_preguntas_por_usuario_semanal'::regclass)
      INTO definicion;
    -- Los tres FILTER con el eje: consultas, votos_up y votos_down. Si alguien
    -- vuelve a dejar un contador sin filtrar, esto lo dice al aplicar.
    IF (length(definicion) - length(replace(definicion, 'es_pregunta', ''))) / 11 < 4 THEN
        RAISE EXCEPTION '024: la vista no filtra es_pregunta en todos sus contadores';
    END IF;
END
$s327b_postcondiciones$;

-- ROLLBACK: re-aplicar el bloque de esa vista tal como está en la 023.
