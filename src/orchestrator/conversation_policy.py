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
# (s316g, rompe el ciclo impl->turn_plan->impl) Vocabulario de dominio compartido por
# la guardia del plan (turn_plan) y la rama del lever (impl): marcas cuyo NOMBRE es
# vocabulario corriente del sector (FUEGO es un fabricante REAL) y el lexicón del test
# de colisión. Viven en la capa INTERFAZ — como NON_PRODUCT_CODES — para que ambos
# consumidores importen hacia abajo y ninguno del otro.
_MARCAS_AMBIGUAS: frozenset[str] = frozenset({"fuego"})
_VOCABULARIO_DOMINIO: frozenset[str] = frozenset({
    "fuego", "incendio", "incendios", "alarma", "alarmas", "central", "centrales",
    "detector", "detectores", "sirena", "sirenas", "pulsador", "pulsadores", "zona",
    "zonas", "lazo", "bucle", "panel", "humo", "temperatura", "extincion", "extinción",
    "evacuacion", "evacuación", "bateria", "batería", "aviso", "avisador",
})

NON_PRODUCT_CODES: frozenset[str] = frozenset(
    {"RS-485", "RS485", "RS-232", "RS232", "IP54", "IP55", "IP66", "EN-54", "EN54"}
)


# (s331 §3.D) Procedencias válidas de la identidad del turno — POR COMPONENTE
# (Sol-4 r-v4: una sola procedencia no representa el estado mixto «canónico
# arrastrado + mención nueva»; Sol-3 r-v5: `pending_derived` = la familia procede
# del pending confirmado sin binding, ni resuelta este turno ni arrastrada).
MODELS_PROVENANCE: tuple[str, ...] = (
    "resolved_this_turn", "carried", "pending_derived", "none",
)
MENTION_PROVENANCE: tuple[str, ...] = ("this_turn", "pending_carried", "none")
_PRESENCE_STATES: tuple[str, ...] = ("vigente", "stale", "cold")


@dataclass(frozen=True, kw_only=True)
class TurnIdentity:
    """(s331 §3.D) Identidad ESTRUCTURADA del turno — el canal por el que la
    resolución gobernada y la mención no-resuelta viajan hasta generación SIN
    pasar por el texto de la query (spoofing cerrado, Fable-3 r-v1/Sol-3 r-v2).

    FRONTERA DE PRIVACIDAD (Sol-2 r-v5): ``mention`` es texto del usuario y vive
    SOLO in-process — JAMÁS se serializa a trace ni a log estructurado (el trace
    admite solo booleanos/contadores/tokens controlados; la vista DERIVADA que sí
    se persiste son los enums/booleanos de esta clase, nunca el string). El texto
    del usuario ya vive en ``query``/``response`` bajo su retención RGPD.

    Un turno sin modelos NI mención no construye TurnIdentity: usa ``None``
    (invariante «no se construye vacío», v6 §3.D)."""

    resolved_models: tuple[str, ...] = ()
    models_provenance: str = "none"
    mention: str | None = None
    mention_provenance: str = "none"
    presence: str | None = None   # vigente|stale|cold — solo si la resolución A corrió
    route_cut: bool = False       # la puerta 2 (corte-de-ruta) disparó este turno

    def __post_init__(self) -> None:
        if self.models_provenance not in MODELS_PROVENANCE:
            raise ValueError(f"models_provenance inválida: {self.models_provenance!r}")
        if self.mention_provenance not in MENTION_PROVENANCE:
            raise ValueError(f"mention_provenance inválida: {self.mention_provenance!r}")
        if self.presence is not None and self.presence not in _PRESENCE_STATES:
            raise ValueError(f"presence inválida: {self.presence!r}")
        if (self.mention is None) != (self.mention_provenance == "none"):
            raise ValueError("mention y mention_provenance deben ir juntas "
                             "(mention=None ⇔ provenance='none')")
        if bool(self.resolved_models) != (self.models_provenance != "none"):
            raise ValueError("resolved_models y models_provenance deben ir juntas "
                             "(vacía ⇔ provenance='none')")
        if self.route_cut and self.mention_provenance != "this_turn":
            raise ValueError("route_cut=True exige mention_provenance='this_turn' "
                             "(solo una mención de ESTE turno corta ruta)")
        if self.models_provenance == "none" and self.mention_provenance == "none":
            raise ValueError("TurnIdentity vacía: usa None en su lugar "
                             "(invariante v6 §3.D)")


