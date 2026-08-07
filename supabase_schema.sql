-- Technical Bot PCI - Supabase Schema
-- Run this in the Supabase SQL Editor to set up the database
-- This is the FULL schema — safe to run on a fresh database (all IF NOT EXISTS)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    content_type TEXT,  -- procedure, specification, troubleshooting, wiring, general
    manufacturer TEXT,  -- e.g. Detnov, Notifier, Honeywell (must be set explicitly)
    has_diagram BOOLEAN DEFAULT FALSE,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity search index (increase lists for >100K chunks)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indexes for metadata filtering
CREATE INDEX IF NOT EXISTS idx_chunks_product_model ON chunks (product_model);
CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks (category);
CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks (content_type);
CREATE INDEX IF NOT EXISTS idx_chunks_manufacturer ON chunks (manufacturer);

-- RPC function for vector similarity search with manufacturer filter
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    content_type TEXT,
    has_diagram BOOLEAN,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    manufacturer TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.product_model,
        c.category,
        c.section_title,
        c.content_type,
        c.has_diagram,
        c.diagram_url,
        c.source_file,
        c.page_number,
        c.manufacturer,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE
        1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Keep creation and hardening of all personal-data tables in one transaction.
-- On a fresh bootstrap, a failed postcondition cannot leave an exposed table
-- committed by an autocommit client.
BEGIN;

-- Query logs for analytics and improvement
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    query TEXT NOT NULL,
    source TEXT DEFAULT 'text',  -- 'text' or 'voice'
    transcription TEXT,          -- original transcription if voice
    product_models TEXT[],       -- models detected in query
    category TEXT,               -- category detected
    chunks_used INTEGER DEFAULT 0,
    response TEXT,               -- full response sent (truncated to 4096 chars, Telegram limit)
    response_length INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    bot_version TEXT,            -- git short hash or tag of code that generated this row
    rag_trace JSONB,
    route TEXT,                  -- s301: canal de la respuesta (rag o shortcut); NULL = pre-s301
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS rag_trace JSONB;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS route TEXT;
DO $route_check$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'query_logs_route_check'
           AND conrelid = 'public.query_logs'::regclass
    ) THEN
        ALTER TABLE query_logs ADD CONSTRAINT query_logs_route_check
            CHECK (route IS NULL OR route IN (
                'rag', 'catalog_shortcut', 'manufacturer_mismatch',
                'manufacturer_no_model', 'clarify', 'decline',
                -- reservados: el aviso v7 promete no registrar cortesia (duo s301)
                'greeting', 'thanks', 'bye'
            ));
    END IF;
END
$route_check$;
-- One DO statement is atomic even when this bootstrap is run with autocommit:
-- a failed ADD rolls the DROP back instead of leaving the table unbounded.
DO $rag_trace_constraint$
BEGIN
    ALTER TABLE public.query_logs
        DROP CONSTRAINT IF EXISTS query_logs_rag_trace_object_size_v1;
    ALTER TABLE public.query_logs
        ADD CONSTRAINT query_logs_rag_trace_object_size_v1
        CHECK (
            rag_trace IS NULL
            OR (
                jsonb_typeof(rag_trace) = 'object'
                AND octet_length(rag_trace::text) <= 8192
            )
        );
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'query_logs'
          AND column_name = 'rag_trace'
          AND data_type = 'jsonb'
          AND is_nullable = 'YES'
          AND column_default IS NULL
          AND is_identity = 'NO'
          AND is_generated = 'NEVER'
    ) THEN
        RAISE EXCEPTION 'query_logs.rag_trace must be plain nullable jsonb';
    END IF;
END
$rag_trace_constraint$;

CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_user ON query_logs (telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_bot_version ON query_logs (bot_version);

-- Feedback from technicians
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    feedback_text TEXT NOT NULL,
    previous_query TEXT,         -- the query they're giving feedback on
    previous_response TEXT,      -- the response they're correcting
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback (created_at DESC);

-- Structured 1-tap answer feedback (👍/👎), exact-linked to its query_logs row
-- via FK. Coexists with `feedback` (spontaneous free-text) — disjoint roles
-- (s286): this table stores verdicts, `feedback` stores prose. ON DELETE
-- CASCADE keeps the documented RGPD deletion (`DELETE FROM query_logs WHERE
-- telegram_user_id = X`, DG_DEPLOYMENT) working without extra steps. The
-- UNIQUE pair makes taps idempotent and lets an upsert implement last-wins
-- verdict toggles (👍→👎). created_at keeps the FIRST vote's timestamp: the
-- upsert only updates supplied columns and never resends created_at.
CREATE TABLE IF NOT EXISTS answer_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('up', 'down')),
    comment TEXT,                -- texto libre: GATEADO por la matriz de retención RGPD
    -- s294 (#60 punto 5): motivo del 👎 en clases cerradas que mapean ~1:1 a la
    -- taxonomía del instrumento (omitted/contradicted/scope) => cada 👎 con motivo
    -- es un caso diagnosticable y semilla de eval orgánico.
    reason_class TEXT CHECK (reason_class IS NULL OR reason_class IN (
        'info', 'wrong', 'scope', 'other'
    )),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (query_log_id, telegram_user_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_feedback_created
ON answer_feedback (created_at DESC);

-- s294 (#60 punto 1): ancla message_id -> query_log_id. Tabla PUENTE (no columna en
-- query_logs) porque una respuesta se envia PARTIDA en N mensajes: una columna solo
-- anclaria uno y las reacciones sobre el resto se perderian. Muere en cascada con su
-- query_log (retencion RGPD).
CREATE TABLE IF NOT EXISTS answer_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,
    telegram_message_id BIGINT NOT NULL,
    part_index SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (telegram_chat_id, telegram_message_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_messages_query_log
ON answer_messages (query_log_id);

-- RGPD consent tracking (one row per user who accepted terms via /accept)
CREATE TABLE IF NOT EXISTS user_consent (
    telegram_user_id BIGINT PRIMARY KEY,
    display_name TEXT,           -- optional, user-provided in /accept
    terms_version TEXT NOT NULL, -- e.g. "v1" — bump if terms change
    accepted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ       -- NULL while consent is active
);

CREATE INDEX IF NOT EXISTS idx_user_consent_active
ON user_consent (telegram_user_id)
WHERE revoked_at IS NULL;

-- Columnas s296/s297 sobre las tablas del bot — MISMAS sentencias idempotentes que las
-- migraciones de la cola (mismos nombres de constraint): aplicar bootstrap y cola en
-- cualquier orden converge al mismo estado. El resto de la maquinaria de retención (rol
-- `rgpd_retencion`, `persona_seudonimo`, `consent_events`, políticas, trigger) tiene UNA
-- fuente: la cola `supabase/migration_proposals/` (s295 → s296 → s297). Entorno nuevo =
-- este bootstrap Y DESPUÉS la cola; sin la cola, el bot funciona y la retención dice
-- honestamente que no puede (exit 2).
-- s296: `/accept` upserta con ON CONFLICT (telegram_user_id, terms_version) — sin este
-- indice, el upsert falla con 42P10 y el gate de consentimiento (fail-closed) no deja
-- entrar a NADIE. Lo cazo el sub-agente: el criterio «lo que el bot escribe va al
-- bootstrap» incluye los INDICES que sus upserts exigen, no solo las columnas.
DO $bootstrap_consent$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='user_consent' AND column_name='id'
    ) THEN
        ALTER TABLE user_consent ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid();
        ALTER TABLE user_consent DROP CONSTRAINT IF EXISTS user_consent_pkey;
        ALTER TABLE user_consent ADD PRIMARY KEY (id);
    END IF;
END
$bootstrap_consent$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_consent_persona_version
    ON user_consent (telegram_user_id, terms_version);

ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS query_log_id UUID REFERENCES query_logs(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS utilidad TEXT,
    ADD COLUMN IF NOT EXISTS utilidad_revisada_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_feedback_query_log ON feedback (query_log_id);
ALTER TABLE answer_feedback
    ADD COLUMN IF NOT EXISTS comment TEXT,
    ADD COLUMN IF NOT EXISTS reason_class TEXT,
    ADD COLUMN IF NOT EXISTS utilidad TEXT,
    ADD COLUMN IF NOT EXISTS utilidad_revisada_at TIMESTAMPTZ;
DO $bootstrap_reason$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'answer_feedback_reason_class_check'
                      AND conrelid = 'public.answer_feedback'::regclass) THEN
        ALTER TABLE answer_feedback ADD CONSTRAINT answer_feedback_reason_class_check
            CHECK (reason_class IS NULL OR reason_class IN ('info', 'wrong', 'scope', 'other'));
    END IF;
END
$bootstrap_reason$;
DO $bootstrap_utilidad$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'feedback_utilidad_check'
                      AND conrelid = 'public.feedback'::regclass) THEN
        ALTER TABLE feedback ADD CONSTRAINT feedback_utilidad_check
            CHECK (utilidad IS NULL OR utilidad IN ('corrigio', 'gold', 'corpus', 'ninguna'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'feedback_utilidad_coherente'
                      AND conrelid = 'public.feedback'::regclass) THEN
        ALTER TABLE feedback ADD CONSTRAINT feedback_utilidad_coherente
            CHECK ((utilidad IS NULL) = (utilidad_revisada_at IS NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'answer_feedback_utilidad_check') THEN
        ALTER TABLE answer_feedback ADD CONSTRAINT answer_feedback_utilidad_check
            CHECK (utilidad IS NULL OR utilidad IN ('corrigio', 'gold', 'corpus', 'ninguna'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'answer_feedback_utilidad_coherente') THEN
        ALTER TABLE answer_feedback ADD CONSTRAINT answer_feedback_utilidad_coherente
            CHECK ((utilidad IS NULL) = (utilidad_revisada_at IS NULL));
    END IF;
END
$bootstrap_utilidad$;

-- Personal-data boundary for a fresh bootstrap.
-- Sincronizado con la COLA COMPLETA: 20260713164800 (hardening) + s295/s296/s297
-- (migration_proposals). ESTADO FINAL, no el intermedio: la versión anterior de este
-- bloque re-concedía a `service_role` el INSERT de tabla en feedback/answer_feedback y el
-- UPDATE de tabla en answer_feedback — re-ejecutar el bootstrap DESHACÍA en silencio la
-- protección de la marca de utilidad (la clase de fallo s296, cazada por el dúo). Ahora
-- re-ejecutarlo re-AFIRMA las garantías, y el CI lo ejerce (test de re-ejecución del
-- bloque tras la cola). Los marcadores delimitan el bloque que el test extrae.
-- >>> RGPD-BOUNDARY-BEGIN <<<
DO $personal_data_boundary$
DECLARE
    table_name text;
    role_name text;
    privilege_name text;
    expected_table_privs text[];
    expected_column_privs text[];
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before hardening';
    END IF;

    FOREACH table_name IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages',
        'user_consent'
    ]
    LOOP
        EXECUTE format(
            'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name
        );
        EXECUTE format(
            'ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name
        );
        EXECUTE format(
            'REVOKE ALL PRIVILEGES ON TABLE public.%I '
            'FROM PUBLIC, anon, authenticated, service_role',
            table_name
        );
    END LOOP;

    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.query_logs TO service_role';
    -- feedback y answer_feedback: INSERT/UPDATE de COLUMNA, nunca de tabla. El INSERT de
    -- tabla cubre TODA columna — incluida `utilidad`, la marca en que se apoyaría un bonus,
    -- que no puede ser escribible desde el canal por el que habla el interesado (s296/s297).
    EXECUTE 'GRANT SELECT ON TABLE public.feedback TO service_role';
    EXECUTE 'GRANT INSERT (telegram_user_id, feedback_text, previous_query, '
            'previous_response, query_log_id) ON public.feedback TO service_role';
    EXECUTE 'GRANT SELECT ON TABLE public.answer_feedback TO service_role';
    EXECUTE 'GRANT INSERT (query_log_id, telegram_user_id, verdict) '
            'ON public.answer_feedback TO service_role';
    EXECUTE 'GRANT UPDATE (telegram_user_id, query_log_id, verdict, comment, reason_class) '
            'ON public.answer_feedback TO service_role';
    -- answer_messages: el bot INSERTA al enviar y LEE al recibir una reaccion.
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.answer_messages TO service_role';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.user_consent TO service_role';

    -- Tablas de la cola de retención, si existen (tras aplicar s296/s297): re-AFIRMAR su
    -- frontera para que una re-ejecución del bootstrap nunca las deje más abiertas. Sus
    -- grants a `rgpd_retencion` no se tocan (el REVOKE nombra roles concretos).
    IF to_regclass('public.persona_seudonimo') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.persona_seudonimo ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE public.persona_seudonimo FORCE ROW LEVEL SECURITY';
        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.persona_seudonimo '
                'FROM PUBLIC, anon, authenticated, service_role';
        EXECUTE 'GRANT SELECT, INSERT ON TABLE public.persona_seudonimo TO service_role';
    END IF;
    IF to_regclass('public.consent_events') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.consent_events ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE public.consent_events FORCE ROW LEVEL SECURITY';
        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.consent_events '
                'FROM PUBLIC, anon, authenticated, service_role';
        EXECUTE 'GRANT SELECT, INSERT ON TABLE public.consent_events TO service_role';
    END IF;
    -- s299: recibos de retención y función de la pasada, si existen. A diferencia de las
    -- dos de arriba, aquí el bot NO recupera NADA: los recibos son evidencia de operación
    -- y la pasada solo la ejecuta el operador (su INSERT/EXECUTE viven en grants a
    -- rgpd_retencion/owner, que este REVOKE nominal no toca).
    IF to_regclass('public.rgpd_recibos') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.rgpd_recibos ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE public.rgpd_recibos FORCE ROW LEVEL SECURITY';
        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.rgpd_recibos '
                'FROM PUBLIC, anon, authenticated, service_role';
    END IF;
    -- NOMINAL, no solo PUBLIC: los default privileges de Supabase conceden EXECUTE a
    -- anon/authenticated/service_role sobre toda función nueva de `public` (verificado
    -- contra pg_default_acl de producción, s299). El REVOKE nominal no toca los grants
    -- a rgpd_retencion.
    IF to_regprocedure('public.rgpd_retencion_pasada(text)') IS NOT NULL THEN
        EXECUTE 'REVOKE ALL ON FUNCTION public.rgpd_retencion_pasada(TEXT) '
                'FROM PUBLIC, anon, authenticated, service_role';
    END IF;
    IF to_regprocedure('public.rgpd_quedan_identificados(bigint)') IS NOT NULL THEN
        EXECUTE 'REVOKE ALL ON FUNCTION public.rgpd_quedan_identificados(BIGINT) '
                'FROM PUBLIC, anon, authenticated, service_role';
    END IF;

    FOREACH table_name IN ARRAY ARRAY[
        'query_logs', 'feedback', 'answer_feedback', 'answer_messages',
        'user_consent'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = to_regclass(format('public.%I', table_name))
              AND relrowsecurity
              AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'personal-data RLS invariant failed for %', table_name;
        END IF;

        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
        LOOP
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                'REFERENCES', 'TRIGGER', 'MAINTAIN'
            ]
            LOOP
                IF has_table_privilege(
                    role_name,
                    format('public.%I', table_name),
                    privilege_name
                ) THEN
                    RAISE EXCEPTION 'unexpected % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
            ]
            LOOP
                IF has_any_column_privilege(
                    role_name,
                    format('public.%I', table_name),
                    privilege_name
                ) THEN
                    RAISE EXCEPTION 'unexpected column % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
        END LOOP;

        -- Estado FINAL por tabla: privilegios de TABLA y de COLUMNA por separado (un grant
        -- de columna no enciende has_table_privilege, pero sí has_any_column_privilege).
        IF table_name = 'user_consent' THEN
            expected_table_privs  := ARRAY['SELECT', 'INSERT', 'UPDATE'];
            expected_column_privs := ARRAY['SELECT', 'INSERT', 'UPDATE'];
        ELSIF table_name = 'feedback' THEN
            expected_table_privs  := ARRAY['SELECT'];
            expected_column_privs := ARRAY['SELECT', 'INSERT'];
        ELSIF table_name = 'answer_feedback' THEN
            expected_table_privs  := ARRAY['SELECT'];
            expected_column_privs := ARRAY['SELECT', 'INSERT', 'UPDATE'];
        ELSE
            expected_table_privs  := ARRAY['SELECT', 'INSERT'];
            expected_column_privs := ARRAY['SELECT', 'INSERT'];
        END IF;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ]
        LOOP
            IF has_table_privilege(
                'service_role',
                format('public.%I', table_name),
                privilege_name
            ) IS DISTINCT FROM (privilege_name = ANY(expected_table_privs)) THEN
                RAISE EXCEPTION 'unexpected service_role % privilege on %',
                    privilege_name, table_name;
            END IF;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
        ]
        LOOP
            IF has_any_column_privilege(
                'service_role',
                format('public.%I', table_name),
                privilege_name
            ) IS DISTINCT FROM (privilege_name = ANY(expected_column_privs)) THEN
                RAISE EXCEPTION 'unexpected service_role column % privilege on %',
                    privilege_name, table_name;
            END IF;
        END LOOP;
    END LOOP;

    -- Positivas NOMINALES: cada columna que el bot escribe, comprobada UNA a UNA.
    -- `has_any_column_privilege` solo prueba que existe ALGUN grant; con esto, una lista
    -- recortada (p.ej. sin `reason_class`) no pasa el bootstrap.
    FOREACH privilege_name IN ARRAY ARRAY[
        'telegram_user_id', 'feedback_text', 'previous_query', 'previous_response',
        'query_log_id'
    ] LOOP
        IF NOT has_column_privilege('service_role', 'public.feedback',
                                    privilege_name, 'INSERT') THEN
            RAISE EXCEPTION 'service_role cannot INSERT feedback.%', privilege_name;
        END IF;
    END LOOP;
    FOREACH privilege_name IN ARRAY ARRAY['query_log_id', 'telegram_user_id', 'verdict'] LOOP
        IF NOT has_column_privilege('service_role', 'public.answer_feedback',
                                    privilege_name, 'INSERT') THEN
            RAISE EXCEPTION 'service_role cannot INSERT answer_feedback.%', privilege_name;
        END IF;
    END LOOP;
    FOREACH privilege_name IN ARRAY ARRAY[
        'telegram_user_id', 'query_log_id', 'verdict', 'comment', 'reason_class'
    ] LOOP
        IF NOT has_column_privilege('service_role', 'public.answer_feedback',
                                    privilege_name, 'UPDATE') THEN
            RAISE EXCEPTION 'service_role cannot UPDATE answer_feedback.%', privilege_name;
        END IF;
    END LOOP;

    -- LA MARCA, nominalmente: ni INSERT ni UPDATE para el bot, en ninguna de las dos
    -- tablas. Es la postcondición que convierte una regresión futura en un fallo ruidoso.
    FOREACH table_name IN ARRAY ARRAY['feedback', 'answer_feedback'] LOOP
        FOREACH privilege_name IN ARRAY ARRAY['INSERT', 'UPDATE'] LOOP
            IF has_column_privilege('service_role', format('public.%I', table_name),
                                    'utilidad', privilege_name)
               OR has_column_privilege('service_role', format('public.%I', table_name),
                                       'utilidad_revisada_at', privilege_name) THEN
                RAISE EXCEPTION 'service_role can % the utilidad mark on % -- the bonus '
                                'datum must not be writable from the bot channel',
                    privilege_name, table_name;
            END IF;
        END LOOP;
    END LOOP;

    -- Las dos tablas de la cola, si existen: MISMO listón que las cinco fijas — RLS
    -- forzada, roles anónimos a cero (tabla y columna), e igualdad exacta para el bot.
    -- Sin esto, «re-afirma su frontera» declaraba más de lo comprobado (dúo, s298).
    FOREACH table_name IN ARRAY ARRAY['persona_seudonimo', 'consent_events'] LOOP
        IF to_regclass(format('public.%I', table_name)) IS NULL THEN
            CONTINUE;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
             WHERE oid = to_regclass(format('public.%I', table_name))
               AND relrowsecurity AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'personal-data RLS invariant failed for %', table_name;
        END IF;
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                'REFERENCES', 'TRIGGER', 'MAINTAIN'
            ] LOOP
                IF has_table_privilege(role_name, format('public.%I', table_name),
                                       privilege_name) THEN
                    RAISE EXCEPTION 'unexpected % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
            FOREACH privilege_name IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'REFERENCES'] LOOP
                IF has_any_column_privilege(role_name, format('public.%I', table_name),
                                            privilege_name) THEN
                    RAISE EXCEPTION 'unexpected column % privilege for % on %',
                        privilege_name, role_name, table_name;
                END IF;
            END LOOP;
        END LOOP;
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ] LOOP
            IF has_table_privilege('service_role', format('public.%I', table_name),
                                   privilege_name)
               IS DISTINCT FROM (privilege_name = ANY(ARRAY['SELECT', 'INSERT'])) THEN
                RAISE EXCEPTION 'unexpected service_role % privilege on %',
                    privilege_name, table_name;
            END IF;
        END LOOP;
        IF has_any_column_privilege('service_role', format('public.%I', table_name), 'UPDATE') THEN
            RAISE EXCEPTION 'service_role must not UPDATE any column of %', table_name;
        END IF;
    END LOOP;

    -- s299: los recibos de retención, si existen — API a CERO, service_role INCLUIDO
    -- (aquí no hay «lo que el bot escribe»: no escribe nada).
    IF to_regclass('public.rgpd_recibos') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
             WHERE oid = to_regclass('public.rgpd_recibos')
               AND relrowsecurity AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'personal-data RLS invariant failed for rgpd_recibos';
        END IF;
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                'REFERENCES', 'TRIGGER', 'MAINTAIN'
            ] LOOP
                IF has_table_privilege(role_name, 'public.rgpd_recibos', privilege_name) THEN
                    RAISE EXCEPTION 'unexpected % privilege for % on rgpd_recibos',
                        privilege_name, role_name;
                END IF;
            END LOOP;
            FOREACH privilege_name IN ARRAY ARRAY[
                'SELECT', 'INSERT', 'UPDATE', 'REFERENCES'
            ] LOOP
                IF has_any_column_privilege(role_name, 'public.rgpd_recibos',
                                            privilege_name) THEN
                    RAISE EXCEPTION 'unexpected column % privilege for % on rgpd_recibos',
                        privilege_name, role_name;
                END IF;
            END LOOP;
        END LOOP;
    END IF;
    -- ...y ni la pasada ni el oráculo de pertenencia son alcanzables desde la API.
    IF to_regprocedure('public.rgpd_retencion_pasada(text)') IS NOT NULL THEN
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF has_function_privilege(role_name, 'public.rgpd_retencion_pasada(text)',
                                      'EXECUTE') THEN
                RAISE EXCEPTION '% can execute the retention pass', role_name;
            END IF;
        END LOOP;
    END IF;
    IF to_regprocedure('public.rgpd_quedan_identificados(bigint)') IS NOT NULL THEN
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF has_function_privilege(role_name,
                                      'public.rgpd_quedan_identificados(bigint)',
                                      'EXECUTE') THEN
                RAISE EXCEPTION '% can execute the membership oracle', role_name;
            END IF;
        END LOOP;
    END IF;
