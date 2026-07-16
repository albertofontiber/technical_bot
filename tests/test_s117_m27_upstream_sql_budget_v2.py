from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts import s117_m27_upstream_sql_budget_v2 as audit


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
    assert audit._surface_tokens("x\u00b2") != audit._surface_tokens("x2")
    assert audit._candidate_tokens("5 mW") == audit._candidate_tokens("5 MW")


def test_protected_tokens_preserve_case_symbols_and_numeric_neighbors():
    protected = audit._protected_tokens([
        "set", "5", "mW", "then", "X1", "\u2264", "20", "\u00b0C",
    ])
    assert protected == ["set", "5", "mW", "X1", "\u2264", "20", "\u00b0C"]
    expected_codepoints = {0x2264, 0x2265, 0x00B0, 0x00B5, 0x03A9, 0x00D7}
    assert expected_codepoints <= {ord(char) for char in audit._TECHNICAL_SYMBOLS}


def test_unique_surface_safe_resegmentation_closes_automatically():
    local = _local()
    row, task, comparison, raw_evidence = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor("Reset at"), _donor("5 mW.", donor_id="donor-2")],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "exact_resegmentation_evidence"
    assert task is None
    occurrence = comparison["comparison"]["occurrences"][0]
    assert occurrence["donor_chunk_ids"] == ["donor-1", "donor-2"]
    assert len(occurrence["donor_span_raw_sha256"]) == 64
    assert row["comparison_receipt_sha256"] == comparison["receipt_sha256"]
    core = {key: value for key, value in comparison.items() if key != "receipt_sha256"}
    assert comparison["receipt_sha256"] == audit._sha_bytes(audit._canonical(core))


def test_case_sensitive_delta_never_closes_automatically():
    local = _local()
    row, task, comparison, raw_evidence = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [_donor("Reset at"), _donor("5 MW.", donor_id="donor-2")],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "unresolved_requires_adjudication"
    assert task is not None
    assert task["reason"] == "near_or_unresolved_content_delta"
    assert task["candidate_method"] == "nfkc_casefold_5_shingle_candidate_discovery_only"
    assert raw_evidence["receipt_sha256"] == task["raw_evidence_sha256"]
    raw_core = {key: value for key, value in raw_evidence.items() if key != "receipt_sha256"}
    assert raw_evidence["receipt_sha256"] == audit._sha_bytes(audit._canonical(raw_core))


def test_multiple_exact_occurrences_require_adjudication():
    local = _local("Reset")
    donor = _donor("Reset procedure Reset")
    row, task, comparison, raw_evidence = audit._audit_row(
        local,
        _m26("no_content_donor"),
        [donor],
        _provenance(local),
        "live",
    )
    assert row["fidelity_outcome"] == "unresolved_requires_adjudication"
    assert task is not None
    assert task["reason"] == "ambiguous_surface_safe_occurrence"
    assert task["donor_evidence"][0]["id"] == "donor-1"
    assert task["comparison_receipt_sha256"] == comparison["receipt_sha256"]
    assert len(task["occurrences"]) == 2
    assert raw_evidence["donors"][0]["id"] == "donor-1"
    components = [item["donor_raw_components"][0] for item in task["occurrences"]]
    assert components[0]["raw_start_char"] != components[1]["raw_start_char"]
    for occurrence, component in zip(task["occurrences"], components, strict=True):
        raw_span = donor["content"][
            component["raw_start_char"] : component["raw_end_char_exclusive"]
        ]
        assert component["raw_span_sha256"] == audit._sha_bytes(raw_span.encode("utf-8"))
        assert occurrence["donor_span_raw_sha256"] == audit._sha_bytes(raw_span.encode("utf-8"))


def test_ambiguous_occurrence_evidence_never_caps_cited_donors():
    local = _local("Reset")
    donors = [_donor("Reset", donor_id=f"donor-{index:02d}") for index in range(13)]
    row, task, comparison, raw_evidence = audit._audit_row(
        local,
        _m26("no_content_donor"),
        donors,
        _provenance(local),
        "live",
    )
    cited = {
        donor_id
        for occurrence in task["occurrences"]
        for donor_id in occurrence["donor_chunk_ids"]
    }
    materialized = {item["id"] for item in raw_evidence["donors"]}
    assert len(cited) == 13
    assert cited <= materialized
    assert task["evidence_complete"] is True
    assert task["donor_evidence_capped"] is False
    assert audit._receipts_crosslinked([task], [comparison], [raw_evidence])


def test_raw_equal_structure_delta_closes_but_does_not_claim_semantics():
    local = _local()
    donor = _donor(local["content"], page_number=5)
    row, task, comparison, raw_evidence = audit._audit_row(
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
    row, task, comparison, raw_evidence = audit._audit_row(
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
        "evidence_complete": True,
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


def test_adjudication_can_be_partial_but_never_coerces_non_string_receipts():
    payload = _adjudication()
    second = {**_task_payload(), "local_row_id": "local-2"}
    decisions = audit.validate_adjudication(
        payload,
        expected_task_manifest_sha256="e" * 64,
        tasks=[_task_payload(), second],
    )
    assert decisions == {"local-1": "benign"}
    assert "local-2" not in decisions
    payload["rows"][0]["rationale"] = 123
    with pytest.raises(ValueError, match="invalid adjudication verdict"):
        audit.validate_adjudication(
            payload,
            expected_task_manifest_sha256="e" * 64,
            tasks=[_task_payload(), second],
        )


def test_benign_adjudication_rejects_incomplete_evidence():
    payload = _adjudication()
    task = {**_task_payload(), "evidence_complete": False}
    with pytest.raises(ValueError, match="complete evidence"):
        audit.validate_adjudication(
            payload,
            expected_task_manifest_sha256="e" * 64,
            tasks=[task],
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
    assert result["context_planning_proxies"]["runtime_model_id"] == "claude-haiku-4-5-20251001"
    assert result["context_planning_proxies"]["pricing_family"] == "Claude Haiku 4.5"
    minimum = result["context_planning_proxies"]["minimum_cacheable_char4_proxy"]
    assert minimum["cacheable_documents"] == 1
    assert minimum["cacheable_logical_calls"] == 2
    assert result["embedding_precontext_plan"]["exact_batch_manifest_available_after_context_generation_only"]
    assert result["embedding_precontext_plan"]["input_chars_floor_from_empty_context"] == 300
