-- ============================================================================
-- 016 — `bot_allowlist` + `bot_invitaciones`: el control de acceso al piloto
--       con Directores Generales (s324e).
--
-- ⚠️ NO APLICADA. Igual que la 015, este fichero se deja preparado para que
--    Alberto lo revise y lo pegue en el SQL editor de Supabase cuando decida.
--
-- ⚠️ Y ADEMÁS, EL ORDEN IMPORTA AQUÍ (a diferencia de la 015). El bot funciona
--    sin estas tablas SOLO mientras `BOT_ALLOWLIST` esté en `off`, que es el
--    default. Secuencia correcta:
--        1. desplegar el código (la puerta nace inerte: bot de hoy, exacto);
--        2. aplicar ESTA migración (FASE A → B → C);
--        3. comprobar el alta de bootstrap con
--           `python -m scripts.s324e_invitaciones allowlist`;
--        4. poner `BOT_ALLOWLIST_BOOTSTRAP=<tu telegram_user_id>` en Railway;
--        5. y solo entonces `BOT_ALLOWLIST=on`.
--    Si se enciende la variable sin la tabla, el bot responde `indeterminado` a
--    todo el mundo (fail-closed) menos a los ids de bootstrap. Se recupera
--    volviendo a poner `off`: sin deploy.
--
-- PROBLEMA QUE RESUELVE. Hoy no hay control de acceso: cualquiera que llegue al
-- bot y envíe `/accept` entra. Con un usuario real eso es una anécdota; con un
-- piloto de DGs son tres problemas a la vez — gasto (cada consulta paga
-- generación, embedding y rerank), confidencialidad (el corpus son manuales de
-- fabricantes servidos con cita) y RGPD (sin puerta, el bot registra la
-- consulta de cualquiera).
--
-- POR QUÉ DOS TABLAS Y NO UNA COLUMNA EN `user_consent`:
--   * son dos preguntas distintas y con plazos distintos. `user_consent`
--     responde «¿aceptó los términos, y cuándo?» y es EVIDENCIA (append-only
--     desde s296: una fila por persona Y versión). La allowlist responde
--     «¿puede entrar HOY?» y es ESTADO vigente, que cambia. Meterlas juntas
--     obligaría a que un alta o una revocación tocaran la prueba del
--     consentimiento, que es justo lo que s296 dejó de hacer;
--   * el orden en el bot es puerta → consentimiento (minimización: quien no
--     está invitado no llega a `/accept` y no deja rastro), así que la puerta
--     tiene que poder decidir SIN mirar el consentimiento;
--   * una invitación existe ANTES de que exista la persona: no tiene
--     `telegram_user_id` hasta que alguien la canjea. No cabe en una tabla
--     indexada por persona.
--
-- RGPD — QUÉ DATO PERSONAL HAY EN CADA COLUMNA (matriz completa en
-- `docs/RGPD_RETENCION.md`, donde estas dos tablas ya están dadas de alta):
--
--   bot_allowlist
--     · telegram_user_id  → IDENTIFICADOR DIRECTO. Es dato personal; ésta es la
--                           razón de ser de la tabla y no se puede seudonimizar
--                           (una lista de acceso con seudónimos no deja entrar
--                           a nadie).
--     · nota              → DATO PERSONAL en texto libre: nombre y cargo («Juan
--                           Pérez, DG de …»). Está para saber quién es quién al
--                           revocar; es el mismo tipo de dato que
--                           `user_consent.display_name`.
--     · alta_por          → etiqueta del OPERADOR que dio el alta (p. ej.
--                           `'alberto'`). Dato personal de un empleado, no de un
--                           interesado externo; es la traza de responsabilidad
--                           que el encargo pide («quién dio de alta a quién»).
--     · origen · alta_at · revocado_at · revocado_por · invitacion_id
--                         → metadatos de la decisión, no describen a la persona
--                           más allá de vincularla a una fecha y un operador.
--
--   bot_invitaciones
--     · nota              → DATO PERSONAL: para quién se emitió (se escribe
--                           ANTES de que la persona use nada, así que existe
--                           aunque nunca la canjee).
--     · canjeada_por      → IDENTIFICADOR DIRECTO de quien la usó. Es la pieza
--                           que permite ver si el enlace lo abrió la persona
--                           prevista o un tercero al que se lo reenviaron.
--     · token_hash        → NO es dato personal, y NO es el token: es su
--                           SHA-256. Quien lea esta tabla (una copia, la
--                           consola, una clave filtrada) NO obtiene
--                           invitaciones utilizables. El token en claro no se
--                           guarda en ninguna parte: se enseña una vez al
--                           crearlo y vive solo en el enlace que Alberto envía.
--     · creada_por · creada_at · expira_at · revocada_at → metadatos.
--
-- CÓMO ENCAJA EN LA RETENCIÓN. Estas dos tablas son ESTADO OPERATIVO, igual que
-- `user_consent`: no se pueden disociar (una lista de acceso sin identificador
-- no autoriza a nadie) y por eso el job mensual `rgpd_retencion_pasada` NO las
-- toca ni necesita una política nueva. Consecuencias, todas deliberadas:
--   · el PLAZO entra en el mismo `[DECIDIR]` con el asesor que ya tienen
--     `user_consent` y `consent_events` — no se inventa uno aquí;
--   · la SUPRESIÓN A PETICIÓN sí las alcanza y hay que añadirlas al runbook:
--        DELETE FROM bot_allowlist WHERE telegram_user_id = X;
--        UPDATE bot_invitaciones SET canjeada_por = NULL
--         WHERE canjeada_por = X;      -- se conserva la traza del canje, sin
--                                      -- el identificador de quien lo hizo
--     (y revisar la `nota`, que puede llevar su nombre escrito dentro);
--   · NO hay FK a `query_logs`, así que nada cascadea hacia aquí: una supresión
--     que solo borre `query_logs` dejaría a la persona en la allowlist. Está
--     escrito arriba y en la matriz porque es justo el paso que se olvida.
-- A juicio del asistente esto no es finalidad nueva (control de acceso a una
-- herramienta de trabajo, base de interés legítimo ya decidida por Alberto el
-- 5-ago), pero **quien decide si toca el aviso o `TERMS_VERSION` es el asesor**,
-- como en la 015.
--
-- Idempotente (IF NOT EXISTS). Tiempo estimado: <1 s. Rollback al pie.
-- ============================================================================


