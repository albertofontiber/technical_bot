"""Transport-neutral contracts for one conversational turn (S276 assessment §3).

Frozen dataclasses only: no telegram, no I/O, no LLM. Phase 0 supports a single
executable plan — ``SingleHopPlan`` (passthrough to the current pipeline).
``ClarifyPlan`` is declared for the contract surface (Phase 1 deterministic
classifier) but ``run_turn`` never produces it in Phase 0.

The four contracts named by the assessment are ``TurnRequest``, ``TurnPlan``
(``single_hop`` | ``clarify``), ``RetrievalResult`` and ``TurnResult``. Extra
fields beyond the assessment are the minimum needed to drive the existing
``execute_rag_turn`` seam without changing its behavior; each is annotated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union


class PlanKind(str, Enum):
    SINGLE_HOP = "single_hop"
    CLARIFY = "clarify"


@dataclass(frozen=True, kw_only=True)
class TurnRequest:
    """Ingress unit of one turn (assessment §3: ``turn -> resolved context``).

    ``query`` and the routing identity describe what the user sent. The resolved
    retrieval inputs (``query_for_retrieval`` / ``target_models`` /
    ``available_models``) mirror the work ``_process_query`` already does before
    the pipeline (carry-forward, model detection, category lookup); in Phase 0
    the ingress adapter fills them so ``run_turn`` stays a pure passthrough.
    """

    # --- user-facing / routing identity ---
    query: str
    retrieval_top_k: int
    rerank_top_k: int
    channel: str = "telegram"
    conversation_id: str | None = None
    # Ingress dedup key (assessment: unique ``(channel, external_update_id)``).
    external_update_id: str | None = None
    source: str = "text"  # text | voice — mirrors _process_query
    transcription: str | None = None  # raw ASR preserved for audit

    # --- resolved retrieval inputs (Phase 0: filled by the ingress adapter) ---
    # None means "caller did not resolve a distinct retrieval query" -> use query.
    query_for_retrieval: str | None = None
    # None is passed through to the pipeline as None; an empty tuple is passed as
    # ``[]``. The distinction matters: the handler passes ``[]`` while the gold
    # harness passes ``None`` — both must be reproducible byte-for-byte.
    target_models: tuple[str, ...] | None = None
    available_models: tuple[str, ...] | None = None

    @property
    def effective_retrieval_query(self) -> str:
        """The retrieval query the pipeline should use (falls back to ``query``)."""
        return self.query if self.query_for_retrieval is None else self.query_for_retrieval


@dataclass(frozen=True, kw_only=True)
class SingleHopPlan:
    """The only plan Phase 0 executes: retrieve -> rerank -> coverage -> generate
    once, delegating to the current pipeline. Carries the resolved inputs that
    ``run_turn`` hands to ``execute_rag_turn``."""

    query_for_retrieval: str
    retrieval_top_k: int
    rerank_top_k: int
    target_models: tuple[str, ...] | None = None
    available_models: tuple[str, ...] | None = None
    kind: PlanKind = field(default=PlanKind.SINGLE_HOP, init=False)


@dataclass(frozen=True, kw_only=True)
class ClarifyPlan:
    """Declared for the contract surface; not produced by ``run_turn`` in Phase 0.
    Phase 1 emits it from the deterministic standalone classifier when a turn is
    ambiguous (variant/product divergence)."""

    reason: str
    question: str
    kind: PlanKind = field(default=PlanKind.CLARIFY, init=False)


TurnPlan = Union[SingleHopPlan, ClarifyPlan]


@dataclass(frozen=True, kw_only=True)
class RetrievalResult:
    """Outcome of retrieval + rerank + governed coverage for the turn.

    ``chunks`` are the served chunks (the exact context the writer sees).
    ``coverage_trace`` is the receipt already produced by ``execute_rag_turn``.
    """

    chunks: tuple[dict[str, Any], ...]
    coverage_trace: dict[str, Any]
    retrieval_rows: int
    reranked_rows: int


@dataclass(frozen=True, kw_only=True)
class TurnResult:
    """Final outcome of the turn.

    ``compute_status`` uses the adjudicated ``convo.turn_runs`` vocabulary
    (``pending`` | ``running`` | ``answer_ready`` | ``delivered`` | ``failed``,
    MT-0b DDL). Phase 0 returns ``answer_ready`` on success; the
    ``pending -> running`` lifecycle and its persistence are MT-0c/0d, not this
    lane. ``generation`` keeps the raw writer
    dict (stop_reason/tokens/traces) so downstream persistence never has to
    reconstruct it.
    """

    answer: str
    diagrams: tuple[dict[str, Any], ...]
    plan: TurnPlan
    compute_status: str
    retrieval: RetrievalResult | None = None
    generation: dict[str, Any] | None = None
