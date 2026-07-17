from __future__ import annotations

from scripts.s151_typed_relation_target_probe import _public_batch


def test_per_chunk_prompt_contains_exactly_one_source() -> None:
    chunk = {
        "chunk_id": "one",
        "manufacturer": "M",
        "product_model": "P",
        "section_title": "S",
        "content": "Exact source",
    }
    assert _public_batch([chunk]) == {"chunks": [chunk]}
