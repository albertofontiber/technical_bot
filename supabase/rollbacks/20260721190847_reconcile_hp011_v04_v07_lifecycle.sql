-- MANUAL ROLLBACK ONLY. Supabase does not apply files from this directory.
-- Review and execute this file as one transaction only if the matching
-- 20260721190847 migration has been applied and must be reversed.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE TEMPORARY TABLE hp011_v07_v04_duplicate_snapshot (
    chunk_id UUID PRIMARY KEY,
    previous_duplicate_of UUID NOT NULL
) ON COMMIT DROP;

INSERT INTO hp011_v07_v04_duplicate_snapshot (
    chunk_id,
    previous_duplicate_of
)
VALUES
    ('01b364e4-6711-4347-b3fe-26e75dc96940', '948028f3-b1c7-4aee-b7ff-2ec1c161052a'),
    ('021c8eee-c1f5-40b1-b126-1ef0e47711f6', '5c7759f3-ef89-4561-a984-55a7a01fa37a'),
    ('0381d19c-2c11-4895-879a-21dbc71d241f', 'b281a5eb-8fff-4480-8a27-e8b02530f655'),
    ('0759a15b-d99c-4b2e-8c9e-58ad7235b5a9', '2ad1fead-dfc5-42d9-9ab4-186398801dcd'),
    ('18140a8a-ab2c-40d4-a81f-2532fbe1b838', '7919bc22-93b6-412c-a28e-f8571f9b39cc'),
    ('2698d9e6-01ef-4075-a741-5dc83b478a57', '675a5d00-946b-4b7a-952b-091be118ebc7'),
    ('2be46e9d-4e01-4f73-84b3-05c92448eacd', '51d7c851-0dcc-4e30-aa65-e2897ec317df'),
    ('32b08704-bec1-4029-a763-d7d87637b1a4', '6da3a9e7-9a02-4599-a9d3-06a4c16628a5'),
    ('3799f087-f6ff-4b05-80fe-745fbc884e58', '2a34b5fc-a7ad-4b7d-b685-778bee8bf612'),
    ('3a661567-4030-4931-af63-99d4bc229505', 'c08f361f-ad81-431f-b5b2-2fb53650bba9'),
    ('475a8f18-7c69-4c7a-8111-45bd67334c96', '77d07600-c619-4ea0-b1ab-0683ddb79697'),
    ('56d1c5d9-ff07-4164-a94f-0c9760b90b2b', '51d7c851-0dcc-4e30-aa65-e2897ec317df'),
    ('5b8590d1-30cd-4a0a-9cc3-2b5c8a65a87b', '7b9ee0c1-0b45-4846-b205-c16d19bfe2e5'),
    ('68f06bc3-55c9-4c5c-a1aa-6b84075a7832', 'c8cb30ce-f372-46fd-b0ff-730e98648e0b'),
    ('6af703df-1a2a-491b-955f-381fa745e7f2', 'e0820cf6-f94f-41d8-8880-9e7a50dcb5f8'),
    ('6e2c0c11-aa6e-4766-a687-4c77879eb496', 'c7545546-f560-4644-a344-a90fb7f95708'),
    ('77d4e1e0-3e3e-48eb-b915-e5a6a85b8ed4', 'dcac98aa-3b8a-4cf9-9150-fe04342dc30b'),
    ('7d5abb00-d546-498d-9654-d6a3dc474e01', '0eb5fb4b-7cdb-4467-87f3-81040f351db3'),
    ('868baea7-0c0a-4ede-9393-e3e35e6b54d3', '835c1cbf-9d61-47c3-a6bf-96fd4045dd74'),
    ('93bf8172-faa2-4566-b936-184d2e5d9cb8', 'ee8eaf02-765e-4b97-b489-5e19f2cb3ef0'),
    ('9f16333e-37a7-4aef-b5e8-d7aae4545c92', '7408f9bf-f6be-4e21-a2a4-bff05fc77790'),
    ('9f971dff-f82d-42bd-b92c-588bc1d11638', '5bedbb18-fbd6-434b-b180-03ee2042d2ee'),
    ('a3549931-2b65-4611-8e46-5aea49bc995e', 'bbeef949-7a3e-4981-85c6-5549fae3faf9'),
    ('af6728be-6f4e-447a-b77f-5436a076ee39', 'c20c2756-87d0-4cd1-bd79-f9ba038e2644'),
    ('b19cc5cd-1483-4b05-8504-8348a6364f5a', 'a9a55135-1b42-4f05-a60b-1b1591d31bba'),
    ('b3c5c2e4-99ba-471e-ad57-8ac8f6a7cee2', 'efd88874-9db7-41c9-96f9-47607b42af33'),
    ('b7e7f9f9-3e99-4d0c-8a4b-3447cf5c1c48', 'ddc6d884-5380-470c-ad17-eee7c14d881d'),
    ('c0a6c7b6-0063-4280-ac12-e5d9b9a3edc6', '5772bc52-f686-4609-8ca0-2a88958f7061'),
    ('c11597fd-7f2c-49b2-853e-f616594fd900', 'b0e6bee6-d492-428e-8948-a66230a57267'),
    ('c91acf0f-2b37-4106-837a-a9f774d1d999', '1aa9b7dd-4ca3-41e8-b399-930ba4ec9c2f'),
    ('d257600d-c510-4053-b9a6-d5fe05e0db06', '45e54f2e-dd33-4709-9ce4-f46e31fe1c70'),
    ('df54b79b-3d7e-4400-8d0d-0a1c6ba4146a', '9cbee4fa-9380-4970-aa9d-1acafb7c67c8'),
    ('e6e6af6a-84d3-4d13-bd02-b5aa3e2f87f0', '2a7b427b-e760-4fc8-9be9-b4d32b4703ff'),
    ('f18362c6-26d2-4bb2-8c97-f1a4fb81729e', 'b4347ec9-0c3e-42fb-a2f2-d1a6f8b79b42'),
    ('f4520a5f-eb24-4808-8902-4f285bbe78e5', '436a5794-8b3f-4519-a776-23c5ca5cc68e'),
    ('f6d3b846-41e3-47c1-905c-23f59807f113', 'b3650bec-3444-41fb-a506-4c25171b3cff'),
    ('f73a5c21-5362-42ea-9908-1eda78890fba', 'f9bed261-c2b3-40ef-86fb-8a74fa4e6de9'),
    ('fa449654-2dba-4064-a6c7-4bfdec83d21c', 'dcac98aa-3b8a-4cf9-9150-fe04342dc30b');

