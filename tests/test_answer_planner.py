from copy import deepcopy

from src.rag.answer_planner import (
    ANSWER_PLANNER_CONTRACT_S119,
    ANSWER_PLANNER_CONTRACT_S120,
    ANSWER_PLANNER_CONTRACT_S122,
    AnswerConflict,
    AnswerConflictEvidence,
    AnswerObligation,
    answer_planner_mode,
    apply_answer_conflict_guard,
    apply_answer_planner,
    enforce_answer_contract,
    build_answer_plan,
    obligation_covered,
    supplement_missing_obligations,
    validate_answer_conflicts,
    validate_answer_plan,
)
from src.rag.structural_neighbor_coverage import CASCADED_LANE


def _chunk(quote, *, facet="query_alignment", hits=None, chunk_id="c1"):
    content = f"prefix {quote} suffix"
    start = content.index(quote)
    card = {
        "candidate_id": chunk_id,
        "start": start,
        "end": start + len(quote),
        "quote": quote,
        "facet": facet,
        "exact_source_span_validated": True,
        "selector_start": start,
        "selector_end": start + len(quote),
        "logical_record_expanded": False,
    }
    if facet == "query_alignment":
        card["alignment_term_hits"] = hits or ["lazo", "equipos", "aisladores"]
    return {
        "id": chunk_id,
        "content": content,
        "retrieval_lane": CASCADED_LANE,
        "coverage_validated": True,
        "local_semantic_validated": True,
        "structural_neighbor_validated": True,
        "coverage_cards": [deepcopy(card)],
        "served_coverage_cards": [card],
    }


def _served_base_chunk(content, *, chunk_id="base1", product_model="GENERIC P1"):
    return {
        "id": chunk_id,
        "content": content,
        "product_model": product_model,
        "retrieval_lane": "base",
    }


def test_normalizes_query_aligned_limits_without_gold_values():
    quote = (
        "Los aisladores deben colocarse entre un máximo de 32 equipos de lazo. "
        "Para las centrales Pearl, no coloque más de 25 equipos de lazo entre "
        "aisladores (20 si utiliza aisladores FET)."
    )
    plan = build_answer_plan(
        "¿Cuántos equipos admite el lazo y qué límites de aisladores tiene?",
        [_chunk(quote)],
    )
    assert [row.kind for row in plan] == ["source_statement", "source_statement"]
    assert "25" in plan[1].required_anchors


def test_normalizes_option_meaning_rows_and_supplements_missing_pairs():
    quote = (
        "| r.i | Rearme inhibido | - -  Rearme inhibido hasta finalizar extinción\n"
        "00  Rearme permitido en cualquier momento (por defecto)\n"
        "De 01 a 30  Rearme inhibido durante el intervalo en minutos |"
    )
    plan = build_answer_plan(
        "Tras la extinción no permite rearme, ¿qué comprobar?",
        [_chunk(quote, hits=["extincion", "rearme", "intervalo"])],
    )
    assert len(plan) == 3
    revised, result = supplement_missing_obligations("Compruebe r.i.\n\nFuente: manual", plan)
    assert result["supplemented"] == 3
    assert "00: Rearme permitido en cualquier momento" in revised
    assert revised.index("Información explícita") < revised.index("Fuente:")
    assert validate_answer_plan(revised, plan)["covered"] == 3


def test_bundles_terminal_paths_but_rejects_unrelated_siren_card():
    terminal_quote = (
        "- Inicio Lazo (+) OUT / Inicio Lazo (-) OUT\n"
        "- (+) Retorno / (-) Retorno"
    )
    siren_quote = (
        "Cada circuito de sirena lleva una resistencia 6K8 final de línea."
    )
    plan = build_answer_plan(
        "¿Qué resistencia de fin de línea lleva el lazo?",
        [
            _chunk(
                terminal_quote,
                facet="query_alignment",
                chunk_id="terminals",
            ),
            _chunk(siren_quote, facet="termination", chunk_id="siren"),
        ],
    )
    assert len(plan) == 1
    assert plan[0].kind == "terminal_bundle"
    assert "Retorno" in plan[0].statement


def test_requires_exact_served_receipt():
    chunk = _chunk("Máximo 25 equipos de lazo entre aisladores.")
    chunk["served_coverage_cards"][0]["quote"] = "tampered"
    assert build_answer_plan("equipos del lazo", [chunk]) == []


def test_binds_per_loop_current_capacity_from_served_base_evidence():
    plan = build_answer_plan(
        "Como se cablea e instala el lazo de la INSPIRE E10?",
        [
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
                product_model="INSPIRE E10",
            )
        ],
    )
    assert len(plan) == 1
    assert plan[0].kind == "structured_numeric"
    assert plan[0].required_anchors == ("750 mA", "lazo")

    revised, result = supplement_missing_obligations(
        "Respuesta\n\n**Fuente:** manual", plan
    )
    assert result["supplemented"] == 1
    assert revised.index("750 mA") < revised.index("**Fuente:**")


def test_rejects_current_capacity_when_question_does_not_ask_installation():
    plan = build_answer_plan(
        "Cual es la resistencia final de linea del lazo de INSPIRE E10?",
        [
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
                product_model="INSPIRE E10",
            )
        ],
    )
    assert plan == []


def test_rejects_unqualified_generic_current_from_served_base_evidence():
    plan = build_answer_plan(
        "Como se cablea el circuito de INSPIRE E10?",
        [
            _served_base_chunk(
                "Cada circuito tiene un consumo maximo de 1 Amp.",
                product_model="INSPIRE E10",
            )
        ],
    )
    assert plan == []


def test_rejects_same_topic_capacity_from_foreign_product():
    plan = build_answer_plan(
        "Como se cablea e instala el lazo de INSPIRE E10?",
        [
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 500 mA por lazo.",
                chunk_id="foreign",
                product_model="PEARL",
            ),
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
                chunk_id="target",
                product_model="INSPIRE E10",
            ),
        ],
    )
    assert len(plan) == 1
    assert plan[0].candidate_id == "target"
    assert "750 mA" in plan[0].statement


