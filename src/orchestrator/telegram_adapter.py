"""Telegram ingress adapter: build a transport-neutral ``TurnRequest`` (MT-0d).

Pure function — no telegram import, no I/O, no config side effects. It maps the
values ``telegram_bot._process_query`` has ALREADY resolved (carry-forward
retrieval query, detected/available models, routing identity) into the frozen
``TurnRequest`` the orchestrator consumes.

The single load-bearing subtlety is the ``None`` vs empty-list distinction on the
model tuples: ``run_turn`` maps ``None -> None`` and ``() -> []`` to reproduce the
two current callers byte-for-byte (the handler passes ``[]`` for "no models
detected", the gold harness passes ``None``). ``_to_tuple`` preserves it: it never
collapses an empty list to ``None``.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..config import RERANK_TOP_K, RETRIEVAL_TOP_K
from .contracts import TurnRequest


def _to_tuple(models: Sequence[str] | None) -> tuple[str, ...] | None:
    # None (caller resolved nothing) stays None; an empty list stays an EMPTY
    # tuple (-> [] downstream), never collapsed to None.
    return None if models is None else tuple(models)


def build_turn_request(
    *,
    query: str,
    query_for_retrieval: str,
    target_models: Sequence[str] | None,
    available_models: Sequence[str] | None,
    update_id: int | str,
    chat_id: int | str,
    source: str = "text",
    transcription: str | None = None,
    retrieval_top_k: int = RETRIEVAL_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
) -> TurnRequest:
    """Construct the ``TurnRequest`` for one Telegram turn from resolved handler
    values. ``update_id``/``chat_id`` become the effectively-once dedup + chat
    keys (stringified). ``query_for_retrieval`` is the handler's already-resolved
    retrieval query (equal to ``query`` when nothing was carried forward)."""
    return TurnRequest(
        query=query,
        query_for_retrieval=query_for_retrieval,
        target_models=_to_tuple(target_models),
        available_models=_to_tuple(available_models),
        retrieval_top_k=retrieval_top_k,
        rerank_top_k=rerank_top_k,
        channel="telegram",
        external_update_id=str(update_id),
        conversation_id=str(chat_id),
        source=source,
        transcription=transcription,
    )
