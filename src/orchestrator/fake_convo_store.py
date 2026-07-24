"""In-memory ``convo`` store that is FAITHFUL to the RPC contract (S281 / MT-0c).

This is the synthetic double on which the whole effectively-once suite runs
(RGPD: no real conversational data in Phase 0). It reproduces, at the bit, the
behaviour of ``20260723100001_s281_convo_rpcs_f0.sql``:

  * dedup uniques: ``(channel, external_update_id)`` on events, ``input_event_id``
    on runs, the logical outbox key, ``(outbox_id, attempt_no)`` on attempts;
  * the ``turn_runs`` state machine with monotonic ``fencing_token`` and the
    owner CAS (``lease_owner`` + ``fencing_token``) on complete/fail;
  * the reclaim eligibility + its exact ``reason`` CASE order (terminal >
    pending > attempt_budget_exhausted > lease_still_live);
  * the two-phase outbox (begin -> send outside -> record) with idempotent ack
    (``attempt_already_sealed``) and retryable/dead_letter budgeting;
  * the ``sending`` lease (``next_attempt_at``) the janitor uses.

An injectable ``ManualClock`` drives every timestamp so leases expire without
sleeps. Timestamps are returned as ISO-8601 strings, matching how PostgREST
serialises a ``timestamptz`` inside ``jsonb_build_object``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .convo_store import (
    DEFAULT_LEASE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_PENDING_ORPHAN_SECONDS,
    DEFAULT_RETRY_SECONDS,
    BeginDeliveryResult,
    ClaimResult,
    CompleteResult,
    FailResult,
    HeartbeatResult,
    IngressResult,
    OutboxRecord,
    ReclaimCandidate,
    ReclaimResult,
    RecordDeliveryResult,
    StuckSending,
)

# CHECK-constraint vocabularies (schema tables 2 & 4/5/6). Violations raise, as
# the SQL constraint would (rollback of the ingress transaction).
_ROLES = frozenset({"user", "assistant", "tool", "system"})
_EVENT_TYPES = frozenset({"message", "tool_call", "tool_result", "run_state", "delivery"})


class ManualClock:
    """Deterministic clock: ``now()`` is frozen until ``advance``/``set``."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def set(self, when: datetime) -> None:
        self._now = when


def _iso(when: datetime | None) -> str | None:
    return when.isoformat() if when is not None else None


@dataclass
class _Conversation:
    id: int
    public_id: str
    channel: str
    external_chat_id: str
    tenant_id: str | None
    state_version: int = 0
    last_event_id: int | None = None
    status: str = "active"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class _Event:
    id: int
    conversation_id: int
    channel: str
    external_update_id: str
    role: str
    event_type: str
    content_text: str | None
    payload: dict[str, Any]
    created_at: datetime | None = None


@dataclass
class _Run:
    id: int
    conversation_id: int
    input_event_id: int
    attempt_no: int = 1
    compute_status: str = "pending"
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    fencing_token: int = 0
    heartbeat_at: datetime | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    answered_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    error_class: str | None = None
    error_detail: str | None = None


@dataclass
class _Outbox:
    id: int
    turn_run_id: int
    conversation_id: int
    channel: str
    destination: str
    logical_delivery_key: str
    payload_text: str
    payload: dict[str, Any]
    max_attempts: int
    delivery_status: str = "pending"
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    external_receipt: str | None = None
    delivered_at: datetime | None = None