def test_rejects_competing_values_within_same_product_slot():
    plan = build_answer_plan(
        "Como se cablea e instala el lazo de INSPIRE E10?",
        [
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 500 mA por lazo.",
                chunk_id="old",
                product_model="INSPIRE E10",
            ),
            _served_base_chunk(
                "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
                chunk_id="new",
                product_model="INSPIRE E10",
            ),
        ],
    )
    assert plan == []


def test_rejects_letter_sibling_and_named_sibling_product_claims():
    assert build_answer_plan(
        "Como se cablea el lazo de CAD-150?",
        [
            _served_base_chunk(
                "El lazo proporciona un maximo de 500 mA por lazo.",
                product_model="CAD-150R",
            )
        ],
    ) == []
    assert build_answer_plan(
        "La RP1r no vuelve a normal tras resetear, que compruebo?",
        [
            _served_base_chunk(
                "Todas las averias son por defecto, enclavadas, y requieren rearme manual.",
                product_model="RP1r-Supra",
            )
        ],
    ) == []


def test_accepts_bounded_numeric_family_suffix_but_not_multimodel_chunk():
    plan = build_answer_plan(
        "Como se conectan las baterias en la central CAD-150?",
        [
            _served_base_chunk(
                "Se requieren dos baterias de 12V 7A/h conectadas en serie.",
                product_model="CAD-150-8",
            )
        ],
    )
    assert [row.kind for row in plan] == ["battery_series_spec"]
    assert build_answer_plan(
        "Como se cablea el M710?",
        [
            _served_base_chunk(
                "El M720 proporciona un maximo de 500 mA por lazo.",
                product_model="M710 M720",
            )
        ],
    ) == []


def test_product_isolation_also_applies_to_served_coverage_cards():
    foreign = _chunk(
        "Inicio Lazo (+) OUT\nInicio Lazo (-) OUT\n(+) Retorno\n(-) Retorno"
    )
    foreign["product_model"] = "PEARL"
    assert build_answer_plan("Como se cablea el lazo de INSPIRE E10?", [foreign]) == []


def test_extracts_battery_series_and_bridge_relations_without_gold_prompting():
    plan = build_answer_plan(
        "Como se conectan las baterias en la central CAD-150?",
        [
            _served_base_chunk(
                "Las centrales requieren dos baterias de 12V 7A/h conectadas en serie. "
                "El cable puente une el polo positivo de una bateria con el polo negativo "
                "de la otra.",
                product_model="CAD-150-8",
            )
        ],
    )
    assert [row.kind for row in plan] == ["battery_series_spec", "battery_bridge"]
    assert plan[0].required_anchors == ("12v", "serie", "7a/h")
    raw = (
        "Conecta las baterias con el cable puente. Despues conecta rojo y negro "
        "al positivo y negativo."
    )
    revised, result = supplement_missing_obligations(raw, plan)
    assert result["supplemented"] == 2
    assert result["covered"] == 2
    assert "positivo de una bateria" in revised


def test_rejects_competing_battery_voltage_specs():
    plan = build_answer_plan(
        "Como se conectan las baterias en la central CAD-150?",
        [
            _served_base_chunk(
                "Se requieren dos baterias de 12V 7A/h conectadas en serie.",
                chunk_id="a",
                product_model="CAD-150-8",
            ),
            _served_base_chunk(
                "Se requieren dos baterias de 24V 7A/h conectadas en serie.",
                chunk_id="b",
                product_model="CAD-150-8",
            ),
        ],
    )
    assert all(row.kind != "battery_series_spec" for row in plan)


def test_extracts_english_battery_spec_when_series_is_next_clause():
    plan = build_answer_plan(
        "Como se conectan las baterias en la central CAD-150?",
        [
            _served_base_chunk(
                "The panel requires two 12V 7Ah batteries. "
                "The batteries must be connected in series. "
                "The cable connects the positive terminal of one battery with "
                "the negative terminal of the other.",
                product_model="CAD-150-8",
            )
        ],
    )
    assert [row.kind for row in plan] == ["battery_series_spec", "battery_bridge"]
    answer = (
        "Use dos baterias de 12 V 7 Ah conectadas en serie. El positivo de una "
        "bateria se conecta mediante el puente al negativo de la otra."
    )
    assert validate_answer_plan(answer, plan)["covered"] == 2


def test_prefers_explicit_cross_battery_bridge_relation():
    plan = build_answer_plan(
        "Como se conectan las baterias en la central CAD-150?",
        [
            _served_base_chunk(
                "Conecte rojo y negro al positivo y negativo de las baterias y use el cable puente.",
                chunk_id="implicit",
                product_model="CAD-150-8",
            ),
            _served_base_chunk(
                "El cable conecta el terminal positivo de una bateria con el terminal negativo de la otra.",
                chunk_id="explicit",
                product_model="CAD-150-8",
            ),
        ],
    )
    bridge = next(row for row in plan if row.kind == "battery_bridge")
    assert bridge.candidate_id == "explicit"


def test_extracts_generic_credential_contrast_without_product_rules():
    plan = build_answer_plan(
        "Como accedo a la configuracion avanzada de AM-8200?",
        [
            _served_base_chunk(
                "Introduzca la clave de administrador por defecto, 2222.",
                chunk_id="admin",
                product_model="AM-8200",
            ),
            _served_base_chunk(
                "La clave de usuario por defecto es 1111.",
                chunk_id="user",
                product_model="AM-8200",
            ),
        ],
    )
    assert [row.kind for row in plan] == [
        "credential_administrator",
        "credential_user",
    ]


