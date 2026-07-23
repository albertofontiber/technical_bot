from copy import deepcopy

from src.rag.post_rerank_coverage import (
    apply_post_rerank_coverage_with_trace,
    has_exact_coverage_receipt,
)
from src.rag.rerank_pool_coverage import (
    APPEND_LIMIT,
    LANE,
    POOL_LIMIT,
    select_rerank_pool_coverage,
)
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


def _row(row_id, content, *, source="manual-a", model="PANEL-A", rank=0):
    return {
        "id": row_id,
        "content": content,
        "section_title": "",
        "source_file": source,
        "product_model": model,
        "page_number": rank + 1,
    }


def _attested(row_id, *, lane=STRUCTURAL_LANE):
    content = "Conexión validada del circuito de salida."
    row = {
        **_row(row_id, content),
        "retrieval_lane": lane,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": 0,
                "end": len(content),
                "quote": content,
                "facet": "connection",
                "exact_source_span_validated": True,
            }
        ],
    }
    row["structural_neighbor_validated"] = True
    return row


def test_selects_distinct_programming_complement_from_fragmented_ui(monkeypatch):
    monkeypatch.setattr(
        "src.rag.rerank_pool_coverage.resolve_query",
        lambda _query: {"allowed_sources": {"manual-a"}, "add_models": ["PANEL-A"]},
    )
    query = (
        "¿Cómo programar una zona para activar una salida de sirena "
        "cuando coinciden dos detectores?"
    )
    reranked = [
        _row(
            "served-input",
            "Condición de entrada: coincidencia de dos detectores en la matriz.",
        )
    ]
    pool = [
        *deepcopy(reranked),
        _row(
            "logic-repeat",
            "Regla de entrada y matriz por coincidencia de detectores en zona.",
            rank=1,
        ),
        _row(
            "output-ui",
            "Editar el evento de salida\n\nAcción: activar\n\n"
            "Aplicar sobre función especial\n\nSeleccionar circuito de sirena\n\n"
            "Transferir a los equipos elegidos",
            rank=2,
        ),
        _row("noise", "Ajuste de fecha y hora del panel.", rank=3),
    ]

    selected, trace = select_rerank_pool_coverage(query, pool, reranked)

    assert "output-ui" in [row["id"] for row in selected]
    assert len(selected) <= APPEND_LIMIT
    assert trace["model_calls"] == 0
    assert trace["database_reads"] == 0
    assert all(row["retrieval_lane"] == LANE for row in selected)
    assert all(has_exact_coverage_receipt(row) for row in selected)


def test_exact_document_call_can_skip_catalog_scope(monkeypatch):
    def forbidden_catalog_lookup(_query):
        raise AssertionError("catalogue lookup crossed an exact document boundary")

    monkeypatch.setattr(
        "src.rag.rerank_pool_coverage.resolve_query",
        forbidden_catalog_lookup,
    )
    query = (
        "¿Cómo programar una zona para activar una salida de sirena "
        "cuando coinciden dos detectores?"
    )
    candidate = _row(
        "exact-document-row",
        "Editar el evento de salida\n\nAcción: activar\n\n"
        "Aplicar sobre función especial\n\nSeleccionar circuito de sirena\n\n"
        "Transferir a los equipos elegidos",
    )

    selected, trace = select_rerank_pool_coverage(
        query,
        [candidate],
        [],
        apply_catalog_scope=False,
    )

    assert [row["id"] for row in selected] == ["exact-document-row"]
    assert trace["catalog_scope_applied"] is False


