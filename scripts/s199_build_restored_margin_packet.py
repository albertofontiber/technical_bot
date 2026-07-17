#!/usr/bin/env python3
"""Freeze S199's fresh 14-item chunks_v2 cohort without semantic postselection."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import _eligible, _quality
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings
from scripts.s194_build_fresh_source_packet import (
    DEFAULT_ENV,
    TARGET_FILES,
    _prior_contract,
    file_sha,
    read_chunks_v2 as _read_chunks_v2,
)
from scripts.s195_build_fresh_source_packet import exclude_target_equivalents
from scripts.s197_build_fresh_source_packet import target_uuid_resolution
from scripts.s198_build_fresh_source_packet import (
    PRIOR_SOURCE_PACKETS as S198_PRIOR_SOURCE_PACKETS,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s199_restored_margin_source_packet_v1.json"
S198_PACKET = ROOT / "evals/s198_fresh_source_packet_v2.json"
PRIOR_SOURCE_PACKETS = (*S198_PRIOR_SOURCE_PACKETS, S198_PACKET)
SEED = "s199-restored-margin-fresh-v1"
TABLE_ITEMS = 7
PROSE_ITEMS = 7
MIN_UNIQUE_MANUFACTURERS = 13


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def _content_sha(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def read_chunks_v2_stable(
    env_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Require two identical complete GET-only scans before population selection."""
    first_rows, first = _read_chunks_v2(env_file, experiment="S199_SCAN_1")
    second_rows, second = _read_chunks_v2(env_file, experiment="S199_SCAN_2")
    first_sha = stable_sha(first_rows)
    second_sha = stable_sha(second_rows)
    if (
        first_sha != second_sha
        or first.get("rows") != second.get("rows")
        or first.get("database_writes") != 0
        or second.get("database_writes") != 0
    ):
        raise RuntimeError("S199 chunks_v2 double-scan fingerprint drift")

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
    values: set[str] = set()
    for path in TARGET_FILES:
        values.update(
            value.lower()
            for value in collect_uuid_strings(
                json.loads(path.read_text(encoding="utf-8"))
            )
        )
    return values


