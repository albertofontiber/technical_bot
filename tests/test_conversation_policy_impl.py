"""MT-1a tests: the deterministic router (per route), the rewriter's fail-closed
post-validation, the CLARIFY fallback, the NON_PRODUCT_CODES trap, the 1h window
boundary — and the GATE: the real policy satisfies all MT-1b turns (48 after the
s281 round-2 hardening).

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


def test_validate_fails_on_fabricated_superset_code_m7100():
    # sol-S1/F5: token-boundary match. "M710" IS a substring of "M7100", so the old
    # `tok in text` passed a rewrite that mutated M710 -> M7100. Boundary catches it.
    ok, reason = validate_rewrite(
        "¿y qué resistencia de fin de línea necesita esa entrada?",
        _m710_state(),
        "¿Qué resistencia de fin de línea necesita la entrada M7100 / MI-DMMI?",
    )
    assert not ok
    assert "dropped" in reason or "fabricated" in reason  # M710 missing / M7100 invented


def test_validate_fails_on_fabricated_unrelated_code_afp2800():
    # Anti-invention: the source only has AFP-400; a rewrite that mints AFP-2800 is
    # a fabricated model even though nothing was "dropped".
    ws = _state(["AFP-400"], last_query="La AFP-400 muestra el aviso 'Tierra'.")
    ok, reason = validate_rewrite(
        "¿y ese aviso cómo se borra?",
        ws,
        # keeps the real AFP-400 (so the DROP gate passes) but MINTS AFP-2800:
        "¿Cómo se borra el aviso de la AFP-400 (o la AFP-2800)?",
    )
    assert not ok and "fabricated" in reason


def test_validate_allows_faithful_reorganization():
    # A rewrite that only reorganizes SOURCE tokens (no new codes) passes both gates.
    ws = _state(["AFP-400"], last_query="La AFP-400 muestra el aviso 'Tierra' (Earth Fault).")
    ok, reason = validate_rewrite(
        "¿y ese aviso cómo se borra?", ws,
        "¿Cómo se borra el aviso Earth Fault en la AFP-400?",
    )
    assert ok, reason


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


def test_rewriter_invalid_output_falls_back_to_clarify():
    # sol-S2 fix: a failed rewrite must NOT re-attach (carry_forward) — the cascade
    # already judged the re-attach insufficient. Clarify the antecedent instead.
    bad = "¿Qué resistencia de fin de línea necesita esa entrada?"  # drops the codes
    rw = make_rewriter(client=FakeClient(bad), prompt_variant="fontiber")
    r = _resolve("¿y qué resistencia de fin de línea necesita esa entrada?", [],
                 ws=_m710_state(), now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.CLARIFY  # $-spent but safe conduct (not carry_forward)
    assert r.requires_llm_rewrite is False
    assert r.clarify_question
    assert "rewrite_failed" in r.rationale and "$-spent" in r.rationale


def test_rewriter_client_exception_falls_back_to_clarify():
    class _Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("network down")

    rw = make_rewriter(client=_Boom(), prompt_variant="fontiber")
    r = _resolve("¿y ese aviso cómo se borra?", [], ws=_state(["AFP-400"]),
                 now=BASE + timedelta(seconds=60), rewrite=rw)
    assert r.route is PolicyRoute.CLARIFY
    assert r.clarify_question


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
# 6b. s281 round-2 hardening — focused unit tests for the adjudicated fixes
# ===========================================================================
def test_articles_are_not_a_dependency_signal_standalone():
    # ARTICULOS (orq+sol-S3/F1): a self-contained question with articles and NO
    # state must route STANDALONE, not clarify.
    for q in (
        "¿Cómo se silencia la alarma acústica una vez verificada la incidencia?",
        "¿Qué sección mínima de cable exige la normativa para los lazos?",
        "¿Cada cuánto conviene revisar las conexiones de tierra?",
    ):
        r = _resolve(q, [], ws=WorkingState())
        assert r.route is PolicyRoute.STANDALONE, q
        assert r.target_models == ()


def test_brand_gate_split_switch_vs_compat_vs_same_brand():
    st = _state(["CAD-250"])  # Detnov in window
    n = BASE + timedelta(seconds=60)
    # brand + model-type token -> switch (drop state).
    sw = _resolve("¿y la Bosch Avenar FPA-1200 cómo se programa?", [], ws=st, now=n)
    assert sw.route is PolicyRoute.STANDALONE and sw.target_models == ()
    # brand alone, in window -> compatibility follow-up -> carry_forward, keep state.
    co = _resolve("¿es compatible con equipos Hochiki?", [], ws=st, now=n)
    assert co.route is PolicyRoute.CARRY_FORWARD and co.target_models == ("CAD-250",)
    # SAME manufacturer named -> exempt (not a switch) -> carry_forward, keep state.
    sm = _resolve("¿y Detnov fabrica algo con más lazos?", [], ws=st, now=n)
    assert sm.route is PolicyRoute.CARRY_FORWARD and sm.target_models == ("CAD-250",)


def test_gas_gate_never_declines_an_in_window_continuation():
    # F4: in-window state + a gas-lexicon follow-up (boiler cutoff) -> carry_forward,
    # NOT decline. A fresh out-of-domain turn still declines.
    st = _state(["CAD-250"])
    r = _resolve("¿y cómo programo el corte de la caldera de gas al saltar la alarma?",
                 [], ws=st, now=BASE + timedelta(seconds=300))
    assert r.route is PolicyRoute.CARRY_FORWARD and r.target_models == ("CAD-250",)
    fresh = _resolve("¿cómo enciendo la caldera de gas de casa?", [], ws=WorkingState())
    assert fresh.route is PolicyRoute.DECLINE


def test_clarify_does_not_resurrect_expired_product():
    # RESURRECCION (sol-S4/F2): a clarify on an expired window must not refresh the
    # timestamp, or a next dangling turn would carry the stale product forward.
    ws = _state(["DGD-600"], at=BASE)
    n2 = BASE + timedelta(seconds=4200)  # 70 min -> expired
    r2 = _resolve("¿y cuál es su tensión?", [], ws=ws, now=n2)
    assert r2.route is PolicyRoute.CLARIFY
    ws2 = advance_working_state(ws, r2, "¿y cuál es su tensión?", None, n2, None)
    assert ws2.last_turn_at == ws.last_turn_at  # NOT refreshed -> still expired
    r3 = _resolve("¿y su consumo en reposo?", [], ws=ws2, now=BASE + timedelta(seconds=4320))
    assert r3.route is PolicyRoute.CLARIFY  # not carry_forward
    assert "DGD-600" not in (r3.target_models or ())


def test_extended_demonstratives_route_to_rewrite():
    # ANAPHOR-RE (F6): esos/este were missed by the old es[ae]s? regex.
    st = _state(["ID3000"])
    n = BASE + timedelta(seconds=60)
    for q in ("¿y esos avisos cómo se gestionan?", "¿y este elemento cómo se direcciona?"):
        r = _resolve(q, [], ws=st, now=n)
        assert r.route is PolicyRoute.REWRITE, q
        assert r.target_models == ("ID3000",)


def test_neuter_eso_still_carries_forward_not_rewrite():
    # The neuter "eso," (discourse filler) must not become a content anaphora.
    st = _state(["ID2000"])
    r = _resolve("eso, ¿cómo se conecta un módulo de aislamiento en su lazo?", [],
                 ws=st, now=BASE + timedelta(seconds=20))
    assert r.route is PolicyRoute.CARRY_FORWARD


def test_normative_code_is_not_a_product():
    # CODIGOS-NORMATIVOS (sol-S6): a standards code must not read as an explicit
    # product (would wrongly STANDALONE on it). With state present it carries forward.
    st = _state(["CAD-250"])
    r = _resolve("¿y cumple la EN-54 en esa configuración?", ["EN-54"], ws=st,
                 now=BASE + timedelta(seconds=60))
    assert r.route is not PolicyRoute.STANDALONE
    assert "EN-54" not in (r.target_models or ())


def test_family_clarify_uses_variant_list():
    # VARIANTES (F7): the clarify text is rendered from _FamilySpec.variants.
    r = _resolve("¿cuántos lazos y zonas puedo configurar?", [], ws=_state(["ZXE"]),
                 now=BASE + timedelta(seconds=60))
    assert r.route is PolicyRoute.CLARIFY
    assert "1/2/5" in r.clarify_question and "1/2/5/10" not in r.clarify_question


def test_first_message_clarify_text_omits_time_passed():
    # F8: a genuine first message (empty state) must not claim time has passed.
    r = _resolve("¿y cuál es su tensión?", [], ws=WorkingState())
    assert r.route is PolicyRoute.CLARIFY
    assert "Ha pasado" not in r.clarify_question


# ===========================================================================
# 7. THE GATE — the real policy satisfies all MT-1b turns (48 after hardening)
# ===========================================================================
def test_real_policy_satisfies_all_multiturn_golds():
    flows = harness.load_flows()
    report = harness.run_contract(flows, policy=DeterministicConversationPolicy())
    assert report["policy_stub"] is False
    assert report["fail"] == 0, report["failures"]
    assert report["pass"] == report["turns"] == 48


def test_default_policy_is_stub_by_default_and_real_when_activated(monkeypatch):
    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)
    assert getattr(default_policy(), "IS_STUB", False) is True  # frozen contract stays green
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    active = default_policy()
    assert getattr(active, "IS_STUB", True) is False
    assert isinstance(active, DeterministicConversationPolicy)


# ===========================================================================
# 8. --e2e core (REAL wiring, exercised with FAKES — $0, no API, no DB)
# ===========================================================================
def test_e2e_core_runs_with_fakes_and_stamps_cost(monkeypatch):
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")  # real policy for the drive
    from src.orchestrator import replay_adapters

    flows = [f for f in harness.load_flows()
             if f["flow_id"] in ("mt01_followup_cad250", "mt02_pron_afp400")]

    def fake_rewrite(q, ws):  # valid, source-bound (policy calls it on REWRITE)
        return "¿Cómo se borra el aviso Earth Fault en la AFP-400?"

    def gen(query, chunks, *, available_models=None):
        return {"answer": f"[ans] {query}", "diagrams": [],
                "input_tokens": 100, "output_tokens": 20}

    adapters = replay_adapters(
        retrieved=[{"id": "c0", "content": "ctx", "similarity": 0.9}], generate=gen)

    def fake_judge(*, question, expected, gold, bot):
        return {"veredicto": "PASS", "usage": {"in": 50, "out": 10}}

    report = harness.run_e2e_flows(
        flows, rewrite=fake_rewrite, adapters=adapters, judge_fn=fake_judge, judge_k=3)

    assert report["mode"] == "e2e"
    assert len(report["flow_results"]) == 2
    assert all(fr["veredicto"] == "PASS" for fr in report["flow_results"])
    c = report["cost"]
    assert c["judge_calls"] == 6            # 2 flows * K=3
    assert c["rewrite_calls"] >= 1          # mt02 t2 is a REWRITE route
    assert c["generate_calls"] >= 3         # standalone + carry/rewrite turns
    assert c["generate_input_tokens"] > 0 and c["judge_input_tokens"] > 0
    assert "usd_estimate" in c and c["usd_estimate"] >= 0
