from scripts.s116_audit_section_lineage import classify_rows


SHA = "c" * 64


def _row(row_id, content, *, title="2.4 Wiring", index=0):
    return {
        "id": row_id,
        "content": content,
        "manufacturer": "Fresh Vendor",
        "product_model": "Panel-Z",
        "document_id": "doc-1",
        "extraction_sha256": SHA,
        "chunk_index": index,
        "section_title": title,
    }


def test_classifies_self_sibling_missing_and_toc_without_semantics():
    rows = [
        _row("self", "## 2.4 Wiring\n\nExact body evidence.", index=1),
        _row("body", "Continuation body without the repeated heading.", index=2),
        _row("missing", "A body whose extracted heading is absent.", title="3.1 Setup", index=8),
        _row(
            "toc",
            "## 4.2 Options\n4.2 Options .... 10\n4.3 Other .... 11\n4.4 More .... 12",
            title="4.2 Options",
            index=10,
        ),
        _row("toc-body", "Body after contents only.", title="4.2 Options", index=11),
    ]
    classified = {row["id"]: row["classification"] for row in classify_rows(rows)}
    assert classified["self"] == "self_byte_anchor"
    assert classified["body"] == "unique_sibling_anchor"
    assert classified["missing"] == "missing_byte_anchor"
    assert classified["toc"] == "toc_only"
    assert classified["toc-body"] == "toc_only"


def test_different_document_or_section_never_supplies_anchor():
    anchor = _row("anchor", "## 2.4 Wiring\n\nBody", index=1)
    other_document = dict(
        _row("other", "Continuation", index=2), document_id="doc-2"
    )
    other_section = _row("section", "Continuation", title="2.5 Wiring", index=2)
    classified = {
        row["id"]: row["classification"]
        for row in classify_rows([anchor, other_document, other_section])
    }
    assert classified["other"] == "missing_byte_anchor"
    assert classified["section"] == "missing_byte_anchor"
