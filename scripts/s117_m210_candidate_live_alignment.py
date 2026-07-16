from __future__ import annotations

import hashlib
import json
import math
import random
import socket
import sys
from pathlib import Path
from typing import Any
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
PREREG_RELATIVE = "evals/s117_m210_candidate_live_alignment_prereg_v1.json"
PERMIT_RELATIVE = "evals/s117_m210_candidate_live_alignment_execution_permit_v1.json"
OUTPUTS = {
    1: "evals/s117_m210_candidate_live_alignment_seed1_v1.json",
    2: "evals/s117_m210_candidate_live_alignment_seed2_v1.json",
}
SELECTED_PATHS = {
    "m27a_seed1": "evals/s117_m27_live_evidence_seed1_v1.json",
    "m27a_seed2": "evals/s117_m27_live_evidence_seed2_v1.json",
    "m27a_gate": "evals/s117_m27_live_evidence_gate_v1.yaml",
    "m27c_seed1": "evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json",
    "m27c_seed2": "evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json",
    "m27c_gate": "evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml",
    "m28_seed1": "evals/s117_m28_candidate_materialization_seed1_v1.json",
    "m28_seed2": "evals/s117_m28_candidate_materialization_seed2_v1.json",
    "m28_gate": "evals/s117_m28_candidate_materialization_gate_v1.yaml",
    "m29_seed1": "evals/s117_m29_reconciled_loss_ledger_seed1_v1.json",
    "m29_seed2": "evals/s117_m29_reconciled_loss_ledger_seed2_v1.json",
    "m29_gate": "evals/s117_m29_reconciled_loss_ledger_gate_v1.yaml",
    "design": "evals/s117_m210_candidate_live_alignment_design_v1.md",
    "runner": "scripts/s117_m210_candidate_live_alignment.py",
    "runner_tests": "tests/test_s117_m210_candidate_live_alignment.py",
}
PRIMARY_JSON_ROLES = ("m27a_seed1", "m27c_seed1", "m28_seed1", "m29_seed1")
SEED_PAIRS = (
    ("m27a_seed1", "m27a_seed2"),
    ("m27c_seed1", "m27c_seed2"),
    ("m28_seed1", "m28_seed2"),
    ("m29_seed1", "m29_seed2"),
)
DEPENDENCY_ROLES = tuple(sorted((*SELECTED_PATHS, "preregistration", "execution_permit")))
CHANGED_EXTRACTION = "8d128ca2ca13754bb74e0dcf16014e74141e352ae819aa25e35784c2f60245f6"
CHANGED_TASK = "acd5058d-06cf-5626-aabd-a93eb75b2f44"
CHANGED_TARGET_CONTENT_SHA = "995c4ac013e1dcb64dca7740592d61f15f07b27dc516357678cc7b0063865a17"
CHANGED_TARGET_FINGERPRINT_SHA = "83adfac4b272c0130e1d86d1851b55b29bc50e4f725aab8320c7cbe4602ec70d"
CHANGED_BASELINE_FINGERPRINT_SHA = "f87e6ec0eea220727a09870c81b4b5578142b555ee0f8656d1655260d5c836ac"
CHANGED_CANDIDATE_FINGERPRINT_SHA = "286610fb5e5771fd4d21fbe184222e1f437da198689c87566a3b0cd5ed180439"
PROJECTION_SHA = "4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881"
PROJECTION_BYTES = 640933
DOCUMENT_IDENTITIES_SHA = "e96ad542c470f858616248429fd82aada4c1e2bd2b1ae02b1a75f6843128195a"
TASK_IDENTITIES_SHA = "fc92a3d2dc194716ff6d0b4263b3abc31d2cdc744db707cb5e0d996c905a2fcc"
GAIN_ANCHOR_SHA = "6b0410a662c5523b04e3c19049199d8f27649653f34a6f3d87fee3a84147a675"
ZERO_SHA = "0" * 64

CHECK_KEYS = (
    "contract_integrity", "m27a_seed_equivalence", "m27c_seed_equivalence",
    "m28_seed_equivalence", "m29_seed_equivalence",
    "m27a_m27c_baseline_bridge_exact", "candidate_projection_bridge_exact",
    "affected_population_exact", "changed_intersection_exact",
    "document_alignment_exact", "target_fingerprints_unique",
    "overlap_fingerprints_unique", "changed_target_mapping_exact",
    "task_membership_exact", "manifest_integrity_exact", "output_schema_exact",
    "zero_external_cost",
)
FAILURE_CODES = (
    "contract_integrity_failure", "m27a_seed_drift", "m27c_seed_drift",
    "m28_seed_drift", "m29_seed_drift", "m27a_receipt_failure",
    "m27c_receipt_failure", "m27a_m27c_baseline_bridge_failure",
    "candidate_projection_bridge_failure", "affected_population_drift",
    "changed_intersection_drift", "document_alignment_failure",
    "target_membership_failure", "overlap_membership_failure",
    "changed_target_mapping_failure", "manifest_integrity_failure",
    "output_schema_failure", "external_call_attempt", "internal_failure",
)
COUNT_KEYS = (
    "documents", "tasks", "baseline_aligned_documents",
    "baseline_unresolved_documents", "candidate_aligned_documents",
    "candidate_unresolved_documents", "baseline_aligned_tasks",
    "baseline_unresolved_tasks", "candidate_aligned_tasks",
    "candidate_unresolved_tasks", "changed_affected_documents",
    "unchanged_affected_documents", "unique_target_memberships",
    "unique_overlap_memberships",
)
EXPECTED_COUNTS = {
    "documents": 18, "tasks": 21, "baseline_aligned_documents": 17,
    "baseline_unresolved_documents": 1, "candidate_aligned_documents": 18,
    "candidate_unresolved_documents": 0, "baseline_aligned_tasks": 20,
    "baseline_unresolved_tasks": 1, "candidate_aligned_tasks": 21,
    "candidate_unresolved_tasks": 0, "changed_affected_documents": 1,
    "unchanged_affected_documents": 17, "unique_target_memberships": 21,
    "unique_overlap_memberships": 21,
}
MANIFEST_KEYS = (
    "documents_sha256", "document_receipts_sha256", "tasks_sha256",
    "task_receipts_sha256", "affected_document_identities_sha256",
    "task_identities_sha256",
)
EXPECTED_OUTPUT_MANIFESTS = {
    "documents_sha256": "bf10c29a4a9e5d2f18d0551593ea0d0fa3b6cc255255f42f96e8ad64fcb726f6",
    "document_receipts_sha256": "30c44ca1acfff987d0a19dc70aac97fd3a1025bfbe480e78c958ce6b5deb0f16",
    "tasks_sha256": "9ff3b7a87005e83676bdc47f290b58904033de23839ddaf09886cefb15a6322a",
    "task_receipts_sha256": "deb09a07347caa54ca488dda335066ae1d71581087715f210ff4114cfb5347b1",
    "affected_document_identities_sha256": DOCUMENT_IDENTITIES_SHA,
    "task_identities_sha256": TASK_IDENTITIES_SHA,
}
DOCUMENT_KEYS = (
    "schema", "extraction_sha256", "baseline_alignment_status",
    "candidate_alignment_status", "candidate_surface_sha256",
    "raw_surface_sha256", "candidate_surface_equal_raw",
    "candidate_missing_block_indexes", "coverage_gain_block_indexes",
    "coverage_regression_block_indexes", "fingerprint_multiset_changed",
    "candidate_mapping_mode", "m210_document_receipt_sha256",
)
TASK_KEYS = (
    "schema", "local_row_id", "extraction_sha256",
    "original_task_evidence_receipt_sha256", "target_content_sha256",
    "target_fingerprint_sha256", "target_source_block_start",
    "target_source_block_end", "target_baseline_occurrences",
    "target_candidate_occurrences", "overlap_count",
    "overlap_fingerprints_sha256", "all_overlap_fingerprints_unique",
    "candidate_membership_mode", "candidate_ordinal",
    "changed_delta_disjoint_from_target", "baseline_alignment_status",
    "candidate_alignment_status", "m210_document_receipt_sha256",
    "m210_task_receipt_sha256",
)
OUTPUT_KEYS = (
    "instrument", "schema_version", "status", "loadable", "authority",
    "candidate_evidence_mode", "candidate_rows_persisted",
    "candidate_row_ids_claimed", "dependencies", "counts", "documents", "tasks",
    "manifests", "checks", "failures", "cost", "authorization",
)
COST = {
    "model_calls": 0, "network_calls": 0, "database_reads": 0,
    "database_writes": 0, "raw_store_reads": 0, "chunk_executions": 0,
    "candidate_executions": 0, "embedding_generations": 0,
    "context_generations": 0, "manual_adjudications": 0,
    "external_calls_blocked": True,
}
AUTH_BOOL_KEYS = (
    "preregistration_frozen", "execution_permit_valid", "M27A_repeat_gate",
    "adjudication", "raw_store_read", "chunk_execution",
    "additional_candidate_execution", "database", "network", "models",
    "embeddings", "retrieval", "rerank", "synthesis", "context_generation",
    "load", "serving", "deploy",
)

M27A_CHECK_KEYS = (
    "affected_documents_exact", "all_21_evidence_complete",
    "all_task_receipts_crosslinked", "live_tasks_exact",
    "m27_seed_bytes_identical", "m27_seed_receipts_valid",
    "original_complete_exact", "review_fiches_exact",
    "supplemented_incomplete_exact", "zero_adjudication",
    "zero_external_cost",
)
M27A_DOCUMENT_KEYS = (
    "alignment_status", "document_stream_whitespace_equal", "extraction_sha256",
    "first_surface_mismatch", "independent_validation_failures",
    "raw_artifact_base64", "raw_artifact_bytes", "raw_artifact_sha256",
    "raw_block_manifest_sha256", "raw_blocks", "raw_surface_sha256",
    "receipt_sha256", "row_by_row_regeneration_equal", "schema",
    "v3_row_manifest_sha256", "v3_rows", "v3_surface_sha256",
)
M27A_RAW_BLOCK_KEYS = (
    "kind", "lineage", "page", "receipt_sha256", "source_block_index",
    "text", "text_sha256",
)
M27A_ROW_KEYS = (
    "chunk_index", "chunker_sha256", "confidence", "content",
    "content_sha256", "duplicate_of", "extraction_sha256", "has_diagram",
    "id", "is_flow_diagram", "materialization_id", "page_number",
    "provenance_contract", "provenance_payload_sha256", "provenance_version",
    "raw_artifact_sha256", "receipt_sha256", "section_anchor",
    "section_lineage", "section_path", "section_title", "source_block_end",
    "source_block_start",
)
M27A_TASK_KEYS = (
    "adjudication_status", "boundary", "comparison_receipt_sha256",
    "evidence_complete", "extraction_sha256", "frozen_policy_evidence",
    "legacy_evidence_completion_verified", "legacy_evidence_mode",
    "legacy_evidence_receipt_sha256", "local_row_id", "mechanical_raw_alignment",
    "original_raw_evidence_sha256", "original_task_receipt_sha256",
    "overlap_manifest_sha256", "overlapping_v3_rows", "raw_block_window",
    "raw_block_window_manifest_sha256", "raw_document_receipt_sha256",
    "receipt_sha256", "schema", "target_row",
)

