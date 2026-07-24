"""MT-1b contract tests: golds schema, interface stability, orchestrator
isolation, and — crucially — proof the deterministic assertions HAVE TEETH.

The multi-turn eval ships as a SPEC before MT-1a implements the policy, so the
suite must (a) stay green with the stub, and (b) prove the assertions bite when a
real policy exists. We do the latter with a genuine (not gold-peeking) reference
classifier defined here: ``run_contract`` against it must report FAIL=0 (the
golds are satisfiable), and against a deliberately-wrong policy must report
FAIL>0 (the assertions are not vacuous).
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import test_multiturn_vs_gold as harness  # noqa: E402
from src.orchestrator.conversation_policy import (  # noqa: E402
    NON_PRODUCT_CODES,
    PolicyNotImplemented,
    PolicyRoute,
    StubConversationPolicy,
    TurnResolution,
    WorkingState,
    default_policy,
)
from src.orchestrator import replay_adapters  # noqa: E402
from src.orchestrator.contracts import TurnRequest  # noqa: E402
from src.orchestrator.fake_convo_store import FakeConvoStore, ManualClock  # noqa: E402
from src.orchestrator.lifecycle import run_conversational_turn  # noqa: E402


FLOWS = harness.load_flows()


# ===========================================================================
# 1. Golds schema + coverage + real-entity provenance
# ===========================================================================
def test_schema_is_valid():
    assert harness.validate_schema(FLOWS) == []


def test_all_coverage_classes_covered():
    # 13 after the s281 round-2 hardening (10 base + standalone_autocontenida,
    # compatibilidad_marca, continuacion_dominio_limitrofe).
    assert harness.covered_classes(FLOWS) == harness._COVERAGE_CLASSES
    assert len(harness._COVERAGE_CLASSES) == 13


def test_reused_golds_are_real_entities():
    gold_qids = {
        r["qid"]
        for r in yaml.safe_load(
            (ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8")
        )
    }
    for f in FLOWS:
        for qid in f.get("reuses_golds", []):
            assert qid in gold_qids, f"{f['flow_id']} reusa gold inexistente {qid}"


def test_every_flow_traces_to_a_source():
    # Each flow either reuses a gold or declares an entity_source (memory/GT):
    # no invented product specs.
    for f in FLOWS:
        assert f.get("reuses_golds") or f.get("entity_source"), (
            f"{f['flow_id']} sin reuses_golds ni entity_source (entidad inventada?)"
        )


# ===========================================================================
# 2. Interface stability + $0 invariants (conversation_policy contract surface)
# ===========================================================================
def test_stub_is_detected_and_raises(monkeypatch):
    # TEST-ENV-LEAK (F11): a leaked CONVERSATION_POLICY=impl from another test/env
    # must not turn the stub real under us — pin the default.
    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)
    policy = default_policy()
    assert getattr(policy, "IS_STUB", False) is True
    with pytest.raises(PolicyNotImplemented):
        policy.resolve(
            query="q", turn_models=[], available_models=None,
            working_state=WorkingState(), now=datetime(2026, 7, 23),
        )


def test_zero_cost_routes_cannot_require_rewrite():
    for route in (PolicyRoute.STANDALONE, PolicyRoute.CARRY_FORWARD,
                  PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
        with pytest.raises(ValueError):
            TurnResolution(
                route=route, query_for_retrieval="q", requires_llm_rewrite=True,
                clarify_question="?", decline_reason="x",
            )


def test_rewrite_route_must_flag_rewrite():
    with pytest.raises(ValueError):
        TurnResolution(route=PolicyRoute.REWRITE, query_for_retrieval="q",
                       requires_llm_rewrite=False)


def test_clarify_and_decline_require_their_payload():
    with pytest.raises(ValueError):
        TurnResolution(route=PolicyRoute.CLARIFY, query_for_retrieval="q")
    with pytest.raises(ValueError):
        TurnResolution(route=PolicyRoute.DECLINE, query_for_retrieval="q")


def test_working_state_window():
    base = datetime(2026, 7, 23, 12, 0, 0)
    ws = WorkingState(last_target_models=("CAD-250",), last_turn_at=base)
    assert ws.within_window(base.replace(minute=50), 3600) is True
    assert ws.within_window(base.replace(hour=13, minute=10), 3600) is False


# ===========================================================================
# 3. Stub-mode harness: green + non-vacuous plumbing ($0)
# ===========================================================================
def test_contract_stub_mode_reports_pending_and_drives_orchestrator(monkeypatch):
    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)  # TEST-ENV-LEAK (F11)
    report = harness.run_contract(FLOWS)  # default_policy() = stub
    assert report["policy_stub"] is True
    assert report["fail"] == 0
    assert report["pending"] == report["turns"]
    # Non-vacuous: the retrieving turns actually crossed the orchestrator + store.
    assert report["plumbing_ok"] >= 25


# ===========================================================================
# 4. A GENUINE reference policy → proof the assertions are satisfiable + bite
# ===========================================================================
FAMILY_UMBRELLAS = frozenset({"ZXSE", "ZXE"})
UNKNOWN_BRANDS = frozenset({"bosch"})  # served-corpus-absent brand tokens
# Full demonstrative set (esos/este were missed by the old es[ae]s? — s281 F6).
_DEMONSTRATIVE = r"(?:ese|esa|esos|esas|este|esta|estos|estas)"
_ANAPHOR = re.compile(rf"\b{_DEMONSTRATIVE}\s+\w+", re.IGNORECASE)
# Dependency signal WITHOUT articles (s281 F1): possessives + demonstratives +
# leading "y". A no-state turn with a dependency signal clarifies; else standalone.
_DEP = re.compile(
    rf"^\s*¿?\s*y\b|\b(su|sus|dicho|dicha|mismo|misma)\b|\b{_DEMONSTRATIVE}\s+\w+|\bes[eo]\b",
    re.IGNORECASE,
)
_VARIANT_SENSITIVE = (
    "cuántos lazos", "cuantos lazos", "lazos y zonas", "cuántas zonas",
    "cuantas zonas", "número de lazos", "numero de lazos",
)
_INVARIANT = ("fin de línea", "fin de linea", "eol", "rfl", "resistencia de fin")


@dataclass(frozen=True)
class _ReferencePolicy:
    """Deterministic router derived ONLY from query + working state (never the
    gold). Minimal but genuine — enough to prove the golds are labelable by a
    real classifier and the eval's assertions have teeth. MT-1a builds the
    production version (real rewriter, catalog-backed brand detection)."""

    IS_STUB: bool = False
    window_seconds: int = 3600

    def resolve(self, *, query, turn_models, available_models, working_state,
                now, rewrite=None) -> TurnResolution:
        ql = query.lower()
        real = tuple(m for m in turn_models if m not in NON_PRODUCT_CODES)

        # (0) explicit but corpus-absent brand -> standalone, no carry-forward.
        if any(b in ql for b in UNKNOWN_BRANDS):
            return TurnResolution(
                route=PolicyRoute.STANDALONE, query_for_retrieval=query,
                target_models=(), rationale="unknown_brand",
            )
        # (1) explicit product in this turn WINS over history.
        if real:
            return TurnResolution(
                route=PolicyRoute.STANDALONE, query_for_retrieval=query,
                target_models=real, rationale="explicit_product",
            )
        # (2) no product named + no usable state -> clarify only if a real
        #     dependency signal is present (a self-contained turn is standalone;
        #     articles are NOT a dependency signal — s281 F1).
        in_window = (
            bool(working_state.last_target_models)
            and working_state.within_window(now, self.window_seconds)
        )
        if not in_window:
            if _DEP.search(query):
                return TurnResolution(
                    route=PolicyRoute.CLARIFY, query_for_retrieval=query,
                    clarify_question="¿De qué central o detector (modelo) hablamos?",
                    rationale="no_antecedent",
                )
            return TurnResolution(
                route=PolicyRoute.STANDALONE, query_for_retrieval=query,
                target_models=(), rationale="standalone_no_dependency",
            )
        models = working_state.last_target_models
        is_family = any(m in FAMILY_UMBRELLAS for m in models)
        variant_sensitive = any(k in ql for k in _VARIANT_SENSITIVE)
        invariant = any(k in ql for k in _INVARIANT)
        # (3) family umbrella + divergent question -> clarify (s79/s80).
        if is_family and variant_sensitive and not invariant:
            return TurnResolution(
                route=PolicyRoute.CLARIFY, query_for_retrieval=query,
                target_models=models,
                clarify_question=f"¿Qué variante de {models[0]} (por nº de lazos)?",
                rationale="divergent_variant",
            )
        # (4) anaphor to prior CONTENT -> rewrite (paid, deferred in contract).
        if _ANAPHOR.search(query):
            return TurnResolution(
                route=PolicyRoute.REWRITE, query_for_retrieval=query,
                target_models=models, requires_llm_rewrite=True,
                rationale="content_anaphor",
            )
        # (5) simple within-window follow-up -> deterministic carry-forward, $0.
        hint = ", ".join(models)
        return TurnResolution(
            route=PolicyRoute.CARRY_FORWARD,
            query_for_retrieval=f"{query} (contexto: {hint})",
            target_models=models, rationale="carry_forward",
        )


def test_reference_policy_satisfies_all_golds():
    report = harness.run_contract(FLOWS, policy=_ReferencePolicy())
    assert report["policy_stub"] is False
    assert report["fail"] == 0, report["failures"]
    assert report["pass"] == report["turns"]


@dataclass(frozen=True)
class _AlwaysStandalone:
    """Wrong-on-purpose policy: never carries context. Must trip the eval."""

    IS_STUB: bool = False

    def resolve(self, *, query, turn_models, available_models, working_state,
                now, rewrite=None) -> TurnResolution:
        return TurnResolution(
            route=PolicyRoute.STANDALONE, query_for_retrieval=query,
            target_models=tuple(turn_models),
        )


def test_assertions_bite_on_a_wrong_policy():
    report = harness.run_contract(FLOWS, policy=_AlwaysStandalone())
    # Every carry_forward / rewrite / clarify follow-up must be caught.
    assert report["fail"] > 0


# ===========================================================================
# 5. Orchestrator-level isolation of two conversations (design §9: CAS/order at
#    the orchestrator, not the transport) + dedup — the parts that EXIST today.
# ===========================================================================
def _iso_flow(clase_id):
    return next(f for f in FLOWS if f["flow_id"] == clase_id)


def _adapters(record):
    def generate(query, chunks, *, available_models=None):
        record.append(query)
        return {"answer": f"[ans] {query}", "diagrams": [], "input_tokens": 0,
                "output_tokens": 0}

    return replay_adapters(
        retrieved=[{"id": "x", "content": "c", "similarity": 0.9}], generate=generate
    )


def _req(chat, update, query):
    return TurnRequest(
        query=query, query_for_retrieval=query, retrieval_top_k=50, rerank_top_k=5,
        channel="telegram", conversation_id=chat, external_update_id=update,
    )


def test_two_conversations_are_isolated_and_dedup_holds():
    store = FakeConvoStore(clock=ManualClock())
    served: list[str] = []

    def sender(payload):
        return f"tg-{payload.outbox_id}"

    a = _iso_flow("mt09_iso_chatA")
    b = _iso_flow("mt09_iso_chatB")

    # Interleave A/B turn-by-turn over ONE store (sequential PTB model, §9).
    outcomes = {}
    for i in range(2):
        outcomes[("A", i)] = run_conversational_turn(
            store, _req("iso-A", f"A-{i}", a["turns"][i]["query"]),
            _adapters(served), "w", sender,
        )
        outcomes[("B", i)] = run_conversational_turn(
            store, _req("iso-B", f"B-{i}", b["turns"][i]["query"]),
            _adapters(served), "w", sender,
        )

    # Two distinct conversations, each delivered, no cross-talk.
    conv_a = {outcomes[("A", i)].conversation_id for i in range(2)}
    conv_b = {outcomes[("B", i)].conversation_id for i in range(2)}
    assert len(conv_a) == 1 and len(conv_b) == 1
    assert conv_a.isdisjoint(conv_b)
    for k, out in outcomes.items():
        assert out.status == "delivered"

    # Per-conversation state_version advances independently (isolation of order).
    assert outcomes[("A", 0)].state_version == 1
    assert outcomes[("A", 1)].state_version == 2
    assert outcomes[("B", 0)].state_version == 1
    assert outcomes[("B", 1)].state_version == 2

    # Dedup: re-driving A-0 with the SAME update_id neither recomputes nor resends.
    n_generations = len(served)
    dup = run_conversational_turn(
        store, _req("iso-A", "A-0", a["turns"][0]["query"]),
        _adapters(served), "w", sender,
    )
    assert dup.is_new_event is False
    assert dup.status in ("already_delivered", "awaiting_delivery")
    assert len(served) == n_generations  # no extra compute


def test_stub_resolve_never_runs_in_contract_plumbing():
    # Belt-and-braces: the stub must not be silently swallowed — a direct call
    # raises, guaranteeing the eval can distinguish "pending" from "passing".
    with pytest.raises(PolicyNotImplemented):
        StubConversationPolicy().resolve(
            query="x", turn_models=[], available_models=None,
            working_state=WorkingState(), now=datetime(2026, 7, 23),
        )
