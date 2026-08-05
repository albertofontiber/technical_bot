-- ============================================================================
-- APLICADA EN PRODUCCIÓN el 5-ago-2026 (Alberto, SQL Editor; verificada contra el
-- catálogo). IDEMPOTENTE: re-ejecutarla es seguro y no-opea/re-afirma. Orden de la cola:
-- s295 → s296 → s297. En un entorno nuevo se aplica tras el bootstrap.
-- ============================================================================
-- s297 — cierra dos gaps declarados en s296 y uno descubierto al evaluar la taxonomía:
--
--   1. LIBRO DE EVENTOS DE CONSENTIMIENTO. El «append-only» de s296 conserva qué versión
--      aceptó cada uno, pero re-aceptar la MISMA versión pisa la fecha y limpia
--      `revoked_at`: se pierde la traza de que alguien revocó y cuándo. Patrón estándar
--      estado + libro: `user_consent` sigue siendo el estado vigente (lo que `has_consent`
--      necesita rápido) y `consent_events` es la EVIDENCIA — solo inserción, nada se pisa.
--   2. MARCA DE UTILIDAD EN EL CANAL ESPONTÁNEO. La marca vivía solo en `answer_feedback`
--      (el voto); la tabla `feedback` —donde el técnico escribe por su cuenta, y por donde
--      llega parte del feedback más valioso— no tenía dónde marcarse.
--
-- (El tercer gap de s296 —feedback perdible por FK colgante— se arregla en código:
-- reintento sin enlace en `log_feedback`, mismo patrón que el fallback de `log_query`.)
--
-- DEPENDENCIA: el preflight exige s296. Es una dependencia OPERATIVA, no técnica — nada de
-- aquí usa el rol ni el seudónimo. Se exige para que la cola de migraciones manuales tenga
-- UN solo orden documentado, que es el mismo en que las prueba juntas el CI.

BEGIN;

DO $s297_preflight$
BEGIN
    IF to_regclass('public.persona_seudonimo') IS NULL THEN
        RAISE EXCEPTION 's297: aplica ANTES 20260804120000_s296_seudonimo_y_calidad_v1.sql '
                        '(orden operativo unico de la cola, no dependencia tecnica)';
    END IF;
END
$s297_preflight$;

-- ---------------------------------------------------------------------------
-- 1. El libro de eventos
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.consent_events (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT NOT NULL,
    terms_version    TEXT NOT NULL,
    evento           TEXT NOT NULL CHECK (evento IN ('accepted', 'revoked')),
    -- Un evento reconstruido no es un evento presenciado: el libro los distingue para no
    -- fingir un histórico que el upsert antiguo destruyó.
    origen           TEXT NOT NULL DEFAULT 'runtime' CHECK (origen IN ('runtime', 'backfill')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_events_user
    ON public.consent_events (telegram_user_id, created_at);

ALTER TABLE public.consent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_events FORCE  ROW LEVEL SECURITY;

-- Mismo patrón que las demás tablas de datos personales: REVOKE **y** RLS (Supabase
-- concede TODO por defecto a anon/authenticated sobre las tablas nuevas de `public` —
-- lección de s296, cazada por el dúo).
REVOKE ALL PRIVILEGES ON TABLE public.consent_events
    FROM PUBLIC, anon, authenticated, service_role;

-- El bot ESCRIBE eventos y puede leerlos. Ni UPDATE ni DELETE para NADIE salvo el owner:
-- un libro de evidencia que se puede editar no es evidencia. La inmutabilidad aquí es
-- estructural (ausencia de privilegio), no una promesa de código.
GRANT SELECT, INSERT ON TABLE public.consent_events TO service_role;

-- BACKFILL declarado como RECONSTRUCCIÓN: el upsert antiguo destruyó el histórico, así que
-- el libro arranca con lo único que sobrevivió — el estado actual. Un evento 'accepted' por
-- fila viva (con su fecha real) y un 'revoked' donde conste revocación. Todo lo anterior
-- (v1..v6 pisadas) es irrecuperable y el libro NO lo finge.
-- CON GUARDA de re-ejecución (hallazgo del dúo): sin ella, un operador inseguro de si ya
-- aplicó la migración la re-corría, todo lo demás no-opeaba por idempotencia, y el backfill
-- RE-INSERTABA un 'accepted' por fila viva — COMMIT limpio, libro afirmando dos aceptaciones
-- donde hubo una, y la postcondición (que usaba >=) tragándoselo. Un libro cuya única razón
-- de ser es no mentir, corrompido en silencio. El gate: backfill solo sobre libro VACÍO.
DO $s297_backfill$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.consent_events) THEN
        INSERT INTO public.consent_events
            (telegram_user_id, terms_version, evento, origen, created_at)
        SELECT telegram_user_id, terms_version, 'accepted', 'backfill',
               COALESCE(accepted_at, NOW())
          FROM public.user_consent;
        INSERT INTO public.consent_events
            (telegram_user_id, terms_version, evento, origen, created_at)
        SELECT telegram_user_id, terms_version, 'revoked', 'backfill', revoked_at
          FROM public.user_consent
         WHERE revoked_at IS NOT NULL;
    END IF;
END
$s297_backfill$;

-- ---------------------------------------------------------------------------
-- 2. La marca de utilidad en el canal espontáneo
-- ---------------------------------------------------------------------------
-- Mismas cuatro categorías que en `answer_feedback` (auditables contra artefactos reales:
-- un commit, un gold, un manual adquirido). NULL = sin revisar ≠ 'ninguna' = revisado sin
-- consecuencia.
ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS utilidad TEXT,
    ADD COLUMN IF NOT EXISTS utilidad_revisada_at TIMESTAMPTZ;

DO $s297_utilidad_check$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'feedback_utilidad_check'
           AND conrelid = 'public.feedback'::regclass
    ) THEN
        ALTER TABLE public.feedback
            ADD CONSTRAINT feedback_utilidad_check
            CHECK (utilidad IS NULL OR utilidad IN ('corrigio', 'gold', 'corpus', 'ninguna'));
    END IF;
