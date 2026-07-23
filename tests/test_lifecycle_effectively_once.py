"""Phase 0 gate: crash at EVERY frontier + chat isolation + per-conversation order.

The effectively-once driver (``run_conversational_turn``) + the janitor
(``reclaim_and_repair``) + the outbox poller (``deliver_pending``) must recover a
crash at each of the five frontiers with no visible double compute nor double
delivery — EXCEPT the one declared at-least-once window (crash after the send,
before ``record_delivery``), which the test asserts AS a documented duplicate.

Concurrency is exercised by DETERMINISTIC INTERLEAVING at the orchestrator level
(no threads): the PTB transport stays sequential in Phase 0 (fix PTB-CONCURRENCIA),
and the fake store is not designed thread-safe. Fencing, not wall-clock races,
is what decides the winner.
"""

import os

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator import replay_adapters, run_turn
from src.orchestrator.contracts import TurnRequest
from src.orchestrator.convo_store import OutboxRecord
from src.orchestrator.fake_convo_store import FakeConvoStore
from src.orchestrator.lifecycle import (
    deliver_pending,
    reclaim_and_repair,
    run_conversational_turn,
)

TELE = "telegram"


class _Crash(BaseException):
    """A hard process crash: bypasses the driver's ``except Exception`` handling,
    so no ``record_delivery`` runs and the outbox is left ``sending``."""


class _Recorder:
    """Captures every send the injected sender performs (its destination/text)."""

    def __init__(self):
        self.sends = []

    def ok(self):
        def _send(payload):
            self.sends.append(payload)
            return f"tg-{payload.outbox_id}-{payload.attempt_no}"

        return _send

    def crash_before_send(self):
        def _send(payload):
            raise _Crash("dead before send")

        return _send

    def crash_after_send(self):
        def _send(payload):
            self.sends.append(payload)  # the user DID receive it
            raise _Crash("dead after send")

        return _send

    def fail(self):
        def _send(payload):
            raise RuntimeError("telegram 500")

        return _send


def _adapters(gen_calls, *, answer_prefix="ANSWER"):
    def generate(query, chunks, *, available_models=None):
        gen_calls.append(query)
        return {"answer": f"{answer_prefix}::{query}", "diagrams": []}

    return replay_adapters(
        retrieved=[{"id": "a", "content": "A", "similarity": 0.9}], generate=generate
    )


def _request(*, chat="chat-1", update="u-1", query="¿tensión del lazo?"):
    return TurnRequest(
        query=query,
        retrieval_top_k=50,
        rerank_top_k=5,
        conversation_id=chat,
        external_update_id=update,
    )


def _drain_recovery(store, sender, *, worker="janitor"):
    """Full background sweep: expire leases, seal stuck sending, re-deliver."""
    store.clock.advance(200)  # expire the sending lease (SENDING_LEASE_SECONDS=180)
    reclaim_and_repair(store, worker, store.clock.now())
    store.clock.advance(200)  # make sealed->retryable rows due
    return deliver_pending(store, sender, store.clock.now())


@pytest.fixture
def store():
    return FakeConvoStore()


# --- happy path --------------------------------------------------------------
def test_happy_path_delivers_once(store):
    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, _request(), _adapters(gen), "W1", rec.ok())
    assert out.status == "delivered" and out.delivered is True
    assert len(gen) == 1 and len(rec.sends) == 1
    assert store.run_status(out.turn_run_id) == "delivered"
    assert store.outbox_status(out.outbox_id) == "delivered"
    assert rec.sends[0].destination == "chat-1"


# --- crash frontier 1: after ingress, before claim ---------------------------
def test_crash_after_ingress_recovers(store):
    req = _request()
    # First worker crashed right after ingress (only the run row exists).
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, req, _adapters(gen), "W1", rec.ok())
    assert out.status == "delivered"
    assert out.is_new_event is False  # ingress deduped
    assert len(gen) == 1 and len(rec.sends) == 1
    assert store.run_status(ing["turn_run_id"]) == "delivered"


