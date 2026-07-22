"""Tests s278 §1b (LIMIT-ORDER, dúo r1): determinismo + autoridad en content_search.

Contratos: los GET directos de content_search (Path A y fallback ilike) llevan
`order` SERVER-SIDE exacto (la ventana deja de ser plan-dependiente) con LIMIT
interno mayor; el rank de autoridad (`documents.status`, UNA llamada batched)
reordena active por delante de superseded DENTRO de la ventana ANTES del corte
final; fail-open sin status (queda solo el orden estable); con <LIMIT filas el
comportamiento es idéntico salvo orden. Residual >ventana declarado en el código,
no testeable aquí (se mide en la pasada e2e).
"""
import pytest

import src.rag.retriever as retriever

_ORDER = "source_file.asc,page_number.asc,id.asc"


class _FakeResp:
    def __init__(self, rows, status=200):
        self._rows, self._status = rows, status

    def raise_for_status(self):
        if self._status >= 400:
            raise RuntimeError(f"HTTP {self._status}")

    @property
    def status_code(self):
        return self._status

    def json(self):
        return self._rows


class _FakeClient:
    get_rows_by_url: dict = {}    # substring de URL → rows a devolver en GET
    fail_urls: set = set()        # substring de URL → el GET lanza (red caída)
    gets: list = []               # [(url, params), ...] — todas las llamadas GET
    post_status: int = 200        # status del RPC (Path B); 500 fuerza el fallback

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url="", *a, **k):
        _FakeClient.gets.append((url, k.get("params")))
        for frag in _FakeClient.fail_urls:
            if frag in url:
                raise RuntimeError("network down")
        for frag, rows in _FakeClient.get_rows_by_url.items():
            if frag in url:
                return _FakeResp(rows)
        return _FakeResp([])

    def post(self, url="", *a, **k):
        return _FakeResp([], status=_FakeClient.post_status)


@pytest.fixture
def fake_http(monkeypatch):
    _FakeClient.get_rows_by_url, _FakeClient.fail_urls = {}, set()
    _FakeClient.gets, _FakeClient.post_status = [], 200
    monkeypatch.setattr(retriever.httpx, "Client", _FakeClient)
    monkeypatch.setattr(retriever, "CHUNKS_TABLE", "chunks_v2")
    return _FakeClient


def _chunk_gets(fake):
    return [p for u, p in fake.gets if "chunks_v2" in u]


def _doc_gets(fake):
    return [p for u, p in fake.gets if "/documents" in u]


# ---------- (i) order server-side exacto ----------

def test_path_a_lleva_order_server_side_exacto(fake_http):
    retriever.content_search("relé de avería", limit=5, product_model="ZX2e")
    (params,) = _chunk_gets(fake_http)
    assert params["order"] == _ORDER
    # ventana interna > corte final (mitigación del residual >LIMIT)
    assert int(params["limit"]) == 5 * retriever._CONTENT_SEARCH_WINDOW_FACTOR


def test_fallback_ilike_sin_rpc_lleva_el_mismo_order(fake_http):
    fake_http.post_status = 500          # RPC caído → Path B cae al GET ilike
    retriever.content_search("pulsador", limit=5)
    (params,) = _chunk_gets(fake_http)
    assert params["order"] == _ORDER
    assert int(params["limit"]) == 5 * retriever._CONTENT_SEARCH_WINDOW_FACTOR


# ---------- (ii) rank de autoridad dentro de la ventana ----------

def test_rank_autoridad_reordena_active_delante_de_superseded(fake_http):
    fake_http.get_rows_by_url = {
        "chunks_v2": [
            {"id": "c-sup", "document_id": "d-sup", "source_file": "a.pdf", "page_number": 1},
            {"id": "c-act", "document_id": "d-act", "source_file": "b.pdf", "page_number": 1},
        ],
        "documents": [
            {"id": "d-sup", "status": "superseded"},
            {"id": "d-act", "status": "active"},
        ],
    }
    out = retriever.content_search("relé", limit=2, product_model="ZX2e")
    assert [c["id"] for c in out] == ["c-act", "c-sup"]
    assert all(c["similarity"] == 0.80 for c in out)
    # UNA llamada batched al estilo _filter_by_document_status, no una por chunk
    doc_gets = _doc_gets(fake_http)
    assert len(doc_gets) == 1
    assert doc_gets[0]["select"] == "id,status"


def test_rank_corre_antes_del_corte_final(fake_http):
    # Con limit=1 el superseded ocupa el primer slot de la ventana server-side:
    # si el rank corriera DESPUÉS del corte, el active jamás entraría.
    fake_http.get_rows_by_url = {
        "chunks_v2": [
            {"id": "c-sup", "document_id": "d-sup"},
            {"id": "c-act", "document_id": "d-act"},
        ],
        "documents": [
            {"id": "d-sup", "status": "superseded"},
            {"id": "d-act", "status": "active"},
        ],
    }
    out = retriever.content_search("relé", limit=1, product_model="ZX2e")
    assert [c["id"] for c in out] == ["c-act"]


def test_legacy_sin_document_id_no_se_penaliza(fake_http):
    # Espejo del fail-open de _filter_by_document_status (que CONSERVA legacy):
    # sin status conocido no se demota — empata con active y decide el orden estable.
    fake_http.get_rows_by_url = {
        "chunks_v2": [
            {"id": "c-legacy", "document_id": None},
            {"id": "c-act", "document_id": "d-act"},
            {"id": "c-sup", "document_id": "d-sup"},
        ],
        "documents": [
            {"id": "d-act", "status": "active"},
            {"id": "d-sup", "status": "superseded"},
        ],
    }
    out = retriever.content_search("relé", limit=3, product_model="ZX2e")
    assert [c["id"] for c in out] == ["c-legacy", "c-act", "c-sup"]


# ---------- (iii) fail-open sin status ----------

def test_fail_open_sin_status_conserva_orden_estable(fake_http):
    fake_http.get_rows_by_url = {
        "chunks_v2": [
            {"id": "c1", "document_id": "d1"},
            {"id": "c2", "document_id": "d2"},
        ],
    }
    fake_http.fail_urls = {"/documents"}
    out = retriever.content_search("relé", limit=2, product_model="ZX2e")
    # el fallo del rank NO mata el path: orden server-side intacto + stamping normal
    assert [c["id"] for c in out] == ["c1", "c2"]
    assert all(c["similarity"] == 0.80 for c in out)


# ---------- (iv) <LIMIT filas: idéntico salvo orden ----------

def test_menos_que_limit_filas_identico_salvo_orden(fake_http):
    fake_http.get_rows_by_url = {
        "chunks_v2": [
            {"id": "c1", "document_id": None},
            {"id": "c2", "document_id": None},
        ],
    }
    out = retriever.content_search("relé", limit=5, product_model="ZX2e")
    assert {c["id"] for c in out} == {"c1", "c2"}
    assert all(c["similarity"] == 0.80 for c in out)
    # todo legacy → ni siquiera se consulta /documents (cero llamadas extra)
    assert _doc_gets(fake_http) == []
