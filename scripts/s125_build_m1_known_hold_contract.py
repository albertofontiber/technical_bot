#!/usr/bin/env python3
"""Build and validate the S125 source-first contract for the 33 known M1 holds.

This script never scores answers.  It binds the migration spec to the exact
S118 parents and the exact source rows already served in the S113 freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREREG_PATH = ROOT / "evals" / "s125_m1_known_hold_migration_prereg_v1.yaml"
SPEC_PATH = ROOT / "evals" / "s125_m1_known_hold_migration_spec_v1.yaml"
SUPPORT_PATH = ROOT / "evals" / "s125_m1_source_support_v1.yaml"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(raw.encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _resolve_frozen_inputs(prereg: dict[str, Any]) -> dict[str, tuple[Path, str]]:
    resolved: dict[str, tuple[Path, str]] = {}
    for name, receipt in (prereg.get("frozen_inputs") or {}).items():
        logical_path = receipt.get("path")
        expected_sha = receipt.get("sha256")
        if not logical_path:
            # The upstream blocker is fully projected into the local S118 input.
            continue
        path = (ROOT / logical_path).resolve()
        if not path.is_file() or file_sha256(path) != expected_sha:
            raise ValueError(f"frozen input mismatch: {name}")
        resolved[name] = (path, expected_sha)
    return resolved


def _context_index(context_freeze: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    rows_by_qid: dict[str, dict[str, Any]] = {}
    contexts_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in context_freeze.get("rows") or []:
        qid = row.get("qid")
        if not qid or qid in rows_by_qid:
            raise ValueError("S113 context qids must be present and unique")
        rows_by_qid[qid] = row
        for source_row in row.get("context") or []:
            context_id = source_row.get("id")
            key = (qid, context_id)
            if not context_id or key in contexts_by_key:
                raise ValueError("S113 context ids must be present and unique within each qid")
            contexts_by_key[key] = {"qid": qid, **source_row}
    return rows_by_qid, contexts_by_key


def build_contract(
    prereg: dict[str, Any],
    spec: dict[str, Any],
    support: dict[str, Any],
    bridge: dict[str, Any],
    projection: dict[str, Any],
    contexts: dict[str, Any],
) -> dict[str, Any]:
    expected_parent_count = prereg["population_contract"]["expected_parent_count"]
    expected_qid_count = prereg["population_contract"]["expected_qid_count"]

    hold_claims = [
        row for row in bridge.get("claims") or []
        if row.get("stage_bucket") == "known-m1-contract-hold"
    ]
    if len(hold_claims) != expected_parent_count:
        raise ValueError("bridge hold count changed")
    bridge_by_key = {(row.get("qid"), row.get("parent_fact_sha256")): row for row in hold_claims}
    if any(None in key for key in bridge_by_key) or len(bridge_by_key) != len(hold_claims):
        raise ValueError("bridge hold qid+sha identities are not exact and unique")

    projected = projection.get("m1_known_holds") or []
    projection_by_key = {
        (
            (row.get("parent_identity") or {}).get("qid"),
            (row.get("parent_identity") or {}).get("parent_fact_sha256"),
        ): row
        for row in projected
    }
    if any(None in key for key in projection_by_key) or set(projection_by_key) != set(bridge_by_key):
        raise ValueError("projection and bridge hold populations differ")

    expected_hist = prereg["population_contract"]["expected_legacy_stage_histogram"]
    actual_hist = dict(sorted(Counter(row["legacy_stage_bucket"] for row in hold_claims).items()))
    if actual_hist != dict(sorted(expected_hist.items())):
        raise ValueError("legacy stage histogram changed")

    rows_by_qid, contexts_by_key = _context_index(contexts)
    spec_parents = spec.get("parents") or []
    spec_by_key = {(row.get("qid"), row.get("parent_fact_sha256")): row for row in spec_parents}
    if any(None in key for key in spec_by_key) or len(spec_by_key) != len(spec_parents):
        raise ValueError("migration spec parent keys must be present and unique")
    if set(spec_by_key) != set(bridge_by_key):
        missing = sorted(str(row) for row in set(bridge_by_key) - set(spec_by_key))
        unexpected = sorted(str(row) for row in set(spec_by_key) - set(bridge_by_key))
        raise ValueError(f"migration spec population mismatch: missing={missing}, unexpected={unexpected}")
    if len({row["qid"] for row in spec_parents}) != expected_qid_count:
        raise ValueError("migration spec qid count changed")

    allowed_dispositions = {"rewrite", "split", "merge_duplicate", "withdraw_unsupported", "unresolved"}
    support_claims = support.get("claims") or {}
    if not isinstance(support_claims, dict):
        raise ValueError("literal support claims must be a mapping")
    migration_ids: set[str] = set()
    claims: list[dict[str, Any]] = []
    parent_rows: list[dict[str, Any]] = []

    for parent in spec_parents:
        fact_key = parent["parent_fact_key"]
        qid = parent["qid"]
        parent_key = (qid, parent["parent_fact_sha256"])
        bridge_parent = bridge_by_key[parent_key]
        projected_parent = projection_by_key[parent_key]
        expected_sha = bridge_parent["parent_fact_sha256"]
        if parent.get("parent_fact_sha256") != expected_sha or bridge_parent.get("qid") != qid:
            raise ValueError(f"parent identity mismatch: {fact_key}")
        projection_identity = projected_parent.get("parent_identity") or {}
        if (projection_identity.get("qid") != qid
                or projection_identity.get("parent_fact_sha256") != expected_sha):
            raise ValueError(f"projection identity mismatch: {fact_key}")

        disposition = parent.get("disposition")
        if disposition not in allowed_dispositions:
            raise ValueError(f"invalid disposition: {fact_key}")
        if not str(parent.get("decision_reason") or "").strip():
            raise ValueError(f"missing decision reason: {fact_key}")
        withdrawn = parent.get("withdrawn_clauses")
        if not isinstance(withdrawn, list):
            raise ValueError(f"withdrawn clauses must be a list: {fact_key}")
        children = parent.get("children")
        if not isinstance(children, list):
            raise ValueError(f"children must be a list: {fact_key}")
        if disposition == "rewrite" and len(children) != 1:
            raise ValueError(f"rewrite must have exactly one child: {fact_key}")
        if disposition == "split" and len(children) < 2:
            raise ValueError(f"split must have at least two children: {fact_key}")
        if disposition in {"merge_duplicate", "withdraw_unsupported", "unresolved"} and children:
            raise ValueError(f"terminal disposition cannot have children: {fact_key}")
        if disposition in {"merge_duplicate", "withdraw_unsupported"} and not withdrawn:
            raise ValueError(f"withdrawal disposition needs an explicit withdrawn clause: {fact_key}")
        if disposition == "merge_duplicate" and not parent.get("replaced_by"):
            raise ValueError(f"merged parent needs a replacement id: {fact_key}")

        child_ids: list[str] = []
        for child in children:
            suffix = str(child.get("suffix") or "").strip()
            migration_id = f"m1.{qid}.{expected_sha[:16]}.{suffix}"
            if not suffix or migration_id in migration_ids:
                raise ValueError(f"duplicate or missing child suffix: {fact_key}")
            migration_ids.add(migration_id)
            child_ids.append(migration_id)
            if child.get("tipo") not in {"core", "supplementary"}:
                raise ValueError(f"invalid child type: {migration_id}")
            for field in ("texto", "valor", "requiredness_reason"):
                if not str(child.get(field) or "").strip():
                    raise ValueError(f"missing {field}: {migration_id}")
            context_ids = child.get("source_context_ids")
            if not isinstance(context_ids, list) or not context_ids or len(set(context_ids)) != len(context_ids):
                raise ValueError(f"source ids must be a nonempty unique list: {migration_id}")
            support_by_context = support_claims.get(migration_id)
            if not isinstance(support_by_context, dict) or set(support_by_context) != set(context_ids):
                raise ValueError(f"literal support context coverage is not exact: {migration_id}")
            source_bindings: list[dict[str, Any]] = []
            for context_id in context_ids:
                source = contexts_by_key.get((qid, context_id))
                if source is None:
                    raise ValueError(f"source row is absent or cross-qid: {migration_id}/{context_id}")
                page = source.get("page_number")
                if isinstance(page, bool) or not isinstance(page, int) or page <= 0:
                    raise ValueError(f"source page is not positive: {migration_id}/{context_id}")
                content = str(source.get("content") or "")
                if not content.strip() or not str(source.get("source_file") or "").strip():
                    raise ValueError(f"source binding is incomplete: {migration_id}/{context_id}")
                anchors = support_by_context[context_id]
                if not isinstance(anchors, list) or not anchors or len(set(anchors)) != len(anchors):
                    raise ValueError(f"support anchors must be a nonempty unique list: {migration_id}/{context_id}")
                spans_by_bounds: dict[tuple[int, int], dict[str, Any]] = {}
                for anchor in anchors:
                    if not isinstance(anchor, str) or not anchor.strip() or content.count(anchor) != 1:
                        raise ValueError(f"support anchor must occur exactly once: {migration_id}/{context_id}/{anchor}")
                    anchor_start = content.index(anchor)
                    line_start = content.rfind("\n", 0, anchor_start) + 1
                    line_end = content.find("\n", anchor_start + len(anchor))
                    if line_end < 0:
                        line_end = len(content)
                    bounds = (line_start, line_end)
                    span = spans_by_bounds.setdefault(bounds, {
                        "start_char": line_start,
                        "end_char": line_end,
                        "literal": content[line_start:line_end],
                        "anchors": [],
                    })
                    span["anchors"].append(anchor)
                support_spans = []
                for bounds in sorted(spans_by_bounds):
                    span = spans_by_bounds[bounds]
                    span["anchors"] = sorted(span["anchors"])
                    span["literal_sha256"] = sha256_bytes(span["literal"].encode("utf-8"))
                    support_spans.append(span)
                source_bindings.append({
                    "context_id": context_id,
                    "source_file": source["source_file"],
                    "page_number": page,
                    "document_id": source.get("document_id"),
                    "product_model": source.get("product_model"),
                    "content_sha256": sha256_bytes(content.encode("utf-8")),
                    "support_spans": support_spans,
                })
            claims.append({
                "migration_id": migration_id,
                "qid": qid,
                "parent_fact_key": fact_key,
                "parent_fact_sha256": expected_sha,
                "texto": child["texto"],
                "valor": child["valor"],
                "tipo": child["tipo"],
                "basis": "explicit",
                "requiredness_reason": child["requiredness_reason"],
                "source_bindings": source_bindings,
                "answer_replay": None,
            })

        parent_rows.append({
            "qid": qid,
            "question": rows_by_qid[qid]["question"],
            "parent_fact_key": fact_key,
            "parent_fact_sha256": expected_sha,
            "legacy_stage_bucket": bridge_parent["legacy_stage_bucket"],
            "blocker": projected_parent["source_decision"],
            "disposition": disposition,
            "decision_reason": parent["decision_reason"],
            "withdrawn_clauses": withdrawn,
            "replaced_by": parent.get("replaced_by") or [],
            "merge_overlap_anchor": parent.get("merge_overlap_anchor"),
            "child_migration_ids": child_ids,
        })

    all_child_ids = {row["migration_id"] for row in claims}
    if set(support_claims) != all_child_ids:
        missing = sorted(all_child_ids - set(support_claims))
        unexpected = sorted(set(support_claims) - all_child_ids)
        raise ValueError(f"literal support population mismatch: missing={missing}, unexpected={unexpected}")
    claim_by_id = {row["migration_id"]: row for row in claims}
    for row in parent_rows:
        for replacement in row["replaced_by"]:
            if replacement not in all_child_ids:
                raise ValueError(f"merge replacement is missing: {replacement}")
            replacement_claim = claim_by_id[replacement]
            overlap = str(row.get("merge_overlap_anchor") or "").strip()
            if replacement_claim["qid"] != row["qid"] or not overlap:
                raise ValueError(f"merge replacement lacks qid-local equivalence receipt: {replacement}")
            supported_literals = [
                span["literal"]
                for binding in replacement_claim["source_bindings"]
                for span in binding["support_spans"]
            ]
            if overlap not in replacement_claim["texto"] + replacement_claim["valor"] and not any(
                overlap in literal for literal in supported_literals
            ):
                raise ValueError(f"merge overlap is not supported by replacement: {replacement}")

    disposition_hist = dict(sorted(Counter(row["disposition"] for row in parent_rows).items()))
    type_hist = dict(sorted(Counter(row["tipo"] for row in claims).items()))
    result: dict[str, Any] = {
        "schema_version": "s125_m1_known_hold_contract_v1",
        "instrument": "s125_build_m1_known_hold_contract",
        "status": "MIGRATION_CONTRACT_FROZEN_NO_BOT_CREDIT",
        "authority": {
            "preregistration": str(PREREG_PATH.relative_to(ROOT)).replace("\\", "/"),
            "preregistration_sha256": file_sha256(PREREG_PATH),
            "migration_spec": str(SPEC_PATH.relative_to(ROOT)).replace("\\", "/"),
            "migration_spec_sha256": file_sha256(SPEC_PATH),
            "literal_support": str(SUPPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "literal_support_sha256": file_sha256(SUPPORT_PATH),
        },
        "summary": {
            "parent_count": len(parent_rows),
            "qid_count": len({row["qid"] for row in parent_rows}),
            "child_count": len(claims),
            "child_type_histogram": type_hist,
            "disposition_histogram": disposition_hist,
            "legacy_stage_histogram": actual_hist,
            "withdrawn_clause_count": sum(len(row["withdrawn_clauses"]) for row in parent_rows),
            "unresolved_parent_count": disposition_hist.get("unresolved", 0),
            "model_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "bot_delta": 0,
            "measurement_delta_only": True,
        },
        "parents": parent_rows,
        "claims": claims,
        "limitations": [
            "This artifact freezes the evaluation contract but does not score the frozen answers.",
            "It reconciles the 33 known blockers only; other provisional legacy carries remain outside an official whole-benchmark atomic KPI.",
        ],
    }
    result["payload_sha256"] = canonical_sha256(result)
    return result


def build_from_files() -> dict[str, Any]:
    prereg = load_yaml(PREREG_PATH)
    spec = load_yaml(SPEC_PATH)
    support = load_yaml(SUPPORT_PATH)
    frozen = _resolve_frozen_inputs(prereg)
    return build_contract(
        prereg=prereg,
        spec=spec,
        support=support,
        bridge=load_json(frozen["atomic_bridge"][0]),
        projection=load_json(frozen["external_contract_projection"][0]),
        contexts=load_json(frozen["served_contexts"][0]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "s125_m1_known_hold_contract_v1.json",
    )
    args = parser.parse_args()
    result = build_from_files()
    output = args.output if args.output.is_absolute() else (ROOT / args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    print(f"payload_sha256={result['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
