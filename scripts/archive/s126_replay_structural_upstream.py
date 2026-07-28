#!/usr/bin/env python3
"""Cheap local replay for the exact S126 upstream candidate contracts."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.evidence_coverage import select_evidence_coverage_cards
from src.rag.procedure_bundle_coverage import (
    select_procedure_bundle_coverage,
    verify_source_span_receipt,
)
from src.rag.query_facets import expand_query_facets

PREREG = ROOT / "evals" / "s126_structural_upstream_prereg_v1.yaml"
OUTPUT = ROOT / "evals" / "s126_structural_upstream_local_replay_v1.json"

COMPATIBILITY_EVIDENCE = {
    "cat013#0:bucle cerrado": (
        "b6602d5a-dbb5-4e2e-8814-1ac3ce066896",
        "loop_topology",
    ),
    "cat013#1:CLIP": (
        "cfcdc8f7-bdaf-412f-a85e-0ffb76878d99",
        "protocol_scope",
    ),
    "cat013#1:SDX-751 roster": (
        "11d96526-d627-4305-8cae-e6852af1b20b",
        "supported_device_roster",
    ),
}
PROCEDURE_EVIDENCE = {
    "cat017#2:licencia CLIP por lazo": (
        "cat017",
        "5bb83899-9d94-4fdd-8d42-24a670a036c5",
        "quantified_licensed_loop_prerequisite",
    ),
    "hp010#1:Nivel 3": (
        "hp010",
        "155a90fe-8c3f-484e-a617-7637fe29b547",
        "procedural_access_prerequisite",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_inputs(prereg: dict[str, Any]) -> dict[str, Path]:
    paths = {}
    for label, receipt in prereg["frozen_inputs"].items():
        path = ROOT / receipt["path"]
        if not path.is_file() or sha256(path) != receipt["sha256"]:
            raise ValueError(f"frozen input drift: {label}")
        paths[label] = path
    return paths


def load_chunks(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = []
    by_id = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") != "chunk":
                continue
            rows.append(row)
            by_id[str(row.get("id") or "")] = row
    return rows, by_id


def accepted_mapping(prereg: dict[str, Any]) -> dict[str, Any]:
    expected = prereg["accepted_data_reconciliation"]
    matches = []
    for line in (ROOT / "data" / "catalog" / "doc_map.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        row = json.loads(line)
        if row.get("document_id") != expected["document_id"]:
            continue
        matches = [
            entry for entry in row.get("entries") or []
            if entry.get("id") == expected["product_id"]
        ]
    valid = matches == [{
        "id": expected["product_id"],
        "provenance": expected["provenance"],
        "role": expected["role"],
        "scope": expected["scope"],
    }]
    return {
        "valid": valid,
        "document_id": expected["document_id"],
        "source_file": expected["source_file"],
        "product_id": expected["product_id"],
        "match_count": len(matches),
    }


@lru_cache(maxsize=1)
def build_payload() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    frozen = verified_inputs(prereg)
    benchmark = yaml.safe_load(frozen["benchmark"].read_text(encoding="utf-8"))
    questions = {row["qid"]: row["question"] for row in benchmark["per_gold"]}
    contexts_payload = json.loads(frozen["frozen_contexts"].read_text(encoding="utf-8"))
    contexts = {row["qid"]: row["context"] for row in contexts_payload["rows"]}
    chunks, by_id = load_chunks(frozen["corpus_snapshot"])

    procedure_rows = []
    for fact_key, (qid, expected_id, expected_facet) in PROCEDURE_EVIDENCE.items():
        selected, trace = select_procedure_bundle_coverage(
            questions[qid], contexts[qid], chunks
        )
        selected_ids = [str(row.get("id") or "") for row in selected]
        receipts_valid = all(
            verify_source_span_receipt(row, card)
            for row in selected
            for card in row.get("coverage_cards") or []
        )
        procedure_rows.append({
            "fact_key": fact_key,
            "selected_ids": selected_ids,
            "selected_facets": trace["selected_facets"],
            "expected_recovered": (
                selected_ids == [expected_id]
                and trace["selected_facets"] == [expected_facet]
                and receipts_valid
            ),
            "receipts_valid": receipts_valid,
            "product_scoped_candidates": trace["product_scoped_candidates"],
        })

    query = questions["cat013"]
    prior_plan = expand_query_facets(query, frozen["prior_query_contract"])
    candidate_plan = expand_query_facets(
        query, frozen["compatibility_query_candidate"]
    )
    compatibility_rows = []
    for fact_key, (chunk_id, expected_facet) in COMPATIBILITY_EVIDENCE.items():
        row = by_id[chunk_id]
        prior_cards = select_evidence_coverage_cards(
            [row],
            archetype="compatibility",
            config_path=frozen["prior_evidence_contract"],
            query=query,
        )
        candidate_cards = select_evidence_coverage_cards(
            [row],
            archetype="compatibility",
            config_path=frozen["compatibility_evidence_candidate"],
            query=query,
        )
        compatibility_rows.append({
            "fact_key": fact_key,
            "chunk_id": chunk_id,
            "source_file": row.get("source_file"),
            "prior_facets": [card["facet"] for card in prior_cards],
            "candidate_facets": [card["facet"] for card in candidate_cards],
            "expected_facet_recovered": expected_facet in {
                card["facet"] for card in candidate_cards
            },
            "candidate_receipts_exact": all(
                card["quote"] == str(row.get("content") or "")[card["start"]:card["end"]]
                and card["exact_source_span_validated"] is True
                for card in candidate_cards
            ),
        })

    mapping = accepted_mapping(prereg)
    checks = {
        "accepted_mapping_exact": mapping["valid"],
        "procedure_claims_recovered": all(
            row["expected_recovered"] for row in procedure_rows
        ),
        "compatibility_plan_has_three_needs": (
            candidate_plan["archetype"] == "compatibility"
            and len(candidate_plan["needs"]) == 3
        ),
        "compatibility_receipts_recovered": all(
            row["expected_facet_recovered"] and row["candidate_receipts_exact"]
            for row in compatibility_rows
        ),
        "baseline_missing_new_compatibility_relations": (
            not compatibility_rows[0]["prior_facets"]
            and not compatibility_rows[2]["prior_facets"]
        ),
    }
    return {
        "instrument": "s126_replay_structural_upstream_v1",
        "status": "GO_LOCAL_CANDIDATE" if all(checks.values()) else "NO_GO_LOCAL_CANDIDATE",
        "checks": checks,
        "accepted_mapping": mapping,
        "procedure_prerequisite_coverage": procedure_rows,
        "compatibility_contract": {
            "prior_plan": prior_plan,
            "candidate_plan": candidate_plan,
            "rows": compatibility_rows,
        },
        "stage_credit": {
            "retrieval_preconditions_recovered": 2,
            "compatibility_validation_preconditions_recovered": 2,
            "facts_moved_to_ok": 0,
            "reason": "local development replay; live navigation and downstream gates remain",
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], **payload["checks"]}, sort_keys=True))
    return 0 if payload["status"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
