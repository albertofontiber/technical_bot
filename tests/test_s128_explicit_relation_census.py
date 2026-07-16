from scripts.s128_adjudicate_explicit_relation_census import build_payload as adjudicate
from scripts.s128_explicit_relation_census import build_payload as scan


def test_s128_candidate_scan_is_local_and_frozen():
    payload = scan()

    assert payload["status"] == "CANDIDATES_ONLY_NOT_ADJUDICATED"
    assert len(payload["document_receipts"]) == 12
    assert payload["candidate_count"] == 168
    assert all(row["chunk_count"] > 0 for row in payload["document_receipts"])
    assert payload["cost"] == {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }


def test_s128_census_passes_only_the_offline_design_gate():
    payload = adjudicate()

    assert payload["status"] == "GO_TO_OFFLINE_EXTRACTOR_DESIGN"
    assert payload["eligible_relation_count"] == 7
    assert payload["relation_closed_class_count"] == 4
    assert payload["hard_negative_acceptances"] == 0
    assert payload["exact_provenance_rate"] == 1.0
    assert all(payload["checks"].values())
    assert payload["authorization"] == "deterministic_offline_extractor_design_only"
    assert payload["credit"] == {
        "facts_moved_to_ok": 0,
        "official_funnel_change": False,
    }
