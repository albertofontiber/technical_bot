from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

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
                    self.connection.clock(),
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
            if len(self.connection.fingerprints) > 1:
                value = self.connection.fingerprints.pop(0)
            else:
                value = self.connection.fingerprints[0]
            self._rows = [(value, self.connection.clock())]
        else:
            self.description = None
            self._rows = []
            if sql.startswith("LOCK TABLE"):
                relation = sql.split('"')[1] + "." + sql.split('"')[3]
                self.connection.locked_relations.append(relation)
            elif sql.strip() == "COMMIT;":
                self.connection.commits += 1
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
        self.executed: list[tuple[str, tuple]] = []
        self.commits = 0
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
        monotonic=lambda: 10.0,
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


def test_real_clock_progress_keeps_open_heartbeat_and_close_fingerprint_ordered():
    clock = TickingClock()
    connection = FakeConnection(clock)
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
    clock.advance(seconds=31)
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
        tmp_path / "events" / "000000-open-fence-test.json", event
    )
    fresh_operator, _fresh_connection, _fresh_clock = make_operator()
    with pytest.raises(fence.FenceOperatorHold) as ambiguous:
        fence.FenceIpcServer(
            ipc_dir=tmp_path, operator=fresh_operator, clock=clock
        )
    assert ambiguous.value.code == "HOLD_FENCE_AMBIGUOUS_RECOVERY"


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


def test_lost_open_response_can_abort_preallocated_session(tmp_path: Path):
    operator, connection, clock = make_operator()
    server = fence.FenceIpcServer(
        ipc_dir=tmp_path, operator=operator, clock=clock
    )
    dropped = False

    def lossy_pump():
        nonlocal dropped
        server.process_pending()
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
        pump=lossy_pump,
    )
    with pytest.raises(fence.FenceOperatorHold) as lost:
        client.open(
            release_config_sha256=RELEASE_SHA,
            live_manifest_contract_sha256=operator.manifest_contract_sha256,
        )
    assert lost.value.code == "HOLD_FENCE_IPC_TIMEOUT"

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
