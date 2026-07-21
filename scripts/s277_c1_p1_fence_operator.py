"""Persistent PostgreSQL fence operator and replay-safe local IPC for S277 P1.

The paid runner must never own the PostgreSQL operator credential.  This module
therefore keeps the database connection in a separate process and exposes only
sealed request/response files.  The operator starts one explicit READ ONLY,
READ COMMITTED transaction, acquires the canonical relations in ``ShareLock``
order with ``NOWAIT``, and holds that same backend until a verified close.

``LOCK TABLE`` is intentionally legal in a PostgreSQL read-only transaction:
the read-only command deny-list does not include ``LOCK``.  ``ShareLock`` then
conflicts with the ``RowExclusiveLock`` used by writers.  READ COMMITTED is
intentional too: the table locks keep corpus rows stable while each catalog
manifest capture can still observe later function/configuration changes.

No function here contacts a provider, mutates Supabase, or loads credentials
into the runner.  The CLI reads its DSN from an operator-only environment
variable; it never accepts or prints a DSN on the command line.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_live_manifest as live_manifest


REQUEST_SCHEMA = "s277_c1_p1_fence_ipc_request_v1"
RESPONSE_SCHEMA = "s277_c1_p1_fence_ipc_response_v1"
STATE_EVENT_SCHEMA = "s277_c1_p1_fence_operator_state_event_v1"
ABORT_RECEIPT_SCHEMA = "s277_c1_p1_fence_abort_receipt_v1"
S277_SUPAVISOR_SESSION_HOST = "aws-1-eu-north-1.pooler.supabase.com"
REQUEST_TTL = timedelta(seconds=30)
ABORT_REQUEST_TTL = timedelta(minutes=45)
DEFAULT_FENCE_WINDOW = timedelta(minutes=40)
DEFAULT_HEARTBEAT_MAX_AGE_SECONDS = 30
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 5

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID = re.compile(r"^[a-f0-9]{32}$")
_SESSION_ID = re.compile(r"^fence-[a-f0-9]{32}$")
_SAFE_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,95}$")
_RELATION = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
_PROJECT_REF = re.compile(r"^[a-z0-9]{20}$")
_CONFLICTING_WITH_SHARE = (
    "RowExclusiveLock",
    "ShareUpdateExclusiveLock",
    "ShareRowExclusiveLock",
    "ExclusiveLock",
    "AccessExclusiveLock",
)


BEGIN_SQL = (
    "BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY;"
)
IDENTITY_SQL = """/* s277:fence-identity */
SELECT
    pg_backend_pid() AS backend_pid,
    current_user AS fence_owner,
    current_setting('transaction_read_only') AS transaction_read_only,
    COALESCE(
        (
            SELECT 'virtualxid:' || lock.virtualxid::text
            FROM pg_locks AS lock
            WHERE lock.pid = pg_backend_pid()
              AND lock.locktype = 'virtualxid'
              AND lock.granted
            ORDER BY lock.virtualxid::text
            LIMIT 1
        ),
        'backend:' || pg_backend_pid()::text
    ) AS txid,
    clock_timestamp() AS checked_at;
"""
LOCK_SNAPSHOT_SQL = """/* s277:fence-lock-snapshot */
SELECT
    namespace.nspname || '.' || relation.relname AS relation,
    lock.mode,
    lock.granted
FROM pg_locks AS lock
JOIN pg_class AS relation ON relation.oid = lock.relation
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE lock.pid = %s
  AND lock.locktype = 'relation'
  AND lock.mode = 'ShareLock'
  AND namespace.nspname || '.' || relation.relname = ANY(%s)
ORDER BY array_position(%s, namespace.nspname || '.' || relation.relname);
"""
INCOMPATIBLE_WAITERS_SQL = """/* s277:fence-incompatible-waiters */
SELECT
    waiter.pid,
    namespace.nspname || '.' || relation.relname AS relation,
    waiter.mode
FROM pg_locks AS waiter
JOIN pg_class AS relation ON relation.oid = waiter.relation
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE waiter.pid <> %s
  AND waiter.locktype = 'relation'
  AND NOT waiter.granted
  AND waiter.mode = ANY(%s)
  AND namespace.nspname || '.' || relation.relname = ANY(%s)
ORDER BY waiter.pid, array_position(%s, namespace.nspname || '.' || relation.relname), waiter.mode;
"""
FINGERPRINT_SQL = """/* s277:fence-fingerprint */
SELECT public.corpus_fingerprint_v1() AS fingerprint,
       clock_timestamp() AS taken_at;
"""


class FenceOperatorHold(RuntimeError):
    """Stable fail-closed condition emitted by the operator boundary."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _hold(code: str, detail: str) -> None:
    raise FenceOperatorHold(code, detail)


