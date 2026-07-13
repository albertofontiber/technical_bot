"""Conservative, deterministic table-of-contents detection."""
from __future__ import annotations

import re

_TOC_DOT_LEADER_RE = re.compile(r"(?:\.[ \t]?){4,}[ \t]*(\d{1,4})[ \t]*$", re.M)
_TOC_HEADING_RE = re.compile(
    r"(?im)^[\s\d.·|#*—-]{0,12}(índice|indice|sommario|sumario|contenidos?|"
    r"tabla de contenidos?|table of contents|contents)\b[^\n]{0,40}$"
)
_TOC_TRAIL_NUM_RE = re.compile(r"(?:^|[ \t])(\d{1,4})[ \t]*$")


def _nondecreasing_ratio(numbers: list[int]) -> float:
    if len(numbers) < 2:
        return 0.0
    return sum(1 for left, right in zip(numbers, numbers[1:]) if right >= left) / (
        len(numbers) - 1
    )


def is_toc_page(text: str) -> bool:
    """Prefer false negatives: require a heading or four ordered dot leaders."""
    if not text:
        return False
    dot_numbers = [int(match.group(1)) for match in _TOC_DOT_LEADER_RE.finditer(text)]
    if (
        len(dot_numbers) >= 4
        and _nondecreasing_ratio(dot_numbers) >= 0.8
        and dot_numbers[-1] >= 5
    ):
        return True
    if _TOC_HEADING_RE.search(text[:300]):
        lines = [line for line in (raw.strip() for raw in text.splitlines()) if line]
        numbers = [
            int(match.group(1))
            for line in lines
            if (match := _TOC_TRAIL_NUM_RE.search(line))
        ]
        return (
            len(lines) >= 8
            and len(numbers) >= max(5, len(lines) // 2)
            and _nondecreasing_ratio(numbers) >= 0.8
            and numbers[-1] >= 5
        )
    return False
