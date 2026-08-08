"""Governed, immutable derivations of raw extraction artifacts.

The raw LlamaParse JSON and its SHA-bound PDF remain authoritative inputs.  A
derivation is a deterministic, content-addressed record plus a compact manifest
that can be replayed before any contextualization, embedding or indexing step.
This module performs no database, network or source-artifact writes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .superscript_overlay import preserve_numeric_superscripts


DERIVATION_CONTRACT = "numeric_pdf_superscript_overlay_v1"
DERIVATION_VERSION = 1


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


@dataclass(frozen=True)
class ExtractionDerivation:
    """One replayable, content-addressed extraction derivation."""

    record: dict[str, Any]
    manifest: dict[str, Any]


def _manifest(
    *,
    raw: bytes,
    source_record: dict[str, Any],
    derived_record: dict[str, Any],
    pdf_path: str | Path,
    applied: tuple[dict[str, Any], ...],
    abstained: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    raw_sha = sha256_bytes(raw)
    derived_sha = sha256_bytes(canonical_json_bytes(derived_record))
    receipts = list(applied)
    abstentions = list(abstained)
    return {
        "schema": "extraction_derivation_manifest_v1",
        "version": DERIVATION_VERSION,
        "contract": DERIVATION_CONTRACT,
        "extraction_sha256": source_record["sha256"],
        "source_raw_artifact_sha256": raw_sha,
        "source_pdf_sha256": source_record["sha256"],
        "derived_artifact_sha256": derived_sha,
        "applied_receipts_sha256": sha256_bytes(canonical_json_bytes(receipts)),
        "abstention_receipts_sha256": sha256_bytes(canonical_json_bytes(abstentions)),
        "applied_count": len(receipts),
        "abstained_count": len(abstentions),
        "changed_pages": sorted({int(row["page_number"]) for row in receipts}),
        "source_file": Path(pdf_path).name,
        "raw_artifact_mutated": False,
        "receipts": receipts,
        "abstentions": abstentions,
    }


def derive_numeric_superscripts(
    raw: bytes,
    pdf_path: str | Path,
) -> ExtractionDerivation:
    """Derive explicit numeric superscript markup from SHA-bound PDF geometry."""
    source = json.loads(raw, parse_constant=_reject_json_constant)
    if not isinstance(source, dict):
        raise ValueError("raw extraction artifact must be a JSON object")
    before = canonical_json_bytes(source)
    result = preserve_numeric_superscripts(source, pdf_path)
    if canonical_json_bytes(source) != before:
        raise RuntimeError("numeric superscript overlay mutated its source record")
    manifest = _manifest(
        raw=raw,
        source_record=source,
        derived_record=result.record,
        pdf_path=pdf_path,
        applied=result.applied,
        abstained=result.abstained,
    )
    return ExtractionDerivation(record=result.record, manifest=manifest)


def validate_derivation(
    envelope: ExtractionDerivation,
    *,
    source_raw: bytes | None = None,
    pdf_path: str | Path | None = None,
) -> list[str]:
    """Validate envelope integrity without trusting its stored hashes.

    Persisted consumers should pass both source inputs; optionality keeps the
    pure envelope check usable after those large artifacts have been detached.
    """
    failures: list[str] = []
    manifest = envelope.manifest
    if manifest.get("schema") != "extraction_derivation_manifest_v1":
        failures.append("schema")
    if manifest.get("version") != DERIVATION_VERSION:
        failures.append("version")
    if manifest.get("contract") != DERIVATION_CONTRACT:
        failures.append("contract")
    if manifest.get("derived_artifact_sha256") != sha256_bytes(
        canonical_json_bytes(envelope.record)
    ):
        failures.append("derived_artifact_sha256")
    receipts = manifest.get("receipts")
    abstentions = manifest.get("abstentions")
    if not isinstance(receipts, list):
        failures.append("receipts")
        receipts = []
    if not isinstance(abstentions, list):
        failures.append("abstentions")
        abstentions = []
    if manifest.get("applied_count") != len(receipts):
        failures.append("applied_count")
    if manifest.get("abstained_count") != len(abstentions):
        failures.append("abstained_count")
    if manifest.get("applied_receipts_sha256") != sha256_bytes(
        canonical_json_bytes(receipts)
    ):
        failures.append("applied_receipts_sha256")
    if manifest.get("abstention_receipts_sha256") != sha256_bytes(
        canonical_json_bytes(abstentions)
    ):
        failures.append("abstention_receipts_sha256")
    changed_pages = sorted(
        {
            int(row["page_number"])
            for row in receipts
            if isinstance(row, dict) and isinstance(row.get("page_number"), int)
        }
    )
    if manifest.get("changed_pages") != changed_pages:
        failures.append("changed_pages")
    if manifest.get("raw_artifact_mutated") is not False:
        failures.append("raw_artifact_mutated")
    if manifest.get("extraction_sha256") != envelope.record.get("sha256"):
        failures.append("extraction_sha256")
    if source_raw is not None:
        if manifest.get("source_raw_artifact_sha256") != sha256_bytes(source_raw):
            failures.append("source_raw_artifact_sha256")
        try:
            source_record = json.loads(
                source_raw, parse_constant=_reject_json_constant
            )
            if manifest.get("extraction_sha256") != source_record.get("sha256"):
                failures.append("source_extraction_sha256")
        except (AttributeError, json.JSONDecodeError, ValueError):
            failures.append("source_raw_json")
    if pdf_path is not None:
        digest = hashlib.sha256()
        with Path(pdf_path).open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if manifest.get("source_pdf_sha256") != digest.hexdigest():
            failures.append("source_pdf_sha256")
    return sorted(set(failures))
