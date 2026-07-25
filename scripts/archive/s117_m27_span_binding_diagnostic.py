#!/usr/bin/env python3
"""Read-only diagnostic for a failed M2.7C span/content binding gate."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts import s117_m27_live_evidence as live
from scripts import s117_m27_loss_accounted_alignment as m27b
from scripts import s117_m27_loss_safe_chunking_probe as probe
from src.reingest import chunk as chunk_module


_RECORD = re.compile(r"^[0-9a-f]{64}\.json$")


def _preview(value: str, limit: int = 500) -> str:
    value = value.replace("\r", "\\r").replace("\n", "\\n")
    return value[:limit]


def _mismatches(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    record = m27b._strict_json(raw)
    blocks = chunk_module._flatten(record.get("result", {}).get("pages", []))
    chunks = sorted(
        probe._with_treatment_override(record), key=lambda chunk: chunk.chunk_index
    )
    rows = [
        probe._fingerprinted(probe._row_core_from_treatment(chunk))
        for chunk in chunks
    ]
    groups: list[list[dict[str, Any]]] = []
    for row in rows:
        span = (row["source_block_start"], row["source_block_end"])
        if groups and span == (
            groups[-1][0]["source_block_start"],
            groups[-1][0]["source_block_end"],
        ):
            groups[-1].append(row)
        else:
            groups.append([row])
    findings = []
    cursor = 0
    for group in groups:
        start = group[0]["source_block_start"]
        end = group[0]["source_block_end"]
        raw_text = "\n\n".join(block.text for block in blocks[start : end + 1])
        treatment_text = "\n\n".join(row["content"] for row in group)
        raw_surface = live._surface(raw_text)
        treatment_surface = live._surface(treatment_text)
        if start != cursor or raw_surface != treatment_surface:
            findings.append({
                "extraction_sha256": path.stem,
                "expected_cursor": cursor,
                "source_block_start": start,
                "source_block_end": end,
                "row_ordinals": [row["ordinal"] for row in group],
                "raw_surface_sha256": probe._sha_bytes(raw_surface.encode("utf-8")),
                "treatment_surface_sha256": probe._sha_bytes(
                    treatment_surface.encode("utf-8")
                ),
                "raw_preview": _preview(raw_text),
                "treatment_preview": _preview(treatment_text),
                "first_surface_mismatch": live._first_surface_mismatch(
                    raw_text, treatment_text
                ),
            })
        cursor = end + 1
    if cursor != len(blocks):
        findings.append({
            "extraction_sha256": path.stem,
            "expected_cursor": cursor,
            "raw_blocks": len(blocks),
            "reason": "incomplete_partition",
        })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    findings = []
    documents_scanned = 0
    paths = (
        path for path in args.store.glob("*.json")
        if _RECORD.fullmatch(path.name)
    )
    for path in sorted(paths, key=lambda item: item.name):
        documents_scanned += 1
        findings.extend(_mismatches(path))
        if len(findings) >= args.limit:
            break
    print(json.dumps({
        "documents_scanned": documents_scanned,
        "findings": findings[: args.limit],
        "authorization": "diagnostic_only_no_contract_change",
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
