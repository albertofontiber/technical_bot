#!/usr/bin/env python3
"""Pure, offline validation primitives for the S117 M2.8 candidate."""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from typing import Any

from scripts import s117_materialize_chunks_v3_local as row_validator
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as provenance


PROJECTION_SCHEMA = "s117_m28_candidate_treatment_projection_v1"
PROJECTION_FIELDS = (
    "schema",
    "extraction_sha256",
    "raw_artifact_sha256",
    "raw_blocks",
    "rows",
    "covered_blocks",
    "missing_block_indexes",
    "surface_sha256",
    "surface_equal_raw",
    "fingerprint_multiset_sha256",
    "coverage_gain_block_indexes",
    "coverage_regression_block_indexes",
    "changed",
)
OUTPUT_TOP_LEVEL = {
    "instrument",
    "schema_version",
    "status",
    "loadable",
    "authority",
    "dependencies",
    "source",
    "generation",
    "population",
    "manifests",
    "checks",
    "failures",
    "cost",
    "authorization",
}
DEPENDENCY_KEYS = {
    "prereg_sha256",
    "permit_sha256",
    "runner_sha256",
    "runner_tests_sha256",
    "design_v2_sha256",
    "design_v3_sha256",
    "baseline_receipt_sha256",
    "m27c_prereg_sha256",
    "m27c_gate_sha256",
    "m27c_seed1_sha256",
    "m27c_seed2_sha256",
    "m27c_probe_base_sha256",
    "m27c_token_validator_sha256",
    "m27c_surface_helper_sha256",
    "compact100_sha256",
    "m28_freeze_sha256",
    "m28_gate_sha256",
    "chunker_sha256",
    "materializer_sha256",
    "row_validator_sha256",
    "candidate_validator_sha256",
    "src_init_sha256",
    "reingest_init_sha256",
}
SOURCE_KEYS = {
    "store_slug",
    "json_files",
    "records",
    "non_record_artifacts",
    "manifest_sha256",
}
GENERATION_KEYS = {
    "manifest_schema",
    "manifest_sha256",
    "materialization_id",
    "rows_manifest_sha256",
    "rows_manifest_bytes",
}
POPULATION_KEYS = {
    "documents",
    "raw_blocks",
    "rows",
    "titled_rows",
    "untitled_rows",
    "covered_blocks",
    "missing_blocks",
    "coverage_gain_blocks",
    "coverage_regression_blocks",
    "changed_documents",
    "unchanged_documents",
    "delta_unchanged_rows",
    "delta_removed_rows",
    "delta_added_rows",
    "delta_overlap_modified_rows",
    "delta_pure_added_rows",
    "validation_failures",
}
MANIFEST_KEYS = {
    "candidate_projection_sha256",
    "candidate_document_receipts_sha256",
    "candidate_row_ids_sha256",
    "coverage_gain_identities_sha256",
}
CHECK_KEYS = {
    "contract_integrity",
    "source_exact",
    "generation_identity_exact",
    "candidate_identity_new",
    "row_mapping_and_identity_exact",
    "global_invariants_exact",
    "raw_token_intervals_exact",
    "treatment_projection_exact",
    "population_exact",
    "output_schema_exact",
    "external_calls_blocked",
}
COST_KEYS = {
    "model_calls",
    "network_calls",
    "database_reads",
    "database_writes",
    "external_calls_blocked",
}
AUTHORIZATION_KEYS = {
    "database",
    "network",
    "models",
    "retrieval",
    "context_generation",
    "embeddings",
    "load",
    "serving",
    "deploy",
    "facts_moved_to_ok",
    "M3",
}
FAILURE_CODES = {
    "contract_integrity",
    "source_drift",
    "generation_identity_drift",
    "row_validation_failure",
    "global_invariant_failure",
    "raw_token_interval_failure",
    "treatment_projection_drift",
    "population_drift",
    "output_schema_failure",
    "external_call_attempted",
    "internal_failure",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def surface(text: str) -> str:
    return " ".join(text.split())


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON float")
    return parsed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def strict_json_loads(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8")
    value = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )
    if not isinstance(value, dict):
        raise ValueError("raw extraction record must be an object")
    return value


def row_core_from_chunk(chunk: Any) -> dict[str, Any]:
    return {
        "ordinal": chunk.chunk_index,
        "content": chunk.content,
        "source_block_start": chunk.source_block_start,
        "source_block_end": chunk.source_block_end,
        "section_anchor": provenance.anchor_to_dict(chunk.section_anchor),
        "section_lineage": [
            provenance.anchor_to_dict(anchor) for anchor in chunk.section_lineage
        ],
        "section_title": chunk.section_title,
        "section_path": chunk.section_path,
        "page_number": chunk.page_number,
        "is_flow_diagram": bool(chunk.is_flow_diagram),
        "has_diagram": bool(chunk.has_diagram),
        "confidence": chunk.confidence,
    }


def fingerprinted(core: dict[str, Any]) -> dict[str, Any]:
    fingerprint_core = {
        "content_surface_sha256": sha256_bytes(
            surface(core["content"]).encode("utf-8")
        ),
        "source_block_start": core["source_block_start"],
        "source_block_end": core["source_block_end"],
        "section_lineage": core["section_lineage"],
        "section_title": core["section_title"],
        "section_path": core["section_path"],
        "page_number": core["page_number"],
        "is_flow_diagram": core["is_flow_diagram"],
        "has_diagram": core["has_diagram"],
        "confidence": core["confidence"],
    }
    return {
        **core,
        "content_sha256": sha256_bytes(core["content"].encode("utf-8")),
        "fingerprint": fingerprint_core,
        "fingerprint_sha256": sha256_bytes(canonical_json_bytes(fingerprint_core)),
    }


def fingerprint_rows(chunks: list[Any]) -> list[dict[str, Any]]:
    return [fingerprinted(row_core_from_chunk(chunk)) for chunk in chunks]


def _expected_page(blocks: list[Any]) -> int | None:
    return next((block.page for block in blocks if block.page is not None), None)


def validate_token_intervals(
    raw: bytes,
    record: dict[str, Any],
    chunks: list[Any],
    rows: list[dict[str, Any]],
) -> None:
    """Validate current chunks directly against the parsed raw token stream."""
    if len(chunks) != len(rows):
        raise RuntimeError("candidate chunk/row cardinality drift")
    if [row["ordinal"] for row in rows] != list(range(len(rows))):
        raise RuntimeError("candidate row ordinals are not contiguous")

    pages = record.get("result", {}).get("pages", [])
    blocks = chunk_module._flatten(pages)
    image_pages = {
        page.get("page")
        for page in pages
        if page.get("page") is not None and page.get("images")
    }
    page_confidence = {
        page.get("page"): page.get("confidence")
        for page in pages
        if page.get("page") is not None and page.get("confidence") is not None
    }
    lineage_rows = []
    for chunk, row in zip(chunks, rows):
        row_validator._validate_expected_chunk(chunk)
        start = row["source_block_start"]
        end = row["source_block_end"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start <= end < len(blocks)
        ):
            raise RuntimeError("candidate span outside raw block population")
        covered = blocks[start : end + 1]
        expected_page = _expected_page(covered)
        if row["page_number"] != expected_page:
            raise RuntimeError("candidate page number is not raw-span-bound")
        if row["is_flow_diagram"] != any(
            block.kind == "mermaid" for block in covered
        ):
            raise RuntimeError("candidate flow flag is not raw-span-bound")
        if row["has_diagram"] != (expected_page in image_pages):
            raise RuntimeError("candidate diagram flag is not raw-page-bound")
        if row["confidence"] != page_confidence.get(expected_page):
            raise RuntimeError("candidate confidence is not raw-page-bound")
        lineage_rows.append({
            "chunk_index": row["ordinal"],
            "source_block_start": start,
            "source_block_end": end,
            "section_anchor": row["section_anchor"],
            "section_lineage": row["section_lineage"],
            "section_title": row["section_title"],
            "section_path": row["section_path"],
        })
    lineage_failures = row_validator._validate_lineage(raw, lineage_rows)
    if lineage_failures:
        raise RuntimeError("candidate lineage is not raw-bound")

    raw_tokens: list[str] = []
    block_intervals: list[tuple[int, int]] = []
    for block in blocks:
        tokens = block.text.split()
        if not tokens:
            raise RuntimeError("parsed raw block has an empty token surface")
        start = len(raw_tokens)
        raw_tokens.extend(tokens)
        block_intervals.append((start, len(raw_tokens)))
    candidate_tokens = [token for row in rows for token in row["content"].split()]
    if candidate_tokens != raw_tokens:
        raise RuntimeError("candidate global token surface differs from raw")

    row_token_cursor = 0
    block_cursor = 0
    for row in rows:
        row_tokens = row["content"].split()
        if not row_tokens:
            raise RuntimeError("candidate row has an empty token surface")
        row_start = row_token_cursor
        row_end = row_start + len(row_tokens)
        while (
            block_cursor < len(block_intervals)
            and block_intervals[block_cursor][1] <= row_start
        ):
            block_cursor += 1
        if block_cursor >= len(block_intervals):
            raise RuntimeError("candidate token interval exceeds raw blocks")
        expected_start = block_cursor
        expected_end = block_cursor
        while (
            expected_end + 1 < len(block_intervals)
            and block_intervals[expected_end + 1][0] < row_end
        ):
            expected_end += 1
        if (
            row["source_block_start"] != expected_start
            or row["source_block_end"] != expected_end
        ):
            raise RuntimeError("candidate token interval is not bound to raw span")
        row_token_cursor = row_end
    if row_token_cursor != len(raw_tokens):
        raise RuntimeError("candidate token cursor did not consume raw surface")


def _require_projection_types(row: dict[str, Any]) -> None:
    if set(row) != set(PROJECTION_FIELDS) or row["schema"] != PROJECTION_SCHEMA:
        raise RuntimeError("projection schema drift")
    if (
        not isinstance(row["extraction_sha256"], str)
        or not _SHA256.fullmatch(row["extraction_sha256"])
    ):
        raise RuntimeError("projection extraction identity drift")
    for key in (
        "raw_artifact_sha256",
        "surface_sha256",
        "fingerprint_multiset_sha256",
    ):
        if not isinstance(row[key], str) or not _SHA256.fullmatch(row[key]):
            raise RuntimeError("projection SHA-256 drift")
    for key in ("raw_blocks", "rows", "covered_blocks"):
        if not isinstance(row[key], int) or isinstance(row[key], bool) or row[key] < 0:
            raise RuntimeError("projection count drift")
    for key in (
        "missing_block_indexes",
        "coverage_gain_block_indexes",
        "coverage_regression_block_indexes",
    ):
        if (
            not isinstance(row[key], list)
            or row[key] != sorted(set(row[key]))
            or any(
                not isinstance(item, int) or isinstance(item, bool) or item < 0
                for item in row[key]
            )
        ):
            raise RuntimeError("projection index set drift")
    if not isinstance(row["surface_equal_raw"], bool) or not isinstance(
        row["changed"], bool
    ):
        raise RuntimeError("projection boolean drift")


def treatment_projection_from_seed(seed: dict[str, Any]) -> list[dict[str, Any]]:
    documents = seed.get("documents")
    if not isinstance(documents, list):
        raise RuntimeError("seed document population is missing")
    result = []
    for document in documents:
        row = {
            "schema": PROJECTION_SCHEMA,
            "extraction_sha256": document["extraction_sha256"],
            "raw_artifact_sha256": document["raw_artifact_sha256"],
            "raw_blocks": document["raw_blocks"],
            "rows": document["treatment_rows"],
            "covered_blocks": document["treatment_covered_blocks"],
            "missing_block_indexes": document["treatment_missing_block_indexes"],
            "surface_sha256": document["treatment_surface_sha256"],
            "surface_equal_raw": document["treatment_surface_equal_raw"],
            "fingerprint_multiset_sha256": document[
                "treatment_fingerprint_multiset_sha256"
            ],
            "coverage_gain_block_indexes": document[
                "coverage_gain_block_indexes"
            ],
            "coverage_regression_block_indexes": document[
                "coverage_regression_block_indexes"
            ],
            "changed": document["changed"],
        }
        _require_projection_types(row)
        result.append(row)
    result.sort(key=lambda row: row["extraction_sha256"])
    identities = [row["extraction_sha256"] for row in result]
    if len(identities) != len(set(identities)):
        raise RuntimeError("duplicate projection extraction identity")
    return result


def delta_contract_from_seed(seed: dict[str, Any]) -> dict[str, Any]:
    deltas = seed.get("changed_document_deltas")
    if deltas is None:
        deltas = []
    if not isinstance(deltas, list):
        raise RuntimeError("seed delta population is missing")
    compact = []
    counts = {
        "delta_unchanged_rows": 0,
        "delta_removed_rows": 0,
        "delta_added_rows": 0,
        "delta_overlap_modified_rows": 0,
        "delta_pure_added_rows": 0,
    }
    for document in deltas:
        extraction = document.get("extraction_sha256")
        unchanged = document.get("unchanged")
        removed = document.get("removed")
        added = document.get("added")
        modified = document.get("modified")
        if (
            not isinstance(extraction, str)
            or not _SHA256.fullmatch(extraction)
            or any(not isinstance(value, list) for value in (unchanged, removed, added, modified))
        ):
            raise RuntimeError("seed delta schema drift")

        def treatment_pair(row: dict[str, Any], ordinal_key: str) -> tuple[int, str]:
            ordinal = row.get(ordinal_key)
            fingerprint = row.get("fingerprint_sha256")
            if ordinal_key == "treatment_ordinal":
                fingerprint = row.get("treatment_fingerprint_sha256", fingerprint)
            if (
                not isinstance(ordinal, int)
                or isinstance(ordinal, bool)
                or ordinal < 0
                or not isinstance(fingerprint, str)
                or not _SHA256.fullmatch(fingerprint)
            ):
                raise RuntimeError("seed delta treatment binding drift")
            return ordinal, fingerprint

        unchanged_pairs = sorted(
            treatment_pair(row, "treatment_ordinal") for row in unchanged
        )
        added_pairs = sorted(treatment_pair(row, "ordinal") for row in added)
        modified_pairs = sorted(
            treatment_pair(row, "treatment_ordinal") for row in modified
        )
        if (
            len(unchanged_pairs) != len(set(unchanged_pairs))
            or len(added_pairs) != len(set(added_pairs))
            or len(modified_pairs) != len(set(modified_pairs))
            or not set(modified_pairs) <= set(added_pairs)
        ):
            raise RuntimeError("seed delta treatment partition drift")
        pure_added_pairs = sorted(set(added_pairs) - set(modified_pairs))
        compact.append({
            "extraction_sha256": extraction,
            "unchanged": [list(pair) for pair in unchanged_pairs],
            "added": [list(pair) for pair in added_pairs],
            "modified": [list(pair) for pair in modified_pairs],
            "pure_added": [list(pair) for pair in pure_added_pairs],
            "removed_count": len(removed),
        })
        counts["delta_unchanged_rows"] += len(unchanged_pairs)
        counts["delta_removed_rows"] += len(removed)
        counts["delta_added_rows"] += len(added_pairs)
        counts["delta_overlap_modified_rows"] += len(modified_pairs)
        counts["delta_pure_added_rows"] += len(pure_added_pairs)
    compact.sort(key=lambda row: row["extraction_sha256"])
    identities = [row["extraction_sha256"] for row in compact]
    if len(identities) != len(set(identities)):
        raise RuntimeError("duplicate seed delta extraction identity")
    return {
        "documents": compact,
        "counts": counts,
        "manifest_sha256": sha256_bytes(canonical_json_bytes(compact)),
    }


def validate_candidate_delta_bindings(
    extraction_sha256: str,
    candidate_rows: list[dict[str, Any]],
    frozen_delta: dict[str, Any] | None,
) -> None:
    if frozen_delta is None:
        return
    candidate_pairs = {
        (row["ordinal"], row["fingerprint_sha256"]) for row in candidate_rows
    }
    required = {
        tuple(pair)
        for key in ("unchanged", "added", "modified", "pure_added")
        for pair in frozen_delta[key]
    }
    if not required <= candidate_pairs:
        raise RuntimeError(
            f"candidate delta treatment binding drift: {extraction_sha256}"
        )


def _fingerprint_multiset_sha256(rows: list[dict[str, Any]]) -> str:
    manifest = [
        {"fingerprint_sha256": row["fingerprint_sha256"], "occurrence": occurrence}
        for occurrence, row in enumerate(
            sorted(rows, key=lambda item: (item["fingerprint_sha256"], item["ordinal"]))
        )
    ]
    return sha256_bytes(canonical_json_bytes(manifest))


def candidate_document_projection(
    raw: bytes,
    record: dict[str, Any],
    rows: list[dict[str, Any]],
    frozen_document: dict[str, Any],
) -> dict[str, Any]:
    blocks = chunk_module._flatten(record.get("result", {}).get("pages", []))
    covered = {
        block_index
        for row in rows
        for block_index in range(row["source_block_start"], row["source_block_end"] + 1)
    }
    population = set(range(len(blocks)))
    baseline_covered = population - set(
        frozen_document["baseline_missing_block_indexes"]
    )
    raw_surface = surface("\n\n".join(block.text for block in blocks))
    candidate_surface = surface("\n\n".join(row["content"] for row in rows))
    fingerprint_sha = _fingerprint_multiset_sha256(rows)
    result = {
        "schema": PROJECTION_SCHEMA,
        "extraction_sha256": record["sha256"],
        "raw_artifact_sha256": sha256_bytes(raw),
        "raw_blocks": len(blocks),
        "rows": len(rows),
        "covered_blocks": len(covered),
        "missing_block_indexes": sorted(population - covered),
        "surface_sha256": sha256_bytes(candidate_surface.encode("utf-8")),
        "surface_equal_raw": candidate_surface == raw_surface,
        "fingerprint_multiset_sha256": fingerprint_sha,
        "coverage_gain_block_indexes": sorted(covered - baseline_covered),
        "coverage_regression_block_indexes": sorted(baseline_covered - covered),
        "changed": (
            fingerprint_sha
            != frozen_document["baseline_fingerprint_multiset_sha256"]
        ),
    }
    _require_projection_types(result)
    return result


def validate_output_schema(payload: dict[str, Any]) -> None:
    if set(payload) != OUTPUT_TOP_LEVEL:
        raise RuntimeError("output top-level schema drift")
    exact_nested = {
        "dependencies": DEPENDENCY_KEYS,
        "source": SOURCE_KEYS,
        "generation": GENERATION_KEYS,
        "population": POPULATION_KEYS,
        "manifests": MANIFEST_KEYS,
        "checks": CHECK_KEYS,
        "cost": COST_KEYS,
        "authorization": AUTHORIZATION_KEYS,
    }
    for key, expected in exact_nested.items():
        if not isinstance(payload[key], dict) or set(payload[key]) != expected:
            raise RuntimeError(f"output {key} schema drift")
    if (
        payload["instrument"] != "s117_m28_candidate_materialization_v1"
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or payload["status"] not in {"GO", "NO_GO"}
        or payload["loadable"] is not False
        or payload["authority"]
        != "raw_store_parsed_block_whitespace_token_surface_only"
    ):
        raise RuntimeError("output envelope drift")
    if any(
        not isinstance(value, str) or not _SHA256.fullmatch(value)
        for value in payload["dependencies"].values()
    ):
        raise RuntimeError("output dependency hash drift")
    source = payload["source"]
    if (
        not isinstance(source["store_slug"], str)
        or re.fullmatch(r"[A-Za-z0-9._-]+", source["store_slug"]) is None
        or any(
            not isinstance(source[key], int)
            or isinstance(source[key], bool)
            or source[key] < 0
            for key in ("json_files", "records")
        )
        or not isinstance(source["non_record_artifacts"], list)
        or any(
            not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9._-]+", name) is None
            for name in source["non_record_artifacts"]
        )
        or not isinstance(source["manifest_sha256"], str)
        or not _SHA256.fullmatch(source["manifest_sha256"])
    ):
        raise RuntimeError("output source type drift")
    generation = payload["generation"]
    try:
        materialization_uuid = uuid.UUID(generation["materialization_id"])
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("output generation identity drift") from exc
    if (
        generation["manifest_schema"] != "chunk_materialization_manifest_v1"
        or not isinstance(generation["manifest_sha256"], str)
        or not _SHA256.fullmatch(generation["manifest_sha256"])
        or not isinstance(generation["rows_manifest_sha256"], str)
        or not _SHA256.fullmatch(generation["rows_manifest_sha256"])
        or not isinstance(generation["rows_manifest_bytes"], int)
        or isinstance(generation["rows_manifest_bytes"], bool)
        or generation["rows_manifest_bytes"] < 0
        or str(materialization_uuid) != generation["materialization_id"]
    ):
        raise RuntimeError("output generation type drift")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in payload["population"].values()
    ):
        raise RuntimeError("output population type drift")
    if any(
        not isinstance(value, str) or not _SHA256.fullmatch(value)
        for value in payload["manifests"].values()
    ):
        raise RuntimeError("output manifest hash drift")
    failures = payload["failures"]
    if (
        not isinstance(failures, list)
        or failures != sorted(set(failures))
        or not set(failures) <= FAILURE_CODES
    ):
        raise RuntimeError("output failure-code drift")
    if not all(isinstance(value, bool) for value in payload["checks"].values()):
        raise RuntimeError("output check type drift")
    if payload["status"] == "GO" and (
        failures or not all(payload["checks"].values())
    ):
        raise RuntimeError("output GO decision drift")
    if payload["status"] == "NO_GO" and (
        not failures or all(payload["checks"].values())
    ):
        raise RuntimeError("output NO_GO decision drift")
    if payload["cost"] != {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "external_calls_blocked": True,
    }:
        raise RuntimeError("output cost contract drift")
    if payload["authorization"] != {
        "database": False,
        "network": False,
        "models": False,
        "retrieval": False,
        "context_generation": False,
        "embeddings": False,
        "load": False,
        "serving": False,
        "deploy": False,
        "facts_moved_to_ok": 0,
        "M3": "BLOCKED",
    }:
        raise RuntimeError("output authorization drift")
