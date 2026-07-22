from __future__ import annotations

import copy
import inspect
import json
from typing import Any

import httpx
import pytest

from src.rag import document_local_coverage as document_local
from src.rag.document_local_coverage import (
    CANDIDATE_LIMIT,
    DOCUMENT_ROWS_LIMIT,
    LANE,
    MAX_HTTP_REQUESTS,
    TIMEOUT_SECONDS,
    TOTAL_CANDIDATE_LIMIT,
    VALIDATION,
    fetch_document_local_candidates,
    resolve_authoritative_documents,
    select_document_local_coverage,
)
from src.rag.post_rerank_coverage import (
    DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR,
    append_validated_coverage,
    apply_post_rerank_coverage_with_trace,
    coverage_context_content,
    has_exact_served_coverage_receipt,
    is_validated_coverage_chunk,
)
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


OLD_SHA = "a" * 64
ACTIVE_SHA = "b" * 64
OLD_DOCUMENT = "doc-v04"
ACTIVE_DOCUMENT = "doc-v07"
LINEAGE_ID = "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
SECOND_LINEAGE_ID = "2c9cb13a-0f66-55e4-85cd-1bfa125381b4"
SOURCE_FILE = "manual-control-revisiones"
QUESTION = (
    "Tras descargar la extincion el panel no vuelve al estado normal despues "
    "de rearmar, que condicion y temporizador debo comprobar?"
)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _document_rows() -> list[dict[str, Any]]:
    common = {
        "revision_lineage_id": LINEAGE_ID,
        "document_family": "manual control extincion",
        "language": "es",
        "doc_type": "usuario",
        "manufacturer": "Fabricante Control",
        "product_model": "Panel-X",
    }
    return [
        {
            **common,
            "id": OLD_DOCUMENT,
            "revision": "v.04",
            "revision_date": "2013-11-01",
            "source_pdf_filename": SOURCE_FILE,
            "source_pdf_sha256": OLD_SHA,
            "status": "superseded",
            "supersedes_id": None,
            "superseded_by_id": ACTIVE_DOCUMENT,
        },
        {
            **common,
            "id": ACTIVE_DOCUMENT,
            "revision": "v.07",
            "revision_date": "2018-05-01",
            "source_pdf_filename": SOURCE_FILE,
            "source_pdf_sha256": ACTIVE_SHA,
            "status": "active",
            "supersedes_id": OLD_DOCUMENT,
            "superseded_by_id": None,
        },
    ]


def _scope(*, extraction_sha256: str = ACTIVE_SHA) -> dict[str, str]:
    return {
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": extraction_sha256,
        "source_file": SOURCE_FILE,
        "manufacturer": "Fabricante Control",
        "product_model": "Panel-X",
    }


def _authority() -> dict[str, str]:
    return {
        "document_id": ACTIVE_DOCUMENT,
        "revision_lineage_id": LINEAGE_ID,
        "extraction_sha256": ACTIVE_SHA,
        "source_file": SOURCE_FILE,
        "language": "es",
        "revision": "v.07",
    }


def _snapshot_payload(
    *,
    document_rows: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    rejections: list[dict[str, Any]] | None = None,
    overflow: bool = False,
    authority: bool = True,
) -> dict[str, Any]:
    family = [
        {**copy.deepcopy(row), "scope_rank": 1}
        for row in (document_rows if document_rows is not None else _document_rows())
    ]
    raw_candidates = []
    for rank, row in enumerate(candidates or [], 1):
        raw_candidates.append(
            {
                **copy.deepcopy(row),
                "authority_scope_rank": 1,
                "snapshot_candidate_rank": rank,
            }
        )
    authorities = []
    if authority:
        authorities.append(
            {
                "scope_rank": 1,
                **_authority(),
                "family_rows": len(family),
            }
        )
    return {
        "schema": document_local.SNAPSHOT_SCHEMA,
        "input_status": "ok",
        "authorities": authorities,
        "document_rows": family,
        "candidates": raw_candidates,
        "rejections": copy.deepcopy(rejections or []),
        "family_rows_read": len(family),
        "candidate_rows": len(raw_candidates),
        "candidate_overflow_scopes": [1] if overflow else [],
    }


def _anchor(row_id: str = "anchor") -> dict[str, Any]:
    content = "Rearme y temporizador de extincion del Panel-X."
    return {
        "id": row_id,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
        "chunk_index": 76,
        "content": content,
        "source_file": SOURCE_FILE,
        "manufacturer": "Fabricante Control",
        "product_model": "Panel-X",
        "language": "es",
        "duplicate_of": None,
        "retrieval_lane": STRUCTURAL_LANE,
        "structural_neighbor_validated": True,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "candidate_rank": 1,
                "start": 0,
                "end": len(content),
                "quote": content,
                "facet": "timing_state",
                "exact_source_span_validated": True,
            }
        ],
    }


def _source_contract_anchor(
    row_id: str = "source-contract-anchor",
) -> dict[str, Any]:
    row = _anchor(row_id)
    row.pop("retrieval_lane")
    row.pop("structural_neighbor_validated")
    row["document_local_anchor_route"] = DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
    return row


