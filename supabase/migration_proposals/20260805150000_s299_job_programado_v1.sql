-- ============================================================================
-- APLICADA EN PRODUCCIÓN el 5-ago-2026 (Alberto, SQL Editor; verificada contra el
-- catálogo: job mensual ACTIVO a nombre de postgres, oráculo cerrado para los 3 roles de
-- la API, recibos blindados, y dry-run del driver con exit 0). IDEMPOTENTE: re-ejecutarla
-- es seguro y no-opea/re-afirma (el `cron.schedule` con el mismo nombre ACTUALIZA el job,
-- no lo duplica). Orden de la cola: s295 → s296 → s297 → s299. En un entorno nuevo se
-- aplica tras el bootstrap.
-- ============================================================================
-- s299 — decisión de Alberto (5-ago): PROGRAMAR la retención. Dos piezas que van juntas:
--
--   1. UNA SOLA IMPLEMENTACIÓN DE LA PASADA. Hasta ahora la pasada vivía en Python
--      (`scripts/rgpd_retencion.py`). Programarla en pg_cron exigiría duplicarla en SQL —
--      y dos implementaciones de una operación IRREVERSIBLE driftan: la próxima tabla con
--      identificador se añade en una y se olvida en la otra, y una de las dos «cumple»
--      sin cumplir. Se mueve la pasada a `public.rgpd_retencion_pasada()` y el script
--      pasa a ser un driver fino de ESTA función: manual y programado ejecutan
--      exactamente el mismo código.
--
--   2. EL RELOJ DENTRO DE LA BASE (pg_cron). La alternativa —un cron en GitHub Actions o
--      en Railway— exige guardar fuera un `DATABASE_URL` de operador, MÁS potente que el
--      `service_role` que s295 evitó tocar a propósito. Con pg_cron ninguna credencial
--      sale de la base: el scheduler corre dentro de Postgres, el job lo ejecuta el rol
--      que lo programó (`postgres`), y la función asume `rgpd_retencion` en la entrada
--      (`SET role` a nivel de función) ⇒ la ventana de 24 meses sigue siendo un
--      invariante del MOTOR también en la ejecución programada.
--
-- ---------------------------------------------------------------------------
-- POR QUÉ LA FUNCIÓN NO REPITE LA VENTANA
-- ---------------------------------------------------------------------------
-- Las sentencias de la pasada NO llevan `created_at < corte`: la ventana la imponen las
-- políticas RLS del rol (s295) y SOLO ellas. Repetir el predicado aquí sería volver a
-- tener dos implementaciones del plazo — justo la clase de drift que esta migración
-- elimina. El `corte` que la función calcula es INFORMATIVO (va al recibo con la misma
-- expresión que usan las políticas); si divergiera, mandaría la política.
--
-- El check de `current_user` dentro del cuerpo es el cinturón del tirante: si una edición
-- futura quitara el `SET role` del encabezado, la función abortaría en vez de correr con
-- los privilegios del operador (owner + BYPASSRLS), que es el fallo más grave posible
-- aquí y sería silencioso. Misma lección que el `SELECT current_user` del script (s295).
--
-- NO es SECURITY DEFINER a propósito: `SET role` + SECURITY DEFINER es una combinación
-- con historial de CVE, y no hace falta — quien puede EJECUTARLA (solo el operador) ya
-- tiene membresía SET en el rol. Dos capas independientes: sin EXECUTE no se entra, y
-- sin membresía el `SET role` de la entrada falla.
--
-- ---------------------------------------------------------------------------
-- RECIBOS EN LA BASE, NO SOLO EN STDOUT
-- ---------------------------------------------------------------------------
-- Una ejecución programada no tiene a nadie mirando stdout. Cada pasada CONFIRMADA deja
-- una fila en `public.rgpd_recibos` (origen, corte, resultado por tabla con ids tocados).
-- Se escribe DENTRO de la misma transacción de la pasada: en un dry-run (el script
-- ejecuta y revierte) el recibo se revierte con todo lo demás — no hace falta columna
-- «aplicado». ALCANCE HONESTO de esa garantía (ronda 2 del dúo): vale para el BOT y los
-- roles de la API, no contra el operador — `postgres` es owner (+ puede asumir el rol
-- con su INSERT) y siempre podría fabricar una fila; lo estructural es que el bot no
-- puede, y que el dry-run no deja rastro.
-- Los ids registrados son UUIDs de FILA; la entrada de `persona_seudonimo` registra solo
-- el CONTEO, porque ahí el id ES la persona. PRECISIÓN (ronda 2): mientras viva la
-- correspondencia de esa persona, uuid → fila → seudónimo → persona sigue siendo un
-- camino: el recibo es dato SEUDONIMIZADO, no evidencia impersonal — solo lectura del
-- operador, y su plazo entra en el mismo [DECIDIR] que `user_consent` (matriz).
--
-- GAP DECLARADO (CI): el contenedor `postgres:17` del workflow no trae pg_cron, así que
-- el bloque de programación corre solo su rama WARNING en CI. La FUNCIÓN — la parte que
-- hace el trabajo irreversible — sí se ejerce entera contra Postgres real, y el fixture
-- reproduce los default privileges de Supabase TAMBIÉN para funciones (verificados
-- contra `pg_default_acl` de producción el 5-ago: toda función nueva de `public` nace
-- ejecutable por anon/authenticated/service_role — por eso los REVOKE de aquí son
-- NOMINALES, no solo PUBLIC). La postcondición 4.4 hace imposible el fallo silencioso
-- en producción: si pg_cron está disponible (verificado en el proyecto: 1.6.4), el job
-- DEBE quedar programado, activo y a nombre de un rol que pueda asumir el de retención,
-- o la migración revienta. Tras aplicar: verificar `SELECT * FROM cron.job` y el primer
-- recibo mensual.

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Precondiciones: exige la cola s295 → s296 → s297 completa
-- ---------------------------------------------------------------------------
DO $s299_preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
        RAISE EXCEPTION 's299: aplica ANTES 20260803140000_s295_rgpd_rol_retencion_v2.sql';
    END IF;
    IF to_regclass('public.persona_seudonimo') IS NULL
       OR to_regprocedure('public.rgpd_quedan_identificados(bigint)') IS NULL THEN
        RAISE EXCEPTION 's299: aplica ANTES 20260804120000_s296_seudonimo_y_calidad_v1.sql';
    END IF;
    IF to_regclass('public.consent_events') IS NULL THEN
        RAISE EXCEPTION 's299: aplica ANTES 20260805120000_s297_ledger_consentimiento_v1.sql';
    END IF;
