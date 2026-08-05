-- ============================================================================
-- APLICADA EN PRODUCCIÓN el 5-ago-2026 (Alberto, SQL Editor; verificada contra el
-- catálogo). IDEMPOTENTE: re-ejecutarla es seguro y no-opea/re-afirma. Orden de la cola:
-- s295 → s296 → s297. En un entorno nuevo se aplica tras el bootstrap.
-- ============================================================================
-- s296 — decisiones de Alberto (4-ago-2026), cuatro piezas que van juntas porque
-- tocan las mismas tablas y no tiene sentido migrar dos veces:
--
--   1. SEUDÓNIMO ESTABLE. El plazo deja de poner el identificador a NULL: lo sustituye
--      por un código aleatorio, el mismo siempre para la misma persona. Motivo de
--      Alberto: no perder el corpus de un buen técnico que se vaya. Con NULL quedarían
--      sus preguntas sueltas, sin saber que son de la misma persona.
--   2. Ese mismo código es el que viaja en los EXPORTS a disco, desde el primer día.
--      PRECISIÓN: el identificador SÍ se lee de la base al proceso que genera el export
--      (la consulta trae la fila entera); lo que se garantiza es que **no se escribe
--      nunca al fichero**. Decir «no sale nunca de la base» sería declarar de más.
--   3. `user_consent` pasa a APPEND-ONLY: una fila por (persona, versión) con su fecha.
--      Hoy el upsert machaca, así que no se puede demostrar que alguien aceptó la v3.
--   4. Enlace en `feedback`, y MARCA DE UTILIDAD en `answer_feedback` para poder
--      reconocer al técnico que aporta feedback valioso — por CALIDAD, no por cantidad.
--
-- ---------------------------------------------------------------------------
-- POR QUÉ UNA TABLA DE CORRESPONDENCIAS Y NO UN HASH
-- ---------------------------------------------------------------------------
-- La alternativa era derivar el código del identificador con HMAC y una clave secreta.
-- Se descarta: los identificadores de Telegram son un espacio pequeño y enumerable, así
-- que quien tenga la clave puede recorrerlos todos y deshacer el seudónimo. Sería
-- irreversible solo destruyendo la clave — y entonces ya no se puede volver a emitir el
-- mismo código para esa persona, que es justo lo que da valor al diseño.
--
-- Con tabla: el código es aleatorio (no deriva de nada), y la irreversibilidad llega en
-- un momento explícito y auditable — cuando se BORRA la fila de correspondencia.
--
-- CONTRAPARTIDA DECLARADA: `persona_seudonimo` **es dato personal mientras existe**.
-- Entra en la matriz, en el procedimiento de supresión y en el alcance del job. Se ha
-- cambiado un riesgo difuso (el identificador esparcido por exports en varios discos)
-- por uno concentrado y gobernado (una tabla, un borrado).

BEGIN;

DO $s296_preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
        RAISE EXCEPTION 's296: aplica ANTES 20260803140000_s295_rgpd_rol_retencion_v2.sql';
    END IF;
END
$s296_preflight$;

