from scripts import s120_versioned_obligation_cache_replay as replay


def test_s120_replay_covers_diagnostics_without_removing_frozen_obligations():
    payload = replay.build_replay()
    gate = payload["gate"]
    assert gate["status"] == "LOCAL_OBLIGATION_CACHE_GO_PROBE_NOT_AUTHORIZED"
    assert all(gate["diagnostic_checks"].values())
    assert len(gate["diagnostic_claim_checks"]) == 4
    assert all(gate["diagnostic_claim_checks"].values())
    assert gate["legacy_obligation_kinds_removed"] == []
    assert gate["historical_legacy_kind_mismatches"] == []
    assert gate["distinct_probe_candidates"] == ["hp005", "hp009", "hp017"]
    assert gate["changed_obligation_packet_qids"] == ["hp005", "hp009", "hp017"]
    assert gate["unexpected_obligation_packet_changes"] == []
    assert gate["missing_expected_obligation_packet_changes"] == []
    assert payload["contract"]["facts_moved_to_ok"] == 0
    assert payload["contract"]["fresh_answer_calls_authorized"] == 0


def test_s120_replay_is_deterministic():
    first = replay.build_replay()
    second = replay.build_replay()
    assert first == second
