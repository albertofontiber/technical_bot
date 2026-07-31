"""s288 F2 — the HYQ lane is scoped by document IDENTITY, not by file name.

The exclusion tests below drive ``fetch_document_scoped_rows`` against a fake
PostgREST that actually honours the filters the lane sends (and can be told to
IGNORE them, which is how the client-side belts get exercised).  No network, no
database: every read is served from in-memory rows.
"""
import json
from pathlib import Path

import httpx
import pytest

import src.rag.doc_scoped_hyq_coverage as lane

ROOT = Path(__file__).resolve().parents[1]
COMPAT_QUERY = ROOT / "config" / "retrieval_facets_compatibility_candidate_v1.yaml"
COMPAT_EVIDENCE = ROOT / "config" / "evidence_coverage_compatibility_candidate_v1.yaml"

DOC_A = "aaaaaaaa-0000-4000-8000-000000000001"
DOC_B = "bbbbbbbb-0000-4000-8000-000000000002"
SHA_A = "a1" * 32
SHA_B = "b2" * 32
PLACEHOLDER_SHA = "backfill:" + "c3" * 32
NEED = "capacidad lazos"
QUESTION = "capacidad de lazos del panel"


# --------------------------------------------------------------------------- #
# Fake PostgREST
# --------------------------------------------------------------------------- #
def _in_values(value: str) -> list[str]:
    """Inverse of ``_postgrest_in`` (its escaping is JSON string escaping)."""
    assert value.startswith("in.(") and value.endswith(")"), value
    return json.loads("[" + value[len("in.(") : -1] + "]")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakePostgrest:
    """Minimal stand-in for the reads this lane performs."""

    def __init__(
        self,
        *,
        documents=None,
        hyq=None,
        chunks=None,
        fail_tables=(),
        honour_document_filter=True,
        honour_duplicate_filter=True,
        embed_overrides=None,
    ):
        self.documents = list(documents or [])
        self.hyq = list(hyq or [])
        self.chunks = list(chunks or [])
        self.fail_tables = set(fail_tables)
        self.honour_document_filter = honour_document_filter
        self.honour_duplicate_filter = honour_duplicate_filter
        self.embed_overrides = dict(embed_overrides or {})
        self.requests: list[dict] = []

    # httpx.Client-compatible surface used by the lane
    def get(self, url, *, headers=None, params=None, timeout=None):
        table = url.rsplit("/", 1)[-1]
        self.requests.append({"table": table, "params": dict(params or {})})
        if table in self.fail_tables:
            raise httpx.ConnectError("simulated PostgREST failure")
        handlers = {
            "documents": self._documents,
            "chunks_v2_hyq": self._navigate,
            "chunks_v2": self._hydrate,
        }
        return _FakeResponse(handlers[table](dict(params or {})))

    def tables(self) -> list[str]:
        return [request["table"] for request in self.requests]

    def _documents(self, params):
        wanted = _in_values(params["id"])
        return [
            {key: row.get(key) for key in ("id", "status", "source_pdf_sha256")}
            for row in self.documents
            if row["id"] in wanted
        ]

    def _parent_of(self, chunk_id):
        parent = next(
            (row for row in self.chunks if row["id"] == chunk_id), None
        )
        if parent is None:
            return None
        embedded = {
            key: parent.get(key)
            for key in ("document_id", "duplicate_of", "source_file", "page_number")
        }
        embedded.update(self.embed_overrides.get(chunk_id, {}))
        return embedded

    def _navigate(self, params):
        wanted = _in_values(params["chunks_v2.document_id"])
        rows = []
        for row in self.hyq:
            embedded = self._parent_of(row["chunk_id"])
            if embedded is None:  # !inner drops rows without a parent
                continue
            if (
                self.honour_document_filter
                and embedded.get("document_id") not in wanted
            ):
                continue
            if (
                self.honour_duplicate_filter
                and params.get("chunks_v2.duplicate_of") == "is.null"
                and embedded.get("duplicate_of") is not None
            ):
                continue
            rows.append(
                {
                    "chunk_id": row["chunk_id"],
                    "question": row["question"],
                    "chunks_v2": embedded,
                }
            )
        rows.sort(key=lambda row: (row["chunk_id"], row["question"]))
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", len(rows)))
        return rows[offset : offset + limit]

    def _hydrate(self, params):
        wanted = _in_values(params["id"])
        rows = [dict(row) for row in self.chunks if row["id"] in wanted]
        return rows[: int(params.get("limit", len(rows)))]


