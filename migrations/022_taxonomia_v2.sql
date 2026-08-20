-- ============================================================================
-- 022 — La taxonomía de preguntas pasa a v2 (s326b).
--       ✅ APLICADA EN PRODUCCIÓN el 19-ago-2026 (conector Supabase, entera y
--          transaccional, postcondiciones verdes). Si necesitas cambiar la
--          taxonomía otra vez, escribe una migración NUEVA: editar ésta deja
--          CI verde y producción con el CHECK viejo (hallazgo Sol s326b).
--       Adjudicación de Alberto (19-ago-2026, sobre la muestra del gate de
--       acuerdo de la v1): fusionar catálogo+especificaciones y
--       instalación+configuración, acotar compatibilidad a «¿funciona X con
--       Y?» (típicamente entre marcas), y separar los mensajes que NO son
--       preguntas. Lista canónica: `config/taxonomia_preguntas.yaml` (la
--       versión vive DENTRO del fichero, no en su nombre).
--
-- POR QUÉ EXISTE ESTA MIGRACIÓN Y NO ES UN CAMBIO DE YAML A SECAS: los ids de
-- la taxonomía viven TAMBIÉN como CHECK en la base (contrato de la 021) —
-- cambiar las categorías es un evento adjudicado, no un hot-swap. Migración
-- hermana = la mitad SQL de ese contrato.
--
-- QUÉ HACE, en este orden y en UNA transacción:
--   0. RETIRA el CHECK viejo ANTES de tocar los datos. El orden es el que
--      exige este diseño (mapa in-place) — no el único diseño posible: vaciar
--      la tabla derivada y dejar que el job la reconstruya evita el estado
--      intermedio del punto 1 y es el patrón PREFERIDO para la próxima
--      (hallazgo Sol s326b; aquí se mapeó para no dejar el panel sin datos ni
--      un minuto, y el backfill corrió acto seguido). El orden NO es
--      cosmético: el primer intento de aplicar esta migración (19-ago, 21:5x)
--      puso el UPDATE delante y murió con 23514 —el CHECK de la v1 rechazaba
--      el id de la v2 que el propio mapa escribía—, revirtiendo entera (la
--      transacción hizo su trabajo: cero filas tocadas). Mapear a ids que el
--      constraint vigente no admite es imposible por construcción; primero se
--      quita el constraint, luego se mapea, luego se pone el nuevo.
--   1. MAPEA los ids retirados a los nuevos en las filas que ya existen. Esto
--      NO es la re-clasificación: es lo mínimo para que el CHECK nuevo pueda
--      aplicarse sin dejar la tabla vacía ni un minuto. Las filas conservan
--      `taxonomia_version = 1`, así que el job las considera PENDIENTES y las
--      re-clasifica TODAS con el prompt nuevo — que es lo único que aplica los
--      puntos 3-7 de Alberto (un código suelto → `otros`, «diferencias entre
--      X e Y» → catálogo, «¿tienes productos de Z?» → catálogo, feedback →
--      `no_es_pregunta`). El mapa mecánico no puede saber eso.
--   2. SUSTITUYE el CHECK de `categoria` por el de la v2.
--
-- CONSECUENCIA VISIBLE Y DELIBERADA hasta que corra el backfill:
-- `bot_clasificacion_cobertura` mostrará `taxonomia_min = 1` frente a la
-- vigente 2 — el desfase se VE, que es justo para lo que se diseñó esa vista.
--
-- ⚠️ CONTRATO DE APLICACIÓN (016/019/021): ENTERA con un aplicador
--    transaccional (SQL Editor de Supabase o `psql --single-transaction`),
--    NUNCA sentencia a sentencia. SIN BEGIN/COMMIT propios A PROPÓSITO.
--
-- REVERSIBILIDAD: la tabla es DERIVADA y reconstruible entera desde
-- `query_logs` — volver a la v1 es restaurar el CHECK de la 021 y re-correr el
-- job con el YAML v1. No hay dato original en juego. Rollback al pie.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FASE 0 — PREFLIGHT
-- ----------------------------------------------------------------------------
DO $s326b_preflight$
BEGIN
    IF to_regclass('public.query_clasificacion') IS NULL THEN
        RAISE EXCEPTION '022: aplica ANTES migrations/021_query_clasificacion.sql';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'public.query_clasificacion'::regclass
           AND conname = 'query_clasificacion_categoria_check') THEN
        RAISE EXCEPTION '022: no encuentro el CHECK de categoria de la 021 '
                        '(¿se renombró? revisa pg_constraint antes de seguir)';
    END IF;
END
$s326b_preflight$;

