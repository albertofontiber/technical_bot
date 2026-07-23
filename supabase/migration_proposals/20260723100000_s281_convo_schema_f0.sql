-- ============================================================================
-- PROPUESTA NO APLICADA — BLOQUEADA POR MATRIZ RGPD. NO EJECUTAR.
-- ============================================================================
-- s281 / lane MT-0b — Esquema PRIVADO `convo` (Fase 0 del build multi-turn).
-- Diseño canónico: evals/s280_multiturn_design_v2.md §1-2; assessment
-- evals/s276_multiturn_multihop_architecture_assessment_v1.md §3.1-3.2.
--
-- Este archivo es una PROPUESTA (patrón supabase/migration_proposals/):
-- deliberadamente excluida de `supabase db push`.  NO se aplica hasta que la
-- matriz de lifecycle RGPD esté FIRMADA por Alberto con validación legal
-- (docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md — fix RGPD-SIN-ESCAPATORIA del dúo
-- r1).  Hasta entonces el código de Fase 0 se verifica EXCLUSIVAMENTE con
-- tests SINTÉTICOS (fixtures/stubs); cero conversaciones reales — eso ya sería
-- tratamiento de datos personales.
--
-- MECANISMO FÍSICO DE ACCESO (fix ACCESO-FISICO-CONVO, load-bearing):
--   * Las TABLAS de `convo` NO reciben NINGÚN grant a anon/authenticated/
--     service_role → PostgREST no puede SELECT/INSERT/UPDATE/DELETE sobre
--     ellas aunque el schema se exponga.
--   * El acceso runtime es EXCLUSIVAMENTE vía RPCs SECURITY DEFINER (archivo
--     hermano 20260723100001_s281_convo_rpcs_f0.sql), expuestas SOLO al rol
--     `convo_rpc` que este archivo crea SIN privilegios de tabla directos.
--   * `convo_rpc` = NOLOGIN/NOINHERIT; PostgREST lo impersona vía `authenticator`
--     con SET ROLE (mismo patrón que public.p1_readonly,
--     supabase/migrations/20260721120000_add_p1_readonly_role.sql).  El bot lo
--     alcanza por la MISMA pila httpx→PostgREST actual (cero dependencias
--     runtime nuevas; alternativa driver-PG-directo DESCARTADA en el diseño).
--
-- CONFIG DE OPERACIÓN REQUERIDA (no es DDL — se hace en el dashboard Supabase
-- / variable PGRST_DB_SCHEMAS, y se declara aquí para honestidad del plan):
--   * añadir `convo` a los schemas expuestos de PostgREST (Accept-Profile:
--     convo) para que `/rpc/<fn>` resuelva las funciones.  Exponer el schema es
--     SEGURO porque las tablas no tienen grants: solo las funciones con EXECUTE
--     a convo_rpc son alcanzables.
--   * las funciones SECURITY DEFINER deben ser PROPIEDAD del rol que posee las
--     tablas `convo` (el runner de la migración, p.ej. postgres/supabase_admin)
--     para que el definer bypasse la ausencia de grants de tabla del caller.
--
-- YAGNI-TABLAS (dúo r1): Fase 0 crea SOLO el núcleo effectively-once.
--   DIFERIDAS a propuesta posterior: retrieval_hops (F2); turn_evidence /
--   answer_claims / claim_support (F3, shape dependiente del contrato S260 no
--   medido).  NO se crean aquí.
--
-- Convención de formato: SIN BEGIN/COMMIT envolvente (el runner de Supabase ya
-- envuelve; regla codificada en tests/test_s277_hp011_lifecycle_migration.py::
-- test_future_cli_migrations_delegate_data_history_atomicity_to_cli).
-- Estado de release: NO_GO_FOR_DB hasta matriz RGPD firmada.
-- Rollback: DROP SCHEMA convo CASCADE; DROP ROLE convo_rpc (previa revocación de
-- las membresías de authenticator/postgres).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0) Schema privado + rol dedicado (sin privilegios de tabla directos)
-- ----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS convo;

