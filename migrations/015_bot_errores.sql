-- ============================================================================
-- 015 — `bot_errors`: el registro de INCIDENCIAS del bot (s324e).
--
-- ✅ APLICADA EN PRODUCCIÓN el 17-ago-2026 (Alberto, SQL editor de Supabase).
--    Verificado el mismo día vía PostgREST: la tabla existe y tiene 0 filas —
--    que es el resultado bueno (0 filas = ningún error del bot desde que se
--    creó, no «no funciona»). Se dejó `NOTIFY pgrst, 'reload schema'` al pie
--    porque PostgREST cachea el esquema y devolvía 404 con la tabla ya creada.
--
--    El bot funciona SIN ella: `log_bot_error` detecta la tabla ausente
--    (PGRST205/404), avisa UNA vez en el log y degrada al registro heredado de
--    s286 (fila en `query_logs` con `source='error'`). Es decir: aplicarla
--    añade insights, no arranca el mecanismo.
--
-- PROBLEMA QUE RESUELVE. Desde s286 un error del bot deja UNA fila en
-- `query_logs` con `source='error'` y un texto `TipoDeExcepcion@etapa` metido
-- en la columna `response`. Con eso se puede CONTAR errores (lo hace
-- `bot_health_report`), pero no se puede aprender de ellos: no hay clase de
-- fallo, no hay módulo de origen, no hay severidad y agrupar exige parsear una
-- cadena. Para un piloto con Directores Generales la pregunta útil no es
-- «¿cuántos errores?» sino «¿qué CLASE de error, en qué MÓDULO, en qué DÍA, y
-- sobre qué preguntas» — y eso son columnas, no substrings.
--
-- POR QUÉ UNA TABLA HIJA Y NO COLUMNAS EN `query_logs`:
--   * un error puede NO tener consulta (un fallo en `/start`, en el callback de
--     feedback o en un job de la JobQueue). Columnas en `query_logs` obligarían
--     a inventar una fila de consulta que no existió;
--   * `query_logs` es la tabla de ADOPCIÓN. Sus consumidores ya filtran
--     `source <> 'error'` en todas partes (vistas de salud, digest, export):
--     ese filtro repetido es la señal de que la fila de error nunca perteneció
--     ahí. Aquí no se elimina esa fila (sigue siendo el contenedor GOBERNADO
--     del texto de la consulta) pero deja de ser el único sitio donde vive el
--     diagnóstico;
--   * una columna JSONB en `query_logs` era la alternativa sin tabla nueva: se
--     descarta porque `rag_trace` ya demostró el problema — su CHECK de tamaño
--     y su validador cerrado son mantenimiento, agrupar por clave JSON no usa
--     índice, y la columna faltó en producción durante meses sin que nadie lo
--     notara.
--
-- RGPD — LA DECISIÓN DE DISEÑO MÁS IMPORTANTE DE ESTA TABLA:
--   **`bot_errors` no contiene dato personal DIRECTO** (no hay
--   `telegram_user_id` ni texto de consulta), **pero SÍ es dato ENLAZABLE**:
--   `query_log_id` es una FK a `query_logs` y el script de insights la recorre
--   justamente para sacar la pregunta y el autor. Corregido tras el dúo r37 —
--   la redacción anterior decía «no contiene dato personal» a secas y eso era
--   inexacto. Lo que se gana NO es quedar fuera del RGPD, sino que la
--   incidencia hereda la gobernanza de `query_logs` en vez de crear un
--   contenedor con reglas propias. Si el tratamiento exige algo más, eso lo
--   decide el asesor jurídico, no esta migración.
--   Consecuencias, todas deliberadas:
--     · `DELETE FROM query_logs WHERE telegram_user_id = X` (el procedimiento
--       de supresión a petición ya documentado) se lleva las incidencias sin
--       añadir un paso al runbook;
--     · el job mensual de retención NO necesita conocer esta tabla: no hay
--       identificador que disociar. No hace falta una quinta política
--       `rgpd_retencion_ventana` ni tocar `rgpd_retencion_pasada`;
--     · a mi juicio no hay finalidad nueva —y por tanto no VEO motivo para
--       subir TERMS_VERSION—, pero **eso lo valida el asesor, no yo** (r37): el
--       aviso v8 está redactado y pendiente solo de revisión jurídica, y es ahí
--       donde entra esta tabla. El texto de
--       la consulta se guarda donde ya se guardaba (`query_logs`) y para lo que
--       ya se declaró («diagnóstico»);
--     · precio declarado: un error de alguien SIN consentimiento, o cuyo turno
--       no tenía consulta, deja una fila huérfana (`query_log_id` NULL). Se
--       cuenta por clase y módulo pero no se puede atribuir a una persona ni a
--       una pregunta. Es el resultado correcto: sin consentimiento no se guarda
--       su texto.
--
-- Idempotente (IF NOT EXISTS). Tiempo estimado: <1 s. Rollback al pie.
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO
-- ============================================================================

