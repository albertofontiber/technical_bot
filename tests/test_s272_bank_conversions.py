"""S272 (DEC-131): el banking de las 2 conversiones es determinista, cierra y está
pineado; los recibos vivos se verifican (sha + flag de apéndice recalculados)."""
from __future__ import annotations

import json

import pytest

import scripts.s272_bank_conversions as mod


def test_banked_funnel_arithmetic() -> None:
    report = mod.build_projection()
    assert report["banked_funnel"] == {
        "denominator": 154,
        "ok": 145,
        "synthesis_miss": 7,
        "retrieval_miss": 2,
        "ok_pct": 94.16,
    }
    assert report["facts_moved_to_ok"] == 2
    assert report["official_atomic_kpi"] is None
    assert report["target"]["required_ok"] == 151
    assert report["target"]["conversions_needed"] == 6
    assert report["target"]["declared"] == "98% de 154 = 151 → +6"
    assert report["production_flag"] == (
        "MUST_PRESERVE_CONTRACT=on (Railway, confirmado por Alberto)"
    )
    assert report["mecanismo_verificado_en_produccion"] == "sí (query_logs 16:26Z)"


def test_remaining_seven_by_class_partitions_the_adjudicated_nine() -> None:
    report = mod.build_projection()
    remaining = report["remaining_synthesis_miss_by_class"]
    assert remaining["serving_view"] == ["obl_0d6a30948dfd"]
    assert remaining["uncited_scope"] == ["obl_2f5d79e354b9"]
    assert remaining["binding_tension"] == ["obl_7bba8d03d496"]
    assert remaining["composites_hybrid_gap"] == [
        "obl_015f9b9aaa3a",
        "obl_7aa723717412",
        "obl_a5d9fa1f9253",
        "obl_b2043cd4379b",
    ]
    flat = {oid for ids in remaining.values() for oid in ids}
    banked = {row["obligation_id"] for row in report["conversions_banked"]}
    assert banked == {"obl_b6f6211be439", "obl_872c35fb41d7"}
    assert len(flat) == 7 and not flat & banked


def test_live_receipts_are_verified_and_scoped() -> None:
    report = mod.build_projection()
    receipts = report["live_receipts"]
    assert [r["label"] for r in receipts] == [
        "b6f6_live_fire_asd535",
        "872c_no_fire_pearl",
        "control_sano_cad250",
    ]
    assert [r["appendix_present"] for r in receipts] == [True, False, False]
    # alcance declarado por conversión: b6f6 vivo ✓ / 872c harness-only
    banked = {row["obligation_id"]: row for row in report["conversions_banked"]}
    assert "FIRE EN VIVO" in banked["obl_b6f6211be439"]["estado_vivo"]
    assert "harness" in banked["obl_872c35fb41d7"]["estado_vivo"]
    assert "composición-de-serving" in banked["obl_872c35fb41d7"]["estado_vivo"]


def test_committed_artifact_matches_recomputation() -> None:
    committed = json.loads(mod.OUTPUT.read_text(encoding="utf-8"))
    assert committed == mod.build_projection()


def test_sha_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        mod.PINNED_SHA256_LF, "evals/s272_live_receipts_v1.json", "0" * 64
    )
    with pytest.raises(ValueError, match="SHA drift"):
        mod.build_projection()


def test_tampered_receipt_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = json.loads(mod.RECEIPTS.read_text(encoding="utf-8"))
    doc["receipts"][0]["response"] = doc["receipts"][0]["response"] + " tamper"
    with pytest.raises(ValueError, match="sha256 del response"):
        mod.verify_receipts(doc)
