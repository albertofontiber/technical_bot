-- s294 · #60 punto 5 — motivo del 👎 («¿qué falló?»), idea de Alberto (1-ago).
--
-- Convierte una señal sin mecanismo (un pulgar hacia abajo) en un CASO
-- DIAGNOSTICABLE: las clases mapean ~1:1 a la taxonomía del instrumento
-- (omitted / contradicted / scope / otro), así que cada 👎 con motivo es semilla
-- de eval orgánico y candidato a gold.
--
-- Se anexa a `answer_feedback` en vez de crear tabla: el motivo pertenece al MISMO
-- voto (mismo UNIQUE query_log_id+telegram_user_id), hereda su CASCADE hacia
-- query_logs y no añade superficie de datos personales nueva.
--
-- TEXTO LIBRE: NO se habilita aquí. La columna `comment` ya existe desde s286 para
-- eso, pero el texto libre entra en la matriz de retención RGPD — que hoy NO existe
-- (no hay purga de query_logs). Con botones basta para la clase diagnóstica; el
-- texto libre queda gateado a esa decisión.

ALTER TABLE answer_feedback
    ADD COLUMN IF NOT EXISTS reason_class TEXT;

DO $feedback_reason_check$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'answer_feedback_reason_class_check'
          AND conrelid = 'public.answer_feedback'::regclass
    ) THEN
        ALTER TABLE answer_feedback
            ADD CONSTRAINT answer_feedback_reason_class_check
            CHECK (reason_class IS NULL OR reason_class IN (
                'info',    -- faltó información
                'wrong',   -- dato incorrecto
                'scope',   -- no era mi pregunta
                'other'    -- otra cosa
            ));
    END IF;
END
$feedback_reason_check$;

-- `answer_feedback` ya tiene GRANT SELECT, INSERT, UPDATE para service_role (el
-- voto 👍→👎 es un upsert), así que el motivo no necesita privilegios nuevos: se
-- escribe con un PATCH sobre la fila del voto que ya existe.
