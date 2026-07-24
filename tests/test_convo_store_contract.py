"""Contract suite for the ``convo`` store, run against ``FakeConvoStore``.

Parametrized over a store factory so the SAME assertions can later run against
``PostgRESTConvoStore`` on a throwaway Postgres (gated by env, out of scope for
the RGPD-synthetic Phase 0). Every ``reason`` string asserted here is the SQL
vocabulary of ``20260723100001_s281_convo_rpcs_f0.sql`` verbatim.
"""

import os

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator.fake_convo_store import FakeConvoStore

TELE = "telegram"


@pytest.fixture(params=["fake"])
def store(request):
    if request.param == "fake":
        return FakeConvoStore()
    raise AssertionError(f"unknown store {request.param!r}")  # pragma: no cover


# --- helpers -----------------------------------------------------------------
def _ingress(store, *, chat="chat-1", update="u-1", role="user", query="q"):
    return store.ingress(
        channel=TELE,
        external_update_id=update,
        external_chat_id=chat,
        role=role,
        content_text=query,
    )


def _seed_running(store, *, owner="W1", chat="chat-1", update="u-1"):
    ing = _ingress(store, chat=chat, update=update)
    run_id = ing["turn_run_id"]
    claim = store.claim_run(turn_run_id=run_id, lease_owner=owner)
    return run_id, claim["fencing_token"]


def _complete(store, run_id, fencing, *, owner="W1", chat="chat-1", text="A", max_attempts=5):
    return store.complete_run(
        turn_run_id=run_id,
        lease_owner=owner,
        fencing_token=fencing,
        channel=TELE,
        destination=chat,
        logical_delivery_key="answer",
        answer_text=text,
        max_attempts=max_attempts,
    )


# --- ingress: dedup + idempotency + ordering ---------------------------------
def test_ingress_new_conversation_and_event(store):
    ing = _ingress(store)
    assert ing["is_new_conversation"] is True
    assert ing["is_new_event"] is True
    assert ing["state_version"] == 1
    assert ing["turn_run_id"] is not None
    assert isinstance(ing["public_id"], str) and len(ing["public_id"]) >= 32


def test_ingress_is_idempotent_by_channel_update_id(store):
    first = _ingress(store, update="dup")
    second = _ingress(store, update="dup")
    assert second["is_new_event"] is False
    assert second["is_new_conversation"] is False
    assert second["event_id"] == first["event_id"]
    assert second["turn_run_id"] == first["turn_run_id"]
    # A duplicate does NOT advance the per-conversation CAS.
    assert second["state_version"] == first["state_version"] == 1


def test_ingress_creates_exactly_one_run_per_input_event(store):
    a = _ingress(store, update="dup")
    b = _ingress(store, update="dup")
    assert a["turn_run_id"] == b["turn_run_id"]


def test_ingress_advances_state_version_monotonically(store):
    v1 = _ingress(store, chat="c", update="u1")["state_version"]
    v2 = _ingress(store, chat="c", update="u2")["state_version"]
    dup = _ingress(store, chat="c", update="u2")  # duplicate mid-stream
    v3 = _ingress(store, chat="c", update="u3")["state_version"]
    assert [v1, v2, v3] == [1, 2, 3]
    assert dup["state_version"] == 2 and dup["is_new_event"] is False


def test_ingress_non_user_role_creates_no_run(store):
    ing = _ingress(store, role="assistant")
    assert ing["is_new_event"] is True
    assert ing["turn_run_id"] is None


def test_ingress_rejects_illegal_role_and_event_type(store):
    with pytest.raises(ValueError):
        store.ingress(
            channel=TELE, external_update_id="x", external_chat_id="c", role="robot"
        )
    with pytest.raises(ValueError):
        store.ingress(
            channel=TELE,
            external_update_id="y",
            external_chat_id="c",
            event_type="nonsense",
        )
    # The rejected ingress left no conversation: a later good ingress is "new".
    ok = _ingress(store, chat="c", update="z")
    assert ok["is_new_conversation"] is True


# --- claim_run ---------------------------------------------------------------
def test_claim_pending_transitions_to_running_with_fencing(store):
    ing = _ingress(store)
    claim = store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="W1")
    assert claim["claimed"] is True
    assert claim["fencing_token"] == 1
    assert claim["attempt_no"] == 1
    assert claim["compute_status"] == "running"
    assert claim["reason"] == "claimed"
    assert claim["lease_expires_at"] is not None


def test_double_claim_is_not_pending(store):
    ing = _ingress(store)
    store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="W1")
    again = store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="W2")
    assert again["claimed"] is False
    assert again["reason"] == "not_pending"
    assert again["compute_status"] == "running"


def test_claim_missing_run_is_run_not_found(store):
    res = store.claim_run(turn_run_id=999999, lease_owner="W1")
    assert res["claimed"] is False and res["reason"] == "run_not_found"


def test_claim_validates_args(store):
    ing = _ingress(store)
    with pytest.raises(ValueError):
        store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="W1", lease_seconds=0)
    with pytest.raises(ValueError):
        store.claim_run(turn_run_id=ing["turn_run_id"], lease_owner="")