END
$personal_data_boundary$;
-- >>> RGPD-BOUNDARY-END <<<

COMMIT;

-- Bot-health views (s286). security_invoker: the view runs with the CALLER's
-- privileges, so the FORCE-RLS + revoked grants of query_logs keep applying —
-- anon/authenticated get permission-denied instead of a definer bypass. Static
-- predicates only: 'error' rows and 'direct' replies are excluded from RAG
-- volume here; the env-driven dogfooding exclusion (INTERNAL_TELEGRAM_IDS)
-- lives ONLY in scripts/bot_health_report.py — single source, views stay
-- unsegmented (s286 dúo r2). % no-info is a DECLARED HEURISTIC (the bot's
-- admit-no-info is free LLM prose; these prefixes are its common openers) and
-- the transport-error bucket counts the fixed _EMPTY_ANSWER_FALLBACK.
-- response_time_ms is PIPELINE latency (measured before Telegram send).
CREATE OR REPLACE VIEW bot_health_daily
WITH (security_invoker = true) AS
SELECT
    created_at::date AS dia,
    bot_version,
    COUNT(*) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS consultas_rag,
    COUNT(DISTINCT telegram_user_id) FILTER (
        WHERE source <> 'error'
    ) AS usuarios_unicos,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS latencia_pipeline_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS latencia_pipeline_p95_ms,
    COUNT(*) FILTER (
        WHERE source <> 'error'
          AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
          AND (response ILIKE 'No tengo información%'
               OR response ILIKE 'No dispongo%')
    ) AS no_info_heuristica,
    COUNT(*) FILTER (
        WHERE response LIKE 'No he podido generar una respuesta completa%'
    ) AS errores_transporte,
    COUNT(*) FILTER (WHERE source = 'error') AS filas_error
