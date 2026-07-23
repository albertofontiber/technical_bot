"""Deterministic conversational policy — MT-1a (S281 / Phase 1).

This is the concrete ``ConversationPolicy`` the frozen interface
(``conversation_policy.py``) declares. It is a **deterministic router in cascade**
with a traceable rationale per decision; the economical rewriter
(``rewriter.py``) is invoked ONLY on the narrow anaphora slice the router cannot
resolve by re-attaching the last product. Everything else is $0.

THE CASCADE (order matters — first match wins):

  A. EXPLICIT PRODUCT in this turn (``turn_models`` minus ``NON_PRODUCT_CODES``)
     -> STANDALONE. The explicit product WINS over working state (design §5); a
     self-correction ("me refería a la X") therefore REPLACES the state, never
     unions it.
  B. NEW BRAND named but no in-corpus model resolved (regex missed it / out of
     served corpus, e.g. "la Bosch Avenar FPA-1200") -> STANDALONE, target=()
     (drop the stale product; downstream admits). This is the catalog-aware
     brand gate MT-1a owes (vara §7.3, DEC-069 dependency).
  C. OUT-OF-DOMAIN lexicon (conservative gas-outside-fire gate, S99) -> DECLINE.
     Runs AFTER A/B so an in-corpus gas *detector* (DGD-600) is never declined.
  D. IN-WINDOW STATE present (product-less follow-up within 1h) -> continuation:
       E. family umbrella + question on the family's DIVERGENT axis (real
          divergence, catalog/GT-anchored) and NOT an invariant attribute
          -> CLARIFY (s79/s80: clarify ONLY on real divergence; an invariant
          answer is ``answer``, never a reflexive clarify).
       F. content anaphora ("ese aviso" / "esa entrada") the re-attach cannot
          resolve -> REWRITE (requires_llm_rewrite=True). With ``rewrite=None``
          (contract mode) it DEFERS (rewritten_query=None, no fabrication). With
          a rewriter injected it calls it; a fail-closed rewrite (None) falls
          back to carry_forward ($-spent, safe).
       G. else -> CARRY_FORWARD ($0): the raw query is preserved VERBATIM and a
          model hint is APPENDED (never substituted).
  H. NO in-window state (empty or expired) + a dependency signal (dangling
     pronoun/ellipsis, e.g. the 70-min "¿y cuál es su tensión?") -> CLARIFY.
  I. NO in-window state + genuinely self-contained (no dependency signal)
     -> STANDALONE (let retrieval + generator handle it; avoids clarify-indebido).

The composition seam ``resolve_conversational_turn`` wires
``extract_product_models`` + this policy into ``(TurnResolution, new WorkingState)``
— what the bot activation (MT-0d, orchestrator + Alberto) will drive. This module
performs NO I/O and NO LLM call itself; the rewriter is the injected callable.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from .conversation_policy import (
    NON_PRODUCT_CODES,
    PolicyRoute,
    RewriteFn,
    TurnResolution,
    WorkingState,
)

WINDOW_SECONDS = 3600  # carry-forward-1h (telegram_bot SESSION_TIMEOUT); design §8


# ---------------------------------------------------------------------------
# Seed tables (data-anchored; the durable versions read the governed catalog,
# DEC-069 2-stage entity linking — declared dependencies, not invented here)
# ---------------------------------------------------------------------------
# Brand/manufacturer name tokens (served + a seed of common unserved PCI brands).
# When a turn names a brand but ``extract_product_models`` resolved no in-corpus
# model, the turn is introducing a NEW product (possibly out of corpus) -> it is
# a product switch, not a follow-up. Anchored to config/manufacturers + the M&A
# 30+-brand universe; extensible. (mt05b Bosch FPA-1200 is the pinned case.)
BRAND_TOKENS: frozenset[str] = frozenset(
    {
        # served
        "detnov", "notifier", "morley", "honeywell",
        # common unserved fire-alarm brands (seed)
        "bosch", "siemens", "kilsen", "cofem", "aguilera", "esser", "hochiki",
        "gst", "kidde", "aritech", "ziton", "apollo", "inim", "teletek",
    }
)


@dataclass(frozen=True)
class _FamilySpec:
    """A model umbrella that denotes a SERIES of variants (GT-anchored). The
    ``divergent_axis`` keywords are the attributes whose answer DIFFERS by variant
    (here: number of loops/zones). A question hitting the axis on the umbrella is
    a real divergence -> clarify; any other question is answered family-generic."""

    divergent_axis: tuple[str, ...]


# Morley ZXSe / ZXe families by number of loops — Alberto GT (memory
# reference_morley_zx_rp1r, s78/s79/s80). ZXSe {ZX1Se..ZX10Se}, ZXe {ZX1e..ZX5e}.
# The umbrella token (as ``extract_product_models`` emits it, normalized upper)
# maps to its divergent axis. Seed; the durable version reads the catalog's
# variant table (DEC-069). NON_PRODUCT_CODES can never be families.
FAMILY_REGISTRY: dict[str, _FamilySpec] = {
    "ZXSE": _FamilySpec(divergent_axis=(
        "cuántos lazos", "cuantos lazos", "número de lazos", "numero de lazos",
        "cuántos bucles", "cuantos bucles", "lazos y zonas",
        "cuántas zonas", "cuantas zonas", "número de zonas", "numero de zonas",
    )),
    "ZXE": _FamilySpec(divergent_axis=(
        "cuántos lazos", "cuantos lazos", "número de lazos", "numero de lazos",
        "cuántos bucles", "cuantos bucles", "lazos y zonas",
        "cuántas zonas", "cuantas zonas", "número de zonas", "numero de zonas",
    )),
}

# Attributes that are INVARIANT across a family's variants -> never clarify on
# them (DEC-092: end-of-line resistance is family-generic in the e-series). A
# defensive negative guard alongside the specific divergent-axis phrases.
_INVARIANT_ATTRS: tuple[str, ...] = (
    "fin de línea", "fin de linea", "resistencia de fin", "eol", "rfl",
)

# Content-anaphora: a demonstrative determiner (ese/esa/esos/esas) + a following
# noun points at specific prior CONTENT that re-attaching the model cannot
# resolve ("ese aviso" = the Earth-Fault notice; "esa entrada" = the M710 input).
# Neuter forms ("eso"/"esto") do NOT match (no [ae] after "es"/"est") — they are
# discourse fillers handled by carry_forward. (Matches the sunk-S99v2 slice.)
_CONTENT_ANAPHOR_RE = re.compile(r"\bes[ae]s?\s+\w+", re.IGNORECASE)

# Dependency signal for the NO-STATE case: a leading continuation conjunction or
# an anaphoric/possessive pronoun => the turn NEEDS an antecedent. Used only to
# split clarify (dangling) vs standalone (self-contained) when there is no usable
# state; when state IS available, a product-less turn defaults to carry_forward.
_DEPENDENCY_RE = re.compile(
    r"^\s*¿?\s*y\b"                              # "¿y ...", "y ..."
    r"|\b(su|sus|le|lo|la|los|las|dicho|dicha|mismo|misma)\b"  # anaphoric pronouns
    r"|\bes[ae]s?\s+\w+\b"                       # demonstrative + noun
    r"|\bes[eo]\b",                              # bare "ese"/"eso"
    re.IGNORECASE,
)

# Conservative OUT-OF-DOMAIN lexicon (S99 gas gate). Deliberately narrow: it must
# never fire on the served fire-adjacent gas detectors (DGD-600 etc.), which are
# handled by the explicit-product branch A before this gate is reached. No gold
# exercises DECLINE (declared gap, vara); this keeps the route genuine + safe.
_OUT_OF_DOMAIN_LEXICON: tuple[str, ...] = (
    "caldera de gas", "cocina de gas", "gas natural", "gas ciudad",
    "bombona de butano", "estufa de gas", "calentador de gas",
)


# ---------------------------------------------------------------------------
# Detection (composes extract_product_models — never duplicates it)
# ---------------------------------------------------------------------------
def detect_turn_signals(query: str) -> tuple[list[str], list[str] | None]:
    """``(turn_models, available_models)`` — mirrors telegram_bot steps 1a/2b, $0.

    ``turn_models`` = ``extract_product_models(query)`` (the existing detector,
    composed). ``available_models`` = category-detected option set (for CLARIFY)
    or None. Imports are local so the module has no import-time DB/config cost
    beyond the detector's own (pure regex)."""
    from src.rag.retriever import (
        CATEGORY_TERMS,
        extract_product_models,
        get_category_models,
    )

    turn_models = extract_product_models(query)
    available: list[str] | None = None
    if not turn_models:
        ql = query.lower()
        for term, cat in CATEGORY_TERMS.items():
            if term in ql:
                available = get_category_models(cat)
                break
    return turn_models, available