-- A.1: ¿existe ya?
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'bot_errors'
) AS table_exists;

-- A.2: precondición — `query_logs` debe existir (la FK cuelga de ella).
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'query_logs'
) AS query_logs_exists;

-- A.3: cuántas filas de error heredadas hay hoy (el «antes» del contador).
SELECT count(*) AS filas_error_heredadas
FROM query_logs WHERE source = 'error';


-- ============================================================================
-- FASE B — APLICAR
-- ============================================================================

CREATE TABLE IF NOT EXISTS bot_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Código corto que el técnico VE en el mensaje de error y puede citar.
    -- No es la clave: es el puente entre lo que se le enseña a una persona y
    -- la fila. UNIQUE para que citar un código resuelva a una sola incidencia.
    codigo TEXT NOT NULL UNIQUE,

    -- Enlace OPCIONAL a la consulta que lo provocó. NULL = no había consulta
    -- (comando, callback, job) o el autor no tenía consentimiento.
    query_log_id UUID REFERENCES query_logs(id) ON DELETE CASCADE,

    -- ---- La taxonomía (vocabulario CERRADO) --------------------------------
    -- Mismo tuple que `CLASES` en src/bot/error_taxonomy.py. Una clase nueva se
    -- añade en los DOS sitios o la base rechaza la fila: el vocabulario no
    -- puede derivar en silencio entre el código y el almacén.
    clase TEXT NOT NULL CHECK (clase IN (
        'red_datos',            -- red/timeout hablando con Supabase o Voyage
        'llm_saturado',         -- 429/529 del proveedor: transitorio
        'llm_fallo',            -- error real del proveedor (incl. credencial)
        'transporte_telegram',  -- envío: >4096 chars, parse_mode roto, bloqueo
        'datos_ausentes',       -- señal explícita de «el dato no está»
        'bug'                   -- residual honesto: defecto NUESTRO
    )),
    severidad TEXT NOT NULL CHECK (severidad IN ('aviso', 'grave', 'critico')),
    reintentable BOOLEAN NOT NULL DEFAULT FALSE,

    -- ---- Diagnóstico -------------------------------------------------------
    tipo_excepcion TEXT NOT NULL,   -- p.ej. 'ReadTimeout', 'KeyError'
    etapa TEXT NOT NULL,            -- 'process_query' | 'handle_voice' | 'global'
    origen TEXT,                    -- 'src/rag/generator.py:939' — RELATIVO
                                    -- (la ruta absoluta lleva el directorio de
                                    -- usuario del worker: no se guarda)
    mensaje_corto TEXT,             -- str(exc) REDACTADO y truncado a 200:
                                    -- sin URLs, sin tokens, sin dígitos largos,
                                    -- y descartado entero si reproducía la
                                    -- consulta (src/bot/error_taxonomy.redactar)

    -- ---- Qué vio el técnico ------------------------------------------------
    usuario_avisado BOOLEAN NOT NULL DEFAULT FALSE,
        -- La métrica que de verdad importa del piloto: ¿se quedó en silencio?
        -- FALSE con `bot_errors` poblada = el mensaje no salió (bot bloqueado,
        -- flag apagado, o el propio aviso falló).

    bot_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE bot_errors IS
    'Incidencias del bot (s324e). Sin dato personal DIRECTO, pero ENLAZABLE: '
    'se une a la persona por query_log_id (FK CASCADE a query_logs), de la que '
    'hereda retencion y supresion. La consulta que provoco el error vive en '
    'query_logs con source=''error''.';

