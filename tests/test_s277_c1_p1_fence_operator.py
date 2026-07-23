from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_fence_operator as fence


NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
PROJECT_REF = "izooestgffgscdirkfia"
RELEASE_SHA = "a" * 64
SEMANTIC = {"generation": {"visual_assets_registry": False}}
CONTRACT = {"schema": "test-live-manifest-contract-v1", "token": "stable"}


class MutableClock:
    def __init__(self, value: datetime = NOW):
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


class TickingClock(MutableClock):
    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(milliseconds=1)
        return current


class FakeCursor:
    def __init__(self, connection: "FakeConnection"):
        self.connection = connection
        self.description = None
        self._rows = []

    def execute(self, sql, params=()):
        self.connection.executed.append((sql, tuple(params)))
        if "s277:fence-identity" in sql:
            self.connection.identity_calls += 1
            if self.connection.identity_calls == self.connection.identity_drift_call:
                self.connection.backend_pid += 1
            self.description = [
                ("backend_pid",),
                ("fence_owner",),
                ("transaction_read_only",),
                ("txid",),
                ("checked_at",),
            ]
            self._rows = [
                (
                    self.connection.backend_pid,
                    self.connection.fence_owner,
                    "on",
                    self.connection.txid,
                    self.connection.clock()
                    + timedelta(seconds=self.connection.database_clock_offset_seconds),
                )
            ]
        elif "s277:fence-lock-snapshot" in sql:
            self.description = [("relation",), ("mode",), ("granted",)]
            self._rows = [
                (relation, "ShareLock", True)
                for relation in self.connection.locked_relations
            ]
        elif "s277:fence-incompatible-waiters" in sql:
            self.description = [("pid",), ("relation",), ("mode",)]
            self._rows = [
                (row["pid"], row["relation"], row["mode"])
                for row in self.connection.waiters
            ]
        elif "s277:fence-fingerprint" in sql:
            self.description = [("fingerprint",), ("taken_at",)]
            advance_seconds = (
                self.connection.fingerprint_advances.pop(0)
                if self.connection.fingerprint_advances
                else self.connection.fingerprint_advance_seconds
            )
            if advance_seconds:
                self.connection.clock.advance(
                    seconds=advance_seconds
                )
            if len(self.connection.fingerprints) > 1:
                value = self.connection.fingerprints.pop(0)
            else:
                value = self.connection.fingerprints[0]
            self._rows = [
                (
                    value,
                    self.connection.clock()
                    + timedelta(seconds=self.connection.database_clock_offset_seconds),
                )
            ]
        else:
            self.description = None
            self._rows = []
            if sql.startswith("LOCK TABLE"):
                relation = sql.split('"')[1] + "." + sql.split('"')[3]
                self.connection.locked_relations.append(relation)
            elif sql.strip() == "COMMIT;":
                self.connection.commits += 1
                if self.connection.commit_advance_seconds:
                    self.connection.clock.advance(
                        seconds=self.connection.commit_advance_seconds
                    )
            elif sql.strip() == "ROLLBACK;":
                if self.connection.rollback_fails:
                    raise RuntimeError("connection lost before rollback acknowledgement")
                self.connection.rollbacks += 1
                self.connection.locked_relations = []

    def fetchall(self):
        return list(self._rows)

    def close(self):
        return None


class FakeConnection:
    def __init__(
        self,
        clock: MutableClock,
        *,
        host: str | None = None,
        port: int = 5432,
        user: str = "postgres",
    ):
        self.clock = clock
        self.info = SimpleNamespace(
            host=host or f"db.{PROJECT_REF}.supabase.co",
            port=port,
            user=user,
            ssl_in_use=True,
        )
        self.backend_pid = 4242
        self.fence_owner = "postgres"
        self.txid = "virtualxid:7/19"
        self.locked_relations: list[str] = []
        self.waiters: list[dict] = []
        self.fingerprints = [{"digest": "f" * 64, "row_count": 123}]
        self.fingerprint_advance_seconds = 0
        self.fingerprint_advances: list[int] = []
        self.identity_calls = 0
        self.identity_drift_call = -1
        self.database_clock_offset_seconds = 0
        self.executed: list[tuple[str, tuple]] = []
        self.commits = 0
        self.commit_advance_seconds = 0
        self.rollbacks = 0
        self.rollback_fails = False
        self.autocommit = False

    def cursor(self):
        return FakeCursor(self)

    def get_transaction_status(self):
        return 0


def capture_manifest(_connection, phase, captured_at):
    return {
        "phase": phase,
        "captured_at": captured_at.isoformat(),
        "token": "stable",
    }


def verify_capture(contract, capture):
    if capture["token"] != contract["token"]:
        raise fence.FenceOperatorHold("HOLD_FENCE_MANIFEST_DRIFT", capture["phase"])


def verify_window(contract, captures):
    for capture in captures:
        verify_capture(contract, capture)
    phases = [capture["phase"] for capture in captures]
    if not (
        phases[0] == "pre"
        and phases[-1] == "post"
        and all(phase == "watch" for phase in phases[1:-1])
    ):
        raise fence.FenceOperatorHold("HOLD_FENCE_MANIFEST_SEQUENCE", str(phases))


