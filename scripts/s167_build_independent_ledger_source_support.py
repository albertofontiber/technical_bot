"""Small dependency-free helpers for the S167 source packet builder."""
from __future__ import annotations

import re
from typing import Any


UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def collect_uuid_strings(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.update(UUID_RE.findall(str(key)))
            found.update(collect_uuid_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_uuid_strings(child))
    elif isinstance(value, str):
        found.update(UUID_RE.findall(value))
    return {item.lower() for item in found}
