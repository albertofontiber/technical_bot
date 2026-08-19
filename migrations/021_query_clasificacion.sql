-- ============================================================================
-- 021 — `query_clasificacion` + las vistas de USO/CALIDAD del panel (s326).
--       ✅ APLICADA EN PRODUCCIÓN el 19-ago-2026 (conector Supabase). NO se
--          edita: un cambio aquí deja CI verde y producción sin él — lo que
--          haga falta va en una migración nueva.
--       Petición de Alberto (19-ago-2026): tipología de pregunta · fabricantes ·
--       modelos · feedback por pregunta · preguntas por usuario. Propuesta
--       adjudicada entera: `evals/s326_panel_metricas_uso_propuesta_v1.md`
--       (drill-down con prosa = OPCIÓN (a); por-usuario con ALIAS de allowlist;
--       taxonomía v1; coste OK).
--
-- QUÉ CREA:
--   · `query_clasificacion` — tabla DERIVADA 1:1 con `query_logs`: categoría
--     (taxonomía cerrada v1, `config/taxonomia_preguntas_v1.yaml`), marcas y
--     modelos canónicos, menciones de marca fuera de corpus. La escribe el job
--     batch (`scripts/clasificar_preguntas.py` / seam CLASIFICADOR_PREGUNTAS);
--     el bot NO la toca. Es desechable y reconstruible entera desde
--     `query_logs` — por eso re-taxonomizar es barato y seguro.
--   · 8 vistas para el panel: 7 agregadas (patrón s301: conteos, ni ids ni
--     prosa) y UNA fila-a-fila (`bot_explorador_v1`, CON la pregunta y el
--     comentario del técnico) — es el «fuera de v1» de DEC-231 que Alberto
--     reabrió a conciencia (adjudicación (a), s326). El alias humano sale de
--     `bot_allowlist.nota`, que el panel de gestión ya enseña.
--
-- RGPD:
--   · `query_clasificacion` NO añade dato personal nuevo: no lleva id de
--     persona; deriva del texto ya registrado. Muere en cascada con su
--     `query_logs` → la supresión documentada (DELETE por telegram_user_id)
--     sigue funcionando sin pasos extra. El job de seudonimización s296 no la
--     toca (nada que seudonimizar). Darla de alta en la matriz de retención
--     como DERIVADO de query_logs.
--   · `bot_explorador_v1` y `bot_preguntas_por_usuario_semanal` EXPONEN al
--     panel autenticado prosa de técnicos y alias con nombre: entran en el
--     addendum del paquete del abogado (gate declarado en PLAN «qué sigue»).
--
-- ⚠️ CONTRATO DE APLICACIÓN (idéntico a la 019, lección de la 016): aplicar
--    ENTERO con un aplicador transaccional (SQL Editor de Supabase o
--    `psql --single-transaction`), NUNCA sentencia a sentencia. SIN
--    BEGIN/COMMIT propios A PROPÓSITO.
--
-- ⚠️ ORDEN DE LA COLA: exige el bootstrap (query_logs/answer_feedback/
--    documents), la 016 (bot_allowlist) y el hardening s278 (service_role con
--    BYPASSRLS). El preflight lo comprueba y aborta con el motivo escrito.
--
-- TAXONOMÍA VERSIONADA: los ids del CHECK de `categoria` son EXACTAMENTE los de
-- `config/taxonomia_preguntas_v1.yaml` (lo cruza
-- tests/test_s326_query_clasificacion_acl.py). Una taxonomía v2 = migración
-- hermana que altere el CHECK + subida de `version` en el YAML — deliberado:
-- cambiar las categorías es un evento adjudicado, no un hot-swap.
--
-- ÍNDICES: solo el PK. A escala de piloto (<10⁴ filas) un seq scan responde en
-- ms; un GIN sobre `marcas` se añadiría con volumen real, no por si acaso.
--
-- REVERSIBILIDAD: nada toca datos existentes. Rollback al pie.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FASE 0 — PREFLIGHT
-- ----------------------------------------------------------------------------
DO $s326_preflight$
BEGIN
    IF to_regclass('public.query_logs') IS NULL
       OR to_regclass('public.answer_feedback') IS NULL THEN
        RAISE EXCEPTION '021: falta el bootstrap (query_logs/answer_feedback — supabase_schema.sql)';
    END IF;
    IF to_regclass('public.bot_allowlist') IS NULL THEN
        RAISE EXCEPTION '021: aplica ANTES migrations/016_allowlist_invitaciones.sql (falta bot_allowlist)';
    END IF;
    IF to_regclass('public.documents') IS NULL THEN
        RAISE EXCEPTION '021: falta documents (migrations/001_document_management.sql)';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles
                    WHERE rolname = 'service_role' AND rolbypassrls) THEN
        RAISE EXCEPTION '021: requiere service_role con BYPASSRLS (hardening s278)';
    END IF;
