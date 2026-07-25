#!/usr/bin/env python3
"""Seal the conservative S128 source-first census adjudication."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "evals" / "s128_explicit_relation_census_candidates_v1.json"
ADJUDICATION = ROOT / "evals" / "s128_explicit_relation_census_adjudication_v1.yaml"
PREREG = ROOT / "evals" / "s128_explicit_relation_census_prereg_v1.yaml"
OUTPUT = ROOT / "evals" / "s128_explicit_relation_census_gate_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def build_payload() -> dict[str, Any]:
    source = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    adjudication = yaml.safe_load(ADJUDICATION.read_text(encoding="utf-8"))
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if _sha(PREREG) != source["prereg_sha256"]:
        raise RuntimeError("S128 candidate/prereg receipt mismatch")
    snapshot = ROOT / prereg["inputs"]["snapshot"]["path"]
    if _sha(snapshot) != prereg["inputs"]["snapshot"]["sha256"]:
        raise RuntimeError("S128 adjudication snapshot drift")
    candidates = source["candidates"]
    by_id = {row["candidate_id"]: row for row in candidates}
    needed_chunk_ids = {str(row["chunk_id"]) for row in candidates}
    source_chunks: dict[str, dict[str, Any]] = {}
    with gzip.open(snapshot, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            row_id = str(row.get("id") or "")
            if row.get("kind") == "chunk" and row_id in needed_chunk_ids:
                source_chunks[row_id] = row
    if set(source_chunks) != needed_chunk_ids:
        raise RuntimeError("S128 adjudication source chunk missing")
    accepted = adjudication["eligible_candidates"]
    unknown = sorted(set(accepted) - set(by_id))
    if unknown:
        raise RuntimeError(f"unknown accepted candidate receipts: {unknown}")
    hard_negatives = set(adjudication["hard_negative_candidates"])
    if not hard_negatives <= set(by_id):
        raise RuntimeError("unknown S128 hard-negative receipt")

    dispositions = []
    relations = []
    exact_receipts = 0
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        quote = str(candidate["quote"])
        source_chunk = source_chunks[str(candidate["chunk_id"])]
        content = str(source_chunk.get("content") or "")
        start, end = candidate["start"], candidate["end"]
        exact = (
            hashlib.sha256(quote.encode("utf-8")).hexdigest()
            == candidate["quote_sha256"]
            and isinstance(start, int)
            and not isinstance(start, bool)
            and isinstance(end, int)
            and not isinstance(end, bool)
            and 0 <= start < end <= len(content)
            and content[start:end] == quote
            and source_chunk.get("document_id") == candidate["document_id"]
            and source_chunk.get("source_file") == candidate["source_file"]
            and source_chunk.get("extraction_sha256") == candidate["extraction_sha256"]
            and source_chunk.get("chunk_index") == candidate["chunk_index"]
        )
        exact_receipts += int(exact)
        mapped = accepted.get(candidate_id) or []
        status = "eligible" if mapped else "rejected"
        disposition = {
            "candidate_id": candidate_id,
            "class_id": candidate["class_id"],
            "status": status,
            "exact_receipt_valid": exact,
            "reason": (
                "normalized_explicit_directional_relation"
                if mapped
                else adjudication["default_rejection_reason"]
            ),
            "hard_negative": candidate_id in hard_negatives,
            "relation_ids": [row["relation_id"] for row in mapped],
        }
        dispositions.append(disposition)
        for relation in mapped:
            relations.append(
                {
                    **relation,
                    "class_id": candidate["class_id"],
                    "candidate_id": candidate_id,
                    "document_id": candidate["document_id"],
                    "source_file": candidate["source_file"],
                    "extraction_sha256": candidate["extraction_sha256"],
                    "chunk_id": candidate["chunk_id"],
                    "chunk_index": candidate["chunk_index"],
                    "start": candidate["start"],
                    "end": candidate["end"],
                    "quote_sha256": candidate["quote_sha256"],
                    "quote": quote,
                }
            )

    relation_ids = [row["relation_id"] for row in relations]
    if len(relation_ids) != len(set(relation_ids)):
        raise RuntimeError("duplicate S128 relation ID")
    class_counts = Counter(row["class_id"] for row in relations)
    predicate_counts = Counter(row["predicate"] for row in relations)
    hard_negative_acceptances = sum(
        row["hard_negative"] and row["status"] == "eligible" for row in dispositions
    )
    provenance_rate = exact_receipts / len(candidates) if candidates else 0.0
    criteria = {
        "minimum_eligible_relations": len(relations) >= adjudication["gate"][
            "minimum_eligible_relations"
        ],
        "minimum_relation_closed_classes": len(class_counts) >= adjudication["gate"][
            "minimum_relation_closed_classes"
        ],
        "exact_provenance_rate": provenance_rate
        == adjudication["gate"]["exact_provenance_rate"],
        "hard_negative_acceptances": hard_negative_acceptances
        == adjudication["gate"]["hard_negative_acceptances"],
    }
    status = "GO_TO_OFFLINE_EXTRACTOR_DESIGN" if all(criteria.values()) else "NO_GO"
    return {
        "instrument": "s128_explicit_relation_census_gate_v1",
        "status": status,
        "checks": criteria,
        "candidate_count": len(candidates),
        "eligible_candidate_count": sum(row["status"] == "eligible" for row in dispositions),
        "rejected_candidate_count": sum(row["status"] == "rejected" for row in dispositions),
        "eligible_relation_count": len(relations),
        "relation_closed_class_count": len(class_counts),
        "relations_by_class": dict(sorted(class_counts.items())),
        "relations_by_predicate": dict(sorted(predicate_counts.items())),
        "exact_provenance_rate": provenance_rate,
        "hard_negative_acceptances": hard_negative_acceptances,
        "relations": relations,
        "candidate_dispositions_sha256": _canonical(dispositions),
        "candidate_dispositions": dispositions,
        "receipts": {
            "candidate_artifact_sha256": _sha(CANDIDATES),
            "adjudication_sha256": _sha(ADJUDICATION),
            "candidates_sha256": source["candidates_sha256"],
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "credit": {"facts_moved_to_ok": 0, "official_funnel_change": False},
        "authorization": (
            "deterministic_offline_extractor_design_only" if status.startswith("GO") else None
        ),
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "eligible_relations": payload["eligible_relation_count"],
                "classes": payload["relation_closed_class_count"],
                "hard_negative_acceptances": payload["hard_negative_acceptances"],
                "cost": payload["cost"],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"].startswith("GO") else 1


if __name__ == "__main__":
    sys.exit(main())
