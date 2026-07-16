from __future__ import annotations

import hashlib
import json
import math
import random
import socket
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREREG_RELATIVE = "evals/s117_m29_reconciled_loss_ledger_prereg_v1.json"
PERMIT_RELATIVE = "evals/s117_m29_reconciled_loss_ledger_execution_permit_v1.json"
OUTPUT_RELATIVES = {
    1: "evals/s117_m29_reconciled_loss_ledger_seed1_v1.json",
    2: "evals/s117_m29_reconciled_loss_ledger_seed2_v1.json",
}

SELECTED_PATHS = {
    "design_v1": "evals/s117_m29_reconciled_loss_ledger_design_v1.md",
    "design_v2": "evals/s117_m29_reconciled_loss_ledger_design_v2.md",
    "runner": "scripts/s117_m29_reconciled_loss_ledger.py",
    "runner_tests": "tests/test_s117_m29_reconciled_loss_ledger.py",
    "m27c_seed1": "evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json",
    "m27c_seed2": "evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json",
    "m27c_gate": "evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml",
    "compact100": "evals/s117_m27_loss_rows_compact_v1.json",
    "m28_seed1": "evals/s117_m28_candidate_materialization_seed1_v1.json",
    "m28_seed2": "evals/s117_m28_candidate_materialization_seed2_v1.json",
    "m28_gate": "evals/s117_m28_candidate_materialization_gate_v1.yaml",
    "m28_prereg": "evals/s117_m28_candidate_materialization_prereg_v1.yaml",
    "m28_permit": "evals/s117_m28_candidate_materialization_execution_permit_v1.yaml",
}
PARSED_ROLES = {"m27c_seed1", "m27c_seed2", "compact100", "m28_seed1", "m28_seed2"}
DEPENDENCY_ROLES = tuple(sorted((*SELECTED_PATHS, "preregistration", "execution_permit")))

CHECK_KEYS = (
    "contract_integrity",
    "m27c_seed_equivalence",
    "candidate_seed_equivalence",
    "candidate_projection_bridge_exact",
    "document_population_exact",
    "document_partitions_exact",
    "compact_integrity_exact",
    "baseline_missing_identity_set_exact",
    "candidate_missing_empty",
    "coverage_gain_exact",
    "coverage_regression_empty",
    "resolved_identity_bindings_exact",
    "manifest_integrity_exact",
    "output_schema_exact",
    "zero_external_cost",
)
FAILURE_CODES = (
    "contract_integrity_failure",
    "m27c_seed_drift",
    "candidate_seed_drift",
    "candidate_projection_bridge_failure",
    "document_population_drift",
    "document_partition_failure",
    "compact_integrity_failure",
    "baseline_missing_identity_drift",
    "candidate_missing_nonempty",
    "coverage_gain_drift",
    "coverage_regression_nonempty",
    "resolved_identity_binding_failure",
    "manifest_integrity_failure",
    "output_schema_failure",
    "external_call_attempt",
    "internal_failure",
)
MANIFEST_KEYS = (
    "documents_sha256",
    "document_receipts_sha256",
    "resolved_baseline_missing_sha256",
    "resolution_receipts_sha256",
    "baseline_missing_identities_sha256",
    "candidate_missing_identities_sha256",
)
POPULATION_KEYS = (
    "documents",
    "raw_blocks",
    "baseline_covered_blocks",
    "baseline_missing_blocks",
    "candidate_covered_blocks",
    "candidate_missing_blocks",
    "coverage_gain_blocks",
    "coverage_regression_blocks",
    "changed_fingerprint_multiset_documents",
    "unchanged_fingerprint_multiset_documents",
    "baseline_authorized_exclusion_identities",
    "baseline_unruled_loss_identities",
    "reconciled_baseline_missing_identities",
    "unresolved_baseline_missing_identities",
)
EXPECTED_POPULATION = {
    "documents": 1068,
    "raw_blocks": 333161,
    "baseline_covered_blocks": 333061,
    "baseline_missing_blocks": 100,
    "candidate_covered_blocks": 333161,
    "candidate_missing_blocks": 0,
    "coverage_gain_blocks": 100,
    "coverage_regression_blocks": 0,
    "changed_fingerprint_multiset_documents": 27,
    "unchanged_fingerprint_multiset_documents": 1041,
    "baseline_authorized_exclusion_identities": 13,
    "baseline_unruled_loss_identities": 87,
    "reconciled_baseline_missing_identities": 100,
    "unresolved_baseline_missing_identities": 0,
}
EXPECTED_PROJECTION_BYTES = 640933
EXPECTED_PROJECTION_SHA256 = "4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881"
EXPECTED_COMPACT_LOGICAL_SHA256 = "bfb54e1465c6ef66cfd72bad02c4f4653c8e9ab60033ca627278c225aec252ab"
EXPECTED_CANDIDATE_DOCUMENT_RECEIPTS_SHA256 = "57e4624d812188f97ea0bd9c81ccb76e6693fde40db41701ad60f3dd9edb293a"
EXPECTED_COVERAGE_GAIN_IDENTITIES_SHA256 = "6b0410a662c5523b04e3c19049199d8f27649653f34a6f3d87fee3a84147a675"
ZERO_SHA = "0" * 64