def _logical_candidate(
    row_id: str = "document-local-target",
    *,
    duplicate_of: str | None = None,
) -> dict[str, Any]:
    content = (
        "| Parametro | Significado |\n"
        "| --- | --- |\n"
        "| r.I | Rearme inhibido tras extincion: -- hasta finalizar la "
        "extincion o agotar t.A; 00 permite rearmar en cualquier momento "
        "(por defecto); de 01 a 30 inhibe durante ese intervalo en minutos. |\n"
        "\nCola no relacionada que no debe entrar en la vista servida."
    )
    row_start = content.index("| r.I")
    clipped_end = content.index("hasta") + len("hasta")
    return {
        "id": row_id,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
        "chunk_index": 82,
        "content": content,
        "context": "",
        "section_title": "Opciones de rearme",
        "document_family": "manual control extincion",
        "product_model": "Panel-X",
        "language": "es",
        "source_file": SOURCE_FILE,
        "page_number": 63,
        "duplicate_of": duplicate_of,
        "manufacturer": "Fabricante Control",
        "doc_type": "usuario",
        "document_status": "active",
        "document_revision": "v.07",
        "document_revision_lineage_id": LINEAGE_ID,
        "document_local_candidate_rank": 0,
        "document_local_authority_document_id": ACTIVE_DOCUMENT,
        "document_local_authority_extraction_sha256": ACTIVE_SHA,
        "document_local_authority_source_file": SOURCE_FILE,
        "document_local_authority_revision_lineage_id": LINEAGE_ID,
        "document_local_authority_document_family": "manual control extincion",
        "document_local_authority_language": "es",
        "document_local_authority_doc_type": "usuario",
        "document_local_authority_manufacturer": "Fabricante Control",
        "document_local_authority_product_model": "Panel-X",
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "candidate_rank": 1,
                "start": row_start,
                "end": clipped_end,
                "quote": content[row_start:clipped_end],
                "facet": "timing_state",
                "exact_source_span_validated": True,
            }
        ],
        "coverage_card_facets": ["timing_state"],
        "local_semantic_validated": True,
    }


def _stamped_document_local(
    content: str,
    start: int,
    end: int,
    *,
    row_id: str = "document-local-record",
) -> dict[str, Any]:
    row = _logical_candidate(row_id)
    row.update(
        {
            "content": content,
            "coverage_cards": [
                {
                    "candidate_id": row_id,
                    "candidate_rank": 1,
                    "start": start,
                    "end": end,
                    "quote": content[start:end],
                    "facet": "timing_state",
                    "exact_source_span_validated": True,
                }
            ],
            "retrieval_lane": LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": VALIDATION,
            "document_local_coverage_rank": 1,
        }
    )
    return row


class _Response:
    def __init__(self, payload: Any):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return copy.deepcopy(self._payload)


class _GetOnlyClient:
    """Deliberately exposes no POST/PATCH/PUT/DELETE methods."""

    def __init__(self, payloads: list[Any]):
        self.payloads = list(payloads)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> _Response:
        self.calls.append((url, copy.deepcopy(kwargs)))
        if not self.payloads:
            raise AssertionError("unexpected extra GET")
        return _Response(self.payloads.pop(0))


def _configure_live_read_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        document_local, "SUPABASE_URL", "https://project-ref.supabase.co"
    )
    monkeypatch.setattr(document_local, "SUPABASE_SERVICE_KEY", "test-only-key")


# ---------------------------------------------------------------------------
# Lifecycle authority: status and reciprocal pointers, never latest-wins.
# ---------------------------------------------------------------------------


def test_resolver_accepts_reciprocal_v07_over_v04_lifecycle() -> None:
    authorities, reason = resolve_authoritative_documents(
        _document_rows(), [_scope()]
    )

    assert reason == "ok"
    assert authorities == [_authority()]


def test_resolver_rejects_two_active_revisions() -> None:
    rows = _document_rows()
    rows[0]["status"] = "active"

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert authorities == []
    assert reason == "ambiguous_active_revision"


def test_resolver_rejects_nonreciprocal_revision_pointer() -> None:
    rows = _document_rows()
    rows[0]["superseded_by_id"] = None

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert authorities == []
    assert reason == "nonreciprocal_revision_chain"


def test_resolver_rejects_anchor_extraction_sha_mismatch() -> None:
    authorities, reason = resolve_authoritative_documents(
        _document_rows(), [_scope(extraction_sha256="c" * 64)]
    )

    assert authorities == []
    assert reason == "active_revision_not_bound_to_anchor_blob"


def test_resolver_rejects_disconnected_second_active_in_same_lineage() -> None:
    rows = _document_rows()
    rows.append(
        {
            **copy.deepcopy(rows[-1]),
            "id": "disconnected-active",
            "revision": "v.08",
            "source_pdf_sha256": "c" * 64,
            "supersedes_id": None,
        }
    )

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert authorities == []
    assert reason == "incomplete_revision_chain"


