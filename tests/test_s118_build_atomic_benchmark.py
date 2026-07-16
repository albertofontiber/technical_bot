from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.s118_build_atomic_benchmark import (
    ROOT,
    _assert_safe_output,
    build_bridge,
    execute,
    freeze_external_contract_projection,
    load_json,
    load_yaml,
    normalized_text_sha256,
    object_sha256,
)


def _child(mid: str, value: str, *, fact_type: str = "core") -> dict:
    return {
        "migration_id": mid,
        "texto": f"Explicit statement {value}",
        "tipo": fact_type,
        "estado": "presente",
        "valor": value,
        "cita": "manual p1",
        "source_pages": [1],
        "basis": "explicit",
        "requiredness_reason": "required" if fact_type == "core" else "secondary",
    }


def _accepted(parent: dict, child: dict, supported_id: str) -> dict:
    return {
        "row_type": "accepted_child",
        "parent_identity": {
            "qid": parent["qid"],
            "fact_key": parent["fact_key"],
            "parent_fact_sha256": parent["parent_fact_sha"],
            "hold_class": "atomicity-and-absence-inference-hold",
        },
        "child_id": child["migration_id"],
        "supported_subclaim_id": supported_id,
        "supported_subclaim": child["texto"],
        "supported_subclaim_sha256": normalized_text_sha256(child["texto"]),
        "texto_sha256": normalized_text_sha256(child["texto"]),
        "valor_sha256": normalized_text_sha256(child["valor"]),
        "cita_sha256": normalized_text_sha256(child["cita"]),
        "citation_binding": {
            "search_fact_key": parent["fact_key"],
            "candidate_id": "candidate-b",
            "manual_id": "manual",
            "page_numbers": [1],
            "excerpt_sha256": normalized_text_sha256("Evidence B"),
        },
        "basis": "explicit",
        "score_track": "content" if child["tipo"] == "core" else "supplementary",
        "requiredness": child["tipo"],
        "requiredness_rationale": "question-conditioned decision",
        "adjudicator_status": "accepted",
        "independent_of_runtime_outcome": True,
    }


def _resign(value: dict) -> None:
    value.pop("payload_sha256", None)
    value["payload_sha256"] = object_sha256(value)


