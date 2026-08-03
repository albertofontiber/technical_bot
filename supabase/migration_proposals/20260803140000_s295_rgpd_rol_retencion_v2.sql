-- ============================================================================
-- PROPUESTA NO APLICADA — decisión de Alberto (3-ago-2026: OK al enfoque). NO EJECUTAR
-- hasta revisar. Vive en `migration_proposals/` (excluida de `supabase db push`).
-- ============================================================================
-- s295 · DEC-177 — hacer EJECUTABLE la retención de 24 meses **sin tocar `service_role`**.
--
-- Ámbito: las tablas de producción de hoy. NO cubre el schema futuro `convo`, que sigue
-- bloqueado por su propia matriz firmada (`docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md`).
--
-- ---------------------------------------------------------------------------
-- POR QUÉ UN ROL DEDICADO Y NO `service_role` (v1 → v2)
-- ---------------------------------------------------------------------------
-- La primera versión concedía los privilegios a `service_role`. `service_role` **es la
-- identidad del bot**: la misma clave que usa el worker de Railway encendido 24/7. Eso
-- pagaba, con superficie permanente del proceso en producción, un privilegio que se ejerce
-- como mucho una vez cada varios meses — y el más fuerte de todos (DELETE) quedaba colgando
-- de un proceso expuesto a internet.
--
-- Aquí el privilegio vive en un rol NOLOGIN que se asume con `SET LOCAL ROLE` desde una
-- conexión de operador. Sus credenciales NO están en el entorno del bot. El hardening de
-- julio (`20260713164800_harden_personal_data_tables_v1.sql`) **queda intacto**:
-- `service_role` conserva exactamente SELECT+INSERT, y sus postcondiciones siguen pasando.
--
-- Patrón ya establecido en este repo: `20260721120000_add_p1_readonly_role.sql`
-- (`p1_readonly`, NOINHERIT + SET TRUE, asumido con `SET LOCAL ROLE`).
--
-- ---------------------------------------------------------------------------
-- LA PIEZA QUE HACE ESTO MEJOR QUE UN GRANT: LA VENTANA VIVE EN LA BASE
-- ---------------------------------------------------------------------------
-- El rol es NOBYPASSRLS, y estas tablas tienen RLS + FORCE RLS con 0 políticas ⇒ sin una
-- política explícita no vería NI UNA FILA. Se aprovecha eso: las políticas de abajo acotan
-- lo que el rol puede tocar a `created_at < now() - interval '24 months'`.
--
-- Consecuencia estructural: **mientras el rol está asumido**, el plazo deja de ser un filtro
-- que el script tenga que acordarse de poner y pasa a ser un invariante del motor: ni un bug
-- ni un parámetro equivocado pueden tocar una fila reciente.
--
-- ALCANCE HONESTO de ese invariante: rige para quien actúa COMO `rgpd_retencion`. NO ata a
-- `postgres` —que es owner y `rolbypassrls`— ni a `service_role`. Una consulta suelta en el
-- editor SQL sigue pudiendo tocar lo que quiera; lo que el invariante garantiza es que ESTE
-- job, y cualquier automatismo que use este rol, no puede excederse. Por eso el propio job
-- comprueba `current_user` tras asumirlo (ver punto 6): sin esa comprobación, un `SET LOCAL
-- ROLE` fuera de transacción sería un no-op silencioso y todo correría como `postgres`.
--
-- Si el plazo cambia, cambia por migración — que es como debe cambiar una decisión
-- gobernada, no por un flag de línea de comandos.
--
-- ---------------------------------------------------------------------------
-- EL DISEÑO, columna por columna
-- ---------------------------------------------------------------------------
--  query_logs.telegram_user_id      -> NULL    (ya nullable)
--  feedback.telegram_user_id        -> NULL    (ya nullable)
--  answer_feedback.telegram_user_id -> NULL    (exige DROP NOT NULL; el voto y su
--                                               comentario son la señal valiosa y se
--                                               conservan sin dueño. El UNIQUE sigue
--                                               vigente: Postgres admite varios NULL)
--  answer_messages                  -> DELETE  (mapeo mensaje->consulta, puramente
--                                               operativo. A 24 meses su valor analítico
--                                               es CERO y carga `telegram_chat_id`, que en
--                                               chat privado ES el user_id)
--  user_consent                     -> [DECIDIR]  fuera de esta propuesta (ver matriz)
--
-- Disociar solo `query_logs` NO anonimiza: las hijas se unen por `query_log_id` y el
-- `ON DELETE CASCADE` de sus FK solo actúa al BORRAR el padre — una retención que ACTUALIZA
-- no dispara nada. Por eso el alcance es el grafo entero.
--
-- Y con el nombre correcto: esto es SEUDONIMIZACIÓN. El texto libre puede identificar.

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Precondiciones
-- ---------------------------------------------------------------------------
DO $s295_preflight$
DECLARE
    relacion TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        RAISE EXCEPTION 's295: hace falta el rol operador `postgres`';
    END IF;
    FOREACH relacion IN ARRAY ARRAY[
        'public.query_logs', 'public.feedback',
        'public.answer_feedback', 'public.answer_messages'
    ] LOOP
        IF to_regclass(relacion) IS NULL THEN
            RAISE EXCEPTION 's295: falta la relacion %', relacion;
        END IF;
    END LOOP;