FROM query_logs
GROUP BY created_at::date, bot_version;

CREATE OR REPLACE VIEW bot_health_semanal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    COUNT(*) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS consultas_rag,
    COUNT(DISTINCT telegram_user_id) FILTER (
        WHERE source <> 'error'
    ) AS usuarios_unicos,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS latencia_pipeline_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) FILTER (
        WHERE source <> 'error' AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
    ) AS latencia_pipeline_p95_ms,
    COUNT(*) FILTER (
        WHERE source <> 'error'
          AND category IS DISTINCT FROM 'direct'
          AND COALESCE(route, 'rag') = 'rag'
          AND (response ILIKE 'No tengo información%'
               OR response ILIKE 'No dispongo%')
    ) AS no_info_heuristica,
    COUNT(*) FILTER (
        WHERE response LIKE 'No he podido generar una respuesta completa%'
    ) AS errores_transporte,
    COUNT(*) FILTER (WHERE source = 'error') AS filas_error
FROM query_logs
GROUP BY date_trunc('week', created_at)::date;

REVOKE ALL PRIVILEGES ON bot_health_daily FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON bot_health_semanal FROM PUBLIC, anon, authenticated;
GRANT SELECT ON bot_health_daily TO service_role;
GRANT SELECT ON bot_health_semanal TO service_role;

