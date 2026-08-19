-- s324h Fase 2 — La SEXTA capa: el default que miente, en la autoridad final.
--
-- Diagnóstico del lote: `source = "text"` estaba replicado en seis sitios, y en
-- ninguno era verdad la mitad de las veces. Las cinco capas de Python ya no lo
-- tienen (DEC-235 + Fase 2). Ésta es la que queda, y es la que manda: mientras la
-- columna tenga DEFAULT, un escritor SQL directo que omita `source` seguirá
-- afirmando que un audio se tecleó.
--
-- VIABILIDAD MEDIDA antes de escribir esto (18-ago):
--   · 102 filas en producción: text×98, voice×4, **0 nulos** → SET NOT NULL pasa.
--   · UN solo escritor de producción: `src/logging_db.py` (dos POST). El resto de
--     consumidores (`bot_health_report`, `enunciados_panel`, `s272_bank_conversions`,
--     `s324_lib`) son GET.
--   · El CHECK incluye 'error' PORQUE EL CÓDIGO LO ESCRIBE (`telegram_bot.py`, la
--     fila padre de una incidencia) y una vista filtra por él (`supabase_schema.sql`).
--     Omitirlo repetiría el fallo que la 017 evitó: un INSERT que revienta en
--     producción justo cuando hay un error que registrar.
--
-- ATOMICIDAD: en BEGIN/COMMIT. Sin ella, si el ADD CONSTRAINT falla quedan
-- aplicados el DROP DEFAULT y el SET NOT NULL con el vocabulario abierto — el
-- mismo defecto que la 017 documenta y que la primera versión de esta migración
-- repetía (cazado por Sol, r48).
--
-- IDEMPOTENTE: se puede correr dos veces sin romper nada.
--
-- ORDEN: esta migración va DESPUÉS del código de la Fase 2 (ya mergeado), no
-- antes. El código ya no depende del DEFAULT: todas sus llamadas pasan `source`
-- explícito, así que quitarlo no puede dejar filas sin escribir. Al revés que la
-- 017, donde el CHECK tenía que existir antes de que el código escribiera el
-- valor nuevo.
--
-- NO APLICADA. La aplica Alberto.

BEGIN;

-- Por si quedara alguna fila anterior sin canal (hoy medido: 0).
UPDATE query_logs SET source = 'text' WHERE source IS NULL;

ALTER TABLE query_logs ALTER COLUMN source DROP DEFAULT;
ALTER TABLE query_logs ALTER COLUMN source SET NOT NULL;

ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS query_logs_source_valido;
ALTER TABLE query_logs ADD CONSTRAINT query_logs_source_valido
    CHECK (source IN ('text', 'voice', 'error'));

COMMIT;

-- ─────────────────────────────── POSTCONDICIÓN (correr después; si falla, revertir)
--
--   SELECT count(*) FROM query_logs WHERE source IS NULL;    -- debe ser 0
--   SELECT DISTINCT source FROM query_logs;                  -- ⊆ {text, voice, error}
--
-- Y la comprobación que de verdad prueba que el default murió:
--
--   INSERT INTO query_logs (telegram_user_id, query) VALUES (0, 'sonda');
--   -- debe FALLAR con «null value in column "source" violates not-null constraint».
--   -- Si pasa, el DEFAULT sigue vivo y la migración no hizo su trabajo.
