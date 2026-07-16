from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts import s117_m27_upstream_sql_budget as audit


def _local(content: str = "Reset at 5 mW.") -> dict:
    return {
        "id": "local-1",
        "extraction_sha256": "a" * 64,
        "chunk_index": 1,
        "content": content,
        "provenance_payload_sha256": "b" * 64,
        "source_block_start": 2,
        "source_block_end": 3,
        "section_title": "Reset",
        "section_path": "Service > Reset",
        "page_number": 4,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": float.hex(0.9),
    }


def _m26(status: str) -> dict:
    return {"structural_identity_status": status}


def _donor(content: str, *, donor_id: str = "donor-1", **overrides) -> dict:
    value = {
        "id": donor_id,
        "chunk_index": 1,
        "content": content,
        "section_title": "Reset",
        "section_path": "Service > Reset",
        "page_number": 4,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": float.hex(0.9),
    }
    value.update(overrides)
    return value


def _provenance(local: dict) -> dict:
    core = {
        "local_row_id": local["id"],
        "extraction_sha256": local["extraction_sha256"],
        "provenance_payload_sha256": local["provenance_payload_sha256"],
        "source_block_start": local["source_block_start"],
        "source_block_end": local["source_block_end"],
        "lineage_valid": True,
    }
    return {**core, "receipt_sha256": audit._sha_bytes(audit._canonical(core))}


def test_surface_safe_normalization_changes_whitespace_only():
    assert audit._surface_tokens("Reset\u00a0 at\n5 mW.") == ["Reset", "at", "5", "mW."]
    assert audit._surface_tokens("5 mW") != audit._surface_tokens("5 MW")
    assert audit._surface_tokens("x²") != audit._surface_tokens("x2")
    assert audit._candidate_tokens("5 mW") == audit._candidate_tokens("5 MW")


def test_protected_tokens_preserve_case_symbols_and_numeric_neighbors():
    protected = audit._protected_tokens(["set", "5", "mW", "then", "X1", "≤", "20", "°C"])
    assert protected == ["set", "5", "mW", "X1", "≤", "20", "°C"]


def test_unique_surface_safe_resegmentation_closes_automatically():
    local = _local()
    row, task = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor("Reset at"), _donor("5 mW.", donor_id="donor-2")],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "exact_resegmentation_evidence"
    assert task is None


def test_case_sensitive_delta_never_closes_automatically():
    local = _local()
    row, task = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor("Reset at"), _donor("5 MW.", donor_id="donor-2")],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "unresolved_requires_adjudication"
    assert task is not None
    assert task["reason"] == "near_or_unresolved_content_delta"


def test_multiple_exact_occurrences_require_adjudication():
    local = _local("Reset")
    row, task = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor("Reset procedure Reset")],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "unresolved_requires_adjudication"
    assert task is not None
    assert task["reason"] == "ambiguous_surface_safe_occurrence"


def test_raw_equal_structure_delta_closes_but_does_not_claim_semantics():
    local = _local()
    donor = _donor(local["content"], page_number=5)
    row, task = audit._audit_row(
        local,
        _m26("no_structural_donor"),
        [donor],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "structure_only_delta"
    assert task is None


def test_invalid_provenance_is_material_risk():
    local = _local()
    receipt = _provenance(local)
    receipt["lineage_valid"] = False
    row, task = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor(local["content"])],
        receipt,
        "live",
    )
    assert row["fidelity_outcome"] == "material_fidelity_risk"
    assert task is None


def _task_payload() -> dict:
    return {
        "local_row_id": "local-1",
        "comparison_receipt_sha256": "c" * 64,
        "raw_evidence_sha256": "d" * 64,
    }


def _adjudication() -> dict:
    return {
        "schema": "s117_m27_fidelity_adjudication_v1",
        "version": 1,
        "task_manifest_sha256": "e" * 64,
        "reviewer": {
            "method": "human_expert",
            "identity": "field-support-reviewer",
            "provider": None,
            "model": None,
        },
        "rows": [{
            "local_row_id": "local-1",
            "comparison_receipt_sha256": "c" * 64,
            "raw_evidence_sha256": "d" * 64,
            "rubric": {
                "negation_changed": False,
                "condition_or_scope_changed": False,
                "warning_or_safety_changed": False,
                "procedure_order_changed": False,
                "reference_target_changed": False,
                "protected_technical_tokens_changed": False,
            },
            "verdict": "benign",
            "rationale": "Whitespace-only extraction artifact.",
        }],
    }


def test_adjudication_contract_cross_checks_identity_and_evidence():
    payload = _adjudication()
    assert audit.validate_adjudication(
        payload,
        expected_task_manifest_sha256="e" * 64,
        tasks=[_task_payload()],
    ) == {"local-1": "benign"}
    model = copy.deepcopy(payload)
    model["reviewer"] = {
        "method": "named_adversarial_model",
        "identity": "review-run-1",
        "provider": None,
        "model": None,
    }
    with pytest.raises(ValueError, match="identity incomplete"):
        audit.validate_adjudication(
            model,
            expected_task_manifest_sha256="e" * 64,
            tasks=[_task_payload()],
        )
    payload["rows"][0]["rubric"]["warning_or_safety_changed"] = True
    with pytest.raises(ValueError, match="rubric/verdict conflict"):
        audit.validate_adjudication(
            payload,
            expected_task_manifest_sha256="e" * 64,
            tasks=[_task_payload()],
        )


def test_workload_separates_exact_counts_from_planning_proxies():
    rows = [
        {
            "extraction_sha256": "a",
            "context_document_chars": 20000,
            "context_instruction_chars": 100,
            "context_input_chars": 20100,
            "content": "x" * 100,
        },
        {
            "extraction_sha256": "a",
            "context_document_chars": 20000,
            "context_instruction_chars": 120,
            "context_input_chars": 20120,
            "content": "y" * 120,
        },
        {
            "extraction_sha256": "b",
            "context_document_chars": 1000,
            "context_instruction_chars": 80,
            "context_input_chars": 1080,
            "content": "z" * 80,
        },
    ]
    result = audit._workload(rows)
    exact = result["exact_before_generation"]
    assert exact["logical_context_calls"] == 3
    assert exact["distinct_extraction_documents"] == 2
    assert exact["subsequent_calls_within_document"] == 1
    assert exact["http_retries"] is None
    minimum = result["context_planning_proxies"]["minimum_cacheable_char4_proxy"]
    assert minimum["cacheable_documents"] == 1
    assert minimum["cacheable_logical_calls"] == 2
    assert result["embedding_precontext_plan"]["exact_batch_manifest_available_after_context_generation_only"]
