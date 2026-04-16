-- ============================================================================
-- Migration 001: Document management tables
-- ============================================================================
-- Introduces the `documents` table that represents the identity of each PDF
-- manual as a first-class entity, separate from its content (chunks).
-- This enables revision management, supersede chains, and document grouping
-- for multi-part manuals.
--
-- This migration is DESTRUCTIVE-SAFE:
--  - All CREATE statements are IF NOT EXISTS
--  - The ALTER TABLE chunks adds a NULLABLE column (no data loss)
--  - After this migration, the backfill script
--      scripts/migrations/001_backfill_documents.py
--    must be run to populate documents from existing chunks and link them.
--
-- Run in Supabase SQL editor. Re-running is safe (idempotent).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Table: documents
-- Purpose: master catalog of every PDF manual ingested, with identity
--          (family, revision, language) and lifecycle (active/superseded).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    document_family TEXT NOT NULL,
        -- Normalized name ignoring rev/date/version suffixes.
        -- Ex: "AM-8100 manual usuario y programacion"
    revision TEXT,
        -- Human-readable revision string as extracted from source.
        -- Ex: "4", "Issue 3", "v1.4", "Rev. A". NULL if undetermined.
    revision_date DATE,
        -- Date of the revision if detectable, NULL otherwise.
    language TEXT,
        -- 'es' | 'en' | 'multi' | NULL
    doc_type TEXT,
        -- 'instalacion' | 'usuario' | 'programacion' | 'comunicacion_tecnica'
        -- | 'hoja_datos' | 'guia_rapida' | NULL
    manufacturer TEXT NOT NULL,
    product_model TEXT,

    -- Source file identity
    source_pdf_filename TEXT NOT NULL,
        -- Original filename as it appeared on disk when ingested
    source_pdf_sha256 TEXT NOT NULL,
        -- SHA-256 of the raw PDF file bytes (full file).
        -- Stable even if the CMS renames the file. A re-compressed or
        -- re-generated PDF will hash differently and be treated as a
        -- new revision, which is the correct behavior.
        -- Backfilled rows use a placeholder with prefix 'backfill:' and
        -- are re-hashed when the PDF is re-processed.

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'active',
        -- 'active' | 'superseded' | 'draft' | 'retired' | 'needs_review'
    supersedes_id UUID REFERENCES documents(id),
        -- FK to the previous (older) revision that this doc supersedes
    superseded_by_id UUID REFERENCES documents(id),
        -- FK to the newer revision that supersedes this doc

    -- Audit
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT,

    -- A given PDF (by content hash) can only be ingested once per manufacturer
    CONSTRAINT documents_mfr_hash_unique UNIQUE (manufacturer, source_pdf_sha256)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_family_status
    ON documents(document_family, status);
CREATE INDEX IF NOT EXISTS idx_documents_mfr_status
    ON documents(manufacturer, status);
CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_product_model
    ON documents(product_model);
CREATE INDEX IF NOT EXISTS idx_documents_filename
    ON documents(source_pdf_filename);

COMMENT ON TABLE documents IS
    'Master catalog of PDF manuals. Each row = one ingested PDF identity, '
    'with revision lifecycle tracking. Chunks.document_id points here.';

COMMENT ON COLUMN documents.status IS
    'Lifecycle status: active (default, used by retrieval), superseded '
    '(replaced by a newer revision, still in DB for audit and explicit '
    'opt-in queries), draft (WIP, not retrievable), retired (manually '
    'removed from use), needs_review (ambiguous revision metadata, humans '
    'must resolve).';

-- ---------------------------------------------------------------------------
-- Table: document_groups
-- Purpose: groups multiple document rows that together form a single logical
--          document (ex: a multi-part leaflet printed in 4 pieces).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_name TEXT NOT NULL,
        -- Human-readable group name. Ex: "MADT951 multi-part leaflet"
    manufacturer TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE document_groups IS
    'Groups of physical documents that together form one logical document '
    '(typically multi-part leaflets with _01/_02/_03 suffixes).';

-- ---------------------------------------------------------------------------
-- Table: document_group_members
-- Purpose: join table between document_groups and documents, with ordering.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_group_members (
    group_id UUID NOT NULL REFERENCES document_groups(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    part_number INT,
        -- 1, 2, 3, ... relative order within the group
    PRIMARY KEY (group_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_dgm_document_id
    ON document_group_members(document_id);

COMMENT ON TABLE document_group_members IS
    'Members of a document_group with their ordering within the group.';

-- ---------------------------------------------------------------------------
-- ALTER chunks: add document_id column
-- Nullable initially for safe backfill. After backfill completes, we can
-- add a NOT NULL constraint in a follow-up migration.
-- ---------------------------------------------------------------------------
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES documents(id);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON chunks(document_id);

COMMENT ON COLUMN chunks.document_id IS
    'FK to the document this chunk belongs to. Enables lifecycle-aware '
    'retrieval (filter by documents.status=''active''). Nullable until '
    'backfill migration completes.';
