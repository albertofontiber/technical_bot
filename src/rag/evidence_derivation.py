"""Apply exact, source-span-derived chunk views before answer synthesis."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import EVIDENCE_DERIVATION_OVERLAY, PROJECT_DIR


REGISTRY_PATH = PROJECT_DIR / "config/extraction_derivations_v5.json"
REGISTRY_SCHEMA = "runtime_evidence_derivations_v5"
REGISTRY_CONTRACT = "active_live_chunk_bound_numeric_superscript_overlay_v5"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _source_key(value: str) -> str:
    value = re.sub(r"(?i)\.pdf$", "", value.strip())
    return re.sub(r"[^a-z0-9]+", "", _fold(value))


def validate_registry(payload: dict[str, Any]) -> list[str]:
    """Validate the complete content-addressed sidecar, fail-closed."""
    failures: list[str] = []
    if payload.get("schema") != REGISTRY_SCHEMA:
        failures.append("schema")
    if payload.get("version") != 5:
        failures.append("version")
    if payload.get("contract") != REGISTRY_CONTRACT:
        failures.append("contract")
    artifact_sha = payload.get("artifact_sha256")
    body = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    if not isinstance(artifact_sha, str) or artifact_sha != _sha(_canonical_bytes(body)):
        failures.append("artifact_sha256")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return sorted(set([*failures, "entries"]))
    if payload.get("entry_count") != len(entries):
        failures.append("entry_count")
    identities: list[tuple[str, str, int]] = []
    derivation_hashes: list[str] = []
    covered_receipt_rows: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"entry_{index}_shape")
            continue
        derivation_sha = entry.get("chunk_derivation_sha256")
        core = {
            key: value
            for key, value in entry.items()
            if key != "chunk_derivation_sha256"
        }
        if (
            not isinstance(derivation_sha, str)
            or derivation_sha != _sha(_canonical_bytes(core))
        ):
            failures.append(f"entry_{index}_chunk_derivation_sha256")
        else:
            derivation_hashes.append(derivation_sha)
        for key in (
            "extraction_sha256",
            "original_chunk_content_sha256",
            "derived_chunk_content_sha256",
            "derivation_manifest_sha256",
        ):
            if not isinstance(entry.get(key), str) or _SHA256.fullmatch(entry[key]) is None:
                failures.append(f"entry_{index}_{key}")
        chunk_id = entry.get("chunk_id")
        if not isinstance(chunk_id, str) or _UUID.fullmatch(chunk_id) is None:
            failures.append(f"entry_{index}_chunk_id")
        chunk_index = entry.get("chunk_index")
        if (
            not isinstance(chunk_index, int)
            or isinstance(chunk_index, bool)
            or chunk_index < 0
        ):
            failures.append(f"entry_{index}_chunk_index")
        else:
            identities.append(
                (
                    str(chunk_id),
                    str(entry.get("extraction_sha256")),
                    chunk_index,
                )
            )
        derived_content = entry.get("derived_content")
        if (
            not isinstance(derived_content, str)
            or not derived_content
            or entry.get("derived_chunk_content_sha256")
            != _sha(derived_content.encode("utf-8"))
        ):
            failures.append(f"entry_{index}_derived_content")
        receipts = entry.get("source_pdf_receipt_sha256s")
        if (
            not isinstance(receipts, list)
            or not receipts
            or not all(isinstance(value, str) and _SHA256.fullmatch(value) for value in receipts)
        ):
            failures.append(f"entry_{index}_source_pdf_receipts")
        else:
            covered_receipt_rows.extend(receipts)
    covered_receipts = set(covered_receipt_rows)
    if len(covered_receipt_rows) != len(covered_receipts):
        failures.append("duplicate_bound_source_receipts")
    if len(identities) != len(set(identities)):
        failures.append("duplicate_chunk_identities")
    if len(derivation_hashes) != len(set(derivation_hashes)):
        failures.append("duplicate_chunk_derivations")
    absent_rows = payload.get("absent_source_pdf_receipts")
    absent_receipt_rows: list[str] = []
    if not isinstance(absent_rows, list):
        failures.append("absent_source_pdf_receipts")
    else:
        for index, row in enumerate(absent_rows):
            value = row.get("source_pdf_receipt_sha256") if isinstance(row, dict) else None
            if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
                failures.append(f"absent_receipt_{index}")
            else:
                absent_receipt_rows.append(value)
    absent_receipts = set(absent_receipt_rows)
    if len(absent_receipt_rows) != len(absent_receipts):
        failures.append("duplicate_absent_source_receipts")
    if covered_receipts.intersection(absent_receipts):
        failures.append("source_receipt_partition_overlap")
    if payload.get("bound_source_pdf_receipt_count") != len(covered_receipts):
        failures.append("bound_source_pdf_receipt_count")
    if payload.get("absent_source_pdf_receipt_count") != len(absent_receipts):
        failures.append("absent_source_pdf_receipt_count")
    if payload.get("source_pdf_receipt_count") != len(
        covered_receipts.union(absent_receipts)
    ):
        failures.append("source_pdf_receipt_count")
    return sorted(set(failures))


@lru_cache(maxsize=4)
def load_registry(path: str = str(REGISTRY_PATH)) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    failures = validate_registry(payload)
    if failures:
        raise RuntimeError(f"invalid evidence derivation registry: {failures}")
    return payload


def clear_registry_cache() -> None:
    load_registry.cache_clear()


def apply_evidence_derivations_with_trace(
    chunks: list[dict[str, Any]],
    *,
    enabled: bool | None = None,
    registry_path: str | Path = REGISTRY_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return an exact derived view without mutating a served source row."""
    active = EVIDENCE_DERIVATION_OVERLAY if enabled is None else enabled
    if not active:
        return chunks, {
            "status": "disabled",
            "artifact_sha256": None,
            "modified_rows": 0,
            "applied_derivations": [],
            "abstentions": [],
        }
    registry = load_registry(str(registry_path))
    by_identity = {
        (entry["chunk_id"], entry["extraction_sha256"], entry["chunk_index"]): entry
        for entry in registry["entries"]
    }
    output: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    abstentions: list[dict[str, Any]] = []
    for row in chunks:
        updated = copy.deepcopy(row)
        extraction = str(row.get("extraction_sha256") or "").casefold()
        chunk_id = str(row.get("id") or "").casefold()
        chunk_index = row.get("chunk_index")
        entry = (
            by_identity.get((chunk_id, extraction, chunk_index))
            if _UUID.fullmatch(chunk_id)
            and _SHA256.fullmatch(extraction)
            and isinstance(chunk_index, int)
            and not isinstance(chunk_index, bool)
            else None
        )
        if entry is None:
            output.append(updated)
            continue
        if _source_key(str(row.get("source_file") or "")) != _source_key(
            entry["source_file"]
        ):
            abstentions.append(
                {
                    "row_id": row.get("id"),
                    "chunk_derivation_sha256": entry["chunk_derivation_sha256"],
                    "reason": "source_file_mismatch",
                }
            )
            output.append(updated)
            continue
        content = str(row.get("content") or "")
        content_sha = _sha(content.encode("utf-8"))
        if content_sha == entry["derived_chunk_content_sha256"]:
            output.append(updated)
            continue
        if content_sha != entry["original_chunk_content_sha256"]:
            abstentions.append(
                {
                    "row_id": row.get("id"),
                    "chunk_derivation_sha256": entry["chunk_derivation_sha256"],
                    "reason": "original_content_hash_mismatch",
                }
            )
            output.append(updated)
            continue
        updated["content"] = entry["derived_content"]
        updated["evidence_derivation_contract"] = REGISTRY_CONTRACT
        updated["evidence_derivation_artifact_sha256"] = registry["artifact_sha256"]
        updated["evidence_derivation_sha256"] = entry["chunk_derivation_sha256"]
        updated["evidence_derivation_source_receipts"] = entry[
            "source_pdf_receipt_sha256s"
        ]
        applied.append(
            {
                "row_id": row.get("id"),
                "chunk_derivation_sha256": entry["chunk_derivation_sha256"],
            }
        )
        output.append(updated)
    return output, {
        "status": "applied" if applied else "no_applicable_derivations",
        "artifact_sha256": registry["artifact_sha256"],
        "modified_rows": len(applied),
        "applied_derivations": applied,
        "abstentions": abstentions,
    }


def apply_evidence_derivations(
    chunks: list[dict[str, Any]],
    *,
    enabled: bool | None = None,
    registry_path: str | Path = REGISTRY_PATH,
) -> list[dict[str, Any]]:
    return apply_evidence_derivations_with_trace(
        chunks, enabled=enabled, registry_path=registry_path
    )[0]