END
$s326_preflight$;

-- ----------------------------------------------------------------------------
-- FASE A — LA TABLA DERIVADA
-- ----------------------------------------------------------------------------
-- PK = query_log_id (1:1): re-clasificar SOBRESCRIBE la fila con la versión
-- vigente — una fila por pregunta, nunca apilar (el histórico de corridas vive
-- en los recibos del job, no aquí). El verbo lo decide el job: fila nueva →
-- INSERT (ignore-duplicates); fila con versión vieja → PATCH de columnas. El
-- upsert merge-duplicates de PostgREST se DESCARTÓ medido (backfill 19-ago):
-- su DO UPDATE SET re-escribe también la PK y exigiría GRANT
-- UPDATE(query_log_id) — justo el permiso que el trinquete de abajo prohíbe.
--   · `origen` declara la procedencia: 'regla' (ruta del plan de turno, $0) o
--     'llm' (Haiku sobre taxonomía cerrada). `origen_coherente` hace imposible
--     un 'llm' sin modelo declarado y un 'regla' con él.
--   · `marcas` = canónicas del catálogo (lo que el corpus CONOCE). `modelos` =
--     los `product_models` del turno con normalización DECLARADA solo-mayúsculas
--     (hallazgo Sol r1 s326, aceptado como límite v1): mapear variantes de
--     modelo al slug canónico es terreno del workstream de identidad (DEC-074),
--     no de esta métrica.
--   · `marcas_libres` = menciones de marca que NO resolvieron contra el
--     catálogo — la materia prima de `bot_marcas_sin_corpus_semanal` (demanda
--     no cubierta). El clasificador canonicaliza antes de escribir: lo que
--     resuelve se muda a `marcas`, aquí solo queda lo desconocido.
CREATE TABLE IF NOT EXISTS public.query_clasificacion (
    query_log_id      UUID PRIMARY KEY
                      REFERENCES public.query_logs(id) ON DELETE CASCADE,
    categoria         TEXT NOT NULL CHECK (categoria IN (
                          'especificaciones',
                          'instalacion_cableado',
                          'configuracion_programacion',
                          'averias_diagnostico',
                          'mantenimiento_pruebas',
                          'compatibilidad_sustitucion',
                          'normativa',
                          'catalogo_documentacion',
                          'otros')),
    taxonomia_version SMALLINT NOT NULL CHECK (taxonomia_version >= 1),
    marcas            TEXT[] NOT NULL DEFAULT '{}',
    modelos           TEXT[] NOT NULL DEFAULT '{}',
    marcas_libres     TEXT[] NOT NULL DEFAULT '{}',
    origen            TEXT NOT NULL CHECK (origen IN ('regla', 'llm')),
    modelo_llm        TEXT,
    clasificado_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT query_clasificacion_origen_coherente CHECK (
        (origen = 'llm' AND modelo_llm IS NOT NULL)
        OR (origen = 'regla' AND modelo_llm IS NULL)
    )
);

COMMENT ON TABLE public.query_clasificacion IS
    'Clasificación DERIVADA de cada pregunta (s326): tipología (taxonomía '
    'cerrada versionada) + marcas/modelos canónicos + menciones fuera de '
    'corpus. La escribe el job batch; reconstruible entera desde query_logs; '
    'muere en cascada con su fila (supresión RGPD intacta).';

ALTER TABLE public.query_clasificacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_clasificacion FORCE ROW LEVEL SECURITY;

-- ACL enumerada (patrón 019/9-bis: toda columna escrita tiene su GRANT).
-- Sin policies a propósito (s278): RLS sin policies = default-deny para todo
-- el mundo; el backend entra por service_role (BYPASSRLS).
REVOKE ALL PRIVILEGES ON TABLE public.query_clasificacion
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.query_clasificacion TO service_role;
GRANT INSERT (query_log_id, categoria, taxonomia_version, marcas, modelos,
              marcas_libres, origen, modelo_llm, clasificado_at)
    ON public.query_clasificacion TO service_role;
GRANT UPDATE (categoria, taxonomia_version, marcas, modelos,
              marcas_libres, origen, modelo_llm, clasificado_at)
    ON public.query_clasificacion TO service_role;

-- ----------------------------------------------------------------------------
-- FASE B — VISTAS AGREGADAS (patrón s301: security_invoker, conteos puros)
-- ----------------------------------------------------------------------------

-- ¿De qué TIPO son las preguntas? `taxonomia_version` viaja en la fila para que
-- una gráfica nunca mezcle dos taxonomías sin decirlo.
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
GROUP BY 1, 2, 3;

