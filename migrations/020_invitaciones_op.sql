-- ============================================================================
-- 020 — `bot_invitaciones.op` (idempotencia por OPERACIÓN) + `revocada_por`
--       (la firma de la anulación, de raíz). s324j; diseño:
--       `evals/s324i_panel_vercel_propuesta_v9.md` §4.2-§4.3 (DEC-239).
--
-- ⚠️ CONTRATO DE APLICACIÓN (v9 §13, lección de la 016): este fichero se
--    aplica ENTERO con un aplicador transaccional — el SQL Editor de Supabase
--    o `psql --single-transaction` — nunca sentencia a sentencia. NO lleva
--    BEGIN/COMMIT propios a propósito (los dos fallos reales de la 016).
--
-- POR QUÉ EXISTE CADA PIEZA:
--   · `op`: el F5 sobre «Generar enlace» reenviaba el formulario y emitía una
--     credencial de más. La clave identifica LA OPERACIÓN (el formulario
--     pintado), no su contenido — un reintento choca con el UNIQUE y no crea
--     nada; una segunda emisión intencional trae un op nuevo y sí.
--   · `revocada_por`: anular una invitación estaba ROTA contra Supabase real
--     (hallazgo S-C1 del dúo, DEC-239): r41 firmaba la anulación en `nota` y
--     la 016 nunca concedió `UPDATE (nota)` — el PATCH entero moría con 42501,
--     invisible para los tests sin red. El cierre NO es conceder la nota (el
--     parche perpetuado): es la columna que faltaba, con el CHECK del patrón
--     `bot_allowlist_revocacion_completa` y el backfill que lo hace posible.
--
-- REVERSIBILIDAD: `ALTER TABLE public.bot_invitaciones DROP CONSTRAINT
-- bot_invitaciones_revocacion_completa, DROP COLUMN op, DROP COLUMN
-- revocada_por;` (los GRANT por columna caen con las columnas).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FASE A — `op`: NOT NULL también para las filas nuevas (v9 §4.2, ronda S2-M6:
-- un UNIQUE nullable admite infinitos NULL y no obliga a nadie). El DEFAULT es
-- lo que permite el NOT NULL sin romper a NADIE: un default VOLÁTIL se evalúa
-- POR FILA en el ADD COLUMN — cada fila histórica recibe un valor distinto y
-- el UNIQUE no choca; y el CLI, que no envía `op`, queda cubierto con la
-- semántica correcta (cada invocación del CLI ES una operación distinta).
-- ----------------------------------------------------------------------------
ALTER TABLE public.bot_invitaciones
    ADD COLUMN op TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::text
    CHECK (char_length(op) BETWEEN 8 AND 64);

COMMENT ON COLUMN public.bot_invitaciones.op IS
    'Token de OPERACIÓN (s324j/DEC-239): identifica el formulario pintado, no '
    'el contenido. El F5 reenvía el mismo op → UNIQUE → «ya emitiste», sin '
    'segunda credencial. Ruido aleatorio, sin dato personal.';

-- ----------------------------------------------------------------------------
-- FASE B — `revocada_por`: columna + backfill + CHECK estricto
-- ----------------------------------------------------------------------------
ALTER TABLE public.bot_invitaciones ADD COLUMN revocada_por TEXT;

-- El backfill hace posible el CHECK estricto sobre las filas YA anuladas: no
-- se inventa un autor (sería falsificar la historia), se declara que es
-- anterior a la columna.
UPDATE public.bot_invitaciones
   SET revocada_por = '(anterior a la 020)'
 WHERE revocada_at IS NOT NULL;

-- El patrón LITERAL de `bot_allowlist_revocacion_completa` (016): fecha y
-- firma van JUNTAS o no van — una anulación sin autor no puede existir.
ALTER TABLE public.bot_invitaciones
    ADD CONSTRAINT bot_invitaciones_revocacion_completa CHECK (
        (revocada_at IS NULL AND revocada_por IS NULL)
        OR (revocada_at IS NOT NULL AND revocada_por IS NOT NULL)
    );

COMMENT ON COLUMN public.bot_invitaciones.revocada_por IS
    'Quién anuló (s324j/DEC-239): panel:<usuario> o cli:<quien>. La columna '
    'que r41 supló firmando en la nota — aquello mezclaba auditoría con texto '
    'humano y estaba roto (la 016 no concedía UPDATE(nota) → 42501).';

-- Lo que NO se añade, con motivo (v9 §4.3): un CHECK que prohíba canjeada_at
-- y revocada_at simultáneos. Con los DOS escritores condicionales (panel y
-- CLI patchean con revocada_at=is.null&canjeada_at=is.null) ese estado ya no
-- es producible, y el CHECK exigiría reescribir la historia si alguna fila
-- legada lo tiene — los CHECK nuevos afirman lo que los escritores garantizan
-- de aquí en adelante, no falsifican lo que pasó.

-- ----------------------------------------------------------------------------
-- FASE C — GRANT por columnas, ADITIVOS a los de la 016
-- ----------------------------------------------------------------------------
GRANT INSERT (op) ON public.bot_invitaciones TO service_role;
GRANT UPDATE (revocada_por) ON public.bot_invitaciones TO service_role;

-- ----------------------------------------------------------------------------
-- FASE D — POSTCONDICIONES (falla ⇒ el aplicador transaccional revierte todo)
-- ----------------------------------------------------------------------------
DO $s324j_020_post$
BEGIN
    -- D.1 Ninguna fila sin op, ninguna duplicada (el default volátil por fila).
    IF EXISTS (SELECT 1 FROM public.bot_invitaciones WHERE op IS NULL)
       OR EXISTS (SELECT op FROM public.bot_invitaciones
                   GROUP BY op HAVING count(*) > 1) THEN
        RAISE EXCEPTION '020: el backfill de op dejo NULLs o duplicados';
    END IF;
    -- D.2 Coherencia de la revocación en TODAS las filas (el CHECK ya la
    -- impone; esto verifica que el backfill no dejó ninguna fuera antes del
    -- ADD CONSTRAINT — cinturón sobre tirantes, gratis).
    IF EXISTS (
        SELECT 1 FROM public.bot_invitaciones
         WHERE (revocada_at IS NULL) <> (revocada_por IS NULL)
    ) THEN
        RAISE EXCEPTION '020: filas con revocada_at/revocada_por incoherentes';
    END IF;
    -- D.3 anon/authenticated siguen sin privilegios sobre la tabla (los GRANT
    -- aditivos no pueden haberles abierto nada).
    IF EXISTS (
        SELECT 1 FROM information_schema.column_privileges c
         WHERE c.table_schema = 'public' AND c.table_name = 'bot_invitaciones'
           AND c.grantee IN ('anon', 'authenticated')
    ) THEN
        RAISE EXCEPTION '020: anon/authenticated tienen privilegios de columna '
                        'sobre bot_invitaciones';
    END IF;
END
$s324j_020_post$;

-- ----------------------------------------------------------------------------
-- FASE E — EXPONER EN LA API (la lección de la FASE D de la 016: PostgREST
-- cachea el esquema y las columnas nuevas devolverían error hasta el reload).
-- ----------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';
