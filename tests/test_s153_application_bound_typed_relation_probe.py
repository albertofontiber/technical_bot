from __future__ import annotations

import json

from scripts.s153_application_bound_typed_relation_probe import _extraction_prompt


def test_extraction_prompt_omits_all_application_identity() -> None:
    chunk = {
        "chunk_id": "secret-id",
        "manufacturer": "M",
        "product_model": "P",
        "section_title": "S",
        "content": "Exact source",
        "source_file": "manual",
    }
    prompt = json.loads(_extraction_prompt(chunk))
    assert prompt == {
        "manufacturer": "M",
        "product_model": "P",
        "section_title": "S",
        "content": "Exact source",
    }
