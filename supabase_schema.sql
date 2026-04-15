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
    response_length INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_user ON query_logs (telegram_user_id);

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

-- Create storage bucket for manual images
-- Note: Run this via Supabase dashboard:
-- Create bucket "manual-images" with public access
