"""Offline mutation tests for the S277 C1 P1 deterministic scorer."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import s277_c1_p1_scorer as scorer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "evals/s277_c1_p1_fact_contract_v1.json"
FREEZE_PATH = ROOT / "evals/s113_full_contexts_freeze_v1.json"


@pytest.fixture(scope="module")
def contract() -> dict:
    return scorer.load_fact_contract(CONTRACT_PATH)


def _chunk(
    row_id: str = "chunk-1",
    *,
    source_file: str = "manual.pdf",
    page_number: int = 1,
    content: str = "Contenido fuente acreditado.",
    product_model: str = "Model",
) -> dict:
    return {
        "id": row_id,
        "content": content,
        "source_file": source_file,
        "page_number": page_number,
        "product_model": product_model,
    }


def _fact(contract: dict, fact_id: str) -> dict:
    return next(row for row in contract["protected_facts"] if row["fact_id"] == fact_id)


def _first_bound_quote(row: dict) -> str:
    return next(
        ref["quote_text"]
        for ref in row["source_refs"]
        if isinstance(ref.get("quote_text"), str) and ref["quote_text"]
    )


def _frozen_chunk(row_id: str) -> dict:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    matches: list[dict] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            if value.get("id") == row_id and isinstance(value.get("content"), str):
                matches.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(freeze)
    assert matches
    return deepcopy(matches[0])


def _hp017_context(monkeypatch: pytest.MonkeyPatch, target_fragment: int = 12) -> list[dict]:
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    from src.rag.post_rerank_coverage import _attest

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hp017 = next(row for row in freeze["rows"] if row["qid"] == "hp017")
    target = next(
        row for row in hp017["context"] if row["id"] == scorer.TARGET_ID
    )
    attested = _attest(deepcopy(target))
    assert attested is not None and attested.get("mandatory_callout_cards")
    context = [
        _chunk(f"dummy-{index}", source_file=f"dummy-{index}.pdf")
        for index in range(1, target_fragment)
    ]
    context.append(attested)
    return context


def _warning_answer(fragment: int, *, shared: bool = False) -> str:
    technical = (
        "Configure el retardo dentro de una regla de causa y efecto, revise sus "
        "condiciones y compruebe la activación de las salidas."
    )
    warning_1 = (
        "Al programar reglas de causa-efecto evite las lógicas contradictorias."
    )
    warning_2 = (
        "Es de vital importancia probar rigurosamente todas las reglas durante la "
        "puesta en marcha del sistema para verificar que no haya conflictos lógicos "
        "entre ellas."
    )
    if shared:
        return f"{technical}\n\n{warning_1}\n>\n{warning_2} [F{fragment}]"
    return (
        f"{technical}\n\n{warning_1} [F{fragment}]\n\n"
        f"{warning_2} [F{fragment}]"
    )


def test_contract_loads_exact_43_plus_separate_target(contract: dict) -> None:
    assert len(contract["protected_facts"]) == 43
    assert contract["population"]["per_qid_base_counts"]["hp013"] == 0
    assert contract["c1_target"]["separate_from_base"] is True
    assert contract["c1_target"]["compound_obligation_ids"] == list(
        scorer.TARGET_OBLIGATION_IDS
    )


def test_contract_statement_hash_tamper_fails_closed(contract: dict) -> None:
    tampered = deepcopy(contract)
    tampered["protected_facts"][0]["statement"] += " alterado"
    with pytest.raises(scorer.ScorerInstrumentError, match="statement hash drift"):
        scorer.validate_fact_contract(tampered)


@pytest.mark.parametrize("answer", ["Dato [F 1]", "Dato [f1]", "Dato [F01]", "Dato [F1"])
def test_global_citation_syntax_is_closed(answer: str) -> None:
    result = scorer.validate_global_citations(answer, [_chunk()])
    assert result.status == scorer.FAIL


def test_global_citations_reject_range_and_context_identity() -> None:
    assert scorer.validate_global_citations("Dato [F2]", [_chunk()]).status == scorer.FAIL
    duplicated = [_chunk("same"), _chunk("same")]
    assert (
        scorer.validate_global_citations("Dato [F1]", duplicated).status
        == scorer.INSTRUMENT_ERROR
    )


def test_global_and_local_citation_happy_path() -> None:
    answer = "La corriente es 0,75 A [F1]."
    global_result = scorer.validate_global_citations(answer, [_chunk()])
    assert global_result.status == scorer.PASS
    units = scorer.parse_local_citation_units(answer)
    assert len(units) == 1
    assert units[0]["citations"] == [1]
    assert "0,75 A" in units[0]["claim_text"]


def test_generic_fact_pass_review_and_wrong_attribution(contract: dict) -> None:
    fact = _fact(contract, "cat001#1:0,75 A")
    good_context = [
        _chunk(
            source_file="997-669-005-3_Instal-Comm_ES.pdf",
            page_number=51,
            content=_first_bound_quote(fact),
        )
    ]
    passed = scorer.score_protected_fact(
        f'{fact["statement"]} [F1].', good_context, fact
    )
    assert passed.status == scorer.PASS

    detached_amount = scorer.score_protected_fact(
        "La salida admite 0,75 A [F1].", good_context, fact
    )
    assert detached_amount.status != scorer.PASS

    paraphrase = scorer.score_protected_fact(
        "La intensidad admisible es la indicada por el fabricante [F1].",
        good_context,
        fact,
    )
    assert paraphrase.status == scorer.REVIEW

    wrong_context = [
        _chunk(
            source_file="997-669-005-3_Instal-Comm_ES.pdf",
            page_number=20,
            content=_first_bound_quote(fact),
        )
    ]
    wrong = scorer.score_protected_fact(
        f'{fact["statement"]} [F1].', wrong_context, fact
    )
    assert wrong.status == scorer.FAIL

    disconnected = scorer.score_protected_fact(
        "La carga mÃ¡xima del lazo estÃ¡ documentada [F1].\n"
        "La cifra es 0,75 A [F1].",
        good_context,
        fact,
    )
    assert disconnected.status != scorer.PASS


def test_generic_fact_never_passes_negation_relation_swap_or_irrelevant_source(
    contract: dict,
) -> None:
    fact = _fact(contract, "cat001#1:0,75 A")
    valid_context = [
        _chunk(
            source_file="997-669-005-3_Instal-Comm_ES.pdf",
            page_number=51,
            content=_first_bound_quote(fact),
        )
    ]
    negated = f'No es cierto que {fact["statement"]} [F1].'
    swapped_relation = "El lazo de 0,75 A tiene una carga máxima diferente [F1]."
    assert scorer.score_protected_fact(negated, valid_context, fact).status == scorer.REVIEW
    assert (
        scorer.score_protected_fact(swapped_relation, valid_context, fact).status
        == scorer.REVIEW
    )

    irrelevant = _chunk(
        source_file="997-669-005-3_Instal-Comm_ES.pdf",
        page_number=51,
        content="Contenido completamente irrelevante.",
    )
    irrelevant["content_sha256"] = fact["source_refs"][0].get("content_sha256")
    assert (
        scorer.score_protected_fact(
            f'{fact["statement"]} [F1].', [irrelevant], fact
        ).status
        == scorer.REVIEW
    )


def test_contract_quote_text_is_hash_bound(contract: dict) -> None:
    tampered = deepcopy(contract)
    ref = next(
        source
        for fact in tampered["protected_facts"]
        for source in fact["source_refs"]
        if source.get("quote_text")
    )
    ref["quote_text"] += " alterado"
    with pytest.raises(scorer.ScorerInstrumentError, match="quote hash drift"):
        scorer.validate_fact_contract(tampered)


def test_hp011_canonical_statement_passes_and_requires_ta(contract: dict) -> None:
    fact = _fact(contract, "hp011#1:r.I")
    context = [
        _chunk(
            source_file="HLSI-MN-103_RP1r-Supra_lr.pdf",
            page_number=63,
            content=_first_bound_quote(fact),
        )
    ]
    answer = f'{fact["statement"]} [F1].'
    result = scorer.score_protected_fact(answer, context, fact)
    assert result.status == scorer.PASS
    assert result.evidence["canonical_identifier_present"] is True
    assert result.evidence["special_state_present"] is True

    no_ta = answer.replace("t.A", "duracion de la descarga")
    no_ta_result = scorer.score_protected_fact(no_ta, context, fact)
    assert no_ta_result.status == scorer.FAIL
    assert no_ta_result.reasons == ("the -- state omits mandatory t.A",)


def test_hp011_rejects_tfi_and_reviews_r1_alias_alone(contract: dict) -> None:
    fact = _fact(contract, "hp011#1:r.I")
    context = [
        _chunk(source_file="HLSI-MN-103_RP1r-Supra_lr.pdf", page_number=63)
    ]
    base = (
        "Rearme inhibido r.1: -- usa t.A; 00 es el valor por defecto y "
        "01 a 30 minutos son el intervalo [F1]."
    )
    assert scorer.score_protected_fact(base, context, fact).status == scorer.REVIEW
    assert (
        scorer.score_protected_fact(base.replace("t.A", "t.A y t.Fi"), context, fact).status
        == scorer.FAIL
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Introduccion\n\n---\n\nConclusion",
        "Introduccion\n\n----\n\nConclusion",
        "Introduccion ----- conclusion",
        "Introduccion -- conclusion",
        "Use la opcion --help",
    ],
)
def test_hp011_markdown_rules_and_nonisolated_runs_do_not_activate_special_state(
    answer: str,
    contract: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fact = _fact(contract, "hp011#1:r.I")
    monkeypatch.setattr(
        scorer,
        "_generic_fact_score",
        lambda *_args: scorer._result("fact:hp011#1:r.I", scorer.PASS),
    )

    result = scorer._score_hp011(answer, [], fact)

    assert result.status == scorer.PASS
    assert result.evidence["special_state_present"] is False


@pytest.mark.parametrize(
    "answer",
    [
        '"--"',
        "`--`",
        "r.1: -- usa t.A",
        "Estado: -- hasta agotar t.A",
        "| Rearme | -- |",
        "reset_mode = --",
    ],
)
def test_hp011_recognizes_only_unambiguous_technical_special_state(answer: str) -> None:
    assert scorer._hp011_has_special_state(answer) is True


def test_hp011_isolated_special_state_enforces_ta_and_tfi(
    contract: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fact = _fact(contract, "hp011#1:r.I")
    monkeypatch.setattr(
        scorer,
        "_generic_fact_score",
        lambda *_args: scorer._result("fact:hp011#1:r.I", scorer.PASS),
    )

    passed = scorer._score_hp011('El valor tecnico es "--" y se agota t.A.', [], fact)
    assert passed.status == scorer.PASS
    assert passed.evidence["special_state_present"] is True
    assert passed.evidence["t.A_present"] is True

    missing_ta = scorer._score_hp011('El valor tecnico es "--".', [], fact)
    assert missing_ta.status == scorer.FAIL
    assert missing_ta.reasons == ("the -- state omits mandatory t.A",)

    forbidden_tfi = scorer._score_hp011(
        'El valor tecnico es "--" y se agotan t.A y t.Fi.', [], fact
    )
    assert forbidden_tfi.status == scorer.FAIL
    assert forbidden_tfi.reasons == ("t.Fi is forbidden inside the -- state",)


def test_hp013_guard_is_safety_scored_even_with_zero_facts(contract: dict) -> None:
    guard = contract["question_guards"][0]
    context = [
        _chunk(
            source_file="ADW535_TD_T140358es_e.pdf",
            page_number=11,
            content=_first_bound_quote(guard),
        )
    ]
    answer = (
        "El manual no documenta un procedimiento para cambiar únicamente la batería. "
        "La EEPROM permite una expectativa matizada, pero no garantiza que la "
        "configuración se conserve durante una operación no documentada [F1]."
    )
    guarded = scorer.score_hp013_guard(answer, context, guard)
    assert guarded.status == scorer.REVIEW
    assert guarded.evidence["machine_safety_precheck"] == scorer.PASS

    unsafe = "Está garantizado que no perderá configuración al cambiar la batería [F1]."
    assert scorer.score_hp013_guard(unsafe, context, guard).status == scorer.FAIL

    ambiguous = "La batería está en la placa; contacte con soporte [F1]."
    assert scorer.score_hp013_guard(ambiguous, context, guard).status == scorer.REVIEW


def test_hp018_diode_fact_is_bound_to_its_own_page_not_same_manual(contract: dict) -> None:
    fact = _fact(contract, "hp018#2:diodo")
    claim = f'{fact["statement"]} [F1].'
    wrong_page = [_frozen_chunk("90d51dac-bd0b-4051-b414-ced0fe6e33bb")]
    assert scorer.score_protected_fact(claim, wrong_page, fact).status == scorer.FAIL

    right_page = [_frozen_chunk("72fc4c53-f507-4e67-9192-ebc68b94be78")]
    assert scorer.score_protected_fact(claim, right_page, fact).status == scorer.PASS


def test_hp017_menu_conflict_fails_flat_number_and_accepts_omission(contract: dict) -> None:
    conflict = contract["registered_conflicts"][0]
    flat = "En el menú seleccione 8: Causa y Efecto."
    assert scorer.score_known_hp017_menu_conflict(flat, conflict).status == scorer.FAIL
    assert (
        scorer.score_known_hp017_menu_conflict(
            "Abra la pantalla Causa y Efecto sin asumir un número de menú.", conflict
        ).status
        == scorer.PASS
    )


def test_hp017_menu_conflict_accepts_explicit_source_disclosure(contract: dict) -> None:
    conflict = contract["registered_conflicts"][0]
    disclosed = (
        "Los fragmentos discrepan: 7: Causa y Efecto en una revisión; "
        "8: Causa y Efecto en la otra revisión."
    )
    assert scorer.score_known_hp017_menu_conflict(disclosed, conflict).status == scorer.PASS


def test_sealed_stored_control_emits_prepaid_hold_without_candidate_claim(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def network_forbidden(*_args, **_kwargs):
        raise AssertionError("stored-control scorer attempted network access")

    import socket

    monkeypatch.setattr(socket.socket, "connect", network_forbidden)
    result = scorer.score_stored_controls(contract=contract)
    assert result["status"] == scorer.REVIEW
    assert result["decision"] == scorer.STORED_CONTROL_HOLD
    assert result["scope"] == "HISTORICAL_CONFLICT_ONLY"
    assert result["confirmed_3_of_3"] is True
    assert result["conflict_failures"] == 3
    assert result["candidate_runtime_measured"] is False
    assert result["candidate_status"] is None
    assert result["paid_model_calls"] == 0
    assert result["network_calls"] == 0
    assert all(row["conflict_status"] == scorer.FAIL for row in result["replicas"])


def test_stored_control_hash_drift_is_instrument_error(
    contract: dict, tmp_path: Path
) -> None:
    tampered = tmp_path / "stored.jsonl"
    tampered.write_bytes(scorer.STORED_CONTROL_PATH.read_bytes() + b"\n")
    result = scorer.score_stored_controls(tampered, contract)
    assert result["status"] == scorer.INSTRUMENT_ERROR
    assert result["decision"] == "HOLD_INSTRUMENT_ERROR"


def test_hp017_context_binding_is_dynamic_and_receipt_bound(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _hp017_context(monkeypatch, target_fragment=3)
    result = scorer.bind_hp017_context(context, contract["c1_target"])
    assert result.status == scorer.PASS
    assert result.evidence["target_fragment"] == 3

    tampered = deepcopy(context)
    tampered[2]["mandatory_callout_cards"][0]["quote"] = "texto alterado"
    assert (
        scorer.bind_hp017_context(tampered, contract["c1_target"]).status
        == scorer.INSTRUMENT_ERROR
    )


def test_hp017_context_binding_accepts_only_byte_intact_full_source_prefix(
    contract: dict,
) -> None:
    target = _frozen_chunk(scorer.TARGET_ID)
    context = [
        _chunk(f"dummy-{index}", source_file=f"dummy-{index}.pdf")
        for index in range(1, 6)
    ]
    context.append(target)

    result = scorer._bind_hp017_context(
        context,
        contract["c1_target"],
        protected_prefix_rows=len(context),
    )

    assert result.status == scorer.PASS
    assert result.evidence["target_fragment"] == 6
    assert result.evidence["delivery_route"] == "protected_prefix_full_source"
    assert result.evidence["callout_start"] == 0
    assert result.evidence["callout_end"] == len(target["content"])

    # The same row outside the declared prefix remains append-strict: no exact
    # callout receipt means no lawful coverage delivery route.
    assert (
        scorer._bind_hp017_context(
            context,
            contract["c1_target"],
            protected_prefix_rows=len(context) - 1,
        ).status
        == scorer.INSTRUMENT_ERROR
    )

    tampered = deepcopy(context)
    tampered[-1]["content"] += " alterado"
    assert (
        scorer._bind_hp017_context(
            tampered,
            contract["c1_target"],
            protected_prefix_rows=len(tampered),
        ).status
        == scorer.INSTRUMENT_ERROR
    )


@pytest.mark.parametrize("invalid_rows", [True, -1, 7])
def test_hp017_context_binding_rejects_invalid_prefix_bounds(
    contract: dict, invalid_rows: object
) -> None:
    context = [_frozen_chunk(scorer.TARGET_ID)]

    assert (
        scorer._bind_hp017_context(
            context,
            contract["c1_target"],
            protected_prefix_rows=invalid_rows,  # type: ignore[arg-type]
        ).status
        == scorer.INSTRUMENT_ERROR
    )


def test_hp017_case_accepts_prefix_route_without_weakening_append_receipts(
    contract: dict,
) -> None:
    target = _frozen_chunk(scorer.TARGET_ID)
    prefix = [
        *[
            _chunk(f"prefix-{index}", source_file=f"prefix-{index}.pdf")
            for index in range(1, 6)
        ],
        target,
        *[
            _chunk(f"prefix-{index}", source_file=f"prefix-{index}.pdf")
            for index in range(7, 11)
        ],
    ]
    served = [*deepcopy(prefix), _chunk("coverage-extra")]
    replica = {
        "answer": _warning_answer(6),
        "served_context": served,
        "rerank": {"prefix": deepcopy(prefix)},
        "structural_fetch": {"output": deepcopy(prefix)},
        "coverage": {"status": "evaluated", "output_context": deepcopy(served)},
        "must_preserve": {"status": "evaluated"},
    }

    result = scorer.score_hp017_case(replica, contract)
    checks = {row["check_id"]: row for row in result.evidence["checks"]}

    assert checks["hp017_coverage"]["status"] == scorer.PASS
    assert (
        checks["hp017_coverage"]["evidence"]["delivery_route"]
        == "protected_prefix_full_source"
    )
    assert checks["hp017_warning_block"]["status"] == scorer.PASS

    # Moving an unreceipted target outside the protected prefix must still fail.
    appended_target = deepcopy(replica)
    appended_target["rerank"]["prefix"] = deepcopy(prefix[:5])
    appended_target["structural_fetch"]["output"] = deepcopy(prefix[:5])
    appended_target["coverage"]["output_context"] = deepcopy(served)
    assert (
        scorer.score_hp017_case(appended_target, contract).status
        == scorer.INSTRUMENT_ERROR
    )


def test_hp017_case_keeps_receipted_coverage_append_route(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    served = _hp017_context(monkeypatch, target_fragment=6)
    prefix = deepcopy(served[:5])
    replica = {
        "answer": _warning_answer(6),
        "served_context": deepcopy(served),
        "rerank": {"prefix": deepcopy(prefix)},
        "structural_fetch": {"output": deepcopy(prefix)},
        "coverage": {"status": "evaluated", "output_context": deepcopy(served)},
        "must_preserve": {"status": "evaluated"},
    }

    result = scorer.score_hp017_case(replica, contract)
    checks = {row["check_id"]: row for row in result.evidence["checks"]}

    assert checks["hp017_coverage"]["status"] == scorer.PASS
    assert (
        checks["hp017_coverage"]["evidence"]["delivery_route"]
        == "coverage_append"
    )
    assert checks["hp017_warning_block"]["status"] == scorer.PASS


def test_hp017_prefix_route_requires_canonical_byte_equal_lineage(
    contract: dict,
) -> None:
    target = _frozen_chunk(scorer.TARGET_ID)
    prefix = [target, _chunk("prefix-2")]
    replica = {
        "answer": _warning_answer(1),
        "served_context": deepcopy(prefix),
        "rerank": {"prefix": deepcopy(prefix)},
        "structural_fetch": {"output": deepcopy(prefix)},
        "coverage": {"status": "evaluated", "output_context": deepcopy(prefix)},
        "must_preserve": {"status": "evaluated"},
    }

    tampered = deepcopy(replica)
    tampered["structural_fetch"]["output"][1]["content"] = "mutated"
    tampered["coverage"]["output_context"][1]["content"] = "mutated"
    result = scorer.score_hp017_case(tampered, contract)
    checks = {row["check_id"]: row for row in result.evidence["checks"]}
    assert checks["hp017_coverage"]["status"] == scorer.FAIL
    assert "canonical rerank prefix" in checks["hp017_coverage"]["reasons"][0]

    duplicated = deepcopy(replica)
    duplicated["served_context"].append(deepcopy(target))
    duplicated["coverage"]["output_context"].append(deepcopy(target))
    result = scorer.score_hp017_case(duplicated, contract)
    checks = {row["check_id"]: row for row in result.evidence["checks"]}
    assert checks["hp017_coverage"]["status"] == scorer.FAIL
    assert "duplicate identity" in checks["hp017_coverage"]["reasons"][0]


def test_hp017_warning_requires_both_exact_clauses_and_dynamic_local_cites(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _hp017_context(monkeypatch, target_fragment=12)
    passed = scorer.score_hp017_warning_block(
        _warning_answer(12), context, contract["c1_target"]
    )
    assert passed.status == scorer.PASS
    assert passed.evidence["target_fragment"] == 12

    missing = _warning_answer(12).replace(
        "Al programar reglas de causa-efecto evite las lógicas contradictorias. [F12]\n\n",
        "",
    )
    assert (
        scorer.score_hp017_warning_block(missing, context, contract["c1_target"]).status
        == scorer.FAIL
    )

    wrong_fragment = _warning_answer(12).replace("[F12]", "[F11]")
    assert (
        scorer.score_hp017_warning_block(
            wrong_fragment, context, contract["c1_target"]
        ).status
        == scorer.FAIL
    )


def test_hp017_warning_shared_citation_is_only_accepted_for_adjacent_pair(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _hp017_context(monkeypatch, target_fragment=4)
    shared = scorer.score_hp017_warning_block(
        _warning_answer(4, shared=True), context, contract["c1_target"]
    )
    assert shared.status == scorer.PASS

    separated = _warning_answer(4, shared=True).replace(
        "\n>\nEs de vital", "\nAquí se introduce otra recomendación técnica.\nEs de vital"
    )
    assert (
        scorer.score_hp017_warning_block(separated, context, contract["c1_target"]).status
        == scorer.FAIL
    )


def test_hp017_warning_rejects_unaccredited_additional_citation(
    contract: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _hp017_context(monkeypatch, target_fragment=5)
    answer = _warning_answer(5).replace("[F5]", "[F5] [F1]")
    assert (
        scorer.score_hp017_warning_block(answer, context, contract["c1_target"]).status
        == scorer.FAIL
    )


def test_score_replica_applies_hp013_guard_and_global_citations(contract: dict) -> None:
    answer = (
        "El manual no documenta un procedimiento para cambiar la batería; la EEPROM "
        "permite una expectativa, pero no garantiza conservación [F1]."
    )
    receipt = {
        "schema": scorer.REPLICA_SCHEMA,
        "replica_key": "hp013:r1",
        "qid": "hp013",
        "replica_id": "r1",
        "answer": answer,
        "served_context": [
            _chunk(
                source_file="ADW535_TD_T140358es_e.pdf",
                page_number=11,
                content=_first_bound_quote(contract["question_guards"][0]),
            )
        ],
        "provider": {"stop_reason": "end_turn"},
    }
    result = scorer.score_replica(receipt, contract)
    assert result["status"] == scorer.REVIEW
    assert result["review_items"]

    receipt["answer"] = answer.replace("[F1]", "[F 1]")
    assert scorer.score_replica(receipt, contract)["status"] == scorer.FAIL


def _dummy_run_replicas() -> list[dict]:
    replicas = []
    for replica_key in scorer.P1_REPLICA_KEYS:
        qid, replica_id = replica_key.split(":", 1)
        replicas.append(
            {
                "schema": scorer.REPLICA_SCHEMA,
                "replica_key": replica_key,
                "qid": qid,
                "replica_id": replica_id,
                "answer": "Dato tecnico no acreditado [F1].",
                "served_context": [_chunk()],
                "provider": {"stop_reason": "end_turn"},
            }
        )
    return replicas


def _run_bindings(contract: dict) -> dict[str, str]:
    return {
        "run_result_sha256": "1" * 64,
        "prereg_sha256": "2" * 64,
        "fact_contract_sha256_lf": scorer.EXPECTED_CONTRACT_SHA256_LF,
        "fact_contract_payload_sha256": contract["payload_sha256"],
        "replica_manifest_sha256": "3" * 64,
    }


def test_score_run_rejects_missing_extra_reordered_and_unbound_population(
    contract: dict,
) -> None:
    full = _dummy_run_replicas()
    for population in ([], full[:-1], [*full, deepcopy(full[-1])], list(reversed(full))):
        result = scorer.score_run(population, contract, bindings=_run_bindings(contract))
        assert result["status"] == scorer.INSTRUMENT_ERROR
        assert result["decision"] == "HOLD_INSTRUMENT_ERROR"

    unbound = scorer.score_run(full, contract)
    assert unbound["status"] == scorer.INSTRUMENT_ERROR
    assert "bindings are absent" in unbound["reasons"][0]


def test_score_run_binds_run_prereg_contract_and_replica_payload(contract: dict) -> None:
    replicas = _dummy_run_replicas()
    bindings = _run_bindings(contract)
    result = scorer.score_run(replicas, contract, bindings=bindings)
    assert result["score_bindings"] == bindings
    assert result["run_result_sha256"] == bindings["run_result_sha256"]
    assert result["prereg_sha256"] == bindings["prereg_sha256"]
    assert result["fact_contract_payload_sha256"] == contract["payload_sha256"]
    assert result["replicas_sha256"] == scorer._canonical_sha256(replicas)

    drifted = deepcopy(bindings)
    drifted["fact_contract_sha256_lf"] = "4" * 64
    rejected = scorer.score_run(replicas, contract, bindings=drifted)
    assert rejected["status"] == scorer.INSTRUMENT_ERROR
    assert "preregistered authority" in rejected["reasons"][0]


def _review_score(contract: dict) -> tuple[dict, dict]:
    receipt = {
        "schema": scorer.REPLICA_SCHEMA,
        "replica_key": "cat001:r1",
        "qid": "cat001",
        "replica_id": "r1",
        "answer": "Consulte en el manual las capacidades del lazo [F1].",
        "served_context": [
            _chunk(
                source_file="997-669-005-3_Instal-Comm_ES.pdf",
                page_number=51,
            )
        ],
        "provider": {"stop_reason": "end_turn"},
    }
    result = scorer.score_replica(receipt, contract)
    assert result["status"] == scorer.REVIEW
    assert result["review_items"]
    return result, receipt


def _complete_adjudication(score_result: dict, decision: str) -> dict:
    packet = scorer.adjudication_template(score_result)
    for row in packet["rows"]:
        row.update(
            {
                "decision": decision,
                "reviewer": "blind-human-reviewer",
                "reviewed_at": "2026-07-20T20:00:00Z",
                "blind": True,
                "rationale": "Compared the exact answer, context and protected statement.",
            }
        )
    return packet


def test_finalize_only_resolves_hash_bound_review_rows(contract: dict) -> None:
    score_result, receipt = _review_score(contract)
    packet = _complete_adjudication(score_result, "ADJUDICATED_PASS")
    final = scorer.finalize_score(
        score_result, packet, replicas=receipt, contract=contract
    )
    assert final["status"] == scorer.PASS
    assert final["adjudication_applied"] is True
    assert all(
        row["decision"] == "ADJUDICATED_PASS" for row in final["row_resolutions"]
    )

    tampered = deepcopy(packet)
    tampered["rows"][0]["binding_sha256"] = "0" * 64
    assert (
        scorer.finalize_score(
            score_result, tampered, replicas=receipt, contract=contract
        )["status"]
        == scorer.INSTRUMENT_ERROR
    )


def test_finalize_adjudicated_fail_remains_no_go(contract: dict) -> None:
    score_result, receipt = _review_score(contract)
    packet = _complete_adjudication(score_result, "ADJUDICATED_PASS")
    packet["rows"][0]["decision"] = "ADJUDICATED_FAIL"
    final = scorer.finalize_score(
        score_result, packet, replicas=receipt, contract=contract
    )
    assert final["status"] == scorer.FAIL
    assert final["decision"] == "NO_GO"


def test_finalize_never_overwrites_machine_fail(contract: dict) -> None:
    receipt = {
        "schema": scorer.REPLICA_SCHEMA,
        "replica_key": "cat001:r1",
        "qid": "cat001",
        "replica_id": "r1",
        "answer": "Dato con cita rota [F 1].",
        "served_context": [_chunk()],
        "provider": {"stop_reason": "end_turn"},
    }
    failed = scorer.score_replica(receipt, contract)
    assert failed["status"] == scorer.FAIL
    final = scorer.finalize_score(failed, replicas=receipt, contract=contract)
    assert final["status"] == scorer.FAIL
    assert final["adjudication_applied"] is False


def test_finalize_rejects_forged_pass_and_any_score_tamper(contract: dict) -> None:
    forged = {
        "schema_version": scorer.SCHEMA_VERSION,
        "scorer_sha256": scorer.scorer_sha256(),
        "status": scorer.PASS,
        "decision": scorer.PASS,
        "review_items": [],
        "claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
        "run_result_sha256": "1" * 64,
    }
    no_inputs = scorer.finalize_score(forged)
    assert no_inputs["status"] == scorer.INSTRUMENT_ERROR
    assert "authoritative persisted inputs" in no_inputs["reasons"][0]

    score_result, receipt = _review_score(contract)
    forged_from_real = deepcopy(score_result)
    forged_from_real["status"] = scorer.PASS
    forged_from_real["review_items"] = []
    rejected = scorer.finalize_score(
        forged_from_real, replicas=receipt, contract=contract
    )
    assert rejected["status"] == scorer.INSTRUMENT_ERROR
    assert "deterministic rescore" in rejected["reasons"][0]


def test_contract_cannot_be_weakened_even_with_recomputed_internal_hashes(
    contract: dict,
) -> None:
    weakened = deepcopy(contract)
    weakened["protected_facts"][0]["surface_forms"]["required_all_groups"] = [
        ["dato"]
    ]
    body = {key: value for key, value in weakened.items() if key != "payload_sha256"}
    weakened["payload_sha256"] = scorer._canonical_sha256(body)
    with pytest.raises(
        scorer.ScorerInstrumentError,
        match="preregistered fact contract payload drift",
    ):
        scorer.validate_fact_contract(weakened)
