-- ============================================================================
-- 019 — `panel_usuarios` + `panel_intentos` + `panel_puerta` +
--       `panel_retencion_pasada`: los usuarios del panel a Supabase (a2) y el
--       cerrojo anti-fuerza-bruta distribuido. s324j; diseño completo y sus
--       seis rondas de dúo: `evals/s324i_panel_vercel_propuesta_v9.md`
--       (DEC-237 → DEC-239).
--
-- ⚠️ CONTRATO DE APLICACIÓN (v9 §13, lección de la 016 tras DOS fallos reales
--    en producción): este fichero se aplica ENTERO con un aplicador
--    transaccional — el SQL Editor de Supabase (ejecuta el script completo en
--    UNA transacción) o `psql --single-transaction`. NUNCA sentencia a
--    sentencia: entre el CREATE TABLE y su REVOKE los defaults de Supabase
--    dejarían la tabla de credenciales expuesta. Y NO lleva BEGIN/COMMIT
--    propios A PROPÓSITO: dentro del SQL Editor un BEGIN interno no abre nada
--    y un ROLLBACK interno desharía las tablas (los dos intentos fallidos de
--    la 016 son exactamente eso).
--
-- ⚠️ ORDEN DE LA COLA: exige s295 → s299 aplicadas (el rol `rgpd_retencion` y
--    la tabla `rgpd_recibos` nacen en `supabase/migration_proposals/`); el
--    preflight de abajo lo comprueba y aborta con el motivo escrito.
--
-- REVERSIBILIDAD: nada de esta migración toca datos existentes. El rollback
-- es `DROP FUNCTION public.panel_retencion_pasada(text); DROP FUNCTION
-- public.panel_puerta(text[], int, numeric, numeric, numeric, int);
-- DROP TABLE public.panel_intentos; DROP TABLE public.panel_usuarios;` más
-- `SELECT cron.unschedule('panel-retencion-diaria');` si el reloj se llegó a
-- programar.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FASE 0 — PREFLIGHT: la cola s295→s299, presente (v9 §13, ronda F4-M2; el
-- patrón literal del preflight de la s299)
-- ----------------------------------------------------------------------------
DO $s324j_preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
        RAISE EXCEPTION '019: aplica ANTES la cola s295→s299 (falta el rol '
                        'rgpd_retencion — 20260803140000_s295_rgpd_rol_retencion_v2.sql)';
    END IF;
    IF to_regclass('public.rgpd_recibos') IS NULL THEN
        RAISE EXCEPTION '019: aplica ANTES la cola s295→s299 (falta rgpd_recibos '
                        '— 20260805150000_s299_job_programado_v1.sql)';
    END IF;
END
$s324j_preflight$;

-- ----------------------------------------------------------------------------
-- FASE A — LAS TABLAS
-- ----------------------------------------------------------------------------

-- Los usuarios del panel. Los CHECK no son adorno (v9 §1.1):
--   · el de `usuario` impone EL MISMO charset y longitud que el backend exige
--     al autenticar (`auth.USUARIO_RE`; la puerta 6-bis ata los dos lados con
--     una tabla de casos compartida) — una fila que el panel jamás podría
--     encontrar no puede ni existir;
--   · el de `registro` corta EN LA BASE el error que `validar_configuracion`
--     caza en el arranque: pegar la contraseña en claro donde iba el hash;
--   · `revocacion_coherente` hace imposibles los estados de auditoría
--     contradictorios que los GRANT por columnas permitirían crear por
--     separado (ronda S2-M5) — reactivar obliga a limpiar fecha y firma en el
--     mismo UPDATE. Estricto desde el día uno: la tabla nace ahora, sin
--     legacy que tolerar.
CREATE TABLE public.panel_usuarios (
    usuario      TEXT PRIMARY KEY
                 CHECK (usuario ~ '^[a-z0-9._@-]{1,64}$'),
    registro     TEXT NOT NULL CHECK (registro LIKE 'scrypt$%'),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    alta_por     TEXT NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocado_en  TIMESTAMPTZ,
    revocado_por TEXT,
    CONSTRAINT panel_usuarios_revocacion_coherente CHECK (
        (activo AND revocado_en IS NULL AND revocado_por IS NULL)
        OR (NOT activo AND revocado_en IS NOT NULL AND revocado_por IS NOT NULL)
    )
);

