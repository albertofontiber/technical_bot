#!/usr/bin/env python3
"""Archived zero-network S127 replay; requires the revoked candidate-v2 code."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.compatibility_bundle_coverage import (
    EVIDENCE_CONFIG,
    QUERY_CONFIG,
    _validate_topology_cards,
    build_compatibility_bundle,
    select_compatibility_bundle_from_pool,
    validate_compatibility_bundle,
)
from src.rag.catalog_resolver import resolve_query
from src.rag.doc_scoped_hyq_coverage import (
    collect_document_scoped_hyq,
    select_document_diverse_parents,
)
from src.rag.evidence_coverage import select_evidence_coverage_cards
from src.rag.query_facets import expand_query_facets

COHORT_V2 = ROOT / "evals" / "s127_compatibility_development_cohort_v2.yaml"
COHORT_V3 = ROOT / "evals" / "s127_compatibility_development_cohort_v3.yaml"
OUTPUT = ROOT / "evals" / "s127_compatibility_generalization_replay_v1.json"
SNAPSHOT = ROOT / "tmp" / "s117_m25" / "derived_snapshot_v2.jsonl.gz"
SNAPSHOT_SHA256 = "a825e4dd02b918ddafebab4419cb416b6edc5f1b823a7a9d423f96718d7b6217"
S126_QUERY_QID = "cat013"
S126_FACET_ROWS = {
    "protocol_scope": "cfcdc8f7-bdaf-412f-a85e-0ffb76878d99",
    "supported_device_roster": "11d96526-d627-4305-8cae-e6852af1b20b",
    "loop_topology": "b6602d5a-dbb5-4e2e-8814-1ac3ce066896",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@lru_cache(maxsize=1)
def _chunks() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if _sha(SNAPSHOT) != SNAPSHOT_SHA256:
        raise ValueError("S127 frozen snapshot drift")
    rows = []
    by_id = {}
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") != "chunk":
                continue
            rows.append(row)
            by_id[str(row.get("id") or "")] = row
    return rows, by_id


def _local_candidate_pool(query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    chunks, _ = _chunks()
    resolution = resolve_query(query)
    groups = resolution.get("source_groups") or []
    plan = expand_query_facets(query, QUERY_CONFIG)
    allowed = set(resolution.get("allowed_sources") or [])
    navigation_rows = [
        {
            "chunk_id": str(row.get("id") or ""),
            "source_file": str(row.get("source_file") or ""),
            "page_number": row.get("page_number"),
            "question": " ".join(
                part for part in (
                    str(row.get("section_title") or ""),
                    str(row.get("content") or ""),
                ) if part
            ),
        }
        for row in chunks
        if str(row.get("source_file") or "") in allowed
    ]
    by_id = {str(row.get("id") or ""): row for row in chunks}
    raw_parent_manifest: list[dict[str, Any]] = []

    def fetcher(scope, needs):
        assert set(scope) == allowed
        parent_ids = select_document_diverse_parents(
            needs,
            navigation_rows,
            source_groups=groups,
            focus_query=query,
        )
        parents = [by_id[parent_id] for parent_id in parent_ids]
        raw_parent_manifest.extend(
            {
                "id": parent_id,
                "source_file": str(by_id[parent_id].get("source_file") or ""),
                "document_id": str(by_id[parent_id].get("document_id") or ""),
                "extraction_sha256": str(by_id[parent_id].get("extraction_sha256") or ""),
                "chunk_index": by_id[parent_id].get("chunk_index"),
                "section_title": str(by_id[parent_id].get("section_title") or ""),
                "facets": [
                    card["facet"]
                    for card in select_evidence_coverage_cards(
                        [by_id[parent_id]],
                        archetype="compatibility",
                        config_path=EVIDENCE_CONFIG,
                        query=query,
                    )
                ],
            }
            for parent_id in parent_ids
        )
        parent_manifest = [
            {
                "id": parent_id,
                "content_sha256": hashlib.sha256(
                    str(by_id[parent_id].get("content") or "").encode("utf-8")
                ).hexdigest(),
            }
            for parent_id in parent_ids
        ]
        return (
            parents,
            len(navigation_rows),
            0,
            {
                "hyq_rows_sha256": _canonical(navigation_rows),
                "selected_parent_ids_sha256": _canonical(parent_ids),
                "hydrated_parents_sha256": _canonical(parent_manifest),
            },
        )

    selected, trace = collect_document_scoped_hyq(
        query,
        fetcher=fetcher,
        query_facets_path=QUERY_CONFIG,
        evidence_config_path=EVIDENCE_CONFIG,
        append_limit=3,
        entity_stratified=True,
        include_fetch_receipts=True,
        return_candidate_pool=True,
    )
    trace["raw_navigation_parent_manifest"] = raw_parent_manifest
    trace["raw_navigation_parent_manifest_sha256"] = _canonical(raw_parent_manifest)
    return selected, trace


@lru_cache(maxsize=16)
def _source_scope_facet_audit(query: str) -> dict[str, Any]:
    chunks, _ = _chunks()
    resolution = resolve_query(query)
    allowed = set(resolution.get("allowed_sources") or [])
    counts: Counter[str] = Counter()
    parent_ids: dict[str, list[str]] = {}
    for row in chunks:
        if str(row.get("source_file") or "") not in allowed:
            continue
        cards = select_evidence_coverage_cards(
            [row], archetype="compatibility", config_path=EVIDENCE_CONFIG, query=query
        )
        for card in cards:
            facet = str(card.get("facet") or "")
            counts[facet] += 1
            parent_ids.setdefault(facet, []).append(str(row.get("id") or ""))
    return {
        "allowed_source_count": len(allowed),
        "facet_counts": dict(sorted(counts.items())),
        "facet_parent_ids_sha256": {
            facet: _canonical(sorted(ids)) for facet, ids in sorted(parent_ids.items())
        },
    }


@lru_cache(maxsize=16)
def _source_scope_relational_audit(query: str) -> dict[str, Any]:
    """Test the frozen relation against every eligible parent in resolved scope.

    This is diagnostic only: it does not alter navigation order or create a
    serving candidate.  It distinguishes a bounded-navigation miss from a
    relation that cannot be established anywhere in the governed source set.
    """
    chunks, _ = _chunks()
    resolution = resolve_query(query)
    allowed = set(resolution.get("allowed_sources") or [])
    groups = resolution.get("source_groups") or []
    by_facet: dict[str, list[dict[str, Any]]] = {
        "protocol_scope": [],
        "supported_device_roster": [],
        "loop_topology": [],
    }
    for original in chunks:
        if str(original.get("source_file") or "") not in allowed:
            continue
        cards = select_evidence_coverage_cards(
            [original],
            archetype="compatibility",
            config_path=EVIDENCE_CONFIG,
            query=query,
        )
        for facet in sorted(by_facet):
            facet_cards = [card for card in cards if card.get("facet") == facet]
            if not facet_cards:
                continue
            projected = dict(original)
            projected["coverage_cards"] = facet_cards
            projected["coverage_card_facets"] = [facet]
            by_facet[facet].append(projected)

    attempted = 0
    rejected: Counter[str] = Counter()
    valid_receipts: list[dict[str, Any]] = []
    ambiguity_keys: set[str] = set()
    for protocol in by_facet["protocol_scope"]:
        for roster in by_facet["supported_device_roster"]:
            for topology in by_facet["loop_topology"]:
                parent_ids = [
                    str(protocol.get("id") or ""),
                    str(roster.get("id") or ""),
                    str(topology.get("id") or ""),
                ]
                attempted += 1
                if len(set(parent_ids)) != 3:
                    rejected["duplicate_parent"] += 1
                    continue
                try:
                    bundle = build_compatibility_bundle(
                        query, [protocol, roster, topology], groups
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    rejected[str(exc)] += 1
                    continue
                ambiguity_hash = _canonical(bundle[0]["compatibility_ambiguity_key"])
                ambiguity_keys.add(ambiguity_hash)
                valid_receipts.append(
                    {
                        "parent_ids": parent_ids,
                        "ambiguity_key_sha256": ambiguity_hash,
                        "bundle_receipt_sha256": bundle[0][
                            "compatibility_bundle_receipt_sha256"
                        ],
                    }
                )

    status = "no_complete_relational_bundle"
    if len(ambiguity_keys) == 1:
        status = "unique_relational_evidence"
    elif len(ambiguity_keys) > 1:
        status = "ambiguous_relational_evidence"
    return {
        "facet_candidate_counts": {
            facet: len(rows) for facet, rows in sorted(by_facet.items())
        },
        "attempted_assignment_count": attempted,
        "valid_assignment_count": len(valid_receipts),
        "ambiguity_key_count": len(ambiguity_keys),
        "status": status,
        "valid_assignment_manifest_sha256": _canonical(valid_receipts),
        "first_valid_assignment": valid_receipts[0] if valid_receipts else None,
        "rejection_reason_counts": dict(sorted(rejected.items())),
    }


def _run_development_once(queries: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in queries:
        query = str(case["question"])
        groups = resolve_query(query).get("source_groups") or []
        pool, navigation_trace = _local_candidate_pool(query)
        curve = {}
        for candidate_limit in (3, 4, 5, 6):
            selected, selection_trace = select_compatibility_bundle_from_pool(
                query, pool, groups, candidate_limit=candidate_limit
            )
            rejection_reasons = Counter(
                str(attempt.get("reason") or "")
                for attempt in selection_trace["attempt_manifest"]
                if attempt.get("status") == "rejected"
            )
            curve[str(candidate_limit)] = {
                "status": selection_trace["status"],
                "selected_parent_ids": [str(row.get("id") or "") for row in selected],
                "bundle_valid": validate_compatibility_bundle(selected),
                "ambiguity_key_sha256s": selection_trace["ambiguity_key_sha256s"],
                "projection_manifest_sha256": selection_trace["projection_manifest_sha256"],
                "attempt_manifest_sha256": selection_trace["attempt_manifest_sha256"],
                "valid_assignment_count": selection_trace["valid_assignment_count"],
                "rejection_reason_counts": dict(sorted(rejection_reasons.items())),
            }
        rows.append(
            {
                "id": case["id"],
                "question_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "resolved_group_count": len(groups),
                "candidate_pool_parent_ids": [str(row.get("id") or "") for row in pool],
                "candidate_pool_sha256": navigation_trace.get("candidate_pool_sha256"),
                "navigation_fetch_receipts": navigation_trace.get("fetch_receipts"),
                "raw_navigation_parent_manifest": navigation_trace.get(
                    "raw_navigation_parent_manifest"
                ),
                "raw_navigation_parent_manifest_sha256": navigation_trace.get(
                    "raw_navigation_parent_manifest_sha256"
                ),
                "source_scope_facet_audit": _source_scope_facet_audit(query),
                "source_scope_relational_audit": _source_scope_relational_audit(query),
                "curve": curve,
            }
        )
    recovery_by_k = {
        str(k): sum(row["curve"][str(k)]["bundle_valid"] for row in rows)
        for k in (3, 4, 5, 6)
    }
    maximum = max(recovery_by_k.values(), default=0)
    chosen_k = (
        min(int(k) for k, value in recovery_by_k.items() if value == maximum)
        if maximum > 0
        else None
    )
    return {
        "rows": rows,
        "recovery_by_k": recovery_by_k,
        "chosen_k": chosen_k,
        "maximum_development_recovery": maximum,
    }


def _exact_control_receipt(
    control: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    row = by_id[str(control["chunk_id"])]
    content = str(row.get("content") or "")
    expected = control.get("exact_card") or {}
    cards = select_evidence_coverage_cards(
        [row], archetype="compatibility", config_path=EVIDENCE_CONFIG, query=""
    )
    topology = [card for card in cards if card.get("facet") == "loop_topology"]
    exact = next(
        (
            card for card in topology
            if card.get("start") == expected.get("start")
            and card.get("end") == expected.get("end")
            and hashlib.sha256(str(card.get("quote") or "").encode("utf-8")).hexdigest()
            == expected.get("quote_sha256")
        ),
        None,
    )
    content_exact = (
        hashlib.sha256(content.encode("utf-8")).hexdigest()
        == control.get("content_sha256")
    )
    guard_accepts = False
    rejection = None
    if exact is not None:
        try:
            _validate_topology_cards([exact])
            guard_accepts = True
        except ValueError as exc:
            rejection = str(exc)
    return {
        "id": control["id"],
        "content_receipt_exact": content_exact,
        "exact_card_found": exact is not None,
        "guard_accepts": guard_accepts,
        "rejection": rejection,
    }


def _control_gate(cohort_v3: dict[str, Any]) -> dict[str, Any]:
    _, by_id = _chunks()
    controls = cohort_v3["exact_topology_controls"]
    positives = [
        _exact_control_receipt(row, by_id) for row in controls["positives"]
    ]
    negatives = [
        _exact_control_receipt(row, by_id)
        for row in controls["exact_card_hard_negatives"]["cases"]
    ]
    pipeline = []
    for control in controls["pipeline_hard_negatives"]["cases"]:
        row = by_id[str(control["chunk_id"])]
        cards = select_evidence_coverage_cards(
            [row], archetype="compatibility", config_path=EVIDENCE_CONFIG, query=""
        )
        pipeline.append(
            {
                "id": control["id"],
                "content_receipt_exact": hashlib.sha256(
                    str(row.get("content") or "").encode("utf-8")
                ).hexdigest() == control["content_sha256"],
                "loop_topology_card_count": sum(
                    card.get("facet") == "loop_topology" for card in cards
                ),
            }
        )
    return {
        "positives": positives,
        "exact_card_hard_negatives": negatives,
        "pipeline_hard_negatives": pipeline,
        "passed": (
            all(
                row["content_receipt_exact"]
                and row["exact_card_found"]
                and row["guard_accepts"]
                for row in positives
            )
            and all(
                row["content_receipt_exact"]
                and row["exact_card_found"]
                and not row["guard_accepts"]
                for row in negatives
            )
            and all(
                row["content_receipt_exact"]
                and row["loop_topology_card_count"] == 0
                for row in pipeline
            )
        ),
    }


def _s126_protected_gate() -> dict[str, Any]:
    benchmark = yaml.safe_load(
        (ROOT / "evals" / "s100_factlevel_full.yaml").read_text(encoding="utf-8")
    )
    query = next(
        row["question"] for row in benchmark["per_gold"] if row["qid"] == S126_QUERY_QID
    )
    groups = resolve_query(query).get("source_groups") or []
    _, by_id = _chunks()
    rows = []
    for facet in ("protocol_scope", "supported_device_roster", "loop_topology"):
        row = dict(by_id[S126_FACET_ROWS[facet]])
        cards = select_evidence_coverage_cards(
            [row], archetype="compatibility", config_path=EVIDENCE_CONFIG, query=query
        )
        row["coverage_cards"] = [card for card in cards if card.get("facet") == facet]
        row["coverage_card_facets"] = [facet]
        rows.append(row)
    bundle = build_compatibility_bundle(query, rows, groups)
    return {
        "valid": validate_compatibility_bundle(bundle),
        "selected_parent_ids": [str(row["id"]) for row in bundle],
        "bundle_receipt_sha256": bundle[0]["compatibility_bundle_receipt_sha256"],
    }


@lru_cache(maxsize=1)
def build_payload() -> dict[str, Any]:
    cohort_v2 = yaml.safe_load(COHORT_V2.read_text(encoding="utf-8"))
    cohort_v3 = yaml.safe_load(COHORT_V3.read_text(encoding="utf-8"))
    first = _run_development_once(cohort_v2["queries"])
    second = _run_development_once(cohort_v2["queries"])
    controls = _control_gate(cohort_v3)
    s126 = _s126_protected_gate()
    deterministic = _canonical(first) == _canonical(second)
    dev004 = next(row for row in first["rows"] if row["id"] == "dev004")
    dev004_closed = all(
        not dev004["curve"][str(k)]["bundle_valid"] for k in (3, 4, 5, 6)
    )
    checks = {
        "two_runs_byte_deterministic": deterministic,
        "topology_controls_pass": controls["passed"],
        "s126_protected_bundle_valid": s126["valid"],
        "dev004_remains_fail_closed": dev004_closed,
        "candidate_limit_selected": first["chosen_k"] in {3, 4, 5, 6},
        "development_signal_present": first["maximum_development_recovery"] >= 1,
    }
    return {
        "instrument": "s127_compatibility_generalization_replay_v1",
        "status": "GO_LOCAL_BUILD" if all(checks.values()) else "NO_GO_LOCAL_BUILD",
        "checks": checks,
        "development": first,
        "second_run_sha256": _canonical(second),
        "first_run_sha256": _canonical(first),
        "topology_controls": controls,
        "s126_protected_gate": s126,
        "receipts": {
            "snapshot_sha256": _sha(SNAPSHOT),
            "query_config_sha256": _sha(QUERY_CONFIG),
            "evidence_config_sha256": _sha(EVIDENCE_CONFIG),
            "bundle_contract_config_sha256": _sha(
                ROOT / "config" / "compatibility_bundle_contract_candidate_v2.yaml"
            ),
            "implementation_sha256": _sha(
                ROOT / "src" / "rag" / "compatibility_bundle_coverage.py"
            ),
            "navigation_sha256": _sha(
                ROOT / "src" / "rag" / "doc_scoped_hyq_coverage.py"
            ),
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "credit": {"facts_moved_to_ok": 0, "official_funnel_change": False},
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
                "checks": payload["checks"],
                "recovery_by_k": payload["development"]["recovery_by_k"],
                "chosen_k": payload["development"]["chosen_k"],
                "cost": payload["cost"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if payload["status"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
