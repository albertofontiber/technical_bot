#!/usr/bin/env python3
"""Project the fail-closed M2.5 document-binding fallback entirely locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m25_freeze_primary_binding as primary
from scripts import s117_m2_legacy_reuse_analysis as m2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m25_projection_prereg_v2.yaml"
_CANONICAL_SHA = re.compile(r"^[0-9a-f]{64}$")
_BACKFILL_SENTINEL = re.compile(r"^backfill:[0-9a-f]{64}$")

BINDING_TERMINALS = (
    "primary_unique_active_pdf_sha",
    "primary_non_active_pdf_sha",
    "primary_ambiguous_pdf_sha",
    "fallback_no_base_chunks",
    "fallback_null_document_id",
    "fallback_ambiguous_document_id",
    "fallback_missing_document",
    "fallback_ambiguous_document_row",
    "fallback_non_active_document",
    "fallback_conflicting_valid_pdf_sha",
    "fallback_shared_document_id_across_extractions",
    "fallback_unique_active_backfill_binding",
    "fallback_null_pdf_sha",
    "fallback_empty_pdf_sha",
    "fallback_malformed_pdf_sha",
)


def _canonical(value: Any) -> bytes:
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


def _iter_hashed_paths(value: Any):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from _iter_hashed_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_hashed_paths(child)


def preflight(
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    snapshot: Path,
    baseline_path: Path,
    derived_snapshot: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.5 projection prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument") != "s117_m25_projection_prereg_v2"
        or prereg.get("status") != "frozen_before_seeded_projection"
    ):
        raise RuntimeError("M2.5 projection prereg contract drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.5 frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.5 frozen input drift: {item['path']}")

    selected = prereg["selected_paths"]
    expected_snapshot = (ROOT / selected["snapshot"]).resolve()
    expected_baseline = (ROOT / selected["primary_baseline"]).resolve()
    expected_derived = (ROOT / selected["derived_snapshot"]).resolve()
    if snapshot.resolve() != expected_snapshot:
        raise RuntimeError("M2.5 snapshot path mismatch")
    if baseline_path.resolve() != expected_baseline:
        raise RuntimeError("M2.5 primary baseline path mismatch")
    if derived_snapshot.resolve() != expected_derived:
        raise RuntimeError("M2.5 derived snapshot path mismatch")

    m2_prereg = ROOT / prereg["selected_paths"]["m2_prereg"]
    m2_state = m2.preflight(m2_prereg, store, sidecar_root)
    return prereg, m2_state


def _source_sha_terminal(value: Any, target_sha: str) -> str:
    if value is None:
        return "fallback_null_pdf_sha"
    if isinstance(value, str) and value == "":
        return "fallback_empty_pdf_sha"
    if isinstance(value, str) and _CANONICAL_SHA.fullmatch(value):
        if value == target_sha:
            raise RuntimeError("primary-absent target has equal canonical document SHA")
        return "fallback_conflicting_valid_pdf_sha"
    if isinstance(value, str) and _BACKFILL_SENTINEL.fullmatch(value):
        return "fallback_unique_active_backfill_binding"
    return "fallback_malformed_pdf_sha"


def _classify_binding(
    baseline_row: dict[str, Any],
    base_chunks: list[dict[str, Any]],
    documents_by_id: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    sha = baseline_row["extraction_sha256"]
    primary_terminal = baseline_row["terminal"]
    if primary_terminal != "primary_absent_pdf_sha":
        payload = {
            "extraction_sha256": sha,
            "terminal": primary_terminal,
            "document_id": (
                baseline_row["document_id"]
                if primary_terminal == "primary_unique_active_pdf_sha"
                else None
            ),
            "status": baseline_row["status"],
            "legacy_base_rows": len(base_chunks),
            "binding_origin": "primary_pdf_sha",
            "primary_receipt_sha256": baseline_row["receipt_sha256"],
        }
    elif not base_chunks:
        payload = {
            "extraction_sha256": sha,
            "terminal": "fallback_no_base_chunks",
            "document_id": None,
            "status": None,
            "legacy_base_rows": 0,
            "binding_origin": "none",
            "primary_receipt_sha256": baseline_row["receipt_sha256"],
        }
    elif any(chunk.get("document_id") is None for chunk in base_chunks):
        payload = {
            "extraction_sha256": sha,
            "terminal": "fallback_null_document_id",
            "document_id": None,
            "status": None,
            "legacy_base_rows": len(base_chunks),
            "binding_origin": "none",
            "primary_receipt_sha256": baseline_row["receipt_sha256"],
        }
    else:
        document_ids = {chunk["document_id"] for chunk in base_chunks}
        if len(document_ids) != 1:
            terminal = "fallback_ambiguous_document_id"
            document_id = None
            status = None
        else:
            candidate_id = next(iter(document_ids))
            document_rows = documents_by_id.get(candidate_id, [])
            if not document_rows:
                terminal = "fallback_missing_document"
                document_id = None
                status = None
            elif len(document_rows) > 1:
                terminal = "fallback_ambiguous_document_row"
                document_id = None
                status = None
            else:
                document = document_rows[0]
                status = document.get("status")
                if status != "active":
                    terminal = "fallback_non_active_document"
                    document_id = None
                else:
                    terminal = _source_sha_terminal(
                        document.get("source_pdf_sha256"), sha
                    )
                    document_id = (
                        candidate_id
                        if terminal == "fallback_unique_active_backfill_binding"
                        else None
                    )
        payload = {
            "extraction_sha256": sha,
            "terminal": terminal,
            "document_id": document_id,
            "status": status,
            "legacy_base_rows": len(base_chunks),
            "binding_origin": (
                "fallback_extraction_sha"
                if terminal == "fallback_unique_active_backfill_binding"
                else "none"
            ),
            "primary_receipt_sha256": baseline_row["receipt_sha256"],
        }
    payload["receipt_sha256"] = _sha_bytes(_canonical(payload))
    return payload


def _apply_inverse_uniqueness(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fail closed when one legacy document is claimed by multiple raws."""
    provisional = [
        row
        for row in bindings
        if row["terminal"] == "fallback_unique_active_backfill_binding"
    ]
    extraction_shas_by_document: dict[str, list[str]] = defaultdict(list)
    for row in provisional:
        extraction_shas_by_document[row["document_id"]].append(
            row["extraction_sha256"]
        )

    result: list[dict[str, Any]] = []
    for row in bindings:
        document_id = row.get("document_id")
        shared_shas = (
            sorted(extraction_shas_by_document.get(document_id, []))
            if row["terminal"] == "fallback_unique_active_backfill_binding"
            else []
        )
        if len(shared_shas) <= 1:
            result.append(row)
            continue
        payload = {key: value for key, value in row.items() if key != "receipt_sha256"}
        payload.update(
            {
                "terminal": "fallback_shared_document_id_across_extractions",
                "document_id": None,
                "binding_origin": "none",
                "observed_document_id": document_id,
                "shared_extraction_sha256": shared_shas,
            }
        )
        payload["receipt_sha256"] = _sha_bytes(_canonical(payload))
        result.append(payload)
    return result


