from scripts.s190_visual_asset_bridge_audit import reconcile_assets


def test_reconcile_requires_document_page_single_url_and_matching_source():
    legacy = [
        {
            "document_id": "d1",
            "page_number": 4,
            "source_file": "Manual A.pdf",
            "diagram_url": "https://assets/a.png",
        },
        {
            "document_id": "d2",
            "page_number": 7,
            "source_file": "Manual B.pdf",
            "diagram_url": "https://assets/b1.png",
        },
        {
            "document_id": "d2",
            "page_number": 7,
            "source_file": "Manual B.pdf",
            "diagram_url": "https://assets/b2.png",
        },
        {
            "document_id": "d3",
            "page_number": 1,
            "source_file": "Wrong revision.pdf",
            "diagram_url": "https://assets/c.png",
        },
    ]
    active = [
        {"document_id": "d1", "page_number": 4, "source_file": "Manual A.pdf"},
        {"document_id": "d1", "page_number": 4, "source_file": "Manual A.pdf"},
        {"document_id": "d2", "page_number": 7, "source_file": "Manual B.pdf"},
        {"document_id": "d3", "page_number": 1, "source_file": "Manual C.pdf"},
    ]

    result = reconcile_assets(legacy, active)

    assert result["exact_document_page_matches"] == 3
    assert result["single_url_matches"] == 2
    assert result["source_consistent_single_url_matches"] == 1
    assert result["ambiguous_multi_url_matches"] == 1
    assert result["active_rows_rebindable"] == 2
    assert len(result["stable_receipts"]) == 1
    assert "diagram_url" not in result["stable_receipts"][0]