END
$s297_utilidad_check$;

-- El UPDATE ya estaba cerrado (hardening de julio), pero el dúo cazó el flanco que quedaba
-- abierto: `service_role` conservaba INSERT **de tabla**, que cubre TODA columna — incluida
-- la marca. El bot podía INSERTAR una fila nueva con `utilidad` ya puesta. Se sustituye por
-- INSERT de COLUMNA sobre exactamente lo que el bot escribe, aquí y en `answer_feedback`
-- (mismo agujero, heredado de s296).
REVOKE INSERT ON TABLE public.feedback FROM service_role;
GRANT INSERT (telegram_user_id, feedback_text, previous_query, previous_response, query_log_id)
    ON public.feedback TO service_role;

REVOKE INSERT ON TABLE public.answer_feedback FROM service_role;
GRANT INSERT (query_log_id, telegram_user_id, verdict)
    ON public.answer_feedback TO service_role;

-- M6 del dúo: la coherencia NULL≠ninguna no estaba gobernada — cabía una marca sin fecha de
-- revisión, o una fecha sin marca. O las dos o ninguna, en ambas tablas.
DO $s297_coherencia$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'feedback_utilidad_coherente') THEN
        ALTER TABLE public.feedback ADD CONSTRAINT feedback_utilidad_coherente
            CHECK ((utilidad IS NULL) = (utilidad_revisada_at IS NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'answer_feedback_utilidad_coherente') THEN
        ALTER TABLE public.answer_feedback ADD CONSTRAINT answer_feedback_utilidad_coherente
            CHECK ((utilidad IS NULL) = (utilidad_revisada_at IS NULL));
    END IF;
END
$s297_coherencia$;

-- ---------------------------------------------------------------------------
-- 3. Postcondiciones
-- ---------------------------------------------------------------------------
DO $s297_post$
DECLARE
    rol TEXT;
    priv TEXT;
BEGIN
    -- 3.1 El libro es de solo inserción para el bot: sin UPDATE/DELETE ni de tabla ni de
    --     columna. La evidencia editable no es evidencia.
    FOREACH priv IN ARRAY ARRAY['UPDATE', 'DELETE', 'TRUNCATE'] LOOP
        IF has_table_privilege('service_role', 'public.consent_events', priv) THEN
            RAISE EXCEPTION 's297: service_role tiene % sobre consent_events', priv;
        END IF;
    END LOOP;
    IF has_any_column_privilege('service_role', 'public.consent_events', 'UPDATE') THEN
        RAISE EXCEPTION 's297: service_role tiene UPDATE de columna sobre consent_events';
    END IF;
    IF NOT has_table_privilege('service_role', 'public.consent_events', 'INSERT')
       OR NOT has_table_privilege('service_role', 'public.consent_events', 'SELECT') THEN
        RAISE EXCEPTION 's297: service_role no puede escribir/leer el libro';
    END IF;

    -- 3.2 Ningún rol anónimo lo toca (y RLS forzada) — los 8 privilegios de tabla y los de
    --     columna, patrón de igualdad de la casa (S4 del dúo: una postcondición más estrecha
    --     que el REVOKE deja pasar regresiones futuras que el REVOKE de hoy no cubre).
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                                    'REFERENCES', 'TRIGGER', 'MAINTAIN'] LOOP
            IF has_table_privilege(rol, 'public.consent_events', priv) THEN
                RAISE EXCEPTION 's297: % tiene % sobre consent_events', rol, priv;
            END IF;
        END LOOP;
        FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'REFERENCES'] LOOP
            IF has_any_column_privilege(rol, 'public.consent_events', priv) THEN
                RAISE EXCEPTION 's297: % tiene % de columna sobre consent_events', rol, priv;
            END IF;
        END LOOP;
    END LOOP;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
         WHERE oid = 'public.consent_events'::regclass
           AND relrowsecurity AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 's297: RLS no esta habilitada Y forzada en consent_events';
    END IF;

    -- 3.3 El backfill dejó el libro consistente con el estado — IGUALDAD, no >=: o corrió
    --     completo sobre libro vacío (== filas del estado) o no corrió (0, re-ejecución).
    --     Cualquier otro valor es un backfill parcial o duplicado.
    IF (SELECT count(*) FROM public.consent_events
         WHERE origen = 'backfill' AND evento = 'accepted')
       NOT IN (0, (SELECT count(*) FROM public.user_consent)) THEN
        RAISE EXCEPTION 's297: backfill parcial o duplicado -- el libro no puede mentir';
    END IF;

    -- 3.4 La marca del canal espontáneo existe y el bot NO puede escribirla — ni por
    --     UPDATE ni por el flanco que el dúo cazó: INSERT de tabla, que cubre toda columna.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='feedback' AND column_name='utilidad'
    ) THEN
        RAISE EXCEPTION 's297: feedback sigue sin columna utilidad';
    END IF;
    IF has_table_privilege('service_role', 'public.feedback', 'UPDATE')
       OR has_any_column_privilege('service_role', 'public.feedback', 'UPDATE') THEN
        RAISE EXCEPTION 's297: service_role puede escribir en feedback -- la marca quedaria '
                        'al alcance del canal del interesado';
    END IF;
    IF has_table_privilege('service_role', 'public.feedback', 'INSERT')
       OR has_table_privilege('service_role', 'public.answer_feedback', 'INSERT') THEN
        RAISE EXCEPTION 's297: service_role conserva INSERT de TABLA -- podria insertar una '
                        'fila con la marca ya puesta';
    END IF;
    IF has_column_privilege('service_role', 'public.feedback', 'utilidad', 'INSERT')
       OR has_column_privilege('service_role', 'public.answer_feedback', 'utilidad', 'INSERT')
       OR has_column_privilege('service_role', 'public.feedback',
                               'utilidad_revisada_at', 'INSERT')
       OR has_column_privilege('service_role', 'public.answer_feedback',
                               'utilidad_revisada_at', 'INSERT') THEN
        RAISE EXCEPTION 's297: service_role puede INSERTAR la marca';
    END IF;
    -- ...pero lo que el bot SÍ escribe tiene que seguir funcionando.
    IF NOT has_column_privilege('service_role', 'public.feedback', 'feedback_text', 'INSERT')
       OR NOT has_column_privilege('service_role', 'public.answer_feedback',
                                   'verdict', 'INSERT') THEN
        RAISE EXCEPTION 's297: se ha roto la escritura normal de feedback/voto';
    END IF;
