import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_locator import (  # noqa: E402
    _unit_quantities,
    collapsed_superscript_bridge,
    decimal_notation_bridge,
    kilo_prefix_bridge,
    support_candidate_priority,
    support_l1_guard_allows,
)


CONTACT_VALUE = "2 A / 0,5 A"
CONTACT_FACT = (
    "Especificacion electrica de los contactos de rele: maximo 2 A "
    "(carga resistiva 30 V CC) / maximo 0,5 A (carga resistiva 30 V CA)"
)


def test_same_family_decimal_bridge_admits_es_gold_vs_en_manual_for_review():
    english = "Contact rating 2 A at 30 VDC resistive load; 0.5 A at 30 VAC resistive load"
    priority = support_candidate_priority(
        CONTACT_VALUE, CONTACT_FACT, english, same_family=True
    )
    assert priority is not None
    assert priority[0] == 1
    assert decimal_notation_bridge(CONTACT_VALUE, english)


def test_decimal_bridge_reads_number_and_unit_split_across_markdown_cells():
    table = (
        "| Contact Rating | 2 | A | 30 VDC resistive load |\n"
        "| | 0.5 | A | 30 VAC resistive load |"
    )
    priority = support_candidate_priority(
        CONTACT_VALUE, CONTACT_FACT, table, same_family=True
    )
    assert priority is not None
    assert priority[0] == 1


def test_decimal_bridge_rejects_cross_family_incomplete_and_wrong_values():
    complete = "Contact rating 2 A at 30 VDC; 0.5 A at 30 VAC"
    assert support_candidate_priority(
        CONTACT_VALUE, CONTACT_FACT, complete, same_family=False
    ) is None
    assert support_candidate_priority(
        CONTACT_VALUE,
        CONTACT_FACT,
        "Contact rating 0.5 A at 30 VAC",
        same_family=True,
    ) is None
    assert support_candidate_priority(
        CONTACT_VALUE,
        CONTACT_FACT,
        "Contact rating 2 A at 30 VDC; 0.55 A at 30 VAC",
        same_family=True,
    ) is None


def test_collapsed_superscript_is_candidate_recall_not_cross_family_credit():
    value = "10^5"
    fact = "vida util minima de los contactos de rele: 10^5 operaciones"
    extracted = "Minimum contact life: 105 operations"
    priority = support_candidate_priority(value, fact, extracted, same_family=True)
    assert collapsed_superscript_bridge(value, extracted)
    assert priority == (1, 0.0)
    assert support_candidate_priority(value, fact, extracted, same_family=False) is None


def test_l1_guard_preserves_prior_semantic_support_only_for_same_family_bridges():
    table = (
        "| Contact Rating | 2 | A | 30 VDC resistive load |\n"
        "| | 0.5 | A | 30 VAC resistive load |\n"
        "| Life Time | 105 | | Operations |"
    )
    assert support_l1_guard_allows(
        CONTACT_VALUE, CONTACT_FACT, table, same_family=True
    )
    assert support_l1_guard_allows(
        "10^5", "vida util minima: 10^5 operaciones", table, same_family=True
    )
    assert not support_l1_guard_allows(
        CONTACT_VALUE, CONTACT_FACT, table, same_family=False
    )
    assert not support_l1_guard_allows(
        "10^5", "vida util minima: 10^5 operaciones", table, same_family=False
    )


def test_collapsed_superscript_bridge_rejects_wrong_exponent_and_unrelated_number():
    value = "10^5"
    fact = "vida util minima de los contactos de rele: 10^5 operaciones"
    assert not collapsed_superscript_bridge(value, "Minimum contact life: 106 operations")
    assert support_candidate_priority(
        value, fact, "Unrelated catalogue number 1050", same_family=True
    ) is None
    assert support_candidate_priority(
        value, fact, "Unrelated catalogue code 105", same_family=True
    ) is None


