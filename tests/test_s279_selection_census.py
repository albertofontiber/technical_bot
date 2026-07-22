"""Unit tests for the pure, offline logic of the s279 selection census.

These cover the deterministic helpers (gold-source parsing, delta classification,
probe adjudication) without any network / RPC / model call.  The live read-only
measurement path is exercised by running the instrument itself.
"""
from __future__ import annotations

import importlib

import pytest

census = importlib.import_module("scripts.s279_selection_census")


# ── gold fuente → source stems ────────────────────────────────────────────────
def test_fuente_stems_plus_separated() -> None:
    row = {"_provenance": {"fuente": "997-669-005-3_Instal-Comm_ES.pdf + 997-671-005-3_Configuration_ES.pdf (configuracion)"}}
    stems = census._fuente_pdf_stems(row)
    assert stems == ["997-669-005-3_Instal-Comm_ES", "997-671-005-3_Configuration_ES"]


def test_fuente_stems_filename_with_spaces() -> None:
    row = {"_provenance": {"fuente": "55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT.pdf"}}
    stems = census._fuente_pdf_stems(row)
    assert stems == ["55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT"]


def test_fuente_stems_empty() -> None:
    assert census._fuente_pdf_stems({}) == []
    assert census._fuente_pdf_stems({"_provenance": {"fuente": "sin fichero"}}) == []


def test_stem_matches_substring_symmetric() -> None:
    assert census._stem_matches("MIDT180", "MIDT180")
    assert census._stem_matches("IT", "55315013 Manual ... IT")  # substring
    assert census._stem_matches("55315013 Manual ... IT", "IT")  # symmetric
    assert not census._stem_matches("MIDT180", "MFDT180")
    assert not census._stem_matches("", "anything")


# ── delta classification ──────────────────────────────────────────────────────
def _arm(*, cands: int, status: str, sem: str | None = None, facet_sel: str | None = None,
         plan_sha: str = "x") -> dict:
    facet: dict = {"applicable": True}
    if facet_sel is not None:
        facet["selected_id"] = facet_sel
    return {
        "candidate_count": cands,
        "status": status,
        "overflow": False,
        "semantic_selected_id": sem,
        "facet": facet,
        "authority_rejections": None,
        "plan": {"sha256": plan_sha},
    }


def test_classify_lane_blocked() -> None:
    v4 = _arm(cands=0, status="unverified_document_lineage")
    v5 = _arm(cands=0, status="unverified_document_lineage")
    d = census.classify_delta(v4, v5, target_id=None)
    assert d["classification"] == "LANE_BLOCKED"
    assert d["lane_blocked_reason"] == "unverified_document_lineage"


def test_classify_same_when_both_fetch_same_selection() -> None:
    v4 = _arm(cands=10, status="fetched", sem="A")
    v5 = _arm(cands=10, status="fetched", sem="A")
    d = census.classify_delta(v4, v5, target_id=None)
    assert d["classification"] == "SAME"


def test_classify_gain_from_facet_row() -> None:
    v4 = _arm(cands=10, status="fetched", sem="A")
    v5 = _arm(cands=10, status="fetched", sem="A", facet_sel="B")
    d = census.classify_delta(v4, v5, target_id="B")
    assert d["classification"] == "GAIN"
    assert d["gained_ids"] == ["B"]
    assert d["gained_includes_target"] is True


def test_classify_loss() -> None:
    v4 = _arm(cands=10, status="fetched", sem="A")
    v5 = _arm(cands=10, status="fetched", sem=None)
    d = census.classify_delta(v4, v5, target_id=None)
    assert d["classification"] == "LOSS"
    assert d["lost_ids"] == ["A"]


def test_classify_zero_candidates_but_fetched_is_same_not_blocked() -> None:
    # both arms reach the RPC and legitimately find no FTS candidate -> SAME.
    v4 = _arm(cands=0, status="no_fts_candidates")
    v5 = _arm(cands=0, status="no_fts_candidates")
    d = census.classify_delta(v4, v5, target_id=None)
    assert d["classification"] == "SAME"


# ── probe adjudication ────────────────────────────────────────────────────────
def _v5_with_target(*, present: bool, per_group: list[dict] | None = None,
                    facet: dict | None = None, sem: str | None = None,
                    status: str = "fetched", cands: int = 10) -> dict:
    return {
        "status": status,
        "candidate_count": cands,
        "semantic_selected_id": sem,
        "facet": facet or {},
        "target_detail": {"present": present, "per_group": per_group or []},
    }


def test_probe_not_selected_no_reach() -> None:
    v5 = _v5_with_target(present=False, status="candidate_cap_exceeded", cands=0)
    verdict = census.adjudicate_probe("cat019", "T", v5)
    assert verdict["verdict"] == "NOT_SELECTED"
    assert "no candidate reach" in verdict["reason"]


def test_probe_not_selected_not_eligible() -> None:
    per_group = [
        {"group_index": 0, "n_terms": 6, "gated_by_A7": True, "terms_hit": 1, "hits": ["x"]},
        {"group_index": 1, "n_terms": 6, "gated_by_A7": True, "terms_hit": 1, "hits": ["y"]},
    ]
    facet = {"selected_id": "W", "selected_chunk_index": 88, "group_index": 2, "terms_hit": 3, "is_target": False}
    v5 = _v5_with_target(present=True, per_group=per_group, facet=facet, sem=None)
    verdict = census.adjudicate_probe("cat019", "T", v5)
    assert verdict["verdict"] == "NOT_SELECTED"
    assert "NOT eligible" in verdict["reason"]
    assert "W" in verdict["reason"]


def test_probe_selected_by_facet() -> None:
    per_group = [{"group_index": 0, "n_terms": 6, "gated_by_A7": True, "terms_hit": 4, "hits": ["a", "b", "c", "d"]}]
    facet = {"selected_id": "T", "selected_chunk_index": 14, "group_index": 0, "terms_hit": 4, "is_target": True}
    v5 = _v5_with_target(present=True, per_group=per_group, facet=facet)
    verdict = census.adjudicate_probe("cat019", "T", v5)
    assert verdict["verdict"] == "SELECTED_BY_FACET"


def test_probe_selected_by_semantic() -> None:
    per_group = [{"group_index": 0, "n_terms": 6, "gated_by_A7": True, "terms_hit": 1, "hits": ["x"]}]
    v5 = _v5_with_target(present=True, per_group=per_group, facet={}, sem="T")
    verdict = census.adjudicate_probe("cat017", "T", v5)
    assert verdict["verdict"] == "SELECTED_BY_SEMANTIC"


def test_anchor_row_shape() -> None:
    scope = {
        "document_id": "d", "extraction_sha256": "e", "source_file": "s",
        "manufacturer": "m", "product_model": "p",
        "document_local_anchor_route": "protected_rerank_prefix",
    }
    row = census._anchor_row(scope)
    assert row["document_local_anchor_route"] == "protected_rerank_prefix"
    assert set(row) == {
        "document_id", "extraction_sha256", "source_file", "manufacturer",
        "product_model", "document_local_anchor_route",
    }


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