COMMENT ON SCHEMA convo IS
    'S281 private multi-turn conversation store. Tables carry NO PostgREST '
    'grants; runtime access is exclusively via SECURITY DEFINER RPCs granted '
    'to role convo_rpc. Blocked for DB apply until the signed RGPD lifecycle '
    'matrix (docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md).';

-- Rol runtime dedicado: NOLOGIN (se impersona vía authenticator), NOINHERIT
-- (no hereda privilegios de otros roles), sin ninguna capacidad elevada.
DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'convo_rpc') THEN
        CREATE ROLE convo_rpc
            NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS;
    ELSE
        IF EXISTS (
            SELECT 1 FROM pg_roles
            WHERE rolname = 'convo_rpc'
              AND (
                  rolsuper OR rolinherit OR rolcreaterole OR rolcreatedb
                  OR rolcanlogin OR rolreplication OR rolbypassrls
              )
        ) THEN
            RAISE EXCEPTION 'existing convo_rpc role has unsafe attributes';
        END IF;
    END IF;
END
$role$;

COMMENT ON ROLE convo_rpc IS
    'S281 NOLOGIN/NOINHERIT PostgREST-impersonated role. Holds NO table '
    'privileges in schema convo; only EXECUTE on the convo.* SECURITY DEFINER '
    'RPCs (granted in the RPC proposal). Impersonated via authenticator SET ROLE.';

-- PostgREST impersona convo_rpc vía authenticator (mismo patrón que p1_readonly).
-- SET TRUE habilita SET ROLE; INHERIT FALSE evita herencia pasiva de privilegios.
-- Guardado por existencia de los roles de plataforma (proposal-safe).
DO $membership$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        EXECUTE 'GRANT convo_rpc TO authenticator WITH SET TRUE, INHERIT FALSE';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        EXECUTE 'GRANT convo_rpc TO postgres WITH SET TRUE, INHERIT FALSE';
    END IF;
END
$membership$;

-- Higiene de exposición: el schema NO es usable por los roles PostgREST por
-- defecto; solo convo_rpc obtiene USAGE (necesario para resolver las funciones).
-- Las tablas seguirán sin grants → no seleccionables aunque el schema se exponga.
REVOKE ALL ON SCHEMA convo FROM PUBLIC;
REVOKE ALL ON SCHEMA convo FROM anon, authenticated, service_role;
GRANT USAGE ON SCHEMA convo TO convo_rpc;

-- Default privileges: cualquier tabla/secuencia/función futura en convo nace sin
-- grants para los roles PostgREST (defensa en profundidad contra exposición
-- accidental — assessment §3.2 "no deben quedar expuestas por accidente").
ALTER DEFAULT PRIVILEGES IN SCHEMA convo
    REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA convo
    REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA convo
    REVOKE ALL ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;

-- ----------------------------------------------------------------------------
-- 1) conversations — una fila por (canal, chat externo)
--    ID interno bigint (joins/orden) + public_id UUID (handle externo).
-- ----------------------------------------------------------------------------
CREATE TABLE convo.conversations (
    id                   BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id            UUID         NOT NULL DEFAULT pg_catalog.gen_random_uuid(),
    channel              TEXT         NOT NULL,
    external_chat_id     TEXT         NOT NULL,
    -- tenant/owner interno (M&A multi-fabricante); NULL = single-tenant hoy.
    tenant_id            TEXT         NULL,
    status               TEXT         NOT NULL DEFAULT 'active',
    -- CAS de orden por conversación (assessment §3.2): monotónico, lo avanza
    -- convo.ingress en cada evento nuevo. Es el handle de versión para las
    -- actualizaciones de working-state (snapshots).
    state_version        BIGINT       NOT NULL DEFAULT 0,
    -- Puntero denormalizado al último evento aplicado (NO FK: evita el ciclo
    -- conversations<->conversation_events; lo mantienen las RPCs).
    last_event_id        BIGINT       NULL,
    -- Lifecycle RGPD (celdas [DECIDIR] en la matriz): clase y caducidad.
    retention_class      TEXT         NULL,
    retention_expires_at TIMESTAMPTZ  NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT pg_catalog.now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT pg_catalog.now(),
    CONSTRAINT conversations_public_id_key UNIQUE (public_id),
    -- Una conversación por canal+chat: es la clave de upsert de ingress.
    CONSTRAINT conversations_channel_chat_key UNIQUE (channel, external_chat_id),
    CONSTRAINT conversations_channel_nonempty CHECK (pg_catalog.length(channel) > 0),
    CONSTRAINT conversations_chat_nonempty CHECK (pg_catalog.length(external_chat_id) > 0),
    CONSTRAINT conversations_status_check
        CHECK (status IN ('active', 'closed', 'archived', 'erased'))
);