# ─── s287 P0 — kilo_prefix_bridge (S5/DEC-096c): 6K8 ↔ 6,8kΩ ↔ 6.8kΩ ↔ 6800Ω ───
# Caso real hp018#1: valor '6K8', chunk servido ZXe p.22 escribe «RFL (6800Ω)» — el guard
# L1 lo mataba por falta de puente de prefijo kilo. Sol-1: el puente solo ACREDITA vía
# same_family (la fila cross-family con el mismo valor queda fuera — DEC-091b).
RFL_VALUE = "6K8"
RFL_FACT = (
    "Resistencia de fin de linea (RFL) = 6,8 kOhm (6K8), 0,5 W minimo, en el final "
    "de cada circuito de sirena (en la ultima sirena) para la supervision"
)
RFL_CHUNK = (
    "Connecting four circular siren devices in series, ending with RFL (6800Ω) "
    "resistor - SIRENA A (-) black line running parallel"
)


def test_kilo_bridge_rkm_code_reaches_base_ohm_spelling():
    assert kilo_prefix_bridge(RFL_VALUE, RFL_CHUNK)
    priority = support_candidate_priority(RFL_VALUE, RFL_FACT, RFL_CHUNK, same_family=True)
    assert priority is not None
    assert priority[0] == 1
    assert support_l1_guard_allows(RFL_VALUE, RFL_FACT, RFL_CHUNK, same_family=True)


def test_kilo_bridge_all_spec_notations_are_equivalent():
    # las 4 grafías del spec canonicalizan a la MISMA cantidad física
    assert (
        _unit_quantities("6K8")
        == _unit_quantities("6800Ω")
        == _unit_quantities("6,8kΩ")
        == _unit_quantities("6.8kΩ")
        == _unit_quantities("6,8 kOhm")
        == {"6800ohm"}
    )
    # y el puente cruza en ambas direcciones grafía-valor ↔ grafía-content
    assert kilo_prefix_bridge("6,8 kOhm", "RFL (6800Ω)")
    assert kilo_prefix_bridge("6800Ω", "resistencia final de linea 6k8")
    assert kilo_prefix_bridge("6800 Ohmios", "RFL de 6,8 kΩ")


def test_kilo_bridge_same_notation_is_not_a_bridge():
    # misma grafía en ambos lados → el carril normal decide, el puente no aporta
    assert not kilo_prefix_bridge("6K8", "resistencia RFL 6k8 en la ultima sirena")
    assert not kilo_prefix_bridge("6800Ω", "RFL (6800Ω)")


def test_kilo_bridge_rejects_wrong_values_and_cross_family():
    # 2K2 ≠ 6800Ω: ni puente ni candidato (quantities_complete lo bloquea ademas)
    assert not kilo_prefix_bridge("2K2", RFL_CHUNK)
    assert support_candidate_priority("2K2", RFL_FACT, RFL_CHUNK, same_family=True) is None
    assert not support_l1_guard_allows("2K2", RFL_FACT, RFL_CHUNK, same_family=True)
    # mismo valor pero fila CROSS-FAMILY (el primo ZXAE/ZXEE con '6800 Ohmios'):
    # el puente detecta la re-grafía pero NO acredita — Sol-1/DEC-091b
    assert kilo_prefix_bridge(RFL_VALUE, "Salida A 6800 Ohmios sirenas de placa")
    assert support_candidate_priority(
        RFL_VALUE, RFL_FACT, "Salida A 6800 Ohmios sirenas de placa", same_family=False
    ) is None
    assert not support_l1_guard_allows(
        RFL_VALUE, RFL_FACT, "Salida A 6800 Ohmios sirenas de placa", same_family=False
    )


def test_kilo_bridge_requires_fact_context_overlap():
    # el valor re-grafiado SIN el contexto del hecho (otra tabla, otro atributo) no entra
    unrelated = "Fuse rating table: primary 6800Ω auxiliary winding impedance"
    assert support_candidate_priority(RFL_VALUE, RFL_FACT, unrelated, same_family=True) is None


def test_kilo_quantities_do_not_disturb_existing_units():
    # el resto de unidades conserva su canónica previa (sin escalado)
    assert _unit_quantities(CONTACT_VALUE) == {"2a", "0.5a"}
    assert _unit_quantities("3 kW") == {"3000w"}
    assert _unit_quantities("47 kohm y 30 vdc") == {"47000ohm", "30vdc"}


def test_normal_high_context_lane_remains_available():
    spanish = (
        "Potencia nominal: maximo 2 A carga resistiva 30 V CC y "
        "0,5 A carga resistiva 30 V CA"
    )
    assert support_candidate_priority(
        CONTACT_VALUE, CONTACT_FACT, spanish, same_family=True
    ) is not None