def test_extracts_generic_commissioning_menu_bundle():
    plan = build_answer_plan(
        "Como se da de alta un detector nuevo en AM-8200?",
        [
            _served_base_chunk(
                "Realice una autobusqueda desde el menu BUCLE. "
                "Asigne la ubicacion desde el menu ZONA. "
                "Nombre el detector desde el menu ELEMENTOS.",
                product_model="AM-8200",
            )
        ],
    )
    bundle = next(row for row in plan if row.kind == "commissioning_menu_bundle")
    assert bundle.required_anchors == (
        "menu BUCLE",
        "menu ZONA",
        "menu ELEMENTOS",
    )


def test_extracts_generic_diagnostic_threshold_direction():
    plan = build_answer_plan(
        "AM-8200 da una alarma de flujo, como se diagnostica?",
        [
            _served_base_chunk(
                "Valor < 100 % apunta a obstruccion / > 100 % apunta a rotura de tubo",
                product_model="AM-8200",
            )
        ],
    )
    assert [row.kind for row in plan] == ["diagnostic_threshold_direction"]


def test_extracts_generic_redundant_power_and_rtc_battery_records():
    plan = build_answer_plan(
        "Como cambio la bateria sin perder configuracion en AM-8200?",
        [
            _served_base_chunk(
                "| PWR-R | = Entrada de alimentacion redundante |",
                chunk_id="power",
                product_model="AM-8200",
            ),
            _served_base_chunk(
                "* Bateria de litio\n* Modulo de reloj RTC",
                chunk_id="rtc",
                product_model="AM-8200",
            ),
        ],
    )
    assert [row.kind for row in plan] == [
        "redundant_power_input",
        "rtc_lithium_battery",
    ]


def test_extracts_generic_zone_scope_without_claiming_impossibility():
    plan = build_answer_plan(
        "Como desactivo un detector individual de AM-8200 sin afectar al resto?",
        [
            _served_base_chunk(
                "Cuando se desconecta una zona, la central no refleja eventos en la zona desconectada.",
                chunk_id="scope",
                product_model="AM-8200",
            ),
            _served_base_chunk(
                "El numero maximo de detectores por zona es 32.",
                chunk_id="capacity",
                product_model="AM-8200",
            ),
        ],
    )
    assert [row.kind for row in plan] == ["zone_disable_scope", "zone_device_capacity"]
    assert all("imposible" not in row.statement.lower() for row in plan)


def test_rejects_conflicting_menu_numbers_for_same_product_route():
    plan = build_answer_plan(
        "Como programo el retardo de salida en AM-8200?",
        [
            _served_base_chunk(
                "Editar Configuracion\n7: Causa y Efecto",
                chunk_id="rev-a",
                product_model="AM-8200",
            ),
            _served_base_chunk(
                "Editar Configuracion\n8: Causa y Efecto",
                chunk_id="rev-b",
                product_model="AM-8200",
            ),
        ],
    )
    assert all(row.kind != "cause_effect_menu_path" for row in plan)


def test_aligns_only_explicit_multi_model_numeric_family_declaration():
    content = (
        "Return the end of the loop to the other end of the loop connector.\n"
        "Loop Start (+) OUT / Loop Start (-) OUT\n"
        "(+) Return / (-) Return\n"
        "All lines form a complete loop circuit."
    )
    plan = build_answer_plan(
        "What end-of-line resistance does the ZXE loop use?",
        [_served_base_chunk(content, product_model="ZX2e/ZX5e")],
    )
    assert [row.kind for row in plan] == ["closed_loop_return_path"]
    assert build_answer_plan(
        "What end-of-line resistance does the ZXE loop use?",
        [_served_base_chunk(content, product_model="ZX2e/ZX5e")],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S119,
    ) == []

    single_sibling = build_answer_plan(
        "What end-of-line resistance does the ZXE loop use?",
        [_served_base_chunk(content, product_model="ZX2e")],
    )
    assert single_sibling == []

    mixed_family = build_answer_plan(
        "What end-of-line resistance does the ZXE loop use?",
        [_served_base_chunk(content, product_model="ZX2e/ABC5")],
    )
    assert mixed_family == []


def test_extracts_complete_closed_loop_relation_but_rejects_partial_path():
    complete = build_answer_plan(
        "Que resistencia de fin de linea lleva el lazo de la ZXE?",
        [
            _served_base_chunk(
                "Retorne el final del lazo al otro extremo del conector de lazo.\n"
                "Inicio Lazo (+) OUT / Inicio Lazo (-) OUT\n"
                "(+) Retorno / (-) Retorno",
                product_model="ZX2e/ZX5e",
            )
        ],
    )
    assert [row.kind for row in complete] == ["closed_loop_return_path"]
    assert validate_answer_plan(
        "Es un lazo cerrado: sale de Inicio Lazo OUT y vuelve a Retorno.", complete
    )["covered"] == 1

    partial = build_answer_plan(
        "Que resistencia de fin de linea lleva el lazo de la ZXE?",
        [
            _served_base_chunk(
                "Inicio Lazo (+) OUT / Inicio Lazo (-) OUT\n(+) Retorno / (-) Retorno",
                product_model="ZX2e/ZX5e",
            )
        ],
    )
    assert partial == []


def test_extracts_product_bound_cause_effect_output_selector():
    plan = build_answer_plan(
        "Como programo la ID3000 para activar una salida de sirena?",
        [
            _served_base_chunk(
                "Accion:\nActivar\nFuncion Especial: Circuito Sirena 1\n"
                "Seleccionar Equipos del Lazo: 1",
                product_model="ID3000",
            )
        ],
    )
    assert [row.kind for row in plan] == ["cause_effect_output_selector"]
    assert "Circuito Sirena 1" in plan[0].statement

    english = build_answer_plan(
        "How do I program an ID3000 sounder output?",
        [
            _served_base_chunk(
                "Action: Activate\nSpecial Function: Sounder Circuit 1\n"
                "Select Loop Devices: 1",
                product_model="ID3000",
            )
        ],
    )
    assert [row.kind for row in english] == ["cause_effect_output_selector"]

    partial = build_answer_plan(
        "Como programo la ID3000 para activar una salida de sirena?",
        [
            _served_base_chunk(
                "Accion: Activar\nFuncion Especial: Circuito Sirena 1",
                product_model="ID3000",
            )
        ],
    )
    assert partial == []

    legacy = build_answer_plan(
        "Como programo la ID3000 para activar una salida de sirena?",
        [
            _served_base_chunk(
                "Accion: Activar\nFuncion Especial: Circuito Sirena 1\n"
                "Seleccionar Equipos del Lazo: 1",
                product_model="ID3000",
            )
        ],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S119,
    )
    assert legacy == []


