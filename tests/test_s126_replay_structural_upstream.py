from scripts.s126_replay_structural_upstream import build_payload


def test_s126_local_candidate_gate_is_exact_and_zero_cost():
    payload = build_payload()
    assert payload["status"] == "GO_LOCAL_CANDIDATE"
    assert all(payload["checks"].values())
    assert payload["cost"] == {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }


def test_s126_local_replay_recovers_only_stage_preconditions():
    payload = build_payload()
    credit = payload["stage_credit"]
    assert credit["retrieval_preconditions_recovered"] == 2
    assert credit["compatibility_validation_preconditions_recovered"] == 2
    assert credit["facts_moved_to_ok"] == 0
    assert all(
        row["expected_recovered"]
        for row in payload["procedure_prerequisite_coverage"]
    )


def test_s126_candidate_adds_missing_generic_compatibility_relations():
    contract = build_payload()["compatibility_contract"]
    assert len(contract["prior_plan"]["needs"]) == 2
    assert len(contract["candidate_plan"]["needs"]) == 3
    by_key = {row["fact_key"]: row for row in contract["rows"]}
    assert by_key["cat013#0:bucle cerrado"]["prior_facets"] == []
    assert by_key["cat013#0:bucle cerrado"]["candidate_facets"] == [
        "loop_topology"
    ]
    assert by_key["cat013#1:SDX-751 roster"]["prior_facets"] == []
    assert by_key["cat013#1:SDX-751 roster"]["candidate_facets"] == [
        "supported_device_roster"
    ]
