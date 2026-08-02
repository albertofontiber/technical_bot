-- s294 · #60 punto 1 — ancla `message_id → query_log_id` para el canal de feedback.
--
-- POR QUÉ UNA TABLA PUENTE Y NO UNA COLUMNA EN query_logs (el debt permitía ambas):
--   1. Una respuesta se envía PARTIDA en N mensajes de Telegram (el splitter del
--      transporte). Una columna solo ancla uno; una reacción sobre cualquier otra
--      parte se quedaría sin mapear.
--   2. No se hace ALTER sobre `query_logs`, que es la tabla caliente y la que gobierna
--      la matriz de retención RGPD.
--
-- RGPD: `telegram_chat_id` identifica a una persona ⇒ la tabla entra en la MISMA
-- frontera de datos personales que query_logs/answer_feedback (RLS + FORCE RLS +
-- REVOKE a anon/authenticated) y muere en cascada con su `query_logs` cuando la
-- retención borra la consulta. Sin fila de query_log no hay ancla: es correcto.

CREATE TABLE IF NOT EXISTS answer_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,
    telegram_message_id BIGINT NOT NULL,
    part_index SMALLINT NOT NULL DEFAULT 0,   -- 0..N-1 dentro de la respuesta
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Un (chat, message) pertenece a UNA sola respuesta: hace idempotente el
    -- estampado ante reintento del bot y da la búsqueda inversa en O(1).
    UNIQUE (telegram_chat_id, telegram_message_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_messages_query_log
ON answer_messages (query_log_id);

DO $answer_messages_boundary$
DECLARE
    role_name text;
    privilege_name text;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'service_role must exist with BYPASSRLS before hardening';
    END IF;

    ALTER TABLE public.answer_messages ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.answer_messages FORCE ROW LEVEL SECURITY;
    REVOKE ALL PRIVILEGES ON TABLE public.answer_messages
        FROM PUBLIC, anon, authenticated, service_role;
    -- El bot INSERTA al enviar y LEE al recibir una reacción. Nada más.
    GRANT SELECT, INSERT ON TABLE public.answer_messages TO service_role;

    -- Postcondiciones (mismo patrón que la frontera de personal_data del bootstrap):
    -- el fallo aborta la migración en vez de dejar la tabla expuesta.
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('public.answer_messages')
          AND relrowsecurity AND relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'personal-data RLS invariant failed for answer_messages';
    END IF;

    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        FOREACH privilege_name IN ARRAY ARRAY[
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
            'REFERENCES', 'TRIGGER', 'MAINTAIN'
        ]
        LOOP
            IF has_table_privilege(
                role_name, 'public.answer_messages', privilege_name
            ) THEN
                RAISE EXCEPTION 'unexpected % privilege for % on answer_messages',
                    privilege_name, role_name;
            END IF;
        END LOOP;
    END LOOP;

    IF NOT has_table_privilege('service_role', 'public.answer_messages', 'SELECT')
       OR NOT has_table_privilege('service_role', 'public.answer_messages', 'INSERT')
    THEN
        RAISE EXCEPTION 'service_role must keep SELECT+INSERT on answer_messages';
    END IF;
END
$answer_messages_boundary$;