# --- heartbeat_run -----------------------------------------------------------
def test_heartbeat_extends_only_for_exact_owner(store):
    run_id, fencing = _seed_running(store)
    good = store.heartbeat_run(turn_run_id=run_id, lease_owner="W1", fencing_token=fencing)
    assert good["extended"] is True and good["reason"] == "extended"
    bad_owner = store.heartbeat_run(turn_run_id=run_id, lease_owner="W2", fencing_token=fencing)
    assert bad_owner["extended"] is False and bad_owner["reason"] == "stale_or_not_running"
    bad_fencing = store.heartbeat_run(turn_run_id=run_id, lease_owner="W1", fencing_token=fencing + 5)
    assert bad_fencing["extended"] is False


def test_heartbeat_stale_after_reclaim(store):
    run_id, f1 = _seed_running(store)
    store.clock.advance(120)  # lease expires
    store.reclaim_run(turn_run_id=run_id, lease_owner="W2")  # fencing -> 2
    stale = store.heartbeat_run(turn_run_id=run_id, lease_owner="W1", fencing_token=f1)
    assert stale["extended"] is False and stale["reason"] == "stale_or_not_running"


# --- reclaim_run -------------------------------------------------------------
def test_reclaim_refuses_live_lease(store):
    run_id, _ = _seed_running(store)
    res = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    assert res["reclaimed"] is False and res["reason"] == "lease_still_live"


def test_reclaim_takes_over_expired_lease(store):
    run_id, f1 = _seed_running(store)
    store.clock.advance(120)
    res = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    assert res["reclaimed"] is True
    assert res["fencing_token"] == f1 + 1
    assert res["attempt_no"] == 2
    assert res["previous_owner"] == "W1"
    assert res["reason"] == "reclaimed"


def test_reclaim_retries_failed_run(store):
    run_id, f1 = _seed_running(store)
    store.fail_run(turn_run_id=run_id, lease_owner="W1", fencing_token=f1)
    res = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    assert res["reclaimed"] is True and res["attempt_no"] == 2


def test_reclaim_pending_says_use_claim_run(store):
    ing = _ingress(store)
    res = store.reclaim_run(turn_run_id=ing["turn_run_id"], lease_owner="W1")
    assert res["reclaimed"] is False and res["reason"] == "use_claim_run"


def test_reclaim_terminal_states_not_reclaimable(store):
    run_id, f1 = _seed_running(store)
    _complete(store, run_id, f1)  # answer_ready
    res = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    assert res["reclaimed"] is False and res["reason"] == "not_reclaimable"


def test_reclaim_budget_exhausted(store):
    run_id, f1 = _seed_running(store)
    store.fail_run(turn_run_id=run_id, lease_owner="W1", fencing_token=f1)
    r2 = store.reclaim_run(turn_run_id=run_id, lease_owner="W2", max_attempts=2)
    assert r2["reclaimed"] is True and r2["attempt_no"] == 2
    store.fail_run(turn_run_id=run_id, lease_owner="W2", fencing_token=r2["fencing_token"])
    r3 = store.reclaim_run(turn_run_id=run_id, lease_owner="W3", max_attempts=2)
    assert r3["reclaimed"] is False
    assert r3["reason"] == "attempt_budget_exhausted"
    assert r3["attempt_no"] == 2


def test_reclaim_missing_run(store):
    res = store.reclaim_run(turn_run_id=999999, lease_owner="W1")
    assert res["reclaimed"] is False and res["reason"] == "run_not_found"


# --- fencing: the loser cannot complete --------------------------------------
def test_old_owner_complete_fails_stale_after_reclaim(store):
    run_id, f1 = _seed_running(store)
    store.clock.advance(120)
    r2 = store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    f2 = r2["fencing_token"]
    loser = _complete(store, run_id, f1, owner="W1", text="stale")
    assert loser["completed"] is False and loser["reason"] == "stale_claim"
    winner = _complete(store, run_id, f2, owner="W2", text="fresh")
    assert winner["completed"] is True and winner["outbox_id"] is not None


# --- complete_run ------------------------------------------------------------
def test_complete_happy_path(store):
    run_id, f1 = _seed_running(store)
    res = _complete(store, run_id, f1)
    assert res["completed"] is True
    assert res["compute_status"] == "answer_ready"
    assert res["outbox_id"] is not None


def test_complete_wrong_fencing_is_stale(store):
    run_id, f1 = _seed_running(store)
    res = _complete(store, run_id, f1 + 9, text="x")
    assert res["completed"] is False and res["reason"] == "stale_claim"


def test_complete_missing_run(store):
    res = store.complete_run(
        turn_run_id=999999,
        lease_owner="W1",
        fencing_token=1,
        channel=TELE,
        destination="c",
        logical_delivery_key="answer",
        answer_text="x",
    )
    assert res["completed"] is False and res["reason"] == "run_not_found"


def test_recomplete_fails_cas_not_running(store):
    # Second complete of the same run hits the CAS guard (no longer running).
    run_id, f1 = _seed_running(store)
    _complete(store, run_id, f1)
    again = _complete(store, run_id, f1)
    assert again["completed"] is False and again["reason"] == "stale_claim"


