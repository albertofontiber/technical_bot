#!/usr/bin/env python3
"""S117 M2: read-only legacy context/embedding reuse audit.

The database phase only captures a deterministic snapshot.  All matching and
cost analysis runs after rollback against that local snapshot.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import struct
from collections import Counter, defaultdict
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Iterable

import yaml
from dotenv import dotenv_values

from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as provenance
from src.reingest import contextualize, embed, language, metadata, sidecar


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m2_legacy_reuse_prereg_v26.yaml"
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.json$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DROP_LANGUAGES = {"fr", "it", "pt", "de"}

DOCUMENT_SQL = """
SELECT id::text, source_pdf_sha256, status
FROM public.documents
ORDER BY id
""".strip()

CHUNKS_SQL = """
SELECT
    id::text,
    document_id::text,
    extraction_sha256,
    chunk_index,
    content,
    context,
    language,
    section_title,
    section_path,
    content_type,
    is_flow_diagram,
    confidence,
    product_model,
    manufacturer,
    distributor,
    protocol,
    doc_type,
    category,
    has_diagram,
    source_file,
    page_number,
    duplicate_of::text,
    parent_id::text,
    ingest_batch,
    (embedding IS NOT NULL) AS embedding_present,
    CASE WHEN embedding IS NULL THEN NULL ELSE vector_dims(embedding)::integer END
        AS embedding_dimensions
FROM public.chunks_v2
ORDER BY id
""".strip()

SESSION_PROOF_SQL = """
SELECT
    current_setting('transaction_read_only'),
    current_setting('transaction_isolation'),
    current_setting('server_version_num')