M27C_CHECK_KEYS = (
    "baseline_covered_exact", "baseline_manifest_exact",
    "baseline_missing_count_exact", "baseline_missing_exact",
    "baseline_rows_exact", "changed_documents_have_delta",
    "coverage_gain_exact", "delta_partitions_exact", "document_population_exact",
    "loss_document_set_exact", "no_coverage_regression", "override_restored",
    "raw_blocks_exact", "treatment_all_blocks_covered",
    "treatment_surface_equal_raw_every_document", "treatment_zero_missing",
    "unaffected_fingerprint_multisets_equal", "unchanged_document_count_exact",
    "zero_adjudication", "zero_external_cost",
)
M27C_POPULATION = {
    "documents": 1068, "raw_blocks": 333161, "baseline_rows": 31212,
    "baseline_covered_blocks": 333061, "baseline_missing_blocks": 100,
    "treatment_rows": 31226, "treatment_covered_blocks": 333161,
    "treatment_missing_blocks": 0, "changed_documents": 27,
    "unchanged_documents": 1041,
}
M27C_DOCUMENT_KEYS = (
    "baseline_covered_blocks", "baseline_fingerprint_multiset_sha256",
    "baseline_missing_block_indexes", "baseline_rows", "baseline_surface_sha256",
    "changed", "coverage_gain_block_indexes", "coverage_regression_block_indexes",
    "delta_counts", "delta_partition_exact", "extraction_sha256",
    "fingerprint_multiset_equal", "raw_artifact_sha256", "raw_blocks",
    "raw_surface_sha256", "receipt_sha256", "schema", "treatment_contract_sha256",
    "treatment_covered_blocks", "treatment_fingerprint_multiset_sha256",
    "treatment_missing_block_indexes", "treatment_rows",
    "treatment_surface_equal_raw", "treatment_surface_sha256",
)
M27C_MANIFESTS = {
    "baseline_missing_identities_sha256": "a9095775f042031012463384a372c20b283e326dde231caef4180541cc1ca780",
    "baseline_rows_sha256": "68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3",
    "deltas_sha256": "ab31ddfa3940042800c3fccd8ee9e1d6f5f2476cd84da843f46bbb1f21c11bd9",
    "documents_sha256": "d65d012b96cf7610bfd74ca0f5219f0a6aa5b96417ce02f6ab7e17449ce65c44",
    "treatment_missing_identities_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

M28_CHECK_KEYS = (
    "candidate_identity_new", "contract_integrity", "external_calls_blocked",
    "generation_identity_exact", "global_invariants_exact", "output_schema_exact",
    "population_exact", "raw_token_intervals_exact",
    "row_mapping_and_identity_exact", "source_exact", "treatment_projection_exact",
)
M28_POPULATION = {
    "documents": 1068, "raw_blocks": 333161, "rows": 31226,
    "titled_rows": 29413, "untitled_rows": 1813, "covered_blocks": 333161,
    "missing_blocks": 0, "coverage_gain_blocks": 100,
    "coverage_regression_blocks": 0, "changed_documents": 27,
    "unchanged_documents": 1041, "delta_unchanged_rows": 2529,
    "delta_removed_rows": 15, "delta_added_rows": 29,
    "delta_overlap_modified_rows": 15, "delta_pure_added_rows": 14,
    "validation_failures": 0,
}
M28_MANIFESTS = {
    "candidate_document_receipts_sha256": "57e4624d812188f97ea0bd9c81ccb76e6693fde40db41701ad60f3dd9edb293a",
    "candidate_projection_sha256": PROJECTION_SHA,
    "candidate_row_ids_sha256": "b6a4a2fe8e973ca05eb7d0e2e1558d591bbf70dc6f5fad8b172ba4b422523c3a",
    "coverage_gain_identities_sha256": GAIN_ANCHOR_SHA,
}

M29_CHECK_KEYS = (
    "baseline_missing_identity_set_exact", "candidate_missing_empty",
    "candidate_projection_bridge_exact", "candidate_seed_equivalence",
    "compact_integrity_exact", "contract_integrity", "coverage_gain_exact",
    "coverage_regression_empty", "document_partitions_exact",
    "document_population_exact", "m27c_seed_equivalence",
    "manifest_integrity_exact", "output_schema_exact",
    "resolved_identity_bindings_exact", "zero_external_cost",
)
M29_POPULATION = {
    "documents": 1068, "raw_blocks": 333161, "baseline_covered_blocks": 333061,
    "baseline_missing_blocks": 100, "candidate_covered_blocks": 333161,
    "candidate_missing_blocks": 0, "coverage_gain_blocks": 100,
    "coverage_regression_blocks": 0, "changed_fingerprint_multiset_documents": 27,
    "unchanged_fingerprint_multiset_documents": 1041,
    "baseline_authorized_exclusion_identities": 13,
    "baseline_unruled_loss_identities": 87,
    "reconciled_baseline_missing_identities": 100,
    "unresolved_baseline_missing_identities": 0,
}
M29_MANIFESTS = {
    "baseline_missing_identities_sha256": "627dea7dca437ea546c9110d9f844e76a7de0a5f2e3a3f2af6c4d43c3b7ee80e",
    "candidate_missing_identities_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "document_receipts_sha256": "f97211522b241251938b145cf3b84b2a75df62f2eabb706d93e63a21bb0c82cd",
    "documents_sha256": "cd46ab22a3288fadc04e4c540ce595175e4d709cd08aebd4e98e04c91d8456dd",
    "resolution_receipts_sha256": "0853022be9de7bd16695729ea002b318de9d4982202059f84dd407af64d43075",
    "resolved_baseline_missing_sha256": "a629340ae4e0144fbaf6ca7ae1f4fa13b00f6cda4075b7f9978b322f0444ffb1",
}
M29_DOCUMENT_KEYS = (
    "baseline_covered_blocks", "baseline_missing_block_indexes",
    "candidate_covered_blocks", "candidate_missing_block_indexes",
    "coverage_gain_block_indexes", "coverage_regression_block_indexes",
    "extraction_sha256", "fingerprint_multiset_changed",
    "m29_document_receipt_sha256", "raw_artifact_sha256", "raw_blocks", "schema",
)
M29_RESOLUTION_KEYS = (
    "baseline_disposition", "baseline_rule_id", "candidate_disposition",
    "extraction_sha256", "kind", "ledger_receipt_sha256",
    "m29_document_receipt_sha256", "m29_resolution_receipt_sha256", "page",
    "resolution_evidence", "schema", "source_block_index", "source_page_ordinal",
    "text_sha256",
)


class AlignmentFailure(RuntimeError):
    def __init__(self, code: str):
        self.code = code if code in FAILURE_CODES else "internal_failure"
        super().__init__(self.code)


class PreflightFailure(AlignmentFailure):
    def __init__(self, code: str, prereg: bool = False, permit: bool = False):
        super().__init__(code)
        self.prereg = prereg
        self.permit = permit


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AlignmentFailure("contract_integrity_failure") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AlignmentFailure("contract_integrity_failure")
        result[key] = value
    return result


def _float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise AlignmentFailure("contract_integrity_failure")
    return result


def strict_json(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AlignmentFailure("contract_integrity_failure")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_float, parse_constant=lambda _: (_ for _ in ()).throw(AlignmentFailure("contract_integrity_failure")))
    except AlignmentFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise AlignmentFailure("contract_integrity_failure") from exc


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _obj(value: Any, keys: tuple[str, ...] | None = None, code: str = "contract_integrity_failure") -> dict[str, Any]:
    if not isinstance(value, dict) or (keys is not None and set(value) != set(keys)):
        raise AlignmentFailure(code)
    return value


def _sha(value: Any, code: str = "contract_integrity_failure") -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise AlignmentFailure(code)
    return value


def _uuid(value: Any, code: str = "contract_integrity_failure") -> str:
    if not isinstance(value, str):
        raise AlignmentFailure(code)
    try:
        if str(UUID(value)) != value:
            raise ValueError
    except ValueError as exc:
        raise AlignmentFailure(code) from exc
    return value


def _index_list(value: Any, raw_blocks: int, code: str) -> list[int]:
    if (
        not isinstance(value, list)
        or any(not _int(item) or item < 0 or item >= raw_blocks for item in value)
        or value != sorted(set(value))
    ):
        raise AlignmentFailure(code)
    return value


def _exact_true_map(value: Any, keys: tuple[str, ...], code: str) -> dict[str, bool]:
    value = _obj(value, keys, code)
    if any(type(item) is not bool or item is not True for item in value.values()):
        raise AlignmentFailure(code)
    return value


def _exact_zero_cost(value: Any, keys: tuple[str, ...], code: str) -> dict[str, int]:
    value = _obj(value, keys, code)
    if any(not _int(item) or item != 0 for item in value.values()):
        raise AlignmentFailure(code)
    return value


def _receipt(row: dict[str, Any], key: str = "receipt_sha256") -> bool:
    observed = row.get(key)
    core = {name: value for name, value in row.items() if name != key}
    return isinstance(observed, str) and observed == sha(canonical(core))


def _jsonl_manifest(rows: list[dict[str, Any]], key: str) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item[key]):
        digest.update(canonical(row) + b"\n")
    return digest.hexdigest()


def _surface(text: str) -> str:
    return " ".join(text.split())


def _fingerprint(row: dict[str, Any]) -> str:
    core = {
        "content_surface_sha256": sha(_surface(row["content"]).encode("utf-8")),
        "source_block_start": row["source_block_start"],
        "source_block_end": row["source_block_end"],
        "section_lineage": row["section_lineage"],
        "section_title": row["section_title"],
        "section_path": row["section_path"],
        "page_number": row["page_number"],
        "is_flow_diagram": row["is_flow_diagram"],
        "has_diagram": row["has_diagram"],
        "confidence": row["confidence"],
    }
    return sha(canonical(core))


def _multiset(rows: list[dict[str, Any]]) -> str:
    ordered = sorted((_fingerprint(row), row["chunk_index"]) for row in rows)
    return sha(canonical([{"fingerprint_sha256": fp, "occurrence": index} for index, (fp, _) in enumerate(ordered)]))


