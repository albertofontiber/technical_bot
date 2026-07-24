"""Behavioral tests for the Phase 0 orchestrator ``run_turn`` passthrough.

These use recording stub adapters (no LLM, no DB) to assert that ``run_turn``
composes ``execute_rag_turn`` faithfully: the served context reaches the result,
the plan is single_hop, and the None/empty model distinction the two current
callers rely on is preserved byte-for-byte.
"""

import os

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.orchestrator import PlanKind, TurnRequest, replay_adapters, run_turn


_FIXTURE = [
    {"id": "a", "content": "A", "similarity": 0.9},
    {"id": "b", "content": "B", "similarity": 0.8},
]


def _recording_generate(record):
    def generate(query, chunks, *, available_models=None):
        record["query"] = query
        record["chunks"] = chunks
        record["available_models"] = available_models
        return {"answer": "ok", "diagrams": [{"url": "u"}]}

    return generate


def _recording_rerank(record):
    def rerank(query, chunks, *, top_k=None, target_models=None):
        record["rerank_target_models"] = target_models
        record["rerank_top_k"] = top_k
        return list(chunks)

    return rerank


def test_run_turn_passthrough_returns_answer_diagrams_and_served_context():
    record = {}
    adapters = replay_adapters(
        retrieved=_FIXTURE, generate=_recording_generate(record)
    )
    req = TurnRequest(query="¿tensión?", retrieval_top_k=50, rerank_top_k=2)

    result = run_turn(req, adapters)

    assert result.answer == "ok"
    assert result.diagrams == ({"url": "u"},)
    assert result.compute_status == "answer_ready"
    assert result.plan.kind is PlanKind.SINGLE_HOP
    # The writer saw exactly the served context, and the result echoes it.
    assert [c["id"] for c in record["chunks"]] == ["a", "b"]
    assert result.retrieval is not None
    assert [c["id"] for c in result.retrieval.chunks] == ["a", "b"]
    assert result.retrieval.retrieval_rows == 2
    assert result.retrieval.reranked_rows == 2


def test_run_turn_uses_query_for_generation_and_effective_query_for_retrieval():
    gen_record = {}
    rr_record = {}
    adapters = replay_adapters(
        retrieved=_FIXTURE,
        generate=_recording_generate(gen_record),
        rerank=_recording_rerank(rr_record),
    )
    req = TurnRequest(
        query="¿y la corriente?",
        retrieval_top_k=50,
        rerank_top_k=5,
        query_for_retrieval="¿y la corriente? (contexto: CAD-250)",
    )

    result = run_turn(req, adapters)

    # rerank + generation see the raw user query; retrieval used the resolved one.
    assert gen_record["query"] == "¿y la corriente?"
    assert result.plan.query_for_retrieval == "¿y la corriente? (contexto: CAD-250)"
    assert rr_record["rerank_top_k"] == 5


def test_run_turn_maps_none_models_to_none():
    rr_record = {}
    gen_record = {}
    adapters = replay_adapters(
        retrieved=_FIXTURE,
        generate=_recording_generate(gen_record),
        rerank=_recording_rerank(rr_record),
    )
    req = TurnRequest(query="Q", retrieval_top_k=50, rerank_top_k=5)  # target None

    run_turn(req, adapters)

    assert rr_record["rerank_target_models"] is None
    assert gen_record["available_models"] is None


def test_run_turn_maps_empty_tuple_models_to_empty_list():
    # The handler passes [] (not None) when no model was detected; a caller that
    # sets an empty tuple must reproduce that exact [], not collapse it to None.
    rr_record = {}
    gen_record = {}
    adapters = replay_adapters(
        retrieved=_FIXTURE,
        generate=_recording_generate(gen_record),
        rerank=_recording_rerank(rr_record),
    )
    req = TurnRequest(
        query="Q",
        retrieval_top_k=50,
        rerank_top_k=5,
        target_models=(),
        available_models=(),
    )

    run_turn(req, adapters)

    assert rr_record["rerank_target_models"] == []
    assert gen_record["available_models"] == []


def test_run_turn_passes_populated_models_through():
    rr_record = {}
    gen_record = {}
    adapters = replay_adapters(
        retrieved=_FIXTURE,
        generate=_recording_generate(gen_record),
        rerank=_recording_rerank(rr_record),
    )
    req = TurnRequest(
        query="Q",
        retrieval_top_k=50,
        rerank_top_k=5,
        target_models=("CAD-250",),
        available_models=("CAD-250", "MAD-461"),
    )

    run_turn(req, adapters)

    assert rr_record["rerank_target_models"] == ["CAD-250"]
    assert gen_record["available_models"] == ["CAD-250", "MAD-461"]
