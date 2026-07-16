from scripts.s126_scan_independent_prerequisites import build_payload


def test_s126_independent_scan_is_exact_and_zero_cost():
    payload = build_payload()
    assert payload["status"] == "VALID_SCAN_REQUIRES_BLINDED_ADJUDICATION"
    assert all(payload["checks"].values())
    assert len(payload["documents"]) == 8
    assert len({row["manufacturer"] for row in payload["documents"]}) == 4
    assert payload["cost"] == {
        "model_calls": 0,
        "network_calls": 0,
        "database_writes": 0,
    }
    assert payload["release_authorization"] is False


def test_s126_independent_scan_receipts_are_bounded_and_exact():
    for row in build_payload()["opportunities"]:
        assert row["exact_source_receipt"] is True
        assert row["end"] - row["start"] <= 720
        assert row["quote"]
