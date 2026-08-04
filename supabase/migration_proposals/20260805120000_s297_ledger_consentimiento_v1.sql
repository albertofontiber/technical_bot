-- ============================================================================
-- PROPUESTA NO APLICADA. Se aplica DESPUÉS de
-- `20260804120000_s296_seudonimo_y_calidad_v1.sql` (tercera de la cola: s295 → s296 → s297).
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
INSERT INTO public.consent_events (telegram_user_id, terms_version, evento, created_at)
SELECT telegram_user_id, terms_version, 'accepted', COALESCE(accepted_at, NOW())
  FROM public.user_consent;
INSERT INTO public.consent_events (telegram_user_id, terms_version, evento, created_at)
SELECT telegram_user_id, terms_version, 'revoked', revoked_at
  FROM public.user_consent
 WHERE revoked_at IS NOT NULL;

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

-- Aquí NO hay que retirar ningún privilegio: `service_role` no tiene UPDATE sobre
-- `feedback` desde el hardening de julio, así que el bot ya no puede escribir la marca.
-- La escribe el operador (postgres) al revisar, igual que en `answer_feedback`.

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

    -- 3.2 Ningún rol anónimo lo toca (y RLS forzada).
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
            IF has_table_privilege(rol, 'public.consent_events', priv) THEN
                RAISE EXCEPTION 's297: % tiene % sobre consent_events', rol, priv;
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

    -- 3.3 El backfill dejó el libro consistente con el estado.
    IF (SELECT count(*) FROM public.consent_events WHERE evento = 'accepted')
       < (SELECT count(*) FROM public.user_consent) THEN
        RAISE EXCEPTION 's297: el backfill no cubrio todas las aceptaciones vivas';
    END IF;

    -- 3.4 La marca del canal espontáneo existe y el bot NO puede escribirla.
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