def collect_candidates(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply every historical document/source-file/product-pair exclusion, including S198."""
    prior_documents, prior_pairs, prior_source_files, dependencies = _prior_contract(
        PRIOR_SOURCE_PACKETS
    )
    prior_documents = {str(value) for value in prior_documents}
    prior_pairs = {
        (_normalized(manufacturer), _normalized(product))
        for manufacturer, product in prior_pairs
    }
    prior_source_files = {_normalized(value) for value in prior_source_files}
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
        "prior_or_target_document_or_source_file": 0,
        "historical_manufacturer_product_pair": 0,
        "generic_eligibility": 0,
    }
    for row in rows:
        if row.get("document_id") in excluded_documents:
            exclusion_counts["prior_or_target_document_or_source_file"] += 1
            continue
        pair = (
            _normalized(row.get("manufacturer")),
            _normalized(row.get("product_model")),
        )
        if pair in prior_pairs:
            exclusion_counts["historical_manufacturer_product_pair"] += 1
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
                "manufacturer_key": _normalized(row["manufacturer"]),
                "pair_key": pair,
                "source_file_key": _normalized(row.get("source_file")),
                "stratum": (
                    "table"
                    if any(
                        unit.unit_kind == "table_row_with_header" for unit in units
                    )
                    else "prose"
                ),
                "quality": _quality(row),
                "tie": stable_sha({"seed": SEED, "chunk_id": row["id"]}),
            }
        )
    return candidates, {
        "prior_documents": prior_documents,
        "prior_pairs": prior_pairs,
        "prior_source_files": prior_source_files,
        "target_ids": target_ids,
        "target_documents": target_documents,
        "dependencies": dependencies,
        "exclusion_counts": exclusion_counts,
    }


def inventory_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "chunk_rows": len(candidates),
        "documents": len({item["row"]["document_id"] for item in candidates}),
        "source_files": len(
            {
                item["source_file_key"]
                for item in candidates
                if item["source_file_key"]
            }
        ),
        "manufacturer_product_pairs": len({item["pair_key"] for item in candidates}),
        "manufacturers": len({item["manufacturer_key"] for item in candidates}),
        "table_documents": len(
            {
                item["row"]["document_id"]
                for item in candidates
                if item["stratum"] == "table"
            }
        ),
        "prose_documents": len(
            {
                item["row"]["document_id"]
                for item in candidates
                if item["stratum"] == "prose"
            }
        ),
        "table_manufacturers": len(
            {
                item["manufacturer_key"]
                for item in candidates
                if item["stratum"] == "table"
            }
        ),
        "prose_manufacturers": len(
            {
                item["manufacturer_key"]
                for item in candidates
                if item["stratum"] == "prose"
            }
        ),
    }


def _candidate_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (-candidate["quality"], candidate["tie"])


def _assign_distinct_sources(
    groups: list[tuple[str, str]],
    grouped: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]] | None:
    """Pick one row per manufacturer/stratum without document, source or pair reuse."""
    ordered = sorted(groups, key=lambda group: (len(grouped[group]), group))
    selected: list[dict[str, Any]] = []
    used_documents: set[str] = set()
    used_sources: set[str] = set()
    used_pairs: set[tuple[str, str]] = set()

    def visit(index: int) -> bool:
        if index == len(ordered):
            return True
        for candidate in grouped[ordered[index]]:
            document = str(candidate["row"]["document_id"])
            source = candidate["source_file_key"]
            pair = candidate["pair_key"]
            if (
                document in used_documents
                or (source and source in used_sources)
                or pair in used_pairs
            ):
                continue
            selected.append(candidate)
            used_documents.add(document)
            if source:
                used_sources.add(source)
            used_pairs.add(pair)
            if visit(index + 1):
                return True
            selected.pop()
            used_documents.remove(document)
            if source:
                used_sources.remove(source)
            used_pairs.remove(pair)
        return False

    return list(selected) if visit(0) else None


def select_balanced(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Prefer 14 unique manufacturers; allow one cross-stratum repeat if necessary."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = (candidate["stratum"], candidate["manufacturer_key"])
        grouped.setdefault(key, []).append(candidate)
    for values in grouped.values():
        values.sort(key=_candidate_key)
    table = sorted(
        manufacturer for stratum, manufacturer in grouped if stratum == "table"
    )
    prose = sorted(
        manufacturer for stratum, manufacturer in grouped if stratum == "prose"
    )
    if len(table) < TABLE_ITEMS or len(prose) < PROSE_ITEMS:
        raise RuntimeError(
            f"S199 insufficient strata manufacturers: table={len(table)}, prose={len(prose)}"
        )

    plans: list[tuple[int, float, str, tuple[str, ...], tuple[str, ...]]] = []
    for table_set in itertools.combinations(table, TABLE_ITEMS):
        for prose_set in itertools.combinations(prose, PROSE_ITEMS):
            distinct = len(set(table_set) | set(prose_set))
            if distinct < MIN_UNIQUE_MANUFACTURERS:
                continue
            groups = [("table", value) for value in table_set] + [
                ("prose", value) for value in prose_set
            ]
            upper_quality = sum(grouped[group][0]["quality"] for group in groups)
            signature = stable_sha({"seed": SEED, "groups": groups})
            plans.append((distinct, upper_quality, signature, table_set, prose_set))
    plans.sort(key=lambda item: (-item[0], -item[1], item[2]))
    for distinct, _, signature, table_set, prose_set in plans:
        groups = [("table", value) for value in table_set] + [
            ("prose", value) for value in prose_set
        ]
        selected = _assign_distinct_sources(groups, grouped)
        if selected is None:
            continue
        selected.sort(
            key=lambda item: (
                0 if item["stratum"] == "table" else 1,
                item["tie"],
            )
        )
        return selected, {
            "unique_manufacturers": distinct,
            "historical_manufacturer_novelty_required": False,
            "within_cohort_manufacturer_repeat_count": (
                TABLE_ITEMS + PROSE_ITEMS - distinct
            ),
            "fallback_used": distinct < TABLE_ITEMS + PROSE_ITEMS,
            "selection_signature": signature,
        }
    raise RuntimeError("S199 no feasible 14-item, >=13-manufacturer balanced selection")


def build_packet(
    rows: list[dict[str, Any]], read_receipt: dict[str, Any]
) -> dict[str, Any]:
    eligible_rows, target_equivalence = exclude_target_equivalents(rows)
    target_equivalence["target_uuid_resolution"] = target_uuid_resolution(rows)
    target_equivalence["unresolved_target_uuids"] = []
    target_equivalence["all_target_uuids_resolved"] = True
    target_equivalence["source_stable_full_scan_sha256"] = read_receipt[
        "stable_full_scan_sha256"
    ]
    candidates, contract = collect_candidates(eligible_rows)
    inventory = inventory_counts(candidates)
    selected, selection_mode = select_balanced(candidates)
    items: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected, 1):
        row = candidate["row"]
        content = row["content"]
        item = {
            "item_id": f"s199_src_{index:02d}",
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
        ROOT / "scripts/s199_build_restored_margin_packet.py",
        ROOT / "src/rag/evidence_units_v2.py",
    ):
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    prior_manufacturers = {
        _normalized(item.get("manufacturer"))
        for path in PRIOR_SOURCE_PACKETS
        for item in json.loads(path.read_text(encoding="utf-8"))["items"]
    }
    body = {
        "instrument": "s199_restored_margin_source_packet_v1",
        "status": "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY",
        "selection": {
            "seed": SEED,
            "population_contract": (
                "RESTORED_14_ITEM_BALANCED_MAXIMUM_MANUFACTURER_DIVERSITY"
            ),
            "items": len(items),
            "table": sum(item["stratum"] == "table" for item in items),
            "prose": sum(item["stratum"] == "prose" for item in items),
            "unique_documents": len(selected_documents),
            "unique_source_files": len(
                {_normalized(item["source_file"]) for item in items}
            ),
            "unique_manufacturer_product_pairs": len(
                {
                    (
                        _normalized(item["manufacturer"]),
                        _normalized(item["product_model"]),
                    )
                    for item in items
                }
            ),
            **selection_mode,
            "historically_seen_manufacturers": sum(
                _normalized(item["manufacturer"]) in prior_manufacturers
                for item in items
            ),
            "question_gold_claim_facet_or_model_outcome_used_for_selection": False,
            "prior_document_overlap": sum(
                str(item["document_id"]) in contract["prior_documents"]
                for item in items
            ),
            "prior_source_file_overlap": sum(
                _normalized(item["source_file"]) in contract["prior_source_files"]
                for item in items
            ),
            "prior_manufacturer_product_pair_overlap": sum(
                (
                    _normalized(item["manufacturer"]),
                    _normalized(item["product_model"]),
                )
                in contract["prior_pairs"]
                for item in items
            ),
            "target_document_overlap": sum(
                str(item["document_id"]) in contract["target_documents"]
                for item in items
            ),
            "target_chunk_overlap": sum(
                str(item["chunk_id"]).lower() in contract["target_ids"]
                for item in items
            ),
            "target_exact_content_overlap": len(
                selected_content.intersection(target_equivalence["content_sha256"])
            ),
            "target_extraction_overlap": len(
                selected_extraction.intersection(
                    target_equivalence["extraction_sha256"]
                )
            ),
            "semantic_near_duplicate_overlap_status": "NOT_MEASURED",
            "oem_relabel_overlap_status": "NOT_MEASURED",
            "exclusion_counts": contract["exclusion_counts"],
        },
        "items": items,
        "eligible_inventory": {
            "definition": (
                "post_target_equivalence_post_all_prior_document_source_file_pair_"
                "and_generic_eligibility"
            ),
            "counts": inventory,
            "selected_identities": [
                {
                    key: item[key]
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
                for item in items
            ],
            "post_selection_reserve_definition": (
                "eligible candidate rows excluding selected documents; no claim of "
                "another balanced cohort"
            ),
            "post_selection_reserve": inventory_counts(reserve),
        },
        "read_receipt": read_receipt,
        "target_equivalence_exclusion": target_equivalence,
        "dependencies": dependencies,
        "chunks_v3_lane": {
            "status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "changed_by_s199": False,
        },
        "railway_deploy_gate": False,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows, read_receipt = read_chunks_v2_stable(args.env_file)
    packet = build_packet(rows, read_receipt)
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": packet["status"],
                "selection": packet["selection"],
                "eligible_inventory": packet["eligible_inventory"]["counts"],
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