COMMENT ON TABLE convo.conversations IS
    'S281 one row per (channel, external_chat_id). state_version = per-conversation '
    'CAS ordering handle advanced by convo.ingress. status=erased is the RGPD '
    'anonymization terminal state.';
COMMENT ON COLUMN convo.conversations.last_event_id IS
    'Denormalized pointer to the latest applied event (no FK to avoid the '
    'conversations<->conversation_events cycle; maintained by RPCs).';

-- ----------------------------------------------------------------------------
-- 2) conversation_events — event log durable, orden global por identity bigint
--    Dedup de ingress: unique (channel, external_update_id). Contiene texto
--    libre del técnico (content_text) = dato personal potencial (matriz RGPD).
-- ----------------------------------------------------------------------------
CREATE TABLE convo.conversation_events (
    id                 BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id    BIGINT      NOT NULL
        REFERENCES convo.conversations (id) ON DELETE CASCADE,
    channel            TEXT        NOT NULL,
    -- Idempotency key del transporte (Telegram update_id). Único por canal.
    external_update_id TEXT        NOT NULL,
    turn_no            INTEGER     NULL,
    idempotency_key    TEXT        NULL,
    role               TEXT        NOT NULL,
    event_type         TEXT        NOT NULL,
    -- Texto libre del técnico / respuesta / tool output: DATO PERSONAL POTENCIAL.
    content_text       TEXT        NULL,
    -- Payload estructurado del trace (no las claves relacionales — JSONB solo
    -- para lo flexible, assessment §3.2).
    payload            JSONB       NOT NULL DEFAULT '{}'::JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    -- DEDUP DE INGRESS (effectively-once, barrera 1): mismo update reentrante
    -- => cero filas nuevas.
    CONSTRAINT conversation_events_channel_update_key
        UNIQUE (channel, external_update_id),
    CONSTRAINT conversation_events_role_check
        CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    CONSTRAINT conversation_events_type_check
        CHECK (event_type IN ('message', 'tool_call', 'tool_result',
                              'run_state', 'delivery'))
);

-- Cursor pagination / orden por conversación (assessment §3.2).
CREATE INDEX conversation_events_conversation_id_idx
    ON convo.conversation_events (conversation_id, id);

COMMENT ON TABLE convo.conversation_events IS
    'S281 immutable durable event log. id (bigint identity) = global order. '
    'UNIQUE (channel, external_update_id) = ingress dedup barrier. content_text '
    'holds free technician text = potential personal data (see RGPD matrix).';

