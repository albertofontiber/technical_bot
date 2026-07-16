from scripts.s116_screen_independent_holdout import _score, _signature


def test_near_duplicate_score_detects_repackaged_text() -> None:
    original = _signature("panel model fc922 installation manual " * 30)
    repackaged = _signature("new distributor cover edition 2026 " + "panel model fc922 installation manual " * 30)
    score = _score(original, repackaged)
    assert score["containment"] >= 0.80


def test_unrelated_text_stays_below_threshold() -> None:
    manual = _signature("fire alarm loop detector wiring resistance " * 20)
    unrelated = _signature("hydraulic pump maintenance oil pressure bearing " * 20)
    score = _score(manual, unrelated)
    assert score["containment"] < 0.80
    assert score["jaccard"] < 0.65
