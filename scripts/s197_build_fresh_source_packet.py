#!/usr/bin/env python3
"""Freeze S197's real-document cohort, excluding both S194 and S195."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s194_build_fresh_source_packet import (
    DEFAULT_ENV,
    PRIOR_PACKETS,
    TARGET_FILES,
    build_packet,
    read_chunks_v2 as _read_chunks_v2,
)
from scripts.s195_build_fresh_source_packet import (
    S194_PACKET,
    exclude_target_equivalents,
)
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s197_fresh_source_packet_v1.json"
S195_PACKET = ROOT / "evals/s195_fresh_source_packet_v1.json"
SEED = "s197-static-author-luna-fresh-v1"
PRIOR_SOURCE_PACKETS = (*PRIOR_PACKETS, S194_PACKET, S195_PACKET)


def _content_sha(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def read_chunks_v2_stable(
    env_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Require two identical full GET-only scans, not merely stable cardinality."""
    first_rows, first = _read_chunks_v2(env_file, experiment="S197_SCAN_1")
    second_rows, second = _read_chunks_v2(env_file, experiment="S197_SCAN_2")
    first_sha = stable_sha(first_rows)
    second_sha = stable_sha(second_rows)
    if (
        first_sha != second_sha
        or first.get("rows") != second.get("rows")
        or first.get("database_writes") != 0
        or second.get("database_writes") != 0
    ):
        raise RuntimeError("S197 chunks_v2 double-scan fingerprint drift")
    first_receipt = {
        **{key: value for key, value in first.items() if key != "snapshot_sha256"},
        "full_scan_sha256": first_sha,
    }
    second_receipt = {
        **{key: value for key, value in second.items() if key != "snapshot_sha256"},
        "full_scan_sha256": second_sha,
    }
    return second_rows, {
        "table": "chunks_v2",
        "rows": len(second_rows),
        "get_requests": int(first["get_requests"]) + int(second["get_requests"]),
        "database_writes": 0,
        "stable_full_scan_sha256": second_sha,
        "consistency": "DOUBLE_IDENTICAL_FULL_SCAN",
        "scan_1": first_receipt,
        "scan_2": second_receipt,
    }


def target_uuid_resolution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_ids: set[str] = set()
    for path in TARGET_FILES:
        target_ids.update(
            value.lower()
            for value in collect_uuid_strings(
                json.loads(path.read_text(encoding="utf-8"))
            )
        )
    resolution = []
    for target_id in sorted(target_ids):
        chunk_matches = sum(
            str(row.get("id") or "").lower() == target_id for row in rows
        )
        document_matches = sum(
            str(row.get("document_id") or "").lower() == target_id for row in rows
        )
        if not chunk_matches and not document_matches:
            raise RuntimeError(f"S197 protected target UUID unresolved: {target_id}")
        resolution.append(
            {
                "target_uuid": target_id,
                "status": (
                    "RESOLVED_AS_CHUNK_AND_DOCUMENT"
                    if chunk_matches and document_matches
                    else (
                        "RESOLVED_AS_CHUNK"
                        if chunk_matches
                        else "RESOLVED_AS_DOCUMENT"
                    )
                ),
                "chunk_rows": chunk_matches,
                "document_rows": document_matches,
                "resolved_rows": chunk_matches + document_matches,
            }
        )
    if not resolution:
        raise RuntimeError("S197 protected target UUID inventory is empty")
    return resolution


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows, read_receipt = read_chunks_v2_stable(args.env_file)
    eligible_rows, target_equivalence = exclude_target_equivalents(rows)
    target_equivalence["target_uuid_resolution"] = target_uuid_resolution(rows)
    target_equivalence["unresolved_target_uuids"] = []
    target_equivalence["all_target_uuids_resolved"] = True
    target_equivalence["source_stable_full_scan_sha256"] = read_receipt[
        "stable_full_scan_sha256"
    ]
    packet = build_packet(
        eligible_rows,
        read_receipt,
        seed=SEED,
        instrument="s197_fresh_source_packet_v1",
        item_prefix="s197_src",
        prior_packets=PRIOR_SOURCE_PACKETS,
        fresh_marker="fresh_after_s196",
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
    packet["selection"]["s194_document_overlap"] = 0
    packet["selection"]["s195_document_overlap"] = 0
    packet["selection"]["prior_semantic_near_duplicate_overlap_status"] = (
        "NOT_MEASURED"
    )
    packet["selection"]["prior_oem_relabel_overlap_status"] = "NOT_MEASURED"
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
                "s195_packet_excluded": True,
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
