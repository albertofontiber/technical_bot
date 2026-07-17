#!/usr/bin/env python3
"""Freeze S198's fresh chunks_v2 cohort and report the remaining reserve."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import _eligible, _quality
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s194_build_fresh_source_packet import (
    DEFAULT_ENV,
    PRIOR_PACKETS,
    TARGET_FILES,
    _prior_contract,
    file_sha,
    read_chunks_v2 as _read_chunks_v2,
)
from scripts.s195_build_fresh_source_packet import (
    S194_PACKET,
    exclude_target_equivalents,
)
from scripts.s197_build_fresh_source_packet import (
    S195_PACKET,
    target_uuid_resolution,
)
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s198_fresh_source_packet_v2.json"
S197_PACKET = ROOT / "evals/s197_fresh_source_packet_v1.json"
SEED = "s198-point-first-scope-fresh-v1"
TABLE_ITEMS = 7
PROSE_ITEMS = 5
PRIOR_SOURCE_PACKETS = (*PRIOR_PACKETS, S194_PACKET, S195_PACKET, S197_PACKET)


def _content_sha(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def read_chunks_v2_stable(
    env_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Require two byte-equivalent complete GET-only scans."""
    first_rows, first = _read_chunks_v2(env_file, experiment="S198_SCAN_1")
    second_rows, second = _read_chunks_v2(env_file, experiment="S198_SCAN_2")
    first_sha = stable_sha(first_rows)
    second_sha = stable_sha(second_rows)
    if (
        first_sha != second_sha
        or first.get("rows") != second.get("rows")
        or first.get("database_writes") != 0
        or second.get("database_writes") != 0
    ):
        raise RuntimeError("S198 chunks_v2 double-scan fingerprint drift")

    def receipt(value: dict[str, Any], full_sha: str) -> dict[str, Any]:
        return {
            **{key: item for key, item in value.items() if key != "snapshot_sha256"},
            "full_scan_sha256": full_sha,
        }

    return second_rows, {
        "table": "chunks_v2",
        "rows": len(second_rows),
        "get_requests": int(first["get_requests"]) + int(second["get_requests"]),
        "database_writes": 0,
        "stable_full_scan_sha256": second_sha,
        "consistency": "DOUBLE_IDENTICAL_FULL_SCAN",
        "scan_1": receipt(first, first_sha),
        "scan_2": receipt(second, second_sha),
    }


def _target_ids() -> set[str]:
    result: set[str] = set()
    for path in TARGET_FILES:
        result.update(
            value.lower()
            for value in collect_uuid_strings(
                json.loads(path.read_text(encoding="utf-8"))
            )
        )
    return result


