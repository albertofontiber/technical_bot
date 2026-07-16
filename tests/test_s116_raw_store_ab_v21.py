from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from scripts.s116_raw_store_ab_v21 import _anchor_resolves, _atomic_lineage_state_valid


def _anchor(**overrides):
    title = overrides.pop("title", "1 Setup")
    level = overrides.pop("level", 1)
    text = overrides.pop("heading_text", f"{'#' * level} {title}")
    values = {
        "heading_text": text,
        "heading_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "source_page": None,
        "source_block_index": 0,
        "title": title,
        "level": level,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _block(anchor, **overrides):
    values = {
        "kind": "heading",
        "text": anchor.heading_text,
        "page": anchor.source_page,
        "source_block_index": anchor.source_block_index,
        "lineage": (anchor,),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_anchor_requires_explicit_block_coordinate() -> None:
    anchor = _anchor()
    block = _block(anchor)
    del block.source_block_index
    assert not _anchor_resolves(anchor, [block])


@pytest.mark.parametrize(
    "mutation",
    [
        {"source_page": 2},
        {"heading_sha256": "0" * 64},
        {"title": "Other"},
        {"level": True},
        {"level": 7},
        {"heading_text": "# Other"},
    ],
)
def test_anchor_rejects_tampered_fields(mutation: dict) -> None:
    original = _anchor()
    block = _block(original)
    assert not _anchor_resolves(_anchor(**mutation), [block])


def test_atomic_empty_state_requires_all_metadata_empty() -> None:
    block = SimpleNamespace(kind="paragraph", text="Preamble", page=1, source_block_index=0, lineage=())
    valid = SimpleNamespace(
        section_lineage=(), section_anchor=None, source_block_start=0, source_block_end=0,
        section_title=None, section_path=None,
    )
    assert _atomic_lineage_state_valid(valid, [block])
    valid.section_title = "Injected"
    assert not _atomic_lineage_state_valid(valid, [block])


def test_atomic_state_detects_mixed_empty_lineage() -> None:
    anchor = _anchor(source_page=1, source_block_index=1)
    blocks = [
        SimpleNamespace(kind="paragraph", text="Preamble", page=1, source_block_index=0, lineage=()),
        _block(anchor),
    ]
    invalid = SimpleNamespace(
        section_lineage=(anchor,), section_anchor=anchor, source_block_start=0, source_block_end=1,
        section_title=anchor.title, section_path=anchor.title,
    )
    assert not _atomic_lineage_state_valid(invalid, blocks)