END
$s295_preflight$;

-- ---------------------------------------------------------------------------
-- 1. El rol
-- ---------------------------------------------------------------------------
DO $s295_rol$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
        CREATE ROLE rgpd_retencion
            NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS;
    ELSIF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'rgpd_retencion'
          AND (rolsuper OR rolinherit OR rolcreaterole OR rolcreatedb
               OR rolcanlogin OR rolreplication OR rolbypassrls)
    ) THEN
        RAISE EXCEPTION 's295: el rol rgpd_retencion existente tiene atributos inseguros';
    END IF;
END
$s295_rol$;

-- NO se pone `ALTER ROLE … SET statement_timeout`: PostgreSQL **no aplica los defaults de
-- ALTER ROLE al asumir un rol con SET ROLE**, así que sería un adorno inerte. El precedente
-- canónico de este repo ya lo documenta (`20260721120000_add_p1_readonly_role.sql`). El
-- límite lo pone la sesión: `scripts/rgpd_retencion.py` emite `SET LOCAL statement_timeout`
-- dentro de la misma transacción, que sí surte efecto.

-- `WITH INHERIT FALSE` es lo que corta la herencia (el `NOINHERIT` del rol destino no
-- interviene aquí); `WITH SET TRUE` permite asumirlo explícitamente. El rol NO se concede a
-- `authenticator`: esto no se ejerce vía PostgREST, y no darle ese camino es parte del punto.
GRANT rgpd_retencion TO postgres WITH INHERIT FALSE;
GRANT rgpd_retencion TO postgres WITH SET TRUE;

GRANT USAGE ON SCHEMA public TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 2. Privilegios de COLUMNA (lo mínimo para contar, devolver recibo y disociar)
-- ---------------------------------------------------------------------------
GRANT SELECT (id, created_at, telegram_user_id) ON public.query_logs      TO rgpd_retencion;
GRANT SELECT (id, created_at, telegram_user_id) ON public.feedback        TO rgpd_retencion;
GRANT SELECT (id, created_at, telegram_user_id) ON public.answer_feedback TO rgpd_retencion;
GRANT SELECT (id, created_at, telegram_chat_id) ON public.answer_messages TO rgpd_retencion;

GRANT UPDATE (telegram_user_id) ON public.query_logs      TO rgpd_retencion;
GRANT UPDATE (telegram_user_id) ON public.feedback        TO rgpd_retencion;
GRANT UPDATE (telegram_user_id) ON public.answer_feedback TO rgpd_retencion;
GRANT DELETE                    ON public.answer_messages TO rgpd_retencion;

-- El rol NO puede leer la pregunta, la transcripción, la respuesta ni el comentario: no
-- los necesita para disociar, y un job de cumplimiento no tiene por qué ver el contenido.

