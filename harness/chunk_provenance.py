"""Deterministic structural rows for immutable ``chunks_v3`` generations.

This module is the materializer.  Independent validation lives in the S117
replay script and deliberately does not call :func:`materialize_raw_record`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from typing import Any

from .chunk import Chunk, SectionAnchor, chunk_document

PROVENANCE_VERSION = 1
PROVENANCE_CONTRACT = "s116_section_lineage_v1"
MATERIALIZATION_NAMESPACE = uuid.UUID("3a4c744b-e79c-57db-98cd-9cb8ef55d4cf")
ROW_NAMESPACE = uuid.UUID("2c1f6003-f8ce-5472-96c4-7c43899234b1")
_NUL = "\x00"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

ROW_MANIFEST_FIELDS = (
    "id",
    "materialization_id",
    "extraction_sha256",
    "chunk_index",
    "content_sha256",
    "provenance_version",
    "provenance_contract",
    "raw_artifact_sha256",
    "chunker_sha256",
    "provenance_payload_sha256",
    "source_block_start",
    "source_block_end",
    "section_anchor",
    "section_lineage",
    "section_title",
    "section_path",
    "page_number",
    "is_flow_diagram",
    "has_diagram",
    "confidence",
    "duplicate_of",
)


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


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def anchor_to_dict(anchor: SectionAnchor | None) -> dict[str, Any] | None:
    if anchor is None:
        return None
    if not isinstance(anchor, SectionAnchor) or not anchor.is_internally_valid():
        raise ValueError("invalid section anchor")
    return {
        "heading_text": anchor.heading_text,
        "title": anchor.title,
        "level": anchor.level,
        "source_page": anchor.source_page,
        "source_block_index": anchor.source_block_index,
        "heading_sha256": anchor.heading_sha256,
    }


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _validate_chunk_envelope(chunk: Chunk) -> None:
    if not isinstance(chunk.content, str) or not chunk.content:
        raise ValueError("invalid chunk content")
    if (
        not isinstance(chunk.chunk_index, int)
        or isinstance(chunk.chunk_index, bool)
        or chunk.chunk_index < 0
    ):
        raise ValueError("invalid chunk index")
    if chunk.page_number is not None and (
        not isinstance(chunk.page_number, int) or isinstance(chunk.page_number, bool)
    ):
        raise ValueError("invalid page number")
    if chunk.confidence is not None and (
        not isinstance(chunk.confidence, (int, float))
        or isinstance(chunk.confidence, bool)
        or not math.isfinite(chunk.confidence)
        or not 0 <= chunk.confidence <= 1
    ):
        raise ValueError("invalid confidence")
    if not isinstance(chunk.is_flow_diagram, bool) or not isinstance(chunk.has_diagram, bool):
        raise ValueError("invalid diagram flags")
    if chunk.section_title is not None and not isinstance(chunk.section_title, str):
        raise ValueError("invalid section title")
    if chunk.section_path is not None and not isinstance(chunk.section_path, str):
        raise ValueError("invalid section path")
    lineage = chunk.section_lineage
    if not isinstance(lineage, tuple) or not all(
        isinstance(anchor, SectionAnchor) and anchor.is_internally_valid()
        for anchor in lineage
    ):
        raise ValueError("invalid section lineage")
    if lineage:
        if (
            chunk.section_anchor != lineage[-1]
            or chunk.section_title != lineage[-1].title
            or chunk.section_path != " > ".join(anchor.title for anchor in lineage)
        ):
            raise ValueError("inconsistent section lineage")
    elif any(
        value is not None
        for value in (chunk.section_anchor, chunk.section_title, chunk.section_path)
    ):
        raise ValueError("inconsistent empty section lineage")


def generation_manifest(
    records: list[dict[str, str]],
    *,
    chunker_sha256: str,
    materializer_sha256: str,
) -> dict[str, Any]:
    if not is_sha256(chunker_sha256) or not is_sha256(materializer_sha256):
        raise ValueError("invalid implementation SHA-256")
    normalized = []
    seen = set()
    for row in sorted(records, key=lambda item: item["extraction_sha256"]):
        extraction = row.get("extraction_sha256")
        raw = row.get("raw_artifact_sha256")
        if not is_sha256(extraction) or not is_sha256(raw) or extraction in seen:
            raise ValueError("invalid or duplicate generation record")
        seen.add(extraction)
        normalized.append({
            "extraction_sha256": extraction,
            "raw_artifact_sha256": raw,
        })
    if not normalized:
        raise ValueError("empty generation")
    return {
        "schema": "chunk_materialization_manifest_v1",
        "version": 1,
        "provenance_contract": PROVENANCE_CONTRACT,
        "provenance_version": PROVENANCE_VERSION,
        "chunker_sha256": chunker_sha256,
        "materializer_sha256": materializer_sha256,
        "records": normalized,
    }


def materialization_identity(manifest: dict[str, Any]) -> tuple[str, str]:
    digest = sha256_bytes(canonical_json_bytes(manifest))
    return digest, str(uuid.uuid5(MATERIALIZATION_NAMESPACE, f"v1{_NUL}{digest}"))


def provenance_payload(
    chunk: Chunk,
    *,
    raw_artifact_sha256: str,
    chunker_sha256: str,
) -> dict[str, Any]:
    _validate_chunk_envelope(chunk)
    if not is_sha256(raw_artifact_sha256) or not is_sha256(chunker_sha256):
        raise ValueError("invalid provenance SHA-256")
    if (
        not isinstance(chunk.source_block_start, int)
        or isinstance(chunk.source_block_start, bool)
        or not isinstance(chunk.source_block_end, int)
        or isinstance(chunk.source_block_end, bool)
        or chunk.source_block_start < 0
        or chunk.source_block_end < chunk.source_block_start
    ):
        raise ValueError("invalid source block span")
    return {
        "provenance_version": PROVENANCE_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT,
        "raw_artifact_sha256": raw_artifact_sha256,
        "chunker_sha256": chunker_sha256,
        "content_sha256": sha256_bytes(chunk.content.encode("utf-8")),
        "source_block_start": chunk.source_block_start,
        "source_block_end": chunk.source_block_end,
        "section_anchor": anchor_to_dict(chunk.section_anchor),
        "section_lineage": [anchor_to_dict(anchor) for anchor in chunk.section_lineage],
    }


def chunk_identity(
    materialization_id: str,
    extraction_sha256: str,
    chunk_index: int,
    provenance_payload_sha256: str,
) -> str:
    uuid.UUID(materialization_id)
    if (
        not is_sha256(extraction_sha256)
        or not is_sha256(provenance_payload_sha256)
        or not isinstance(chunk_index, int)
        or isinstance(chunk_index, bool)
        or chunk_index < 0
    ):
        raise ValueError("invalid chunk identity input")
    name = _NUL.join((
        "v1",
        materialization_id,
        extraction_sha256,
        str(chunk_index),
        provenance_payload_sha256,
    ))
    return str(uuid.uuid5(ROW_NAMESPACE, name))


def _row_from_chunk(
    chunk: Chunk,
    *,
    materialization_id: str,
    extraction_sha256: str,
    raw_artifact_sha256: str,
    chunker_sha256: str,
) -> dict[str, Any]:
    payload = provenance_payload(
        chunk,
        raw_artifact_sha256=raw_artifact_sha256,
        chunker_sha256=chunker_sha256,
    )
    payload_sha = sha256_bytes(canonical_json_bytes(payload))
    row_id = chunk_identity(
        materialization_id,
        extraction_sha256,
        chunk.chunk_index,
        payload_sha,
    )
    return {
        "id": row_id,
        "materialization_id": materialization_id,
        "extraction_sha256": extraction_sha256,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        **payload,
        "provenance_payload_sha256": payload_sha,
        "section_title": chunk.section_title,
        "section_path": chunk.section_path,
        "page_number": chunk.page_number,
        "is_flow_diagram": bool(chunk.is_flow_diagram),
        "has_diagram": bool(chunk.has_diagram),
        "confidence": chunk.confidence,
        "duplicate_of": chunk.duplicate_of,
    }


def materialize_raw_record(
    raw: bytes,
    *,
    materialization_id: str,
    chunker_sha256: str,
) -> list[dict[str, Any]]:
    """Materialize deterministic structural rows from one complete raw JSON."""
    record = json.loads(raw, parse_constant=_reject_json_constant)
    extraction_sha256 = record.get("sha256")
    if not is_sha256(extraction_sha256):
        raise ValueError("raw record lacks a valid extraction SHA-256")
    raw_sha256 = sha256_bytes(raw)
    chunks = chunk_document(record)
    if [chunk.chunk_index for chunk in chunks] != list(range(len(chunks))):
        raise ValueError("non-contiguous chunk ordinals")
    rows = [
        _row_from_chunk(
            chunk,
            materialization_id=materialization_id,
            extraction_sha256=extraction_sha256,
            raw_artifact_sha256=raw_sha256,
            chunker_sha256=chunker_sha256,
        )
        for chunk in chunks
    ]
    transient_to_stable = {
        chunk.id: row["id"] for chunk, row in zip(chunks, rows)
    }
    for chunk, row in zip(chunks, rows):
        if chunk.duplicate_of is None:
            row["duplicate_of"] = None
        elif chunk.duplicate_of in transient_to_stable:
            row["duplicate_of"] = transient_to_stable[chunk.duplicate_of]
        else:
            raise ValueError("duplicate target is outside the materialized record")
    return rows


def row_manifest_bytes(rows: list[dict[str, Any]]) -> bytes:
    ordered = sorted(
        rows,
        key=lambda row: (row["extraction_sha256"], row["chunk_index"]),
    )
    lines = []
    for row in ordered:
        if set(ROW_MANIFEST_FIELDS) - set(row):
            raise ValueError("row is missing manifest fields")
        core = {field: row[field] for field in ROW_MANIFEST_FIELDS}
        lines.append(canonical_json_bytes(core))
    return b"\n".join(lines) + (b"\n" if lines else b"")