-- ============================================================================
-- FASE A — DIAGNÓSTICO
-- ============================================================================

-- A.1: ¿existen ya?
SELECT
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = 'bot_allowlist')
    AS allowlist_exists,
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = 'bot_invitaciones')
    AS invitaciones_exists;

-- A.2: precondición del bootstrap — quién usa hoy el bot. Estas son las
-- personas que la FASE B dará de alta para que el encendido de la puerta no
-- eche a nadie que ya estaba dentro.
SELECT telegram_user_id, display_name, accepted_at
FROM user_consent
WHERE revoked_at IS NULL
ORDER BY accepted_at;


-- ============================================================================
-- FASE B — APLICAR
-- ============================================================================

-- B.1 — Las invitaciones. Se crea PRIMERO: la allowlist la referencia.
CREATE TABLE IF NOT EXISTS bot_invitaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- SHA-256 del token en hex (64 chars). UNIQUE porque es la clave de
    -- búsqueda del canje: el índice que crea es lo que hace que el UPDATE
    -- condicional resuelva por índice y no por seq scan.
    -- NO se guarda el token: ver la cabecera.
    token_hash TEXT NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),

    -- Para quién es. DATO PERSONAL (nombre/cargo). Es lo que convierte el
    -- listado en algo accionable: sin nota, «hay 4 invitaciones pendientes» no
    -- se puede auditar ni revocar con criterio.
    nota TEXT,

    creada_por TEXT NOT NULL,               -- etiqueta del operador
    creada_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Caducidad OBLIGATORIA (NOT NULL, sin default): una invitación sin fecha
    -- de muerte es una llave permanente circulando por WhatsApp. El valor lo
    -- pone quien la emite (`--dias`, 2 por defecto desde que Alberto pidió
    -- acortar la ventana en la que un enlace olvidado sigue vivo).
    expira_at TIMESTAMPTZ NOT NULL,

    -- El canje. Las dos columnas se escriben JUNTAS en el UPDATE condicional
    -- que hace el bot; `canjeada_por` es IDENTIFICADOR DIRECTO de quien abrió
    -- el enlace — que puede NO ser la persona de `nota` si se lo reenviaron, y
    -- ése es exactamente el dato que permite verlo.
    canjeada_at TIMESTAMPTZ,
    canjeada_por BIGINT,

    revocada_at TIMESTAMPTZ,                -- anulación por el operador

    -- Un canje es atómico: o están las dos marcas o no está ninguna. Sin esto,
    -- una fila con `canjeada_at` y sin `canjeada_por` (o al revés) sería un
    -- canje que no se puede atribuir a nadie.
    CONSTRAINT bot_invitaciones_canje_completo CHECK (
        (canjeada_at IS NULL AND canjeada_por IS NULL)
        OR (canjeada_at IS NOT NULL AND canjeada_por IS NOT NULL)
    ),

    -- LA COTA DE VIDA, en la base y no solo en el script (dúo, menor 7). Se
    -- afirmaba «se acota a 7 días» y era falso: `--dias` aceptaba cualquier
    -- entero y aquí solo se exigía NOT NULL, así que un `--dias 3650` pasaba y
    -- creaba justo lo que este diseño dice evitar — una llave de vida larga
    -- circulando por un chat. Con el CHECK la frase es verdad para CUALQUIER
    -- cliente de la tabla, no solo para el que se porta bien.
    CONSTRAINT bot_invitaciones_caducidad_acotada CHECK (
        expira_at > creada_at
        AND expira_at <= creada_at + interval '7 days'
    )
);