-- ---------------------------------------------------------------------------
-- 3. Las políticas: la ventana de 24 meses como invariante del motor
-- ---------------------------------------------------------------------------
-- Primero, la precondición de la que cuelga TODO el invariante, afirmada aquí y no
-- heredada: sin RLS + FORCE RLS estas políticas no gobiernan nada. `answer_feedback` solo
-- las recibía en `supabase_schema.sql` (nunca en una migración versionada), así que un
-- entorno levantado con `db push` no las tendría.
ALTER TABLE public.query_logs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_logs      FORCE  ROW LEVEL SECURITY;
ALTER TABLE public.feedback        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback        FORCE  ROW LEVEL SECURITY;
ALTER TABLE public.answer_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answer_feedback FORCE  ROW LEVEL SECURITY;
ALTER TABLE public.answer_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answer_messages FORCE  ROW LEVEL SECURITY;

-- Solo aplican al rol nombrado. `service_role` tiene rolbypassrls ⇒ el bot no se entera.
DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.query_logs;
CREATE POLICY rgpd_retencion_ventana ON public.query_logs
    TO rgpd_retencion
    USING      (created_at < now() - interval '24 months')
    WITH CHECK (created_at < now() - interval '24 months');

DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.feedback;
CREATE POLICY rgpd_retencion_ventana ON public.feedback
    TO rgpd_retencion
    USING      (created_at < now() - interval '24 months')
    WITH CHECK (created_at < now() - interval '24 months');

DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.answer_feedback;
CREATE POLICY rgpd_retencion_ventana ON public.answer_feedback
    TO rgpd_retencion
    USING      (created_at < now() - interval '24 months')
    WITH CHECK (created_at < now() - interval '24 months');

DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.answer_messages;
CREATE POLICY rgpd_retencion_ventana ON public.answer_messages
    TO rgpd_retencion
    USING (created_at < now() - interval '24 months');

-- ---------------------------------------------------------------------------
-- 4. Cambios de esquema
-- ---------------------------------------------------------------------------
-- 4.a `created_at` era NULLABLE en las cuatro: una fila con fecha NULL no satisface
-- `created_at < corte` NUNCA ⇒ conservaría su identificador para siempre, y el «invariante»
-- tendría un agujero silencioso. Hoy hay 0 nulos (verificado contra producción el 3-ago),
-- así que el SET NOT NULL es seguro y cierra el hueco de forma permanente.
ALTER TABLE public.query_logs      ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE public.feedback        ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE public.answer_feedback ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE public.answer_messages ALTER COLUMN created_at SET NOT NULL;

-- 4.b La columna que permite disociar el voto.
-- Verificado por el dúo que no rompe nada: el UNIQUE (query_log_id, telegram_user_id)
-- sigue válido (NULLS DISTINCT), el índice es sobre `created_at`, y los lectores filtran
-- con `eq.` ⇒ simplemente no casan las filas disociadas.
ALTER TABLE public.answer_feedback ALTER COLUMN telegram_user_id DROP NOT NULL;

-- ---------------------------------------------------------------------------
-- 5. Que la retención no se pueda DESHACER sola
-- ---------------------------------------------------------------------------
-- Hueco real: disociar `query_logs.telegram_user_id` NO borra la fila, así que un teclado
-- antiguo sigue llevando su `query_log_id`. Si alguien pulsa 👍/👎 en un mensaje de hace dos
-- años, `log_answer_feedback` inserta un voto CON su `telegram_user_id`, la FK se cumple, el
-- UNIQUE no choca (NULLS DISTINCT) — y la consulta vencida queda re-identificada otros 24
-- meses. El código ya contempla el caso del BORRADO (falla la FK), no el de la disociación.
--
-- Se cierra en el motor y no en Python: cualquier cliente, hoy o mañana, queda cubierto.
CREATE OR REPLACE FUNCTION public.rgpd_no_reidentificar_v1()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $rgpd_trigger$
BEGIN
    IF NEW.telegram_user_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.query_logs q
         WHERE q.id = NEW.query_log_id AND q.telegram_user_id IS NULL
    ) THEN
        RAISE EXCEPTION 'rgpd: la consulta % ya esta disociada; no se le puede volver a '
                        'asociar una persona', NEW.query_log_id
              USING ERRCODE = 'raise_exception';
    END IF;
    RETURN NEW;
END
$rgpd_trigger$;

