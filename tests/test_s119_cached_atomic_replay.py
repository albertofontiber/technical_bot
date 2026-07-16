from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.s119_cached_atomic_replay import (
    ROOT,
    _coverage_pattern_rows,
    build_replay,
    build_source_projection,
    execute,
    file_sha256,
    load_json,
    load_yaml,
    validate_contract,
    validate_source_projection,
)


CONTRACT_PATH = ROOT / "evals/s119_cached_atomic_replay_contract_v1.yaml"


def _inputs() -> dict:
    contract = load_yaml(CONTRACT_PATH)
    frozen = contract["frozen_inputs"]
    return {
        "contract": contract,
        "bridge": load_json(ROOT / frozen["s118_bridge"]["path"]),
        "gate": load_yaml(ROOT / frozen["s118_gate"]["path"]),
        "contexts": load_json(ROOT / frozen["s113_contexts"]["path"]),
        "answers": load_json(ROOT / frozen["s113_answers"]["path"]),
        "projection": load_json(ROOT / frozen["source_projection"]["path"]),
        "claim_evidence_adjudication": load_yaml(
            ROOT / frozen["claim_evidence_adjudication"]["path"]
        ),
        "cached_answer_adjudication": load_yaml(
            ROOT / frozen["cached_answer_adjudication"]["path"]
        ),
        "input_receipts": {"test": "frozen"},
    }


def _build(data: dict | None = None) -> dict:
    return build_replay(**(data or _inputs()))


def test_real_cached_replay_reconciles_22_claims_without_calls() -> None:
    output = _build()
    summary = output["summary"]
    assert summary["cohort_claims"] == 22
    assert summary["generator_support_present"] == 22
    assert summary["cached_answers_available"] == 11
    assert summary["cached_answers_missing"] == 11
    assert summary["cohort_stage_histogram"] == {
        "OK": 7,
        "synthesis-miss": 4,
        "synthesis-not-measured": 11,
    }
    assert output["cost"] == {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }


def test_real_replay_keeps_official_metric_blocked() -> None:
    summary = _build()["summary"]
    assert summary["official_atomic_content_denominator"] is None
    assert summary["official_atomic_target_ok_for_95_percent"] is None
    assert summary["official_ok_after_replay"] is None
    assert summary["cached_claims_observed_ok"] == 7
    assert summary["facts_moved_to_ok_by_runtime_change"] == 0
    assert summary["causal_bot_improvement_claimed"] is False


def test_known_relational_misses_are_not_anchor_false_positives() -> None:
    rows = {row["claim_id"]: row for row in _build()["claim_results"]}
    assert rows["m0.hp005.output_selection.1"]["stage_bucket"] == "synthesis-miss"
    assert rows["m0.hp009.closed_loop_return.1"]["stage_bucket"] == "synthesis-miss"
    assert rows["m0.hp009.closed_loop_return.2"]["stage_bucket"] == "synthesis-miss"
    assert rows["m0.hp017.rule1.2"]["stage_bucket"] == "synthesis-miss"
    assert rows["m0.hp017.rule1.1"]["stage_bucket"] == "OK"


def test_missing_answer_is_unmeasured_never_synthesis_miss() -> None:
    data = _inputs()
    data["answers"] = copy.deepcopy(data["answers"])
    row = next(row for row in data["answers"]["rows"] if row["qid"] == "cat001")
    row.update({"executed": False, "answer": None, "answer_sha256": None})
    data["cached_answer_adjudication"] = copy.deepcopy(
        data["cached_answer_adjudication"]
    )
    data["cached_answer_adjudication"]["rows"] = [
        row for row in data["cached_answer_adjudication"]["rows"]
        if row["qid"] != "cat001"
    ]
    output = _build(data)
    cat001 = [row for row in output["claim_results"] if row["qid"] == "cat001"]
    assert {row["stage_bucket"] for row in cat001} == {"synthesis-not-measured"}


def test_adjudicated_evidence_content_drift_fails_closed() -> None:
    data = _inputs()
    data["contexts"] = copy.deepcopy(data["contexts"])
    row = next(row for row in data["contexts"]["rows"] if row["qid"] == "cat010")
    candidate = next(
        candidate for candidate in row["context"]
        if candidate["id"] == "048f407c-eda7-416e-a63e-6d07a583dd78"
    )
    candidate["content"] += " drift"
    with pytest.raises(ValueError, match="accepted evidence binding is invalid"):
        _build(data)


def test_contract_rejects_runtime_outcome_fields() -> None:
    contract = load_yaml(CONTRACT_PATH)
    contract = copy.deepcopy(contract)
    contract["claims"][0]["stage_bucket"] = "OK"
    with pytest.raises(ValueError, match="schema|runtime outcome"):
        validate_contract(contract)


def test_contract_rejects_unsafe_or_unbounded_regex_features() -> None:
    contract = load_yaml(CONTRACT_PATH)
    contract = copy.deepcopy(contract)
    contract["claims"][0]["synthesis"]["coverage_patterns"] = ["(?s).*"]
    with pytest.raises(ValueError, match="unsafe semantic pattern"):
        validate_contract(contract)
    contract = load_yaml(CONTRACT_PATH)
    contract["claims"][0]["synthesis"]["coverage_patterns"] = ["32.{0,}"]
    with pytest.raises(ValueError, match="unsafe semantic pattern"):
        validate_contract(contract)


def test_contract_rejects_authority_or_policy_drift() -> None:
    contract = load_yaml(CONTRACT_PATH)
    authority_drift = copy.deepcopy(contract)
    authority_drift["authority"] = "official_atomic_credit"
    with pytest.raises(ValueError, match="identity"):
        validate_contract(authority_drift)
    policy_drift = copy.deepcopy(contract)
    policy_drift["policy"]["official_atomic_denominator"] = 132
    with pytest.raises(ValueError, match="identity"):
        validate_contract(policy_drift)