END
$s299_preflight$;

-- ---------------------------------------------------------------------------
-- 1. Los recibos
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.rgpd_recibos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ejecutado_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    origen       TEXT NOT NULL CHECK (origen IN ('manual', 'cron')),
    corte        TIMESTAMPTZ NOT NULL,
    resultado    JSONB NOT NULL
);

ALTER TABLE public.rgpd_recibos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rgpd_recibos FORCE  ROW LEVEL SECURITY;

-- Mismo patrón que el resto de la cola: REVOKE **y** RLS (Supabase concede TODO por
-- defecto a anon/authenticated sobre las tablas nuevas de `public`). El bot NO pinta
-- nada aquí: los recibos son evidencia de operación, no datos de la aplicación.
REVOKE ALL PRIVILEGES ON TABLE public.rgpd_recibos
    FROM PUBLIC, anon, authenticated, service_role;

-- El rol de retención SOLO inserta. Ni lee, ni corrige, ni borra: un recibo que se puede
-- editar no es un recibo. La lectura es del operador (owner).
GRANT INSERT ON TABLE public.rgpd_recibos TO rgpd_retencion;

DROP POLICY IF EXISTS rgpd_recibos_inserta ON public.rgpd_recibos;
CREATE POLICY rgpd_recibos_inserta ON public.rgpd_recibos
    FOR INSERT TO rgpd_retencion WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 1.b «¿le queda algo identificado?» aprende la 4ª tabla — y deja de ser oráculo público
