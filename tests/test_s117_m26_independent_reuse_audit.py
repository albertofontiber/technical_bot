from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path

import pytest
import yaml

from scripts import s117_m2_legacy_reuse_analysis as m2
from scripts import s117_m26_independent_reuse_audit as audit
from src.reingest import retrieval_policy


def _local() -> dict:
    return {
        "id": "local-1",
        "extraction_sha256": "sha-a",
        "content": "Alarm reset procedure",
        "section_title": "Reset",
        "section_path": ["Service", "Reset"],
        "page_number": 7,
        "is_flow_diagram": False,
        "has_diagram": True,
        "confidence_f32": "0x1.e00000p-1",
        "context_input_sha256": "context-input",
    }


def _donor(**overrides) -> dict:
    donor = {
        "id": "donor-1",
        "document_id": "document-1",
        "extraction_sha256": "sha-a",
        "content": "Alarm reset procedure",
        "section_title": "Reset",
        "section_path": ["Service", "Reset"],
        "page_number": 7,
        "is_flow_diagram": False,
        "has_diagram": True,
        "confidence_f32": "0x1.e00000p-1",
        "duplicate_of": None,
    }
    donor.update(overrides)
    return donor


def _context_contract() -> dict:
    return {
        "contextualizer_sha256": "contextualizer-sha",
        "context_prompt_sha256": "prompt-sha",
        "context_model": "model-a",
        "context_limits": {"document": 20, "chunk": 10, "output": 2},
    }


def _context_donor(**overrides) -> dict:
    context = "Reset instructions for product family."
    donor = _donor(
        context=context,
        context_sha256=audit._sha_bytes(context.encode("utf-8")),
        context_input_sha256="context-input",
        **_context_contract(),
    )
    donor.update(overrides)
    return donor


def _embedding_contract() -> dict:
    return {
        "embedding_provider": "provider-a",
        "embedding_model": "embed-a",
        "embedding_input_type": "document",
        "embedding_dimensions": 2,
        "embedding_max_chars": 16000,
    }


def _embedding_donor(local: dict | None = None, **overrides) -> dict:
    local = local or _local()
    context = "Reset instructions for product family."
    payload = [0.25, -0.5]
    donor = _donor(
        context=context,
        embedding_present=True,
        embedding_input_sha256=m2._embedding_receipt(context, local["content"])[
            "embedding_input_sha256"
        ],
        embedding_sha256=audit._vector_sha256(payload),
        embedding_payload_f32=payload,
        **_embedding_contract(),
    )
    donor.update(overrides)
    return donor


def test_structural_discovery_has_closed_precedence():
    local = _local()
    assert audit._discover_structural(local, [])[0] == "no_content_donor"
    assert (
        audit._discover_structural(local, [_donor(page_number=8)])[0]
        == "no_structural_donor"
    )
    assert (
        audit._discover_structural(local, [_donor(), _donor(id="donor-2")])[0]
        == "multiple_structural_donors"
    )
    marked = _donor(duplicate_of="canonical-donor")
    assert audit._discover_structural(local, [marked]) == (
        "unique_donor_marked_duplicate",
        marked,
    )
    donor = _donor()
    assert audit._discover_structural(local, [donor]) == (
        "independent_unique_structural_donor",
        donor,
    )


def test_structural_discovery_is_invariant_to_forbidden_metadata():
    local = _local()
    donor = _donor()
    expected = audit._discover_structural(local, [donor])
    mutated_local = copy.deepcopy(local)
    mutated_donor = copy.deepcopy(donor)
    for field in (
        "manufacturer",
        "model",
        "product_type",
        "source_path",
        "document_id",
        "context",
        "embedding_model",
    ):
        mutated_local[field] = f"local-{field}"
        mutated_donor[field] = f"donor-{field}"
    assert audit._discover_structural(mutated_local, [mutated_donor]) == (
        expected[0],
        mutated_donor,
    )


