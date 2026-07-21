from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "supabase/migrations/20260721190847_reconcile_hp011_v04_v07_lifecycle.sql"
)
ROLLBACK = (
    ROOT
    / "supabase/rollbacks/20260721190847_reconcile_hp011_v04_v07_lifecycle.sql"
)

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
OLD_DOCUMENT = "e98e05ff-ee1d-5341-869a-65768855dae9"
NEW_DOCUMENT = "494e71be-873b-48c1-adb3-a21a122da111"
OLD_PAGE_63 = "77d07600-c619-4ea0-b1ab-0683ddb79697"
NEW_PAGE_63 = "475a8f18-7c69-4c7a-8111-45bd67334c96"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snapshot_pairs(sql: str) -> tuple[tuple[str, str], ...]:
    block = re.search(
        r"INSERT INTO hp011_v07_v04_duplicate_snapshot\s*\(.*?\)\s*"
        r"VALUES\s*(.*?)\s*;\s*DO\s+\$hp011_lifecycle(?:_rollback)?\$",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert block is not None
    pairs = re.findall(
        rf"\('({UUID})',\s*'({UUID})'\)",
        block.group(1),
        re.IGNORECASE,
    )
    return tuple((left.lower(), right.lower()) for left, right in pairs)


def _snapshot_sha256(pairs: tuple[tuple[str, str], ...]) -> str:
    payload = "\n".join(f"{left}->{right}" for left, right in sorted(pairs))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def test_migration_and_rollback_freeze_the_same_exact_before_state() -> None:
    migration_pairs = _snapshot_pairs(_read(MIGRATION))
    rollback_pairs = _snapshot_pairs(_read(ROLLBACK))

    assert migration_pairs == rollback_pairs
    assert len(migration_pairs) == 38
    assert len({left for left, _ in migration_pairs}) == 38
    assert (NEW_PAGE_63, OLD_PAGE_63) in migration_pairs
    assert _snapshot_sha256(migration_pairs) == (
        "388f54ce86bbfcc340cd58fed8cab49c23015a70d50211468f460f95d1aceb7b"
    )


def test_migration_is_one_short_fail_closed_transaction() -> None:
    sql = _read(MIGRATION)
    lowered = sql.lower()

    assert len(re.findall(r"(?im)^\s*begin\s*;", sql)) == 1
    assert re.search(r"(?im)^\s*commit\s*;\s*(?:--.*\s*)*\Z", sql)
    assert "set local lock_timeout = '5s';" in lowered
    assert "set local statement_timeout = '30s';" in lowered
    assert "create temporary table hp011_v07_v04_duplicate_snapshot" in lowered
    assert "on commit drop" in lowered
    assert "order by d.id" in lowered and "order by c.id" in lowered
    assert lowered.count("for update;") == 2
    assert lowered.count("raise exception") >= 13

    first_update = lowered.index("update public.documents")
    for guard in (
        "document identity or lifecycle precondition drift",
        "source partition precondition drift",
        "duplicate topology precondition drift",
        "frozen duplicate snapshot does not match live state",
        "page-63 source contract drift",
    ):
        assert lowered.index(guard) < first_update


def test_migration_freezes_identity_partition_and_duplicate_topology() -> None:
    sql = _read(MIGRATION)

    for value in (
        OLD_DOCUMENT,
        NEW_DOCUMENT,
        "ccabe3df906990c9b95d0d180d811e0444278089d4ce30678d86948cb197e93e",
        "914ceacf8395729f73876cb9e397a8cb3154d70ba67903b6e055f2b4398be573",
        "HLSI-MN-103_RP1r-Supra_lr",
        "v.04",
        "v.07",
        "2013-11-01",
        "2018-05-01",
        "Notifier",
        "RP1r",
        "Lifecycle precedence intentionally deferred.",
        "Lifecycle precedence resolved by migration 20260721190847",
        OLD_PAGE_63,
        NEW_PAGE_63,
        "position('t.A' IN content) > 0",
        "position('t.H' IN content) > 0",
    ):
        assert value in sql

    for expected_count in (190, 94, 96, 43, 42, 40, 38, 3, 4):
        assert re.search(rf"<>\s*{expected_count}\b", sql)

    assert "c.duplicate_of IS DISTINCT FROM expected.previous_duplicate_of" in sql
    assert "target.document_id IS DISTINCT FROM old_document" in sql
    assert "target.extraction_sha256 IS DISTINCT FROM old_extraction" in sql


def test_migration_changes_only_lifecycle_and_cross_revision_dedupe() -> None:
    sql = _read(MIGRATION)
    lowered = sql.lower()

    assert lowered.count("update public.documents") == 2
    assert lowered.count("update public.chunks_v2 as c") == 1
    assert not re.search(r"(?im)^\s*(?:delete|truncate|alter|drop)\b", sql)
    assert not re.search(r"(?im)^\s*create\s+table\s+public\.", sql)
    assert not re.search(r"(?im)^\s*insert\s+into\s+public\.", sql)

    chunk_update = re.search(
        r"UPDATE public\.chunks_v2 AS c\s+(.*?)GET DIAGNOSTICS changed = ROW_COUNT;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert chunk_update is not None
    update_body = chunk_update.group(1).lower()
    assert "set duplicate_of = null" in update_body
    set_clause = update_body.split("from pg_temp.", 1)[0]
    for forbidden in (
        "content",
        "context",
        "embedding",
        "search_vector",
        "document_id =",
        "extraction_sha256 =",
    ):
        assert forbidden not in set_clause

    document_updates = re.findall(
        r"UPDATE public\.documents\s+(.*?)GET DIAGNOSTICS changed = ROW_COUNT;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert len(document_updates) == 2
    assignments = "\n".join(document_updates).lower()
    for forbidden in (
        "revision =",
        "revision_date =",
        "source_pdf_sha256 =",
        "document_family =",
        "manufacturer =",
        "product_model =",
    ):
        assert forbidden not in assignments
    assert assignments.count("notes = replace(") == 2


def test_postconditions_preserve_intra_revision_dedupe_and_open_v07_page_63() -> None:
    sql = _read(MIGRATION)

    assert "WHERE id = old_document\n           AND status = 'superseded'" in sql
    assert "WHERE id = new_document\n           AND status = 'active'" in sql
    assert re.search(
        r"document_id = new_document AND duplicate_of IS NOT NULL\) <> 4",
        sql,
    )
    assert "c.document_id = new_document\n               AND target.document_id = old_document" in sql
    assert "id = new_page_63\n               AND document_id = new_document\n               AND duplicate_of IS NULL" in sql
    assert "OR target.duplicate_of IS NOT NULL" in sql
    assert "OR target.id = c.id" in sql


def test_manual_rollback_is_atomic_exact_and_not_auto_applied() -> None:
    sql = _read(ROLLBACK)
    lowered = sql.lower()

    assert ROLLBACK.parent.name == "rollbacks"
    assert ROLLBACK.parent != MIGRATION.parent
    assert len(re.findall(r"(?im)^\s*begin\s*;", sql)) == 1
    assert re.search(r"(?im)^\s*commit\s*;\s*\Z", sql)
    assert "manual rollback only" in lowered
    assert "set local lock_timeout = '5s';" in lowered
    assert "set local statement_timeout = '30s';" in lowered
    assert lowered.count("for update;") == 2
    assert lowered.count("update public.documents") == 2
    assert lowered.count("update public.chunks_v2 as c") == 1
    assert "set duplicate_of = expected.previous_duplicate_of" in lowered
    assert "set status = 'active'" in lowered
    assert "set supersedes_id = null" in lowered
    assert "notes = old_notes_before" in lowered
    assert "notes = new_notes_before" in lowered
    assert "rollback dedupe restore count drift" in lowered
    assert "rollback postcondition failed" in lowered
    assert re.search(
        r"document_id = new_document AND duplicate_of IS NOT NULL\) <> 42",
        sql,
    )
