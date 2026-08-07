-- ============================================================================
-- s308 v2 — Backfill de `documents.product_model` desde los chunks CURADOS (#65)
-- ============================================================================
-- POR QUÉ. La campaña H0 (s285, DEC-161) re-tagueó la identidad en los CHUNKS
-- (unknown 318→1) pero `documents.product_model` conservó los valores de ingesta:
-- para `MADT235` dice `AFP4000` mientras sus chunks curados dicen `ART1194`. En
-- s307 esa columna stale casi entra como fuente del inventario — el próximo
-- consumidor caerá. Este backfill la reconcilia desde la verdad curada.
--
-- ⚠️ IMPACTO EN SERVING, DECLARADO (Sol s308 — mi claim «byte-idéntico» era FALSO):
-- el RPC document-local de s278 SÍ lee `documents.product_model` (exige identidad
-- no vacía y la compara entre revisiones). Medido en vivo: **175 de los 591 docs
-- pasan de sin-identidad (NULL/''/unknown) a identidad curada** → ganan
-- elegibilidad en esa lane. Es una CORRECCIÓN (la lane estaba bloqueada por
-- metadato roto), observable en `rag_trace.coverage.lane_outcomes`. Riesgo de
-- deriva de linaje MEDIDO Y NULO: solo 5 docs tocados tienen linaje y 0 tienen
-- hermanos fuera del conjunto (postcondición 5 lo re-verifica igualmente).
--
-- SEMÁNTICA DE RE-EJECUCIÓN (dúo s308, convergente): esta migración re-impone la
-- verdad CURADA cada vez que se corre, y RESPALDA TODO lo que pisa, también en
-- re-runs (el respaldo es multi-fila por documento: PK document_id+backed_up_at —
-- la v1 con ON CONFLICT DO NOTHING habría pisado ediciones manuales SIN respaldo).
-- Una edición manual de identidad en `documents` NO es el sitio: la identidad se
-- cura en los CHUNKS y este backfill la propaga. Rollback al estado pre-run N:
--   UPDATE documents d SET product_model = b.product_model_old
--     FROM _s308_backup_documents_pm b
--    WHERE d.id = b.document_id AND b.backed_up_at >= '<ts del run N>';
--
-- ALCANCE (dimensionado vivo, 8-ago): 591 inequívocos (UN pm curado ≠ documents;
-- 585 active + 5 needs_review + 1 superseded) · 0 ambiguos · 413 ya coinciden ·
-- 165 sin chunks curados NO se tocan.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public._s308_backup_documents_pm (
    document_id UUID NOT NULL,
    product_model_old TEXT,
    product_model_new TEXT,
    backed_up_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_id, backed_up_at)
);

-- Hardening (Sol s308): mismo listón que toda tabla de public — RLS y API a cero.
ALTER TABLE public._s308_backup_documents_pm ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON public._s308_backup_documents_pm
    FROM PUBLIC, anon, authenticated;

DO $s308$
DECLARE
    n_ineq   INT;
    n_backup INT;
    n_upd    INT;
    n_resid  INT;
    n_linajes_mixtos INT;
    pm_madt  TEXT;