-- ---------------------------------------------------------------------------
-- 1. La correspondencia persona ↔ código
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.persona_seudonimo (
    telegram_user_id BIGINT PRIMARY KEY,
    seudonimo        UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.persona_seudonimo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.persona_seudonimo FORCE  ROW LEVEL SECURITY;

-- REVOKE explícito, como en las otras cinco tablas de datos personales. NO es redundante
-- con la RLS: Supabase aplica `ALTER DEFAULT PRIVILEGES ... GRANT ALL ... TO anon,
-- authenticated` sobre `public`, así que una tabla nueva NACE con privilegios para roles
-- anónimos. La RLS lo tapa hoy, pero el patrón del repo es REVOKE **y** RLS — y esta es
-- precisamente la tabla que vincula el código con la persona.
REVOKE ALL PRIVILEGES ON TABLE public.persona_seudonimo
    FROM PUBLIC, anon, authenticated, service_role;

-- El bot necesita EMITIR el código (primera vez que alguien usa el bot) y LEERLO. No
-- necesita borrarlo ni cambiarlo: un código que cambia deja de agrupar.
GRANT SELECT, INSERT ON TABLE public.persona_seudonimo TO service_role;

-- El rol de retención lee el código para estamparlo, y BORRA la correspondencia — ese
-- borrado es el punto de no retorno.
GRANT SELECT, DELETE ON TABLE public.persona_seudonimo TO rgpd_retencion;

-- Y puede EMITIR el que falte. Sin esto, alguien sin código (la emisión en `/accept` es
-- fail-open: si falla, el técnico entra igual) quedaría FUERA de la retención para
-- siempre — el `UPDATE ... FROM persona_seudonimo` no casaría sus filas, conservaría su
-- identificador, y el recibo diría «0 tocadas» sin que nada chirriara. Es la clase de
-- fallo «aparenta cumplimiento» otra vez, y la destapó el test contra Postgres real.
-- Emitir un código es inocuo: es un UUID aleatorio.
GRANT INSERT (telegram_user_id) ON TABLE public.persona_seudonimo TO rgpd_retencion;

-- Sin política no vería nada (el rol es NOBYPASSRLS).
-- TRES políticas y no una: la ventana acota SOLO el borrado.
--
-- Con una sola `FOR ALL` acotada por fecha, el `USING` se reutiliza como comprobación de
-- INSERT y el job no podía ni emitir un código (el recién creado tiene `created_at = now()`
-- y no pasa la ventana). Y con una sola `USING (true)`, el job borraba el vínculo de quien
-- acaba de hacer `/accept` y aún no ha preguntado. Leer y emitir siempre; DESTRUIR solo lo
-- que ya venció.
DROP POLICY IF EXISTS rgpd_retencion_correspondencia ON public.persona_seudonimo;
DROP POLICY IF EXISTS rgpd_retencion_correspondencia_lee ON public.persona_seudonimo;
DROP POLICY IF EXISTS rgpd_retencion_correspondencia_emite ON public.persona_seudonimo;
DROP POLICY IF EXISTS rgpd_retencion_correspondencia_destruye ON public.persona_seudonimo;

CREATE POLICY rgpd_retencion_correspondencia_lee ON public.persona_seudonimo
    FOR SELECT TO rgpd_retencion USING (true);

CREATE POLICY rgpd_retencion_correspondencia_emite ON public.persona_seudonimo
    FOR INSERT TO rgpd_retencion WITH CHECK (true);

CREATE POLICY rgpd_retencion_correspondencia_destruye ON public.persona_seudonimo
    FOR DELETE TO rgpd_retencion USING (true);
-- SIN ventana, y a conciencia. Se intentó acotar por `created_at` y era el criterio
-- equivocado: esa fecha dice cuándo se EMITIÓ el código, no cuándo vencen los datos, así
-- que un código emitido por el propio job no podría borrarse nunca.
--
-- Lo que de verdad protege es `rgpd_quedan_identificados()`: solo se destruye el vínculo de
-- quien no tiene NINGUNA fila identificada. El caso que preocupaba —alguien que hizo
-- `/accept` y aún no ha preguntado— resulta ser BENIGNO: no tiene datos, así que su código
-- no agrupa nada; si luego pregunta, recibe uno nuevo y su corpus entero queda bajo ese.
-- No hay nada que partir. Declarado en vez de «arreglado» con un criterio que no aplica.

-- BACKFILL: quien ya usaba el bot antes de esta migración necesita su código igual. Si no,
-- su histórico sería el único que llegaría a los 24 meses sin nada que lo agrupe — que es
-- justo el caso que Alberto quiere evitar, y encima con los técnicos más antiguos.
INSERT INTO public.persona_seudonimo (telegram_user_id)
SELECT DISTINCT telegram_user_id FROM public.query_logs WHERE telegram_user_id IS NOT NULL
UNION
SELECT DISTINCT telegram_user_id FROM public.feedback WHERE telegram_user_id IS NOT NULL
UNION
SELECT DISTINCT telegram_user_id FROM public.answer_feedback WHERE telegram_user_id IS NOT NULL
UNION
SELECT DISTINCT telegram_user_id FROM public.user_consent WHERE telegram_user_id IS NOT NULL
ON CONFLICT (telegram_user_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 1.b «¿le queda algo identificado a esta persona?» — la pregunta que el rol NO puede
--     responder por sí mismo
-- ---------------------------------------------------------------------------
-- El vínculo solo debe destruirse cuando a esa persona no le queda ninguna fila
-- identificada. Pero el rol es NOBYPASSRLS y su política solo le enseña las filas
-- VENCIDAS: preguntándole a él, las recientes «no existen» y destruiría el vínculo de
-- alguien que todavía tiene datos suyos identificados. Consecuencia: cuando esas filas
-- venciesen, habría que emitirle un código NUEVO — y el corpus del técnico quedaría
-- partido en dos, que es exactamente lo que el diseño existe para evitar.
--
-- (Lo destapó el test contra Postgres real. Leyendo el SQL la consulta parece correcta:
-- lo que falla es que se ejecuta con una visibilidad recortada.)
--
-- Se resuelve con una función acotada que responde SOLO esa pregunta —un booleano, ninguna
-- fila— y que corre con los privilegios de su dueño para poder ver el conjunto completo.
CREATE OR REPLACE FUNCTION public.rgpd_quedan_identificados(p_user BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT EXISTS (SELECT 1 FROM public.query_logs      WHERE telegram_user_id = p_user)
        OR EXISTS (SELECT 1 FROM public.feedback        WHERE telegram_user_id = p_user)
        OR EXISTS (SELECT 1 FROM public.answer_feedback WHERE telegram_user_id = p_user);
$$;

-- `user_consent` queda FUERA de la pregunta a propósito: su plazo es una decisión aparte
-- (pendiente en la matriz) y, si contase, el vínculo no se destruiría jamás — la prueba
-- del consentimiento se conserva, así que la condición nunca se cumpliría. Se declara la
-- consecuencia: tras la retención puede quedar una fila de consentimiento con el
-- identificador, aunque el resto ya esté disociado.

REVOKE ALL ON FUNCTION public.rgpd_quedan_identificados(BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.rgpd_quedan_identificados(BIGINT) TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 2. Dónde aterriza el código en los registros
-- ---------------------------------------------------------------------------
-- Columna aparte, no reutilizar `telegram_user_id`: son tipos distintos y, sobre todo,
-- significados distintos — uno identifica a una persona, el otro solo agrupa filas.
ALTER TABLE public.query_logs      ADD COLUMN IF NOT EXISTS seudonimo UUID;
ALTER TABLE public.feedback        ADD COLUMN IF NOT EXISTS seudonimo UUID;
ALTER TABLE public.answer_feedback ADD COLUMN IF NOT EXISTS seudonimo UUID;

CREATE INDEX IF NOT EXISTS idx_query_logs_seudonimo ON public.query_logs (seudonimo);

-- El rol de retención escribe el código donde antes ponía NULL.
GRANT SELECT (seudonimo), UPDATE (seudonimo) ON public.query_logs      TO rgpd_retencion;
GRANT SELECT (seudonimo), UPDATE (seudonimo) ON public.feedback        TO rgpd_retencion;
GRANT SELECT (seudonimo), UPDATE (seudonimo) ON public.answer_feedback TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 3. `user_consent` APPEND-ONLY: una fila por (persona, versión), con su fecha
-- ---------------------------------------------------------------------------
-- Antes: PK sobre `telegram_user_id` + upsert ⇒ la aceptación nueva MACHACABA la
-- anterior, y con ella la prueba de que esa persona aceptó la versión de entonces.
DO $s296_consent$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='user_consent' AND column_name='id'
    ) THEN
        ALTER TABLE public.user_consent ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid();
        ALTER TABLE public.user_consent DROP CONSTRAINT IF EXISTS user_consent_pkey;
        ALTER TABLE public.user_consent ADD PRIMARY KEY (id);
    END IF;
END
$s296_consent$;

-- Una aceptación por persona y versión. Re-aceptar la MISMA versión refresca su fila
-- (no crea duplicados); aceptar una versión NUEVA deja la anterior intacta como prueba.
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_consent_persona_version
    ON public.user_consent (telegram_user_id, terms_version);

-- ---------------------------------------------------------------------------
-- 4. El enlace que le faltaba a `feedback`
-- ---------------------------------------------------------------------------
-- La tabla guardaba COPIAS del texto de la pregunta y la respuesta, sin referencia a
-- ellas, así que no podía cascadear. Se añade el enlace y se rellena en las escrituras
-- NUEVAS; las filas antiguas quedan huérfanas y así se declara en la matriz (no se
-- pueden emparejar a posteriori: solo tienen texto).
ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS query_log_id UUID REFERENCES public.query_logs(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_feedback_query_log ON public.feedback (query_log_id);

-- No hace falta GRANT: `service_role` ya tiene INSERT de TABLA sobre `feedback`
-- (`supabase_schema.sql`), que cubre cualquier columna nueva. Un `GRANT INSERT (columna)`
-- aquí sería un no-op decorativo, y un no-op decorativo en una migración de privilegios
-- es peor que nada: parece que protege algo.

-- ---------------------------------------------------------------------------
-- 5. La marca de UTILIDAD — para reconocer calidad, no cantidad
-- ---------------------------------------------------------------------------
-- Decisión de Alberto: podrá haber un bonus para quien aporte feedback valioso, y se
-- basará en CALIDAD. Un contador de votos o de comentarios se infla en una tarde; lo que
-- no se infla es feedback que LLEVÓ A ALGO. Por eso la marca la pone una PERSONA al
-- revisar, después del hecho, y no la calcula el sistema.
ALTER TABLE public.answer_feedback
    ADD COLUMN IF NOT EXISTS utilidad TEXT,
    ADD COLUMN IF NOT EXISTS utilidad_revisada_at TIMESTAMPTZ;

DO $s296_utilidad_check$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'answer_feedback_utilidad_check'
           AND conrelid = 'public.answer_feedback'::regclass
    ) THEN
        ALTER TABLE public.answer_feedback
            ADD CONSTRAINT answer_feedback_utilidad_check
            CHECK (utilidad IS NULL OR utilidad IN (
                'corrigio',   -- destapó un fallo real que se corrigió
                'gold',       -- produjo un caso de evaluación
                'corpus',     -- señaló un manual o contenido que no teníamos
                'ninguna'     -- revisado y sin consecuencia
            ));
    END IF;
END
$s296_utilidad_check$;

-- ---------------------------------------------------------------------------
-- 5.b LA PIEZA LOAD-BEARING: el bot NO puede escribir la marca
-- ---------------------------------------------------------------------------
-- `service_role` es la identidad del proceso con el que habla el técnico. Si pudiera
-- escribir `utilidad`, el dato que reparte dinero sería escribible desde el mismo canal
-- que el interesado toca. Se sustituye su UPDATE de TABLA por UPDATE de COLUMNA sobre
-- exactamente lo que el voto necesita.
--
-- Esto ENDURECE la postura de julio, no la relaja: se quita un privilegio, no se añade.
REVOKE UPDATE ON TABLE public.answer_feedback FROM service_role;
GRANT UPDATE (telegram_user_id, query_log_id, verdict, comment, reason_class)
    ON public.answer_feedback TO service_role;

-- ---------------------------------------------------------------------------
-- 6. Postcondiciones
-- ---------------------------------------------------------------------------
DO $s296_post$
DECLARE
    tabla TEXT;
BEGIN
    -- 6.1 El bot puede emitir y leer códigos, pero no cambiarlos ni borrarlos: un código
    --     que cambia deja de agrupar, que es justo lo que se quiere conservar.
    IF NOT has_table_privilege('service_role', 'public.persona_seudonimo', 'INSERT')
       OR NOT has_table_privilege('service_role', 'public.persona_seudonimo', 'SELECT') THEN
        RAISE EXCEPTION 's296: service_role no puede emitir/leer seudonimos';
    END IF;
    IF has_table_privilege('service_role', 'public.persona_seudonimo', 'UPDATE')
       OR has_table_privilege('service_role', 'public.persona_seudonimo', 'DELETE')
       OR has_any_column_privilege('service_role', 'public.persona_seudonimo', 'UPDATE') THEN
        RAISE EXCEPTION 's296: service_role no debe poder cambiar ni borrar un seudonimo';
    END IF;

    -- 6.1.b Ningun rol anonimo toca la tabla del vinculo.
    FOREACH tabla IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF has_table_privilege(tabla, 'public.persona_seudonimo', 'SELECT')
           OR has_table_privilege(tabla, 'public.persona_seudonimo', 'INSERT')
           OR has_table_privilege(tabla, 'public.persona_seudonimo', 'UPDATE')
           OR has_table_privilege(tabla, 'public.persona_seudonimo', 'DELETE')
           OR has_any_column_privilege(tabla, 'public.persona_seudonimo', 'SELECT') THEN
            RAISE EXCEPTION 's296: % tiene privilegios sobre persona_seudonimo', tabla;
        END IF;
    END LOOP;

    -- 6.1.c Las tres politicas separadas: leer, emitir y destruir son operaciones
    -- distintas y colapsarlas en una `FOR ALL` rompio el mecanismo una vez.
    FOREACH tabla IN ARRAY ARRAY['rgpd_retencion_correspondencia_lee',
                                 'rgpd_retencion_correspondencia_emite',
                                 'rgpd_retencion_correspondencia_destruye'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
             WHERE schemaname='public' AND tablename='persona_seudonimo' AND policyname=tabla
        ) THEN
            RAISE EXCEPTION 's296: falta la politica %', tabla;
        END IF;
    END LOOP;

    -- 6.2 El rol de retencion puede estampar el codigo y destruir la correspondencia.
    FOREACH tabla IN ARRAY ARRAY['query_logs', 'feedback', 'answer_feedback'] LOOP
        IF NOT has_column_privilege('rgpd_retencion', format('public.%I', tabla),
                                    'seudonimo', 'UPDATE') THEN
            RAISE EXCEPTION 's296: rgpd_retencion no puede estampar el seudonimo en %', tabla;
        END IF;
    END LOOP;
    IF NOT has_table_privilege('rgpd_retencion', 'public.persona_seudonimo', 'DELETE') THEN
        RAISE EXCEPTION 's296: rgpd_retencion no puede destruir la correspondencia';
    END IF;

    -- 6.3 LA MARCA DE UTILIDAD NO ES ESCRIBIBLE POR EL BOT.
    IF has_table_privilege('service_role', 'public.answer_feedback', 'UPDATE') THEN
        RAISE EXCEPTION 's296: service_role conserva UPDATE de TABLA en answer_feedback; '
                        'la marca de utilidad quedaria a su alcance';
    END IF;
    IF has_column_privilege('service_role', 'public.answer_feedback', 'utilidad', 'UPDATE')
       OR has_column_privilege('service_role', 'public.answer_feedback',
                               'utilidad_revisada_at', 'UPDATE') THEN
        RAISE EXCEPTION 's296: service_role NO debe poder escribir la marca de utilidad -- '
                        'es el dato en que se basa un bonus, y el interesado habla por ese canal';
    END IF;
    -- ...pero el voto tiene que seguir funcionando (upsert 👍->👎).
    IF NOT has_column_privilege('service_role', 'public.answer_feedback', 'verdict', 'UPDATE')
       OR NOT has_column_privilege('service_role', 'public.answer_feedback',
                                   'comment', 'UPDATE') THEN
        RAISE EXCEPTION 's296: se ha roto el upsert del voto';
    END IF;

    -- 6.4 `user_consent` conserva una fila por (persona, version).
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname='public' AND tablename='user_consent'
           AND indexname='idx_user_consent_persona_version'
    ) THEN
        RAISE EXCEPTION 's296: falta el unico (persona, version) en user_consent';
    END IF;

    -- 6.5 `feedback` ya puede cascadear.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='feedback' AND column_name='query_log_id'
    ) THEN
        RAISE EXCEPTION 's296: feedback sigue sin enlace a query_logs';
    END IF;
END
$s296_post$;

COMMIT;

-- ---------------------------------------------------------------------------
-- CAMBIO ACOMPAÑANTE OBLIGATORIO EN `supabase_schema.sql` (bootstrap)
-- ---------------------------------------------------------------------------
-- ⚠️ SIN ESTO, LA PIEZA 5.b SE DESHACE SOLA. El bootstrap está escrito para re-ejecutarse
-- y hace:
--     REVOKE ALL … FROM service_role
--     GRANT SELECT, INSERT, UPDATE ON TABLE public.answer_feedback TO service_role
-- con una postcondición de IGUALDAD EXACTA (`expected = ['SELECT','INSERT','UPDATE']`).
-- Re-correrlo devuelve a `service_role` el UPDATE de TABLA, le quita los grants de columna,
-- y **la marca de utilidad vuelve a ser escribible desde el canal por el que habla el
-- interesado** — sin que nada falle ni avise. Un entorno nuevo nacería igual.
--
-- Al aplicar esta propuesta hay que, en `supabase_schema.sql`:
--   1. Sustituir el GRANT de tabla por el de columna:
--        EXECUTE 'GRANT SELECT, INSERT ON TABLE public.answer_feedback TO service_role';
--        EXECUTE 'GRANT UPDATE (telegram_user_id, query_log_id, verdict, comment, '
--                'reason_class) ON public.answer_feedback TO service_role';
--   2. Ajustar `expected_service_privileges` de `answer_feedback` a ['SELECT','INSERT'] y
--      añadir la comprobación de que NO tiene UPDATE de columna sobre `utilidad`.
--   3. Replicar el bloque de `persona_seudonimo` (tabla + REVOKE + RLS + política + grants)
--      y las columnas nuevas, para que un bootstrap limpio quede completo.
--
-- NO se modifica aquí, por lo mismo que en s295: hacerlo antes de aplicar crearía la
-- divergencia inversa (bootstrap con privilegios que producción no tiene). Los dos cambios
-- van juntos o no van.

-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   GRANT UPDATE ON TABLE public.answer_feedback TO service_role;   -- restaura s286
--   ALTER TABLE public.answer_feedback DROP COLUMN utilidad, DROP COLUMN utilidad_revisada_at;
--   ALTER TABLE public.feedback DROP COLUMN query_log_id;
--   DROP INDEX IF EXISTS public.idx_user_consent_persona_version;
--   ALTER TABLE public.query_logs DROP COLUMN seudonimo;            -- x3 tablas
--   DROP TABLE public.persona_seudonimo;
--
-- Reversible MIENTRAS no se haya ejecutado la retención. Después no: los seudónimos
-- estampados serían lo único que agrupa las filas ya disociadas, y las correspondencias
-- borradas no se pueden reconstruir. Declarado, no escondido.