-- ----------------------------------------------------------------------------
-- 3) conversation_snapshots — working state versionado + summary derivado
--    (assessment §3.1). Escritura vía RPC dedicada = MT-0c (fuera del scope de
--    los 5 RPC de MT-0b); aquí solo la tabla.
-- ----------------------------------------------------------------------------
CREATE TABLE convo.conversation_snapshots (
    id                BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id   BIGINT      NOT NULL
        REFERENCES convo.conversations (id) ON DELETE CASCADE,
    snapshot_version  BIGINT      NOT NULL,
    -- Rango de eventos que resume (provenance del summary).
    through_event_id  BIGINT      NOT NULL
        REFERENCES convo.conversation_events (id) ON DELETE CASCADE,
    kind              TEXT        NOT NULL,
    -- Working state: producto/manual activo, locale/revisión, refs pendientes,
    -- restricciones, last_event_id (assessment §3.1). Puede reflejar dato
    -- personal derivado de los mensajes.
    working_state     JSONB       NOT NULL DEFAULT '{}'::JSONB,
    summary_text      TEXT        NULL,
    provenance        JSONB       NOT NULL DEFAULT '{}'::JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    CONSTRAINT conversation_snapshots_kind_check
        CHECK (kind IN ('working_state', 'summary')),
    -- Una versión por (conversación, tipo).
    CONSTRAINT conversation_snapshots_version_key
        UNIQUE (conversation_id, kind, snapshot_version)
);

CREATE INDEX conversation_snapshots_latest_idx
    ON convo.conversation_snapshots (conversation_id, kind, snapshot_version DESC);

COMMENT ON TABLE convo.conversation_snapshots IS
    'S281 versioned working state + derived summary. Never the only copy of the '
    'conversation (the event log is canonical). Writer RPC deferred to MT-0c.';

-- ----------------------------------------------------------------------------
-- 4) turn_runs — máquina de estados de cómputo con lease + fencing
--    Una fila por evento de entrada (unique input_event_id => idempotencia de
--    creación de run). attempt_no se incrementa in-place en reclaim.
--
--    MÁQUINA DE ESTADOS compute_status (transiciones forzadas por las RPCs vía
--    CAS; el CHECK solo restringe el conjunto de estados de UNA fila):
--       pending    --claim_run-->    running        (fencing 0->1)
--       running    --complete_run--> answer_ready   (CAS lease_owner+fencing;
--                                                     + INSERT outbox, atómico)
--       answer_ready --record_delivery(ok)--> delivered
--       running    --(worker error)--> failed
--       pending    --(worker error)--> failed
--       running(expired lease) --reclaim_run--> running (fencing++, attempt++)
--       failed     --reclaim_run-->   running        (retry, fencing++, attempt++)
--    Terminales: delivered (éxito), failed (sin reclaim disponible).
-- ----------------------------------------------------------------------------
CREATE TABLE convo.turn_runs (
    id                BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id   BIGINT      NOT NULL
        REFERENCES convo.conversations (id) ON DELETE CASCADE,
    input_event_id    BIGINT      NOT NULL
        REFERENCES convo.conversation_events (id) ON DELETE CASCADE,
    attempt_no        INTEGER     NOT NULL DEFAULT 1,
    compute_status    TEXT        NOT NULL DEFAULT 'pending',
    -- Ruta del orquestador (F0/F1: single_hop|clarify — diseño §1.3/§1.5).
    route             TEXT        NULL,
    pipeline_version  TEXT        NULL,
    model_version     TEXT        NULL,
    prompt_version    TEXT        NULL,
    -- Lease + fencing (assessment §3.2): el lease NO da ownership por sí solo;
    -- toda transición running->answer_ready hace CAS sobre lease_owner+fencing.
    lease_owner       TEXT        NULL,
    lease_expires_at  TIMESTAMPTZ NULL,
    fencing_token     BIGINT      NOT NULL DEFAULT 0,
    heartbeat_at      TIMESTAMPTZ NULL,
    tokens_input      INTEGER     NULL,
    tokens_output     INTEGER     NULL,
    cost_usd          NUMERIC(12, 6) NULL,
    latency_ms        INTEGER     NULL,
    error_class       TEXT        NULL,
    error_detail      TEXT        NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    started_at        TIMESTAMPTZ NULL,
    answered_at       TIMESTAMPTZ NULL,
    delivered_at      TIMESTAMPTZ NULL,
    failed_at         TIMESTAMPTZ NULL,
    -- Idempotencia de creación de run: a lo sumo un run por evento de entrada.
    CONSTRAINT turn_runs_input_event_key UNIQUE (input_event_id),
    CONSTRAINT turn_runs_status_check
        CHECK (compute_status IN ('pending', 'running', 'answer_ready',
                                 'delivered', 'failed')),
    CONSTRAINT turn_runs_route_check
        CHECK (route IS NULL OR route IN ('single_hop', 'clarify')),
    CONSTRAINT turn_runs_attempt_positive CHECK (attempt_no >= 1),
    CONSTRAINT turn_runs_fencing_nonneg CHECK (fencing_token >= 0),
    -- Invariantes de fila de la máquina de estados (lo que un CHECK sí puede):
    --   running exige propietario de lease + expiración.
    CONSTRAINT turn_runs_running_requires_lease CHECK (
        compute_status <> 'running'
        OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
    ),
    --   answer_ready/delivered exigen answered_at sellado.
    CONSTRAINT turn_runs_answered_requires_ts CHECK (
        compute_status NOT IN ('answer_ready', 'delivered')
        OR answered_at IS NOT NULL
    ),
    --   delivered exige delivered_at sellado.
    CONSTRAINT turn_runs_delivered_requires_ts CHECK (
        compute_status <> 'delivered' OR delivered_at IS NOT NULL
    )
);

