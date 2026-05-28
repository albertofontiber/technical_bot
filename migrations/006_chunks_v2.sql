-- ============================================================================
-- Migration 006: tabla chunks_v2 — corpus re-ingestado (PLAN_RAG_2026 Fase 1)
-- ============================================================================
-- La Etapa B del pipeline de re-ingesta indexa en chunks_v2, una tabla NUEVA y
-- vacía, en paralelo a la `chunks` de producción. El bot sigue sirviendo desde
-- `chunks` sin interrupción hasta que el GATE (recall de las 52 preguntas del
-- eval) da el visto bueno; entonces el SWAP (FASE D, al final, manual) cambia
-- las dos tablas con un RENAME atómico.
--
-- Por qué una tabla nueva y no un ALTER sobre `chunks`:
--   - El embedding cambia de dimensión (1536 OpenAI → 1024 Voyage). Un ALTER
--     de tipo de columna sobre 168k filas es lento y deja la tabla inservible
--     a mitad. Tabla nueva = el bot nunca ve un estado intermedio.
--   - Si el corpus re-ingestado sale mal, `chunks` sigue intacta: el rollback
--     es no hacer el SWAP. Cero riesgo para producción.
--
-- Contrato con el retriever: src/rag/retriever.py selecciona columnas de
-- `chunks` por NOMBRE (id, content, product_model, category, section_title,
-- content_type, manufacturer, protocol, doc_type, has_diagram, diagram_url,
-- source_file, page_number, document_id) y llama a las RPC match_chunks /
-- search_chunks_text. chunks_v2 es un superconjunto de esas columnas; tras el
-- SWAP el retriever funciona sin tocar una línea de Python — solo se
-- reemplazan los cuerpos de las RPC (FASE D).
--
-- Ejecución: copiar-pegar las FASES A-C en el Supabase SQL Editor. La FASE D
-- (SWAP) se ejecuta SOLO después de que el GATE pase. Todo es idempotente.
-- ============================================================================


