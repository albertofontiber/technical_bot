-- ============================================================================
-- PROPUESTA NO APLICADA — BLOQUEADA POR MATRIZ RGPD. NO EJECUTAR.
-- ============================================================================
-- s281 / lane MT-0c — RPCs de LECTURA SECURITY DEFINER del schema `convo` (F0).
-- Enmienda de MT-0b: sus 8 RPCs son todas MUTANTES; el janitor/poller de MT-0c
-- (src/orchestrator/lifecycle.py) necesita una superficie de LECTURA para
-- DESCUBRIR candidatos de recuperación. Sin ella, las recuperaciones de las
-- fronteras 3-5 no tienen actor ni superficie contra el store real (hallazgo
-- SCAN-SIN-SUPERFICIE-REAL del dúo r1).
-- Requiere aplicado previo de 20260723100000_s281_convo_schema_f0.sql
-- (+ 20260723100001 para el rol convo_rpc y el schema).
--
-- CONTRATO GLOBAL (idéntico a las 8 mutantes):
--   * Cada función = UNA lectura corta bajo PostgREST POST /rpc. CERO HTTP/LLM.
--   * SECURITY DEFINER + `SET search_path = pg_catalog`: builtins sin ambigüedad,
--     tablas cualificadas `convo.*` (higiene anti schema-shadowing). Propiedad
--     del rol que posee las tablas convo.
--   * REVOKE ALL a PUBLIC/anon/authenticated/service_role; GRANT EXECUTE SOLO a
--     convo_rpc (el mismo principal que las mutantes; el bearer JWT role=convo_rpc
--     acuñado como p1_readonly — runbook:227-233).
--   * `now()` es el instante de comparación del DB (no se pasa por la red): el
--     cliente Python acepta un `now` por paridad con el fake pero no lo envía.
--
-- SETOF jsonb: PostgREST serializa el conjunto como un array JSON de objetos; el
-- cliente mapea cada fila a su dataclass (ReclaimCandidate/OutboxRecord/
-- StuckSending). Los shapes coinciden con convo_store.py.
--
-- Scheduling del janitor/poller que LLAMA estas RPCs = dependencia MT-0d.
-- Estado de release: NO_GO_FOR_DB hasta matriz RGPD firmada.
-- Rollback: cae con DROP SCHEMA convo CASCADE (archivo de schema hermano).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- READ (1) convo.list_reclaimable_runs — candidatos huérfanos de cómputo
-- ----------------------------------------------------------------------------
-- CONTRATO DE LECTURA:
--   DEVUELVE (SETOF jsonb, uno por run): {turn_run_id, compute_status,
--     attempt_no} de todo run huérfano dentro de presupuesto (attempt_no <
--     p_max_attempts) en uno de tres estados:
--       * 'running' con lease VENCIDO (frontera 2: worker caído tras claim);
--       * 'failed' (error de cómputo registrado, apto para retry);
--       * 'pending' con edad > p_pending_age_seconds (frontera 1: worker caído
--         entre ingress y claim — que el partial index running/failed NO ve).
--   El janitor sólo REPORTA estas filas (no muta): la recuperación de cómputo de
--   un run concreto la hace _acquire (reclaim-antes-de-recomputar) al re-invocar
--   run_conversational_turn. running/failed salen del turn_runs_reclaimable_idx;
--   el ramal pending es un scan acotado por estado (los pending viejos son raros).
CREATE FUNCTION convo.list_reclaimable_runs(
    p_max_attempts       INTEGER DEFAULT 5,
    p_pending_age_seconds INTEGER DEFAULT 600
)
RETURNS SETOF JSONB
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
    SELECT jsonb_build_object(
        'turn_run_id', tr.id,
        'compute_status', tr.compute_status,
        'attempt_no', tr.attempt_no
    )
      FROM convo.turn_runs AS tr
     WHERE tr.attempt_no < p_max_attempts
       AND (
           tr.compute_status = 'failed'
           OR (tr.compute_status = 'running'
               AND (tr.lease_expires_at IS NULL OR tr.lease_expires_at < now()))
           OR (tr.compute_status = 'pending'
               AND tr.created_at
                   < now() - make_interval(secs => p_pending_age_seconds))
       )
     ORDER BY tr.id;
