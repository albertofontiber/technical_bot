#!/usr/bin/env python3
"""Freeze S195's entirely fresh, read-only chunks_v2 author cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s194_build_fresh_source_packet import (
    DEFAULT_ENV,
    PRIOR_PACKETS,
    TARGET_FILES,
    build_packet,
    read_chunks_v2,
)
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s195_fresh_source_packet_v1.json"
S194_PACKET = ROOT / "evals/s194_fresh_source_packet_v1.json"
SEED = "s195-author-transport-fresh-v1"


def _content_sha(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def exclude_target_equivalents(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exclude exact content/extraction twins of UUID-bound protected target rows."""
    target_ids: set[str] = set()
    for path in TARGET_FILES:
        target_ids.update(
            collect_uuid_strings(json.loads(path.read_text(encoding="utf-8")))
        )
    target_rows = [
        row
        for row in rows
        if str(row.get("id")).lower() in target_ids
        or str(row.get("document_id")).lower() in target_ids
    ]
    content_hashes = {_content_sha(row.get("content")) for row in target_rows}
    extraction_hashes = {
        str(row["extraction_sha256"])
        for row in target_rows
        if row.get("extraction_sha256")
    }
    filtered = [
        row
        for row in rows
        if _content_sha(row.get("content")) not in content_hashes
        and str(row.get("extraction_sha256") or "") not in extraction_hashes
    ]
    return filtered, {
        "method": "TARGET_UUID_ROWS_TO_EXACT_CONTENT_AND_EXTRACTION_HASH_EXCLUSION",
        "target_uuid_count": len(target_ids),
        "target_rows_resolved": len(target_rows),
        "resolved_rows": [
            {
                "chunk_id": str(row["id"]),
                "document_id": str(row["document_id"]),
                "content_sha256": _content_sha(row.get("content")),
                "extraction_sha256": str(row.get("extraction_sha256") or ""),
            }
            for row in target_rows
        ],
        "content_sha256": sorted(content_hashes),
        "extraction_sha256": sorted(extraction_hashes),
        "rows_excluded": len(rows) - len(filtered),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows, read_receipt = read_chunks_v2(args.env_file, experiment="S195")
    eligible_rows, target_equivalence = exclude_target_equivalents(rows)
    packet = build_packet(
        eligible_rows,
        read_receipt,
        seed=SEED,
        instrument="s195_fresh_source_packet_v1",
        item_prefix="s195_src",
        prior_packets=(*PRIOR_PACKETS, S194_PACKET),
        fresh_marker="fresh_after_s194",
    )
    packet.pop("packet_sha256", None)
    selected_content = {_content_sha(row["excerpt"]) for row in packet["items"]}
    selected_extraction = {
        str(row["extraction_sha256"])
        for row in packet["items"]
        if row.get("extraction_sha256")
    }
    packet["selection"]["target_exact_content_overlap"] = len(
        selected_content.intersection(target_equivalence["content_sha256"])
    )
    packet["selection"]["target_extraction_overlap"] = len(
        selected_extraction.intersection(target_equivalence["extraction_sha256"])
    )
    packet["target_equivalence_exclusion"] = target_equivalence
    packet["packet_sha256"] = stable_sha(packet)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": packet["status"],
                **{
                    key: packet["selection"][key]
                    for key in (
                        "items",
                        "manufacturers",
                        "unique_documents",
                        "table",
                        "prose",
                        "prior_document_overlap",
                        "target_document_overlap",
                        "development_product_pair_overlap",
                    )
                },
                "s194_packet_excluded": True,
                "target_exact_content_overlap": packet["selection"][
                    "target_exact_content_overlap"
                ],
                "target_extraction_overlap": packet["selection"][
                    "target_extraction_overlap"
                ],
                "read_rows": read_receipt["rows"],
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
