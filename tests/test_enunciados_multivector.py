"""Tests del multi-vector de enunciados T0 (s94b; sustituye a los del sidecar del piloto).

Contratos: invariante de NO-SERVICIO (los GET léxicos llevan parent_id=is.null sobre
chunks_v2; el RPC solo recibe include_surrogates con el flag on), swap-from-ROW
(linkage en la fila, sin sidecar), 1:1 con similarity del surrogate, keep-max,
fail-closed, flag default OFF.
"""
import os

import pytest

import src.rag.retriever as retriever


class _FakeResp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    @property
    def status_code(self):
        return 200

    def json(self):
        return self._rows


class _FakeClient:
    rows: list = []
    post_rows_by_url: dict = {}       # substring de URL → rows a devolver
    last_get_params: dict | None = None
    last_post_json: dict | None = None
    posts: list = []                  # [(url, json), ...] — todas las llamadas POST

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        _FakeClient.last_get_params = k.get("params")
        return _FakeResp(_FakeClient.rows)

    def post(self, url="", *a, **k):
        _FakeClient.last_post_json = k.get("json")
        _FakeClient.posts.append((url, k.get("json")))
        for frag, rows in _FakeClient.post_rows_by_url.items():
            if frag in url:
                return _FakeResp(rows)
        return _FakeResp([])


@pytest.fixture
def fake_http(monkeypatch):
    _FakeClient.rows, _FakeClient.last_get_params, _FakeClient.last_post_json = [], None, None
    _FakeClient.posts, _FakeClient.post_rows_by_url = [], {}
    monkeypatch.setattr(retriever.httpx, "Client", _FakeClient)
    return _FakeClient


def test_flag_default_off():
    assert os.getenv("ENUNCIADOS_MULTIVECTOR", "off") == "off"
    assert retriever._multivector_on() is False


# ---------- invariante de no-servicio ----------

def test_no_surrogates_inyecta_filtro_en_chunks_v2(monkeypatch):
    monkeypatch.setattr(retriever, "CHUNKS_TABLE", "chunks_v2")
    p = retriever._no_surrogates({"select": "id"})
    assert p["parent_id"] == "is.null"


def test_no_surrogates_inerte_en_tabla_legacy(monkeypatch):
    monkeypatch.setattr(retriever, "CHUNKS_TABLE", "chunks")
    p = retriever._no_surrogates({"select": "id"})
    assert "parent_id" not in p           # la tabla legacy no tiene la columna


def test_keyword_search_lleva_el_filtro(fake_http, monkeypatch):
    monkeypatch.setattr(retriever, "CHUNKS_TABLE", "chunks_v2")
    retriever.keyword_search("ZX2e", limit=3)
    assert fake_http.last_get_params.get("parent_id") == "is.null"


def test_rpc_sin_flag_una_sola_llamada(fake_http, monkeypatch):
    monkeypatch.delenv("ENUNCIADOS_MULTIVECTOR", raising=False)
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4)
    assert len(fake_http.posts) == 1
    assert "match_chunks_v2_enunciados" not in fake_http.posts[0][0]


def test_rpc_con_flag_llama_al_canal_enunciados(fake_http, monkeypatch):
    """(s95 [D2]) flag on + _v2 → 2ª llamada al RPC de la tabla SEPARADA con los
    MISMOS threshold/count pineados (nunca include_surrogates: DEC-088)."""
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")
    retriever.vector_search("query", 5, 0.3, "ADW535", None, [0.0] * 4)
    assert len(fake_http.posts) == 2
    url2, json2 = fake_http.posts[1]
    assert "match_chunks_v2_enunciados" in url2
    assert json2["match_threshold"] == 0.3
    # (A3 Dense-X) se piden ENUNCIADOS_FETCH_K unidades (colapsan a padres únicos)
    assert json2["match_count"] == retriever.ENUNCIADOS_FETCH_K
    # (012) paridad de canal: el filtro de producto viaja también al canal enunciados
    assert json2["filter_product"] == "ADW535"
    assert all("include_surrogates" not in (j or {}) for _, j in fake_http.posts)


def test_colapso_por_padre_antes_de_fusionar(fake_http, monkeypatch):
    """(A3 Dense-X) 2 surrogates del MISMO padre → colapsan keep-max ANTES del cap:
    no desperdician slots (post-swap serían el mismo padre igualmente)."""
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")
    fake_http.post_rows_by_url = {
        "match_chunks_v2_enunciados": [{"id": "e1", "parent_id": "p1", "similarity": 0.9},
                                       {"id": "e1b", "parent_id": "p1", "similarity": 0.85},
                                       {"id": "e2", "parent_id": "p2", "similarity": 0.6}],
        "match_chunks_v2": [{"id": "r1", "similarity": 0.8}],
    }
    out = retriever.vector_search("query", 3, 0.3, None, None, [0.0] * 4)
    # e1b (mismo padre que e1, menor sim) colapsa → entra e2 en su lugar
    assert [c["id"] for c in out] == ["e1", "r1", "e2"]


