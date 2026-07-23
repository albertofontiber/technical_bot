"""s278 §3 — reserva obligation-aware de warnings (clase hp002).

Fixtures sintéticos al estilo de tests/test_post_rerank_coverage.py.  El fallo
real (hp002:r1): el bloque de ADVERTENCIA del MISMO documento ya servido
(ASD535 p121, chunk 5b6a3a19) estaba en el pool pagado (#28) y nunca llegó al
contexto — la puerta de 6 términos de ``_query_card`` lo dejó fuera y el cap
global ``MAX_APPENDED=4`` se consumió antes.  La reserva tiene presupuesto
PROPIO (1 fila), es determinista (sin QID/gold/LLM) y fail-open.
"""
from copy import deepcopy

from src.rag.doc_scoped_hyq_coverage import LANE as HYQ_LANE
from src.rag.post_rerank_coverage import (
    MAX_APPENDED,
    apply_post_rerank_coverage_with_trace,
    coverage_context_content,
    is_validated_coverage_chunk,
)
from src.rag.rerank_pool_coverage import (
    OBLIGATION_WARNING_LANE,
    select_obligation_warning_reserve,
)
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE

_PROCEDURAL_QUERY = (
    "El aspirador ASD535 da una alarma de flujo bajo intermitente; "
    "¿cuál es la causa más probable y cómo se diagnostica?"
)
_SPEC_QUERY = "¿Qué resistencia de fin de línea lleva el lazo del ASD535?"
# Control hp009 (settled s93/DEC-084): pregunta family-generic de EOL,
# conducta esperada = answer de spec — la reserva NO debe disparar.
_HP009_CONTROL_QUERY = (
    "¿Cuál es la resistencia de fin de línea recomendada para los lazos "
    "de la central Morley ZXe?"
)
_WARNING_SENTENCE = (
    "ADVERTENCIA: antes de iniciar los trabajos de mantenimiento deben "
    "bloquearse los controles de incendio, las alertas remotas y las zonas "
    "de extinción."
)
_SERVED_SOURCE = "asd535-manual.pdf"


def _served_base(row_id="base", *, source_file=_SERVED_SOURCE):
    return {
        "id": row_id,
        "content": "Puesta en marcha del equipo.",
        "source_file": source_file,
        "similarity": 0.9,
    }


def _warning_pool_row(row_id="warning-pool", *, source_file=_SERVED_SOURCE):
    content = (
        "9.3 Trabajos previos en el equipo de aspiración.\n\n"
        + _WARNING_SENTENCE
        + "\n\nEl filtro se revisa según el plan del fabricante."
    )
    return {
        "id": row_id,
        "content": content,
        "source_file": source_file,
        "section_title": "Trabajos previos",
        "page_number": 121,
    }


def _lane_candidate(row_id, *, lane=STRUCTURAL_LANE):
    content = "La resistencia máxima del lazo es 35 ohmios."
    start = content.index("resistencia")
    end = len(content) - 1
    row = {
        "id": row_id,
        "content": content,
        "source_file": "otro-manual.pdf",
        "retrieval_lane": lane,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": start,
                "end": end,
                "quote": content[start:end],
                "facet": "loop_resistance",
                "exact_source_span_validated": True,
            }
        ],
    }
    if lane == STRUCTURAL_LANE:
        row["structural_neighbor_validated"] = True
    else:
        row["hyq_navigation_validated"] = True
    return row


def _apply(query, reranked, pool, **overrides):
    kwargs = dict(
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
        obligation_reserve_enabled=True,
    )
    kwargs.update(overrides)
    return apply_post_rerank_coverage_with_trace(
        query, reranked, retrieval_pool=pool, **kwargs
    )


def test_flag_off_is_inert_and_never_calls_the_reserve():
    reranked = [_served_base()]
    snapshot = deepcopy(reranked)
    pool = [_warning_pool_row()]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("default-off obligation reserve was called")

    # default (None -> config, off) y off explícito: byte-inerte, ni una lane.
    for override in (
        {"obligation_reserve_enabled": None},
        {"obligation_reserve_enabled": False},
    ):
        output, trace = _apply(
            _PROCEDURAL_QUERY,
            reranked,
            pool,
            obligation_reserve_collector=forbidden,
            **override,
        )

        assert output is reranked
        assert reranked == snapshot
        assert trace["status"] == "disabled_or_not_applicable"
        assert trace["lanes"] == []


