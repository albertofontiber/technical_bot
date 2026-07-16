from __future__ import annotations

import hashlib
from dataclasses import replace

from scripts.s116_raw_store_ab_v21 import _atomic_lineage_state_valid
from src.reingest.chunk import (
    Chunk,
    SectionAnchor,
    _cleanup,
    _flatten,
    chunk_document,
)


def _record(*pages: dict) -> dict:
    return {"result": {"pages": list(pages)}}


def _page(md: str, page: int | None = 1) -> dict:
    row = {"md": md}
    if page is not None:
        row["page"] = page
    return row


def _anchor(title: str, index: int, page: int | None = 1, level: int = 1) -> SectionAnchor:
    text = f"{'#' * level} {title}"
    return SectionAnchor(
        heading_text=text,
        title=title,
        level=level,
        source_page=page,
        source_block_index=index,
        heading_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def _chunk(
    content: str,
    lineage: tuple[SectionAnchor, ...],
    start: int,
    end: int,
    *,
    flow: bool = False,
) -> Chunk:
    anchor = lineage[-1] if lineage else None
    return Chunk(
        content=content,
        section_title=anchor.title if anchor else None,
        section_path=" > ".join(item.title for item in lineage) if lineage else None,
        page_number=1,
        chunk_index=0,
        is_flow_diagram=flow,
        section_anchor=anchor,
        section_lineage=lineage,
        source_block_start=start,
        source_block_end=end,
    )


def test_same_page_continuation_keeps_resolvable_anchor_without_injection() -> None:
    record = _record(_page("# Setup\n\n" + "A" * 1800 + "\n\n" + "B" * 1800))
    blocks = _flatten(record["result"]["pages"])
    chunks = chunk_document(record)
    assert len(chunks) == 2
    assert chunks[0].section_anchor == chunks[1].section_anchor
    assert chunks[1].content == "B" * 1800
    assert "# Setup" not in chunks[1].content
    assert all(_atomic_lineage_state_valid(chunk, blocks) for chunk in chunks)


def test_page_crossing_continuation_points_to_original_heading_page() -> None:
    record = _record(
        _page("# Setup\n\n" + "A" * 1800, 1),
        _page("B" * 1800, 2),
    )
    chunks = chunk_document(record)
    assert len(chunks) == 2
    assert chunks[1].section_anchor is not None
    assert chunks[1].section_anchor.source_page == 1
    assert chunks[1].page_number == 2


def test_none_page_is_valid_when_heading_occurrence_resolves() -> None:
    record = _record(_page("# Setup\n\n" + "Body" * 10, None))
    blocks = _flatten(record["result"]["pages"])
    chunk = chunk_document(record)[0]
    assert chunk.section_anchor is not None
    assert chunk.section_anchor.source_page is None
    assert chunk.section_anchor.is_internally_valid()
    assert _atomic_lineage_state_valid(chunk, blocks)


def test_repeated_running_heading_creates_new_occurrence_identity() -> None:
    record = _record(
        _page("# Status\n\n" + "A" * 500, 1),
        _page("# Status\n\n" + "B" * 500, 2),
    )
    chunks = chunk_document(record)
    assert len(chunks) == 2
    assert chunks[0].section_anchor is not None and chunks[1].section_anchor is not None
    assert chunks[0].section_anchor.heading_text == chunks[1].section_anchor.heading_text
    assert chunks[0].section_anchor.identity != chunks[1].section_anchor.identity


def test_identical_heading_text_at_different_level_or_index_stays_distinct() -> None:
    blocks = _flatten([_page("# Status\n\nBody\n\n## Status\n\nMore")])
    headings = [block for block in blocks if block.kind == "heading"]
    assert [block.source_block_index for block in headings] == [0, 2]
    assert headings[0].lineage[-1].level == 1
    assert headings[1].lineage[-1].level == 2
    assert headings[0].lineage[-1].identity != headings[1].lineage[-1].identity


def test_mixed_unanchored_preamble_cannot_inherit_later_section() -> None:
    record = _record(_page("Preamble\n\n# Setup\n\n" + "A" * 600))
    blocks = _flatten(record["result"]["pages"])
    chunk = chunk_document(record)[0]
    assert chunk.section_lineage == ()
    assert chunk.section_anchor is None
    assert chunk.section_title is None and chunk.section_path is None
    assert _atomic_lineage_state_valid(chunk, blocks)


def test_mixed_siblings_resolve_only_to_real_common_parent() -> None:
    record = _record(_page("# Parent\n\n## A\n\nAlpha\n\n## B\n\nBeta"))
    chunk = chunk_document(record)[0]
    assert chunk.section_title == "Parent"
    assert [item.title for item in chunk.section_lineage] == ["Parent"]


def test_oversized_pieces_keep_full_lineage_and_source_index() -> None:
    body = ("A" * 100 + ". ") * 100
    record = _record(_page("# Setup\n\n" + body))
    blocks = _flatten(record["result"]["pages"])
    chunks = chunk_document(record)
    assert len(chunks) >= 2
    identities = {chunk.section_anchor.identity for chunk in chunks if chunk.section_anchor}
    source_spans = {(chunk.source_block_start, chunk.source_block_end) for chunk in chunks}
    assert len(identities) == 1
    assert source_spans == {(0, 0), (1, 1)}
    heading_chunks = [chunk for chunk in chunks if chunk.source_block_start == 0]
    body_chunks = [chunk for chunk in chunks if chunk.source_block_start == 1]
    assert len(heading_chunks) == 1
    assert heading_chunks[0].content == "# Setup"
    assert (heading_chunks[0].source_block_start, heading_chunks[0].source_block_end) == (0, 0)
    assert body_chunks
    assert all((chunk.source_block_start, chunk.source_block_end) == (1, 1) for chunk in body_chunks)
    assert all("# Setup" not in chunk.content for chunk in body_chunks)
    assert all(chunk.section_title == "Setup" for chunk in body_chunks)
    assert all(_atomic_lineage_state_valid(chunk, blocks) for chunk in chunks)


def test_cleanup_merges_only_same_full_lineage_and_updates_span() -> None:
    parent = _anchor("Parent", 0)
    child_a = _anchor("A", 1, level=2)
    child_b = _anchor("B", 2, level=2)
    merged = _cleanup([
        _chunk("A" * 500, (parent, child_a), 1, 1),
        _chunk("tail" * 5, (parent, child_a), 2, 2),
    ])
    assert len(merged) == 1
    assert merged[0].source_block_end == 2
    separate = _cleanup([
        _chunk("A" * 500, (parent, child_a), 1, 1),
        _chunk("tail" * 5, (parent, child_b), 2, 2),
    ])
    assert len(separate) == 2


def test_cleanup_keeps_diagram_barrier_and_preserves_short_content() -> None:
    anchor = _anchor("Setup", 0)
    diagram = _cleanup([
        _chunk("A" * 500, (anchor,), 0, 0),
        _chunk("```mermaid\nstart-->process-->finish\n```", (anchor,), 1, 1, flow=True),
    ])
    assert len(diagram) == 2
    preserved = _cleanup([
        _chunk("A" * 500, (anchor,), 0, 0),
        _chunk("#", (anchor,), 1, 1),
        _chunk("tail" * 5, (anchor,), 2, 2),
    ])
    assert len(preserved) == 1
    assert preserved[0].content == f"{'A' * 500}\n\n#\n\n{'tail' * 5}"
    assert preserved[0].source_block_end == 2


def test_flatten_indexes_are_unique_contiguous_and_monotonic() -> None:
    blocks = _flatten([_page("# A\n\nBody", 1), _page("## B\n\nMore", 2)])
    indexes = [block.source_block_index for block in blocks]
    assert indexes == list(range(len(blocks)))


def test_anchor_tampering_fails_internal_validation() -> None:
    anchor = _anchor("Setup", 0)
    assert anchor.is_internally_valid()
    assert not replace(anchor, heading_sha256="0" * 64).is_internally_valid()
    assert not replace(anchor, title="Other").is_internally_valid()
    assert not replace(anchor, level=7).is_internally_valid()
