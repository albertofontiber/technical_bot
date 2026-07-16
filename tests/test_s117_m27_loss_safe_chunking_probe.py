from __future__ import annotations

import json
import random

import pytest

from scripts import s117_m27_loss_safe_chunking_probe as probe
from src.reingest import chunk as chunk_module


def _baseline_row(content: str, start: int = 0, end: int = 0, index: int = 0) -> dict:
    return {
        "chunk_index": index,
        "content": content,
        "source_block_start": start,
        "source_block_end": end,
        "section_anchor": None,
        "section_lineage": [],
        "section_title": None,
        "section_path": None,
        "page_number": 1,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence": None,
    }


def test_override_is_scoped_and_restored_after_success():
    observed = []

    def fake(record):
        observed.append(chunk_module.NOISE_CHARS)
        return [record]

    record = {"value": 1}
    assert probe._with_treatment_override(record, chunker=fake) == [record]
    assert observed == [0]
    assert chunk_module.NOISE_CHARS == 15


def test_override_is_restored_after_failure():
    def fail(_record):
        assert chunk_module.NOISE_CHARS == 0
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        probe._with_treatment_override({}, chunker=fail)
    assert chunk_module.NOISE_CHARS == 15


def test_override_fails_closed_on_preexisting_global_drift(monkeypatch):
    monkeypatch.setattr(chunk_module, "NOISE_CHARS", 7)
    with pytest.raises(RuntimeError, match="baseline NOISE_CHARS drift"):
        probe._with_treatment_override({})


def test_fingerprint_is_independent_of_ordinal_but_not_span():
    first = probe._fingerprinted(probe._row_core_from_baseline(_baseline_row("E01")))
    second_row = _baseline_row("E01", index=9)
    second = probe._fingerprinted(probe._row_core_from_baseline(second_row))
    assert first["fingerprint_sha256"] == second["fingerprint_sha256"]
    moved = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("E01", start=1, end=1))
    )
    assert first["fingerprint_sha256"] != moved["fingerprint_sha256"]


def test_multiset_delta_preserves_duplicate_occurrences():
    base_a = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("same", index=0))
    )
    base_b = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("same", index=1))
    )
    treatment = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("same", index=0))
    )
    delta = probe._multiset_delta([base_a, base_b], [treatment])
    assert len(delta["unchanged"]) == 1
    assert [row["ordinal"] for row in delta["removed"]] == [1]
    assert delta["added"] == []


def test_multiset_delta_crosslinks_only_overlapping_modified_spans():
    baseline = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("alpha", 0, 1))
    )
    treatment_overlap = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("beta", 1, 2))
    )
    treatment_far = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("gamma", 3, 3, index=1))
    )
    delta = probe._multiset_delta(
        [baseline], [treatment_overlap, treatment_far]
    )
    assert len(delta["modified"]) == 1
    assert delta["modified"][0]["overlap_start"] == 1
    assert delta["modified"][0]["overlap_end"] == 1


def test_document_probe_recovers_short_alphanumeric_block():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "E01"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    document, delta = probe._document_probe(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        baseline_rows_raw=[],
        treatment_contract_sha256="a" * 64,
    )
    assert document["baseline_missing_block_indexes"] == [0]
    assert document["treatment_missing_block_indexes"] == []
    assert document["coverage_gain_block_indexes"] == [0]
    assert document["treatment_surface_equal_raw"]
    assert delta is not None
    assert [row["content"] for row in delta["added"]] == ["E01"]
    assert chunk_module.NOISE_CHARS == 15


def test_document_probe_leaves_long_content_fingerprint_unchanged():
    content = "Technical installation procedure " * 20
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": content}]},
    }
    raw = json.dumps(record).encode("utf-8")
    document, delta = probe._document_probe(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        baseline_rows_raw=[_baseline_row(content)],
        treatment_contract_sha256="a" * 64,
    )
    assert document["fingerprint_multiset_equal"]
    assert not document["changed"]
    assert delta is None


def test_validate_rows_rejects_out_of_range_and_noncontiguous_ordinals():
    valid = probe._fingerprinted(
        probe._row_core_from_baseline(_baseline_row("content"))
    )
    probe._validate_rows([valid], 1)
    invalid = dict(valid, ordinal=2)
    with pytest.raises(RuntimeError, match="non-contiguous"):
        probe._validate_rows([invalid], 1)
    invalid_span = dict(valid, source_block_end=2)
    with pytest.raises(RuntimeError, match="outside raw block"):
        probe._validate_rows([invalid_span], 1)


def test_treatment_metadata_and_lineage_are_independently_raw_bound():
    record = {
        "sha256": "f" * 64,
        "result": {
            "pages": [{
                "page": 3,
                "confidence": 0.75,
                "images": [{"name": "diagram"}],
                "md": "# Setup\n\nE01",
            }]
        },
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = probe._with_treatment_override(record)
    rows = [
        probe._fingerprinted(probe._row_core_from_treatment(chunk))
        for chunk in chunks
    ]
    probe._validate_treatment_against_raw(raw, record, chunks, rows)
    forged = [dict(row) for row in rows]
    forged[0]["page_number"] = 99
    with pytest.raises(RuntimeError, match="page number"):
        probe._validate_treatment_against_raw(raw, record, chunks, forged)


def test_treatment_lineage_tampering_is_rejected():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "# Setup\n\ncontent"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = probe._with_treatment_override(record)
    rows = [
        probe._fingerprinted(probe._row_core_from_treatment(chunk))
        for chunk in chunks
    ]
    forged = [dict(row) for row in rows]
    forged[0]["section_lineage"] = []
    forged[0]["section_anchor"] = None
    with pytest.raises(RuntimeError, match="lineage"):
        probe._validate_treatment_against_raw(raw, record, chunks, forged)


def test_content_cannot_be_shifted_between_declared_spans():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta\n\ngamma"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [
        chunk_module.Chunk(
            content="alpha\n\nbeta",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=0,
            source_block_start=0,
            source_block_end=0,
        ),
        chunk_module.Chunk(
            content="gamma",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=1,
            source_block_start=1,
            source_block_end=2,
        ),
    ]
    rows = [
        probe._fingerprinted(probe._row_core_from_treatment(chunk))
        for chunk in chunks
    ]
    with pytest.raises(RuntimeError, match="not bound to its raw span"):
        probe._validate_treatment_against_raw(raw, record, chunks, rows)


def test_shared_oversized_span_reconstructs_raw_surface():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "Sentence. " * 1200}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = probe._with_treatment_override(record)
    assert len(chunks) >= 2
    assert {(chunk.source_block_start, chunk.source_block_end) for chunk in chunks} == {
        (0, 0)
    }
    rows = [
        probe._fingerprinted(probe._row_core_from_treatment(chunk))
        for chunk in chunks
    ]
    probe._validate_treatment_against_raw(raw, record, chunks, rows)


def test_row_and_chunk_perturbation_restores_canonical_document_output():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "E01\n\n# Setup\n\ncontent"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    first = probe._document_probe(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        baseline_rows_raw=[],
        treatment_contract_sha256="a" * 64,
        rng=random.Random(1),
    )
    second = probe._document_probe(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        baseline_rows_raw=[],
        treatment_contract_sha256="a" * 64,
        rng=random.Random(2),
    )
    assert first == second


def test_diagnostic_id_is_deterministic_and_input_bound():
    first = probe._diagnostic_id("a" * 64, "b" * 64, 1, "c" * 64)
    assert first == probe._diagnostic_id("a" * 64, "b" * 64, 1, "c" * 64)
    assert first != probe._diagnostic_id("a" * 64, "b" * 64, 2, "c" * 64)