M27_CHECK_KEYS = (
    "baseline_covered_exact",
    "baseline_manifest_exact",
    "baseline_missing_count_exact",
    "baseline_missing_exact",
    "baseline_rows_exact",
    "changed_documents_have_delta",
    "coverage_gain_exact",
    "delta_partitions_exact",
    "document_population_exact",
    "loss_document_set_exact",
    "no_coverage_regression",
    "override_restored",
    "raw_blocks_exact",
    "treatment_all_blocks_covered",
    "treatment_surface_equal_raw_every_document",
    "treatment_zero_missing",
    "unaffected_fingerprint_multisets_equal",
    "unchanged_document_count_exact",
    "zero_adjudication",
    "zero_external_cost",
)
M27_POPULATION = {
    "baseline_covered_blocks": 333061,
    "baseline_missing_blocks": 100,
    "baseline_rows": 31212,
    "changed_documents": 27,
    "documents": 1068,
    "raw_blocks": 333161,
    "treatment_covered_blocks": 333161,
    "treatment_missing_blocks": 0,
    "treatment_rows": 31226,
    "unchanged_documents": 1041,
}
M28_CHECK_KEYS = (
    "candidate_identity_new",
    "contract_integrity",
    "external_calls_blocked",
    "generation_identity_exact",
    "global_invariants_exact",
    "output_schema_exact",
    "population_exact",
    "raw_token_intervals_exact",
    "row_mapping_and_identity_exact",
    "source_exact",
    "treatment_projection_exact",
)
M28_POPULATION = {
    "changed_documents": 27,
    "coverage_gain_blocks": 100,
    "coverage_regression_blocks": 0,
    "covered_blocks": 333161,
    "delta_added_rows": 29,
    "delta_overlap_modified_rows": 15,
    "delta_pure_added_rows": 14,
    "delta_removed_rows": 15,
    "delta_unchanged_rows": 2529,
    "documents": 1068,
    "missing_blocks": 0,
    "raw_blocks": 333161,
    "rows": 31226,
    "titled_rows": 29413,
    "unchanged_documents": 1041,
    "untitled_rows": 1813,
    "validation_failures": 0,
}
DOCUMENT_KEYS = (
    "schema",
    "extraction_sha256",
    "raw_artifact_sha256",
    "raw_blocks",
    "baseline_covered_blocks",
    "baseline_missing_block_indexes",
    "candidate_covered_blocks",
    "candidate_missing_block_indexes",
    "coverage_gain_block_indexes",
    "coverage_regression_block_indexes",
    "fingerprint_multiset_changed",
    "m29_document_receipt_sha256",
)
RESOLUTION_KEYS = (
    "schema",
    "extraction_sha256",
    "source_block_index",
    "source_page_ordinal",
    "page",
    "kind",
    "text_sha256",
    "ledger_receipt_sha256",
    "baseline_disposition",
    "baseline_rule_id",
    "candidate_disposition",
    "m29_document_receipt_sha256",
    "resolution_evidence",
    "m29_resolution_receipt_sha256",
)
OUTPUT_KEYS = (
    "instrument",
    "schema_version",
    "status",
    "loadable",
    "authority",
    "candidate_evidence_mode",
    "candidate_per_document_receipts_persisted",
    "dependencies",
    "population",
    "documents",
    "resolved_baseline_missing_identities",
    "manifests",
    "checks",
    "failures",
    "cost",
    "authorization",
)
COST = {
    "database_reads": 0,
    "database_writes": 0,
    "model_calls": 0,
    "network_calls": 0,
    "raw_store_reads": 0,
    "chunk_executions": 0,
    "manual_adjudications": 0,
    "additional_candidate_executions": 0,
    "external_calls_blocked": True,
}
AUTHORIZATION_KEYS = (
    "preregistration_frozen",
    "execution_permit_valid",
    "raw_store_read",
    "chunk_execution",
    "manual_adjudication",
    "additional_candidate_execution",
    "M27A",
    "database",
    "network",
    "models",
    "embeddings",
    "retrieval",
    "context_generation",
    "load",
    "serving",
    "deploy",
    "facts_moved_to_ok",
    "M3",
)


class LedgerFailure(RuntimeError):
    def __init__(self, code: str):
        self.code = code if code in FAILURE_CODES else "internal_failure"
        super().__init__(self.code)


class PreflightFailure(LedgerFailure):
    def __init__(self, code: str, preregistration_frozen: bool = False, execution_permit_valid: bool = False):
        super().__init__(code)
        self.preregistration_frozen = preregistration_frozen
        self.execution_permit_valid = execution_permit_valid


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LedgerFailure("contract_integrity_failure") from exc


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LedgerFailure("contract_integrity_failure")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise LedgerFailure("contract_integrity_failure")
    return parsed


def _reject_constant(_: str) -> None:
    raise LedgerFailure("contract_integrity_failure")


