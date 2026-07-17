#!/usr/bin/env python3
"""Build a deterministic, source-first S146 packet without opening its text."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "tmp/s117_m25/derived_snapshot_v2.jsonl.gz"
PRIOR_CHUNKS = ROOT / "tmp/s135_representative_chunks_shadow_v2/chunks.csv"
DEFAULT_OUT = ROOT / "evals/s146_fresh_source_packet_v1.json"
SEED = "s146_fresh_source_packet_v1"
RELATION = re.compile(
    r"(?i)\b(?:must|shall|should|before|after|when|if|set|select|configure|connect|"
    r"debe|deber[áa]|antes|despu[ée]s|cuando|si|ajust|seleccion|configur|conect|"
    r"alarm|fault|aver[ií]a|tensi[oó]n|volt|corriente|resistencia|terminal)\b"
)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _excluded_documents() -> set[str]:
    with PRIOR_CHUNKS.open(encoding="utf-8", newline="") as handle:
        return {row["document_id"] for row in csv.DictReader(handle)}


def _quality(row: dict[str, Any]) -> int:
    text = str(row["content"])
    relation_count = len(RELATION.findall(text))
    numeric_count = len(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*(?:V|mA|A|s|min|%|Ω|ohm))?\b", text, re.I))
    return min(relation_count, 30) * 8 + min(numeric_count, 25) * 2 + min(len(text) // 250, 16)


def _eligible(row: dict[str, Any], active: set[str], excluded: set[str]) -> bool:
    text = str(row.get("content") or "")
    return bool(
        row.get("kind") == "chunk"
        and row.get("document_id") in active
        and row.get("document_id") not in excluded
        and row.get("manufacturer")
        and row.get("product_model")
        and row.get("source_file")
        and 900 <= len(text) <= 4500
        and "table of contents" not in text.casefold()
        and "contenido" != str(row.get("section_title") or "").strip().casefold()
        and text.count("�") / max(1, len(text)) <= 0.002
        and len(RELATION.findall(text)) >= 2
    )


def build_packet() -> dict[str, Any]:
    excluded = _excluded_documents()
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
        text = row["content"]
        units = build_header_aware_evidence_units(
            text, fragment_number=1, candidate_id=row["id"]
        )
        has_contextual_table = any(unit.unit_kind == "table_row_with_header" for unit in units)
        candidates.append(
            {
                "row": row,
                "stratum": "table" if has_contextual_table else "prose",
                "quality": _quality(row),
                "tie": stable_sha({"seed": SEED, "chunk_id": row["id"]}),
            }
        )

    selected: list[dict[str, Any]] = []
    used_manufacturers: set[str] = set()
    for stratum in ("table", "prose"):
        best_by_manufacturer: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            row = candidate["row"]
            manufacturer = row["manufacturer"]
            if candidate["stratum"] != stratum or manufacturer in used_manufacturers:
                continue
            current = best_by_manufacturer.get(manufacturer)
            key = (candidate["quality"], candidate["tie"])
            if current is None or key > (current["quality"], current["tie"]):
                best_by_manufacturer[manufacturer] = candidate
        ranked = sorted(
            best_by_manufacturer.values(),
            key=lambda item: (-item["quality"], item["tie"]),
        )
        if len(ranked) < 7:
            raise RuntimeError(f"S146 insufficient {stratum} manufacturers")
        chosen = ranked[:7]
        selected.extend(chosen)
        used_manufacturers.update(item["row"]["manufacturer"] for item in chosen)

    items = []
    for index, candidate in enumerate(selected, 1):
        row = candidate["row"]
        excerpt = row["content"]
        items.append(
            {
                "item_id": f"s146_src_{index:02d}",
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
        "instrument": "s146_fresh_source_packet_v1",
        "status": "SEALED_SOURCE_FIRST",
        "selection": {
            "seed": SEED,
            "items": 14,
            "manufacturers": 14,
            "table": 7,
            "prose": 7,
            "prior_s135_documents_excluded": len(excluded),
            "question_or_gold_used_for_selection": False,
        },
        "dependencies": {
            "snapshot_sha256": file_sha(SNAPSHOT),
            "prior_chunks_sha256": file_sha(PRIOR_CHUNKS),
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
    print(
        json.dumps(
            {
                "status": packet["status"],
                **{key: packet["selection"][key] for key in ("items", "manufacturers", "table", "prose")},
                "packet_sha256": packet["packet_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
