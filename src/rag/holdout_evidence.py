"""Gap-free, non-overlapping source units for frozen planner holdouts."""
from __future__ import annotations

import hashlib
from typing import Any


def _partition_spans(content: str, max_chars: int) -> list[tuple[int, int]]:
    """Partition every source byte once, preferring a prior line boundary."""
    spans: list[tuple[int, int]] = []
    start = 0
    while start < len(content):
        tentative_end = min(len(content), start + max_chars)
        end = tentative_end
        if tentative_end < len(content):
            boundary = content.rfind("\n", start + max_chars // 2, tentative_end)
            if boundary >= start:
                end = boundary + 1
        if end <= start:
            end = tentative_end
        spans.append((start, end))
        start = end
    return spans


def atomic_evidence_unit_rows(
    markdown: str,
    item_id: str,
    page_number: int,
    *,
    max_chars: int = 450,
    broad_limit: int = 600,
) -> list[dict[str, Any]]:
    """Serialize one gap-free partition with no alternative duplicate path.

    Every non-whitespace source character belongs to exactly one unit. This is
    deliberately simpler than a retrieval chunker: a holdout mapping must have
    one unambiguous ID path, while a model may select several adjacent bounded
    units when a sentence or table crosses a partition boundary.
    """
    if not 100 <= max_chars <= broad_limit:
        raise ValueError("invalid holdout evidence-unit bounds")
    rows: list[dict[str, Any]] = []
    covered = bytearray(len(markdown))
    for ordinal, (start, end) in enumerate(_partition_spans(markdown, max_chars), 1):
        content = markdown[start:end]
        if not content.strip():
            continue
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        identity = hashlib.sha256(
            (
                f"{page_number}:{item_id}_p{page_number}:gap_free_partition_v1:"
                f"{start}-{end}:{digest}"
            ).encode("utf-8")
        ).hexdigest()[:10]
        for index in range(start, end):
            if not markdown[index].isspace():
                if covered[index]:
                    raise ValueError("overlapping holdout evidence spans")
                covered[index] = 1
        rows.append(
            {
                "unit_id": f"E{ordinal:03d}_{identity}",
                "fragment_number": page_number,
                "candidate_id": f"{item_id}_p{page_number}",
                "unit_kind": "gap_free_partition_v1",
                "source_spans": [[start, end]],
                "content": content,
                "content_sha256": digest,
            }
        )
    missing = [
        index
        for index, char in enumerate(markdown)
        if not char.isspace() and not covered[index]
    ]
    if missing:
        raise ValueError(f"holdout evidence coverage gap at source offset {missing[0]}")
    if not rows:
        raise ValueError(f"no evidence units built for {item_id} page {page_number}")
    broad = [row["unit_id"] for row in rows if len(row["content"]) > broad_limit]
    if broad:
        raise ValueError(f"broad evidence units are forbidden: {broad}")
    return rows