-- FK index (conversación) para joins y borrado en cascada eficiente.
CREATE INDEX turn_runs_conversation_id_idx
    ON convo.turn_runs (conversation_id);
-- Partial index de LEASES ACTIVOS (heartbeat/monitor de runs vivos).
CREATE INDEX turn_runs_active_lease_idx
    ON convo.turn_runs (lease_expires_at)
    WHERE compute_status = 'running';
-- Partial index de candidatos a RECLAIM (running con lease vencido, y failed).
CREATE INDEX turn_runs_reclaimable_idx
    ON convo.turn_runs (lease_expires_at)
    WHERE compute_status IN ('running', 'failed');

COMMENT ON TABLE convo.turn_runs IS
    'S281 compute state machine. Lease alone is not ownership: running->answer_ready '
    'CAS is over (lease_owner, fencing_token, compute_status=running) inside the '
    'complete_run transaction. reclaim increments fencing_token so a stale worker '
    'can neither complete nor publish after a new owner.';

-- ----------------------------------------------------------------------------
-- 5) delivery_outbox — outbox transaccional (assessment §3.2)
--    El outbox `pending` se crea en la MISMA transacción que marca el run
--    answer_ready (dentro de convo.complete_run). El envío a Telegram ocurre
--    DESPUÉS, fuera de toda transacción.
-- ----------------------------------------------------------------------------
CREATE TABLE convo.delivery_outbox (
    id                   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    turn_run_id          BIGINT      NOT NULL
        REFERENCES convo.turn_runs (id) ON DELETE CASCADE,
    -- Denormalizado para alcance de lifecycle RGPD y scoping de índices.
    conversation_id      BIGINT      NOT NULL
        REFERENCES convo.conversations (id) ON DELETE CASCADE,
    channel              TEXT        NOT NULL,
    destination          TEXT        NOT NULL,
    -- Clave lógica de entrega (idempotencia del envío; barrera 2, no sustituye
    -- al fencing).
    logical_delivery_key TEXT        NOT NULL,
    -- Respuesta final del bot (puede reflejar dato personal del hilo).
    payload_text         TEXT        NOT NULL,
    payload              JSONB       NOT NULL DEFAULT '{}'::JSONB,
    delivery_status      TEXT        NOT NULL DEFAULT 'pending',
    attempt_count        INTEGER     NOT NULL DEFAULT 0,
    max_attempts         INTEGER     NOT NULL DEFAULT 5,
    next_attempt_at      TIMESTAMPTZ NULL,
    -- Receipt externo (message_id de Telegram) — conciliación effectively-once.
    external_receipt     TEXT        NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    delivered_at         TIMESTAMPTZ NULL,
    -- UNIQUE lógica del outbox (assessment §3.2): segunda barrera de no-reemisión.
    CONSTRAINT delivery_outbox_logical_key
        UNIQUE (turn_run_id, channel, destination, logical_delivery_key),
    CONSTRAINT delivery_outbox_status_check
        CHECK (delivery_status IN ('pending', 'sending', 'delivered',
                                  'retryable', 'dead_letter')),
    CONSTRAINT delivery_outbox_attempts_nonneg CHECK (attempt_count >= 0),
    CONSTRAINT delivery_outbox_max_attempts_positive CHECK (max_attempts >= 1),
    CONSTRAINT delivery_outbox_delivered_requires_ts CHECK (
        delivery_status <> 'delivered' OR delivered_at IS NOT NULL
    )
);

