-- ============================================================================
-- Migration 002: Fix FTS (search_vector) para que matchee términos con acento
-- ============================================================================
-- Problema: `fts.menú` devuelve 0 hits aunque "menú" aparece 5+ veces en content.
--   Causa: to_tsvector('spanish', content) preserva acentos inconsistentemente y
--   no normaliza. Query `menú` (con tilde) no matchea tokens `menu` (sin).
--
-- Fix: crear text search config 'spanish_unaccent' = spanish + unaccent extension,
--   y repoblar search_vector con la nueva config. Queries posteriores via PostgREST
--   fts.<term> usarán la config por defecto de la DB, así que también la seteamos.
--
-- Ejecución: copiar-pegar por FASES en Supabase SQL Editor. Cada fase es idempotente
--   y se puede re-ejecutar sin efectos secundarios.
--
-- Tiempo estimado: FASE B (~30-60 seg para UPDATE de 148k chunks), resto instantáneo.
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO (read-only, ejecuta primero y comparte output)
-- ============================================================================

-- A.1: Trigger actual sobre chunks (para saber cómo se pobla search_vector)
SELECT tgname, pg_get_triggerdef(t.oid) AS trigger_def
FROM pg_trigger t
WHERE tgrelid = 'public.chunks'::regclass
  AND NOT tgisinternal;

-- A.2: ¿search_vector es columna generada?
SELECT column_name, is_generated, generation_expression
FROM information_schema.columns
WHERE table_name = 'chunks' AND column_name = 'search_vector';

-- A.3: Extensiones instaladas
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('unaccent', 'pg_trgm', 'vector');

-- A.4: Default text search config de la DB actual
SHOW default_text_search_config;

-- A.5: Stats — cuántos chunks tienen search_vector populado
SELECT
  COUNT(*) FILTER (WHERE search_vector IS NULL)     AS null_sv,
  COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS populated_sv,
  COUNT(*)                                          AS total
FROM chunks;

-- A.6: Ejemplo de tsvector para un chunk que contiene "menú"
-- (Demuestra el problema: menú aparece en content pero NO en search_vector como token 'menú')
SELECT id, LEFT(content, 80) AS content_preview, search_vector
FROM chunks
WHERE content ILIKE '%menú%'
  AND source_file = 'CAD-250-MC-380-es'
LIMIT 1;


-- ============================================================================
-- FASE B — APLICAR FIX
-- ============================================================================
-- Ejecuta las secciones B.1-B.4 en orden. Son idempotentes (safe to re-run).

-- B.1: Habilitar extensión unaccent
CREATE EXTENSION IF NOT EXISTS unaccent;

-- B.2: Crear text search config spanish_unaccent (drop + recreate para idempotencia)
DROP TEXT SEARCH CONFIGURATION IF EXISTS public.spanish_unaccent CASCADE;
CREATE TEXT SEARCH CONFIGURATION public.spanish_unaccent (COPY = spanish);
ALTER TEXT SEARCH CONFIGURATION public.spanish_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, spanish_stem;

-- B.3: Setear nueva config como default del DB
-- IMPORTANTE: esto hace que todas las queries FTS subsecuentes (incluyendo
-- PostgREST fts.*) usen spanish_unaccent automáticamente.
ALTER DATABASE postgres SET default_text_search_config = 'public.spanish_unaccent';

-- B.4: Repoblar search_vector con nueva config para TODO el corpus
-- NOTA: tarda ~30-60 seg para 148k chunks. Si el trigger ya genera la columna
-- automáticamente con to_tsvector() sin especificar config, este UPDATE será
-- idempotente con cada INSERT posterior (el trigger usará la nueva default_config).
UPDATE chunks
SET search_vector = to_tsvector('public.spanish_unaccent', content);


-- ============================================================================
-- FASE C — VALIDACIÓN (ejecuta después de FASE B)
-- ============================================================================

-- C.1: Ahora debe devolver ≥5 hits (antes: 0 para CAD-250-MC-380-es)
SELECT COUNT(*) AS hits_menu
FROM chunks
WHERE source_file = 'CAD-250-MC-380-es'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'menú');

-- C.2: programación debe matchear aunque el contenido diga "programación" con tilde
SELECT COUNT(*) AS hits_programacion
FROM chunks
WHERE source_file = 'Manual instalacion CAD-250 (MI_372_es_2024 e)'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'programación');

-- C.3: configuración en MC-380
SELECT COUNT(*) AS hits_configuracion
FROM chunks
WHERE source_file = 'CAD-250-MC-380-es'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'configuración');

-- C.4: avanzado — el stemmer debe llevar "avanzado" a "avanz" y matchear
SELECT COUNT(*) AS hits_avanzado
FROM chunks
WHERE source_file = 'CAD-250-MC-380-es'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'avanzado');

-- C.5: "coincidencia" en ID3000 (MPDT190, que contiene "Niveles COINCIDENCIA en ALARMA")
SELECT COUNT(*) AS hits_coincidencia
FROM chunks
WHERE product_model = 'ID3000'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'coincidencia');


-- ============================================================================
-- RESULTADO ESPERADO TRAS FASE C
-- ============================================================================
-- C.1 hits_menu          → ≥ 5   (antes: 0)
-- C.2 hits_programacion  → ≥ 3   (antes: 0)
-- C.3 hits_configuracion → ≥ 5   (antes: 0)
-- C.4 hits_avanzado      → ≥ 5   (antes: 0)
-- C.5 hits_coincidencia  → ≥ 5   (antes: 0; MPDT190 tiene sección dedicada)
-- ============================================================================
