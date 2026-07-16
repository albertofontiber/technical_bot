from __future__ import annotations

import json

import pytest

from scripts import s117_m27_loss_safe_chunking_probe as base
from scripts import s117_m27_loss_safe_chunking_probe_v2 as probe
from src.reingest import chunk as chunk_module


def _rows(chunks):
    return [
        base._fingerprinted(base._row_core_from_treatment(chunk))
        for chunk in chunks
    ]


def test_shifted_content_span_exploit_is_rejected():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta\n\ngamma"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [
        chunk_module.Chunk(
            content="alpha beta",
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
    with pytest.raises(RuntimeError, match="token interval is not bound"):
        probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


def test_legitimate_oversized_split_plus_tail_merge_is_accepted():
    record = {
        "sha256": "f" * 64,
        "result": {
            "pages": [{
                "page": 1,
                "md": ("Sentence. " * 1200) + "\n\ntail",
            }]
        },
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = sorted(
        base._with_treatment_override(record), key=lambda chunk: chunk.chunk_index
    )
    spans = [(chunk.source_block_start, chunk.source_block_end) for chunk in chunks]
    assert (0, 0) in spans
    assert (0, 1) in spans
    probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


def test_shared_oversized_span_without_tail_is_accepted():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "Sentence. " * 1200}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = sorted(
        base._with_treatment_override(record), key=lambda chunk: chunk.chunk_index
    )
    assert len(chunks) >= 2
    assert {(chunk.source_block_start, chunk.source_block_end) for chunk in chunks} == {
        (0, 0)
    }
    probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


@pytest.mark.parametrize("markdown", ["", "___\n\n---\n\n----"])
def test_empty_document_and_symbol_only_blocks_are_well_defined(markdown):
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": markdown}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = sorted(
        base._with_treatment_override(record), key=lambda chunk: chunk.chunk_index
    )
    probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


def test_span_metadata_tampering_is_rejected_even_with_exact_global_surface():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [
        chunk_module.Chunk(
            content="alpha",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=0,
            source_block_start=0,
            source_block_end=1,
        ),
        chunk_module.Chunk(
            content="beta",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=1,
            source_block_start=1,
            source_block_end=1,
        ),
    ]
    with pytest.raises(RuntimeError, match="token interval is not bound"):
        probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


def test_global_surface_reorder_is_rejected_before_span_claim():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [
        chunk_module.Chunk(
            content="beta",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=0,
            source_block_start=0,
            source_block_end=0,
        ),
        chunk_module.Chunk(
            content="alpha",
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=1,
            source_block_start=1,
            source_block_end=1,
        ),
    ]
    with pytest.raises(RuntimeError, match="global token surface"):
        probe._validate_treatment_against_raw(raw, record, chunks, _rows(chunks))


def test_scoped_base_overrides_restore_even_when_build_fails(monkeypatch):
    original_loader = base._load_contract
    original_validator = base._validate_treatment_against_raw
    original_file = base.__file__

    def fail(**_kwargs):
        assert base._load_contract is probe._load_contract
        assert base._validate_treatment_against_raw is probe._validate_treatment_against_raw
        assert base.__file__ == probe.__file__
        raise ValueError("stop")

    monkeypatch.setattr(base, "build_probe", fail)
    with pytest.raises(ValueError, match="stop"):
        probe.build_probe()
    assert base._load_contract is original_loader
    assert base._validate_treatment_against_raw is original_validator
    assert base.__file__ == original_file
