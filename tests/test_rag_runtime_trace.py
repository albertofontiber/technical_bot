import json

import httpx

from src import logging_db
from src.release_profiles import DOCUMENT_LOCAL_LANE
from src.rag.runtime_trace import (
    SENSITIVE_RAW_KEYS,
    TRACE_MAX_BYTES,
    build_rag_serving_trace,
    validate_rag_serving_trace,
)
from src.rag.post_rerank_coverage import append_validated_coverage
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _valid_coverage_chunk(monkeypatch):
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    content = (
        "La regla contiene una instrucción de entrada y otra de salida. "
        "Al programar reglas de causa-efecto evite las lógicas contradictorias. "
        "Es de vital importancia probar rigurosamente todas las reglas durante "
        "la puesta en marcha del sistema para verificar que no haya conflictos "
        "lógicos entre ellas."
    )
    quote = "La regla contiene una instrucción de entrada y otra de salida."
    candidate = {
        "id": "coverage-1",
        "content": content,
        "source_file": "manual",
        "retrieval_lane": STRUCTURAL_LANE,
        "structural_neighbor_validated": True,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": "coverage-1",
                "start": 0,
                "end": len(quote),
                "quote": quote,
                "exact_source_span_validated": True,
            }
        ],
    }
    served = append_validated_coverage([], [candidate])
    assert len(served) == 1
    assert served[0].get("mandatory_callout_cards")
    return served[0]


def _minimal_valid_trace():
    return build_rag_serving_trace(
        coverage_trace={
            "enabled": False,
            "status": "disabled_or_not_applicable",
            "protected_prefix_rows": 1,
            "protected_prefix_equal": True,
            "appended_ids": [],
            "lanes": [],
        },
        served_chunks=[{"id": "prefix"}],
        must_preserve_trace=None,
        must_preserve_outcome={"status": "disabled"},
        release_policy={"profile": "off"},
        transport_parts=1,
    )


def test_runtime_trace_is_bounded_allowlisted_and_contains_c1_receipt_counts(monkeypatch):
    secret = "SOURCE-CONTENT-MUST-NEVER-LEAK"
    coverage_chunk = _valid_coverage_chunk(monkeypatch)
    trace = build_rag_serving_trace(
        coverage_trace={
            "enabled": True,
            "status": "appended",
            "protected_prefix_rows": 10,
            "protected_prefix_equal": True,
            "appended_ids": ["coverage-1", "secret-chunk-2"],
            "query": secret,
            "lanes": [
                {
                    "lane": "same_blob_structural_neighbor_coverage_v1",
                    "status": "selected",
                    "selected_ids": ["secret-chunk-2"],
                    "quote": secret,
                }
            ],
        },
        served_chunks=[{"content": secret}, coverage_chunk],
        must_preserve_trace={
            "identity_resolved": True,
            "resolved_ids": ["secret-model"],
            "cited_fragments": [12],
            "atoms_detected": 2,
            "atoms_bound": 2,
            "atoms_missing": 2,
            "atoms_appended": 2,
            "appendix_appended": True,
        },
        must_preserve_outcome={"status": "evaluated"},
        release_policy={
            "profile": "coverage_c1_v1",
            "structural_neighbor_coverage": True,
            "coverage_mandatory_callout": True,
        },
        transport_parts=2,
    )

    encoded = json.dumps(trace, ensure_ascii=False).encode("utf-8")
    assert len(encoded) <= TRACE_MAX_BYTES
    assert secret not in encoded.decode("utf-8")
    assert not (set(_walk_keys(trace)) & SENSITIVE_RAW_KEYS)
    assert trace["coverage"]["appended_rows"] == 2
    assert trace["coverage"]["mandatory_callout_cards"] == 1
    assert trace["must_preserve"]["cited_fragment_count"] == 1
    assert trace["must_preserve"]["atoms_appended"] == 2
    assert trace["coverage"]["configured_lanes"] == [STRUCTURAL_LANE]
    assert trace["coverage"]["executed_lanes"] == [STRUCTURAL_LANE]
    assert trace["transport"] == {"message_parts": 2, "render_status": "html"}
    assert validate_rag_serving_trace(trace) == trace