-- El medidor de honestidad de la tipología: si el job no corre, las gráficas de
-- arriba se quedan viejas EN SILENCIO — esta vista dice cuántas preguntas no
-- tienen NINGUNA clasificación. ALCANCE HONESTO (hallazgo Sol r1 s326): la
-- columna se llama `sin_clasificar`, no «pendientes», porque el SQL no puede
-- saber la versión VIGENTE de la taxonomía (vive en el YAML): tras subir a v2,
-- las filas v1 son pendientes PARA EL JOB pero aquí cuentan como clasificadas —
-- el desfase se ve en `taxonomia_min`/`taxonomia_max` contra la vigente, y el
-- recibo del job es la autoridad de «cuánto queda».
CREATE OR REPLACE VIEW public.bot_clasificacion_cobertura
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    COUNT(*) AS consultas,
    COUNT(qc.query_log_id) AS clasificadas,
    COUNT(*) - COUNT(qc.query_log_id) AS sin_clasificar,
    MIN(qc.taxonomia_version) AS taxonomia_min,
    MAX(qc.taxonomia_version) AS taxonomia_max
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
WHERE ql.source <> 'error'
GROUP BY 1;

-- ¿Por qué FABRICANTES se pregunta? (canónicos: lo que el bot resolvió contra
-- el catálogo — una marca no resuelta NO aparece aquí; el hueco lo enseña
-- bot_marcas_sin_corpus_semanal, no la alfombra.)
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
GROUP BY 1, 2;

-- ¿Por qué MODELOS se pregunta?
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
GROUP BY 1, 2;

-- ¿En qué TIPO de pregunta falla el bot? El cruce calidad×tipología que hoy no
-- existe: el voto del PROPIO autor de la pregunta (mismo telegram_user_id).
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
GROUP BY 1, 2;

-- ¿Quién pregunta cuánto, y con qué feedback? El ALIAS es la `nota` de la
-- allowlist (adjudicación de Alberto, s326) — el mismo dato que la pestaña de
-- Acceso ya enseña. Sin alta en la allowlist (histórico pre-piloto): la
-- etiqueta fija 'sin alta (histórico)', SIN el id — correlacionar un
-- identificador directo con conteos sería exposición nueva (hallazgo Sol r1
-- s326); los históricos se agrupan bajo esa etiqueta a conciencia, y quien
-- necesite el detalle tiene la base, no el panel.
CREATE OR REPLACE VIEW public.bot_preguntas_por_usuario_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    COALESCE(ba.nota, 'sin alta (histórico)') AS quien,
    COUNT(*) AS consultas,
    COUNT(*) FILTER (WHERE af.verdict = 'up')   AS votos_up,
    COUNT(*) FILTER (WHERE af.verdict = 'down') AS votos_down
FROM public.query_logs ql
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE ql.source <> 'error'
GROUP BY 1, 2;