def _fixture() -> dict:
    fact_a = {"texto": "Parent A", "tipo": "core", "estado": "presente",
              "valor": "A", "cita": "p1"}
    fact_b = {"texto": "Parent B", "tipo": "core", "estado": "presente",
              "valor": "B", "cita": "p2"}
    meta = {"texto": "Pointer", "tipo": "core", "estado": "presente",
            "valor": "Apendice A", "cita": "p3"}
    fact_c = {"texto": "Parent C", "tipo": "core", "estado": "presente",
              "valor": "C", "cita": "p4"}
    fact_d = {"texto": "Parent D", "tipo": "core", "estado": "presente",
              "valor": "D", "cita": "p5"}
    gold = [
        {"qid": "q1", "atomic_facts": [fact_a, fact_b]},
        {"qid": "q2", "atomic_facts": [meta]},
        {"qid": "q3", "atomic_facts": [fact_c]},
        {"qid": "q4", "atomic_facts": [fact_d]},
    ]
    assessment = {"per_gold": [
        {"qid": "q1", "facts": [
            {"key": "q1#0:A", "valor": "A", "clase": "retrieval-miss"},
            {"key": "q1#1:B", "valor": "B", "clase": "OK"},
        ]},
        {"qid": "q2", "facts": [
            {"key": "q2#0:Apendice A", "valor": "Apendice A", "clase": "meta-ref"},
        ]},
        {"qid": "q3", "facts": [{"key": "q3#0:C", "valor": "C", "clase": "OK"}]},
        {"qid": "q4", "facts": [{"key": "q4#0:D", "valor": "D", "clase": "OK"}]},
    ]}
    ledger = {"rows": [
        {"fact_key": "q1#0:A", "baseline_class": "retrieval-miss",
         "diagnostic_class": "retrieval-miss", "diagnostic_evidence": "old"},
        {"fact_key": "q1#1:B", "baseline_class": "OK",
         "diagnostic_class": "atomicity-and-absence-inference-hold",
         "diagnostic_evidence": "audit"},
        {"fact_key": "q2#0:Apendice A", "baseline_class": "meta-ref",
         "diagnostic_class": "meta-ref", "diagnostic_evidence": "old"},
        {"fact_key": "q3#0:C", "baseline_class": "OK",
         "diagnostic_class": "OK", "diagnostic_evidence": "old"},
        {"fact_key": "q4#0:D", "baseline_class": "OK",
         "diagnostic_class": "OK", "diagnostic_evidence": "old"},
    ]}
    sha_a, sha_b, sha_c = object_sha256(fact_a), object_sha256(fact_b), object_sha256(fact_c)
    m0 = {
        "instrument": "s106_atomic_migrator_v1",
        "source": {"sha256": "a" * 64},
        "validation": {"v2_fact_errors": 0, "gold_store_errors": 0},
        "changes": [{
            "migration_id": "m0.q1.a", "qid": "q1", "operation": "split",
            "parent_fact_sha": sha_a, "before": copy.deepcopy(fact_a),
            "after": [_child("m0.q1.a.1", "A1"), _child("m0.q1.a.2", "A2")],
        }],
    }
    transform = {
        "migration_id": "s118.q1.b", "qid": "q1", "fact_key": "q1#1:B",
        "parent_fact_sha": sha_b,
        "required_adjudicated_class": "atomicity-and-absence-inference-hold",
        "operation": "split_and_withdraw_unsupported_absence",
        "after": [_child("s118.q1.b.1", "B1"),
                  _child("s118.q1.b.2", "B2", fact_type="supplementary")],
        "withdrawals": [{"component": "unsupported absence", "reason": "not explicit"}],
    }
    input_receipts = {
        "gold_v1": {"logical_path": "evals/gold.yaml", "sha256": "a" * 64},
        "historical_assessment": {"logical_path": "evals/assessment.yaml", "sha256": "b" * 64},
        "current_partial_ledger": {"logical_path": "evals/ledger.json", "sha256": "c" * 64},
        "atomicity_adjudication": {"logical_path": "evals/s114.yaml", "sha256": "d" * 64},
        "evidence_search": {"logical_path": "evals/search.json", "sha256": "e" * 64},
        "child_adjudication": {"logical_path": "evals/child.yaml", "sha256": "f" * 64},
        "external_contract_projection": {"logical_path": "evals/projection.json", "sha256": "1" * 64},
        "upstream_m210_gate": {"logical_path": "evals/upstream.yaml", "sha256": "2" * 64},
    }
    external_sources = {
        "m0_full_manifest": {"logical_path": "evals/m0.json", "sha256": "3" * 64},
        "m1_pending_blockers": {"logical_path": "evals/blockers.json", "sha256": "4" * 64},
    }
    spec = {
        "external_sources": external_sources,
        "benchmark_policy": {"transformed_stage_policy": "pending_replay_never_inherit_parent_stage"},
        "transformations": [transform],
        "expected_bridge": {
            "historical_rows": 5,
            "historical_scored_parents": 4,
            "meta_reference_exclusions": 1,
            "m0_transformed_parents_in_population": 1,
            "s118_transformed_parents_in_population": 1,
            "unchanged_scored_parents": 2,
            "known_m1_contract_holds": 1,
            "legacy_carries_without_known_m1_blocker": 1,
            "transformed_content_claims_pending_replay": 3,
            "provisional_hybrid_content_denominator": 5,
            "provisional_hybrid_target_ok_for_95_percent": 5,
            "official_atomic_content_denominator": None,
            "official_atomic_target_ok_for_95_percent": None,
            "facts_moved_to_ok": 0,
        },
    }
    child_rows = [
        _accepted(transform, transform["after"][0], "supported.b1"),
        _accepted(transform, transform["after"][1], "supported.b2"),
        {
            "row_type": "withdrawal",
            "parent_identity": {
                "qid": "q1", "fact_key": "q1#1:B", "parent_fact_sha256": sha_b,
                "hold_class": "atomicity-and-absence-inference-hold",
            },
            "withdrawal_id": "s118.q1.b.withdrawal.1",
            "unsupported_subclaim": "unsupported absence",
            "unsupported_subclaim_sha256": normalized_text_sha256("unsupported absence"),
            "adjudicator_status": "withdrawn",
            "independent_of_runtime_outcome": True,
        },
    ]
    child_adjudication = {
        "instrument": "s118_child_claim_adjudication_v1",
        "status": "frozen_before_hybrid_bridge_execution",
        "normalization": "NFKC_then_unicode_whitespace_collapse_then_utf8_sha256",
        "independent_of_runtime_outcome": True,
        "source_receipts": {
            "gold_v1": {"path": "evals/gold.yaml", "sha256": "a" * 64},
            "s114_atomicity_adjudication": {"path": "evals/s114.yaml", "sha256": "d" * 64},
            "s114_evidence_search": {"path": "evals/search.json", "sha256": "e" * 64},
        },
        "rows": child_rows,
    }
    search = {"rows": [{
        "fact_key": "q1#1:B",
        "candidate_rows": [{
            "id": "candidate-b", "source_file": "manual", "page_number": 1,
            "excerpt": "Evidence B",
        }],
    }]}
    blockers = {
        "schema": "s106_m1_pending_blockers_v1",
        "status": "diagnostic_only_no_promotions",
        "counts": {"pending_decisions": 1},
        "source_hashes": {"closure_sha256": "5" * 64},
        "decisions": [{
            "migration_id": f"carry.q3.{sha_c[:16]}", "qid": "q3",
            "blocking_issue": "known composite", "decision_stage": "review",
        }],
    }
    population_receipts = {
        key: input_receipts[key]
        for key in ("gold_v1", "historical_assessment", "current_partial_ledger")
    }
    projection = freeze_external_contract_projection(
        gold_rows=gold, assessment=assessment, current_ledger=ledger,
        m0_manifest=m0, m1_blockers=blockers, delta_spec=spec,
        population_receipts=population_receipts,
    )
    return {
        "gold_rows": gold,
        "assessment": assessment,
        "current_ledger": ledger,
        "s114_adjudication": {"rows": [{
            "fact_key": "q1#1:B",
            "adjudicated_class": "atomicity-and-absence-inference-hold",
        }]},
        "child_adjudication": child_adjudication,
        "evidence_search": search,
        "external_projection": projection,
        "delta_spec": spec,
        "input_receipts": input_receipts,
        "upstream_gate": {
            "status": "CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY",
            "authority": "structural",
            "decision": {"facts_moved_to_ok": 0, "M3": "BLOCKED"},
        },
        "_m0": m0,
        "_blockers": blockers,
    }


