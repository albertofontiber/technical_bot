#!/usr/bin/env python3
"""Build the S147 source-first packet, excluding every prior challenge document."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import (
    PRIOR_CHUNKS,
    SNAPSHOT,
    _eligible,
    _excluded_documents,
    _quality,
    file_sha,
    stable_sha,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
PRIOR_PACKET = ROOT / "evals/s146_fresh_source_packet_v1.json"
DEFAULT_OUT = ROOT / "evals/s147_fresh_source_packet_v1.json"
SEED = "s147_fresh_source_packet_v1"


def build_packet() -> dict[str, Any]:
    prior = json.loads(PRIOR_PACKET.read_text(encoding="utf-8"))
    prior_documents = {row["document_id"] for row in prior["items"]}
    excluded = _excluded_documents() | prior_documents
    active: set[str] = set()
    rows: list[dict[str, Any]] = []
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("kind") == "document" and row.get("status") == "active":
                active.add(row["id"])
            elif row.get("kind") == "chunk":
                rows.append(row)

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not _eligible(row, active, excluded):
            continue
        units = build_header_aware_evidence_units(
            row["content"], fragment_number=1, candidate_id=row["id"]
        )
        candidates.append(
            {
                "row": row,
                "stratum": (
                    "table"
                    if any(unit.unit_kind == "table_row_with_header" for unit in units)
                    else "prose"
                ),
                "quality": _quality(row),
                "tie": stable_sha({"seed": SEED, "chunk_id": row["id"]}),
            }
        )

    selected: list[dict[str, Any]] = []
    used_manufacturers: set[str] = set()
    for stratum in ("table", "prose"):
        best_by_manufacturer: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            manufacturer = candidate["row"]["manufacturer"]
            if candidate["stratum"] != stratum or manufacturer in used_manufacturers:
                continue
            current = best_by_manufacturer.get(manufacturer)
            key = (candidate["quality"], candidate["tie"])
            if current is None or key > (current["quality"], current["tie"]):
                best_by_manufacturer[manufacturer] = candidate
        ranked = sorted(
            best_by_manufacturer.values(), key=lambda item: (-item["quality"], item["tie"])
        )
        if len(ranked) < 7:
            raise RuntimeError(f"S147 insufficient {stratum} manufacturers")
        chosen = ranked[:7]
        selected.extend(chosen)
        used_manufacturers.update(item["row"]["manufacturer"] for item in chosen)

    items = []
    for index, candidate in enumerate(selected, 1):
        row = candidate["row"]
        excerpt = row["content"]
        items.append(
            {
                "item_id": f"s147_src_{index:02d}",
                "stratum": candidate["stratum"],
                "manufacturer": row["manufacturer"],
                "product_model": row["product_model"],
                "document_id": row["document_id"],
                "chunk_id": row["id"],
                "extraction_sha256": row["extraction_sha256"],
                "source_file": row["source_file"],
                "page_number": row.get("page_number"),
                "section_title": row.get("section_title"),
                "excerpt": excerpt,
                "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
            }
        )
    body = {
        "instrument": "s147_fresh_source_packet_v1",
        "status": "SEALED_SOURCE_FIRST",
        "selection": {
            "seed": SEED,
            "items": 14,
            "manufacturers": 14,
            "table": 7,
            "prose": 7,
            "prior_documents_excluded": len(excluded),
            "s146_document_overlap": 0,
            "question_or_gold_used_for_selection": False,
        },
        "dependencies": {
            "snapshot_sha256": file_sha(SNAPSHOT),
            "prior_chunks_sha256": file_sha(PRIOR_CHUNKS),
            "s146_source_packet_sha256": file_sha(PRIOR_PACKET),
        },
        "items": items,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    packet = build_packet()
    args.out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": packet["status"], **packet["selection"], "packet_sha256": packet["packet_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