def test_scope_accepts_exact_metadata_model_but_rejects_cross_family(monkeypatch):
    monkeypatch.setattr(
        "src.rag.rerank_pool_coverage.resolve_query",
        lambda _query: {
            "allowed_sources": {"catalogued-manual"},
            "add_models": ["PANEL-A"],
        },
    )
    query = "¿Cómo conectar los terminales y comprobar el cableado?"
    pool = [
        _row(
            "cross-family",
            "Conectar terminales, polaridad y cableado del circuito. "
            "Comprobar continuidad, pantalla, tierra y límites de instalación.",
            source="other-manual",
            model="PANEL-B",
        ),
        _row(
            "metadata-equivalent",
            "Conectar terminales, polaridad y cableado del circuito. "
            "Comprobar continuidad, pantalla, tierra y límites de instalación.",
            source="pending-catalog-adjudication",
            model="Panel A",
            rank=1,
        ),
    ]

    selected, trace = select_rerank_pool_coverage(query, pool, [])

    assert [row["id"] for row in selected] == ["metadata-equivalent"]
    assert trace["canonical_scope_rows"] == 1


def test_rejects_toc_duplicate_prefix_and_pool_overflow(monkeypatch):
    monkeypatch.setattr(
        "src.rag.rerank_pool_coverage.resolve_query",
        lambda _query: {"allowed_sources": set(), "add_models": []},
    )
    query = "¿Cómo programar una regla de entrada y salida?"
    served = _row("served", "Regla de entrada y salida.")
    toc = _row(
        "toc",
        "# Índice\n1 Programación 5\n2 Regla entrada 10\n3 Salida 15\n"
        "4 Matriz 20\n5 Retardo 25\n6 Edición 30\n7 Menú 35\n8 Acción 40\n",
    )

    selected, _ = select_rerank_pool_coverage(query, [served, toc], [served])
    overflow, trace = select_rerank_pool_coverage(
        query,
        [_row(str(index), "Regla de entrada y salida.") for index in range(POOL_LIMIT + 1)],
        [],
    )

    assert selected == []
    assert overflow == []
    assert trace["status"] == "not_applicable_or_pool_overflow"


def test_same_location_dedup_rejects_only_near_duplicates(monkeypatch):
    monkeypatch.setattr(
        "src.rag.rerank_pool_coverage.resolve_query",
        lambda _query: {"allowed_sources": set(), "add_models": []},
    )
    query = (
        "Conectar terminales de retorno del lazo y colocar la resistencia "
        "final de linea con la polaridad correcta"
    )
    first = _row(
        "return-terminals",
        "Conectar los terminales de retorno del lazo respetando la polaridad "
        "correcta antes de comprobar el cableado.",
    )
    near_duplicate = _row(
        "return-terminals-copy",
        "Conectar los terminales de retorno del lazo respetando la polaridad "
        "correcta antes de comprobar todo el cableado.",
    )
    distinct_same_page = _row(
        "end-of-line",
        "Colocar la resistencia final de linea en el ultimo dispositivo del "
        "lazo y verificar la polaridad correcta de los terminales.",
    )

    selected, trace = select_rerank_pool_coverage(
        query,
        [first, near_duplicate, distinct_same_page],
        [],
    )

    assert trace["duplicate_location_rows_rejected"] == 1
    assert trace["canonical_scope_rows"] == 2
    assert "return-terminals-copy" not in trace["selected_ids"]
    assert "return-terminals" in {row["id"] for row in selected}


def test_pool_lane_sees_prior_lane_candidates_as_coverage_context():
    reranked = [_row("base", "Base protegida.")]
    structural = _attested("structural")
    pool_candidate = {
        **_attested("pool", lane=LANE),
        "rerank_pool_coverage_validated": True,
    }
    observed_context = []

    def structural_collector(_query, _reranked):
        return [structural], {"lane": STRUCTURAL_LANE, "status": "selected"}

    def pool_collector(_query, _pool, context):
        observed_context.extend(row["id"] for row in context)
        return [pool_candidate], {"lane": LANE, "status": "selected"}

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        retrieval_pool=[_row("pool-source", "Conexión del circuito.")],
        enabled=True,
        structural_enabled=True,
        hyq_enabled=False,
        pool_enabled=True,
        structural_collector=structural_collector,
        pool_collector=pool_collector,
    )

    assert observed_context == ["base", "structural"]
    assert [row["id"] for row in output] == ["base", "structural", "pool"]
    assert trace["protected_prefix_equal"] is True
