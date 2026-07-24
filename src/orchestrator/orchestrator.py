"""Phase 0 turn orchestrator: single-hop passthrough over the current pipeline.

Transport-neutral (no telegram import). The only plan Phase 0 executes is
``SingleHopPlan``, which delegates to ``execute_rag_turn`` with byte-identical
arguments to the current callers (handler and gold harness). No new LLM call, no
persistent state — that is MT-0c/0d.

Retrieval/rerank/generation failures are intentionally NOT swallowed here: they
propagate to the caller's transport error boundary, exactly as the existing seam
(``execute_rag_turn``) documents. The synchronous hot path is isolated in an
executor by the *transport adapter* (MT-0d), not by this function.
"""

from __future__ import annotations

from .adapters import RagServingAdapters, execute_rag_turn
from .contracts import RetrievalResult, SingleHopPlan, TurnRequest, TurnResult


def plan_turn(request: TurnRequest) -> SingleHopPlan:
    """Phase 0 planner: always ``single_hop``. Clarify is deferred to Phase 1
    (deterministic standalone classifier + gated rewrite)."""
    return SingleHopPlan(
        query_for_retrieval=request.effective_retrieval_query,
        retrieval_top_k=request.retrieval_top_k,
        rerank_top_k=request.rerank_top_k,
        target_models=request.target_models,
        available_models=request.available_models,
    )


def run_turn(request: TurnRequest, adapters: RagServingAdapters) -> TurnResult:
    """Execute one turn through the current pipeline and shape the result.

    ``None`` target/available models are passed through as ``None``; an empty
    tuple is passed as ``[]`` — the exact distinction the two current callers
    rely on.
    """
    plan = plan_turn(request)

    pipeline = execute_rag_turn(
        query=request.query,
        query_for_retrieval=plan.query_for_retrieval,
        target_models=(
            None if plan.target_models is None else list(plan.target_models)
        ),
        available_models=(
            None if plan.available_models is None else list(plan.available_models)
        ),
        retrieval_top_k=plan.retrieval_top_k,
        rerank_top_k=plan.rerank_top_k,
        adapters=adapters,
    )

    generation = pipeline["generation"]
    retrieval = RetrievalResult(
        chunks=tuple(pipeline["chunks"]),
        coverage_trace=pipeline["coverage_trace"],
        retrieval_rows=pipeline["retrieval_rows"],
        reranked_rows=pipeline["reranked_rows"],
    )
    return TurnResult(
        answer=generation.get("answer", ""),
        diagrams=tuple(generation.get("diagrams") or ()),
        plan=plan,
        compute_status="answer_ready",
        retrieval=retrieval,
        generation=generation,
    )