-- s301: feedback, motivos del 👎 y uso por canal — AGREGADOS puros (ni ids ni prosa).
CREATE OR REPLACE VIEW bot_feedback_semanal
WITH (security_invoker = true) AS
SELECT
    COALESCE(v.semana, f.semana) AS semana,
    COALESCE(v.votos_up, 0)        AS votos_up,
    COALESCE(v.votos_down, 0)      AS votos_down,
    COALESCE(v.con_motivo, 0)      AS votos_down_con_motivo,
    COALESCE(v.con_comentario, 0)  AS votos_con_comentario,
    COALESCE(v.marcados_utiles, 0) AS marcados_utiles,
    COALESCE(f.mensajes, 0)        AS feedback_libre
FROM (
    SELECT date_trunc('week', created_at)::date AS semana,
           COUNT(*) FILTER (WHERE verdict = 'up')        AS votos_up,
           COUNT(*) FILTER (WHERE verdict = 'down')      AS votos_down,
           COUNT(*) FILTER (WHERE verdict = 'down'
                              AND reason_class IS NOT NULL) AS con_motivo,
           COUNT(*) FILTER (WHERE comment IS NOT NULL)   AS con_comentario,
           COUNT(*) FILTER (WHERE utilidad IS NOT NULL
                              AND utilidad <> 'ninguna') AS marcados_utiles
      FROM answer_feedback
     GROUP BY 1
) v
FULL JOIN (
    SELECT date_trunc('week', created_at)::date AS semana,
           COUNT(*) AS mensajes
      FROM feedback
     GROUP BY 1
) f USING (semana);

