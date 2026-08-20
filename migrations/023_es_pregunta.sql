-- ============================================================================
-- 023 — `es_pregunta`: el eje que separa lo que PIDE algo de lo que no (s327).
--       Adjudicación de Alberto (19-ago, noche): «lo BP es separar lo que es
--       pregunta de lo que no, para que las no-preguntas no entren en el
--       análisis». Lista de categorías: `config/taxonomia_preguntas.yaml` (v7).
--
-- POR QUÉ UNA COLUMNA Y NO UNA CATEGORÍA MÁS: `no_es_pregunta` (v2→v6) competía
-- con las categorías TEMÁTICAS, y son ejes ORTOGONALES — una queja sobre un
-- catálogo mal servido tiene tema (catálogo) y no es una pregunta. Con una sola
-- etiqueta había que elegir, y se perdía la otra mitad. Con dos ejes, las
-- vistas de análisis filtran `es_pregunta` y las no-preguntas se miran aparte
-- (`bot_no_preguntas_v1`), que es donde vive el feedback en prosa.
--
-- DOS LECCIONES DE ORDEN, las dos aprendidas fallando y revirtiendo entero:
--   · el CHECK se retira ANTES de mapear datos (la 022, error 23514);
--   · una columna NUEVA en una vista existente va AL FINAL del SELECT — no en
--     medio: `CREATE OR REPLACE VIEW` no renombra ni reordena (42P16), y hacer
--     DROP+CREATE tiraría permisos y dependencias.
--
-- ORDEN (lección de la 022, que murió al primer intento por ponerlo al revés):
--   A. columna NUEVA nullable + GRANT (sin el GRANT el job muere con 42501 —
--      lección del backfill de s326: toda columna escrita tiene su permiso);
--   B. backfill desde la categoría vieja: `no_es_pregunta` ⇒ false, resto true;
--   C. FUERA el CHECK viejo, mapa de `no_es_pregunta` → `otros`, CHECK v7;
--   D. `SET NOT NULL` (ya no queda ninguna nula);
--   E. vistas: las de análisis filtran preguntas, y nace la de no-preguntas;
--   F. postcondiciones.
--
-- «ANTE LA DUDA, PREGUNTA» EN SQL: las vistas usan `COALESCE(qc.es_pregunta,
-- TRUE)` allí donde parten de `query_logs` — una fila aún sin clasificar cuenta
-- como pregunta, que es el sesgo que pidió Alberto (mejor colar una no-pregunta
-- que perder una pregunta real).
--
-- ⚠️ CONTRATO DE APLICACIÓN (016/019/021/022): ENTERA con un aplicador
--    transaccional, NUNCA sentencia a sentencia. SIN BEGIN/COMMIT propios.
--
-- REVERSIBILIDAD: la tabla es DERIVADA. Rollback al pie (vaciar + restaurar).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FASE 0 — PREFLIGHT
-- ----------------------------------------------------------------------------
DO $s327_preflight$
BEGIN
    IF to_regclass('public.query_clasificacion') IS NULL THEN
        RAISE EXCEPTION '023: aplica ANTES migrations/021_query_clasificacion.sql';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'public.query_clasificacion'::regclass
           AND conname = 'query_clasificacion_categoria_check') THEN
        RAISE EXCEPTION '023: falta el CHECK de categoria (¿se aplicó la 022?)';
    END IF;
END
$s327_preflight$;

-- ----------------------------------------------------------------------------
-- FASE A — LA COLUMNA + SU GRANT
-- ----------------------------------------------------------------------------
ALTER TABLE public.query_clasificacion
    ADD COLUMN IF NOT EXISTS es_pregunta BOOLEAN;

COMMENT ON COLUMN public.query_clasificacion.es_pregunta IS
    's327: ¿el mensaje PIDE algo? Eje ortogonal al tema. Interrogación ⇒ TRUE '
    'por regla de código; el resto lo infiere el clasificador con sesgo «ante '
    'la duda, pregunta». Las vistas de análisis filtran por esta columna.';

GRANT INSERT (es_pregunta), UPDATE (es_pregunta)
    ON public.query_clasificacion TO service_role;

-- ----------------------------------------------------------------------------
-- FASE B — BACKFILL desde la categoría que se retira
-- ----------------------------------------------------------------------------
UPDATE public.query_clasificacion
   SET es_pregunta = (categoria <> 'no_es_pregunta')
 WHERE es_pregunta IS NULL;

-- ----------------------------------------------------------------------------
-- FASE C — FUERA el CHECK viejo → mapa → CHECK de la v7
-- ----------------------------------------------------------------------------
ALTER TABLE public.query_clasificacion
    DROP CONSTRAINT query_clasificacion_categoria_check;

