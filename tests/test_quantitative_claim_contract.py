from src.rag.quantitative_claim_contract import (
    extract_quantitative_fields,
    find_partial_quantitative_claims,
)


def _names(text: str) -> list[str]:
    return [row.canonical for row in extract_quantitative_fields(text)]


def test_extracts_range_step_scope_and_units() -> None:
    assert _names("05 a 295 seg. Variable en intervalos de 5 seg.") == [
        "05seg",
        "295seg",
        "5seg",
    ]
    assert _names("En A11 a C32: ±20 %, 80 %, 120 % y 300 s") == [
        "config:a11",
        "config:c32",
        "±20%",
        "80%",
        "120%",
        "300s",
    ]


def test_ignores_dates_pages_revisions_and_bare_identifiers() -> None:
    assert _names("Page 56, Issue 1, Rev. 008, 2019-12-09, model ASD 535") == []


def test_detects_partial_cited_quantitative_claim() -> None:
    source = (
        "El tiempo de activación puede configurarse de 05 a 295 seg. "
        "y siempre en intervalos de 5 seg."
    )
    answer = "Configura el tiempo entre 05 y 295 seg. [F1]"
    findings = find_partial_quantitative_claims(
        answer, [{"id": "chunk-1", "content": source}]
    )
    assert len(findings) == 1
    assert findings[0].present_fields == ("295seg",)
    assert findings[0].missing_fields == ("05seg", "5seg")


def test_complete_or_unbound_claim_is_not_flagged() -> None:
    source = (
        "El tiempo de activación puede configurarse de 05 a 295 seg. "
        "y siempre en intervalos de 5 seg."
    )
    complete = "El tiempo va de 05 a 295 seg., en intervalos de 5 seg. [F1]"
    assert find_partial_quantitative_claims(
        complete, [{"id": "chunk-1", "content": source}]
    ) == []
    unrelated = "La tensión auxiliar es 24 V. [F1]"
    assert find_partial_quantitative_claims(
        unrelated, [{"id": "chunk-1", "content": source}]
    ) == []
