from __future__ import annotations

import hashlib
from types import SimpleNamespace

from scripts.s116_raw_store_ab_v2 import (
    METRIC_KEYS,
    _anchor_resolves,
    _lineage_resolves,
    _zero_metrics,
)


def _anchor(page: int | None = None, index: int = 0, title: str = "1 Setup", level: int = 1):
    text = f"{'#' * level} {title}"
    return SimpleNamespace(
        heading_text=text,
        heading_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_page=page,
        source_block_index=index,
        title=title,
        level=level,
    )


def test_anchor_resolves_real_block_and_allows_none_page() -> None:
    anchor = _anchor()
    block = SimpleNamespace(
        kind="heading", text=anchor.heading_text, page=None, source_block_index=0, lineage=(anchor,)
    )
    assert _anchor_resolves(anchor, [block])
    anchor.source_block_index = 1
    assert not _anchor_resolves(anchor, [block])


def test_full_lineage_must_match_every_block_in_source_span() -> None:
    anchor = _anchor(page=1)
    blocks = [
        SimpleNamespace(kind="heading", text=anchor.heading_text, page=1, source_block_index=0, lineage=(anchor,)),
        SimpleNamespace(kind="paragraph", text="Body", page=1, source_block_index=1, lineage=(anchor,)),
    ]
    chunk = SimpleNamespace(
        section_lineage=(anchor,), section_anchor=anchor, source_block_start=0, source_block_end=1,
        section_title="1 Setup", section_path="1 Setup",
    )
    assert _lineage_resolves(chunk, blocks)
    blocks[1].lineage = ()
    assert not _lineage_resolves(chunk, blocks)


def test_metric_schema_keeps_explicit_zeroes() -> None:
    metrics = _zero_metrics()
    assert tuple(metrics) == METRIC_KEYS
    assert all(metrics[key] == 0 for key in METRIC_KEYS)
