from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import s117_m26_freeze_legacy_cohorts as freezer


SHA = "a" * 64


def _local() -> dict:
    row = {
        "id": "local-1",
        "extraction_sha256": SHA,
        "content": "contenido",
        "section_title": "Título",
        "section_path": "Manual > Título",
        "page_number": 4,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": "0x1.0000000000000p-1",
        "preterminal": None,
        "context_input_sha256": "c" * 64,
    }
    for field in freezer.m2.METADATA_FIELDS:
        row[field] = f"meta-{field}"
    return row


def _donor() -> dict:
    row = {
        "id": "donor-1",
        "extraction_sha256": SHA,
        "content": "contenido",
        "section_title": "Título",
        "section_path": "Manual > Título",
        "page_number": 4,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": "0x1.0000000000000p-1",
        "parent_id": None,
        "context": "Contexto técnico",
        "embedding_present": True,
        "embedding_dimensions": freezer.m2.embed.EMBED_DIMENSIONS,
    }
    for field in freezer.m2.METADATA_FIELDS:
        row[field] = f"meta-{field}"
    return row


def test_strict_pairs_replays_legacy_receipt_schemas() -> None:
    local = _local()
    donor = _donor()
    result = freezer._strict_pairs(
        [{"id": "doc", "source_pdf_sha256": SHA, "status": "active"}],
        [donor],
        [local],
    )

    assert result["membership"] == {"local-1": "donor-1"}
    context_receipt = {
        "id": "local-1",
        "context_sha256": hashlib.sha256(
            donor["context"].encode("utf-8")
        ).hexdigest(),
        "context_input_sha256": "c" * 64,
    }
    expected_context = hashlib.sha256(
        freezer._canonical(context_receipt) + b"\n"
    ).hexdigest()
    assert result["legacy_context_manifest_sha256"] == expected_context


def test_strict_pairs_keeps_metadata_selector_inside_freezer_only() -> None:
    local = _local()
    donor = _donor()
    donor[freezer.m2.METADATA_FIELDS[0]] = "different"
    result = freezer._strict_pairs(
        [{"id": "doc", "source_pdf_sha256": SHA, "status": "active"}],
        [donor],
        [local],
    )
    assert result["membership"] == {}


def test_strict_pairs_excludes_policy_and_nonactive_targets() -> None:
    local = _local()
    local["preterminal"] = "policy_excluded_language"
    assert freezer._strict_pairs(
        [{"id": "doc", "source_pdf_sha256": SHA, "status": "active"}],
        [_donor()],
        [local],
    )["membership"] == {}

    local["preterminal"] = None
    assert freezer._strict_pairs(
        [{"id": "doc", "source_pdf_sha256": SHA, "status": "retired"}],
        [_donor()],
        [local],
    )["membership"] == {}


def test_pair_manifest_is_order_independent_and_commits_donor() -> None:
    first = freezer._membership_rows({"b": "d2", "a": "d1"})
    second = freezer._membership_rows({"a": "d1", "b": "d2"})
    assert first == second
    assert freezer._membership_manifest(first) == freezer._membership_manifest(second)

    changed = freezer._membership_rows({"a": "other", "b": "d2"})
    assert freezer._membership_manifest(first) != freezer._membership_manifest(changed)


def test_freezer_source_has_no_external_access() -> None:
    source = Path(freezer.__file__).read_text(encoding="utf-8").casefold()
    for forbidden in ("psycopg2", "dotenv", "httpx", "anthropic", "voyageai"):
        assert forbidden not in source