def test_final_contract_is_accepted_by_projection_freeze_validation() -> None:
    validate_contract(load_yaml(CONTRACT_PATH), allow_pending_projection=True)


def test_bridge_population_must_be_bijective() -> None:
    data = _inputs()
    data["bridge"] = copy.deepcopy(data["bridge"])
    row = next(
        row for row in data["bridge"]["claims"]
        if row["stage_bucket"] == "pending-replay"
    )
    row["claim_id"] = "drifted.claim"
    data["bridge"].pop("payload_sha256")
    from scripts.s119_cached_atomic_replay import object_sha256
    data["bridge"]["payload_sha256"] = object_sha256(data["bridge"])
    with pytest.raises(ValueError, match="not bijective"):
        _build(data)


def test_source_projection_excludes_outcome_aware_s106_fields() -> None:
    projection = _inputs()["projection"]
    validate_source_projection(projection, _inputs()["contract"])
    for row in projection["rows"]:
        assert "observed_answer" not in row["source_row"]
        assert "adjudication" not in row["source_row"]
        assert "proposal" not in row["source_row"]


def test_answer_context_must_match_per_qid_not_only_global_freeze() -> None:
    data = _inputs()
    data["answers"] = copy.deepcopy(data["answers"])
    row = next(row for row in data["answers"]["rows"] if row["qid"] == "hp005")
    row["serving_context_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="per-qid receipt mismatch"):
        _build(data)


def test_manual_answer_adjudication_is_answer_sha_and_verdict_bound() -> None:
    data = _inputs()
    data["cached_answer_adjudication"] = copy.deepcopy(
        data["cached_answer_adjudication"]
    )
    row = next(
        row for row in data["cached_answer_adjudication"]["rows"]
        if row["claim_id"] == "m0.hp005.output_selection.1"
    )
    row["verdict"] = "OK"
    with pytest.raises(ValueError, match="semantic verdict drift"):
        _build(data)


def test_claim_evidence_adjudication_binds_claim_text_and_pages() -> None:
    data = _inputs()
    data["claim_evidence_adjudication"] = copy.deepcopy(
        data["claim_evidence_adjudication"]
    )
    row = data["claim_evidence_adjudication"]["rows"][0]
    row["claim_source_pages"] = ["999"]
    with pytest.raises(ValueError, match="lineage drift"):
        _build(data)


def test_claim_evidence_relation_and_page_basis_are_typed() -> None:
    data = _inputs()
    data["claim_evidence_adjudication"] = copy.deepcopy(
        data["claim_evidence_adjudication"]
    )
    row = data["claim_evidence_adjudication"]["rows"][0]
    row["page_basis"] = "free text"
    with pytest.raises(ValueError, match="lineage drift"):
        _build(data)
    data = _inputs()
    data["claim_evidence_adjudication"] = copy.deepcopy(
        data["claim_evidence_adjudication"]
    )
    group = data["claim_evidence_adjudication"]["rows"][0]["evidence_groups"][0]
    group["relation"] = "free text"
    with pytest.raises(ValueError, match="accepted evidence binding is invalid"):
        _build(data)


def test_source_projection_builder_is_exact_and_payload_bound() -> None:
    contract = load_yaml(CONTRACT_PATH)
    source = {
        "instrument": "s106_p0_selection_adjudication_v1",
        "rows": [
            {"key": key, "source_truth": f"truth {index}"}
            for index, key in enumerate(contract["external_source"]["required_row_keys"])
        ],
    }
    projection = build_source_projection(source, contract)
    assert projection["row_keys"] == contract["external_source"]["required_row_keys"]
    validate_source_projection(projection, contract)
    projection["rows"][0]["source_row"]["source_truth"] = "drift"
    with pytest.raises(ValueError, match="payload hash"):
        validate_source_projection(projection, contract)


def test_coverage_matching_never_crosses_blank_section_boundary() -> None:
    answer = "Lazo analógico sin RFL.\n\n## Otro circuito\nLazo cerrado."
    rows = _coverage_pattern_rows(
        ["lazo analogico.{0,180}lazo cerrado"], answer,
    )
    assert rows == [{
        "pattern": "lazo analogico.{0,180}lazo cerrado",
        "matched": False,
        "matched_line_start": None,
        "matched_line_count": None,
    }]


def test_coverage_matching_allows_one_adjacent_semantic_pair() -> None:
    answer = "Equipos sin aisladores internos:\n- Máximo 20 equipos entre aisladores."
    rows = _coverage_pattern_rows(
        ["equipos sin aisladores internos.{0,120}20 equipos entre aisladores"], answer,
    )
    assert rows[0]["matched"] is True
    assert rows[0]["matched_line_count"] == 2


def test_execute_is_byte_deterministic_and_canonical() -> None:
    output_path = ROOT / "evals/s119_cached_atomic_replay_v1.json"
    execute(root=ROOT, contract_path=CONTRACT_PATH, output_path=output_path)
    first = output_path.read_bytes()
    first_sha = file_sha256(output_path)
    execute(root=ROOT, contract_path=CONTRACT_PATH, output_path=output_path)
    assert output_path.read_bytes() == first
    assert file_sha256(output_path) == first_sha


def test_execute_rejects_noncanonical_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="canonical allowlisted artifact"):
        execute(
            root=ROOT,
            contract_path=CONTRACT_PATH,
            output_path=tmp_path / "replay.json",
        )


def test_strict_json_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_json(path)