def test_resolver_accepts_complete_three_revision_chain() -> None:
    rows = _document_rows()
    middle = {
        **copy.deepcopy(rows[0]),
        "id": "doc-v06",
        "revision": "v.06",
        "source_pdf_sha256": "c" * 64,
        "supersedes_id": OLD_DOCUMENT,
        "superseded_by_id": ACTIVE_DOCUMENT,
    }
    rows[0]["superseded_by_id"] = middle["id"]
    rows[1]["supersedes_id"] = middle["id"]
    rows.insert(1, middle)

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert reason == "ok"
    assert authorities == [_authority()]


# ---------------------------------------------------------------------------
# GET-only fetch and global safety bounds.
# ---------------------------------------------------------------------------


def test_fetcher_uses_only_get_and_exact_authority_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    source_row = _logical_candidate()
    client = _GetOnlyClient([_snapshot_payload(candidates=[source_row])])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert [row["id"] for row in candidates] == [source_row["id"]]
    assert authorities == [_authority()]
    assert trace["status"] == "fetched"
    assert trace["http_requests"] == len(client.calls) == 1
    assert trace["model_calls"] == trace["database_writes"] == 0
    assert not any(
        hasattr(client, method) for method in ("post", "patch", "put", "delete")
    )

    snapshot_url, snapshot_call = client.calls[0]
    # s278 flip a v3 (DEC-150): el fetcher de runtime llama al RPC canónico v3;
    # los seals históricos del P1 siguen pineando el SQL v2 (vivo en DB).
    assert snapshot_url == (
        "https://project-ref.supabase.co/rest/v1/rpc/document_local_snapshot_v3"
    )
    assert set(snapshot_call) == {"headers", "params", "timeout"}
    params = snapshot_call["params"]
    assert json.loads(params["anchor_scopes"]) == [
        {
            "document_id": ACTIVE_DOCUMENT,
            "extraction_sha256": ACTIVE_SHA,
            "source_file": SOURCE_FILE,
        }
    ]
    assert params["fts_query"]
    assert params["family_limit"] == str(DOCUMENT_ROWS_LIMIT)
    assert params["candidate_limit"] == str(CANDIDATE_LIMIT)
    assert source_row["id"] not in json.dumps(params, sort_keys=True)


def test_fetcher_accepts_exact_blob_seed_from_governed_source_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    source_row = _logical_candidate()
    source_contract_anchor = _source_contract_anchor()
    client = _GetOnlyClient([_snapshot_payload(candidates=[source_row])])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION,
        [source_contract_anchor],
        client=client,
    )

    assert [row["id"] for row in candidates] == [source_row["id"]]
    assert authorities == [_authority()]
    assert trace["status"] == "fetched"
    assert trace["seed_scope_count"] == 1
    assert trace["seed_sources"] == {DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR: 1}
    assert trace["seed_scopes_truncated"] is False
    assert trace["http_requests"] == len(client.calls) == 1
    assert json.loads(client.calls[0][1]["params"]["anchor_scopes"]) == [
        {
            "document_id": ACTIVE_DOCUMENT,
            "extraction_sha256": ACTIVE_SHA,
            "source_file": SOURCE_FILE,
        }
    ]


@pytest.mark.parametrize(
    "reason",
    [
        "unverified_document_lineage",
        "active_revision_not_bound_to_anchor_blob",
        "ambiguous_active_revision",
    ],
)
def test_governed_source_contract_seed_fails_closed_on_rpc_authority_rejection(
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
) -> None:
    _configure_live_read_globals(monkeypatch)
    payload = _snapshot_payload(
        document_rows=[],
        authority=False,
        rejections=[{"scope_rank": 1, "reason": reason}],
    )
    client = _GetOnlyClient([payload])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION,
        [_source_contract_anchor()],
        client=client,
    )

    assert candidates == authorities == []
    assert trace["status"] == reason
    assert trace["authority_rejections"] == [reason]
    assert trace["seed_sources"] == {DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR: 1}
    assert trace["http_requests"] == len(client.calls) == 1


def test_fetcher_enforces_one_global_http_request_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    client = _GetOnlyClient([])

    with pytest.raises(RuntimeError, match="unsafe document-local read budget"):
        fetch_document_local_candidates(
            QUESTION,
            [_anchor()],
            client=client,
            max_http_requests=2,
        )

    assert len(client.calls) == 0
    assert MAX_HTTP_REQUESTS == 1


def test_fetcher_fails_closed_on_document_scope_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    rows = [
        {**copy.deepcopy(_document_rows()[0]), "id": f"doc-{index}"}
        for index in range(DOCUMENT_ROWS_LIMIT + 1)
    ]
    client = _GetOnlyClient(
        [
            _snapshot_payload(
                document_rows=rows,
                authority=False,
                rejections=[
                    {"scope_rank": 1, "reason": "document_scope_overflow"}
                ],
            )
        ]
    )

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert candidates == authorities == []
    assert trace["status"] == "document_scope_overflow"
    assert trace["overflow"] is True
    assert len(client.calls) == 1


