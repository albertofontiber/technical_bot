import json
from pathlib import Path

import pytest

from src.rag.structured_claims import claim_supported, extract_numeric_claims


FIXTURES = Path(__file__).parent / "fixtures/s107_structured_claims_v2.json"


def test_hp014_claim_binds_resistance_operator_value_and_unit():
    statement = "La resistencia maxima del lazo en el ID2000 no debe superar los 35 ohmios."
    source = (
        "La resistencia maxima del lazo no debe superar los 35 ohmios. "
        "La capacidad del cable debe ser inferior a 0,5 uF."
    )
    result = claim_supported(statement, source, entity_id="ID2000")
    assert result["supported"] is True
    claim = result["statement_claims"][0]
    assert (claim["attribute"], claim["operator"], claim["value"], claim["unit"]) == (
        "loop_resistance",
        "maximum",
        "35",
        "ohm",
    )


def test_same_number_different_attribute_or_unit_is_rejected():
    source = "La tension maxima es 24 V; la resistencia maxima del lazo es 35 ohmios."
    false_statement = "La tension maxima del ID2000 es 35 V."
    result = claim_supported(false_statement, source, entity_id="ID2000")
    assert result["supported"] is False


def test_wrong_operator_is_rejected_even_when_value_and_unit_match():
    source = "La resistencia minima del lazo es 35 ohmios."
    statement = "La resistencia maxima del lazo es 35 ohmios."
    assert claim_supported(statement, source, entity_id="ID2000")["supported"] is False


def test_table_markup_and_column_transposition_fail_closed():
    table = "| Modelo | Tension maxima | Resistencia lazo |\n| A | 24 V | 35 ohmios |"
    statement = "La tension maxima del modelo A es 35 V."
    result = claim_supported(statement, table, entity_id="A100")
    assert result["supported"] is False
    assert result["source_claims"] == []


def test_decimal_comma_and_microfarad_are_canonicalized():
    claims = extract_numeric_claims(
        "La capacidad maxima del cable es 0,5 uF.", entity_id="ID2000"
    )
    assert len(claims) == 1
    assert (claims[0].value, claims[0].unit) == ("0.5", "microfarad")


def test_conflicting_model_mention_fails_closed():
    statement = "La resistencia maxima del lazo ID3000 es 35 ohmios."
    source = "La resistencia maxima del lazo ID2000 es 35 ohmios."
    result = claim_supported(statement, source, entity_id="ID2000")
    assert result["supported"] is False


def test_range_claim_binds_both_bounds_and_inherited_unit():
    result = claim_supported(
        "En la RP1R, el tiempo de activacion es variable de 05 a 295 seg.",
        "El tiempo de activacion esta comprendido entre 5 y 295 segundos.",
        entity_id="RP1R",
    )
    assert result["supported"] is True
    claim = result["source_claims"][0]
    assert (
        claim["operator"],
        claim["lower_value"],
        claim["upper_value"],
        claim["unit"],
    ) == ("range_inclusive", "5", "295", "second")


def test_markdown_table_binds_model_row_attribute_column_and_header():
    source = (
        "| Modelo | Tension maxima | Resistencia maxima del lazo |\n"
        "| --- | --- | --- |\n"
        "| P100 | 24 V | 35 ohmios |\n"
        "| P200 | 48 V | 18 ohmios |"
    )
    result = claim_supported(
        "La tension maxima del P100 es 24 V.", source, entity_id="P100"
    )
    assert result["supported"] is True
    source_claim = next(
        claim for claim in result["source_claims"] if claim["attribute"] == "voltage"
    )
    assert source_claim["source_kind"] == "markdown_table"
    assert source_claim["header"] == "Tension maxima"
    assert source_claim["table_row"] == 2
    assert source_claim["table_column"] == 1


def test_realistic_key_value_table_binds_range_to_description_cell():
    source = (
        "| Valor variable de 05 a 295 seg. | Tiempo de activacion del circuito "
        "de extincion, o periodo de inundacion. |\n"
        "| --- | --- |\n"
        "| -- | Circuito activado hasta rearme de la central |"
    )
    result = claim_supported(
        "En la RP1R, el tiempo de activacion es variable de 5 a 295 segundos.",
        source,
        entity_id="RP1R",
    )
    assert result["supported"] is True
    assert result["source_claims"][0]["binding"] == "table[row=0,key_value]"


COHORT = json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("fixture", COHORT, ids=lambda row: row["id"])
def test_non_target_adversarial_conformance_cohort(fixture):
    result = claim_supported(
        fixture["statement"], fixture["source"], entity_id=fixture["entity"]
    )
    assert result["supported"] is fixture["expected"]
