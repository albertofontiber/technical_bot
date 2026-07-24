"""Contract shape tests for the transport-neutral turn orchestrator (MT-0a).

Pure, $0, deterministic: frozen-ness, discriminated plan variants, and the
resolved-retrieval-query fallback that ``run_turn`` relies on.
"""

import dataclasses

import pytest

from src.orchestrator.contracts import (
    ClarifyPlan,
    PlanKind,
    RetrievalResult,
    SingleHopPlan,
    TurnRequest,
    TurnResult,
)


def test_turn_request_defaults_are_stateless_and_telegram_channel():
    req = TurnRequest(query="¿tensión del lazo?", retrieval_top_k=50, rerank_top_k=5)
    assert req.channel == "telegram"
    assert req.conversation_id is None
    assert req.external_update_id is None
    assert req.source == "text"
    assert req.target_models is None
    assert req.available_models is None


def test_effective_retrieval_query_falls_back_to_query_when_unset():
    req = TurnRequest(query="Q", retrieval_top_k=50, rerank_top_k=5)
    assert req.effective_retrieval_query == "Q"


def test_effective_retrieval_query_uses_resolved_value_when_present():
    req = TurnRequest(
        query="¿y la corriente?",
        retrieval_top_k=50,
        rerank_top_k=5,
        query_for_retrieval="¿y la corriente? (contexto: CAD-250)",
    )
    assert req.effective_retrieval_query == "¿y la corriente? (contexto: CAD-250)"


def test_turn_request_is_frozen():
    req = TurnRequest(query="Q", retrieval_top_k=50, rerank_top_k=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.query = "otra"  # type: ignore[misc]


def test_single_hop_plan_kind_is_fixed_and_not_settable():
    plan = SingleHopPlan(query_for_retrieval="Q", retrieval_top_k=50, rerank_top_k=5)
    assert plan.kind is PlanKind.SINGLE_HOP
    # `kind` is init=False, so it is not a constructor argument.
    with pytest.raises(TypeError):
        SingleHopPlan(  # type: ignore[call-arg]
            query_for_retrieval="Q",
            retrieval_top_k=50,
            rerank_top_k=5,
            kind=PlanKind.CLARIFY,
        )


def test_clarify_plan_shape():
    plan = ClarifyPlan(reason="variant_divergence", question="¿ZX2e o ZX5e?")
    assert plan.kind is PlanKind.CLARIFY
    assert plan.reason == "variant_divergence"
    assert plan.question == "¿ZX2e o ZX5e?"
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.question = "otra"  # type: ignore[misc]


def test_plan_kind_string_values_are_stable():
    # The wire/trace values MT-0d persists must not drift.
    assert PlanKind.SINGLE_HOP.value == "single_hop"
    assert PlanKind.CLARIFY.value == "clarify"


def test_retrieval_result_and_turn_result_carry_the_expected_fields():
    retrieval = RetrievalResult(
        chunks=({"id": "a"},),
        coverage_trace={"status": "no_append"},
        retrieval_rows=50,
        reranked_rows=5,
    )
    plan = SingleHopPlan(query_for_retrieval="Q", retrieval_top_k=50, rerank_top_k=5)
    result = TurnResult(
        answer="respuesta",
        diagrams=(),
        plan=plan,
        compute_status="answer_ready",
        retrieval=retrieval,
        generation={"answer": "respuesta", "diagrams": []},
    )
    assert result.compute_status == "answer_ready"
    assert result.retrieval is retrieval
    assert result.plan.kind is PlanKind.SINGLE_HOP
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.answer = "otra"  # type: ignore[misc]