def make_operator(
    *,
    clock: MutableClock | None = None,
    connection: FakeConnection | None = None,
    capture=capture_manifest,
    monotonic=None,
    fence_window: timedelta = fence.DEFAULT_FENCE_WINDOW,
):
    clock = clock or MutableClock()
    connection = connection or FakeConnection(clock)
    operator = fence.PostgreSQLFenceOperator(
        connection=connection,
        project_ref=PROJECT_REF,
        target_semantic_config=SEMANTIC,
        release_config_sha256=RELEASE_SHA,
        manifest_contract=CONTRACT,
        capture_manifest=capture,
        verify_manifest_capture=verify_capture,
        verify_manifest_window=verify_window,
        clock=clock,
        monotonic=monotonic or (lambda: 10.0),
        fence_window=fence_window,
    )
    return operator, connection, clock


def test_happy_path_receipts_verify_and_commit_only_after_manifest_window():
    operator, connection, clock = make_operator()

    opened = operator.open()
    fingerprint = opened["fingerprint_receipt"]
    open_receipt = opened["fence_open_receipt"]
    p1.verify_fingerprint_receipt(
        fingerprint, release_config_sha256=RELEASE_SHA, now=clock()
    )
    p1.verify_fence_open_receipt(
        open_receipt,
        release_config_sha256=RELEASE_SHA,
        fingerprint=fingerprint["fingerprint"],
        target_semantic_config=SEMANTIC,
        now=clock(),
    )
    assert open_receipt["live_manifest_contract_sha256"] == fence._sha256_json(
        CONTRACT
    )
    assert connection.commits == 0

    closed = operator.close(session_id=opened["session_id"])
    close_receipt = closed["fence_close_receipt"]
    result = p1.verify_fence_close_receipt(
        open_receipt, close_receipt, now=clock()
    )

    assert result["status"] == "P1_WINDOW_CLOSED_VERIFIED"
    assert close_receipt["live_manifest_contract_sha256"] == open_receipt[
        "live_manifest_contract_sha256"
    ]
    assert close_receipt["live_manifest_post_capture_sha256"] == p1.sha256_json(
        closed["live_manifest_post_capture"]
    )
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert operator.terminal_status == "CLOSED"


def test_sql_order_is_begin_then_canonical_nowait_locks_before_any_select():
    operator, connection, _clock = make_operator()
    operator.open()

    statements = [sql.strip() for sql, _params in connection.executed]
    assert statements[0] == fence.BEGIN_SQL
    assert statements[1] == "SET LOCAL statement_timeout = '30s';"
    lock_sql = statements[2 : 2 + len(p1.BASE_FENCE_RELATIONS)]
    assert lock_sql == [
        f'LOCK TABLE "{relation.split(".")[0]}"."{relation.split(".")[1]}" '
        "IN SHARE MODE NOWAIT;"
        for relation in p1.BASE_FENCE_RELATIONS
    ]
    assert "s277:fence-identity" in statements[2 + len(lock_sql)]
    fingerprint_index = next(
        index
        for index, statement in enumerate(statements)
        if "s277:fence-fingerprint" in statement
    )
    assert statements[fingerprint_index - 1] == (
        "SET LOCAL statement_timeout = "
        f"'{fence.FINGERPRINT_STATEMENT_TIMEOUT_SECONDS}s';"
    )
    assert statements[fingerprint_index + 1] == (
        "SET LOCAL statement_timeout = "
        f"'{fence.BASE_STATEMENT_TIMEOUT_SECONDS}s';"
    )


def test_real_clock_progress_keeps_open_heartbeat_and_close_fingerprint_ordered():
    clock = TickingClock()
    connection = FakeConnection(clock)
    connection.fingerprint_advances = [0, 71]
    operator, _connection, _clock = make_operator(
        clock=clock,
        connection=connection,
        monotonic=lambda: (clock.value - NOW).total_seconds(),
    )
    opened = operator.open()
    p1.verify_fence_open_receipt(
        opened["fence_open_receipt"],
        release_config_sha256=RELEASE_SHA,
        fingerprint=opened["fingerprint_receipt"]["fingerprint"],
        target_semantic_config=SEMANTIC,
        now=clock(),
    )
    closed = operator.close(session_id=opened["session_id"])
    close_receipt = closed["fence_close_receipt"]
    p1.verify_fence_close_receipt(
        opened["fence_open_receipt"],
        close_receipt,
        now=clock(),
    )
    fingerprint_at = datetime.fromisoformat(
        close_receipt["final_fingerprint_taken_at"].replace("Z", "+00:00")
    )
    heartbeat_at = datetime.fromisoformat(
        close_receipt["last_heartbeat_at"].replace("Z", "+00:00")
    )
    closed_at = datetime.fromisoformat(
        close_receipt["closed_at"].replace("Z", "+00:00")
    )
    assert fingerprint_at <= heartbeat_at <= closed_at