def _document(document_id, sha256, status="active"):
    return {"id": document_id, "status": status, "source_pdf_sha256": sha256}


def _chunk(
    chunk_id,
    document_id,
    sha256,
    *,
    source_file="manual",
    page_number=1,
    content="El sistema admite cuatro lazos y 792 dispositivos en total.",
    duplicate_of=None,
):
    return {
        "id": chunk_id,
        "content": content,
        "source_file": source_file,
        "page_number": page_number,
        "document_id": document_id,
        "extraction_sha256": sha256,
        "chunk_index": 0,
        "duplicate_of": duplicate_of,
    }


def _hyq_row(chunk_id, question=QUESTION):
    return {"chunk_id": chunk_id, "question": question}


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setattr(lane, "SUPABASE_URL", "https://fake.supabase.test")
    monkeypatch.setattr(lane, "SUPABASE_SERVICE_KEY", "fake-service-key")


def _fetch(client, scope=(DOC_A,), needs=(NEED,)):
    return lane.fetch_document_scoped_rows(
        list(scope), list(needs), client=client, include_receipts=True
    )


def _reasons(receipts, identifier):
    return sorted(
        entry["reason"]
        for entry in receipts["parents_rejected"]
        if entry["id"] == identifier
    )


# --------------------------------------------------------------------------- #
# Parent selection (unchanged internal shape: the flattened, parent-derived row)
# --------------------------------------------------------------------------- #
def test_parent_selection_is_bounded_and_source_diverse():
    rows = [
        {
            "chunk_id": f"a-{index}",
            "source_file": "manual-a",
            "page_number": index,
            "question": f"capacidad total lazos dispositivos variante {index}",
        }
        for index in range(8)
    ] + [
        {
            "chunk_id": "b-1",
            "source_file": "manual-b",
            "page_number": 1,
            "question": "capacidad total lazos dispositivos alternativa",
        }
    ]

    selected = lane.select_document_diverse_parents(
        ["capacidad total lazos dispositivos"], rows
    )

    assert "b-1" in selected
    assert len(selected) <= lane.PARENT_LIMIT


def test_parent_selection_stratifies_compound_query_by_governed_entity():
    rows = [
        {
            "chunk_id": "panel-topology",
            "source_file": "panel-install",
            "page_number": 9,
            "question": "topologia bucle cerrado retorno del panel",
        },
        {
            "chunk_id": "detector-protocol",
            "source_file": "detector-manual",
            "page_number": 69,
            "question": "protocolo de comunicacion del detector",
        },
        {
            "chunk_id": "detector-roster",
            "source_file": "detector-manual",
            "page_number": 71,
            "question": "equipos y detectores compatibles",
        },
        {
            "chunk_id": "generic-noise",
            "source_file": "popular-manual",
            "page_number": 1,
            "question": "protocolo detector equipos compatibles topologia bucle retorno",
        },
    ]
    selected = lane.select_document_diverse_parents(
        [
            "panel detector protocolo",
            "panel detector equipos compatibles",
            "panel detector topologia bucle retorno",
        ],
        rows,
        source_groups=[
            {"token": "panel", "sources": ["panel-install"]},
            {"token": "detector", "sources": ["detector-manual"]},
        ],
        focus_query="panel detector",
    )

    assert "generic-noise" not in selected
    assert "panel-topology" in selected
    assert {"detector-protocol", "detector-roster"}.issubset(selected)


