from __future__ import annotations

from pathlib import Path

import pytest

from scripts import s117_m25_project_document_binding as project


SHA = "a" * 64


def _primary_absent() -> dict:
    return {
        "extraction_sha256": SHA,
        "terminal": "primary_absent_pdf_sha",
        "document_id": None,
        "status": None,
        "receipt_sha256": "p" * 64,
    }


def _chunk(document_id: str | None) -> dict:
    return {"document_id": document_id, "parent_id": None}


def _doc(value: object, status: str = "active") -> dict:
    return {"id": "doc", "source_pdf_sha256": value, "status": status}


@pytest.mark.parametrize(
    ("chunks", "documents", "terminal"),
    [
        ([], {}, "fallback_no_base_chunks"),
        ([_chunk(None)], {}, "fallback_null_document_id"),
        ([_chunk("a"), _chunk("b")], {}, "fallback_ambiguous_document_id"),
        ([_chunk("doc")], {}, "fallback_missing_document"),
        (
            [_chunk("doc")],
            {"doc": [_doc("backfill:" + "b" * 64), _doc("backfill:" + "b" * 64)]},
            "fallback_ambiguous_document_row",
        ),
        (
            [_chunk("doc")],
            {"doc": [_doc("backfill:" + "b" * 64, "superseded")]},
            "fallback_non_active_document",
        ),
        (
            [_chunk("doc")],
            {"doc": [_doc("b" * 64)]},
            "fallback_conflicting_valid_pdf_sha",
        ),
        (
            [_chunk("doc")],
            {"doc": [_doc("backfill:" + "b" * 64)]},
            "fallback_unique_active_backfill_binding",
        ),
        ([_chunk("doc")], {"doc": [_doc(None)]}, "fallback_null_pdf_sha"),
        ([_chunk("doc")], {"doc": [_doc("")]}, "fallback_empty_pdf_sha"),
        ([_chunk("doc")], {"doc": [_doc("legacy")]}, "fallback_malformed_pdf_sha"),
    ],
)
def test_fallback_precedence_is_closed(chunks: list, documents: dict, terminal: str) -> None:
    result = project._classify_binding(_primary_absent(), chunks, documents)
    assert result["terminal"] == terminal
    assert (result["document_id"] == "doc") is (
        terminal == "fallback_unique_active_backfill_binding"
    )


def test_equal_canonical_sha_after_primary_absent_is_internal_no_go() -> None:
    with pytest.raises(RuntimeError, match="equal canonical"):
        project._classify_binding(
            _primary_absent(),
            [_chunk("doc")],
            {"doc": [_doc(SHA)]},
        )


def test_primary_terminals_never_enter_fallback() -> None:
    row = {
        **_primary_absent(),
        "terminal": "primary_unique_active_pdf_sha",
        "document_id": "primary-doc",
        "status": "active",
    }
    result = project._classify_binding(row, [_chunk(None)], {})
    assert result["terminal"] == "primary_unique_active_pdf_sha"
    assert result["document_id"] == "primary-doc"
    assert result["binding_origin"] == "primary_pdf_sha"


def test_inverse_document_collision_fails_closed_for_every_raw() -> None:
    first = project._classify_binding(
        _primary_absent(),
        [_chunk("doc")],
        {"doc": [_doc("backfill:" + "b" * 64)]},
    )
    second_primary = {**_primary_absent(), "extraction_sha256": "c" * 64}
    second = project._classify_binding(
        second_primary,
        [_chunk("doc")],
        {"doc": [_doc("backfill:" + "b" * 64)]},
    )

    resolved = project._apply_inverse_uniqueness([first, second])

    assert {row["terminal"] for row in resolved} == {
        "fallback_shared_document_id_across_extractions"
    }
    assert all(row["document_id"] is None for row in resolved)
    assert all(row["observed_document_id"] == "doc" for row in resolved)
    assert all(
        row["shared_extraction_sha256"] == ["a" * 64, "c" * 64]
        for row in resolved
    )


def test_derived_preservation_checks_detect_mutation_and_extra_rows() -> None:
    documents = [{"id": "doc", "source_pdf_sha256": "b" * 64, "status": "active"}]
    chunks = [{"id": "chunk", "content": "source"}]
    aliases = [{"id": "doc", "source_pdf_sha256": "a" * 64, "status": "active"}]
    receipt = {"gzip_sha256": "frozen", "canonical_jsonl_sha256": "logical"}

    valid = project._derived_preservation_checks(
        documents,
        chunks,
        aliases,
        documents + aliases,
        chunks,
        receipt,
        receipt,
    )
    assert all(valid.values())

    invalid = project._derived_preservation_checks(
        documents,
        chunks,
        aliases,
        documents + aliases + [{"id": "unexpected"}],
        [{"id": "chunk", "content": "mutated"}],
        receipt,
        receipt,
    )
    assert not invalid["source_chunks_byte_logically_identical"]
    assert not invalid["only_exact_safe_aliases_added"]
    assert not invalid["derived_document_count_exact"]


def test_semantic_delta_gate_reconciles_every_downstream_stage() -> None:
    eligible = 10
    funnel = {
        "total_local": 0,
        "policy_eligible": 0,
        "target_document_resolved": 10,
        "target_document_active": 10,
        "extraction_hit": 10,
        "content_hit": 8,
        "structure_hit": 7,
        "metadata_hit": 4,
        "unique_donor": 3,
        "context_reuse_candidate": 2,
        "embedding_reuse_candidate": 1,
    }
    terminals = {
        "policy_excluded_register_only": 0,
        "policy_excluded_language": 0,
        "target_document_unresolved": -10,
        "document_status_excluded": 0,
        "no_extraction_donor": 0,
        "content_miss": 2,
        "structure_miss": 1,
        "metadata_miss": 3,
        "ambiguous_donor": 1,
        "unique_donor_context_missing": 1,
        "unique_donor_embedding_missing_or_wrong_dim": 1,
        "legacy_context_and_embedding_candidate": 1,
    }
    assert all(project._semantic_delta_checks(funnel, terminals, eligible).values())


def test_semantic_delta_gate_rejects_noop() -> None:
    checks = project._semantic_delta_checks({}, {}, eligible_rows=10)
    assert not all(checks.values())
    assert not checks["unresolved_delta_exact"]
    assert not checks["resolved_active_extraction_delta_exact"]


def test_projection_runner_has_no_external_or_manufacturer_branches() -> None:
    source = Path(project.__file__).read_text(encoding="utf-8").casefold()
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