CREATE OR REPLACE VIEW bot_motivos_negativos
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    COALESCE(reason_class, '(sin motivo)') AS motivo,
    COUNT(*) AS votos
FROM answer_feedback
WHERE verdict = 'down'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW bot_uso_por_canal
WITH (security_invoker = true) AS
SELECT
    date_trunc('week', created_at)::date AS semana,
    CASE WHEN source = 'error' THEN 'error'
         ELSE COALESCE(route, 'rag') END AS canal,
    COUNT(*) AS consultas,
    COUNT(DISTINCT telegram_user_id) AS personas
FROM query_logs
GROUP BY 1, 2;

REVOKE ALL PRIVILEGES ON bot_feedback_semanal, bot_motivos_negativos, bot_uso_por_canal
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON bot_feedback_semanal, bot_motivos_negativos, bot_uso_por_canal
    TO service_role;

-- s306 (#63): salud del canal de retrieval — ¿cuántos turnos respondieron con el
-- pool DEGRADADO (fail-open de canal), y qué canal falla? Lee los tokens acotados
-- de rag_trace.retrieval.channel_failures (allowlist en runtime_trace, sin prosa).
-- «sin medida» ≠ «sano»: las filas pre-s306 no tienen la sección y NO cuentan
-- como sanas — la confusión entre ambas cosas era exactamente el defecto #63.
CREATE OR REPLACE VIEW salud_canal_retrieval_v1
WITH (security_invoker = true) AS
SELECT
    date_trunc('day', created_at)::date AS dia,
    COUNT(*) AS turnos_rag,
    COUNT(*) FILTER (
        WHERE rag_trace IS NOT NULL AND rag_trace ? 'retrieval'
    ) AS turnos_con_medida,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(
            rag_trace -> 'retrieval' -> 'channel_failures'
        ) > 0
    ) AS turnos_degradados,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "VECTOR"}]'
    ) AS fallos_vector,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "ENUNCIADOS"}]'
    ) AS fallos_enunciados,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "HYQ_TABLE"}]'
    ) AS fallos_hyq_table,
    COUNT(*) FILTER (
        WHERE rag_trace -> 'retrieval' -> 'channel_failures'
              @> '[{"channel": "HYQ_HYDRATE"}]'
    ) AS fallos_hyq_hydrate
FROM query_logs
WHERE COALESCE(route, 'rag') = 'rag'   -- los shortcuts no hacen retrieval
GROUP BY 1;

REVOKE ALL PRIVILEGES ON salud_canal_retrieval_v1
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON salud_canal_retrieval_v1 TO service_role;

-- Create storage bucket for manual images
-- Note: Run this via Supabase dashboard:
-- Create bucket "manual-images" with public access