-- ---------------------------------------------------------------------------
-- Dos hallazgos del dúo (s299) sobre la función de s296:
--
--   (a) NO miraba `answer_messages`. Un ancla RECIENTE colgada de una consulta ya
--       vencida sobrevive a la pasada (la ventana RLS no deja borrarla) llevando
--       `telegram_chat_id` — que en chat privado ES la persona. Con la versión de 3
--       tablas, el vínculo se destruía con esa fila identificada AÚN VIVA: la cadena
--       chat_id → query_log_id → seudónimo re-identificaba el corpus recién disociado.
--       El punto de no retorno llegaba ANTES de tiempo — exactamente lo que esta
--       función existe para impedir.
--   (b) En producción era EJECUTABLE por anon/authenticated/service_role (VERIFICADO
--       contra el catálogo vivo el 5-ago-2026): Supabase concede EXECUTE por default
--       privileges a toda función nueva de `public`, y s296 solo revocó PUBLIC — un
--       ORÁCULO de pertenencia («¿este telegram_user_id tiene datos?») expuesto por
--       PostgREST RPC con la clave anónima, y encima SECURITY DEFINER. Se revoca
--       NOMINAL, como ya hacía el precedente s277 del repo.
--
-- `user_consent`/`consent_events` siguen FUERA a propósito (decisión s296: su plazo es
-- decisión aparte y, si contasen, el vínculo no se destruiría jamás).
CREATE OR REPLACE FUNCTION public.rgpd_quedan_identificados(p_user BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT EXISTS (SELECT 1 FROM public.query_logs      WHERE telegram_user_id = p_user)
        OR EXISTS (SELECT 1 FROM public.feedback        WHERE telegram_user_id = p_user)
        OR EXISTS (SELECT 1 FROM public.answer_feedback WHERE telegram_user_id = p_user)
        -- s299(a): el ancla lleva chat_id == user_id en chat privado. En grupo el
        -- chat_id es el grupo y no casa con la persona: declarado, no disimulado.
        OR EXISTS (SELECT 1 FROM public.answer_messages WHERE telegram_chat_id = p_user);
$$;

REVOKE ALL ON FUNCTION public.rgpd_quedan_identificados(BIGINT)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.rgpd_quedan_identificados(BIGINT) TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 2. LA pasada — la única implementación
-- ---------------------------------------------------------------------------
-- `p_origen` SIN default (dúo s299): un `SELECT rgpd_retencion_pasada()` suelto en el
-- SQL Editor estamparía `origen='cron'` falso en un recibo inmutable. El origen se
-- declara SIEMPRE: el reloj pasa 'cron', el driver pasa 'manual'.
CREATE OR REPLACE FUNCTION public.rgpd_retencion_pasada(p_origen TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SET role = rgpd_retencion
SET search_path = public, pg_temp
AS $rgpd_pasada$
DECLARE
    -- INFORMATIVO (va al recibo). La ventana REAL la imponen las políticas RLS del rol:
    -- esta expresión es la MISMA que la de las políticas para que el recibo no mienta,
    -- pero si divergieran, manda la política.
    v_corte     TIMESTAMPTZ := now() - interval '24 months';
    v_ids       TEXT[];
    v_conteo    INTEGER;
    v_resultado JSONB := '{}'::jsonb;
BEGIN
    -- El cinturón del tirante (ver cabecera): si el `SET role` del encabezado
    -- desapareciera, esto corta ANTES de tocar nada.
    IF current_user <> 'rgpd_retencion' THEN
        RAISE EXCEPTION 'rgpd: la pasada debe correr como rgpd_retencion y corre como %. '
                        'Sin el rol asumido, la ventana de 24 meses no la garantiza nadie. '
                        'Abortado sin tocar nada.', current_user;
    END IF;

    -- Segunda capa SIN duplicar la ventana (dúo s299): correr como el rol no basta si
    -- las políticas están DESARMADAS (un `DISABLE ROW LEVEL SECURITY` de debug entre
    -- re-afirmaciones del bootstrap) — y el reloj mensual corre DESATENDIDO: disociaría
    -- filas de ayer y vaciaría `answer_messages` entera, con un recibo de aspecto
    -- normal. Se aserta el MECANISMO (RLS forzada + política presente en las 4 tablas),
    -- no el plazo: la ventana sigue teniendo UNA sola fuente.
    IF EXISTS (
        SELECT 1
          FROM unnest(ARRAY['query_logs', 'feedback', 'answer_feedback',
                            'answer_messages']) AS t(tabla)
         WHERE NOT EXISTS (
                   SELECT 1 FROM pg_class c
                    WHERE c.oid = to_regclass(format('public.%I', t.tabla))
                      AND c.relrowsecurity AND c.relforcerowsecurity
               )
            -- EXACTAMENTE UNA política alcanza al rol (ronda 2 del dúo): las permisivas
            -- se OR-ean — una segunda de debug (`USING (true)`, al rol o a PUBLIC)
            -- abriría la ventana con la aserción en verde y recibo de aspecto normal.
            OR (SELECT count(*) FROM pg_policies p
                 WHERE p.schemaname = 'public' AND p.tablename = t.tabla
                   AND ('rgpd_retencion' = ANY(p.roles) OR 'public' = ANY(p.roles))) <> 1
            -- ...y es LA de la ventana, con el predicado que s295 instaló. Mismo listón
            -- que la postcondición 6.6 de s295 (Postgres normaliza `24 months` a
            -- `2 years`): VERIFICACIÓN de la única fuente, no una segunda fuente.
            OR NOT EXISTS (
                   SELECT 1 FROM pg_policies p
                    WHERE p.schemaname = 'public' AND p.tablename = t.tabla
                      AND p.policyname = 'rgpd_retencion_ventana'
                      AND 'rgpd_retencion' = ANY(p.roles)
                      AND p.qual LIKE '%created_at%'
                      AND (p.qual LIKE '%2 years%' OR p.qual LIKE '%24 mons%')
               )
    ) THEN
        RAISE EXCEPTION 'rgpd: la ventana NO esta armada en alguna de las 4 tablas (RLS '
                        'deshabilitada, politica ausente o alterada, o una politica '
                        'EXTRA alcanza al rol). Pasada abortada sin tocar nada.';
    END IF;

    -- Primero, EMITIR el código que falte (la emisión en /accept es fail-open): sin
    -- código, el UPDATE...FROM no casaría esas filas y conservarían el identificador
    -- PARA SIEMPRE con un recibo diciendo «0 tocadas». La RLS solo enseña filas vencidas
    -- a este rol, así que esto alcanza exactamente a quien toca.
    INSERT INTO public.persona_seudonimo (telegram_user_id)
    SELECT DISTINCT telegram_user_id FROM public.query_logs
     WHERE telegram_user_id IS NOT NULL
    ON CONFLICT (telegram_user_id) DO NOTHING;
    INSERT INTO public.persona_seudonimo (telegram_user_id)
    SELECT DISTINCT telegram_user_id FROM public.feedback
     WHERE telegram_user_id IS NOT NULL
    ON CONFLICT (telegram_user_id) DO NOTHING;
    INSERT INTO public.persona_seudonimo (telegram_user_id)
    SELECT DISTINCT telegram_user_id FROM public.answer_feedback
     WHERE telegram_user_id IS NOT NULL
    ON CONFLICT (telegram_user_id) DO NOTHING;

    -- El ciclo completo, no solo la tabla padre (las hijas se unen por query_log_id y el
    -- CASCADE solo actúa al BORRAR). s296: se ESTAMPA el seudónimo y se retira el
    -- identificador EN LA MISMA SENTENCIA — separarlos dejaría una ventana sin lo uno ni
    -- lo otro.
    WITH tocadas AS (
        UPDATE public.query_logs AS t
           SET seudonimo = p.seudonimo, telegram_user_id = NULL
          FROM public.persona_seudonimo AS p
         WHERE p.telegram_user_id = t.telegram_user_id
           AND t.telegram_user_id IS NOT NULL
        RETURNING t.id
    )
    SELECT COALESCE(array_agg(id::text), '{}') INTO v_ids FROM tocadas;
    v_resultado := v_resultado || jsonb_build_object('query_logs', jsonb_build_object(
        'modo', 'nulificar', 'tocadas', COALESCE(array_length(v_ids, 1), 0),
        'ids', to_jsonb(v_ids)));

    WITH tocadas AS (
        UPDATE public.feedback AS t
           SET seudonimo = p.seudonimo, telegram_user_id = NULL
          FROM public.persona_seudonimo AS p
         WHERE p.telegram_user_id = t.telegram_user_id
           AND t.telegram_user_id IS NOT NULL
        RETURNING t.id
    )
    SELECT COALESCE(array_agg(id::text), '{}') INTO v_ids FROM tocadas;
    v_resultado := v_resultado || jsonb_build_object('feedback', jsonb_build_object(
        'modo', 'nulificar', 'tocadas', COALESCE(array_length(v_ids, 1), 0),
        'ids', to_jsonb(v_ids)));

    WITH tocadas AS (
        UPDATE public.answer_feedback AS t
           SET seudonimo = p.seudonimo, telegram_user_id = NULL
          FROM public.persona_seudonimo AS p
         WHERE p.telegram_user_id = t.telegram_user_id
           AND t.telegram_user_id IS NOT NULL
        RETURNING t.id
    )
    SELECT COALESCE(array_agg(id::text), '{}') INTO v_ids FROM tocadas;
    v_resultado := v_resultado || jsonb_build_object('answer_feedback', jsonb_build_object(
        'modo', 'nulificar', 'tocadas', COALESCE(array_length(v_ids, 1), 0),
        'ids', to_jsonb(v_ids)));

    -- Mapeo operativo mensaje→consulta: a 24 meses su valor analítico es CERO y carga
    -- `telegram_chat_id` (== user_id en chat privado) ⇒ se borra, no se disocia.
    WITH borradas AS (
        DELETE FROM public.answer_messages RETURNING id
    )
    SELECT COALESCE(array_agg(id::text), '{}') INTO v_ids FROM borradas;
    v_resultado := v_resultado || jsonb_build_object('answer_messages', jsonb_build_object(
        'modo', 'borrar', 'tocadas', COALESCE(array_length(v_ids, 1), 0),
        'ids', to_jsonb(v_ids)));

    -- EL PUNTO DE NO RETORNO, el último a propósito: mientras la correspondencia existe,
    -- todo lo anterior es reversible. Solo se destruye el vínculo de quien no tiene
    -- NINGUNA fila identificada — y la pregunta la responde
    -- `rgpd_quedan_identificados()` (SECURITY DEFINER, visibilidad completa), porque a
    -- este rol la RLS solo le enseña filas vencidas y un NOT EXISTS desde aquí
    -- destruiría vínculos de gente con filas RECIENTES, partiendo su corpus en dos.
    -- CARRERA DECLARADA (ronda 2 del dúo, READ COMMITTED): una consulta que se confirme
    -- en el instante exacto de esta sentencia puede llegar DESPUÉS del snapshot del
    -- oráculo y el vínculo destruirse igual. Consecuencia: el mismo «corpus en dos
    -- códigos» del que vuelve tras la destrucción — límite YA declarado en s296, no una
    -- re-identificación — y la emisión de códigos de la siguiente pasada lo recoge. A
    -- esta escala (pasada mensual, minutos de duración en ms) es ~0; si la escala sube,
    -- la pasada debe subir a SERIALIZABLE con retry (anotado en TECH_DEBT).
    WITH destruidas AS (
        DELETE FROM public.persona_seudonimo p
         WHERE NOT public.rgpd_quedan_identificados(p.telegram_user_id)
        RETURNING 1
    )
    SELECT count(*) INTO v_conteo FROM destruidas;
    v_resultado := v_resultado || jsonb_build_object('persona_seudonimo', jsonb_build_object(
        'modo', 'destruir_vinculo', 'tocadas', v_conteo,
        'ids', '[]'::jsonb));      -- el id ES la persona: NO se registra

    -- El recibo, en la MISMA transacción: si la pasada se revierte (dry-run del script),
    -- el recibo se revierte con ella ⇒ toda fila persistida = pasada confirmada.
    INSERT INTO public.rgpd_recibos (origen, corte, resultado)
    VALUES (p_origen, v_corte, v_resultado);

    RETURN jsonb_build_object('corte', to_jsonb(v_corte), 'origen', p_origen,
                              'tablas', v_resultado);
END
$rgpd_pasada$;

-- Solo el operador la ejecuta. NOMINAL, no solo PUBLIC (dúo s299 + catálogo vivo): los
-- default privileges de Supabase conceden EXECUTE a anon/authenticated/service_role
-- sobre toda función nueva de `public` — revocar solo PUBLIC los dejaba puestos, y la
-- postcondición 4.2 habría tumbado la migración entera en el SQL Editor (el precedente
-- s277 del repo ya revocaba nominal). Aunque alguno lo ganara, el `SET role` de la
-- entrada le fallaría por no tener membresía en el rol. Dos capas.
REVOKE ALL ON FUNCTION public.rgpd_retencion_pasada(TEXT)
    FROM PUBLIC, anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 3. El reloj (condicional: pg_cron no existe en el contenedor de CI)
-- ---------------------------------------------------------------------------
DO $s299_cron$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
        -- El job corre como QUIEN LO PROGRAMA (`cron.job.username = current_user`). Si
        -- ese rol no tuviera membresía SET en rgpd_retencion, el `SET role` de la
        -- función fallaría CADA MES en silencio (solo visible en job_run_details). Se
        -- exige aquí, en el momento de programar — no se supone (dúo s299).
        IF NOT (
            (SELECT rolsuper FROM pg_roles WHERE rolname = current_user)
            OR EXISTS (
                SELECT 1 FROM pg_auth_members m
                  JOIN pg_roles objetivo ON objetivo.oid = m.roleid
                  JOIN pg_roles miembro  ON miembro.oid  = m.member
                 WHERE objetivo.rolname = 'rgpd_retencion'
                   AND miembro.rolname = current_user
                   AND m.set_option
            )
        ) THEN
            RAISE EXCEPTION 's299: % no tiene membresia SET en rgpd_retencion -- '
                            'programa el job desde el rol operador (postgres) o el '
                            'reloj fallara cada mes', current_user;
        END IF;
        CREATE EXTENSION IF NOT EXISTS pg_cron;
        -- Mensual, día 1 a las 04:30 UTC. `cron.schedule` con el mismo jobname
        -- ACTUALIZA el job existente: re-ejecutar esta migración no duplica el reloj.
        -- El job corre como quien lo programó (postgres), que tiene membresía SET en
        -- rgpd_retencion — la función asume el rol en la entrada.
        PERFORM cron.schedule(
            'rgpd-retencion-mensual',
            '30 4 1 * *',
            'SELECT public.rgpd_retencion_pasada(''cron'')'
        );
    ELSE
        RAISE WARNING 's299: pg_cron NO disponible en este servidor -- el job NO queda '
                      'programado. Esperado SOLO en el contenedor de CI; en produccion '
                      'pg_cron esta disponible y la postcondicion 4 exige el job.';
    END IF;
END
$s299_cron$;

-- ---------------------------------------------------------------------------
-- 4. Postcondiciones
-- ---------------------------------------------------------------------------
DO $s299_post$
DECLARE
    rol TEXT;
    priv TEXT;
BEGIN
    -- 4.1 La función existe, asume el rol EN EL ENCABEZADO y no es SECURITY DEFINER
    -- (SET role + SECURITY DEFINER es la combinación con historial de CVE).
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
         WHERE oid = to_regprocedure('public.rgpd_retencion_pasada(text)')
           AND NOT prosecdef
           AND proconfig @> ARRAY['role=rgpd_retencion']
    ) THEN
        RAISE EXCEPTION 's299: rgpd_retencion_pasada no existe, es SECURITY DEFINER, o '
                        'perdio el SET role del encabezado';
    END IF;

    -- 4.2 Nadie de la API puede ejecutar NI la pasada NI el oráculo de pertenencia.
    -- (Esta postcondición es la que habría tumbado la migración con el REVOKE
    -- solo-PUBLIC: los default privileges de Supabase les daban EXECUTE a los tres.)
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        IF has_function_privilege(rol, 'public.rgpd_retencion_pasada(text)', 'EXECUTE') THEN
            RAISE EXCEPTION 's299: % puede ejecutar la pasada de retencion', rol;
        END IF;
        IF has_function_privilege(rol, 'public.rgpd_quedan_identificados(bigint)',
                                  'EXECUTE') THEN
            RAISE EXCEPTION 's299: % puede ejecutar el oraculo de pertenencia '
                            '(quien tiene datos) via RPC', rol;
        END IF;
    END LOOP;
    IF NOT has_function_privilege('rgpd_retencion',
                                  'public.rgpd_quedan_identificados(bigint)', 'EXECUTE') THEN
        RAISE EXCEPTION 's299: rgpd_retencion perdio EXECUTE sobre rgpd_quedan_identificados';
    END IF;

    -- 4.3 Los recibos: RLS forzada; API a CERO (tabla y columna); el rol de retención
    -- EXACTAMENTE INSERT y nada más (igualdad, no ausencia-de-algunos).
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
         WHERE oid = 'public.rgpd_recibos'::regclass
           AND relrowsecurity AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 's299: RLS no esta habilitada Y forzada en rgpd_recibos';
    END IF;
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        FOREACH priv IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ] LOOP
            IF has_table_privilege(rol, 'public.rgpd_recibos', priv) THEN
                RAISE EXCEPTION 's299: % tiene % sobre rgpd_recibos', rol, priv;
            END IF;
        END LOOP;
        FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'REFERENCES'] LOOP
            IF has_any_column_privilege(rol, 'public.rgpd_recibos', priv) THEN
                RAISE EXCEPTION 's299: % tiene % de columna sobre rgpd_recibos', rol, priv;
            END IF;
        END LOOP;
    END LOOP;
    FOREACH priv IN ARRAY ARRAY[
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
        'REFERENCES', 'TRIGGER', 'MAINTAIN'
    ] LOOP
        IF has_table_privilege('rgpd_retencion', 'public.rgpd_recibos', priv)
           IS DISTINCT FROM (priv = 'INSERT') THEN
            RAISE EXCEPTION 's299: rgpd_retencion deberia tener EXACTAMENTE INSERT en '
                            'rgpd_recibos (fallo en %)', priv;
        END IF;
    END LOOP;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'public' AND tablename = 'rgpd_recibos'
           AND policyname = 'rgpd_recibos_inserta'
           AND 'rgpd_retencion' = ANY(roles)
    ) THEN
        RAISE EXCEPTION 's299: falta la politica de insercion de recibos';
    END IF;

    -- 4.4 El reloj: si pg_cron está DISPONIBLE, el job DEBE existir ACTIVO, con el
    -- comando y el horario exactos, y a nombre de un rol que PUEDE asumir
    -- rgpd_retencion (superusuario o membresía SET) — hace imposible tanto el
    -- «migración en verde sin programar nada» como el «job programado que fallará cada
    -- mes» (dúo s299). Si no está disponible (contenedor de CI), WARNING ya emitido.
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF NOT EXISTS (
            SELECT 1 FROM cron.job j
             WHERE j.jobname = 'rgpd-retencion-mensual'
               AND j.command LIKE '%rgpd_retencion_pasada%'
               AND j.schedule = '30 4 1 * *'
               AND j.active
               AND (
                   EXISTS (SELECT 1 FROM pg_roles r
                            WHERE r.rolname = j.username AND r.rolsuper)
                   OR EXISTS (
                       SELECT 1 FROM pg_auth_members m
                         JOIN pg_roles objetivo ON objetivo.oid = m.roleid
                         JOIN pg_roles miembro  ON miembro.oid  = m.member
                        WHERE objetivo.rolname = 'rgpd_retencion'
                          AND miembro.rolname = j.username
                          AND m.set_option
                   )
               )
        ) THEN
            RAISE EXCEPTION 's299: el job mensual no existe, esta inactivo, cambio de '
                            'horario/comando, o su username no puede asumir el rol';
        END IF;
    ELSIF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
        RAISE EXCEPTION 's299: pg_cron disponible pero no instalado -- el bloque 3 no corrio';
    END IF;

    -- 4.5 El punto de no retorno mira las CUATRO tablas identificadas — incluida el
    -- ancla (hallazgo (a) del dúo): sin esto, un ancla reciente de una consulta vencida
    -- dejaba viva la cadena chat_id → consulta → seudónimo tras destruir el vínculo.
    IF pg_get_functiondef(to_regprocedure('public.rgpd_quedan_identificados(bigint)'))
       NOT ILIKE '%answer_messages%' THEN
        RAISE EXCEPTION 's299: rgpd_quedan_identificados no mira answer_messages -- '
                        'el punto de no retorno llegaria antes de tiempo';
    END IF;