# --------------------------------------------------------------------------- #
# F2.1 navigation contract + budget
# --------------------------------------------------------------------------- #
def test_navigation_scopes_by_document_id_through_the_parent_embed(credentials):
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_A)],
    )

    parents, hyq_rows, requests, receipts = _fetch(client)

    assert [row["id"] for row in parents] == ["chunk-a"]
    assert hyq_rows == 1
    # Authority read is FIRST, then navigation, then hydration.
    assert client.tables() == ["documents", "chunks_v2_hyq", "chunks_v2"]
    navigation = client.requests[1]["params"]
    assert navigation["select"] == (
        "chunk_id,question,"
        "chunks_v2!inner(document_id,duplicate_of,source_file,page_number)"
    )
    assert navigation["chunks_v2.document_id"] == lane._postgrest_in([DOC_A])
    assert navigation["chunks_v2.duplicate_of"] == "is.null"
    # The name scope is dead, and the order key is top-level only.
    assert "source_file" not in navigation
    assert navigation["order"] == "chunk_id.asc,question.asc"
    assert requests == 3
    assert receipts["scope_document_ids"] == [DOC_A]
    assert receipts["parents_rejected"] == []


def test_navigation_rows_carry_parent_derived_source_and_page(credentials):
    embedded = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[
            _chunk("chunk-a", DOC_A, SHA_A, source_file="parent-name", page_number=42)
        ],
    )
    page = embedded._navigate(
        {
            "chunks_v2.document_id": lane._postgrest_in([DOC_A]),
            "chunks_v2.duplicate_of": "is.null",
        }
    )

    flattened = lane._flatten_navigation_rows(page, {DOC_A: SHA_A})

    assert flattened == [
        {
            "chunk_id": "chunk-a",
            "question": QUESTION,
            "document_id": DOC_A,
            "source_file": "parent-name",
            "page_number": 42,
        }
    ]


def test_http_budget_is_exactly_six_with_zero_slack():
    assert lane.MAX_HTTP_REQUESTS == 6
    documents_reads = 1
    navigation_pages = lane.ROW_LIMIT // lane.PAGE_SIZE
    hydration_reads = 1
    assert (
        documents_reads + navigation_pages + hydration_reads
        == lane.MAX_HTTP_REQUESTS
    )


def test_empty_document_scope_fails_closed(credentials):
    with pytest.raises(RuntimeError):
        lane.fetch_document_scoped_rows([], [NEED], client=_FakePostgrest())


# --------------------------------------------------------------------------- #
# F2.3 exclusion gate
# --------------------------------------------------------------------------- #
def test_superseded_document_never_navigates_or_hydrates(credentials):
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A, status="superseded")],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_A)],
    )

    parents, hyq_rows, requests, receipts = _fetch(client)

    assert parents == []
    assert hyq_rows == 0
    assert client.tables() == ["documents"]  # navigation never ran
    assert requests == 1
    assert _reasons(receipts, DOC_A) == ["document_not_active"]


def test_placeholder_sha_document_is_rejected_before_navigation(credentials):
    client = _FakePostgrest(
        documents=[_document(DOC_A, PLACEHOLDER_SHA)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, PLACEHOLDER_SHA)],
    )

    parents, _, _, receipts = _fetch(client)

    assert parents == []
    assert client.tables() == ["documents"]
    assert _reasons(receipts, DOC_A) == ["document_sha_placeholder"]


def test_missing_document_row_is_rejected(credentials):
    client = _FakePostgrest(
        documents=[],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_A)],
    )

    parents, _, _, receipts = _fetch(client)

    assert parents == []
    assert _reasons(receipts, DOC_A) == ["document_row_missing"]


