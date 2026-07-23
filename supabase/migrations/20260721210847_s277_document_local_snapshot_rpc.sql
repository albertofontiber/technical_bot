-- S277: atomic, read-only document-local coverage snapshot.
--
-- The serving lane must not infer lifecycle authority from a partial REST
-- hydration.  This STABLE RPC resolves the complete exact-identity document
-- family and its FTS candidates inside one PostgreSQL statement snapshot.
-- PostgREST exposes STABLE functions to GET in a READ ONLY transaction.
--
-- Rollback:
--   DROP FUNCTION IF EXISTS public.document_local_snapshot_v1(JSONB, TEXT, INTEGER, INTEGER);

CREATE OR REPLACE FUNCTION public.document_local_snapshot_v1(
    anchor_scopes JSONB,
    fts_query TEXT,
    family_limit INTEGER DEFAULT 16,
    candidate_limit INTEGER DEFAULT 64
)
RETURNS JSONB
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
WITH RECURSIVE
input_shape AS (
    SELECT
        pg_catalog.jsonb_typeof(anchor_scopes) = 'array' AS anchors_are_array,
        CASE
            WHEN pg_catalog.jsonb_typeof(anchor_scopes) = 'array'
            THEN pg_catalog.jsonb_array_length(anchor_scopes) BETWEEN 1 AND 2
            ELSE FALSE
        END
        AND fts_query IS NOT NULL
        AND pg_catalog.length(fts_query) BETWEEN 1 AND 480
        AND fts_query ~ '^[a-z0-9()&|]+$'
        AND pg_catalog.pg_input_is_valid(
            fts_query, 'pg_catalog.tsquery'
        )
        AND family_limit BETWEEN 1 AND 32
        AND candidate_limit BETWEEN 1 AND 64 AS request_valid
),
raw_scopes AS (
    SELECT
        entry.scope_rank::INTEGER AS scope_rank,
        entry.scope
    FROM input_shape AS input
    CROSS JOIN LATERAL pg_catalog.jsonb_array_elements(
        CASE
            WHEN input.anchors_are_array THEN anchor_scopes
            ELSE '[]'::JSONB
        END
    ) WITH ORDINALITY AS entry(scope, scope_rank)
    WHERE input.request_valid
),
scopes AS (
    SELECT
        raw.scope_rank,
        raw.scope,
        pg_catalog.jsonb_typeof(raw.scope) = 'object'
        AND raw.scope ?& ARRAY[
            'document_id', 'extraction_sha256', 'source_file'
        ]
        AND (
            raw.scope
            - 'document_id'
            - 'extraction_sha256'
            - 'source_file'
        ) = '{}'::JSONB
        AND (raw.scope->>'document_id') ~* (
            '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-'
            '[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        )
        AND (raw.scope->>'extraction_sha256') ~ '^[0-9a-f]{64}$'
        AND pg_catalog.length(pg_catalog.btrim(raw.scope->>'source_file'))
            BETWEEN 1 AND 512 AS anchor_valid,
        CASE
            WHEN (raw.scope->>'document_id') ~* (
                '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-'
                '[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
            )
            THEN (raw.scope->>'document_id')::UUID
            ELSE NULL
        END AS anchor_document_id,
        pg_catalog.lower(raw.scope->>'extraction_sha256') AS anchor_extraction_sha256,
        raw.scope->>'source_file' AS anchor_source_file
    FROM raw_scopes AS raw
),
seed_rows AS (
    SELECT
        scope.scope_rank,
        scope.anchor_valid,
        scope.anchor_document_id,
        scope.anchor_extraction_sha256,
        scope.anchor_source_file,
        document.id AS seed_id,
        document.document_family,
        document.revision,
        document.language,
        document.doc_type,
        document.manufacturer,
        document.product_model,
        document.source_pdf_filename,
        document.source_pdf_sha256,
        document.status,
        document.supersedes_id,
        document.superseded_by_id,
        document.id IS NOT NULL
        AND pg_catalog.btrim(COALESCE(document.document_family, '')) <> ''
        AND pg_catalog.btrim(COALESCE(document.language, '')) <> ''
        AND pg_catalog.btrim(COALESCE(document.doc_type, '')) <> ''
        AND pg_catalog.btrim(COALESCE(document.manufacturer, '')) <> ''
        AND pg_catalog.btrim(COALESCE(document.product_model, '')) <> ''
            AS identity_complete
    FROM scopes AS scope
    LEFT JOIN public.documents AS document
      ON scope.anchor_valid
     AND document.id = scope.anchor_document_id
),
family_rows AS (
    SELECT
        seed.scope_rank,
        family.id,
        family.document_family,
        family.revision,
        family.language,
        family.doc_type,
        family.manufacturer,
        family.product_model,
        family.source_pdf_filename,
        family.source_pdf_sha256,
        family.status,
        family.supersedes_id,
        family.superseded_by_id
    FROM seed_rows AS seed
    JOIN LATERAL (
        SELECT
            candidate.id,
            candidate.document_family,
            candidate.revision,
            candidate.language,
            candidate.doc_type,
            candidate.manufacturer,
            candidate.product_model,
            candidate.source_pdf_filename,
            candidate.source_pdf_sha256,
            candidate.status,
            candidate.supersedes_id,
            candidate.superseded_by_id
        FROM public.documents AS candidate
        WHERE seed.identity_complete
          AND pg_catalog.lower(seed.language) = 'es'
          AND candidate.document_family
                IS NOT DISTINCT FROM seed.document_family
          AND candidate.language IS NOT DISTINCT FROM seed.language
          AND candidate.manufacturer IS NOT DISTINCT FROM seed.manufacturer
        ORDER BY candidate.id
        LIMIT family_limit + 1
    ) AS family ON TRUE
),
family_stats AS (
    SELECT
        seed.scope_rank,
        pg_catalog.count(family.id)::INTEGER AS family_count,
        pg_catalog.count(family.id) FILTER (
            WHERE family.status = 'active'
        )::INTEGER AS active_count,
        pg_catalog.count(family.id) FILTER (
            WHERE family.supersedes_id IS NULL
        )::INTEGER AS root_count,
        pg_catalog.count(family.id) FILTER (
            WHERE family.status NOT IN ('active', 'superseded')
        )::INTEGER AS invalid_status_count,
        pg_catalog.count(family.id) FILTER (
            WHERE family.doc_type IS DISTINCT FROM seed.doc_type
               OR family.product_model IS DISTINCT FROM seed.product_model
        )::INTEGER AS identity_drift_count
    FROM seed_rows AS seed
    LEFT JOIN family_rows AS family
      ON family.scope_rank = seed.scope_rank
    GROUP BY seed.scope_rank
),
reciprocal_stats AS (
    SELECT
        family.scope_rank,
        pg_catalog.bool_and(
            (
                family.supersedes_id IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM family_rows AS older
                    WHERE older.scope_rank = family.scope_rank
                      AND older.id = family.supersedes_id
                      AND older.superseded_by_id = family.id
                )
            )
            AND (
                family.superseded_by_id IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM family_rows AS newer
                    WHERE newer.scope_rank = family.scope_rank
                      AND newer.id = family.superseded_by_id
                      AND newer.supersedes_id = family.id
                )
            )
        ) AS reciprocal
    FROM family_rows AS family
    GROUP BY family.scope_rank
),
walk AS (
    SELECT
        family.scope_rank,
        family.id,
        ARRAY[family.id]::UUID[] AS path
    FROM family_rows AS family
    JOIN family_stats AS stats
      ON stats.scope_rank = family.scope_rank
     AND stats.family_count <= family_limit
    WHERE family.supersedes_id IS NULL

    UNION ALL

    SELECT
        newer.scope_rank,
        newer.id,
        walk.path || newer.id
    FROM walk
    JOIN family_rows AS newer
      ON newer.scope_rank = walk.scope_rank
     AND newer.supersedes_id = walk.id
    WHERE NOT newer.id = ANY(walk.path)
      AND pg_catalog.cardinality(walk.path) <= family_limit
),
walk_stats AS (
    SELECT
        walk.scope_rank,
        pg_catalog.count(DISTINCT walk.id)::INTEGER AS walked_count
    FROM walk
    GROUP BY walk.scope_rank
),
scope_checks AS (
    SELECT
        seed.*,
        stats.family_count,
        stats.active_count,
        stats.root_count,
        stats.invalid_status_count,
        stats.identity_drift_count,
        COALESCE(reciprocal.reciprocal, FALSE) AS reciprocal,
        COALESCE(walked.walked_count, 0) AS walked_count,
        CASE
            WHEN NOT seed.anchor_valid THEN 'invalid_anchor_scope'
            WHEN seed.seed_id IS NULL THEN 'document_seed_not_found'
            WHEN NOT seed.identity_complete THEN 'ambiguous_document_family'
            WHEN pg_catalog.lower(seed.language) <> 'es'
                THEN 'unsupported_document_language'
            WHEN seed.status <> 'active'
              OR seed.superseded_by_id IS NOT NULL
              OR pg_catalog.lower(seed.source_pdf_sha256)
                    IS DISTINCT FROM seed.anchor_extraction_sha256
              OR seed.source_pdf_filename
                    IS DISTINCT FROM seed.anchor_source_file
                THEN 'active_revision_not_bound_to_anchor_blob'
            WHEN stats.family_count > family_limit
                THEN 'document_scope_overflow'
            WHEN stats.identity_drift_count <> 0
                THEN 'ambiguous_document_family'
            WHEN stats.invalid_status_count <> 0
                THEN 'invalid_revision_status'
            WHEN stats.active_count <> 1
                THEN 'ambiguous_active_revision'
            WHEN stats.root_count <> 1
                THEN 'branched_or_cyclic_revision_chain'
            WHEN NOT COALESCE(reciprocal.reciprocal, FALSE)
                THEN 'nonreciprocal_revision_chain'
            WHEN COALESCE(walked.walked_count, 0) <> stats.family_count
                THEN 'incomplete_revision_chain'
            ELSE 'ok'
        END AS authority_status
    FROM seed_rows AS seed
    JOIN family_stats AS stats USING (scope_rank)
    LEFT JOIN reciprocal_stats AS reciprocal USING (scope_rank)
    LEFT JOIN walk_stats AS walked USING (scope_rank)
),
authorities AS (
    SELECT DISTINCT ON (check_row.seed_id)
        check_row.scope_rank,
        check_row.seed_id AS document_id,
        pg_catalog.lower(check_row.source_pdf_sha256) AS extraction_sha256,
        check_row.source_pdf_filename AS source_file,
        check_row.document_family,
        check_row.revision,
        check_row.language,
        check_row.doc_type,
        check_row.manufacturer,
        check_row.product_model,
        check_row.family_count
    FROM scope_checks AS check_row
    WHERE check_row.authority_status = 'ok'
    ORDER BY check_row.seed_id, check_row.scope_rank
),
ranked_candidates AS (
    SELECT
        candidate.id,
        candidate.document_id,
        candidate.extraction_sha256,
        candidate.chunk_index,
        candidate.content,
        candidate.context,
        candidate.section_title,
        candidate.product_model,
        candidate.language,
        candidate.source_file,
        candidate.page_number,
        candidate.duplicate_of,
        candidate.manufacturer,
        candidate.doc_type,
        authority.revision AS document_revision,
        authority.scope_rank AS authority_scope_rank,
        pg_catalog.row_number() OVER (
            PARTITION BY authority.document_id
            ORDER BY candidate.chunk_index ASC NULLS LAST, candidate.id ASC
        )::INTEGER AS snapshot_candidate_rank
    FROM authorities AS authority
    JOIN LATERAL (
        SELECT
            chunk.id,
            chunk.document_id,
            chunk.extraction_sha256,
            chunk.chunk_index,
            chunk.content,
            chunk.context,
            chunk.section_title,
            chunk.product_model,
            chunk.language,
            chunk.source_file,
            chunk.page_number,
            chunk.duplicate_of,
            chunk.manufacturer,
            chunk.doc_type
        FROM public.chunks_v2 AS chunk
        WHERE chunk.document_id = authority.document_id
          AND pg_catalog.lower(chunk.extraction_sha256)
                = authority.extraction_sha256
          AND chunk.source_file = authority.source_file
          AND chunk.language IS NOT DISTINCT FROM authority.language
          AND chunk.doc_type IS NOT DISTINCT FROM authority.doc_type
          AND chunk.manufacturer IS NOT DISTINCT FROM authority.manufacturer
          AND chunk.product_model IS NOT DISTINCT FROM authority.product_model
          AND chunk.duplicate_of IS NULL
          AND chunk.search_vector @@ pg_catalog.to_tsquery(
              'public.spanish_unaccent'::pg_catalog.regconfig,
              fts_query
          )
        ORDER BY chunk.chunk_index ASC NULLS LAST, chunk.id ASC
        LIMIT candidate_limit + 1
    ) AS candidate ON TRUE
),
bounded_candidates AS (
    SELECT *
    FROM ranked_candidates
    WHERE snapshot_candidate_rank <= candidate_limit + 1
),
payload AS (
    SELECT pg_catalog.jsonb_build_object(
        'schema', 'document_local_snapshot_v1',
        'input_status', CASE
            WHEN (SELECT request_valid FROM input_shape) THEN 'ok'
            ELSE 'invalid_request'
        END,
        'authorities', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'scope_rank', authority.scope_rank,
                    'document_id', authority.document_id,
                    'extraction_sha256', authority.extraction_sha256,
                    'source_file', authority.source_file,
                    'language', authority.language,
                    'revision', authority.revision,
                    'family_rows', authority.family_count
                )
                ORDER BY authority.document_id
            )
            FROM authorities AS authority
        ), '[]'::JSONB),
        'document_rows', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.to_jsonb(family)
                ORDER BY family.scope_rank, family.id
            )
            FROM family_rows AS family
        ), '[]'::JSONB),
        'candidates', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.to_jsonb(candidate)
                ORDER BY
                    candidate.document_id,
                    candidate.snapshot_candidate_rank,
                    candidate.id
            )
            FROM bounded_candidates AS candidate
        ), '[]'::JSONB),
        'rejections', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                pg_catalog.jsonb_build_object(
                    'scope_rank', check_row.scope_rank,
                    'reason', check_row.authority_status
                )
                ORDER BY check_row.scope_rank
            )
            FROM scope_checks AS check_row
            WHERE check_row.authority_status <> 'ok'
        ), '[]'::JSONB),
        'family_rows_read', (
            SELECT pg_catalog.count(*) FROM family_rows
        ),
        'candidate_rows', (
            SELECT pg_catalog.count(*) FROM bounded_candidates
        ),
        'candidate_overflow_scopes', COALESCE((
            SELECT pg_catalog.jsonb_agg(
                overflow.scope_rank ORDER BY overflow.scope_rank
            )
            FROM (
                SELECT DISTINCT candidate.authority_scope_rank AS scope_rank
                FROM bounded_candidates AS candidate
                WHERE candidate.snapshot_candidate_rank > candidate_limit
            ) AS overflow
        ), '[]'::JSONB)
    ) AS value
)
SELECT payload.value
FROM payload;
$function$;

REVOKE ALL ON FUNCTION public.document_local_snapshot_v1(
    JSONB, TEXT, INTEGER, INTEGER
) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.document_local_snapshot_v1(
    JSONB, TEXT, INTEGER, INTEGER
) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.document_local_snapshot_v1(
    JSONB, TEXT, INTEGER, INTEGER
) TO service_role;

COMMENT ON FUNCTION public.document_local_snapshot_v1(
    JSONB, TEXT, INTEGER, INTEGER
) IS
    'S277 read-only atomic lifecycle + exact-blob FTS snapshot; '
    'service_role only; ES v1; bounded at two scopes.';

NOTIFY pgrst, 'reload schema';