COMMENT ON TABLE public.panel_usuarios IS
    'Usuarios del panel web (s324j/DEC-239). Baja LÓGICA (activo=false), sin '
    'DELETE: conservar quién dio el alta y quién revocó es la mitad barata de '
    'la auditoría. La supresión a petición (RGPD) la ejecuta el operador '
    'aparte. Dato personal EN CLARO: fila propia en la matriz de retención '
    '(docs/RGPD_RETENCION.md); plazo de las filas revocadas [DECIDIR: Alberto].';

-- El cerrojo distribuido. Las claves llegan SEUDONIMIZADAS desde
-- `dashboard/cerrojo.py` (`u:`/`ip:` + HMAC truncado, v9 §3.1): un volcado de
-- esta tabla no enseña ni usuarios ni IPs. Sigue siendo dato personal
-- SEUDONIMIZADO (con la clave K se puede recomprobar un identificador): fila
-- propia en la matriz, plazo 24 h operativas / ≤48 h con la red diaria de
-- abajo, evidenciada por recibo.
CREATE TABLE public.panel_intentos (
    clave  TEXT PRIMARY KEY,
    fallos INTEGER NOT NULL DEFAULT 0 CHECK (fallos >= 0),
    ultimo TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_panel_intentos_ultimo ON public.panel_intentos (ultimo);

COMMENT ON TABLE public.panel_intentos IS
    'Contador de intentos de login del panel (s324j/DEC-239). Claves '
    'seudonimizadas (HMAC); la ventana de retención de 24 h la impone la '
    'POLICY rgpd_retencion_ventana — si la constante Python y la política '
    'divergieran, MANDA LA POLÍTICA (doctrina s299).';

-- ----------------------------------------------------------------------------
-- FASE B — LA FRONTERA (el patrón de la 016, tabla por tabla; v9 §1.2)
-- Supabase concede TODO por defecto a anon/authenticated sobre las tablas
-- nuevas de `public`: el REVOKE es la migración, no un adorno.
-- ----------------------------------------------------------------------------

ALTER TABLE public.panel_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.panel_usuarios FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.panel_usuarios
    FROM PUBLIC, anon, authenticated, service_role;
-- El camino de autenticación solo puede LEER lo que usa; las columnas de
-- auditoría (alta_por, creado_en, revocado_*) no viajan a PostgREST y no son
-- reescribibles por REST — la traza de quién dio el alta no se edita con la
-- credencial del panel. INSERT/UPDATE existen para el script de operación
-- (`scripts/s324j_panel_usuario.py`); el código del panel NO escribe aquí.
-- LÍMITE declarado, el mismo de la 016: panel y script comparten
-- SUPABASE_SERVICE_KEY — los privilegios no separan «panel» de «operador»
-- (eso lo separa el código); sí impiden lo que ninguno debe poder hacer.
GRANT SELECT (usuario, registro, activo) ON public.panel_usuarios TO service_role;
GRANT INSERT (usuario, registro, activo, alta_por)
    ON public.panel_usuarios TO service_role;
GRANT UPDATE (registro, activo, revocado_en, revocado_por)
    ON public.panel_usuarios TO service_role;
-- Sin DELETE: la baja es lógica; la supresión a petición va aparte, a la vista.

ALTER TABLE public.panel_intentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.panel_intentos FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.panel_intentos
    FROM PUBLIC, anon, authenticated, service_role;
-- Los CUATRO GRANT del cerrojo, ENUMERADOS (v9 §1.2, ronda F2-M1: la RPC es
-- SECURITY INVOKER y ejerce exactamente estos privilegios — una sentencia de
-- su cuerpo sin GRANT sería el 42501 de S-C1, reproducido dentro de la
-- función; la puerta 9-bis cruza el cuerpo con esta lista):
GRANT SELECT ON public.panel_intentos TO service_role;             -- FOR UPDATE de admitir
GRANT INSERT (clave, fallos, ultimo) ON public.panel_intentos TO service_role;  -- siembra+upsert
GRANT UPDATE (fallos, ultimo) ON public.panel_intentos TO service_role;         -- incremento
GRANT DELETE ON public.panel_intentos TO service_role;             -- poda, cap y acierto
-- DELETE aquí y no en las otras tablas, con motivo: borrar ES el contrato de
-- esta tabla (poda, cap, acierto) y no hay nada que conservar.

-- La retención necesita SU acceso (v9 §1.2, ronda S2-M1): la pasada corre como
-- `rgpd_retencion`, no como `service_role`, y su ventana la impone la POLICY —
-- el rol no puede tocar una fila dentro de plazo AUNQUE el SQL de la pasada
-- tuviera un bug. `service_role` tiene rolbypassrls: el camino del cerrojo no
-- se entera (mismo comentario que deja escrito la s295).
GRANT SELECT (clave, ultimo) ON public.panel_intentos TO rgpd_retencion;
GRANT DELETE ON public.panel_intentos TO rgpd_retencion;
CREATE POLICY rgpd_retencion_ventana ON public.panel_intentos
    TO rgpd_retencion
    USING (ultimo < now() - interval '24 hours');

-- ----------------------------------------------------------------------------
-- FASE C — `panel_puerta`: la ADMISIÓN entera en una transacción (v9 §3.2-3.4)
-- ----------------------------------------------------------------------------
-- Por qué una RPC, cuando este repo ya rechazó una con motivo (el canje,
-- logging_db): PostgREST no puede expresar `fallos = fallos + 1`, y la
-- admisión exige leer-decidir-contar SIN ventana entre medias. Se construye
-- con el patrón endurecido de s277 (`document_local_snapshot_v2`): SECURITY
-- INVOKER (no presta privilegios — corre como service_role, que ya tiene los
-- suyos arriba) + search_path vacío + REVOKE nominal del EXECUTE (las
-- funciones nacen ejecutables por PUBLIC; ese default ES el agujero de s296).
--
-- LA TABLA DE CASOS (puerta 4; la misma que ejercita el doble en memoria
-- `auth.Cerrojo.admitir` — con libres=4, base=60, max=900):
--   fallos previos 0..4  → espera 0 (admitido; queda fallos+1)
--   fallos previos 5     → espera hasta ultimo+60s
--   fallos previos 6     → espera hasta ultimo+120s
--   fallos previos 9     → espera hasta ultimo+900s (techo)
--   bloqueado            → SIN incrementar (hoy un intento bloqueado tampoco suma)
CREATE OR REPLACE FUNCTION public.panel_puerta(
    claves text[], libres int, base_s numeric, max_s numeric,
    retencion_s numeric, cap int
) RETURNS numeric
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $panel_puerta$
DECLARE
    v_ahora   timestamptz;   -- se fija DESPUÉS del lock (ver abajo)
    v_clave   text;
    v_fallos  int;
    v_ultimo  timestamptz;
    v_espera  numeric;
    v_max     numeric := 0;
    v_count   int;
    v_nuevas  int;
BEGIN
    -- (ronda F6-m2) La contención tiene que producir una RESPUESTA de error
    -- (≥400 → el transporte la trata como configuración → 503 fail-closed),
    -- no un timeout del cliente httpx (→ fail-open justo bajo ataque). El
    -- lock_timeout se consulta al empezar CADA espera de lock, así que acota
    -- la cola del advisory lock de abajo. `statement_timeout` NO se fija aquí
    -- a propósito: dentro de una función solo aplicaría a sentencias
    -- top-level futuras, no a la llamada en curso — sería decorativo, y un
    -- control decorativo es peor que su ausencia declarada.
    PERFORM set_config('lock_timeout', '2s', true);

    -- (ronda S2-M2, F3-m2) El cap exige serializar llamadas con claves
    -- DISJUNTAS. Semántica REAL, sin eufemismo: un advisory lock DE
    -- TRANSACCIÓN se retiene hasta el COMMIT, así que cada `admitir` se
    -- serializa ENTERO contra los demás — a esta escala es gratis y es el
    -- invariante exacto del cerrojo en memoria. La siembra + FOR UPDATE de
    -- abajo queda como SEGUNDA capa: hoy redundante bajo este lock, y lo que
    -- sostiene la corrección si algún día alguien lo estrecha.
    PERFORM pg_advisory_xact_lock(hashtext('panel_intentos'));

    -- El reloj se lee DESPUÉS del lock, y con clock_timestamp() — NO now()
    -- (ronda del dúo sobre el cableado, S-m1): `now()` es el instante de
    -- INICIO de la transacción, constante durante toda ella; dos `admitir`
    -- encoladas en el lock (T2 empezó antes que T1 pero espera su turno)
    -- escribirían `ultimo` con instantes en desorden, haciéndolo RETROCEDER.
    -- `clock_timestamp()` leído aquí es el tiempo real en el momento en que
    -- esta llamada YA tiene el lock: monotónico entre las transacciones que el
    -- lock serializa, que es justo lo que el reloj monotónico del doble en
    -- memoria garantiza.
    v_ahora := clock_timestamp();

    -- (1) Poda: la retención ejecutada en cada escritura. La constante viaja
    -- como argumento (una sola fuente en Python); la ventana RGPD canónica la
    -- impone la POLICY de arriba — si divergieran, manda la política.
    DELETE FROM public.panel_intentos
     WHERE ultimo < v_ahora - make_interval(secs => retencion_s);

    -- (2) El techo DURO, con la aritmética exacta (ronda S2-M3): si el
    -- recuento MÁS las claves que esta llamada va a sembrar supera el cap, se
    -- sacrifica lo más antiguo hasta que la siembra quepa. Perder un bloqueo
    -- vivo regala una tanda de intentos; quedarse sin techo regala la tabla.
    SELECT count(*) INTO v_count FROM public.panel_intentos;
    SELECT count(*) INTO v_nuevas
      FROM unnest(claves) AS t(c)
     WHERE NOT EXISTS (SELECT 1 FROM public.panel_intentos p WHERE p.clave = t.c);
    IF v_count + v_nuevas > cap THEN
        DELETE FROM public.panel_intentos
         WHERE clave IN (SELECT clave FROM public.panel_intentos
                          ORDER BY ultimo ASC
                          LIMIT (v_count + v_nuevas - cap));
    END IF;

    -- (3) SIEMBRA antes del lock de fila (ronda S-C3): FOR UPDATE no puede
    -- bloquear una fila que no existe — sin esto, la primera ráfaga contra
    -- una clave fresca vería «ausente» N veces y entraría entera. En orden
    -- estable de claves (sin interbloqueo entre llamadas).
    INSERT INTO public.panel_intentos (clave, fallos, ultimo)
        SELECT t.c, 0, v_ahora FROM unnest(claves) AS t(c) ORDER BY t.c
        ON CONFLICT (clave) DO NOTHING;

    -- (4) La espera, con la fórmula del cerrojo de hoy (auth.py:
    -- min(base·2^(fallos−libres−1), max) desde `ultimo`). FOR UPDATE en el
    -- mismo orden estable: la llamada que espera relee la versión confirmada
    -- (EvalPlanQual bajo READ COMMITTED — el mismo mecanismo con el que el
    -- canje gana a dos pulsadores simultáneos).
    FOR v_clave IN SELECT t.c FROM unnest(claves) AS t(c) ORDER BY t.c LOOP
        SELECT p.fallos, p.ultimo INTO v_fallos, v_ultimo
          FROM public.panel_intentos p WHERE p.clave = v_clave FOR UPDATE;
        IF FOUND AND v_fallos > libres THEN
            v_espera := GREATEST(
                0,
                extract(epoch FROM (v_ultimo - v_ahora))
                + LEAST(base_s * power(2, v_fallos - libres - 1), max_s)
            );
            v_max := GREATEST(v_max, v_espera);
        END IF;
    END LOOP;
    IF v_max > 0 THEN
        RETURN v_max;   -- bloqueado: SIN incrementar (basta una clave cerrada)
    END IF;

    -- (5) Admitido: CONTAR YA (contar-al-admitir es lo que acota el rebaño;
    -- `acierto` — un DELETE por REST — es la devolución del provisional). El
    -- incremento es SIEMPRE upsert, nunca UPDATE a secas (ronda S6-M2): un
    -- `acierto` concurrente, que corre FUERA del advisory lock, puede borrar
    -- la fila sembrada entre (3) y aquí — con el upsert renace con fallos=1,
    -- que además es la verdad: ese fallo es POSTERIOR al acierto que limpió.
    -- La admisión nunca queda sin contar.
    INSERT INTO public.panel_intentos (clave, fallos, ultimo)
        SELECT t.c, 1, v_ahora FROM unnest(claves) AS t(c) ORDER BY t.c
        ON CONFLICT (clave) DO UPDATE
            SET fallos = public.panel_intentos.fallos + 1,
                ultimo = EXCLUDED.ultimo;
    RETURN 0;
END
$panel_puerta$;

-- El EXECUTE, nominal (el patrón s277/s299: revocar solo PUBLIC deja puestos
-- los defaults de Supabase sobre anon/authenticated).
REVOKE ALL ON FUNCTION public.panel_puerta(text[], int, numeric, numeric, numeric, int)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.panel_puerta(text[], int, numeric, numeric, numeric, int)
    TO service_role;

-- ----------------------------------------------------------------------------
-- FASE D — `panel_retencion_pasada`: el patrón s299, INSTANCIADO (v9 §6)
-- ----------------------------------------------------------------------------
-- No se AMPLÍA `rgpd_retencion_pasada` (su autocontrol afirma EXACTAMENTE 4
-- tablas, una política por tabla y el predicado de 24 meses; su recibo lleva
-- UN corte — es un contrato vivo endurecido por su propio dúo): se instancia
-- el patrón en una hermana pequeña con SU ventana y SU recibo. Mismas tres
-- piezas: corre como `rgpd_retencion` con el cinturón de current_user, aserta
-- SU mecanismo antes de tocar nada, y deja recibo en `rgpd_recibos` en la
-- misma transacción.
CREATE OR REPLACE FUNCTION public.panel_retencion_pasada(p_origen TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SET role = rgpd_retencion
SET search_path = public, pg_temp
AS $panel_pasada$
DECLARE
    -- INFORMATIVO (va al recibo). La ventana REAL la impone la política; esta
    -- expresión es la MISMA para que el recibo no mienta — si divergieran,
    -- manda la política (doctrina s299).
    v_corte  TIMESTAMPTZ := now() - interval '24 hours';
    v_conteo INTEGER;
BEGIN
    -- El cinturón del tirante: si el SET role del encabezado desapareciera,
    -- esto corta ANTES de tocar nada.
    IF current_user <> 'rgpd_retencion' THEN
        RAISE EXCEPTION 'panel_retencion: la pasada debe correr como '
                        'rgpd_retencion y corre como %. Abortado sin tocar nada.',
                        current_user;
    END IF;

    -- La ventana, ARMADA (el autocontrol del patrón s299, para ESTA tabla):
    -- RLS forzada + exactamente UNA política alcanza al rol + es LA de la
    -- ventana de 24 h. Sin esto, un DISABLE de debug o una política extra
    -- permisiva vaciarían la tabla con un recibo de aspecto normal.
    IF NOT EXISTS (
           SELECT 1 FROM pg_class c
            WHERE c.oid = to_regclass('public.panel_intentos')
              AND c.relrowsecurity AND c.relforcerowsecurity
       )
       OR (SELECT count(*) FROM pg_policies p
            WHERE p.schemaname = 'public' AND p.tablename = 'panel_intentos'
              AND ('rgpd_retencion' = ANY(p.roles) OR 'public' = ANY(p.roles))) <> 1
       OR NOT EXISTS (
           SELECT 1 FROM pg_policies p
            WHERE p.schemaname = 'public' AND p.tablename = 'panel_intentos'
              AND p.policyname = 'rgpd_retencion_ventana'
              AND 'rgpd_retencion' = ANY(p.roles)
              AND p.qual LIKE '%ultimo%'
              -- Acepta las dos representaciones equivalentes de '24 hours' que
              -- normaliza Postgres (ronda del dúo sobre el cableado, F-m2):
              -- '24:00:00' hoy, '1 day' si alguien reescribe la política con
              -- esa forma idéntica. Tirante por SEMÁNTICA, no por texto.
              AND (p.qual LIKE '%24:00:00%' OR p.qual LIKE '%1 day%')
       ) THEN
        RAISE EXCEPTION 'panel_retencion: la ventana NO esta armada en '
                        'panel_intentos (RLS deshabilitada, politica ausente o '
                        'alterada, o una politica EXTRA alcanza al rol). '
                        'Pasada abortada sin tocar nada.';
    END IF;

    -- El DELETE no lleva `ultimo < corte` A PROPÓSITO (doctrina s299): la
    -- ventana la impone la POLICY del rol — una sola fuente. Una fila dentro
    -- de plazo es intocable para este rol aunque este SQL tuviera un bug.
    DELETE FROM public.panel_intentos;
    GET DIAGNOSTICS v_conteo = ROW_COUNT;

    -- El recibo, en la MISMA transacción: toda fila persistida = pasada
    -- confirmada. Distinguible por su `resultado` (una sola clave,
    -- panel_intentos) — no toca el CHECK ni el contrato de la de 24 meses.
    INSERT INTO public.rgpd_recibos (origen, corte, resultado)
    VALUES (p_origen, v_corte,
            jsonb_build_object('panel_intentos',
                               jsonb_build_object('modo', 'purga_ventana_24h',
                                                  'tocadas', v_conteo)));

    RETURN jsonb_build_object('corte', to_jsonb(v_corte), 'origen', p_origen,
                              'panel_intentos', v_conteo);
END
$panel_pasada$;

-- REVOKE NOMINAL (ronda S4-M3/F4-M1 — la clase que s296→s299 sufrió VIVA en
-- producción: los defaults de Supabase conceden EXECUTE sobre toda función
-- nueva de `public`, y revocar solo PUBLIC los deja puestos). Solo el
-- operador (y el reloj, cuyo username puede asumir el rol) la ejecutan.
REVOKE ALL ON FUNCTION public.panel_retencion_pasada(TEXT)
    FROM PUBLIC, anon, authenticated, service_role;

-- ----------------------------------------------------------------------------
-- FASE E — EL RELOJ: diario (v9 §6, ronda S5-M1 — con red mensual una fila
-- escrita tras la pasada vivía ~31 días y «24 h» sobre-prometía). Condicional:
-- pg_cron no existe en el contenedor de CI (mismo gap declarado que la s299).
-- `cron.schedule` con el mismo jobname ACTUALIZA, no duplica.
-- ----------------------------------------------------------------------------
DO $s324j_reloj$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'panel-retencion-diaria',
            '45 4 * * *',
            $$SELECT public.panel_retencion_pasada('cron');$$
        );
    ELSE
        RAISE WARNING '019: pg_cron no disponible — el reloj diario NO queda '
                      'programado (esperado en CI; en Supabase debe quedar).';
    END IF;
END
$s324j_reloj$;

-- ----------------------------------------------------------------------------
-- FASE F — POSTCONDICIONES (si alguna falla, el aplicador transaccional
-- revierte el fichero ENTERO — ese es el contrato de aplicación)
-- ----------------------------------------------------------------------------
DO $s324j_post$
DECLARE
    v_malo TEXT;
BEGIN
    -- F.1 RLS + FORCE en las dos tablas.
    SELECT string_agg(t.tabla, ', ') INTO v_malo
      FROM unnest(ARRAY['panel_usuarios', 'panel_intentos']) AS t(tabla)
     WHERE NOT EXISTS (
               SELECT 1 FROM pg_class c
                WHERE c.oid = to_regclass(format('public.%I', t.tabla))
                  AND c.relrowsecurity AND c.relforcerowsecurity
           );
    IF v_malo IS NOT NULL THEN
        RAISE EXCEPTION '019: RLS/FORCE ausente en: %', v_malo;
    END IF;

    -- F.2 anon/authenticated sin NINGÚN privilegio sobre las tablas nuevas.
    IF EXISTS (
        SELECT 1 FROM information_schema.role_table_grants g
         WHERE g.table_schema = 'public'
           AND g.table_name IN ('panel_usuarios', 'panel_intentos')
           AND g.grantee IN ('anon', 'authenticated')
    ) OR EXISTS (
        SELECT 1 FROM information_schema.column_privileges c
         WHERE c.table_schema = 'public'
           AND c.table_name IN ('panel_usuarios', 'panel_intentos')
           AND c.grantee IN ('anon', 'authenticated')
    ) THEN
        RAISE EXCEPTION '019: anon/authenticated conservan privilegios sobre '
                        'las tablas del panel — el REVOKE no surtió efecto';
    END IF;

    -- F.3 service_role NO puede ejecutar la pasada de retención, y anon/
    -- authenticated no pueden ejecutar NINGUNA de las dos funciones.
    IF has_function_privilege('service_role',
           'public.panel_retencion_pasada(text)', 'EXECUTE')
       OR has_function_privilege('anon',
           'public.panel_retencion_pasada(text)', 'EXECUTE')
       OR has_function_privilege('authenticated',
           'public.panel_retencion_pasada(text)', 'EXECUTE')
       OR has_function_privilege('anon',
           'public.panel_puerta(text[], int, numeric, numeric, numeric, int)',
           'EXECUTE')
       OR has_function_privilege('authenticated',
           'public.panel_puerta(text[], int, numeric, numeric, numeric, int)',
           'EXECUTE') THEN
        RAISE EXCEPTION '019: el EXECUTE de las funciones del panel quedó '
                        'abierto a un rol que no debe tenerlo (defaults de '
                        'Supabase — el agujero de s296)';
    END IF;
    IF NOT has_function_privilege('service_role',
           'public.panel_puerta(text[], int, numeric, numeric, numeric, int)',
           'EXECUTE') THEN
        RAISE EXCEPTION '019: service_role NO puede ejecutar panel_puerta — '
                        'el cerrojo distribuido quedaría muerto';
    END IF;

    -- F.4 La ventana de retención, armada (misma aserción que ejecuta la
    -- pasada — verificada también aquí para que la migración no quede en
    -- verde con la política torcida).
    IF (SELECT count(*) FROM pg_policies p
         WHERE p.schemaname = 'public' AND p.tablename = 'panel_intentos') <> 1
       OR NOT EXISTS (
           SELECT 1 FROM pg_policies p
            WHERE p.schemaname = 'public' AND p.tablename = 'panel_intentos'
              AND p.policyname = 'rgpd_retencion_ventana'
              AND 'rgpd_retencion' = ANY(p.roles)
              AND p.qual LIKE '%ultimo%'
              AND (p.qual LIKE '%24:00:00%' OR p.qual LIKE '%1 day%')
       ) THEN
        RAISE EXCEPTION '019: la POLICY de ventana de panel_intentos no quedó '
                        'como se declaró';
    END IF;

    -- F.5 El reloj: si pg_cron está disponible, el job DEBE existir ACTIVO,
    -- con comando y horario exactos y un username que PUEDE asumir el rol
    -- (el patrón 4.4 de la s299 — imposible el «migración en verde sin
    -- programar nada» y el «job programado que fallará cada día»).
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF NOT EXISTS (
            SELECT 1 FROM cron.job j
             WHERE j.jobname = 'panel-retencion-diaria'
               AND j.command LIKE '%panel_retencion_pasada%'
               AND j.schedule = '45 4 * * *'
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
            RAISE EXCEPTION '019: el reloj diario no existe, esta inactivo, '
                            'cambio de horario/comando, o su username no puede '
                            'asumir rgpd_retencion';
        END IF;
    END IF;
END
$s324j_post$;

-- ----------------------------------------------------------------------------
-- FASE G — EXPONER EN LA API (la FASE D de la 016, que nació de DOS incidentes
-- reales: las tablas existían y PostgREST devolvía 404 desde su caché — y aquí
-- además hay funciones nuevas que el caché tiene que redescubrir). Idempotente.
-- ----------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';
