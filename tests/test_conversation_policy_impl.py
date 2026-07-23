"""MT-1a tests: the deterministic router (per route), the rewriter's fail-closed
post-validation, the carry_forward fallback, the NON_PRODUCT_CODES trap, the 1h
window boundary — and the GATE: the real policy satisfies all 31 MT-1b turns.

$0: no real API call (fake Anthropic client), no DB (turn_models passed directly
where the router is exercised in isolation; the composition path uses the pure
regex detector).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.orchestrator.conversation_policy import (  # noqa: E402
    NON_PRODUCT_CODES,
    PolicyRoute,
    WorkingState,
    default_policy,
)
from src.orchestrator.conversation_policy_impl import (  # noqa: E402
    DeterministicConversationPolicy,
    advance_working_state,
    detect_turn_signals,
    resolve_conversational_turn,
)
from src.orchestrator.rewriter import (  # noqa: E402
    REWRITE_PROMPT_CONDENSE_LC,
    REWRITE_PROMPT_FONTIBER,
    make_rewriter,
    validate_rewrite,
)

import test_multiturn_vs_gold as harness  # noqa: E402

BASE = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
POLICY = DeterministicConversationPolicy()


def _resolve(query, turn_models, ws=None, now=None, available=None, rewrite=None):
    return POLICY.resolve(
        query=query,
        turn_models=turn_models,
        available_models=available,
        working_state=ws or WorkingState(),
        now=now or BASE,
        rewrite=rewrite,
    )


def _state(models, *, at=BASE, last_query="prev", available=None):
    return WorkingState(
        last_target_models=tuple(models),
        last_query=last_query,
        last_turn_at=at,
        available_models=tuple(available) if available else None,
    )


# ===========================================================================
# Fake Anthropic client (mirrors response.content[0].text)
# ===========================================================================
class _Block:
    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, producer):
        self._producer = producer

    def create(self, **kwargs):
        text = self._producer(kwargs) if callable(self._producer) else self._producer
        return _Resp(text)


class FakeClient:
    def __init__(self, producer):
        self.messages = _Messages(producer)


# ===========================================================================
# 1. Router — one test per route
# ===========================================================================
def test_A_explicit_product_standalone_wins_over_state():
    r = _resolve("¿y en la CAD-150 cómo van las baterías?", ["CAD-150"],
                 ws=_state(["CAD-250"]))
    assert r.route is PolicyRoute.STANDALONE
    assert r.target_models == ("CAD-150",)
    assert "CAD-250" not in (r.target_models or ())  # no leak
    assert r.requires_llm_rewrite is False


def test_A_self_correction_replaces_not_unions():
    r = _resolve("perdón, me refería a la ID2000", ["ID2000"], ws=_state(["ID3000"]))
    assert r.route is PolicyRoute.STANDALONE
    assert set(r.target_models) == {"ID2000"}  # not {ID2000, ID3000}


def test_B_brand_switch_out_of_corpus_drops_state():
    # extract_product_models returns [] for Bosch Avenar FPA-1200 (verified).
    r = _resolve("¿y la Bosch Avenar FPA-1200 cómo se programa?", [], ws=_state(["ID3000"]))
    assert r.route is PolicyRoute.STANDALONE
    assert "ID3000" not in (r.target_models or ())
    assert r.rationale.startswith("new_brand")


def test_C_out_of_domain_gas_declines_only_without_product():
    r = _resolve("¿cómo enciendo la caldera de gas de casa?", [], ws=WorkingState())
    assert r.route is PolicyRoute.DECLINE
    assert r.decline_reason
    # In-corpus gas DETECTOR must NOT decline (explicit product wins first).
    r2 = _resolve("¿MTBF del detector de gas DGD-600?", ["DGD-600"], ws=WorkingState())
    assert r2.route is PolicyRoute.STANDALONE


def test_G_carry_forward_preserves_query_verbatim_and_appends_hint():
    r = _resolve("¿y qué contraseña trae por defecto?", [], ws=_state(["CAD-250"]),
                 now=BASE + timedelta(seconds=120))
    assert r.route is PolicyRoute.CARRY_FORWARD
    assert r.target_models == ("CAD-250",)
    assert r.requires_llm_rewrite is False
    assert r.query_for_retrieval.startswith("¿y qué contraseña trae por defecto?")
    assert "CAD-250" in r.query_for_retrieval  # hint appended, not substituted


def test_F_content_anaphor_rewrite_defers_when_no_rewriter():
    r = _resolve("¿y ese aviso cómo se borra una vez localizado?", [],
                 ws=_state(["AFP-400"]), now=BASE + timedelta(seconds=90))
    assert r.route is PolicyRoute.REWRITE
    assert r.requires_llm_rewrite is True
    assert r.rewritten_query is None  # $0 contract: never fabricate
    assert r.target_models == ("AFP-400",)


def test_E_family_divergence_clarifies():
    r = _resolve("¿cuántos lazos y zonas puedo configurar?", [], ws=_state(["ZXSE"]),
                 now=BASE + timedelta(seconds=60))
    assert r.route is PolicyRoute.CLARIFY
    assert r.clarify_question
    assert r.requires_llm_rewrite is False


def test_E_family_invariant_attribute_answers_not_clarify():
    # DEC-092: end-of-line resistance is invariant across the e-series -> answer.
    r = _resolve("¿cuál es la resistencia de fin de línea recomendada para los lazos?",
                 [], ws=_state(["ZXE"]), now=BASE + timedelta(seconds=60))
    assert r.route is PolicyRoute.CARRY_FORWARD
    assert r.target_models == ("ZXE",)


def test_H_dangling_anaphor_no_antecedent_clarifies_and_leaks_nothing():
    # Expired window: the pronoun "su" has no antecedent -> clarify, drop product.
    r = _resolve("¿y cuál es su tensión de alimentación?", [], ws=_state(["DGD-600"]),
                 now=BASE + timedelta(seconds=4200))  # 70 min > 3600
    assert r.route is PolicyRoute.CLARIFY
    assert "DGD-600" not in (r.target_models or ())
    assert r.clarify_question


# ===========================================================================
# 2. NON_PRODUCT_CODES trap (S99b / DEC-092)
# ===========================================================================
def test_rs485_trap_does_not_change_product():
    # extract_product_models('...RS485...') -> ['RS-485'] (false positive).
    r = _resolve("¿la comunicación con los módulos va por RS485 o por el lazo?",
                 ["RS-485"], ws=_state(["CAD-250"]), now=BASE + timedelta(seconds=60))
    assert r.route is PolicyRoute.CARRY_FORWARD
    assert r.target_models == ("CAD-250",)
    assert "RS-485" not in (r.target_models or ())
    assert "RS485" in r.query_for_retrieval  # raw token preserved verbatim


def test_non_product_codes_are_the_seed_denylist():
    assert "RS-485" in NON_PRODUCT_CODES and "EN-54" in NON_PRODUCT_CODES


# ===========================================================================
# 3. 1h window boundary
# ===========================================================================
def test_window_boundary_pins_3600s():
    ws = _state(["DGD-600"])
    inside = _resolve("¿y su tensión de alimentación?", [], ws=ws,
                      now=BASE + timedelta(seconds=3599))
    assert inside.route is PolicyRoute.CARRY_FORWARD
    outside = _resolve("¿y su tensión de alimentación?", [], ws=ws,
                       now=BASE + timedelta(seconds=3600))
    assert outside.route is PolicyRoute.CLARIFY


# ===========================================================================
# 4. Rewriter post-validation (fail-closed)
# ===========================================================================
def _m710_state():
    return _state(["M710", "MI-DMMI"],
                  last_query="¿Cómo se cablea el módulo de entrada M710 / MI-DMMI?")


def test_validate_ok_when_codes_preserved():
    ok, reason = validate_rewrite(
        "¿y qué resistencia de fin de línea necesita esa entrada?",
        _m710_state(),
        "¿Qué resistencia de fin de línea necesita la entrada M710 / MI-DMMI?",
    )
    assert ok, reason


def test_validate_fails_when_target_code_dropped():
    ok, reason = validate_rewrite(
        "¿y qué resistencia de fin de línea necesita esa entrada?",
        _m710_state(),
        "¿Qué resistencia de fin de línea necesita esa entrada?",  # dropped codes
    )
    assert not ok and "dropped" in reason


def test_validate_fails_when_raw_turn_token_mutated():
    ws = _state(["CAD-250"])
    ok, _ = validate_rewrite("¿la comunicación va por RS485?", ws,
                             "¿La comunicación de la CAD-250 va por RS-485?")  # RS485 -> RS-485
    assert not ok  # RS485 (raw token + NON_PRODUCT_CODE) not verbatim


def test_validate_fails_empty_and_too_long():
    ws = _m710_state()
    assert not validate_rewrite("q?", ws, "")[0]
    assert not validate_rewrite("q?", ws, "x" * 5000)[0]


# ===========================================================================
# 5. Rewriter wired into the policy (fake client) + fallback to carry_forward
# ===========================================================================
def test_rewriter_valid_output_produces_rewrite_route():
    good = "¿Qué resistencia de fin de línea necesita la entrada M710 / MI-DMMI?"
    rw = make_rewriter(client=FakeClient(good), prompt_variant="fontiber")
    r = _resolve("¿y qué resistencia de fin de línea necesita esa entrada?", [],
                 ws=_m710_state(), now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.REWRITE
    assert r.rewritten_query == good
    assert "M710" in r.query_for_retrieval and "MI-DMMI" in r.query_for_retrieval


def test_rewriter_invalid_output_falls_back_to_carry_forward():
    bad = "¿Qué resistencia de fin de línea necesita esa entrada?"  # drops the codes
    rw = make_rewriter(client=FakeClient(bad), prompt_variant="fontiber")
    r = _resolve("¿y qué resistencia de fin de línea necesita esa entrada?", [],
                 ws=_m710_state(), now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.CARRY_FORWARD  # $-spent but safe conduct
    assert r.requires_llm_rewrite is False
    assert "rewrite_failed" in r.rationale


def test_rewriter_client_exception_falls_back():
    class _Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("network down")

    rw = make_rewriter(client=_Boom(), prompt_variant="fontiber")
    r = _resolve("¿y ese aviso cómo se borra?", [], ws=_state(["AFP-400"]),
                 now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.CARRY_FORWARD


def test_condense_lc_variant_builds_and_validates():
    captured = {}

    def producer(kw):
        captured.update(kw)
        return "¿Cómo se borra el aviso Earth Fault en la AFP-400?"

    rw = make_rewriter(client=FakeClient(producer), prompt_variant="condense_lc")
    ws = _state(["AFP-400"],
                last_query="La AFP-400 muestra el aviso 'Tierra' (Earth Fault).")
    r = _resolve("¿y ese aviso cómo se borra?", [], ws=ws,
                 now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.REWRITE
    # condense_lc sends a single user block, no system prompt.
    assert "system" not in captured
    assert "Entrada de seguimiento" in captured["messages"][0]["content"]


def test_prompt_variants_are_distinct_and_present():
    assert "VERBATIM" in REWRITE_PROMPT_FONTIBER
    assert "pregunta autónoma" in REWRITE_PROMPT_CONDENSE_LC.lower()
    with pytest.raises(ValueError):
        make_rewriter(client=FakeClient("x"), prompt_variant="nope")


# ===========================================================================
# 6. Composition seam + state advance
# ===========================================================================
def test_resolve_conversational_turn_composes_and_advances_state():
    ws0 = WorkingState()
    res1, ws1 = resolve_conversational_turn(
        "En la Detnov CAD-250, ¿cómo entro al menú?", ws0, BASE)
    assert res1.route is PolicyRoute.STANDALONE
    assert ws1.last_target_models == ("CAD-250",)
    res2, ws2 = resolve_conversational_turn(
        "¿y la contraseña por defecto?", ws1, BASE + timedelta(seconds=60))
    assert res2.route is PolicyRoute.CARRY_FORWARD
    assert ws2.last_target_models == ("CAD-250",)


def test_advance_state_preserves_model_on_clarify():
    ws = _state(["CAD-250"])
    clarify = _resolve("¿y su tensión?", [], ws=ws, now=BASE + timedelta(seconds=4200))
    assert clarify.route is PolicyRoute.CLARIFY
    ws2 = advance_working_state(ws, clarify, "¿y su tensión?", None,
                                BASE + timedelta(seconds=4200), None)
    # Clarify does not disambiguate: prior model kept, timestamp refreshed.
    assert ws2.last_target_models == ("CAD-250",)


def test_detect_turn_signals_is_pure_regex():
    models, _ = detect_turn_signals("En la Detnov CAD-250, ¿cómo entro?")
    assert "CAD-250" in models


# ===========================================================================
# 7. THE GATE — the real policy satisfies all 31 MT-1b turns
# ===========================================================================
def test_real_policy_satisfies_all_multiturn_golds():
    flows = harness.load_flows()
    report = harness.run_contract(flows, policy=DeterministicConversationPolicy())
    assert report["policy_stub"] is False
    assert report["fail"] == 0, report["failures"]
    assert report["pass"] == report["turns"] == 31


def test_default_policy_is_stub_by_default_and_real_when_activated(monkeypatch):
    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)
    assert getattr(default_policy(), "IS_STUB", False) is True  # frozen contract stays green
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    active = default_policy()
    assert getattr(active, "IS_STUB", True) is False
    assert isinstance(active, DeterministicConversationPolicy)