def test_two_second_database_clock_skew_is_tolerated_end_to_end():
    clock = MutableClock()
    connection = FakeConnection(clock)
    connection.database_clock_offset_seconds = 1
    operator, _connection, _clock = make_operator(
        clock=clock, connection=connection
    )

    opened = operator.open()
    p1.verify_fence_open_receipt(
        opened["fence_open_receipt"],
        release_config_sha256=RELEASE_SHA,
        fingerprint=opened["fingerprint_receipt"]["fingerprint"],
        target_semantic_config=SEMANTIC,
        now=clock(),
    )
    closed = operator.close(session_id=opened["session_id"])
    p1.verify_fence_close_receipt(
        opened["fence_open_receipt"],
        closed["fence_close_receipt"],
        now=clock(),
    )


def test_supavisor_transaction_mode_6543_is_rejected_before_sql():
    clock = MutableClock()
    connection = FakeConnection(
        clock,
        host=fence.S277_SUPAVISOR_SESSION_HOST,
        port=6543,
        user=f"postgres.{PROJECT_REF}",
    )

    with pytest.raises(fence.FenceOperatorHold) as caught:
        make_operator(clock=clock, connection=connection)

    assert caught.value.code == "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED"
    assert connection.executed == []


def test_pinned_supavisor_session_mode_5432_is_accepted():
    clock = MutableClock()
    connection = FakeConnection(
        clock,
        host=fence.S277_SUPAVISOR_SESSION_HOST,
        port=5432,
        user=f"postgres.{PROJECT_REF}",
    )
    operator, _connection, _clock = make_operator(
        clock=clock, connection=connection
    )

    assert operator.transport["mode"] == "supavisor_session"


