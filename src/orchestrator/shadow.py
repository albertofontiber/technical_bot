"""CONVO_SHADOW persistence (S281 / MT-0d).

Phase-0 shadow: after the user has ALREADY been answered by the live path, the
turn is persisted into the effectively-once ``convo`` store so the existing
retrieval/coverage traces gain a durable home. It runs the effectively-once
cycle WITHOUT the delivery leg (the transport already sent the answer), so the
run settles at ``answer_ready`` and its outbox row stays ``pending`` with NO
poller in Phase 0.

Hard invariants (a shadow must never harm the live turn):
  * it NEVER alters the answer shown to the user (it runs after the reply);
  * it NEVER raises into the handler (``maybe_shadow_persist`` is fail-open;
    every error is logged);
  * with the flag on but NO store injected it is a no-op logged exactly once
    (Phase 0: only tests inject a ``FakeConvoStore`` — RGPD: synthetic only).

The real store is NEVER wired here in Phase 0. Its activation is an ops
dependency (shared with ``schedule_maintenance`` and ``PostgRESTConvoStore``):
a signed RGPD lifecycle matrix, the applied ``convo`` DDL, a minted
``role=convo_rpc`` JWT, and ``PGRST_DB_SCHEMAS`` including ``convo``.

Why not ``run_conversational_turn``? That driver performs the SEND (delivery
leg). In shadow the transport already answered, so a second send would double-
deliver. This module drives ingress -> claim -> complete_run directly and stops
there.
"""

from __future__ import annotations

import logging
from typing import Any

from .contracts import RetrievalResult, TurnRequest, TurnResult
from .convo_store import DEFAULT_LEASE_SECONDS, ConvoStore
from .orchestrator import plan_turn

logger = logging.getLogger(__name__)

# One bot answer per turn (mirrors ``lifecycle.LOGICAL_DELIVERY_KEY``).
SHADOW_LOGICAL_DELIVERY_KEY = "answer"
SHADOW_WORKER_ID = "shadow-f0"

# Injection point: Phase 0 tests set this to a ``FakeConvoStore``. Production
# leaves it ``None`` (no store configured -> no-op logged once).
_SHADOW_STORE: ConvoStore | None = None
_NO_STORE_LOGGED = False


def register_shadow_store(store: ConvoStore | None) -> None:
    """Inject (or clear) the shadow store. Phase 0: tests only."""
    global _SHADOW_STORE, _NO_STORE_LOGGED
    _SHADOW_STORE = store
    _NO_STORE_LOGGED = False


def get_shadow_store() -> ConvoStore | None:
    return _SHADOW_STORE


def turn_result_from_pipeline(
    request: TurnRequest, pipeline: dict[str, Any]
) -> TurnResult:
    """Shape a ``TurnResult`` from a raw ``execute_rag_turn`` dict (the live OFF
    path). Mirrors ``run_turn``'s tail so the shadow persists the same object
    whether or not ``ORCHESTRATOR_PATH`` drove the compute."""
    generation = pipeline["generation"]
    retrieval = RetrievalResult(
        chunks=tuple(pipeline["chunks"]),
        coverage_trace=pipeline["coverage_trace"],
        retrieval_rows=pipeline["retrieval_rows"],
        reranked_rows=pipeline["reranked_rows"],
    )
    return TurnResult(
        answer=generation.get("answer", ""),
        diagrams=tuple(generation.get("diagrams") or ()),
        plan=plan_turn(request),
        compute_status="answer_ready",
        retrieval=retrieval,
        generation=generation,
    )


def _shadow_answer_payload(result: TurnResult) -> dict[str, Any]:
    """The persisted retrieval/coverage trace carried on the outbox payload."""
    retrieval = result.retrieval
    return {
        "diagrams": list(result.diagrams),
        "coverage_trace": retrieval.coverage_trace if retrieval is not None else None,
        "retrieval_rows": retrieval.retrieval_rows if retrieval is not None else None,
        "reranked_rows": retrieval.reranked_rows if retrieval is not None else None,
        "chunks_served": len(retrieval.chunks) if retrieval is not None else 0,
    }


def shadow_persist_turn(
    store: ConvoStore, request: TurnRequest, result: TurnResult
) -> Any:
    """Persist one already-answered turn effectively-once, WITHOUT delivery.

    ingress (dedup, real ``update_id``) -> claim -> complete_run (answer +
    retrieval/coverage trace in the outbox payload). No begin/record_delivery:
    the answer was already sent by the transport, so on success the run is left
    ``answer_ready`` and its outbox ``pending`` (no poller in Phase 0). A
    duplicate update whose run is no longer claimable is skipped (idempotent).

    Returns the ``CompleteResult`` on a fresh persist, or ``None`` when nothing
    was persisted (missing keys / dedup / not claimable). It does NOT swallow
    store exceptions — the fail-open boundary is ``maybe_shadow_persist``.
    """
    if request.external_update_id is None or request.conversation_id is None:
        return None

    ingress = store.ingress(
        channel=request.channel,
        external_update_id=request.external_update_id,
        external_chat_id=request.conversation_id,
        role="user",
        event_type="message",
        content_text=request.query,
        payload={"source": request.source},
    )
    turn_run_id = ingress["turn_run_id"]
    if turn_run_id is None:
        return None

    claim = store.claim_run(
        turn_run_id=turn_run_id,
        lease_owner=SHADOW_WORKER_ID,
        lease_seconds=DEFAULT_LEASE_SECONDS,
    )
    if not claim["claimed"]:
        # Already persisted by a prior shadow (dedup), or otherwise not pending.
        return None

    generation = result.generation or {}
    return store.complete_run(
        turn_run_id=turn_run_id,
        lease_owner=SHADOW_WORKER_ID,
        fencing_token=claim["fencing_token"],
        channel=request.channel,
        destination=request.conversation_id,
        logical_delivery_key=SHADOW_LOGICAL_DELIVERY_KEY,
        answer_text=result.answer,
        answer_payload=_shadow_answer_payload(result),
        # The generator emits input_tokens/output_tokens; cost/latency are not
        # meaningful for a post-hoc shadow (the transport already answered).
        tokens_input=generation.get("input_tokens"),
        tokens_output=generation.get("output_tokens"),
        cost_usd=None,
        latency_ms=None,
    )


def maybe_shadow_persist(request: TurnRequest, result: TurnResult) -> None:
    """Handler entry point: fail-open shadow persistence.

    Reads the injected store; with none configured, logs once and returns. Any
    exception is swallowed (logged) so the shadow can NEVER tumble the handler.
    """
    global _NO_STORE_LOGGED
    store = _SHADOW_STORE
    if store is None:
        if not _NO_STORE_LOGGED:
            logger.info(
                "CONVO_SHADOW on but no store injected; shadow persistence is a "
                "no-op (Phase 0: real store gated on RGPD matrix + convo_rpc JWT)"
            )
            _NO_STORE_LOGGED = True
        return
    try:
        shadow_persist_turn(store, request, result)
    except Exception as exc:  # fail-open: a shadow must never harm the live turn
        logger.warning(
            "CONVO_SHADOW persistence failed open (%s)", type(exc).__name__
        )
