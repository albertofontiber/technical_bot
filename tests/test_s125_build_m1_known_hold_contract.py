from __future__ import annotations

import copy

import pytest

from scripts.s125_build_m1_known_hold_contract import (
    PREREG_PATH,
    SPEC_PATH,
    SUPPORT_PATH,
    build_contract,
    build_from_files,
    load_json,
    load_yaml,
)


def _inputs():
    prereg = load_yaml(PREREG_PATH)
    spec = load_yaml(SPEC_PATH)
    support = load_yaml(SUPPORT_PATH)
    frozen = prereg["frozen_inputs"]
    root = PREREG_PATH.parent.parent
    return (
        prereg,
        spec,
        support,
        load_json(root / frozen["atomic_bridge"]["path"]),
        load_json(root / frozen["external_contract_projection"]["path"]),
        load_json(root / frozen["served_contexts"]["path"]),
    )


def test_real_contract_accounts_for_exact_population_and_has_no_answer_credit():
    result = build_from_files()
    assert result["status"] == "MIGRATION_CONTRACT_FROZEN_NO_BOT_CREDIT"
    assert result["summary"] == {
        "parent_count": 33,
        "qid_count": 13,
        "child_count": 70,
        "child_type_histogram": {"core": 58, "supplementary": 12},
        "disposition_histogram": {"merge_duplicate": 1, "rewrite": 7, "split": 24, "unresolved": 1},
        "legacy_stage_histogram": {"OK": 29, "rest": 1, "retrieval-miss": 1, "synthesis-miss": 2},
        "withdrawn_clause_count": 19,
        "unresolved_parent_count": 1,
        "model_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "bot_delta": 0,
        "measurement_delta_only": True,
    }
    assert all(claim["basis"] == "explicit" for claim in result["claims"])
    assert all(claim["answer_replay"] is None for claim in result["claims"])
    assert all(
        binding["support_spans"]
        for claim in result["claims"]
        for binding in claim["source_bindings"]
    )


def test_build_is_byte_semantically_deterministic():
    assert build_from_files() == build_from_files()


def test_missing_parent_fails_closed():
    prereg, spec, support, bridge, projection, contexts = _inputs()
    tampered = copy.deepcopy(spec)
    tampered["parents"].pop()
    with pytest.raises(ValueError, match="population mismatch"):
        build_contract(prereg, tampered, support, bridge, projection, contexts)


def test_cross_qid_source_binding_fails_closed():
    prereg, spec, support, bridge, projection, contexts = _inputs()
    tampered = copy.deepcopy(spec)
    child = tampered["parents"][0]["children"][0]
    old_id = child["source_context_ids"][0]
    wrong_id = "5ba44464-842b-46f7-ac43-259be83ad416"
    child["source_context_ids"] = [wrong_id]
    tampered_support = copy.deepcopy(support)
    claim_support = tampered_support["claims"]["m1.cat005.c30477c37c3d5942.max_remote_sensors"]
    claim_support[wrong_id] = claim_support.pop(old_id)
    with pytest.raises(ValueError, match="cross-qid"):
        build_contract(prereg, tampered, tampered_support, bridge, projection, contexts)


def test_merge_must_reference_an_existing_child():
    prereg, spec, support, bridge, projection, contexts = _inputs()
    tampered = copy.deepcopy(spec)
    merge = next(row for row in tampered["parents"] if row["disposition"] == "merge_duplicate")
    merge["replaced_by"] = ["m1.missing"]
    with pytest.raises(ValueError, match="replacement is missing"):
        build_contract(prereg, tampered, support, bridge, projection, contexts)


def test_literal_support_anchor_must_exist_exactly_once():
    prereg, spec, support, bridge, projection, contexts = _inputs()
    tampered = copy.deepcopy(support)
    tampered["claims"]["m1.cat005.c30477c37c3d5942.max_remote_sensors"][
        "934b00a8-739f-4d7b-8853-32caad5232a4"
    ] = ["not in frozen source"]
    with pytest.raises(ValueError, match="support anchor must occur exactly once"):
        build_contract(prereg, spec, tampered, bridge, projection, contexts)