BEGIN
    -- 1. El conjunto INEQUÍVOCO se calcula FRESCO en cada ejecución (nunca desde
    --    el respaldo: el respaldo es auditoría, no fuente — dúo s308).
    CREATE TEMP TABLE _s308_ineq ON COMMIT DROP AS
    SELECT d.id,
           d.product_model AS pm_viejo,
           (SELECT (array_agg(DISTINCT c.product_model))[1]
              FROM public.chunks_v2 c
             WHERE c.document_id = d.id
               AND c.product_model IS NOT NULL AND c.product_model <> ''
               AND lower(c.product_model) <> 'unknown') AS pm_nuevo
      FROM public.documents d
     WHERE (SELECT COUNT(DISTINCT c.product_model)
              FROM public.chunks_v2 c
             WHERE c.document_id = d.id
               AND c.product_model IS NOT NULL AND c.product_model <> ''
               AND lower(c.product_model) <> 'unknown') = 1;
    DELETE FROM _s308_ineq WHERE pm_nuevo IS NOT DISTINCT FROM pm_viejo;

    -- 2. Cota de radio de acción ANTES de escribir (Sol s308: «solo toca 591» no
    --    estaba protegido — una selección accidental de miles habría pasado).
    SELECT COUNT(*) INTO n_ineq FROM _s308_ineq;
    IF n_ineq > 700 THEN
        RAISE EXCEPTION 's308: % inequívocos — cota 700; selección sospechosa', n_ineq;
    END IF;
    -- En el PRIMER run se esperan ~591; en re-runs sanos, 0. Ambos son legales.

    -- 3. Respaldo de TODO lo que se va a pisar, SIEMPRE (multi-fila: re-runs
    --    también quedan auditados).
    INSERT INTO public._s308_backup_documents_pm
                (document_id, product_model_old, product_model_new)
    SELECT id, pm_viejo, pm_nuevo FROM _s308_ineq;
    GET DIAGNOSTICS n_backup = ROW_COUNT;
    IF n_backup <> n_ineq THEN
        RAISE EXCEPTION 's308: respaldo % ≠ inequívocos %', n_backup, n_ineq;
    END IF;

    -- 4. El UPDATE, desde el conjunto FRESCO — y ni una fila más.
    UPDATE public.documents d
       SET product_model = i.pm_nuevo
      FROM _s308_ineq i
     WHERE d.id = i.id;
    GET DIAGNOSTICS n_upd = ROW_COUNT;
    IF n_upd <> n_ineq THEN
        RAISE EXCEPTION 's308: update % ≠ inequívocos %', n_upd, n_ineq;
    END IF;

    -- 5. Postcondiciones sobre el ESTADO FINAL (abortan la transacción entera):
    --    caso probado del #65 · 0 inequívocos residuales · 0 linajes que este run
    --    haya dejado MIXTOS (la comparación de identidad entre revisiones del RPC
    --    s278 exige consistencia dentro del linaje).
    SELECT product_model INTO pm_madt FROM public.documents
     WHERE source_pdf_filename = 'MADT235' LIMIT 1;
    IF pm_madt IS DISTINCT FROM 'ART1194' THEN
        RAISE EXCEPTION 's308: MADT235 dice % (esperado ART1194)', pm_madt;
    END IF;

    SELECT COUNT(*) INTO n_resid FROM (
        SELECT d.id FROM public.documents d
         WHERE (SELECT COUNT(DISTINCT c.product_model) FROM public.chunks_v2 c
                 WHERE c.document_id = d.id AND c.product_model IS NOT NULL
                   AND c.product_model <> '' AND lower(c.product_model) <> 'unknown') = 1
           AND (SELECT (array_agg(DISTINCT c.product_model))[1] FROM public.chunks_v2 c
                 WHERE c.document_id = d.id AND c.product_model IS NOT NULL
                   AND c.product_model <> '' AND lower(c.product_model) <> 'unknown')
               IS DISTINCT FROM d.product_model
    ) t;
    IF n_resid <> 0 THEN
        RAISE EXCEPTION 's308: quedan % inequívocos sin reconciliar', n_resid;
    END IF;

    SELECT COUNT(*) INTO n_linajes_mixtos FROM (
        SELECT d2.revision_lineage_id
          FROM public.documents d2
         WHERE d2.revision_lineage_id IN (
                   SELECT d3.revision_lineage_id FROM public.documents d3
                    WHERE d3.id IN (SELECT id FROM _s308_ineq)
                      AND d3.revision_lineage_id IS NOT NULL)
           AND COALESCE(btrim(d2.product_model), '') <> ''
         GROUP BY d2.revision_lineage_id
        HAVING COUNT(DISTINCT d2.product_model) > 1
    ) t;
    IF n_linajes_mixtos <> 0 THEN
        RAISE EXCEPTION 's308: % linajes tocados quedaron MIXTOS', n_linajes_mixtos;
    END IF;
END;
$s308$;

COMMIT;