@dataclass(frozen=True, kw_only=True)
class WorkingState:
    """Durable per-conversation working state (design §6/§8).

    Since s316f (fase B, DEC-202) this is the single conversational state for BOTH
    regimes: the legacy keys (``last_detected_models``/``last_query_time``) are
    RETIRED — the stub regime reads/writes this state via ``transicion_basica``.
    ``last_turn_at`` drives the 1-hour window; an empty / expired state means
    "no context to carry".
    """

    last_target_models: tuple[str, ...] = ()
    last_query: str | None = None
    last_answer_excerpt: str | None = None
    last_turn_at: datetime | None = None
    available_models: tuple[str, ...] | None = None
    # (s331 §3.C.1) Mención con forma de modelo que la resolución NO pudo bindear y
    # que provocó un CLARIFY dirigido (puerta 2). Lifecycle EXPLÍCITO (B3 §11 v6):
    # SET solo en la ruta CLARIFY-de-mención (copia del estado prior con SOLO estos
    # dos campos añadidos — el resto INTACTO, incluida la no-renovación de
    # ``last_turn_at``: el invariante anti-resurrección S99 se preserva); CONSUME o
    # CLEAR explícitos en TODAS las rutas de salida del turno siguiente (answer,
    # negación→clarify, cambio-de-tema→clarify/decline); EXPIRE con la ventana de
    # 1 h sobre ``pending_at``. Una mención caducada jamás corta un carry-forward.
    pending_mention: str | None = None
    pending_at: datetime | None = None

    @property
    def is_empty(self) -> bool:
        return not self.last_target_models and self.last_query is None

    def pending_within_window(self, now: datetime, window_seconds: int) -> bool:
        """True si hay mención pendiente y su ventana propia sigue viva."""
        if self.pending_mention is None or self.pending_at is None:
            return False
        return (now - self.pending_at).total_seconds() < window_seconds

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
    # (s331 §3.D) Identidad estructurada del turno para generación/plantillas/trace.
    # None = sin identidad (o levers apagados) ⇒ conducta de hoy byte-idéntica.
    turn_identity: "TurnIdentity | None" = None

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

# (s316g, DEC-203) El clasificador de intencion del lever INTENT_LLM: mismo patron que
# RewriteFn (la politica no hace I/O; el transporte inyecta; None = diferir = conducta
# de hoy). Devuelve "compat" | "switch" | None; el contrato del parser vive en
# orchestrator/intent_llm.py y todo valor fuera de el se trata como None.
IntentFn = Callable[[str, "WorkingState"], str | None]


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
        intent: "IntentFn | None" = None,
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
        intent: "IntentFn | None" = None,
    ) -> TurnResolution:
        raise PolicyNotImplemented(
            "ConversationPolicy is not implemented yet (MT-1a). MT-1b ships the "
            "interface + eval as a spec; run --contract again once MT-1a replaces "
            "default_policy() with the real classifier/rewrite."
        )


# Composition seam: the orchestrator + eval obtain the active policy here. MT-1a
# fills in the concrete policy (``conversation_policy_impl``) WITHOUT touching the
# dataclasses/enum/invariants above. s319 PR-C (DEC-211): la política REAL es el
# DEFAULT (= producción; graduación tras el asentamiento del ship); el stub queda
# para el instrumento MT y los contratos congelados vía CONVERSATION_POLICY=stub
# EXPLÍCITO. Enum estricto impl|stub (un typo revienta, no degrada en silencio).
# The import is lazy to avoid the impl<->interface import cycle.
def default_policy() -> ConversationPolicy:
    """Return the active conversational policy: the deterministic MT-1a policy
    (default, = producción desde DEC-211), or the frozen-contract stub when
    ``CONVERSATION_POLICY=stub`` is set explicitly."""
    from .conversation_policy_impl import (
        DeterministicConversationPolicy,
        conversation_policy_active,
    )

    if conversation_policy_active():
        return DeterministicConversationPolicy()
    return StubConversationPolicy()


__all__ = [
    "PolicyRoute",
    "ZERO_COST_ROUTES",
    "NON_PRODUCT_CODES",
    "MODELS_PROVENANCE",
    "MENTION_PROVENANCE",
    "TurnIdentity",
    "WorkingState",
    "TurnResolution",
    "RewriteFn",
    "IntentFn",
    "ConversationPolicy",
    "PolicyNotImplemented",
    "StubConversationPolicy",
    "default_policy",
]
