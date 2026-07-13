-- Reconcile four visually verified source blobs without changing lifecycle or
-- retrieval ranking. This migration is deliberately narrow: it does not deploy
-- the stale monolithic migration 016, quarantine rows, rewrite retrieval RPCs,
-- or infer revision precedence. Both hp011 revisions remain active until a
-- separate measured lifecycle gate decides whether v.04 should be superseded.

DO $reconcile$
DECLARE
    hp011_document constant uuid := '494e71be-873b-48c1-adb3-a21a122da111';
    hp011_v04_document constant uuid := 'e98e05ff-ee1d-5341-869a-65768855dae9';
    hp014_document constant uuid := '17bd36ac-412b-4607-aa52-f9dbf37e26b7';
    hp017_document constant uuid := '17d4b914-fa21-4b41-a928-bafe1846528a';
    hp011_v04_sha constant text := 'ccabe3df906990c9b95d0d180d811e0444278089d4ce30678d86948cb197e93e';
    hp011_v07_sha constant text := '914ceacf8395729f73876cb9e397a8cb3154d70ba67903b6e055f2b4398be573';
    hp014_sha constant text := '28d55702e22a558f39771aae39782ee80f9390ed237f214cad9c76a2c75a70c6';
    hp017_sha constant text := 'bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b';
    before_documents bigint;
    before_chunks bigint;
    before_enunciados bigint;
    before_hyq bigint;
    changed bigint;