def test_fetcher_fails_closed_on_candidate_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    rows = [
        _logical_candidate(f"candidate-{index}")
        for index in range(CANDIDATE_LIMIT + 1)
    ]
    client = _GetOnlyClient(
        [_snapshot_payload(candidates=rows, overflow=True)]
    )

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert candidates == authorities == []
    assert trace["status"] == "candidate_cap_exceeded"
    assert trace["overflow"] is True
    assert trace["fts_candidate_rows"] == CANDIDATE_LIMIT + 1
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("document_id", "other-document"),
        ("document_revision_lineage_id", SECOND_LINEAGE_ID),
        ("extraction_sha256", "d" * 64),
        ("source_file", "other-source"),
        ("duplicate_of", "canonical-id"),
    ],
)
def test_fetcher_revalidates_every_candidate_scope_field(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    bad_value: str,
) -> None:
    _configure_live_read_globals(monkeypatch)
    row = _logical_candidate()
    row[field] = bad_value
    client = _GetOnlyClient([_snapshot_payload(candidates=[row])])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert candidates == authorities == []
    assert trace["status"] == "candidate_scope_mismatch"


@pytest.mark.parametrize("legacy_language", [None, "en"])
def test_fetcher_uses_authoritative_document_identity_for_legacy_chunk_labels(
    monkeypatch: pytest.MonkeyPatch,
    legacy_language: str | None,
) -> None:
    _configure_live_read_globals(monkeypatch)
    row = _logical_candidate()
    row["language"] = legacy_language
    row["doc_type"] = None
    row["manufacturer"] = "Legacy Manufacturer Label"
    row["product_model"] = "Panel-X-Legacy"
    client = _GetOnlyClient([_snapshot_payload(candidates=[row])])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert authorities == [_authority()]
    assert [candidate["id"] for candidate in candidates] == [row["id"]]
    assert {
        field: candidates[0][field]
        for field in document_local._IDENTITY_FIELDS
    } == {
        "document_family": "manual control extincion",
        "language": "es",
        "doc_type": "usuario",
        "manufacturer": "Fabricante Control",
        "product_model": "Panel-X",
    }
    assert all(
        candidates[0][field]
        == candidates[0][f"document_local_authority_{field}"]
        for field in document_local._IDENTITY_FIELDS
    )
    assert trace["status"] == "fetched"


def test_fetcher_enforces_deadline_before_atomic_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    moments = iter((0.0, TIMEOUT_SECONDS + 0.01))
    monkeypatch.setattr(document_local.time, "monotonic", lambda: next(moments))
    client = _GetOnlyClient([])

    with pytest.raises(TimeoutError, match="deadline exceeded"):
        fetch_document_local_candidates(
            QUESTION, [_anchor()], client=client, timeout_seconds=TIMEOUT_SECONDS
        )

    assert len(client.calls) == 0


def test_fetcher_does_not_retry_transport_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)

    class TimeoutClient:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, *_args: Any, **_kwargs: Any) -> Any:
            self.calls += 1
            raise httpx.ReadTimeout("bounded read timed out")

    client = TimeoutClient()
    with pytest.raises(httpx.ReadTimeout, match="bounded read timed out"):
        fetch_document_local_candidates(QUESTION, [_anchor()], client=client)

    assert client.calls == 1


@pytest.mark.parametrize("es_first", [True, False])
def test_fetcher_rejects_english_scope_without_suppressing_spanish(
    monkeypatch: pytest.MonkeyPatch,
    es_first: bool,
) -> None:
    _configure_live_read_globals(monkeypatch)
    english_sha = "d" * 64
    english_document = "doc-en"
    english_file = "manual-en"
    english_anchor = {
        **_anchor("anchor-en"),
        "document_id": english_document,
        "extraction_sha256": english_sha,
        "source_file": english_file,
        "language": "en",
    }
    anchors = [_anchor(), english_anchor] if es_first else [english_anchor, _anchor()]
    es_rank, en_rank = ((1, 2) if es_first else (2, 1))
    document_rows = [
        {**copy.deepcopy(row), "scope_rank": es_rank} for row in _document_rows()
    ]
    document_rows.append(
        {
            **copy.deepcopy(_document_rows()[-1]),
            "scope_rank": en_rank,
            "id": english_document,
            "document_family": "english family",
            "language": "en",
            "source_pdf_filename": english_file,
            "source_pdf_sha256": english_sha,
            "supersedes_id": None,
        }
    )
    candidate = {
        **_logical_candidate(),
        "authority_scope_rank": es_rank,
        "snapshot_candidate_rank": 1,
    }
    payload = {
        "schema": document_local.SNAPSHOT_SCHEMA,
        "input_status": "ok",
        "authorities": [
            {
                "scope_rank": es_rank,
                **_authority(),
                "family_rows": 2,
            }
        ],
        "document_rows": document_rows,
        "candidates": [candidate],
        "rejections": [
            {"scope_rank": en_rank, "reason": "unsupported_document_language"}
        ],
        "family_rows_read": len(document_rows),
        "candidate_rows": 1,
        "candidate_overflow_scopes": [],
    }
    client = _GetOnlyClient([payload])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, anchors, client=client
    )

    assert [row["id"] for row in candidates] == ["document-local-target"]
    assert authorities == [_authority()]
    assert trace["status"] == "fetched"
    assert trace["authority_rejections"] == ["unsupported_document_language"]
    assert len(client.calls) == 1


