from scripts.s165_offline_transport_attribution import run


def test_s165_offline_attribution_never_grants_original_credit():
    result = run()
    assert result["decision"]["s165_credit"] is False
    assert result["decision"]["target_probe"] is False
    assert result["decision"]["production"] is False
    assert result["cost"] == {"model_calls": 0, "usd": 0}


def test_s165_offline_attribution_has_no_unknown_or_parse_failures():
    result = run()
    assert result["attribution"]["unknown_id_failures"] == 0
    assert result["attribution"]["parse_failures"] == 0
