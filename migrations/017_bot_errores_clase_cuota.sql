-- ============================================================================
-- 017 — `bot_errors.clase`: abrir el vocabulario y añadir `cuota_agotada` (s324f)
--
-- ⚠️ NO APLICADA. Se deja preparada para que Alberto la pegue en el SQL editor
--    de Supabase cuando quiera. El bot funciona SIN ella: hoy la cuota agotada
--    se registra como `llm_fallo`, que es correcto pero mete en el mismo cajón
--    «el proveedor no tiene saldo» y «el proveedor rechazó la petición».
--
-- POR QUÉ. En el piloto, la primera usuaria invitada mandó un audio, la cuenta
-- de OpenAI de producción no tenía saldo, y el bot le respondió que estaba
-- **saturado** y que probara más tarde. Dos afirmaciones falsas: no había
-- congestión, y reintentar no iba a funcionar nunca. El código ya distingue los
-- dos casos (`error_taxonomy._es_cuota_agotada`) y sirve el mensaje correcto;
-- lo que falta es poder GUARDARLO con nombre propio, para que el informe de
-- incidencias diga «esto se arregla pagando» en vez de mezclarlo con fallos que
-- se arreglan con código.
--
-- DECISIÓN DE ALBERTO (17-ago): «si se pueden añadir más de 6, mejor, incluso si
-- hay que hacer una migración para acomodar >6 categorías».
--
-- QUÉ HACE, exactamente:
--   1. sustituye el CHECK cerrado de 6 valores por uno de 7 (añade
--      `cuota_agotada`);
--   2. NO reescribe ninguna fila existente. Las incidencias ya registradas como
--      `llm_fallo` se quedan como están: re-etiquetar el pasado haría que el
--      histórico contase algo que en su momento no se sabía.
--
-- Idempotente. Tiempo estimado: <1 s. Reversible (rollback al pie).
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO (leer antes de aplicar)
-- ============================================================================

-- A.1: el CHECK actual, para saber de dónde se parte.
SELECT pg_get_constraintdef(con.oid) AS check_actual
  FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = rel.relnamespace
 WHERE n.nspname = 'public'
   AND rel.relname = 'bot_errors'
   AND con.conname = 'bot_errors_clase_check';

-- A.2: qué clases hay REALMENTE guardadas. Si aquí apareciera un valor que el
--      CHECK nuevo no admite, la migración fallaría — mejor verlo antes.
SELECT clase, count(*) AS filas
  FROM public.bot_errors
 GROUP BY clase
 ORDER BY filas DESC;


-- ============================================================================
-- FASE B — EL CAMBIO
-- ============================================================================

-- (dúo r40) Los dos ALTER van en UNA transacción. La primera versión hacía DROP
-- y luego ADD sueltos: si el ADD fallaba —un valor inesperado ya guardado, un
-- corte— la columna se quedaba SIN vocabulario cerrado y cualquier cosa entraba,
-- justo en la tabla que existe para clasificar. Con BEGIN/COMMIT, o se cambian
-- los dos o no cambia ninguno.
--
-- ⚠️ Esto NO es la validación con BEGIN/ROLLBACK que reventó la 016: allí se
-- revertía a propósito y se llevó por delante el fichero entero. Aquí se
-- CONFIRMA con COMMIT. Si tu cliente SQL ya abre transacción por su cuenta,
-- estas dos líneas son inocuas (avisa de «transaction already in progress» y
-- sigue).
BEGIN;

ALTER TABLE public.bot_errors
    DROP CONSTRAINT IF EXISTS bot_errors_clase_check;

ALTER TABLE public.bot_errors
    ADD CONSTRAINT bot_errors_clase_check CHECK (clase IN (
        'red_datos',
        'llm_saturado',
        'llm_fallo',
        -- (s324f) NUEVA. El proveedor de IA rechaza por SALDO, no por ritmo:
        -- mismo 429, consecuencia opuesta. No es reintentable y no se arregla
        -- sola — necesita que una persona recargue, y por eso el bot avisa al
        -- operador en vez de decirle al técnico que espere.
        'cuota_agotada',
        'transporte_telegram',
        'datos_ausentes',
        'bug'
    ));

COMMENT ON COLUMN public.bot_errors.clase IS
    'Clase de fallo por CAUSA (vocabulario cerrado, s324e/s324f): red_datos · '
    'llm_saturado (congestión: reintentar sirve) · llm_fallo · cuota_agotada '
    '(sin saldo: reintentar NO sirve) · transporte_telegram · datos_ausentes · bug.';

COMMIT;


-- ============================================================================
-- FASE C — VERIFICACIÓN (debe devolver el CHECK con los 7 valores)
-- ============================================================================

SELECT pg_get_constraintdef(con.oid) AS check_nuevo
  FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = rel.relnamespace
 WHERE n.nspname = 'public'
   AND rel.relname = 'bot_errors'
   AND con.conname = 'bot_errors_clase_check';

-- (s324e, lección cableada) PostgREST cachea el esquema: se le avisa desde aquí
-- en vez de confiar en que se refresque solo. Idempotente.
NOTIFY pgrst, 'reload schema';


-- ============================================================================
-- ROLLBACK (si hiciera falta volver a las 6 clases)
--
-- ⚠️ Antes de ejecutarlo hay que dejar el CÓDIGO en su estado anterior: si el
--    bot sigue clasificando como `cuota_agotada` y el CHECK ya no lo admite,
--    los INSERT fallarán y el diagnóstico se perderá justo cuando hace falta.
--    Y si ya hay filas con la clase nueva, hay que reasignarlas primero:
--      UPDATE public.bot_errors SET clase = 'llm_fallo' WHERE clase = 'cuota_agotada';
--
-- ALTER TABLE public.bot_errors DROP CONSTRAINT bot_errors_clase_check;
-- ALTER TABLE public.bot_errors ADD CONSTRAINT bot_errors_clase_check CHECK (
--     clase IN ('red_datos','llm_saturado','llm_fallo','transporte_telegram',
--               'datos_ausentes','bug'));
-- NOTIFY pgrst, 'reload schema';
-- ============================================================================
