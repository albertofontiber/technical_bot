import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_locator import (  # noqa: E402
    collapsed_superscript_bridge,
    decimal_notation_bridge,
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


def test_normal_high_context_lane_remains_available():
    spanish = (
        "Potencia nominal: maximo 2 A carga resistiva 30 V CC y "
        "0,5 A carga resistiva 30 V CA"
    )
    assert support_candidate_priority(
        CONTACT_VALUE, CONTACT_FACT, spanish, same_family=True
    ) is not None