def test_v2_document_local_trace_counts_rows_without_copying_raw_evidence():
    private = "PRIVATE-DOCUMENT-ID-AND-CONTENT"
    trace = build_rag_serving_trace(
        coverage_trace={
            "enabled": True,
            "status": "appended",
            "protected_prefix_rows": 10,
            "protected_prefix_equal": True,
            "appended_ids": [private],
            "query": private,
            "lanes": [
                {
                    "lane": DOCUMENT_LOCAL_LANE,
                    "status": "selected",
                    "selected_ids": [private],
                    "document_id": private,
                    "source_file": private,
                    "content": private,
                    "quote": private,
                    "query_plan_sha256": private,
                }
            ],
        },
        served_chunks=[],
        must_preserve_trace=None,
        must_preserve_outcome={"status": "disabled"},
        release_policy={
            "profile": "coverage_c1_v2",
            "structural_neighbor_coverage": True,
            "document_local_coverage": True,
            "coverage_mandatory_callout": True,
        },
        transport_parts=1,
    )

    encoded = json.dumps(trace, ensure_ascii=False)
    assert private not in encoded
    assert not (set(_walk_keys(trace)) & SENSITIVE_RAW_KEYS)
    assert trace["release_profile"] == "coverage_c1_v2"
    assert trace["coverage"]["configured_lanes"] == [
        STRUCTURAL_LANE,
        DOCUMENT_LOCAL_LANE,
    ]
    assert trace["coverage"]["executed_lanes"] == [DOCUMENT_LOCAL_LANE]
    assert trace["coverage"]["lane_outcomes"] == [
        {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "selected",
            "selected_rows": 1,
        }
    ]
    assert validate_rag_serving_trace(trace) == trace


def test_document_local_runtime_statuses_are_preserved_by_closed_schema():
    statuses = (
        "selected",
        "no_validated_structural_anchor",
        "source_scope_overflow",
        "no_bounded_query_plan",
        "invalid_anchor_scope",
        "document_seed_not_found",
        "ambiguous_document_family",
        "unsupported_document_language",
        "active_revision_not_bound_to_anchor_blob",
        "document_scope_overflow",
        "invalid_revision_status",
        "ambiguous_active_revision",
        "branched_or_cyclic_revision_chain",
        "nonreciprocal_revision_chain",
        "incomplete_revision_chain",
        "no_authoritative_source_scope",
        "candidate_scope_mismatch",
        "combined_candidate_cap_exceeded",
        "candidate_cap_exceeded",
        "no_fts_candidates",
        "no_candidates",
        "fetched",
        "selector_pool_overflow",
        "no_query_aligned_candidate",
        "best_candidate_already_covered",
        "winner_scope_mismatch",
        "skipped_no_append_capacity",
        "skipped_no_served_structural_anchor",
        "error",
    )
    for status in statuses:
        trace = build_rag_serving_trace(
            coverage_trace={
                "enabled": True,
                "status": "no_append",
                "protected_prefix_rows": 1,
                "protected_prefix_equal": True,
                "appended_ids": [],
                "lanes": [{"lane": DOCUMENT_LOCAL_LANE, "status": status}],
            },
            served_chunks=[],
            must_preserve_trace=None,
            must_preserve_outcome={"status": "disabled"},
            release_policy={
                "profile": "coverage_c1_v2",
                "structural_neighbor_coverage": True,
                "document_local_coverage": True,
            },
            transport_parts=1,
        )
        assert trace["coverage"]["lane_outcomes"][0]["status"] == status
        assert validate_rag_serving_trace(trace) == trace


def test_runtime_trace_rejects_private_tokens_in_every_copied_enum_field():
    private = "PrivateTicketABC123"
    trace = build_rag_serving_trace(
        coverage_trace={
            "enabled": True,
            "status": private,
            "error_type": private,
            "lanes": [
                {"lane": private, "status": private, "error_type": private}
            ],
        },
        served_chunks=[],
        must_preserve_trace={"reason": private},
        must_preserve_outcome={"status": private, "error_type": private},
        release_policy={"profile": private},
        transport_parts=1,
    )

    encoded = json.dumps(trace, ensure_ascii=False)
    assert private not in encoded
    assert trace["release_profile"] == "unknown"
    assert trace["coverage"]["status"] == "unknown"
    assert trace["coverage"]["error_type"] == "OtherError"
    assert trace["coverage"]["lane_outcomes"][0]["lane"] == "unknown_lane"
    assert trace["must_preserve"]["status"] == "not_available"


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _Client:
    def __init__(self, responses, calls):
        self.responses = list(responses)
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, _url, *, headers, json):
        self.calls.append({"headers": headers, "json": json})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _patch_client(monkeypatch, responses, calls):
    monkeypatch.setattr(
        logging_db.httpx,
        "Client",
        lambda **_kwargs: _Client(responses, calls),
    )