def _without_runtime_receipts(result: dict[str, Any]) -> dict[str, Any]:
    copy = dict(result)
    copy.pop("dependencies", None)
    copy.pop("determinism", None)
    copy.pop("capture_receipt", None)
    return copy


def _delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {
        key: after.get(key, 0) - before.get(key, 0)
        for key in sorted(set(after) | set(before))
    }


def _counter_matches_expected(
    observed: Counter, expected: dict[str, int]
) -> bool:
    return set(observed) <= set(expected) and {
        key: observed.get(key, 0) for key in expected
    } == expected


def _workload_delta(after: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    return {
        cohort: {
            key: after[cohort][key] - before[cohort][key]
            for key in after[cohort]
            if isinstance(after[cohort][key], int)
        }
        for cohort in after
    }


def _derived_preservation_checks(
    source_documents: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
    derived_documents: list[dict[str, Any]],
    derived_chunks: list[dict[str, Any]],
    source_receipt_before: dict[str, Any],
    source_receipt_after: dict[str, Any],
) -> dict[str, bool]:
    original_count = len(source_documents)
    derived_originals = derived_documents[:original_count]
    derived_aliases = derived_documents[original_count:]
    source_multiset = Counter(_canonical(row) for row in source_documents)
    derived_original_multiset = Counter(_canonical(row) for row in derived_originals)
    return {
        "source_snapshot_receipt_unchanged": source_receipt_before
        == source_receipt_after,
        "source_chunks_byte_logically_identical": _canonical(derived_chunks)
        == _canonical(source_chunks),
        "source_chunk_count_unchanged": len(derived_chunks) == len(source_chunks),
        "source_documents_prefix_byte_logically_identical": _canonical(
            derived_originals
        )
        == _canonical(source_documents),
        "source_documents_multiset_identical": source_multiset
        == derived_original_multiset,
        "only_exact_safe_aliases_added": _canonical(derived_aliases)
        == _canonical(aliases),
        "derived_document_count_exact": len(derived_documents)
        == len(source_documents) + len(aliases),
    }


def _semantic_delta_checks(
    funnel_delta: dict[str, int],
    terminal_delta: dict[str, int],
    eligible_rows: int,
) -> dict[str, bool]:
    downstream_terminals = (
        "content_miss",
        "structure_miss",
        "metadata_miss",
        "ambiguous_donor",
        "unique_donor_context_missing",
        "unique_donor_embedding_missing_or_wrong_dim",
        "legacy_context_and_embedding_candidate",
    )
    invariant_terminals = (
        "policy_excluded_register_only",
        "policy_excluded_language",
        "document_status_excluded",
        "no_extraction_donor",
    )
    stage_keys = (
        "content_hit",
        "structure_hit",
        "metadata_hit",
        "unique_donor",
        "context_reuse_candidate",
        "embedding_reuse_candidate",
    )
    stage = [funnel_delta.get(key, 0) for key in stage_keys]
    return {
        "funnel_population_invariant": funnel_delta.get("total_local", 0) == 0
        and funnel_delta.get("policy_eligible", 0) == 0,
        "unresolved_delta_exact": terminal_delta.get(
            "target_document_unresolved", 0
        )
        == -eligible_rows,
        "resolved_active_extraction_delta_exact": all(
            funnel_delta.get(key, 0) == eligible_rows
            for key in (
                "target_document_resolved",
                "target_document_active",
                "extraction_hit",
            )
        ),
        "pre_downstream_terminals_invariant": all(
            terminal_delta.get(key, 0) == 0 for key in invariant_terminals
        ),
        "downstream_terminal_deltas_nonnegative": all(
            terminal_delta.get(key, 0) >= 0 for key in downstream_terminals
        ),
        "downstream_terminal_population_exact": sum(
            terminal_delta.get(key, 0) for key in downstream_terminals
        )
        == eligible_rows,
        "downstream_funnel_deltas_monotonic": (
            all(0 <= value <= eligible_rows for value in stage)
            and all(left >= right for left, right in zip(stage, stage[1:]))
        ),
        "downstream_waterfall_reconciled": (
            eligible_rows - funnel_delta.get("content_hit", 0)
            == terminal_delta.get("content_miss", 0)
            and funnel_delta.get("content_hit", 0)
            - funnel_delta.get("structure_hit", 0)
            == terminal_delta.get("structure_miss", 0)
            and funnel_delta.get("structure_hit", 0)
            - funnel_delta.get("metadata_hit", 0)
            == terminal_delta.get("metadata_miss", 0)
            and funnel_delta.get("metadata_hit", 0)
            - funnel_delta.get("unique_donor", 0)
            == terminal_delta.get("ambiguous_donor", 0)
            and funnel_delta.get("unique_donor", 0)
            - funnel_delta.get("context_reuse_candidate", 0)
            == terminal_delta.get("unique_donor_context_missing", 0)
            and funnel_delta.get("context_reuse_candidate", 0)
            - funnel_delta.get("embedding_reuse_candidate", 0)
            == terminal_delta.get(
                "unique_donor_embedding_missing_or_wrong_dim", 0
            )
            and funnel_delta.get("embedding_reuse_candidate", 0)
            == terminal_delta.get("legacy_context_and_embedding_candidate", 0)
        ),
    }


def run_projection(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    snapshot: Path,
    baseline_path: Path,
    derived_snapshot: Path,
) -> dict[str, Any]:
    prereg, m2_state = preflight(
        prereg_path,
        store,
        sidecar_root,
        snapshot,
        baseline_path,
        derived_snapshot,
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_rows = baseline["rows"]
    baseline_by_sha = {row["extraction_sha256"]: row for row in baseline_rows}
    if len(baseline_by_sha) != 1068:
        raise RuntimeError("M2.5 primary baseline cardinality drift")

    header, documents, remote_chunks, source_snapshot_receipt = m2.read_snapshot(snapshot)
    documents_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    documents_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        value = document.get("source_pdf_sha256")
        if isinstance(value, str):
            documents_by_sha[value].append(document)
        documents_by_id[document["id"]].append(document)
    base_by_extraction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in remote_chunks:
        if chunk.get("parent_id") is None:
            base_by_extraction[chunk.get("extraction_sha256")].append(chunk)

    recomputed_primary = [
        primary._classify_primary(row["extraction_sha256"], documents_by_sha)
        for row in baseline_rows
    ]
    primary_receipts_identical = _canonical(recomputed_primary) == _canonical(
        baseline_rows
    )
    if not primary_receipts_identical:
        raise RuntimeError("M2.5 primary receipts drift")
    primary_manifest = hashlib.sha256()
    for row in recomputed_primary:
        primary_manifest.update(_canonical(row) + b"\n")
    primary_manifest_identical = (
        primary_manifest.hexdigest() == baseline["primary_manifest_sha256"]
    )
    if not primary_manifest_identical:
        raise RuntimeError("M2.5 primary manifest drift")

    forward_bindings = [
        _classify_binding(
            baseline_by_sha[sha],
            base_by_extraction.get(sha, []),
            documents_by_id,
        )
        for sha in sorted(baseline_by_sha)
    ]
    bindings = _apply_inverse_uniqueness(forward_bindings)
    terminal_counts = Counter(row["terminal"] for row in bindings)
    if sum(terminal_counts.values()) != 1068:
        raise RuntimeError("M2.5 binding taxonomy is not closed")
    unknown_terminals = set(terminal_counts) - set(BINDING_TERMINALS)
    if unknown_terminals:
        raise RuntimeError(f"M2.5 unknown binding terminals: {sorted(unknown_terminals)}")
    binding_manifest = hashlib.sha256()
    for row in bindings:
        binding_manifest.update(_canonical(row) + b"\n")

    safe_bindings = [
        row
        for row in bindings
        if row["terminal"] == "fallback_unique_active_backfill_binding"
    ]
    aliases = [
        {
            "id": row["document_id"],
            "source_pdf_sha256": row["extraction_sha256"],
            "status": "active",
        }
        for row in safe_bindings
    ]
    derived_header = {
        **header,
        "schema": "s117_m25_derived_snapshot_v1",
        "derived_from_gzip_sha256": source_snapshot_receipt["gzip_sha256"],
        "binding_manifest_sha256": binding_manifest.hexdigest(),
        "synthetic_document_aliases": len(aliases),
    }
    derived_documents = [
        {"kind": "document", **document} for document in documents
    ] + [{"kind": "document", **alias} for alias in aliases]
    derived_chunks = [{"kind": "chunk", **chunk} for chunk in remote_chunks]
    derived_receipt = m2._write_snapshot_lines(
        derived_snapshot,
        derived_header,
        derived_documents,
        derived_chunks,
    )
    _, readback_documents, readback_chunks, _ = m2.read_snapshot(derived_snapshot)
    _, _, _, source_snapshot_receipt_after = m2.read_snapshot(snapshot)
    preservation_checks = _derived_preservation_checks(
        documents,
        remote_chunks,
        aliases,
        readback_documents,
        readback_chunks,
        source_snapshot_receipt,
        source_snapshot_receipt_after,
    )

    s117_result_path = ROOT / m2_state["prereg"]["frozen_inputs"][
        "s117_development_result"
    ]["path"]
    local_rows, local_receipt = m2.build_local_population(
        m2_state["record_files"],
        s117_result_path,
        m2_state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
        sidecar_root,
    )
    if local_receipt["rows"] != 31212 or local_receipt["documents"] != 1068:
        raise RuntimeError("M2.5 local population drift")

    baseline_analysis = m2.analyze_snapshot(snapshot, local_rows, local_receipt)
    frozen_m2 = json.loads(
        (ROOT / prereg["selected_paths"]["m2_seed_baseline"]).read_text(
            encoding="utf-8"
        )
    )
    frozen_core = _without_runtime_receipts(frozen_m2)
    primary_m2_analysis_identical = _canonical(baseline_analysis) == _canonical(
        frozen_core
    )
    if not primary_m2_analysis_identical:
        raise RuntimeError("M2.5 primary M2 analysis drift")

    projected_first = m2.analyze_snapshot(derived_snapshot, local_rows, local_receipt)
    projected_second = m2.analyze_snapshot(derived_snapshot, local_rows, local_receipt)
    projection_in_process_deterministic = _canonical(
        projected_first
    ) == _canonical(projected_second)
    if not projection_in_process_deterministic:
        raise RuntimeError("M2.5 projection is not deterministic in-process")

    local_rows_by_sha = Counter(row["extraction_sha256"] for row in local_rows)
    eligible_rows_by_sha = Counter(
        row["extraction_sha256"]
        for row in local_rows
        if row.get("preterminal") is None
    )
    terminal_local_rows = Counter()
    terminal_eligible_rows = Counter()
    terminal_legacy_rows = Counter()
    for row in bindings:
        terminal = row["terminal"]
        sha = row["extraction_sha256"]
        terminal_local_rows[terminal] += local_rows_by_sha[sha]
        terminal_eligible_rows[terminal] += eligible_rows_by_sha[sha]
        terminal_legacy_rows[terminal] += row["legacy_base_rows"]

    safe_terminal = "fallback_unique_active_backfill_binding"
    safe_shas = {
        row["extraction_sha256"]
        for row in safe_bindings
    }
    safe_preterminals = Counter(
        row.get("preterminal") or "__eligible__"
        for row in local_rows
        if row["extraction_sha256"] in safe_shas
    )
    primary_terminal_counts = Counter(row["terminal"] for row in recomputed_primary)
    expected = prereg["expected_evidence"]
    funnel_delta = _delta(projected_first["funnel"], baseline_analysis["funnel"])
    terminal_delta = _delta(
        projected_first["terminals"], baseline_analysis["terminals"]
    )
    workload_delta = _workload_delta(
        projected_first["workloads"], baseline_analysis["workloads"]
    )
    eligible_safe_rows = terminal_eligible_rows[safe_terminal]
    evidence_checks = {
        "primary_terminal_counts_exact": _counter_matches_expected(
            primary_terminal_counts, expected["primary_terminals"]
        ),
        "binding_document_counts_exact": _counter_matches_expected(
            terminal_counts, expected["binding_documents"]
        ),
        "binding_legacy_row_counts_exact": _counter_matches_expected(
            terminal_legacy_rows, expected["binding_legacy_base_rows"]
        ),
        "safe_raw_count_exact": len(safe_bindings)
        == expected["safe_cohort"]["raws"],
        "safe_document_ids_inverse_unique": len(
            {row["document_id"] for row in safe_bindings}
        )
        == len(safe_bindings),
        "safe_local_row_count_exact": terminal_local_rows[safe_terminal]
        == expected["safe_cohort"]["local_rows"],
        "safe_policy_eligible_row_count_exact": eligible_safe_rows
        == expected["safe_cohort"]["policy_eligible_local_rows"],
        "safe_preterminal_counts_exact": _counter_matches_expected(
            safe_preterminals, expected["safe_cohort"]["preterminals"]
        ),
        "inverse_collisions_fail_closed_with_evidence": all(
            row.get("document_id") is None
            and isinstance(row.get("observed_document_id"), str)
            and len(row.get("shared_extraction_sha256", [])) >= 2
            for row in bindings
            if row["terminal"]
            == "fallback_shared_document_id_across_extractions"
        ),
        "source_snapshot_cardinality_exact": (
            source_snapshot_receipt["documents"]
            == expected["source_snapshot"]["documents"]
            and source_snapshot_receipt["chunks"]
            == expected["source_snapshot"]["chunks"]
        ),
        "derived_snapshot_cardinality_exact": (
            derived_receipt["documents"]
            == expected["derived_snapshot"]["documents"]
            and derived_receipt["chunks"]
            == expected["derived_snapshot"]["chunks"]
        ),
    }
    semantic_checks = _semantic_delta_checks(
        funnel_delta,
        terminal_delta,
        expected["safe_cohort"]["policy_eligible_local_rows"],
    )
    projection_checks_all = all(projected_first["checks"].values())
    checks = {
        "primary_receipts_byte_identical": primary_receipts_identical,
        "primary_manifest_identical": primary_manifest_identical,
        "primary_m2_analysis_identical": primary_m2_analysis_identical,
        "binding_taxonomy_closed": sum(terminal_counts.values()) == 1068
        and set(terminal_counts) <= set(BINDING_TERMINALS),
        "projection_in_process_deterministic": projection_in_process_deterministic,
        "projection_status_go": projected_first["status"] == "GO",
        "projection_checks_all": projection_checks_all,
        "snapshot_vector_payloads_zero": header.get("vector_payloads") == 0,
        "no_admitted_reuse": True,
        **evidence_checks,
        **preservation_checks,
        **semantic_checks,
    }
    result = {
        "instrument": "s117_m25_document_binding_projection_v2",
        "status": "GO" if all(checks.values()) else "NO_GO",
        "source_snapshot": source_snapshot_receipt,
        "derived_snapshot": derived_receipt,
        "primary_invariance": {
            "documents": len(recomputed_primary),
            "manifest_sha256": primary_manifest.hexdigest(),
            "baseline_artifact_sha256": _sha_file(baseline_path),
            "m2_analysis_byte_logically_identical": True,
        },
        "binding": {
            "documents": len(bindings),
            "terminals": {
                terminal: terminal_counts.get(terminal, 0)
                for terminal in BINDING_TERMINALS
            },
            "local_rows_by_terminal": {
                terminal: terminal_local_rows.get(terminal, 0)
                for terminal in BINDING_TERMINALS
            },
            "policy_eligible_local_rows_by_terminal": {
                terminal: terminal_eligible_rows.get(terminal, 0)
                for terminal in BINDING_TERMINALS
            },
            "legacy_base_rows_by_terminal": {
                terminal: terminal_legacy_rows.get(terminal, 0)
                for terminal in BINDING_TERMINALS
            },
            "manifest_sha256": binding_manifest.hexdigest(),
            "rows": bindings,
        },
        "projection": projected_first,
        "delta_vs_m2": {
            "funnel": funnel_delta,
            "terminals": terminal_delta,
            "workloads": workload_delta,
        },
        "claim": {
            "admitted_reuse": False,
            "strict_label": "candidate_only_legacy_v2_reuse",
            "structural_ceiling_authorizing": False,
        },
        "checks": checks,
        "cost": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "vector_payloads": 0,
            "historical_snapshot_capture_reads": 1,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "runner_sha256": _sha_file(Path(__file__)),
            "primary_freeze_sha256": prereg["frozen_inputs"]["primary_freeze"][
                "sha256"
            ],
        },
    }
    logical = _canonical(result)
    result["determinism"] = {
        "same_process_byte_identical": True,
        "logical_payload_sha256": _sha_bytes(logical),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--primary-baseline", type=Path, required=True)
    parser.add_argument("--derived-snapshot", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = run_projection(
        prereg_path=args.prereg,
        store=args.store,
        sidecar_root=args.sidecar_root,
        snapshot=args.snapshot,
        baseline_path=args.primary_baseline,
        derived_snapshot=args.derived_snapshot,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "binding_terminals": result["binding"]["terminals"],
        "policy_eligible_local_rows_by_terminal": result["binding"][
            "policy_eligible_local_rows_by_terminal"
        ],
        "funnel": result["projection"]["funnel"],
        "terminals": result["projection"]["terminals"],
        "workloads": result["projection"]["workloads"],
        "delta_vs_m2": result["delta_vs_m2"],
        "checks": result["checks"],
        "determinism": result["determinism"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "GO" and all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
