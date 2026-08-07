"""s306 — el fail-open de canal deja de ser invisible (TECH_DEBT #63).

Origen: en la sonda s303 un 500 transitorio del RPC de enunciados bajó el pool de
34 a 23 chunks (−32%) sin que ningún log ni métrica lo registrara. El mismo turno,
repetido, dio 34. El bot habría respondido con un tercio menos de evidencia y nadie
lo sabría.

Contratos que fija este fichero, por capa:
  · retriever — los fail-opens INTERIORES (enunciados / hyq) registran en el mismo
    seam `_trace` que el canal VECTOR (s289); el serving NO cambia (fail-open
    intacto). Reintento ÚNICO ante 5xx del RPC de enunciados — y SOLO ante 5xx:
    un 4xx es error de la petición (repetirla no lo arregla) y un timeout ya pagó
    la espera (repetirlo la duplicaría en el turno malo).
  · serving_pipeline — pasa el seam por FIRMA (no por try/TypeError: reintenta
    re-corriendo el retrieval entero para enmascarar un bug genuino); los fakes
    sin `_trace` siguen funcionando y simplemente no reportan salud.
  · runtime_trace — sección `retrieval` REQUERIDA con tokens de allowlist; el
    `repr` del error (URL/payload) jamás cruza al trace persistido. «Sin medida»
    y «sin fallos» son distinguibles — la confusión entre ambas ERA el defecto.
"""
from __future__ import annotations

import httpx
import pytest

import src.rag.retriever as retriever
from src.orchestrator import from_production  # noqa: F401  (import sanity)
from src.rag.runtime_trace import (
    build_rag_serving_trace,
    validate_rag_serving_trace,
)
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn


# ---------------------------------------------------------------- fakes http


class _Resp:
    def __init__(self, rows=None, status=200):
        self._rows = rows or []
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=None, response=None
            )

    def json(self):
        return self._rows


class _Cliente:
    """Cliente falso: respuestas por-URL programables como COLA (FIFO), para
    poder simular «500 y luego 200» — el fallo transitorio real de s303."""

    colas: dict = {}          # substring de URL → lista de _Resp (se consume)
    posts: list = []          # [(url, json), ...]

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        return _Resp([])

    def post(self, url="", *a, **k):
        _Cliente.posts.append((url, k.get("json")))
        for frag, cola in _Cliente.colas.items():
            if frag in url:
                return cola.pop(0) if len(cola) > 1 else cola[0]
        return _Resp([])


@pytest.fixture
def http_falso(monkeypatch):
    _Cliente.colas, _Cliente.posts = {}, []
    monkeypatch.setattr(retriever.httpx, "Client", _Cliente)
    return _Cliente


@pytest.fixture
def canal_enunciados_on(monkeypatch):
    monkeypatch.setenv("ENUNCIADOS_MULTIVECTOR", "on")
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")


def _posts_enunciados():
    return [u for u, _ in _Cliente.posts if "match_chunks_v2_enunciados" in u]


# ------------------------------------------------- retriever: registro + retry


def test_enunciados_fail_open_registra_y_sirve(http_falso, canal_enunciados_on):
    """El defecto original: el canal cae, el serving sigue (fail-open intacto),
    pero AHORA queda registro con canal y tipo — no solo un WARNING volátil."""
    http_falso.colas = {"match_chunks_v2_enunciados": [_Resp(status=500)]}
    trace: dict = {}
    out = retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4,
                                  _trace=trace)
    assert out == []                                  # canal real vacío en el fake
    assert len(trace["channel_failures"]) == 1
    fallo = trace["channel_failures"][0]
    assert fallo["channel"] == "ENUNCIADOS"
    assert fallo["error_type"] == "HTTPStatusError"
    assert "error" in fallo                           # repr en proceso, para depurar


def test_500_transitorio_se_reintenta_una_vez_y_no_cuenta_como_fallo(
    http_falso, canal_enunciados_on
):
    """El caso EXACTO de s303: 500 y, al repetir, 200. Con el reintento el turno
    es SANO — ni fail-open ni registro — y el RPC se llamó exactamente 2 veces."""
    http_falso.colas = {"match_chunks_v2_enunciados": [_Resp(status=500), _Resp([])]}
    trace: dict = {}
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4, _trace=trace)
    assert "channel_failures" not in trace
    assert len(_posts_enunciados()) == 2


def test_5xx_persistente_no_reintenta_una_tercera_vez(http_falso, canal_enunciados_on):
    http_falso.colas = {"match_chunks_v2_enunciados": [_Resp(status=503)]}
    trace: dict = {}
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4, _trace=trace)
    assert len(_posts_enunciados()) == 2              # el único reintento, no un bucle
    assert trace["channel_failures"][0]["channel"] == "ENUNCIADOS"


def test_4xx_no_se_reintenta(http_falso, canal_enunciados_on):
    """Un 400 es error de la petición: repetirla no lo arregla y escondería el
    bug real tras una segunda llamada idéntica."""
    http_falso.colas = {"match_chunks_v2_enunciados": [_Resp(status=400)]}
    trace: dict = {}
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4, _trace=trace)
    assert len(_posts_enunciados()) == 1
    assert trace["channel_failures"][0]["channel"] == "ENUNCIADOS"


def test_timeout_no_se_reintenta(http_falso, canal_enunciados_on):
    """El timeout ya pagó la espera entera; repetirlo duplicaría la latencia del
    turno malo. Se registra y se sigue."""
    class _ClienteTimeout(_Cliente):
        def post(self, url="", *a, **k):
            _Cliente.posts.append((url, k.get("json")))
            if "match_chunks_v2_enunciados" in url:
                raise httpx.ReadTimeout("lento")
            return _Resp([])

    import src.rag.retriever as r
    r.httpx.Client = _ClienteTimeout
    trace: dict = {}
    retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4, _trace=trace)
    assert len(_posts_enunciados()) == 1
    assert trace["channel_failures"][0]["error_type"] == "ReadTimeout"


