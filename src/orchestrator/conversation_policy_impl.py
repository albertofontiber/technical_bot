"""Deterministic conversational policy — MT-1a (S281 / Phase 1).

This is the concrete ``ConversationPolicy`` the frozen interface
(``conversation_policy.py``) declares. It is a **deterministic router in cascade**
with a traceable rationale per decision; the economical rewriter
(``rewriter.py``) is invoked ONLY on the narrow anaphora slice the router cannot
resolve by re-attaching the last product. Everything else is $0.

THE CASCADE (order matters — first match wins):

  A. EXPLICIT PRODUCT in this turn (``turn_models`` minus ``NON_PRODUCT_CODES``
     and normative/standards codes) -> STANDALONE. The explicit product WINS over
     working state (design §5); a self-correction ("me refería a la X") therefore
     REPLACES the state, never unions it.
  B. BRAND named (no in-corpus model resolved) -> deterministic split:
       * SAME manufacturer as the state -> not a switch, fall through to C/D.
       * brand + model-type token (e.g. "la Bosch Avenar FPA-1200") -> STANDALONE,
         target=() (new product, drop stale state; downstream admits).
       * brand alone, in-window (e.g. "¿es compatible con Hochiki?") -> CARRY_FORWARD
         (a compatibility follow-up about the state product).
       * brand alone, no usable state -> STANDALONE, target=() (new topic).
     Catalog-aware brand gate (vara §7.3, DEC-069 dependency).
  C. OUT-OF-DOMAIN lexicon (conservative gas-outside-fire gate, S99) -> DECLINE.
     Runs AFTER A/B and ONLY when NOT an in-window continuation, so neither an
     in-corpus gas *detector* (DGD-600, branch A) nor an in-window follow-up that
     mentions gas (a boiler-cutoff maneuver from a fire panel) is ever declined.
  D. IN-WINDOW STATE present (product-less follow-up within 1h) -> continuation:
       E. family umbrella + question on the family's DIVERGENT axis (real
          divergence, catalog/GT-anchored) and NOT an invariant attribute
          -> CLARIFY (s79/s80: clarify ONLY on real divergence; an invariant
          answer is ``answer``, never a reflexive clarify).
       F. content anaphora ("ese aviso" / "esos avisos" / "este módulo") the
          re-attach cannot resolve -> REWRITE (requires_llm_rewrite=True). With
          ``rewrite=None`` (contract mode) it DEFERS (rewritten_query=None, no
          fabrication). With a rewriter injected it calls it; a fail-closed
          rewrite (None) falls back to CLARIFY of the antecedent (not
          carry_forward: the cascade already judged the re-attach insufficient,
          so retrieving on the ambiguous query is unsafe; $-spent, declared).
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
from pathlib import Path

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
# model, the turn MAY be introducing a NEW product (possibly out of corpus). The
# gate is a deterministic split (see ``resolve`` branch B): brand + model-type
# token => product switch; brand alone in-window => compatibility follow-up
# (carry-forward); brand of the SAME manufacturer as the state => exempt.
# Anchored to config/manufacturers (governed source) UNIONED with a seed of the
# M&A 30+-brand universe (MT-1a S99 fix; mt05b Bosch FPA-1200 is the pinned case).
_SEED_BRAND_TOKENS: frozenset[str] = frozenset(
    {
        # served
        "detnov", "notifier", "morley", "honeywell",
        # common unserved fire-alarm brands (seed)
        "bosch", "siemens", "kilsen", "cofem", "aguilera", "esser", "hochiki",
        "gst", "kidde", "aritech", "ziton", "apollo", "inim", "teletek",
    }
)


def _config_brand_tokens() -> frozenset[str]:
    """Primary brand word of every ``config/manufacturers/*.yaml`` (the governed
    source): Detnov, Morley, Notifier, Argus, Pepperl, Securiton, Spectrex,
    Xtralis... Best-effort + import-light (a small yaml read); on any failure the
    seed alone stands. The durable version also unions the model catalog's brand
    set (heavier — declared extension, not loaded here)."""
    tokens: set[str] = set()
    try:  # pragma: no cover - trivial IO guard
        import yaml  # local: not needed unless deriving brands

        cfg_dir = Path(__file__).resolve().parents[2] / "config" / "manufacturers"
        for p in sorted(cfg_dir.glob("*.yaml")):
            if p.name.startswith("_"):
                continue
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            name = str(data.get("manufacturer") or "")
            # Primary word only (avoids generic suffixes like "Security"/"Fuchs").
            for w in re.split(r"[^A-Za-zÀ-ÿ0-9]+", name.lower()):
                if len(w) >= 3:
                    tokens.add(w)
                    break
    except Exception:
        pass
    return frozenset(tokens)


BRAND_TOKENS: frozenset[str] = _SEED_BRAND_TOKENS | _config_brand_tokens()

# Brand-word -> canonical manufacturer, for the SAME-manufacturer exemption in the
# brand gate (naming the state's own brand is not a product switch). Only served
# manufacturers matter here (the working-state model is always in-corpus); unserved
# brands fall through as "different manufacturer" and are never exempt.
_BRAND_TO_MANUFACTURER: dict[str, str] = {
    "detnov": "Detnov",
    "notifier": "Notifier",
    "morley": "Morley",
    "honeywell": "Honeywell",
}

# A model-type token (vendor code with digits: FPA-1200, AM-2000, IDX3000). When a
# brand is named ALONGSIDE such a token the turn introduces a concrete product =>
# switch (drop stale state). A brand with NO model-type token in-window is a
# compatibility follow-up (carry-forward). Normative/non-product codes are excluded
# so "EN-54"/"NFPA-72" beside a brand never read as a model.
_MODEL_TYPE_TOKEN_RE = re.compile(
    r"\b[A-Za-z]{2,}-\d{2,}\b"        # FPA-1200, AM-2000, CAD-250
    r"|\b[A-Za-z]{2,}\d{3,}\b",       # FPA1200, IDX3000 (no hyphen)
    re.IGNORECASE,
)

# Normative/standards codes (NFPA 72, EN 54, UNE 23007, UL 864, CEA 4040, ISO
# 7240). They look like product codes to the detector but are NEVER a product ->
# filtered alongside NON_PRODUCT_CODES (S99 / sol-S6). Hyphen or space separator.
_NORMATIVE_CODE_RE = re.compile(
    r"\b(?:NFPA|EN|UNE|UL|CEA|ISO)[-\s]?\d+", re.IGNORECASE
)


@dataclass(frozen=True)
class _FamilySpec:
    """A model umbrella that denotes a SERIES of variants (GT-anchored). The
    ``divergent_axis`` keywords are the attributes whose answer DIFFERS by variant
    (here: number of loops/zones). ``variants`` is the GT variant list (by number
    of loops) used to render the clarify question precisely. A question hitting the
    axis on the umbrella is a real divergence -> clarify; any other question is
    answered family-generic."""

    divergent_axis: tuple[str, ...]
    variants: tuple[str, ...]


_LOOP_AXIS: tuple[str, ...] = (
    "cuántos lazos", "cuantos lazos", "número de lazos", "numero de lazos",
    "cuántos bucles", "cuantos bucles", "lazos y zonas",
    "cuántas zonas", "cuantas zonas", "número de zonas", "numero de zonas",
)

# Morley ZXSe / ZXe families by number of loops — Alberto GT (memory
# reference_morley_zx_rp1r, s78/s79/s80). ZXSe {ZX1Se..ZX10Se}, ZXe {ZX1e..ZX5e}.
# The umbrella token (as ``extract_product_models`` emits it, normalized upper)
# maps to its divergent axis + variant list. Seed; the durable version reads the
# catalog's variant table (DEC-069). NON_PRODUCT_CODES can never be families.
FAMILY_REGISTRY: dict[str, _FamilySpec] = {
    "ZXSE": _FamilySpec(divergent_axis=_LOOP_AXIS, variants=("1", "2", "5", "10")),
    "ZXE": _FamilySpec(divergent_axis=_LOOP_AXIS, variants=("1", "2", "5")),
}

# Attributes that are INVARIANT across a family's variants -> never clarify on
# them (DEC-092: end-of-line resistance is family-generic in the e-series). A
# defensive negative guard alongside the specific divergent-axis phrases.
_INVARIANT_ATTRS: tuple[str, ...] = (
    "fin de línea", "fin de linea", "resistencia de fin", "eol", "rfl",
)

# Demonstrative determiners (gendered forms only). ``ese/esa/esos/esas`` and
# ``este/esta/estos/estas`` — the plural/singular masculine+feminine set. The
# NEUTER singulars ``eso``/``esto`` are deliberately EXCLUDED (they are discourse
# fillers — "eso, ¿cómo...?" — handled by carry_forward, not content anaphora).
_DEMONSTRATIVE = r"(?:ese|esa|esos|esas|este|esta|estos|estas)"

# Content-anaphora: a demonstrative determiner + a following noun points at
# specific prior CONTENT that re-attaching the model cannot resolve ("ese aviso"
# = the Earth-Fault notice; "esos avisos" = the batch of notices; "este módulo"
# = the loop module). (Matches the sunk-S99v2 slice; extended to the full
# demonstrative set — the old ``es[ae]s?`` missed "esos"/"este..." — sol/F6.)
_CONTENT_ANAPHOR_RE = re.compile(rf"\b{_DEMONSTRATIVE}\s+\w+", re.IGNORECASE)

# Dependency signal for the NO-STATE case: a leading continuation conjunction, a
# possessive/anaphoric pronoun, or a demonstrative + noun => the turn NEEDS an
# antecedent. Used only to split clarify (dangling) vs standalone (self-contained)
# when there is no usable state. The Spanish ARTICLES (le|lo|la|los|las) were
# REMOVED (S99 / orq+sol-S3 + F1x5): they fire on almost every self-contained
# question, mis-routing standalone turns to clarify. Declared safe degradation: a
# rare true object clitic ("¿cómo lo borro?") now falls to STANDALONE (retrieval +
# generator handle it) instead of a reflexive clarify.
_DEPENDENCY_RE = re.compile(
    r"^\s*¿?\s*y\b"                              # "¿y ...", "y ..."
    r"|\b(su|sus|dicho|dicha|mismo|misma)\b"     # possessive / anaphoric pronouns
    rf"|\b{_DEMONSTRATIVE}\s+\w+\b"              # demonstrative + noun
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
                try:
                    available = get_category_models(cat)
                except Exception:
                    # Fail-open: un fallo del lookup de categoría (DB caída,
                    # entorno sin credenciales) no puede tumbar el turno — la
                    # categoría solo alimenta las opciones de CLARIFY.
                    available = None
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
    def _matched_brands(ql: str) -> list[str]:
        return [b for b in BRAND_TOKENS if re.search(rf"\b{re.escape(b)}\b", ql)]

    @staticmethod
    def _is_out_of_domain(ql: str) -> bool:
        return any(term in ql for term in _OUT_OF_DOMAIN_LEXICON)

    @staticmethod
    def _is_normative_code(model: str) -> bool:
        return bool(_NORMATIVE_CODE_RE.fullmatch(model.strip()))

    @staticmethod
    def _has_model_type_token(ql: str) -> bool:
        """A concrete vendor model code (with digits) is present — excluding
        normative/non-product codes so they never read as a model."""
        np_codes = {c.upper() for c in NON_PRODUCT_CODES}
        for m in _MODEL_TYPE_TOKEN_RE.finditer(ql):
            tok = m.group(0)
            norm = tok.upper().replace(" ", "")
            if norm in np_codes or _NORMATIVE_CODE_RE.fullmatch(tok):
                continue
            return True
        return False

    @staticmethod
    def _same_manufacturer(matched_brands: Sequence[str], state_models: Sequence[str]) -> bool:
        """True when a named brand is the SAME manufacturer as the working-state
        product (naming your own brand is not a switch). Catalog-first classifier
        (file-backed, $0/no DB); Honeywell collapses to its Notifier/Morley
        sub-brands."""
        if not matched_brands or not state_models:
            return False
        from src.rag.retriever import classify_model_manufacturer

        state_mfrs = {classify_model_manufacturer(m) for m in state_models}
        state_mfrs.discard(None)
        if not state_mfrs:
            return False
        for b in matched_brands:
            bm = _BRAND_TO_MANUFACTURER.get(b)
            if not bm:
                continue
            if bm in state_mfrs:
                return True
            if bm == "Honeywell" and state_mfrs & {"Notifier", "Morley"}:
                return True
        return False

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
        # A-filter: drop bus/protocol (NON_PRODUCT_CODES) AND normative/standards
        # codes (NFPA/EN/UNE/UL/CEA/ISO) — neither is a product (sol-S6).
        real = tuple(
            m for m in turn_models
            if m not in NON_PRODUCT_CODES and not self._is_normative_code(m)
        )
        avail = tuple(available_models) if available_models else None

        # in_window is computed HERE (before B/C) so a brand/out-of-domain gate can
        # never override an in-window continuation (gas-gate S99 / F4).
        in_window = bool(working_state.last_target_models) and working_state.within_window(
            now, self.window_seconds
        )

        # A. Explicit product in THIS turn wins over history.
        if real:
            return TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=real,
                available_models=avail,
                rationale="explicit_product",
            )

        # B. Brand gate (deterministic split — S99 / fable-F3 + sol-S7).
        matched_brands = self._matched_brands(ql)
        if matched_brands:
            same_mfr = in_window and self._same_manufacturer(
                matched_brands, working_state.last_target_models
            )
            if same_mfr:
                pass  # naming your OWN brand is not a switch -> fall through to C/D.
            elif self._has_model_type_token(ql):
                # Brand + concrete model code -> new product -> switch, drop state.
                return TurnResolution(
                    route=PolicyRoute.STANDALONE,
                    query_for_retrieval=query,
                    target_models=(),
                    available_models=avail,
                    rationale="new_brand_switch_model_token",
                )
            elif in_window:
                # Brand alone, in-window -> compatibility follow-up about the state
                # product (e.g. "¿es compatible con Hochiki?") -> carry-forward.
                return self._carry_forward(
                    query, working_state.last_target_models, "brand_compatibility_in_window"
                )
            else:
                # Brand named, no usable state -> new topic (possibly out-of-corpus).
                return TurnResolution(
                    route=PolicyRoute.STANDALONE,
                    query_for_retrieval=query,
                    target_models=(),
                    available_models=avail,
                    rationale="new_brand_no_state",
                )

        # C. Out-of-domain (conservative gas-outside-fire gate). Runs AFTER A/B and
        #    ONLY when NOT an in-window continuation: an in-window follow-up (even
        #    one mentioning gas, e.g. a boiler-cutoff maneuver from a fire panel) is
        #    never hard-declined (F4). A fresh out-of-domain turn still declines.
        if not in_window and self._is_out_of_domain(ql):
            return TurnResolution(
                route=PolicyRoute.DECLINE,
                query_for_retrieval=query,
                decline_reason="fuera_de_dominio_pci_fuego",
                rationale="out_of_domain_gas",
            )

        # D. In-window state -> continuation.
        if in_window:
            models = working_state.last_target_models

            # E. Family umbrella + divergent-axis question -> clarify (real divergence).
            if self._family_divergence(models, ql):
                umbrella = next((m for m in models if m in FAMILY_REGISTRY), models[0])
                spec = FAMILY_REGISTRY.get(umbrella)
                variants = "/".join(spec.variants) if spec else "1/2/5/10"
                return TurnResolution(
                    route=PolicyRoute.CLARIFY,
                    query_for_retrieval=query,
                    target_models=models,
                    available_models=working_state.available_models or avail,
                    clarify_question=(
                        f"La {umbrella} tiene variantes por número de lazos "
                        f"({variants}) y ese dato cambia entre ellas. ¿Con qué "
                        f"variante estás trabajando?"
                    ),
                    rationale="divergent_variant",
                )

            # F. Content anaphora -> rewrite (defers in $0 mode; clarify if invalid).
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
                    # Fail-CLOSED: the cascade already judged re-attaching the model
                    # INSUFFICIENT (that is why it chose rewrite), so a carry-forward
                    # fallback would retrieve on an ambiguous query. Ask which
                    # element/notice instead. The $ was spent (declared).
                    return TurnResolution(
                        route=PolicyRoute.CLARIFY,
                        query_for_retrieval=query,
                        target_models=models,
                        available_models=avail,
                        clarify_question=(
                            "¿A qué aviso o elemento concreto te refieres? Necesito "
                            "precisarlo para darte la respuesta correcta."
                        ),
                        rationale="content_anaphor:rewrite_failed_clarify($-spent)",
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
            # The text is conditional: a genuine FIRST message never had a prior
            # context, so it must not claim "time has passed" (F8).
            if working_state.is_empty:
                clarify_q = (
                    "¿De qué central o detector (modelo) estamos hablando? Necesito "
                    "el modelo para responder con precisión."
                )
            else:
                clarify_q = (
                    "¿De qué central o detector (modelo) estamos hablando? Ha pasado "
                    "un rato y necesito el modelo para responder con precisión."
                )
            return TurnResolution(
                route=PolicyRoute.CLARIFY,
                query_for_retrieval=query,
                target_models=(),  # never leak an expired product (mt07b)
                available_models=avail,
                clarify_question=clarify_q,
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
    wants the rewriter to see prior answer text on the next turn.

    TODO(MT-0d activation — sol-S8, by DESIGN not a defect): the bot does NOT yet
    consume this policy (activation is MT-0d + Alberto, out of the MT-1a brief).
    When it is wired, the handler MUST call ``advance_working_state`` a SECOND time
    after generation, passing ``answer_excerpt=<generated answer>``, so the durable
    ``last_answer_excerpt`` is populated and the rewriter can resolve content
    anaphora ("ese aviso") against the prior answer text on the next turn. This
    one-line composition seam intentionally passes ``None`` (pre-retrieval)."""
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
    (the user has not disambiguated) AND return the prior state INTACT — crucially
    WITHOUT refreshing ``last_turn_at``. Refreshing it would RESURRECT an expired
    product: a clarify at 70 min followed by another dangling turn would find the
    (stale) model back "in window" and carry it forward (S99 / sol-S4 + F2). An
    expired context stays expired until the user re-establishes a model. Mirrors
    the MT-1b harness ``update_working_state`` so production and eval stay in
    lock-step."""
    if resolution.route in (PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
        return ws
    avail_tuple = tuple(available) if available else None
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