def _build(data: dict) -> dict:
    return build_bridge(**{key: value for key, value in data.items() if not key.startswith("_")})


def test_build_bridge_is_explicitly_hybrid_and_has_no_official_denominator():
    output = _build(_fixture())
    assert output["status"] == "HYBRID_DIAGNOSTIC_BRIDGE_NO_OFFICIAL_ATOMIC_CREDIT"
    assert output["summary"]["provisional_hybrid_content_denominator"] == 5
    assert output["summary"]["official_atomic_content_denominator"] is None
    assert output["summary"]["facts_moved_to_ok"] == 0


def test_known_m1_hold_never_inherits_ok_credit():
    output = _build(_fixture())
    q3 = next(claim for claim in output["claims"] if claim["qid"] == "q3")
    assert q3["legacy_stage_bucket"] == "OK"
    assert q3["stage_bucket"] == "known-m1-contract-hold"
    assert q3["stage_status"] == "known-m1-contract-hold-no-stage-credit"


def test_transformed_children_never_inherit_parent_stage():
    output = _build(_fixture())
    transformed = [claim for claim in output["claims"] if claim["transform_source"] != "frozen-benchmark-carry"]
    assert {claim["stage_bucket"] for claim in transformed} == {"pending-replay"}


def test_supplementary_and_withdrawn_components_are_not_scored():
    output = _build(_fixture())
    assert {claim["valor"] for claim in output["claims"]} == {"A1", "A2", "B1", "C", "D"}
    parent = next(row for row in output["parents"] if row["fact_key"] == "q1#1:B")
    assert parent["excluded_child_count"] == 1
    assert parent["withdrawal_count"] == 1


def test_meta_reference_remains_excluded():
    output = _build(_fixture())
    assert output["excluded_rows"][0]["fact_key"] == "q2#0:Apendice A"


def test_s114_population_or_baseline_drift_fails_closed():
    data = _fixture()
    data["current_ledger"]["rows"][0]["baseline_class"] = "OK"
    with pytest.raises(ValueError, match="S114 baseline"):
        _build(data)


def test_projected_m0_before_payload_must_equal_parent():
    data = _fixture()
    data["external_projection"]["m0_changes"][0]["before"]["texto"] = "tampered"
    _resign(data["external_projection"])
    with pytest.raises(ValueError, match="M0 before payload"):
        _build(data)


def test_delta_cannot_select_on_runtime_outcome():
    data = _fixture()
    data["delta_spec"]["transformations"][0]["in_pool"] = False
    with pytest.raises(ValueError, match="runtime outcomes"):
        _build(data)


def test_child_adjudication_cannot_contain_runtime_outcome():
    data = _fixture()
    data["child_adjudication"]["rows"][0]["stage"] = "OK"
    with pytest.raises(ValueError, match="runtime outcome"):
        _build(data)


