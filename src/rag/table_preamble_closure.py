"""Deterministic closure for table preambles split from served table rows.

The selector is deliberately narrower than a semantic-neighbor lane.  It may
only recover the immediately preceding, same-blob Markdown heading/preamble of
a table that already survived reranking.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

LANE = "same_blob_table_preamble_closure_v2"
VALIDATION = "same_blob_exact_predecessor_single_table_heading_v2"
MAX_PREAMBLE_CHARS = 1200
MAX_PREAMBLES = 2
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def normalize_heading(value: str) -> str:
    """Normalize formatting, not semantics, for exact heading continuity."""
    folded = _fold(value)
    folded = re.sub(r"[`*_~]", "", folded)
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return " ".join(folded.split())


def _is_markdown_table_pair(first: str, second: str) -> bool:
    first = first.strip()
    second = second.strip()
    if not first.startswith("|") or not first.endswith("|"):
        return False
    if not second.startswith("|") or not second.endswith("|"):
        return False
    cells = [cell.strip() for cell in second.strip("|").split("|")]
    return len(cells) >= 2 and all(_TABLE_SEPARATOR_CELL.fullmatch(cell) for cell in cells)


def begins_with_markdown_table(content: str) -> bool:
    lines = [line for line in (content or "").splitlines() if line.strip()]
    return len(lines) >= 2 and _is_markdown_table_pair(lines[0], lines[1])


def contains_markdown_table(content: str) -> bool:
    """Detect a complete pipe-table header anywhere in a candidate span."""
    lines = (content or "").splitlines()
    return any(
        _is_markdown_table_pair(lines[index], lines[index + 1])
        for index in range(len(lines) - 1)
    )


def _identity(row: dict[str, Any]) -> tuple[str, str] | None:
    document_id = str(row.get("document_id") or "")
    extraction = str(row.get("extraction_sha256") or "").lower()
    if not document_id or not _SHA256.fullmatch(extraction):
        return None
    return document_id, extraction


def _index(row: dict[str, Any]) -> int | None:
    value = row.get("chunk_index")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def matching_preamble_span(
    content: str, section_title: str, *, max_chars: int = MAX_PREAMBLE_CHARS
) -> tuple[int, int] | None:
    """Return the final exact heading-to-boundary span for ``section_title``."""
    expected = normalize_heading(section_title)
    if not expected or not content:
        return None
    offset = 0
    starts: list[int] = []
    for line in content.splitlines(keepends=True):
        match = _HEADING.fullmatch(line.rstrip("\r\n"))
        if match and normalize_heading(match.group(1)) == expected:
            starts.append(offset)
        offset += len(line)
    if not starts:
        return None
    start = starts[-1]
    end = len(content)
    if not 0 <= start < end or end - start > max_chars:
        return None
    return start, end


def select_table_preambles(
    seeds: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    max_preambles: int = MAX_PREAMBLES,
    max_chars: int = MAX_PREAMBLE_CHARS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select exact same-blob predecessor preambles without mutating inputs."""
    if (
        isinstance(max_preambles, bool)
        or not isinstance(max_preambles, int)
        or not 1 <= max_preambles <= MAX_PREAMBLES
        or isinstance(max_chars, bool)
        or not isinstance(max_chars, int)
        or not 1 <= max_chars <= MAX_PREAMBLE_CHARS
    ):
        raise ValueError("invalid table preamble bounds")

    candidate_by_position: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for candidate in candidates:
        identity = _identity(candidate)
        index = _index(candidate)
        if identity is None or index is None:
            continue
        candidate_by_position.setdefault((*identity, index), []).append(candidate)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    trace: dict[str, Any] = {
        "lane": LANE,
        "validation": VALIDATION,
        "seed_rows": len(seeds),
        "table_seed_rows": 0,
        "exact_predecessor_rows": 0,
        "heading_matched_rows": 0,
        "cross_table_rejected_rows": 0,
        "selected_ids": [],
        "model_calls": 0,
        "database_writes": 0,
    }
    for seed in seeds:
        if len(selected) >= max_preambles:
            break
        identity = _identity(seed)
        index = _index(seed)
        title = str(seed.get("section_title") or "")
        if (
            identity is None
            or index is None
            or index == 0
            or not title.strip()
            or not begins_with_markdown_table(str(seed.get("content") or ""))
        ):
            continue
        trace["table_seed_rows"] += 1
        predecessors = candidate_by_position.get((*identity, index - 1), [])
        if len(predecessors) != 1:
            continue
        trace["exact_predecessor_rows"] += 1
        predecessor = predecessors[0]
        predecessor_id = str(predecessor.get("id") or "")
        if not predecessor_id or predecessor_id in seen:
            continue
        content = str(predecessor.get("content") or "")
        span = matching_preamble_span(content, title, max_chars=max_chars)
        if span is None:
            continue
        trace["heading_matched_rows"] += 1
        start, end = span
        if contains_markdown_table(content[start:end]):
            trace["cross_table_rejected_rows"] += 1
            continue
        card = {
            "candidate_id": predecessor_id,
            "candidate_rank": len(selected) + 1,
            "start": start,
            "end": end,
            "quote": content[start:end],
            "facet": "table_preamble",
            "exact_source_span_validated": True,
        }
        enriched = dict(predecessor)
        enriched.update(
            {
                "retrieval_lane": LANE,
                "table_preamble_validated": True,
                "table_preamble_validation": VALIDATION,
                "table_preamble_seed_id": str(seed.get("id") or ""),
                "table_preamble_seed_chunk_index": index,
                "table_preamble_rank": len(selected) + 1,
                "coverage_cards": [card],
                "coverage_card_facets": ["table_preamble"],
                "local_semantic_validated": True,
            }
        )
        selected.append(enriched)
        seen.add(predecessor_id)

    trace["selected_ids"] = [str(row["id"]) for row in selected]
    trace["status"] = "selected" if selected else "no_exact_table_preamble"
    return selected, trace