def test_fetcher_english_only_scope_fails_closed_before_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    anchor = {
        **_anchor(),
        "language": "en",
    }
    english_row = {
        **copy.deepcopy(_document_rows()[-1]),
        "scope_rank": 1,
        "language": "en",
    }
    payload = {
        "schema": document_local.SNAPSHOT_SCHEMA,
        "input_status": "ok",
        "authorities": [],
        "document_rows": [english_row],
        "candidates": [],
        "rejections": [
            {"scope_rank": 1, "reason": "unsupported_document_language"}
        ],
        "family_rows_read": 1,
        "candidate_rows": 0,
        "candidate_overflow_scopes": [],
    }
    client = _GetOnlyClient([payload])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [anchor], client=client
    )

    assert candidates == authorities == []
    assert trace["status"] == "unsupported_document_language"
    assert trace["fts_queries"] == 0
    assert len(client.calls) == 1


def test_fetcher_rejects_tampered_snapshot_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    payload = _snapshot_payload()
    payload["schema"] = "document_local_snapshot_v1"
    client = _GetOnlyClient([payload])

    with pytest.raises(RuntimeError, match="snapshot contract mismatch"):
        fetch_document_local_candidates(QUESTION, [_anchor()], client=client)


def test_fetcher_python_revalidation_rejects_false_rpc_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_live_read_globals(monkeypatch)
    rows = _document_rows()
    rows.append(
        {
            **copy.deepcopy(rows[-1]),
            "id": "disconnected-active",
            "source_pdf_sha256": "e" * 64,
            "supersedes_id": None,
        }
    )
    client = _GetOnlyClient([_snapshot_payload(document_rows=rows)])

    with pytest.raises(RuntimeError, match="lifecycle receipt mismatch"):
        fetch_document_local_candidates(QUESTION, [_anchor()], client=client)


@pytest.mark.parametrize(
    (
        "first_count",
        "second_count",
        "overflow_scopes",
        "expected_count",
        "expected_status",
    ),
    [
        (32, 32, [], TOTAL_CANDIDATE_LIMIT, "fetched"),
        (40, 40, [], 0, "combined_candidate_cap_exceeded"),
        (CANDIDATE_LIMIT + 1, 1, [1], 1, "fetched"),
    ],
)
def test_fetcher_keeps_valid_scopes_independent_under_candidate_volume(
    monkeypatch: pytest.MonkeyPatch,
    first_count: int,
    second_count: int,
    overflow_scopes: list[int],
    expected_count: int,
    expected_status: str,
) -> None:
    _configure_live_read_globals(monkeypatch)
    second_document = "doc-second"
    second_sha = "e" * 64
    second_file = "manual-second"
    second_anchor = {
        **_anchor("anchor-second"),
        "document_id": second_document,
        "extraction_sha256": second_sha,
        "source_file": second_file,
        "product_model": "Panel-Y",
    }
    second_document_row = {
        **copy.deepcopy(_document_rows()[-1]),
        "scope_rank": 2,
        "id": second_document,
        "revision_lineage_id": SECOND_LINEAGE_ID,
        "document_family": "manual second",
        "product_model": "Panel-Y",
        "source_pdf_filename": second_file,
        "source_pdf_sha256": second_sha,
        "supersedes_id": None,
    }
    raw_candidates: list[dict[str, Any]] = []
    for scope_rank, count in ((1, first_count), (2, second_count)):
        for candidate_rank in range(1, count + 1):
            row = _logical_candidate(f"candidate-{scope_rank}-{candidate_rank}")
            if scope_rank == 2:
                row.update(
                    {
                        "document_id": second_document,
                        "document_revision_lineage_id": SECOND_LINEAGE_ID,
                        "document_local_authority_revision_lineage_id": (
                            SECOND_LINEAGE_ID
                        ),
                        "extraction_sha256": second_sha,
                        "source_file": second_file,
                        "product_model": "Panel-Y",
                    }
                )
            row.update(
                {
                    "authority_scope_rank": scope_rank,
                    "snapshot_candidate_rank": candidate_rank,
                }
            )
            raw_candidates.append(row)
    document_rows = [
        {**copy.deepcopy(row), "scope_rank": 1} for row in _document_rows()
    ] + [second_document_row]
    payload = {
        "schema": document_local.SNAPSHOT_SCHEMA,
        "input_status": "ok",
        "authorities": [
            {"scope_rank": 1, **_authority(), "family_rows": 2},
            {
                "scope_rank": 2,
                "document_id": second_document,
                "revision_lineage_id": SECOND_LINEAGE_ID,
                "extraction_sha256": second_sha,
                "source_file": second_file,
                "language": "es",
                "revision": "v.07",
                "family_rows": 1,
            },
        ],
        "document_rows": document_rows,
        "candidates": raw_candidates,
        "rejections": [],
        "family_rows_read": len(document_rows),
        "candidate_rows": len(raw_candidates),
        "candidate_overflow_scopes": overflow_scopes,
    }
    client = _GetOnlyClient([payload])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor(), second_anchor], client=client
    )

    assert len(candidates) == expected_count
    assert trace["status"] == expected_status
    if expected_status == "combined_candidate_cap_exceeded":
        assert authorities == []
        assert trace["overflow"] is True
    elif overflow_scopes:
        assert {row["document_id"] for row in candidates} == {second_document}
        assert [row["document_id"] for row in authorities] == [second_document]
        assert trace["candidate_overflow_scopes"] == [1]
    else:
        assert len(authorities) == 2