@pytest.mark.parametrize(
    ("primary", "binding", "expected"),
    [
        (
            {"terminal": "primary_unique_active_pdf_sha", "document_id": "d1"},
            {"terminal": "unused", "document_id": None},
            ("live_exact_active", "d1"),
        ),
        (
            {"terminal": "primary_non_active_pdf_sha", "document_id": "d2"},
            {"terminal": "unused", "document_id": None},
            ("live_exact_nonactive", "d2"),
        ),
        (
            {"terminal": "primary_absent_pdf_sha", "document_id": None},
            {
                "terminal": "fallback_unique_active_backfill_binding",
                "document_id": "d3",
            },
            ("projected_backfill_candidate", "d3"),
        ),
        (
            {"terminal": "primary_absent_pdf_sha", "document_id": None},
            {"terminal": "fallback_non_active_document", "document_id": "d4"},
            ("projected_backfill_nonactive", None),
        ),
        (
            {"terminal": "primary_absent_pdf_sha", "document_id": None},
            {"terminal": "fallback_unresolved", "document_id": None},
            ("binding_unresolved", None),
        ),
    ],
)
def test_load_binding_axis(primary, binding, expected):
    assert audit._binding_status_and_expected_id(primary, binding) == expected


def test_primary_binding_is_recomputed_from_source_documents():
    rows = [
        {
            "extraction_sha256": "sha-a",
            "terminal": "primary_unique_active_pdf_sha",
            "document_id": "d1",
            "status": "active",
            "matching_document_count": 1,
        },
        {
            "extraction_sha256": "sha-b",
            "terminal": "primary_non_active_pdf_sha",
            "document_id": "d2",
            "status": "inactive",
            "matching_document_count": 1,
        },
        {
            "extraction_sha256": "sha-c",
            "terminal": "primary_absent_pdf_sha",
            "document_id": None,
            "status": None,
            "matching_document_count": 0,
        },
    ]
    documents = [
        {"id": "d1", "source_pdf_sha256": "sha-a", "status": "active"},
        {"id": "d2", "source_pdf_sha256": "sha-b", "status": "inactive"},
    ]
    manifest = audit._validate_primary_binding_against_source(rows, documents)
    assert len(manifest) == 64
    with pytest.raises(RuntimeError, match="contradicts source documents"):
        audit._validate_primary_binding_against_source(
            [{**rows[0], "document_id": "wrong"}], documents
        )


@pytest.mark.parametrize(
    ("status", "donor", "load", "expected_id", "expected"),
    [
        ("no_content_donor", None, "live_exact_active", "d1", "structural_donor_not_unique"),
        ("independent_unique_structural_donor", _donor(document_id="d1"), "live_exact_active", "d1", "live_exact_document_match"),
        ("independent_unique_structural_donor", _donor(document_id="d1"), "projected_backfill_candidate", "d1", "projected_observed_document_match"),
        ("independent_unique_structural_donor", _donor(document_id="d1"), "binding_unresolved", None, "expected_document_binding_unavailable"),
        ("independent_unique_structural_donor", _donor(document_id="other"), "live_exact_active", "d1", "donor_document_binding_mismatch"),
    ],
)
def test_binding_evidence_is_orthogonal(status, donor, load, expected_id, expected):
    assert audit._donor_binding_evidence(status, donor, load, expected_id) == expected


def test_context_evidence_precedence_and_cryptographic_failure():
    local = _local()
    contract = _context_contract()
    assert audit._context_evidence(local, None, "no_content_donor", contract) == "structural_identity_not_unique"
    assert audit._context_evidence(local, _donor(context=""), "independent_unique_structural_donor", contract) == "context_missing_or_empty"
    assert audit._context_evidence(local, _donor(context="present"), "independent_unique_structural_donor", contract) == "context_generation_receipt_unavailable"
    missing_output = _context_donor(context_sha256=None)
    assert audit._context_evidence(local, missing_output, "independent_unique_structural_donor", contract) == "context_output_receipt_unavailable"
    with pytest.raises(RuntimeError, match="context output receipt"):
        audit._context_evidence(local, _context_donor(context_sha256="bad"), "independent_unique_structural_donor", contract)
    assert audit._context_evidence(local, _context_donor(context_model="other"), "independent_unique_structural_donor", contract) == "context_contract_mismatch"
    assert audit._context_evidence(local, _context_donor(context_input_sha256="other"), "independent_unique_structural_donor", contract) == "context_target_donor_input_mismatch"
    assert audit._context_evidence(local, _context_donor(), "independent_unique_structural_donor", contract) == "context_evidence_compatible"