def test_child_text_and_requiredness_are_hash_bound():
    data = _fixture()
    data["delta_spec"]["transformations"][0]["after"][0]["texto"] = "plausible rewrite"
    with pytest.raises(ValueError, match="exact accepted adjudication"):
        _build(data)


def test_evidence_span_is_hash_bound():
    data = _fixture()
    data["evidence_search"]["rows"][0]["candidate_rows"][0]["excerpt"] = "tampered"
    with pytest.raises(ValueError, match="frozen evidence search"):
        _build(data)


def test_withdrawals_are_bijective():
    data = _fixture()
    data["delta_spec"]["transformations"][0]["withdrawals"][0]["component"] = "different"
    with pytest.raises(ValueError, match="bijective"):
        _build(data)


def test_parent_identity_is_qid_plus_sha_not_sha_alone():
    data = _fixture()
    duplicate = copy.deepcopy(data["gold_rows"][3]["atomic_facts"][0])
    data["gold_rows"].append({"qid": "q5", "atomic_facts": [duplicate]})
    data["assessment"]["per_gold"].append({
        "qid": "q5", "facts": [{"key": "q5#0:D", "valor": "D", "clase": "OK"}],
    })
    data["current_ledger"]["rows"].append({
        "fact_key": "q5#0:D", "baseline_class": "OK", "diagnostic_class": "OK",
        "diagnostic_evidence": "old",
    })
    expected = data["delta_spec"]["expected_bridge"]
    expected["historical_rows"] = 6
    expected["historical_scored_parents"] = 5
    expected["unchanged_scored_parents"] = 3
    expected["legacy_carries_without_known_m1_blocker"] = 2
    expected["provisional_hybrid_content_denominator"] = 6
    expected["provisional_hybrid_target_ok_for_95_percent"] = 6
    population_receipts = {
        key: data["input_receipts"][key]
        for key in ("gold_v1", "historical_assessment", "current_partial_ledger")
    }
    data["external_projection"] = freeze_external_contract_projection(
        gold_rows=data["gold_rows"], assessment=data["assessment"],
        current_ledger=data["current_ledger"], m0_manifest=data["_m0"],
        m1_blockers=data["_blockers"], delta_spec=data["delta_spec"],
        population_receipts=population_receipts,
    )
    output = _build(data)
    q5 = next(claim for claim in output["claims"] if claim["qid"] == "q5")
    assert q5["stage_bucket"] == "OK"


@pytest.mark.parametrize("field,value", [
    ("valor", None), ("estado", "ausente-probado"), ("basis", "unresolved"),
])
def test_delta_child_must_be_an_explicit_positive_claim(field, value):
    data = _fixture()
    data["delta_spec"]["transformations"][0]["after"][0][field] = value
    with pytest.raises(ValueError, match="explicit positive"):
        _build(data)


def test_output_payload_is_deterministic():
    first = _build(_fixture())
    second = _build(_fixture())
    assert first == second
    payload = copy.deepcopy(first)
    digest = payload.pop("payload_sha256")
    assert digest == object_sha256(payload)


