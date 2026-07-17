from __future__ import annotations

import json
from pathlib import Path

from src.rag.evidence_units_v2 import (
    build_header_aware_evidence_units,
    reconstruct_unit_content,
)


ROOT = Path(__file__).resolve().parents[1]


def test_burned_fixed_width_table_row_carries_its_headers() -> None:
    packet = json.loads(
        (ROOT / "evals/s145_adversarial_sufficiency_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    source = packet["questions"][0]["full_source"]
    units = build_header_aware_evidence_units(
        source, fragment_number=1, candidate_id="burned-q01"
    )
    matches = [
        unit
        for unit in units
        if unit.unit_kind == "table_row_with_header"
        and "Set Z1-Z8, Zone Alarm Delayed" in unit.content
    ]
    assert len(matches) == 1
    assert "Permitted in UL 864" in matches[0].content
    assert "Settings Permitted" in matches[0].content
    assert "Clear all zones" in matches[0].content


def test_markdown_row_is_composed_with_header_and_source_bound() -> None:
    source = (
        "Settings\n\n"
        "| Mode | Delay | Allowed |\n"
        "| --- | ---: | :---: |\n"
        "| Alarm | 30 s | Yes |\n"
        "| Fault | 10 s | No |\n"
    )
    units = build_header_aware_evidence_units(
        source, fragment_number=2, candidate_id="markdown-table"
    )
    rows = [unit for unit in units if unit.unit_kind == "table_row_with_header"]
    assert len(rows) == 2
    assert all("| Mode | Delay | Allowed |" in unit.content for unit in rows)
    assert all(reconstruct_unit_content(source, unit) == unit.content for unit in units)


def test_units_are_deterministic_and_identity_changes_with_candidate() -> None:
    source = "Heading\n\nFirst technical paragraph.\n\nSecond technical paragraph."
    first = build_header_aware_evidence_units(
        source, fragment_number=3, candidate_id="chunk-a"
    )
    second = build_header_aware_evidence_units(
        source, fragment_number=3, candidate_id="chunk-a"
    )
    changed = build_header_aware_evidence_units(
        source, fragment_number=3, candidate_id="chunk-b"
    )
    assert first == second
    assert [unit.unit_id for unit in first] != [unit.unit_id for unit in changed]
    assert all(reconstruct_unit_content(source, unit) == unit.content for unit in first)
    assert {unit.unit_kind for unit in first} == {"contiguous"}