def _validate_m27a(seed: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    keys = ("authorization", "checks", "claim", "contract_integrity", "cost", "counts", "dependencies", "determinism", "evidence_status", "instrument", "legacy_document_receipts", "manifests", "mechanical_alignment_status", "raw_document_receipts", "review_fiches", "status", "task_evidence")
    seed = _obj(seed, keys, "m27a_receipt_failure")
    if (seed["instrument"], seed["contract_integrity"], seed["evidence_status"], seed["mechanical_alignment_status"], seed["status"]) != ("s117_m27_live_evidence_v1", "GO", "GO", "NO_GO", "CONTRACT_GO_EVIDENCE_GO_ALIGNMENT_NO_GO"):
        raise AlignmentFailure("m27a_receipt_failure")
    expected_counts = {"affected_documents": 18, "aligned_documents": 17, "aligned_tasks": 20, "live_tasks": 21, "original_complete_tasks": 14, "supplemented_tasks": 7, "unresolved_alignment_documents": 1, "unresolved_alignment_tasks": 1}
    if seed["counts"] != expected_counts or any(not _int(v) for v in seed["counts"].values()):
        raise AlignmentFailure("affected_population_drift")
    _exact_true_map(seed["checks"], M27A_CHECK_KEYS, "m27a_receipt_failure")
    _exact_zero_cost(
        seed["cost"],
        ("database_reads", "database_writes", "embedding_calls", "model_calls"),
        "m27a_receipt_failure",
    )
    if seed["authorization"] != {
        "M3": "BLOCKED", "adjudication": False, "chunk_change": False,
        "context_generation": False, "database": False,
        "embedding_generation": False, "load": False, "model_calls": False,
        "policy_change": False, "serving": False,
    } or seed["claim"] != {
        "alignment_is_adjudication": False, "facts_moved_to_ok": 0,
        "raw_store_only_not_pdf_fidelity": True,
    } or any(type(seed["authorization"][key]) is not bool for key in seed["authorization"] if key != "M3") or type(seed["claim"]["alignment_is_adjudication"]) is not bool or type(seed["claim"]["raw_store_only_not_pdf_fidelity"]) is not bool or not _int(seed["claim"]["facts_moved_to_ok"]):
        raise AlignmentFailure("m27a_receipt_failure")
    _sha(_obj(seed["determinism"], ("logical_payload_sha256",), "m27a_receipt_failure")["logical_payload_sha256"], "m27a_receipt_failure")
    docs = seed["raw_document_receipts"]
    tasks = seed["task_evidence"]
    if not isinstance(docs, list) or not isinstance(tasks, list) or len(docs) != 18 or len(tasks) != 21:
        raise AlignmentFailure("affected_population_drift")
    doc_map: dict[str, dict[str, Any]] = {}
    for doc in docs:
        doc = _obj(doc, M27A_DOCUMENT_KEYS, "m27a_receipt_failure")
        raw_blocks = doc["raw_blocks"]
        rows = doc["v3_rows"]
        if (
            doc["schema"] != "s117_m27_raw_document_stream_evidence_v1"
            or not _receipt(doc)
            or not isinstance(raw_blocks, list)
            or not isinstance(rows, list)
            or not _int(doc["raw_artifact_bytes"])
            or doc["raw_artifact_bytes"] < 0
            or not isinstance(doc["raw_artifact_base64"], str)
            or doc["alignment_status"] not in ("exact_whitespace_equivalent", "unresolved")
            or type(doc["document_stream_whitespace_equal"]) is not bool
            or type(doc["row_by_row_regeneration_equal"]) is not bool
            or not isinstance(doc["independent_validation_failures"], list)
        ):
            raise AlignmentFailure("m27a_receipt_failure")
        extraction = _sha(doc["extraction_sha256"], "m27a_receipt_failure")
        artifact = _sha(doc["raw_artifact_sha256"], "m27a_receipt_failure")
        for name in ("raw_block_manifest_sha256", "raw_surface_sha256", "v3_row_manifest_sha256", "v3_surface_sha256"):
            _sha(doc[name], "m27a_receipt_failure")
        if extraction in doc_map:
            raise AlignmentFailure("m27a_receipt_failure")
        for index, row in enumerate(raw_blocks):
            row = _obj(row, M27A_RAW_BLOCK_KEYS, "m27a_receipt_failure")
            if (
                not _receipt(row)
                or not _int(row["source_block_index"])
                or row["source_block_index"] != index
                or not isinstance(row["text"], str)
                or row["text_sha256"] != sha(row["text"].encode("utf-8"))
                or not isinstance(row["kind"], str)
                or not isinstance(row["lineage"], list)
            ):
                raise AlignmentFailure("m27a_receipt_failure")
        seen_chunks: set[int] = set()
        for row in rows:
            row = _obj(row, M27A_ROW_KEYS, "m27a_receipt_failure")
            if (
                not _receipt(row)
                or not _int(row["chunk_index"])
                or row["chunk_index"] in seen_chunks
                or row["extraction_sha256"] != extraction
                or row["raw_artifact_sha256"] != artifact
                or not isinstance(row["content"], str)
                or row["content_sha256"] != sha(row["content"].encode("utf-8"))
                or not _int(row["source_block_start"])
                or not _int(row["source_block_end"])
                or row["source_block_start"] < 0
                or row["source_block_end"] < row["source_block_start"]
                or row["source_block_end"] >= len(raw_blocks)
                or type(row["is_flow_diagram"]) is not bool
                or type(row["has_diagram"]) is not bool
            ):
                raise AlignmentFailure("m27a_receipt_failure")
            seen_chunks.add(row["chunk_index"])
        if (
            doc["raw_block_manifest_sha256"] != _jsonl_manifest(raw_blocks, "source_block_index")
            or doc["v3_row_manifest_sha256"] != _jsonl_manifest(rows, "chunk_index")
        ):
            raise AlignmentFailure("m27a_receipt_failure")
        doc_map[extraction] = doc
    task_map: dict[str, dict[str, Any]] = {}
    doc_receipts = {d["receipt_sha256"] for d in docs}
    for task in tasks:
        task = _obj(task, M27A_TASK_KEYS, "m27a_receipt_failure")
        target = _obj(task["target_row"], M27A_ROW_KEYS, "m27a_receipt_failure")
        overlaps = task["overlapping_v3_rows"]
        if (
            task["schema"] != "s117_m27_live_task_evidence_v1"
            or not _receipt(task)
            or not _receipt(target)
            or not isinstance(overlaps, list)
            or any(not _receipt(_obj(row, M27A_ROW_KEYS, "m27a_receipt_failure")) for row in overlaps)
            or task["evidence_complete"] is not True
            or task["adjudication_status"] != "not_authorized"
        ):
            raise AlignmentFailure("m27a_receipt_failure")
        task_id = _uuid(task["local_row_id"], "m27a_receipt_failure")
        if task_id in task_map or task["raw_document_receipt_sha256"] not in doc_receipts or task["extraction_sha256"] not in doc_map:
            raise AlignmentFailure("m27a_receipt_failure")
        document = doc_map[task["extraction_sha256"]]
        document_rows = {row["receipt_sha256"]: row for row in document["v3_rows"]}
        if (
            document["receipt_sha256"] != task["raw_document_receipt_sha256"]
            or target["receipt_sha256"] not in document_rows
            or any(row["receipt_sha256"] not in document_rows for row in overlaps)
            or target["extraction_sha256"] != task["extraction_sha256"]
            or any(row["extraction_sha256"] != task["extraction_sha256"] for row in overlaps)
            or task["overlap_manifest_sha256"] != _jsonl_manifest(overlaps, "chunk_index")
        ):
            raise AlignmentFailure("m27a_receipt_failure")
        task_map[task_id] = task
    legacy = seed["legacy_document_receipts"]
    reviews = seed["review_fiches"]
    if (
        not isinstance(legacy, list)
        or not isinstance(reviews, list)
        or any(not isinstance(row, dict) or not _receipt(row) for row in legacy)
        or any(not isinstance(row, dict) or "local_row_id" not in row for row in reviews)
        or not {row.get("extraction_sha256") for row in legacy}.issubset(set(doc_map))
        or {row.get("local_row_id") for row in reviews} != set(task_map)
    ):
        raise AlignmentFailure("m27a_receipt_failure")
    manifests = _obj(
        seed["manifests"],
        ("raw_document_receipts_sha256", "legacy_document_receipts_sha256", "task_evidence_sha256", "review_fiches_sha256"),
        "m27a_receipt_failure",
    )
    expected = {
        "raw_document_receipts_sha256": _jsonl_manifest(docs, "extraction_sha256"),
        "legacy_document_receipts_sha256": _jsonl_manifest(legacy, "extraction_sha256"),
        "task_evidence_sha256": _jsonl_manifest(tasks, "local_row_id"),
        "review_fiches_sha256": _jsonl_manifest(reviews, "local_row_id"),
    }
    if manifests != expected:
        raise AlignmentFailure("m27a_receipt_failure")
    return doc_map, task_map


def _m27c_projection(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for doc in documents:
        result.append({
            "schema": "s117_m28_candidate_treatment_projection_v1",
            "extraction_sha256": doc["extraction_sha256"], "raw_artifact_sha256": doc["raw_artifact_sha256"],
            "raw_blocks": doc["raw_blocks"], "rows": doc["treatment_rows"],
            "covered_blocks": doc["treatment_covered_blocks"], "missing_block_indexes": doc["treatment_missing_block_indexes"],
            "surface_sha256": doc["treatment_surface_sha256"], "surface_equal_raw": doc["treatment_surface_equal_raw"],
            "fingerprint_multiset_sha256": doc["treatment_fingerprint_multiset_sha256"],
            "coverage_gain_block_indexes": doc["coverage_gain_block_indexes"],
            "coverage_regression_block_indexes": doc["coverage_regression_block_indexes"], "changed": doc["changed"],
        })
    return sorted(result, key=lambda row: row["extraction_sha256"])


def _validate_m27c(seed: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    top_keys = (
        "authority", "authorization", "changed_document_deltas", "checks", "cost",
        "dependencies", "determinism", "documents", "instrument", "manifests",
        "population", "status", "statuses", "supersedes", "treatment_contract",
    )
    seed = _obj(seed, top_keys, "m27c_receipt_failure")
    if (
        seed["instrument"] != "s117_m27_loss_safe_chunking_probe_v2"
        or seed["authority"] != "raw_store_parsed_block_surface_only"
        or seed["status"] != "CONTRACT_GO_BASELINE_GO_TREATMENT_GO_DELTA_GO"
        or seed["statuses"] != {
            "baseline_replay": "GO", "contract_integrity": "GO",
            "delta_accounted": "GO", "treatment_lossless": "GO",
        }
        or seed["population"] != M27C_POPULATION
        or not isinstance(seed["population"], dict)
        or any(not _int(value) for value in seed["population"].values())
    ):
        raise AlignmentFailure("m27c_receipt_failure")
    _exact_true_map(seed["checks"], M27C_CHECK_KEYS, "m27c_receipt_failure")
    _exact_zero_cost(
        seed["cost"],
        ("database_reads", "database_writes", "model_calls", "network_calls"),
        "m27c_receipt_failure",
    )
    if seed["authorization"] != {
        "M3": "BLOCKED", "context_generation": False, "database": False,
        "deploy": False, "embeddings": False, "facts_moved_to_ok": 0,
        "implementation": False, "load": False, "models": False,
        "network": False, "policy_change": False, "serving": False,
    } or any(type(seed["authorization"][key]) is not bool for key in seed["authorization"] if key not in ("M3", "facts_moved_to_ok")) or not _int(seed["authorization"]["facts_moved_to_ok"]):
        raise AlignmentFailure("m27c_receipt_failure")
    contract = _obj(
        seed["treatment_contract"],
        ("base_chunker_sha256", "loadable", "override", "runner_sha256", "sha256"),
        "m27c_receipt_failure",
    )
    if (
        contract["sha256"] != "2bf622a934c4e4d3ce6812e20078fb32775710cf280cc76fd28abf1a0c71ce1d"
        or contract["loadable"] is not False
        or contract["override"] != {
            "baseline": 15, "only_behavioral_override": True,
            "scope": "single_call_with_finally_restore", "symbol": "src.reingest.chunk.NOISE_CHARS",
            "treatment": 0,
        }
        or not _int(contract["override"].get("baseline"))
        or not _int(contract["override"].get("treatment"))
        or type(contract["override"].get("only_behavioral_override")) is not bool
    ):
        raise AlignmentFailure("m27c_receipt_failure")
    docs = seed["documents"]
    deltas = seed["changed_document_deltas"]
    if not isinstance(docs, list) or len(docs) != 1068 or not isinstance(deltas, list) or len(deltas) != 27:
        raise AlignmentFailure("m27c_receipt_failure")
    doc_map: dict[str, dict[str, Any]] = {}
    for doc in docs:
        doc = _obj(doc, M27C_DOCUMENT_KEYS, "m27c_receipt_failure")
        if doc["schema"] != "s117_m27_loss_safe_chunking_document_v1" or not _receipt(doc):
            raise AlignmentFailure("m27c_receipt_failure")
        extraction = _sha(doc["extraction_sha256"], "m27c_receipt_failure")
        _sha(doc["raw_artifact_sha256"], "m27c_receipt_failure")
        for name in (
            "raw_surface_sha256", "baseline_surface_sha256",
            "baseline_fingerprint_multiset_sha256", "treatment_surface_sha256",
            "treatment_fingerprint_multiset_sha256", "treatment_contract_sha256",
        ):
            _sha(doc[name], "m27c_receipt_failure")
        raw_blocks = doc["raw_blocks"]
        numeric = (
            "raw_blocks", "baseline_rows", "baseline_covered_blocks",
            "treatment_rows", "treatment_covered_blocks",
        )
        if any(not _int(doc[name]) or doc[name] < 0 for name in numeric) or raw_blocks < 1:
            raise AlignmentFailure("m27c_receipt_failure")
        baseline_missing = _index_list(doc["baseline_missing_block_indexes"], raw_blocks, "m27c_receipt_failure")
        treatment_missing = _index_list(doc["treatment_missing_block_indexes"], raw_blocks, "m27c_receipt_failure")
        gains = _index_list(doc["coverage_gain_block_indexes"], raw_blocks, "m27c_receipt_failure")
        regressions = _index_list(doc["coverage_regression_block_indexes"], raw_blocks, "m27c_receipt_failure")
        if (
            doc["baseline_covered_blocks"] != raw_blocks - len(baseline_missing)
            or doc["treatment_covered_blocks"] != raw_blocks - len(treatment_missing)
            or gains != sorted(set(baseline_missing) - set(treatment_missing))
            or regressions != sorted(set(treatment_missing) - set(baseline_missing))
            or type(doc["treatment_surface_equal_raw"]) is not bool
            or type(doc["fingerprint_multiset_equal"]) is not bool
            or type(doc["changed"]) is not bool
            or type(doc["delta_partition_exact"]) is not bool
            or doc["treatment_surface_equal_raw"] is not True
            or doc["treatment_surface_sha256"] != doc["raw_surface_sha256"]
            or doc["changed"] is doc["fingerprint_multiset_equal"]
            or doc["delta_partition_exact"] is not True
            or treatment_missing
            or regressions
        ):
            raise AlignmentFailure("m27c_receipt_failure")
        delta_counts = _obj(doc["delta_counts"], ("added", "modified", "removed", "unchanged"), "m27c_receipt_failure")
        if any(not _int(value) or value < 0 for value in delta_counts.values()):
            raise AlignmentFailure("m27c_receipt_failure")
        if extraction in doc_map:
            raise AlignmentFailure("m27c_receipt_failure")
        doc_map[extraction] = doc
    delta_map: dict[str, dict[str, Any]] = {}
    unchanged_keys = ("baseline_ordinal", "fingerprint_sha256", "treatment_ordinal")
    modified_keys = (
        "baseline_fingerprint_sha256", "baseline_ordinal", "overlap_end",
        "overlap_start", "treatment_fingerprint_sha256", "treatment_ordinal",
    )
    removed_keys = (
        "confidence", "content", "content_sha256", "content_surface_sha256",
        "fingerprint_sha256", "has_diagram", "is_flow_diagram",
        "meaningful_characters", "ordinal", "page_number", "section_anchor",
        "section_lineage", "section_path", "section_title", "source_block_end",
        "source_block_start",
    )
    for delta in deltas:
        delta = _obj(
            delta,
            ("added", "extraction_sha256", "modified", "receipt_sha256", "removed", "schema", "treatment_contract_sha256", "unchanged"),
            "m27c_receipt_failure",
        )
        extraction = _sha(delta["extraction_sha256"], "m27c_receipt_failure")
        if (
            delta["schema"] != "s117_m27_loss_safe_chunking_delta_v1"
            or not _receipt(delta)
            or extraction in delta_map
            or extraction not in doc_map
            or doc_map[extraction]["changed"] is not True
            or delta["treatment_contract_sha256"] != contract["sha256"]
            or any(not isinstance(delta[name], list) for name in ("added", "modified", "removed", "unchanged"))
        ):
            raise AlignmentFailure("m27c_receipt_failure")
        for row in delta["unchanged"]:
            row = _obj(row, unchanged_keys, "m27c_receipt_failure")
            if any(not _int(row[name]) or row[name] < 0 for name in ("baseline_ordinal", "treatment_ordinal")):
                raise AlignmentFailure("m27c_receipt_failure")
            _sha(row["fingerprint_sha256"], "m27c_receipt_failure")
        for row in delta["modified"]:
            row = _obj(row, modified_keys, "m27c_receipt_failure")
            if any(not _int(row[name]) or row[name] < 0 for name in ("baseline_ordinal", "treatment_ordinal", "overlap_start", "overlap_end")) or row["overlap_end"] < row["overlap_start"]:
                raise AlignmentFailure("m27c_receipt_failure")
            _sha(row["baseline_fingerprint_sha256"], "m27c_receipt_failure")
            _sha(row["treatment_fingerprint_sha256"], "m27c_receipt_failure")
        for group, keys in ((delta["removed"], removed_keys), (delta["added"], (*removed_keys, "diagnostic_id"))):
            for row in group:
                row = _obj(row, keys, "m27c_receipt_failure")
                if any(not _int(row[name]) for name in ("ordinal", "source_block_start", "source_block_end")) or row["source_block_end"] < row["source_block_start"]:
                    raise AlignmentFailure("m27c_receipt_failure")
                for name in ("content_sha256", "content_surface_sha256", "fingerprint_sha256"):
                    _sha(row[name], "m27c_receipt_failure")
        expected_counts = {name: len(delta[name]) for name in ("added", "modified", "removed", "unchanged")}
        if doc_map[extraction]["delta_counts"] != expected_counts:
            raise AlignmentFailure("m27c_receipt_failure")
        delta_map[extraction] = delta
    if set(delta_map) != {key for key, doc in doc_map.items() if doc["changed"]}:
        raise AlignmentFailure("m27c_receipt_failure")
    manifests = _obj(seed["manifests"], tuple(M27C_MANIFESTS), "m27c_receipt_failure")
    if manifests != M27C_MANIFESTS or manifests["documents_sha256"] != _jsonl_manifest(docs, "extraction_sha256") or manifests["deltas_sha256"] != _jsonl_manifest(deltas, "extraction_sha256"):
        raise AlignmentFailure("m27c_receipt_failure")
    projection = _m27c_projection(docs)
    raw = canonical(projection)
    if len(raw) != PROJECTION_BYTES or sha(raw) != PROJECTION_SHA:
        raise AlignmentFailure("candidate_projection_bridge_failure")
    return doc_map, delta_map, projection


def _validate_m28(seed: Any) -> None:
    seed = _obj(seed, (
        "authority", "authorization", "checks", "cost", "dependencies", "failures",
        "generation", "instrument", "loadable", "manifests", "population",
        "schema_version", "source", "status",
    ), "m28_seed_drift")
    if (
        seed["instrument"] != "s117_m28_candidate_materialization_v1"
        or not _int(seed["schema_version"])
        or seed["schema_version"] != 1
        or seed["status"] != "GO"
        or seed["authority"] != "raw_store_parsed_block_whitespace_token_surface_only"
        or seed["loadable"] is not False
        or seed["failures"] != []
        or seed["population"] != M28_POPULATION
        or not isinstance(seed["population"], dict)
        or any(not _int(value) for value in seed["population"].values())
    ):
        raise AlignmentFailure("m28_seed_drift")
    _exact_true_map(seed["checks"], M28_CHECK_KEYS, "m28_seed_drift")
    cost = _obj(seed["cost"], ("database_reads", "database_writes", "external_calls_blocked", "model_calls", "network_calls"), "m28_seed_drift")
    if cost != {"database_reads": 0, "database_writes": 0, "external_calls_blocked": True, "model_calls": 0, "network_calls": 0} or cost["external_calls_blocked"] is not True or any(not _int(cost[key]) for key in ("database_reads", "database_writes", "model_calls", "network_calls")):
        raise AlignmentFailure("m28_seed_drift")
    if seed["authorization"] != {
        "M3": "BLOCKED", "context_generation": False, "database": False,
        "deploy": False, "embeddings": False, "facts_moved_to_ok": 0,
        "load": False, "models": False, "network": False, "retrieval": False,
        "serving": False,
    } or any(type(seed["authorization"][key]) is not bool for key in seed["authorization"] if key not in ("M3", "facts_moved_to_ok")) or not _int(seed["authorization"]["facts_moved_to_ok"]):
        raise AlignmentFailure("m28_seed_drift")
    manifests = _obj(seed["manifests"], tuple(M28_MANIFESTS), "m28_seed_drift")
    if manifests != M28_MANIFESTS:
        raise AlignmentFailure("candidate_projection_bridge_failure")
    source = _obj(seed["source"], ("json_files", "manifest_sha256", "non_record_artifacts", "records", "store_slug"), "m28_seed_drift")
    generation = _obj(seed["generation"], ("manifest_schema", "manifest_sha256", "materialization_id", "rows_manifest_bytes", "rows_manifest_sha256"), "m28_seed_drift")
    if not _int(source["json_files"]) or source["json_files"] != 1069 or not _int(source["records"]) or source["records"] != 1068 or source["non_record_artifacts"] != ["_failures.json"] or not isinstance(source["store_slug"], str) or generation["manifest_schema"] != "chunk_materialization_manifest_v1" or not _int(generation["rows_manifest_bytes"]) or generation["rows_manifest_bytes"] < 0:
        raise AlignmentFailure("m28_seed_drift")
    for value in (source["manifest_sha256"], generation["manifest_sha256"], generation["rows_manifest_sha256"]):
        _sha(value, "m28_seed_drift")
    _uuid(generation["materialization_id"], "m28_seed_drift")


def _validate_m29(seed: Any) -> dict[str, dict[str, Any]]:
    seed = _obj(seed, (
        "instrument", "schema_version", "status", "loadable", "authority",
        "candidate_evidence_mode", "candidate_per_document_receipts_persisted",
        "dependencies", "population", "documents",
        "resolved_baseline_missing_identities", "manifests", "checks", "failures",
        "cost", "authorization",
    ), "m29_seed_drift")
    if (
        seed["instrument"] != "s117_m29_reconciled_loss_ledger_v1"
        or not _int(seed["schema_version"])
        or seed["schema_version"] != 1
        or seed["status"] != "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY"
        or seed["loadable"] is not False
        or seed["authority"] != "reconciled_frozen_evidence_raw_parsed_block_surface_only"
        or seed["candidate_evidence_mode"] != "substituted_from_frozen_treatment_via_exact_projection_hash"
        or seed["candidate_per_document_receipts_persisted"] is not False
        or seed["failures"] != []
        or seed["population"] != M29_POPULATION
        or not isinstance(seed["population"], dict)
        or any(not _int(value) for value in seed["population"].values())
    ):
        raise AlignmentFailure("m29_seed_drift")
    _exact_true_map(seed["checks"], M29_CHECK_KEYS, "m29_seed_drift")
    cost = _obj(seed["cost"], ("additional_candidate_executions", "chunk_executions", "database_reads", "database_writes", "external_calls_blocked", "manual_adjudications", "model_calls", "network_calls", "raw_store_reads"), "m29_seed_drift")
    if cost != {
        "additional_candidate_executions": 0, "chunk_executions": 0,
        "database_reads": 0, "database_writes": 0,
        "external_calls_blocked": True, "manual_adjudications": 0,
        "model_calls": 0, "network_calls": 0, "raw_store_reads": 0,
    } or cost["external_calls_blocked"] is not True or any(not _int(cost[key]) for key in cost if key != "external_calls_blocked"):
        raise AlignmentFailure("m29_seed_drift")
    if seed["authorization"] != {
        "M27A": False, "M3": "BLOCKED", "additional_candidate_execution": False,
        "chunk_execution": False, "context_generation": False, "database": False,
        "deploy": False, "embeddings": False, "execution_permit_valid": True,
        "facts_moved_to_ok": 0, "load": False, "manual_adjudication": False,
        "models": False, "network": False, "preregistration_frozen": True,
        "raw_store_read": False, "retrieval": False, "serving": False,
    } or any(type(seed["authorization"][key]) is not bool for key in seed["authorization"] if key not in ("M3", "facts_moved_to_ok")) or not _int(seed["authorization"]["facts_moved_to_ok"]):
        raise AlignmentFailure("m29_seed_drift")
    documents = seed["documents"]
    resolved = seed["resolved_baseline_missing_identities"]
    if not isinstance(documents, list) or len(documents) != 1068 or not isinstance(resolved, list) or len(resolved) != 100:
        raise AlignmentFailure("m29_seed_drift")
    doc_map: dict[str, dict[str, Any]] = {}
    for doc in documents:
        doc = _obj(doc, M29_DOCUMENT_KEYS, "m29_seed_drift")
        if doc["schema"] != "s117_m29_document_reconciliation_v1" or not _receipt(doc, "m29_document_receipt_sha256"):
            raise AlignmentFailure("m29_seed_drift")
        extraction = _sha(doc["extraction_sha256"], "m29_seed_drift")
        _sha(doc["raw_artifact_sha256"], "m29_seed_drift")
        raw_blocks = doc["raw_blocks"]
        if extraction in doc_map or not _int(raw_blocks) or raw_blocks < 1 or any(not _int(doc[name]) or doc[name] < 0 for name in ("baseline_covered_blocks", "candidate_covered_blocks")) or type(doc["fingerprint_multiset_changed"]) is not bool:
            raise AlignmentFailure("m29_seed_drift")
        baseline_missing = _index_list(doc["baseline_missing_block_indexes"], raw_blocks, "m29_seed_drift")
        candidate_missing = _index_list(doc["candidate_missing_block_indexes"], raw_blocks, "m29_seed_drift")
        gains = _index_list(doc["coverage_gain_block_indexes"], raw_blocks, "m29_seed_drift")
        regressions = _index_list(doc["coverage_regression_block_indexes"], raw_blocks, "m29_seed_drift")
        if doc["baseline_covered_blocks"] != raw_blocks - len(baseline_missing) or doc["candidate_covered_blocks"] != raw_blocks - len(candidate_missing) or gains != sorted(set(baseline_missing) - set(candidate_missing)) or regressions != sorted(set(candidate_missing) - set(baseline_missing)):
            raise AlignmentFailure("m29_seed_drift")
        doc_map[extraction] = doc
    resolved_identities: set[tuple[str, int]] = set()
    for row in resolved:
        row = _obj(row, M29_RESOLUTION_KEYS, "m29_seed_drift")
        extraction = _sha(row["extraction_sha256"], "m29_seed_drift")
        if not _int(row["source_block_index"]):
            raise AlignmentFailure("m29_seed_drift")
        identity = (extraction, row["source_block_index"])
        if (
            row["schema"] != "s117_m29_resolved_baseline_missing_identity_v1"
            or not _receipt(row, "m29_resolution_receipt_sha256")
            or extraction not in doc_map
            or row["m29_document_receipt_sha256"] != doc_map[extraction]["m29_document_receipt_sha256"]
            or not _int(row["source_page_ordinal"])
            or not _int(row["page"])
            or row["source_block_index"] < 0
            or row["source_block_index"] >= doc_map[extraction]["raw_blocks"]
            or identity in resolved_identities
            or not isinstance(row["kind"], str)
            or row["baseline_disposition"] not in ("authorized_exclusion", "unruled_loss")
            or row["candidate_disposition"] != "covered"
            or not isinstance(row["resolution_evidence"], str)
            or (row["baseline_rule_id"] is not None and not isinstance(row["baseline_rule_id"], str))
        ):
            raise AlignmentFailure("m29_seed_drift")
        for name in ("text_sha256", "ledger_receipt_sha256", "m29_document_receipt_sha256", "m29_resolution_receipt_sha256"):
            _sha(row[name], "m29_seed_drift")
        resolved_identities.add(identity)
    document_receipts = [{"extraction_sha256": row["extraction_sha256"], "m29_document_receipt_sha256": row["m29_document_receipt_sha256"]} for row in documents]
    resolution_receipts = [{"extraction_sha256": row["extraction_sha256"], "source_block_index": row["source_block_index"], "m29_resolution_receipt_sha256": row["m29_resolution_receipt_sha256"]} for row in resolved]
    baseline_missing = sorted(({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["baseline_missing_block_indexes"]), key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    candidate_missing = sorted(({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["candidate_missing_block_indexes"]), key=lambda row: (row["extraction_sha256"], row["source_block_index"]))
    expected_manifests = {
        "documents_sha256": sha(canonical(documents)),
        "document_receipts_sha256": sha(canonical(document_receipts)),
        "resolved_baseline_missing_sha256": sha(canonical(resolved)),
        "resolution_receipts_sha256": sha(canonical(resolution_receipts)),
        "baseline_missing_identities_sha256": sha(canonical(baseline_missing)),
        "candidate_missing_identities_sha256": sha(canonical(candidate_missing)),
    }
    manifests = _obj(seed["manifests"], tuple(expected_manifests), "m29_seed_drift")
    baseline_identity_set = {(row["extraction_sha256"], row["source_block_index"]) for row in baseline_missing}
    if manifests != expected_manifests or manifests != M29_MANIFESTS or resolved_identities != baseline_identity_set:
        raise AlignmentFailure("m29_seed_drift")
    return doc_map


def _authorization(prereg: bool, permit: bool) -> dict[str, Any]:
    result = {key: False for key in AUTH_BOOL_KEYS}
    result["preregistration_frozen"] = prereg
    result["execution_permit_valid"] = permit
    result["facts_moved_to_ok"] = 0
    result["M3"] = "BLOCKED"
    return result


def _manifests(documents: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, str]:
    doc_receipts = [{"extraction_sha256": row["extraction_sha256"], "m210_document_receipt_sha256": row["m210_document_receipt_sha256"]} for row in documents]
    task_receipts = [{"local_row_id": row["local_row_id"], "m210_task_receipt_sha256": row["m210_task_receipt_sha256"]} for row in tasks]
    doc_ids = [{"extraction_sha256": row["extraction_sha256"]} for row in documents]
    task_ids = [{"local_row_id": row["local_row_id"]} for row in tasks]
    return {
        "documents_sha256": sha(canonical(documents)), "document_receipts_sha256": sha(canonical(doc_receipts)),
        "tasks_sha256": sha(canonical(tasks)), "task_receipts_sha256": sha(canonical(task_receipts)),
        "affected_document_identities_sha256": sha(canonical(doc_ids)), "task_identities_sha256": sha(canonical(task_ids)),
    }


def build_payload(m27a: Any, m27c: Any, m28: Any, m29: Any, dependencies: dict[str, str], seed: int) -> dict[str, Any]:
    if seed not in (1, 2) or set(dependencies) != set(DEPENDENCY_ROLES) or any(_sha(v) != v for v in dependencies.values()):
        raise AlignmentFailure("contract_integrity_failure")
    a_docs, a_tasks = _validate_m27a(m27a)
    c_docs, deltas, projection = _validate_m27c(m27c)
    _validate_m28(m28)
    n_docs = _validate_m29(m29)
    if sha(canonical(projection)) != m28["manifests"]["candidate_projection_sha256"]:
        raise AlignmentFailure("candidate_projection_bridge_failure")
    affected = sorted(a_docs)
    if sha(canonical([{"extraction_sha256": x} for x in affected])) != DOCUMENT_IDENTITIES_SHA:
        raise AlignmentFailure("affected_population_drift")
    changed = sorted(set(affected) & {x for x, row in c_docs.items() if row["changed"]})
    if changed != [CHANGED_EXTRACTION]:
        raise AlignmentFailure("changed_intersection_drift")

    documents = []
    for extraction in affected:
        a = a_docs[extraction]
        c = c_docs.get(extraction)
        n = n_docs.get(extraction)
        if c is None or n is None or a["raw_artifact_sha256"] != c["raw_artifact_sha256"] or a["raw_surface_sha256"] != c["raw_surface_sha256"] or len(a["raw_blocks"]) != c["raw_blocks"] or len(a["v3_rows"]) != c["baseline_rows"] or _multiset(a["v3_rows"]) != c["baseline_fingerprint_multiset_sha256"]:
            raise AlignmentFailure("m27a_m27c_baseline_bridge_failure")
        if n["raw_artifact_sha256"] != c["raw_artifact_sha256"] or n["raw_blocks"] != c["raw_blocks"] or n["baseline_covered_blocks"] != c["baseline_covered_blocks"] or n["baseline_missing_block_indexes"] != c["baseline_missing_block_indexes"] or n["candidate_covered_blocks"] != c["treatment_covered_blocks"] or n["candidate_missing_block_indexes"] != c["treatment_missing_block_indexes"] or n["coverage_gain_block_indexes"] != c["coverage_gain_block_indexes"] or n["coverage_regression_block_indexes"] != c["coverage_regression_block_indexes"] or n["fingerprint_multiset_changed"] != c["changed"]:
            raise AlignmentFailure("document_alignment_failure")
        if c["treatment_surface_equal_raw"] is not True or c["treatment_missing_block_indexes"] or c["coverage_regression_block_indexes"]:
            raise AlignmentFailure("document_alignment_failure")
        if extraction == CHANGED_EXTRACTION:
            delta = deltas.get(extraction)
            if (
                a["alignment_status"] != "unresolved"
                or c["raw_blocks"] != 1455
                or c["baseline_rows"] != 119
                or c["treatment_rows"] != 119
                or c["baseline_missing_block_indexes"] != [630, 631]
                or c["coverage_gain_block_indexes"] != [630, 631]
                or c["changed"] is not True
                or c["fingerprint_multiset_equal"] is not False
                or delta is None
                or {name: len(delta[name]) for name in ("unchanged", "removed", "added", "modified")} != {"unchanged": 118, "removed": 1, "added": 1, "modified": 1}
                or [(row["ordinal"], row["source_block_start"], row["source_block_end"], row["fingerprint_sha256"]) for row in delta["removed"]] != [(39, 629, 629, CHANGED_BASELINE_FINGERPRINT_SHA)]
                or [(row["ordinal"], row["source_block_start"], row["source_block_end"], row["fingerprint_sha256"]) for row in delta["added"]] != [(39, 629, 631, CHANGED_CANDIDATE_FINGERPRINT_SHA)]
                or delta["modified"] != [{
                    "baseline_fingerprint_sha256": CHANGED_BASELINE_FINGERPRINT_SHA,
                    "baseline_ordinal": 39, "overlap_end": 629, "overlap_start": 629,
                    "treatment_fingerprint_sha256": CHANGED_CANDIDATE_FINGERPRINT_SHA,
                    "treatment_ordinal": 39,
                }]
            ):
                raise AlignmentFailure("changed_target_mapping_failure")
        elif (
            a["alignment_status"] != "exact_whitespace_equivalent"
            or c["changed"] is not False
            or c["fingerprint_multiset_equal"] is not True
            or extraction in deltas
            or c["coverage_gain_block_indexes"]
        ):
            raise AlignmentFailure("document_alignment_failure")
        core = {
            "schema": "s117_m210_candidate_document_alignment_v1", "extraction_sha256": extraction,
            "baseline_alignment_status": a["alignment_status"], "candidate_alignment_status": "exact_whitespace_equivalent",
            "candidate_surface_sha256": c["treatment_surface_sha256"], "raw_surface_sha256": c["raw_surface_sha256"],
            "candidate_surface_equal_raw": True, "candidate_missing_block_indexes": [],
            "coverage_gain_block_indexes": c["coverage_gain_block_indexes"], "coverage_regression_block_indexes": [],
            "fingerprint_multiset_changed": c["changed"],
            "candidate_mapping_mode": "frozen_changed_delta" if c["changed"] else "unchanged_fingerprint_multiset",
        }
        core["m210_document_receipt_sha256"] = sha(canonical(core))
        documents.append(core)
    random.Random(seed).shuffle(documents)
    documents.sort(key=lambda row: row["extraction_sha256"])
    doc_output = {row["extraction_sha256"]: row for row in documents}

    tasks = []
    for task_id, task in a_tasks.items():
        extraction = task["extraction_sha256"]
        doc = a_docs[extraction]
        fingerprints = [_fingerprint(row) for row in doc["v3_rows"]]
        target_fp = _fingerprint(task["target_row"])
        baseline_occurrences = fingerprints.count(target_fp)
        overlaps = task["overlapping_v3_rows"]
        overlap_payload = sorted(({
            "fingerprint_sha256": _fingerprint(row), "source_block_start": row["source_block_start"],
            "source_block_end": row["source_block_end"],
        } for row in overlaps), key=lambda row: (row["source_block_start"], row["source_block_end"], row["fingerprint_sha256"]))
        if baseline_occurrences != 1:
            raise AlignmentFailure("target_membership_failure")
        if len(overlaps) != 1 or any(fingerprints.count(row["fingerprint_sha256"]) != 1 for row in overlap_payload):
            raise AlignmentFailure("overlap_membership_failure")
        if (
            task["target_row"]["content_sha256"] != sha(task["target_row"]["content"].encode("utf-8"))
            or task["target_row"]["receipt_sha256"] not in {row["receipt_sha256"] for row in doc["v3_rows"]}
            or task["mechanical_raw_alignment"] != doc["alignment_status"]
        ):
            raise AlignmentFailure("target_membership_failure")
        candidate_ordinal = None
        mode = "unique_fingerprint_membership"
        if extraction == CHANGED_EXTRACTION:
            delta = deltas.get(extraction)
            matches = [row for row in delta["unchanged"] if row["fingerprint_sha256"] == target_fp and row["baseline_ordinal"] == task["target_row"]["chunk_index"]]
            if (
                task_id != CHANGED_TASK
                or target_fp != CHANGED_TARGET_FINGERPRINT_SHA
                or task["target_row"]["content_sha256"] != CHANGED_TARGET_CONTENT_SHA
                or task["target_row"]["chunk_index"] != 61
                or task["target_row"]["source_block_start"] != 796
                or task["target_row"]["source_block_end"] != 796
                or overlap_payload != [{"fingerprint_sha256": CHANGED_TARGET_FINGERPRINT_SHA, "source_block_end": 796, "source_block_start": 796}]
                or matches != [{"baseline_ordinal": 61, "fingerprint_sha256": CHANGED_TARGET_FINGERPRINT_SHA, "treatment_ordinal": 61}]
            ):
                raise AlignmentFailure("changed_target_mapping_failure")
            modified = delta["modified"]
            if modified != [{"baseline_fingerprint_sha256": CHANGED_BASELINE_FINGERPRINT_SHA, "baseline_ordinal": 39, "overlap_end": 629, "overlap_start": 629, "treatment_fingerprint_sha256": CHANGED_CANDIDATE_FINGERPRINT_SHA, "treatment_ordinal": 39}] or not (modified[0]["overlap_end"] < task["target_row"]["source_block_start"]):
                raise AlignmentFailure("changed_target_mapping_failure")
            candidate_ordinal = 61
            mode = "frozen_delta_unchanged_mapping"
        elif not c_docs[extraction]["fingerprint_multiset_equal"] or c_docs[extraction]["changed"]:
            raise AlignmentFailure("target_membership_failure")
        core = {
            "schema": "s117_m210_candidate_task_alignment_v1", "local_row_id": task_id,
            "extraction_sha256": extraction, "original_task_evidence_receipt_sha256": task["receipt_sha256"],
            "target_content_sha256": task["target_row"]["content_sha256"], "target_fingerprint_sha256": target_fp,
            "target_source_block_start": task["target_row"]["source_block_start"], "target_source_block_end": task["target_row"]["source_block_end"],
            "target_baseline_occurrences": 1, "target_candidate_occurrences": 1,
            "overlap_count": 1, "overlap_fingerprints_sha256": sha(canonical(overlap_payload)),
            "all_overlap_fingerprints_unique": True, "candidate_membership_mode": mode,
            "candidate_ordinal": candidate_ordinal, "changed_delta_disjoint_from_target": True,
            "baseline_alignment_status": task["mechanical_raw_alignment"], "candidate_alignment_status": "exact_whitespace_equivalent",
            "m210_document_receipt_sha256": doc_output[extraction]["m210_document_receipt_sha256"],
        }
        core["m210_task_receipt_sha256"] = sha(canonical(core))
        tasks.append(core)
    random.Random(seed ^ 0x210).shuffle(tasks)
    tasks.sort(key=lambda row: row["local_row_id"])
    if sha(canonical([{"local_row_id": row["local_row_id"]} for row in tasks])) != TASK_IDENTITIES_SHA:
        raise AlignmentFailure("affected_population_drift")
    counts = {
        "documents": len(documents), "tasks": len(tasks),
        "baseline_aligned_documents": sum(row["baseline_alignment_status"] == "exact_whitespace_equivalent" for row in documents),
        "baseline_unresolved_documents": sum(row["baseline_alignment_status"] == "unresolved" for row in documents),
        "candidate_aligned_documents": 18, "candidate_unresolved_documents": 0,
        "baseline_aligned_tasks": sum(row["baseline_alignment_status"] == "exact_whitespace_equivalent" for row in tasks),
        "baseline_unresolved_tasks": sum(row["baseline_alignment_status"] == "unresolved" for row in tasks),
        "candidate_aligned_tasks": 21, "candidate_unresolved_tasks": 0,
        "changed_affected_documents": 1, "unchanged_affected_documents": 17,
        "unique_target_memberships": 21, "unique_overlap_memberships": 21,
    }
    if counts != EXPECTED_COUNTS:
        raise AlignmentFailure("affected_population_drift")
    payload = {
        "instrument": "s117_m210_candidate_live_alignment_v1", "schema_version": 1,
        "status": "CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY", "loadable": False,
        "authority": "frozen_candidate_projection_and_delta_raw_parsed_block_surface_only",
        "candidate_evidence_mode": "substituted_from_m27c_treatment_via_m28_exact_projection_hash",
        "candidate_rows_persisted": False, "candidate_row_ids_claimed": False,
        "dependencies": dict(sorted(dependencies.items())), "counts": counts,
        "documents": documents, "tasks": tasks, "manifests": _manifests(documents, tasks),
        "checks": {key: True for key in CHECK_KEYS}, "failures": [], "cost": dict(COST),
        "authorization": _authorization(True, True),
    }
    validate_output(payload)
    return payload


def validate_output(payload: Any) -> None:
    payload = _obj(payload, OUTPUT_KEYS, "output_schema_failure")
    if payload["instrument"] != "s117_m210_candidate_live_alignment_v1" or not _int(payload["schema_version"]) or payload["schema_version"] != 1 or payload["loadable"] is not False or payload["authority"] != "frozen_candidate_projection_and_delta_raw_parsed_block_surface_only" or payload["candidate_evidence_mode"] != "substituted_from_m27c_treatment_via_m28_exact_projection_hash" or payload["candidate_rows_persisted"] is not False or payload["candidate_row_ids_claimed"] is not False:
        raise AlignmentFailure("output_schema_failure")
    dependencies = _obj(payload["dependencies"], DEPENDENCY_ROLES, "output_schema_failure")
    if any(_sha(value, "output_schema_failure") != value for value in dependencies.values()):
        raise AlignmentFailure("output_schema_failure")
    counts = _obj(payload["counts"], COUNT_KEYS, "output_schema_failure")
    if any(not _int(value) or value < 0 for value in counts.values()):
        raise AlignmentFailure("output_schema_failure")
    checks = _obj(payload["checks"], CHECK_KEYS, "output_schema_failure")
    if any(type(value) is not bool for value in checks.values()):
        raise AlignmentFailure("output_schema_failure")
    manifests = _obj(payload["manifests"], MANIFEST_KEYS, "output_schema_failure")
    if any(_sha(value, "output_schema_failure") != value for value in manifests.values()):
        raise AlignmentFailure("output_schema_failure")
    cost = _obj(payload["cost"], tuple(COST), "output_schema_failure")
    if cost != COST or any(not _int(cost[key]) for key in COST if key != "external_calls_blocked") or cost["external_calls_blocked"] is not True:
        raise AlignmentFailure("output_schema_failure")
    auth = payload["authorization"]
    if not isinstance(auth, dict) or set(auth) != set((*AUTH_BOOL_KEYS, "facts_moved_to_ok", "M3")) or any(type(auth[key]) is not bool for key in AUTH_BOOL_KEYS) or not _int(auth["facts_moved_to_ok"]) or auth != _authorization(auth["preregistration_frozen"], auth["execution_permit_valid"]) or (auth["execution_permit_valid"] and not auth["preregistration_frozen"]):
        raise AlignmentFailure("output_schema_failure")
    failures = payload["failures"]
    if not isinstance(failures, list) or any(code not in FAILURE_CODES for code in failures) or len(failures) != len(set(failures)):
        raise AlignmentFailure("output_schema_failure")
    documents, tasks = payload["documents"], payload["tasks"]
    if payload["status"] == "NO_GO":
        if not isinstance(documents, list) or not isinstance(tasks, list) or documents or tasks or counts != {key: 0 for key in COUNT_KEYS} or manifests != {key: ZERO_SHA for key in MANIFEST_KEYS} or dependencies != {key: ZERO_SHA for key in DEPENDENCY_ROLES} or any(value is not False for value in checks.values()) or len(failures) != 1:
            raise AlignmentFailure("output_schema_failure")
        return
    if payload["status"] != "CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY" or failures or counts != EXPECTED_COUNTS or any(value is not True for value in checks.values()) or not auth["preregistration_frozen"] or not auth["execution_permit_valid"]:
        raise AlignmentFailure("output_schema_failure")
    if not isinstance(documents, list) or not isinstance(tasks, list) or len(documents) != 18 or len(tasks) != 21:
        raise AlignmentFailure("output_schema_failure")
    changed_documents = []
    document_ids: set[str] = set()
    for row in documents:
        _obj(row, DOCUMENT_KEYS, "output_schema_failure")
        extraction = _sha(row["extraction_sha256"], "output_schema_failure")
        gains = row["coverage_gain_block_indexes"]
        if not isinstance(gains, list) or any(not _int(value) or value < 0 for value in gains) or gains != sorted(set(gains)):
            raise AlignmentFailure("output_schema_failure")
        if extraction in document_ids or row["schema"] != "s117_m210_candidate_document_alignment_v1" or not _receipt(row, "m210_document_receipt_sha256") or row["baseline_alignment_status"] not in ("exact_whitespace_equivalent", "unresolved") or row["candidate_alignment_status"] != "exact_whitespace_equivalent" or _sha(row["candidate_surface_sha256"], "output_schema_failure") != row["candidate_surface_sha256"] or _sha(row["raw_surface_sha256"], "output_schema_failure") != row["raw_surface_sha256"] or row["candidate_surface_sha256"] != row["raw_surface_sha256"] or row["candidate_surface_equal_raw"] is not True or row["candidate_missing_block_indexes"] != [] or row["coverage_regression_block_indexes"] != [] or type(row["fingerprint_multiset_changed"]) is not bool or row["candidate_mapping_mode"] not in ("unchanged_fingerprint_multiset", "frozen_changed_delta") or (row["fingerprint_multiset_changed"] and row["candidate_mapping_mode"] != "frozen_changed_delta") or (not row["fingerprint_multiset_changed"] and row["candidate_mapping_mode"] != "unchanged_fingerprint_multiset"):
            raise AlignmentFailure("output_schema_failure")
        document_ids.add(extraction)
        if row["fingerprint_multiset_changed"]:
            changed_documents.append(row)
        elif row["baseline_alignment_status"] != "exact_whitespace_equivalent" or gains:
            raise AlignmentFailure("output_schema_failure")
    if len(changed_documents) != 1 or changed_documents[0]["extraction_sha256"] != CHANGED_EXTRACTION or changed_documents[0]["baseline_alignment_status"] != "unresolved" or changed_documents[0]["coverage_gain_block_indexes"] != [630, 631]:
        raise AlignmentFailure("output_schema_failure")
    if documents != sorted(documents, key=lambda row: row["extraction_sha256"]):
        raise AlignmentFailure("output_schema_failure")
    doc_receipts = {row["extraction_sha256"]: row["m210_document_receipt_sha256"] for row in documents}
    task_ids: set[str] = set()
    changed_tasks = []
    for row in tasks:
        _obj(row, TASK_KEYS, "output_schema_failure")
        task_id = _uuid(row["local_row_id"], "output_schema_failure")
        extraction = _sha(row["extraction_sha256"], "output_schema_failure")
        for name in ("original_task_evidence_receipt_sha256", "target_content_sha256", "target_fingerprint_sha256", "overlap_fingerprints_sha256", "m210_document_receipt_sha256", "m210_task_receipt_sha256"):
            _sha(row[name], "output_schema_failure")
        if task_id in task_ids or extraction not in doc_receipts or row["schema"] != "s117_m210_candidate_task_alignment_v1" or not _receipt(row, "m210_task_receipt_sha256") or any(not _int(row[name]) for name in ("target_source_block_start", "target_source_block_end", "target_baseline_occurrences", "target_candidate_occurrences", "overlap_count")) or row["target_source_block_start"] < 0 or row["target_source_block_end"] < row["target_source_block_start"] or row["target_baseline_occurrences"] != 1 or row["target_candidate_occurrences"] != 1 or row["overlap_count"] != 1 or row["all_overlap_fingerprints_unique"] is not True or row["changed_delta_disjoint_from_target"] is not True or row["candidate_alignment_status"] != "exact_whitespace_equivalent" or row["baseline_alignment_status"] not in ("exact_whitespace_equivalent", "unresolved") or row["baseline_alignment_status"] != next(document["baseline_alignment_status"] for document in documents if document["extraction_sha256"] == extraction) or row["m210_document_receipt_sha256"] != doc_receipts.get(extraction):
            raise AlignmentFailure("output_schema_failure")
        if row["candidate_membership_mode"] == "frozen_delta_unchanged_mapping":
            if task_id != CHANGED_TASK or extraction != CHANGED_EXTRACTION or not _int(row["candidate_ordinal"]) or row["candidate_ordinal"] != 61 or row["baseline_alignment_status"] != "unresolved" or row["target_content_sha256"] != CHANGED_TARGET_CONTENT_SHA or row["target_fingerprint_sha256"] != CHANGED_TARGET_FINGERPRINT_SHA or row["target_source_block_start"] != 796 or row["target_source_block_end"] != 796:
                raise AlignmentFailure("output_schema_failure")
            changed_tasks.append(row)
        elif row["candidate_membership_mode"] == "unique_fingerprint_membership":
            if row["candidate_ordinal"] is not None or row["baseline_alignment_status"] != "exact_whitespace_equivalent":
                raise AlignmentFailure("output_schema_failure")
        else:
            raise AlignmentFailure("output_schema_failure")
        task_ids.add(task_id)
    if len(changed_tasks) != 1:
        raise AlignmentFailure("output_schema_failure")
    if tasks != sorted(tasks, key=lambda row: row["local_row_id"]):
        raise AlignmentFailure("output_schema_failure")
    expected_manifests = _manifests(documents, tasks)
    if manifests != expected_manifests or manifests != EXPECTED_OUTPUT_MANIFESTS:
        raise AlignmentFailure("manifest_integrity_failure")


def _failure_payload(code: str, prereg: bool = False, permit: bool = False) -> dict[str, Any]:
    return {
        "instrument": "s117_m210_candidate_live_alignment_v1", "schema_version": 1,
        "status": "NO_GO", "loadable": False,
        "authority": "frozen_candidate_projection_and_delta_raw_parsed_block_surface_only",
        "candidate_evidence_mode": "substituted_from_m27c_treatment_via_m28_exact_projection_hash",
        "candidate_rows_persisted": False, "candidate_row_ids_claimed": False,
        "dependencies": {key: ZERO_SHA for key in DEPENDENCY_ROLES},
        "counts": {key: 0 for key in COUNT_KEYS}, "documents": [], "tasks": [],
        "manifests": {key: ZERO_SHA for key in MANIFEST_KEYS},
        "checks": {key: False for key in CHECK_KEYS},
        "failures": [code if code in FAILURE_CODES else "internal_failure"],
        "cost": dict(COST), "authorization": _authorization(prereg, permit),
    }


def _resolve_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise AlignmentFailure("contract_integrity_failure")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AlignmentFailure("contract_integrity_failure")
    base, current = root.resolve(), root
    if current.is_symlink():
        raise AlignmentFailure("contract_integrity_failure")
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise AlignmentFailure("contract_integrity_failure")
    try:
        result = current.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AlignmentFailure("contract_integrity_failure") from exc
    if not result.is_file() or not result.is_relative_to(base):
        raise AlignmentFailure("contract_integrity_failure")
    return result


def _validate_prereg(value: Any) -> dict[str, Any]:
    value = _obj(value, ("instrument", "schema_version", "status", "scope", "frozen_inputs", "expected", "execution", "authorization"))
    if value["instrument"] != "s117_m210_candidate_live_alignment_prereg_v1" or not _int(value["schema_version"]) or value["schema_version"] != 1 or value["status"] != "frozen_before_execution":
        raise AlignmentFailure("contract_integrity_failure")
    frozen = _obj(value["frozen_inputs"], tuple(SELECTED_PATHS))
    for role, relative in SELECTED_PATHS.items():
        item = _obj(frozen[role], ("path", "sha256", "format", "use"))
        parsed = role in PRIMARY_JSON_ROLES
        if item["path"] != relative or item["format"] != ("JSON" if parsed else "blob") or item["use"] != ("parsed" if parsed else "hash-only"):
            raise AlignmentFailure("contract_integrity_failure")
        _sha(item["sha256"])
    expected = _obj(value["expected"], (
        "counts", "projection", "changed_extraction_sha256", "changed_task_id",
        "changed_mapping", "check_keys", "failure_codes", "dependency_roles",
        "document_identities_sha256", "task_identities_sha256",
    ))
    if expected != {
        "counts": EXPECTED_COUNTS,
        "projection": {"bytes": PROJECTION_BYTES, "sha256": PROJECTION_SHA},
        "changed_extraction_sha256": CHANGED_EXTRACTION,
        "changed_task_id": CHANGED_TASK,
        "changed_mapping": {
            "target_baseline_ordinal": 61, "target_candidate_ordinal": 61,
            "modified_baseline_ordinal": 39, "modified_candidate_ordinal": 39,
            "coverage_gain_block_indexes": [630, 631],
        },
        "check_keys": list(CHECK_KEYS), "failure_codes": list(FAILURE_CODES),
        "dependency_roles": list(DEPENDENCY_ROLES),
        "document_identities_sha256": DOCUMENT_IDENTITIES_SHA,
        "task_identities_sha256": TASK_IDENTITIES_SHA,
    }:
        raise AlignmentFailure("contract_integrity_failure")
    if (
        not isinstance(expected["counts"], dict)
        or any(not _int(item) for item in expected["counts"].values())
        or not _int(expected["projection"]["bytes"])
        or any(not _int(expected["changed_mapping"][name]) for name in ("target_baseline_ordinal", "target_candidate_ordinal", "modified_baseline_ordinal", "modified_candidate_ordinal"))
        or any(not _int(item) for item in expected["changed_mapping"]["coverage_gain_block_indexes"])
    ):
        raise AlignmentFailure("contract_integrity_failure")
    scope = _obj(value["scope"], ("purpose", "authority", "allowed", "forbidden"))
    if scope != {
        "purpose": "derive_candidate_live_alignment_from_frozen_evidence",
        "authority": "frozen_candidate_projection_and_delta_raw_parsed_block_surface_only",
        "allowed": ["local_frozen_evidence_read", "local_eval_write"],
        "forbidden": ["raw_store_read", "chunk_execution", "candidate_execution", "database", "network", "models"],
    }:
        raise AlignmentFailure("contract_integrity_failure")
    execution = _obj(value["execution"], ("seeds", "outputs", "perturbation", "required"))
    if execution != {
        "seeds": [1, 2], "outputs": {"1": OUTPUTS[1], "2": OUTPUTS[2]},
        "perturbation": "shuffle_documents_and_tasks_then_restore_canonical_order",
        "required": ["focused_tests_green", "adversarial_go", "permit_valid"],
    }:
        raise AlignmentFailure("contract_integrity_failure")
    if any(not _int(item) for item in execution["seeds"]):
        raise AlignmentFailure("contract_integrity_failure")
    authorization = _obj(value["authorization"], (
        "preregistration_frozen", "alignment_execution", "raw_store_read",
        "chunk_execution", "additional_candidate_execution", "database", "network",
        "models", "load", "serving", "deploy", "facts_moved_to_ok", "M3",
    ))
    if authorization != {
        "preregistration_frozen": True, "alignment_execution": False,
        "raw_store_read": False, "chunk_execution": False,
        "additional_candidate_execution": False, "database": False,
        "network": False, "models": False, "load": False, "serving": False,
        "deploy": False, "facts_moved_to_ok": 0, "M3": "BLOCKED",
    } or any(type(authorization[key]) is not bool for key in authorization if key not in ("facts_moved_to_ok", "M3")) or not _int(authorization["facts_moved_to_ok"]):
        raise AlignmentFailure("contract_integrity_failure")
    return value


def _validate_permit(value: Any, prereg: dict[str, Any], prereg_sha: str, seed: int) -> None:
    value = _obj(value, ("instrument", "schema_version", "status", "bindings", "allowed_seeds", "additional_candidate_execution", "authorization"))
    if value["instrument"] != "s117_m210_candidate_live_alignment_execution_permit_v1" or not _int(value["schema_version"]) or value["schema_version"] != 1 or value["status"] != "authorized_two_seeded_local_alignment_derivations" or value["allowed_seeds"] != [1, 2] or any(not _int(item) for item in value["allowed_seeds"]) or seed not in value["allowed_seeds"] or value["additional_candidate_execution"] is not False:
        raise AlignmentFailure("contract_integrity_failure")
    bindings = _obj(value["bindings"], ("preregistration_sha256", "design_sha256", "runner_sha256", "runner_tests_sha256"))
    expected = {"preregistration_sha256": prereg_sha, "design_sha256": prereg["frozen_inputs"]["design"]["sha256"], "runner_sha256": prereg["frozen_inputs"]["runner"]["sha256"], "runner_tests_sha256": prereg["frozen_inputs"]["runner_tests"]["sha256"]}
    if bindings != expected:
        raise AlignmentFailure("contract_integrity_failure")
    authorization = _obj(value["authorization"], (
        "alignment_execution", "raw_store_read", "chunk_execution",
        "additional_candidate_execution", "database", "network", "models", "load",
        "serving", "deploy", "facts_moved_to_ok", "M3",
    ))
    if authorization != {
        "alignment_execution": True, "raw_store_read": False,
        "chunk_execution": False, "additional_candidate_execution": False,
        "database": False, "network": False, "models": False, "load": False,
        "serving": False, "deploy": False, "facts_moved_to_ok": 0,
        "M3": "BLOCKED",
    } or any(type(authorization[key]) is not bool for key in authorization if key not in ("facts_moved_to_ok", "M3")) or not _int(authorization["facts_moved_to_ok"]):
        raise AlignmentFailure("contract_integrity_failure")


def _load_authorized(seed: int, root: Path = ROOT) -> tuple[dict[str, bytes], dict[str, str]]:
    try:
        prereg_raw = _resolve_file(root, PREREG_RELATIVE).read_bytes()
        prereg = _validate_prereg(strict_json(prereg_raw))
    except (AlignmentFailure, OSError) as exc:
        code = exc.code if isinstance(exc, AlignmentFailure) else "contract_integrity_failure"
        raise PreflightFailure(code) from exc
    observed, raws = {}, {}
    try:
        for role, relative in SELECTED_PATHS.items():
            raw = _resolve_file(root, relative).read_bytes()
            digest = sha(raw)
            if digest != prereg["frozen_inputs"][role]["sha256"]:
                raise AlignmentFailure("contract_integrity_failure")
            observed[role] = digest
            if role in PRIMARY_JSON_ROLES:
                raws[role] = raw
        for left, right in SEED_PAIRS:
            if observed[left] != observed[right]:
                raise AlignmentFailure(left.split("_")[0] + "_seed_drift")
    except (AlignmentFailure, OSError) as exc:
        code = exc.code if isinstance(exc, AlignmentFailure) else "contract_integrity_failure"
        raise PreflightFailure(code) from exc
    prereg_sha = sha(prereg_raw)
    try:
        permit_raw = _resolve_file(root, PERMIT_RELATIVE).read_bytes()
        _validate_permit(strict_json(permit_raw), prereg, prereg_sha, seed)
    except (AlignmentFailure, OSError) as exc:
        code = exc.code if isinstance(exc, AlignmentFailure) else "contract_integrity_failure"
        raise PreflightFailure(code, True, False) from exc
    return raws, dict(sorted({**observed, "preregistration": prereg_sha, "execution_permit": sha(permit_raw)}.items()))


def _output_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise AlignmentFailure("contract_integrity_failure")
    parts = relative.split("/")
    if len(parts) < 2 or any(part in ("", ".", "..") for part in parts):
        raise AlignmentFailure("contract_integrity_failure")
    base, parent = root.resolve(), root
    if root.is_symlink():
        raise AlignmentFailure("contract_integrity_failure")
    for part in parts[:-1]:
        parent = parent / part
        if parent.is_symlink():
            raise AlignmentFailure("contract_integrity_failure")
        if parent.exists():
            if not parent.is_dir():
                raise AlignmentFailure("contract_integrity_failure")
        else:
            try:
                parent.mkdir()
            except OSError as exc:
                raise AlignmentFailure("contract_integrity_failure") from exc
        if parent.is_symlink() or not parent.resolve().is_relative_to(base):
            raise AlignmentFailure("contract_integrity_failure")
    path = parent / parts[-1]
    if path.exists() or path.is_symlink():
        raise AlignmentFailure("contract_integrity_failure")
    if not parent.resolve().is_relative_to(base):
        raise AlignmentFailure("contract_integrity_failure")
    return path


def _write(root: Path, relative: str, payload: dict[str, Any]) -> None:
    validate_output(payload)
    path = _output_path(root, relative)
    try:
        with path.open("xb") as handle:
            handle.write(canonical(payload) + b"\n")
    except OSError as exc:
        raise AlignmentFailure("contract_integrity_failure") from exc


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "--seed" or args[1] not in ("1", "2"):
        return 2
    seed = int(args[1])
    prereg = permit = False
    original_socket = socket.socket
    try:
        raws, dependencies = _load_authorized(seed)
        prereg = permit = True
        socket.socket = lambda *_, **__: (_ for _ in ()).throw(AlignmentFailure("external_call_attempt"))
        parsed = {role: strict_json(raw) for role, raw in raws.items()}
        payload = build_payload(parsed["m27a_seed1"], parsed["m27c_seed1"], parsed["m28_seed1"], parsed["m29_seed1"], dependencies, seed)
        _write(ROOT, OUTPUTS[seed], payload)
        print('{"failures":[],"status":"CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY"}')
        return 0
    except PreflightFailure as exc:
        prereg, permit = exc.prereg, exc.permit
        payload = _failure_payload(exc.code, prereg, permit)
    except AlignmentFailure as exc:
        payload = _failure_payload(exc.code, prereg, permit)
    except Exception:
        payload = _failure_payload("internal_failure", prereg, permit)
    finally:
        socket.socket = original_socket
    try:
        _write(ROOT, OUTPUTS[seed], payload)
    except Exception:
        return 1
    print(json.dumps({"failures": payload["failures"], "status": "NO_GO"}, sort_keys=True, separators=(",", ":")))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
