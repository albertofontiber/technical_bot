-- ============================================================================
-- Migration 003: FTS search_vector con section_title boost (TECH_DEBT #25 Fase 1)
-- ============================================================================
-- Problema (hp001, sesión 16): query "menú de programación avanzada CAD-250"
--   no trae el chunk correcto aunque existe en BD. El chunk tiene
--   `section_title = "AJUSTES (Menú principal) > AVANZADO(Submenú)"` y el
--   content también contiene "AJUSTES > AVANZADO", pero el retriever usa
--   vector similarity sobre content y el embedding de "programación avanzada"
--   no matchea bien con un content dominado por otra terminología.
--
-- Root cause: el FTS actual (`search_vector`) solo indexa `content`. Los
-- section_titles — cadenas de navegación altamente descriptivas como
-- "AJUSTES > AVANZADO > Sistema" — son texto curado de alto valor pero no
-- contribuyen al ranking.
--
-- Fix: weighted tsvector combinando title (peso A, máximo) + content
-- (peso B). Postgres FTS `ts_rank` automáticamente boostea matches en
-- title. `plfts` (matching booleano) continúa funcionando porque la union
-- || preserva todos los tokens — match en title O content produce hit.
--
-- Ejecución: copiar-pegar por FASES en Supabase SQL Editor. Cada fase es
-- idempotente y se puede re-ejecutar sin efectos secundarios.
--
-- Tiempo estimado: FASE B (~60-90 seg para UPDATE de 168k chunks).
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO (read-only, ejecuta primero y comparte output)
-- ============================================================================

-- A.1: ¿search_vector es columna generada STORED, o poblada via trigger?
SELECT column_name, is_generated, generation_expression
FROM information_schema.columns
WHERE table_name = 'chunks' AND column_name = 'search_vector';

-- A.2: Triggers activos sobre chunks
SELECT tgname, pg_get_triggerdef(t.oid) AS trigger_def
FROM pg_trigger t
WHERE tgrelid = 'public.chunks'::regclass
  AND NOT tgisinternal;

-- A.3: Baseline — hp001 chunks target debe existir y tener title
SELECT id, source_file, section_title, LEFT(content, 100) AS content_preview
FROM chunks
WHERE id IN (
  '267d9584-1fa9-4a69-aad0-7166f66b5432',
  'b7476847-be0b-4552-91ed-bcb8d0d097d5'
);

-- A.4: Stats — cuántos chunks tienen section_title no-null
SELECT
  COUNT(*) FILTER (WHERE section_title IS NULL OR section_title = '') AS null_title,
  COUNT(*) FILTER (WHERE section_title IS NOT NULL AND section_title != '') AS has_title,
  COUNT(*) AS total
FROM chunks;

-- A.5: Prueba actual — query "AJUSTES AVANZADO" debe devolver pocos/ningún hit
-- en el estado actual (antes de la migration), porque search_vector solo
-- contiene tokens de content y "AJUSTES" aparece pocas veces literal.
SELECT COUNT(*) AS hits_before
FROM chunks
WHERE source_file LIKE '%CAD-250%'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'ajustes avanzado');


-- ============================================================================
-- FASE B — APLICAR FIX
-- ============================================================================
-- Ejecuta B.1 a B.3 en orden. Idempotentes.

-- B.1: Actualizar/crear función trigger para poblar search_vector con weights
-- Peso A = section_title (0.1 → 1.0 según rank), Peso B = content (0.4 por default)
-- Postgres weights default: {A:1.0, B:0.4, C:0.2, D:0.1}
-- Con los defaults, un match en title es ~2.5× más valioso que en content.
CREATE OR REPLACE FUNCTION update_chunks_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.section_title, '')), 'A') ||
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.content, '')), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- B.2: Asegurar que el trigger está registrado (drop + recreate para idempotencia)
DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON chunks;
CREATE TRIGGER chunks_search_vector_trigger
BEFORE INSERT OR UPDATE OF content, section_title
ON chunks
FOR EACH ROW
EXECUTE FUNCTION update_chunks_search_vector();

-- B.3: Backfill — repoblar search_vector con la nueva estructura (title + content)
-- IMPORTANTE: ejecutar UPDATE completo sobre 168k chunks supera el timeout del
-- Supabase SQL Editor (proxy/upstream timeout, no statement_timeout). Dividimos
-- en 16 batches por primer char del UUID (hex: 0-9, a-f). Cada batch actualiza
-- ~10k rows y termina en ~5-10 seg. Ejecuta los 16 statements en orden.
-- Son idempotentes individualmente (re-ejecutables).
--
-- Alternativa si prefieres 1 solo statement: usa psql directo con connection
-- string (sin timeout del editor):
--   psql "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
--   SET statement_timeout = '30min';
--   <el UPDATE completo del bloque de abajo, sin el WHERE id::text LIKE>

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '0%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '1%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '2%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '3%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '4%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '5%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '6%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '7%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '8%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE '9%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'a%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'b%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'c%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'd%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'e%';

UPDATE chunks SET search_vector =
  setweight(to_tsvector('public.spanish_unaccent', coalesce(section_title, '')), 'A') ||
  setweight(to_tsvector('public.spanish_unaccent', coalesce(content, '')), 'B')
WHERE id::text LIKE 'f%';


-- ============================================================================
-- FASE C — VALIDACIÓN (ejecuta después de FASE B)
-- ============================================================================

-- C.1: hp001 — los 2 chunks target deben hacer hit con "ajustes avanzado"
SELECT id, section_title,
       ts_rank(search_vector, plainto_tsquery('public.spanish_unaccent', 'ajustes avanzado')) AS rank
FROM chunks
WHERE id IN (
  '267d9584-1fa9-4a69-aad0-7166f66b5432',
  'b7476847-be0b-4552-91ed-bcb8d0d097d5'
);

-- C.2: Hits totales — debe subir significativamente vs A.5
SELECT COUNT(*) AS hits_after
FROM chunks
WHERE source_file LIKE '%CAD-250%'
  AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'ajustes avanzado');

-- C.3: Top-5 ranking — los chunks target deben aparecer en posiciones altas
SELECT
  ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector,
    plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) DESC) AS pos,
  id,
  LEFT(section_title, 60) AS title_preview,
  ts_rank(search_vector, plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) AS rank
FROM chunks
WHERE source_file LIKE '%CAD-250%'
ORDER BY ts_rank(search_vector, plainto_tsquery('public.spanish_unaccent', 'menú programación avanzada')) DESC
LIMIT 5;

-- C.4: No regression — queries que funcionaban antes siguen funcionando
-- (menú, configuración, avanzado en MC-380 deben seguir matcheando)
SELECT
  (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%' AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'menú')) AS menu,
  (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%' AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'configuración')) AS configuracion,
  (SELECT COUNT(*) FROM chunks WHERE source_file LIKE '%CAD-250%' AND search_vector @@ plainto_tsquery('public.spanish_unaccent', 'avanzado')) AS avanzado;


-- ============================================================================
-- RESULTADO ESPERADO TRAS FASE C
-- ============================================================================
-- C.1: ambos chunks target devuelven rank > 0 (antes: hit booleano inconsistente)
-- C.2: hits_after > A.5.hits_before (más matches porque title también cuenta)
-- C.3: chunks con "AJUSTES > AVANZADO" en title aparecen en top-5 para
--      query "menú programación avanzada" (antes: no salían en top-46)
-- C.4: queries no-regresión siguen devolviendo los mismos conteos o mayores
-- ============================================================================