# ---------------------------------------------------------------------------
# Selector admission, cap-one, dedupe, receipts and generic implementation.
# ---------------------------------------------------------------------------


def test_selector_returns_only_first_ranked_complement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _logical_candidate("first")
    second = _logical_candidate("second")
    monkeypatch.setattr(
        document_local,
        "select_rerank_pool_coverage",
        lambda _query, _candidates, _context, **_kwargs: (
            [copy.deepcopy(first), copy.deepcopy(second)],
            {"eligible_rows": 2, "catalog_scope_applied": False},
        ),
    )

    selected, trace = select_document_local_coverage(
        QUESTION, [first, second], [], [_authority()]
    )

    assert [row["id"] for row in selected] == ["first"]
    assert selected[0]["retrieval_lane"] == LANE
    assert selected[0]["document_local_coverage_validated"] is True
    assert selected[0]["document_local_coverage_validation"] == VALIDATION
    assert selected[0]["document_local_coverage_rank"] == 1
    assert trace["eligible_rows"] == 2
    assert trace["status"] == "selected"
    assert trace["selected_ids"] == ["first"]
    assert trace["satisfied_ids"] == ["first"]
    assert trace["satisfaction_route"] == "coverage_append"
    assert trace["catalog_scope_applied"] is False


def test_selector_rejects_combined_two_scope_pool_before_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_authority = {
        **_authority(),
        "document_id": "doc-second",
        "extraction_sha256": "c" * 64,
        "source_file": "manual-second",
    }
    candidates = []
    for index in range(TOTAL_CANDIDATE_LIMIT + 1):
        row = _logical_candidate(f"combined-{index}")
        if index % 2:
            row.update(
                {
                    "document_id": second_authority["document_id"],
                    "extraction_sha256": second_authority["extraction_sha256"],
                    "source_file": second_authority["source_file"],
                    "document_local_authority_document_id": second_authority[
                        "document_id"
                    ],
                    "document_local_authority_extraction_sha256": second_authority[
                        "extraction_sha256"
                    ],
                    "document_local_authority_source_file": second_authority[
                        "source_file"
                    ],
                }
            )
        candidates.append(row)

    monkeypatch.setattr(
        document_local,
        "select_rerank_pool_coverage",
        lambda *_args, **_kwargs: pytest.fail("overflow must stop before ranking"),
    )
    selected, trace = select_document_local_coverage(
        QUESTION, candidates, [], [_authority(), second_authority]
    )

    assert selected == []
    assert trace["status"] == "combined_candidate_cap_exceeded"
    assert trace["overflow"] is True


def test_selector_does_not_replace_an_already_covered_best_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winner = _logical_candidate("winner")
    weaker = _logical_candidate("weaker")
    monkeypatch.setattr(
        document_local,
        "select_rerank_pool_coverage",
        lambda _query, _candidates, _context, **_kwargs: (
            [copy.deepcopy(winner), copy.deepcopy(weaker)],
            {"eligible_rows": 2, "catalog_scope_applied": False},
        ),
    )

    selected, trace = select_document_local_coverage(
        QUESTION,
        [winner, weaker],
        [{"id": "winner"}],
        [_authority()],
    )

    assert selected == []
    assert trace["status"] == "best_candidate_already_covered"
    assert trace["selected_ids"] == []
    assert trace["satisfied_ids"] == ["winner"]
    assert trace["satisfaction_route"] == "already_served"


def test_selector_rejects_duplicate_mark_before_semantic_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = _logical_candidate(duplicate_of="canonical-id")

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("duplicate row reached semantic ranking")

    monkeypatch.setattr(document_local, "select_rerank_pool_coverage", forbidden)

    selected, trace = select_document_local_coverage(
        QUESTION, [duplicate], [], [_authority()]
    )

    assert selected == []
    assert trace["status"] == "candidate_scope_mismatch"


def test_append_rejects_tampered_document_local_exact_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _logical_candidate()
    tampered = copy.deepcopy(candidate)
    tampered["coverage_cards"][0]["quote"] += " inventado"
    monkeypatch.setattr(
        document_local,
        "select_rerank_pool_coverage",
        lambda _query, _candidates, _context, **_kwargs: (
            [copy.deepcopy(tampered)],
            {"eligible_rows": 1, "catalog_scope_applied": False},
        ),
    )
    selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )
    prefix = [{"id": "prefix", "content": "prefijo"}]

    output = append_validated_coverage(prefix, selected)

    assert trace["status"] == "selected"
    assert output is prefix