DROP TRIGGER IF EXISTS rgpd_no_reidentificar ON public.answer_feedback;
CREATE TRIGGER rgpd_no_reidentificar
    BEFORE INSERT OR UPDATE ON public.answer_feedback
    FOR EACH ROW EXECUTE FUNCTION public.rgpd_no_reidentificar_v1();

-- El bot ya trata el fallo de escritura del voto como «no se pudo registrar» (mismo camino
-- que el teclado obsoleto tras un borrado RGPD), asi que no hace falta tocarlo.

-- ---------------------------------------------------------------------------
-- 6. Postcondiciones
-- ---------------------------------------------------------------------------
DO $s295_post$
DECLARE
    faltan TEXT;
    tabla TEXT;
    priv TEXT;
    columna TEXT;
    esperado_rol TEXT[] := ARRAY['SELECT', 'UPDATE'];
BEGIN
    -- 6.1 PRECONDICION del invariante: sin RLS + FORCE RLS las politicas no gobiernan nada.
    FOREACH tabla IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages'
    ] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
             WHERE oid = format('public.%I', tabla)::regclass
               AND relrowsecurity AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 's295: RLS no esta habilitada Y forzada en %', tabla;
        END IF;
    END LOOP;

    -- 6.2 El rol tiene lo que necesita.
    SELECT string_agg(t.tabla, ', ') INTO faltan
      FROM (VALUES ('query_logs'), ('feedback'), ('answer_feedback')) AS t(tabla)
     WHERE NOT has_column_privilege('rgpd_retencion', ('public.' || t.tabla)::regclass,
                                    'telegram_user_id', 'UPDATE');
    IF faltan IS NOT NULL THEN
        RAISE EXCEPTION 's295: rgpd_retencion sin UPDATE(telegram_user_id) en: %', faltan;
    END IF;
    IF NOT has_table_privilege('rgpd_retencion', 'public.answer_messages', 'DELETE') THEN
        RAISE EXCEPTION 's295: rgpd_retencion sin DELETE en answer_messages';
    END IF;

    -- 6.3 ...y NADA mas. IGUALDAD EXACTA sobre los 8 privilegios, como hace el bootstrap:
    -- "ausencia de algunos" deja pasar justo el que no se te ocurrio comprobar.
    FOREACH tabla IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages'
    ] LOOP
        FOREACH priv IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ] LOOP
            -- Privilegio de TABLA: el unico admitido es DELETE en answer_messages.
            IF has_table_privilege('rgpd_retencion', format('public.%I', tabla), priv)
               IS DISTINCT FROM (tabla = 'answer_messages' AND priv = 'DELETE') THEN
                RAISE EXCEPTION 's295: privilegio de TABLA inesperado % en % para rgpd_retencion',
                    priv, tabla;
            END IF;
            -- Privilegio de COLUMNA: solo SELECT y UPDATE, nada mas.
            IF priv <> ALL(esperado_rol)
               AND priv <> 'DELETE'
               AND has_any_column_privilege('rgpd_retencion', format('public.%I', tabla), priv) THEN
                RAISE EXCEPTION 's295: privilegio de COLUMNA inesperado % en % para rgpd_retencion',
                    priv, tabla;
            END IF;
        END LOOP;
    END LOOP;

    -- 6.4 El rol NO puede leer contenido: se comprueban TODAS las columnas de texto libre,
    -- no una de muestra.
    FOREACH columna IN ARRAY ARRAY['query', 'response', 'transcription'] LOOP
        IF has_column_privilege('rgpd_retencion', 'public.query_logs', columna, 'SELECT') THEN
            RAISE EXCEPTION 's295: rgpd_retencion no debe poder LEER query_logs.%', columna;
        END IF;
    END LOOP;
    IF has_column_privilege('rgpd_retencion', 'public.answer_feedback', 'comment', 'SELECT') THEN
        RAISE EXCEPTION 's295: rgpd_retencion no debe poder LEER el comentario del voto';
    END IF;

    -- 6.5 `service_role` EXACTAMENTE como estaba: el hardening de julio no se toca.
    FOREACH tabla IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages', 'user_consent'
    ] LOOP
        FOREACH priv IN ARRAY ARRAY['UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
            -- UPDATE de tabla es legitimo en answer_feedback (upsert del voto, s286) y en
            -- user_consent (re-aceptacion). Todo lo demas debe ser FALSO.
            IF has_table_privilege('service_role', format('public.%I', tabla), priv)
               IS DISTINCT FROM (priv = 'UPDATE'
                                 AND tabla IN ('answer_feedback', 'user_consent')) THEN
                RAISE EXCEPTION 's295: service_role ha ganado o perdido % en % -- el hardening '
                                'de julio debe quedar EXACTAMENTE como estaba', priv, tabla;
            END IF;
        END LOOP;
    END LOOP;
    IF has_any_column_privilege('service_role', 'public.query_logs', 'UPDATE')
       OR has_any_column_privilege('service_role', 'public.feedback', 'UPDATE') THEN
        RAISE EXCEPTION 's295: service_role ha ganado UPDATE de columna -- no era el plan';
    END IF;

    -- 6.6 Las politicas existen Y dicen lo que deben: nombre, rol y predicado.
    FOREACH tabla IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages'
    ] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
             WHERE schemaname = 'public' AND tablename = tabla
               AND policyname = 'rgpd_retencion_ventana'
               AND roles @> ARRAY['rgpd_retencion']::name[]
               AND qual LIKE '%24 mons%'
        ) THEN
            RAISE EXCEPTION 's295: la politica de ventana de % no existe, no apunta al rol, '
                            'o su predicado no acota a 24 meses', tabla;
        END IF;
    END LOOP;

    -- 6.7 El esquema admite la disociacion y no deja filas sin fecha (que nunca vencerian).
    IF (SELECT is_nullable FROM information_schema.columns
         WHERE table_schema='public' AND table_name='answer_feedback'
           AND column_name='telegram_user_id') <> 'YES' THEN
        RAISE EXCEPTION 's295: answer_feedback.telegram_user_id sigue siendo NOT NULL';
    END IF;
    FOREACH tabla IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages'
    ] LOOP
        IF (SELECT is_nullable FROM information_schema.columns
             WHERE table_schema='public' AND table_name=tabla
               AND column_name='created_at') <> 'NO' THEN
            RAISE EXCEPTION 's295: %.created_at sigue siendo NULLABLE -- una fila sin fecha '
                            'no vence jamas', tabla;
        END IF;
    END LOOP;

    -- 6.8 El trigger anti-reidentificacion esta armado.
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
         WHERE tgrelid = 'public.answer_feedback'::regclass
           AND tgname = 'rgpd_no_reidentificar' AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 's295: falta el trigger rgpd_no_reidentificar';
    END IF;
