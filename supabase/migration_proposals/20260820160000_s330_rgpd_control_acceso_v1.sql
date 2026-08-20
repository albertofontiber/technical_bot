-- ============================================================================
-- s330 — La retención alcanza a las TRES tablas de control de acceso.
--
-- NO APLICADA TODAVÍA. La aplica Alberto en el SQL Editor, como el resto de esta
-- cola (s295 → s296 → s297 → s299 → **s330**). Idempotente: re-ejecutarla es
-- segura (CREATE OR REPLACE, ADD COLUMN IF NOT EXISTS, DROP POLICY IF EXISTS).
-- ============================================================================
-- QUÉ CIERRA. `docs/RGPD_RETENCION.md` marcaba «PENDIENTE MATERIAL — plazo y purga
-- de las dos tablas (art. 5.1.e)»: `bot_invitaciones` y `bot_allowlist` no tenían
-- plazo aplicado, y `panel_usuarios` recibió el suyo el 20-ago (DEC-252). El plazo
-- —24 meses, el mismo del resto de la matriz— lo adjudicó Alberto el 17-ago.
--
-- NO ES UN JOB NUEVO, y eso es deliberado: `rgpd_retencion_pasada` ya existe, ya la
-- corre pg_cron cada mes y ya deja recibo. Un segundo mecanismo sería exactamente
-- el drift que s299 eliminó — dos implementaciones de una operación irreversible.
-- Aquí solo se AMPLÍA: privilegios, políticas y tres sentencias más.
--
-- ---------------------------------------------------------------------------
-- LO QUE EL DÚO ENCONTRÓ Y QUE CAMBIÓ EL DISEÑO (Sol 7/7 + Fable 3/3, 0 FP)
-- ---------------------------------------------------------------------------
-- (1) La regla canónica NO ERA EJECUTABLE. La matriz manda `canjeada_por = NULL`
--     conservando `canjeada_at`, y eso viola `bot_invitaciones_canje_completo`
--     (016:179-182) ⇒ `23514` ⇒ la pasada mensual ENTERA se revierte, dejando sin
--     disociar también `query_logs`/`feedback`/`answer_feedback`/el vínculo, con el
--     error visible solo en `cron.job_run_details`.
--
-- (2) Y el mismo CHECK rompe la SUPRESIÓN A PETICIÓN, que es de HOY: la sentencia
--     del runbook (016:101, DG_DEPLOYMENT:152, RGPD_RETENCION:223 y :531) falla
--     igual. El derecho del art. 17 estaba prescrito en una forma que la base
--     rechaza. Es el hallazgo más caro de esta sesión y apareció arreglando otra cosa.
--
--     Adjudicación de Alberto (20-ago): TERCER ESTADO EXPLÍCITO. `disociada_at` marca
--     «el identificador se retiró de esta fila», la estampe la retención o la
--     supresión. El invariante original sigue vivo para todo lo demás: un canje SIN
--     marca de disociación sigue teniendo que ser atribuible.
--
-- (3) La aserción de mecanismo de s299 exige que el `qual` de cada política contenga
--     literalmente `created_at` + el intervalo. Las anclas nuevas son `revocado_at`,
--     `revocado_en` y una función ⇒ ampliar el array de 4 a 7 nombres habría hecho
--     que la pasada ABORTARA CADA MES. Se rediseña a pares (tabla, ancla) y, para la
--     política que delega en función, se exige que el `prosrc` de ESA función lleve el
--     intervalo: se verifica la única fuente, no se crea una segunda.
--
-- (4) Re-ejecutar s299 después de esto reinstalaría la función de 4 tablas y dejaría
--     la pasada en VERDE-PARCIAL silencioso. El cierre no es un banner (ese control ya
--     falló una vez, con el comentario de 016): s299 gana una precondición ejecutable.
--
-- ---------------------------------------------------------------------------
-- POR QUÉ HACE FALTA UNA FUNCIÓN Y NO UN PREDICADO DIRECTO
-- ---------------------------------------------------------------------------
-- La regla de la invitación canjeada ancla en `bot_allowlist.revocado_at` — OTRA tabla.
-- Una subconsulta dentro de la política se evalúa bajo las políticas del propio rol,
-- que solo le enseñan filas vencidas:
--   · alta VIVA        → no la ve → `NOT EXISTS` cierto → disociaría un acceso ACTIVO
--                        (es el fallo #2 de s296, punto por punto);
--   · alta YA BORRADA  → nada la referencia → la invitación guardaría el nombre PARA
--                        SIEMPRE, en silencio (el fallo #1 de s296).
-- Por eso: función acotada con visibilidad completa, igual que `rgpd_quedan_identificados`.
-- Y NACE BLINDADA, que es la lección que s299 pagó: aquel oráculo quedó ejecutable por
-- anon/authenticated/service_role porque los default privileges de Supabase conceden
-- EXECUTE sobre toda función nueva de `public` y un REVOKE a PUBLIC no los alcanza.
-- ============================================================================
BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Precondiciones — la cola, en orden
-- ---------------------------------------------------------------------------
DO $s330_pre$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
        RAISE EXCEPTION 's330: aplica ANTES 20260803140000_s295_rgpd_rol_retencion_v2.sql';
    END IF;
    IF to_regprocedure('public.rgpd_retencion_pasada(text)') IS NULL THEN
        RAISE EXCEPTION 's330: aplica ANTES 20260805150000_s299_job_programado_v1.sql';
    END IF;
    IF to_regclass('public.bot_invitaciones') IS NULL
       OR to_regclass('public.bot_allowlist') IS NULL THEN
        RAISE EXCEPTION 's330: aplica ANTES migrations/016_allowlist_invitaciones.sql';
    END IF;
    IF to_regclass('public.panel_usuarios') IS NULL THEN
        RAISE EXCEPTION 's330: aplica ANTES migrations/019_panel_usuarios_cerrojo.sql';
    END IF;
END
$s330_pre$;

-- ---------------------------------------------------------------------------
-- 1. El tercer estado (adjudicado por Alberto, 20-ago)
-- ---------------------------------------------------------------------------
-- `disociada_at` NO es un plazo ni una fecha de negocio: es la marca de que el
-- identificador se retiró de esta fila. La estampan las DOS rutas (retención mensual
-- y supresión a petición), y sirve además de recibo por fila y de predicado de
-- idempotencia — sin ella, la pasada re-tocaría cada mes lo ya disociado e inflaría
-- el recibo con trabajo que no existe.
ALTER TABLE public.bot_invitaciones
    ADD COLUMN IF NOT EXISTS disociada_at TIMESTAMPTZ;

COMMENT ON COLUMN public.bot_invitaciones.disociada_at IS
    'Marca de que el identificador de quien canjeo se retiro de esta fila (s330). '
    'La estampan la retencion mensual y la supresion a peticion. NULL = fila intacta.';

-- El CHECK ampliado. Los dos brazos originales siguen exactamente igual; se añade
-- SOLO el estado nuevo, y exige la marca — sin ella, un canje sin atribuir sigue
-- siendo imposible, que es para lo que se creó la restricción.
ALTER TABLE public.bot_invitaciones
    DROP CONSTRAINT IF EXISTS bot_invitaciones_canje_completo;
ALTER TABLE public.bot_invitaciones
    ADD CONSTRAINT bot_invitaciones_canje_completo CHECK (
        (canjeada_at IS NULL     AND canjeada_por IS NULL)
        OR (canjeada_at IS NOT NULL AND canjeada_por IS NOT NULL)
        OR (canjeada_at IS NOT NULL AND canjeada_por IS NULL
            AND disociada_at IS NOT NULL)
    );

-- ---------------------------------------------------------------------------
-- 2. Privilegios de COLUMNA para el rol (mismo listón que s295: lo mínimo)
-- ---------------------------------------------------------------------------
-- El rol NO recibe SELECT sobre `nota` en ninguna de las dos tablas: para ponerla a
-- NULL no hace falta leerla, y no poder leerla es la garantía de que este rol nunca
-- ve el contenido personal que retira.
GRANT SELECT (id, creada_at, canjeada_at, disociada_at)
    ON public.bot_invitaciones TO rgpd_retencion;
GRANT UPDATE (nota, canjeada_por, disociada_at)
    ON public.bot_invitaciones TO rgpd_retencion;

GRANT SELECT (telegram_user_id, revocado_at, invitacion_id)
    ON public.bot_allowlist TO rgpd_retencion;
GRANT DELETE ON public.bot_allowlist TO rgpd_retencion;

GRANT SELECT (usuario, revocado_en) ON public.panel_usuarios TO rgpd_retencion;
GRANT DELETE                        ON public.panel_usuarios TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 3. El oráculo acotado, con visibilidad completa y blindado al nacer
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.rgpd_invitacion_vencida(p_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $rgpd_inv$
    -- Nunca canjeada: la `nota` es el único dato personal de una llave que nadie usó.
    -- Canjeada: vence cuando NO queda alta viva ni revocada-hace-poco que la referencie
    -- (adjudicado 20-ago: también el caso «el alta ya no existe», que si no quedaría
    -- fuera de la retención en silencio), con suelo propio de 24 meses desde el canje
    -- para no disociar la traza de un canje reciente cuya alta alguien borró a mano.
    SELECT CASE
             WHEN i.canjeada_at IS NULL
             THEN i.creada_at   < now() - interval '24 months'
             ELSE i.canjeada_at < now() - interval '24 months'
                  AND NOT EXISTS (
                      SELECT 1 FROM public.bot_allowlist a
                       WHERE a.invitacion_id = p_id
                         AND (a.revocado_at IS NULL
                              OR a.revocado_at >= now() - interval '24 months'))
           END
      FROM public.bot_invitaciones i
     WHERE i.id = p_id;
$rgpd_inv$;

-- La lección de s299, aplicada de entrada y no después de que el dúo la cace.
REVOKE ALL ON FUNCTION public.rgpd_invitacion_vencida(UUID)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.rgpd_invitacion_vencida(UUID) TO rgpd_retencion;

-- ---------------------------------------------------------------------------
-- 4. Las políticas: la ventana sigue siendo un invariante del MOTOR
-- ---------------------------------------------------------------------------
-- RLS ya está ENABLE + FORCE en las tres (016:276-279, 019:110-111); se re-afirma por
-- si alguna quedara desarmada, que es barato y es justo lo que la aserción vigila.
ALTER TABLE public.bot_invitaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_invitaciones FORCE  ROW LEVEL SECURITY;
ALTER TABLE public.bot_allowlist    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_allowlist    FORCE  ROW LEVEL SECURITY;
ALTER TABLE public.panel_usuarios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.panel_usuarios   FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.bot_invitaciones;
CREATE POLICY rgpd_retencion_ventana ON public.bot_invitaciones
    TO rgpd_retencion
    USING      (public.rgpd_invitacion_vencida(id))
    WITH CHECK (public.rgpd_invitacion_vencida(id));

-- `revocado_at` es NULL en las altas VIVAS ⇒ el predicado es NULL ⇒ no las ve.
-- La conservación del acceso activo es una propiedad del motor, no una condición escrita.
DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.bot_allowlist;
CREATE POLICY rgpd_retencion_ventana ON public.bot_allowlist
    TO rgpd_retencion
    USING (revocado_at < now() - interval '24 months');

-- Ídem: el CHECK `panel_usuarios_revocacion_coherente` garantiza que `revocado_en` solo
-- está relleno cuando `activo = FALSE`.
DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.panel_usuarios;
CREATE POLICY rgpd_retencion_ventana ON public.panel_usuarios
    TO rgpd_retencion
    USING (revocado_en < now() - interval '24 months');

COMMIT;

-- ---------------------------------------------------------------------------
-- 5. La pasada, ampliada a 7 tablas
-- ---------------------------------------------------------------------------
-- DERIVADA del original de s299: las cuatro sentencias que ya existían y la
-- destrucción del vínculo quedan BYTE-IDÉNTICAS (se generó sustituyendo solo la
-- aserción e insertando las tres nuevas). Transcribir a mano una función
-- irreversible es pedir un typo que nadie ve hasta que borra de más.
--
-- POR QUÉ UN `DROP` Y NO SOLO `CREATE OR REPLACE` — hallazgo del gate contra PostgreSQL
-- 17 real, no una precaución teórica: `CREATE OR REPLACE` sobre esta función falla con
-- `42501 permission denied for function rgpd_retencion_pasada`. La causa es su propio
-- encabezado: al reemplazar una función que lleva `SET role = rgpd_retencion`, el
-- chequeo del objeto previo ocurre YA con ese rol asumido, y a ese rol s299 le revocó
-- todo — incluido EXECUTE sobre ella misma. Cuando s299 la creó no existía nada que
-- chequear, así que el problema aparece SOLO al ampliarla. Verificado por eliminación:
-- reemplazarla sin `SET role` pasa; con él, no. Quitar el `SET role` no es opción — es
-- el invariante que hace que la ventana la garantice el motor.
--
-- Y el `DROP` obliga a re-declarar los REVOKE: la función nace de nuevo y los default
-- privileges de Supabase le conceden EXECUTE a la API entera. Es exactamente el agujero
-- que s299 tuvo abierto en producción con `rgpd_quedan_identificados`.
--
-- El job de pg_cron NO se rompe: `cron.schedule` guarda el comando como TEXTO, no como
-- dependencia del catálogo, así que el DROP no lo arrastra y el CREATE lo re-satisface.
BEGIN;

DROP FUNCTION IF EXISTS public.rgpd_retencion_pasada(TEXT);

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
          FROM (VALUES ('query_logs',       'created_at'),
                       ('feedback',         'created_at'),
                       ('answer_feedback',  'created_at'),
                       ('answer_messages',  'created_at'),
                       -- s330: las anclas de estas tres NO son `created_at`, y por eso
                       -- la aserción pasó a llevar la suya por tabla. Con el array de
                       -- nombres de s299 la pasada habría abortado CADA MES.
                       ('bot_allowlist',    'revocado_at'),
                       ('panel_usuarios',   'revocado_en'),
                       -- La de invitaciones delega en la función: su `qual` nombra al
                       -- oráculo, y el intervalo se verifica DENTRO de él (abajo).
                       ('bot_invitaciones', 'rgpd_invitacion_vencida')
               ) AS t(tabla, ancla)
         WHERE NOT EXISTS (
                   SELECT 1 FROM pg_class c
                    WHERE c.oid = to_regclass(format('public.%I', t.tabla))
                      AND c.relrowsecurity AND c.relforcerowsecurity
               )
            -- EXACTAMENTE UNA política alcanza al rol (ronda 2 del dúo s299): las
            -- permisivas se OR-ean — una segunda de debug (`USING (true)`, al rol o a
            -- PUBLIC) abriría la ventana con la aserción en verde y recibo normal.
            OR (SELECT count(*) FROM pg_policies p
                 WHERE p.schemaname = 'public' AND p.tablename = t.tabla
                   AND ('rgpd_retencion' = ANY(p.roles) OR 'public' = ANY(p.roles))) <> 1
            -- ...y es LA de la ventana, con SU ancla. Para las seis directas se exige
            -- además el intervalo en el propio `qual`; para invitaciones, que el `qual`
            -- nombre al oráculo. VERIFICACIÓN de la única fuente, no una segunda fuente.
            OR NOT EXISTS (
                   SELECT 1 FROM pg_policies p
                    WHERE p.schemaname = 'public' AND p.tablename = t.tabla
                      AND p.policyname = 'rgpd_retencion_ventana'
                      AND 'rgpd_retencion' = ANY(p.roles)
                      AND p.qual LIKE '%' || t.ancla || '%'
                      AND (t.tabla = 'bot_invitaciones'
                           OR p.qual LIKE '%2 years%' OR p.qual LIKE '%24 mons%')
               )
    ) THEN
        RAISE EXCEPTION 'rgpd: la ventana NO esta armada en alguna de las 7 tablas (RLS '
                        'deshabilitada, politica ausente o alterada, o una politica '
                        'EXTRA alcanza al rol). Pasada abortada sin tocar nada.';
    END IF;

    -- s330 — y el agujero que abriría delegar en una función sin mirar dentro: si
    -- alguien reemplazara `rgpd_invitacion_vencida` por `SELECT true`, la aserción de
    -- arriba seguiría verde y la pasada disociaría invitaciones RECIENTES. Se exige que
    -- el intervalo de 24 meses siga estando en su cuerpo — misma clase de verificación
    -- que la postcondición 6.6 de s295, aplicada al sitio donde ahora vive la ventana.
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
         WHERE oid = to_regprocedure('public.rgpd_invitacion_vencida(uuid)')
           AND prosecdef
           AND prosrc LIKE '%24 months%'
    ) THEN
        RAISE EXCEPTION 'rgpd: rgpd_invitacion_vencida no existe, no es SECURITY DEFINER '
                        'o perdio el intervalo de 24 meses. Pasada abortada sin tocar nada.';
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

    -- ========================= s330: control de acceso =========================
    -- ORDEN: invitaciones ANTES que allowlist. La regla de la invitación canjeada
    -- mira el `revocado_at` del alta; si se borrara el alta primero, el ancla
    -- desaparecería DENTRO de la misma pasada. (El caso del alta ya inexistente lo
    -- cubre el oráculo, pero eso es la red — no una excusa para el orden malo.)
    --
    -- `disociada_at IS NULL` es el predicado de IDEMPOTENCIA, no la ventana: la
    -- ventana la sigue imponiendo la política. Sin él, cada pasada re-tocaría lo ya
    -- disociado y el recibo cobraría trabajo inexistente.
    WITH tocadas AS (
        UPDATE public.bot_invitaciones AS t
           SET nota = NULL, canjeada_por = NULL, disociada_at = now()
         WHERE t.disociada_at IS NULL
        RETURNING t.id
    )
    SELECT COALESCE(array_agg(id::text), '{}') INTO v_ids FROM tocadas;
    v_resultado := v_resultado || jsonb_build_object('bot_invitaciones', jsonb_build_object(
        'modo', 'disociar', 'tocadas', COALESCE(array_length(v_ids, 1), 0),
        'ids', to_jsonb(v_ids)));

    -- `telegram_user_id` es la PK: no se puede disociar sin destruir la fila. Es la
    -- ÚNICA excepción al principio rector, declarada en la matriz. La traza «hubo un
    -- alta y la emitió X» sobrevive en la invitación, ya sin la persona.
    -- El id ES la persona ⇒ el recibo lleva CONTEO, nunca ids (patrón persona_seudonimo).
    WITH borradas AS (
        DELETE FROM public.bot_allowlist RETURNING 1
    )
    SELECT count(*) INTO v_conteo FROM borradas;
    v_resultado := v_resultado || jsonb_build_object('bot_allowlist', jsonb_build_object(
        'modo', 'borrar', 'tocadas', v_conteo, 'ids', '[]'::jsonb));

    -- Ídem con el usuario del panel (DEC-252, 20-ago). Sujeto distinto —administrador,
    -- no técnico— y el mismo plazo por decisión de Alberto: una sola ventana es más
    -- simple de cumplir, de auditar y de explicar que tres.
    WITH borrados AS (
        DELETE FROM public.panel_usuarios RETURNING 1
    )
    SELECT count(*) INTO v_conteo FROM borrados;
    v_resultado := v_resultado || jsonb_build_object('panel_usuarios', jsonb_build_object(
        'modo', 'borrar', 'tocadas', v_conteo, 'ids', '[]'::jsonb));

    -- El recibo, en la MISMA transacción: si la pasada se revierte (dry-run del script),
    -- el recibo se revierte con ella ⇒ toda fila persistida = pasada confirmada.
    INSERT INTO public.rgpd_recibos (origen, corte, resultado)
    VALUES (p_origen, v_corte, v_resultado);

    RETURN jsonb_build_object('corte', to_jsonb(v_corte), 'origen', p_origen,
                              'tablas', v_resultado);
END
$rgpd_pasada$;

-- Los mismos REVOKE que s299, re-declarados porque la función es NUEVA (ver arriba).
-- Sin esto, cualquiera con la clave anónima podría disparar la retención por RPC.
REVOKE ALL ON FUNCTION public.rgpd_retencion_pasada(TEXT)
    FROM PUBLIC, anon, authenticated, service_role;

COMMIT;

-- ---------------------------------------------------------------------------
-- 6. Postcondiciones — lo afirmado se comprueba en el mismo acto
-- ---------------------------------------------------------------------------
DO $s330_post$
DECLARE
    rol  TEXT;
    faltan TEXT;
    v_constraint TEXT;
BEGIN
    -- 6.1 El oráculo nuevo NO es alcanzable por los roles de la API. Es LA lección de
    -- s299: los default privileges de Supabase conceden EXECUTE sobre toda función
    -- nueva de `public`, y un REVOKE a PUBLIC no los alcanza. Sin esto, cualquiera con
    -- la clave anónima podría preguntar por RPC si una invitación existe y está vencida.
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        IF has_function_privilege(rol, 'public.rgpd_invitacion_vencida(uuid)', 'EXECUTE') THEN
            RAISE EXCEPTION 's330: % puede ejecutar rgpd_invitacion_vencida', rol;
        END IF;
    END LOOP;
    IF NOT has_function_privilege('rgpd_retencion',
                                  'public.rgpd_invitacion_vencida(uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 's330: rgpd_retencion no puede ejecutar el oraculo que su politica usa';
    END IF;

    -- 6.1.b Y LA PASADA tampoco: el DROP+CREATE de la sección 5 la hizo nacer de nuevo
    -- bajo los default privileges de Supabase. Sin este control, ampliar la retención
    -- habría REABIERTO el agujero que s299 cerró.
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        IF has_function_privilege(rol, 'public.rgpd_retencion_pasada(text)', 'EXECUTE') THEN
            RAISE EXCEPTION 's330: % puede ejecutar la pasada de retencion', rol;
        END IF;
    END LOOP;

    -- 6.2 El rol NO gana lectura del contenido personal que retira.
    IF has_column_privilege('rgpd_retencion', 'public.bot_invitaciones', 'nota', 'SELECT')
       OR has_column_privilege('rgpd_retencion', 'public.bot_allowlist', 'nota', 'SELECT') THEN
        RAISE EXCEPTION 's330: rgpd_retencion puede LEER la nota -- solo debe poder borrarla';
    END IF;

    -- 6.3 La ventana está armada en las SIETE tablas (misma forma que la aserción de
    -- la función: si esto pasa aquí, la pasada no abortará el día 1).
    SELECT string_agg(t.tabla, ', ') INTO faltan
      FROM (VALUES ('query_logs'), ('feedback'), ('answer_feedback'), ('answer_messages'),
                   ('bot_invitaciones'), ('bot_allowlist'), ('panel_usuarios')) AS t(tabla)
     WHERE NOT EXISTS (
               SELECT 1 FROM pg_policies p
                WHERE p.schemaname = 'public' AND p.tablename = t.tabla
                  AND p.policyname = 'rgpd_retencion_ventana'
                  AND 'rgpd_retencion' = ANY(p.roles));
    IF faltan IS NOT NULL THEN
        RAISE EXCEPTION 's330: falta la politica de ventana en: %', faltan;
    END IF;

    -- 6.4 La función VIVA es la de 7 tablas. Es la postcondición que delata el drift
    -- de F-2: si alguien re-ejecutara s299 después, esto vuelve a fallar al re-aplicar.
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
         WHERE oid = to_regprocedure('public.rgpd_retencion_pasada(text)')
           AND prosrc LIKE '%bot_invitaciones%'
           AND prosrc LIKE '%bot_allowlist%'
           AND prosrc LIKE '%panel_usuarios%'
    ) THEN
        RAISE EXCEPTION 's330: la pasada viva NO cubre las 3 tablas de control de acceso '
                        '-- alguien reinstalo la version de s299 (4 tablas)';
    END IF;

    -- 6.5 El tercer estado es legal y el original sigue prohibido: un canje sin
    -- atribución Y SIN marca de disociación tiene que seguir siendo imposible.
    BEGIN
        INSERT INTO public.bot_invitaciones
            (token_hash, nota, creada_por, expira_at, canjeada_at, canjeada_por)
        VALUES (repeat('a', 64), 's330 postcondicion', 'postcondicion',
                now() + interval '1 day', now(), NULL);
        RAISE EXCEPTION 's330: el CHECK admite un canje sin atribuir y sin marca de '
                        'disociacion -- el invariante original se ha perdido';
    EXCEPTION
        WHEN check_violation THEN
            -- ...pero LA restriccion correcta. Tragarse cualquier check_violation
            -- daria verde si el INSERT hubiera fallado por la caducidad o por el
            -- formato del hash, sin haber probado nada de lo que se afirma aqui.
            GET STACKED DIAGNOSTICS v_constraint = CONSTRAINT_NAME;
            IF v_constraint IS DISTINCT FROM 'bot_invitaciones_canje_completo' THEN
                RAISE EXCEPTION 's330: el control negativo no probo lo que dice -- '
                                'el INSERT fallo por %, no por el CHECK del canje',
                                COALESCE(v_constraint, '(sin nombre)');
            END IF;
    END;
END
$s330_post$;

-- ============================================================================
-- ROLLBACK (copiar y pegar; deja el sistema exactamente como antes de s330)
-- ---------------------------------------------------------------------------
-- OJO con el orden: primero la función de 4 tablas (si no, la pasada mensual buscaría
-- políticas que ya no existen y abortaría), y `disociada_at` SOLO se puede quitar si
-- ninguna fila la usa — si la retención o una supresión ya la estamparon, quitarla
-- destruiría la única prueba de que el identificador se retiró.
--
--   -- 1. Reinstalar la pasada de 4 tablas:
--   --    re-ejecutar 20260805150000_s299_job_programado_v1.sql ENTERA.
--   -- 2. Políticas y privilegios:
--   DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.bot_invitaciones;
--   DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.bot_allowlist;
--   DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.panel_usuarios;
--   REVOKE ALL ON public.bot_invitaciones, public.bot_allowlist, public.panel_usuarios
--       FROM rgpd_retencion;
--   DROP FUNCTION IF EXISTS public.rgpd_invitacion_vencida(UUID);
--   -- 3. El esquema (solo si nadie estampó la marca):
--   --    SELECT count(*) FROM public.bot_invitaciones WHERE disociada_at IS NOT NULL;
--   --    Si es 0:
--   ALTER TABLE public.bot_invitaciones DROP CONSTRAINT bot_invitaciones_canje_completo;
--   ALTER TABLE public.bot_invitaciones ADD CONSTRAINT bot_invitaciones_canje_completo
--       CHECK ((canjeada_at IS NULL AND canjeada_por IS NULL)
--              OR (canjeada_at IS NOT NULL AND canjeada_por IS NOT NULL));
--   ALTER TABLE public.bot_invitaciones DROP COLUMN disociada_at;
--   -- ...y si NO es 0, el CHECK viejo rechazaría esas filas: hay que decidir antes qué
--   -- se hace con ellas, que es una decisión de cumplimiento, no de esquema.
-- ============================================================================
