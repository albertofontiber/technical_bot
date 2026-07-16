#!/usr/bin/env python3
"""Fail-closed local receipt builder for the S117 M2.8 chunk candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml

from scripts import s117_m28_candidate_validation as validation
from scripts import s117_materialize_chunks_v3_local as row_validator
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as materializer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m28_candidate_materialization_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s117_m28_candidate_materialization_execution_permit_v1.yaml"
DEFAULT_STORE_RELATIVE = Path("data/extraction/agent_anthropic-sonnet-45")
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.json$")
_ZERO_SHA = "0" * 64
_ZERO_UUID = "00000000-0000-0000-0000-000000000000"
REQUIRED_PATHS = {
    "baseline_receipt": "evals/s117_chunks_v3_development_materialization_v1.json",
    "m27c_prereg": "evals/s117_m27_loss_safe_chunking_probe_prereg_v2.yaml",
    "m27c_gate": "evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml",
    "m27c_seed1": "evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json",
    "m27c_seed2": "evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json",
    "m27c_probe_base": "scripts/s117_m27_loss_safe_chunking_probe.py",
    "m27c_token_validator": "scripts/s117_m27_loss_safe_chunking_probe_v2.py",
    "m27c_surface_helper": "scripts/s117_m27_live_evidence.py",
    "compact100": "evals/s117_m27_loss_rows_compact_v1.json",
    "m28_freeze": "evals/s117_m28_content_preservation_implementation_freeze_v1.yaml",
    "m28_gate": "evals/s117_m28_content_preservation_implementation_gate_v1.yaml",
    "chunker": "src/reingest/chunk.py",
    "materializer": "src/reingest/chunk_provenance.py",
    "row_validator": "scripts/s117_materialize_chunks_v3_local.py",
    "candidate_validator": "scripts/s117_m28_candidate_validation.py",
    "src_init": "src/__init__.py",
    "reingest_init": "src/reingest/__init__.py",
    "runner": "scripts/s117_m28_candidate_materialization.py",
    "runner_tests": "tests/test_s117_m28_candidate_materialization.py",
    "design_v2": "evals/s117_m28_candidate_materialization_design_v2.md",
    "design_v3": "evals/s117_m28_candidate_materialization_design_v3.md",
}
_REQUIRED_INPUTS = set(REQUIRED_PATHS)


class CandidateFailure(RuntimeError):
    def __init__(self, code: str):
        if code not in validation.FAILURE_CODES:
            code = "internal_failure"
        self.code = code
        super().__init__(code)


class ExternalCallBlocked(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _under(root: Path, selected: Path) -> Path:
    if root.is_symlink() or selected.is_absolute() or ".." in selected.parts:
        raise CandidateFailure("contract_integrity")
    resolved_root = root.resolve(strict=True)
    cursor = root
    for part in selected.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CandidateFailure("contract_integrity")
    resolved = (resolved_root / selected).resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise CandidateFailure("contract_integrity")
    return resolved


@contextmanager
def block_external_connections() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise ExternalCallBlocked("external connection blocked")

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


def _authorization() -> dict[str, Any]:
    return {
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
    }


def _cost() -> dict[str, Any]:
    return {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "external_calls_blocked": True,
    }


def _dependency_defaults() -> dict[str, str]:
    return {key: _ZERO_SHA for key in validation.DEPENDENCY_KEYS}


def no_go_payload(
    code: str,
    dependencies: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = {
        "instrument": "s117_m28_candidate_materialization_v1",
        "schema_version": 1,
        "status": "NO_GO",
        "loadable": False,
        "authority": "raw_store_parsed_block_whitespace_token_surface_only",
        "dependencies": dependencies or _dependency_defaults(),
        "source": {
            "store_slug": DEFAULT_STORE_RELATIVE.name,
            "json_files": 0,
            "records": 0,
            "non_record_artifacts": [],
            "manifest_sha256": _ZERO_SHA,
        },
        "generation": {
            "manifest_schema": "chunk_materialization_manifest_v1",
            "manifest_sha256": _ZERO_SHA,
            "materialization_id": _ZERO_UUID,
            "rows_manifest_sha256": _ZERO_SHA,
            "rows_manifest_bytes": 0,
        },
        "population": {
            "documents": 0,
            "raw_blocks": 0,
            "rows": 0,
            "titled_rows": 0,
            "untitled_rows": 0,
            "covered_blocks": 0,
            "missing_blocks": 0,
            "coverage_gain_blocks": 0,
            "coverage_regression_blocks": 0,
            "changed_documents": 0,
            "unchanged_documents": 0,
            "delta_unchanged_rows": 0,
            "delta_removed_rows": 0,
            "delta_added_rows": 0,
            "delta_overlap_modified_rows": 0,
            "delta_pure_added_rows": 0,
            "validation_failures": 1,
        },
        "manifests": {
            "candidate_projection_sha256": _ZERO_SHA,
            "candidate_document_receipts_sha256": _ZERO_SHA,
            "candidate_row_ids_sha256": _ZERO_SHA,
            "coverage_gain_identities_sha256": _ZERO_SHA,
        },
        "checks": {
            key: key == "external_calls_blocked" for key in validation.CHECK_KEYS
        },
        "failures": [
            code if code in validation.FAILURE_CODES else "internal_failure"
        ],
        "cost": _cost(),
        "authorization": _authorization(),
    }
    validation.validate_output_schema(payload)
    return payload


def _validate_contract_shape(prereg: dict[str, Any]) -> None:
    if (
        prereg.get("instrument")
        != "s117_m28_candidate_materialization_prereg_v1"
        or prereg.get("status") != "frozen_before_candidate_execution"
        or set(prereg.get("frozen_inputs", {})) != _REQUIRED_INPUTS
        or prereg.get("selected_store_relative_path")
        != DEFAULT_STORE_RELATIVE.as_posix()
    ):
        raise CandidateFailure("contract_integrity")
    for role, item in prereg["frozen_inputs"].items():
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "sha256"}
            or item["path"] != REQUIRED_PATHS[role]
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        ):
            raise CandidateFailure("contract_integrity")


def _load_authorized(
    prereg_path: Path,
    permit_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Path]]:
    if (
        prereg_path.resolve() != DEFAULT_PREREG.resolve()
        or permit_path.resolve() != DEFAULT_PERMIT.resolve()
        or not prereg_path.is_file()
        or not permit_path.is_file()
    ):
        raise CandidateFailure("contract_integrity")
    prereg_raw = prereg_path.read_bytes()
    permit_raw = permit_path.read_bytes()
    prereg = yaml.safe_load(prereg_raw)
    permit = yaml.safe_load(permit_raw)
    if not isinstance(prereg, dict) or not isinstance(permit, dict):
        raise CandidateFailure("contract_integrity")
    _validate_contract_shape(prereg)
    if (
        permit.get("instrument")
        != "s117_m28_candidate_materialization_execution_permit_v1"
        or permit.get("status") != "EXECUTION_GO_LOCAL_ONLY"
        or permit.get("prereg_sha256") != hashlib.sha256(prereg_raw).hexdigest()
        or permit.get("selected_store_relative_path")
        != DEFAULT_STORE_RELATIVE.as_posix()
    ):
        raise CandidateFailure("contract_integrity")

    selected: dict[str, Path] = {}
    for role, item in prereg["frozen_inputs"].items():
        path = _under(ROOT, Path(item["path"]))
        if not path.is_file() or _sha(path) != item["sha256"]:
            raise CandidateFailure("contract_integrity")
        selected[role] = path
    for role in ("runner", "runner_tests", "design_v2", "design_v3"):
        if permit.get(f"{role}_sha256") != prereg["frozen_inputs"][role]["sha256"]:
            raise CandidateFailure("contract_integrity")

    dependencies = {
        "prereg_sha256": hashlib.sha256(prereg_raw).hexdigest(),
        "permit_sha256": hashlib.sha256(permit_raw).hexdigest(),
        "runner_sha256": prereg["frozen_inputs"]["runner"]["sha256"],
        "runner_tests_sha256": prereg["frozen_inputs"]["runner_tests"]["sha256"],
        "design_v2_sha256": prereg["frozen_inputs"]["design_v2"]["sha256"],
        "design_v3_sha256": prereg["frozen_inputs"]["design_v3"]["sha256"],
        "baseline_receipt_sha256": prereg["frozen_inputs"]["baseline_receipt"]["sha256"],
        "m27c_prereg_sha256": prereg["frozen_inputs"]["m27c_prereg"]["sha256"],
        "m27c_gate_sha256": prereg["frozen_inputs"]["m27c_gate"]["sha256"],
        "m27c_seed1_sha256": prereg["frozen_inputs"]["m27c_seed1"]["sha256"],
        "m27c_seed2_sha256": prereg["frozen_inputs"]["m27c_seed2"]["sha256"],
        "m27c_probe_base_sha256": prereg["frozen_inputs"]["m27c_probe_base"]["sha256"],
        "m27c_token_validator_sha256": prereg["frozen_inputs"]["m27c_token_validator"]["sha256"],
        "m27c_surface_helper_sha256": prereg["frozen_inputs"]["m27c_surface_helper"]["sha256"],
        "compact100_sha256": prereg["frozen_inputs"]["compact100"]["sha256"],
        "m28_freeze_sha256": prereg["frozen_inputs"]["m28_freeze"]["sha256"],
        "m28_gate_sha256": prereg["frozen_inputs"]["m28_gate"]["sha256"],
        "chunker_sha256": prereg["frozen_inputs"]["chunker"]["sha256"],
        "materializer_sha256": prereg["frozen_inputs"]["materializer"]["sha256"],
        "row_validator_sha256": prereg["frozen_inputs"]["row_validator"]["sha256"],
        "candidate_validator_sha256": prereg["frozen_inputs"]["candidate_validator"]["sha256"],
        "src_init_sha256": prereg["frozen_inputs"]["src_init"]["sha256"],
        "reingest_init_sha256": prereg["frozen_inputs"]["reingest_init"]["sha256"],
    }
    return prereg, permit, dependencies, selected


def _strict_record(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = path.read_bytes()
        record = validation.strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CandidateFailure("source_drift") from exc
    if record.get("sha256") != path.stem:
        raise CandidateFailure("source_drift")
    return raw, record


def _selected_json_files(store: Path) -> list[Path]:
    if store.is_symlink():
        raise CandidateFailure("source_drift")
    resolved_store = store.resolve(strict=True)
    entries = sorted(store.iterdir(), key=lambda path: path.name)
    for path in entries:
        resolved = path.resolve(strict=True)
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix != ".json"
            or not resolved.is_relative_to(resolved_store)
        ):
            raise CandidateFailure("source_drift")
    return entries


def _independent_generation(
    descriptors: list[dict[str, str]],
    chunker_sha256: str,
    materializer_sha256: str,
) -> tuple[dict[str, Any], str, str]:
    production = materializer.generation_manifest(
        descriptors,
        chunker_sha256=chunker_sha256,
        materializer_sha256=materializer_sha256,
    )
    independent = row_validator._expected_generation_manifest(
        descriptors,
        chunker_sha256=chunker_sha256,
        materializer_sha256=materializer_sha256,
    )
    if production != independent:
        raise CandidateFailure("generation_identity_drift")
    production_sha, production_id = materializer.materialization_identity(production)
    expected_sha, expected_id = row_validator._expected_identity(independent)
    if (production_sha, production_id) != (expected_sha, expected_id):
        raise CandidateFailure("generation_identity_drift")
    return production, production_sha, production_id


def _document_receipts_manifest(projections: list[dict[str, Any]]) -> str:
    receipts = [
        {
            "extraction_sha256": row["extraction_sha256"],
            "receipt_sha256": validation.sha256_bytes(
                validation.canonical_json_bytes(row)
            ),
        }
        for row in projections
    ]
    return validation.sha256_bytes(validation.canonical_json_bytes(receipts))


def build_candidate_payload(
    store: Path,
    seed: int,
    prereg: dict[str, Any],
    dependencies: dict[str, str],
    baseline_receipt: dict[str, Any],
    m27c_seed1: dict[str, Any],
    m27c_seed2: dict[str, Any],
) -> dict[str, Any]:
    _validate_contract_shape(prereg)
    expected = prereg["expected"]
    files = _selected_json_files(store)
    source_manifest = row_validator._store_manifest(files)
    record_files = [path for path in files if _RECORD_NAME.fullmatch(path.name)]
    non_records = [path.name for path in files if path not in record_files]
    if (
        len(files) != expected["source"]["json_files"]
        or len(record_files) != expected["source"]["records"]
        or non_records != expected["source"]["non_record_artifacts"]
        or source_manifest != expected["source"]["manifest_sha256"]
    ):
        raise CandidateFailure("source_drift")

    projection1 = validation.treatment_projection_from_seed(m27c_seed1)
    projection2 = validation.treatment_projection_from_seed(m27c_seed2)
    frozen_projection_bytes = validation.canonical_json_bytes(projection1)
    if (
        projection1 != projection2
        or len(frozen_projection_bytes) != expected["projection"]["bytes"]
        or validation.sha256_bytes(frozen_projection_bytes)
        != expected["projection"]["sha256"]
    ):
        raise CandidateFailure("contract_integrity")
    frozen_documents = {
        row["extraction_sha256"]: row for row in m27c_seed1["documents"]
    }
    delta1 = validation.delta_contract_from_seed(m27c_seed1)
    delta2 = validation.delta_contract_from_seed(m27c_seed2)
    if delta1 != delta2:
        raise CandidateFailure("contract_integrity")
    delta_by_document = {
        row["extraction_sha256"]: row for row in delta1["documents"]
    }
    expected_changed = {
        row["extraction_sha256"] for row in projection1 if row["changed"]
    }
    if set(delta_by_document) != expected_changed:
        raise CandidateFailure("contract_integrity")

    raw_by_name: dict[str, tuple[bytes, dict[str, Any]]] = {}
    descriptors = []
    for path in record_files:
        raw, record = _strict_record(path)
        raw_sha = validation.sha256_bytes(raw)
        descriptors.append({
            "extraction_sha256": record["sha256"],
            "raw_artifact_sha256": raw_sha,
        })
        raw_by_name[path.name] = (raw, record)

    chunker_sha = dependencies["chunker_sha256"]
    materializer_sha = dependencies["materializer_sha256"]
    manifest, manifest_sha, materialization_id = _independent_generation(
        descriptors, chunker_sha, materializer_sha
    )
    generation_expected = expected["generation"]
    baseline_generation = baseline_receipt["generation"]
    if (
        manifest_sha != generation_expected["manifest_sha256"]
        or materialization_id != generation_expected["materialization_id"]
        or manifest_sha == baseline_generation["manifest_sha256"]
        or materialization_id == baseline_generation["materialization_id"]
        or manifest["chunker_sha256"] == baseline_receipt["dependencies"]["chunker_sha256"]
    ):
        raise CandidateFailure("generation_identity_drift")

    processing = list(record_files)
    random.Random(seed).shuffle(processing)
    all_rows: list[dict[str, Any]] = []
    candidate_projections = []
    raw_block_total = 0
    for path in processing:
        raw, record = raw_by_name[path.name]
        rows = materializer.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha,
        )
        if row_validator.validate_rows_against_raw(
            raw,
            rows,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha,
        ):
            raise CandidateFailure("row_validation_failure")
        chunks = chunk_module.chunk_document(record)
        fingerprint_rows = validation.fingerprint_rows(chunks)
        try:
            validation.validate_token_intervals(raw, record, chunks, fingerprint_rows)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise CandidateFailure("raw_token_interval_failure") from exc
        try:
            validation.validate_candidate_delta_bindings(
                record["sha256"],
                fingerprint_rows,
                delta_by_document.get(record["sha256"]),
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise CandidateFailure("treatment_projection_drift") from exc
        frozen_document = frozen_documents.get(record["sha256"])
        if frozen_document is None:
            raise CandidateFailure("treatment_projection_drift")
        candidate_projections.append(validation.candidate_document_projection(
            raw, record, fingerprint_rows, frozen_document
        ))
        raw_block_total += len(chunk_module._flatten(record.get("result", {}).get("pages", [])))
        all_rows.extend(rows)

    random.Random(seed ^ 0x5A17).shuffle(all_rows)
    all_rows.sort(key=lambda row: (row["extraction_sha256"], row["chunk_index"]))
    candidate_projections.sort(key=lambda row: row["extraction_sha256"])
    if row_validator._global_failures(all_rows):
        raise CandidateFailure("global_invariant_failure")
    rows_manifest = materializer.row_manifest_bytes(all_rows)
    if rows_manifest != row_validator._independent_manifest_bytes(all_rows):
        raise CandidateFailure("row_validation_failure")
    candidate_projection_bytes = validation.canonical_json_bytes(candidate_projections)
    if candidate_projection_bytes != frozen_projection_bytes:
        raise CandidateFailure("treatment_projection_drift")

    covered = sum(row["covered_blocks"] for row in candidate_projections)
    missing = sum(len(row["missing_block_indexes"]) for row in candidate_projections)
    gains = [
        {"extraction_sha256": row["extraction_sha256"], "block_index": index}
        for row in candidate_projections
        for index in row["coverage_gain_block_indexes"]
    ]
    regressions = sum(
        len(row["coverage_regression_block_indexes"])
        for row in candidate_projections
    )
    titled = sum(1 for row in all_rows if bool(row["section_title"]))
    population = {
        "documents": len(record_files),
        "raw_blocks": raw_block_total,
        "rows": len(all_rows),
        "titled_rows": titled,
        "untitled_rows": len(all_rows) - titled,
        "covered_blocks": covered,
        "missing_blocks": missing,
        "coverage_gain_blocks": len(gains),
        "coverage_regression_blocks": regressions,
        "changed_documents": sum(1 for row in candidate_projections if row["changed"]),
        "unchanged_documents": sum(1 for row in candidate_projections if not row["changed"]),
        **delta1["counts"],
        "validation_failures": 0,
    }
    if population != expected["population"]:
        raise CandidateFailure("population_drift")

    row_ids = [row["id"] for row in all_rows]
    payload = {
        "instrument": "s117_m28_candidate_materialization_v1",
        "schema_version": 1,
        "status": "GO",
        "loadable": False,
        "authority": "raw_store_parsed_block_whitespace_token_surface_only",
        "dependencies": dependencies,
        "source": {
            "store_slug": store.name,
            "json_files": len(files),
            "records": len(record_files),
            "non_record_artifacts": non_records,
            "manifest_sha256": source_manifest,
        },
        "generation": {
            "manifest_schema": manifest["schema"],
            "manifest_sha256": manifest_sha,
            "materialization_id": materialization_id,
            "rows_manifest_sha256": validation.sha256_bytes(rows_manifest),
            "rows_manifest_bytes": len(rows_manifest),
        },
        "population": population,
        "manifests": {
            "candidate_projection_sha256": validation.sha256_bytes(
                candidate_projection_bytes
            ),
            "candidate_document_receipts_sha256": _document_receipts_manifest(
                candidate_projections
            ),
            "candidate_row_ids_sha256": validation.sha256_bytes(
                validation.canonical_json_bytes(row_ids)
            ),
            "coverage_gain_identities_sha256": validation.sha256_bytes(
                validation.canonical_json_bytes(gains)
            ),
        },
        "checks": {key: True for key in validation.CHECK_KEYS},
        "failures": [],
        "cost": _cost(),
        "authorization": _authorization(),
    }
    if payload["generation"]["rows_manifest_sha256"] == expected["baseline_rows_manifest_sha256"]:
        raise CandidateFailure("generation_identity_drift")
    validation.validate_output_schema(payload)
    return payload


def safe_build_candidate_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    dependencies = kwargs.get("dependencies")
    try:
        with block_external_connections():
            return build_candidate_payload(*args, **kwargs)
    except CandidateFailure as exc:
        return no_go_payload(exc.code, dependencies)
    except ExternalCallBlocked:
        return no_go_payload("external_call_attempted", dependencies)
    except Exception:
        return no_go_payload("internal_failure", dependencies)


def _load_json(path: Path) -> dict[str, Any]:
    return validation.strict_json_loads(path.read_bytes())


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    validation.validate_output_schema(payload)
    path.write_bytes(validation.canonical_json_bytes(payload) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-workspace-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(1, 2), required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    dependencies = _dependency_defaults()
    try:
        prereg, _permit, dependencies, selected = _load_authorized(
            args.prereg, args.permit
        )
        store = _under(args.source_workspace_root, DEFAULT_STORE_RELATIVE)
        payload = safe_build_candidate_payload(
            store=store,
            seed=args.seed,
            prereg=prereg,
            dependencies=dependencies,
            baseline_receipt=_load_json(selected["baseline_receipt"]),
            m27c_seed1=_load_json(selected["m27c_seed1"]),
            m27c_seed2=_load_json(selected["m27c_seed2"]),
        )
    except CandidateFailure as exc:
        payload = no_go_payload(exc.code, dependencies)
    except Exception:
        payload = no_go_payload("internal_failure", dependencies)
    _write_payload(args.out, payload)
    return 0 if payload["status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