# ---------------------------------------------------------------------------
# The policy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeterministicConversationPolicy:
    """MT-1a's concrete policy. Deterministic cascade; the injected ``rewrite``
    callable is used ONLY on the REWRITE route (and only when supplied)."""

    IS_STUB: bool = field(default=False, init=False)
    window_seconds: int = WINDOW_SECONDS

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _mentions_brand(ql: str) -> bool:
        return any(re.search(rf"\b{re.escape(b)}\b", ql) for b in BRAND_TOKENS)

    @staticmethod
    def _is_out_of_domain(ql: str) -> bool:
        return any(term in ql for term in _OUT_OF_DOMAIN_LEXICON)

    @staticmethod
    def _family_divergence(models: Sequence[str], ql: str) -> bool:
        """True when a state model is a known family AND the question hits its
        divergent axis AND does not ask about an invariant attribute."""
        if any(term in ql for term in _INVARIANT_ATTRS):
            return False
        for m in models:
            spec = FAMILY_REGISTRY.get(m)
            if spec and any(term in ql for term in spec.divergent_axis):
                return True
        return False

    def _carry_forward(self, query: str, models: tuple[str, ...], why: str) -> TurnResolution:
        hint = ", ".join(models)
        # Raw query preserved byte-verbatim; model hint APPENDED (design invariant).
        qfr = f"{query} (contexto: {hint})" if hint else query
        return TurnResolution(
            route=PolicyRoute.CARRY_FORWARD,
            query_for_retrieval=qfr,
            target_models=models,
            rationale=f"carry_forward:{why}",
        )

    # -- the router ---------------------------------------------------------
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
        ql = query.lower()
        real = tuple(m for m in turn_models if m not in NON_PRODUCT_CODES)
        avail = tuple(available_models) if available_models else None

        # A. Explicit product in THIS turn wins over history.
        if real:
            return TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=real,
                available_models=avail,
                rationale="explicit_product",
            )

        # B. A brand is named but the regex resolved no in-corpus model: the turn
        #    introduces a NEW/out-of-corpus product -> standalone, drop stale state.
        if self._mentions_brand(ql):
            return TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=(),
                available_models=avail,
                rationale="new_brand_named_no_corpus_model",
            )

        # C. Out-of-domain (conservative gas-outside-fire gate). After A/B so an
        #    in-corpus gas detector is never declined.
        if self._is_out_of_domain(ql):
            return TurnResolution(
                route=PolicyRoute.DECLINE,
                query_for_retrieval=query,
                decline_reason="fuera_de_dominio_pci_fuego",
                rationale="out_of_domain_gas",
            )

        in_window = bool(working_state.last_target_models) and working_state.within_window(
            now, self.window_seconds
        )

        # D. In-window state -> continuation.
        if in_window:
            models = working_state.last_target_models

            # E. Family umbrella + divergent-axis question -> clarify (real divergence).
            if self._family_divergence(models, ql):
                umbrella = next((m for m in models if m in FAMILY_REGISTRY), models[0])
                return TurnResolution(
                    route=PolicyRoute.CLARIFY,
                    query_for_retrieval=query,
                    target_models=models,
                    available_models=working_state.available_models or avail,
                    clarify_question=(
                        f"La {umbrella} tiene variantes por número de lazos "
                        f"(1/2/5/10) y ese dato cambia entre ellas. ¿Con qué "
                        f"variante estás trabajando?"
                    ),
                    rationale="divergent_variant",
                )

            # F. Content anaphora -> rewrite (defers in $0 mode; fallback if invalid).
            if _CONTENT_ANAPHOR_RE.search(query):
                if rewrite is None:
                    return TurnResolution(
                        route=PolicyRoute.REWRITE,
                        query_for_retrieval=query,  # raw fallback; --e2e supplies text
                        target_models=models,
                        available_models=avail,
                        requires_llm_rewrite=True,
                        rewritten_query=None,  # deferred: never fabricate
                        rationale="content_anaphor:deferred($0)",
                    )
                rewritten = rewrite(query, working_state)
                if rewritten is None:
                    # Fail-closed: the $-was-spent but the conduct is safe.
                    return self._carry_forward(
                        query, models, "content_anaphor:rewrite_failed_fallback"
                    )
                return TurnResolution(
                    route=PolicyRoute.REWRITE,
                    query_for_retrieval=rewritten,
                    target_models=models,
                    available_models=avail,
                    requires_llm_rewrite=True,
                    rewritten_query=rewritten,
                    rationale="content_anaphor:rewritten",
                )

            # G. Simple within-window follow-up -> deterministic carry-forward, $0.
            return self._carry_forward(query, models, "within_window_followup")

        # H/I. No usable state (empty or expired).
        if self._depends_on_context(query):
            # Dangling anaphora with no antecedent -> clarify (ask for the model).
            return TurnResolution(
                route=PolicyRoute.CLARIFY,
                query_for_retrieval=query,
                target_models=(),  # never leak an expired product (mt07b)
                available_models=avail,
                clarify_question=(
                    "¿De qué central o detector (modelo) estamos hablando? Ha pasado "
                    "un rato y necesito el modelo para responder con precisión."
                ),
                rationale="dangling_no_antecedent",
            )
        # Genuinely standalone product-less turn -> let retrieval/generator handle it.
        return TurnResolution(
            route=PolicyRoute.STANDALONE,
            query_for_retrieval=query,
            target_models=(),
            available_models=avail,
            rationale="standalone_no_product",
        )

    @staticmethod
    def _depends_on_context(query: str) -> bool:
        return bool(_DEPENDENCY_RE.search(query))