def test_embedding_evidence_precedence_and_cryptographic_failure():
    local = _local()
    contract = _embedding_contract()
    unique = "independent_unique_structural_donor"
    assert audit._embedding_evidence(local, None, "no_content_donor", contract) == "structural_identity_not_unique"
    assert audit._embedding_evidence(local, _donor(), unique, contract) == "embedding_missing"
    assert audit._embedding_evidence(local, _donor(embedding_present=True), unique, contract) == "embedding_model_receipt_unavailable"
    missing_vector = _embedding_donor(embedding_sha256=None)
    assert audit._embedding_evidence(local, missing_vector, unique, contract) == "embedding_vector_receipt_unavailable"
    with pytest.raises(RuntimeError, match="embedding vector receipt"):
        audit._embedding_evidence(local, _embedding_donor(embedding_sha256="bad"), unique, contract)
    assert audit._embedding_evidence(local, _embedding_donor(embedding_model="other"), unique, contract) == "embedding_query_contract_mismatch"
    with pytest.raises(RuntimeError, match="dimensions contradict"):
        audit._embedding_evidence(local, _embedding_donor(embedding_dimensions=3), unique, {**contract, "embedding_dimensions": 3})
    assert audit._embedding_evidence(local, _embedding_donor(embedding_input_sha256="other"), unique, contract) == "embedding_target_donor_input_mismatch"
    assert audit._embedding_evidence(local, _embedding_donor(), unique, contract) == "embedding_evidence_compatible"


def test_embedding_authorization_depends_on_context_authorization():
    base = {
        "load_status": "live_exact_active",
        "policy_class": "eligible",
        "structural_status": "independent_unique_structural_donor",
        "binding_evidence": "live_exact_document_match",
        "context_status": "context_evidence_compatible",
        "embedding_status": "embedding_evidence_compatible",
    }
    assert audit._authorization(**base) == (True, True)
    assert audit._authorization(**{**base, "context_status": "context_contract_mismatch"}) == (False, False)
    for field, value in (
        ("load_status", "projected_backfill_candidate"),
        ("policy_class", "unsupported_language"),
        ("structural_status", "multiple_structural_donors"),
        ("binding_evidence", "donor_document_binding_mismatch"),
    ):
        assert audit._authorization(**{**base, field: value}) == (False, False)


def test_taxonomy_gate_rejects_unknown_or_missing_rows():
    allowed = ("a", "b")
    assert audit._taxonomy_closed(Counter({"a": 2, "b": 1}), allowed, 3)
    assert not audit._taxonomy_closed(Counter({"a": 2, "unknown": 1}), allowed, 3)
    assert not audit._taxonomy_closed(Counter({"a": 2}), allowed, 3)


def test_policy_contract_is_recomputed_not_trusted():
    payload = {
        "design_sha256": "design-sha",
        "implementation_sha256": "implementation-sha",
        "policy": retrieval_policy.contract_payload(),
    }
    expected = audit._sha_bytes(audit._canonical(payload))
    prereg = {
        "policy_contract": {**payload, "sha256": expected},
        "frozen_inputs": {
            "design_v4": {"sha256": "design-sha"},
            "policy": {"sha256": "implementation-sha"},
        },
    }
    assert audit._policy_contract_sha256(prereg) == expected
    prereg["policy_contract"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="policy contract drift"):
        audit._policy_contract_sha256(prereg)


def test_policy_contract_must_bind_frozen_inputs():
    prereg = {
        "policy_contract": {
            "design_sha256": "design-sha",
            "implementation_sha256": "implementation-sha",
            "sha256": "unused",
        },
        "frozen_inputs": {
            "design_v4": {"sha256": "different"},
            "policy": {"sha256": "implementation-sha"},
        },
    }
    with pytest.raises(RuntimeError, match="not bound to frozen inputs"):
        audit._policy_contract_sha256(prereg)


def test_enrichment_contracts_are_recomputed_from_runtime():
    prereg = yaml.safe_load(audit.DEFAULT_PREREG.read_text(encoding="utf-8"))
    audit._validate_enrichment_contracts(prereg)
    prereg["expected_embedding_contract"]["embedding_dimensions"] += 1
    with pytest.raises(RuntimeError, match="embedding contract drift"):
        audit._validate_enrichment_contracts(prereg)


def test_runner_has_no_selector_or_external_execution_escape_hatches():
    source = Path(audit.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "_metadata_matches(",
        "derived_snapshot",
        "s117_m26_freeze_legacy_cohorts",
        "psycopg2",
        "requests.",
        "http://",
        "https://",
    ):
        assert forbidden not in source
    assert source.index("audit_rows.append(row)") < source.index(
        "# Membership is consumed only after independent discovery/classification."
    )
    assert '"status": "GO"' not in source
