"""Effectively-once turn driver + recovery janitor (S281 / MT-0c).

Composes the MT-0a compute (``run_turn``) with the ``convo`` effectively-once
RPCs so a single conversational turn is idempotent under crashes at every
boundary. Transport-neutral: the ``sender`` (Telegram in MT-0d) is injected, and
the LLM/network send ALWAYS happens OUTSIDE every store transaction.

--------------------------------------------------------------------------------
LEASE SIZING + HEARTBEAT (declared MT-0d/F1 dependency)
--------------------------------------------------------------------------------
Two leases, dimensioned to their phase (not the single 60s knob): compute uses
``COMPUTE_LEASE_SECONDS`` (sized to the p99 of a slow turn — LLM retries), and
delivery uses ``SENDING_LEASE_SECONDS``. ``convo.heartbeat_run`` EXISTS but the
Phase-0 driver does not yet call it during compute; wiring a heartbeat loop is a
declared MT-0d/F1 dependency. Until then the oversized compute lease — not a
heartbeat — is what keeps a live-but-slow worker from being fenced mid-flight;
fencing only ever prevents PUBLISHING a stale answer, never double COMPUTE.

--------------------------------------------------------------------------------
AT-LEAST-ONCE WINDOW (declared, not disguised)
--------------------------------------------------------------------------------
Egress cannot be exactly-once in Phase 0. The user can receive the answer TWICE
in two ways, both because there is NO fencing of delivery (impossible without a
provider-side idempotency key, which Telegram ``sendMessage`` does not offer):
  1. crash post-send: the process dies AFTER the Telegram HTTP send returns but
     BEFORE ``record_delivery`` commits — the outbox row stays ``sending``;
  2. sender alive-but-slow: the send outlives ``SENDING_LEASE_SECONDS``, the
     janitor seals the row ``retryable`` and the poller re-sends while the
     original HTTP request can still land.
The janitor cannot tell either case from a clean crash-before-send, so it seals
``sending`` -> ``retryable`` and the poller re-sends. The transactional outbox
MINIMISES this window (exactly one send, only on a stall/crash inside it); it
does not eliminate it.

--------------------------------------------------------------------------------
FRONTIER RECOVERY IN PRODUCTION (declared MT-0d dependency)
--------------------------------------------------------------------------------
Frontiers 3-5 (post-complete) recover autonomously via the outbox poller +
janitor once those are SCHEDULED (MT-0d). Frontiers 1-2 (a crash after ingress /
after claim, before an answer persists) DEPEND on a real actor re-driving the
turn: python-telegram-bot confirms the update offset at FETCH, so after a crash
Telegram will NOT redeliver the update — recovery needs either a manual offset
replay or a recompute driven by the janitor/scheduler that reclaims-before-
recomputing. The fake surfaces those orphans (``find_reclaimable_runs`` now
includes aged ``pending`` runs); the actor that acts on them is MT-0d. No
boundary "just recovers" without that transport wiring.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .contracts import TurnRequest, TurnResult
from .convo_store import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_PENDING_ORPHAN_SECONDS,
    DEFAULT_RETRY_SECONDS,
    ConvoStore,
    ConvoStoreWithScan,
    OutboxRecord,
    RecordDeliveryResult,
)
from .orchestrator import run_turn

# One bot answer per user turn; the turn_run_id already scopes the outbox unique.
LOGICAL_DELIVERY_KEY = "answer"

# Compute lease: sized to the p99 of a slow turn (LLM retries), NOT the 60s SQL
# default. Used by ``_acquire`` for both the clean claim and the reclaim-before-
# recompute of compute. Heartbeat wiring that would let a shorter lease survive a
# slow turn is a declared MT-0d/F1 dependency (see module docstring).
COMPUTE_LEASE_SECONDS = 600
# Delivery (sending) lease: the window ``begin_delivery`` holds the outbox before
# ``record_delivery`` seals it. Wider than the SQL default to make the
# alive-but-slow duplicate rare; it cannot be eliminated (no delivery fencing).
SENDING_LEASE_SECONDS = 180


@dataclass(frozen=True, kw_only=True)
class DeliveryPayload:
    """What the injected ``sender`` receives. It uses ``destination`` + ``text``."""

    channel: str
    destination: str
    text: str
    payload: dict[str, Any]
    outbox_id: int
    attempt_no: int
    logical_delivery_key: str
    turn_run_id: int
    conversation_id: int


# The sender returns an external receipt (e.g. Telegram message_id) on success.
# A clean send failure (network 5xx) raises Exception -> recorded as a failed
# attempt (outbox -> retryable/dead_letter). A hard crash is modelled as a
# BaseException that propagates WITHOUT record_delivery (-> stuck 'sending').
Sender = Callable[[DeliveryPayload], str]


@dataclass(frozen=True, kw_only=True)
class DeliveryOutcome:
    delivered: bool
    started: bool
    reason: str
    outbox_id: int
    attempt_no: int | None = None
    receipt: str | None = None
    ack: RecordDeliveryResult | None = None


@dataclass(frozen=True, kw_only=True)
class TurnOutcome:
    """Result of one ``run_conversational_turn`` invocation.

    ``status`` values:
      * ``delivered``          — computed this call and delivered.
      * ``send_failed``        — computed this call; a delivery attempt ACTUALLY
                                 RAN (``begin_delivery`` won) and the send failed
                                 (outbox -> retryable/dead_letter).
      * ``delivery_race``      — computed this call, but ``begin_delivery`` lost
                                 the race: the outbox was already claimed
                                 (``not_claimable``) by a concurrent poller, so NO
                                 attempt ran here. Not a failure — the other actor
                                 owns the send. (Distinct from ``send_failed``,
                                 which means an attempt ran and failed.)
      * ``already_delivered``  — dedup: the run was already delivered (no resend).
      * ``awaiting_delivery``  — computed by a prior (crashed) call; the poller
                                 will deliver its pending outbox.
      * ``abandoned_stale``    — reclaimed away mid-compute; the reclaimer answers.
      * ``claim_lost``         — another worker holds a live lease.
      * ``not_runnable``       — reclaim refused (budget exhausted / not found).
    """

    status: str
    turn_run_id: int | None
    conversation_id: int | None
    outbox_id: int | None = None
    delivered: bool = False
    receipt: str | None = None
    is_new_event: bool = True
    state_version: int | None = None
    result: TurnResult | None = None


@dataclass(frozen=True, kw_only=True)
class RepairSummary:
    """What one janitor sweep observed. ``orphaned_runs`` are REPORTED, never
    mutated (each dict: turn_run_id / compute_status / attempt_no); only stuck
    ``sending`` rows are sealed."""

    orphaned_runs: tuple[dict[str, Any], ...] = ()
    sealed_sending: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class _Acquisition:
    owned: bool
    fencing: int | None = None
    terminal_status: str | None = None


def _acquire(
    store: ConvoStore,
    turn_run_id: int,
    worker_id: str,
    lease_seconds: int,
    max_attempts: int,
) -> _Acquisition:
    """Claim a pending run, or take over an expired-lease/failed one (reclaim).

    Returns ownership + fencing, or a terminal status for callers that must not
    compute (already delivered, awaiting delivery, another live owner, ...).
    """
    claim = store.claim_run(
        turn_run_id=turn_run_id, lease_owner=worker_id, lease_seconds=lease_seconds
    )
    if claim["claimed"]:
        return _Acquisition(owned=True, fencing=claim["fencing_token"])

    status = claim["compute_status"]
    if status == "delivered":
        return _Acquisition(owned=False, terminal_status="already_delivered")
    if status == "answer_ready":
        return _Acquisition(owned=False, terminal_status="awaiting_delivery")

    # running (maybe stale) or failed -> attempt to take over.
    rec = store.reclaim_run(
        turn_run_id=turn_run_id,
        lease_owner=worker_id,
        lease_seconds=lease_seconds,
        max_attempts=max_attempts,
    )
    if rec["reclaimed"]:
        return _Acquisition(owned=True, fencing=rec["fencing_token"])

    reason = rec["reason"]
    if reason == "lease_still_live":
        return _Acquisition(owned=False, terminal_status="claim_lost")
    if reason == "not_reclaimable":
        # Raced into answer_ready/delivered between our claim and reclaim; the
        # poller resolves it (a delivered run simply won't be in its scan).
        return _Acquisition(owned=False, terminal_status="awaiting_delivery")
    # attempt_budget_exhausted / use_claim_run / run_not_found.
    return _Acquisition(owned=False, terminal_status="not_runnable")


def deliver_outbox(
    store: ConvoStore,
    record: OutboxRecord,
    sender: Sender,
    *,
    lease_seconds: int = SENDING_LEASE_SECONDS,
    retry_seconds: int = DEFAULT_RETRY_SECONDS,
) -> DeliveryOutcome:
    """One delivery attempt: begin_delivery -> send (OUTSIDE the store) -> record.

    The send is the ONLY step outside a store transaction. A clean send failure
    is recorded (outbox -> retryable/dead_letter); a hard crash (BaseException)
    propagates without a record, leaving the row ``sending`` for the janitor.
    """
    begin = store.begin_delivery(outbox_id=record.outbox_id, lease_seconds=lease_seconds)
    if not begin["started"]:
        # Already sending/delivered/dead_letter, or gone: nothing to do here.
        return DeliveryOutcome(
            delivered=False,
            started=False,
            reason=begin["reason"],
            outbox_id=record.outbox_id,
        )

    attempt_no = begin["attempt_no"]
    assert attempt_no is not None
    payload = DeliveryPayload(
        channel=record.channel,
        destination=record.destination,
        text=record.payload_text,
        payload=record.payload,
        outbox_id=record.outbox_id,
        attempt_no=attempt_no,
        logical_delivery_key=record.logical_delivery_key,
        turn_run_id=record.turn_run_id,
        conversation_id=record.conversation_id,
    )

    # --- SEND: outside every store transaction (the at-least-once window) ---
    try:
        receipt = sender(payload)
    except Exception as exc:  # clean send failure -> record it, outbox retryable
        ack = store.record_delivery(
            outbox_id=record.outbox_id,
            attempt_no=attempt_no,
            success=False,
            error_class=type(exc).__name__,
            error_detail=str(exc)[:2000],
            retry_seconds=retry_seconds,
        )
        return DeliveryOutcome(
            delivered=False,
            started=True,
            reason="send_failed",
            outbox_id=record.outbox_id,
            attempt_no=attempt_no,
            ack=ack,
        )

    ack = store.record_delivery(
        outbox_id=record.outbox_id,
        attempt_no=attempt_no,
        success=True,
        external_receipt=receipt,
    )
    delivered = ack["delivery_status"] == "delivered"
    return DeliveryOutcome(
        delivered=delivered,
        started=True,
        reason=ack["reason"],
        outbox_id=record.outbox_id,
        attempt_no=attempt_no,
        receipt=receipt,
        ack=ack,
    )


def run_conversational_turn(
    store: ConvoStore,
    request: TurnRequest,
    adapters: Any,
    worker_id: str,
    sender: Sender,
    *,
    compute_lease_seconds: int = COMPUTE_LEASE_SECONDS,
    sending_lease_seconds: int = SENDING_LEASE_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_seconds: int = DEFAULT_RETRY_SECONDS,
) -> TurnOutcome:
    """Drive one turn effectively-once. Idempotent under re-invocation.

    ingress (dedup) -> claim/reclaim -> run_turn (MT-0a) -> complete_run (CAS +
    outbox, atomic) -> deliver_outbox (send outside the store) -> record_delivery.

    Duplicate policy: a re-delivered update whose run is already ``delivered`` is
    NOT recomputed nor resent; a run still ``pending``/``failed`` continues the
    cycle; a run ``answer_ready`` from a crashed prior call is left to the poller.
    A ``run_turn`` exception is recorded via ``fail_run`` and then RE-RAISED — the
    error reaches the transport boundary; it is never swallowed.
    """
    channel = request.channel
    external_update_id = request.external_update_id
    external_chat_id = request.conversation_id
    if external_update_id is None or external_chat_id is None:
        raise ValueError(
            "run_conversational_turn requires request.external_update_id and "
            "request.conversation_id (the effectively-once dedup + chat keys)"
        )

    ingress = store.ingress(
        channel=channel,
        external_update_id=external_update_id,
        external_chat_id=external_chat_id,
        role="user",
        event_type="message",
        content_text=request.query,
        payload={"source": request.source},
    )
    turn_run_id = ingress["turn_run_id"]
    conversation_id = ingress["conversation_id"]
    if turn_run_id is None:
        # role='user' always yields a run; guard keeps the type honest.
        raise RuntimeError("ingress did not create a turn_run for a user event")

    acq = _acquire(store, turn_run_id, worker_id, compute_lease_seconds, max_attempts)
    if not acq.owned:
        return TurnOutcome(
            status=acq.terminal_status or "not_runnable",
            turn_run_id=turn_run_id,
            conversation_id=conversation_id,
            delivered=acq.terminal_status == "already_delivered",
            is_new_event=ingress["is_new_event"],
            state_version=ingress["state_version"],
        )

    fencing = acq.fencing
    assert fencing is not None

    started = time.monotonic()
    try:
        result = run_turn(request, adapters)
    except Exception as exc:
        # Record the failure (enables retry via reclaim) then RE-RAISE.
        store.fail_run(
            turn_run_id=turn_run_id,
            lease_owner=worker_id,
            fencing_token=fencing,
            error_class=type(exc).__name__,
            error_detail=str(exc)[:2000],
        )
        raise
    latency_ms = int((time.monotonic() - started) * 1000)

    generation = result.generation or {}
    completion = store.complete_run(
        turn_run_id=turn_run_id,
        lease_owner=worker_id,
        fencing_token=fencing,
        channel=channel,
        destination=external_chat_id,
        logical_delivery_key=LOGICAL_DELIVERY_KEY,
        answer_text=result.answer,
        answer_payload={"diagrams": list(result.diagrams)},
        # The generator emits ``input_tokens``/``output_tokens`` (src/rag/
        # generator.py ~L829); map them to the store's tokens_input/tokens_output
        # (reading the old tokens_* keys always yielded NULL). latency is measured
        # HERE around run_turn (monotonic); cost_usd stays None — the generator
        # does not produce a cost figure.
        tokens_input=generation.get("input_tokens"),
        tokens_output=generation.get("output_tokens"),
        cost_usd=None,
        latency_ms=latency_ms,
        max_attempts=max_attempts,
    )
    if not completion["completed"]:
        # Reclaimed away mid-compute (stale_claim): abandon WITHOUT sending; the
        # new owner will produce and deliver the answer.
        return TurnOutcome(
            status="abandoned_stale",
            turn_run_id=turn_run_id,
            conversation_id=conversation_id,
            is_new_event=ingress["is_new_event"],
            state_version=ingress["state_version"],
            result=result,
        )

    outbox_id = completion["outbox_id"]
    assert outbox_id is not None
    record = OutboxRecord(
        outbox_id=outbox_id,
        turn_run_id=turn_run_id,
        conversation_id=conversation_id,
        channel=channel,
        destination=external_chat_id,
        logical_delivery_key=LOGICAL_DELIVERY_KEY,
        payload_text=result.answer,
        payload={"diagrams": list(result.diagrams)},
    )
    delivery = deliver_outbox(
        store, record, sender,
        lease_seconds=sending_lease_seconds, retry_seconds=retry_seconds,
    )
    # A delivery attempt only "failed" if it actually RAN. If begin_delivery lost
    # the race (started=False, e.g. a poller already claimed the outbox), that is
    # a delivery_race, not a send_failed (the loser recorded no attempt).
    if delivery.delivered:
        status = "delivered"
    elif delivery.started:
        status = "send_failed"
    else:
        status = "delivery_race"
    return TurnOutcome(
        status=status,
        turn_run_id=turn_run_id,
        conversation_id=conversation_id,
        outbox_id=outbox_id,
        delivered=delivery.delivered,
        receipt=delivery.receipt,
        is_new_event=ingress["is_new_event"],
        state_version=ingress["state_version"],
        result=result,
    )


def deliver_pending(
    store: ConvoStoreWithScan,
    sender: Sender,
    now: datetime,
    *,
    lease_seconds: int = SENDING_LEASE_SECONDS,
    retry_seconds: int = DEFAULT_RETRY_SECONDS,
) -> list[DeliveryOutcome]:
    """Outbox poller: deliver every due ``pending``/``retryable`` row.

    Recovers a crash between ``complete_run`` and the send (outbox left
    ``pending``), and re-sends rows the janitor sealed to ``retryable``.
    """
    outcomes: list[DeliveryOutcome] = []
    for record in store.find_deliverable_outbox(now=now):
        outcomes.append(
            deliver_outbox(
                store, record, sender, lease_seconds=lease_seconds, retry_seconds=retry_seconds
            )
        )
    return outcomes


def reclaim_and_repair(
    store: ConvoStoreWithScan,
    worker_id: str,
    now: datetime,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_seconds: int = DEFAULT_RETRY_SECONDS,
    pending_age_seconds: int = DEFAULT_PENDING_ORPHAN_SECONDS,
) -> RepairSummary:
    """Janitor: (i) REPORT orphaned runs (no mutation), (ii) seal stuck ``sending``.

    (i) The janitor does NOT reclaim runs. Reclaiming here was DANGEROUS: a run
    reclaimed but not recomputed burns its attempt budget on successive sweeps
    until it is running-expired AND budget-exhausted — invisible to the scan and
    irrecoverable, its live lease also blocking the only real re-invocation. The
    reclaim-before-recompute of compute lives SOLELY in ``_acquire`` (driven by a
    real re-invocation of ``run_conversational_turn``). This sweep only REPORTS
    orphans — expired-lease ``running``, ``failed``, and aged ``pending`` — in
    ``orphaned_runs`` (turn_run_id / compute_status / attempt_no), leaving
    ``attempt_no`` and ``fencing_token`` untouched. ``worker_id`` is retained as
    the janitor identity for the sealing below.

    (ii) Seals every ``sending`` row whose lease (``next_attempt_at``) has
    expired via ``record_delivery(success=false, 'sending_lease_expired')`` ->
    ``retryable``/``dead_letter``, so ``deliver_pending`` can re-send. This is the
    load-bearing recovery for a sender that died (or stalled) between begin and
    record. Scheduling this sweep + the poller is a declared MT-0d dependency.
    """
    orphaned: list[dict[str, Any]] = [
        {
            "turn_run_id": cand.turn_run_id,
            "compute_status": cand.compute_status,
            "attempt_no": cand.attempt_no,
        }
        for cand in store.find_reclaimable_runs(
            now=now, max_attempts=max_attempts, pending_age_seconds=pending_age_seconds
        )
    ]

    sealed: list[dict[str, Any]] = []
    for stuck in store.find_stuck_sending(now=now):
        ack = store.record_delivery(
            outbox_id=stuck.outbox_id,
            attempt_no=stuck.attempt_no,
            success=False,
            error_class="sending_lease_expired",
            error_detail="sender lease expired; sealed by janitor",
            retry_seconds=retry_seconds,
        )
        sealed.append(
            {
                "outbox_id": stuck.outbox_id,
                "attempt_no": stuck.attempt_no,
                "delivery_status": ack["delivery_status"],
                "reason": ack["reason"],
            }
        )

    return RepairSummary(orphaned_runs=tuple(orphaned), sealed_sending=tuple(sealed))
