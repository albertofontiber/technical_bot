#!/usr/bin/env python3
"""Build the document-independent S167 answer-ledger promotion packet."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import (
    SNAPSHOT,
    _eligible,
    _excluded_documents,
    _quality,
    file_sha,
    prior_chunks_sha256,
)
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
S114 = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
S146 = ROOT / "evals/s146_fresh_source_packet_v1.json"
S147 = ROOT / "evals/s147_fresh_source_packet_v1.json"
TARGET_FILES = (
    ROOT / "evals/s141_source_bound_technical_obligations_v1.json",
    ROOT / "evals/s149_target_evidence_selector_probe_v1.json",
    ROOT / "evals/s150_target_coverage_verifier_probe_v1.json",
    ROOT / "evals/s158_target_table_preamble_probe_v1.json",
    ROOT / "evals/s159_target_table_preamble_probe_v2.json",
    ROOT / "evals/s160_target_table_preamble_probe_v3.json",
    ROOT / "evals/s163_synthesis_residual_audit_v1.json",
)
DEFAULT_OUT = ROOT / "evals/s167_independent_ledger_source_packet_v1.json"
SEED = "s167-document-independent-ledger-v1"
PER_STRATUM = 7


def _content_sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _prior_document_ids(
    s114: dict[str, Any], s146: dict[str, Any], s147: dict[str, Any]
) -> set[str]:
    chosen_ids = {row["chunk_id"] for row in s114["chosen"]}
    return (
        _excluded_documents()
        | {s114["source_rows"][chunk_id]["document_id"] for chunk_id in chosen_ids}
        | {row["document_id"] for row in s146["items"]}
        | {row["document_id"] for row in s147["items"]}
    )


def build_from_rows(
    rows: list[dict[str, Any]],
    active: set[str],
    prior_documents: set[str],
    target_ids: set[str],
    development_pairs: set[tuple[str, str]],
    *,
    seed: str = SEED,
    instrument: str = "s167_independent_ledger_source_packet_v1",
    item_prefix: str = "s167_src",
    per_stratum: int = PER_STRATUM,
) -> dict[str, Any]:
    target_documents = {
        row["document_id"] for row in rows if str(row.get("id", "")).lower() in target_ids
    }
    excluded_documents = prior_documents | target_documents
    candidates = []
    exclusion_counts = {
        "prior_or_target_document": 0,
        "development_product_pair": 0,
        "generic_eligibility": 0,
    }
    for row in rows:
        if row.get("document_id") in excluded_documents:
            exclusion_counts["prior_or_target_document"] += 1
            continue
        pair = (
            str(row.get("manufacturer") or "").casefold(),
            str(row.get("product_model") or "").casefold(),
        )
        if pair in development_pairs:
            exclusion_counts["development_product_pair"] += 1
            continue
        if not _eligible(row, active, excluded_documents):
            exclusion_counts["generic_eligibility"] += 1
            continue
        units = build_header_aware_evidence_units(
            row["content"], fragment_number=1, candidate_id=row["id"]
        )
        stratum = (
            "table"
            if any(unit.unit_kind == "table_row_with_header" for unit in units)
            else "prose"
        )
        candidates.append(
            {
                "row": row,
                "stratum": stratum,
                "quality": _quality(row),
                "tie": stable_sha({"seed": seed, "chunk_id": row["id"]}),
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
        if len(ranked) < per_stratum:
            raise RuntimeError(
                f"S167 insufficient document-independent {stratum} manufacturers: "
                f"{len(ranked)}"
            )
        chosen = ranked[:per_stratum]
        selected.extend(chosen)
        used_manufacturers.update(item["row"]["manufacturer"] for item in chosen)

    items = []
    for index, candidate in enumerate(selected, start=1):
        row = candidate["row"]
        content = row["content"]
        items.append(
            {
                "item_id": f"{item_prefix}_{index:02d}",
                "stratum": candidate["stratum"],
                "manufacturer": row["manufacturer"],
                "product_model": row["product_model"],
                "document_id": row["document_id"],
                "chunk_id": row["id"],
                "extraction_sha256": row["extraction_sha256"],
                "source_file": row["source_file"],
                "page_number": row.get("page_number"),
                "section_title": row.get("section_title"),
                "section_path": row.get("section_path"),
                "excerpt": content,
                "excerpt_sha256": _content_sha(content),
                "selection_quality": candidate["quality"],
                "selection_tie": candidate["tie"],
            }
        )
    body: dict[str, Any] = {
        "instrument": instrument,
        "status": "SEALED_SOURCE_FIRST_DOCUMENT_INDEPENDENT",
        "selection": {
            "seed": seed,
            "items": len(items),
            "manufacturers": len({row["manufacturer"] for row in items}),
            "unique_documents": len({row["document_id"] for row in items}),
            "table": sum(row["stratum"] == "table" for row in items),
            "prose": sum(row["stratum"] == "prose" for row in items),
            "question_or_gold_used_for_selection": False,
            "prior_document_overlap": sum(
                row["document_id"] in prior_documents for row in items
            ),
            "target_document_overlap": sum(
                row["document_id"] in target_documents for row in items
            ),
            "target_chunk_overlap": sum(row["chunk_id"].lower() in target_ids for row in items),
            "development_product_pair_overlap": sum(
                (row["manufacturer"].casefold(), row["product_model"].casefold())
                in development_pairs
                for row in items
            ),
            "prior_documents_excluded": len(prior_documents),
            "target_documents_excluded": len(target_documents),
            "exclusion_counts": exclusion_counts,
        },
        "items": items,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def build_packet() -> dict[str, Any]:
    s114 = json.loads(S114.read_text(encoding="utf-8"))
    s146 = json.loads(S146.read_text(encoding="utf-8"))
    s147 = json.loads(S147.read_text(encoding="utf-8"))
    target_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in TARGET_FILES]
    target_ids: set[str] = set()
    for value in target_payloads:
        target_ids.update(collect_uuid_strings(value))
    development_pairs = {
        (row["manufacturer"].casefold(), row["product_model"].casefold())
        for row in s146["items"] + s147["items"]
    }
    active: set[str] = set()
    rows: list[dict[str, Any]] = []
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("kind") == "document" and row.get("status") == "active":
                active.add(row["id"])
            elif row.get("kind") == "chunk":
                rows.append(row)
    result = build_from_rows(
        rows,
        active,
        _prior_document_ids(s114, s146, s147),
        target_ids,
        development_pairs,
    )
    result.pop("packet_sha256", None)
    result["dependencies"] = {
        "snapshot_sha256": file_sha(SNAPSHOT),
        "prior_chunks_sha256": prior_chunks_sha256(),
        "s114_sha256": file_sha(S114),
        "s146_sha256": file_sha(S146),
        "s147_sha256": file_sha(S147),
        "target_files": {str(path.relative_to(ROOT)): file_sha(path) for path in TARGET_FILES},
    }
    return {**result, "packet_sha256": stable_sha(result)}


def main() -> int:
    result = build_packet()
    DEFAULT_OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["selection"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