def test_procedural_query_reserves_the_warning_beyond_the_global_cap():
    reranked = [_served_base()]
    warning = _warning_pool_row()
    pool = [
        {
            "id": "pool-noise",
            "content": "Datos generales del sistema de aspiración.",
            "source_file": _SERVED_SOURCE,
        },
        warning,
    ]

    def structural_collector(_query, _reranked):
        return (
            [_lane_candidate("structural-1"), _lane_candidate("structural-2")],
            {"lane": STRUCTURAL_LANE, "status": "selected"},
        )

    def hyq_collector(_query):
        return (
            [
                _lane_candidate("hyq-1", lane=HYQ_LANE),
                _lane_candidate("hyq-2", lane=HYQ_LANE),
            ],
            {"lane": HYQ_LANE, "status": "selected"},
        )

    output, trace = _apply(
        _PROCEDURAL_QUERY,
        reranked,
        pool,
        structural_enabled=True,
        hyq_enabled=True,
        structural_collector=structural_collector,
        hyq_collector=hyq_collector,
    )

    # Los 4 huecos del cap global quedan intactos y la reserva entra ADEMÁS.
    assert len(output) - len(reranked) == MAX_APPENDED + 1
    assert [row["id"] for row in output[1:5]] == [
        "structural-1",
        "structural-2",
        "hyq-1",
        "hyq-2",
    ]
    reserved = output[-1]
    assert reserved["id"] == "warning-pool"
    assert reserved["retrieval_lane"] == OBLIGATION_WARNING_LANE
    assert reserved["obligation_warning_reserve_rank"] == 1
    assert is_validated_coverage_chunk(reserved) is True
    assert coverage_context_content(reserved) == _WARNING_SENTENCE
    assert trace["protected_prefix_equal"] is True
    assert "warning-pool" in trace["appended_ids"]
    assert trace["lanes"][-1]["lane"] == OBLIGATION_WARNING_LANE
    assert trace["lanes"][-1]["status"] == "selected"
    assert trace["lanes"][-1]["selected_ids"] == ["warning-pool"]


def test_non_procedural_query_does_not_reserve():
    reranked = [_served_base()]
    pool = [_warning_pool_row()]

    output, trace = _apply(_SPEC_QUERY, reranked, pool)

    assert output is reranked
    assert trace["status"] == "no_append"
    assert trace["appended_ids"] == []
    assert trace["lanes"][-1]["lane"] == OBLIGATION_WARNING_LANE
    assert trace["lanes"][-1]["status"] == "non_procedural_query"


def test_cross_family_warning_is_not_reserved():
    reranked = [_served_base()]
    pool = [_warning_pool_row(source_file="otra-familia-manual.pdf")]

    output, trace = _apply(_PROCEDURAL_QUERY, reranked, pool)

    assert output is reranked
    assert trace["appended_ids"] == []
    assert trace["lanes"][-1]["status"] == "no_warning_in_served_scope"


def test_pool_without_warning_is_a_no_op():
    reranked = [_served_base()]
    pool = [
        {
            "id": "sin-aviso",
            "content": "El caudal nominal del aspirador es de 60 l/min.",
            "source_file": _SERVED_SOURCE,
        }
    ]

    output, trace = _apply(_PROCEDURAL_QUERY, reranked, pool)

    assert output is reranked
    assert trace["appended_ids"] == []
    assert trace["lanes"][-1]["status"] == "no_warning_in_served_scope"


def test_failed_exact_pool_revalidation_is_a_no_op():
    reranked = [_served_base()]
    warning = _warning_pool_row()
    # El selector ve una copia con content DISTINTO al del pool real: la
    # attestación interna es válida, pero la revalidación id+content contra el
    # pool pagado debe rechazar la reserva.
    stale = dict(warning, content=warning["content"] + "\nRevisión posterior.")

    def stale_collector(query, _pool, served):
        selected, lane_trace = select_obligation_warning_reserve(
            query, [stale], served
        )
        assert [row["id"] for row in selected] == ["warning-pool"]
        return selected, lane_trace

    output, trace = _apply(
        _PROCEDURAL_QUERY,
        reranked,
        [warning],
        obligation_reserve_collector=stale_collector,
    )

    assert output is reranked
    assert trace["status"] == "no_append"
    assert trace["appended_ids"] == []


def test_hp009_family_generic_eol_control_does_not_reserve():
    reranked = [_served_base("zx-base", source_file="morley-zxe-manual.pdf")]
    pool = [
        _warning_pool_row("zx-warning", source_file="morley-zxe-manual.pdf")
    ]

    output, trace = _apply(_HP009_CONTROL_QUERY, reranked, pool)

    assert output is reranked
    assert trace["appended_ids"] == []
    assert trace["lanes"][-1]["status"] == "non_procedural_query"


def test_selector_reserves_at_most_one_warning_row():
    served = [_served_base()]
    pool = [_warning_pool_row("warning-a"), _warning_pool_row("warning-b")]

    selected, trace = select_obligation_warning_reserve(
        _PROCEDURAL_QUERY, pool, served
    )

    assert [row["id"] for row in selected] == ["warning-a"]
    assert trace["selected_ids"] == ["warning-a"]
    assert selected[0]["coverage_cards"][0]["quote"] == _WARNING_SENTENCE


def test_selector_skips_a_warning_chunk_already_served():
    warning = _warning_pool_row()
    served = [_served_base(), dict(warning)]

    selected, trace = select_obligation_warning_reserve(
        _PROCEDURAL_QUERY, [warning], served
    )

    assert selected == []
    assert trace["status"] == "no_warning_in_served_scope"


def test_oversized_warning_block_is_omitted_whole():
    oversized = {
        "id": "oversized",
        "content": "ADVERTENCIA: "
        + ("nunca debe puentearse el relé general de fallo del equipo " * 12),
        "source_file": _SERVED_SOURCE,
    }

    selected, trace = select_obligation_warning_reserve(
        _PROCEDURAL_QUERY, [oversized], [_served_base()]
    )

    assert selected == []
    assert trace["status"] == "no_warning_in_served_scope"