-- ============================================================================
-- FASE A — TABLA chunks_v2
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ---- Identidad / procedencia -------------------------------------------
    document_id UUID REFERENCES documents(id),
        -- FK al manual en `documents` (idempotente por hash, NO se reconstruye).
    extraction_sha256 TEXT NOT NULL,
        -- SHA-256 del PDF fuente = clave del store de extracción
        -- (data/extraction/<config>/<sha256>.json). Es la clave de
        -- idempotencia de la Etapa B: re-procesar un manual =
        -- DELETE WHERE extraction_sha256 = X, luego re-INSERT.
    chunk_index INTEGER,
        -- Orden ordinal del chunk dentro del documento (0,1,2,...). Permite
        -- reconstruir la secuencia y razonar parent-child.

    -- ---- Contenido ---------------------------------------------------------
    content TEXT NOT NULL,
        -- El texto del chunk tal cual se extrajo (markdown de LlamaParse).
    context TEXT,
        -- Blurb de contextual retrieval (B7): 1-2 frases que sitúan el chunk
        -- en el documento. SEPARADO de content — se antepone al content para
        -- embeber e indexar FTS, pero no contamina la cita textual.
    embedding vector(1024),
        -- Voyage voyage-4-large @1024 dims. 1024 es un CONTRATO: todos los
        -- modelos serios soportan Matryoshka, así que un cambio futuro de
        -- modelo no obliga a migrar el schema.
    search_vector tsvector,
        -- FTS ponderado (trigger abajo). A=section_title, B=content, C=context.

    -- ---- Idioma (B1/B2) ----------------------------------------------------
    language TEXT,
        -- Idioma dominante del chunk: 'es' | 'en' | 'pt' | 'fr' | 'it' | ...
        -- El filtro de idioma del retrieval lo necesita bien etiquetado.

    -- ---- Estructura (B3) ---------------------------------------------------
    section_title TEXT,
        -- Título de la sección inmediata (último header markdown).
    section_path TEXT,
        -- Breadcrumb jerárquico parent-child: 'H1 > H2 > H3'. Texto curado de
        -- alto valor para el ranking FTS (peso A).
    content_type TEXT,
        -- procedure | specification | troubleshooting | wiring | general

    -- ---- Diagramas de flujo (B4 — doble vía, tarea #12) --------------------
    is_flow_diagram BOOLEAN NOT NULL DEFAULT FALSE,
        -- TRUE si el chunk procede de una página de diagrama de flujo. El VLM
        -- alucina en flowcharts (notas inventadas, etiquetas mal leídas): estos
        -- chunks son orientativos, NUNCA fuente citable única.
    confidence REAL,
        -- Confianza de extracción de LlamaParse a nivel de página (0-1).

    -- ---- Metadata de producto (B5) -----------------------------------------
    product_model TEXT,
    manufacturer TEXT,
        -- Marca REAL del producto (quien lo fabrica, según el datasheet).
        -- Ej.: Securiton para ASD/ADW, Xtralis para VESDA, Pfannenberg para
        -- PA5, Argus para SG100, Pepperl-Fuchs para Z728. Para los productos
        -- de marca propia es la misma marca (Detnov, Notifier, Morley).
    distributor TEXT,
        -- Canal por el que llega el producto a Fontiber, cuando difiere de la
        -- marca. NULL para productos de marca propia (no hay distribuidor
        -- separado). Ej.: 'Detnov' para Pfannenberg/Argus/Pepperl-Fuchs/
        -- Securiton/Spectrex/SenseWare; 'Notifier' para VESDA (Xtralis).
        -- La reconciliación del retriever con esta distinción es Fase 2; aquí
        -- se captura el dato para no tener que migrar el schema más adelante.
    protocol TEXT,
    doc_type TEXT,
        -- instalacion | usuario | programacion | comunicacion_tecnica | ...
    category TEXT,

    -- ---- Diagramas / imagen adjunta ----------------------------------------
    has_diagram BOOLEAN NOT NULL DEFAULT FALSE,
    diagram_url TEXT,
        -- URL de la imagen de la página (Supabase Storage). Para is_flow_diagram
        -- se adjunta SIEMPRE a la respuesta del técnico (doble vía).

    -- ---- Fuente ------------------------------------------------------------
    source_file TEXT,
        -- Identificador estable por documento (basename del PDF sin extensión).
        -- El retriever agrupa y diversifica por este campo.
    page_number INTEGER,
        -- Página del PDF (índice, 1-based) — prerrequisito del deep-link
        -- manual.pdf#page=N. Fiable: viene del JSON de LlamaParse.

    -- ---- Dedup semántico (B6 — NO destructivo) -----------------------------
    duplicate_of UUID REFERENCES chunks_v2(id),
        -- Si NO es NULL, este chunk es un duplicado semántico del referenciado
        -- (típicamente la versión EN de un chunk ES, o duplicación del chunker).
        -- NO se borra: se marca. El retrieval filtra duplicate_of IS NULL.

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE chunks_v2 IS
    'Corpus re-ingestado (PLAN_RAG_2026 Fase 1). Reemplaza a chunks vía SWAP '
    'tras pasar el GATE de recall. Embedding Voyage @1024, extracción agéntica '
    'LlamaParse, contextual retrieval.';


-- ============================================================================
-- FASE B — ÍNDICES Y TRIGGER FTS
-- ============================================================================

-- B.1: Índice vectorial HNSW (sustituye al ivfflat de `chunks`).
-- HNSW da mejor recall/latencia y no necesita el parámetro `lists` calibrado
-- al tamaño del corpus. Defaults (m=16, ef_construction=64) son adecuados para
-- ~150k chunks. Nota de rendimiento: si la carga masiva de la Etapa B resulta
-- lenta, se puede DROP este índice, cargar, y recrearlo al final.
CREATE INDEX IF NOT EXISTS idx_chunks_v2_embedding
    ON chunks_v2 USING hnsw (embedding vector_cosine_ops);

-- B.2: Índice FTS.
CREATE INDEX IF NOT EXISTS idx_chunks_v2_search_vector
    ON chunks_v2 USING gin (search_vector);

-- B.3: Índices de filtrado de metadata (mismos que usa el retriever).
CREATE INDEX IF NOT EXISTS idx_chunks_v2_product_model ON chunks_v2 (product_model);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_category      ON chunks_v2 (category);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_content_type  ON chunks_v2 (content_type);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_manufacturer  ON chunks_v2 (manufacturer);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_source_file   ON chunks_v2 (source_file);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_document_id   ON chunks_v2 (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_v2_language      ON chunks_v2 (language);
-- Idempotencia de la Etapa B: borrado por archivo fuente.
CREATE INDEX IF NOT EXISTS idx_chunks_v2_extraction    ON chunks_v2 (extraction_sha256);
-- El retrieval filtra duplicate_of IS NULL — índice parcial para esa condición.
CREATE INDEX IF NOT EXISTS idx_chunks_v2_not_duplicate
    ON chunks_v2 (id) WHERE duplicate_of IS NULL;

-- B.4: Trigger que puebla search_vector.
-- Misma config 'public.spanish_unaccent' que `chunks` (migración 002): español
-- + unaccent, para que 'menú' matchee 'menu'. Pesos: A=section_path (breadcrumb
-- navegacional, alto valor), B=content, C=context (blurb — señal leve).
CREATE OR REPLACE FUNCTION update_chunks_v2_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('public.spanish_unaccent',
        coalesce(NEW.section_path, NEW.section_title, '')), 'A') ||
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.content, '')), 'B') ||
    setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.context, '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chunks_v2_search_vector_trigger ON chunks_v2;