def test_append_rejects_tampered_normalized_document_identity() -> None:
    candidate = _logical_candidate()
    candidate.update(
        {
            "retrieval_lane": LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": VALIDATION,
            "document_local_coverage_rank": 1,
        }
    )
    candidate["product_model"] = "Panel-X-Legacy"
    prefix = [{"id": "prefix", "content": "prefijo"}]

    output = append_validated_coverage(prefix, [candidate])

    assert output is prefix


def test_document_local_lane_is_generic_and_has_no_model_or_write_dependency() -> None:
    source = inspect.getsource(document_local).casefold()
    for forbidden in (
        "hp011",
        "475a8f18-7c69-4c7a-8111-45bd67334c96",
        "hlsi-mn-103",
        "p63",
        "anthropic",
        "openai",
        ".post(",
        ".patch(",
        ".put(",
        ".delete(",
    ):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# Production append seam and exact logical-record serving.
# ---------------------------------------------------------------------------


def test_apply_serves_one_complete_exact_logical_record_and_protects_prefix() -> None:
    prefix = [{"id": "prefix", "content": "prefijo byte-identico", "score": 0.9}]
    prefix_before = copy.deepcopy(prefix)
    prefix_bytes = _json_bytes(prefix)
    anchor = _anchor()
    target = _logical_candidate()
    observed: dict[str, Any] = {}

    def structural_collector(_query: str, _prefix: list[dict]) -> tuple[list[dict], dict]:
        return [copy.deepcopy(anchor)], {
            "lane": STRUCTURAL_LANE,
            "status": "selected",
            "selected_ids": [anchor["id"]],
        }

    def document_local_collector(
        _query: str,
        anchors: list[dict],
        covered_context: list[dict],
    ) -> tuple[list[dict], dict]:
        observed["anchors"] = [row["id"] for row in anchors]
        observed["covered"] = [row["id"] for row in covered_context]
        selected = copy.deepcopy(target)
        selected.update(
            {
                "retrieval_lane": LANE,
                "document_local_coverage_validated": True,
                "document_local_coverage_validation": VALIDATION,
                "document_local_coverage_rank": 1,
            }
        )
        return [selected], {
            "lane": LANE,
            "status": "selected",
            "selected_ids": [selected["id"]],
            "model_calls": 0,
            "database_writes": 0,
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        QUESTION,
        prefix,
        enabled=True,
        structural_enabled=True,
        document_local_enabled=True,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
        structural_collector=structural_collector,
        document_local_collector=document_local_collector,
    )

    assert prefix == prefix_before
    assert _json_bytes(prefix) == prefix_bytes
    assert _json_bytes(output[: len(prefix)]) == prefix_bytes
    assert [row["id"] for row in output] == ["prefix", "anchor", target["id"]]
    assert observed == {
        "anchors": ["anchor"],
        "covered": ["prefix", "anchor"],
    }
    assert trace["protected_prefix_equal"] is True
    assert trace["model_calls"] == trace["database_writes"] == 0

    served = output[-1]
    assert is_validated_coverage_chunk(served) is True
    assert has_exact_served_coverage_receipt(served) is True
    view = coverage_context_content(served)
    assert "Rearme inhibido tras extincion" in view
    assert "t.A" in view
    assert "00 permite rearmar en cualquier momento" in view
    assert "de 01 a 30" in view
    assert "Cola no relacionada" not in view
    assert len(view) <= 1800


def test_document_local_record_can_start_in_separator_but_serves_only_data_row() -> None:
    content = (
        "| Parametro | Significado |\n"
        "| --- | --- |\n"
        "| r.I | t.A; 00 libre; 01 a 30 minutos. |\n"
        "\nCola no relacionada."
    )
    start = content.index("| ---")
    end = content.index("00 libre") + len("00 libre")
    candidate = _stamped_document_local(content, start, end)

    output = append_validated_coverage([], [candidate])

    assert len(output) == 1
    served = output[0]
    assert coverage_context_content(served) == (
        "| r.I | t.A; 00 libre; 01 a 30 minutos. |"
    )
    card = served["served_coverage_cards"][0]
    assert card["record_kind"] == "markdown_pipe_row_v1"
    assert card["complete_record_validated"] is True
    assert has_exact_served_coverage_receipt(served) is True
    assert coverage_context_content(served, logical_record_expansion=False) == content[
        start:end
    ]


@pytest.mark.parametrize(
    "content,start_token,end_token",
    [
        (
            "Parrafo de prosa cuyo final relevante sigue mas alla del recorte.",
            "Parrafo",
            "relevante",
        ),
        (
            "| Parametro | Valor |\n| --- | --- |\n",
            "| ---",
            "--- |",
        ),
        (
            "<tr><td>r.I</td><td>00 libre y 01 a 30</td></tr>",
            "<tr>",
            "00 libre",
        ),
        (
            "| A | uno |\n| B | dos |\n",
            "| A",
            "dos |",
        ),
        (
            "| Campo | valor aislado |",
            "| Campo",
            "aislado |",
        ),
        (
            "Texto normal\n| --- | --- |\n| Dato | valor |",
            "| Dato",
            "valor |",
        ),
        (
            "| A | B | C |\n| --- | --- |\n| uno | dos |",
            "| uno",
            "dos |",
        ),
    ],
)
def test_document_local_record_fails_closed_without_one_provable_pipe_row(
    content: str,
    start_token: str,
    end_token: str,
) -> None:
    start = content.index(start_token)
    end = content.index(end_token) + len(end_token)
    candidate = _stamped_document_local(content, start, end)
    prefix = [{"id": "prefix", "content": "estable"}]

    output = append_validated_coverage(prefix, [candidate])

    assert output is prefix