UPDATE public.query_clasificacion
   SET categoria = 'otros'
 WHERE categoria = 'no_es_pregunta';

ALTER TABLE public.query_clasificacion
    ADD CONSTRAINT query_clasificacion_categoria_check CHECK (categoria IN (
        'catalogo_especificaciones',
        'instalacion_configuracion',
        'averias_diagnostico',
        'mantenimiento_pruebas',
        'compatibilidad_sustitucion',
        'normativa',
        'otros'));

-- ----------------------------------------------------------------------------
-- FASE D — la columna pasa a obligatoria
-- ----------------------------------------------------------------------------
ALTER TABLE public.query_clasificacion
    ALTER COLUMN es_pregunta SET NOT NULL;

-- ----------------------------------------------------------------------------
-- FASE E — LAS VISTAS: análisis SOLO de preguntas + una para lo que no lo es
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.bot_tipologia_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    qc.categoria,
    qc.taxonomia_version,
    COUNT(*) AS consultas,
    COUNT(DISTINCT ql.telegram_user_id) AS personas
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
WHERE qc.es_pregunta
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW public.bot_marcas_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    m.marca,
    COUNT(*) AS consultas,
    COUNT(DISTINCT ql.telegram_user_id) AS personas
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
CROSS JOIN LATERAL unnest(qc.marcas) AS m(marca)
WHERE qc.es_pregunta
GROUP BY 1, 2;

CREATE OR REPLACE VIEW public.bot_modelos_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    mo.modelo,
    COUNT(*) AS consultas,
    COUNT(DISTINCT ql.telegram_user_id) AS personas
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
CROSS JOIN LATERAL unnest(qc.modelos) AS mo(modelo)
WHERE qc.es_pregunta
GROUP BY 1, 2;

CREATE OR REPLACE VIEW public.bot_feedback_tipologia_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    qc.categoria,
    COUNT(*) FILTER (WHERE af.verdict = 'up')   AS votos_up,
    COUNT(*) FILTER (WHERE af.verdict = 'down') AS votos_down,
    COUNT(*) FILTER (WHERE af.verdict = 'down'
                       AND af.reason_class IS NOT NULL) AS down_con_motivo
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
JOIN public.answer_feedback af
     ON af.query_log_id = ql.id
    AND af.telegram_user_id = ql.telegram_user_id
WHERE qc.es_pregunta
GROUP BY 1, 2;

-- Una marca mencionada en una QUEJA no es demanda de esa marca: filtra igual.
CREATE OR REPLACE VIEW public.bot_marcas_sin_corpus_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    ml.marca_libre,
    COUNT(*) AS menciones
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
CROSS JOIN LATERAL unnest(qc.marcas_libres) AS ml(marca_libre)
WHERE qc.es_pregunta
  AND NOT EXISTS (
    SELECT 1 FROM public.documents d
     WHERE d.status = 'active'
       AND lower(d.manufacturer) = lower(ml.marca_libre))
GROUP BY 1, 2;

-- Por usuario: PREGUNTAS (el «ante la duda» aplica — una fila sin clasificar
-- cuenta como pregunta) y, aparte, los mensajes que no lo son.
CREATE OR REPLACE VIEW public.bot_preguntas_por_usuario_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    COALESCE(ba.nota, 'sin alta (histórico)') AS quien,
    COUNT(*) FILTER (WHERE COALESCE(qc.es_pregunta, TRUE))     AS consultas,
    COUNT(*) FILTER (WHERE af.verdict = 'up')   AS votos_up,
    COUNT(*) FILTER (WHERE af.verdict = 'down') AS votos_down,
    -- AL FINAL a propósito: `CREATE OR REPLACE VIEW` no puede insertar una
    -- columna en medio ni renombrar (42P16) — lo cazó el primer intento de
    -- aplicar esta migración, que revirtió entero. Columna nueva ⇒ al final,
    -- o toca DROP + CREATE (y eso invalidaría permisos y dependencias).
    COUNT(*) FILTER (WHERE NOT COALESCE(qc.es_pregunta, TRUE)) AS otros_mensajes
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE ql.source <> 'error'
GROUP BY 1, 2;

-- Cobertura del job: NO filtra (mide el trabajo pendiente, no el análisis) y
-- ahora dice además cuántos de los clasificados no son preguntas.
CREATE OR REPLACE VIEW public.bot_clasificacion_cobertura
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    COUNT(*) AS consultas,
    COUNT(qc.query_log_id) AS clasificadas,
    COUNT(*) - COUNT(qc.query_log_id) AS sin_clasificar,
    MIN(qc.taxonomia_version) AS taxonomia_min,
    MAX(qc.taxonomia_version) AS taxonomia_max,
    COUNT(*) FILTER (WHERE qc.es_pregunta IS FALSE) AS no_preguntas
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
WHERE ql.source <> 'error'
GROUP BY 1;

