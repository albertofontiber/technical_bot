from scripts.s115_reference_edge_nested_replay import build_payload


EXTRACTION = "b" * 64


def _row(row_id, content, *, section="", index=0):
    return {
        "id": row_id,
        "content": content,
        "manufacturer": "Vendor",
        "product_model": "Panel-X",
        "document_id": "doc-1",
        "extraction_sha256": EXTRACTION,
        "section_title": section,
        "chunk_index": index,
    }


def test_nested_replay_is_in_memory_zero_cost_and_receipt_checked():
    source = _row("s", "To diagnose airflow, see section 7.6.1.", index=1)
    target = _row(
        "t",
        "## 7.6.1 Reading airflow\n\nPress OK and check code X11 for airflow measurement.",
        section="7.6.1 Reading airflow",
        index=2,
    )
    nested = {
        "sample": [
            {
                "manufacturer": "Vendor",
                "product_model": "Panel-X",
                "chunk_id": "s",
                "question": "How do I diagnose the airflow?",
                "scope_key": "scope-1",
            }
        ]
    }
    base = {"candidate_scopes": {"scope-1": [source, target]}}

    payload = build_payload(nested, base, frozen_receipts={"sealed": True})

    assert payload["gate"]["questions"] == 1
    assert payload["gate"]["questions_with_selections"] == 1
    assert payload["gate"]["receipt_count"] == 1
    assert payload["gate"]["all_receipts_verified"] is True
    assert payload["gate"]["database_get_requests"] == 0
    assert payload["gate"]["database_writes"] == 0
    assert payload["gate"]["model_calls"] == 0
    assert payload["rows"][0]["selected_ids"] == ["t"]
    assert payload["rows"][0]["selected_receipts"][0]["receipts_verified"] is True


def test_empty_receipt_set_is_not_reported_as_verified():
    source = _row("s", "No explicit section reference is present here.", index=1)
    nested = {
        "sample": [
            {
                "manufacturer": "Vendor",
                "product_model": "Panel-X",
                "chunk_id": "s",
                "question": "How do I diagnose airflow?",
                "scope_key": "scope-1",
            }
        ]
    }
    payload = build_payload(
        nested, {"candidate_scopes": {"scope-1": [source]}}
    )
    assert payload["gate"]["receipt_count"] == 0
    assert payload["gate"]["all_receipts_verified"] == "not_applicable"
    assert payload["gate"]["potential_reference_edges"] == 0