-- DOS índices, cada uno con la consulta REAL que lo usa (dúo r37: había cinco
-- y tres eran aparato anticipatorio — el script descarga por fecha y agrega en
-- Python, así que agrupar por clase/origen/aviso NO toca la base).
--
--   1. created_at DESC — lo usa LITERALMENTE el script en cada corrida:
--      `?order=created_at.desc&created_at=gte.<fecha>` (paginado).
CREATE INDEX IF NOT EXISTS idx_bot_errors_created
    ON bot_errors (created_at DESC);
--   2. query_log_id — NO es para leer, es para BORRAR: Postgres no indexa
--      automáticamente el lado hijo de una FK, así que sin esto cada
--      `DELETE FROM query_logs WHERE telegram_user_id = X` (la supresión a
--      petición) hace un seq scan de bot_errors por cada fila borrada. El
--      índice es lo que mantiene barato el derecho de supresión.
CREATE INDEX IF NOT EXISTS idx_bot_errors_query_log
    ON bot_errors (query_log_id);
-- Si algún día el agregado se hace en SQL (vista o RPC) en vez de en Python,
-- ESE cambio trae sus índices; no antes.

-- ---- Frontera de seguridad, IGUAL que el resto de tablas del bot -----------
-- Mismo patrón que `supabase_schema.sql`: RLS forzada, privilegios revocados
-- nominalmente y concesión MÍNIMA. El bot solo INSERTA: no lee sus propios
-- errores (nada del serving los consulta) y no los actualiza jamás — una
-- incidencia es un hecho ocurrido, no un estado. El SELECT lo ejerce el
-- operador con sus credenciales, no el worker.
ALTER TABLE public.bot_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_errors FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.bot_errors
    FROM PUBLIC, anon, authenticated, service_role;
GRANT INSERT (codigo, query_log_id, clase, severidad, reintentable,
              tipo_excepcion, etapa, origen, mensaje_corto, usuario_avisado,
              bot_version) ON public.bot_errors TO service_role;
-- El script de insights (scripts/s324e_bot_errores_insights.py) lee con
-- SUPABASE_SERVICE_KEY, igual que bot_health_report. Se concede SELECT de
-- tabla, NO UPDATE ni DELETE: los insights se leen, no se editan.
GRANT SELECT ON TABLE public.bot_errors TO service_role;


-- ============================================================================
-- FASE C — VALIDACIÓN (postcondiciones; si alguna falla, ROLLBACK)
-- ============================================================================

-- C.1: la tabla existe con sus columnas.
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'bot_errors'
ORDER BY ordinal_position;

-- C.2: INVARIANTE — cero columnas de dato personal directo. Debe devolver 0.
SELECT count(*) AS columnas_personales_prohibidas
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'bot_errors'
  AND column_name IN ('telegram_user_id', 'telegram_chat_id', 'query',
                      'display_name', 'transcription', 'response');

-- C.3: INVARIANTE — RLS habilitada Y forzada (el bot usa service_role, que
-- lleva BYPASSRLS; FORCE es lo que hace que la frontera signifique algo).
SELECT relrowsecurity, relforcerowsecurity
FROM pg_class WHERE oid = 'public.bot_errors'::regclass;

-- C.4: INVARIANTE — la FK cascadea (sin esto, la supresión a petición dejaría
-- incidencias apuntando a consultas borradas y el borrado fallaría).
SELECT confdeltype = 'c' AS cascada_ok
FROM pg_constraint
WHERE conrelid = 'public.bot_errors'::regclass AND contype = 'f';

-- C.5: el bot NO puede leer ni modificar más de lo concedido. Debe salir
-- INSERT (por columnas) y SELECT, y nada de UPDATE/DELETE/TRUNCATE.
SELECT privilege_type, column_name
FROM information_schema.column_privileges
WHERE table_name = 'bot_errors' AND grantee = 'service_role'
ORDER BY privilege_type, column_name;


-- ============================================================================
-- ROLLBACK (completo — no toca ninguna tabla existente)
-- ============================================================================
-- DROP TABLE IF EXISTS public.bot_errors;
--
-- Tras el DROP, el bot sigue funcionando: `log_bot_error` detecta la tabla
-- ausente y degrada al registro heredado de s286. Nada más que revertir.
-- ============================================================================

-- (s324e) Exponer en la API: PostgREST cachea el esquema y una tabla recién creada puede
-- devolver 404 hasta que se recarga. Idempotente.
NOTIFY pgrst, 'reload schema';