""".strip()
SET_STATEMENT_TIMEOUT_SQL = "SET LOCAL statement_timeout = %s"
SET_LOCK_TIMEOUT_SQL = "SET LOCAL lock_timeout = %s"

DOCUMENT_COLUMNS = ("id", "source_pdf_sha256", "status")
CHUNK_COLUMNS = (
    "id",
    "document_id",
    "extraction_sha256",
    "chunk_index",
    "content",
    "context",
    "language",
    "section_title",
    "section_path",
    "content_type",
    "is_flow_diagram",
    "confidence",
    "product_model",
    "manufacturer",
    "distributor",
    "protocol",
    "doc_type",
    "category",
    "has_diagram",
    "source_file",
    "page_number",
    "duplicate_of",
    "parent_id",
    "ingest_batch",
    "embedding_present",
    "embedding_dimensions",
)
METADATA_FIELDS = (
    "language",
    "source_file",
    "product_model",
    "manufacturer",
    "distributor",
    "protocol",
    "doc_type",
    "category",
    "content_type",
)
TERMINALS = (
    "policy_excluded_register_only",
    "policy_excluded_language",
    "target_document_unresolved",
    "document_status_excluded",
    "no_extraction_donor",
    "content_miss",
    "structure_miss",
    "metadata_miss",
    "ambiguous_donor",
    "unique_donor_context_missing",
    "unique_donor_embedding_missing_or_wrong_dim",
    "legacy_context_and_embedding_candidate",
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _strict_json(raw: bytes) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    parsed = json.loads(raw, parse_constant=reject)
    if not isinstance(parsed, dict):
        raise ValueError("raw record must be an object")
    return parsed


def _f32_hex(value: Any) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("confidence must be a finite number or null")
    return struct.pack(">f", float(value)).hex()


def _ceil_char4(chars: int) -> int:
    return (chars + 3) // 4


def _manufacturer_config_manifest() -> tuple[int, str]:
    files = sorted((ROOT / "config/manufacturers").glob("*.yaml"), key=lambda p: p.name)
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return len(files), digest.hexdigest()


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{_sha_bytes(raw)}\n".encode("utf-8")
        )
    return digest.hexdigest()


def _verify_portal_sidecars(sidecar_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    root = sidecar_root.resolve()
    digest = hashlib.sha256()
    observed_entries = 0
    for expected in contract["files"]:
        relative = Path(expected["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("unsafe portal sidecar path")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("portal sidecar escapes selected root") from exc
        raw = path.read_bytes()
        def reject_nonfinite(value: str) -> None:
            raise ValueError(f"non-finite JSON constant: {value}")

        parsed = json.loads(raw, parse_constant=reject_nonfinite)
        entries = len(parsed) if isinstance(parsed, list) else None
        sha = _sha_bytes(raw)
        if (len(raw), entries, sha) != (
            expected["bytes"],
            expected["entries"],
            expected["sha256"],
        ):
            raise RuntimeError(f"portal sidecar drift: {expected['path']}")
        digest.update(
            f"{relative.as_posix()}\0{len(raw)}\0{sha}\n".encode("utf-8")
        )
        observed_entries += entries
    if digest.hexdigest() != contract["manifest_sha256"]:
        raise RuntimeError("portal sidecar manifest drift")
    return {
        "files": len(contract["files"]),
        "entries": observed_entries,
        "manifest_sha256": digest.hexdigest(),
    }


@contextmanager
def _bound_sidecar_root(sidecar_root: Path):
    original_root = sidecar._ROOT
    sidecar._ROOT = str(sidecar_root.resolve())
    sidecar.reload()
    try:
        yield
    finally:
        sidecar._ROOT = original_root
        sidecar.reload()


def _canonical_portal_source_path(source_path: str) -> str | None:
    normalized = source_path.replace("\\", "/")
    raw_parts = normalized.split("/")
    portal_directories = {
        f"Manuales_{channel}"
        for channel in (sidecar._config().get("channels", []) or [])
    }
    if not any(part in portal_directories for part in raw_parts):
        return None
    if (
        len(raw_parts) != 2
        or any(part in {"", ".", ".."} for part in raw_parts)
        or raw_parts[0] not in portal_directories
    ):
        raise RuntimeError("non-canonical portal source_path")
    canonical = "/".join(raw_parts)
    if not sidecar.is_portal_channel(canonical):
        raise RuntimeError("portal source_path lost channel identity")
    return canonical


def _version(distribution: str) -> str:
    return importlib.metadata.version(distribution)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_prereg(prereg_path: Path) -> dict[str, Any]:
    child = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    inheritance = child.get("inherits")
    if not inheritance:
        return child
    parent_path = ROOT / inheritance["path"]
    if _sha_file(parent_path) != inheritance["sha256"]:
        raise RuntimeError("inherited preregistration drift")
    parent = _load_prereg(parent_path)
    return _deep_merge(parent, {key: value for key, value in child.items() if key != "inherits"})


def preflight(prereg_path: Path, store: Path, sidecar_root: Path) -> dict[str, Any]:
    prereg = _load_prereg(prereg_path)
    for name, design_value in prereg["design"].items():
        if name.endswith("_sha256"):
            continue
        design_path = ROOT / design_value
        if _sha_file(design_path) != prereg["design"][f"{name}_sha256"]:
            raise RuntimeError(f"M2 {name} design drift")
    assert_readonly_sql_contract()
    expected_runtime = prereg["runtime"]
    observed_runtime = {
        "python": platform.python_version(),
        "lingua-language-detector": _version("lingua-language-detector"),
        "psycopg2-binary": _version("psycopg2-binary"),
        "PyYAML": _version("PyYAML"),
    }
    if observed_runtime != expected_runtime:
        raise RuntimeError("runtime drift before database access")

    for item in prereg["frozen_inputs"].values():
        if not isinstance(item, dict) or "path" not in item:
            continue
        path = ROOT / item["path"]
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"frozen input drift: {item['path']}")

    config_count, config_sha = _manufacturer_config_manifest()
    expected_config = prereg["frozen_inputs"]["manufacturer_config_manifest"]
    if (config_count, config_sha) != (
        expected_config["yaml_files"],
        expected_config["sha256"],
    ):
        raise RuntimeError("manufacturer config drift")

    files = sorted(store.glob("*.json"), key=lambda path: path.name)
    records = [path for path in files if _RECORD_NAME.fullmatch(path.name)]
    non_records = [path.name for path in files if path not in records]
    expected_store = prereg["frozen_inputs"]["raw_store"]
    if (
        len(files) != expected_store["json_files"]
        or len(records) != expected_store["extraction_records"]
        or _store_manifest(files) != expected_store["manifest_sha256"]
        or non_records != [expected_store["expected_non_record_artifact"]]
    ):
        raise RuntimeError("raw store drift")

    effective = {
        "contextualizer_model": contextualize._MODEL,
        "max_doc_chars": contextualize._MAX_DOC_CHARS,
        "max_chunk_chars": contextualize._MAX_CHUNK_CHARS,
        "max_output_tokens": 200,
        "embedding_provider": embed.EMBED_PROVIDER,
        "embedding_model": embed.EMBED_MODEL,
        "embedding_input_type": "document",
        "embedding_dimensions": embed.EMBED_DIMENSIONS,
        "max_embedding_chars": embed._MAX_EMBED_CHARS,
    }
    if effective != prereg["effective_enrichment_contract"]:
        raise RuntimeError("effective enrichment contract drift")
    sidecar_receipt = _verify_portal_sidecars(
        sidecar_root,
        prereg["frozen_inputs"]["portal_sidecars"],
    )
    return {
        "prereg": prereg,
        "runtime": observed_runtime,
        "record_files": records,
        "raw_store_manifest_sha256": expected_store["manifest_sha256"],
        "effective_enrichment_contract": effective,
        "portal_sidecar_receipt": sidecar_receipt,
    }


def assert_readonly_sql_contract() -> None:
    statements = (
        DOCUMENT_SQL,
        CHUNKS_SQL,
        SESSION_PROOF_SQL,
        SET_STATEMENT_TIMEOUT_SQL,
        SET_LOCK_TIMEOUT_SQL,
    )
    for statement in statements:
        prefix = statement.lstrip().split(None, 1)[0].upper()
        if prefix not in {"SELECT", "SET"}:
            raise RuntimeError(f"non-read-only SQL prefix: {prefix}")
        if re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE|ALTER|DROP|CREATE|CALL)\b", statement, re.I):
            raise RuntimeError("mutating SQL in M2 contract")
    if re.search(r"embedding\s*::\s*text|SELECT\s+[^;]*\bembedding\s*(,|FROM)", CHUNKS_SQL, re.I | re.S):
        raise RuntimeError("vector payload selected by M2")


def _normalized_document(values: tuple[Any, ...]) -> dict[str, Any]:
    row = dict(zip(DOCUMENT_COLUMNS, values, strict=True))
    return {"kind": "document", **row}


def _normalized_chunk(values: tuple[Any, ...]) -> dict[str, Any]:
    row = dict(zip(CHUNK_COLUMNS, values, strict=True))
    row["confidence_f32"] = _f32_hex(row.pop("confidence"))
    return {"kind": "chunk", **row}


def _write_snapshot_lines(
    output: Path,
    header: dict[str, Any],
    documents: Iterable[dict[str, Any]],
    chunks: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_digest = hashlib.sha256()
    counts = Counter()
    with output.open("wb") as raw_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as gz:
            for row in ({"kind": "header", **header}, *documents, *chunks):
                line = canonical_json_bytes(row) + b"\n"
                raw_digest.update(line)
                gz.write(line)
                counts[row["kind"]] += 1
    return {
        "canonical_jsonl_sha256": raw_digest.hexdigest(),
        "gzip_sha256": _sha_file(output),
        "gzip_bytes": output.stat().st_size,
        "documents": counts["document"],
        "chunks": counts["chunk"],
    }


def capture_remote_snapshot(
    database_url: str,
    snapshot_path: Path,
    prereg: dict[str, Any],
) -> dict[str, Any]:
    """Capture a consistent snapshot and rollback before returning."""
    import psycopg2

    connection = None
    rolled_back = False
    try:
        connection = psycopg2.connect(
            database_url,
            connect_timeout=10,
            application_name="technical_bot_s117_m2_readonly",
        )
        connection.set_session(
            isolation_level="REPEATABLE READ",
            readonly=True,
            autocommit=False,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                SET_STATEMENT_TIMEOUT_SQL,
                (prereg["remote_contract"]["statement_timeout_ms"],),
            )
            cursor.execute(
                SET_LOCK_TIMEOUT_SQL,
                (prereg["remote_contract"]["lock_timeout_ms"],),
            )
            cursor.execute(SESSION_PROOF_SQL)
            read_only, isolation, server_version = cursor.fetchone()
        if read_only != "on" or isolation != "repeatable read":
            raise RuntimeError("database transaction is not repeatable-read read-only")

        header = {
            "schema": "s117_m2_remote_snapshot_v1",
            "transaction_read_only": read_only,
            "transaction_isolation": isolation,
            "server_version_num": server_version,
            "vector_payloads": 0,
        }
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        raw_digest = hashlib.sha256()
        counts = Counter()

        def write_row(handle: gzip.GzipFile, row: dict[str, Any]) -> None:
            line = canonical_json_bytes(row) + b"\n"
            raw_digest.update(line)
            handle.write(line)
            counts[row["kind"]] += 1

        try:
            with snapshot_path.open("wb") as raw_file:
                with gzip.GzipFile(
                    filename="", mode="wb", fileobj=raw_file, mtime=0
                ) as gz:
                    write_row(gz, {"kind": "header", **header})
                    with connection.cursor(name="s117_m2_documents") as cursor:
                        cursor.itersize = prereg["remote_contract"]["cursor_batch_rows"]
                        cursor.execute(DOCUMENT_SQL)
                        for values in cursor:
                            write_row(gz, _normalized_document(values))
                    with connection.cursor(name="s117_m2_chunks") as cursor:
                        cursor.itersize = prereg["remote_contract"]["cursor_batch_rows"]
                        cursor.execute(CHUNKS_SQL)
                        for values in cursor:
                            write_row(gz, _normalized_chunk(values))
        except Exception:
            snapshot_path.unlink(missing_ok=True)
            raise
        connection.rollback()
        rolled_back = True
        receipt = {
            "canonical_jsonl_sha256": raw_digest.hexdigest(),
            "gzip_sha256": _sha_file(snapshot_path),
            "gzip_bytes": snapshot_path.stat().st_size,
            "documents": counts["document"],
            "chunks": counts["chunk"],
        }
        return {
            **receipt,
            "transaction_read_only": read_only,
            "transaction_isolation": isolation,
            "server_version_num": server_version,
            "rollback_completed_before_analysis": True,
            "database_writes": 0,
            "vector_payloads": 0,
        }
    finally:
        if connection is not None:
            if not rolled_back:
                try:
                    connection.rollback()
                except Exception:
                    pass
            connection.close()


def read_snapshot(snapshot_path: Path) -> tuple[dict[str, Any], list[dict], list[dict], dict]:
    header: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    with gzip.open(snapshot_path, "rb") as handle:
        for raw_line in handle:
            digest.update(raw_line)
            row = json.loads(
                raw_line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite snapshot constant: {value}")
                ),
            )
            kind = row.pop("kind")
            if kind == "header":
                if header is not None:
                    raise ValueError("duplicate snapshot header")
                header = row
            elif kind == "document":
                documents.append(row)
            elif kind == "chunk":
                chunks.append(row)
            else:
                raise ValueError(f"unknown snapshot row kind: {kind}")
    if header is None:
        raise ValueError("snapshot header missing")
    receipt = {
        "canonical_jsonl_sha256": digest.hexdigest(),
        "gzip_sha256": _sha_file(snapshot_path),
        "gzip_bytes": snapshot_path.stat().st_size,
        "documents": len(documents),
        "chunks": len(chunks),
    }
    return header, documents, chunks, receipt


def _context_receipt(record: dict[str, Any], content: str) -> dict[str, Any]:
    document = contextualize.full_document_text(record)[: contextualize._MAX_DOC_CHARS]
    document_block = f"<document>\n{document}\n</document>"
    instruction = contextualize._INSTRUCTION.format(
        chunk=content[: contextualize._MAX_CHUNK_CHARS]
    )
    components = {
        "model": contextualize._MODEL,
        "max_tokens": 200,
        "document_text_sha256": _sha_bytes(document_block.encode("utf-8")),
        "document_text_chars": len(document_block),
        "instruction_sha256": _sha_bytes(instruction.encode("utf-8")),
        "instruction_chars": len(instruction),
    }
    return {
        "context_input_sha256": _sha_bytes(canonical_json_bytes(components)),
        "context_input_chars": len(document_block) + len(instruction),
        "context_document_chars": len(document_block),
        "context_instruction_chars": len(instruction),
    }


def _local_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "id",
            "extraction_sha256",
            "chunk_index",
            "content_sha256",
            "section_title",
            "section_path",
            "page_number",
            "is_flow_diagram",
            "has_diagram",
            "confidence_f32",
            "preterminal",
            "diagnostic_v2_index",
            *METADATA_FIELDS,
            "context_input_sha256",
        )
    }


def build_local_population(
    record_files: list[Path],
    s117_result_path: Path,
    chunker_sha256: str,
    sidecar_root: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    binding = _bound_sidecar_root(sidecar_root) if sidecar_root else nullcontext()
    with binding:
        return _build_local_population_bound(
            record_files,
            s117_result_path,
            chunker_sha256,
        )


def _build_local_population_bound(
    record_files: list[Path],
    s117_result_path: Path,
    chunker_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    s117_result = json.loads(s117_result_path.read_text(encoding="utf-8"))
    materialization_id = s117_result["generation"]["materialization_id"]
    local_rows: list[dict[str, Any]] = []
    portal_paths = 0
    resolved_portal_paths = 0
    missing_portal_paths = 0
    per_document_counts: dict[str, int] = {}

    for path in record_files:
        raw = path.read_bytes()
        record = _strict_json(raw)
        extraction_sha = record.get("sha256")
        if extraction_sha != path.stem:
            raise ValueError("raw identity drift")
        source_path = record.get("source_path") or ""
        portal_source_path = _canonical_portal_source_path(source_path)
        metadata_source_path = portal_source_path or source_path
        if portal_source_path is not None:
            portal_paths += 1
            if sidecar.lookup(portal_source_path) is None:
                missing_portal_paths += 1
            else:
                resolved_portal_paths += 1

        structural = provenance.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        profile = language.profile_document(record)
        kept: list[Any] = []
        kept_original_indexes: list[int] = []
        dropped_indexes: set[int] = set()
        if profile.verdict != "register_only":
            chunks = chunk_module.chunk_document(record)
            if len(structural) != len(chunks):
                raise ValueError("materializer/chunker cardinality mismatch")
            for structural_row, chunk in zip(structural, chunks, strict=True):
                if structural_row["content"] != chunk.content:
                    raise ValueError("materializer/chunker content mismatch")
            for original_index, chunk in enumerate(chunks):
                chunk.language = language.detect_language(chunk.content)
                if chunk.language in _DROP_LANGUAGES:
                    dropped_indexes.add(original_index)
                    continue
                if chunk.language == "unknown":
                    chunk.language = profile.dominant
                kept.append(chunk)
                kept_original_indexes.append(original_index)
            for diagnostic_index, chunk in enumerate(kept):
                chunk.chunk_index = diagnostic_index
            sample = " ".join(chunk.content for chunk in kept[:4])
            document_metadata = metadata.detect_document_metadata(metadata_source_path, sample)
            metadata.apply_metadata(kept, document_metadata)

        kept_by_original = dict(zip(kept_original_indexes, kept, strict=True))
        diagnostic_by_original = {
            original: diagnostic for diagnostic, original in enumerate(kept_original_indexes)
        }
        for original_index, structural_row in enumerate(structural):
            row = dict(structural_row)
            row["content_sha256"] = _sha_bytes(row["content"].encode("utf-8"))
            row["confidence_f32"] = _f32_hex(row["confidence"])
            row["diagnostic_v2_index"] = diagnostic_by_original.get(original_index)
            if profile.verdict == "register_only":
                row["preterminal"] = "policy_excluded_register_only"
            elif original_index in dropped_indexes:
                row["preterminal"] = "policy_excluded_language"
            else:
                row["preterminal"] = None
                enriched = kept_by_original[original_index]
                for field in METADATA_FIELDS:
                    row[field] = getattr(enriched, field)
                row.update(_context_receipt(record, row["content"]))
            local_rows.append(row)
        per_document_counts[extraction_sha] = len(structural)

    manifest = hashlib.sha256()
    for row in sorted(local_rows, key=lambda item: (item["extraction_sha256"], item["chunk_index"])):
        manifest.update(canonical_json_bytes(_local_manifest_row(row)) + b"\n")
    return local_rows, {
        "rows": len(local_rows),
        "documents": len(record_files),
        "portal_source_paths": portal_paths,
        "resolved_portal_source_paths": resolved_portal_paths,
        "missing_portal_source_paths": missing_portal_paths,
        "manifest_sha256": manifest.hexdigest(),
        "per_document_count_manifest_sha256": _sha_bytes(canonical_json_bytes(per_document_counts)),
    }


def _structure_matches(local: dict[str, Any], donor: dict[str, Any]) -> bool:
    return all(
        local.get(field) == donor.get(field)
        for field in (
            "section_title",
            "section_path",
            "page_number",
            "is_flow_diagram",
            "has_diagram",
            "confidence_f32",
        )
    )


def _metadata_matches(local: dict[str, Any], donor: dict[str, Any]) -> bool:
    return all(local.get(field) == donor.get(field) for field in METADATA_FIELDS)


def _embedding_receipt(context: str, content: str) -> dict[str, Any]:
    text = f"{context}\n\n{content}"[: embed._MAX_EMBED_CHARS]
    envelope = {
        "provider": embed.EMBED_PROVIDER,
        "model": embed.EMBED_MODEL,
        "input_type": "document",
        "dimensions": embed.EMBED_DIMENSIONS,
        "max_chars": embed._MAX_EMBED_CHARS,
        "text_sha256": _sha_bytes(text.encode("utf-8")),
    }
    return {
        "embedding_input_sha256": _sha_bytes(canonical_json_bytes(envelope)),
        "embedding_input_chars": len(text),
    }


def _workload(
    active_rows: list[dict[str, Any]],
    context_reuse: dict[str, dict[str, Any]],
    embedding_reuse_ids: set[str],
) -> dict[str, Any]:
    context_needed = [row for row in active_rows if row["id"] not in context_reuse]
    context_chars = sum(row["context_input_chars"] for row in context_needed)
    context_tokens = sum(_ceil_char4(row["context_input_chars"]) for row in context_needed)
    document_calls: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in context_needed:
        document_calls[row["extraction_sha256"]].append(row)
    cache_write_chars = 0
    cache_read_chars = 0
    instruction_chars = 0
    for rows in document_calls.values():
        cache_write_chars += rows[0]["context_document_chars"]
        cache_read_chars += rows[0]["context_document_chars"] * (len(rows) - 1)
        instruction_chars += sum(row["context_instruction_chars"] for row in rows)

    embedding_needed = [row for row in active_rows if row["id"] not in embedding_reuse_ids]
    exact_embedding_chars = 0
    generated_context_rows = 0
    generated_context_lower = 0
    for row in embedding_needed:
        donor = context_reuse.get(row["id"])
        if donor is not None:
            exact_embedding_chars += _embedding_receipt(donor["context"], row["content"])[
                "embedding_input_chars"
            ]
        else:
            generated_context_rows += 1
            generated_context_lower += min(len(row["content"]), embed._MAX_EMBED_CHARS)
    generated_context_upper = generated_context_rows * embed._MAX_EMBED_CHARS
    return {
        "productive_rows": len(active_rows),
        "context_calls": len(context_needed),
        "context_input_chars": context_chars,
        "context_input_tokens_char4_proxy": context_tokens,
        "context_output_tokens_ceiling": len(context_needed) * 200,
        "context_documents": len(document_calls),
        "prompt_cache_write_document_chars": cache_write_chars,
        "prompt_cache_read_document_chars": cache_read_chars,
        "uncached_instruction_chars": instruction_chars,
        "embedding_calls": len(embedding_needed),
        "embedding_input_chars_exact_when_context_reused": exact_embedding_chars,
        "embedding_rows_with_generated_context": generated_context_rows,
        "embedding_input_chars_lower_bound_when_context_generated": generated_context_lower,
        "embedding_input_chars_upper_bound_when_context_generated": generated_context_upper,
        "embedding_input_tokens_char4_proxy_lower_bound": (
            _ceil_char4(exact_embedding_chars) + _ceil_char4(generated_context_lower)
        ),
        "embedding_input_tokens_char4_proxy_upper_bound": (
            _ceil_char4(exact_embedding_chars) + _ceil_char4(generated_context_upper)
        ),
        "currency_estimate": None,
    }


def analyze_snapshot(
    snapshot_path: Path,
    local_rows: list[dict[str, Any]],
    local_receipt: dict[str, Any],
) -> dict[str, Any]:
    header, documents, remote_chunks, snapshot_receipt = read_snapshot(snapshot_path)
    if (
        header.get("transaction_read_only") != "on"
        or header.get("transaction_isolation") != "repeatable read"
        or header.get("vector_payloads") != 0
    ):
        raise ValueError("snapshot lacks read-only transaction proof")

    docs_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in documents:
        docs_by_sha[row.get("source_pdf_sha256")].append(row)

    base_chunks = [row for row in remote_chunks if row.get("parent_id") is None]
    surrogates = len(remote_chunks) - len(base_chunks)
    chunks_by_extraction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in base_chunks:
        chunks_by_extraction[row.get("extraction_sha256")].append(row)

    terminals = Counter()
    funnel = Counter(total_local=len(local_rows))
    document_statuses = Counter()
    manufacturer_terminals: dict[str, Counter] = defaultdict(Counter)
    document_terminals: dict[str, Counter] = defaultdict(Counter)
    donor_document_binding_drift = 0
    donor_duplicates = 0
    active_rows: list[dict[str, Any]] = []
    strict_context_reuse: dict[str, dict[str, Any]] = {}
    strict_embedding_reuse: set[str] = set()
    ceiling_context_reuse: dict[str, dict[str, Any]] = {}
    ceiling_embedding_reuse: set[str] = set()
    strict_context_manifest = hashlib.sha256()
    strict_embedding_manifest = hashlib.sha256()

    def finish(row: dict[str, Any], terminal: str) -> None:
        terminals[terminal] += 1
        manufacturer = row.get("manufacturer") or "__unresolved__"
        manufacturer_terminals[manufacturer][terminal] += 1
        document_terminals[row["extraction_sha256"]][terminal] += 1

    for local in local_rows:
        if local.get("preterminal"):
            finish(local, local["preterminal"])
            continue
        funnel["policy_eligible"] += 1
        matching_docs = docs_by_sha.get(local["extraction_sha256"], [])
        if (
            len(matching_docs) != 1
            or not _SHA256.fullmatch(matching_docs[0].get("source_pdf_sha256") or "")
        ):
            finish(local, "target_document_unresolved")
            continue
        target_doc = matching_docs[0]
        funnel["target_document_resolved"] += 1
        document_statuses[target_doc.get("status") or "__null__"] += 1
        if target_doc.get("status") != "active":
            finish(local, "document_status_excluded")
            continue
        funnel["target_document_active"] += 1
        active_rows.append(local)

        extraction_candidates = chunks_by_extraction.get(local["extraction_sha256"], [])
        if not extraction_candidates:
            finish(local, "no_extraction_donor")
            continue
        funnel["extraction_hit"] += 1
        content_candidates = [
            donor for donor in extraction_candidates if donor.get("content") == local["content"]
        ]
        if not content_candidates:
            finish(local, "content_miss")
            continue
        funnel["content_hit"] += 1
        structure_candidates = [
            donor for donor in content_candidates if _structure_matches(local, donor)
        ]
        if not structure_candidates:
            finish(local, "structure_miss")
            continue
        funnel["structure_hit"] += 1

        if len(structure_candidates) == 1:
            ceiling_donor = structure_candidates[0]
            if isinstance(ceiling_donor.get("context"), str) and ceiling_donor["context"].strip():
                ceiling_context_reuse[local["id"]] = ceiling_donor
                if (
                    ceiling_donor.get("embedding_present") is True
                    and ceiling_donor.get("embedding_dimensions") == embed.EMBED_DIMENSIONS
                ):
                    ceiling_embedding_reuse.add(local["id"])

        metadata_candidates = [
            donor for donor in structure_candidates if _metadata_matches(local, donor)
        ]
        if not metadata_candidates:
            finish(local, "metadata_miss")
            continue
        funnel["metadata_hit"] += 1
        if len(metadata_candidates) != 1:
            finish(local, "ambiguous_donor")
            continue
        funnel["unique_donor"] += 1
        donor = metadata_candidates[0]
        if donor.get("document_id") != target_doc["id"]:
            donor_document_binding_drift += 1
        if donor.get("duplicate_of") is not None:
            donor_duplicates += 1
        context = donor.get("context")
        if not isinstance(context, str) or not context.strip():
            finish(local, "unique_donor_context_missing")
            continue
        funnel["context_reuse_candidate"] += 1
        strict_context_reuse[local["id"]] = donor
        context_receipt = {
            "id": local["id"],
            "context_sha256": _sha_bytes(context.encode("utf-8")),
            "context_input_sha256": local["context_input_sha256"],
        }
        strict_context_manifest.update(canonical_json_bytes(context_receipt) + b"\n")
        if (
            donor.get("embedding_present") is not True
            or donor.get("embedding_dimensions") != embed.EMBED_DIMENSIONS
        ):
            finish(local, "unique_donor_embedding_missing_or_wrong_dim")
            continue
        funnel["embedding_reuse_candidate"] += 1
        strict_embedding_reuse.add(local["id"])
        embedding_receipt = {
            "id": local["id"],
            **_embedding_receipt(context, local["content"]),
        }
        strict_embedding_manifest.update(canonical_json_bytes(embedding_receipt) + b"\n")
        finish(local, "legacy_context_and_embedding_candidate")

    terminal_total = sum(terminals.values())
    monotonic_keys = (
        "total_local",
        "policy_eligible",
        "target_document_resolved",
        "target_document_active",
        "extraction_hit",
        "content_hit",
        "structure_hit",
        "metadata_hit",
        "unique_donor",
        "context_reuse_candidate",
        "embedding_reuse_candidate",
    )
    monotonic_values = [funnel[key] for key in monotonic_keys]
    monotonic = all(a >= b for a, b in zip(monotonic_values, monotonic_values[1:]))
    taxonomy_closed = terminal_total == len(local_rows) and set(terminals) <= set(TERMINALS)

    remote_manifest = hashlib.sha256()
    for row in remote_chunks:
        compact = {
            "id": row["id"],
            "extraction_sha256": row["extraction_sha256"],
            "content_sha256": _sha_bytes((row.get("content") or "").encode("utf-8")),
            "context_sha256": (
                _sha_bytes(row["context"].encode("utf-8"))
                if isinstance(row.get("context"), str)
                else None
            ),
            "parent_id": row.get("parent_id"),
            "duplicate_of": row.get("duplicate_of"),
            "embedding_present": row.get("embedding_present"),
            "embedding_dimensions": row.get("embedding_dimensions"),
        }
        remote_manifest.update(canonical_json_bytes(compact) + b"\n")

    top_documents = sorted(
        (
            {"extraction_sha256": sha, "terminals": dict(sorted(counts.items()))}
            for sha, counts in document_terminals.items()
        ),
        key=lambda item: (-sum(item["terminals"].values()), item["extraction_sha256"]),
    )[:30]
    return {
        "instrument": "s117_m2_legacy_reuse_analysis_v1",
        "status": "GO" if taxonomy_closed and monotonic else "NO_GO",
        "snapshot": {
            **snapshot_receipt,
            "transaction_read_only": header["transaction_read_only"],
            "transaction_isolation": header["transaction_isolation"],
            "server_version_num": header["server_version_num"],
            "remote_semantic_manifest_sha256": remote_manifest.hexdigest(),
            "base_chunks": len(base_chunks),
            "surrogate_chunks": surrogates,
        },
        "local": local_receipt,
        "funnel": {key: funnel[key] for key in monotonic_keys},
        "terminals": {key: terminals[key] for key in TERMINALS},
        "document_status_rows": dict(sorted(document_statuses.items())),
        "diagnostics": {
            "donor_document_binding_drift": donor_document_binding_drift,
            "unique_donors_marked_duplicate": donor_duplicates,
            "by_manufacturer": {
                manufacturer: dict(sorted(counts.items()))
                for manufacturer, counts in sorted(manufacturer_terminals.items())
            },
            "top_documents": top_documents,
        },
        "reuse_receipts": {
            "strict_context_candidates": len(strict_context_reuse),
            "strict_context_manifest_sha256": strict_context_manifest.hexdigest(),
            "strict_embedding_candidates": len(strict_embedding_reuse),
            "strict_embedding_input_manifest_sha256": strict_embedding_manifest.hexdigest(),
            "vector_sha256": None,
            "historical_model_receipt": None,
            "claim": "candidate_only_legacy_v2_reuse",
        },
        "workloads": {
            "strict": _workload(active_rows, strict_context_reuse, strict_embedding_reuse),
            "structural_ceiling_non_authorizing": _workload(
                active_rows,
                ceiling_context_reuse,
                ceiling_embedding_reuse,
            ),
        },
        "checks": {
            "transaction_read_only": header["transaction_read_only"] == "on",
            "transaction_repeatable_read": header["transaction_isolation"] == "repeatable read",
            "zero_vector_payloads": header["vector_payloads"] == 0,
            "portal_sidecars_complete": (
                local_receipt["resolved_portal_source_paths"]
                == local_receipt["portal_source_paths"]
                and local_receipt["missing_portal_source_paths"] == 0
            ),
            "terminal_taxonomy_closed": taxonomy_closed,
            "funnel_monotonic": monotonic,
            "currency_estimates_absent": True,
        },
        "cost": {
            "model_calls": 0,
            "database_reads": 1,
            "database_writes": 0,
            "vector_payloads": 0,
        },
    }


def _load_database_url(env_file: Path) -> str:
    values = dotenv_values(env_file)
    database_url = values.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from the selected env file")
    return str(database_url)


def _assert_seeded_replay_cli(prereg: dict[str, Any], args: Any) -> None:
    if "seeded_replay_gate" not in prereg:
        return
    if not args.replay:
        raise RuntimeError("seeded M2 contract is replay-only")
    if args.env_file is not None:
        raise RuntimeError("seeded M2 replay forbids --env-file")
    expected = (ROOT / prereg["frozen_inputs"]["remote_snapshot"]["path"]).resolve()
    if args.snapshot.resolve() != expected:
        raise RuntimeError("seeded M2 replay snapshot path mismatch")


def _assert_consumed_snapshot(
    prereg: dict[str, Any],
    snapshot_receipt: dict[str, Any],
) -> None:
    if "seeded_replay_gate" not in prereg:
        return
    expected = prereg["frozen_inputs"]["remote_snapshot"]
    if (
        snapshot_receipt["gzip_sha256"] != expected["sha256"]
        or snapshot_receipt["canonical_jsonl_sha256"]
        != expected["canonical_jsonl_sha256"]
    ):
        raise RuntimeError("consumed snapshot receipt drift")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    selected_prereg = _load_prereg(args.prereg)
    _assert_seeded_replay_cli(selected_prereg, args)
    state = preflight(args.prereg, args.store, args.sidecar_root)
    s117_result_path = (
        ROOT / state["prereg"]["frozen_inputs"]["s117_development_result"]["path"]
    )
    s117_result = json.loads(s117_result_path.read_text(encoding="utf-8"))
    local_rows, local_receipt = build_local_population(
        state["record_files"],
        s117_result_path,
        state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
        args.sidecar_root,
    )
    expected_store = state["prereg"]["frozen_inputs"]["raw_store"]
    expected_sidecars = state["prereg"]["frozen_inputs"]["portal_sidecars"]
    if (
        local_receipt["portal_source_paths"]
        != expected_store["expected_portal_source_paths"]
        or local_receipt["resolved_portal_source_paths"]
        != expected_sidecars["expected_resolved_portal_paths"]
        or local_receipt["missing_portal_source_paths"]
        != expected_sidecars["expected_missing_portal_paths"]
    ):
        raise RuntimeError("portal sidecar population drift")
    if (
        local_receipt["rows"] != s117_result["summary"]["chunks_total"]
        or local_receipt["documents"] != s117_result["summary"]["records_processed"]
    ):
        raise RuntimeError("local S117 population drift")

    capture_receipt = None
    if not args.replay:
        if args.env_file is None:
            raise RuntimeError("--env-file is required for capture")
        database_url = _load_database_url(args.env_file)
        capture_receipt = capture_remote_snapshot(
            database_url,
            args.snapshot,
            state["prereg"],
        )
        if not capture_receipt["rollback_completed_before_analysis"]:
            raise RuntimeError("rollback proof missing")
    first = analyze_snapshot(args.snapshot, local_rows, local_receipt)
    second = analyze_snapshot(args.snapshot, local_rows, local_receipt)
    _assert_consumed_snapshot(state["prereg"], first["snapshot"])
    _assert_consumed_snapshot(state["prereg"], second["snapshot"])
    first_bytes = canonical_json_bytes(first)
    second_bytes = canonical_json_bytes(second)
    first["determinism"] = {
        "byte_logically_identical": first_bytes == second_bytes,
        "payload_sha256": _sha_bytes(first_bytes),
    }
    if not first["determinism"]["byte_logically_identical"]:
        first["status"] = "NO_GO"
    if capture_receipt is not None:
        first["capture_receipt"] = capture_receipt
    first["dependencies"] = {
        "prereg_sha256": _sha_file(args.prereg),
        "analyzer_sha256": _sha_file(Path(__file__)),
        "runtime": state["runtime"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(first, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": first["status"],
        "funnel": first["funnel"],
        "terminals": first["terminals"],
        "workloads": first["workloads"],
        "checks": first["checks"],
        "determinism": first["determinism"],
    }, ensure_ascii=False, indent=2))
    return 0 if first["status"] == "GO" and all(first["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