BEGIN
    -- Migration 016 owns a different, review-gated admission model. Never
    -- bypass it if it has subsequently been installed.
    IF to_regclass('public.document_ingestion_identity_bindings') IS NOT NULL
       OR to_regclass('public.document_ingestion_identity_admissions') IS NOT NULL THEN
        RAISE EXCEPTION
            'validated revision reconciliation must use the deployed admission workflow';
    END IF;
    IF to_regprocedure('public.corpus_fingerprint_v1()') IS NULL THEN
        RAISE EXCEPTION 'migration 014 corpus fingerprint prerequisite is missing';
    END IF;

    SELECT count(*) INTO before_documents FROM public.documents;
    SELECT count(*) INTO before_chunks FROM public.chunks_v2;
    SELECT count(*) INTO before_enunciados FROM public.chunks_v2_enunciados;
    SELECT count(*) INTO before_hyq FROM public.chunks_v2_hyq;

    IF NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id=hp011_document AND status='active'
           AND document_family='HLSI-MN-103_RP1r-Supra_lr'
           AND manufacturer='Notifier'
           AND source_pdf_sha256='backfill:6ca8d2760eb6fdf5f3f1131ae692534f2cc1f75382608f5deda47a216f1c75e5'
    ) THEN
        RAISE EXCEPTION 'hp011 registry precondition drift';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id=hp014_document AND status='active'
           AND document_family='MIDT180' AND manufacturer='Notifier'
           AND source_pdf_sha256='backfill:fa38b368fd6d52ae5fbabb5b6f73264fbb6e35382c043db9c2b51e158e462632'
    ) THEN
        RAISE EXCEPTION 'hp014 registry precondition drift';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.documents
         WHERE id=hp017_document AND status='active'
           AND document_family='997-671-005-3_Configuration_ES'
           AND manufacturer='Notifier'
           AND source_pdf_sha256='backfill:59241d920b1488ada6687f9157b19c51d749e0f689e497ac55c324826f0ac2c5'
    ) THEN
        RAISE EXCEPTION 'hp017 registry precondition drift';
    END IF;
    IF EXISTS (SELECT 1 FROM public.documents WHERE id=hp011_v04_document)
       OR EXISTS (
            SELECT 1 FROM public.documents
             WHERE source_pdf_sha256 IN (hp011_v04_sha, hp011_v07_sha, hp014_sha, hp017_sha)
       ) THEN
        RAISE EXCEPTION 'target exact source identity already exists or conflicts';
    END IF;

    IF (SELECT count(*) FROM public.chunks_v2 WHERE document_id=hp011_document) <> 190
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id=hp011_document AND extraction_sha256=hp011_v04_sha) <> 94
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id=hp011_document AND extraction_sha256=hp011_v07_sha) <> 96
       OR (SELECT count(DISTINCT extraction_sha256) FROM public.chunks_v2
            WHERE document_id=hp011_document) <> 2
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id=hp014_document AND extraction_sha256=hp014_sha) <> 88
       OR (SELECT count(*) FROM public.chunks_v2 WHERE document_id=hp014_document) <> 88
       OR (SELECT count(*) FROM public.chunks_v2
            WHERE document_id=hp017_document AND extraction_sha256=hp017_sha) <> 124
       OR (SELECT count(*) FROM public.chunks_v2 WHERE document_id=hp017_document) <> 124
       OR (SELECT count(*) FROM public.chunks_v2_enunciados
            WHERE document_id=hp011_document AND extraction_sha256=hp011_v04_sha) <> 2 THEN
        RAISE EXCEPTION 'target chunk partition precondition drift';
    END IF;

    INSERT INTO public.documents (
        id, document_family, revision, revision_date, language, doc_type,
        manufacturer, product_model, source_pdf_filename, source_pdf_sha256,
        status, supersedes_id, superseded_by_id, ingested_at, notes
    )
    SELECT hp011_v04_document, document_family, 'v.04', DATE '2013-11-01',
           'es', 'usuario', manufacturer, product_model, source_pdf_filename,
           hp011_v04_sha, 'active', NULL, NULL, ingested_at,
           'Validated source split from legacy multi-hash parent. Cover: HLSI-MN-103 v.04, November 2013. Lifecycle precedence intentionally deferred.'
      FROM public.documents WHERE id=hp011_document;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'hp011 v.04 document insert failed'; END IF;

    UPDATE public.documents
       SET revision='v.07', revision_date=DATE '2018-05-01', language='es',
           doc_type='usuario', source_pdf_sha256=hp011_v07_sha,
           notes=coalesce(notes || E'\n', '') ||
             'Validated source split: cover HLSI-MN-103 v.07, May 2018. Lifecycle precedence intentionally deferred.'
     WHERE id=hp011_document;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'hp011 v.07 registry update failed'; END IF;

    UPDATE public.chunks_v2
       SET document_id=hp011_v04_document
     WHERE document_id=hp011_document AND extraction_sha256=hp011_v04_sha;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 94 THEN RAISE EXCEPTION 'hp011 v.04 chunk split count drift: %', changed; END IF;

    UPDATE public.chunks_v2_enunciados
       SET document_id=hp011_v04_document
     WHERE document_id=hp011_document AND extraction_sha256=hp011_v04_sha;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 2 THEN RAISE EXCEPTION 'hp011 v.04 enunciado split count drift: %', changed; END IF;

    UPDATE public.documents
       SET revision='MI-DT-180', revision_date=DATE '2003-03-31', language='es',
           doc_type='instalacion', source_pdf_sha256=hp014_sha,
           notes=coalesce(notes || E'\n', '') ||
             'Validated local source blob. Cover: MI-DT-180 (Doc. 997-214), 31 March 2003.'
     WHERE id=hp014_document;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'hp014 registry update failed'; END IF;

    UPDATE public.documents
       SET revision='997-671-005-3', revision_date=NULL, language='es',
           doc_type='programacion', source_pdf_sha256=hp017_sha,
           notes=coalesce(notes || E'\n', '') ||
             'Validated local source blob. Cover declares document 997-671-005-3; revision date not asserted.'
     WHERE id=hp017_document;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'hp017 registry update failed'; END IF;

    IF (SELECT count(*) FROM public.documents) <> before_documents + 1
       OR (SELECT count(*) FROM public.chunks_v2) <> before_chunks
       OR (SELECT count(*) FROM public.chunks_v2_enunciados) <> before_enunciados
       OR (SELECT count(*) FROM public.chunks_v2_hyq) <> before_hyq THEN
        RAISE EXCEPTION 'global corpus cardinality changed unexpectedly';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM public.chunks_v2 c
          JOIN public.documents d ON d.id=c.document_id
         WHERE c.document_id IN (hp011_document, hp011_v04_document,
                                 hp014_document, hp017_document)
           AND c.extraction_sha256 IS DISTINCT FROM d.source_pdf_sha256
    ) THEN
        RAISE EXCEPTION 'reconciled chunk/document source identity mismatch';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM public.chunks_v2_enunciados e
          JOIN public.chunks_v2 p ON p.id=e.parent_id
         WHERE p.document_id IN (hp011_document, hp011_v04_document,
                                 hp014_document, hp017_document)
           AND e.document_id IS DISTINCT FROM p.document_id
    ) THEN
        RAISE EXCEPTION 'reconciled enunciado/parent document identity mismatch';
    END IF;
END
$reconcile$;

COMMENT ON COLUMN public.documents.source_pdf_sha256 IS
'SHA-256 of exact PDF bytes. Legacy backfill placeholders remain unreviewed; reconciled rows are bound to locally verified blobs.';
