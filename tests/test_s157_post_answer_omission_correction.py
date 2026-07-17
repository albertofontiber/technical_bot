from scripts.s157_post_answer_omission_correction import (
    author_schema,
    build_revision_prompt,
    runtime_chunks,
    validate_authored,
)


def _source():
    return {
        "item_id": "x", "manufacturer": "M", "product_model": "P", "source_file": "manual",
        "bundle_sha256": "abc", "chunks": [
            {"fragment_number": 1, "chunk_id": "a", "content": "Antes: desconecte la zona."},
            {"fragment_number": 2, "chunk_id": "b", "content": "Después: espere 300 s."},
            {"fragment_number": 3, "chunk_id": "c", "content": "Verifique el LED."},
        ],
    }


def test_authored_item_requires_exact_multifragment_quotes():
    raw = {
        "item_id": "x", "eligible": True, "question": "¿Qué hago?",
        "answer_points": [
            {"claim": "Desconectar", "exact_quote": "desconecte la zona", "fragment_number": 1},
            {"claim": "Esperar", "exact_quote": "espere 300 s", "fragment_number": 2},
        ],
    }
    result = validate_authored(raw, _source())
    assert result["eligible"] and len(result["answer_points"]) == 2
    raw["answer_points"][1]["fragment_number"] = 1
    assert not validate_authored(raw, _source())["eligible"]


def test_runtime_chunks_keep_source_identity():
    rows = runtime_chunks(_source())
    assert [row["id"] for row in rows] == ["a", "b", "c"]
    assert all(row["product_model"] == "P" for row in rows)


def test_revision_prompt_keeps_draft_source_and_omissions_separate():
    prompt = build_revision_prompt("ORIGINAL", "DRAFT", "OMITTED")
    assert prompt.index("ORIGINAL") < prompt.index("DRAFT") < prompt.index("OMITTED")


def test_author_schema_forbids_extra_fields():
    assert author_schema()["additionalProperties"] is False
