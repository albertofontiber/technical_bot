from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk_provenance as provenance


def _raw(markdown: str, extraction_sha256: str = "a" * 64) -> bytes:
    return (json.dumps({
        "sha256": extraction_sha256,
        "result": {"pages": [{"page": 1, "md": markdown, "confidence": 0.9}]},
    }, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _identity(raw: bytes) -> tuple[str, str]:
    chunker = "b" * 64
    materializer = "c" * 64
    manifest = provenance.generation_manifest(
        [{"extraction_sha256": "a" * 64, "raw_artifact_sha256": hashlib.sha256(raw).hexdigest()}],
        chunker_sha256=chunker,
        materializer_sha256=materializer,
    )
    return provenance.materialization_identity(manifest)


def test_generation_and_rows_are_deterministic_and_nul_delimited() -> None:
    raw = _raw("# Setup\n\n" + "Install the panel safely. " * 40)
    manifest_sha, materialization_id = _identity(raw)
    assert materialization_id == provenance.materialization_identity(
        provenance.generation_manifest(
            [{"extraction_sha256": "a" * 64, "raw_artifact_sha256": hashlib.sha256(raw).hexdigest()}],
            chunker_sha256="b" * 64,
            materializer_sha256="c" * 64,
        )
    )[1]
    assert manifest_sha != hashlib.sha256(f"v1\\0{manifest_sha}".encode()).hexdigest()
    first = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    second = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    assert first == second
    assert replay.validate_rows_against_raw(
        raw, first, materialization_id=materialization_id, chunker_sha256="b" * 64
    ) == []


def test_raw_chunker_and_span_change_identity() -> None:
    raw = _raw("# Setup\n\n" + "A useful installation sentence. " * 40)
    _, materialization_id = _identity(raw)
    rows = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    original = rows[0]["id"]
    changed_chunker = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="d" * 64
    )
    assert changed_chunker[0]["id"] != original

    tampered = copy.deepcopy(rows)
    tampered[0]["source_block_end"] += 1
    payload = {key: tampered[0][key] for key in (
        "provenance_version", "provenance_contract", "raw_artifact_sha256",
        "chunker_sha256", "content_sha256", "source_block_start",
        "source_block_end", "section_anchor", "section_lineage",
    )}
    payload_sha = hashlib.sha256(provenance.canonical_json_bytes(payload)).hexdigest()
    changed_id = provenance.chunk_identity(materialization_id, "a" * 64, 0, payload_sha)
    assert changed_id != original


def test_independent_validator_rejects_tampered_content_even_with_new_hash() -> None:
    raw = _raw("# Configuration\n\n" + "Set the supervised output. " * 40)
    _, materialization_id = _identity(raw)
    rows = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    rows[0]["content"] += " invented"
    rows[0]["content_sha256"] = hashlib.sha256(rows[0]["content"].encode()).hexdigest()
    failures = replay.validate_rows_against_raw(
        raw, rows, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    assert "row_mismatch" in failures


def test_repeated_headings_and_oversized_blocks_validate_without_special_cases() -> None:
    markdown = (
        "# Zone\n\n" + "A" * 7600 + "\n\n"
        "# Zone\n\n" + "B" * 900 + "\n\n"
        "## Wiring\n\n" + "Connect terminal one. " * 40
    )
    raw = _raw(markdown)
    _, materialization_id = _identity(raw)
    rows = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    assert len(rows) >= 2
    assert len({row["id"] for row in rows}) == len(rows)
    assert replay.validate_rows_against_raw(
        raw, rows, materialization_id=materialization_id, chunker_sha256="b" * 64
    ) == []


def test_row_manifest_is_closed_canonical_jsonl() -> None:
    raw = _raw("# Test\n\n" + "A deterministic body. " * 40)
    _, materialization_id = _identity(raw)
    rows = provenance.materialize_raw_record(
        raw, materialization_id=materialization_id, chunker_sha256="b" * 64
    )
    payload = provenance.row_manifest_bytes(rows)
    assert payload.endswith(b"\n")
    decoded = [json.loads(line) for line in payload.splitlines()]
    assert set(decoded[0]) == set(provenance.ROW_MANIFEST_FIELDS)
    assert "content" not in decoded[0]


def test_global_duplicate_contract_rejects_chains_and_cross_generation() -> None:
    row_a = {"id": "a", "materialization_id": "m", "duplicate_of": None,
             "extraction_sha256": "1", "chunk_index": 0}
    row_b = {"id": "b", "materialization_id": "m", "duplicate_of": "a",
             "extraction_sha256": "1", "chunk_index": 1}
    row_c = {"id": "c", "materialization_id": "m", "duplicate_of": "b",
             "extraction_sha256": "2", "chunk_index": 0}
    assert "duplicate_chain" in replay._global_failures([row_a, row_b, row_c])
    row_c.update({"materialization_id": "other", "duplicate_of": "a"})
    assert "cross_generation_duplicate" in replay._global_failures([row_a, row_b, row_c])


def test_materializer_has_no_frozen_document_branches() -> None:
    paths = [
        Path(provenance.__file__),
        Path(replay.__file__),
    ]
    text = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    for forbidden in ("hochiki", "bosch", "siemens", "apollo", "0d175dd3", "b4926f04"):
        assert forbidden not in text


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="implementation SHA"):
        provenance.generation_manifest([], chunker_sha256="bad", materializer_sha256="c" * 64)
    with pytest.raises(ValueError, match="raw record"):
        provenance.materialize_raw_record(
            b'{"result":{"pages":[]}}',
            materialization_id="00000000-0000-0000-0000-000000000000",
            chunker_sha256="b" * 64,
        )


def test_canonical_json_rejects_non_finite_numbers() -> None:
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            provenance.canonical_json_bytes({"value": value})


@pytest.mark.parametrize("confidence", [math.nan, math.inf, -math.inf, -0.01, 1.01, True])
def test_materializer_and_independent_validator_reject_invalid_confidence(
    confidence: object,
) -> None:
    raw = (json.dumps({
        "sha256": "a" * 64,
        "result": {"pages": [{
            "page": 1,
            "md": "# Setup\n\n" + "Install safely. " * 40,
            "confidence": confidence,
        }]},
    }, allow_nan=True) + "\n").encode("utf-8")
    _, materialization_id = _identity(raw)
    with pytest.raises(ValueError):
        provenance.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256="b" * 64,
        )
    with pytest.raises(ValueError):
        replay.validate_rows_against_raw(
            raw,
            [],
            materialization_id=materialization_id,
            chunker_sha256="b" * 64,
        )


def test_materializer_and_independent_validator_reject_boolean_page() -> None:
    raw = (json.dumps({
        "sha256": "a" * 64,
        "result": {"pages": [{
            "page": True,
            "md": "Unanchored installation content. " * 40,
            "confidence": 0.9,
        }]},
    }) + "\n").encode("utf-8")
    _, materialization_id = _identity(raw)
    with pytest.raises(ValueError, match="page number"):
        provenance.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256="b" * 64,
        )
    with pytest.raises(ValueError, match="page number"):
        replay.validate_rows_against_raw(
            raw,
            [],
            materialization_id=materialization_id,
            chunker_sha256="b" * 64,
        )
