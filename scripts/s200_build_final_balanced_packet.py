#!/usr/bin/env python3
"""Freeze the final 24-item, manufacturer-balanced point-first holdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s199_build_restored_margin_packet as base
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s194_build_fresh_source_packet import DEFAULT_ENV, TARGET_FILES, file_sha
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s200_final_balanced_source_packet_v1.json"
S199_PACKET = ROOT / "evals/s199_restored_margin_source_packet_v1.json"
PRIOR_SOURCE_PACKETS = (*base.PRIOR_SOURCE_PACKETS, S199_PACKET)
SEED = "s200-final-balanced-holdout-v1"
TABLE_ITEMS = 12
PROSE_ITEMS = 12
TOTAL_ITEMS = TABLE_ITEMS + PROSE_ITEMS


def _normalized(value: Any) -> str:
    return base._normalized(value)


def _content_sha(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def read_chunks_v2_stable(
    env_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first_rows, first = base._read_chunks_v2(env_file, experiment="S200_SCAN_1")
    second_rows, second = base._read_chunks_v2(env_file, experiment="S200_SCAN_2")
    first_sha = stable_sha(first_rows)
    second_sha = stable_sha(second_rows)
    if (
        first_sha != second_sha
        or first.get("rows") != second.get("rows")
        or first.get("database_writes") != 0
        or second.get("database_writes") != 0
    ):
        raise RuntimeError("S200 chunks_v2 double-scan fingerprint drift")

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


def collect_candidates(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prior_packets, seed = base.PRIOR_SOURCE_PACKETS, base.SEED
    base.PRIOR_SOURCE_PACKETS = PRIOR_SOURCE_PACKETS
    base.SEED = SEED
    try:
        return base.collect_candidates(rows)
    finally:
        base.PRIOR_SOURCE_PACKETS = prior_packets
        base.SEED = seed


def select_final_balanced(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Cover every available manufacturer, then fill each stratum by least representation."""
    available = {candidate["manufacturer_key"] for candidate in candidates}
    by_stratum = {
        stratum: {
            candidate["manufacturer_key"]
            for candidate in candidates
            if candidate["stratum"] == stratum
        }
        for stratum in ("table", "prose")
    }
    if (
        len(candidates) < TOTAL_ITEMS
        or len(by_stratum["table"]) < 8
        or len(by_stratum["prose"]) < 8
    ):
        raise RuntimeError("S200 final balanced source population is insufficient")

    selected: list[dict[str, Any]] = []
    used_documents: set[str] = set()
    used_sources: set[str] = set()
    used_pairs: set[tuple[str, str]] = set()
    manufacturer_counts: Counter[str] = Counter()
    stratum_counts: Counter[tuple[str, str]] = Counter()

    def feasible(candidate: dict[str, Any]) -> bool:
        source = candidate["source_file_key"]
        return (
            str(candidate["row"]["document_id"]) not in used_documents
            and (not source or source not in used_sources)
            and candidate["pair_key"] not in used_pairs
        )

    def choose(stratum: str, required: int) -> None:
        while sum(item["stratum"] == stratum for item in selected) < required:
            pool = [
                candidate
                for candidate in candidates
                if candidate["stratum"] == stratum and feasible(candidate)
            ]
            if not pool:
                raise RuntimeError(f"S200 cannot fill {stratum} without identity reuse")
            pool.sort(
                key=lambda candidate: (
                    stratum_counts[(stratum, candidate["manufacturer_key"])],
                    manufacturer_counts[candidate["manufacturer_key"]],
                    -candidate["quality"],
                    candidate["tie"],
                )
            )
            candidate = pool[0]
            selected.append(candidate)
            manufacturer = candidate["manufacturer_key"]
            manufacturer_counts[manufacturer] += 1
            stratum_counts[(stratum, manufacturer)] += 1
            used_documents.add(str(candidate["row"]["document_id"]))
            if candidate["source_file_key"]:
                used_sources.add(candidate["source_file_key"])
            used_pairs.add(candidate["pair_key"])

    # Prose has the smaller manufacturer inventory; allocate it before table.
    choose("prose", PROSE_ITEMS)
    choose("table", TABLE_ITEMS)
    covered = set(manufacturer_counts)
    if covered != available:
        raise RuntimeError(
            f"S200 selector failed maximum manufacturer coverage: {len(covered)} != {len(available)}"
        )
    selected.sort(
        key=lambda item: (0 if item["stratum"] == "table" else 1, item["tie"])
    )
    return selected, {
        "available_manufacturers": len(available),
        "covered_manufacturers": len(covered),
        "table_manufacturers": len(
            {item["manufacturer_key"] for item in selected if item["stratum"] == "table"}
        ),
        "prose_manufacturers": len(
            {item["manufacturer_key"] for item in selected if item["stratum"] == "prose"}
        ),
        "min_items_per_manufacturer": min(manufacturer_counts.values()),
        "max_items_per_manufacturer": max(manufacturer_counts.values()),
        "manufacturer_item_counts_sha256": stable_sha(dict(sorted(manufacturer_counts.items()))),
    }