-- Demanda NO cubierta = señal de corpus y de M&A (cierra la intención de
-- `query_gaps`, TECH_DEBT #8): menciones de marca que no resolvieron contra el
-- catálogo. El NOT EXISTS contra `documents` re-verifica en LECTURA: si una
-- marca se ingesta después, sus menciones históricas dejan de contar como
-- hueco sin re-clasificar nada.
CREATE OR REPLACE VIEW public.bot_marcas_sin_corpus_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', ql.created_at)::date AS semana,
    ml.marca_libre,
    COUNT(*) AS menciones
FROM public.query_clasificacion qc
JOIN public.query_logs ql ON ql.id = qc.query_log_id
CROSS JOIN LATERAL unnest(qc.marcas_libres) AS ml(marca_libre)
WHERE NOT EXISTS (
    SELECT 1 FROM public.documents d
     WHERE d.status = 'active'
       AND lower(d.manufacturer) = lower(ml.marca_libre))
GROUP BY 1, 2;

-- ----------------------------------------------------------------------------
-- FASE C — LA VISTA FILA-A-FILA DEL EXPLORADOR (prosa: adjudicación (a), s326)
-- ----------------------------------------------------------------------------
-- Una fila por pregunta CON su texto, su clasificación y el feedback del autor.
-- Es deliberadamente lo que DEC-231 dejó fuera de la v1 y Alberto reabrió:
-- entra en el addendum del paquete del abogado. Solo la lee el panel
-- (service_role, server-side); `anon`/`authenticated` quedan revocados abajo.
-- El feedback enlazado es el del AUTOR de la pregunta (mismo telegram_user_id);
-- `response` NO se expone: para leer respuestas está la base, no el panel.
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
    af.comment
FROM public.query_logs ql
LEFT JOIN public.query_clasificacion qc ON qc.query_log_id = ql.id
LEFT JOIN public.bot_allowlist ba ON ba.telegram_user_id = ql.telegram_user_id
LEFT JOIN public.answer_feedback af
       ON af.query_log_id = ql.id
      AND af.telegram_user_id = ql.telegram_user_id
WHERE ql.source <> 'error';

-- ----------------------------------------------------------------------------
-- FASE D — ACL DE LAS VISTAS + RECARGA DE POSTGREST
-- ----------------------------------------------------------------------------
REVOKE ALL PRIVILEGES ON public.bot_tipologia_semanal,
    public.bot_clasificacion_cobertura,
    public.bot_marcas_semanal,
    public.bot_modelos_semanal,
    public.bot_feedback_tipologia_semanal,
    public.bot_preguntas_por_usuario_semanal,
    public.bot_marcas_sin_corpus_semanal,
    public.bot_explorador_v1
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.bot_tipologia_semanal,
    public.bot_clasificacion_cobertura,
    public.bot_marcas_semanal,
    public.bot_modelos_semanal,
    public.bot_feedback_tipologia_semanal,
    public.bot_preguntas_por_usuario_semanal,
    public.bot_marcas_sin_corpus_semanal,
    public.bot_explorador_v1
    TO service_role;

NOTIFY pgrst, 'reload schema';

-- ----------------------------------------------------------------------------
-- FASE E — POSTCONDICIONES (la migración se auto-comprueba o aborta entera)
-- ----------------------------------------------------------------------------
DO $s326_postcondiciones$
DECLARE
    vista TEXT;
    columna TEXT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
         WHERE oid = 'public.query_clasificacion'::regclass
           AND relrowsecurity AND relforcerowsecurity) THEN
        RAISE EXCEPTION '021: query_clasificacion sin RLS ENABLE+FORCE';
    END IF;
    FOREACH columna IN ARRAY ARRAY[
        'query_log_id', 'categoria', 'taxonomia_version', 'marcas', 'modelos',
        'marcas_libres', 'origen', 'modelo_llm', 'clasificado_at'
    ] LOOP
        IF NOT has_column_privilege('service_role',
                                    'public.query_clasificacion',
                                    columna, 'INSERT') THEN
            RAISE EXCEPTION '021: service_role no puede INSERT query_clasificacion.%',
                columna;
        END IF;
    END LOOP;
    -- anon Y authenticated: la migración comprueba TODO lo que revoca
    -- (hallazgo Fable r1 s326 — comprobar la mitad es auto-comprobarse a medias).
    FOREACH columna IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF has_table_privilege(columna, 'public.query_clasificacion', 'SELECT') THEN
            RAISE EXCEPTION '021: % puede leer query_clasificacion', columna;
        END IF;
    END LOOP;
    FOREACH vista IN ARRAY ARRAY[
        'bot_tipologia_semanal', 'bot_clasificacion_cobertura',
        'bot_marcas_semanal', 'bot_modelos_semanal',
        'bot_feedback_tipologia_semanal', 'bot_preguntas_por_usuario_semanal',
        'bot_marcas_sin_corpus_semanal', 'bot_explorador_v1'
    ] LOOP
        IF to_regclass('public.' || vista) IS NULL THEN
            RAISE EXCEPTION '021: falta la vista %', vista;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
             WHERE oid = ('public.' || vista)::regclass
               AND reloptions @> ARRAY['security_invoker=true']) THEN
            RAISE EXCEPTION '021: % sin security_invoker', vista;
        END IF;
        FOREACH columna IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF has_table_privilege(columna, 'public.' || vista, 'SELECT') THEN
                RAISE EXCEPTION '021: % puede leer %', columna, vista;
            END IF;
        END LOOP;
    END LOOP;
END
$s326_postcondiciones$;

-- ----------------------------------------------------------------------------
-- ROLLBACK (copia/pega; nada de esto toca query_logs ni el feedback):
--   DROP VIEW IF EXISTS public.bot_explorador_v1;
--   DROP VIEW IF EXISTS public.bot_marcas_sin_corpus_semanal;
--   DROP VIEW IF EXISTS public.bot_preguntas_por_usuario_semanal;
--   DROP VIEW IF EXISTS public.bot_feedback_tipologia_semanal;
--   DROP VIEW IF EXISTS public.bot_modelos_semanal;
--   DROP VIEW IF EXISTS public.bot_marcas_semanal;
--   DROP VIEW IF EXISTS public.bot_clasificacion_cobertura;
--   DROP VIEW IF EXISTS public.bot_tipologia_semanal;
--   DROP TABLE IF EXISTS public.query_clasificacion;
--   NOTIFY pgrst, 'reload schema';
-- ----------------------------------------------------------------------------