-- NUEVA: lo que NO es una pregunta, que es donde vive el feedback en prosa.
-- Fila a fila y CON texto, igual que el Explorador (mismo gate RGPD: panel
-- autenticado, addendum del abogado).
CREATE OR REPLACE VIEW public.bot_no_preguntas_v1
WITH (security_invoker = true) AS
SELECT
    ql.id,
    ql.created_at,
    qc.categoria,
    ql.query AS mensaje,
    COALESCE(ba.nota, 'sin alta (histórico)') AS quien,
    af.verdict,
    af.comment
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE NOT qc.es_pregunta;

-- El Explorador expone la columna para poder filtrar por ella.
CREATE OR REPLACE VIEW public.bot_explorador_v1
WITH (security_invoker = true) AS
SELECT
    ql.id,
    ql.created_at,
    ql.source AS canal,
    COALESCE(ql.route, 'rag') AS ruta,
    qc.categoria,
    qc.taxonomia_version,
    qc.marcas,
    qc.modelos,
    ql.query AS pregunta,
    ql.response_length,
    COALESCE(ba.nota, 'sin alta (histórico)') AS quien,
    af.verdict,
    af.reason_class,
    af.comment,
    COALESCE(qc.es_pregunta, TRUE) AS es_pregunta   -- al final: ver 42P16 arriba
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE ql.source <> 'error';

REVOKE ALL PRIVILEGES ON public.bot_no_preguntas_v1 FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.bot_no_preguntas_v1 TO service_role;

NOTIFY pgrst, 'reload schema';

-- ----------------------------------------------------------------------------
-- FASE F — POSTCONDICIONES
-- ----------------------------------------------------------------------------
DO $s327_postcondiciones$
DECLARE
    definicion TEXT;
    rol TEXT;
    pendientes BIGINT;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'query_clasificacion'
                  AND column_name = 'es_pregunta'
                  AND is_nullable = 'YES') THEN
        RAISE EXCEPTION '023: es_pregunta quedó nullable';
    END IF;
    IF NOT has_column_privilege('service_role', 'public.query_clasificacion',
                                'es_pregunta', 'INSERT')
       OR NOT has_column_privilege('service_role', 'public.query_clasificacion',
                                   'es_pregunta', 'UPDATE') THEN
        RAISE EXCEPTION '023: service_role no puede escribir es_pregunta';
    END IF;
    SELECT count(*) INTO pendientes
      FROM public.query_clasificacion WHERE categoria = 'no_es_pregunta';
    IF pendientes > 0 THEN
        RAISE EXCEPTION '023: quedan % filas con la categoría retirada', pendientes;
    END IF;
    SELECT pg_get_constraintdef(oid) INTO definicion
      FROM pg_constraint
     WHERE conrelid = 'public.query_clasificacion'::regclass
       AND conname = 'query_clasificacion_categoria_check';
    IF position('''no_es_pregunta''' IN definicion) > 0 THEN
        RAISE EXCEPTION '023: el CHECK todavía admite no_es_pregunta';
    END IF;
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF has_table_privilege(rol, 'public.bot_no_preguntas_v1', 'SELECT') THEN
            RAISE EXCEPTION '023: % puede leer bot_no_preguntas_v1', rol;
        END IF;
    END LOOP;
END
$s327_postcondiciones$;

-- ----------------------------------------------------------------------------
-- ROLLBACK (la tabla es derivada; se vacía y se reconstruye con el YAML v6):
--   DROP VIEW IF EXISTS public.bot_no_preguntas_v1;
--   DELETE FROM public.query_clasificacion;
--   ALTER TABLE public.query_clasificacion DROP COLUMN es_pregunta;
--   ALTER TABLE public.query_clasificacion
--       DROP CONSTRAINT query_clasificacion_categoria_check;
--   ALTER TABLE public.query_clasificacion
--       ADD CONSTRAINT query_clasificacion_categoria_check CHECK (categoria IN (
--           'catalogo_especificaciones','instalacion_configuracion',
--           'averias_diagnostico','mantenimiento_pruebas',
--           'compatibilidad_sustitucion','normativa','no_es_pregunta','otros'));
--   -- y restaurar las vistas de la 021/022 (sin el filtro es_pregunta).
-- ----------------------------------------------------------------------------
