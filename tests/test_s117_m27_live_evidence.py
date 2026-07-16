from __future__ import annotations

import copy
import base64
import json

import pytest
import yaml

from scripts import s117_m27_live_evidence as evidence
from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk_provenance as provenance


def _row(
    chunk_index: int,
    start: int,
    end: int,
    *,
    row_id: str | None = None,
    content: str = "x",
) -> dict:
    return {
        "id": row_id or f"row-{chunk_index}",
        "chunk_index": chunk_index,
        "source_block_start": start,
        "source_block_end": end,
        "content": content,
    }


def _block(index: int) -> dict:
    core = {
        "source_block_index": index,
        "kind": "paragraph",
        "page": 1,
        "text": f"block {index}",
        "text_sha256": evidence._sha_bytes(f"block {index}".encode("utf-8")),
        "lineage": [],
    }
    return {
        **core,
        "receipt_sha256": evidence._sha_bytes(evidence._canonical(core)),
    }


def test_surface_normalizes_only_whitespace():
    assert evidence._surface("A\n\t  B\u00a0C") == "A B C"
    assert evidence._surface("10 µA") != evidence._surface("10 μA")
    assert evidence._surface("ZX50") != evidence._surface("zx50")


def test_first_surface_mismatch_is_exact_and_explains_length_delta():
    mismatch = evidence._first_surface_mismatch("a b c", "a b X")
    assert mismatch["token_index"] == 2
    assert mismatch["raw_token"] == "c"
    assert mismatch["v3_token"] == "X"
    length_delta = evidence._first_surface_mismatch("a b", "a b c")
    assert length_delta["token_index"] == 2
    assert length_delta["raw_token"] is None
    assert length_delta["v3_token"] == "c"
    assert evidence._first_surface_mismatch("a\n b", "a b") is None


def test_shared_oversized_block_materializes_all_overlapping_siblings():
    rows = [
        _row(0, 3, 3),
        _row(1, 3, 3),
        _row(2, 3, 4),
        _row(3, 4, 4),
        _row(4, 5, 5),
    ]
    overlap = evidence._overlapping_rows(rows, rows[1])
    assert [row["chunk_index"] for row in overlap] == [0, 1, 2]


def test_overlap_does_not_claim_adjacent_nonoverlapping_chunk():
    target = _row(1, 10, 12)
    rows = [
        _row(0, 8, 9),
        target,
        _row(2, 12, 14),
        _row(3, 13, 15),
    ]
    assert [
        row["chunk_index"]
        for row in evidence._overlapping_rows(rows, target)
    ] == [1, 2]


def test_block_window_includes_one_boundary_on_each_side():
    blocks = [_block(index) for index in range(8)]
    overlap = [_row(0, 2, 3), _row(1, 3, 5)]
    window, boundary = evidence._block_window(blocks, overlap)
    assert [row["source_block_index"] for row in window] == [1, 2, 3, 4, 5, 6]
    assert boundary == {
        "overlap_start": 2,
        "overlap_end": 5,
        "previous_boundary": 1,
        "next_boundary": 6,
    }


def test_block_window_is_fail_safe_at_document_edges():
    blocks = [_block(index) for index in range(3)]
    window, boundary = evidence._block_window(blocks, [_row(0, 0, 2)])
    assert window == blocks
    assert boundary["previous_boundary"] is None
    assert boundary["next_boundary"] is None


def test_full_legacy_receipt_is_order_independent_and_uncapped():
    donors = [
        {"id": "b", "chunk_index": 1, "content": "B"},
        {"id": "a", "chunk_index": 0, "content": "A"},
    ]
    first = evidence._legacy_document_receipt("f" * 64, donors)
    second = evidence._legacy_document_receipt("f" * 64, list(reversed(donors)))
    assert first == second
    assert first["donor_count"] == 2
    assert [row["id"] for row in first["donor_rows"]] == ["a", "b"]