def test_source_file_collision_only_serves_the_scoped_document(credentials):
    """Two documents, same ``source_file``: only the scoped id may serve."""
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A), _document(DOC_B, SHA_B)],
        hyq=[_hyq_row("chunk-a"), _hyq_row("chunk-b")],
        chunks=[
            _chunk("chunk-a", DOC_A, SHA_A, source_file="shared-name"),
            _chunk("chunk-b", DOC_B, SHA_B, source_file="shared-name"),
        ],
    )

    parents, hyq_rows, _, receipts = _fetch(client, scope=(DOC_A,))

    assert [row["id"] for row in parents] == ["chunk-a"]
    assert hyq_rows == 1
    # The colliding document is never even hydrated.
    assert client.requests[-1]["params"]["id"] == lane._postgrest_in(["chunk-a"])
    assert receipts["scope_document_ids"] == [DOC_A]


def test_navigation_belt_drops_rows_outside_the_authorised_scope(credentials):
    """If the deploy ignored the embed filter, the client-side belt still holds."""
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A), _document(DOC_B, SHA_B)],
        hyq=[_hyq_row("chunk-a"), _hyq_row("chunk-b")],
        chunks=[
            _chunk("chunk-a", DOC_A, SHA_A, source_file="shared-name"),
            _chunk("chunk-b", DOC_B, SHA_B, source_file="shared-name"),
        ],
        honour_document_filter=False,
    )

    parents, hyq_rows, _, receipts = _fetch(client, scope=(DOC_A,))

    assert [row["id"] for row in parents] == ["chunk-a"]
    assert hyq_rows == 1
    assert receipts["navigation_rows_skipped"] == 1


def test_sha_mismatch_parent_is_never_served(credentials):
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_B)],  # binds to another blob
    )

    parents, _, _, receipts = _fetch(client)

    assert parents == []
    assert _reasons(receipts, "chunk-a") == ["parent_extraction_sha_mismatch"]


def test_duplicate_parent_is_dropped_in_navigation_and_in_hydration(credentials):
    """Belt AND braces: the server filter is simulated OFF on purpose."""
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-dup"), _hyq_row("chunk-ok")],
        chunks=[
            _chunk("chunk-dup", DOC_A, SHA_A, duplicate_of="chunk-ok"),
            _chunk("chunk-ok", DOC_A, SHA_A),
        ],
        honour_duplicate_filter=False,
    )

    parents, hyq_rows, _, receipts = _fetch(client)

    assert [row["id"] for row in parents] == ["chunk-ok"]
    assert hyq_rows == 1
    assert receipts["navigation_rows_skipped"] == 1

    # Braces: a duplicate that somehow reached hydration is rejected there too.
    assert (
        lane._parent_rejection_reason(
            _chunk("chunk-dup", DOC_A, SHA_A, duplicate_of="chunk-ok"),
            {DOC_A: SHA_A},
        )
        == "parent_marked_duplicate"
    )


def test_hydrated_parent_from_another_document_is_rejected(credentials):
    """Navigation claimed the scoped doc; the real chunk belongs elsewhere."""
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_B, SHA_B, source_file="shared-name")],
        embed_overrides={"chunk-a": {"document_id": DOC_A}},
    )

    parents, hyq_rows, _, receipts = _fetch(client)

    assert parents == []
    assert hyq_rows == 1
    assert _reasons(receipts, "chunk-a") == ["parent_document_out_of_scope"]


def test_mixed_state_partial_backfill_serves_the_real_document(credentials):
    """P-A applied to one doc and not the other must not kill the lane."""
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A), _document(DOC_B, PLACEHOLDER_SHA)],
        hyq=[_hyq_row("chunk-a"), _hyq_row("chunk-b")],
        chunks=[
            _chunk("chunk-a", DOC_A, SHA_A, source_file="real-manual"),
            _chunk("chunk-b", DOC_B, PLACEHOLDER_SHA, source_file="placeholder-manual"),
        ],
    )

    parents, hyq_rows, _, receipts = _fetch(client, scope=(DOC_A, DOC_B))

    assert [row["id"] for row in parents] == ["chunk-a"]
    assert hyq_rows == 1
    assert _reasons(receipts, DOC_B) == ["document_sha_placeholder"]
    assert receipts["scope_document_ids"] == sorted([DOC_A, DOC_B])
    assert client.requests[1]["params"]["chunks_v2.document_id"] == (
        lane._postgrest_in([DOC_A])
    )


