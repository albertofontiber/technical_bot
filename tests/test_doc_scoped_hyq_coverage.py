from pathlib import Path

import src.rag.doc_scoped_hyq_coverage as lane

ROOT = Path(__file__).resolve().parents[1]
COMPAT_QUERY = ROOT / "config" / "retrieval_facets_compatibility_candidate_v1.yaml"
COMPAT_EVIDENCE = ROOT / "config" / "evidence_coverage_compatibility_candidate_v1.yaml"


def test_parent_selection_is_bounded_and_source_diverse():
    rows = [
        {
            "chunk_id": f"a-{index}",
            "source_file": "manual-a",
            "page_number": index,
            "question": f"capacidad total lazos dispositivos variante {index}",
        }
        for index in range(8)
    ] + [
        {
            "chunk_id": "b-1",
            "source_file": "manual-b",
            "page_number": 1,
            "question": "capacidad total lazos dispositivos alternativa",
        }
    ]

    selected = lane.select_document_diverse_parents(
        ["capacidad total lazos dispositivos"], rows
    )

    assert "b-1" in selected
    assert len(selected) <= lane.PARENT_LIMIT


def test_parent_selection_stratifies_compound_query_by_governed_entity():
    rows = [
        {
            "chunk_id": "panel-topology",
            "source_file": "panel-install",
            "page_number": 9,
            "question": "topologia bucle cerrado retorno del panel",
        },
        {
            "chunk_id": "detector-protocol",
            "source_file": "detector-manual",
            "page_number": 69,
            "question": "protocolo de comunicacion del detector",
        },
        {
            "chunk_id": "detector-roster",
            "source_file": "detector-manual",
            "page_number": 71,
            "question": "equipos y detectores compatibles",
        },
        {
            "chunk_id": "generic-noise",
            "source_file": "popular-manual",
            "page_number": 1,
            "question": "protocolo detector equipos compatibles topologia bucle retorno",
        },
    ]
    selected = lane.select_document_diverse_parents(
        [
            "panel detector protocolo",
            "panel detector equipos compatibles",
            "panel detector topologia bucle retorno",
        ],
        rows,
        source_groups=[
            {"token": "panel", "sources": ["panel-install"]},
            {"token": "detector", "sources": ["detector-manual"]},
        ],
        focus_query="panel detector",
    )

    assert "generic-noise" not in selected
    assert "panel-topology" in selected
    assert {"detector-protocol", "detector-roster"}.issubset(selected)


def test_collection_serves_parent_source_not_generated_hyq(monkeypatch):
    content = "El sistema admite cuatro lazos y 792 dispositivos en total."
    parent = {
        "id": "parent-real",
        "content": content,
        "source_file": "manual-real",
    }
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual-real"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query: {"archetype": "capacity_count", "needs": ["capacidad lazos"]},
    )
    monkeypatch.setattr(
        lane,
        "select_evidence_coverage_cards",
        lambda candidates, **_kwargs: [
            {
                "candidate_id": candidates[0]["id"],
                "start": 0,
                "end": len(content),
                "quote": content,
                "facet": "capacity",
                "exact_source_span_validated": True,
            }
        ],
    )

    def fetcher(scope, needs):
        assert scope == ["manual-real"]
        assert needs == ["capacidad lazos"]
        return [parent], 23

    selected, trace = lane.collect_document_scoped_hyq(
        "¿Cuántos lazos admite?", fetcher=fetcher
    )

    assert selected[0]["id"] == "parent-real"
    assert selected[0]["content"] == content
    assert "question" not in selected[0]
    assert selected[0]["hyq_navigation_validated"] is True
    assert trace["served_hyq_prose"] is False
    assert trace["hyq_rows"] == 23
    assert trace["http_requests"] == 0


def test_collection_propagates_hyq_http_request_count(monkeypatch):
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query: {"archetype": "capacity_quantity", "needs": ["capacity"]},
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad", fetcher=lambda _scope, _needs: ([], 1200, 3)
    )

    assert selected == []
    assert trace["http_requests"] == 3


def test_collection_propagates_versioned_fetch_fingerprints(monkeypatch):
    receipts = {
        "hyq_rows_sha256": "a" * 64,
        "selected_parent_ids_sha256": "b" * 64,
        "hydrated_parents_sha256": "c" * 64,
    }
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query: {"archetype": "capacity_quantity", "needs": ["capacity"]},
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: ([], 1200, 3, receipts),
        include_fetch_receipts=True,
    )

    assert selected == []
    assert trace["fetch_receipts"] == receipts


def test_collection_prefers_complementary_facets_over_duplicate_early_parents(monkeypatch):
    parents = [
        {"id": "unit-a", "content": "a", "source_file": "manual"},
        {"id": "unit-b", "content": "b", "source_file": "manual"},
        {"id": "total", "content": "c", "source_file": "manual"},
    ]
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query: {"archetype": "capacity_quantity", "needs": ["capacity"]},
    )

    def cards(candidates, **_kwargs):
        parent = candidates[0]
        facet = "system_total" if parent["id"] == "total" else "per_unit_capacity"
        return [
            {
                "candidate_id": parent["id"],
                "start": 0,
                "end": 1,
                "quote": parent["content"],
                "facet": facet,
                "query_term_hits": ["model"],
                "exact_source_span_validated": True,
            }
        ]

    monkeypatch.setattr(lane, "select_evidence_coverage_cards", cards)
    selected, _ = lane.collect_document_scoped_hyq(
        "capacidad del modelo", fetcher=lambda _scope, _needs: (parents, 3)
    )

    assert [row["id"] for row in selected] == ["unit-a", "total"]


def test_collection_rejects_hydrated_parent_outside_canonical_scope(monkeypatch):
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"allowed-manual"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query: {"archetype": "capacity_quantity", "needs": ["capacity"]},
    )
    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: (
            [{"id": "cross-scope", "content": "lazo capacidad", "source_file": "other"}],
            1,
        ),
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"


def test_candidate_compatibility_contract_can_cover_three_complementary_relations(monkeypatch):
    parents = [
        {
            "id": "protocol",
            "content": "La comunicación del lazo utiliza el protocolo CLIP; consulte los equipos compatibles.",
            "source_file": "manual-a",
        },
        {
            "id": "roster",
            "content": "Equipos de lazo compatibles: detector óptico SDX-751.",
            "source_file": "manual-a",
        },
        {
            "id": "topology",
            "content": "El bucle debe ser cerrado: sale de la central y el retorno vuelve a ella.",
            "source_file": "manual-b",
        },
    ]
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual-a", "manual-b"})},
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "¿Es compatible el detector SDX-751 con esta central y su lazo?",
        fetcher=lambda _scope, _needs: (parents, 30, 2),
        query_facets_path=COMPAT_QUERY,
        evidence_config_path=COMPAT_EVIDENCE,
        append_limit=3,
        entity_stratified=True,
    )

    assert [row["id"] for row in selected] == ["protocol", "roster", "topology"]
    assert {facet for row in selected for facet in row["coverage_card_facets"]} == {
        "protocol_scope",
        "supported_device_roster",
        "loop_topology",
    }
    assert trace["served_hyq_prose"] is False
    assert trace["http_requests"] == 2


def test_candidate_compatibility_append_budget_is_bounded():
    try:
        lane.collect_document_scoped_hyq("compatibilidad", append_limit=4)
    except ValueError as exc:
        assert str(exc) == "HYQ append limit must be 1..3"
    else:
        raise AssertionError("over-budget compatibility append must fail closed")