END
$s299_post$;

COMMIT;

-- ---------------------------------------------------------------------------
-- CAMBIO ACOMPAÑANTE EN `supabase_schema.sql` (bloque RGPD-BOUNDARY)
-- ---------------------------------------------------------------------------
-- Re-afirmación condicional de `rgpd_recibos` (RLS + REVOKE, API a cero — a diferencia de
-- persona_seudonimo/consent_events, aquí service_role NO recibe nada) y del REVOKE de
-- EXECUTE sobre la función. Mismo motivo que s296/s297: re-correr el bootstrap debe
-- re-AFIRMAR las garantías, nunca deshacerlas. El CI re-ejecuta el bloque tras la cola.
--
-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   SELECT cron.unschedule('rgpd-retencion-mensual');   -- si pg_cron está instalado
--   DROP FUNCTION public.rgpd_retencion_pasada(TEXT);
--   DROP TABLE public.rgpd_recibos;   -- ⚠️ se lleva los recibos: exportarlos antes
--   -- la extensión pg_cron se DEJA: es un recurso compartido del proyecto
--   -- rgpd_quedan_identificados: para volver a la versión de 3 tablas, re-aplicar
--   -- s296 §1.b — pero NO revertir sus REVOKE nominales: el oráculo público era un
--   -- fallo vivo en producción, no parte del diseño de s296
--
-- El rollback deja la retención otra vez en manual-sin-recibos-durables
-- (`scripts/rgpd_retencion.py` dejaría de funcionar: llama a la función). Reversible
-- mientras no haya corrido ninguna pasada con filas vencidas; después, lo irreversible
-- ya no es el esquema sino la disociación hecha — como en s295.