def test_documents_read_failure_degrades_closed(credentials):
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_A)],
        fail_tables={"documents"},
    )

    parents, hyq_rows, requests, receipts = _fetch(client)

    assert parents == []
    assert hyq_rows == 0
    assert requests == 1
    assert client.tables() == ["documents"]
    assert _reasons(receipts, DOC_A) == ["documents_read_failed"]


# --------------------------------------------------------------------------- #
# Collector: scope from the resolver, re-assert by document_id, receipts
# --------------------------------------------------------------------------- #
def _patch_resolution(monkeypatch, document_ids, *, archetype="capacity_count",
                      needs=(NEED,), source_files=None):
    source_files = source_files or [f"manual-{index}" for index in range(len(document_ids))]
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {
            "allowed_sources": frozenset(source_files),
            "resolved_documents": [
                {"document_id": document_id, "source_file": source_file}
                for document_id, source_file in zip(document_ids, source_files)
            ],
        },
    )
    # s288b: la lane pasa SIEMPRE su puntero de facets (default de la firma), así
    # que el doble tiene que aceptar el argumento de config.
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query, *_args, **_kwargs: {
            "archetype": archetype,
            "needs": list(needs),
        },
    )


def test_collection_serves_parent_source_not_generated_hyq(monkeypatch):
    content = "El sistema admite cuatro lazos y 792 dispositivos en total."
    parent = {
        "id": "parent-real",
        "content": content,
        "source_file": "manual-real",
        "document_id": DOC_A,
    }
    _patch_resolution(monkeypatch, [DOC_A], source_files=["manual-real"])
    monkeypatch.setattr(
        lane,
        "select_evidence_coverage_cards",
        lambda candidates, **_kwargs: [
            {
                "candidate_id": candidates[0]["id"],
                "start": 0,
                "end": len(content),
                "quote": content,
                "facet": "capacity",
                # s288b: el selector real SIEMPRE emite esta clave; la barrera
                # espejo exige que al menos una card la traiga no vacía.
                "query_term_hits": ["lazos"],
                "exact_source_span_validated": True,
            }
        ],
    )

    def fetcher(scope, needs):
        assert scope == [DOC_A]  # document ids, not file names
        assert needs == [NEED]
        return [parent], 23

    selected, trace = lane.collect_document_scoped_hyq(
        "¿Cuántos lazos admite?", fetcher=fetcher
    )

    assert selected[0]["id"] == "parent-real"
    assert selected[0]["content"] == content
    assert "question" not in selected[0]
    assert selected[0]["hyq_navigation_validated"] is True
    assert trace["served_hyq_prose"] is False
    assert trace["hyq_rows"] == 23
    assert trace["http_requests"] == 0
    assert trace["scope_document_ids"] == [DOC_A]
    assert trace["parents_rejected"] == []


def test_collection_without_resolved_documents_is_not_applicable(monkeypatch):
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {"allowed_sources": frozenset({"manual"})},
    )
    monkeypatch.setattr(
        lane,
        "expand_query_facets",
        lambda _query, *_args, **_kwargs: {
            "archetype": "capacity_quantity",
            "needs": ["capacity"],
        },
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a name-only resolution must not reach the fetcher")

    selected, trace = lane.collect_document_scoped_hyq("capacidad", fetcher=forbidden)

    assert selected == []
    assert trace["status"] == "not_applicable"
    assert trace["scope_document_ids"] == []


def test_collection_propagates_hyq_http_request_count(monkeypatch):
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"])

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad", fetcher=lambda _scope, _needs: ([], 1200, 3)
    )

    assert selected == []
    assert trace["http_requests"] == 3


