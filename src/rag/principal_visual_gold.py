"""Successor gate for a principal visual gold and independent disagreement probe."""
from __future__ import annotations

from typing import Any

from src.rag.visual_gold import all_pass


def principal_publication_gate(
    principal_candidate_review: dict[str, Any],
    independent_counterpart_review: dict[str, Any],
) -> bool:
    """Gate the principal gold without publishing its blind counterpart.

    The principal candidate must pass its independent pixel review completely.
    The independently authored counterpart remains a disagreement probe: its own
    standalone wording or completeness defects are diagnostic unless they reveal
    a material disagreement with the principal candidate.  It must still target
    the frozen topic and both candidates must materially agree.
    """
    if not all_pass(principal_candidate_review):
        return False
    rows = independent_counterpart_review.get("reviews")
    return bool(rows) and all(
        row.get("topic_aligned") is True
        and row.get("counterpart_materially_agrees") is True
        and not row.get("material_disagreements")
        for row in rows
    )
