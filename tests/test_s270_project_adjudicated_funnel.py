"""S270 (DEC-125): la proyección adjudicada es determinista, cierra y está pineada."""
from __future__ import annotations

import json

import pytest

import scripts.s270_project_adjudicated_funnel as mod


def test_adjudicated_funnel_arithmetic() -> None:
    report = mod.build_projection()
    assert report["adjudicated_funnel"] == {
        "denominator": 154,
        "ok": 143,
        "synthesis_miss": 9,
        "synthesis_miss_composition": {"core_required": 8, "disclosure_respec": 1},
        "retrieval_miss": 2,
        "ok_pct": 92.86,
    }
    assert report["facts_moved_to_ok"] == 0
    assert report["official_atomic_kpi"] is None
    assert report["target"]["required_ok"] == 151
    assert report["target"]["conversions_needed"] == 8
    assert report["target"]["declared"] == "98% de 154 = 151 → +8"


def test_adjudication_effects_match_alberto_marks() -> None:
    effects = mod.build_projection()["adjudication_effects"]
    # El ❌ de Alberto al demote de la fila 2 la deja CORE.
    assert "obl_015f9b9aaa3a" in effects["core_required_confirmed"]
    assert effects["supplementary_demoted"] == ["obl_07eee3300535", "obl_161564ff41bf"]
    assert effects["disclosure_respec"] == ["obl_872c35fb41d7"]
    assert effects["warning_block_merge"]["absorbe"] == [
        "obl_0d6a30948dfd",
        "obl_16637b935bd4",
    ]
    assert effects["warning_block_merge"]["carrier"] == "obl_0d6a30948dfd"


def test_committed_artifact_matches_recomputation() -> None:
    committed = json.loads(mod.OUTPUT.read_text(encoding="utf-8"))
    assert committed == mod.build_projection()


def test_sha_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        mod.PINNED_SHA256_LF, "evals/s270_gold_adjudication_v1.yaml", "0" * 64
    )
    with pytest.raises(ValueError, match="SHA drift"):
        mod.build_projection()