def test_collection_propagates_versioned_fetch_fingerprints(monkeypatch):
    receipts = {
        "hyq_rows_sha256": "a" * 64,
        "selected_parent_ids_sha256": "b" * 64,
        "hydrated_parents_sha256": "c" * 64,
    }
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"])

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: ([], 1200, 3, receipts),
        include_fetch_receipts=True,
    )

    assert selected == []
    assert trace["fetch_receipts"] == receipts


def test_collection_carries_fetcher_rejections_into_the_trace(monkeypatch):
    receipts = {
        "hyq_rows_sha256": "a" * 64,
        "selected_parent_ids_sha256": "b" * 64,
        "hydrated_parents_sha256": "c" * 64,
        "scope_document_ids": [DOC_A],
        "parents_rejected": [
            {"id": DOC_A, "reason": "document_sha_placeholder", "scope": "document"}
        ],
    }
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"])

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: ([], 0, 1, receipts),
        include_fetch_receipts=True,
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"
    assert trace["parents_rejected"] == receipts["parents_rejected"]


def test_collection_prefers_complementary_facets_over_duplicate_early_parents(monkeypatch):
    parents = [
        {"id": "unit-a", "content": "a", "source_file": "manual", "document_id": DOC_A},
        {"id": "unit-b", "content": "b", "source_file": "manual", "document_id": DOC_A},
        {"id": "total", "content": "c", "source_file": "manual", "document_id": DOC_A},
    ]
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])

    def cards(candidates, **_kwargs):
        parent = candidates[0]
        facet = "system_total" if parent["id"] == "total" else "per_unit_capacity"
        return [
            {
                "candidate_id": parent["id"],
                "start": 0,
                "end": 1,
                "quote": parent["content"],
                "facet": facet,
                "query_term_hits": ["model"],
                "exact_source_span_validated": True,
            }
        ]

    monkeypatch.setattr(lane, "select_evidence_coverage_cards", cards)
    selected, _ = lane.collect_document_scoped_hyq(
        "capacidad del modelo", fetcher=lambda _scope, _needs: (parents, 3)
    )

    assert [row["id"] for row in selected] == ["unit-a", "total"]


def test_collection_traces_the_parent_that_produced_no_card(monkeypatch):
    """s288b: el descarte sin-card deja de ser un ``continue`` mudo.

    Antes, un parent que no producía card desaparecía sin razón y el síntoma era
    indistinguible de un hueco de corpus (feedback_corpus_gap).
    """
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])
    monkeypatch.setattr(lane, "select_evidence_coverage_cards", lambda *_a, **_k: [])

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: (
            [
                {
                    "id": "cardless",
                    "content": "prosa sin faceta",
                    "source_file": "manual",
                    "document_id": DOC_A,
                }
            ],
            1,
        ),
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"
    assert trace["parents_rejected"] == [
        {"id": "cardless", "reason": "no_matching_card", "scope": "parent"}
    ]


def test_collection_rejects_the_parent_without_a_query_aligned_card(monkeypatch):
    """s288b (barrera espejo de ``_query_card`` en rerank_pool_coverage).

    ``evidence_coverage_facets_v5`` no exige alineación de query en la card; sin
    esta barrera, adoptar v5 relajaría el gate de la lane.  Un parent cuyas cards
    NO comparten ningún anclaje distintivo con la pregunta no sirve, y se traza.
    """
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])
    monkeypatch.setattr(
        lane,
        "select_evidence_coverage_cards",
        lambda candidates, **_kwargs: [
            {
                "candidate_id": candidates[0]["id"],
                "start": 0,
                "end": 5,
                "quote": "lazos",
                "facet": "per_unit_capacity",
                "query_term_hits": [],
                "exact_source_span_validated": True,
            }
        ],
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: (
            [
                {
                    "id": "unaligned",
                    "content": "lazos",
                    "source_file": "manual",
                    "document_id": DOC_A,
                }
            ],
            1,
        ),
    )

    assert selected == []
    assert trace["parents_rejected"] == [
        {"id": "unaligned", "reason": "no_query_aligned_card", "scope": "parent"}
    ]