-- ----------------------------------------------------------------------------
-- FASE A — FUERA EL CHECK VIEJO (antes de tocar los datos: ver cabecera, punto 0)
-- ----------------------------------------------------------------------------
ALTER TABLE public.query_clasificacion
    DROP CONSTRAINT query_clasificacion_categoria_check;

-- ----------------------------------------------------------------------------
-- FASE B — EL MAPA (solo para que el CHECK nuevo pueda aplicarse; la verdad la
--          pone el job al re-clasificar, ver cabecera)
-- ----------------------------------------------------------------------------
UPDATE public.query_clasificacion
   SET categoria = CASE categoria
           WHEN 'especificaciones'           THEN 'catalogo_especificaciones'
           WHEN 'catalogo_documentacion'     THEN 'catalogo_especificaciones'
           WHEN 'instalacion_cableado'       THEN 'instalacion_configuracion'
           WHEN 'configuracion_programacion' THEN 'instalacion_configuracion'
           ELSE categoria
       END
 WHERE categoria IN ('especificaciones', 'catalogo_documentacion',
                     'instalacion_cableado', 'configuracion_programacion');

-- ----------------------------------------------------------------------------
-- FASE C — EL CHECK DE LA v2
-- ----------------------------------------------------------------------------
ALTER TABLE public.query_clasificacion
    ADD CONSTRAINT query_clasificacion_categoria_check CHECK (categoria IN (
        'catalogo_especificaciones',
        'instalacion_configuracion',
        'averias_diagnostico',
        'mantenimiento_pruebas',
        'compatibilidad_sustitucion',
        'normativa',
        'no_es_pregunta',
        'otros'));

-- ----------------------------------------------------------------------------
-- FASE D — POSTCONDICIONES (la migración se auto-comprueba o aborta entera)
-- ----------------------------------------------------------------------------
DO $s326b_postcondiciones$
DECLARE
    definicion TEXT;
    id_v2 TEXT;
    id_retirado TEXT;
    residuales BIGINT;
BEGIN
    SELECT pg_get_constraintdef(oid) INTO definicion
      FROM pg_constraint
     WHERE conrelid = 'public.query_clasificacion'::regclass
       AND conname = 'query_clasificacion_categoria_check';

    -- Los OCHO ids de la v2, presentes...
    FOREACH id_v2 IN ARRAY ARRAY[
        'catalogo_especificaciones', 'instalacion_configuracion',
        'averias_diagnostico', 'mantenimiento_pruebas',
        'compatibilidad_sustitucion', 'normativa', 'no_es_pregunta', 'otros'
    ] LOOP
        IF position('''' || id_v2 || '''' IN definicion) = 0 THEN
            RAISE EXCEPTION '022: el CHECK no admite %', id_v2;
        END IF;
    END LOOP;

    -- ...y los CUATRO retirados, ausentes del CHECK Y de los datos. Comprobar
    -- las dos cosas: un CHECK correcto con filas viejas dentro sería un estado
    -- imposible que solo se detecta mirando ambos lados.
    FOREACH id_retirado IN ARRAY ARRAY[
        'especificaciones', 'catalogo_documentacion',
        'instalacion_cableado', 'configuracion_programacion'
    ] LOOP
        IF position('''' || id_retirado || '''' IN definicion) > 0 THEN
            RAISE EXCEPTION '022: el CHECK todavía admite el id retirado %',
                id_retirado;
        END IF;
        SELECT count(*) INTO residuales
          FROM public.query_clasificacion WHERE categoria = id_retirado;
        IF residuales > 0 THEN
            RAISE EXCEPTION '022: quedan % filas con el id retirado %',
                residuales, id_retirado;
        END IF;
    END LOOP;
END
$s326b_postcondiciones$;

-- ----------------------------------------------------------------------------
-- ROLLBACK (a la v1). La tabla es DERIVADA: se VACÍA y se deja que el job la
-- reconstruya. Remapear las categorías a mano NO vale —lo cazó Sol—: dejaría
-- `taxonomia_version` en el número alto, `es_pendiente` no re-encolaría nada y
-- el dato quedaría etiquetado con una versión que no corresponde a sus
-- categorías. Vaciar es lo único que restaura un estado consistente:
--   DELETE FROM public.query_clasificacion;
--   ALTER TABLE public.query_clasificacion
--       DROP CONSTRAINT query_clasificacion_categoria_check;
--   ALTER TABLE public.query_clasificacion
--       ADD CONSTRAINT query_clasificacion_categoria_check CHECK (categoria IN (
--           'especificaciones','instalacion_cableado','configuracion_programacion',
--           'averias_diagnostico','mantenimiento_pruebas','compatibilidad_sustitucion',
--           'normativa','catalogo_documentacion','otros'));
--   -- y re-correr el job con RUTA_TAXONOMIA apuntando al YAML v1.
-- ----------------------------------------------------------------------------