@dataclass
class _Attempt:
    id: int
    outbox_id: int
    attempt_no: int
    attempt_status: str
    external_receipt: str | None = None
    error_class: str | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class FakeConvoStore:
    """Contract-faithful in-memory ``ConvoStore`` + ``ConvoScanner``."""

    def __init__(self, clock: ManualClock | None = None) -> None:
        self.clock = clock or ManualClock()
        self._conversations: dict[tuple[str, str], _Conversation] = {}
        self._conv_by_id: dict[int, _Conversation] = {}
        self._events: dict[int, _Event] = {}
        self._event_by_update: dict[tuple[str, str], int] = {}
        self._runs: dict[int, _Run] = {}
        self._run_by_input_event: dict[int, int] = {}
        self._outbox: dict[int, _Outbox] = {}
        self._outbox_by_logical: dict[tuple[int, str, str, str], int] = {}
        self._attempts: dict[int, _Attempt] = {}
        self._attempt_by_key: dict[tuple[int, int], int] = {}
        self._seq = {"conv": 0, "event": 0, "run": 0, "outbox": 0, "attempt": 0}

    def _next(self, name: str) -> int:
        self._seq[name] += 1
        return self._seq[name]

    # -- RPC (1) ingress ------------------------------------------------------
    def ingress(
        self,
        *,
        channel: str,
        external_update_id: str,
        external_chat_id: str,
        role: str = "user",
        event_type: str = "message",
        content_text: str | None = None,
        payload: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> IngressResult:
        # CHECK constraints validated FIRST: a violation rolls back the whole
        # transaction, so no conversation is created on a bad role/event_type.
        if not channel:
            raise ValueError("ingress: channel must be non-empty")
        if not external_chat_id:
            raise ValueError("ingress: external_chat_id must be non-empty")
        if role not in _ROLES:
            raise ValueError(f"ingress: illegal role {role!r}")
        if event_type not in _EVENT_TYPES:
            raise ValueError(f"ingress: illegal event_type {event_type!r}")

        now = self.clock.now()
        conv_key = (channel, external_chat_id)
        conv = self._conversations.get(conv_key)
        if conv is None:
            conv = _Conversation(
                id=self._next("conv"),
                public_id=str(uuid.uuid4()),
                channel=channel,
                external_chat_id=external_chat_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
            self._conversations[conv_key] = conv
            self._conv_by_id[conv.id] = conv
            conv_is_new = True
        else:
            conv.updated_at = now  # upsert DO UPDATE SET updated_at = now()
            conv_is_new = False

        event_key = (channel, external_update_id)
        existing_event_id = self._event_by_update.get(event_key)
        if existing_event_id is not None:
            # Duplicate ingress: recover the already-registered state, advance
            # nothing (idempotent). conversation_id comes from the stored event.
            ev = self._events[existing_event_id]
            conv_row = self._conv_by_id[ev.conversation_id]
            return IngressResult(
                conversation_id=ev.conversation_id,
                public_id=conv_row.public_id,
                event_id=existing_event_id,
                turn_run_id=self._run_by_input_event.get(existing_event_id),
                is_new_event=False,
                is_new_conversation=False,
                state_version=conv_row.state_version,
            )

        event_id = self._next("event")
        self._events[event_id] = _Event(
            id=event_id,
            conversation_id=conv.id,
            channel=channel,
            external_update_id=external_update_id,
            role=role,
            event_type=event_type,
            content_text=content_text,
            payload=dict(payload) if payload is not None else {},
            created_at=now,
        )
        self._event_by_update[event_key] = event_id

        # New event: advance the per-conversation CAS + last-event pointer.
        conv.state_version += 1
        conv.last_event_id = event_id
        conv.updated_at = now

        turn_run_id: int | None = None
        if role == "user":
            turn_run_id = self._run_by_input_event.get(event_id)
            if turn_run_id is None:
                turn_run_id = self._next("run")
                self._runs[turn_run_id] = _Run(
                    id=turn_run_id,
                    conversation_id=conv.id,
                    input_event_id=event_id,
                    created_at=now,
                )
                self._run_by_input_event[event_id] = turn_run_id

        return IngressResult(
            conversation_id=conv.id,
            public_id=conv.public_id,
            event_id=event_id,
            turn_run_id=turn_run_id,
            is_new_event=True,
            is_new_conversation=conv_is_new,
            state_version=conv.state_version,
        )

    # -- RPC (2a) claim_run ---------------------------------------------------
    def claim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> ClaimResult:
        if lease_seconds <= 0:
            raise ValueError("claim_run: lease_seconds must be positive")
        if not lease_owner:
            raise ValueError("claim_run: lease_owner must be non-empty")

        now = self.clock.now()
        run = self._runs.get(turn_run_id)
        if run is not None and run.compute_status == "pending":
            run.compute_status = "running"
            run.lease_owner = lease_owner
            run.lease_expires_at = now + timedelta(seconds=lease_seconds)
            run.fencing_token += 1
            run.heartbeat_at = now
            if run.started_at is None:
                run.started_at = now
            return ClaimResult(
                claimed=True,
                fencing_token=run.fencing_token,
                attempt_no=run.attempt_no,
                compute_status="running",
                lease_expires_at=_iso(run.lease_expires_at),
                reason="claimed",
            )

        status = run.compute_status if run is not None else None
        return ClaimResult(
            claimed=False,
            fencing_token=None,
            attempt_no=None,
            compute_status=status,
            lease_expires_at=None,
            reason="run_not_found" if status is None else "not_pending",
        )

    # -- RPC (2b) heartbeat_run ----------------------------------------------
    def heartbeat_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> HeartbeatResult:
        if lease_seconds <= 0:
            raise ValueError("heartbeat_run: lease_seconds must be positive")

        now = self.clock.now()
        run = self._runs.get(turn_run_id)
        found = (
            run is not None
            and run.compute_status == "running"
            and run.lease_owner == lease_owner
            and run.fencing_token == fencing_token
        )
        if found:
            assert run is not None
            run.lease_expires_at = now + timedelta(seconds=lease_seconds)
            run.heartbeat_at = now
            return HeartbeatResult(
                extended=True,
                lease_expires_at=_iso(run.lease_expires_at),
                reason="extended",
            )
        return HeartbeatResult(
            extended=False, lease_expires_at=None, reason="stale_or_not_running"
        )

    # -- RPC (2c) reclaim_run -------------------------------------------------
    def reclaim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> ReclaimResult:
        if lease_seconds <= 0:
            raise ValueError("reclaim_run: lease_seconds must be positive")
        if not lease_owner:
            raise ValueError("reclaim_run: lease_owner must be non-empty")

        now = self.clock.now()
        run = self._runs.get(turn_run_id)
        if run is None:
            return ReclaimResult(
                reclaimed=False,
                fencing_token=None,
                attempt_no=None,
                lease_expires_at=None,
                previous_owner=None,
                reason="run_not_found",
            )

        prev_owner = run.lease_owner
        status = run.compute_status
        attempt = run.attempt_no
        lease_expired = run.lease_expires_at is None or run.lease_expires_at < now
        eligible = attempt < max_attempts and (
            (status == "running" and lease_expired) or status == "failed"
        )
        if eligible:
            run.compute_status = "running"
            run.lease_owner = lease_owner
            run.lease_expires_at = now + timedelta(seconds=lease_seconds)
            run.fencing_token += 1
            run.attempt_no += 1
            run.heartbeat_at = now
            if run.started_at is None:
                run.started_at = now
            return ReclaimResult(
                reclaimed=True,
                fencing_token=run.fencing_token,
                attempt_no=run.attempt_no,
                lease_expires_at=_iso(run.lease_expires_at),
                previous_owner=prev_owner,
                reason="reclaimed",
            )

        # Terminal states FIRST (so a delivered run with a high attempt_no is not
        # mislabelled attempt_budget_exhausted). Exact CASE order of the SQL.
        if status in ("answer_ready", "delivered"):
            reason = "not_reclaimable"
        elif status == "pending":
            reason = "use_claim_run"
        elif attempt >= max_attempts:
            reason = "attempt_budget_exhausted"
        elif status == "running":
            reason = "lease_still_live"
        else:
            reason = "not_reclaimable"
        return ReclaimResult(
            reclaimed=False,
            fencing_token=None,
            attempt_no=attempt,
            lease_expires_at=None,
            previous_owner=prev_owner,
            reason=reason,
        )

    # -- RPC (3) complete_run -------------------------------------------------
    def complete_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        channel: str,
        destination: str,
        logical_delivery_key: str,
        answer_text: str,
        answer_payload: dict[str, Any] | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> CompleteResult:
        # Validate-first (same pattern as ``ingress``): in PG the outbox INSERT
        # carries CHECK ``delivery_outbox_max_attempts_positive`` (max_attempts>=1);
        # a violation rolls back the WHOLE transaction — the run never reaches
        # answer_ready and no outbox is created. Raising BEFORE mutating anything
        # reproduces that rollback instead of certifying a phantom answer_ready.
        if max_attempts < 1:
            raise ValueError(
                f"complete_run: max_attempts must be >= 1 (got {max_attempts}); "
                "delivery_outbox_max_attempts_positive would roll back the txn"
            )
        now = self.clock.now()
        run = self._runs.get(turn_run_id)
        cas_ok = (
            run is not None
            and run.compute_status == "running"
            and run.lease_owner == lease_owner
            and run.fencing_token == fencing_token
        )
        if not cas_ok:
            status = run.compute_status if run is not None else None
            return CompleteResult(
                completed=False,
                outbox_id=None,
                compute_status=status,
                reason="run_not_found" if status is None else "stale_claim",
            )

        assert run is not None
        run.compute_status = "answer_ready"
        run.answered_at = now
        run.tokens_input = tokens_input
        run.tokens_output = tokens_output
        run.cost_usd = cost_usd
        run.latency_ms = latency_ms

        logical_key = (turn_run_id, channel, destination, logical_delivery_key)
        outbox_id = self._outbox_by_logical.get(logical_key)
        if outbox_id is None:
            outbox_id = self._next("outbox")
            self._outbox[outbox_id] = _Outbox(
                id=outbox_id,
                turn_run_id=turn_run_id,
                conversation_id=run.conversation_id,
                channel=channel,
                destination=destination,
                logical_delivery_key=logical_delivery_key,
                payload_text=answer_text,
                payload=dict(answer_payload) if answer_payload is not None else {},
                max_attempts=max_attempts,
            )
            self._outbox_by_logical[logical_key] = outbox_id

        return CompleteResult(
            completed=True,
            outbox_id=outbox_id,
            compute_status="answer_ready",
            reason="completed",
        )

    # -- RPC (6) fail_run -----------------------------------------------------
    def fail_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        error_class: str | None = None,
        error_detail: str | None = None,
    ) -> FailResult:
        now = self.clock.now()
        run = self._runs.get(turn_run_id)
        cas_ok = (
            run is not None
            and run.compute_status == "running"
            and run.lease_owner == lease_owner
            and run.fencing_token == fencing_token
        )
        if cas_ok:
            assert run is not None
            run.compute_status = "failed"
            run.failed_at = now
            run.error_class = error_class
            run.error_detail = error_detail
            return FailResult(failed=True, compute_status="failed", reason="failed")

        status = run.compute_status if run is not None else None
        return FailResult(
            failed=False,
            compute_status=status,
            reason="run_not_found" if status is None else "stale_claim",
        )

    # -- RPC (5a) begin_delivery ---------------------------------------------
    def begin_delivery(
        self,
        *,
        outbox_id: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> BeginDeliveryResult:
        now = self.clock.now()
        ob = self._outbox.get(outbox_id)
        if ob is None or ob.delivery_status not in ("pending", "retryable"):
            status = ob.delivery_status if ob is not None else None
            return BeginDeliveryResult(
                started=False,
                outbox_id=outbox_id,
                attempt_no=None,
                reason="outbox_not_found" if status is None else "not_claimable",
            )

        ob.delivery_status = "sending"
        ob.attempt_count += 1
        ob.next_attempt_at = now + timedelta(seconds=lease_seconds)
        attempt_no = ob.attempt_count

        attempt_id = self._next("attempt")
        self._attempts[attempt_id] = _Attempt(
            id=attempt_id,
            outbox_id=outbox_id,
            attempt_no=attempt_no,
            attempt_status="sending",
            started_at=now,
        )
        self._attempt_by_key[(outbox_id, attempt_no)] = attempt_id

        return BeginDeliveryResult(
            started=True, outbox_id=outbox_id, attempt_no=attempt_no, reason="sending"
        )

    # -- RPC (5b) record_delivery --------------------------------------------
    def record_delivery(
        self,
        *,
        outbox_id: int,
        attempt_no: int,
        success: bool,
        external_receipt: str | None = None,
        error_class: str | None = None,
        error_detail: str | None = None,
        retry_seconds: int = DEFAULT_RETRY_SECONDS,
    ) -> RecordDeliveryResult:
        now = self.clock.now()
        attempt_id = self._attempt_by_key.get((outbox_id, attempt_no))
        attempt = self._attempts.get(attempt_id) if attempt_id is not None else None

        if attempt is None:
            return RecordDeliveryResult(
                acknowledged=False,
                delivery_status=None,
                turn_delivered=False,
                reason="attempt_not_found",
            )
        if attempt.attempt_status != "sending":
            # Second ack over a sealed attempt does NOT re-stamp receipt/status.
            return RecordDeliveryResult(
                acknowledged=False,
                delivery_status=None,
                turn_delivered=False,
                reason="attempt_already_sealed",
            )

        attempt.attempt_status = "succeeded" if success else "failed"
        attempt.external_receipt = external_receipt
        attempt.error_class = error_class
        attempt.error_detail = error_detail
        attempt.finished_at = now

        ob = self._outbox[outbox_id]
        turn_delivered = False
        if success:
            if ob.delivery_status != "delivered":
                ob.delivery_status = "delivered"
                ob.external_receipt = external_receipt
                ob.delivered_at = now
            new_status = "delivered"
            run = self._runs.get(ob.turn_run_id)
            if run is not None and run.compute_status == "answer_ready":
                run.compute_status = "delivered"
                if run.delivered_at is None:
                    run.delivered_at = now
                turn_delivered = True
        elif ob.attempt_count >= ob.max_attempts:
            new_status = "dead_letter"
            ob.delivery_status = "dead_letter"
        else:
            new_status = "retryable"
            ob.delivery_status = "retryable"
            ob.next_attempt_at = now + timedelta(seconds=retry_seconds)

        return RecordDeliveryResult(
            acknowledged=True,
            delivery_status=new_status,
            turn_delivered=turn_delivered,
            reason="delivered" if success else new_status,
        )

    # -- scanner (deferred read surface; maps to the partial indexes) ---------
    def find_reclaimable_runs(
        self,
        *,
        now: datetime,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        pending_age_seconds: int = DEFAULT_PENDING_ORPHAN_SECONDS,
    ) -> list[ReclaimCandidate]:
        """Orphan candidates the janitor surfaces (it reports; never mutates).

        Three shapes: ``failed``, expired-lease ``running`` (both from the
        ``turn_runs_reclaimable_idx`` partial index), and ``pending`` runs older
        than ``pending_age_seconds`` — a frontier-1 crash (worker died between
        ingress and claim) that the running/failed index alone cannot see.
        """
        out: list[ReclaimCandidate] = []
        for run in self._runs.values():
            if run.attempt_no >= max_attempts:
                continue
            lease_expired = run.lease_expires_at is None or run.lease_expires_at < now
            if run.compute_status == "failed" or (
                run.compute_status == "running" and lease_expired
            ):
                is_orphan = True
            elif run.compute_status == "pending":
                is_orphan = run.created_at is not None and (
                    run.created_at + timedelta(seconds=pending_age_seconds) < now
                )
            else:
                is_orphan = False
            if is_orphan:
                out.append(
                    ReclaimCandidate(
                        turn_run_id=run.id,
                        compute_status=run.compute_status,
                        attempt_no=run.attempt_no,
                    )
                )
        out.sort(key=lambda c: c.turn_run_id)
        return out

    def find_deliverable_outbox(self, *, now: datetime) -> list[OutboxRecord]:
        out: list[_Outbox] = [
            ob
            for ob in self._outbox.values()
            if ob.delivery_status in ("pending", "retryable")
            and (ob.next_attempt_at is None or ob.next_attempt_at <= now)
        ]
        # Partial index order: next_attempt_at NULLS FIRST, id.
        out.sort(key=lambda ob: (ob.next_attempt_at is not None, ob.next_attempt_at or now, ob.id))
        return [self._to_record(ob) for ob in out]

    def find_stuck_sending(self, *, now: datetime) -> list[StuckSending]:
        out = [
            StuckSending(outbox_id=ob.id, attempt_no=ob.attempt_count)
            for ob in self._outbox.values()
            if ob.delivery_status == "sending"
            and ob.next_attempt_at is not None
            and ob.next_attempt_at < now
        ]
        out.sort(key=lambda s: s.outbox_id)
        return out

    def _to_record(self, ob: _Outbox) -> OutboxRecord:
        return OutboxRecord(
            outbox_id=ob.id,
            turn_run_id=ob.turn_run_id,
            conversation_id=ob.conversation_id,
            channel=ob.channel,
            destination=ob.destination,
            logical_delivery_key=ob.logical_delivery_key,
            payload_text=ob.payload_text,
            payload=dict(ob.payload),
            delivery_status=ob.delivery_status,
            attempt_count=ob.attempt_count,
            next_attempt_at=ob.next_attempt_at,
        )

    # -- read helpers for assertions (not part of the RPC contract) -----------
    def run_status(self, turn_run_id: int) -> str | None:
        run = self._runs.get(turn_run_id)
        return run.compute_status if run is not None else None

    def outbox_status(self, outbox_id: int) -> str | None:
        ob = self._outbox.get(outbox_id)
        return ob.delivery_status if ob is not None else None