def build_packet(
    rows: list[dict[str, Any]], read_receipt: dict[str, Any]
) -> dict[str, Any]:
    eligible_rows, target_equivalence = base.exclude_target_equivalents(rows)
    target_equivalence["target_uuid_resolution"] = base.target_uuid_resolution(rows)
    target_equivalence["unresolved_target_uuids"] = []
    target_equivalence["all_target_uuids_resolved"] = True
    target_equivalence["source_stable_full_scan_sha256"] = read_receipt[
        "stable_full_scan_sha256"
    ]
    candidates, contract = collect_candidates(eligible_rows)
    selected, balance = select_final_balanced(candidates)
    items: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected, 1):
        row = candidate["row"]
        content = row["content"]
        item = {
            "item_id": f"s200_src_{index:02d}",
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

    selected_documents = {str(item["document_id"]) for item in items}
    selected_content = {_content_sha(item["excerpt"]) for item in items}
    selected_extraction = {
        str(item["extraction_sha256"])
        for item in items
        if item.get("extraction_sha256")
    }
    reserve = [
        candidate
        for candidate in candidates
        if str(candidate["row"]["document_id"]) not in selected_documents
    ]
    dependencies = contract["dependencies"]
    for path in TARGET_FILES:
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    for path in (
        ROOT / "scripts/s200_build_final_balanced_packet.py",
        ROOT / "src/rag/evidence_units_v2.py",
    ):
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    zero_overlap = {
        "prior_document_overlap": sum(
            str(item["document_id"]) in contract["prior_documents"] for item in items
        ),
        "prior_source_file_overlap": sum(
            _normalized(item["source_file"]) in contract["prior_source_files"]
            for item in items
        ),
        "prior_manufacturer_product_pair_overlap": sum(
            (_normalized(item["manufacturer"]), _normalized(item["product_model"]))
            in contract["prior_pairs"]
            for item in items
        ),
        "target_document_overlap": sum(
            str(item["document_id"]) in contract["target_documents"] for item in items
        ),
        "target_chunk_overlap": sum(
            str(item["chunk_id"]).lower() in contract["target_ids"] for item in items
        ),
        "target_exact_content_overlap": len(
            selected_content.intersection(target_equivalence["content_sha256"])
        ),
        "target_extraction_overlap": len(
            selected_extraction.intersection(target_equivalence["extraction_sha256"])
        ),
    }
    body = {
        "instrument": "s200_final_balanced_source_packet_v1",
        "status": "SEALED_FINAL_FRESH_LIVE_CHUNKS_V2_GET_ONLY",
        "selection": {
            "seed": SEED,
            "population_contract": "FINAL_24_ITEM_12_TABLE_12_PROSE_MAXIMUM_MANUFACTURER_BALANCE",
            "items": len(items),
            "table": sum(item["stratum"] == "table" for item in items),
            "prose": sum(item["stratum"] == "prose" for item in items),
            "unique_documents": len(selected_documents),
            "unique_source_files": len({_normalized(item["source_file"]) for item in items}),
            "unique_manufacturer_product_pairs": len(
                {(_normalized(item["manufacturer"]), _normalized(item["product_model"])) for item in items}
            ),
            **balance,
            **zero_overlap,
            "question_gold_claim_facet_or_model_outcome_used_for_selection": False,
            "aggregate_counts_from_s198_s199_only": True,
            "semantic_near_duplicate_overlap_status": "NOT_MEASURED",
            "oem_relabel_overlap_status": "NOT_MEASURED",
            "exclusion_counts": contract["exclusion_counts"],
        },
        "items": items,
        "eligible_inventory": {
            "definition": "post_target_equivalence_post_all_prior_through_s199_document_source_file_pair_and_generic_eligibility",
            "counts": base.inventory_counts(candidates),
            "post_selection_reserve_definition": "eligible candidate rows excluding selected documents; point-first lane closes after S200 regardless of reserve",
            "post_selection_reserve": base.inventory_counts(reserve),
        },
        "read_receipt": read_receipt,
        "target_equivalence_exclusion": target_equivalence,
        "dependencies": dependencies,
        "chunks_v3_lane": {
            "status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "changed_by_s200": False,
        },
        "railway_deploy_gate": False,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows, receipt = read_chunks_v2_stable(args.env_file)
    packet = build_packet(rows, receipt)
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": packet["status"],
                "selection": packet["selection"],
                "inventory": packet["eligible_inventory"]["counts"],
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