COMMENT ON TABLE bot_invitaciones IS
    'Invitaciones de UN SOLO USO al piloto (s324e). Guarda el SHA-256 del '
    'token, nunca el token. `nota` y `canjeada_por` son dato personal; el '
    'plazo comparte el [DECIDIR] de user_consent (docs/RGPD_RETENCION.md).';

-- B.2 — La allowlist: quién puede usar el bot HOY.
CREATE TABLE IF NOT EXISTS bot_allowlist (
    -- Una fila por persona: la pregunta de la puerta es «¿este id, sí o no?».
    telegram_user_id BIGINT PRIMARY KEY,

    nota TEXT,                              -- nombre/cargo — DATO PERSONAL

    -- ---- La traza de responsabilidad (el «quién dio de alta a quién») -------
    origen TEXT NOT NULL CHECK (origen IN ('bootstrap', 'invitacion', 'manual')),
    alta_por TEXT NOT NULL,                 -- operador; en un canje, el autor
                                            -- de la invitación (la decisión fue
                                            -- suya, no de quien pulsó)
    alta_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    invitacion_id UUID REFERENCES bot_invitaciones(id) ON DELETE SET NULL,

    -- ---- La baja: LÓGICA, no un DELETE -------------------------------------
    -- Un DELETE borraría la única prueba de que esa persona tuvo acceso, quién
    -- se lo dio y cuándo se le quitó. Mismo criterio que `user_consent.
    -- revoked_at`. El DELETE queda reservado a la supresión a petición, que es
    -- otra cosa: allí el objetivo ES que no quede rastro.
    revocado_at TIMESTAMPTZ,
    revocado_por TEXT,
    motivo_revocacion TEXT,

    CONSTRAINT bot_allowlist_revocacion_completa CHECK (
        (revocado_at IS NULL AND revocado_por IS NULL)
        OR (revocado_at IS NOT NULL AND revocado_por IS NOT NULL)
    )
);

COMMENT ON TABLE bot_allowlist IS
    'Quien puede usar el bot (s324e). `telegram_user_id` y `nota` son dato '
    'personal; la baja es LOGICA (revocado_at) para conservar la traza. NO '
    'cascadea desde query_logs: la supresion a peticion debe borrarla aparte '
    '(docs/RGPD_RETENCION.md).';

-- ÍNDICES — solo los que una consulta REAL usa (lección de la 015: allí nacieron
-- cinco y tres eran aparato anticipatorio).
--   1. La puerta consulta en CADA update:
--      `?telegram_user_id=eq.X&revocado_at=is.null` → el PK resuelve el filtro
--      por persona y el parcial evita leer la fila para descartarla por
--      revocada. A la escala del piloto da igual; a 30 técnicos, no.
CREATE INDEX IF NOT EXISTS idx_bot_allowlist_activos
    ON bot_allowlist (telegram_user_id) WHERE revocado_at IS NULL;
--   2. El canje filtra por `token_hash` — ya lo cubre el UNIQUE de B.1.
--   3. NO se indexa `bot_allowlist.invitacion_id`: el índice del lado hijo de
--      una FK sirve para abaratar el borrado del padre, y aquí el padre no se
--      borra nunca (las invitaciones se anulan, no se eliminan).

