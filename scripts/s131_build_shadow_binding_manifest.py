#!/usr/bin/env python3
"""Build deterministic, metadata-only shadow binding manifests for S131."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s131_shadow_binding_manifest_prereg_v1.yaml"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BACKFILL = re.compile(r"^backfill:[0-9a-f]{64}$")
_BOUND_ACTIVE = {
    "bound_active_physical_sha_verified",
    "bound_active_legacy_snapshot_only",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _assert_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise RuntimeError(f"invalid SHA-256: {label}")
    return value


def source_pdf_identity_status(value: str | None) -> str:
    if value is None:
        return "unknown"
    if _SHA256.fullmatch(value):
        return "known_physical"
    if _BACKFILL.fullmatch(value):
        return "synthetic_backfill"
    return "unknown"


def _validate_frozen_inputs(prereg: dict[str, Any]) -> None:
    for name, spec in prereg["design"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"design drift: {name}")
    for name, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"frozen input drift: {name}")
    for arm, spec in prereg["arms"].items():
        receipt = spec["materialization_receipt"]
        if file_sha(ROOT / receipt["path"]) != receipt["sha256"]:
            raise RuntimeError(f"arm receipt drift: {arm}")


def _load_raw_descriptors(prereg: dict[str, Any]) -> dict[str, str]:
    payload = load_json(ROOT / prereg["frozen_inputs"]["raw_descriptors"]["path"])
    rows = payload.get("documents")
    if not isinstance(rows, list):
        raise RuntimeError("raw descriptor rows absent")
    descriptors: dict[str, str] = {}
    for row in rows:
        extraction = _assert_sha(row.get("extraction_sha256"), "extraction")
        raw_artifact = _assert_sha(row.get("raw_artifact_sha256"), "raw artifact")
        if extraction in descriptors:
            raise RuntimeError("duplicate raw descriptor extraction")
        descriptors[extraction] = raw_artifact
    expected = prereg["expected_population"]["extractions"]
    if len(descriptors) != expected:
        raise RuntimeError("raw descriptor count drift")
    return descriptors


def _load_snapshot(prereg: dict[str, Any]) -> dict[str, Any]:
    spec = prereg["frozen_inputs"]["snapshot"]
    documents: dict[str, dict[str, Any]] = {}
    pairs: collections.Counter[tuple[str, str]] = collections.Counter()
    extraction_to_documents: dict[str, set[str]] = collections.defaultdict(set)
    logical = hashlib.sha256()
    chunk_rows = 0
    with gzip.open(ROOT / spec["path"], "rb") as stream:
        for raw_line in stream:
            logical.update(raw_line)
            row = json.loads(raw_line)
            if row.get("kind") == "document":
                identifier = str(row.get("id") or "")
                if not identifier or identifier in documents:
                    raise RuntimeError("invalid or duplicate snapshot document")
                documents[identifier] = row
            elif row.get("kind") == "chunk":
                chunk_rows += 1
                extraction = _assert_sha(row.get("extraction_sha256"), "snapshot extraction")
                document = str(row.get("document_id") or "")
                pairs[(document, extraction)] += 1
                extraction_to_documents[extraction].add(document)
    ledger = [
        {
            "document_id": document,
            "extraction_sha256": extraction,
            "chunk_rows": count,
        }
        for (document, extraction), count in sorted(pairs.items())
    ]
    checks = {
        "canonical_jsonl_sha256": logical.hexdigest() == spec["canonical_jsonl_sha256"],
        "documents": len(documents) == spec["documents"],
        "chunks": chunk_rows == spec["chunks"],
        "binding_pairs": len(ledger) == spec["binding_pairs"],
        "binding_ledger_sha256": canonical_sha(ledger) == spec["binding_ledger_sha256"],
    }
    if not all(checks.values()):
        raise RuntimeError("snapshot logical receipt drift")
    return {
        "documents": documents,
        "extraction_to_documents": extraction_to_documents,
        "binding_ledger_sha256": canonical_sha(ledger),
        "checks": checks,
    }


def _load_m25(prereg: dict[str, Any], extractions: set[str]) -> dict[str, dict[str, Any]]:
    payload = load_json(ROOT / prereg["frozen_inputs"]["m25"]["path"])
    rows: dict[str, dict[str, Any]] = {}
    for row in payload.get("rows", []):
        extraction = _assert_sha(row.get("extraction_sha256"), "M25 extraction")
        if extraction in rows:
            raise RuntimeError("duplicate M25 extraction")
        rows[extraction] = row
    if set(rows) != extractions:
        raise RuntimeError("M25 extraction universe drift")
    return rows


def _load_heldout(prereg: dict[str, Any], extractions: set[str]) -> set[str]:
    payload = load_json(ROOT / prereg["frozen_inputs"]["heldout"]["path"])
    if payload.get("status") != "GO":
        raise RuntimeError("heldout embargo is not GO")
    heldout = set(payload.get("closure", {}).get("extraction_sha256s", []))
    if len(heldout) != prereg["expected_population"]["partitions"]["heldout_s130"]["extractions_total"]:
        raise RuntimeError("heldout extraction count drift")
    if not heldout <= extractions or not all(_SHA256.fullmatch(value) for value in heldout):
        raise RuntimeError("heldout extraction universe drift")
    return heldout


def _validate_arm_receipt(
    prereg: dict[str, Any], arm: str, descriptors: dict[str, str]
) -> dict[str, Any]:
    spec = prereg["arms"][arm]
    payload = load_json(ROOT / spec["materialization_receipt"]["path"])
    generation = payload.get("generation", {})
    if generation.get("materialization_id") != spec["materialization_id"]:
        raise RuntimeError(f"materialization ID drift: {arm}")
    if generation.get("manifest_sha256") != spec["generation_manifest_sha256"]:
        raise RuntimeError(f"generation manifest drift: {arm}")
    observed_chunks = (
        payload.get("summary", {}).get("chunks_total")
        if arm == "baseline"
        else payload.get("population", {}).get("rows")
    )
    if observed_chunks != spec["expected_chunks_global"]:
        raise RuntimeError(f"global chunk count drift: {arm}")
    if payload.get("source", {}).get("manifest_sha256") != prereg["frozen_inputs"]["raw_descriptors"]["source_manifest_sha256"]:
        raise RuntimeError(f"source manifest drift: {arm}")
    descriptor_rows = [
        {"extraction_sha256": extraction, "raw_artifact_sha256": raw_artifact}
        for extraction, raw_artifact in sorted(descriptors.items())
    ]
    if arm == "baseline":
        records = generation.get("manifest", {}).get("records", [])
        baseline_descriptors = {
            row["extraction_sha256"]: row["raw_artifact_sha256"] for row in records
        }
        if baseline_descriptors != descriptors:
            raise RuntimeError("baseline raw descriptors diverge")
        if canonical_sha(generation["manifest"]) != spec["generation_manifest_sha256"]:
            raise RuntimeError("baseline manifest does not commit descriptors")
    else:
        reconstructed_manifest = {
            "schema": "chunk_materialization_manifest_v1",
            "version": 1,
            "provenance_contract": "s116_section_lineage_v1",
            "provenance_version": 1,
            "chunker_sha256": payload.get("dependencies", {}).get("chunker_sha256"),
            "materializer_sha256": payload.get("dependencies", {}).get("materializer_sha256"),
            "records": descriptor_rows,
        }
        if canonical_sha(reconstructed_manifest) != spec["generation_manifest_sha256"]:
            raise RuntimeError("candidate manifest does not commit descriptors")
    return {
        "materialization_id": spec["materialization_id"],
        "generation_manifest_sha256": spec["generation_manifest_sha256"],
        "expected_chunks_global": spec["expected_chunks_global"],
    }


def _classify_binding(
    extraction: str,
    *,
    snapshot: dict[str, Any],
    m25: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    document_ids = snapshot["extraction_to_documents"].get(extraction, set())
    if not document_ids:
        return {
            "document_id": None,
            "binding_status": "unbound_absent_from_snapshot",
            "binding_authority": "absent_from_snapshot_shadow_only",
            "document_status_at_snapshot": None,
            "source_pdf_identity": None,
            "source_pdf_identity_status": "unknown",
        }
    if document_ids == {""}:
        return {
            "document_id": None,
            "binding_status": "unbound_snapshot_empty_document",
            "binding_authority": "snapshot_empty_document_shadow_only",
            "document_status_at_snapshot": None,
            "source_pdf_identity": None,
            "source_pdf_identity_status": "unknown",
        }
    if "" in document_ids or len(document_ids) != 1:
        raise RuntimeError(f"non-reciprocal snapshot extraction binding: {extraction}")
    document_id = next(iter(document_ids))
    document = snapshot["documents"].get(document_id)
    if document is None:
        raise RuntimeError(f"snapshot document missing: {document_id}")
    status = document.get("status")
    source_pdf_identity = document.get("source_pdf_sha256")
    if not isinstance(source_pdf_identity, str) or not source_pdf_identity:
        raise RuntimeError(f"bound document PDF identity missing: {document_id}")
    identity_status = source_pdf_identity_status(source_pdf_identity)
    m25_row = m25[extraction]
    if status == "active":
        exact_physical = (
            m25_row.get("terminal") == "primary_unique_active_pdf_sha"
            and m25_row.get("document_id") == document_id
            and m25_row.get("matching_document_count") == 1
            and m25_row.get("status") == "active"
            and source_pdf_identity == extraction
            and identity_status == "known_physical"
        )
        if exact_physical:
            binding_status = "bound_active_physical_sha_verified"
            authority = "m25_exact_active_and_snapshot_reciprocal"
        else:
            if m25_row.get("terminal") == "primary_unique_active_pdf_sha":
                raise RuntimeError(f"contradictory exact-active binding: {extraction}")
            binding_status = "bound_active_legacy_snapshot_only"
            authority = "legacy_snapshot_reciprocal_shadow_only"
    elif status in {"needs_review", "superseded"}:
        binding_status = "bound_nonactive_legacy_snapshot"
        authority = "legacy_snapshot_reciprocal_shadow_only"
    else:
        raise RuntimeError(f"unsupported bound document status: {status}")
    return {
        "document_id": document_id,
        "binding_status": binding_status,
        "binding_authority": authority,
        "document_status_at_snapshot": status,
        "source_pdf_identity": source_pdf_identity,
        "source_pdf_identity_status": identity_status,
    }


def build_payload(prereg_path: Path, arm: str) -> dict[str, Any]:
    prereg = load_yaml(prereg_path)
    _validate_frozen_inputs(prereg)
    descriptors = _load_raw_descriptors(prereg)
    descriptor_rows = [
        {"extraction_sha256": extraction, "raw_artifact_sha256": raw_artifact}
        for extraction, raw_artifact in sorted(descriptors.items())
    ]
    snapshot = _load_snapshot(prereg)
    if set(snapshot["extraction_to_documents"]) - set(descriptors):
        raise RuntimeError("snapshot contains extraction outside raw descriptors")
    m25 = _load_m25(prereg, set(descriptors))
    heldout = _load_heldout(prereg, set(descriptors))
    generation = _validate_arm_receipt(prereg, arm, descriptors)
    heldout_sha = prereg["frozen_inputs"]["heldout"]["sha256"]
    entries = []
    for extraction, raw_artifact in sorted(descriptors.items()):
        classification = _classify_binding(
            extraction,
            snapshot=snapshot,
            m25=m25,
        )
        core = {
            "materialization_id": generation["materialization_id"],
            "extraction_sha256": extraction,
            "raw_artifact_sha256": raw_artifact,
            **classification,
            "evaluation_partition": "heldout_s130" if extraction in heldout else "development",
            "snapshot_binding_ledger_sha256": snapshot["binding_ledger_sha256"],
            "heldout_manifest_sha256": heldout_sha,
        }
        entries.append({**core, "binding_receipt_sha256": canonical_sha(core)})

    status_counts = collections.Counter(row["binding_status"] for row in entries)
    partition_counts: dict[str, dict[str, int]] = {}
    for partition in ("development", "heldout_s130"):
        selected = [row for row in entries if row["evaluation_partition"] == partition]
        partition_counts[partition] = {
            "extractions_total": len(selected),
            "bound_active_extractions": sum(
                row["binding_status"] in _BOUND_ACTIVE for row in selected
            ),
        }
    expected = prereg["expected_population"]
    checks = {
        "bindings_exact": len(entries) == expected["bindings_per_arm"],
        "binding_statuses_exact": dict(status_counts) == expected["binding_statuses"],
        "partitions_exact": partition_counts == expected["partitions"],
        "distinct_bound_documents_exact": len(
            {row["document_id"] for row in entries if row["document_id"] is not None}
        )
        == expected["distinct_bound_documents"],
        "distinct_active_bound_documents_exact": len(
            {
                row["document_id"]
                for row in entries
                if row["binding_status"] in _BOUND_ACTIVE
            }
        )
        == expected["distinct_active_bound_documents"],
        "heldout_all_bound_active": all(
            row["binding_status"] in _BOUND_ACTIVE
            for row in entries
            if row["evaluation_partition"] == "heldout_s130"
        ),
        "receipts_exact": all(
            row["binding_receipt_sha256"]
            == canonical_sha({key: value for key, value in row.items() if key != "binding_receipt_sha256"})
            for row in entries
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"binding manifest population drift: {checks}")
    payload = {
        "instrument": "s131_shadow_binding_manifest_v1",
        "schema_version": 1,
        "arm": arm,
        "status": "GO",
        "authority": "legacy_snapshot_reciprocal_shadow_only_no_production_binding_claim",
        "dependencies": {
            "prereg_sha256": file_sha(prereg_path),
            "design_v3_sha256": prereg["design"]["v3"]["sha256"],
            "snapshot_sha256": prereg["frozen_inputs"]["snapshot"]["sha256"],
            "m25_sha256": prereg["frozen_inputs"]["m25"]["sha256"],
            "raw_descriptors_sha256": prereg["frozen_inputs"]["raw_descriptors"]["sha256"],
            "heldout_sha256": heldout_sha,
        },
        "generation": generation,
        "population": {
            "extractions": len(entries),
            "binding_statuses": dict(sorted(status_counts.items())),
            "partitions": partition_counts,
            "distinct_bound_documents": expected["distinct_bound_documents"],
            "distinct_active_bound_documents": expected["distinct_active_bound_documents"],
        },
        "manifests": {
            "raw_descriptors_sha256": canonical_sha(descriptor_rows),
            "entries_sha256": canonical_sha(entries),
            "binding_receipts_sha256": canonical_sha(
                [row["binding_receipt_sha256"] for row in entries]
            ),
            "snapshot_binding_ledger_sha256": snapshot["binding_ledger_sha256"],
            "heldout_manifest_sha256": heldout_sha,
        },
        "checks": checks,
        "entries": entries,
        "authorization": {
            "database": False,
            "migration_apply": False,
            "retrieval": False,
            "models": False,
            "embeddings": False,
            "serving": False,
            "deploy": False,
            "facts_moved_to_ok": 0,
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "embeddings": 0,
            "raw_store_reads": 0,
        },
    }
    payload["determinism"] = {"logical_payload_sha256": canonical_sha(payload)}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_payload(args.prereg.resolve(), args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
