from scripts.s275_serving_view_reach_preflight import build_report


def test_s275_reach_preflight_freezes_all_six_residuals():
    report = build_report()

    assert report["population"]["target_count"] == 6
    assert report["summary"]["view_status_histogram"] == {
        "FULL": 4,
        "PARTIAL": 1,
        "ABSENT": 1,
    }


def test_s275_only_b2043_is_a_pure_serving_view_gap():
    report = build_report()
    targets = report["targets"]

    assert targets["obl_b2043cd4379b"]["status"] == "ABSENT"
    assert targets["obl_7aa723717412"]["status"] == "PARTIAL"
    assert targets["obl_b2043cd4379b"]["pure_serving_view_gap"] is True
    assert targets["obl_7aa723717412"]["pure_serving_view_gap"] is False
    assert targets["obl_7aa723717412"][
        "all_required_anchors_in_served_overlap"
    ] is True
    assert report["summary"]["pure_serving_view_gaps"] == [
        "obl_b2043cd4379b"
    ]
    assert report["summary"]["direct_causal_candidate_count"] == 1
    assert report["summary"]["cannot_by_itself_supply_required_plus_5"] is True


def test_s275_other_four_were_already_fully_served():
    report = build_report()
    targets = report["targets"]

    for obligation_id in (
        "obl_2f5d79e354b9",
        "obl_7bba8d03d496",
        "obl_a5d9fa1f9253",
        "obl_015f9b9aaa3a",
    ):
        assert targets[obligation_id]["status"] == "FULL"
        assert targets[obligation_id]["pure_serving_view_gap"] is False
