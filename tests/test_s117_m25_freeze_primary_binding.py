from __future__ import annotations

from pathlib import Path

from scripts import s117_m25_freeze_primary_binding as freeze


def _doc(identifier: str, status: str) -> dict:
    return {"id": identifier, "status": status, "source_pdf_sha256": "a" * 64}


def test_primary_binding_taxonomy_is_fail_closed() -> None:
    sha = "a" * 64
    absent = freeze._classify_primary(sha, {})
    active = freeze._classify_primary(sha, {sha: [_doc("active", "active")]})
    inactive = freeze._classify_primary(sha, {sha: [_doc("retired", "retired")]})
    ambiguous = freeze._classify_primary(
        sha,
        {sha: [_doc("one", "active"), _doc("two", "active")]},
    )
    assert absent["terminal"] == "primary_absent_pdf_sha"
    assert active["terminal"] == "primary_unique_active_pdf_sha"
    assert active["document_id"] == "active"
    assert inactive["terminal"] == "primary_non_active_pdf_sha"
    assert inactive["status"] == "retired"
    assert ambiguous["terminal"] == "primary_ambiguous_pdf_sha"
    assert ambiguous["document_id"] is None
    assert len({row["receipt_sha256"] for row in (absent, active, inactive, ambiguous)}) == 4


def test_primary_freezer_has_no_external_or_manufacturer_branches() -> None:
    source = Path(freeze.__file__).read_text(encoding="utf-8").casefold()
    for forbidden in (
        "psycopg2",
        "dotenv",
        "anthropic",
        "voyage",
        "hochiki",
        "notifier",
        "aritech",
    ):
        assert forbidden not in source
