"""Conversational turn policy — the interface MT-1a implements (S281 / Phase 1).

This module is the CONTRACT SURFACE the multi-turn eval (MT-1b) pins and the
Phase-1 classifier/rewrite lane (MT-1a) fills in. It ships here as a **stub** so
that:

  * the eval (``scripts/test_multiturn_vs_gold.py``) can import a stable
    interface and DETECT the not-yet-implemented state ($0, no LLM), and
  * MT-1a has a frozen shape to build against (it replaces ``default_policy()``
    and adds a concrete class — it does NOT change the dataclasses/enum).

WHY A POLICY LAYER (assessment §3.1 + design v2 §5/§8)
-----------------------------------------------------
Phase 0 (``run_turn``) is a stateless single-hop passthrough. Phase 1 adds the
one conversational capability that pays for technicians: resolving a follow-up
turn against durable working state BEFORE retrieval. The resolution is a
**deterministic router first** (§5: pronouns/deictics/ellipsis + absence of an
explicit product); an economical **source-bound rewrite** is invoked ONLY on the
narrow slice the router marks non-resolvable deterministically. Simple
within-window follow-ups stay **$0** via the router + working state (§8, the
carry-forward-1h migration) — never an LLM call.

THE ROUTES (what the orchestrator does with each)
-------------------------------------------------
``STANDALONE``    the turn is self-contained (explicit product, or no dependency
                  signal): use ``query`` as the retrieval query unchanged. $0.
``CARRY_FORWARD`` dependent, but resolvable deterministically from working state
                  (re-attach the last product to the retrieval query, query text
                  preserved VERBATIM so technical codes never mutate). $0 — this
                  is the migrated carry-forward-1h path (design §8).
``REWRITE``       dependent with anaphora the re-attach cannot resolve: needs the
                  economical source-bound rewrite (1 call). ``requires_llm_rewrite``
                  is True. In the $0 contract mode the rewriter is not injected,
                  so ``rewritten_query`` stays None and the route is asserted
                  without paying; ``--e2e`` supplies the real rewriter + judge.
``CLARIFY``       the answer would DIVERGE across the candidate products/variants
                  and the turn does not disambiguate (s79/s80: clarify ONLY on
                  real divergence — an invariant answer is ``answer``, never a
                  reflexive clarify). $0.
``DECLINE``       the turn is outside the served domain (S99 domain gate). $0.

HARD INVARIANTS (the eval checks these; MT-1a must preserve them)
----------------------------------------------------------------
  * A route other than ``REWRITE`` NEVER sets ``requires_llm_rewrite`` — the $0
    guarantee for standalone + carry-forward + clarify + decline.
  * ``CARRY_FORWARD`` preserves the raw ``query`` inside ``query_for_retrieval``
    byte-for-byte (a model hint may be APPENDED, never a substitution) so
    technical codes survive intact (the S99b regression: RS-485/IP54/6,8 kΩ must
    never be rewritten away).
  * An EXPLICIT product in the turn WINS over working state (design §5): the
    resolved ``target_models`` are the turn's, and the stale product does not
    leak. Self-correction ("me refería a la X") REPLACES, never unions.
  * ``extract_product_models`` (the existing detector) is composed, not
    duplicated: the caller passes its output as ``turn_models``. It has KNOWN
    false positives on bus/protocol codes (``extract_product_models('RS485')``
    -> ``['RS-485']``); the product-change gate MUST NOT treat such a code as a
    product change — see ``NON_PRODUCT_CODES`` and the eval's ``codigos_tecnicos``
    class. This is exactly the trap that sank the S99 rewrite v2.

NOTHING HERE PERFORMS I/O OR AN LLM CALL. The rewriter is an INJECTED callable
(``RewriteFn``); the policy decides WHEN to call it, never how it is built.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Protocol, runtime_checkable


class PolicyRoute(str, Enum):
    """How the orchestrator should treat a resolved turn (see module docstring)."""

    STANDALONE = "standalone"
    CARRY_FORWARD = "carry_forward"
    REWRITE = "rewrite"
    CLARIFY = "clarify"
    DECLINE = "decline"


# The $0 routes: none of them may require the economical rewriter.
ZERO_COST_ROUTES: frozenset[PolicyRoute] = frozenset(
    {
        PolicyRoute.STANDALONE,
        PolicyRoute.CARRY_FORWARD,
        PolicyRoute.CLARIFY,
        PolicyRoute.DECLINE,
    }
)


# Bus/protocol/spec tokens the deterministic detector (``extract_product_models``)
# emits as if they were product models but which MUST NOT drive a product change.
# Seed list, NOT exhaustive — the real guard belongs in the governed catalog
# (DEC-069/2-etapa entity linking). Declared here so the eval can pin the
# regression and MT-1a has a concrete starting denylist.
NON_PRODUCT_CODES: frozenset[str] = frozenset(
    {"RS-485", "RS485", "RS-232", "RS232", "IP54", "IP55", "IP66", "EN-54", "EN54"}
)


@dataclass(frozen=True, kw_only=True)
class WorkingState:
    """Durable per-conversation working state (design §6/§8).

    In Phase 1 this is the single source of truth that REPLACES the in-memory
    ``context.user_data['last_detected_models']`` carry-forward
    (``telegram_bot`` step 1b). ``last_turn_at`` drives the 1-hour window; an
    empty / expired state means "no context to carry".
    """

    last_target_models: tuple[str, ...] = ()
    last_query: str | None = None
    last_answer_excerpt: str | None = None
    last_turn_at: datetime | None = None
    available_models: tuple[str, ...] | None = None

    @property
    def is_empty(self) -> bool:
        return not self.last_target_models and self.last_query is None

    def within_window(self, now: datetime, window_seconds: int) -> bool:
        """True when the last turn is recent enough to carry context forward."""
        if self.last_turn_at is None:
            return False
        return (now - self.last_turn_at).total_seconds() < window_seconds


@dataclass(frozen=True, kw_only=True)
class TurnResolution:
    """The policy's verdict for one turn: route + resolved retrieval inputs.

    ``query_for_retrieval`` is what the orchestrator hands to retrieval (it fills
    ``TurnRequest.query_for_retrieval``). ``target_models`` / ``available_models``
    are the resolved routing identity. ``rationale`` is a deterministic,
    LLM-free trace string for the eval/audit (never shown to the user).
    """

    route: PolicyRoute
    query_for_retrieval: str
    target_models: tuple[str, ...] | None = None
    available_models: tuple[str, ...] | None = None
    requires_llm_rewrite: bool = False
    rewritten_query: str | None = None
    clarify_question: str | None = None
    decline_reason: str | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        # Enforce the $0 invariant at construction so a mis-built resolution
        # cannot silently claim a free route while flagging a paid rewrite.
        if self.route in ZERO_COST_ROUTES and self.requires_llm_rewrite:
            raise ValueError(
                f"route {self.route.value} is $0 but requires_llm_rewrite=True; "
                "only REWRITE may require the economical rewriter"
            )
        if self.route is PolicyRoute.REWRITE and not self.requires_llm_rewrite:
            raise ValueError("REWRITE route must set requires_llm_rewrite=True")
        if self.route is PolicyRoute.CLARIFY and not self.clarify_question:
            raise ValueError("CLARIFY route must carry a clarify_question")
        if self.route is PolicyRoute.DECLINE and not self.decline_reason:
            raise ValueError("DECLINE route must carry a decline_reason")


# The economical source-bound rewriter MT-1a wires (S99 pattern). Takes the raw
# turn + working state, returns a STANDALONE retrieval query. Injected, never
# constructed inside the policy. In $0 contract mode it is None (not called).
RewriteFn = Callable[[str, WorkingState], str]


class PolicyNotImplemented(NotImplementedError):
    """Raised by the stub so the eval reports PENDING instead of crashing."""


@runtime_checkable
class ConversationPolicy(Protocol):
    """The interface MT-1a implements. One method, pure (no I/O beyond the
    optional injected ``rewrite`` callable)."""

    #: MT-1a's real class sets this False; the eval keys "not implemented" on it.
    IS_STUB: bool

    def resolve(
        self,
        *,
        query: str,
        turn_models: Sequence[str],
        available_models: Sequence[str] | None,
        working_state: WorkingState,
        now: datetime,
        rewrite: RewriteFn | None = None,
    ) -> TurnResolution:
        """Resolve one turn into a route + retrieval inputs.

        ``turn_models`` is ``extract_product_models(query)`` (composed, not
        re-derived). ``available_models`` is the category-detected option set
        (for CLARIFY), or None. ``rewrite`` is the economical rewriter, supplied
        only in ``--e2e``; when None the policy must NOT fabricate a rewrite — it
        returns ``route=REWRITE`` with ``rewritten_query=None`` and defers.
        """
        ...


@dataclass(frozen=True)
class StubConversationPolicy:
    """Placeholder until MT-1a lands. Every ``resolve`` raises so the eval can
    report PENDING (the suite stays green: the eval is a ready spec, not a
    failing gate, before the implementation exists)."""

    IS_STUB: bool = field(default=True, init=False)

    def resolve(
        self,
        *,
        query: str,
        turn_models: Sequence[str],
        available_models: Sequence[str] | None,
        working_state: WorkingState,
        now: datetime,
        rewrite: RewriteFn | None = None,
    ) -> TurnResolution:
        raise PolicyNotImplemented(
            "ConversationPolicy is not implemented yet (MT-1a). MT-1b ships the "
            "interface + eval as a spec; run --contract again once MT-1a replaces "
            "default_policy() with the real classifier/rewrite."
        )


# Composition seam: the orchestrator + eval obtain the active policy here. MT-1a
# replaces the body to return its concrete policy (keeping the signature).
def default_policy() -> ConversationPolicy:
    """Return the active conversational policy. Phase-1-pending: the stub."""
    return StubConversationPolicy()


__all__ = [
    "PolicyRoute",
    "ZERO_COST_ROUTES",
    "NON_PRODUCT_CODES",
    "WorkingState",
    "TurnResolution",
    "RewriteFn",
    "ConversationPolicy",
    "PolicyNotImplemented",
    "StubConversationPolicy",
    "default_policy",
]
