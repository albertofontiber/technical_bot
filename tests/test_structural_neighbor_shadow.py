import copy
import inspect
import json

from src.rag import structural_neighbor_shadow as shadow


SECRET = "s" * 32
HASH = "a" * 64


def _row(row_id, index, content):
    return {
        "id": row_id,
        "document_id": "doc-1",
        "extraction_sha256": HASH,
        "chunk_index": index,
        "content": content,
        "section_title": "",
        "product_model": "ID2000",
        "language": "es",
        "source_file": "manual",
        "page_number": 1,
        "duplicate_of": None,
    }


def _fetcher(served, **_kwargs):
    candidate = _row(
        "neighbor",
        16,
        "La pantalla mantiene continuidad y la resistencia máxima del lazo "
        "no debe superar los 35 ohmios. Compruebe la instalación y terminales.",
    )
    return served, [candidate], {"http_requests": 2, "rows_read": len(served) + 1}


def test_disabled_is_inert_and_calls_nothing():
    called = []
    served = [_row("seed", 10, "Conexión de módulo aislador al lazo")]
    before = copy.deepcopy(served)

    event = shadow.observe_structural_neighbor_shadow(
        "¿Cómo se conecta el módulo?",
        served,
        enabled=False,
        fetcher=lambda *_args, **_kwargs: called.append("fetch"),
        sink=lambda _event: called.append("sink"),
    )

    assert event == {"schema": shadow.EVENT_SCHEMA, "status": "disabled", "emitted": False}
    assert called == []
    assert served == before


def test_enabled_observer_is_redacted_non_mutating_and_never_attests():
    served = [_row("seed", 10, "Conexión de módulo aislador al lazo")]
    before = copy.deepcopy(served)
    emitted = []
    query = "¿Cómo se conecta un módulo aislador al lazo ID2000?"

    event = shadow.observe_structural_neighbor_shadow(
        query,
        served,
        enabled=True,
        hmac_key=SECRET,
        hmac_key_version="v1",
        fetcher=_fetcher,
        sink=emitted.append,
        sample_basis_points=10000,
    )

    assert event["status"] == "observed"
    assert event["selected_ids"] == ["neighbor"]
    assert event["served_identity_equal"] is True
    assert event["generator_calls"] == 0
    assert event["database_writes"] == 0
    assert event["coverage_attestations"] == 0
    assert served == before
    encoded = json.dumps(emitted[0], ensure_ascii=False)
    assert set(emitted[0]) <= shadow.TELEMETRY_ALLOWED_FIELDS
    assert emitted[0]["sampling_hmac_key_version"] == "v1"
    assert query not in encoded
    assert "35 ohmios" not in encoded
    assert "content" not in encoded


def test_fetch_error_and_sink_error_both_fail_open():
    served = [_row("seed", 10, "Conexión del lazo")]
    before = copy.deepcopy(served)

    def broken_fetcher(*_args, **_kwargs):
        raise TimeoutError("secret raw failure detail")

    event = shadow.observe_structural_neighbor_shadow(
        "¿Cómo se conecta?",
        served,
        enabled=True,
        hmac_key=SECRET,
        hmac_key_version="v1",
        fetcher=broken_fetcher,
        sink=lambda _event: (_ for _ in ()).throw(RuntimeError("sink down")),
        sample_basis_points=10000,
    )

    assert event["status"] == "error"
    assert event["error_type"] == "TimeoutError"
    assert event["sink_status"] == "error"
    assert "secret raw failure detail" not in json.dumps(event)
    assert served == before


def test_sampled_out_does_not_fetch_or_emit():
    called = []
    event = shadow.observe_structural_neighbor_shadow(
        "q",
        [_row("seed", 10, "x")],
        enabled=True,
        hmac_key=SECRET,
        hmac_key_version="v1",
        fetcher=lambda *_a, **_k: called.append("fetch"),
        sink=lambda _event: called.append("sink"),
        sample_basis_points=1,
    )
    if event["status"] == "sampled_out":
        assert called == []


def test_enabled_observer_requires_non_secret_hmac_key_version():
    event = shadow.observe_structural_neighbor_shadow(
        "q",
        [_row("seed", 10, "x")],
        enabled=True,
        hmac_key=SECRET,
        hmac_key_version="",
        sample_basis_points=10000,
    )
    assert event == {
        "schema": shadow.EVENT_SCHEMA,
        "status": "configuration_error",
        "error_type": "MissingTelemetryHmacKeyVersion",
        "emitted": False,
    }


def test_observer_module_has_no_generator_dependency_or_answer_return_path():
    source = inspect.getsource(shadow)
    assert "from .generator" not in source
    assert "generate_answer" not in source
    assert "return served_chunks" not in source


def test_http_fetcher_uses_get_only_and_respects_same_blob_filter():
    served = [_row("seed", 10, "Conexión del lazo")]
    neighbor = _row("neighbor", 11, "Continuidad y resistencia del lazo")

    class Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Client:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return Response(served if len(self.calls) == 1 else [served[0], neighbor])

    client = Client()
    hydrated, candidates, trace = shadow.fetch_structural_neighbor_rows(
        served,
        max_gap=8,
        max_candidates=20,
        max_http_requests=12,
        timeout_seconds=1.0,
        client=client,
    )

    assert hydrated == served
    assert {row["id"] for row in candidates} == {"seed", "neighbor"}
    assert trace["http_requests"] == 2
    assert len(client.calls) == 2
    neighbor_params = client.calls[1][1]["params"]
    assert neighbor_params["document_id"] == "eq.doc-1"
    assert neighbor_params["extraction_sha256"] == f"eq.{HASH}"
    assert neighbor_params["chunk_index"] == "gte.2"
    assert neighbor_params["and"] == "(chunk_index.lte.18)"