CREATE INDEX delivery_outbox_turn_run_id_idx
    ON convo.delivery_outbox (turn_run_id);
CREATE INDEX delivery_outbox_conversation_id_idx
    ON convo.delivery_outbox (conversation_id);
-- Partial index de OUTBOX PENDIENTE (el sender lo poll-ea).
CREATE INDEX delivery_outbox_pending_idx
    ON convo.delivery_outbox (next_attempt_at NULLS FIRST, id)
    WHERE delivery_status IN ('pending', 'retryable');
-- Partial index de SENDING ATASCADO: recovery de un sender caído entre
-- begin_delivery y record_delivery (la fila queda 'sending' y el índice de
-- pendientes NO la ve). El janitor de MT-0c escanea sending con next_attempt_at
-- vencido y lo sella vía record_delivery(success=false, 'sending_lease_expired').
CREATE INDEX delivery_outbox_sending_stale_idx
    ON convo.delivery_outbox (next_attempt_at)
    WHERE delivery_status = 'sending';

COMMENT ON TABLE convo.delivery_outbox IS
    'S281 transactional outbox. pending row is created in the same transaction as '
    'the run answer_ready CAS (convo.complete_run). Telegram send happens AFTER, '
    'outside any transaction. UNIQUE logical key = second no-reemission barrier.';

-- ----------------------------------------------------------------------------
-- 6) delivery_attempts — ledger de intentos/receipts por entrega
-- ----------------------------------------------------------------------------
CREATE TABLE convo.delivery_attempts (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outbox_id        BIGINT      NOT NULL
        REFERENCES convo.delivery_outbox (id) ON DELETE CASCADE,
    attempt_no       INTEGER     NOT NULL,
    attempt_status   TEXT        NOT NULL,
    external_receipt TEXT        NULL,
    error_class      TEXT        NULL,
    error_detail     TEXT        NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    finished_at      TIMESTAMPTZ NULL,
    CONSTRAINT delivery_attempts_no_key UNIQUE (outbox_id, attempt_no),
    CONSTRAINT delivery_attempts_status_check
        CHECK (attempt_status IN ('sending', 'succeeded', 'failed')),
    CONSTRAINT delivery_attempts_no_positive CHECK (attempt_no >= 1)
);

CREATE INDEX delivery_attempts_outbox_id_idx
    ON convo.delivery_attempts (outbox_id);

COMMENT ON TABLE convo.delivery_attempts IS
    'S281 per-delivery attempt/receipt ledger. One row per send attempt; the '
    'succeeded/failed ack is recorded by convo.record_delivery after the '
    'out-of-transaction Telegram send.';

-- ----------------------------------------------------------------------------
-- 7) Cierre de seguridad: REVOKE explícito sobre TODO lo creado (defensa en
--    profundidad — las tablas ya nacen sin grants, esto lo hace inequívoco).
-- ----------------------------------------------------------------------------
REVOKE ALL ON ALL TABLES IN SCHEMA convo
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA convo
    FROM PUBLIC, anon, authenticated, service_role;

-- convo_rpc NO recibe NINGÚN privilegio de tabla aquí (por diseño): su única vía
-- a los datos son los RPCs SECURITY DEFINER del archivo hermano.

NOTIFY pgrst, 'reload schema';
