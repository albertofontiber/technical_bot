#!/usr/bin/env python3
"""Build the deterministic S134 canonical document-metadata shadow manifest."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s134_document_metadata_manifest_prereg_v1.yaml"


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


def _field_value(value: Any, *, field: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"non-string document metadata: {field}")
    if not value.strip():
        return None
    return value


def _validate_frozen_files(prereg: dict[str, Any], root: Path) -> None:
    design = prereg["design"]
    if file_sha(root / design["path"]) != design["sha256"]:
        raise RuntimeError("design drift")
    for name in ("snapshot", "candidate_bindings"):
        spec = prereg["frozen_inputs"][name]
        if file_sha(root / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"frozen input drift: {name}")


def _active_documents(
    prereg: dict[str, Any], root: Path
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    spec = prereg["frozen_inputs"]["candidate_bindings"]
    payload = load_json(root / spec["path"])
    if payload.get("status") != "GO":
        raise RuntimeError("candidate binding manifest is not GO")
    if payload.get("generation", {}).get("materialization_id") != spec["materialization_id"]:
        raise RuntimeError("candidate materialization identity drift")

    accepted = set(prereg["contract"]["active_binding_statuses"])
    grouped: dict[str, list[str]] = collections.defaultdict(list)
    for row in payload.get("entries", []):
        if row.get("binding_status") not in accepted:
            continue
        document_id = row.get("document_id")
        extraction = row.get("extraction_sha256")
        if not isinstance(document_id, str) or not document_id:
            raise RuntimeError("active binding without document_id")
        if not isinstance(extraction, str) or len(extraction) != 64:
            raise RuntimeError("active binding without extraction_sha256")
        grouped[document_id].append(extraction)

    for document_id, extractions in grouped.items():
        if len(extractions) != len(set(extractions)):
            raise RuntimeError(f"duplicate active extraction binding: {document_id}")
        grouped[document_id] = sorted(extractions)

    expected = prereg["expected_population"]
    if sum(map(len, grouped.values())) != expected["active_extraction_bindings"]:
        raise RuntimeError("active extraction binding count drift")
    if len(grouped) != expected["distinct_active_documents"]:
        raise RuntimeError("active document count drift")
    cardinalities = collections.Counter(map(len, grouped.values()))
    if cardinalities != collections.Counter(
        {
            1: expected["active_documents_with_one_extraction"],
            2: expected["active_documents_with_two_extractions"],
        }
    ):
        raise RuntimeError("active extraction cardinality drift")
    return dict(grouped), payload


def _snapshot_metadata(
    prereg: dict[str, Any], root: Path, active_documents: dict[str, list[str]]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    spec = prereg["frozen_inputs"]["snapshot"]
    required = list(prereg["contract"]["required_fields"])
    optional = list(prereg["contract"]["optional_fields"])
    fields = required + optional
    values: dict[str, dict[str, set[str]]] = {
        document_id: {field: set() for field in fields}
        for document_id in active_documents
    }
    chunk_counts: collections.Counter[str] = collections.Counter()
    observed_extractions: dict[str, set[str]] = collections.defaultdict(set)
    logical = hashlib.sha256()
    document_rows = 0
    chunk_rows = 0

    with gzip.open(root / spec["path"], "rb") as stream:
        for raw_line in stream:
            logical.update(raw_line)
            row = json.loads(raw_line)
            if row.get("kind") == "document":
                document_rows += 1
                continue
            if row.get("kind") != "chunk":
                continue
            chunk_rows += 1
            document_id = row.get("document_id")
            if document_id not in active_documents or row.get("parent_id") is not None:
                continue
            extraction = row.get("extraction_sha256")
            if extraction not in active_documents[document_id]:
                raise RuntimeError(
                    f"active document contains unbound extraction: {document_id}"
                )
            observed_extractions[document_id].add(extraction)
            chunk_counts[document_id] += 1
            for field in fields:
                value = _field_value(row.get(field), field=field)
                if value is not None:
                    values[document_id][field].add(value)

    snapshot_checks = {
        "canonical_jsonl_sha256": logical.hexdigest() == spec["canonical_jsonl_sha256"],
        "documents": document_rows == spec["documents"],
        "chunks": chunk_rows == spec["chunks"],
    }
    if not all(snapshot_checks.values()):
        raise RuntimeError("snapshot logical receipt drift")

    records: dict[str, dict[str, Any]] = {}
    conflicts = 0
    missing_required = 0
    for document_id in sorted(active_documents):
        if not chunk_counts[document_id]:
            raise RuntimeError(f"active document has no base chunks: {document_id}")
        if observed_extractions[document_id] != set(active_documents[document_id]):
            raise RuntimeError(f"active extraction missing from base chunks: {document_id}")
        record: dict[str, Any] = {}
        for field in fields:
            field_values = values[document_id][field]
            if len(field_values) > 1:
                conflicts += 1
            if field in required and not field_values:
                missing_required += 1
            record[field] = next(iter(field_values)) if len(field_values) == 1 else None
        records[document_id] = record

    expected = prereg["expected_population"]
    if sum(chunk_counts.values()) != expected["source_base_chunks"]:
        raise RuntimeError("source base chunk count drift")
    if conflicts != expected["field_conflicts"]:
        raise RuntimeError(f"document metadata conflict count drift: {conflicts}")
    if missing_required != expected["missing_required_values"]:
        raise RuntimeError(
            f"required document metadata missing count drift: {missing_required}"
        )
    return records, {
        "snapshot_checks": snapshot_checks,
        "source_base_chunks": sum(chunk_counts.values()),
        "chunk_counts": dict(chunk_counts),
        "field_conflicts": conflicts,
        "missing_required_values": missing_required,
    }


def build_manifest(prereg: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    _validate_frozen_files(prereg, root)
    active_documents, bindings = _active_documents(prereg, root)
    metadata, snapshot = _snapshot_metadata(prereg, root, active_documents)
    authority = prereg["contract"]["authority"]
    snapshot_sha = prereg["frozen_inputs"]["snapshot"]["sha256"]
    materialization_id = prereg["frozen_inputs"]["candidate_bindings"][
        "materialization_id"
    ]

    entries: list[dict[str, Any]] = []
    for document_id in sorted(active_documents):
        row = {
            "materialization_id": materialization_id,
            "document_id": document_id,
            "extraction_sha256s": active_documents[document_id],
            **metadata[document_id],
            "metadata_authority": authority,
            "source_snapshot_sha256": snapshot_sha,
            "source_base_chunk_count": snapshot["chunk_counts"][document_id],
        }
        row["metadata_receipt_sha256"] = canonical_sha(row)
        entries.append(row)

    checks = {
        **snapshot["snapshot_checks"],
        "active_extraction_bindings": (
            sum(len(row["extraction_sha256s"]) for row in entries)
            == prereg["expected_population"]["active_extraction_bindings"]
        ),
        "distinct_active_documents": (
            len(entries) == prereg["expected_population"]["distinct_active_documents"]
        ),
        "field_conflicts_zero": snapshot["field_conflicts"] == 0,
        "missing_required_values_zero": snapshot["missing_required_values"] == 0,
        "entries_sorted": [row["document_id"] for row in entries]
        == sorted(row["document_id"] for row in entries),
    }
    if not all(checks.values()):
        raise RuntimeError("metadata manifest gate failed")

    return {
        "instrument": "s134_document_metadata_manifest_v1",
        "schema_version": 1,
        "status": "GO",
        "authority": authority,
        "generation": {
            "materialization_id": materialization_id,
            "candidate_bindings_sha256": prereg["frozen_inputs"][
                "candidate_bindings"
            ]["sha256"],
            "source_snapshot_sha256": snapshot_sha,
            "source_snapshot_canonical_jsonl_sha256": prereg["frozen_inputs"][
                "snapshot"
            ]["canonical_jsonl_sha256"],
        },
        "population": {
            "active_extraction_bindings": sum(
                len(row["extraction_sha256s"]) for row in entries
            ),
            "distinct_active_documents": len(entries),
            "active_documents_by_extraction_count": {
                str(count): documents
                for count, documents in sorted(
                    collections.Counter(
                        len(row["extraction_sha256s"]) for row in entries
                    ).items()
                )
            },
            "source_base_chunks": snapshot["source_base_chunks"],
            "field_conflicts": snapshot["field_conflicts"],
            "missing_required_values": snapshot["missing_required_values"],
        },
        "manifests": {"entries_sha256": canonical_sha(entries)},
        "checks": checks,
        "entries": entries,
        "authorization": prereg["authorization"],
        "cost": prereg["cost"],
        "determinism": {
            "canonical_json": True,
            "entry_order": "document_id_ascending",
        },
        "dependencies": {
            "design_sha256": prereg["design"]["sha256"],
            "candidate_binding_manifest_sha256": file_sha(
                root / prereg["frozen_inputs"]["candidate_bindings"]["path"]
            ),
            "source_snapshot_sha256": file_sha(
                root / prereg["frozen_inputs"]["snapshot"]["path"]
            ),
            "binding_entries_sha256": bindings["manifests"]["entries_sha256"],
        },
    }


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    prereg = load_yaml(prereg_path)
    allowed = {
        ROOT / value
        for value in prereg["execution"].values()
        if isinstance(value, str) and value.endswith(".json")
    }
    if output_path not in allowed:
        raise RuntimeError("output is not preregistered")
    write_manifest(output_path, build_manifest(prereg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