$function$;

-- ----------------------------------------------------------------------------
-- READ (2) convo.list_deliverable_outbox — outbox entregable (poller)
-- ----------------------------------------------------------------------------
-- CONTRATO DE LECTURA:
--   DEVUELVE (SETOF jsonb, hasta p_limit filas): cada outbox 'pending'/'retryable'
--     cuyo next_attempt_at ya venció (NULL = inmediato). Incluye el PAYLOAD
--     COMPLETO (payload_text/payload/destino/canal): el envío ocurre FUERA del
--     store, así que el poller debe llevarse el contenido consigo. Orden del
--     partial index delivery_outbox_pending_idx: next_attempt_at NULLS FIRST, id.
CREATE FUNCTION convo.list_deliverable_outbox(
    p_limit INTEGER DEFAULT 200
)
RETURNS SETOF JSONB
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
    SELECT jsonb_build_object(
        'outbox_id', ob.id,
        'turn_run_id', ob.turn_run_id,
        'conversation_id', ob.conversation_id,
        'channel', ob.channel,
        'destination', ob.destination,
        'logical_delivery_key', ob.logical_delivery_key,
        'payload_text', ob.payload_text,
        'payload', ob.payload,
        'delivery_status', ob.delivery_status,
        'attempt_count', ob.attempt_count,
        'next_attempt_at', ob.next_attempt_at
    )
      FROM convo.delivery_outbox AS ob
     WHERE ob.delivery_status IN ('pending', 'retryable')
       AND (ob.next_attempt_at IS NULL OR ob.next_attempt_at <= now())
     ORDER BY ob.next_attempt_at ASC NULLS FIRST, ob.id
     LIMIT p_limit;
$function$;

-- ----------------------------------------------------------------------------
-- READ (3) convo.list_stuck_sending — outbox atascado en 'sending' (janitor)
-- ----------------------------------------------------------------------------
-- CONTRATO DE LECTURA:
--   DEVUELVE (SETOF jsonb, uno por fila): {outbox_id, attempt_no} de cada outbox
--     'sending' cuyo lease (next_attempt_at) venció — el sender murió (o se
--     estancó) entre begin_delivery y record_delivery. attempt_no es el intento
--     abierto (delivery_outbox.attempt_count) que record_delivery debe sellar con
--     error_class='sending_lease_expired'. Sale del delivery_outbox_sending_stale_idx.
CREATE FUNCTION convo.list_stuck_sending()
RETURNS SETOF JSONB
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
    SELECT jsonb_build_object(
        'outbox_id', ob.id,
        'attempt_no', ob.attempt_count
    )
      FROM convo.delivery_outbox AS ob
     WHERE ob.delivery_status = 'sending'
       AND ob.next_attempt_at IS NOT NULL
       AND ob.next_attempt_at < now()
     ORDER BY ob.id;
$function$;

-- ----------------------------------------------------------------------------
-- Grants: REVOKE por defecto; EXECUTE SOLO a convo_rpc. Comentario-contrato/fn.
-- ----------------------------------------------------------------------------
DO $grants$
DECLARE
    fn TEXT;
    fns TEXT[] := ARRAY[
        'convo.list_reclaimable_runs(integer,integer)',
        'convo.list_deliverable_outbox(integer)',
        'convo.list_stuck_sending()'
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

COMMENT ON FUNCTION convo.list_reclaimable_runs(integer,integer) IS
    'S281 read: orphan compute candidates the janitor REPORTS (never reclaims) — '
    'expired-lease running, failed, and pending older than p_pending_age_seconds. '
    'Bounded by p_max_attempts. Read-only, one txn.';
COMMENT ON FUNCTION convo.list_deliverable_outbox(integer) IS
    'S281 read: due pending/retryable outbox rows WITH full payload for the poller '
    '(send happens outside the store). Order next_attempt_at NULLS FIRST, id.';
COMMENT ON FUNCTION convo.list_stuck_sending() IS
    'S281 read: outbox stuck in sending with an expired lease (sender died/stalled '
    'between begin and record); {outbox_id, attempt_no} for the janitor to seal.';

NOTIFY pgrst, 'reload schema';
