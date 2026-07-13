import json

import pytest

from scripts.s107_shadow_adjudication_join import (
    build_redacted_receipt,
    hmac_sha256_utf8_exact,
    join_shadow_events_in_memory,
)


SECRET = "s107-test-secret-that-is-longer-than-32-characters"
QUERY = "¿Qué tensión admite el lazo?"
CHUNK_ID = "00000000-0000-0000-0000-000000000001"
CONTENT = "Tensión nominal del lazo: 24 Vcc."


def _event(query=QUERY, *, version="v1", event_id="event-1", selected_ids=None):
    return {
        "schema": "structural_neighbor_shadow_event_v1",
        "event_id": event_id,
        "query_hmac_sha256": hmac_sha256_utf8_exact(SECRET, query),
        "sampling_hmac_key_version": version,
        "selected_ids": selected_ids if selected_ids is not None else [CHUNK_ID],
    }


def _chunks():
    return [
        {
            "id": CHUNK_ID,
            "content": CONTENT,
            "source_file": "manual.pdf",
            "page_number": 7,
            "section_title": "Lazo",
            "document_id": "doc-1",
            "extraction_sha256": "a" * 64,
            "language": "es",
        }
    ]


def test_exact_utf8_join_duplicate_query_rows_and_redacted_receipt():
    result = join_shadow_events_in_memory(
        [_event(), _event()],
        query_rows=[
            {"query": QUERY, "created_at": "2026-07-13T00:00:00Z"},
            {"query": QUERY, "created_at": "2026-07-13T00:01:00Z"},
        ],
        chunk_rows=_chunks(),
        hmac_secret=SECRET,
        hmac_key_version="v1",
    )
    assert len(result.cases) == 1
    assert result.cases[0].query == QUERY
    assert result.cases[0].query_occurrences == 2
    assert result.cases[0].anchors[0].content == CONTENT
    assert result.duplicate_event_ids == 1
    assert result.duplicate_query_events == 0
    assert result.duplicate_query_rows == 1
    assert not result.promotion_blocked

    receipt = build_redacted_receipt(
        result,
        [
            {
                "event_id": "event-1",
                "anchors": [
                    {"id": CHUNK_ID, "relevant": True, "critical_reason": None}
                ],
            }
        ],
    )
    encoded = json.dumps(receipt, ensure_ascii=False)
    assert QUERY not in encoded
    assert CONTENT not in encoded
    assert receipt["relevant_anchors"] == 1
    assert receipt["critical_false_positives"] == 0


def test_raw_utf8_equality_is_not_normalized_or_trimmed():
    result = join_shadow_events_in_memory(
        [_event()],
        query_rows=[{"query": QUERY + " ", "created_at": "2026-07-13T00:00:00Z"}],
        chunk_rows=_chunks(),
        hmac_secret=SECRET,
        hmac_key_version="v1",
    )
    assert result.unjoinable_query_events == ("event-1",)
    assert result.promotion_blocked


def test_key_version_and_missing_anchor_fail_closed():
    result = join_shadow_events_in_memory(
        [_event(version="v2"), _event(event_id="event-2", selected_ids=["missing"])],
        query_rows=[{"query": QUERY, "created_at": "2026-07-13T00:00:00Z"}],
        chunk_rows=_chunks(),
        hmac_secret=SECRET,
        hmac_key_version="v1",
    )
    assert result.wrong_key_version_events == ("event-1",)
    assert result.missing_anchor_events == ("event-2",)
    assert result.promotion_blocked


def test_first_event_wins_for_unique_query_denominator():
    result = join_shadow_events_in_memory(
        [_event(event_id="event-1"), _event(event_id="event-2")],
        query_rows=[{"query": QUERY, "created_at": "2026-07-13T00:00:00Z"}],
        chunk_rows=_chunks(),
        hmac_secret=SECRET,
        hmac_key_version="v1",
    )
    assert [case.event_id for case in result.cases] == ["event-1"]
    assert result.duplicate_query_events == 1


def test_query_projection_rejects_identity_or_response_fields():
    with pytest.raises(ValueError, match="unsafe projection"):
        join_shadow_events_in_memory(
            [_event()],
            query_rows=[
                {
                    "query": QUERY,
                    "created_at": "2026-07-13T00:00:00Z",
                    "telegram_user_id": 123,
                }
            ],
            chunk_rows=_chunks(),
            hmac_secret=SECRET,
            hmac_key_version="v1",
        )


def test_receipt_rejects_free_text_and_incomplete_labels():
    result = join_shadow_events_in_memory(
        [_event()],
        query_rows=[{"query": QUERY, "created_at": "2026-07-13T00:00:00Z"}],
        chunk_rows=_chunks(),
        hmac_secret=SECRET,
        hmac_key_version="v1",
    )
    with pytest.raises(ValueError, match="free-text"):
        build_redacted_receipt(
            result,
            [
                {
                    "event_id": "event-1",
                    "anchors": [
                        {
                            "id": CHUNK_ID,
                            "relevant": True,
                            "critical_reason": None,
                            "notes": QUERY,
                        }
                    ],
                }
            ],
        )
    with pytest.raises(ValueError, match="incomplete"):
        build_redacted_receipt(
            result, [{"event_id": "event-1", "anchors": []}]
        )
