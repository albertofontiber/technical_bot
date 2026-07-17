from __future__ import annotations

from scripts.s147_per_item_header_aware_gate import _public_source


def test_per_item_author_prompt_cannot_cross_contaminate_sources() -> None:
    row = {
        "item_id": "one",
        "stratum": "prose",
        "manufacturer": "Example",
        "product_model": "M1",
        "excerpt": "Exact source",
        "secret": "not public",
    }
    assert _public_source(row) == {
        "items": [
            {
                "item_id": "one",
                "stratum": "prose",
                "manufacturer": "Example",
                "product_model": "M1",
                "excerpt": "Exact source",
            }
        ]
    }
