import copy
import json

import pytest

from src.rag import evidence_derivation as derivation


ORIGINAL = "Life time 105 operations"
DERIVED = "Life time 10<sup>5</sup> operations"


def _registry():
    core = {
        "chunk_id": "11111111-1111-4111-8111-111111111111",
        "extraction_sha256": "a" * 64,
        "source_file": "manual.pdf",
        "chunk_index": 7,
        "original_chunk_content_sha256": derivation._sha(ORIGINAL.encode()),
        "derived_chunk_content_sha256": derivation._sha(DERIVED.encode()),
        "derived_content": DERIVED,
        "source_pdf_receipt_sha256s": ["b" * 64],
        "derivation_manifest_sha256": "c" * 64,
    }
    entry = {
        **core,
        "chunk_derivation_sha256": derivation._sha(
            derivation._canonical_bytes(core)
        ),
    }
    body = {
        "schema": derivation.REGISTRY_SCHEMA,
        "version": 5,
        "contract": derivation.REGISTRY_CONTRACT,
        "source_derivation_contract": "numeric_pdf_superscript_overlay_v1",
        "source_discovery_sha256": "d" * 64,
        "document_manifests": [],
        "source_pdf_receipt_count": 1,
        "bound_source_pdf_receipt_count": 1,
        "absent_source_pdf_receipt_count": 0,
        "absent_source_pdf_receipts": [],
        "entry_count": 1,
        "entries": [entry],
    }
    return {**body, "artifact_sha256": derivation._sha(derivation._canonical_bytes(body))}


def _path(tmp_path, payload=None):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload or _registry()), encoding="utf-8")
    derivation.clear_registry_cache()
    return path


def _row(**changes):
    row = {
        "id": "11111111-1111-4111-8111-111111111111",
        "extraction_sha256": "a" * 64,
        "source_file": "manual",
        "chunk_index": 7,
        "page_number": 5,
        "content": ORIGINAL,
        "similarity": 0.9,
    }
    row.update(changes)
    return row


def test_checked_in_registry_is_content_addressed_and_complete():
    registry = derivation.load_registry()
    assert derivation.validate_registry(registry) == []
    assert registry["source_pdf_receipt_count"] == 33
    assert registry["bound_source_pdf_receipt_count"] == 30
    assert registry["absent_source_pdf_receipt_count"] == 3
    assert registry["entry_count"] == 13


def test_disabled_path_is_exact_identity_and_reads_no_registry(monkeypatch):
    rows = [{"id": "same", "content": "105"}]
    monkeypatch.setattr(
        derivation,
        "load_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("registry read")),
    )
    output, trace = derivation.apply_evidence_derivations_with_trace(
        rows, enabled=False
    )
    assert output is rows
    assert trace["status"] == "disabled"


def test_exact_chunk_identity_applies_to_copy_and_is_idempotent(tmp_path):
    path = _path(tmp_path)
    row = _row()
    before = copy.deepcopy(row)
    output, trace = derivation.apply_evidence_derivations_with_trace(
        [row], enabled=True, registry_path=path
    )

    assert row == before
    assert output[0]["content"] == DERIVED
    assert output[0]["evidence_derivation_source_receipts"] == ["b" * 64]
    assert trace["modified_rows"] == 1

    second, second_trace = derivation.apply_evidence_derivations_with_trace(
        output, enabled=True, registry_path=path
    )
    assert second[0]["content"] == DERIVED
    assert second_trace["modified_rows"] == 0


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"source_file": "other.pdf"}, "source_file_mismatch"),
        ({"content": "same semantics, wrong bytes"}, "original_content_hash_mismatch"),
    ],
)
def test_source_or_content_mismatch_abstains(tmp_path, changes, reason):
    path = _path(tmp_path)
    row = _row(**changes)
    output, trace = derivation.apply_evidence_derivations_with_trace(
        [row], enabled=True, registry_path=path
    )
    assert output == [row]
    assert trace["modified_rows"] == 0
    assert trace["abstentions"][0]["reason"] == reason


def test_wrong_ordinal_has_no_applicable_derivation(tmp_path):
    path = _path(tmp_path)
    row = _row(chunk_index=8)
    output, trace = derivation.apply_evidence_derivations_with_trace(
        [row], enabled=True, registry_path=path
    )
    assert output == [row]
    assert trace["status"] == "no_applicable_derivations"


def test_tampered_registry_fails_closed(tmp_path):
    registry = _registry()
    registry["entries"][0]["derived_content"] = "tampered"
    path = _path(tmp_path, registry)
    with pytest.raises(RuntimeError, match="invalid evidence derivation registry"):
        derivation.load_registry(str(path))
    derivation.clear_registry_cache()


def test_registry_rejects_receipt_reuse_across_bound_chunks():
    registry = _registry()
    duplicate = copy.deepcopy(registry["entries"][0])
    duplicate["chunk_id"] = "22222222-2222-4222-8222-222222222222"
    duplicate["chunk_index"] = 8
    core = {
        key: value
        for key, value in duplicate.items()
        if key != "chunk_derivation_sha256"
    }
    duplicate["chunk_derivation_sha256"] = derivation._sha(
        derivation._canonical_bytes(core)
    )
    registry["entries"].append(duplicate)
    registry["entry_count"] = 2
    body = {
        key: value for key, value in registry.items() if key != "artifact_sha256"
    }
    registry["artifact_sha256"] = derivation._sha(
        derivation._canonical_bytes(body)
    )

    assert "duplicate_bound_source_receipts" in derivation.validate_registry(
        registry
    )


def test_registry_rejects_duplicate_absent_receipts():
    registry = _registry()
    absent = {
        "source_pdf_receipt_sha256": "d" * 64,
        "reason": "exact_source_line_absent_from_live_chunks_v2",
    }
    registry["absent_source_pdf_receipts"] = [absent, copy.deepcopy(absent)]
    registry["absent_source_pdf_receipt_count"] = 1
    registry["source_pdf_receipt_count"] = 2
    body = {
        key: value for key, value in registry.items() if key != "artifact_sha256"
    }
    registry["artifact_sha256"] = derivation._sha(
        derivation._canonical_bytes(body)
    )

    assert "duplicate_absent_source_receipts" in derivation.validate_registry(
        registry
    )