def test_fusion_pineada_union_sort_cap(fake_http, monkeypatch):
    """(s95 [D2]) unión → sort similarity desc → cap top_k: un solo ranking con el
    mismo cap que T1 (misma semántica de competición, sin el artefacto de índice)."""
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")
    fake_http.post_rows_by_url = {
        "match_chunks_v2_enunciados": [{"id": "e1", "parent_id": "p1", "similarity": 0.9},
                                       {"id": "e2", "parent_id": "p2", "similarity": 0.5}],
        "match_chunks_v2": [{"id": "r1", "similarity": 0.8},
                            {"id": "r2", "similarity": 0.7}],
    }
    out = retriever.vector_search("query", 3, 0.3, None, None, [0.0] * 4)
    assert [c["id"] for c in out] == ["e1", "r1", "r2"]     # e2 (0.5) cae por el cap


# ---------- swap from-row ----------

def test_swap_sustituye_y_conserva_similarity(fake_http):
    fake_http.rows = [{"id": "p1", "content": "tabla fuente", "product_model": "ZX2e",
                       "parent_id": None}]
    out = retriever._enunciados_swap(
        [{"id": "s1", "parent_id": "p1", "similarity": 0.77, "_channel": "VECTOR"},
         {"id": "normal", "similarity": 0.5}])
    assert [c["id"] for c in out] == ["p1", "normal"]
    assert out[0]["similarity"] == 0.77                  # presencia, score del surrogate
    assert out[0]["_swapped_from_surrogate"] == "s1"
    assert out[0]["product_model"] == "ZX2e"             # hidratado


def test_swap_keep_max(fake_http):
    fake_http.rows = [{"id": "p1", "content": "t", "parent_id": None}]
    out = retriever._enunciados_swap(
        [{"id": "s1", "parent_id": "p1", "similarity": 0.60},
         {"id": "s2", "parent_id": "p1", "similarity": 0.82}])
    assert len(out) == 1 and out[0]["id"] == "p1" and out[0]["similarity"] == 0.82


def test_swap_fail_closed_padre_no_hidratable(fake_http):
    fake_http.rows = []                                   # el fetch no devuelve el padre
    out = retriever._enunciados_swap(
        [{"id": "s1", "parent_id": "p-missing", "similarity": 0.9},
         {"id": "n1", "similarity": 0.4}])
    assert [c["id"] for c in out] == ["n1"]               # surrogate FUERA


def test_swap_noop_sin_surrogates(fake_http):
    chunks = [{"id": "a", "similarity": 0.6}, {"id": "b", "parent_id": None}]
    assert retriever._enunciados_swap(chunks) == chunks


# ---------- H8 (dúo T0): huecos de cobertura ----------

def test_content_search_path_a_lleva_el_filtro(fake_http, monkeypatch):
    monkeypatch.setattr(retriever, "CHUNKS_TABLE", "chunks_v2")
    retriever.content_search("relé de avería", product_model="ZX2e", limit=5)
    assert fake_http.last_get_params.get("parent_id") == "is.null"


def test_rpc_legacy_suffix_sin_canal_enunciados_ni_con_flag(fake_http, monkeypatch):
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "")          # tabla legacy
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4)
    assert len(fake_http.posts) == 1
    assert "include_surrogates" not in fake_http.last_post_json


def test_fetch_missing_doc_chunks_excluye_surrogates_textual():
    """(H3/CRÍTICO cross-model) El path IDENTITY_FETCH appendea sin swap → su GET debe
    excluir surrogates INCONDICIONALMENTE. Test textual del invariante en el código."""
    import inspect
    import src.rag.catalog_resolver as cr
    src = inspect.getsource(cr.fetch_missing_doc_chunks)
    assert '"parent_id": "is.null"' in src


def test_swap_corre_antes_del_trace_de_canales():
    """(H8) El swap debe ser PRE-merge y PRE-trace: si corriera después, los surrogates
    morirían en filtros o la famtie no acreditaría (dúo s94 H6)."""
    import inspect
    src = inspect.getsource(retriever.retrieve_chunks)
    i_swap = src.index("_enunciados_swap")
    i_trace = src.index('_tr("channels"')
    i_merge = src.index("_merge_channels(")
    assert i_swap < i_trace < i_merge


# ---------- s96 dúo: H1 fail-open propio + H3 parser estricto ----------

def test_flag_valores_truthy_y_fail_fast(monkeypatch):
    """(H3) 'true'/'1' NO pueden ser OFF silencioso; typo → error (espejo fetch_mode)."""
    for raw, esperado in [("on", True), ("true", True), ("1", True), ("yes", True),
                          ("off", False), ("", False), ("0", False)]:
        monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", raw)
        assert retriever._multivector_on() is esperado, raw
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "onn")
    import pytest as _pt
    with _pt.raises(RuntimeError):
        retriever._multivector_on()


def test_fallo_del_rpc_enunciados_no_mata_el_canal_real(fake_http, monkeypatch):
    """(H1 CRÍTICO) hiccup del RPC de enunciados → fail-open a solo-reales; el canal
    vectorial NO puede caer por la tabla nueva."""
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")

    class _Boom:
        status_code = 500
        def raise_for_status(self):
            raise RuntimeError("supabase hiccup")
        def json(self): return []

    real_post = fake_http.post
    def post(self, url="", *a, **k):
        if "match_chunks_v2_enunciados" in url:
            _FakeClient.posts.append((url, k.get("json")))
            return _Boom()
        return real_post(self, url, *a, **k)
    monkeypatch.setattr(_FakeClient, "post", post)
    fake_http.post_rows_by_url = {"match_chunks_v2": [{"id": "r1", "similarity": 0.8}]}
    out = retriever.vector_search("query", 3, 0.3, None, None, [0.0] * 4)
    assert [c["id"] for c in out] == ["r1"]        # los reales sobreviven