def test_document_local_record_rejects_oversized_markdown_row() -> None:
    content = f"| Campo | {'x' * 1450} |"
    candidate = _stamped_document_local(content, 0, 20)
    prefix = [{"id": "prefix", "content": "estable"}]

    assert append_validated_coverage(prefix, [candidate]) is prefix


def test_document_local_record_receipt_rejects_tampered_record_bounds() -> None:
    content = "| Campo | Valor |\n| --- | --- |\n| Clave | valor completo |"
    start = content.index("| Clave")
    candidate = _stamped_document_local(content, start, start + 15)
    served = append_validated_coverage([], [candidate])[0]
    served["served_coverage_cards"][0]["record_end"] -= 1

    assert has_exact_served_coverage_receipt(served) is False


def test_append_seam_caps_document_local_lane_at_one() -> None:
    prefix = [{"id": "prefix", "content": "prefijo"}]
    candidates = []
    for row_id in ("first", "second"):
        candidate = _logical_candidate(row_id)
        candidate.update(
            {
                "retrieval_lane": LANE,
                "document_local_coverage_validated": True,
                "document_local_coverage_validation": VALIDATION,
                "document_local_coverage_rank": 1,
            }
        )
        candidates.append(candidate)

    output = append_validated_coverage(prefix, candidates)

    assert [row["id"] for row in output] == ["prefix", "first"]


# ---------------------------------------------------------------------------
# s278 §4 — identidad de blob canónica documento<->chunks/doc_map (UN sitio).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("document_blob", "chunk_blob", "matches"),
    [
        ("X.pdf", "X", True),
        ("X", "X", True),
        ("X.pdf", "X.pdf", True),
        ("X-v2.pdf", "X", False),
        ("X.pdf.pdf", "X", False),
        ("X.pdf.pdf", "X.pdf", False),
        ("X.PDF", "X", False),
        ("X .pdf", "X", False),
        ("X.pdfX", "X", False),
        (".pdf", "", False),
        ("", "", False),
        ("X.pdf", "Y", False),
    ],
)
def test_blob_identity_match_contract(
    document_blob: str, chunk_blob: str, matches: bool
) -> None:
    assert document_local.blob_identity_match(document_blob, chunk_blob) is matches
    assert document_local.blob_identity_match(chunk_blob, document_blob) is matches


def test_resolver_binds_pdf_document_filename_to_bare_chunk_scope() -> None:
    rows = _document_rows()
    for row in rows:
        row["source_pdf_filename"] = SOURCE_FILE + ".pdf"

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert reason == "ok"
    assert authorities == [
        {**_authority(), "source_file": SOURCE_FILE + ".pdf"}
    ]


@pytest.mark.parametrize(
    "filename",
    [
        SOURCE_FILE + "-v2.pdf",
        SOURCE_FILE + ".pdf.pdf",
        SOURCE_FILE + ".PDF",
    ],
)
def test_resolver_rejects_adversarial_blob_identity_variants(
    filename: str,
) -> None:
    rows = _document_rows()
    for row in rows:
        row["source_pdf_filename"] = filename

    authorities, reason = resolve_authoritative_documents(rows, [_scope()])

    assert authorities == []
    assert reason == "active_revision_not_bound_to_anchor_blob"


def test_fetcher_accepts_canonical_pdf_blob_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida el contrato PYTHON de identidad canónica en el fetch (s278 dúo
    r2, Sol#1 — framing corregido): el payload de este test es sintético y el
    RPC v2 REAL nunca lo produciría (su comparación de blob y su join de
    chunks son estrictos en SQL), así que esto NO es un cierre e2e.  El path
    SQL canónico vive como propuesta NO-aplicada en
    supabase/migration_proposals/20260722200000_s278_document_local_snapshot_v3_canonical_blob.sql
    (pendiente de visto junto al data-fix §4)."""
    _configure_live_read_globals(monkeypatch)
    pdf_name = SOURCE_FILE + ".pdf"
    document_rows = _document_rows()
    for row in document_rows:
        row["source_pdf_filename"] = pdf_name
    payload = _snapshot_payload(
        document_rows=document_rows, candidates=[_logical_candidate()]
    )
    payload["authorities"][0]["source_file"] = pdf_name
    client = _GetOnlyClient([payload])

    candidates, authorities, trace = fetch_document_local_candidates(
        QUESTION, [_anchor()], client=client
    )

    assert trace["status"] == "fetched"
    assert authorities == [{**_authority(), "source_file": pdf_name}]
    assert candidates[0]["source_file"] == SOURCE_FILE
    assert candidates[0]["document_local_authority_source_file"] == pdf_name