def _expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _hold(code, detail)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _json_copy(value: Any, *, field: str) -> Any:
    try:
        result = json.loads(_canonical_bytes(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FenceOperatorHold("HOLD_FENCE_OPERATOR_SHAPE", field) from exc
    _expect(result == value, "HOLD_FENCE_OPERATOR_SHAPE", field)
    return result


def _utc(value: datetime) -> datetime:
    _expect(
        value.tzinfo is not None and value.utcoffset() is not None,
        "HOLD_FENCE_OPERATOR_TIME",
        "timezone-aware clock required",
    )
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise FenceOperatorHold("HOLD_FENCE_OPERATOR_TIME", field) from exc
    return _utc(parsed)


def _rows(connection: Any, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, tuple(params))
        description = cursor.description or ()
        columns = [str(item[0]) for item in description]
        raw_rows = cursor.fetchall() if description else []
        result: list[dict[str, Any]] = []
        for row in raw_rows:
            if isinstance(row, Mapping):
                result.append({str(key): item for key, item in row.items()})
            else:
                result.append(dict(zip(columns, row, strict=True)))
        return result
    finally:
        cursor.close()


def _execute(connection: Any, sql: str, params: Sequence[Any] = ()) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, tuple(params))
    finally:
        cursor.close()


def _quote_relation(relation: str) -> str:
    _expect(
        _RELATION.fullmatch(relation) is not None,
        "HOLD_FENCE_CANONICAL_SURFACE",
        relation,
    )
    schema, name = relation.split(".", 1)
    return f'"{schema}"."{name}"'


def validate_persistent_transport(
    connection: Any,
    *,
    project_ref: str,
    approved_session_host: str = S277_SUPAVISOR_SESSION_HOST,
) -> dict[str, Any]:
    """Accept only direct or pinned Supavisor session-mode TLS on port 5432."""

    _expect(
        _PROJECT_REF.fullmatch(project_ref) is not None,
        "HOLD_FENCE_PROJECT_REF",
        project_ref,
    )
    info = getattr(connection, "info", None)
    host = str(getattr(info, "host", "") or "").lower()
    port = int(getattr(info, "port", 0) or 0)
    user = str(getattr(info, "user", "") or "")
    tls = getattr(info, "ssl_in_use", None)
    _expect(
        port == 5432,
        "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED",
        f"port {port or '<unknown>'}; transaction mode :6543 is forbidden",
    )
    _expect(
        tls is True,
        "HOLD_FENCE_TLS_REQUIRED",
        "database transport is not proven TLS",
    )
    direct_host = f"db.{project_ref}.supabase.co"
    if host == direct_host:
        return {"mode": "direct", "host": host, "port": 5432, "tls": True}
    _expect(
        host == approved_session_host.lower()
        and user == f"postgres.{project_ref}",
        "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED",
        "host/user is neither the pinned direct endpoint nor pinned session pooler",
    )
    return {
        "mode": "supavisor_session",
        "host": host,
        "port": 5432,
        "tls": True,
        "authenticated_project_ref": project_ref,
    }


@dataclass(frozen=True)
class P1ReadonlyManifestCapture:
    """Capture the live manifest as p1_readonly on the operator transaction."""

    project_ref: str
    visual_assets_registry: str
    postgrest_snapshot_provider: Callable[[str], Mapping[str, Any]]

    def __call__(
        self, connection: Any, phase: str, captured_at: datetime
    ) -> Mapping[str, Any]:
        _execute(connection, "SET LOCAL ROLE p1_readonly;")
        try:
            snapshot = self.postgrest_snapshot_provider(phase)
            return live_manifest.capture_live_manifest(
                connection,
                project_ref=self.project_ref,
                visual_assets_registry=self.visual_assets_registry,
                phase=phase,
                postgrest_snapshot=snapshot,
                captured_at=captured_at,
            )
        finally:
            _execute(connection, "RESET ROLE;")


class BoundPostgrestSnapshotProvider:
    """Supply a sealed pre/watch snapshot and a genuinely later post artifact.

    The post path must not exist when the provider is constructed.  A separate
    operator-side capture step publishes it exclusively after the fence process
    has started.  Watches deliberately reuse the pre snapshot; final close
    always reloads the independently published post file.
    """

    def __init__(self, *, pre_path: Path, post_path: Path) -> None:
        self.pre_path = pre_path.resolve()
        self.post_path = post_path.resolve()
        _expect(
            self.pre_path != self.post_path,
            "HOLD_POSTGREST_SNAPSHOT_BINDING",
            "pre/post paths must be distinct",
        )
        self.pre_snapshot = load_json_object(self.pre_path)
        self.pre_sha256 = _sha256_json(self.pre_snapshot)
        self.pre_served = False
        _expect(
            not self.post_path.exists(),
            "HOLD_POSTGREST_POST_NOT_FRESH",
            "post snapshot must be published after operator startup",
        )

    def __call__(self, phase: str) -> Mapping[str, Any]:
        _expect(
            phase in {"pre", "watch", "post"},
            "HOLD_POSTGREST_SNAPSHOT_BINDING",
            phase,
        )
        if phase in {"pre", "watch"}:
            _expect(
                not self.post_path.exists(),
                "HOLD_POSTGREST_POST_NOT_FRESH",
                "post snapshot was published before the final close window",
            )
            if phase == "pre":
                self.pre_served = True
            return _json_copy(self.pre_snapshot, field=f"postgrest {phase} snapshot")
        _expect(
            self.pre_served,
            "HOLD_POSTGREST_SNAPSHOT_BINDING",
            "post requested before pre snapshot was bound",
        )
        post = load_json_object(self.post_path)
        # The semantic payload is allowed to be identical when production did
        # not drift; freshness comes from exclusive publication of a new path.
        return _json_copy(post, field="postgrest post snapshot")


@dataclass
class _OpenState:
    session_id: str
    opened_at: datetime
    deadline_at: datetime
    last_heartbeat_at: datetime
    backend_pid: int
    txid: str
    fence_owner: str
    initial_fingerprint: Mapping[str, Any]
    open_receipt: Mapping[str, Any]
    manifest_captures: list[Mapping[str, Any]]


class PostgreSQLFenceOperator:
    """Own one persistent connection and one non-recoverable fence session."""

    def __init__(
        self,
        *,
        connection: Any,
        project_ref: str,
        target_semantic_config: Mapping[str, Any],
        release_config_sha256: str,
        manifest_contract: Mapping[str, Any],
        capture_manifest: Callable[[Any, str, datetime], Mapping[str, Any]],
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        fence_window: timedelta = DEFAULT_FENCE_WINDOW,
        heartbeat_max_age_seconds: int = DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
        fingerprint_ceiling_ms: int = 5_000,
        approved_session_host: str = S277_SUPAVISOR_SESSION_HOST,
        verify_manifest_capture: Callable[[Mapping[str, Any], Mapping[str, Any]], None]
        | None = None,
        verify_manifest_window: Callable[
            [Mapping[str, Any], Sequence[Mapping[str, Any]]], None
        ]
        | None = None,
    ) -> None:
        _expect(
            _HEX64.fullmatch(release_config_sha256) is not None,
            "HOLD_FENCE_RELEASE_IDENTITY",
            "release_config_sha256",
        )
        _expect(
            timedelta(0) < fence_window <= p1.MAX_FENCE_WINDOW,
            "HOLD_FENCE_WINDOW",
            "fence window must be within 45 minutes",
        )
        _expect(
            0 < heartbeat_max_age_seconds <= 300,
            "HOLD_FENCE_HEARTBEAT_POLICY",
            str(heartbeat_max_age_seconds),
        )
        _expect(
            isinstance(fingerprint_ceiling_ms, int) and fingerprint_ceiling_ms > 0,
            "HOLD_FINGERPRINT_CEILING",
            str(fingerprint_ceiling_ms),
        )
        transport = validate_persistent_transport(
            connection,
            project_ref=project_ref,
            approved_session_host=approved_session_host,
        )
        status_reader = getattr(connection, "get_transaction_status", None)
        _expect(
            callable(status_reader) and int(status_reader()) == 0,
            "HOLD_FENCE_CONNECTION_NOT_IDLE",
            "operator requires a fresh idle database session",
        )
        try:
            # Suppress Psycopg's implicit BEGIN: the explicit BEGIN options below
            # must be the first server statement, including through Supavisor.
            connection.autocommit = True
        except Exception as exc:
            raise FenceOperatorHold(
                "HOLD_FENCE_CONNECTION_CONTROL", type(exc).__name__
            ) from exc
        semantic = _json_copy(target_semantic_config, field="target_semantic_config")
        surface = p1.expected_surface(semantic)
        relations = surface["relations"]
        _expect(
            relations
            in (
                list(p1.BASE_FENCE_RELATIONS),
                [*p1.BASE_FENCE_RELATIONS, p1.VISUAL_FENCE_RELATION],
            ),
            "HOLD_FENCE_CANONICAL_SURFACE",
            "relations",
        )
        _expect(
            callable(capture_manifest),
            "HOLD_FENCE_MANIFEST_REQUIRED",
            "capture callback missing",
        )
        contract = _json_copy(manifest_contract, field="manifest_contract")
        _expect(
            bool(contract),
            "HOLD_FENCE_MANIFEST_REQUIRED",
            "manifest contract missing",
        )
        self.connection = connection
        self.project_ref = project_ref
        self.target_semantic_config = semantic
        self.release_config_sha256 = release_config_sha256
        self.manifest_contract = contract
        self.manifest_contract_sha256 = _sha256_json(contract)
        self.capture_manifest = capture_manifest
        self.verify_manifest_capture = (
            verify_manifest_capture or live_manifest.verify_manifest_capture
        )
        self.verify_manifest_window = (
            verify_manifest_window or live_manifest.verify_manifest_window
        )
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic or time.monotonic
        self.fence_window = fence_window
        self.heartbeat_max_age_seconds = heartbeat_max_age_seconds
        self.fingerprint_ceiling_ms = fingerprint_ceiling_ms
        self.transport = transport
        self.relations = list(relations)
        self.state: _OpenState | None = None
        self.terminal_status: str | None = None
        self.rollback_confirmed = False

    def _now(self) -> datetime:
        return _utc(self.clock())

    def _rollback_transaction(self) -> bool:
        try:
            _execute(self.connection, "ROLLBACK;")
        except Exception:
            # Closing the operator connection is the only safe follow-up.  The
            # IPC state remains ambiguous and therefore blocks restart.
            self.rollback_confirmed = False
            return False
        self.rollback_confirmed = True
        return True

    def _mark_aborted(self) -> None:
        confirmed = self._rollback_transaction()
        self.state = None
        self.terminal_status = "ABORTED" if confirmed else "AMBIGUOUS"

    def _commit_transaction(self) -> None:
        _execute(self.connection, "COMMIT;")

    def _abort(self, code: str, detail: str) -> None:
        if self.state is not None:
            self._mark_aborted()
        _hold(code, detail)

    def _identity(self) -> dict[str, Any]:
        rows = _rows(self.connection, IDENTITY_SQL)
        _expect(len(rows) == 1, "HOLD_CORPUS_FENCE_LOST", "session identity")
        row = rows[0]
        _expect(
            row.get("transaction_read_only") == "on"
            and isinstance(row.get("backend_pid"), int)
            and bool(row.get("txid"))
            and bool(row.get("fence_owner")),
            "HOLD_CORPUS_FENCE_LOST",
            "session is not the expected read-only backend",
        )
        checked = row.get("checked_at")
        if isinstance(checked, datetime):
            checked_at = _utc(checked)
        else:
            checked_at = _parse_time(checked, field="database checked_at")
        return {
            "backend_pid": int(row["backend_pid"]),
            "txid": str(row["txid"]),
            "fence_owner": str(row["fence_owner"]),
            "checked_at": checked_at,
        }

    def _lock_rows(self, backend_pid: int) -> list[dict[str, Any]]:
        rows = _rows(
            self.connection,
            LOCK_SNAPSHOT_SQL,
            (backend_pid, self.relations, self.relations),
        )
        canonical: list[dict[str, Any]] = []
        for expected, row in zip(self.relations, rows, strict=False):
            _expect(
                row.get("relation") == expected
                and row.get("mode") == "ShareLock"
                and row.get("granted") is True,
                "HOLD_CORPUS_FENCE_LOST",
                f"ShareLock missing for {expected}",
            )
            canonical.append(
                {"relation": expected, "mode": "ShareLock", "granted": True}
            )
        _expect(
            len(rows) == len(self.relations),
            "HOLD_CORPUS_FENCE_LOST",
            "canonical ShareLock count drift",
        )
        return canonical

    def _waiters(self, backend_pid: int) -> list[dict[str, Any]]:
        rows = _rows(
            self.connection,
            INCOMPATIBLE_WAITERS_SQL,
            (
                backend_pid,
                list(_CONFLICTING_WITH_SHARE),
                self.relations,
                self.relations,
            ),
        )
        normalized = [
            {
                "pid": int(row["pid"]),
                "relation": str(row["relation"]),
                "mode": str(row["mode"]),
            }
            for row in rows
        ]
        _expect(
            normalized == [],
            "HOLD_CORPUS_FENCE_LOST",
            "incompatible writer/DDL waiter detected",
        )
        return normalized

    def _fingerprint(self) -> tuple[dict[str, Any], datetime, int]:
        started = self.monotonic()
        rows = _rows(self.connection, FINGERPRINT_SQL)
        elapsed_ms = max(0, round((self.monotonic() - started) * 1000))
        _expect(
            len(rows) == 1 and isinstance(rows[0].get("fingerprint"), Mapping),
            "HOLD_FINGERPRINT_RECEIPT",
            "corpus_fingerprint_v1 result",
        )
        _expect(
            elapsed_ms <= self.fingerprint_ceiling_ms,
            "HOLD_FINGERPRINT_CEILING",
            f"{elapsed_ms}>{self.fingerprint_ceiling_ms}",
        )
        taken = rows[0].get("taken_at")
        taken_at = _utc(taken) if isinstance(taken, datetime) else _parse_time(
            taken, field="fingerprint taken_at"
        )
        fingerprint = _json_copy(rows[0]["fingerprint"], field="fingerprint")
        return fingerprint, taken_at, elapsed_ms

    def _assert_open(self, session_id: str) -> _OpenState:
        state = self.state
        _expect(
            state is not None
            and self.terminal_status is None
            and state.session_id == session_id,
            "HOLD_FENCE_SESSION",
            "unknown or terminal fence session",
        )
        return state

    def _probe_open_state(self, state: _OpenState) -> tuple[datetime, list[dict[str, Any]]]:
        now = self._now()
        if now >= state.deadline_at:
            self._abort("HOLD_CORPUS_FENCE_LOST", "fence deadline reached")
        if now - state.last_heartbeat_at > timedelta(
            seconds=self.heartbeat_max_age_seconds
        ):
            self._abort("HOLD_CORPUS_FENCE_LOST", "operator heartbeat stale")
        identity = self._identity()
        if (
            identity["backend_pid"] != state.backend_pid
            or identity["txid"] != state.txid
            or identity["fence_owner"] != state.fence_owner
        ):
            self._abort("HOLD_CORPUS_FENCE_LOST", "backend/transaction identity drift")
        locks = self._lock_rows(state.backend_pid)
        self._waiters(state.backend_pid)
        checked_at = identity["checked_at"]
        if checked_at > self._now() + timedelta(seconds=2):
            self._abort("HOLD_CORPUS_FENCE_LOST", "database clock is in the future")
        state.last_heartbeat_at = checked_at
        return checked_at, locks

    def open(self, *, session_id: str | None = None) -> dict[str, Any]:
        _expect(
            self.state is None and self.terminal_status is None,
            "HOLD_FENCE_SESSION",
            "operator is single-use",
        )
        try:
            requested_session_id = session_id or f"fence-{uuid4().hex}"
            _expect(
                _SESSION_ID.fullmatch(requested_session_id) is not None,
                "HOLD_FENCE_SESSION",
                "invalid preallocated session id",
            )
            _execute(self.connection, BEGIN_SQL)
            # ALTER ROLE settings are not loaded by SET LOCAL ROLE. Bound every
            # operator statement so a catalog probe cannot orphan the fence.
            _execute(self.connection, "SET LOCAL statement_timeout = '30s';")
            # PostgreSQL recommends taking SHARE locks before the first SELECT
            # at stronger snapshot levels; doing it first is safe at READ COMMITTED too.
            for relation in self.relations:
                _execute(
                    self.connection,
                    f"LOCK TABLE {_quote_relation(relation)} IN SHARE MODE NOWAIT;",
                )
            opened_at = self._now()
            identity = self._identity()
            locks = self._lock_rows(identity["backend_pid"])
            waiters = self._waiters(identity["backend_pid"])
            fingerprint, _taken_at, elapsed_ms = self._fingerprint()
            pre_capture = _json_copy(
                self.capture_manifest(
                    self.connection, "pre", identity["checked_at"]
                ),
                field="pre live manifest",
            )
            self.verify_manifest_capture(self.manifest_contract, pre_capture)
            refreshed_identity = self._identity()
            _expect(
                refreshed_identity["backend_pid"] == identity["backend_pid"]
                and refreshed_identity["txid"] == identity["txid"]
                and refreshed_identity["fence_owner"] == identity["fence_owner"],
                "HOLD_CORPUS_FENCE_LOST",
                "backend/transaction changed during open checks",
            )
            identity = refreshed_identity
            locks = self._lock_rows(identity["backend_pid"])
            waiters = self._waiters(identity["backend_pid"])
            deadline_at = opened_at + self.fence_window
            verified_at = self._now()
            _expect(
                identity["checked_at"] <= verified_at < deadline_at
                and verified_at - identity["checked_at"]
                <= timedelta(seconds=self.heartbeat_max_age_seconds),
                "HOLD_CORPUS_FENCE_LOST",
                "open checks exceeded deadline/heartbeat policy",
            )
            open_receipt = {
                "schema": p1.FENCE_OPEN_SCHEMA,
                "status": "OPEN_VERIFIED",
                "release_config_sha256": self.release_config_sha256,
                "initial_fingerprint": fingerprint,
                "persistent_session": True,
                "transaction_pooler": False,
                "backend_pid": identity["backend_pid"],
                "txid": identity["txid"],
                "fence_owner": identity["fence_owner"],
                "opened_at": _iso(opened_at),
                "last_heartbeat_at": _iso(identity["checked_at"]),
                "heartbeat_max_age_seconds": self.heartbeat_max_age_seconds,
                "deadline_at": _iso(deadline_at),
                "relations": list(self.relations),
                "locks": locks,
                "incompatible_waiters": waiters,
                "rpc_manifest_sha256": p1.expected_declared_rpc_surface_sha256(
                    self.target_semantic_config
                ),
                "physical_manifest_sha256": p1.expected_declared_lock_surface_sha256(
                    self.target_semantic_config
                ),
                "live_manifest_contract_sha256": self.manifest_contract_sha256,
            }
            fingerprint_receipt = {
                "schema": p1.FINGERPRINT_SCHEMA,
                "status": "PASS",
                "release_config_sha256": self.release_config_sha256,
                "function_audit_sha256_lf": p1.EXPECTED_FUNCTION_AUDIT_SHA256_LF,
                "function_definition_sha256": p1.EXPECTED_FUNCTION_DEFINITION_SHA256,
                "elapsed_ms": elapsed_ms,
                "ceiling_ms": self.fingerprint_ceiling_ms,
                "fingerprint": fingerprint,
                "expires_at": _iso(deadline_at),
            }
            self.state = _OpenState(
                session_id=requested_session_id,
                opened_at=opened_at,
                deadline_at=deadline_at,
                last_heartbeat_at=identity["checked_at"],
                backend_pid=identity["backend_pid"],
                txid=identity["txid"],
                fence_owner=identity["fence_owner"],
                initial_fingerprint=fingerprint,
                open_receipt=open_receipt,
                manifest_captures=[pre_capture],
            )
            return {
                "session_id": requested_session_id,
                "fingerprint_receipt": fingerprint_receipt,
                "fence_open_receipt": open_receipt,
                "live_manifest_pre_capture": pre_capture,
            }
        except FenceOperatorHold:
            self._mark_aborted()
            raise
        except Exception as exc:
            self._mark_aborted()
            raise FenceOperatorHold(
                "HOLD_FENCE_OPEN_FAILED", type(exc).__name__
            ) from exc

    def heartbeat(self, session_id: str) -> dict[str, Any]:
        state = self._assert_open(session_id)
        try:
            checked_at, locks = self._probe_open_state(state)
            return {
                "session_id": session_id,
                "checked_at": _iso(checked_at),
                "backend_pid": state.backend_pid,
                "txid": state.txid,
                "locks": locks,
            }
        except FenceOperatorHold as exc:
            if self.state is not None:
                self._mark_aborted()
            raise exc
        except Exception as exc:
            if self.state is not None:
                self._mark_aborted()
            raise FenceOperatorHold(
                "HOLD_FENCE_HEARTBEAT_FAILED", type(exc).__name__
            ) from exc

    def watch(
        self,
        *,
        session_id: str,
        phase: str,
        call_key: str,
        run_genesis: Mapping[str, Any],
    ) -> dict[str, Any]:
        _expect(
            phase == "before_provider_send",
            "HOLD_CORPUS_FENCE_LOST",
            "watch phase",
        )
        state = self._assert_open(session_id)
        try:
            checked_at, locks = self._probe_open_state(state)
            capture = _json_copy(
                self.capture_manifest(self.connection, "watch", checked_at),
                field="watch live manifest",
            )
            self.verify_manifest_capture(self.manifest_contract, capture)
            state.manifest_captures.append(capture)
            genesis = p1.verify_run_genesis(run_genesis)
            receipt = {
                "schema": p1.FENCE_WATCH_SCHEMA,
                "status": "OPEN_VERIFIED",
                "phase": "before_provider_send",
                "call_key": call_key,
                "replica_key": call_key.rsplit(":", 1)[0],
                "checked_at": _iso(checked_at),
                "run_genesis_sha256": genesis["run_genesis_sha256"],
                "release_config_sha256": state.open_receipt[
                    "release_config_sha256"
                ],
                "fingerprint_sha256": p1.sha256_json(
                    state.open_receipt["initial_fingerprint"]
                ),
                "fence_open_receipt_sha256": p1.sha256_json(state.open_receipt),
                "backend_pid": state.backend_pid,
                "txid": state.txid,
                "fence_owner": state.fence_owner,
                "deadline_at": _iso(state.deadline_at),
                "last_heartbeat_at": _iso(checked_at),
                "heartbeat_max_age_seconds": self.heartbeat_max_age_seconds,
                "relations": list(self.relations),
                "locks": locks,
                "incompatible_waiters": [],
                "rpc_manifest_sha256": state.open_receipt[
                    "rpc_manifest_sha256"
                ],
                "physical_manifest_sha256": state.open_receipt[
                    "physical_manifest_sha256"
                ],
            }
            _expect(
                set(receipt) == p1.FENCE_WATCH_EXACT_KEYS,
                "HOLD_CORPUS_FENCE_LOST",
                "watch receipt shape",
            )
            return receipt
        except FenceOperatorHold as exc:
            if self.state is not None:
                self._mark_aborted()
            raise exc
        except Exception as exc:
            if self.state is not None:
                self._mark_aborted()
            raise FenceOperatorHold(
                "HOLD_FENCE_WATCH_FAILED", type(exc).__name__
            ) from exc

    def close(self, *, session_id: str) -> dict[str, Any]:
        state = self._assert_open(session_id)
        try:
            checked_at, _locks = self._probe_open_state(state)
            post_capture = _json_copy(
                self.capture_manifest(self.connection, "post", checked_at),
                field="post live manifest",
            )
            captures = [*state.manifest_captures, post_capture]
            self.verify_manifest_window(self.manifest_contract, captures)
            final_fingerprint, fingerprint_at, _elapsed = self._fingerprint()
            # Recheck physical evidence after the potentially expensive final
            # fingerprint without moving the heartbeat past fingerprint_at.
            locks = self._lock_rows(state.backend_pid)
            self._waiters(state.backend_pid)
            if final_fingerprint != state.initial_fingerprint:
                self._abort("HOLD_CORPUS_DRIFT", "final fingerprint differs")
            closed_at = self._now()
            if closed_at > state.deadline_at:
                self._abort("HOLD_CORPUS_FENCE_LOST", "close after deadline")
            post_capture_sha256 = p1.sha256_json(post_capture)
            close_receipt = {
                "schema": p1.FENCE_CLOSE_SCHEMA,
                "status": "CLOSED_VERIFIED",
                "release_config_sha256": self.release_config_sha256,
                "backend_pid": state.backend_pid,
                "txid": state.txid,
                "fence_owner": state.fence_owner,
                "rpc_manifest_sha256": state.open_receipt[
                    "rpc_manifest_sha256"
                ],
                "physical_manifest_sha256": state.open_receipt[
                    "physical_manifest_sha256"
                ],
                "live_manifest_contract_sha256": self.manifest_contract_sha256,
                "live_manifest_post_capture_sha256": post_capture_sha256,
                "initial_fingerprint": state.initial_fingerprint,
                "final_fingerprint": final_fingerprint,
                "verified_under_lock": True,
                "last_heartbeat_at": _iso(checked_at),
                "final_fingerprint_taken_at": _iso(fingerprint_at),
                "relations": list(self.relations),
                "locks": locks,
                "incompatible_waiters": [],
                "closed_at": _iso(closed_at),
            }
            p1.verify_fence_close_receipt(
                state.open_receipt, close_receipt, now=closed_at
            )
            self._commit_transaction()
            self.state = None
            self.terminal_status = "CLOSED"
            return {
                "fence_close_receipt": close_receipt,
                "live_manifest_post_capture": post_capture,
            }
        except FenceOperatorHold:
            if self.state is not None:
                self._mark_aborted()
            raise
        except Exception as exc:
            if self.state is not None:
                self._mark_aborted()
            raise FenceOperatorHold(
                "HOLD_FENCE_CLOSE_FAILED", type(exc).__name__
            ) from exc

    def abort(self, *, session_id: str, reason_code: str) -> dict[str, Any]:
        """Release an open fence after a runner-side failure.

        The receipt exists only when PostgreSQL acknowledged ``ROLLBACK``.  A
        lost acknowledgement is deliberately left ``AMBIGUOUS`` so no caller
        can claim that the locks were released safely.
        """

        state = self._assert_open(session_id)
        _expect(
            isinstance(reason_code, str)
            and _SAFE_REASON_CODE.fullmatch(reason_code) is not None,
            "HOLD_FENCE_ABORT_REASON",
            "reason_code must be a safe stable code",
        )
        aborted_at = self._now()
        confirmed = self._rollback_transaction()
        self.state = None
        if not confirmed:
            self.terminal_status = "AMBIGUOUS"
            _hold(
                "HOLD_FENCE_ABORT_AMBIGUOUS",
                "ROLLBACK acknowledgement was not observed",
            )
        self.terminal_status = "ABORTED"
        return {
            "schema": ABORT_RECEIPT_SCHEMA,
            "status": "ABORTED_CONFIRMED",
            "session_id": session_id,
            "reason_code": reason_code,
            "release_config_sha256": self.release_config_sha256,
            "live_manifest_contract_sha256": self.manifest_contract_sha256,
            "backend_pid": state.backend_pid,
            "txid": state.txid,
            "fence_owner": state.fence_owner,
            "rollback_confirmed": True,
            "aborted_at": _iso(aborted_at),
        }


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def write_json_atomic_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    """Publish canonical JSON atomically without ever replacing an artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _expect(not path.is_symlink(), "HOLD_FENCE_IPC_PATH", str(path))
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    payload = _canonical_bytes(value) + b"\n"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise FenceOperatorHold(
                "HOLD_FENCE_IPC_REPLAY", str(path.name)
            ) from exc
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def load_json_object(path: Path) -> dict[str, Any]:
    _expect(
        path.is_file() and not path.is_symlink(),
        "HOLD_FENCE_IPC_PATH",
        str(path),
    )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FenceOperatorHold("HOLD_FENCE_IPC_SHAPE", path.name) from exc
    _expect(isinstance(value, dict), "HOLD_FENCE_IPC_SHAPE", path.name)
    return value


def build_ipc_request(
    *,
    action: str,
    sequence: int,
    session_id: str | None,
    payload: Mapping[str, Any],
    now: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    created_at = _utc(now)
    ttl = ABORT_REQUEST_TTL if action == "abort" else REQUEST_TTL
    unsigned = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id or uuid4().hex,
        "action": action,
        "sequence": sequence,
        "session_id": session_id,
        "created_at": _iso(created_at),
        "expires_at": _iso(created_at + ttl),
        "payload": _json_copy(payload, field="ipc request payload"),
    }
    return {**unsigned, "request_sha256": _sha256_json(unsigned)}


def verify_ipc_request(request: Mapping[str, Any], *, now: datetime) -> dict[str, Any]:
    expected = {
        "schema",
        "request_id",
        "action",
        "sequence",
        "session_id",
        "created_at",
        "expires_at",
        "payload",
        "request_sha256",
    }
    _expect(set(request) == expected, "HOLD_FENCE_IPC_SHAPE", "request keys")
    unsigned = {key: request[key] for key in expected - {"request_sha256"}}
    _expect(
        request.get("schema") == REQUEST_SCHEMA
        and _REQUEST_ID.fullmatch(str(request.get("request_id"))) is not None
        and request.get("action") in {"open", "watch", "close", "abort"}
        and isinstance(request.get("sequence"), int)
        and request.get("sequence") >= 0
        and isinstance(request.get("payload"), Mapping)
        and request.get("request_sha256") == _sha256_json(unsigned),
        "HOLD_FENCE_IPC_SHAPE",
        "request identity/hash",
    )
    created = _parse_time(request["created_at"], field="request created_at")
    expires = _parse_time(request["expires_at"], field="request expires_at")
    checked = _utc(now)
    expected_ttl = (
        ABORT_REQUEST_TTL if request.get("action") == "abort" else REQUEST_TTL
    )
    _expect(
        created <= checked < expires
        and expires - created == expected_ttl
        and checked - created <= expected_ttl,
        "HOLD_FENCE_IPC_STALE",
        str(request["request_id"]),
    )
    return dict(request)


class FenceIpcServer:
    """Single-threaded, ordered IPC dispatcher around one operator."""

    def __init__(
        self,
        *,
        ipc_dir: Path,
        operator: PostgreSQLFenceOperator,
        clock: Callable[[], datetime] | None = None,
        heartbeat_interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        self.root = ipc_dir.resolve()
        self.requests = self.root / "requests"
        self.responses = self.root / "responses"
        self.events = self.root / "events"
        for path in (self.requests, self.responses, self.events):
            path.mkdir(parents=True, exist_ok=True)
            _expect(not path.is_symlink(), "HOLD_FENCE_IPC_PATH", str(path))
        self.operator = operator
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.next_sequence = 0
        self.session_id: str | None = None
        self._last_heartbeat_monotonic = time.monotonic()
        self._refuse_ambiguous_recovery()

    def _refuse_ambiguous_recovery(self) -> None:
        events = sorted(self.events.glob("*.json"))
        statuses: dict[str, str] = {}
        for path in events:
            event = load_json_object(path)
            if event.get("schema") == STATE_EVENT_SCHEMA:
                statuses[str(event.get("session_id"))] = str(event.get("status"))
        ambiguous = [session for session, status in statuses.items() if status == "OPEN"]
        _expect(
            not ambiguous,
            "HOLD_FENCE_AMBIGUOUS_RECOVERY",
            "an earlier process ended with an unclosed transaction marker",
        )

    def _event(self, status: str, session_id: str, sequence: int) -> None:
        value = {
            "schema": STATE_EVENT_SCHEMA,
            "status": status,
            "session_id": session_id,
            "sequence": sequence,
            "recorded_at": _iso(_utc(self.clock())),
        }
        write_json_atomic_exclusive(
            self.events / f"{sequence:06d}-{status.lower()}-{session_id}.json", value
        )

    def _response(
        self,
        request: Mapping[str, Any],
        *,
        status: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        unsigned = {
            "schema": RESPONSE_SCHEMA,
            "status": status,
            "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "action": request["action"],
            "sequence": request["sequence"],
            "session_id": self.session_id,
            "responded_at": _iso(_utc(self.clock())),
            "payload": _json_copy(payload, field="ipc response payload"),
        }
        return {**unsigned, "response_sha256": _sha256_json(unsigned)}

    def _dispatch(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        action = request["action"]
        sequence = request["sequence"]
        _expect(
            sequence == self.next_sequence,
            "HOLD_FENCE_IPC_SEQUENCE",
            f"expected {self.next_sequence}; got {sequence}",
        )
        if action == "open":
            _expect(
                sequence == 0
                and isinstance(request.get("session_id"), str)
                and _SESSION_ID.fullmatch(str(request.get("session_id"))) is not None
                and self.session_id is None,
                "HOLD_FENCE_IPC_SEQUENCE",
                "open identity",
            )
            payload = request["payload"]
            _expect(
                set(payload)
                == {
                    "release_config_sha256",
                    "live_manifest_contract_sha256",
                }
                and payload["release_config_sha256"]
                == self.operator.release_config_sha256
                and payload["live_manifest_contract_sha256"]
                == self.operator.manifest_contract_sha256,
                "HOLD_FENCE_IPC_BINDING",
                "open release/manifest binding",
            )
            self.session_id = str(request["session_id"])
            result = self.operator.open(session_id=self.session_id)
            _expect(
                result.get("session_id") == self.session_id,
                "HOLD_FENCE_IPC_BINDING",
                "preallocated/open session id drift",
            )
            self._event("OPEN", self.session_id, sequence)
        else:
            _expect(
                self.session_id is not None
                and request.get("session_id") == self.session_id,
                "HOLD_FENCE_IPC_BINDING",
                "session_id",
            )
            if action == "watch":
                payload = request["payload"]
                _expect(
                    set(payload) == {"phase", "call_key", "run_genesis"},
                    "HOLD_FENCE_IPC_SHAPE",
                    "watch payload",
                )
                result = {
                    "fence_watch_receipt": self.operator.watch(
                        session_id=self.session_id,
                        phase=str(payload["phase"]),
                        call_key=str(payload["call_key"]),
                        run_genesis=payload["run_genesis"],
                    )
                }
            elif action == "close":
                _expect(
                    request["payload"]
                    == {
                        "fence_open_receipt_sha256": p1.sha256_json(
                            self.operator.state.open_receipt
                        )
                    },
                    "HOLD_FENCE_IPC_BINDING",
                    "close open-receipt binding",
                )
                result = self.operator.close(session_id=self.session_id)
                self._event("CLOSED", self.session_id, sequence)
            else:
                payload = request["payload"]
                _expect(
                    set(payload) == {"reason_code"},
                    "HOLD_FENCE_IPC_SHAPE",
                    "abort payload",
                )
                result = {
                    "fence_abort_receipt": self.operator.abort(
                        session_id=self.session_id,
                        reason_code=str(payload["reason_code"]),
                    )
                }
                self._event("ABORTED", self.session_id, sequence)
        self.next_sequence += 1
        return result

    def process_path(self, path: Path) -> dict[str, Any]:
        request = verify_ipc_request(load_json_object(path), now=_utc(self.clock()))
        _expect(
            path.name == f"{request['request_id']}.json",
            "HOLD_FENCE_IPC_PATH",
            path.name,
        )
        response_path = self.responses / path.name
        if response_path.exists():
            existing = load_json_object(response_path)
            _expect(
                existing.get("request_sha256") == request["request_sha256"],
                "HOLD_FENCE_IPC_REPLAY",
                path.name,
            )
            return existing
        try:
            payload = self._dispatch(request)
            response = self._response(request, status="PASS", payload=payload)
        except FenceOperatorHold as exc:
            if (
                self.session_id is not None
                and self.operator.terminal_status == "ABORTED"
                and self.operator.rollback_confirmed
            ):
                self._event("ABORTED", self.session_id, int(request["sequence"]))
            response = self._response(
                request,
                status="HOLD",
                payload={"code": exc.code, "detail": exc.detail},
            )
        write_json_atomic_exclusive(response_path, response)
        return response

    def process_pending(self) -> int:
        processed = 0
        pending = list(self.requests.glob("*.json"))

        def request_order(path: Path) -> tuple[int, str]:
            try:
                sequence = load_json_object(path).get("sequence")
            except FenceOperatorHold:
                sequence = None
            return (
                sequence if isinstance(sequence, int) and sequence >= 0 else 2**31,
                path.name,
            )

        for path in sorted(pending, key=request_order):
            if not (self.responses / path.name).exists():
                self.process_path(path)
                processed += 1
        return processed

    def serve_forever(self, *, poll_interval_seconds: float = 0.1) -> None:
        while self.operator.terminal_status not in {
            "CLOSED",
            "ABORTED",
            "AMBIGUOUS",
        }:
            self.process_pending()
            if self.session_id is not None:
                elapsed = time.monotonic() - self._last_heartbeat_monotonic
                if elapsed >= self.heartbeat_interval_seconds:
                    try:
                        self.operator.heartbeat(self.session_id)
                    except FenceOperatorHold:
                        if (
                            self.operator.terminal_status == "ABORTED"
                            and self.operator.rollback_confirmed
                        ):
                            self._event(
                                "ABORTED", self.session_id, self.next_sequence
                            )
                        raise
                    self._last_heartbeat_monotonic = time.monotonic()
            time.sleep(poll_interval_seconds)


def verify_ipc_response(
    response: Mapping[str, Any], *, request: Mapping[str, Any]
) -> dict[str, Any]:
    expected = {
        "schema",
        "status",
        "request_id",
        "request_sha256",
        "action",
        "sequence",
        "session_id",
        "responded_at",
        "payload",
        "response_sha256",
    }
    _expect(set(response) == expected, "HOLD_FENCE_IPC_SHAPE", "response keys")
    unsigned = {key: response[key] for key in expected - {"response_sha256"}}
    _expect(
        response.get("schema") == RESPONSE_SCHEMA
        and response.get("request_id") == request.get("request_id")
        and response.get("request_sha256") == request.get("request_sha256")
        and response.get("action") == request.get("action")
        and response.get("sequence") == request.get("sequence")
        and response.get("response_sha256") == _sha256_json(unsigned),
        "HOLD_FENCE_IPC_BINDING",
        "response request/hash binding",
    )
    _expect(
        response.get("status") == "PASS",
        str(response.get("payload", {}).get("code", "HOLD_FENCE_OPERATOR")),
        str(response.get("payload", {}).get("detail", "operator hold")),
    )
    return dict(response)


class FenceIpcClient:
    """Credential-free runner client; request files are exclusive and sealed."""

    def __init__(
        self,
        *,
        ipc_dir: Path,
        clock: Callable[[], datetime] | None = None,
        timeout_seconds: float = 10.0,
        pump: Callable[[], Any] | None = None,
    ) -> None:
        self.root = ipc_dir.resolve()
        self.requests = self.root / "requests"
        self.responses = self.root / "responses"
        self.requests.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.timeout_seconds = timeout_seconds
        self.pump = pump
        self.sequence = 0
        self.session_id: str | None = None
        self.open_receipt: Mapping[str, Any] | None = None

    def _exchange(
        self,
        action: str,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        request = build_ipc_request(
            action=action,
            sequence=self.sequence,
            session_id=self.session_id,
            payload=payload,
            now=_utc(self.clock()),
        )
        request_path = self.requests / f"{request['request_id']}.json"
        response_path = self.responses / request_path.name
        write_json_atomic_exclusive(request_path, request)
        # A durably published sequence is never reused when its response is
        # lost. This makes a sequence-1 abort possible after ambiguous open.
        self.sequence += 1
        deadline = time.monotonic() + (
            self.timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        while not response_path.exists():
            if self.pump is not None:
                self.pump()
            if time.monotonic() >= deadline:
                _hold("HOLD_FENCE_IPC_TIMEOUT", str(request["request_id"]))
            time.sleep(0.01)
        response = verify_ipc_response(
            load_json_object(response_path), request=request
        )
        if action == "open":
            session_id = response.get("session_id")
            _expect(
                isinstance(session_id, str)
                and _SESSION_ID.fullmatch(session_id) is not None
                and session_id == self.session_id,
                "HOLD_FENCE_IPC_BINDING",
                "open session id",
            )
        return response

    def open(
        self, *, release_config_sha256: str, live_manifest_contract_sha256: str
    ) -> dict[str, Any]:
        _expect(
            self.sequence == 0 and self.session_id is None,
            "HOLD_FENCE_SESSION",
            "open already attempted",
        )
        # Preallocate the identity before the operator can acquire a lock. A
        # lost response can therefore still be followed by a bound abort.
        self.session_id = f"fence-{uuid4().hex}"
        response = self._exchange(
            "open",
            {
                "release_config_sha256": release_config_sha256,
                "live_manifest_contract_sha256": live_manifest_contract_sha256,
            },
        )
        result = dict(response["payload"])
        self.open_receipt = result["fence_open_receipt"]
        return result

    def _confirmed_abort_event(self) -> Mapping[str, Any] | None:
        if self.session_id is None:
            return None
        for path in sorted((self.root / "events").glob("*.json")):
            event = load_json_object(path)
            if (
                event.get("schema") == STATE_EVENT_SCHEMA
                and event.get("status") == "ABORTED"
                and event.get("session_id") == self.session_id
            ):
                return event
        return None

    def abort_pending_open(self, *, reason_code: str) -> dict[str, Any]:
        """Abort a preallocated session whose open response was not confirmed."""

        _expect(
            self.session_id is not None and self.open_receipt is None,
            "HOLD_FENCE_SESSION",
            "no unconfirmed open session",
        )
        _expect(
            _SAFE_REASON_CODE.fullmatch(reason_code) is not None,
            "HOLD_FENCE_ABORT_REASON",
            "reason_code must be a safe stable code",
        )
        event = self._confirmed_abort_event()
        if event is not None:
            return {
                "fence_abort_receipt": {
                    "schema": ABORT_RECEIPT_SCHEMA,
                    "status": "ABORTED_CONFIRMED",
                    "session_id": self.session_id,
                    "reason_code": reason_code,
                    "rollback_confirmed": True,
                    "recovered_from_operator_event_sha256": p1.sha256_json(event),
                }
            }
        try:
            response = self._exchange(
                "abort",
                {"reason_code": reason_code},
                timeout_seconds=60.0,
            )
            return dict(response["payload"])
        except FenceOperatorHold:
            event = self._confirmed_abort_event()
            if event is None:
                raise
            return {
                "fence_abort_receipt": {
                    "schema": ABORT_RECEIPT_SCHEMA,
                    "status": "ABORTED_CONFIRMED",
                    "session_id": self.session_id,
                    "reason_code": reason_code,
                    "rollback_confirmed": True,
                    "recovered_from_operator_event_sha256": p1.sha256_json(event),
                }
            }

    def watch(
        self, *, phase: str, call_key: str, run_genesis: Mapping[str, Any]
    ) -> dict[str, Any]:
        _expect(self.session_id is not None, "HOLD_FENCE_SESSION", "not open")
        response = self._exchange(
            "watch",
            {"phase": phase, "call_key": call_key, "run_genesis": run_genesis},
        )
        return dict(response["payload"]["fence_watch_receipt"])

    def close(self) -> dict[str, Any]:
        _expect(
            self.session_id is not None and self.open_receipt is not None,
            "HOLD_FENCE_SESSION",
            "not open",
        )
        response = self._exchange(
            "close",
            {"fence_open_receipt_sha256": p1.sha256_json(self.open_receipt)},
        )
        return dict(response["payload"])

    def abort(self, *, reason_code: str) -> dict[str, Any]:
        _expect(
            self.session_id is not None and self.open_receipt is not None,
            "HOLD_FENCE_SESSION",
            "not open",
        )
        response = self._exchange("abort", {"reason_code": reason_code})
        return dict(response["payload"])


@dataclass(frozen=True)
class IpcFenceWatcher:
    """Adapter matching ``s277_c1_p1.FenceWatcher`` without a DB credential."""

    client: FenceIpcClient

    def verify(
        self,
        *,
        phase: str,
        replica: Any,
        call_key: str,
        run_genesis: Mapping[str, Any],
        fence_open_receipt: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        _expect(
            self.client.open_receipt == fence_open_receipt,
            "HOLD_FENCE_IPC_BINDING",
            "runner/open receipt drift",
        )
        return self.client.watch(
            phase=phase, call_key=call_key, run_genesis=run_genesis
        )


def _load_json(path: str) -> dict[str, Any]:
    return load_json_object(Path(path).resolve())


def _cli_serve(args: argparse.Namespace) -> int:
    release = _load_json(args.release_config)
    contract = _load_json(args.live_manifest_contract)
    snapshot_provider = BoundPostgrestSnapshotProvider(
        pre_path=Path(args.postgrest_pre_snapshot),
        post_path=Path(args.postgrest_post_snapshot),
    )
    database_url = os.environ.get(args.database_url_env)
    _expect(
        bool(database_url),
        "HOLD_FENCE_OPERATOR_CREDENTIAL",
        f"missing operator-only env {args.database_url_env}",
    )
    try:
        import psycopg2
    except ImportError as exc:
        raise FenceOperatorHold(
            "HOLD_FENCE_OPERATOR_DEPENDENCY", "psycopg2"
        ) from exc
    connection = psycopg2.connect(database_url, connect_timeout=15, sslmode="require")
    semantic = release.get("derived_config", {}).get("target_semantic_config")
    _expect(
        isinstance(semantic, Mapping),
        "HOLD_FENCE_RELEASE_IDENTITY",
        "target semantic config",
    )
    visual = "on" if semantic.get("generation", {}).get(
        "visual_assets_registry"
    ) else "off"
    capture = P1ReadonlyManifestCapture(
        project_ref=args.project_ref,
        visual_assets_registry=visual,
        postgrest_snapshot_provider=snapshot_provider,
    )
    operator = PostgreSQLFenceOperator(
        connection=connection,
        project_ref=args.project_ref,
        target_semantic_config=semantic,
        release_config_sha256=p1.sha256_json(release),
        manifest_contract=contract,
        capture_manifest=capture,
    )
    server = FenceIpcServer(ipc_dir=Path(args.ipc_dir), operator=operator)
    try:
        if args.once:
            server.process_pending()
        else:
            server.serve_forever()
    finally:
        connection.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve = subparsers.add_parser("serve")
    serve.add_argument("--ipc-dir", required=True)
    serve.add_argument("--release-config", required=True)
    serve.add_argument("--live-manifest-contract", required=True)
    serve.add_argument("--postgrest-pre-snapshot", required=True)
    serve.add_argument("--postgrest-post-snapshot", required=True)
    serve.add_argument("--project-ref", required=True)
    serve.add_argument("--database-url-env", default="P1_FENCE_DATABASE_URL")
    serve.add_argument("--once", action="store_true")
    serve.set_defaults(handler=_cli_serve)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except FenceOperatorHold as exc:
        print(json.dumps({"status": "HOLD", "code": exc.code, "detail": exc.detail}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