END
$s297_post$;

COMMIT;

-- ---------------------------------------------------------------------------
-- BOOTSTRAP (`supabase_schema.sql`)
-- ---------------------------------------------------------------------------
-- Al aplicar, replicar en el bootstrap: la tabla + índice + RLS/FORCE + REVOKE + GRANT
-- SELECT,INSERT a service_role, y las dos columnas de `feedback` con su CHECK. Sin tocar
-- sus postcondiciones de `feedback` (siguen esperando SELECT+INSERT, que no cambia).
--
-- RESIDUAL DECLARADO (S6 del dúo): el CI conecta como `postgres` SUPERUSER, que ignora
-- incluso FORCE RLS, así que ningún test observa la RLS de esta tabla para el camino del
-- operador. La inmutabilidad frente al BOT sí se ejerce de verdad (ausencia de GRANT,
-- ejecutada como service_role); el residuo es solo el camino operador, ruidoso si fallara.

-- ---------------------------------------------------------------------------
-- RETENCIÓN DEL PROPIO LIBRO (declarado, no cableado)
-- ---------------------------------------------------------------------------
-- `consent_events` contiene `telegram_user_id`: ES dato personal. Su plazo sigue la misma
-- decisión pendiente que `user_consent` (la prueba del consentimiento se conserva mientras
-- se traten datos de esa persona); por eso queda FUERA de `rgpd_quedan_identificados()`,
-- como `user_consent` — si contase, el vínculo no se destruiría jamás. Fila nueva en la
-- matriz (`docs/RGPD_RETENCION.md`).
--
-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   DROP TABLE public.consent_events;
--   ALTER TABLE public.feedback DROP CONSTRAINT IF EXISTS feedback_utilidad_check;
--   ALTER TABLE public.feedback DROP COLUMN IF EXISTS utilidad,
--                               DROP COLUMN IF EXISTS utilidad_revisada_at;
-- Reversible sin pérdida estructural; se pierde la evidencia acumulada en el libro.