CREATE TRIGGER chunks_v2_search_vector_trigger
BEFORE INSERT OR UPDATE OF content, context, section_title, section_path
ON chunks_v2
FOR EACH ROW
EXECUTE FUNCTION update_chunks_v2_search_vector();


-- ============================================================================
-- FASE C — RPC DE BÚSQUEDA SOBRE chunks_v2
-- ============================================================================
-- Réplicas de match_chunks / search_chunks_text adaptadas a chunks_v2:
--   - embedding vector(1024) en vez de 1536.
--   - filtran duplicate_of IS NULL (no devuelven duplicados marcados por B6).
--   - devuelven las columnas nuevas (language, is_flow_diagram, confidence,
--     section_path, context) para que el generador pueda usarlas.
-- Sufijo _v2 para coexistir con las RPC de producción. El SWAP (FASE D) las
-- renombra a los nombres canónicos.

-- C.1: Búsqueda vectorial.
CREATE OR REPLACE FUNCTION match_chunks_v2(
    query_embedding vector(1024),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    context TEXT,
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    section_path TEXT,
    content_type TEXT,
    manufacturer TEXT,
    distributor TEXT,
    protocol TEXT,
    doc_type TEXT,
    language TEXT,
    is_flow_diagram BOOLEAN,
    confidence REAL,
    has_diagram BOOLEAN,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    document_id UUID,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks_v2 c
    WHERE
        c.duplicate_of IS NULL
        AND c.embedding IS NOT NULL
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- C.2: Búsqueda full-text (FTS ponderado).
-- Contrato del retriever (content_search, Path B): payload
-- {search_query, filter_product, filter_manufacturer, filter_category, match_limit}.
CREATE OR REPLACE FUNCTION search_chunks_text_v2(
    search_query TEXT,
    filter_product TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    match_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    context TEXT,
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    section_path TEXT,
    content_type TEXT,
    manufacturer TEXT,
    distributor TEXT,
    protocol TEXT,
    doc_type TEXT,
    language TEXT,
    is_flow_diagram BOOLEAN,
    confidence REAL,
    has_diagram BOOLEAN,
    diagram_url TEXT,
    source_file TEXT,
    page_number INTEGER,
    document_id UUID,
    rank FLOAT
)
LANGUAGE plpgsql
AS $$
DECLARE
    ts_query tsquery := plainto_tsquery('public.spanish_unaccent', search_query);
BEGIN
    RETURN QUERY
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id,
        ts_rank(c.search_vector, ts_query)::FLOAT AS rank
    FROM chunks_v2 c
    WHERE
        c.duplicate_of IS NULL
        AND c.search_vector @@ ts_query
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY ts_rank(c.search_vector, ts_query) DESC
    LIMIT match_limit;
END;
$$;


-- ============================================================================
-- FASE D — SWAP (NO EJECUTAR hasta que el GATE pase)
-- ============================================================================
-- Cuando el recall de las 52 preguntas del eval sobre chunks_v2 sea aceptable,
-- ejecutar este bloque dentro de UNA transacción. Es atómico: el bot pasa de
-- `chunks` a `chunks_v2` sin ver un estado intermedio.
--
-- BEGIN;
--
--   -- Renombrar tablas.
--   ALTER TABLE chunks    RENAME TO chunks_old;
--   ALTER TABLE chunks_v2 RENAME TO chunks;
--
--   -- Reemplazar las RPC: las de producción esperan vector(1536) / la tabla
--   -- vieja; las _v2 ya apuntan a la tabla correcta (ahora llamada `chunks`).
--   -- DROP de las viejas (firma incompatible) + RENAME de las _v2.
--   DROP FUNCTION IF EXISTS match_chunks(vector,float,int,text,text,text);
--   DROP FUNCTION IF EXISTS search_chunks_text(text,text,text,text,int);
--   ALTER FUNCTION match_chunks_v2(vector,float,int,text,text,text)
--       RENAME TO match_chunks;
--   ALTER FUNCTION search_chunks_text_v2(text,text,text,text,int)
--       RENAME TO search_chunks_text;
--
--   -- El trigger de FTS viaja con la tabla en el RENAME; su función sigue
--   -- llamándose update_chunks_v2_search_vector (inocuo — es solo un nombre).
--
-- COMMIT;
--
-- Rollback (si algo va mal tras el SWAP): el inverso, chunks↔chunks_old.
-- `chunks_old` se conserva hasta confirmar en producción; luego DROP manual.
-- ============================================================================
