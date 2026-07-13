from src.rag.evidence_coverage import (
    ALIGNED_CONFIG,
    MULTIFACET_CONFIG,
    STRICT_ALIGNED_CONFIG,
    _project_terms,
    _tokens,
    select_evidence_coverage_cards,
)


def test_selects_exact_limit_span_for_installation_archetype():
    content = (
        "Introducción general de cableado y montaje sin valores.\n\n"
        "La resistencia máxima del lazo no debe superar los 35 ohmios. "
        "Puede comprobarlo midiendo entre los extremos del circuito."
    )
    cards = select_evidence_coverage_cards(
        [{"id": "c1", "content": content}], archetype="connect_install_wire"
    )
    assert any("35 ohmios" in card["quote"] for card in cards)
    assert all(card["quote"] in content for card in cards)


def test_unknown_archetype_and_short_headings_fail_closed():
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": "Programación"}], archetype="unknown"
    ) == []
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": "Instalación"}], archetype="connect_install_wire"
    ) == []


def test_configured_stems_match_gender_and_clitics_without_target_values():
    content = "La resistencia máxima debe comprobarlo el instalador mediante medición."
    projected = _project_terms(
        _tokens(content), ["limite", "maxim", "seguridad", "comprobar", "medicion"]
    )
    assert {"maxim", "comprobar", "medicion"}.issubset(projected)


def test_comparison_facet_can_return_two_exact_spans_under_global_cap():
    content = (
        "El modelo A admite cuatro LIB y 792 dispositivos en total en el sistema.\n\n"
        "El modelo B admite dos LIB y 396 dispositivos en total en el sistema."
    )
    cards = select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="capacity_quantity",
        config_path=MULTIFACET_CONFIG,
    )
    totals = [card for card in cards if card["facet"] == "system_total"]
    assert len(totals) == 2
    assert all(card["quote"] in content for card in totals)


def test_required_any_rejects_table_header_without_redundancy_signal():
    content = (
        "| Borne | Señal | Cableado |\n| 1 | PWR + | Alimentación principal |\n\n"
        "El cable de alimentación redundante se conecta a los bornes 3 y 4."
    )
    cards = select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="replace_without_loss",
        config_path=MULTIFACET_CONFIG,
    )
    redundant = next(card for card in cards if card["facet"] == "redundant_power")
    assert "redundante" in redundant["quote"]


def test_query_alignment_rejects_generic_facet_match_without_question_anchor():
    content = "La matriz contiene una condición de entrada y una acción de salida."
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="program_delay_cause_effect",
        config_path=ALIGNED_CONFIG,
        query="¿Cómo se configuran las contraseñas de nivel 2 y nivel 3?",
    ) == []


def test_query_alignment_keeps_distinctive_relay_fault_evidence():
    content = (
        "La condición de avería no queda enclavada; el relé cambia cuando falla "
        "la alimentación y la sirena queda activa."
    )
    cards = select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="fault_reset_recovery",
        config_path=ALIGNED_CONFIG,
        query="¿Cómo se comportan el relé, la sirena y la alimentación ante una avería?",
    )
    assert cards
    assert {"rele", "sirena"}.issubset(set(cards[0]["query_term_hits"]))


def test_strict_alignment_rejects_single_generic_line_anchor():
    content = (
        "En los repetidores, la resistencia de terminación de línea queda en el circuito."
    )
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="connect_install_wire",
        config_path=STRICT_ALIGNED_CONFIG,
        query="¿Cómo se conecta un módulo de aislamiento de línea en un lazo ID2000?",
    ) == []


def test_strict_alignment_rejects_two_weak_programming_anchors():
    content = (
        "El retardo aplicado a la activación de la salida corresponde a la Zona 20."
    )
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="program_delay_cause_effect",
        config_path=STRICT_ALIGNED_CONFIG,
        query=(
            "¿Cómo se programa una zona para activar una salida solo cuando haya "
            "coincidencia de dos detectores?"
        ),
    ) == []


def test_strict_alignment_does_not_count_solo_as_a_technical_anchor():
    content = (
        "SIRENAS: seleccionar Zona. Conexión a: solo control de matriz de equipos."
    )
    assert select_evidence_coverage_cards(
        [{"id": "c1", "content": content}],
        archetype="program_delay_cause_effect",
        config_path=STRICT_ALIGNED_CONFIG,
        query=(
            "¿Cómo se programa una zona para activar una sirena solo cuando haya "
            "coincidencia de dos detectores?"
        ),
    ) == []
