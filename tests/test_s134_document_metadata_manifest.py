from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from scripts import s134_build_document_metadata_manifest as audit


EXTRACTION = "a" * 64
DOCUMENT = "00000000-0000-0000-0000-000000000001"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(
    tmp_path: Path,
    *,
    second_manufacturer: str | None = None,
    product_model: str | None = "MODEL-1",
) -> dict:
    design = tmp_path / "design.md"
    design.write_text("frozen design\n", encoding="utf-8")
    bindings = {
        "status": "GO",
        "generation": {"materialization_id": "materialization-1"},
        "manifests": {"entries_sha256": "b" * 64},
        "entries": [
            {
                "document_id": DOCUMENT,
                "extraction_sha256": EXTRACTION,
                "binding_status": "bound_active_physical_sha_verified",
            }
        ],
    }
    binding_path = tmp_path / "bindings.json"
    _write_json(binding_path, bindings)
    rows = [
        {"kind": "document", "id": DOCUMENT},
        {
            "kind": "chunk",
            "id": "chunk-1",
            "parent_id": None,
            "document_id": DOCUMENT,
            "extraction_sha256": EXTRACTION,
            "manufacturer": "Maker",
            "product_model": product_model,
            "source_file": "manual.pdf",
            "distributor": None,
            "doc_type": None,
            "category": "fire",
        },
    ]
    if second_manufacturer is not None:
        rows.append(
            {
                **rows[-1],
                "id": "chunk-2",
                "manufacturer": second_manufacturer,
            }
        )
    logical = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in rows
    )
    snapshot = tmp_path / "snapshot.jsonl.gz"
    with gzip.GzipFile(filename=str(snapshot), mode="wb", mtime=0) as stream:
        stream.write(logical)

    base_chunks = 1 + int(second_manufacturer is not None)
    return {
        "design": {"path": "design.md", "sha256": audit.file_sha(design)},
        "frozen_inputs": {
            "snapshot": {
                "path": "snapshot.jsonl.gz",
                "sha256": audit.file_sha(snapshot),
                "canonical_jsonl_sha256": hashlib.sha256(logical).hexdigest(),
                "documents": 1,
                "chunks": base_chunks,
            },
            "candidate_bindings": {
                "path": "bindings.json",
                "sha256": audit.file_sha(binding_path),
                "materialization_id": "materialization-1",
            },
        },
        "contract": {
            "authority": "legacy_v2_unanimous_active_shadow_v1",
            "required_fields": ["manufacturer", "product_model", "source_file"],
            "optional_fields": ["distributor", "doc_type", "category"],
            "active_binding_statuses": ["bound_active_physical_sha_verified"],
        },
        "expected_population": {
            "active_extraction_bindings": 1,
            "distinct_active_documents": 1,
            "active_documents_with_one_extraction": 1,
            "active_documents_with_two_extractions": 0,
            "source_base_chunks": base_chunks,
            "field_conflicts": 0,
            "missing_required_values": 0,
        },
        "authorization": {"models": False, "database": False},
        "cost": {"model_calls": 0, "database_reads": 0},
    }


def test_synthetic_manifest_is_deterministic_and_metadata_only(tmp_path: Path) -> None:
    prereg = _fixture(tmp_path)
    first = audit.build_manifest(prereg, root=tmp_path)
    second = audit.build_manifest(prereg, root=tmp_path)
    assert audit.canonical_bytes(first) == audit.canonical_bytes(second)
    assert first["status"] == "GO"
    assert first["population"]["source_base_chunks"] == 1
    row = first["entries"][0]
    assert row["manufacturer"] == "Maker"
    assert row["distributor"] is None
    core = {key: value for key, value in row.items() if key != "metadata_receipt_sha256"}
    assert row["metadata_receipt_sha256"] == audit.canonical_sha(core)
    forbidden = {"content", "context", "question", "answer", "embedding"}
    assert not (set(row) & forbidden)


def test_conflicting_metadata_fails_closed(tmp_path: Path) -> None:
    prereg = _fixture(tmp_path, second_manufacturer="Other Maker")
    with pytest.raises(RuntimeError, match="conflict count drift"):
        audit.build_manifest(prereg, root=tmp_path)


def test_missing_required_metadata_fails_closed(tmp_path: Path) -> None:
    prereg = _fixture(tmp_path, product_model=None)
    with pytest.raises(RuntimeError, match="required document metadata missing"):
        audit.build_manifest(prereg, root=tmp_path)


def test_real_manifest_gate_and_receipts() -> None:
    path = audit.ROOT / "evals/s134_document_metadata_manifest_seed1_v1.json"
    if not path.exists():
        pytest.skip("S134 evidence has not been executed yet")
    payload = audit.load_json(path)
    assert payload["status"] == "GO"
    assert payload["population"] == {
        "active_extraction_bindings": 1002,
        "distinct_active_documents": 999,
        "active_documents_by_extraction_count": {"1": 996, "2": 3},
        "source_base_chunks": 24803,
        "field_conflicts": 0,
        "missing_required_values": 0,
    }
    assert all(payload["checks"].values())
    for row in payload["entries"]:
        core = {
            key: value for key, value in row.items() if key != "metadata_receipt_sha256"
        }
        assert row["metadata_receipt_sha256"] == audit.canonical_sha(core)


def test_real_seed_outputs_are_byte_identical() -> None:
    seed1 = audit.ROOT / "evals/s134_document_metadata_manifest_seed1_v1.json"
    seed2 = audit.ROOT / "evals/s134_document_metadata_manifest_seed2_v1.json"
    if not seed1.exists() or not seed2.exists():
        pytest.skip("S134 determinism evidence has not been executed yet")
    assert seed1.read_bytes() == seed2.read_bytes()