def test_keeps_stable_cause_effect_rules_separate_from_conflicting_menu_number():
    plan = build_answer_plan(
        "Como programo el retardo de salida de alarma en Pearl?",
        [
            _served_base_chunk(
                "Regla 1: para cualquier entrada de alarma todas las sirenas deben activarse. "
                "En Editar Configuracion seleccione 7: Causa y Efecto. "
                "Aqui hay dos reglas de causa-efecto por defecto. Deben eliminarse antes "
                "de crear reglas personalizadas.",
                chunk_id="rev-a",
                product_model="Pearl",
            ),
            _served_base_chunk(
                "En Editar Configuracion seleccione 8: Causa y Efecto.",
                chunk_id="rev-b",
                product_model="Pearl",
            ),
        ],
    )
    kinds = [row.kind for row in plan]
    assert "cause_effect_rule_behavior" in kinds
    assert "cause_effect_default_rules_precondition" in kinds
    assert "cause_effect_menu_path" not in kinds


def test_rejects_unknown_answer_planner_contract_version():
    assert ANSWER_PLANNER_CONTRACT_S119 != ANSWER_PLANNER_CONTRACT_S120
    try:
        build_answer_plan("question", [], planner_contract_version="typo")
    except ValueError as error:
        assert "planner_contract_version" in str(error)
    else:
        raise AssertionError("unknown planner contract was accepted")


def test_extracts_default_latched_fault_rule_for_reset_recovery():
    plan = build_answer_plan(
        "La RP1r no vuelve a normal tras resetear, que compruebo?",
        [
            _served_base_chunk(
                "Todas las averias son por defecto, enclavadas, y requieren de un "
                "rearme manual de la central para su restablecimiento.",
                product_model="RP1r",
            )
        ],
    )
    assert len(plan) == 1
    assert plan[0].kind == "default_latched_faults"
    revised, result = supplement_missing_obligations("Respuesta", plan)
    assert result["covered"] == 1
    assert "rearme manual" in revised


def test_does_not_extract_latched_rule_for_non_recovery_question():
    plan = build_answer_plan(
        "Que salidas tiene la central RP1r?",
        [
            _served_base_chunk(
                "Todas las averias son por defecto, enclavadas, y requieren rearme manual.",
                product_model="RP1r",
            )
        ],
    )
    assert plan == []


def test_mode_is_strict_and_default_off_is_bit_inert(monkeypatch):
    monkeypatch.delenv("ANSWER_OBLIGATION_PLANNER", raising=False)
    assert answer_planner_mode() == "off"
    answer = "byte-identical"
    assert apply_answer_planner("query", [], answer) == (answer, None)

    monkeypatch.setenv("ANSWER_OBLIGATION_PLANNER", "typo")
    try:
        answer_planner_mode()
    except RuntimeError as error:
        assert "off|observe|supplement|guided" in str(error)
    else:
        raise AssertionError("invalid planner mode was accepted")


def test_guided_mode_validates_without_post_generation_mutation():
    answer = "La respuesta omite el dato."
    chunk = _served_base_chunk(
        "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
        product_model="INSPIRE E10",
    )
    revised, metadata = apply_answer_planner(
        "Como se cablea el lazo de INSPIRE E10?", [chunk], answer, mode="guided"
    )
    assert revised == answer
    assert metadata["validation"]["covered"] == 0


def test_source_statement_anchors_are_stably_sorted():
    chunk = _chunk(
        "La capacidad maxima admite 32 equipos por lazo.",
        facet="query_alignment",
    )
    plan = build_answer_plan(
        "Cuantos equipos admite el lazo?",
        [chunk],
    )
    assert plan
    assert list(plan[0].required_anchors[1:]) == sorted(plan[0].required_anchors[1:])


def _relation_obligation(kind, statement, anchors):
    return AnswerObligation(
        obligation_id=f"obl_{kind}",
        fragment_number=3,
        candidate_id="synthetic-source",
        facet=f"served_relation:{kind}",
        kind=kind,
        statement=statement,
        required_anchors=tuple(anchors),
        source_start=0,
        source_end=len(statement),
    )


def _menu_conflict():
    evidence = tuple(
        AnswerConflictEvidence(
            fragment_number=index,
            candidate_id=f"synthetic-{value}",
            product_scope="SYNTHETIC-100",
            source_file=f"manual-r{value}",
            document_revision=value,
            value=value,
            statement=f"{value}: Cause and Effect",
            source_start=0,
            source_end=20,
        )
        for index, value in ((1, "7"), (2, "8"))
    )
    return AnswerConflict(
        conflict_id="conf_synthetic",
        kind="document_value_conflict",
        product_scope="synthetic100",
        operation="cause_effect_menu_path",
        values=("7", "8"),
        evidence=evidence,
    )


