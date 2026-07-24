"""Composition seam for the orchestrator over the existing production pipeline.

``RagServingAdapters`` and ``execute_rag_turn`` already live in
``src.rag.serving_pipeline`` — the single seam the Telegram handler and the gold
harness both cross. The orchestrator does NOT introduce a parallel seam; it
re-exports that one and adds:

  * ``from_production()`` — wires the real pipeline functions (today each call
    site constructs the adapter inline; centralizing it removes that
    duplication without changing behavior);
  * ``replay_adapters()`` — deterministic stub/replay adapters for the parity
    instrument and unit tests (frozen retrieval, identity rerank, no-op shadow,
    caller-supplied ``generate`` and coverage fetchers).

No telegram import lives in this package. The heavy pipeline imports inside
``from_production`` are local so importing the package stays light.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from ..rag.serving_pipeline import RagServingAdapters, execute_rag_turn

__all__ = [
    "RagServingAdapters",
    "execute_rag_turn",
    "from_production",
    "replay_adapters",
]


def from_production() -> RagServingAdapters:
    """Wire the real pipeline functions (retrieval -> shadow -> generation).

    Mirrors the inline construction in ``telegram_bot._process_query`` exactly, so
    a turn driven through the orchestrator is byte-identical to the current
    handler path.
    """
    from ..rag.retriever import retrieve_chunks
    from ..rag.reranker import rerank
    from ..rag.generator import generate_answer
    from ..rag.structural_neighbor_shadow import observe_structural_neighbor_shadow

    return RagServingAdapters(
        retrieve=retrieve_chunks,
        rerank=rerank,
        observe_structural_shadow=observe_structural_neighbor_shadow,
        generate=generate_answer,
    )


def replay_adapters(
    *,
    retrieved: Sequence[dict[str, Any]],
    generate: Callable[..., dict[str, Any]],
    rerank: Callable[..., list[dict[str, Any]]] | None = None,
    observe_structural_shadow: Callable[..., None] | None = None,
    structural_fetcher: Callable[..., tuple[list, list, dict]] | None = None,
    document_local_fetcher: Callable[..., tuple[list, list, dict]] | None = None,
) -> RagServingAdapters:
    """Deterministic adapters for offline parity/unit tests.

    ``retrieve`` replays a frozen copy of ``retrieved`` (fresh dicts per call so a
    downstream mutation cannot leak between routes). ``rerank`` defaults to
    identity (order preserved). ``observe_structural_shadow`` defaults to a no-op.
    The coverage fetchers default to empty results so the real coverage logic
    runs deterministically without a database. ``generate`` is always supplied by
    the caller (the real ``generate_answer`` for prompt-byte capture, or a
    recording stub).
    """
    frozen = [dict(row) for row in retrieved]

    def _retrieve(_query, **_kwargs):
        return [dict(row) for row in frozen]

    def _identity_rerank(_query, chunks, **_kwargs):
        return list(chunks)

    def _empty_fetcher(*_args, **_kwargs):
        return [], [], {}

    return RagServingAdapters(
        retrieve=_retrieve,
        rerank=rerank or _identity_rerank,
        observe_structural_shadow=observe_structural_shadow or (lambda *_a, **_k: None),
        generate=generate,
        structural_fetcher=structural_fetcher or _empty_fetcher,
        document_local_fetcher=document_local_fetcher or _empty_fetcher,
    )
