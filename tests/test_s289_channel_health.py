"""s289 — observabilidad de canales del retriever (DEC-167(c)).

El fail-open del canal VECTOR principal era el ÚNICO silencioso del retriever
(un vector muerto se veía como "pool pequeño"). Contratos:
  - fail-open intacto (serving idéntico: sigue devolviendo los canales keyword);
  - AHORA deja log WARNING + entrada en `_trace["channel_failures"]`;
  - `_trace["channel_health"]` = filas aportadas por canal pre-fusión;
  - `_trace=None` (default, prod) => cero efecto (seam inerte s85).
"""
from __future__ import annotations

import logging

import src.rag.retriever as retriever


def _mk(row_id: str, sim: float = 0.8) -> dict:
    return {"id": row_id, "content": f"contenido {row_id}", "similarity": sim,
            "source_file": "manual", "product_model": "X"}


def _patch_pipeline(monkeypatch, *, vector, keyword_rows):
    monkeypatch.setattr(retriever, "HYDE_ENABLED", False)
    monkeypatch.setattr(retriever, "embed_query", lambda _q: [0.0] * 8)
    monkeypatch.setattr(retriever, "extract_product_models", lambda _q: [])
    monkeypatch.setattr(retriever, "vector_search", vector)
    monkeypatch.setattr(retriever, "keyword_search", lambda *a, **k: keyword_rows)
    monkeypatch.setattr(
        retriever, "_filter_by_document_status", lambda chunks: chunks
    )
    # Sin modelo detectado, el Step 5b fetchea fresco del corpus (REST) — en CI
    # no hay SUPABASE_URL y httpx revienta. Fuera del objeto de estos tests.
    monkeypatch.setattr(
        retriever, "_diversify_by_manufacturer", lambda chunks, *a, **k: chunks
    )


def test_vector_fail_open_logs_and_traces(monkeypatch, caplog):
    def _boom(*_a, **_k):
        raise RuntimeError("rpc caido")

    _patch_pipeline(monkeypatch, vector=_boom, keyword_rows=[])
    trace: dict = {}
    with caplog.at_level(logging.WARNING, logger=retriever.logger.name):
        out = retriever.retrieve_chunks("consulta generica", top_k=5, _trace=trace)
    assert out == []  # fail-open intacto: sin vector ni keyword, pool vacío
    assert trace["channel_failures"] == [
        {"channel": "VECTOR", "error": "RuntimeError('rpc caido')"}
    ]
    assert trace["channel_health"] == {}
    assert any("canal VECTOR fail-open" in r.message for r in caplog.records)


def test_vector_fail_open_without_trace_still_serves_and_logs(monkeypatch, caplog):
    def _boom(*_a, **_k):
        raise RuntimeError("rpc caido")

    _patch_pipeline(monkeypatch, vector=_boom, keyword_rows=[])
    with caplog.at_level(logging.WARNING, logger=retriever.logger.name):
        out = retriever.retrieve_chunks("consulta generica", top_k=5)
    assert out == []
    assert any("canal VECTOR fail-open" in r.message for r in caplog.records)


def test_channel_health_counts_rows_per_channel(monkeypatch):
    rows = [_mk("v1"), _mk("v2", 0.7)]
    _patch_pipeline(
        monkeypatch, vector=lambda *a, **k: rows, keyword_rows=[]
    )
    trace: dict = {}
    out = retriever.retrieve_chunks("consulta generica", top_k=5, _trace=trace)
    assert trace["channel_health"] == {"VECTOR": 2}
    assert "channel_failures" not in trace
    assert [c["id"] for c in out] == ["v1", "v2"]