def eligible_inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count the exact post-exclusion candidate population before S198 selection."""
    prior_documents, development_pairs, prior_source_files, _ = _prior_contract(
        PRIOR_SOURCE_PACKETS
    )
    prior_documents = set(prior_documents)
    prior_documents.update(
        str(row["document_id"])
        for row in rows
        if _normalized(row.get("source_file")) in prior_source_files
    )
    target_ids = _target_ids()
    target_documents = {
        str(row["document_id"])
        for row in rows
        if str(row.get("id") or "").lower() in target_ids
        or str(row.get("document_id") or "").lower() in target_ids
    }
    excluded_documents = prior_documents | target_documents
    active = {str(row["document_id"]) for row in rows}
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if row.get("document_id") in excluded_documents:
            continue
        pair = (_normalized(row.get("manufacturer")), _normalized(row.get("product_model")))
        if pair in development_pairs:
            continue
        if not _eligible({**row, "kind": "chunk"}, active, excluded_documents):
            continue
        units = build_header_aware_evidence_units(
            row["content"], fragment_number=1, candidate_id=row["id"]
        )
        candidates.append(
            {
                "chunk_id": str(row["id"]),
                "document_id": str(row["document_id"]),
                "source_file": str(row.get("source_file") or ""),
                "manufacturer": str(row["manufacturer"]),
                "product_model": str(row["product_model"]),
                "stratum": (
                    "table"
                    if any(unit.unit_kind == "table_row_with_header" for unit in units)
                    else "prose"
                ),
            }
        )

    def counts(values: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "chunk_rows": len(values),
            "documents": len({row["document_id"] for row in values}),
            "source_files": len(
                {_normalized(row["source_file"]) for row in values if row["source_file"]}
            ),
            "manufacturer_product_pairs": len(
                {
                    (_normalized(row["manufacturer"]), _normalized(row["product_model"]))
                    for row in values
                }
            ),
            "manufacturers": len({_normalized(row["manufacturer"]) for row in values}),
            "table_documents": len(
                {row["document_id"] for row in values if row["stratum"] == "table"}
            ),
            "prose_documents": len(
                {row["document_id"] for row in values if row["stratum"] == "prose"}
            ),
            "table_manufacturers": len(
                {
                    _normalized(row["manufacturer"])
                    for row in values
                    if row["stratum"] == "table"
                }
            ),
            "prose_manufacturers": len(
                {
                    _normalized(row["manufacturer"])
                    for row in values
                    if row["stratum"] == "prose"
                }
            ),
        }

    return {
        "definition": (
            "post_target_equivalence_post_prior_document_source_file_pair_and_"
            "generic_eligibility"
        ),
        "counts": counts(candidates),
        "candidates": candidates,
    }


def build_exhaustion_aware_packet(
    rows: list[dict[str, Any]], read_receipt: dict[str, Any]
) -> dict[str, Any]:
    """Select 7 table + all 5 available prose manufacturers under frozen exclusions."""
    prior_documents, development_pairs, prior_source_files, dependencies = _prior_contract(
        PRIOR_SOURCE_PACKETS
    )
    prior_documents = set(prior_documents)
    prior_documents.update(
        str(row["document_id"])
        for row in rows
        if _normalized(row.get("source_file")) in prior_source_files
    )
    target_ids = _target_ids()
    target_documents = {
        str(row["document_id"])
        for row in rows
        if str(row.get("id") or "").lower() in target_ids
        or str(row.get("document_id") or "").lower() in target_ids
    }
    excluded_documents = prior_documents | target_documents
    active = {str(row["document_id"]) for row in rows}
    candidates: list[dict[str, Any]] = []
    exclusion_counts = {
        "prior_or_target_document": 0,
        "development_product_pair": 0,
        "generic_eligibility": 0,
    }
    for row in rows:
        if row.get("document_id") in excluded_documents:
            exclusion_counts["prior_or_target_document"] += 1
            continue
        pair = (_normalized(row.get("manufacturer")), _normalized(row.get("product_model")))
        if pair in development_pairs:
            exclusion_counts["development_product_pair"] += 1
            continue
        if not _eligible({**row, "kind": "chunk"}, active, excluded_documents):
            exclusion_counts["generic_eligibility"] += 1
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
    for stratum, required in (("table", TABLE_ITEMS), ("prose", PROSE_ITEMS)):
        best_by_manufacturer: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            row = candidate["row"]
            manufacturer = _normalized(row["manufacturer"])
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
        if len(ranked) < required:
            raise RuntimeError(
                f"S198 exhaustion-aware insufficient {stratum} manufacturers: "
                f"{len(ranked)} < {required}"
            )
        chosen = ranked[:required]
        selected.extend(chosen)
        used_manufacturers.update(
            _normalized(item["row"]["manufacturer"]) for item in chosen
        )
    items = []
    for index, candidate in enumerate(selected, 1):
        row = candidate["row"]
        content = row["content"]
        item = {
            "item_id": f"s198e_src_{index:02d}",
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
        units = build_header_aware_evidence_units(
            content, fragment_number=1, candidate_id=item["item_id"]
        )
        item["evidence_unit_manifest"] = [
            {
                "unit_id": unit.unit_id,
                "unit_kind": unit.unit_kind,
                "source_spans": [list(span) for span in unit.source_spans],
                "content_sha256": unit.content_sha256,
            }
            for unit in units
        ]
        items.append(item)
    for path in TARGET_FILES:
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    unitizer = ROOT / "src/rag/evidence_units_v2.py"
    dependencies[str(unitizer.relative_to(ROOT)).replace("\\", "/")] = file_sha(unitizer)
    body = {
        "instrument": "s198_fresh_source_packet_v2",
        "status": "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY",
        "selection": {
            "seed": SEED,
            "items": len(items),
            "manufacturers": len({_normalized(item["manufacturer"]) for item in items}),
            "unique_documents": len({item["document_id"] for item in items}),
            "table": sum(item["stratum"] == "table" for item in items),
            "prose": sum(item["stratum"] == "prose" for item in items),
            "question_or_gold_used_for_selection": False,
            "fresh_after_s198_population_no_go": True,
            "prior_document_overlap": sum(
                item["document_id"] in prior_documents for item in items
            ),
            "target_document_overlap": sum(
                item["document_id"] in target_documents for item in items
            ),
            "target_chunk_overlap": sum(
                str(item["chunk_id"]).lower() in target_ids for item in items
            ),
            "development_product_pair_overlap": sum(
                (_normalized(item["manufacturer"]), _normalized(item["product_model"]))
                in development_pairs
                for item in items
            ),
            "prior_documents_excluded": len(prior_documents),
            "target_documents_excluded": len(target_documents),
            "exclusion_counts": exclusion_counts,
        },
        "items": items,
        "read_receipt": read_receipt,
        "dependencies": dependencies,
    }
    return {**body, "packet_sha256": stable_sha(body)}


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
    inventory = eligible_inventory(eligible_rows)
    packet = build_exhaustion_aware_packet(eligible_rows, read_receipt)
    packet.pop("packet_sha256", None)
    selected_content = {_content_sha(row["excerpt"]) for row in packet["items"]}
    selected_extraction = {
        str(row["extraction_sha256"])
        for row in packet["items"]
        if row.get("extraction_sha256")
    }
    packet["selection"].update(
        {
            "target_exact_content_overlap": len(
                selected_content.intersection(target_equivalence["content_sha256"])
            ),
            "target_extraction_overlap": len(
                selected_extraction.intersection(target_equivalence["extraction_sha256"])
            ),
            "s194_document_overlap": 0,
            "s195_document_overlap": 0,
            "s197_document_overlap": 0,
            "population_contract": "EXHAUSTION_AWARE_7_TABLE_5_PROSE",
            "prior_semantic_near_duplicate_overlap_status": "NOT_MEASURED",
            "prior_oem_relabel_overlap_status": "NOT_MEASURED",
        }
    )
    selected_documents = {row["document_id"] for row in packet["items"]}
    reserve = [
        row for row in inventory.pop("candidates") if row["document_id"] not in selected_documents
    ]
    inventory["selected_identities"] = [
        {
            key: row[key]
            for key in (
                "item_id",
                "document_id",
                "chunk_id",
                "source_file",
                "manufacturer",
                "product_model",
                "stratum",
            )
        }
        for row in packet["items"]
    ]
    inventory["post_selection_reserve_definition"] = (
        "eligible candidate rows excluding selected documents; may include selected "
        "manufacturers or manufacturer-product pairs and is not a future "
        "manufacturer-disjoint cohort capacity claim"
    )
    inventory["post_selection_reserve"] = eligible_inventory_counts(reserve)
    packet["eligible_inventory"] = inventory
    packet["target_equivalence_exclusion"] = target_equivalence
    packet["packet_sha256"] = stable_sha(packet)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": packet["status"],
                "selection": packet["selection"],
                "eligible_inventory": inventory["counts"],
                "post_selection_reserve": inventory["post_selection_reserve"],
                "read_rows": read_receipt["rows"],
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


def eligible_inventory_counts(values: list[dict[str, Any]]) -> dict[str, int]:
    """Public deterministic counter for a previously filtered candidate list."""
    return {
        "chunk_rows": len(values),
        "documents": len({row["document_id"] for row in values}),
        "source_files": len(
            {_normalized(row["source_file"]) for row in values if row["source_file"]}
        ),
        "manufacturer_product_pairs": len(
            {
                (_normalized(row["manufacturer"]), _normalized(row["product_model"]))
                for row in values
            }
        ),
        "manufacturers": len({_normalized(row["manufacturer"]) for row in values}),
        "table_documents": len(
            {row["document_id"] for row in values if row["stratum"] == "table"}
        ),
        "prose_documents": len(
            {row["document_id"] for row in values if row["stratum"] == "prose"}
        ),
        "table_manufacturers": len(
            {
                _normalized(row["manufacturer"])
                for row in values
                if row["stratum"] == "table"
            }
        ),
        "prose_manufacturers": len(
            {
                _normalized(row["manufacturer"])
                for row in values
                if row["stratum"] == "prose"
            }
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