def test_hyq_table_fail_open_registra(http_falso, monkeypatch):
    monkeypatch.setattr(retriever, "HYQ_TABLE_ON", True)
    monkeypatch.setattr(retriever, "RPC_SUFFIX", "_v2")

    def _boom(*_a, **_k):
        raise RuntimeError("rpc hyq caido")

    monkeypatch.setattr(retriever, "_hyq_table_hits", _boom)
    trace: dict = {}
    out = retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4,
                                  _trace=trace)
    assert out == []                                  # fail-open intacto
    assert trace["channel_failures"] == [{
        "channel": "HYQ_TABLE", "error": "RuntimeError('rpc hyq caido')",
        "error_type": "RuntimeError",
    }]


def test_sin_trace_todo_sigue_igual(http_falso, canal_enunciados_on):
    """`_trace=None` (default, y TODOS los callers no-bot: harness, sondas,
    deep_lookup) => cero efecto. El seam es opt-in, jamás un peaje."""
    http_falso.colas = {"match_chunks_v2_enunciados": [_Resp(status=500)]}
    out = retriever.vector_search("query", 5, 0.3, None, None, [0.0] * 4)
    assert out == []


# ------------------------------------------- serving_pipeline: el seam por firma


def _turno(retrieve):
    return execute_rag_turn(
        query="q", query_for_retrieval="q",
        target_models=None, available_models=None,
        retrieval_top_k=5, rerank_top_k=2,
        adapters=RagServingAdapters(
            retrieve=retrieve,
            rerank=lambda _q, chunks, **_k: list(chunks),
            observe_structural_shadow=lambda _q, _c: None,
            generate=lambda _q, chunks, **_k: {"answer": "ok", "diagrams": []},
        ),
    )


def test_pipeline_pasa_el_seam_a_quien_lo_acepta():
    visto = {}

    def retrieve(_q, top_k=5, _trace=None):
        visto["trace"] = _trace
        _trace["channel_failures"] = [{"channel": "VECTOR", "error": "x",
                                       "error_type": "RuntimeError"}]
        return [{"id": "a", "content": "A"}]

    pipeline = _turno(retrieve)
    assert visto["trace"] is not None
    assert pipeline["retrieval_health"]["channel_failures"][0]["channel"] == "VECTOR"


def test_pipeline_tolera_fakes_sin_el_seam():
    """La razón de pasar por FIRMA: los adapters de test existentes no aceptan
    `_trace` y deben seguir funcionando sin cambios — salud vacía, no TypeError."""
    pipeline = _turno(lambda _q, top_k=5: [{"id": "a", "content": "A"}])
    assert pipeline["retrieval_health"] == {}


# --------------------------------------------------- runtime_trace: tokens, no repr


def _trace_con(health):
    return build_rag_serving_trace(
        coverage_trace=None,
        served_chunks=[],
        must_preserve_trace=None,
        must_preserve_outcome=None,
        release_policy={"profile": "off"},
        transport_parts=1,
        retrieval_health=health,
    )


def test_seccion_retrieval_persiste_tokens_y_jamas_el_repr():
    trace = _trace_con({"channel_failures": [
        {"channel": "ENUNCIADOS", "error_type": "HTTPStatusError",
         "error": "HTTPStatusError('https://xyz.supabase.co/rest/v1/rpc/...')"},
    ]})
    assert trace["retrieval"] == {"channel_failures": [
        {"channel": "ENUNCIADOS", "error_type": "HTTPStatusError"},
    ]}
    assert "supabase" not in str(trace)               # el repr NUNCA cruza
    assert validate_rag_serving_trace(trace) is not None


def test_tokens_fuera_de_allowlist_degradan_a_desconocido():
    trace = _trace_con({"channel_failures": [
        {"channel": "CANAL_INVENTADO", "error_type": "ClaseRara"},
    ]})
    assert trace["retrieval"]["channel_failures"] == [
        {"channel": "unknown_channel", "error_type": "OtherError"},
    ]
    assert validate_rag_serving_trace(trace) is not None


def test_salud_es_lista_vacia_no_ausencia():
    """«Sin fallos» = lista vacía PRESENTE. La ausencia de la sección ya no
    valida — la confusión entre «sin datos» y «sano» era el defecto #63."""
    trace = _trace_con(None)
    assert trace["retrieval"] == {"channel_failures": []}
    assert validate_rag_serving_trace(trace) is not None

    sin_seccion = {k: v for k, v in trace.items() if k != "retrieval"}
    assert validate_rag_serving_trace(sin_seccion) is None


def test_validador_rechaza_shapes_ajenos():
    base = _trace_con(None)
    con_extra = dict(base)
    con_extra["retrieval"] = {"channel_failures": [], "prosa": "no"}
    assert validate_rag_serving_trace(con_extra) is None

    con_canal_libre = dict(base)
    con_canal_libre["retrieval"] = {"channel_failures": [
        {"channel": "LO_QUE_SEA", "error_type": "OtherError"},
    ]}
    assert validate_rag_serving_trace(con_canal_libre) is None


def test_lista_acotada_a_8():
    salud = {"channel_failures": [
        {"channel": "VECTOR", "error_type": "RuntimeError"} for _ in range(30)
    ]}
    trace = _trace_con(salud)
    assert len(trace["retrieval"]["channel_failures"]) == 8
    assert validate_rag_serving_trace(trace) is not None
