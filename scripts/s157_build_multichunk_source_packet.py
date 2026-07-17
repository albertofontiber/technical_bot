#!/usr/bin/env python3
"""Build a deterministic source-first multichunk cohort for S157."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import (
    RELATION,
    SNAPSHOT,
    _quality,
    prior_exclusion_contract,
)


ROOT = Path(__file__).resolve().parents[1]
S146_PACKET = ROOT / "evals/s146_fresh_source_packet_v1.json"
S147_PACKET = ROOT / "evals/s147_fresh_source_packet_v1.json"
TARGET_FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_OUT = ROOT / "evals/s157_multichunk_source_packet_v1.json"
SEED = "s157_multichunk_source_packet_v1"
QIDS = {"cat018", "hp002", "hp011", "hp017"}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def excluded_documents() -> set[str]:
    excluded, _ = prior_exclusion_contract()
    for path in (S146_PACKET, S147_PACKET):
        packet = json.loads(path.read_text(encoding="utf-8"))
        excluded.update(str(row["document_id"]) for row in packet["items"])
    freeze = json.loads(TARGET_FREEZE.read_text(encoding="utf-8"))
    for row in freeze["rows"]:
        if row["qid"] in QIDS:
            excluded.update(
                str(chunk["document_id"]) for chunk in row["context"] if chunk.get("document_id")
            )
    return excluded


def eligible(row: dict[str, Any], active: set[str], excluded: set[str]) -> bool:
    text = str(row.get("content") or "")
    return bool(
        row.get("kind") == "chunk"
        and row.get("document_id") in active
        and row.get("document_id") not in excluded
        and row.get("manufacturer") and row.get("product_model") and row.get("source_file")
        and isinstance(row.get("chunk_index"), int)
        and 700 <= len(text) <= 4500
        and "table of contents" not in text.casefold()
        and text.count("�") / max(1, len(text)) <= 0.002
        and len(RELATION.findall(text)) >= 2
    )


def build_packet() -> dict[str, Any]:
    excluded = excluded_documents()
    _, prior_chunks_sha256 = prior_exclusion_contract()
    active: set[str] = set()
    chunks: list[dict[str, Any]] = []
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("kind") == "document" and row.get("status") == "active":
                active.add(str(row["id"]))
            elif row.get("kind") == "chunk":
                chunks.append(row)

    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in chunks:
        if eligible(row, active, excluded):
            by_doc[str(row["document_id"])].append(row)

    windows: list[dict[str, Any]] = []
    for document_id, rows in by_doc.items():
        rows.sort(key=lambda row: (row["chunk_index"], row["id"]))
        for offset in range(len(rows) - 2):
            bundle = rows[offset : offset + 3]
            indices = [row["chunk_index"] for row in bundle]
            if indices[-1] - indices[0] > 4:
                continue
            manufacturers = {str(row["manufacturer"]) for row in bundle}
            models = {str(row["product_model"]) for row in bundle}
            extractions = {str(row["extraction_sha256"]) for row in bundle}
            if len(manufacturers) != 1 or len(models) != 1 or len(extractions) != 1:
                continue
            relation_total = sum(len(RELATION.findall(str(row["content"]))) for row in bundle)
            sections = {str(row.get("section_title") or "") for row in bundle}
            score = sum(_quality(row) for row in bundle) + min(relation_total, 40) * 3 + len(sections) * 8
            windows.append({
                "document_id": document_id, "rows": bundle, "score": score,
                "manufacturer": next(iter(manufacturers)),
                "tie": stable_sha({"seed": SEED, "document_id": document_id, "ids": [r["id"] for r in bundle]}),
            })

    best_by_manufacturer: dict[str, dict[str, Any]] = {}
    for window in windows:
        current = best_by_manufacturer.get(window["manufacturer"])
        if current is None or (window["score"], window["tie"]) > (current["score"], current["tie"]):
            best_by_manufacturer[window["manufacturer"]] = window
    ranked = sorted(best_by_manufacturer.values(), key=lambda row: (-row["score"], row["tie"]))
    if len(ranked) < 12:
        raise RuntimeError("S157 requires twelve distinct manufacturers")

    items = []
    for index, window in enumerate(ranked[:12], 1):
        rows = window["rows"]
        public_chunks = []
        for fragment, row in enumerate(rows, 1):
            content = str(row["content"])
            public_chunks.append({
                "fragment_number": fragment, "chunk_id": row["id"],
                "chunk_index": row["chunk_index"], "page_number": row.get("page_number"),
                "section_title": row.get("section_title"), "content_type": row.get("content_type"),
                "content": content, "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            })
        items.append({
            "item_id": f"s157_src_{index:02d}", "manufacturer": window["manufacturer"],
            "product_model": rows[0]["product_model"], "document_id": window["document_id"],
            "extraction_sha256": rows[0]["extraction_sha256"], "source_file": rows[0]["source_file"],
            "chunks": public_chunks,
            "bundle_sha256": stable_sha(public_chunks),
        })
    body = {
        "instrument": "s157_multichunk_source_packet_v1", "status": "SEALED_SOURCE_FIRST",
        "selection": {
            "seed": SEED, "items": 12, "chunks_per_item": 3, "manufacturers": 12,
            "documents": 12, "excluded_documents": len(excluded),
            "target_document_overlap": 0, "s146_s147_overlap": 0,
            "question_or_gold_used_for_selection": False,
        },
        "dependencies": {
            "snapshot_sha256": file_sha(SNAPSHOT), "prior_chunks_sha256": prior_chunks_sha256,
            "s146_packet_sha256": file_sha(S146_PACKET), "s147_packet_sha256": file_sha(S147_PACKET),
            "target_freeze_sha256": file_sha(TARGET_FREEZE),
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
    print(json.dumps({**packet["selection"], "packet_sha256": packet["packet_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