def test_missing_share_lock_aborts_and_rolls_back():
    operator, connection, _clock = make_operator()
    opened = operator.open()
    connection.locked_relations.pop()

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.heartbeat(opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert connection.rollbacks == 1
    assert operator.terminal_status == "ABORTED"


def test_incompatible_waiter_aborts_and_rolls_back():
    operator, connection, _clock = make_operator()
    opened = operator.open()
    connection.waiters = [
        {
            "pid": 9999,
            "relation": "public.chunks_v2",
            "mode": "RowExclusiveLock",
        }
    ]

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.heartbeat(opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert connection.rollbacks == 1


def test_stale_heartbeat_is_terminal_instead_of_silently_recovered():
    operator, connection, clock = make_operator()
    opened = operator.open()
    clock.advance(seconds=fence.DEFAULT_HEARTBEAT_MAX_AGE_SECONDS + 1)

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.heartbeat(opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert "heartbeat stale" in caught.value.detail
    assert connection.rollbacks == 1


def test_final_fingerprint_drift_rolls_back_and_never_commits():
    operator, connection, _clock = make_operator()
    first = {"digest": "a" * 64, "row_count": 123}
    second = {"digest": "b" * 64, "row_count": 124}
    connection.fingerprints = [first, second]
    opened = operator.open()

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.close(session_id=opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_DRIFT"
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_post_manifest_heartbeat_staleness_aborts_before_final_fingerprint():
    clock = MutableClock()
    connection = FakeConnection(clock)

    def slow_post_manifest(_connection, phase, captured_at):
        if phase == "post":
            clock.advance(seconds=fence.DEFAULT_HEARTBEAT_MAX_AGE_SECONDS + 1)
        return capture_manifest(_connection, phase, captured_at)

    operator, _connection, _clock = make_operator(
        clock=clock,
        connection=connection,
        capture=slow_post_manifest,
        monotonic=lambda: (clock.value - NOW).total_seconds(),
    )
    opened = operator.open()

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.close(session_id=opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert "heartbeat stale" in caught.value.detail
    assert sum(
        "s277:fence-fingerprint" in sql for sql, _params in connection.executed
    ) == 1
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_backend_drift_after_final_fingerprint_rolls_back():
    operator, connection, _clock = make_operator()
    opened = operator.open()
    connection.identity_drift_call = 6

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.close(session_id=opened["session_id"])

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert connection.rollbacks == 1
    assert connection.commits == 0


@pytest.mark.parametrize(
    ("advance_seconds", "fence_window", "expected_code"),
    [
        (121, fence.DEFAULT_FENCE_WINDOW, "HOLD_FINGERPRINT_CEILING"),
        (91, timedelta(seconds=90), "HOLD_CORPUS_FENCE_LOST"),
    ],
)
def test_final_fingerprint_ceiling_or_deadline_crossing_rolls_back(
    advance_seconds: int,
    fence_window: timedelta,
    expected_code: str,
):
    clock = MutableClock()
    connection = FakeConnection(clock)
    connection.fingerprint_advances = [0, advance_seconds]
    operator, _connection, _clock = make_operator(
        clock=clock,
        connection=connection,
        monotonic=lambda: (clock.value - NOW).total_seconds(),
        fence_window=fence_window,
    )
    opened = operator.open()

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.close(session_id=opened["session_id"])

    assert caught.value.code == expected_code
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_late_commit_ack_is_closed_hold_and_never_aborted(tmp_path: Path):
    clock = MutableClock()
    connection = FakeConnection(clock)
    connection.commit_advance_seconds = 31
    operator, _connection, _clock = make_operator(
        clock=clock,
        connection=connection,
        monotonic=lambda: (clock.value - NOW).total_seconds(),
    )
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )

    with pytest.raises(fence.FenceOperatorHold) as caught:
        client.close()

    assert caught.value.code == "HOLD_FENCE_CLOSE_POST_COMMIT_FRESHNESS"
    assert operator.terminal_status == "CLOSED"
    assert client.confirmed_terminal_status() == "CLOSED"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    with pytest.raises(fence.FenceOperatorHold) as no_abort:
        client.abort(reason_code="HOLD_CLOSE_RESPONSE_UNUSABLE")
    assert no_abort.value.code == "HOLD_FENCE_ALREADY_CLOSED"
    assert [
        fence.load_json_object(path)["action"]
        for path in (tmp_path / "requests").glob("*.json")
    ].count("abort") == 0


def test_manifest_post_drift_rolls_back_before_commit():
    captures = 0

    def drifting_capture(_connection, phase, captured_at):
        nonlocal captures
        captures += 1
        return {
            "phase": phase,
            "captured_at": captured_at.isoformat(),
            "token": "changed" if phase == "post" else "stable",
        }

    operator, connection, _clock = make_operator(capture=drifting_capture)
    opened = operator.open()

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.close(session_id=opened["session_id"])

    assert caught.value.code == "HOLD_FENCE_MANIFEST_DRIFT"
    assert captures == 2
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_watch_has_exact_runner_shape_and_is_bound_through_open_hash(monkeypatch):
    operator, _connection, clock = make_operator()
    opened = operator.open()
    genesis = {
        "run_genesis_sha256": "1" * 64,
        "target_semantic_config": SEMANTIC,
    }
    monkeypatch.setattr(p1, "verify_run_genesis", lambda value: dict(value))

    receipt = operator.watch(
        session_id=opened["session_id"],
        phase="before_provider_send",
        call_key="hp017:r1:embedding",
        run_genesis=genesis,
    )

    assert set(receipt) == p1.FENCE_WATCH_EXACT_KEYS
    assert receipt["fence_open_receipt_sha256"] == p1.sha256_json(
        opened["fence_open_receipt"]
    )
    p1.verify_fence_watch_receipt(
        receipt,
        open_receipt=opened["fence_open_receipt"],
        run_genesis=genesis,
        call_key="hp017:r1:embedding",
        now=clock(),
    )


def test_watch_reprobes_after_slow_manifest_capture_before_return(monkeypatch):
    clock = MutableClock()

    def slow_capture(connection, phase, captured_at):
        capture = capture_manifest(connection, phase, captured_at)
        if phase == "watch":
            clock.advance(seconds=3)
        return capture

    operator, connection, _clock = make_operator(clock=clock, capture=slow_capture)
    opened = operator.open()
    genesis = {
        "run_genesis_sha256": "1" * 64,
        "target_semantic_config": SEMANTIC,
    }
    monkeypatch.setattr(p1, "verify_run_genesis", lambda value: dict(value))
    identity_calls_before_watch = connection.identity_calls

    receipt = operator.watch(
        session_id=opened["session_id"],
        phase="before_provider_send",
        call_key="hp017:r1:embedding",
        run_genesis=genesis,
    )

    assert connection.identity_calls == identity_calls_before_watch + 2
    assert receipt["checked_at"] == fence._iso(clock())
    assert receipt["last_heartbeat_at"] == receipt["checked_at"]
    p1.verify_fence_watch_receipt(
        receipt,
        open_receipt=opened["fence_open_receipt"],
        run_genesis=genesis,
        call_key="hp017:r1:embedding",
        now=clock(),
    )


def test_watch_reprobe_does_not_refresh_capture_past_heartbeat_limit(monkeypatch):
    clock = MutableClock()

    def stale_capture(connection, phase, captured_at):
        capture = capture_manifest(connection, phase, captured_at)
        if phase == "watch":
            clock.advance(seconds=31)
        return capture

    operator, connection, _clock = make_operator(
        clock=clock, capture=stale_capture
    )
    opened = operator.open()
    genesis = {
        "run_genesis_sha256": "1" * 64,
        "target_semantic_config": SEMANTIC,
    }
    monkeypatch.setattr(p1, "verify_run_genesis", lambda value: dict(value))

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.watch(
            session_id=opened["session_id"],
            phase="before_provider_send",
            call_key="hp017:r1:embedding",
            run_genesis=genesis,
        )

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert operator.terminal_status == "ABORTED"
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_watch_reprobe_rejects_identity_drift_after_manifest_capture(monkeypatch):
    operator, connection, _clock = make_operator()
    opened = operator.open()
    genesis = {
        "run_genesis_sha256": "1" * 64,
        "target_semantic_config": SEMANTIC,
    }
    monkeypatch.setattr(p1, "verify_run_genesis", lambda value: dict(value))
    connection.identity_drift_call = connection.identity_calls + 2

    with pytest.raises(fence.FenceOperatorHold) as caught:
        operator.watch(
            session_id=opened["session_id"],
            phase="before_provider_send",
            call_key="hp017:r1:embedding",
            run_genesis=genesis,
        )

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert operator.terminal_status == "ABORTED"
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_ipc_round_trip_is_ordered_exclusive_and_replay_safe(
    tmp_path: Path, monkeypatch
):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )

    opened = client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    request_path = next((tmp_path / "requests").glob("*.json"))
    before = len(connection.executed)
    same_response = server.process_path(request_path)
    assert same_response["status"] == "PASS"
    assert len(connection.executed) == before

    genesis = {
        "run_genesis_sha256": "1" * 64,
        "target_semantic_config": SEMANTIC,
    }
    monkeypatch.setattr(p1, "verify_run_genesis", lambda value: dict(value))
    watcher = fence.IpcFenceWatcher(client)
    watch = watcher.verify(
        phase="before_provider_send",
        replica=None,
        call_key="hp017:r1:embedding",
        run_genesis=genesis,
        fence_open_receipt=opened["fence_open_receipt"],
    )
    assert watch["call_key"] == "hp017:r1:embedding"
    closed = client.close()
    assert closed["fence_close_receipt"]["status"] == "CLOSED_VERIFIED"
    assert connection.commits == 1


def test_expired_request_with_durable_response_replays_without_sql(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    open_request = min((tmp_path / "requests").glob("*.json"))
    before = len(connection.executed)
    clock.advance(seconds=int(fence.OPEN_CLOSE_REQUEST_TTL.total_seconds()) + 1)

    replay = server.process_path(open_request)

    assert replay["status"] == "PASS"
    assert len(connection.executed) == before


def test_ipc_stale_request_and_ambiguous_restart_fail_closed(tmp_path: Path):
    operator, _connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    request = fence.build_ipc_request(
        action="open",
        sequence=0,
        session_id=None,
        payload={
            "release_config_sha256": RELEASE_SHA,
            "live_manifest_contract_sha256": operator.manifest_contract_sha256,
        },
        now=clock(),
    )
    path = tmp_path / "requests" / f"{request['request_id']}.json"
    fence.write_json_atomic_exclusive(path, request)
    clock.advance(seconds=int(fence.OPEN_CLOSE_REQUEST_TTL.total_seconds()) + 1)
    with pytest.raises(fence.FenceOperatorHold) as stale:
        server.process_path(path)
    assert stale.value.code == "HOLD_FENCE_IPC_STALE"

    # An OPEN marker without CLOSED/ABORTED proves an uncertain prior process;
    # a new operator is never allowed to infer recovery.
    event = {
        "schema": fence.STATE_EVENT_SCHEMA,
        "status": "OPEN",
        "session_id": "fence-" + "1" * 32,
        "sequence": 0,
        "recorded_at": NOW.isoformat(),
    }
    fence.write_json_atomic_exclusive(
        tmp_path / "events" / f"000000-open-{event['session_id']}.json", event
    )
    fresh_operator, _fresh_connection, _fresh_clock = make_operator()
    with pytest.raises(fence.FenceOperatorHold) as ambiguous:
        fence.FenceIpcServer(
            ipc_dir=tmp_path, operator=fresh_operator, clock=clock
        )
    assert ambiguous.value.code == "HOLD_FENCE_AMBIGUOUS_RECOVERY"


@pytest.mark.parametrize(
    ("action", "expected_ttl"),
    [
        ("open", fence.OPEN_CLOSE_REQUEST_TTL),
        ("watch", fence.REQUEST_TTL),
        ("close", fence.OPEN_CLOSE_REQUEST_TTL),
        ("abort", fence.ABORT_REQUEST_TTL),
    ],
)
def test_ipc_request_ttl_is_action_specific(action: str, expected_ttl: timedelta):
    request = fence.build_ipc_request(
        action=action,
        sequence=0,
        session_id=None,
        payload={},
        now=NOW,
    )
    created = datetime.fromisoformat(request["created_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))
    assert expires - created == expected_ttl
    assert (
        fence.OPEN_CLOSE_SERVER_CEILING_SECONDS
        + fence.OPEN_CLOSE_MAX_UNCHECKED_BLOCK_SECONDS
        + fence.OPEN_CLOSE_RESPONSE_ALLOWANCE_SECONDS
        < fence.OPEN_CLOSE_IPC_TIMEOUT_SECONDS
        < fence.OPEN_CLOSE_REQUEST_TTL.total_seconds()
    )


def test_bound_postgrest_provider_requires_later_distinct_post_file(tmp_path: Path):
    pre = tmp_path / "pre.json"
    post = tmp_path / "post.json"
    pre_value = {"schema": "safe-snapshot", "value": 1}
    fence.write_json_atomic_exclusive(pre, pre_value)
    provider = fence.BoundPostgrestSnapshotProvider(
        pre_path=pre, post_path=post
    )

    assert provider("pre") == pre_value
    assert provider("watch") == pre_value
    with pytest.raises(fence.FenceOperatorHold) as missing_post:
        provider("post")
    assert missing_post.value.code == "HOLD_FENCE_IPC_PATH"

    # Equal semantic content is valid when production did not drift, but it is
    # supplied through a newly and exclusively published post-fence artifact.
    fence.write_json_atomic_exclusive(post, pre_value)
    with pytest.raises(fence.FenceOperatorHold) as premature_watch:
        provider("watch")
    assert premature_watch.value.code == "HOLD_POSTGREST_POST_NOT_FRESH"
    assert provider("post") == pre_value

    with pytest.raises(fence.FenceOperatorHold) as same_path:
        fence.BoundPostgrestSnapshotProvider(pre_path=pre, post_path=pre)
    assert same_path.value.code == "HOLD_POSTGREST_SNAPSHOT_BINDING"

    another_post = tmp_path / "already-there.json"
    fence.write_json_atomic_exclusive(another_post, pre_value)
    with pytest.raises(fence.FenceOperatorHold) as not_fresh:
        fence.BoundPostgrestSnapshotProvider(
            pre_path=pre, post_path=another_post
        )
    assert not_fresh.value.code == "HOLD_POSTGREST_POST_NOT_FRESH"


def test_ipc_records_aborted_only_after_confirmed_rollback(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    connection.locked_relations.pop()

    with pytest.raises(fence.FenceOperatorHold) as stopped:
        client.watch(
            phase="before_provider_send",
            call_key="hp017:r1:embedding",
            run_genesis={},
        )
    assert stopped.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert operator.rollback_confirmed is True
    statuses = [
        fence.load_json_object(path)["status"]
        for path in sorted((tmp_path / "events").glob("*.json"))
    ]
    assert statuses == ["OPEN", "ABORTED"]

    # Because rollback was acknowledged, this is not an ambiguous restart.
    fresh_operator, _fresh_connection, _fresh_clock = make_operator()
    fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=fresh_operator, clock=clock
    )


def test_failed_rollback_leaves_open_marker_ambiguous(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    connection.locked_relations.pop()
    connection.rollback_fails = True

    with pytest.raises(fence.FenceOperatorHold):
        client.watch(
            phase="before_provider_send",
            call_key="hp017:r1:embedding",
            run_genesis={},
        )
    assert operator.terminal_status == "AMBIGUOUS"
    assert operator.rollback_confirmed is False
    statuses = [
        fence.load_json_object(path)["status"]
        for path in sorted((tmp_path / "events").glob("*.json"))
    ]
    assert statuses == ["OPEN"]

    fresh_operator, _fresh_connection, _fresh_clock = make_operator()
    with pytest.raises(fence.FenceOperatorHold) as ambiguous:
        fence.FenceIpcServer(
            ipc_dir=tmp_path, operator=fresh_operator, clock=clock
        )
    assert ambiguous.value.code == "HOLD_FENCE_AMBIGUOUS_RECOVERY"


def test_ipc_explicit_abort_confirms_rollback_and_persists_receipt(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    opened = client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )

    result = client.abort(reason_code="HOLD_POSTGREST_POST_CAPTURE_FAILED")
    receipt = result["fence_abort_receipt"]

    assert receipt == {
        "schema": fence.ABORT_RECEIPT_SCHEMA,
        "status": "ABORTED_CONFIRMED",
        "session_id": opened["session_id"],
        "reason_code": "HOLD_POSTGREST_POST_CAPTURE_FAILED",
        "release_config_sha256": RELEASE_SHA,
        "live_manifest_contract_sha256": operator.manifest_contract_sha256,
        "backend_pid": 4242,
        "txid": "virtualxid:7/19",
        "fence_owner": "postgres",
        "rollback_confirmed": True,
        "aborted_at": NOW.isoformat().replace("+00:00", "Z"),
    }
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert operator.terminal_status == "ABORTED"
    assert [
        fence.load_json_object(path)["status"]
        for path in sorted((tmp_path / "events").glob("*.json"))
    ] == ["OPEN", "ABORTED"]


def test_serve_loop_never_heartbeats_after_terminal_dispatch(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    request = fence.build_ipc_request(
        action="abort",
        sequence=client.sequence,
        session_id=client.session_id,
        payload={"reason_code": "HOLD_TERMINAL_LOOP_TEST"},
        now=clock(),
    )
    request_path = tmp_path / "requests" / f"{request['request_id']}.json"
    fence.write_json_atomic_exclusive(request_path, request)
    server._last_heartbeat_monotonic = 0

    server.serve_forever(poll_interval_seconds=0)

    response = fence.load_json_object(tmp_path / "responses" / request_path.name)
    assert response["status"] == "PASS"
    assert operator.terminal_status == "ABORTED"
    assert connection.rollbacks == 1
    assert len(list((tmp_path / "events").glob("*-aborted-*.json"))) == 1


@pytest.mark.parametrize("terminal_action", ["close", "abort"])
def test_lost_terminal_response_is_recovered_exactly_without_second_end(
    tmp_path: Path,
    terminal_action: str,
    monkeypatch,
):
    operator, connection, clock = make_operator()
    dropped: list[dict[str, object]] = []
    real_writer = fence.write_json_atomic_exclusive

    def drop_terminal_response(path, value):
        if (
            path.parent.name == "responses"
            and value.get("action") == terminal_action
        ):
            dropped.append(dict(value))
            return
        real_writer(path, value)

    monkeypatch.setattr(fence, "write_json_atomic_exclusive", drop_terminal_response)
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    errors: list[BaseException] = []

    def serve():
        try:
            server.serve_forever(poll_interval_seconds=0.001)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path,
        clock=clock,
        timeout_seconds=1.0,
        open_close_timeout_seconds=1.0,
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )

    if terminal_action == "close":
        result = client.close()
        assert result == dropped[0]["payload"]
        assert connection.commits == 1
        assert connection.rollbacks == 0
    else:
        result = client.abort(reason_code="HOLD_ORIGINAL_ABORT_REASON")
        assert result == dropped[0]["payload"]
        assert result["fence_abort_receipt"]["reason_code"] == (
            "HOLD_ORIGINAL_ABORT_REASON"
        )
        assert connection.rollbacks == 1
        assert connection.commits == 0
    worker.join(timeout=1.0)
    assert not worker.is_alive()
    assert errors == []
    actions = [
        fence.load_json_object(path)["action"]
        for path in (tmp_path / "requests").glob("*.json")
    ]
    assert actions.count(terminal_action) == 1
    assert not (terminal_action == "close" and "abort" in actions)


def test_fresh_server_reconstructs_missing_close_response_without_sql(
    tmp_path: Path,
):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    client.close()
    close_request = next(
        path
        for path in (tmp_path / "requests").glob("*.json")
        if fence.load_json_object(path)["action"] == "close"
    )
    close_response = tmp_path / "responses" / close_request.name
    original = fence.load_json_object(close_response)
    close_response.unlink()
    fresh_operator, fresh_connection, _fresh_clock = make_operator()
    fresh_server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=fresh_operator, clock=clock
    )

    recovered = fresh_server.process_path(close_request)

    assert recovered == original
    assert fence.load_json_object(close_response) == original
    assert fresh_connection.executed == []
    assert connection.commits == 1


def test_conflicting_terminal_journals_are_rejected(tmp_path: Path):
    operator, _connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    client.close()
    closed_path = next((tmp_path / "events").glob("*-closed-*.json"))
    closed = fence.load_json_object(closed_path)
    request_id = "b" * 32
    request_sha = "c" * 64
    reason = "HOLD_CONFLICTING_ABORT"
    response_unsigned = {
        "schema": fence.RESPONSE_SCHEMA,
        "status": "PASS",
        "request_id": request_id,
        "request_sha256": request_sha,
        "action": "abort",
        "sequence": closed["sequence"],
        "session_id": closed["session_id"],
        "responded_at": NOW.isoformat().replace("+00:00", "Z"),
        "payload": {
            "fence_abort_receipt": {
                "reason_code": reason,
                "rollback_confirmed": True,
            }
        },
    }
    response = {
        **response_unsigned,
        "response_sha256": fence._sha256_json(response_unsigned),
    }
    journal_unsigned = {
        "schema": fence.TERMINAL_JOURNAL_SCHEMA,
        "status": "ABORTED",
        "session_id": closed["session_id"],
        "sequence": closed["sequence"],
        "request_id": request_id,
        "request_sha256": request_sha,
        "action": "abort",
        "response": response,
        "reason_code": reason,
        "transaction_end": "ROLLBACK_CONFIRMED",
        "recorded_at": NOW.isoformat().replace("+00:00", "Z"),
    }
    conflicting = {
        **journal_unsigned,
        "journal_sha256": fence._sha256_json(journal_unsigned),
    }
    fence.write_json_atomic_exclusive(
        tmp_path
        / "events"
        / (
            f"{int(closed['sequence']):06d}-aborted-"
            f"{closed['session_id']}.json"
        ),
        conflicting,
    )

    with pytest.raises(fence.FenceOperatorHold) as caught:
        client.confirmed_terminal_status()

    assert caught.value.code == "HOLD_FENCE_TERMINAL_CONFLICT"


def test_tampered_terminal_journal_is_rejected(tmp_path: Path):
    operator, _connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    client.abort(reason_code="HOLD_ORIGINAL_ABORT_REASON")
    journal_path = next((tmp_path / "events").glob("*-aborted-*.json"))
    journal = fence.load_json_object(journal_path)
    journal["reason_code"] = "HOLD_TAMPERED_REASON"
    journal_path.write_text(
        fence._canonical_bytes(journal).decode("utf-8"), encoding="utf-8"
    )

    with pytest.raises(fence.FenceOperatorHold) as caught:
        client.confirmed_terminal_status()

    assert caught.value.code == "HOLD_FENCE_TERMINAL_JOURNAL"


def test_abort_pending_open_waits_behind_long_open_and_rolls_back_once(
    tmp_path: Path,
):
    def slow_open_capture(_connection, phase, captured_at):
        if phase == "pre":
            time.sleep(0.1)
        return capture_manifest(_connection, phase, captured_at)

    operator, connection, clock = make_operator(capture=slow_open_capture)
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    worker = threading.Thread(
        target=lambda: server.serve_forever(poll_interval_seconds=0.001),
        daemon=True,
    )
    worker.start()
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path,
        clock=clock,
        timeout_seconds=1.0,
        open_close_timeout_seconds=0.03,
    )

    with pytest.raises(fence.FenceOperatorHold) as lost:
        client.open(
            release_config_sha256=RELEASE_SHA,
            live_manifest_contract_sha256=operator.manifest_contract_sha256,
        )
    assert lost.value.code == "HOLD_FENCE_IPC_TIMEOUT"
    recovered = client.abort_pending_open(reason_code="HOLD_OPEN_RESPONSE_LOST")

    worker.join(timeout=1.0)
    assert recovered["fence_abort_receipt"]["reason_code"] == (
        "HOLD_OPEN_RESPONSE_LOST"
    )
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert not worker.is_alive()


def test_lost_open_response_can_abort_preallocated_session(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    dropped = False

    def lossy_pump():
        nonlocal dropped
        # In production the server is a SEPARATE process: a server-side hold
        # (e.g. HOLD_FENCE_IPC_SEQUENCE when it re-dispatches the orphaned
        # request after this pump deleted its response) never crosses into the
        # client, which only ever observes its own timeout. The inline pump
        # must reproduce that isolation or the expected HOLD_FENCE_IPC_TIMEOUT
        # races with the server's hold (platform-timing dependent: surfaced on
        # Linux CI, masked on Windows).
        try:
            server.process_pending()
        except fence.FenceOperatorHold:
            pass
        if not dropped:
            for path in (tmp_path / "responses").glob("*.json"):
                response = fence.load_json_object(path)
                if response.get("action") == "open":
                    path.unlink()
                    dropped = True

    client = fence.FenceIpcClient(
        ipc_dir=tmp_path,
        clock=clock,
        timeout_seconds=0.03,
        open_close_timeout_seconds=0.03,
        pump=lossy_pump,
    )
    with pytest.raises(fence.FenceOperatorHold) as lost:
        client.open(
            release_config_sha256=RELEASE_SHA,
            live_manifest_contract_sha256=operator.manifest_contract_sha256,
        )
    # Both arms of the SAME unconfirmed-open ambiguity, and which one the client
    # observes is polling timing (production-legitimate on both): TIMEOUT when
    # the deadline fires before the server re-polls, or the server's re-dispatch
    # of the orphaned request writing its HOLD(SEQUENCE) as the response
    # (process_path catches the hold into a response file, so it DOES reach a
    # real out-of-process client). The invariant under test is the recovery
    # below, not which ambiguity arm fired.
    assert lost.value.code in {
        "HOLD_FENCE_IPC_TIMEOUT",
        "HOLD_FENCE_IPC_SEQUENCE",
    }

    recovered = client.abort_pending_open(
        reason_code="HOLD_FENCE_OPEN_UNCONFIRMED"
    )
    assert recovered["fence_abort_receipt"]["rollback_confirmed"] is True
    assert connection.rollbacks == 1
    assert operator.terminal_status == "ABORTED"
    assert [
        fence.load_json_object(path)["status"]
        for path in sorted((tmp_path / "events").glob("*.json"))
    ] == ["OPEN", "ABORTED"]


def test_ipc_abort_without_session_and_unsafe_reason_fail_closed(tmp_path: Path):
    operator, _connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    with pytest.raises(fence.FenceOperatorHold) as not_open:
        client.abort(reason_code="HOLD_TEST")
    assert not_open.value.code == "HOLD_FENCE_SESSION"

    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    with pytest.raises(fence.FenceOperatorHold) as unsafe:
        client.abort(reason_code="contains secret detail")
    assert unsafe.value.code == "HOLD_FENCE_ABORT_REASON"


def test_ipc_abort_rollback_failure_remains_ambiguous(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    client = fence.FenceIpcClient(
        ipc_dir=tmp_path, clock=clock, pump=server.process_pending
    )
    client.open(
        release_config_sha256=RELEASE_SHA,
        live_manifest_contract_sha256=operator.manifest_contract_sha256,
    )
    connection.rollback_fails = True

    with pytest.raises(fence.FenceOperatorHold) as ambiguous:
        client.abort(reason_code="HOLD_RUNNER_FAILED")

    assert ambiguous.value.code == "HOLD_FENCE_ABORT_AMBIGUOUS"
    assert operator.terminal_status == "AMBIGUOUS"
    assert operator.rollback_confirmed is False
    assert [
        fence.load_json_object(path)["status"]
        for path in sorted((tmp_path / "events").glob("*.json"))
    ] == ["OPEN"]