# --- crash frontier 2: after claim, before complete --------------------------
def test_crash_after_claim_recovers_via_reclaim(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    run_id = ing["turn_run_id"]
    store.claim_run(turn_run_id=run_id, lease_owner="W1")  # W1 claimed, then crashed
    store.clock.advance(120)  # its lease expires

    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, req, _adapters(gen), "W2", rec.ok())
    assert out.status == "delivered"
    assert len(gen) == 1  # only W2 computed; W1 never persisted an answer
    assert len(rec.sends) == 1
    assert store.run_status(run_id) == "delivered"


# --- crash frontier 3: after complete, before begin_delivery -----------------
def test_crash_after_complete_recovers_via_poller(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    run_id = ing["turn_run_id"]
    claim = store.claim_run(turn_run_id=run_id, lease_owner="W1")
    gen = []
    result = run_turn(req, _adapters(gen))
    comp = store.complete_run(
        turn_run_id=run_id, lease_owner="W1", fencing_token=claim["fencing_token"],
        channel=TELE, destination="chat-1", logical_delivery_key="answer",
        answer_text=result.answer,
    )
    # Crash before begin_delivery: outbox is 'pending'. Poller recovers it.
    rec = _Recorder()
    outcomes = deliver_pending(store, rec.ok(), store.clock.now())
    assert len(outcomes) == 1 and outcomes[0].delivered is True
    assert len(gen) == 1 and len(rec.sends) == 1
    assert store.run_status(run_id) == "delivered"
    assert store.outbox_status(comp["outbox_id"]) == "delivered"


# --- crash frontier 4: after begin_delivery, before the send -----------------
def test_crash_before_send_recovers_without_duplicate(store):
    req = _request()
    gen = []
    rec = _Recorder()
    with pytest.raises(_Crash):
        run_conversational_turn(store, req, _adapters(gen), "W1", rec.crash_before_send())
    # The send never happened; outbox is stuck 'sending'.
    assert len(rec.sends) == 0
    recovered = _drain_recovery(store, rec.ok())
    assert any(o.delivered for o in recovered)
    # Exactly ONE real send total: no user-visible duplicate.
    assert len(rec.sends) == 1
    assert len(gen) == 1  # never recomputed


# --- crash frontier 5: after the send, before record_delivery ----------------
def test_crash_after_send_is_the_declared_at_least_once_window(store):
    req = _request()
    gen = []
    rec = _Recorder()
    with pytest.raises(_Crash):
        run_conversational_turn(store, req, _adapters(gen), "W1", rec.crash_after_send())
    assert len(rec.sends) == 1  # the user already received it once
    recovered = _drain_recovery(store, rec.ok())
    assert any(o.delivered for o in recovered)
    # The DECLARED window: the janitor cannot distinguish this from crash-4, so
    # the user receives the answer TWICE. Outbox minimises, does not eliminate.
    assert len(rec.sends) == 2
    assert len(gen) == 1  # compute still ran exactly once


# --- clean (non-crash) send failure: retryable, not stuck --------------------
def test_clean_send_failure_becomes_retryable_then_delivers(store):
    req = _request()
    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, req, _adapters(gen), "W1", rec.fail())
    assert out.status == "send_failed" and out.delivered is False
    assert store.outbox_status(out.outbox_id) == "retryable"
    # Poller re-delivers once the retry backoff is due.
    store.clock.advance(120)
    outcomes = deliver_pending(store, rec.ok(), store.clock.now())
    assert any(o.delivered for o in outcomes)
    assert store.run_status(out.turn_run_id) == "delivered"