def test_complete_max_attempts_zero_rolls_back(store):
    # In PG the outbox INSERT's CHECK delivery_outbox_max_attempts_positive
    # (max_attempts>=1) rolls back the WHOLE transaction: the run never reaches
    # answer_ready and no outbox is created. The fake must validate-first and
    # raise (rollback semantics), not certify a phantom answer_ready + outbox.
    run_id, f1 = _seed_running(store)
    with pytest.raises(ValueError):
        _complete(store, run_id, f1, max_attempts=0)
    # Nothing mutated: the run is still running (not answer_ready), no outbox.
    assert store.run_status(run_id) == "running"
    assert store.outbox_status(1) is None


# --- fail_run ----------------------------------------------------------------
def test_fail_run_transitions_running_to_failed(store):
    run_id, f1 = _seed_running(store)
    res = store.fail_run(
        turn_run_id=run_id, lease_owner="W1", fencing_token=f1, error_class="Boom"
    )
    assert res["failed"] is True and res["compute_status"] == "failed"


def test_fail_run_stale_fencing(store):
    run_id, f1 = _seed_running(store)
    store.clock.advance(120)
    store.reclaim_run(turn_run_id=run_id, lease_owner="W2")
    res = store.fail_run(turn_run_id=run_id, lease_owner="W1", fencing_token=f1)
    assert res["failed"] is False and res["reason"] == "stale_claim"


def test_fail_run_missing(store):
    res = store.fail_run(turn_run_id=999999, lease_owner="W1", fencing_token=1)
    assert res["failed"] is False and res["reason"] == "run_not_found"


# --- delivery: begin + record + idempotent ack -------------------------------
def _outbox(store, *, max_attempts=5):
    run_id, f1 = _seed_running(store)
    res = _complete(store, run_id, f1, max_attempts=max_attempts)
    return run_id, res["outbox_id"]


def test_begin_delivery_claims_pending_outbox(store):
    _, outbox_id = _outbox(store)
    res = store.begin_delivery(outbox_id=outbox_id)
    assert res["started"] is True and res["attempt_no"] == 1 and res["reason"] == "sending"


def test_second_begin_is_not_claimable(store):
    _, outbox_id = _outbox(store)
    store.begin_delivery(outbox_id=outbox_id)
    again = store.begin_delivery(outbox_id=outbox_id)
    assert again["started"] is False and again["reason"] == "not_claimable"


def test_begin_missing_outbox(store):
    res = store.begin_delivery(outbox_id=999999)
    assert res["started"] is False and res["reason"] == "outbox_not_found"


def test_record_success_marks_delivered_and_turn_delivered(store):
    run_id, outbox_id = _outbox(store)
    begin = store.begin_delivery(outbox_id=outbox_id)
    res = store.record_delivery(
        outbox_id=outbox_id, attempt_no=begin["attempt_no"], success=True, external_receipt="tg-1"
    )
    assert res["acknowledged"] is True
    assert res["delivery_status"] == "delivered"
    assert res["turn_delivered"] is True
    assert store.run_status(run_id) == "delivered"


def test_record_is_idempotent_over_sealed_attempt(store):
    _, outbox_id = _outbox(store)
    begin = store.begin_delivery(outbox_id=outbox_id)
    store.record_delivery(outbox_id=outbox_id, attempt_no=begin["attempt_no"], success=True, external_receipt="tg-1")
    again = store.record_delivery(
        outbox_id=outbox_id, attempt_no=begin["attempt_no"], success=True, external_receipt="tg-2"
    )
    assert again["acknowledged"] is False
    assert again["reason"] == "attempt_already_sealed"
    assert again["turn_delivered"] is False


def test_record_attempt_not_found_without_begin(store):
    _, outbox_id = _outbox(store)
    res = store.record_delivery(outbox_id=outbox_id, attempt_no=1, success=True)
    assert res["acknowledged"] is False and res["reason"] == "attempt_not_found"


def test_delivered_outbox_is_not_claimable_again(store):
    _, outbox_id = _outbox(store)
    begin = store.begin_delivery(outbox_id=outbox_id)
    store.record_delivery(outbox_id=outbox_id, attempt_no=begin["attempt_no"], success=True)
    reclaim_send = store.begin_delivery(outbox_id=outbox_id)
    assert reclaim_send["started"] is False and reclaim_send["reason"] == "not_claimable"


def test_failed_delivery_goes_retryable_then_dead_letter(store):
    _, outbox_id = _outbox(store, max_attempts=2)
    b1 = store.begin_delivery(outbox_id=outbox_id)
    r1 = store.record_delivery(outbox_id=outbox_id, attempt_no=b1["attempt_no"], success=False, error_class="net")
    assert r1["delivery_status"] == "retryable"
    b2 = store.begin_delivery(outbox_id=outbox_id)
    r2 = store.record_delivery(outbox_id=outbox_id, attempt_no=b2["attempt_no"], success=False, error_class="net")
    assert r2["delivery_status"] == "dead_letter"
    dead = store.begin_delivery(outbox_id=outbox_id)
    assert dead["started"] is False and dead["reason"] == "not_claimable"
