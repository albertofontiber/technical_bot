-- ============================================================================
-- PROPUESTA NO APLICADA — BLOQUEADA POR MATRIZ RGPD. NO EJECUTAR.
-- ============================================================================
-- s281 / lane MT-0b — RPCs SECURITY DEFINER del schema `convo` (Fase 0).
-- Requiere aplicado previo de 20260723100000_s281_convo_schema_f0.sql.
-- Diseño canónico: evals/s280_multiturn_design_v2.md §1 (fix ACCESO-FISICO-CONVO)
-- + assessment §3.2 (paquete effectively-once ÍNTEGRO en F0).
--
-- CONTRATO GLOBAL de estas RPCs (fix ACCESO-FISICO-CONVO):
--   * Cada función = UNA transacción corta (el cuerpo de la función ES la
--     transacción bajo PostgREST POST /rpc).  CERO llamadas HTTP/LLM dentro:
--     el envío a Telegram y la generación LLM ocurren FUERA, en el orquestador.
--   * SECURITY DEFINER + `SET search_path = pg_catalog`: los builtins resuelven
--     sin ambigüedad y TODAS las tablas se cualifican `convo.*` (higiene contra
--     schema-shadowing).  Deben ser propiedad del rol que posee las tablas convo.
--   * REVOKE ALL a PUBLIC/anon/authenticated/service_role; GRANT EXECUTE SOLO a
--     convo_rpc.  Las tablas no tienen grants → el definer es la única vía.
--
-- Convención de formato: SIN BEGIN/COMMIT envolvente.
-- Estado de release: NO_GO_FOR_DB hasta matriz RGPD firmada.
-- Rollback: cae con DROP SCHEMA convo CASCADE (archivo hermano).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RPC (1) convo.ingress — dedup idempotente de ingress + orden por conversación
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: idempotencia por (channel, external_update_id). Un update
--     reentrante NO crea filas nuevas y devuelve el MISMO conversation_id /
--     event_id / turn_run_id con is_new_event=false. Un evento nuevo: upsert de
--     la conversación (por channel+external_chat_id), INSERT del evento, avance
--     de state_version (CAS de orden), y creación idempotente del turn_run
--     pending para eventos role='user'. Todo en una transacción.
--   FALLA: si p_role/p_event_type violan los CHECK del schema (excepción del
--     constraint, rollback de la transacción). No hay fallo "silencioso".
--   DEVUELVE: jsonb {conversation_id, public_id, event_id, turn_run_id,
--     is_new_event, is_new_conversation, state_version}.
CREATE FUNCTION convo.ingress(
    p_channel            TEXT,
    p_external_update_id TEXT,
    p_external_chat_id   TEXT,
    p_role               TEXT        DEFAULT 'user',
    p_event_type         TEXT        DEFAULT 'message',
    p_content_text       TEXT        DEFAULT NULL,
    p_payload            JSONB       DEFAULT '{}'::JSONB,
    p_tenant_id          TEXT        DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_conversation_id BIGINT;
    v_public_id       UUID;
    v_state_version   BIGINT;
    v_conv_is_new     BOOLEAN;
    v_event_id        BIGINT;
    v_is_new_event    BOOLEAN;
    v_turn_run_id     BIGINT;
BEGIN
    -- Upsert de la conversación. El truco (xmax = 0) distingue INSERT (0) de
    -- UPDATE (<>0) en un upsert con RETURNING — idioma estándar de Postgres.
    INSERT INTO convo.conversations (channel, external_chat_id, tenant_id)
    VALUES (p_channel, p_external_chat_id, p_tenant_id)
    ON CONFLICT (channel, external_chat_id)
    DO UPDATE SET updated_at = now()
    RETURNING id, public_id, state_version, (xmax::text::bigint = 0)
    INTO v_conversation_id, v_public_id, v_state_version, v_conv_is_new;

    -- INSERT del evento con dedup idempotente (barrera 1 de effectively-once).
    INSERT INTO convo.conversation_events (
        conversation_id, channel, external_update_id,
        role, event_type, content_text, payload
    )
    VALUES (
        v_conversation_id, p_channel, p_external_update_id,
        p_role, p_event_type, p_content_text, p_payload
    )
    ON CONFLICT (channel, external_update_id) DO NOTHING
    RETURNING id INTO v_event_id;

    IF v_event_id IS NULL THEN
        -- Ingress DUPLICADO: recupera el estado ya registrado (idempotente).
        v_is_new_event := FALSE;
        SELECT ev.id, ev.conversation_id
          INTO v_event_id, v_conversation_id
          FROM convo.conversation_events AS ev
         WHERE ev.channel = p_channel
           AND ev.external_update_id = p_external_update_id;
        SELECT tr.id INTO v_turn_run_id
          FROM convo.turn_runs AS tr
         WHERE tr.input_event_id = v_event_id;
        -- state_version actual de la conversación (no se avanza en duplicado).
        SELECT c.state_version, c.public_id
          INTO v_state_version, v_public_id
          FROM convo.conversations AS c
         WHERE c.id = v_conversation_id;
        v_conv_is_new := FALSE;
    ELSE
        v_is_new_event := TRUE;
        -- Avance del CAS de orden por conversación + puntero al último evento.
        UPDATE convo.conversations
           SET state_version = state_version + 1,
               last_event_id = v_event_id,
               updated_at = now()
         WHERE id = v_conversation_id
        RETURNING state_version INTO v_state_version;

        -- Un turno de usuario engendra su run de cómputo pending (idempotente
        -- por la unique input_event_id; barrera de creación única de run).
        IF p_role = 'user' THEN
            INSERT INTO convo.turn_runs (conversation_id, input_event_id)
            VALUES (v_conversation_id, v_event_id)
            ON CONFLICT (input_event_id) DO NOTHING
            RETURNING id INTO v_turn_run_id;
            IF v_turn_run_id IS NULL THEN
                SELECT tr.id INTO v_turn_run_id
                  FROM convo.turn_runs AS tr
                 WHERE tr.input_event_id = v_event_id;
            END IF;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'conversation_id', v_conversation_id,
        'public_id', v_public_id,
        'event_id', v_event_id,
        'turn_run_id', v_turn_run_id,
        'is_new_event', v_is_new_event,
        'is_new_conversation', v_conv_is_new,
        'state_version', v_state_version
    );
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (2a) convo.claim_run — primer claim del lease + fencing (adquisición)
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: transición pending->running SOLO si el run está en pending.
--     Incrementa fencing_token (monotónico), fija lease_owner/lease_expires_at,
--     sella started_at. Es la adquisición limpia; el reclaim de runs crashed va
--     por convo.reclaim_run (2c).
--   FALLA (claimed=false, sin cambios): run inexistente, o no está en pending
--     (ya lo tiene otro worker / answer_ready / delivered). reason lo explica.
--   DEVUELVE: jsonb {claimed, fencing_token, attempt_no, compute_status,
--     lease_expires_at, reason}.
CREATE FUNCTION convo.claim_run(
    p_turn_run_id BIGINT,
    p_lease_owner TEXT,
    p_lease_seconds INTEGER DEFAULT 60
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_fencing    BIGINT;
    v_attempt    INTEGER;
    v_lease_exp  TIMESTAMPTZ;
    v_status     TEXT;
BEGIN
    IF p_lease_seconds <= 0 THEN
        RAISE EXCEPTION 'claim_run: p_lease_seconds must be positive (got %)',
            p_lease_seconds;
    END IF;
    IF p_lease_owner IS NULL OR length(p_lease_owner) = 0 THEN
        RAISE EXCEPTION 'claim_run: p_lease_owner must be non-empty';
    END IF;

    UPDATE convo.turn_runs
       SET compute_status = 'running',
           lease_owner = p_lease_owner,
           lease_expires_at = now() + make_interval(secs => p_lease_seconds),
           fencing_token = fencing_token + 1,
           heartbeat_at = now(),
           started_at = COALESCE(started_at, now()),
           updated_at = now()
     WHERE id = p_turn_run_id
       AND compute_status = 'pending'
    RETURNING fencing_token, attempt_no, lease_expires_at
      INTO v_fencing, v_attempt, v_lease_exp;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'claimed', TRUE,
            'fencing_token', v_fencing,
            'attempt_no', v_attempt,
            'compute_status', 'running',
            'lease_expires_at', v_lease_exp,
            'reason', 'claimed'
        );
    END IF;

    SELECT compute_status INTO v_status
      FROM convo.turn_runs WHERE id = p_turn_run_id;
    RETURN jsonb_build_object(
        'claimed', FALSE,
        'fencing_token', NULL,
        'attempt_no', NULL,
        'compute_status', v_status,
        'lease_expires_at', NULL,
        'reason', CASE
            WHEN v_status IS NULL THEN 'run_not_found'
            ELSE 'not_pending'
        END
    );
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (2b) convo.heartbeat_run — extensión del lease por el propietario vivo
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: extiende lease_expires_at SOLO si el caller sigue siendo el
--     propietario exacto (lease_owner + fencing_token) de un run en running.
--   FALLA (extended=false, sin cambios): fencing/owner obsoleto (fue reclamado)
--     o el run ya no está en running. Es la señal para que el worker abandone.
--   DEVUELVE: jsonb {extended, lease_expires_at, reason}.
CREATE FUNCTION convo.heartbeat_run(
    p_turn_run_id BIGINT,
    p_lease_owner TEXT,
    p_fencing_token BIGINT,
    p_lease_seconds INTEGER DEFAULT 60
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_lease_exp TIMESTAMPTZ;
BEGIN
    IF p_lease_seconds <= 0 THEN
        RAISE EXCEPTION 'heartbeat_run: p_lease_seconds must be positive';
    END IF;

    UPDATE convo.turn_runs
       SET lease_expires_at = now() + make_interval(secs => p_lease_seconds),
           heartbeat_at = now(),
           updated_at = now()
     WHERE id = p_turn_run_id
       AND compute_status = 'running'
       AND lease_owner = p_lease_owner
       AND fencing_token = p_fencing_token
    RETURNING lease_expires_at INTO v_lease_exp;

    RETURN jsonb_build_object(
        'extended', FOUND,
        'lease_expires_at', v_lease_exp,
        'reason', CASE WHEN FOUND THEN 'extended' ELSE 'stale_or_not_running' END
    );
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (2c / 4) convo.reclaim_run — reclamo de lease expirado o retry de failed
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: reasigna a un nuevo propietario un run 'running' con lease
--     VENCIDO (worker caído) o 'failed' (retry), incrementando fencing_token
--     (así el propietario anterior ya no puede completar ni publicar) y
--     attempt_no. Acotado por p_max_attempts. El caller localiza candidatos con
--     el partial index turn_runs_reclaimable_idx y llama por id (una txn corta).
--   FALLA (reclaimed=false, sin cambios): lease aún vivo, run inexistente,
--     estado no reclamable, o presupuesto de intentos agotado. reason lo dice.
--   DEVUELVE: jsonb {reclaimed, fencing_token, attempt_no, lease_expires_at,
--     previous_owner, reason}.
CREATE FUNCTION convo.reclaim_run(
    p_turn_run_id BIGINT,
    p_lease_owner TEXT,
    p_lease_seconds INTEGER DEFAULT 60,
    p_max_attempts INTEGER DEFAULT 5
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_prev_owner TEXT;
    v_status     TEXT;
    v_attempt    INTEGER;
    v_lease_exp  TIMESTAMPTZ;
    v_fencing    BIGINT;
    v_new_attempt INTEGER;
    v_reason     TEXT;
BEGIN
    IF p_lease_seconds <= 0 THEN
        RAISE EXCEPTION 'reclaim_run: p_lease_seconds must be positive';
    END IF;
    IF p_lease_owner IS NULL OR length(p_lease_owner) = 0 THEN
        RAISE EXCEPTION 'reclaim_run: p_lease_owner must be non-empty';
    END IF;

    -- Lock + lectura del estado previo (para previous_owner y diagnóstico).
    SELECT lease_owner, compute_status, attempt_no
      INTO v_prev_owner, v_status, v_attempt
      FROM convo.turn_runs
     WHERE id = p_turn_run_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'reclaimed', FALSE, 'fencing_token', NULL, 'attempt_no', NULL,
            'lease_expires_at', NULL, 'previous_owner', NULL,
            'reason', 'run_not_found');
    END IF;

    UPDATE convo.turn_runs
       SET compute_status = 'running',
           lease_owner = p_lease_owner,
           lease_expires_at = now() + make_interval(secs => p_lease_seconds),
           fencing_token = fencing_token + 1,
           attempt_no = attempt_no + 1,
           heartbeat_at = now(),
           started_at = COALESCE(started_at, now()),
           updated_at = now()
     WHERE id = p_turn_run_id
       AND attempt_no < p_max_attempts
       AND (
           (compute_status = 'running'
            AND (lease_expires_at IS NULL OR lease_expires_at < now()))
           OR compute_status = 'failed'
       )
    RETURNING fencing_token, attempt_no, lease_expires_at
      INTO v_fencing, v_new_attempt, v_lease_exp;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'reclaimed', TRUE,
            'fencing_token', v_fencing,
            'attempt_no', v_new_attempt,
            'lease_expires_at', v_lease_exp,
            'previous_owner', v_prev_owner,
            'reason', 'reclaimed');
    END IF;

    -- Estados terminales/no-reclamables PRIMERO: un run ya entregado con
    -- attempt_no alto no debe reportar 'attempt_budget_exhausted' (engañoso).
    v_reason := CASE
        WHEN v_status IN ('answer_ready', 'delivered') THEN 'not_reclaimable'
        WHEN v_status = 'pending' THEN 'use_claim_run'
        WHEN v_attempt >= p_max_attempts THEN 'attempt_budget_exhausted'
        WHEN v_status = 'running' THEN 'lease_still_live'
        ELSE 'not_reclaimable'
    END;
    RETURN jsonb_build_object(
        'reclaimed', FALSE, 'fencing_token', NULL, 'attempt_no', v_attempt,
        'lease_expires_at', NULL, 'previous_owner', v_prev_owner,
        'reason', v_reason);
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (3) convo.complete_run — CAS running->answer_ready + INSERT outbox ATÓMICO
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL (corazón del effectively-once):
--   GARANTIZA: la transición running->answer_ready y la creación del outbox
--     pending ocurren en la MISMA transacción, guardadas por CAS sobre
--     (id, compute_status=running, lease_owner, fencing_token). Un claim STALE
--     (fencing viejo tras un reclaim, o run ya no running) NO produce efecto:
--     falla limpio. El outbox es idempotente por su unique lógica (re-complete
--     del propietario legítimo no duplica).
--   FALLA (completed=false, sin cambios): CAS no casa (stale_claim), o run no
--     encontrado.
--   DEVUELVE: jsonb {completed, outbox_id, compute_status, reason}.
CREATE FUNCTION convo.complete_run(
    p_turn_run_id BIGINT,
    p_lease_owner TEXT,
    p_fencing_token BIGINT,
    p_channel TEXT,
    p_destination TEXT,
    p_logical_delivery_key TEXT,
    p_answer_text TEXT,
    p_answer_payload JSONB DEFAULT '{}'::JSONB,
    p_tokens_input INTEGER DEFAULT NULL,
    p_tokens_output INTEGER DEFAULT NULL,
    p_cost_usd NUMERIC DEFAULT NULL,
    p_latency_ms INTEGER DEFAULT NULL,
    p_max_attempts INTEGER DEFAULT 5
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_conversation_id BIGINT;
    v_outbox_id       BIGINT;
    v_status          TEXT;
BEGIN
    -- CAS propietario: SOLO el dueño vigente (lease_owner + fencing_token) de un
    -- run 'running' completa. Un reclaim habrá subido el fencing => stale falla.
    UPDATE convo.turn_runs
       SET compute_status = 'answer_ready',
           answered_at = now(),
           tokens_input = p_tokens_input,
           tokens_output = p_tokens_output,
           cost_usd = p_cost_usd,
           latency_ms = p_latency_ms,
           updated_at = now()
     WHERE id = p_turn_run_id
       AND compute_status = 'running'
       AND lease_owner = p_lease_owner
       AND fencing_token = p_fencing_token
    RETURNING conversation_id INTO v_conversation_id;

    IF NOT FOUND THEN
        SELECT compute_status INTO v_status
          FROM convo.turn_runs WHERE id = p_turn_run_id;
        RETURN jsonb_build_object(
            'completed', FALSE,
            'outbox_id', NULL,
            'compute_status', v_status,
            'reason', CASE
                WHEN v_status IS NULL THEN 'run_not_found'
                ELSE 'stale_claim'
            END);
    END IF;

    -- Outbox pending en la MISMA transacción; idempotente por la unique lógica.
    INSERT INTO convo.delivery_outbox (
        turn_run_id, conversation_id, channel, destination,
        logical_delivery_key, payload_text, payload, max_attempts
    )
    VALUES (
        p_turn_run_id, v_conversation_id, p_channel, p_destination,
        p_logical_delivery_key, p_answer_text, p_answer_payload, p_max_attempts
    )
    ON CONFLICT (turn_run_id, channel, destination, logical_delivery_key)
    DO NOTHING
    RETURNING id INTO v_outbox_id;

    IF v_outbox_id IS NULL THEN
        SELECT id INTO v_outbox_id
          FROM convo.delivery_outbox
         WHERE turn_run_id = p_turn_run_id
           AND channel = p_channel
           AND destination = p_destination
           AND logical_delivery_key = p_logical_delivery_key;
    END IF;

    RETURN jsonb_build_object(
        'completed', TRUE,
        'outbox_id', v_outbox_id,
        'compute_status', 'answer_ready',
        'reason', 'completed');
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (6) convo.fail_run — CAS running->failed (error de worker)
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: transición running->failed guardada por CAS sobre
--     (id, compute_status=running, lease_owner, fencing_token) — el mismo
--     patrón propietario que complete_run. Sella failed_at y escribe
--     error_class/error_detail. Habilita el retry vía reclaim_run (failed ->
--     running). Sin esta RPC el estado 'failed' sería inalcanzable y
--     error_class/error_detail columnas muertas.
--   FALLA (failed=false, sin cambios): CAS no casa (fencing viejo tras reclaim o
--     run no running) -> 'stale_claim'; o run inexistente -> 'run_not_found'.
--   DEVUELVE: jsonb {failed, compute_status, reason}.
CREATE FUNCTION convo.fail_run(
    p_turn_run_id BIGINT,
    p_lease_owner TEXT,
    p_fencing_token BIGINT,
    p_error_class TEXT DEFAULT NULL,
    p_error_detail TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_status TEXT;
BEGIN
    UPDATE convo.turn_runs
       SET compute_status = 'failed',
           failed_at = now(),
           error_class = p_error_class,
           error_detail = p_error_detail,
           updated_at = now()
     WHERE id = p_turn_run_id
       AND compute_status = 'running'
       AND lease_owner = p_lease_owner
       AND fencing_token = p_fencing_token;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'failed', TRUE,
            'compute_status', 'failed',
            'reason', 'failed');
    END IF;

    SELECT compute_status INTO v_status
      FROM convo.turn_runs WHERE id = p_turn_run_id;
    RETURN jsonb_build_object(
        'failed', FALSE,
        'compute_status', v_status,
        'reason', CASE
            WHEN v_status IS NULL THEN 'run_not_found'
            ELSE 'stale_claim'
        END);
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (5a) convo.begin_delivery — CAS pending/retryable->sending (claim de envío)
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: reclama un outbox para envío (pending|retryable -> sending),
--     incrementa attempt_count y abre una fila delivery_attempts 'sending'. El
--     row-lock + guard de estado impiden que dos senders tomen el mismo outbox.
--     Debe llamarse ANTES del envío HTTP a Telegram (que ocurre fuera de la txn).
--   FALLA (started=false, sin cambios): ya 'sending'/'delivered'/'dead_letter',
--     u outbox inexistente.
--   DEVUELVE: jsonb {started, outbox_id, attempt_no, reason}.
CREATE FUNCTION convo.begin_delivery(
    p_outbox_id BIGINT,
    p_lease_seconds INTEGER DEFAULT 60
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_attempt_no INTEGER;
    v_status     TEXT;
BEGIN
    UPDATE convo.delivery_outbox
       SET delivery_status = 'sending',
           attempt_count = attempt_count + 1,
           next_attempt_at = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     WHERE id = p_outbox_id
       AND delivery_status IN ('pending', 'retryable')
    RETURNING attempt_count INTO v_attempt_no;

    IF NOT FOUND THEN
        SELECT delivery_status INTO v_status
          FROM convo.delivery_outbox WHERE id = p_outbox_id;
        RETURN jsonb_build_object(
            'started', FALSE, 'outbox_id', p_outbox_id, 'attempt_no', NULL,
            'reason', CASE
                WHEN v_status IS NULL THEN 'outbox_not_found'
                ELSE 'not_claimable'
            END);
    END IF;

    INSERT INTO convo.delivery_attempts (outbox_id, attempt_no, attempt_status)
    VALUES (p_outbox_id, v_attempt_no, 'sending');

    RETURN jsonb_build_object(
        'started', TRUE, 'outbox_id', p_outbox_id, 'attempt_no', v_attempt_no,
        'reason', 'sending');
END;
$function$;

-- ----------------------------------------------------------------------------
-- RPC (5b) convo.record_delivery — acuse del envío (attempt + receipt + estado)
-- ----------------------------------------------------------------------------
-- CONTRATO TRANSACCIONAL:
--   GARANTIZA: registra el resultado del envío ya realizado a Telegram (fuera de
--     transacción). Éxito: sella el attempt 'succeeded' + receipt, flip del
--     outbox a 'delivered' (idempotente: si ya delivered, no-op) y del turn_run
--     a 'delivered'. Fallo: attempt 'failed'; outbox -> 'retryable' (con
--     next_attempt_at) mientras haya presupuesto, si no -> 'dead_letter'. Toda
--     la conciliación en una transacción. NO reemite un delivery ya confirmado.
--   IDEMPOTENCIA DEL ACUSE: el sellado del attempt se guarda con
--     attempt_status='sending'; un segundo acuse sobre el mismo intento NO
--     re-pisa receipt/estado (acknowledged=false, reason='attempt_already_sealed').
--   FALLA (acknowledged=false): la fila delivery_attempts (outbox_id, attempt_no)
--     no existe (begin_delivery no precedió) -> 'attempt_not_found'; o ya estaba
--     sellada -> 'attempt_already_sealed'.
--   DEVUELVE: jsonb {acknowledged, delivery_status, turn_delivered, reason}.
CREATE FUNCTION convo.record_delivery(
    p_outbox_id BIGINT,
    p_attempt_no INTEGER,
    p_success BOOLEAN,
    p_external_receipt TEXT DEFAULT NULL,
    p_error_class TEXT DEFAULT NULL,
    p_error_detail TEXT DEFAULT NULL,
    p_retry_seconds INTEGER DEFAULT 60
)
RETURNS JSONB
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
    v_attempt_id    BIGINT;
    v_attempt_count INTEGER;
    v_max_attempts  INTEGER;
    v_turn_run_id   BIGINT;
    v_new_status    TEXT;
    v_turn_delivered BOOLEAN := FALSE;
BEGIN
    -- Sella el intento correspondiente (abierto por begin_delivery).
    UPDATE convo.delivery_attempts
       SET attempt_status = CASE WHEN p_success THEN 'succeeded' ELSE 'failed' END,
           external_receipt = p_external_receipt,
           error_class = p_error_class,
           error_detail = p_error_detail,
           finished_at = now()
     WHERE outbox_id = p_outbox_id
       AND attempt_no = p_attempt_no
       AND attempt_status = 'sending'
    RETURNING id INTO v_attempt_id;

    IF NOT FOUND THEN
        -- Distingue intento inexistente de ya-sellado (idempotencia del acuse:
        -- un segundo acuse NO re-pisa receipt ni estado).
        IF EXISTS (
            SELECT 1 FROM convo.delivery_attempts
             WHERE outbox_id = p_outbox_id AND attempt_no = p_attempt_no
        ) THEN
            RETURN jsonb_build_object(
                'acknowledged', FALSE, 'delivery_status', NULL,
                'turn_delivered', FALSE, 'reason', 'attempt_already_sealed');
        END IF;
        RETURN jsonb_build_object(
            'acknowledged', FALSE, 'delivery_status', NULL,
            'turn_delivered', FALSE, 'reason', 'attempt_not_found');
    END IF;

    SELECT attempt_count, max_attempts, turn_run_id
      INTO v_attempt_count, v_max_attempts, v_turn_run_id
      FROM convo.delivery_outbox
     WHERE id = p_outbox_id
     FOR UPDATE;

    IF p_success THEN
        UPDATE convo.delivery_outbox
           SET delivery_status = 'delivered',
               external_receipt = p_external_receipt,
               delivered_at = now(),
               updated_at = now()
         WHERE id = p_outbox_id
           AND delivery_status <> 'delivered';
        v_new_status := 'delivered';

        -- Marca el run entregado (idempotente: solo desde answer_ready).
        UPDATE convo.turn_runs
           SET compute_status = 'delivered',
               delivered_at = COALESCE(delivered_at, now()),
               updated_at = now()
         WHERE id = v_turn_run_id
           AND compute_status = 'answer_ready'
        RETURNING TRUE INTO v_turn_delivered;
        v_turn_delivered := COALESCE(v_turn_delivered, FALSE);
    ELSE
        IF v_attempt_count >= v_max_attempts THEN
            v_new_status := 'dead_letter';
            UPDATE convo.delivery_outbox
               SET delivery_status = 'dead_letter', updated_at = now()
             WHERE id = p_outbox_id;
        ELSE
            v_new_status := 'retryable';
            UPDATE convo.delivery_outbox
               SET delivery_status = 'retryable',
                   next_attempt_at = now() + make_interval(secs => p_retry_seconds),
                   updated_at = now()
             WHERE id = p_outbox_id;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'acknowledged', TRUE,
        'delivery_status', v_new_status,
        'turn_delivered', v_turn_delivered,
        'reason', CASE WHEN p_success THEN 'delivered' ELSE v_new_status END);
END;
$function$;

-- ----------------------------------------------------------------------------
-- Grants: REVOKE por defecto; EXECUTE SOLO a convo_rpc. Comentario-contrato por fn.
-- ----------------------------------------------------------------------------
DO $grants$
DECLARE
    fn TEXT;
    fns TEXT[] := ARRAY[
        'convo.ingress(text,text,text,text,text,text,jsonb,text)',
        'convo.claim_run(bigint,text,integer)',
        'convo.heartbeat_run(bigint,text,bigint,integer)',
        'convo.reclaim_run(bigint,text,integer,integer)',
        'convo.complete_run(bigint,text,bigint,text,text,text,text,jsonb,integer,integer,numeric,integer,integer)',
        'convo.fail_run(bigint,text,bigint,text,text)',
        'convo.begin_delivery(bigint,integer)',
        'convo.record_delivery(bigint,integer,boolean,text,text,text,integer)'
    ];
BEGIN
    FOREACH fn IN ARRAY fns LOOP
        EXECUTE format(
            'REVOKE ALL ON FUNCTION %s FROM PUBLIC, anon, authenticated, service_role',
            fn);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO convo_rpc', fn);
    END LOOP;
END
$grants$;

COMMENT ON FUNCTION convo.ingress(text,text,text,text,text,text,jsonb,text) IS
    'S281 ingress: idempotent dedup by (channel, external_update_id) + per-conversation '
    'state_version advance + idempotent pending turn_run for user turns. One txn, no HTTP/LLM.';
COMMENT ON FUNCTION convo.claim_run(bigint,text,integer) IS
    'S281 claim: pending->running with fencing++ (clean acquisition). One txn.';
COMMENT ON FUNCTION convo.heartbeat_run(bigint,text,bigint,integer) IS
    'S281 heartbeat: extends lease only for the exact owner (lease_owner+fencing_token) of a running run.';
COMMENT ON FUNCTION convo.reclaim_run(bigint,text,integer,integer) IS
    'S281 reclaim: expired-lease running or failed -> running with fencing++/attempt++; bounded by max_attempts. Fails clean if lease live.';
COMMENT ON FUNCTION convo.complete_run(bigint,text,bigint,text,text,text,text,jsonb,integer,integer,numeric,integer,integer) IS
    'S281 complete: CAS running->answer_ready + outbox pending INSERT, atomic in one txn, guarded by lease_owner+fencing_token. Stale claim fails clean.';
COMMENT ON FUNCTION convo.fail_run(bigint,text,bigint,text,text) IS
    'S281 fail_run: CAS running->failed guarded by lease_owner+fencing_token; seals failed_at + error_class/detail; enables retry via reclaim_run. Stale claim fails clean.';
COMMENT ON FUNCTION convo.begin_delivery(bigint,integer) IS
    'S281 begin_delivery: CAS pending/retryable->sending + open attempt. Call before the out-of-txn Telegram send.';
COMMENT ON FUNCTION convo.record_delivery(bigint,integer,boolean,text,text,text,integer) IS
    'S281 record_delivery: seal attempt + receipt; success flips outbox+run to delivered (idempotent), failure -> retryable/dead_letter. No re-emission of confirmed delivery.';

NOTIFY pgrst, 'reload schema';
