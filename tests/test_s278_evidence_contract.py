"""s278 §5 — Evidence Contract v1 (flag ``EVIDENCE_CONTRACT``, default off).

Contratos verificados (diseño ``evals/s278_vnext_design_v2.md`` §5 + tabla
``evals/s278_ec_item_table_v1.md``):

  - inercia byte-exacta con flag off, en el seam del generador (el módulo NI se
    importa) y en el oráculo offline (replay de 3 etapas intacto);
  - APPEND de span servido-no-citado (espejo hp018:r2, universal_compound);
  - DISCLOSE determinista de conteo declarado vs enumeración servida (espejo
    hp017 seis-vs-siete) con ambos valores y ambas citas;
  - ARITHMETIC solo con operandos anclados en spans servidos (espejo hp012
    ``4 × (99 + 99) = 792``) y negativo sin operandos;
  - fail-closed: sin fuente citable no se actúa (silencio > invención);
  - cap propio (3) con orden estable seguridad-primero;
  - receipt con clase, span-hash, fuente y motivo; idempotencia;
  - cero identificadores de eval (qid/gold) en el módulo de runtime.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import src.rag.generator as gen
from src.rag import evidence_contract as ec
from src.rag.evidence_contract import apply_evidence_contract
from scripts import s277_c1_p1_offline_counterfactual as preflight


# ───────────────────────────── fixtures deterministas ─────────────────────────────

def _card(content: str, *, source_file="manual-x.pdf", page=5, **extra) -> dict:
    row = {
        "content": content,
        "source_file": source_file,
        "page_number": page,
        "similarity": 0.9,
        "product_model": "ZX5e",
        "section_title": "Instalación",
        "content_type": "manual",
    }
    row.update(extra)
    return row


# Espejo hp018:r2#0 (MIE-MI-530rv001 p20): cláusula universal compuesta servida
# y NO citada por la respuesta.
_UNIVERSAL_SPAN = (
    "Cada circuito de sirena se supervisa ante cortocircuito y circuito abierto."
)
_UNIVERSAL_CARD = _card(
    "Conexión de sirenas de la ZX5e.\n\n" + _UNIVERSAL_SPAN,
    source_file="MIE-MI-530rv001.pdf",
    page=20,
)
_UNIVERSAL_QUESTION = "¿Cuántos circuitos de sirena supervisados tiene la ZX5e?"
_UNIVERSAL_ANSWER = "La ZX5e dispone de 4 circuitos de sirena [F1]."

# Espejo hp017#3 (997-671-005-3 p44, DEC-128): prosa declara SEIS tipos, la
# enumeración servida lista SIETE etiquetas.
_SIX_SEVEN_COUNT_SPAN = (
    "El panel permite seleccionar uno de seis tipos de retardo para las sirenas:"
)
_SIX_SEVEN_CARD = _card(
    "Retardos de sirena.\n"
    + _SIX_SEVEN_COUNT_SPAN
    + "\n- Fijo\n- Estandar\n- No Silenc\n- Est. Ext.\n- RetExtStd\n"
    "- No Sil. Ext\n- SinRetExt",
    source_file="997-671-005-3_Configuration_ES.pdf",
    page=44,
)
_SIX_SEVEN_QUESTION = "¿Cuántos tipos de retardo de sirena puedo configurar?"
_SIX_SEVEN_ANSWER = "Puede configurar seis tipos de retardo de sirena [F1]."

# Espejo hp012#3 (15088SP p61): «792» NO servido; los operandos SÍ.
_ARITHMETIC_CARD = _card(
    "Capacidad del sistema.\n"
    "El AFP1010 admite un maximo de dos LIB-400 (un total de cuatro SLC de "
    "lazo). Cada lazo SLC soporta hasta 99 detectores inteligentes y hasta 99 "
    "modulos direccionables.",
    source_file="15088SP.pdf",
    page=61,
)
_ARITHMETIC_QUESTION = "¿Cuántos dispositivos soporta en total el AFP1010?"
_ARITHMETIC_ANSWER = "El AFP1010 admite dos LIB-400 [F1]."

# Advertencia MANDATORY con forma-buena (trigger léxico + verbo conjugado).
_WARNING_SPAN = (
    "ADVERTENCIA: antes de conectar las bases del lazo deben desconectarse la "
    "alimentación y las baterías del equipo."
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ───────────────────────────── seam del generador ─────────────────────────────

class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._text)],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
        )


def _fake_anthropic(monkeypatch, text):
    fake = _FakeMessages(text)
    monkeypatch.setattr(
        gen.anthropic, "Anthropic",
        lambda api_key=None: SimpleNamespace(messages=fake),
    )
    return fake


def test_flag_off_seam_is_byte_inert_and_never_imports_the_module(monkeypatch):
    monkeypatch.delenv("EVIDENCE_CONTRACT", raising=False)
    _fake_anthropic(monkeypatch, _UNIVERSAL_ANSWER)
    saved = sys.modules.pop("src.rag.evidence_contract")
    try:
        result = gen.generate_answer(_UNIVERSAL_QUESTION, [dict(_UNIVERSAL_CARD)])
        # Byte-inerte: ni rastro del contrato en la respuesta ni en el dict.
        assert result["answer"] == _UNIVERSAL_ANSWER
        assert "evidence_contract" not in result
        assert ec.APPENDIX_HEADER not in result["answer"]
        # Con flag off el módulo NI SE IMPORTA (contrato del seam).
        assert "src.rag.evidence_contract" not in sys.modules
    finally:
        sys.modules["src.rag.evidence_contract"] = saved


def test_flag_on_seam_appends_served_uncited_span_after_conflict_guard(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CONTRACT", "on")
    _fake_anthropic(monkeypatch, _UNIVERSAL_ANSWER)
    result = gen.generate_answer(_UNIVERSAL_QUESTION, [dict(_UNIVERSAL_CARD)])
    assert result["answer"].startswith(_UNIVERSAL_ANSWER)
    assert ec.APPENDIX_HEADER in result["answer"]
    assert _UNIVERSAL_SPAN in result["answer"]
    assert "(MIE-MI-530rv001, p. 20) [F1]" in result["answer"]
    receipt = result["evidence_contract"]
    assert receipt["schema"] == ec.SCHEMA
    assert receipt["appended_entries"] == 1
    [action] = receipt["actions"]
    assert action["action"] == "append"
    assert action["class"] == ec.CLASS_UNIVERSAL
    assert action["source_file"] == "MIE-MI-530rv001.pdf"
    assert action["span_sha256"] == _sha256(_UNIVERSAL_SPAN)
    assert "reason" in action


def test_flag_on_seam_fails_open_on_contract_exception(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CONTRACT", "on")
    _fake_anthropic(monkeypatch, _UNIVERSAL_ANSWER)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(ec, "apply_evidence_contract", _boom)
    result = gen.generate_answer(_UNIVERSAL_QUESTION, [dict(_UNIVERSAL_CARD)])
    assert result["answer"] == _UNIVERSAL_ANSWER  # respuesta intacta (fail-open)
    assert result["evidence_contract"]["status"] == "error"
    assert result["evidence_contract"]["error_type"] == "RuntimeError"


# ───────────────────────── APPEND espejo hp018:r2 (módulo) ─────────────────────────

def test_append_served_uncited_universal_compound_hp018_mirror():
    result = apply_evidence_contract(
        _UNIVERSAL_ANSWER, [dict(_UNIVERSAL_CARD)], _UNIVERSAL_QUESTION
    )
    assert result["text"].startswith(_UNIVERSAL_ANSWER)
    assert f'- "{_UNIVERSAL_SPAN}" (MIE-MI-530rv001, p. 20) [F1]' in result["text"]
    assert "📖" in result["text"]  # sin seguridad ni disclose → emoji genérico
    [action] = result["actions"]
    assert action["class"] == ec.CLASS_UNIVERSAL
    assert action["fragment_number"] == 1
    assert action["page_number"] == 20


def test_no_action_when_answer_already_covers_the_obligation():
    covered = _UNIVERSAL_ANSWER + " " + _UNIVERSAL_SPAN
    result = apply_evidence_contract(
        covered, [dict(_UNIVERSAL_CARD)], _UNIVERSAL_QUESTION
    )
    assert result["actions"] == []
    assert result["text"] is covered  # MISMO objeto → byte-idéntico
    assert result["receipt"]["unsatisfied"] == 0


# ───────────────────────── DISCLOSE espejo hp017 (seis-vs-siete) ─────────────────────────

def test_disclose_declared_six_vs_enumerated_seven_hp017_mirror():
    result = apply_evidence_contract(
        _SIX_SEVEN_ANSWER, [dict(_SIX_SEVEN_CARD)], _SIX_SEVEN_QUESTION
    )
    text = result["text"]
    # Plantilla determinista con AMBOS valores y AMBAS citas (léxico de
    # disclosure de must_preserve → un F-COUNT en conflicto queda satisfecho).
    assert "la fuente es inconsistente" in text
    assert "declara 6 tipos" in text
    assert "lista 7" in text
    assert text.count("(997-671-005-3_Configuration_ES, p. 44) [F1]") == 2
    assert "📋" in text
    [action] = result["actions"]
    assert action["action"] == "disclose"
    assert action["class"] == ec.CLASS_ATTRIBUTION
    assert action["kind"] == "declared_vs_enumerated"
    assert action["counterpart"]["fragment_number"] == 1
    assert len(action["counterpart"]["span_sha256"]) == 64


def test_contract_is_idempotent_over_its_own_output():
    first = apply_evidence_contract(
        _SIX_SEVEN_ANSWER, [dict(_SIX_SEVEN_CARD)], _SIX_SEVEN_QUESTION
    )
    assert first["actions"]
    second = apply_evidence_contract(
        first["text"], [dict(_SIX_SEVEN_CARD)], _SIX_SEVEN_QUESTION
    )
    assert second["actions"] == []
    assert second["text"] is first["text"]


# ───────────────────────── ARITHMETIC espejo hp012 ─────────────────────────

def test_arithmetic_derivation_with_served_operands_hp012_mirror():
    result = apply_evidence_contract(
        _ARITHMETIC_ANSWER, [dict(_ARITHMETIC_CARD)], _ARITHMETIC_QUESTION
    )
    text = result["text"]
    assert "4 × (99 + 99) = 792" in text
    assert "operandos citados" in text
    assert '"hasta 99 detectores"' in text
    [action] = result["actions"]
    assert action["class"] == ec.CLASS_ARITHMETIC
    assert action["derivation"] == "4 × (99 + 99) = 792"
    assert len(action["operand_sha256"]) == 3


def test_arithmetic_negative_without_both_served_operands():
    # Solo UN sumando servido → jamás se deriva (los operandos deben estar
    # TODOS en spans servidos; ninguna otra obligación aplica a esta pregunta).
    partial = _card(
        "Capacidad del sistema.\n"
        "El AFP1010 admite un maximo de dos LIB-400 (un total de cuatro SLC de "
        "lazo). Cada lazo SLC soporta hasta 99 detectores inteligentes.",
        source_file="15088SP.pdf",
        page=61,
    )
    result = apply_evidence_contract(
        _ARITHMETIC_ANSWER, [partial], _ARITHMETIC_QUESTION
    )
    assert result["actions"] == []
    assert result["text"] is _ARITHMETIC_ANSWER
    assert "792" not in result["text"]


def test_arithmetic_negative_when_total_already_answered():
    answered = "El AFP1010 soporta un total de 792 dispositivos [F1]."
    result = apply_evidence_contract(
        answered, [dict(_ARITHMETIC_CARD)], _ARITHMETIC_QUESTION
    )
    assert result["actions"] == []
    assert result["text"] is answered


# ───────────────────────── fail-closed + cap + receipt ─────────────────────────

def test_fail_closed_without_citable_source():
    uncitable = dict(_UNIVERSAL_CARD)
    uncitable["source_file"] = ""  # sin fuente no hay cita → no se actúa
    result = apply_evidence_contract(
        _UNIVERSAL_ANSWER, [uncitable], _UNIVERSAL_QUESTION
    )
    assert result["actions"] == []
    assert result["text"] is _UNIVERSAL_ANSWER
    assert result["receipt"]["skipped_unanchored"] == 1
    assert result["receipt"]["unsatisfied"] == 1


def test_append_cap_with_stable_safety_first_order():
    content = "\n\n".join(
        [
            "Instalación del lazo de detección.",
            _WARNING_SPAN,
            "Cada detector del lazo debe llevar su base con el diodo de bloqueo "
            "montado y orientado.",
            "Todos los detectores del lazo deben quedar numerados y rotulados en "
            "el plano de la instalación.",
            "Cada base del lazo se conecta con polaridad directa y cable "
            "apantallado de dos hilos.",
            "Todas las bases del lazo deben revisarse periódicamente y limpiarse "
            "con aire comprimido.",
        ]
    )
    question = "¿Cómo se conectan los detectores y las bases del lazo?"
    answer = "Los detectores se montan en sus bases [F1]."
    result = apply_evidence_contract(answer, [_card(content)], question)
    receipt = result["receipt"]
    assert receipt["appended_entries"] == ec.APPEND_CAP == 3
    assert receipt["cap_reached"] is True
    # Orden ESTABLE: seguridad primero (precedente must_preserve v2).
    assert receipt["actions"][0]["class"] == ec.CLASS_SAFETY
    assert result["text"].index(_WARNING_SPAN) < result["text"].index(
        "Cada detector del lazo"
    )
    assert "⚠️" in result["text"]
    for action in receipt["actions"]:
        # Receipt: clase + span-hash + fuente + motivo en CADA acción.
        assert action["class"] in (ec.CLASS_SAFETY, ec.CLASS_UNIVERSAL)
        assert len(action["span_sha256"]) == 64
        assert action["source_file"] == "manual-x.pdf"
        assert action["reason"]


def test_empty_context_or_answer_is_inert():
    result = apply_evidence_contract("", [dict(_UNIVERSAL_CARD)], "pregunta")
    assert result["actions"] == []
    assert result["receipt"]["reason"] == "empty_answer_or_no_served_context"
    result = apply_evidence_contract("respuesta", [], "pregunta")
    assert result["actions"] == []


# ───────────────────────── oráculo offline (brazo opt-in) ─────────────────────────

def _oracle_receipt(question: str, card: dict, draft: str) -> dict:
    return {
        "schema": "test",
        "replica_key": "hp:r1",
        "qid": "hp",
        "replica_id": "r1",
        "input": {"question": question},
        "served_context": [card],
        "answer": draft,
        "answer_sha256": preflight.sha256_text(draft),
        "must_preserve": {"status": "evaluated"},
        "generation_chain": {
            "stages": [
                {
                    "name": "diagram_postprocess",
                    "output_text": draft,
                    "output_sha256": preflight.sha256_text(draft),
                },
                {"name": "answer_planner"},
                {"name": "must_preserve"},
                {"name": "conflict_guard"},
            ]
        },
    }


def _passthrough_stages():
    return {
        "apply_answer_planner": lambda _q, _c, a: (a, None),
        "apply_must_preserve_contract": (
            lambda _q, _c, a, *, detect_fn: (a, None)
        ),
        "detect_atoms": object(),
        "apply_answer_conflict_guard": lambda _q, _c, a: (a, None),
    }


def test_oracle_replay_without_arm_stays_byte_identical():
    receipt = _oracle_receipt(
        _SIX_SEVEN_QUESTION, dict(_SIX_SEVEN_CARD), _SIX_SEVEN_ANSWER
    )
    row, scoring_view = preflight.replay_receipt(receipt, **_passthrough_stages())
    assert [s["name"] for s in row["stages"]] == [
        "answer_planner", "must_preserve", "conflict_guard",
    ]
    assert row["candidate_answer"] == _SIX_SEVEN_ANSWER
    assert row["source_answer_byte_exact"] is True
    assert scoring_view["answer"] == _SIX_SEVEN_ANSWER


def test_oracle_replay_with_arm_runs_after_conflict_guard_and_traces():
    receipt = _oracle_receipt(
        _SIX_SEVEN_QUESTION, dict(_SIX_SEVEN_CARD), _SIX_SEVEN_ANSWER
    )
    row, scoring_view = preflight.replay_receipt(
        receipt,
        apply_evidence_contract=apply_evidence_contract,
        **_passthrough_stages(),
    )
    assert [s["name"] for s in row["stages"]] == [
        "answer_planner", "must_preserve", "conflict_guard", "evidence_contract",
    ]
    stage = row["stages"][-1]
    assert stage["trace"]["schema"] == ec.SCHEMA
    assert stage["input_sha256"] == preflight.sha256_text(_SIX_SEVEN_ANSWER)
    assert stage["output_sha256"] == preflight.sha256_text(row["candidate_answer"])
    assert "la fuente es inconsistente" in row["candidate_answer"]
    assert row["source_answer_byte_exact"] is False
    assert scoring_view["answer"] == row["candidate_answer"]


def test_oracle_cli_arm_is_opt_in_default_off():
    base = [
        "--source-run", "run",
        "--release-config", "cfg.json",
        "--fact-contract", "contract.json",
        "--baseline-adjudication", "adj.json",
        "--output", "out.json",
    ]
    assert preflight.parse_args(base).with_evidence_contract is False
    assert (
        preflight.parse_args(base + ["--with-evidence-contract"])
        .with_evidence_contract
        is True
    )


# ───────────────────────── higiene: sin QID/gold en runtime ─────────────────────────

def test_runtime_module_has_no_eval_identifiers():
    source = Path(ec.__file__).read_text(encoding="utf-8")
    assert not re.search(r"(?i)\b(qid|gold|replica)\w*\b", source)
