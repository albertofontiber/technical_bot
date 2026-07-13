import src.rag.doc_scoped_hyq_coverage as lane


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