END
$s295_post$;

COMMIT;

-- ---------------------------------------------------------------------------
-- BOOTSTRAP (`supabase_schema.sql`)
-- ---------------------------------------------------------------------------
-- A diferencia de la v1, esta propuesta **no exige tocar sus postcondiciones**: solo
-- comprueban `anon`, `authenticated` y `service_role`, y ninguno cambia. Su
-- `REVOKE ALL … FROM PUBLIC, anon, authenticated, service_role` tampoco alcanza a
-- `rgpd_retencion` (revoca de los roles nombrados). Ese es otro efecto de haber sacado el
-- privilegio de `service_role`: desaparece el acoplamiento que en la v1 obligaba a mover
-- dos ficheros a la vez.
--
-- Lo que SÍ conviene, para que un bootstrap limpio quede completo: replicar el bloque de
-- rol + grants + políticas + DROP NOT NULL de arriba. Se hace al aplicar, no antes: hacerlo
-- ahora crearía la divergencia inversa (bootstrap con un rol que producción no tiene).
--
-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.query_logs;      (x4 tablas)
--   REVOKE ALL ON public.query_logs FROM rgpd_retencion;                    (x4 tablas)
--   REVOKE USAGE ON SCHEMA public FROM rgpd_retencion;
--   REVOKE rgpd_retencion FROM postgres;
--   DROP ROLE rgpd_retencion;
--   ALTER TABLE public.answer_feedback ALTER COLUMN telegram_user_id SET NOT NULL;
--
-- El último paso **falla en cuanto haya una sola fila disociada** ⇒ el rollback del esquema
-- deja de ser posible tras la primera ejecución real. Declarado, no escondido. Los
-- privilegios sí se retiran siempre.
