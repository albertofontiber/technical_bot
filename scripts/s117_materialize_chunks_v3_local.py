#!/usr/bin/env python3
"""Local, deterministic S117 materialization and independent raw replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as materializer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_chunks_v3_local_migration_prereg_v21.yaml"
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.json$")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _strict_json_loads(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw, parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise ValueError("raw extraction record must be an object")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _anchor(anchor: object | None) -> dict[str, Any] | None:
    if anchor is None:
        return None
    return {
        "heading_text": anchor.heading_text,
        "title": anchor.title,
        "level": anchor.level,
        "source_page": anchor.source_page,
        "source_block_index": anchor.source_block_index,
        "heading_sha256": anchor.heading_sha256,
    }


def _validate_expected_chunk(chunk: object) -> None:
    """Independent envelope validation; does not call the row materializer."""
    if not isinstance(chunk.content, str) or not chunk.content:
        raise ValueError("invalid expected chunk content")
    if (
        not isinstance(chunk.chunk_index, int)
        or isinstance(chunk.chunk_index, bool)
        or chunk.chunk_index < 0
    ):
        raise ValueError("invalid expected chunk index")
    if chunk.page_number is not None and (
        not isinstance(chunk.page_number, int) or isinstance(chunk.page_number, bool)
    ):
        raise ValueError("invalid expected page number")
    if chunk.confidence is not None and (
        not isinstance(chunk.confidence, (int, float))
        or isinstance(chunk.confidence, bool)
        or not math.isfinite(chunk.confidence)
        or not 0 <= chunk.confidence <= 1
    ):
        raise ValueError("invalid expected confidence")
    if not isinstance(chunk.is_flow_diagram, bool) or not isinstance(chunk.has_diagram, bool):
        raise ValueError("invalid expected diagram flags")
    lineage = chunk.section_lineage
    if not isinstance(lineage, tuple) or not all(
        isinstance(anchor, chunk_module.SectionAnchor) and anchor.is_internally_valid()
        for anchor in lineage
    ):
        raise ValueError("invalid expected section lineage")
    if lineage:
        if (
            chunk.section_anchor != lineage[-1]
            or chunk.section_title != lineage[-1].title
            or chunk.section_path != " > ".join(anchor.title for anchor in lineage)
        ):
            raise ValueError("inconsistent expected section lineage")
    elif any(
        value is not None
        for value in (chunk.section_anchor, chunk.section_title, chunk.section_path)
    ):
        raise ValueError("inconsistent expected empty section lineage")


def _expected_generation_manifest(
    records: list[dict[str, str]],
    *,
    chunker_sha256: str,
    materializer_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "chunk_materialization_manifest_v1",
        "version": 1,
        "provenance_contract": "s116_section_lineage_v1",
        "provenance_version": 1,
        "chunker_sha256": chunker_sha256,
        "materializer_sha256": materializer_sha256,
        "records": sorted(records, key=lambda item: item["extraction_sha256"]),
    }


def _expected_identity(manifest: dict[str, Any]) -> tuple[str, str]:
    digest = hashlib.sha256(materializer.canonical_json_bytes(manifest)).hexdigest()
    identity = uuid.uuid5(
        materializer.MATERIALIZATION_NAMESPACE,
        "\x00".join(("v1", digest)),
    )
    return digest, str(identity)


def _expected_rows(
    raw: bytes,
    *,
    materialization_id: str,
    chunker_sha256: str,
) -> list[dict[str, Any]]:
    """Independent field reconstruction; never calls the row mapper."""
    record = _strict_json_loads(raw)
    extraction_sha256 = record["sha256"]
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    chunks = chunk_module.chunk_document(record)
    if [chunk.chunk_index for chunk in chunks] != list(range(len(chunks))):
        raise ValueError("non-contiguous expected chunk ordinals")
    expected = []
    transient_to_stable = {}
    for chunk in chunks:
        _validate_expected_chunk(chunk)
        lineage = [_anchor(item) for item in chunk.section_lineage]
        anchor = _anchor(chunk.section_anchor)
        content_sha256 = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        payload = {
            "provenance_version": 1,
            "provenance_contract": "s116_section_lineage_v1",
            "raw_artifact_sha256": raw_sha256,
            "chunker_sha256": chunker_sha256,
            "content_sha256": content_sha256,
            "source_block_start": chunk.source_block_start,
            "source_block_end": chunk.source_block_end,
            "section_anchor": anchor,
            "section_lineage": lineage,
        }
        payload_sha = hashlib.sha256(materializer.canonical_json_bytes(payload)).hexdigest()
        name = "\x00".join((
            "v1",
            materialization_id,
            extraction_sha256,
            str(chunk.chunk_index),
            payload_sha,
        ))
        row_id = str(uuid.uuid5(materializer.ROW_NAMESPACE, name))
        transient_to_stable[chunk.id] = row_id
        expected.append({
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
        })
    for chunk, row in zip(chunks, expected):
        row["duplicate_of"] = (
            None
            if chunk.duplicate_of is None
            else transient_to_stable.get(chunk.duplicate_of, "outside-generation")
        )
    return expected


def _anchor_resolves(anchor: dict[str, Any], blocks: list[object]) -> bool:
    index = anchor.get("source_block_index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(blocks):
        return False
    block = blocks[index]
    try:
        rebuilt = chunk_module.SectionAnchor(
            heading_text=anchor.get("heading_text"),
            title=anchor.get("title"),
            level=anchor.get("level"),
            source_page=anchor.get("source_page"),
            source_block_index=index,
            heading_sha256=anchor.get("heading_sha256"),
        )
        return (
            rebuilt.is_internally_valid()
            and block.kind == "heading"
            and block.source_block_index == index
            and block.text == rebuilt.heading_text
            and block.page == rebuilt.source_page
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _validate_lineage(raw: bytes, rows: list[dict[str, Any]]) -> list[str]:
    record = _strict_json_loads(raw)
    blocks = chunk_module._flatten(record.get("result", {}).get("pages", []))
    failures = []
    for row in rows:
        start = row.get("source_block_start")
        end = row.get("source_block_end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
            or end >= len(blocks)
        ):
            failures.append(f"span:{row.get('chunk_index')}")
            continue
        expected = [_anchor(item) for item in chunk_module._common_lineage(blocks[start : end + 1])]
        lineage = row.get("section_lineage")
        anchor = row.get("section_anchor")
        if lineage != expected:
            failures.append(f"lineage:{row.get('chunk_index')}")
        if not lineage:
            if any(row.get(key) is not None for key in ("section_anchor", "section_title", "section_path")):
                failures.append(f"empty_state:{row.get('chunk_index')}")
            continue
        if anchor != lineage[-1] or not all(_anchor_resolves(item, blocks) for item in lineage):
            failures.append(f"anchor:{row.get('chunk_index')}")
        if row.get("section_title") != lineage[-1]["title"]:
            failures.append(f"title:{row.get('chunk_index')}")
        if row.get("section_path") != " > ".join(item["title"] for item in lineage):
            failures.append(f"path:{row.get('chunk_index')}")
    return failures


def validate_rows_against_raw(
    raw: bytes,
    rows: list[dict[str, Any]],
    *,
    materialization_id: str,
    chunker_sha256: str,
) -> list[str]:
    """Reconstruct expected fields without calling the materializer mapper."""
    failures = []
    if rows != _expected_rows(
        raw,
        materialization_id=materialization_id,
        chunker_sha256=chunker_sha256,
    ):
        failures.append("row_mismatch")
    failures.extend(_validate_lineage(raw, rows))
    return failures


def _independent_manifest_bytes(rows: list[dict[str, Any]]) -> bytes:
    lines = []
    for row in sorted(rows, key=lambda item: (item["extraction_sha256"], item["chunk_index"])):
        core = {field: row[field] for field in materializer.ROW_MANIFEST_FIELDS}
        lines.append(materializer.canonical_json_bytes(core))
    return b"\n".join(lines) + (b"\n" if lines else b"")


def _global_failures(rows: list[dict[str, Any]]) -> list[str]:
    failures = []
    ids = [row["id"] for row in rows]
    ordinals = [(row["materialization_id"], row["extraction_sha256"], row["chunk_index"]) for row in rows]
    if len(ids) != len(set(ids)):
        failures.append("duplicate_ids")
    if len(ordinals) != len(set(ordinals)):
        failures.append("duplicate_ordinals")
    by_id = {row["id"]: row for row in rows}
    for row in rows:
        target_id = row.get("duplicate_of")
        if target_id is None:
            continue
        target = by_id.get(target_id)
        if target is None:
            failures.append("orphan_duplicate")
        elif target_id == row["id"]:
            failures.append("self_duplicate")
        elif target["materialization_id"] != row["materialization_id"]:
            failures.append("cross_generation_duplicate")
        elif target.get("duplicate_of") is not None:
            failures.append("duplicate_chain")
    return sorted(set(failures))


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode("utf-8"))
    return digest.hexdigest()


def build_payload(store: Path, label: str, prereg_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    frozen = prereg["frozen_inputs"]
    chunker_path = ROOT / frozen["chunker"]["path"]
    if _sha(chunker_path) != frozen["chunker"]["sha256"]:
        raise RuntimeError("chunker drift")
    files = sorted(store.glob("*.json"), key=lambda path: path.name)
    source_manifest = _store_manifest(files)
    record_files = [path for path in files if _RECORD_NAME.fullmatch(path.name)]
    non_records = [path.name for path in files if path not in record_files]
    descriptors = []
    raw_by_name = {}
    for path in record_files:
        raw = path.read_bytes()
        record = _strict_json_loads(raw)
        if record.get("sha256") != path.stem:
            raise RuntimeError(f"raw filename/identity drift: {path.name}")
        descriptors.append({
            "extraction_sha256": path.stem,
            "raw_artifact_sha256": hashlib.sha256(raw).hexdigest(),
        })
        raw_by_name[path.name] = raw

    chunker_sha256 = _sha(chunker_path)
    materializer_path = ROOT / "src/reingest/chunk_provenance.py"
    materializer_sha256 = _sha(materializer_path)
    manifest = materializer.generation_manifest(
        descriptors,
        chunker_sha256=chunker_sha256,
        materializer_sha256=materializer_sha256,
    )
    expected_manifest = _expected_generation_manifest(
        descriptors,
        chunker_sha256=chunker_sha256,
        materializer_sha256=materializer_sha256,
    )
    manifest_failures = [] if manifest == expected_manifest else ["generation_manifest_mismatch"]
    manifest_sha256, materialization_id = materializer.materialization_identity(manifest)
    expected_sha256, expected_id = _expected_identity(expected_manifest)
    if (manifest_sha256, materialization_id) != (expected_sha256, expected_id):
        manifest_failures.append("generation_identity_mismatch")

    all_rows = []
    document_streams = {}
    validation_failures = []
    for name, raw in sorted(raw_by_name.items()):
        actual = materializer.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        for failure in validate_rows_against_raw(
            raw,
            actual,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        ):
            validation_failures.append(f"{name}:{failure}")
        all_rows.extend(actual)
        stream = "\n\n".join(row["content"] for row in actual)
        document_streams[name] = hashlib.sha256(stream.encode("utf-8")).hexdigest()

    actual_jsonl = materializer.row_manifest_bytes(all_rows)
    expected_jsonl = _independent_manifest_bytes(all_rows)
    if actual_jsonl != expected_jsonl:
        validation_failures.append("row_manifest_mapper_mismatch")
    stream_manifest = hashlib.sha256()
    for name, digest in sorted(document_streams.items()):
        stream_manifest.update(f"{name}\0{digest}\n".encode("utf-8"))
    global_failures = _global_failures(all_rows)
    validation_failures.extend(global_failures)
    summary = {
        "records_processed": len(record_files),
        "non_record_artifacts": len(non_records),
        "chunks_total": len(all_rows),
        "titled_chunks": sum(1 for row in all_rows if row["section_title"]),
        "untitled_chunks": sum(1 for row in all_rows if not row["section_title"]),
        "validation_failures": len(validation_failures) + len(manifest_failures),
    }
    expected = frozen[f"{label}_store"]
    checks = {
        "source_manifest": source_manifest == expected["manifest_sha256"],
        "record_count": len(record_files) == expected["extraction_records"],
        "chunk_count": len(all_rows) == expected["expected_chunks"],
        "titled_chunk_count": summary["titled_chunks"] == expected["expected_titled_chunks"],
        "zero_validation_failures": not validation_failures and not manifest_failures,
        "non_record_contract": (
            non_records == [expected["expected_non_record_artifact"]]
            if "expected_non_record_artifact" in expected
            else not non_records
        ),
    }
    if "expected_content_stream_manifest_sha256" in expected:
        checks["content_stream_manifest"] = (
            stream_manifest.hexdigest() == expected["expected_content_stream_manifest_sha256"]
        )
    return {
        "instrument": "s117_chunks_v3_local_materialization_v1",
        "label": label,
        "status": "GO" if all(checks.values()) else "NO_GO",
        "runtime": {"python": platform.python_version()},
        "dependencies": {
            "prereg_sha256": _sha(prereg_path),
            "chunker_sha256": chunker_sha256,
            "materializer_sha256": materializer_sha256,
            "validator_sha256": _sha(Path(__file__)),
        },
        "source": {
            "store_slug": store.name,
            "json_files": len(files),
            "manifest_sha256": source_manifest,
            "non_record_artifacts": non_records,
        },
        "generation": {
            "manifest": manifest,
            "manifest_sha256": manifest_sha256,
            "materialization_id": materialization_id,
            "rows_manifest_sha256": hashlib.sha256(actual_jsonl).hexdigest(),
            "rows_manifest_bytes": len(actual_jsonl),
            "content_stream_manifest_sha256": stream_manifest.hexdigest(),
        },
        "summary": summary,
        "checks": checks,
        "failures": sorted(manifest_failures + validation_failures),
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--label", choices=("development", "independent"), required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    first = build_payload(args.store, args.label, args.prereg)
    second = build_payload(args.store, args.label, args.prereg)
    first_bytes = materializer.canonical_json_bytes(first)
    second_bytes = materializer.canonical_json_bytes(second)
    first["determinism"] = {
        "byte_logically_identical": first_bytes == second_bytes,
        "payload_sha256": hashlib.sha256(first_bytes).hexdigest(),
    }
    if not first["determinism"]["byte_logically_identical"]:
        first["status"] = "NO_GO"
    args.out.write_text(
        json.dumps(first, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "status": first["status"],
            "summary": first["summary"],
            "checks": first["checks"],
            "determinism": first["determinism"],
        },
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if first["status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