def _write(path: Path, value, *, is_json: bool = False) -> str:
    if is_json:
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_execute_validates_hashes_and_cannot_overwrite_inputs(tmp_path):
    data = _fixture()
    root = tmp_path / "repo"
    evals = root / "evals"
    evals.mkdir(parents=True)
    values = {
        "gold_v1": data["gold_rows"],
        "historical_assessment": data["assessment"],
        "current_partial_ledger": data["current_ledger"],
        "atomicity_adjudication": data["s114_adjudication"],
        "evidence_search": data["evidence_search"],
        "upstream_m210_gate": data["upstream_gate"],
    }
    paths = {key: evals / f"{key}.{'json' if key in {'current_partial_ledger', 'evidence_search'} else 'yaml'}"
             for key in values}
    refs = {}
    for key, path in paths.items():
        digest = _write(path, values[key], is_json=path.suffix == ".json")
        refs[key] = {"path": path.relative_to(root).as_posix(), "sha256": digest}
    data["input_receipts"] = {
        key: {"logical_path": ref["path"], "sha256": ref["sha256"]}
        for key, ref in refs.items()
    }
    child = data["child_adjudication"]
    child["source_receipts"] = {
        "gold_v1": {"path": refs["gold_v1"]["path"], "sha256": refs["gold_v1"]["sha256"]},
        "s114_atomicity_adjudication": {
            "path": refs["atomicity_adjudication"]["path"],
            "sha256": refs["atomicity_adjudication"]["sha256"],
        },
        "s114_evidence_search": {
            "path": refs["evidence_search"]["path"], "sha256": refs["evidence_search"]["sha256"],
        },
    }
    child_path = evals / "child.yaml"
    child_sha = _write(child_path, child)
    refs["child_adjudication"] = {
        "path": child_path.relative_to(root).as_posix(), "sha256": child_sha,
    }
    data["input_receipts"]["child_adjudication"] = {
        "logical_path": refs["child_adjudication"]["path"], "sha256": child_sha,
    }
    gold_sha = refs["gold_v1"]["sha256"]
    data["_m0"]["source"]["sha256"] = gold_sha
    population_receipts = {
        key: data["input_receipts"][key]
        for key in ("gold_v1", "historical_assessment", "current_partial_ledger")
    }
    projection = freeze_external_contract_projection(
        gold_rows=data["gold_rows"], assessment=data["assessment"],
        current_ledger=data["current_ledger"], m0_manifest=data["_m0"],
        m1_blockers=data["_blockers"], delta_spec=data["delta_spec"],
        population_receipts=population_receipts,
    )
    projection_path = evals / "projection.json"
    projection_sha = _write(projection_path, projection, is_json=True)
    refs["external_contract_projection"] = {
        "path": projection_path.relative_to(root).as_posix(), "sha256": projection_sha,
    }
    refs = {**refs}
    spec = {
        "instrument": "s118_atomic_benchmark_delta_v1",
        "frozen_inputs": refs,
        **data["delta_spec"],
    }
    delta_path = evals / "delta.yaml"
    _write(delta_path, spec)
    output_path = evals / "s118_atomic_benchmark_bridge_v1.json"
    output = execute(root=root, delta_path=delta_path, output_path=output_path)
    assert output["summary"]["provisional_hybrid_content_denominator"] == 5

    with pytest.raises(ValueError, match="allowlisted"):
        execute(root=root, delta_path=delta_path, output_path=paths["gold_v1"])
    paths["historical_assessment"].write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 drift"):
        execute(root=root, delta_path=delta_path, output_path=output_path)


def test_strict_loaders_reject_duplicates_aliases_and_nonfinite(tmp_path):
    duplicate_json = tmp_path / "duplicate.json"
    duplicate_json.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_json(duplicate_json)

    nonfinite_json = tmp_path / "nonfinite.json"
    nonfinite_json.write_text('{"a": NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON"):
        load_json(nonfinite_json)

    duplicate_yaml = tmp_path / "duplicate.yaml"
    duplicate_yaml.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate YAML key"):
        load_yaml(duplicate_yaml)

    alias_yaml = tmp_path / "alias.yaml"
    alias_yaml.write_text("a: &x [1]\nb: *x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aliases"):
        load_yaml(alias_yaml)

    nonfinite_yaml = tmp_path / "nonfinite.yaml"
    nonfinite_yaml.write_text("a: .nan\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite YAML"):
        load_yaml(nonfinite_yaml)


def test_canonical_output_rejects_symlink_when_platform_allows_it(tmp_path):
    root = tmp_path / "repo"
    evals = root / "evals"
    evals.mkdir(parents=True)
    target = evals / "target.json"
    target.write_text("{}", encoding="utf-8")
    canonical = evals / "s118_atomic_benchmark_bridge_v1.json"
    try:
        canonical.symlink_to(target)
    except OSError:
        pytest.skip("platform does not permit symlink creation")
    with pytest.raises(ValueError, match="symlink or junction"):
        _assert_safe_output(
            root, canonical, set(), "evals/s118_atomic_benchmark_bridge_v1.json",
        )


def test_real_artifact_smoke_freezes_holds_and_invalid_hp015_absence():
    bridge = load_json(ROOT / "evals/s118_atomic_benchmark_bridge_v1.json")
    assert bridge["status"] == "HYBRID_DIAGNOSTIC_BRIDGE_NO_OFFICIAL_ATOMIC_CREDIT"
    holds = [claim for claim in bridge["claims"] if claim["stage_bucket"] == "known-m1-contract-hold"]
    assert len(holds) == 33
    assert sum(claim["legacy_stage_bucket"] == "OK" for claim in holds) == 29
    assert bridge["summary"]["official_atomic_content_denominator"] is None
    claim_text = "\n".join(str(claim.get("texto") or "").lower() for claim in bridge["claims"])
    assert "no existe desactivar un detector concreto" not in claim_text
    assert "no se puede aislar uno solo" not in claim_text
    assert "no una bateria tampon a bordo" not in claim_text
    payload = copy.deepcopy(bridge)
    digest = payload.pop("payload_sha256")
    assert digest == object_sha256(payload)