# ---------------------------------------------------------------------------
# Composition seam (what MT-0d / activation wires to the bot; also the paid
# --e2e path). Mirrors the MT-1b harness's detect -> resolve -> advance loop so
# the bot behaves byte-identically to the eval.
# ---------------------------------------------------------------------------
def resolve_conversational_turn(
    query: str,
    working_state: WorkingState,
    now: datetime,
    rewrite: RewriteFn | None = None,
) -> tuple[TurnResolution, WorkingState]:
    """Compose ``extract_product_models`` + the policy into a resolved turn.

    Returns ``(resolution, new_working_state)``. The new state is advanced from
    the resolution WITHOUT the answer excerpt (unknown pre-retrieval); the bot
    backfills the excerpt post-generation via ``advance_working_state`` if it
    wants the rewriter to see prior answer text on the next turn."""
    turn_models, available = detect_turn_signals(query)
    policy = DeterministicConversationPolicy()
    resolution = policy.resolve(
        query=query,
        turn_models=turn_models,
        available_models=available,
        working_state=working_state,
        now=now,
        rewrite=rewrite,
    )
    new_state = advance_working_state(
        working_state, resolution, query, None, now, available
    )
    return resolution, new_state


def advance_working_state(
    ws: WorkingState,
    resolution: TurnResolution,
    query: str,
    answer_excerpt: str | None,
    now: datetime,
    available: Sequence[str] | None,
) -> WorkingState:
    """Durable state after a resolved turn. CLARIFY/DECLINE do NOT fix a model
    (the user has not disambiguated) — they keep the prior model and only refresh
    the activity timestamp. Mirrors the MT-1b harness ``update_working_state`` so
    production and eval stay in lock-step."""
    avail_tuple = tuple(available) if available else None
    if resolution.route in (PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
        return WorkingState(
            last_target_models=ws.last_target_models,
            last_query=ws.last_query,
            last_answer_excerpt=ws.last_answer_excerpt,
            last_turn_at=now,
            available_models=avail_tuple or ws.available_models,
        )
    models = tuple(resolution.target_models or ())
    return WorkingState(
        last_target_models=models,
        last_query=query,
        last_answer_excerpt=(answer_excerpt or "")[:500] or None,
        last_turn_at=now,
        available_models=avail_tuple,
    )


# ---------------------------------------------------------------------------
# Activation gate for default_policy() (design philosophy: Phase-1 activation is
# flag-gated / default-OFF — the orchestrator + Alberto flip it, like
# ORCHESTRATOR_PATH / CONVO_SHADOW). Read at RUNTIME so an A/B can toggle in one
# process. ``conversation_policy.default_policy()`` calls this.
# ---------------------------------------------------------------------------
def conversation_policy_active() -> bool:
    """True when ``CONVERSATION_POLICY=impl`` (default OFF -> the stub, keeping
    the frozen contract tests green until the orchestrator activates Phase 1)."""
    return os.getenv("CONVERSATION_POLICY", "stub").strip().lower() == "impl"


__all__ = [
    "WINDOW_SECONDS",
    "BRAND_TOKENS",
    "FAMILY_REGISTRY",
    "DeterministicConversationPolicy",
    "detect_turn_signals",
    "resolve_conversational_turn",
    "advance_working_state",
    "conversation_policy_active",
]