def test_a_consumer_with_its_own_contract_can_opt_out_of_the_query_barrier(monkeypatch):
    """El opt-out es EXPLÍCITO y fail-closed por default (bundle de compatibilidad).

    Su gate relacional de dos entidades sustituye a la alineación por query, del
    mismo modo que la reserva obligation-aware sustituye la suya (s278 §3).
    """
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])
    monkeypatch.setattr(
        lane,
        "select_evidence_coverage_cards",
        lambda candidates, **_kwargs: [
            {
                "candidate_id": candidates[0]["id"],
                "start": 0,
                "end": 5,
                "quote": "lazos",
                "facet": "per_unit_capacity",
                "query_term_hits": [],
                "exact_source_span_validated": True,
            }
        ],
    )
    parents = (
        [
            {
                "id": "unaligned",
                "content": "lazos",
                "source_file": "manual",
                "document_id": DOC_A,
            }
        ],
        1,
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: parents,
        require_query_aligned_card=False,
    )

    assert [row["id"] for row in selected] == ["unaligned"]
    assert trace["parents_rejected"] == []


def test_collection_rejects_hydrated_parent_outside_document_scope(monkeypatch):
    """Same file NAME, different document identity: the name cannot authorise."""
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["shared-name"])
    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: (
            [
                {
                    "id": "cross-scope",
                    "content": "lazo capacidad",
                    "source_file": "shared-name",
                    "document_id": DOC_B,
                }
            ],
            1,
        ),
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"
    assert trace["parents_rejected"] == [
        {
            "id": "cross-scope",
            "reason": "parent_document_out_of_scope",
            "scope": "parent",
        }
    ]


def test_collection_rejects_duplicate_parent_after_hydration(monkeypatch):
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])
    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda _scope, _needs: (
            [
                {
                    "id": "dup",
                    "content": "lazo capacidad",
                    "source_file": "manual",
                    "document_id": DOC_A,
                    "duplicate_of": "other",
                }
            ],
            1,
        ),
    )

    assert selected == []
    assert trace["parents_rejected"] == [
        {"id": "dup", "reason": "parent_marked_duplicate", "scope": "parent"}
    ]