def strict_json_bytes(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise LedgerFailure("contract_integrity_failure")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except LedgerFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise LedgerFailure("contract_integrity_failure") from exc


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_object(value: Any, code: str = "contract_integrity_failure") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LedgerFailure(code)
    return value


def _require_exact_keys(value: Any, keys: tuple[str, ...], code: str = "contract_integrity_failure") -> dict[str, Any]:
    obj = _require_object(value, code)
    if set(obj) != set(keys):
        raise LedgerFailure(code)
    return obj


def _require_sha(value: Any, code: str = "contract_integrity_failure") -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise LedgerFailure(code)
    return value


def _index_list(value: Any, raw_blocks: int, code: str) -> list[int]:
    if not isinstance(value, list) or any(not _is_int(item) or item < 0 or item >= raw_blocks for item in value):
        raise LedgerFailure(code)
    if value != sorted(set(value)):
        raise LedgerFailure(code)
    return value


def _resolve_file(root: Path, relative: str, code: str = "contract_integrity_failure") -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise LedgerFailure(code)
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise LedgerFailure(code)
    base = root.resolve()
    current = root
    if current.is_symlink():
        raise LedgerFailure(code)
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise LedgerFailure(code)
    try:
        resolved = current.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LedgerFailure(code) from exc
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise LedgerFailure(code)
    return resolved


def _authorization(preregistration_frozen: bool, execution_permit_valid: bool) -> dict[str, Any]:
    return {
        "preregistration_frozen": preregistration_frozen,
        "execution_permit_valid": execution_permit_valid,
        "raw_store_read": False,
        "chunk_execution": False,
        "manual_adjudication": False,
        "additional_candidate_execution": False,
        "M27A": False,
        "database": False,
        "network": False,
        "models": False,
        "embeddings": False,
        "retrieval": False,
        "context_generation": False,
        "load": False,
        "serving": False,
        "deploy": False,
        "facts_moved_to_ok": 0,
        "M3": "BLOCKED",
    }


def _failure_payload(code: str, preregistration_frozen: bool = False, execution_permit_valid: bool = False) -> dict[str, Any]:
    failure = code if code in FAILURE_CODES else "internal_failure"
    return {
        "instrument": "s117_m29_reconciled_loss_ledger_v1",
        "schema_version": 1,
        "status": "NO_GO",
        "loadable": False,
        "authority": "reconciled_frozen_evidence_raw_parsed_block_surface_only",
        "candidate_evidence_mode": "substituted_from_frozen_treatment_via_exact_projection_hash",
        "candidate_per_document_receipts_persisted": False,
        "dependencies": {role: ZERO_SHA for role in DEPENDENCY_ROLES},
        "population": {key: 0 for key in POPULATION_KEYS},
        "documents": [],
        "resolved_baseline_missing_identities": [],
        "manifests": {key: ZERO_SHA for key in MANIFEST_KEYS},
        "checks": {key: False for key in CHECK_KEYS},
        "failures": [failure],
        "cost": dict(COST),
        "authorization": _authorization(preregistration_frozen, execution_permit_valid),
    }


def _validate_m27(seed: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seed = _require_object(seed)
    if seed.get("instrument") != "s117_m27_loss_safe_chunking_probe_v2" or seed.get("authority") != "raw_store_parsed_block_surface_only" or seed.get("status") != "CONTRACT_GO_BASELINE_GO_TREATMENT_GO_DELTA_GO":
        raise LedgerFailure("contract_integrity_failure")
    statuses = _require_exact_keys(seed.get("statuses"), ("baseline_replay", "contract_integrity", "delta_accounted", "treatment_lossless"))
    if any(value != "GO" for value in statuses.values()):
        raise LedgerFailure("contract_integrity_failure")
    checks = _require_exact_keys(seed.get("checks"), M27_CHECK_KEYS)
    if any(value is not True for value in checks.values()):
        raise LedgerFailure("contract_integrity_failure")
    cost = _require_exact_keys(seed.get("cost"), ("database_reads", "database_writes", "model_calls", "network_calls"))
    if any(not _is_int(value) or value != 0 for value in cost.values()):
        raise LedgerFailure("contract_integrity_failure")
    population = _require_exact_keys(seed.get("population"), tuple(M27_POPULATION))
    if any(not _is_int(value) for value in population.values()) or population != M27_POPULATION:
        raise LedgerFailure("document_population_drift")
    raw_documents = seed.get("documents")
    if not isinstance(raw_documents, list):
        raise LedgerFailure("document_population_drift")

    projections: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_documents:
        row = _require_object(raw, "document_partition_failure")
        extraction = _require_sha(row.get("extraction_sha256"), "document_partition_failure")
        raw_artifact = _require_sha(row.get("raw_artifact_sha256"), "document_partition_failure")
        if extraction in seen:
            raise LedgerFailure("document_partition_failure")
        seen.add(extraction)
        raw_blocks = row.get("raw_blocks")
        baseline_covered = row.get("baseline_covered_blocks")
        treatment_covered = row.get("treatment_covered_blocks")
        treatment_rows = row.get("treatment_rows")
        if any(not _is_int(value) or value < 0 for value in (raw_blocks, baseline_covered, treatment_covered, treatment_rows)):
            raise LedgerFailure("document_partition_failure")
        baseline_missing = _index_list(row.get("baseline_missing_block_indexes"), raw_blocks, "document_partition_failure")
        candidate_missing = _index_list(row.get("treatment_missing_block_indexes"), raw_blocks, "document_partition_failure")
        gains = _index_list(row.get("coverage_gain_block_indexes"), raw_blocks, "document_partition_failure")
        regressions = _index_list(row.get("coverage_regression_block_indexes"), raw_blocks, "document_partition_failure")
        if baseline_covered != raw_blocks - len(baseline_missing) or treatment_covered != raw_blocks - len(candidate_missing):
            raise LedgerFailure("document_partition_failure")
        if gains != sorted(set(baseline_missing) - set(candidate_missing)):
            raise LedgerFailure("coverage_gain_drift")
        if regressions != sorted(set(candidate_missing) - set(baseline_missing)):
            raise LedgerFailure("coverage_regression_nonempty")
        changed = row.get("changed")
        surface_equal = row.get("treatment_surface_equal_raw")
        if not isinstance(changed, bool) or not isinstance(surface_equal, bool):
            raise LedgerFailure("document_partition_failure")
        surface_sha = _require_sha(row.get("treatment_surface_sha256"), "document_partition_failure")
        fingerprints_sha = _require_sha(row.get("treatment_fingerprint_multiset_sha256"), "document_partition_failure")
        projection = {
            "schema": "s117_m28_candidate_treatment_projection_v1",
            "extraction_sha256": extraction,
            "raw_artifact_sha256": raw_artifact,
            "raw_blocks": raw_blocks,
            "rows": treatment_rows,
            "covered_blocks": treatment_covered,
            "missing_block_indexes": candidate_missing,
            "surface_sha256": surface_sha,
            "surface_equal_raw": surface_equal,
            "fingerprint_multiset_sha256": fingerprints_sha,
            "coverage_gain_block_indexes": gains,
            "coverage_regression_block_indexes": regressions,
            "changed": changed,
        }
        base_document = {
            "schema": "s117_m29_document_reconciliation_v1",
            "extraction_sha256": extraction,
            "raw_artifact_sha256": raw_artifact,
            "raw_blocks": raw_blocks,
            "baseline_covered_blocks": baseline_covered,
            "baseline_missing_block_indexes": baseline_missing,
            "candidate_covered_blocks": treatment_covered,
            "candidate_missing_block_indexes": candidate_missing,
            "coverage_gain_block_indexes": gains,
            "coverage_regression_block_indexes": regressions,
            "fingerprint_multiset_changed": changed,
        }
        base_document["m29_document_receipt_sha256"] = sha256_bytes(canonical_json_bytes(base_document))
        projections.append(projection)
        documents.append(base_document)
    projections.sort(key=lambda row: row["extraction_sha256"])
    documents.sort(key=lambda row: row["extraction_sha256"])
    if len(documents) != 1068:
        raise LedgerFailure("document_population_drift")
    projection_bytes = canonical_json_bytes(projections)
    if len(projection_bytes) != EXPECTED_PROJECTION_BYTES or sha256_bytes(projection_bytes) != EXPECTED_PROJECTION_SHA256:
        raise LedgerFailure("candidate_projection_bridge_failure")
    return projections, documents


def _validate_m28(receipt: Any) -> dict[str, Any]:
    top_keys = (
        "authority", "authorization", "checks", "cost", "dependencies", "failures",
        "generation", "instrument", "loadable", "manifests", "population",
        "schema_version", "source", "status",
    )
    receipt = _require_exact_keys(receipt, top_keys, "candidate_seed_drift")
    if receipt["instrument"] != "s117_m28_candidate_materialization_v1" or not _is_int(receipt["schema_version"]) or receipt["schema_version"] != 1 or receipt["status"] != "GO" or receipt["loadable"] is not False or receipt["authority"] != "raw_store_parsed_block_whitespace_token_surface_only" or receipt["failures"] != []:
        raise LedgerFailure("candidate_seed_drift")
    checks = _require_exact_keys(receipt["checks"], M28_CHECK_KEYS, "candidate_seed_drift")
    if any(value is not True for value in checks.values()):
        raise LedgerFailure("candidate_seed_drift")
    cost = _require_exact_keys(receipt["cost"], ("database_reads", "database_writes", "external_calls_blocked", "model_calls", "network_calls"), "candidate_seed_drift")
    if (
        any(not _is_int(cost[key]) or cost[key] != 0 for key in ("database_reads", "database_writes", "model_calls", "network_calls"))
        or cost["external_calls_blocked"] is not True
    ):
        raise LedgerFailure("candidate_seed_drift")
    population = _require_exact_keys(receipt["population"], tuple(M28_POPULATION), "candidate_seed_drift")
    if any(not _is_int(value) for value in population.values()) or population != M28_POPULATION:
        raise LedgerFailure("candidate_seed_drift")
    manifests = _require_exact_keys(receipt["manifests"], ("candidate_document_receipts_sha256", "candidate_projection_sha256", "candidate_row_ids_sha256", "coverage_gain_identities_sha256"), "candidate_seed_drift")
    if manifests["candidate_projection_sha256"] != EXPECTED_PROJECTION_SHA256 or manifests["candidate_document_receipts_sha256"] != EXPECTED_CANDIDATE_DOCUMENT_RECEIPTS_SHA256 or manifests["coverage_gain_identities_sha256"] != EXPECTED_COVERAGE_GAIN_IDENTITIES_SHA256:
        raise LedgerFailure("candidate_projection_bridge_failure")
    _require_sha(manifests["candidate_row_ids_sha256"], "candidate_seed_drift")
    return receipt


def _compact_rows(compact: Any) -> list[dict[str, Any]]:
    compact = _require_exact_keys(compact, ("authority", "authorization", "counts", "instrument", "logical_payload_sha256", "rows", "source", "unique_unruled_texts"), "compact_integrity_failure")
    if compact["instrument"] != "s117_m27_compact_loss_report_v1" or compact["authority"] != "diagnostic_only_no_policy_or_semantic_adjudication" or compact["logical_payload_sha256"] != EXPECTED_COMPACT_LOGICAL_SHA256:
        raise LedgerFailure("compact_integrity_failure")
    logical = dict(compact)
    logical.pop("logical_payload_sha256")
    if sha256_bytes(canonical_json_bytes(logical)) != EXPECTED_COMPACT_LOGICAL_SHA256:
        raise LedgerFailure("compact_integrity_failure")
    counts = _require_exact_keys(compact["counts"], ("dispositions", "documents", "rows", "unique_unruled_texts", "unruled_surface_categories"), "compact_integrity_failure")
    if (
        any(not _is_int(counts[key]) for key in ("rows", "documents", "unique_unruled_texts"))
        or counts["rows"] != 100
        or counts["documents"] != 27
        or counts["unique_unruled_texts"] != 24
        or counts["dispositions"] != {"authorized_exclusion": 13, "unruled_loss": 87}
        or counts["unruled_surface_categories"]
        != {"alpha_numeric_mixed": 10, "ascii_decimal_only": 5, "lexical_no_digits": 7, "symbol_only": 65}
    ):
        raise LedgerFailure("compact_integrity_failure")
    unique_texts = compact["unique_unruled_texts"]
    if not isinstance(unique_texts, list) or len(unique_texts) != 24 or unique_texts != sorted(set(unique_texts)) or any(not isinstance(item, str) for item in unique_texts):
        raise LedgerFailure("compact_integrity_failure")
    raw_rows = compact["rows"]
    if not isinstance(raw_rows, list) or len(raw_rows) != 100:
        raise LedgerFailure("compact_integrity_failure")
    result: list[dict[str, Any]] = []
    identities: set[tuple[str, int]] = set()
    for raw in raw_rows:
        row = _require_object(raw, "compact_integrity_failure")
        extraction = _require_sha(row.get("extraction_sha256"), "compact_integrity_failure")
        block_index = row.get("source_block_index")
        page_ordinal = row.get("source_page_ordinal")
        page = row.get("page")
        if any(not _is_int(value) for value in (block_index, page_ordinal, page)) or block_index < 0 or page_ordinal < 0 or page < 1:
            raise LedgerFailure("compact_integrity_failure")
        identity = (extraction, block_index)
        if identity in identities:
            raise LedgerFailure("compact_integrity_failure")
        identities.add(identity)
        kind = row.get("kind")
        if kind not in ("heading", "paragraph", "table"):
            raise LedgerFailure("compact_integrity_failure")
        text = row.get("text")
        text_sha = _require_sha(row.get("text_sha256"), "compact_integrity_failure")
        if not isinstance(text, str) or sha256_bytes(text.encode("utf-8")) != text_sha:
            raise LedgerFailure("compact_integrity_failure")
        ledger_receipt = _require_sha(row.get("ledger_receipt_sha256"), "compact_integrity_failure")
        disposition = row.get("disposition")
        rule_id = row.get("rule_id")
        if disposition == "authorized_exclusion":
            if rule_id != "standalone_numeric_page_boundary_exact_v1":
                raise LedgerFailure("compact_integrity_failure")
        elif disposition == "unruled_loss":
            if rule_id is not None:
                raise LedgerFailure("compact_integrity_failure")
        else:
            raise LedgerFailure("compact_integrity_failure")
        result.append({
            "extraction_sha256": extraction,
            "source_block_index": block_index,
            "source_page_ordinal": page_ordinal,
            "page": page,
            "kind": kind,
            "text_sha256": text_sha,
            "ledger_receipt_sha256": ledger_receipt,
            "baseline_disposition": disposition,
            "baseline_rule_id": rule_id,
        })
    result.sort(key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    return result


def _manifest_payload(documents: list[dict[str, Any]], resolved: list[dict[str, Any]], baseline_missing: list[dict[str, Any]], candidate_missing: list[dict[str, Any]]) -> dict[str, str]:
    document_receipts = [
        {"extraction_sha256": row["extraction_sha256"], "m29_document_receipt_sha256": row["m29_document_receipt_sha256"]}
        for row in documents
    ]
    resolution_receipts = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": row["source_block_index"], "m29_resolution_receipt_sha256": row["m29_resolution_receipt_sha256"]}
        for row in resolved
    ]
    return {
        "documents_sha256": sha256_bytes(canonical_json_bytes(documents)),
        "document_receipts_sha256": sha256_bytes(canonical_json_bytes(document_receipts)),
        "resolved_baseline_missing_sha256": sha256_bytes(canonical_json_bytes(resolved)),
        "resolution_receipts_sha256": sha256_bytes(canonical_json_bytes(resolution_receipts)),
        "baseline_missing_identities_sha256": sha256_bytes(canonical_json_bytes(baseline_missing)),
        "candidate_missing_identities_sha256": sha256_bytes(canonical_json_bytes(candidate_missing)),
    }


def _coverage_gain_anchor(identities: list[dict[str, Any]]) -> str:
    normalized = [
        {
            "extraction_sha256": row["extraction_sha256"],
            "block_index": row["source_block_index"],
        }
        for row in identities
    ]
    return sha256_bytes(canonical_json_bytes(normalized))


def build_payload(m27_seed1: Any, m27_seed2: Any, compact: Any, m28_seed1: Any, m28_seed2: Any, dependencies: dict[str, str], seed: int) -> dict[str, Any]:
    if seed not in (1, 2) or set(dependencies) != set(DEPENDENCY_ROLES) or any(_require_sha(value) != value for value in dependencies.values()):
        raise LedgerFailure("contract_integrity_failure")
    projection1, documents1 = _validate_m27(m27_seed1)
    projection2, documents2 = _validate_m27(m27_seed2)
    if canonical_json_bytes(projection1) != canonical_json_bytes(projection2) or canonical_json_bytes(documents1) != canonical_json_bytes(documents2):
        raise LedgerFailure("m27c_seed_drift")
    candidate1 = _validate_m28(m28_seed1)
    candidate2 = _validate_m28(m28_seed2)
    if canonical_json_bytes(candidate1) != canonical_json_bytes(candidate2):
        raise LedgerFailure("candidate_seed_drift")
    if candidate1["manifests"]["candidate_projection_sha256"] != sha256_bytes(canonical_json_bytes(projection1)):
        raise LedgerFailure("candidate_projection_bridge_failure")

    documents = list(documents1)
    random.Random(seed).shuffle(documents)
    documents.sort(key=lambda row: row["extraction_sha256"])
    by_extraction = {row["extraction_sha256"]: row for row in documents}
    baseline_missing = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["baseline_missing_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    candidate_missing = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["candidate_missing_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    gains = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["coverage_gain_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    regressions = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["coverage_regression_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    compact_rows = _compact_rows(compact)
    compact_identities = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": row["source_block_index"]}
        for row in compact_rows
    ]
    if compact_identities != baseline_missing:
        raise LedgerFailure("baseline_missing_identity_drift")
    if candidate_missing:
        raise LedgerFailure("candidate_missing_nonempty")
    if gains != baseline_missing:
        raise LedgerFailure("coverage_gain_drift")
    if _coverage_gain_anchor(gains) != EXPECTED_COVERAGE_GAIN_IDENTITIES_SHA256:
        raise LedgerFailure("coverage_gain_drift")
    if regressions:
        raise LedgerFailure("coverage_regression_nonempty")

    resolved: list[dict[str, Any]] = []
    gain_set = {(row["extraction_sha256"], row["source_block_index"]) for row in gains}
    candidate_missing_set = {(row["extraction_sha256"], row["source_block_index"]) for row in candidate_missing}
    shuffled_rows = list(compact_rows)
    random.Random(seed ^ 0x5A17).shuffle(shuffled_rows)
    for compact_row in shuffled_rows:
        identity = (compact_row["extraction_sha256"], compact_row["source_block_index"])
        document = by_extraction.get(compact_row["extraction_sha256"])
        if document is None or identity not in gain_set or identity in candidate_missing_set:
            raise LedgerFailure("resolved_identity_binding_failure")
        resolution = {
            "schema": "s117_m29_resolved_baseline_missing_identity_v1",
            **compact_row,
            "candidate_disposition": "covered",
            "m29_document_receipt_sha256": document["m29_document_receipt_sha256"],
            "resolution_evidence": "substituted_treatment_document_via_candidate_projection_sha256_4cd69ba2912a",
        }
        resolution["m29_resolution_receipt_sha256"] = sha256_bytes(canonical_json_bytes(resolution))
        resolved.append(resolution)
    resolved.sort(key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    if len(resolved) != 100:
        raise LedgerFailure("resolved_identity_binding_failure")

    dispositions = {"authorized_exclusion": 0, "unruled_loss": 0}
    for row in resolved:
        dispositions[row["baseline_disposition"]] += 1
    population = {
        "documents": len(documents),
        "raw_blocks": sum(row["raw_blocks"] for row in documents),
        "baseline_covered_blocks": sum(row["baseline_covered_blocks"] for row in documents),
        "baseline_missing_blocks": len(baseline_missing),
        "candidate_covered_blocks": sum(row["candidate_covered_blocks"] for row in documents),
        "candidate_missing_blocks": len(candidate_missing),
        "coverage_gain_blocks": len(gains),
        "coverage_regression_blocks": len(regressions),
        "changed_fingerprint_multiset_documents": sum(1 for row in documents if row["fingerprint_multiset_changed"]),
        "unchanged_fingerprint_multiset_documents": sum(1 for row in documents if not row["fingerprint_multiset_changed"]),
        "baseline_authorized_exclusion_identities": dispositions["authorized_exclusion"],
        "baseline_unruled_loss_identities": dispositions["unruled_loss"],
        "reconciled_baseline_missing_identities": len(resolved),
        "unresolved_baseline_missing_identities": len(baseline_missing) - len(resolved),
    }
    if population != EXPECTED_POPULATION:
        raise LedgerFailure("document_population_drift")
    manifests = _manifest_payload(documents, resolved, baseline_missing, candidate_missing)
    payload = {
        "instrument": "s117_m29_reconciled_loss_ledger_v1",
        "schema_version": 1,
        "status": "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY",
        "loadable": False,
        "authority": "reconciled_frozen_evidence_raw_parsed_block_surface_only",
        "candidate_evidence_mode": "substituted_from_frozen_treatment_via_exact_projection_hash",
        "candidate_per_document_receipts_persisted": False,
        "dependencies": dict(sorted(dependencies.items())),
        "population": population,
        "documents": documents,
        "resolved_baseline_missing_identities": resolved,
        "manifests": manifests,
        "checks": {key: True for key in CHECK_KEYS},
        "failures": [],
        "cost": dict(COST),
        "authorization": _authorization(True, True),
    }
    validate_output(payload)
    return payload


def validate_output(payload: Any) -> None:
    payload = _require_exact_keys(payload, OUTPUT_KEYS, "output_schema_failure")
    if payload["instrument"] != "s117_m29_reconciled_loss_ledger_v1" or not _is_int(payload["schema_version"]) or payload["schema_version"] != 1 or payload["loadable"] is not False or payload["authority"] != "reconciled_frozen_evidence_raw_parsed_block_surface_only" or payload["candidate_evidence_mode"] != "substituted_from_frozen_treatment_via_exact_projection_hash" or payload["candidate_per_document_receipts_persisted"] is not False:
        raise LedgerFailure("output_schema_failure")
    dependencies = _require_exact_keys(payload["dependencies"], DEPENDENCY_ROLES, "output_schema_failure")
    if any(_require_sha(value, "output_schema_failure") != value for value in dependencies.values()):
        raise LedgerFailure("output_schema_failure")
    population = _require_exact_keys(payload["population"], POPULATION_KEYS, "output_schema_failure")
    if any(not _is_int(value) or value < 0 for value in population.values()):
        raise LedgerFailure("output_schema_failure")
    checks = _require_exact_keys(payload["checks"], CHECK_KEYS, "output_schema_failure")
    if any(type(value) is not bool for value in checks.values()):
        raise LedgerFailure("output_schema_failure")
    manifests = _require_exact_keys(payload["manifests"], MANIFEST_KEYS, "output_schema_failure")
    if any(_require_sha(value, "output_schema_failure") != value for value in manifests.values()):
        raise LedgerFailure("output_schema_failure")
    cost = _require_exact_keys(payload["cost"], tuple(COST), "output_schema_failure")
    if (
        any(
            not _is_int(cost[key]) or cost[key] != 0
            for key in (
                "database_reads", "database_writes", "model_calls", "network_calls",
                "raw_store_reads", "chunk_executions", "manual_adjudications",
                "additional_candidate_executions",
            )
        )
        or cost["external_calls_blocked"] is not True
    ):
        raise LedgerFailure("output_schema_failure")
    authorization = _require_exact_keys(payload["authorization"], AUTHORIZATION_KEYS, "output_schema_failure")
    authorization_bool_keys = (
        "preregistration_frozen", "execution_permit_valid", "raw_store_read",
        "chunk_execution", "manual_adjudication", "additional_candidate_execution",
        "M27A", "database", "network", "models", "embeddings", "retrieval",
        "context_generation", "load", "serving", "deploy",
    )
    if any(type(authorization[key]) is not bool for key in authorization_bool_keys):
        raise LedgerFailure("output_schema_failure")
    if not _is_int(authorization["facts_moved_to_ok"]) or authorization["facts_moved_to_ok"] != 0 or authorization["M3"] != "BLOCKED":
        raise LedgerFailure("output_schema_failure")
    if authorization["execution_permit_valid"] and not authorization["preregistration_frozen"]:
        raise LedgerFailure("output_schema_failure")
    fixed_authorization = _authorization(authorization["preregistration_frozen"], authorization["execution_permit_valid"])
    if authorization != fixed_authorization:
        raise LedgerFailure("output_schema_failure")
    failures = payload["failures"]
    if (
        not isinstance(failures, list)
        or any(code not in FAILURE_CODES for code in failures)
        or len(failures) != len(set(failures))
        or failures != sorted(failures, key=FAILURE_CODES.index)
    ):
        raise LedgerFailure("output_schema_failure")
    documents = payload["documents"]
    resolved = payload["resolved_baseline_missing_identities"]
    if not isinstance(documents, list) or not isinstance(resolved, list):
        raise LedgerFailure("output_schema_failure")
    if payload["status"] == "NO_GO":
        if documents or resolved or population != {key: 0 for key in POPULATION_KEYS} or manifests != {key: ZERO_SHA for key in MANIFEST_KEYS} or dependencies != {key: ZERO_SHA for key in DEPENDENCY_ROLES} or any(value is not False for value in checks.values()) or len(failures) != 1:
            raise LedgerFailure("output_schema_failure")
        return
    if payload["status"] != "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY" or failures or any(value is not True for value in checks.values()) or population != EXPECTED_POPULATION or not authorization["preregistration_frozen"] or not authorization["execution_permit_valid"] or any(value == ZERO_SHA for value in dependencies.values()):
        raise LedgerFailure("output_schema_failure")
    if documents != sorted(documents, key=lambda row: row.get("extraction_sha256", "")) or resolved != sorted(resolved, key=lambda row: (row.get("extraction_sha256", ""), row.get("source_block_index", -1))):
        raise LedgerFailure("output_schema_failure")
    seen_documents: set[str] = set()
    for document in documents:
        _require_exact_keys(document, DOCUMENT_KEYS, "output_schema_failure")
        if document.get("schema") != "s117_m29_document_reconciliation_v1":
            raise LedgerFailure("output_schema_failure")
        extraction = _require_sha(document.get("extraction_sha256"), "output_schema_failure")
        _require_sha(document.get("raw_artifact_sha256"), "output_schema_failure")
        if extraction in seen_documents:
            raise LedgerFailure("output_schema_failure")
        seen_documents.add(extraction)
        raw_blocks = document.get("raw_blocks")
        baseline_covered = document.get("baseline_covered_blocks")
        candidate_covered = document.get("candidate_covered_blocks")
        if any(not _is_int(value) or value < 0 for value in (raw_blocks, baseline_covered, candidate_covered)):
            raise LedgerFailure("output_schema_failure")
        baseline_indexes = _index_list(document.get("baseline_missing_block_indexes"), raw_blocks, "output_schema_failure")
        candidate_indexes = _index_list(document.get("candidate_missing_block_indexes"), raw_blocks, "output_schema_failure")
        gain_indexes = _index_list(document.get("coverage_gain_block_indexes"), raw_blocks, "output_schema_failure")
        regression_indexes = _index_list(document.get("coverage_regression_block_indexes"), raw_blocks, "output_schema_failure")
        if (
            baseline_covered != raw_blocks - len(baseline_indexes)
            or candidate_covered != raw_blocks - len(candidate_indexes)
            or gain_indexes != sorted(set(baseline_indexes) - set(candidate_indexes))
            or regression_indexes != sorted(set(candidate_indexes) - set(baseline_indexes))
            or not isinstance(document.get("fingerprint_multiset_changed"), bool)
        ):
            raise LedgerFailure("output_schema_failure")
        receipt = dict(document)
        observed = _require_sha(receipt.pop("m29_document_receipt_sha256"), "output_schema_failure")
        if sha256_bytes(canonical_json_bytes(receipt)) != observed:
            raise LedgerFailure("output_schema_failure")
    document_receipts = {
        row["extraction_sha256"]: row["m29_document_receipt_sha256"]
        for row in documents
    }
    seen_resolutions: set[tuple[str, int]] = set()
    for resolution in resolved:
        _require_exact_keys(resolution, RESOLUTION_KEYS, "output_schema_failure")
        if resolution.get("schema") != "s117_m29_resolved_baseline_missing_identity_v1":
            raise LedgerFailure("output_schema_failure")
        extraction = _require_sha(resolution.get("extraction_sha256"), "output_schema_failure")
        block_index = resolution.get("source_block_index")
        page_ordinal = resolution.get("source_page_ordinal")
        page = resolution.get("page")
        if any(not _is_int(value) for value in (block_index, page_ordinal, page)) or block_index < 0 or page_ordinal < 0 or page < 1:
            raise LedgerFailure("output_schema_failure")
        identity = (extraction, block_index)
        if identity in seen_resolutions:
            raise LedgerFailure("output_schema_failure")
        seen_resolutions.add(identity)
        if resolution.get("kind") not in ("heading", "paragraph", "table"):
            raise LedgerFailure("output_schema_failure")
        _require_sha(resolution.get("text_sha256"), "output_schema_failure")
        _require_sha(resolution.get("ledger_receipt_sha256"), "output_schema_failure")
        disposition = resolution.get("baseline_disposition")
        rule = resolution.get("baseline_rule_id")
        if not (
            (disposition == "authorized_exclusion" and rule == "standalone_numeric_page_boundary_exact_v1")
            or (disposition == "unruled_loss" and rule is None)
        ):
            raise LedgerFailure("output_schema_failure")
        if (
            resolution.get("candidate_disposition") != "covered"
            or resolution.get("resolution_evidence") != "substituted_treatment_document_via_candidate_projection_sha256_4cd69ba2912a"
            or resolution.get("m29_document_receipt_sha256") != document_receipts.get(extraction)
        ):
            raise LedgerFailure("output_schema_failure")
        receipt = dict(resolution)
        observed = _require_sha(receipt.pop("m29_resolution_receipt_sha256"), "output_schema_failure")
        if sha256_bytes(canonical_json_bytes(receipt)) != observed:
            raise LedgerFailure("output_schema_failure")
    baseline_missing = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
        for row in documents for index in row["baseline_missing_block_indexes"]
    ]
    baseline_missing.sort(key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    candidate_missing = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
        for row in documents for index in row["candidate_missing_block_indexes"]
    ]
    candidate_missing.sort(key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    gains = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
        for row in documents for index in row["coverage_gain_block_indexes"]
    ]
    gains.sort(key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    regressions = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
        for row in documents for index in row["coverage_regression_block_indexes"]
    ]
    resolved_identities = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": row["source_block_index"]}
        for row in resolved
    ]
    if (
        candidate_missing
        or regressions
        or gains != baseline_missing
        or resolved_identities != baseline_missing
        or _coverage_gain_anchor(gains) != EXPECTED_COVERAGE_GAIN_IDENTITIES_SHA256
    ):
        raise LedgerFailure("output_schema_failure")
    observed_population = {
        "documents": len(documents),
        "raw_blocks": sum(row["raw_blocks"] for row in documents),
        "baseline_covered_blocks": sum(row["baseline_covered_blocks"] for row in documents),
        "baseline_missing_blocks": len(baseline_missing),
        "candidate_covered_blocks": sum(row["candidate_covered_blocks"] for row in documents),
        "candidate_missing_blocks": len(candidate_missing),
        "coverage_gain_blocks": len(gains),
        "coverage_regression_blocks": len(regressions),
        "changed_fingerprint_multiset_documents": sum(1 for row in documents if row["fingerprint_multiset_changed"]),
        "unchanged_fingerprint_multiset_documents": sum(1 for row in documents if not row["fingerprint_multiset_changed"]),
        "baseline_authorized_exclusion_identities": sum(1 for row in resolved if row["baseline_disposition"] == "authorized_exclusion"),
        "baseline_unruled_loss_identities": sum(1 for row in resolved if row["baseline_disposition"] == "unruled_loss"),
        "reconciled_baseline_missing_identities": len(resolved),
        "unresolved_baseline_missing_identities": len(baseline_missing) - len(resolved),
    }
    if population != observed_population:
        raise LedgerFailure("output_schema_failure")
    if manifests != _manifest_payload(documents, resolved, baseline_missing, candidate_missing):
        raise LedgerFailure("manifest_integrity_failure")


def _validate_prereg(prereg: Any) -> dict[str, Any]:
    prereg = _require_exact_keys(prereg, ("instrument", "schema_version", "status", "scope", "frozen_inputs", "expected", "execution", "authorization"))
    if prereg["instrument"] != "s117_m29_reconciled_loss_ledger_prereg_v1" or not _is_int(prereg["schema_version"]) or prereg["schema_version"] != 1 or prereg["status"] != "frozen_before_execution":
        raise LedgerFailure("contract_integrity_failure")
    frozen = _require_exact_keys(prereg["frozen_inputs"], tuple(SELECTED_PATHS))
    for role, expected_path in SELECTED_PATHS.items():
        item = _require_exact_keys(frozen[role], ("path", "sha256", "format", "use"))
        if item["path"] != expected_path or item["format"] != ("JSON" if role in PARSED_ROLES else "blob") or item["use"] != ("parsed" if role in PARSED_ROLES else "hash-only"):
            raise LedgerFailure("contract_integrity_failure")
        _require_sha(item["sha256"])
    expected = _require_exact_keys(prereg["expected"], ("projection", "population", "check_keys", "failure_codes", "dependency_roles"))
    if expected["projection"] != {"bytes": EXPECTED_PROJECTION_BYTES, "sha256": EXPECTED_PROJECTION_SHA256} or expected["population"] != EXPECTED_POPULATION or expected["check_keys"] != list(CHECK_KEYS) or expected["failure_codes"] != list(FAILURE_CODES) or expected["dependency_roles"] != list(DEPENDENCY_ROLES):
        raise LedgerFailure("contract_integrity_failure")
    execution = _require_exact_keys(prereg["execution"], ("seeds", "outputs", "perturbation", "required"))
    if execution["seeds"] != [1, 2] or execution["outputs"] != {"1": OUTPUT_RELATIVES[1], "2": OUTPUT_RELATIVES[2]} or execution["perturbation"] != "shuffle_documents_and_resolutions_then_restore_canonical_order" or not isinstance(execution["required"], list):
        raise LedgerFailure("contract_integrity_failure")
    scope = _require_exact_keys(prereg["scope"], ("purpose", "authority", "allowed", "forbidden"))
    if scope["purpose"] != "derive_reconciled_loss_ledger_from_frozen_evidence" or scope["authority"] != "reconciled_frozen_evidence_raw_parsed_block_surface_only" or not isinstance(scope["allowed"], list) or not isinstance(scope["forbidden"], list):
        raise LedgerFailure("contract_integrity_failure")
    authorization = _require_exact_keys(prereg["authorization"], ("preregistration_frozen", "ledger_execution", "raw_store_read", "chunk_execution", "database", "network", "models", "load", "serving", "deploy", "facts_moved_to_ok", "M3"))
    if any(type(authorization[key]) is not bool for key in ("preregistration_frozen", "ledger_execution", "raw_store_read", "chunk_execution", "database", "network", "models", "load", "serving", "deploy")) or not _is_int(authorization["facts_moved_to_ok"]):
        raise LedgerFailure("contract_integrity_failure")
    if authorization != {"preregistration_frozen": True, "ledger_execution": False, "raw_store_read": False, "chunk_execution": False, "database": False, "network": False, "models": False, "load": False, "serving": False, "deploy": False, "facts_moved_to_ok": 0, "M3": "BLOCKED"}:
        raise LedgerFailure("contract_integrity_failure")
    return prereg


def _validate_permit(permit: Any, seed: int, prereg_sha: str, prereg: dict[str, Any]) -> dict[str, Any]:
    permit = _require_exact_keys(permit, ("instrument", "schema_version", "status", "bindings", "allowed_seeds", "additional_candidate_execution", "authorization"))
    if permit["instrument"] != "s117_m29_reconciled_loss_ledger_execution_permit_v1" or not _is_int(permit["schema_version"]) or permit["schema_version"] != 1 or permit["status"] != "authorized_two_seeded_local_ledger_executions" or permit["allowed_seeds"] != [1, 2] or seed not in permit["allowed_seeds"] or permit["additional_candidate_execution"] is not False:
        raise LedgerFailure("contract_integrity_failure")
    bindings = _require_exact_keys(permit["bindings"], ("preregistration_sha256", "design_v2_sha256", "runner_sha256", "runner_tests_sha256"))
    if bindings != {"preregistration_sha256": prereg_sha, "design_v2_sha256": prereg["frozen_inputs"]["design_v2"]["sha256"], "runner_sha256": prereg["frozen_inputs"]["runner"]["sha256"], "runner_tests_sha256": prereg["frozen_inputs"]["runner_tests"]["sha256"]}:
        raise LedgerFailure("contract_integrity_failure")
    authorization = _require_exact_keys(permit["authorization"], ("ledger_execution", "raw_store_read", "chunk_execution", "database", "network", "models", "load", "serving", "deploy", "facts_moved_to_ok", "M3"))
    if any(type(authorization[key]) is not bool for key in ("ledger_execution", "raw_store_read", "chunk_execution", "database", "network", "models", "load", "serving", "deploy")) or not _is_int(authorization["facts_moved_to_ok"]):
        raise LedgerFailure("contract_integrity_failure")
    if authorization != {"ledger_execution": True, "raw_store_read": False, "chunk_execution": False, "database": False, "network": False, "models": False, "load": False, "serving": False, "deploy": False, "facts_moved_to_ok": 0, "M3": "BLOCKED"}:
        raise LedgerFailure("contract_integrity_failure")
    return permit


def _load_authorized(seed: int, root: Path = ROOT) -> tuple[dict[str, bytes], dict[str, str]]:
    prereg_path = _resolve_file(root, PREREG_RELATIVE)
    prereg_raw = prereg_path.read_bytes()
    try:
        prereg = _validate_prereg(strict_json_bytes(prereg_raw))
    except LedgerFailure as exc:
        raise PreflightFailure(exc.code) from exc
    observed: dict[str, str] = {}
    raws: dict[str, bytes] = {}
    try:
        for role, expected_path in SELECTED_PATHS.items():
            path = _resolve_file(root, expected_path)
            raw = path.read_bytes()
            digest = sha256_bytes(raw)
            if digest != prereg["frozen_inputs"][role]["sha256"]:
                raise LedgerFailure("contract_integrity_failure")
            observed[role] = digest
            if role in PARSED_ROLES:
                raws[role] = raw
    except LedgerFailure as exc:
        raise PreflightFailure(exc.code) from exc
    prereg_sha = sha256_bytes(prereg_raw)
    try:
        permit_path = _resolve_file(root, PERMIT_RELATIVE)
        permit_raw = permit_path.read_bytes()
        _validate_permit(strict_json_bytes(permit_raw), seed, prereg_sha, prereg)
    except (LedgerFailure, OSError) as exc:
        code = exc.code if isinstance(exc, LedgerFailure) else "contract_integrity_failure"
        raise PreflightFailure(code, preregistration_frozen=True) from exc
    dependencies = {
        **observed,
        "preregistration": prereg_sha,
        "execution_permit": sha256_bytes(permit_raw),
    }
    return raws, dict(sorted(dependencies.items()))


def _parse_seed(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "--seed" or argv[1] not in ("1", "2"):
        raise LedgerFailure("contract_integrity_failure")
    return int(argv[1])


def _resolve_output(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise LedgerFailure("contract_integrity_failure")
    parts = relative.split("/")
    if len(parts) < 2 or any(part in ("", ".", "..") for part in parts):
        raise LedgerFailure("contract_integrity_failure")
    base = root.resolve()
    if root.is_symlink():
        raise LedgerFailure("contract_integrity_failure")
    parent = root
    for part in parts[:-1]:
        parent = parent / part
        if parent.is_symlink():
            raise LedgerFailure("contract_integrity_failure")
        if parent.exists():
            if not parent.is_dir():
                raise LedgerFailure("contract_integrity_failure")
        else:
            try:
                parent.mkdir()
            except OSError as exc:
                raise LedgerFailure("contract_integrity_failure") from exc
        if parent.is_symlink() or not parent.resolve().is_relative_to(base):
            raise LedgerFailure("contract_integrity_failure")
    output = parent / parts[-1]
    if output.is_symlink() or output.exists():
        raise LedgerFailure("contract_integrity_failure")
    if not parent.resolve().is_relative_to(base):
        raise LedgerFailure("contract_integrity_failure")
    return output


def _write_payload(root: Path, relative: str, payload: dict[str, Any]) -> None:
    validate_output(payload)
    path = _resolve_output(root, relative)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(payload) + b"\n")
    except OSError as exc:
        raise LedgerFailure("contract_integrity_failure") from exc


def main(argv: list[str] | None = None) -> int:
    try:
        seed = _parse_seed(list(sys.argv[1:] if argv is None else argv))
    except LedgerFailure:
        return 2
    output_relative = OUTPUT_RELATIVES[seed]
    prereg_ok = False
    permit_ok = False
    original_socket = socket.socket
    try:
        raws, dependencies = _load_authorized(seed)
        prereg_ok = True
        permit_ok = True

        def blocked_socket(*_: Any, **__: Any) -> Any:
            raise LedgerFailure("external_call_attempt")

        socket.socket = blocked_socket
        parsed = {role: strict_json_bytes(raw) for role, raw in raws.items()}
        payload = build_payload(
            parsed["m27c_seed1"], parsed["m27c_seed2"], parsed["compact100"],
            parsed["m28_seed1"], parsed["m28_seed2"], dependencies, seed,
        )
        _write_payload(ROOT, output_relative, payload)
        print('{"failures":[],"status":"RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY"}')
        return 0
    except PreflightFailure as exc:
        prereg_ok = exc.preregistration_frozen
        permit_ok = exc.execution_permit_valid
        payload = _failure_payload(exc.code, prereg_ok, permit_ok)
    except LedgerFailure as exc:
        payload = _failure_payload(exc.code, prereg_ok, permit_ok)
    except Exception:
        payload = _failure_payload("internal_failure", prereg_ok, permit_ok)
    finally:
        socket.socket = original_socket
    try:
        _write_payload(ROOT, output_relative, payload)
    except Exception:
        return 1
    print(json.dumps({"failures": payload["failures"], "status": "NO_GO"}, separators=(",", ":"), sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
