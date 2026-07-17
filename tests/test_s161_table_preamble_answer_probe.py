from scripts.s161_table_preamble_answer_probe import (
    FAULT_BEHAVIOR_ID,
    PREAMBLE_ID,
    RATINGS_ID,
    TABLE_ID,
    score_answer,
)


FRAGMENTS = [
    "other-1",
    FAULT_BEHAVIOR_ID,
    "other-3",
    "other-4",
    TABLE_ID,
    "other-6",
    "other-7",
    "other-8",
    RATINGS_ID,
    "other-10",
    "other-11",
    PREAMBLE_ID,
]


GOOD_ANSWER = """
Los relés de alarma del canal 1 y del canal 2 tienen contactos NC, C y NA [F5].
Los relés de avería del canal 1 y el AUX del canal 2 tienen contactos NC, C y NA [F5].
El canal 1, el canal 2 o una avería común generan condición de avería [F2].
La salida de sirena 1 usa los bornes 17 y 18; la salida de sirena 2, los bornes 19 y 20 [F5].
Cada salida, sirena 1 y sirena 2, lleva 47 kohm de fin de línea [F5].
CH2 o canal 2 solo está disponible en modelos de dos canales [F12].

La avería también se indica en modo de servicio y ante un corte de alimentación [F2].
El estado de avería no está enclavado [F2].
Los contactos admiten 2,0 A a 30 V CC y 0,5 A a 30 V CA [F9].
"""


def test_s161_score_accepts_complete_source_cited_answer():
    result = score_answer(GOOD_ANSWER, FRAGMENTS)
    assert result["recovered_covered"] == 5
    assert result["protected_covered"] == 4
    assert result["invalid_citations"] == []
    assert result["unsupported_relay_life_claim"] is False


def test_s161_score_rejects_missing_preamble_citation_and_invalid_citation():
    answer = GOOD_ANSWER.replace("[F12]", "[F99]")
    result = score_answer(answer, FRAGMENTS)
    assert result["recovered_covered"] == 0
    assert result["invalid_citations"] == [99]


def test_s161_score_keeps_document_extraction_hold_out_of_credit():
    answer = GOOD_ANSWER + "\nLa vida del relé es 100000 operaciones [F9]."
    result = score_answer(answer, FRAGMENTS)
    assert result["unsupported_relay_life_claim"] is True

