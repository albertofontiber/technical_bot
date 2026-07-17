import copy

from scripts.s167_build_independent_ledger_source import build_from_rows


def _row(manufacturer: str, stratum: str, number: int, document: str) -> dict:
    prefix = (
        "| Field | Value |\n| --- | --- |\n| mode | safe |\n"
        if stratum == "table"
        else "Technical procedure.\n\n"
    )
    content = prefix + "The technician must configure and shall verify. " + "x" * 900
    return {
        "kind": "chunk",
        "id": f"00000000-0000-4000-8000-{number:012d}",
        "content": content,
        "manufacturer": manufacturer,
        "product_model": f"P-{number}",
        "document_id": document,
        "extraction_sha256": "a" * 64,
        "source_file": "manual",
        "page_number": 1,
        "section_title": "section",
        "section_path": "section",
    }


def _fixtures():
    rows = []
    number = 1
    for manufacturer in [f"M{i:02d}" for i in range(18)]:
        for stratum in ("table", "prose"):
            rows.append(_row(manufacturer, stratum, number, f"doc-{number}"))
            number += 1
    active = {row["document_id"] for row in rows}
    return rows, active


def test_s167_source_selection_is_document_independent_balanced_and_deterministic():
    rows, active = _fixtures()
    first = build_from_rows(rows, active, set(), set(), set())
    second = build_from_rows(copy.deepcopy(rows), set(active), set(), set(), set())
    assert first == second
    assert first["selection"]["items"] == 14
    assert first["selection"]["manufacturers"] == 14
    assert first["selection"]["unique_documents"] == 14
    assert first["selection"]["table"] == 7
    assert first["selection"]["prose"] == 7
    assert first["selection"]["prior_document_overlap"] == 0
    assert first["selection"]["target_document_overlap"] == 0


def test_s167_excludes_whole_prior_target_documents_and_development_pairs():
    rows, active = _fixtures()
    prior = rows[0]
    target = rows[1]
    dev = rows[2]
    result = build_from_rows(
        rows,
        active,
        {prior["document_id"]},
        {target["id"]},
        {(dev["manufacturer"].casefold(), dev["product_model"].casefold())},
    )
    selected_docs = {row["document_id"] for row in result["items"]}
    selected_pairs = {
        (row["manufacturer"].casefold(), row["product_model"].casefold())
        for row in result["items"]
    }
    assert prior["document_id"] not in selected_docs
    assert target["document_id"] not in selected_docs
    assert (dev["manufacturer"].casefold(), dev["product_model"].casefold()) not in selected_pairs
    assert result["selection"]["target_chunk_overlap"] == 0