def test_seed_validation_rejects_broken_task_manifest():
    empty_manifest = evidence._manifest([], "local_row_id")
    seed = {
        "instrument": "s117_m27_upstream_sql_budget_v2",
        "contract_integrity": "GO",
        "local_readiness": "NO_GO",
        "task_manifest": {"rows": [], "sha256": evidence._manifest([], "x")},
        "comparison_receipts": [],
        "raw_evidence_receipts": [],
        "audit_rows": [],
        "manifests": {
            "audit_rows_sha256": empty_manifest,
            "comparison_receipts_sha256": empty_manifest,
            "raw_evidence_receipts_sha256": empty_manifest,
        },
    }
    evidence._validate_seed(seed)
    broken = copy.deepcopy(seed)
    broken["task_manifest"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="task manifest drift"):
        evidence._validate_seed(broken)


def test_policy_receipt_must_reproduce_m26_hash(monkeypatch):
    local = {
        "extraction_sha256": "f" * 64,
        "chunk_index": 3,
        "preterminal": None,
        "duplicate_of": None,
        "language": "es",
    }
    core = {
        "extraction_sha256": "f" * 64,
        "chunk_index": 3,
        "retrieval_policy_class": "eligible",
        "language": "es",
        "duplicate_of": None,
        "policy_contract_sha256": "a" * 64,
    }
    m26_row = {
        "retrieval_policy_class": "eligible",
        "policy_receipt_sha256": evidence._sha_bytes(evidence._canonical(core)),
        "receipt_sha256": "b" * 64,
    }
    wrapper = evidence._policy_receipt(local, m26_row, "a" * 64)
    assert wrapper[
        "m26_policy_receipt_sha256"
    ] == m26_row["policy_receipt_sha256"]
    assert wrapper["selected_rule_id"] == "eligible"
    assert evidence._receipt_valid(wrapper)
    assert evidence._policy_wrapper_valid(wrapper, "a" * 64)
    m26_row["policy_receipt_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="did not reproduce"):
        evidence._policy_receipt(local, m26_row, "a" * 64)


def test_sha_validator_is_strict_lowercase_hex():
    assert evidence._is_sha256("a" * 64)
    assert not evidence._is_sha256("A" * 64)
    assert not evidence._is_sha256("g" * 64)
    assert not evidence._is_sha256("a" * 63)


def test_receipt_validator_detects_tampering():
    core = {"schema": "example", "value": 1}
    receipt = {
        **core,
        "receipt_sha256": evidence._sha_bytes(evidence._canonical(core)),
    }
    assert evidence._receipt_valid(receipt)
    receipt["value"] = 2
    assert not evidence._receipt_valid(receipt)


def test_structural_projection_matches_independent_expected_rows():
    raw = json.dumps({
        "sha256": "f" * 64,
        "result": {
            "pages": [{
                "page": 1,
                "md": "# Heading\n\nFirst sentence. Second sentence.",
            }],
        },
    }, sort_keys=True).encode("utf-8")
    materialization_id = "00000000-0000-0000-0000-000000000001"
    chunker_sha256 = "a" * 64
    actual = provenance.materialize_raw_record(
        raw,
        materialization_id=materialization_id,
        chunker_sha256=chunker_sha256,
    )
    projected = [evidence._structural_row(row) for row in actual]
    expected = replay._expected_rows(
        raw,
        materialization_id=materialization_id,
        chunker_sha256=chunker_sha256,
    )
    assert projected == expected
    assert replay.validate_rows_against_raw(
        raw,
        projected,
        materialization_id=materialization_id,
        chunker_sha256=chunker_sha256,
    ) == []


def _make_receipt(core: dict) -> dict:
    return {
        **core,
        "receipt_sha256": evidence._sha_bytes(evidence._canonical(core)),
    }


def _crosslink_fixture() -> dict:
    local_id = "row-1"
    extraction = "f" * 64
    target = _make_receipt({
        "id": local_id,
        "extraction_sha256": extraction,
        "chunk_index": 0,
        "source_block_start": 0,
        "source_block_end": 0,
        "content": "block 0",
    })
    block = _block(0)
    raw_bytes = b"{}"
    raw_surface = evidence._surface(block["text"])
    v3_surface = evidence._surface(target["content"])
    document = _make_receipt({
        "schema": "doc",
        "extraction_sha256": extraction,
        "v3_rows": [target],
        "raw_blocks": [block],
        "raw_artifact_base64": base64.b64encode(raw_bytes).decode("ascii"),
        "raw_artifact_bytes": len(raw_bytes),
        "raw_artifact_sha256": evidence._sha_bytes(raw_bytes),
        "raw_block_manifest_sha256": evidence._manifest(
            [block], "source_block_index"
        ),
        "v3_row_manifest_sha256": evidence._manifest([target], "chunk_index"),
        "raw_surface_sha256": evidence._sha_bytes(raw_surface.encode("utf-8")),
        "v3_surface_sha256": evidence._sha_bytes(v3_surface.encode("utf-8")),
        "row_by_row_regeneration_equal": True,
        "independent_validation_failures": [],
        "document_stream_whitespace_equal": True,
        "first_surface_mismatch": None,
        "alignment_status": "exact_whitespace_equivalent",
    })
    original_raw = _make_receipt({
        "schema": "raw",
        "local_row_id": local_id,
        "donors": [],
        "local_protected_tokens": ["block", "0"],
    })
    comparison = _make_receipt({
        "schema": "comparison",
        "local_row_id": local_id,
    })
    policy_payload = evidence.retrieval_policy.contract_payload()
    policy_contract_sha256 = "a" * 64
    m26_policy_core = {
        "extraction_sha256": extraction,
        "chunk_index": 0,
        "retrieval_policy_class": "eligible",
        "language": "es",
        "duplicate_of": None,
        "policy_contract_sha256": policy_contract_sha256,
    }
    m26_policy_sha256 = evidence._sha_bytes(evidence._canonical(m26_policy_core))
    m26_row = _make_receipt({
        "local_row_id": local_id,
        "retrieval_policy_class": "eligible",
        "policy_receipt_sha256": m26_policy_sha256,
    })
    policy = _make_receipt({
        "schema": "policy",
        "version": 1,
        "policy_contract_payload": policy_payload,
        "policy_contract_payload_sha256": evidence._sha_bytes(
            evidence._canonical(policy_payload)
        ),
        "policy_contract_sha256": policy_contract_sha256,
        "extraction_sha256": extraction,
        "chunk_index": 0,
        "language": "es",
        "preterminal": None,
        "duplicate_of": None,
        "evaluated_rules": evidence._evaluated_policy_rules(None, None),
        "selected_rule_id": "eligible",
        "retrieval_policy_class": "eligible",
        "m26_policy_receipt_sha256": m26_policy_sha256,
        "m26_row_receipt_sha256": m26_row["receipt_sha256"],
    })
    original_task_core = {
        "local_row_id": local_id,
        "reason": "ambiguous_surface_safe_occurrence",
        "candidate_method": "surface_safe_whitespace_only_token_sequence",
    }
    original_task = {
        **original_task_core,
        "task_receipt_sha256": evidence._sha_bytes(
            evidence._canonical(original_task_core)
        ),
    }
    overlap = [target]
    window, boundary = evidence._block_window([block], overlap)
    task = _make_receipt({
        "schema": "task",
        "local_row_id": local_id,
        "extraction_sha256": extraction,
        "original_task_receipt_sha256": original_task["task_receipt_sha256"],
        "raw_document_receipt_sha256": document["receipt_sha256"],
        "target_row": target,
        "legacy_evidence_completion_verified": True,
        "evidence_complete": True,
        "overlapping_v3_rows": overlap,
        "overlap_manifest_sha256": evidence._manifest(overlap, "chunk_index"),
        "raw_block_window": window,
        "boundary": boundary,
        "raw_block_window_manifest_sha256": evidence._manifest(
            window, "source_block_index"
        ),
        "comparison_receipt_sha256": comparison["receipt_sha256"],
        "original_raw_evidence_sha256": original_raw["receipt_sha256"],
        "frozen_policy_evidence": policy,
        "legacy_evidence_mode": "m27_original_complete",
        "legacy_evidence_receipt_sha256": original_raw["receipt_sha256"],
        "mechanical_raw_alignment": "exact_whitespace_equivalent",
    })
    fiche = {
        "local_row_id": local_id,
        "reason": original_task["reason"],
        "candidate_method": original_task["candidate_method"],
        "local_content": target["content"],
        "local_protected_tokens": original_raw["local_protected_tokens"],
        "raw_block_window": window,
        "overlapping_v3_chunk_indexes": [0],
        "original_donor_evidence": [],
        "task_evidence_receipt_sha256": task["receipt_sha256"],
        "comparison_receipt_sha256": comparison["receipt_sha256"],
        "mechanical_raw_alignment": "exact_whitespace_equivalent",
        "policy_class_under_frozen_contract": "eligible",
        "review_status": "not_authorized",
        "legacy_full_document_receipt_sha256": None,
    }
    return {
        "task_evidence": [task],
        "review_fiches": [fiche],
        "document_receipts": [document],
        "legacy_receipts": [],
        "original_raw": {local_id: original_raw},
        "comparisons": {local_id: comparison},
        "original_tasks": {local_id: original_task},
        "m26_rows": {local_id: m26_row},
        "policy_contract_sha256": policy_contract_sha256,
    }


def test_crosslink_validator_rejects_deletion_and_duplicate():
    fixture = _crosslink_fixture()
    assert evidence._evidence_crosslinked(**fixture)
    deleted = copy.deepcopy(fixture)
    deleted["review_fiches"] = []
    assert not evidence._evidence_crosslinked(**deleted)
    duplicated = copy.deepcopy(fixture)
    duplicated["task_evidence"].append(copy.deepcopy(duplicated["task_evidence"][0]))
    assert not evidence._evidence_crosslinked(**duplicated)


def test_crosslink_validator_rejects_valid_hash_pointing_to_wrong_document():
    fixture = _crosslink_fixture()
    wrong_core = {
        key: value
        for key, value in fixture["document_receipts"][0].items()
        if key != "receipt_sha256"
    }
    wrong_core["extraction_sha256"] = "e" * 64
    wrong_document = _make_receipt(wrong_core)
    fixture["document_receipts"].append(wrong_document)
    task_core = {
        key: value
        for key, value in fixture["task_evidence"][0].items()
        if key != "receipt_sha256"
    }
    task_core["raw_document_receipt_sha256"] = wrong_document["receipt_sha256"]
    fixture["task_evidence"][0] = _make_receipt(task_core)
    fixture["review_fiches"][0]["task_evidence_receipt_sha256"] = fixture[
        "task_evidence"
    ][0]["receipt_sha256"]
    assert not evidence._evidence_crosslinked(**fixture)


def test_crosslink_validator_rejects_fiche_content_drift():
    fixture = _crosslink_fixture()
    fixture["review_fiches"][0]["local_content"] = "different"
    assert not evidence._evidence_crosslinked(**fixture)


def test_crosslink_validator_rejects_task_document_alignment_drift():
    fixture = _crosslink_fixture()
    task_core = {
        key: value
        for key, value in fixture["task_evidence"][0].items()
        if key != "receipt_sha256"
    }
    task_core["mechanical_raw_alignment"] = "unresolved"
    fixture["task_evidence"][0] = _make_receipt(task_core)
    fixture["review_fiches"][0]["mechanical_raw_alignment"] = "unresolved"
    fixture["review_fiches"][0]["task_evidence_receipt_sha256"] = fixture[
        "task_evidence"
    ][0]["receipt_sha256"]
    assert not evidence._evidence_crosslinked(**fixture)


def test_policy_wrapper_rejects_posthoc_contract_hash():
    fixture = _crosslink_fixture()
    wrapper = copy.deepcopy(
        fixture["task_evidence"][0]["frozen_policy_evidence"]
    )
    wrapper_core = {
        key: value for key, value in wrapper.items() if key != "receipt_sha256"
    }
    wrapper_core["policy_contract_sha256"] = "b" * 64
    tampered = _make_receipt(wrapper_core)
    assert not evidence._policy_wrapper_valid(tampered, "a" * 64)


def test_selected_path_binding_requires_sha256(tmp_path, monkeypatch):
    frozen = tmp_path / "input.txt"
    frozen.write_text("x", encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text(yaml.safe_dump({
        "instrument": "s117_m27_live_evidence_prereg_v1",
        "status": "frozen_before_seeded_evidence",
        "frozen_inputs": {"bad": {"path": "input.txt"}},
        "selected_paths": {"source": "input.txt"},
        "selected_path_bindings": {"source": "bad"},
    }), encoding="utf-8")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(evidence, "DEFAULT_PREREG", prereg_path)
    with pytest.raises(RuntimeError, match="not hash-bound"):
        evidence._load_prereg(prereg_path)
