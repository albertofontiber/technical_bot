from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json

import pytest

from src.reingest import chunk as chunk_module
from src.reingest.chunk import Chunk, SectionAnchor, _cleanup, chunk_document
from scripts import s117_m27_loss_safe_chunking_probe as probe_base
from scripts import s117_m27_loss_safe_chunking_probe_v2 as probe_v2


def _anchor(title: str, index: int, *, level: int = 1) -> SectionAnchor:
    text = f"{'#' * level} {title}"
    return SectionAnchor(
        heading_text=text,
        title=title,
        level=level,
        source_page=1,
        source_block_index=index,
        heading_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _chunk(
    content: str,
    lineage: tuple[SectionAnchor, ...],
    start: int,
    end: int,
    *,
    flow: bool = False,
    has_diagram: bool = False,
) -> Chunk:
    anchor = lineage[-1] if lineage else None
    return Chunk(
        content=content,
        section_title=anchor.title if anchor else None,
        section_path=" > ".join(item.title for item in lineage) if lineage else None,
        page_number=1,
        chunk_index=0,
        is_flow_diagram=flow,
        has_diagram=has_diagram,
        section_anchor=anchor,
        section_lineage=lineage,
        source_block_start=start,
        source_block_end=end,
    )


def _signature(chunks: list[Chunk]) -> list[tuple]:
    return [(
        chunk.content,
        chunk.source_block_start,
        chunk.source_block_end,
        tuple(anchor.identity for anchor in chunk.section_lineage),
        chunk.section_title,
        chunk.section_path,
        chunk.is_flow_diagram,
        chunk.has_diagram,
    ) for chunk in chunks]


def _tokens(chunks: list[Chunk]) -> list[str]:
    return [token for chunk in chunks for token in chunk.content.split()]


def _probe_rows(chunks: list[Chunk]) -> list[dict]:
    return [
        probe_base._fingerprinted(probe_base._row_core_from_treatment(chunk))
        for chunk in chunks
    ]


def test_noise_and_meaningful_metrics_are_inert_in_production_functions():
    for function in (chunk_module._cleanup, chunk_module.chunk_document):
        tree = ast.parse(inspect.getsource(function))
        loaded_names = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        assert "NOISE_CHARS" not in loaded_names
        assert "_meaningful_len" not in loaded_names
    cleanup_tree = ast.parse(inspect.getsource(chunk_module._cleanup))
    assert not any(isinstance(node, ast.Continue) for node in ast.walk(cleanup_tree))


def test_noise_values_and_raising_meaningful_metric_cannot_change_output(monkeypatch):
    anchor = _anchor("Setup", 0)
    source = [
        _chunk("A" * 500, (anchor,), 0, 0),
        _chunk("#", (anchor,), 1, 1),
        _chunk("tail", (anchor,), 2, 2),
    ]

    def forbidden(_content: str) -> int:
        raise AssertionError("_meaningful_len must be inert")

    monkeypatch.setattr(chunk_module, "_meaningful_len", forbidden)
    observed = []
    for value in (0, 15, 10**9):
        monkeypatch.setattr(chunk_module, "NOISE_CHARS", value)
        observed.append(_signature(_cleanup(copy.deepcopy(source))))
        chunks = chunk_document({
            "result": {"pages": [{"page": 1, "md": "# H\n\nE01"}]}
        })
        assert _tokens(chunks) == ["#", "H", "E01"]
    assert observed[0] == observed[1] == observed[2]


@pytest.mark.parametrize(
    "content",
    ["E01", "# H", "108", "NO_CONTENT_HERE", "___", "---"],
)
def test_standalone_short_content_is_preserved(content: str):
    result = _cleanup([_chunk(content, (), 0, 0)])
    assert len(result) == 1
    assert result[0].content == content
    assert (result[0].source_block_start, result[0].source_block_end) == (0, 0)


def test_cleanup_preserves_input_token_surface_before_mutating_merge_target():
    anchor = _anchor("Setup", 0)
    source = [
        _chunk("alpha " * 100, (anchor,), 0, 0),
        _chunk("beta", (anchor,), 1, 1, has_diagram=True),
        _chunk("gamma", (anchor,), 2, 2),
    ]
    expected_tokens = list(_tokens(source))
    result = _cleanup(source)
    assert _tokens(result) == expected_tokens
    assert len(result) == 1
    assert result[0].source_block_start == 0
    assert result[0].source_block_end == 2
    assert result[0].has_diagram


def test_cleanup_preserves_lineage_gap_flow_and_max_barriers():
    parent = _anchor("Parent", 0)
    child_a = _anchor("A", 1, level=2)
    child_b = _anchor("B", 2, level=2)

    different_lineage = _cleanup([
        _chunk("A" * 500, (parent, child_a), 0, 0),
        _chunk("tail", (parent, child_b), 1, 1),
    ])
    assert len(different_lineage) == 2

    gap = _cleanup([
        _chunk("A" * 500, (parent, child_a), 0, 0),
        _chunk("tail", (parent, child_a), 2, 2),
    ])
    assert len(gap) == 2

    flow = _cleanup([
        _chunk("A" * 500, (parent, child_a), 0, 0),
        _chunk("```mermaid\na-->b\n```", (parent, child_a), 1, 1, flow=True),
    ])
    assert len(flow) == 2

    over_max = _cleanup([
        _chunk("A" * chunk_module.MAX_CHARS, (parent, child_a), 0, 0),
        _chunk("x", (parent, child_a), 1, 1),
    ])
    assert len(over_max) == 2


def test_cleanup_accepts_legitimate_shared_and_partial_overlap_spans():
    anchor = _anchor("Setup", 0)
    result = _cleanup([
        _chunk("A" * 500, (anchor,), 1, 1),
        _chunk("tail", (anchor,), 1, 2),
    ])
    assert len(result) == 1
    assert result[0].content == f"{'A' * 500}\n\ntail"
    assert (result[0].source_block_start, result[0].source_block_end) == (1, 2)


def test_token_interval_validator_rejects_omission_explicitly():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [_chunk("alpha", (), 0, 1)]
    with pytest.raises(RuntimeError, match="global token surface"):
        probe_v2._validate_treatment_against_raw(
            raw, record, chunks, _probe_rows(chunks)
        )


def test_token_interval_validator_rejects_duplication_explicitly():
    record = {
        "sha256": "f" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]},
    }
    raw = json.dumps(record).encode("utf-8")
    chunks = [_chunk("alpha alpha beta", (), 0, 1)]
    with pytest.raises(RuntimeError, match="global token surface"):
        probe_v2._validate_treatment_against_raw(
            raw, record, chunks, _probe_rows(chunks)
        )


def test_chunk_document_keeps_ordinals_and_lineage_coherent_for_short_sections():
    record = {
        "result": {
            "pages": [{
                "page": 1,
                "md": "# First\n\nE01\n\n# Second\n\n108",
            }]
        }
    }
    chunks = chunk_document(record)
    assert len(chunks) == 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert _tokens(chunks) == ["#", "First", "E01", "#", "Second", "108"]
    assert (chunks[0].source_block_start, chunks[0].source_block_end) == (0, 3)
    assert chunks[0].section_lineage == ()
    assert chunks[0].section_anchor is None
    assert chunks[0].section_title is None
    assert chunks[0].section_path is None