def test_s122_output_selector_uses_atomic_claim_not_navigation_label():
    content = (
        "Accion: Activar\nFuncion Especial: Circuito Sirena 1\n"
        "Seleccionar Equipos del Lazo: 1"
    )
    plan = build_answer_plan(
        "Como activo la salida de sirena de la ID3000?",
        [_served_base_chunk(content, product_model="ID3000")],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert [row.kind for row in plan] == ["cause_effect_output_selector"]
    assert plan[0].required_anchors == ("Activar", "Circuito Sirena 1")
    assert obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1.", plan[0]
    )
    assert obligation_covered(
        "Sí, Accion: Activar. Funcion Especial: Circuito Sirena 1.", plan[0]
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 2.", plan[0]
    )
    assert not obligation_covered(
        "Activar Circuito Sirena 1 no esta permitido.", plan[0]
    )
    assert not obligation_covered(
        "Accion: Activar el Rele 2.\nFuncion Especial: Circuito Sirena 1.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar el Rele 2.\nEl Circuito Sirena 1 queda deshabilitado.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1 queda deshabilitado.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1 no está habilitado.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "Sin embargo, Circuito Sirena 1 no debe activarse.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "Correccion: use Circuito Sirena 2.",
        plan[0],
    )
    assert not obligation_covered(
        "Accion: Activar. Funcion Especial: Circuito Sirena 1.\n\n"
        "Sin embargo, Circuito Sirena 1 no debe activarse.",
        plan[0],
    )
    for later_output_correction in (
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "Pero no debe activarse.",
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "Correccion: Funcion Especial: Circuito Sirena 2.",
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "Circuito Sirena 1 queda fuera de servicio.",
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "No debe activarse.",
        "- No debe activarse.\n\n"
        "Accion: Activar. Funcion Especial: Circuito Sirena 1.",
    ):
        assert not obligation_covered(later_output_correction, plan[0])
    for non_assertion in (
        "Activar Circuito Sirena 1 esta prohibido.",
        "Activar Circuito Sirena 1 es incorrecto.",
        "¿Debo activar Circuito Sirena 1?",
        "Puede que haya que activar Circuito Sirena 1.",
        "Se podria activar Circuito Sirena 1.",
        "Accion: Activar el Rele 2. El Circuito Sirena 1 no se usa.",
        "Accion: Activar. Funcion Especial: Circuito Sirena 1. "
        "No ejecutar esta configuracion.",
    ):
        assert not obligation_covered(non_assertion, plan[0])

    wrong_requested_output = build_answer_plan(
        "Como activo el Circuito Sirena 2 de la ID3000?",
        [_served_base_chunk(content, product_model="ID3000")],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "cause_effect_output_selector" not in [
        row.kind for row in wrong_requested_output
    ]


def test_s122_slash_family_rejects_relation_that_diverges_by_variant():
    def output_record(number):
        return _served_base_chunk(
            f"Accion: Activar\nFuncion Especial: Circuito Sirena {number}\n"
            "Seleccionar Equipos del Lazo: 1",
            chunk_id=f"variant-{number}",
            product_model="ZX2e/ZX5e",
        )

    plan = build_answer_plan(
        "Como activo la salida de sirena de la ZXe?",
        [output_record(1), output_record(2)],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "cause_effect_output_selector" not in [row.kind for row in plan]


def test_s122_slash_family_rejects_intra_chunk_output_and_topology_divergence():
    output_chunk = _served_base_chunk(
        "ZX2e: Accion: Activar, Funcion Especial: Circuito Sirena 1, "
        "Seleccionar Equipos del Lazo: 1\n"
        "ZX5e: Accion: Activar, Funcion Especial: Circuito Sirena 2, "
        "Seleccionar Equipos del Lazo: 1",
        product_model="ZX2e/ZX5e",
    )
    output_plan = build_answer_plan(
        "Como activo la salida de sirena de la ZXe?",
        [output_chunk],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "cause_effect_output_selector" not in [
        row.kind for row in output_plan
    ]

    topology_chunk = _served_base_chunk(
        "ZX2e: Loop Start OUT vuelve a Return y forma un complete loop circuit.\n"
        "ZX5e: Loop Start OUT no vuelve a Return y no es un closed loop.",
        product_model="ZX2e/ZX5e",
    )
    topology_plan = build_answer_plan(
        "Cual es la RFL del lazo de la ZXe?",
        [topology_chunk],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "closed_loop_return_path" not in [
        row.kind for row in topology_plan
    ]


def test_s122_slash_family_propagates_multiline_variant_headers():
    output_chunk = _served_base_chunk(
        "ZX2e:\n"
        "Accion: Activar\nFuncion Especial: Circuito Sirena 1\n"
        "Seleccionar Equipos del Lazo: 1\n"
        "ZX5e:\n"
        "Accion: Activar\nFuncion Especial: Circuito Sirena 2\n"
        "Seleccionar Equipos del Lazo: 1",
        product_model="ZX2e/ZX5e",
    )
    output_plan = build_answer_plan(
        "Como activo la salida de sirena de la ZXe?",
        [output_chunk],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "cause_effect_output_selector" not in [
        row.kind for row in output_plan
    ]

    topology_chunk = _served_base_chunk(
        "ZX2e:\nLoop Start OUT vuelve a Return como complete loop circuit.\n"
        "ZX5e:\nLoop Start OUT no vuelve a Return y no es closed loop.",
        product_model="ZX2e/ZX5e",
    )
    topology_plan = build_answer_plan(
        "Cual es la RFL del lazo de la ZXe?",
        [topology_chunk],
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "closed_loop_return_path" not in [
        row.kind for row in topology_plan
    ]


def test_s122_closed_loop_requires_positive_bounded_relation():
    obligation = _relation_obligation(
        "closed_loop_return_path",
        "Loop Start OUT returns to Return and forms a complete loop circuit.",
        ("Loop Start", "OUT", "Return"),
    )
    assert obligation_covered(
        "Wire a complete loop circuit: Loop Start OUT returns to Return.",
        obligation,
    )
    assert not obligation_covered(
        "This is not a closed loop. Loop Start OUT returns to Return.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT returns to Return as a complete loop circuit? No.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT is shown here.\n\n"
        "An unrelated complete loop circuit uses Return elsewhere.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT alimenta una rama. Return pertenece a otra. "
        "Un circuito distinto es un complete loop circuit.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT alimenta una rama; Return pertenece a otra; "
        "un circuito distinto es un complete loop circuit.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT returns to Return as a complete loop circuit. "
        "Cada circuito lleva una resistencia final de linea.",
        obligation,
    )
    assert not obligation_covered(
        "Loop Start OUT returns to Return as a complete loop circuit. "
        "Instale una resistencia EOL de 10 kohm.",
        obligation,
    )
    for misleading_negation in (
        "Loop Start OUT returns to Return as a complete loop circuit. "
        "Sin embargo, instale una resistencia EOL de 10 kohm.",
        "Loop Start OUT returns to Return as a complete loop circuit. "
        "No obstante, instale una RFL de 10 kohm.",
        "Loop Start OUT returns to Return as a complete loop circuit. "
        "No olvide instalar una resistencia EOL de 10 kohm.",
    ):
        assert not obligation_covered(misleading_negation, obligation)
    assert obligation_covered(
        "El fragmento no define una RFL. Loop Start OUT returns to Return "
        "as a complete loop circuit.",
        obligation,
    )
    assert obligation_covered(
        "Lazo sin RFL. Loop Start OUT returns to Return as a complete loop circuit.",
        obligation,
    )
    terminal = _relation_obligation(
        "terminal_bundle",
        "Loop Start OUT and Return.",
        ("Loop Start", "OUT", "Return"),
    )
    assert not obligation_covered(
        "Do not use Loop Start OUT or Return for this circuit.", terminal
    )


def test_s122_default_rule_deletion_rejects_negated_instruction():
    obligation = _relation_obligation(
        "cause_effect_default_rules_precondition",
        "Deben eliminarse las dos reglas por defecto.",
        ("dos reglas", "por defecto", "eliminar"),
    )
    assert obligation_covered("Deben eliminarse las dos reglas por defecto.", obligation)
    assert not obligation_covered(
        "Las dos reglas por defecto no deben eliminarse.", obligation
    )
    assert not obligation_covered(
        "Las dos reglas por defecto deben eliminarse? No.", obligation
    )


def test_s122_rule_behavior_binds_exact_rule_identifier():
    obligation = _relation_obligation(
        "cause_effect_rule_behavior",
        "Regla 2: cualquier entrada de alarma activa todas las sirenas.",
        ("Regla 2", "cualquier entrada de alarma", "todas las sirenas"),
    )
    assert obligation_covered(
        "Regla 2: cualquier entrada de alarma activa todas las sirenas.",
        obligation,
    )
    assert obligation_covered(
        "Sí, Regla 2: cualquier entrada de alarma activa todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 1: cualquier entrada de alarma activa todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2 no se aplica. Regla 1 establece que cualquier entrada "
        "de alarma activa todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2 queda anulada, mientras Regla 1 establece que cualquier "
        "entrada de alarma activa todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2 queda anulada, pero cualquier entrada de alarma activa "
        "todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2 queda revocada, pero cualquier entrada de alarma activa "
        "todas las sirenas.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2: cualquier entrada de alarma activa todas las sirenas. "
        "Sin embargo, Regla 2 no las activa.",
        obligation,
    )
    assert not obligation_covered(
        "Regla 2: cualquier entrada de alarma activa todas las sirenas. "
        "Correccion: Regla 2 queda revocada.",
        obligation,
    )
    for later_rule_correction in (
        "Regla 2: cualquier entrada de alarma activa todas las sirenas. "
        "Pero ya no se aplica.",
        "Regla 2: cualquier entrada de alarma activa todas las sirenas. "
        "Regla 2 queda suspendida.",
        "Regla 2: cualquier entrada de alarma activa todas las sirenas. "
        "No se aplica.",
        "- No se aplica.\n\n"
        "Regla 2: cualquier entrada de alarma activa todas las sirenas.",
    ):
        assert not obligation_covered(later_rule_correction, obligation)


def test_s122_conflict_requires_both_values_and_explicit_disclosure():
    conflict = _menu_conflict()
    one_sided = validate_answer_conflicts(
        "Select 8: Cause and Effect.", [conflict]
    )
    assert len(one_sided["unsafe"]) == 1
    disclosed = validate_answer_conflicts(
        "The revisions differ: one states 7: Cause and Effect and the other "
        "states 8: Cause and Effect.",
        [conflict],
    )
    assert disclosed["unsafe"] == []
    unrelated_disclosure = validate_answer_conflicts(
        "Other manuals differ for a separate setting.\n\n"
        "Use 7: Cause and Effect here; another page says 8: Cause and Effect.",
        [conflict],
    )
    assert len(unrelated_disclosure["unsafe"]) == 1
    menu_number = validate_answer_conflicts(
        "Seleccione el menu numero 8 de Causa y Efecto.", [conflict]
    )
    assert len(menu_number["unsafe"]) == 1
    one_sided_choice = validate_answer_conflicts(
        "Las revisiones discrepan: 7: Causa y Efecto es incorrecto; "
        "seleccione 8: Causa y Efecto.",
        [conflict],
    )
    assert len(one_sided_choice["unsafe"]) == 1
    negated_disclosure = validate_answer_conflicts(
        "No existe discrepancia: seleccione 7: Causa y Efecto, no "
        "8: Causa y Efecto.",
        [conflict],
    )
    assert len(negated_disclosure["unsafe"]) == 1
    word_number = validate_answer_conflicts(
        "Seleccione el menu numero ocho de Causa y Efecto.", [conflict]
    )
    assert len(word_number["unsafe"]) == 1
    coreferential_choice = validate_answer_conflicts(
        "Las revisiones discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto. Use esta ultima.",
        [conflict],
    )
    assert len(coreferential_choice["unsafe"]) == 1
    no_choice = validate_answer_conflicts(
        "Las revisiones discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto. No seleccione ninguna hasta confirmar la revision.",
        [conflict],
    )
    assert no_choice["unsafe"] == []
    relative_choice = validate_answer_conflicts(
        "En Causa y Efecto, seleccione la ultima opcion del menu.",
        [conflict],
    )
    assert len(relative_choice["unsafe"]) == 1
    postfix_negated_disclosure = validate_answer_conflicts(
        "La discrepancia no existe: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        [conflict],
    )
    assert len(postfix_negated_disclosure["unsafe"]) == 1
    obsolete_disclosure = validate_answer_conflicts(
        "La discrepancia ya no aplica: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        [conflict],
    )
    assert len(obsolete_disclosure["unsafe"]) == 1
    false_existential_disclosure = validate_answer_conflicts(
        "Existe una discrepancia falsa: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        [conflict],
    )
    assert len(false_existential_disclosure["unsafe"]) == 1
    for rejected_disclosure in (
        "Los fragmentos discrepan falsamente: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        "Es falso que los fragmentos discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        "Es mentira que las revisiones discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        "Si los fragmentos discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto.",
        'El tecnico dijo: "Los fragmentos discrepan: 7: Causa y Efecto; '
        '8: Causa y Efecto."',
    ):
        result = validate_answer_conflicts(rejected_disclosure, [conflict])
        assert len(result["unsafe"]) == 1
    contradicted_disclosure = validate_answer_conflicts(
        "Las revisiones discrepan: 7: Causa y Efecto; "
        "8: Causa y Efecto; las revisiones no discrepan.",
        [conflict],
    )
    assert len(contradicted_disclosure["unsafe"]) == 1
    english_later_contradiction = validate_answer_conflicts(
        "The revisions differ: one states 7: Cause and Effect and the other "
        "states 8: Cause and Effect.\n\nThe revisions do not differ.",
        [conflict],
    )
    assert len(english_later_contradiction["unsafe"]) == 1
    for coreferential_denial in (
        "Las revisiones discrepan: 7: Causa y Efecto; 8: Causa y Efecto. "
        "En realidad, ambas coinciden.",
        "The revisions differ: one states 7: Cause and Effect and the other "
        "states 8: Cause and Effect. The revisions are the same.",
        "The revisions differ: one states 7: Cause and Effect and the other "
        "states 8: Cause and Effect. Actually, there is no difference.",
        "Las revisiones discrepan: 7: Causa y Efecto; 8: Causa y Efecto. "
        "Ambas coinciden.",
        "The revisions differ: one states 7: Cause and Effect and the other "
        "states 8: Cause and Effect. Both agree.",
    ):
        result = validate_answer_conflicts(coreferential_denial, [conflict])
        assert len(result["unsafe"]) == 1


def test_s122_conflict_ignores_unrelated_operational_directives():
    conflict = _menu_conflict()
    answer = (
        "Los fragmentos discrepan para el número de menú de Causa y Efecto: "
        "[F1] indica 7: Causa y Efecto; [F2] indica 8: Causa y Efecto. "
        "No seleccione ningún número de menú hasta confirmar la revisión.\n\n"
        "Seleccione 5: Retardo Activación Salidas.\n\n"
        "Seleccionar el tipo de retardo."
    )
    result = validate_answer_conflicts(answer, [conflict])
    assert result["unsafe"] == []
    assert result["rows"][0]["directive_values"] == []


def test_s122_conflict_scopes_relative_directives_to_the_conflict_window():
    conflict = _menu_conflict()
    disclosure = (
        "Los fragmentos discrepan para el número de menú de Causa y Efecto: "
        "[F1] indica 7: Causa y Efecto; [F2] indica 8: Causa y Efecto. "
        "No seleccione ningún número hasta confirmar la revisión."
    )
    unrelated = validate_answer_conflicts(
        disclosure
        + "\n\nPara el tipo de retardo, seleccione la primera opción.",
        [conflict],
    )
    assert unrelated["unsafe"] == []

    for coreferential_choice in (
        disclosure + " Use la segunda.",
        disclosure + " Seleccione esa opción.",
        disclosure + " Choose that option.",
    ):
        result = validate_answer_conflicts(coreferential_choice, [conflict])
        assert len(result["unsafe"]) == 1


def _pearl_menu_conflict_chunks():
    return [
        {
            **_served_base_chunk(
                "En Editar Configuración seleccione 7: Causa y Efecto.",
                chunk_id="pearl-menu-7",
                product_model="PEARL",
            ),
            "source_file": "Pearl-config.pdf",
            "document_revision": "997-671-005-3",
        },
        {
            **_served_base_chunk(
                "Menú Editar Configuración\n8: Causa y Efecto",
                chunk_id="pearl-menu-8",
                product_model="PEARL",
            ),
            "source_file": "Pearl-config.pdf",
            "document_revision": "997-671-005-3",
        },
    ]


def test_conflict_guard_repairs_only_unsafe_paragraph_and_revalidates():
    answer = (
        "Programación del retardo de salida en PEARL.\n\n"
        "Desde Editar Configuración, seleccione 8: Causa y Efecto [F2].\n\n"
        "Seleccione 5: Retardo Activación Salidas para operar el panel [F1].\n\n"
        "Fuente: manual PEARL."
    )
    revised, trace = apply_answer_conflict_guard(
        "¿Cómo programo el retardo de salida en la central PEARL?",
        _pearl_menu_conflict_chunks(),
        answer,
    )
    assert trace["action"] == "surgical_repair"
    assert trace["repaired_blocks"] == 1
    assert "seleccione 8: Causa y Efecto" not in revised
    assert "[F1] indica 7: Causa y Efecto" in revised
    assert "[F2] indica 8: Causa y Efecto" in revised
    assert "Seleccione 5: Retardo Activación Salidas" in revised
    assert revised.startswith("Programación del retardo de salida en PEARL.")
    assert revised.endswith("Fuente: manual PEARL.")


def test_conflict_guard_safe_and_not_applicable_paths_are_byte_identical():
    safe = (
        "Los fragmentos discrepan para el número de menú de Causa y Efecto: "
        "[F1] indica 7: Causa y Efecto; [F2] indica 8: Causa y Efecto. "
        "No seleccione ningún número de menú hasta confirmar la revisión.\n\n"
        "Seleccione 5: Retardo Activación Salidas."
    )
    passed, pass_trace = apply_answer_conflict_guard(
        "¿Cómo programo el retardo de salida en la central PEARL?",
        _pearl_menu_conflict_chunks(),
        safe,
    )
    untouched, na_trace = apply_answer_conflict_guard(
        "¿Qué tensión tiene la central PEARL?",
        _pearl_menu_conflict_chunks(),
        "Respuesta sin conflicto.\n",
    )
    assert passed == safe
    assert pass_trace["action"] == "pass"
    assert untouched == "Respuesta sin conflicto.\n"
    assert na_trace["action"] == "not_applicable"


def test_conflict_guard_removes_repeated_unsafe_choices_once():
    answer = (
        "Seleccione 8: Causa y Efecto.\n\n"
        "Como recordatorio, use 7: Causa y Efecto."
    )
    revised, trace = apply_answer_conflict_guard(
        "¿Cómo programo el retardo de salida en la central PEARL?",
        _pearl_menu_conflict_chunks(),
        answer,
    )
    assert trace["action"] == "surgical_repair"
    assert trace["repaired_blocks"] == 2
    assert revised.count("Los fragmentos discrepan") == 1
    assert "Seleccione 8" not in revised
    assert "use 7" not in revised


def test_s122_reconstructs_core_failure_without_retaining_unsafe_draft():
    plan = [
        _relation_obligation(
            "closed_loop_return_path",
            "Retorne el final del lazo al panel; Inicio Lazo OUT; Retorno; lazo cerrado.",
            ("Inicio Lazo", "OUT", "Retorno"),
        )
    ]
    revised, metadata = enforce_answer_contract(
        "Cual es la resistencia final de linea del lazo de TEST-100?",
        "Cada circuito lleva una resistencia final de linea.",
        plan,
        [],
    )
    assert metadata["action"] == "source_bound_reconstruction"
    assert metadata["query_core_coverage"] is True
    assert "Cada circuito" not in revised
    assert "Respuesta verificada con la evidencia disponible" in revised
    assert metadata["validation"]["covered"] == 1


def test_s122_fail_closes_when_only_prerequisites_cover_delay_question():
    plan = [
        _relation_obligation(
            "cause_effect_rule_behavior",
            "Regla 1: cualquier entrada de alarma activa todas las sirenas.",
            ("Regla 1", "cualquier entrada de alarma", "todas las sirenas"),
        ),
        _relation_obligation(
            "cause_effect_default_rules_precondition",
            "Deben eliminarse las dos reglas por defecto.",
            ("dos reglas", "por defecto", "eliminar"),
        ),
    ]
    revised, metadata = enforce_answer_contract(
        "Como programo el retardo de salida en TEST-100?",
        "Seleccione 8: Causa y Efecto.",
        plan,
        [_menu_conflict()],
    )
    assert metadata["action"] == "fail_closed"
    assert metadata["query_core_coverage"] is False
    assert "No es posible confirmar el procedimiento completo" in revised
    assert "Seleccione 8" not in revised
    assert "discrepan" in revised


def test_s122_fail_closes_even_when_safe_draft_covers_only_delay_prerequisites():
    plan = [
        _relation_obligation(
            "cause_effect_rule_behavior",
            "Regla 1: cualquier entrada de alarma activa todas las sirenas.",
            ("Regla 1", "cualquier entrada de alarma", "todas las sirenas"),
        ),
        _relation_obligation(
            "cause_effect_default_rules_precondition",
            "Deben eliminarse las dos reglas por defecto.",
            ("dos reglas", "por defecto", "eliminar"),
        ),
    ]
    safe_but_incomplete = (
        "Regla 1: cualquier entrada de alarma activa todas las sirenas. "
        "Deben eliminarse las dos reglas por defecto.\n\n"
        "Las revisiones discrepan: una indica 7: Causa y Efecto y otra "
        "8: Causa y Efecto. No seleccione ninguna hasta confirmar la revision."
    )
    revised, metadata = enforce_answer_contract(
        "Como programo el retardo de salida en TEST-100?",
        safe_but_incomplete,
        plan,
        [_menu_conflict()],
    )
    assert metadata["initial_validation"]["covered"] == 2
    assert metadata["initial_conflict_validation"]["unsafe"] == []
    assert metadata["action"] == "fail_closed"
    assert metadata["query_core_coverage"] is False
    assert "No es posible confirmar el procedimiento completo" in revised


def test_s122_query_core_guard_fails_closed_without_contract_evidence():
    cases = (
        (
            "Como programo el retardo de salida?",
            "Seleccione el menu 8 y ajuste 30 segundos.",
        ),
        (
            "Que resistencia EOL lleva el lazo?",
            "Instale una resistencia de 10 kohm.",
        ),
    )
    for query, unsafe_draft in cases:
        revised, metadata = enforce_answer_contract(query, unsafe_draft, [], [])
        assert metadata["action"] == "fail_closed"
        assert metadata["query_core_coverage"] is False
        assert unsafe_draft not in revised


def test_s122_query_core_guard_does_not_claim_unsupported_eol_or_output_specs():
    unguarded_queries = (
        "Que resistencia EOL llevan las lineas de zona?",
        "Que salidas de rele y sirena tiene este detector?",
    )
    for query in unguarded_queries:
        draft = "Respuesta tecnica fuera de los tipos contractuales S122."
        revised, metadata = enforce_answer_contract(query, draft, [], [])
        assert metadata["action"] == "pass"
        assert metadata["query_core_coverage"] is True
        assert revised == draft