DO $hp011_lifecycle_rollback$
DECLARE
    old_document CONSTANT UUID := 'e98e05ff-ee1d-5341-869a-65768855dae9';
    new_document CONSTANT UUID := '494e71be-873b-48c1-adb3-a21a122da111';
    old_extraction CONSTANT TEXT :=
        'ccabe3df906990c9b95d0d180d811e0444278089d4ce30678d86948cb197e93e';
    new_extraction CONSTANT TEXT :=
        '914ceacf8395729f73876cb9e397a8cb3154d70ba67903b6e055f2b4398be573';
    old_notes_before CONSTANT TEXT :=
        'Validated source split from legacy multi-hash parent. Cover: HLSI-MN-103 v.04, November 2013. Lifecycle precedence intentionally deferred.';
    new_notes_before CONSTANT TEXT := E'Backfilled from pre-migration chunks (Phase 1 of document-management refactor).\nValidated source split: cover HLSI-MN-103 v.07, May 2018. Lifecycle precedence intentionally deferred.';
    resolved_note CONSTANT TEXT :=
        'Lifecycle precedence resolved by migration 20260721190847: v.07 supersedes v.04; HP011 source-contract adjudication.';
    changed BIGINT;
BEGIN
    PERFORM d.id
      FROM public.documents AS d
     WHERE d.id IN (old_document, new_document)
     ORDER BY d.id
     FOR UPDATE;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 2 THEN
        RAISE EXCEPTION 'HP011 rollback document lock cardinality drift: %', changed;
    END IF;

    PERFORM c.id
      FROM public.chunks_v2 AS c
     WHERE c.document_id IN (old_document, new_document)
     ORDER BY c.id
     FOR UPDATE;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 190 THEN
        RAISE EXCEPTION 'HP011 rollback chunk lock cardinality drift: %', changed;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id = old_document
           AND revision = 'v.04'
           AND revision_date = DATE '2013-11-01'
           AND source_pdf_sha256 = old_extraction
           AND status = 'superseded'
           AND supersedes_id IS NULL
           AND superseded_by_id = new_document
           AND notes = replace(
               old_notes_before,
               'Lifecycle precedence intentionally deferred.',
               resolved_note
           )
    ) OR NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id = new_document
           AND revision = 'v.07'
           AND revision_date = DATE '2018-05-01'
           AND source_pdf_sha256 = new_extraction
           AND status = 'active'
           AND supersedes_id = old_document
           AND superseded_by_id IS NULL
           AND notes = replace(
               new_notes_before,
               'Lifecycle precedence intentionally deferred.',
               resolved_note
           )
    ) THEN
        RAISE EXCEPTION 'HP011 rollback lifecycle precondition drift';
    END IF;

    IF (SELECT count(*) FROM pg_temp.hp011_v07_v04_duplicate_snapshot) <> 38
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = old_document) <> 94
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = new_document) <> 96
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = old_document
              AND extraction_sha256 = old_extraction) <> 94
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = new_document
              AND extraction_sha256 = new_extraction) <> 96
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = old_document AND duplicate_of IS NOT NULL) <> 43
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id = new_document AND duplicate_of IS NOT NULL) <> 4
       OR EXISTS (
            SELECT 1
              FROM public.chunks_v2 AS c
              JOIN public.chunks_v2 AS target ON target.id = c.duplicate_of
             WHERE c.document_id = new_document
               AND target.document_id = old_document
       ) THEN
        RAISE EXCEPTION 'HP011 rollback source or dedupe precondition drift';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM pg_temp.hp011_v07_v04_duplicate_snapshot AS expected
          LEFT JOIN public.chunks_v2 AS c ON c.id = expected.chunk_id
          LEFT JOIN public.chunks_v2 AS target
            ON target.id = expected.previous_duplicate_of
         WHERE c.document_id IS DISTINCT FROM new_document
            OR c.extraction_sha256 IS DISTINCT FROM new_extraction
            OR c.duplicate_of IS NOT NULL
            OR target.document_id IS DISTINCT FROM old_document
            OR target.extraction_sha256 IS DISTINCT FROM old_extraction
    ) THEN
        RAISE EXCEPTION 'HP011 rollback snapshot no longer matches target rows';
    END IF;

    UPDATE public.chunks_v2 AS c
       SET duplicate_of = expected.previous_duplicate_of
      FROM pg_temp.hp011_v07_v04_duplicate_snapshot AS expected
     WHERE c.id = expected.chunk_id
       AND c.document_id = new_document
       AND c.duplicate_of IS NULL;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 38 THEN
        RAISE EXCEPTION 'HP011 rollback dedupe restore count drift: %', changed;
    END IF;

    UPDATE public.documents
       SET status = 'active',
           superseded_by_id = NULL,
           notes = old_notes_before
     WHERE id = old_document
       AND status = 'superseded'
       AND supersedes_id IS NULL
       AND superseded_by_id = new_document;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN
        RAISE EXCEPTION 'HP011 rollback v.04 update count drift: %', changed;
    END IF;

    UPDATE public.documents
       SET supersedes_id = NULL,
           notes = new_notes_before
     WHERE id = new_document
       AND status = 'active'
       AND supersedes_id = old_document
       AND superseded_by_id IS NULL;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN
        RAISE EXCEPTION 'HP011 rollback v.07 update count drift: %', changed;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id = old_document
           AND status = 'active'
           AND supersedes_id IS NULL
           AND superseded_by_id IS NULL
           AND notes = old_notes_before
    ) OR NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id = new_document
           AND status = 'active'
           AND supersedes_id IS NULL
           AND superseded_by_id IS NULL
           AND notes = new_notes_before
    ) OR (SELECT count(*) FROM public.chunks_v2
         WHERE document_id = old_document AND duplicate_of IS NOT NULL) <> 43
       OR (SELECT count(*) FROM public.chunks_v2
         WHERE document_id = new_document AND duplicate_of IS NOT NULL) <> 42
       OR (SELECT count(*)
             FROM public.chunks_v2 AS c
             JOIN public.chunks_v2 AS target ON target.id = c.duplicate_of
            WHERE c.document_id = old_document
              AND target.document_id = new_document) <> 40
       OR (SELECT count(*)
             FROM public.chunks_v2 AS c
             JOIN public.chunks_v2 AS target ON target.id = c.duplicate_of
            WHERE c.document_id = new_document
              AND target.document_id = old_document) <> 38
       OR (SELECT count(*)
             FROM public.chunks_v2 AS c
             JOIN public.chunks_v2 AS target ON target.id = c.duplicate_of
            WHERE c.document_id = old_document
              AND target.document_id = old_document) <> 3
       OR (SELECT count(*)
             FROM public.chunks_v2 AS c
             JOIN public.chunks_v2 AS target ON target.id = c.duplicate_of
            WHERE c.document_id = new_document
              AND target.document_id = new_document) <> 4 THEN
        RAISE EXCEPTION 'HP011 rollback postcondition failed';
    END IF;
END
$hp011_lifecycle_rollback$;

COMMIT;