def test_query_logger_retries_once_without_trace_for_missing_column(monkeypatch):
    calls = []
    _patch_client(
        monkeypatch,
        [
            _Response(
                400,
                {
                    "code": "PGRST204",
                    "message": "Could not find the 'rag_trace' column in query_logs",
                },
            ),
            _Response(201, {}),
        ],
        calls,
    )

    logging_db.log_query(1, "q", rag_trace=_minimal_valid_trace())

    assert len(calls) == 2
    assert "rag_trace" in calls[0]["json"]
    assert "rag_trace" not in calls[1]["json"]


def test_query_logger_does_not_retry_uncertain_timeout(monkeypatch):
    calls = []
    request = httpx.Request("POST", "https://example.invalid/query_logs")
    _patch_client(
        monkeypatch,
        [httpx.ReadTimeout("uncertain", request=request)],
        calls,
    )

    logging_db.log_query(1, "q", rag_trace=_minimal_valid_trace())

    assert len(calls) == 1


def test_query_logger_rejects_arbitrary_json_at_the_sink(monkeypatch):
    calls = []
    _patch_client(monkeypatch, [_Response(201, {})], calls)

    logging_db.log_query(
        1,
        "q",
        rag_trace={
            "schema": "rag_serving_trace_v1",
            "content": "PRIVATE-CONTENT",
        },
    )

    assert len(calls) == 1
    assert "rag_trace" not in calls[0]["json"]


def test_false_or_stale_callout_metadata_never_counts(monkeypatch):
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    fake = {
        "id": "fake",
        "post_rerank_coverage": True,
        "mandatory_callout_cards": [{"quote": "private"}],
    }
    trace = build_rag_serving_trace(
        coverage_trace={
            "enabled": True,
            "status": "appended",
            "protected_prefix_rows": 1,
            "protected_prefix_equal": True,
            "appended_ids": ["fake"],
            "lanes": [],
        },
        served_chunks=[fake],
        must_preserve_trace=None,
        must_preserve_outcome={"status": "disabled"},
        release_policy={
            "profile": "coverage_c1_v1",
            "structural_neighbor_coverage": True,
            "coverage_mandatory_callout": True,
        },
        transport_parts=1,
    )
    assert trace["coverage"]["mandatory_callout_cards"] == 0


def test_sink_validator_requires_the_exact_allowlisted_shape():
    trace = _minimal_valid_trace()
    for private_key in ("qid", "question", "answer", "expected_fact", "gold"):
        mutated = json.loads(json.dumps(trace))
        mutated[private_key] = "PRIVATE-CANARY"
        assert validate_rag_serving_trace(mutated) is None
    malformed = json.loads(json.dumps(trace))
    malformed["release_profile"] = {"private": "value"}
    assert validate_rag_serving_trace(malformed) is None


def test_lane_statuses_and_selected_parent_ids_remain_truthful():
    trace = build_rag_serving_trace(
        coverage_trace={
            "enabled": True,
            "status": "no_append",
            "protected_prefix_rows": 1,
            "protected_prefix_equal": True,
            "appended_ids": [],
            "lanes": [
                {
                    "lane": "canonical_document_hyq_coverage_v1",
                    "status": "no_query_aligned_candidate",
                    "selected_parent_ids": ["private-parent"],
                }
            ],
        },
        served_chunks=[],
        must_preserve_trace=None,
        must_preserve_outcome={"status": "disabled"},
        release_policy={"profile": "legacy"},
        transport_parts=1,
    )
    outcome = trace["coverage"]["lane_outcomes"][0]
    assert outcome["status"] == "no_query_aligned_candidate"
    assert outcome["selected_rows"] == 1
