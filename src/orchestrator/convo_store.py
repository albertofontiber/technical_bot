"""Client interface for the `convo` effectively-once RPCs (S281 / MT-0c).

The authority for every shape and reason string in this module is the RPC
proposal ``supabase/migration_proposals/20260723100001_s281_convo_rpcs_f0.sql``.
The Python return dicts carry the EXACT keys of each RPC's ``jsonb_build_object``;
the ``reason`` vocabularies are the SQL vocabularies verbatim. Any drift between
this file, ``fake_convo_store.py`` and that SQL is a bug.

Two protocols are declared:

  * ``ConvoStore`` — the 8 transactional RPCs (ingress, claim_run, heartbeat_run,
    reclaim_run, complete_run, fail_run, begin_delivery, record_delivery). These
    are the effectively-once mutating surface. ``PostgRESTConvoStore`` implements
    them over the same httpx->PostgREST stack the corpus retriever already uses,
    with ``Accept-Profile: convo`` / ``Content-Profile: convo``.
  * ``ConvoScanner`` — three READ operations the janitor (``lifecycle.py``) needs
    to discover recovery candidates: reclaimable runs, deliverable outbox rows,
    and stuck ``sending`` rows. They map to the schema's partial indexes
    (``turn_runs_reclaimable_idx``, ``delivery_outbox_pending_idx``,
    ``delivery_outbox_sending_stale_idx``). MT-0b delivered NO read/scan RPCs for
    these (its 8 RPCs are all mutating), so ``PostgRESTConvoStore`` cannot serve
    them today — they are a DECLARED deferred read surface. In Phase 0 the only
    ``ConvoScanner`` is ``FakeConvoStore`` (RGPD: synthetic-only testing).

``PostgRESTConvoStore`` is never exercised against the network in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypedDict

import httpx


# --- default lifecycle knobs (mirror the SQL DEFAULTs) -----------------------
DEFAULT_LEASE_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_RETRY_SECONDS = 60


# --- return shapes: EXACT keys of each RPC's jsonb_build_object ---------------
class IngressResult(TypedDict):
    conversation_id: int
    public_id: str
    event_id: int
    turn_run_id: int | None
    is_new_event: bool
    is_new_conversation: bool
    state_version: int


class ClaimResult(TypedDict):
    claimed: bool
    fencing_token: int | None
    attempt_no: int | None
    compute_status: str | None
    lease_expires_at: str | None
    reason: str


class HeartbeatResult(TypedDict):
    extended: bool
    lease_expires_at: str | None
    reason: str


class ReclaimResult(TypedDict):
    reclaimed: bool
    fencing_token: int | None
    attempt_no: int | None
    lease_expires_at: str | None
    previous_owner: str | None
    reason: str


class CompleteResult(TypedDict):
    completed: bool
    outbox_id: int | None
    compute_status: str | None
    reason: str


class FailResult(TypedDict):
    failed: bool
    compute_status: str | None
    reason: str


class BeginDeliveryResult(TypedDict):
    started: bool
    outbox_id: int
    attempt_no: int | None
    reason: str


class RecordDeliveryResult(TypedDict):
    acknowledged: bool
    delivery_status: str | None
    turn_delivered: bool
    reason: str


# --- scanner records (read surface for the janitor) --------------------------
@dataclass(frozen=True, kw_only=True)
class ReclaimCandidate:
    """A run the janitor may reclaim: expired-lease ``running`` or ``failed``."""

    turn_run_id: int
    compute_status: str
    attempt_no: int


@dataclass(frozen=True, kw_only=True)
class OutboxRecord:
    """A deliverable outbox row with the content the sender needs.

    Models what a ``list_deliverable_outbox`` read RPC would return: the send is
    performed OUTSIDE the store, so the poller must carry the payload with it.
    """

    outbox_id: int
    turn_run_id: int
    conversation_id: int
    channel: str
    destination: str
    logical_delivery_key: str
    payload_text: str
    payload: dict[str, Any] = field(default_factory=dict)
    delivery_status: str = "pending"
    attempt_count: int = 0
    next_attempt_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class StuckSending:
    """An outbox stuck in ``sending`` (sender died between begin and record).

    ``attempt_no`` is the open attempt (``delivery_outbox.attempt_count``) that
    ``record_delivery`` must seal with ``error_class='sending_lease_expired'``.
    """

    outbox_id: int
    attempt_no: int


class ConvoStore(Protocol):
    """The 8 effectively-once RPCs. Keyword-only args mirror the SQL parameters."""

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
    ) -> IngressResult: ...

    def claim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> ClaimResult: ...

    def heartbeat_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> HeartbeatResult: ...

    def reclaim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> ReclaimResult: ...

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
    ) -> CompleteResult: ...

    def fail_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        error_class: str | None = None,
        error_detail: str | None = None,
    ) -> FailResult: ...

    def begin_delivery(
        self,
        *,
        outbox_id: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> BeginDeliveryResult: ...

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
    ) -> RecordDeliveryResult: ...


class ConvoScanner(Protocol):
    """Read surface the janitor uses to find recovery candidates.

    Deferred read RPCs against the real store; served only by ``FakeConvoStore``
    in Phase 0. ``now`` is the comparison instant (a real scan would use the DB
    ``now()``); the fake compares against its injected clock.
    """

    def find_reclaimable_runs(
        self, *, now: datetime, max_attempts: int = DEFAULT_MAX_ATTEMPTS
    ) -> list[ReclaimCandidate]: ...

    def find_deliverable_outbox(self, *, now: datetime) -> list[OutboxRecord]: ...

    def find_stuck_sending(self, *, now: datetime) -> list[StuckSending]: ...


class ConvoStoreWithScan(ConvoStore, ConvoScanner, Protocol):
    """Mutating RPCs + scan surface — what the janitor requires."""


class PostgRESTConvoStore:
    """Thin httpx client for the ``convo`` RPCs over PostgREST.

    Same stack as ``src.rag.retriever`` (apikey + Bearer service key), adding
    ``Accept-Profile: convo`` / ``Content-Profile: convo`` so ``/rpc/<fn>``
    resolves the SECURITY DEFINER functions of the private schema. The PostgREST
    role is ``convo_rpc`` (impersonated via ``authenticator``); this client only
    needs the service key the platform already injects.

    NEVER exercised against the network in tests (RGPD: no real conversational
    data; the whole suite runs on ``FakeConvoStore``). A live smoke belongs in a
    later apply/rollback lane, gated behind an env var and skipped by default.

    It implements ``ConvoStore`` (the 8 RPCs) but NOT ``ConvoScanner``: MT-0b
    shipped no read/scan RPCs, so candidate discovery against the real store is a
    declared deferred surface (see module docstring).
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_key: str | None = None,
        schema: str = "convo",
        timeout: float = 15.0,
    ) -> None:
        if base_url is None or service_key is None:
            # Lazy so importing this module never requires Supabase env vars
            # (tests import the Protocol/types without touching config).
            from ..config import SUPABASE_URL, SUPABASE_SERVICE_KEY

            base_url = base_url or SUPABASE_URL
            service_key = service_key or SUPABASE_SERVICE_KEY
        self._rpc_url = f"{base_url}/rest/v1/rpc"
        self._schema = schema
        self._timeout = timeout
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Accept-Profile": schema,
            "Content-Profile": schema,
        }

    def _call(self, fn: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST /rpc/<fn>; a jsonb-returning function yields the object directly."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._rpc_url}/{fn}", headers=self._headers, json=body
            )
            resp.raise_for_status()
            return resp.json()

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
        return self._call(
            "ingress",
            {
                "p_channel": channel,
                "p_external_update_id": external_update_id,
                "p_external_chat_id": external_chat_id,
                "p_role": role,
                "p_event_type": event_type,
                "p_content_text": content_text,
                "p_payload": payload if payload is not None else {},
                "p_tenant_id": tenant_id,
            },
        )  # type: ignore[return-value]

    def claim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> ClaimResult:
        return self._call(
            "claim_run",
            {
                "p_turn_run_id": turn_run_id,
                "p_lease_owner": lease_owner,
                "p_lease_seconds": lease_seconds,
            },
        )  # type: ignore[return-value]

    def heartbeat_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> HeartbeatResult:
        return self._call(
            "heartbeat_run",
            {
                "p_turn_run_id": turn_run_id,
                "p_lease_owner": lease_owner,
                "p_fencing_token": fencing_token,
                "p_lease_seconds": lease_seconds,
            },
        )  # type: ignore[return-value]

    def reclaim_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> ReclaimResult:
        return self._call(
            "reclaim_run",
            {
                "p_turn_run_id": turn_run_id,
                "p_lease_owner": lease_owner,
                "p_lease_seconds": lease_seconds,
                "p_max_attempts": max_attempts,
            },
        )  # type: ignore[return-value]

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
        return self._call(
            "complete_run",
            {
                "p_turn_run_id": turn_run_id,
                "p_lease_owner": lease_owner,
                "p_fencing_token": fencing_token,
                "p_channel": channel,
                "p_destination": destination,
                "p_logical_delivery_key": logical_delivery_key,
                "p_answer_text": answer_text,
                "p_answer_payload": answer_payload if answer_payload is not None else {},
                "p_tokens_input": tokens_input,
                "p_tokens_output": tokens_output,
                "p_cost_usd": cost_usd,
                "p_latency_ms": latency_ms,
                "p_max_attempts": max_attempts,
            },
        )  # type: ignore[return-value]

    def fail_run(
        self,
        *,
        turn_run_id: int,
        lease_owner: str,
        fencing_token: int,
        error_class: str | None = None,
        error_detail: str | None = None,
    ) -> FailResult:
        return self._call(
            "fail_run",
            {
                "p_turn_run_id": turn_run_id,
                "p_lease_owner": lease_owner,
                "p_fencing_token": fencing_token,
                "p_error_class": error_class,
                "p_error_detail": error_detail,
            },
        )  # type: ignore[return-value]

    def begin_delivery(
        self,
        *,
        outbox_id: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> BeginDeliveryResult:
        return self._call(
            "begin_delivery",
            {"p_outbox_id": outbox_id, "p_lease_seconds": lease_seconds},
        )  # type: ignore[return-value]

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
        return self._call(
            "record_delivery",
            {
                "p_outbox_id": outbox_id,
                "p_attempt_no": attempt_no,
                "p_success": success,
                "p_external_receipt": external_receipt,
                "p_error_class": error_class,
                "p_error_detail": error_detail,
                "p_retry_seconds": retry_seconds,
            },
        )  # type: ignore[return-value]