-- B.3 — BOOTSTRAP, explícito y auditable. Quien ya tiene consentimiento activo
-- entra en la allowlist con `origen='bootstrap'`: nadie que estuviera usando el
-- bot se queda fuera al encender la puerta. No es un `if user_id == …` en el
-- código ni una fila escrita a mano sin explicación — es una regla que se lee.
-- `ON CONFLICT DO NOTHING` la hace repetible y no pisa un alta posterior.
INSERT INTO bot_allowlist (telegram_user_id, nota, origen, alta_por)
SELECT
    uc.telegram_user_id,
    COALESCE(uc.display_name, '(sin nombre)')
        || ' — alta automatica: usaba el bot antes de la puerta',
    'bootstrap',
    'migracion_016'
FROM user_consent uc
WHERE uc.revoked_at IS NULL
ON CONFLICT (telegram_user_id) DO NOTHING;

-- ---- Frontera de seguridad, IGUAL que el resto de tablas del bot -----------
-- Mismo patrón que `supabase_schema.sql` y la 015: RLS forzada, privilegios
-- revocados nominalmente y concesión MÍNIMA.
--
-- LÍMITE DECLARADO, para que nadie lea de más estos GRANT: el bot y el script
-- de operación usan LA MISMA credencial (`SUPABASE_SERVICE_KEY`), así que los
-- privilegios NO separan «lo que hace el bot» de «lo que hace el operador» —
-- eso lo separa el código. Lo que sí impiden es lo que NINGUNO de los dos debe
-- poder hacer (borrar filas), y dejan la frontera lista para el día en que el
-- script tenga credencial propia.
ALTER TABLE public.bot_allowlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_allowlist FORCE ROW LEVEL SECURITY;
ALTER TABLE public.bot_invitaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_invitaciones FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.bot_allowlist
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL PRIVILEGES ON TABLE public.bot_invitaciones
    FROM PUBLIC, anon, authenticated, service_role;

-- La puerta LEE la allowlist en cada update; el canje INSERTA; el script da
-- altas y revoca (UPDATE). Sin DELETE: la baja es lógica, y la supresión a
-- petición la ejecuta el operador con sus propias credenciales, a la vista.
GRANT SELECT ON TABLE public.bot_allowlist TO service_role;
GRANT INSERT (telegram_user_id, nota, origen, alta_por, alta_at, invitacion_id,
              revocado_at, revocado_por, motivo_revocacion)
    ON public.bot_allowlist TO service_role;
-- UPDATE por COLUMNAS. `revocado_at` está dentro a propósito y con dos efectos:
-- permite al script revocar, y permite que un canje RE-ADMITA a alguien
-- revocado. Eso último es deliberado: para volver hace falta una invitación
-- NUEVA, que solo puede emitir el operador y queda con su firma; el revocado no
-- puede volver solo, porque sus invitaciones anteriores ya están canjeadas.
--
-- ⚠️ `telegram_user_id` VA EN LA LISTA, y no porque queramos poder reescribir la
-- identidad de una fila. Es un requisito MECÁNICO de PostgREST: un upsert
-- (`Prefer: resolution=merge-duplicates`) genera
-- `ON CONFLICT (telegram_user_id) DO UPDATE SET … telegram_user_id =
-- EXCLUDED.telegram_user_id …` incluyendo la propia columna de conflicto, así
-- que sin este privilegio el canje de una persona que YA tuviera fila (una
-- re-admisión) fallaría por permisos. La asignación es un no-op —la columna se
-- re-escribe con su propio valor, que es justo el que hizo saltar el conflicto—
-- pero el privilegio hay que concederlo igual.
-- VERIFICAR AL APLICAR (no se ha podido probar contra un PostgREST vivo): si al
-- ejercer una re-admisión no hiciera falta, RETIRAR esta columna de la lista —
-- la frontera más estrecha es la buena.
GRANT UPDATE (telegram_user_id, nota, origen, alta_por, alta_at, invitacion_id,
              revocado_at, revocado_por, motivo_revocacion)
    ON public.bot_allowlist TO service_role;

GRANT SELECT ON TABLE public.bot_invitaciones TO service_role;
GRANT INSERT (token_hash, nota, creada_por, expira_at)
    ON public.bot_invitaciones TO service_role;
-- El canje escribe `canjeada_at`/`canjeada_por`; el operador anula con
-- `revocada_at`. `token_hash` NO es actualizable: reescribir el hash de una
-- invitación ya emitida sería cambiar la llave por debajo.
GRANT UPDATE (canjeada_at, canjeada_por, revocada_at)
    ON public.bot_invitaciones TO service_role;