# --- repeated clean failures exhaust the budget -> dead_letter ----------------
def test_repeated_clean_failures_reach_dead_letter_and_poller_stops(store):
    req = _request()
    gen = []
    rec = _Recorder()
    # max_attempts=2: the driver's first attempt fails cleanly -> retryable.
    out = run_conversational_turn(
        store, req, _adapters(gen), "W1", rec.fail(), max_attempts=2
    )
    assert out.status == "send_failed"
    assert store.outbox_status(out.outbox_id) == "retryable"

    # The poller retries once the backoff is due; the second clean failure spends
    # the last attempt -> dead_letter (no resend budget remains).
    store.clock.advance(120)
    again = deliver_pending(store, rec.fail(), store.clock.now())
    assert len(again) == 1
    assert again[0].ack is not None
    assert again[0].ack["delivery_status"] == "dead_letter"
    assert store.outbox_status(out.outbox_id) == "dead_letter"

    # The run stays answer_ready (never delivered) and the poller no longer sees
    # the row: a dead_letter outbox is out of the deliverable scan.
    assert store.run_status(out.turn_run_id) == "answer_ready"
    store.clock.advance(120)
    assert deliver_pending(store, rec.ok(), store.clock.now()) == []
    assert len(gen) == 1  # computed exactly once, never resent after dead_letter


# --- compute error is recorded (fail_run) and re-raised, then retryable ------
def test_compute_exception_records_failure_and_reraises(store):
    req = _request()
    rec = _Recorder()
    boom_calls = []

    def boom(query, chunks, *, available_models=None):
        boom_calls.append(query)
        raise RuntimeError("writer blew up")

    boom_adapters = replay_adapters(
        retrieved=[{"id": "a", "content": "A", "similarity": 0.9}], generate=boom
    )
    with pytest.raises(RuntimeError):
        run_conversational_turn(store, req, boom_adapters, "W1", rec.ok())
    # Recover the run id via a deduped ingress; it must be recorded 'failed'.
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    assert store.run_status(ing["turn_run_id"]) == "failed"
    assert len(rec.sends) == 0

    # Retry with a healthy writer: the driver self-heals (reclaim of failed).
    gen = []
    out = run_conversational_turn(store, req, _adapters(gen), "W2", rec.ok())
    assert out.status == "delivered"
    assert len(gen) == 1 and len(rec.sends) == 1


# --- two workers competing: live lease -> loser does not publish -------------
def test_second_worker_backs_off_live_lease(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="W1")  # live lease
    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, req, _adapters(gen), "W2", rec.ok())
    assert out.status == "claim_lost"
    assert len(rec.sends) == 0 and len(gen) == 0


