-- ============================================================================
-- s308 — Backfill de `documents.product_model` desde los chunks CURADOS (#65)
-- ============================================================================
-- POR QUÉ. La campaña H0 (s285, DEC-161) re-tagueó la identidad en los CHUNKS
-- (unknown 318→1) pero `documents.product_model` conservó los valores de ingesta:
-- para `MADT235` dice `AFP4000` mientras sus chunks curados dicen `ART1194`, y
-- mantiene `unknown` donde los chunks ya tienen identidad. En s307 esa columna
-- stale casi entra como fuente del inventario por fabricante — el próximo
-- consumidor caerá. Este backfill la reconcilia UNA vez desde la verdad curada.
--
-- ALCANCE (dimensionado contra la base viva, 8-ago):
--   · 591 docs INEQUÍVOCOS: exactamente UN product_model curado distinto en sus
--     chunks (vía document_id), y difiere del valor en documents → SE ACTUALIZAN.
--   · 0 docs ambiguos (ninguún doc tiene >1 pm curado — firma s304).
--   · 413 ya coinciden · 165 sin chunks curados → NO SE TOCAN.
--
-- REVERSIBLE: los valores previos quedan en `_s308_backup_documents_pm`
-- (patrón de las campañas s285/s287). Rollback:
--   UPDATE documents d SET product_model = b.product_model_old
--     FROM _s308_backup_documents_pm b WHERE d.id = b.document_id;
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public._s308_backup_documents_pm (
    document_id UUID PRIMARY KEY,
    product_model_old TEXT,
    product_model_new TEXT,
    backed_up_at TIMESTAMPTZ DEFAULT NOW()
);

WITH curado AS (
    SELECT d.id,
           d.product_model AS pm_doc,
           (SELECT array_agg(DISTINCT c.product_model)
              FROM public.chunks_v2 c
             WHERE c.document_id = d.id
               AND c.product_model IS NOT NULL AND c.product_model <> ''
               AND lower(c.product_model) <> 'unknown') AS pms
      FROM public.documents d
), inequivocos AS (
    SELECT id, pm_doc, pms[1] AS pm_curado
      FROM curado
     WHERE array_length(pms, 1) = 1
       AND pms[1] IS DISTINCT FROM pm_doc
)
INSERT INTO public._s308_backup_documents_pm
            (document_id, product_model_old, product_model_new)
SELECT id, pm_doc, pm_curado FROM inequivocos
ON CONFLICT (document_id) DO NOTHING;

UPDATE public.documents d
   SET product_model = b.product_model_new
  FROM public._s308_backup_documents_pm b
 WHERE d.id = b.document_id
   AND d.product_model IS DISTINCT FROM b.product_model_new;

-- Postcondiciones: (1) el caso probado del #65 quedó corregido; (2) no queda
-- ningún doc inequívocamente desalineado; (3) el respaldo existe y dimensiona.
DO $s308_post$
DECLARE
    n_backup  INT;
    n_desalineados INT;
    pm_madt   TEXT;
BEGIN
    SELECT COUNT(*) INTO n_backup FROM public._s308_backup_documents_pm;
    IF n_backup < 500 THEN
        RAISE EXCEPTION 's308: respaldo con % filas — se esperaban ~591', n_backup;
    END IF;

    SELECT product_model INTO pm_madt FROM public.documents
     WHERE source_pdf_filename = 'MADT235' LIMIT 1;
    IF pm_madt IS DISTINCT FROM 'ART1194' THEN
        RAISE EXCEPTION 's308: MADT235 sigue diciendo % (esperado ART1194)', pm_madt;
    END IF;

    WITH curado AS (
        SELECT d.id, d.product_model AS pm_doc,
               (SELECT array_agg(DISTINCT c.product_model)
                  FROM public.chunks_v2 c
                 WHERE c.document_id = d.id
                   AND c.product_model IS NOT NULL AND c.product_model <> ''
                   AND lower(c.product_model) <> 'unknown') AS pms
          FROM public.documents d)
    SELECT COUNT(*) INTO n_desalineados FROM curado
     WHERE array_length(pms, 1) = 1 AND pms[1] IS DISTINCT FROM pm_doc;
    IF n_desalineados <> 0 THEN
        RAISE EXCEPTION 's308: quedan % docs inequívocos sin reconciliar', n_desalineados;
    END IF;
END;
$s308_post$;

COMMIT;
