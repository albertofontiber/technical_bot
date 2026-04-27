-- ============================================================================
-- Migration 004: query_logs — añadir response + bot_version (sesión 21)
-- ============================================================================
-- Problema (sesión 21): para curar eval orgánico desde queries reales del DG,
--   necesitamos query + respuesta + versión del bot que la generó. La tabla
--   actual `query_logs` solo guarda metadata (chunks_used, response_length,
--   response_time_ms) pero NO la respuesta en sí. Sin response, perdemos la
--   mitad de la señal.
--
--   Adicionalmente, durante el uso del DG iteraremos el bot. Sin trazar qué
--   versión generó cada respuesta, queries de semana 2 y semana 4 quedan
--   indistinguibles, contaminando el análisis.
--
-- Fix:
--   - Columna `response` (TEXT, nullable) — contenido completo de la respuesta
--     enviada al usuario, truncado a 4096 chars (límite Telegram).
--   - Columna `bot_version` (TEXT, nullable) — git commit short hash o tag
--     que identifica el código que generó la respuesta. Lo inyecta el bot
--     desde env var BOT_VERSION o lectura de `git rev-parse --short HEAD`.
--
-- Idempotente: usa IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
-- Tiempo estimado: <1 seg (ALTER TABLE sin rewrite, columnas nullable).
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO (read-only)
-- ============================================================================

-- A.1: Verificar estructura actual de query_logs
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'query_logs'
ORDER BY ordinal_position;

-- A.2: Conteo de filas existentes (para confirmar que el ALTER no rompe nada)
SELECT COUNT(*) AS total_rows FROM query_logs;


-- ============================================================================
-- FASE B — APLICAR FIX
-- ============================================================================

-- B.1: Añadir columna response (respuesta completa, truncada a 4096 chars)
ALTER TABLE query_logs
ADD COLUMN IF NOT EXISTS response TEXT;

-- B.2: Añadir columna bot_version (git short hash o tag)
ALTER TABLE query_logs
ADD COLUMN IF NOT EXISTS bot_version TEXT;

-- B.3: Índice por bot_version para análisis comparativo entre versiones
CREATE INDEX IF NOT EXISTS idx_query_logs_bot_version
ON query_logs (bot_version);


-- ============================================================================
-- FASE C — VALIDACIÓN
-- ============================================================================

-- C.1: Verificar que las columnas existen
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'query_logs'
  AND column_name IN ('response', 'bot_version');

-- C.2: Filas existentes mantienen NULL en las columnas nuevas (esperado)
SELECT
  COUNT(*) AS total,
  COUNT(response) AS with_response,
  COUNT(bot_version) AS with_version
FROM query_logs;


-- ============================================================================
-- RESULTADO ESPERADO TRAS FASE C
-- ============================================================================
-- C.1: 2 filas devueltas (response: text, bot_version: text)
-- C.2: total = filas previas, with_response = 0, with_version = 0
--      (filas nuevas a partir del deploy tendrán ambos campos poblados)
-- ============================================================================