# --- two workers competing: stale fencing -> loser cannot complete/publish ---
def test_stale_worker_cannot_publish_after_reclaim(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    run_id = ing["turn_run_id"]
    c1 = store.claim_run(turn_run_id=run_id, lease_owner="W1")
    store.clock.advance(120)
    r2 = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")

    # W1 wakes up with a stale fencing: its complete is rejected.
    stale = store.complete_run(
        turn_run_id=run_id, lease_owner="W1", fencing_token=c1["fencing_token"],
        channel=TELE, destination="chat-1", logical_delivery_key="answer",
        answer_text="STALE-W1",
    )
    assert stale["completed"] is False and stale["reason"] == "stale_claim"

    gen = []
    result = run_turn(req, _adapters(gen, answer_prefix="FRESH"))
    store.complete_run(
        turn_run_id=run_id, lease_owner="W2", fencing_token=r2["fencing_token"],
        channel=TELE, destination="chat-1", logical_delivery_key="answer",
        answer_text=result.answer,
    )
    rec = _Recorder()
    deliver_pending(store, rec.ok(), store.clock.now())
    assert len(rec.sends) == 1
    assert rec.sends[0].text.startswith("FRESH::")  # only the winner's answer


# --- duplicate Telegram updates -> exactly one response ----------------------
def test_duplicate_update_yields_single_response(store):
    req = _request(update="same-update")
    gen = []
    rec = _Recorder()
    first = run_conversational_turn(store, req, _adapters(gen), "W1", rec.ok())
    second = run_conversational_turn(store, req, _adapters(gen), "W1", rec.ok())
    assert first.status == "delivered"
    assert second.status == "already_delivered" and second.delivered is True
    assert first.turn_run_id == second.turn_run_id
    assert len(gen) == 1  # no recompute
    assert len(rec.sends) == 1  # no resend


# --- two isolated conversations: nothing crosses -----------------------------
def test_two_conversations_are_isolated(store):
    gen = []
    rec = _Recorder()
    out_a = run_conversational_turn(
        store, _request(chat="chat-A", update="uA", query="A?"), _adapters(gen), "W", rec.ok()
    )
    out_b = run_conversational_turn(
        store, _request(chat="chat-B", update="uB", query="B?"), _adapters(gen), "W", rec.ok()
    )
    assert out_a.conversation_id != out_b.conversation_id
    assert out_a.turn_run_id != out_b.turn_run_id
    assert out_a.state_version == 1 and out_b.state_version == 1
    by_dest = {s.destination: s.text for s in rec.sends}
    assert by_dest["chat-A"].endswith("A?")
    assert by_dest["chat-B"].endswith("B?")


# --- order per conversation: state_version is monotonic ----------------------
def test_state_version_monotonic_within_conversation(store):
    v1 = store.ingress(channel=TELE, external_update_id="u1", external_chat_id="c")["state_version"]
    v2 = store.ingress(channel=TELE, external_update_id="u2", external_chat_id="c")["state_version"]
    dup = store.ingress(channel=TELE, external_update_id="u2", external_chat_id="c")
    v3 = store.ingress(channel=TELE, external_update_id="u3", external_chat_id="c")["state_version"]
    assert [v1, v2, v3] == [1, 2, 3]
    assert dup["is_new_event"] is False and dup["state_version"] == 2


# --- janitor: REPORTS orphans WITHOUT mutating; fencing is a store property --
def test_janitor_reports_orphan_without_reclaiming(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    run_id = ing["turn_run_id"]
    c1 = store.claim_run(turn_run_id=run_id, lease_owner="W1")
    store.clock.advance(120)  # W1 crashed; its lease expired

    # The janitor REPORTS the orphan and does NOT reclaim it (no mutation).
    summary = reclaim_and_repair(store, "janitor", store.clock.now())
    assert not hasattr(summary, "reclaimed_runs")  # the mutant phase is gone
    orphan = {r["turn_run_id"]: r for r in summary.orphaned_runs}
    assert run_id in orphan
    assert orphan[run_id]["compute_status"] == "running"
    # Budget intact: a reclaim would have bumped attempt_no to 2.
    assert orphan[run_id]["attempt_no"] == 1

    # The fencing guarantee is a STORE-level property (reclaim_run), demonstrated
    # DIRECTLY — not something the janitor does. A store reclaim bumps fencing so
    # the crashed owner can neither complete nor publish.
    r2 = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    assert r2["reclaimed"] is True
    stale = store.complete_run(
        turn_run_id=run_id, lease_owner="W1", fencing_token=c1["fencing_token"],
        channel=TELE, destination="chat-1", logical_delivery_key="answer", answer_text="x",
    )
    assert stale["completed"] is False and stale["reason"] == "stale_claim"


# --- janitor: N sweeps over an orphan never burn the attempt budget ----------
def test_janitor_multi_sweep_keeps_budget_and_run_recoverable(store):
    req = _request()
    ing = store.ingress(
        channel=TELE, external_update_id="u-1", external_chat_id="chat-1",
        role="user", content_text=req.query,
    )
    run_id = ing["turn_run_id"]
    store.claim_run(turn_run_id=run_id, lease_owner="W1")  # W1 claimed then crashed
    store.clock.advance(120)  # lease expired -> orphan

    # The old bug: each sweep reclaimed + spent an attempt until the run was both
    # budget-exhausted AND invisible to the scan (irrecoverable). Now N successive
    # sweeps leave attempt_no INTACT (the janitor only reports).
    for _ in range(6):
        summary = reclaim_and_repair(store, "janitor", store.clock.now())
        entry = next(r for r in summary.orphaned_runs if r["turn_run_id"] == run_id)
        assert entry["attempt_no"] == 1  # never mutated across sweeps

    # The run is STILL recoverable by a real re-invocation, which reclaims ONCE
    # (attempt_no -> 2, well within budget) and delivers.
    gen = []
    rec = _Recorder()
    out = run_conversational_turn(store, req, _adapters(gen), "W2", rec.ok())
    assert out.status == "delivered"
    assert len(gen) == 1 and len(rec.sends) == 1
    assert store.run_status(run_id) == "delivered"