-- ============================================================================
-- FASE C — VALIDACIÓN (postcondiciones; si alguna falla, ROLLBACK)
-- ============================================================================

-- C.1: las tablas existen con sus columnas.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('bot_allowlist', 'bot_invitaciones')
ORDER BY table_name, ordinal_position;

-- C.2: INVARIANTE — el bootstrap NO dejó fuera a nadie. Debe devolver 0 filas.
-- Si devuelve alguna, encender `BOT_ALLOWLIST` echaría a esa persona.
SELECT uc.telegram_user_id, uc.display_name
FROM user_consent uc
LEFT JOIN bot_allowlist a ON a.telegram_user_id = uc.telegram_user_id
WHERE uc.revoked_at IS NULL AND a.telegram_user_id IS NULL;

-- C.3: INVARIANTE — RLS habilitada Y forzada en las dos.
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE oid IN ('public.bot_allowlist'::regclass,
              'public.bot_invitaciones'::regclass);

-- C.4: INVARIANTE — el token en claro NO tiene dónde vivir. Debe devolver 0:
-- ninguna columna que se llame `token`, `secreto` o similar.
SELECT count(*) AS columnas_de_secreto_prohibidas
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'bot_invitaciones'
  AND column_name IN ('token', 'token_claro', 'secreto', 'secret', 'enlace');

-- C.5: INVARIANTE — nadie puede BORRAR. Debe salir SELECT/INSERT/UPDATE y
-- jamás DELETE ni TRUNCATE.
SELECT table_name, privilege_type, count(*) AS columnas
FROM information_schema.column_privileges
WHERE table_name IN ('bot_allowlist', 'bot_invitaciones')
  AND grantee = 'service_role'
GROUP BY table_name, privilege_type
ORDER BY table_name, privilege_type;

-- C.6: la prueba de vida del UN SOLO USO vive en un fichero APARTE:
--      `migrations/016_validacion_un_solo_uso.sql`
-- Por qué (s324e, dos incidentes reales al aplicar esta migración): esa prueba necesita
-- deshacer lo que escribe, y CÓMO se deshace depende de si el cliente SQL abre o no una
-- transacción por su cuenta — con `BEGIN/ROLLBACK` se revirtió el fichero entero en un
-- cliente, y con `SAVEPOINT` falló con «can only be used in transaction blocks» en otro.
-- Un fichero que CREA tablas no puede depender de eso: aquí no hay control de transacción
-- de ningún tipo, y la prueba se ejecuta por separado cuando ya están creadas.

-- ALCANCE HONESTO DE C.6: esto demuestra que la CONDICIÓN del canje funciona,
-- que es lo que depende de nosotros. La garantía frente a dos personas pulsando
-- el enlace EN EL MISMO INSTANTE no la da esta prueba (haría falta abrir dos
-- sesiones), sino el motor: bajo READ COMMITTED la segunda escritura espera al
-- COMMIT de la primera y entonces RE-EVALÚA su WHERE sobre la versión nueva
-- (EvalPlanQual), donde `canjeada_at` ya no es NULL. Por eso el canje tiene que
-- seguir siendo UN update condicional y no un SELECT seguido de un UPDATE.


-- ============================================================================
-- ROLLBACK (completo — no toca ninguna tabla existente)
-- ============================================================================
-- Poner ANTES `BOT_ALLOWLIST=off` en Railway: con la variable encendida y las
-- tablas ausentes, solo entran los ids de `BOT_ALLOWLIST_BOOTSTRAP`.
--
-- DROP TABLE IF EXISTS public.bot_allowlist;      -- primero: referencia a la otra
-- DROP TABLE IF EXISTS public.bot_invitaciones;
--
-- Tras el DROP el bot vuelve a la conducta de hoy (con la puerta apagada):
-- cualquiera que acepte los términos puede usarlo.
-- ============================================================================

-- ============================================================================
-- FASE D — EXPONER EN LA API (s324e, segundo incidente real: las tablas existían y
-- PostgREST seguía devolviendo 404). PostgREST cachea el esquema; una migración que crea
-- tablas para que las use la API REST debe dejarlas visibles ella misma en vez de confiar
-- en que el caché se refresque solo. Idempotente.
-- ============================================================================
NOTIFY pgrst, 'reload schema';
