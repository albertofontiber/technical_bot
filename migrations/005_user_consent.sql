-- ============================================================================
-- Migration 005: user_consent — RGPD opt-in tracking (sesión 21)
-- ============================================================================
-- Problema (sesión 21): el plan de pasar el bot a directores generales de
--   empresas en fase de due diligence requiere capturar queries (texto + voz)
--   + respuestas + metadata. Sin consent explícito y persistente, esto es
--   problema legal (RGPD).
--
-- Fix: tabla `user_consent` con un row por usuario que ha aceptado los
--   términos via /accept. El bot bloquea cualquier query del usuario hasta
--   que aparezca en esta tabla.
--
--   - `terms_version` permite forzar re-aceptación si los términos cambian.
--   - `display_name` es opcional (DG puede dar su nombre o no) para que
--     en la revisión podamos saber qué queries vienen de quién sin tener
--     que hacer un SELECT join contra el ID de Telegram.
--
-- Idempotente: usa IF NOT EXISTS.
-- Tiempo estimado: <1 seg.
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO
-- ============================================================================

-- A.1: Verificar que la tabla NO existe todavía
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'user_consent'
) AS table_exists;


-- ============================================================================
-- FASE B — APLICAR FIX
-- ============================================================================

-- B.1: Crear tabla user_consent
CREATE TABLE IF NOT EXISTS user_consent (
    telegram_user_id BIGINT PRIMARY KEY,
    display_name TEXT,           -- optional, user-provided in /accept
    terms_version TEXT NOT NULL, -- e.g. "v1" — bump if terms change
    accepted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ       -- NULL while consent is active
);

-- B.2: Index for active-consent lookups
CREATE INDEX IF NOT EXISTS idx_user_consent_active
ON user_consent (telegram_user_id)
WHERE revoked_at IS NULL;


-- ============================================================================
-- FASE C — VALIDACIÓN
-- ============================================================================

-- C.1: Tabla creada
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user_consent'
ORDER BY ordinal_position;

-- C.2: Sin filas todavía (esperado)
SELECT COUNT(*) AS consent_rows FROM user_consent;