def test_collection_degrades_closed_when_the_documents_read_fails(
    monkeypatch, credentials
):
    """End-to-end fail-closed: no crash, no rows, reason traced."""
    _patch_resolution(monkeypatch, [DOC_A], archetype="capacity_quantity",
                      needs=["capacity"], source_files=["manual"])
    client = _FakePostgrest(
        documents=[_document(DOC_A, SHA_A)],
        hyq=[_hyq_row("chunk-a")],
        chunks=[_chunk("chunk-a", DOC_A, SHA_A)],
        fail_tables={"documents"},
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "capacidad",
        fetcher=lambda scope, needs: lane.fetch_document_scoped_rows(
            scope, needs, client=client, include_receipts=True
        ),
        include_fetch_receipts=True,
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"
    assert trace["parents_rejected"] == [
        {"id": DOC_A, "reason": "documents_read_failed", "scope": "document"}
    ]


def test_candidate_compatibility_contract_can_cover_three_complementary_relations(monkeypatch):
    parents = [
        {
            "id": "protocol",
            "content": "La comunicación del lazo utiliza el protocolo CLIP; consulte los equipos compatibles.",
            "source_file": "manual-a",
            "document_id": DOC_A,
        },
        {
            "id": "roster",
            "content": "Equipos de lazo compatibles: detector óptico SDX-751.",
            "source_file": "manual-a",
            "document_id": DOC_A,
        },
        {
            "id": "topology",
            "content": "El bucle debe ser cerrado: sale de la central y el retorno vuelve a ella.",
            "source_file": "manual-b",
            "document_id": DOC_B,
        },
    ]
    monkeypatch.setattr(
        lane,
        "resolve_query",
        lambda _query: {
            "allowed_sources": frozenset({"manual-a", "manual-b"}),
            "resolved_documents": [
                {"document_id": DOC_A, "source_file": "manual-a"},
                {"document_id": DOC_B, "source_file": "manual-b"},
            ],
        },
    )

    selected, trace = lane.collect_document_scoped_hyq(
        "¿Es compatible el detector SDX-751 con esta central y su lazo?",
        fetcher=lambda _scope, _needs: (parents, 30, 2),
        query_facets_path=COMPAT_QUERY,
        evidence_config_path=COMPAT_EVIDENCE,
        append_limit=3,
        entity_stratified=True,
        # Calca el call site real (compatibility_bundle_coverage.py): su gate
        # relacional sustituye a la barrera espejo de alineación (s288b).
        require_query_aligned_card=False,
    )

    assert [row["id"] for row in selected] == ["protocol", "roster", "topology"]
    assert {facet for row in selected for facet in row["coverage_card_facets"]} == {
        "protocol_scope",
        "supported_device_roster",
        "loop_topology",
    }
    assert trace["served_hyq_prose"] is False
    assert trace["http_requests"] == 2


def test_candidate_compatibility_append_budget_is_bounded():
    try:
        lane.collect_document_scoped_hyq("compatibilidad", append_limit=4)
    except ValueError as exc:
        assert str(exc) == "HYQ append limit must be 1..3"
    else:
        raise AssertionError("over-budget compatibility append must fail closed")


# --------------------------------------------------------------------------- #
# Optional read-only smoke against the real deploy (skipped without credentials)
# --------------------------------------------------------------------------- #
def _live_credentials() -> bool:
    from src import config

    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


@pytest.mark.skipif(
    not _live_credentials(), reason="no Supabase credentials for the embed smoke"
)
def test_smoke_real_postgrest_accepts_the_embedded_document_scope():
    """One read-only navigation read: does the deploy accept ``chunks_v2!inner``?"""
    from src import config

    base = config.SUPABASE_URL.rstrip("/") + "/rest/v1/"
    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=30.0) as client:
        seed = client.get(
            base + "chunks_v2_hyq",
            headers=headers,
            params={
                "select": "chunk_id,chunks_v2!inner(document_id)",
                "chunks_v2.document_id": "not.is.null",
                "chunks_v2.duplicate_of": "is.null",
                "limit": "1",
            },
        )
        assert seed.status_code == 200, seed.text
        seed_rows = seed.json()
        if not seed_rows:
            pytest.skip("no navigable hyq rows in this deploy")
        document_id = str(seed_rows[0]["chunks_v2"]["document_id"])

        navigation = client.get(
            base + "chunks_v2_hyq",
            headers=headers,
            params={
                "select": lane._HYQ_SELECT,
                "chunks_v2.document_id": lane._postgrest_in([document_id]),
                "chunks_v2.duplicate_of": "is.null",
                "order": lane._HYQ_ORDER,
                "limit": "5",
                "offset": "0",
            },
        )
        assert navigation.status_code == 200, navigation.text
        rows = navigation.json()
        assert isinstance(rows, list) and rows
        for row in rows:
            parent = row["chunks_v2"]
            assert set(parent) == {
                "document_id",
                "duplicate_of",
                "source_file",
                "page_number",
            }
            assert str(parent["document_id"]) == document_id
            assert parent["duplicate_of"] is None
        assert len(lane._flatten_navigation_rows(rows, {document_id: SHA_A})) == len(rows)

        authority = client.get(
            base + "documents",
            headers=headers,
            params={
                "select": lane._DOCUMENT_SELECT,
                "id": lane._postgrest_in([document_id]),
                "limit": "1",
            },
        )
        assert authority.status_code == 200, authority.text
        assert [str(row["id"]) for row in authority.json()] == [document_id]
