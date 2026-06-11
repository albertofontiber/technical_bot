"""Regression tests del lever s59 (DEC-040): el retrieval NO filtra por category.

Contexto: chunks_v2.category no contiene la taxonomía canónica (0 filas; 58% NULL,
25% 'ES'-idioma) — todo filtro contra esa columna devolvía 0 filas y mataba el
canal vectorial principal en el 85% de las queries del eval. El lever elimina el
uso de category como criterio de retrieval (el filtro, NO la detección: las
constantes siguen exportadas para el bot/log).

Tests in-memory con monkeypatch; sin DB.
"""
import inspect

import pytest

import src.rag.retriever as retriever


def test_retrieve_chunks_signature_has_no_category_filter():
    """La firma pública ya no acepta category_filter (nadie lo pasaba)."""
    params = inspect.signature(retriever.retrieve_chunks).parameters
    assert "category_filter" not in params


def test_content_search_signature_has_no_category():
    """content_search ya no acepta category (filtro contra columna rota)."""
    params = inspect.signature(retriever.content_search).parameters
    assert "category" not in params


def test_vector_search_never_called_with_category(monkeypatch):
    """retrieve_chunks no pasa categoría al RPC vectorial — query que ANTES
    detectaba 'Centrales de incendios' ('central') y recibía 0 filas."""
    calls = []

    def fake_vector_search(query, top_k=50, threshold=0.3, product_filter=None,
                           category_filter=None, precomputed_embedding=None):
        calls.append({"category_filter": category_filter, "top_k": top_k})
        return [{"id": f"v{i}", "content": "x", "similarity": 0.5,
                 "source_file": "doc-a", "product_model": "PEARL"} for i in range(3)]

    monkeypatch.setattr(retriever, "vector_search", fake_vector_search)
    monkeypatch.setattr(retriever, "embed_query", lambda q: [0.0] * 4)
    monkeypatch.setattr(retriever, "keyword_search", lambda m, limit=5: [])
    monkeypatch.setattr(retriever, "content_search",
                        lambda term, limit=5, product_model=None: [])
    monkeypatch.setattr(retriever, "diagram_search",
                        lambda m, content_type=None, limit=3: [])
    monkeypatch.setattr(retriever, "_filter_by_document_status", lambda c: c)
    monkeypatch.setattr(retriever, "_get_source_files_for_model", lambda m: [])

    retriever.retrieve_chunks("¿cuántos equipos admite un lazo de la central PEARL?")

    assert calls, "el canal vectorial debe ejecutarse"
    assert all(c["category_filter"] is None for c in calls), \
        f"el RPC vectorial recibió categoría: {calls}"


def test_no_model_query_runs_no_category_search_tasks(monkeypatch):
    """Query sin modelo con categoría detectable ('sirena'): las antiguas
    search_tasks 3c-i (synonym/keyword + category, boosts 0.80-0.85) ya no
    existen; solo queda la task PCI_TERMS (boost 0.70)."""
    content_calls = []

    def fake_content_search(term, limit=5, product_model=None):
        content_calls.append({"term": term, "product_model": product_model})
        return [{"id": f"c-{term}", "content": "x", "similarity": 0.0,
                 "source_file": "doc-a", "product_model": None}]

    monkeypatch.setattr(retriever, "content_search", fake_content_search)
    monkeypatch.setattr(retriever, "embed_query", lambda q: [0.0] * 4)
    monkeypatch.setattr(retriever, "vector_search",
                        lambda *a, **k: [])
    monkeypatch.setattr(retriever, "_filter_by_document_status", lambda c: c)
    monkeypatch.setattr(retriever, "_diversify_by_manufacturer",
                        lambda chunks, top_k, q="", precomputed_embedding=None: chunks)

    result = retriever.retrieve_chunks(
        "¿qué problemas dan las sirenas con error de batería en general?")

    # Solo la búsqueda PCI_TERMS (genérica, sin product_model) debe correr.
    assert len(content_calls) == 1, content_calls
    assert content_calls[0]["product_model"] is None
    # Y su boost es el genérico 0.70 (no los 0.80/0.85 de las tasks muertas).
    assert all(c.get("similarity") == 0.70 for c in result if str(c.get("id", "")).startswith("c-"))


def test_fts_payload_filter_category_always_none(monkeypatch):
    """El payload del RPC search_chunks_text lleva filter_category=None SIEMPRE."""
    captured = {}

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return []

        @staticmethod
        def raise_for_status():
            return None

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            captured["payload"] = json
            return FakeResp()

        def get(self, url, headers=None, params=None):
            captured["get_params"] = params
            return FakeResp()

    monkeypatch.setattr(retriever.httpx, "Client", FakeClient)
    retriever.content_search("sirena", limit=5)

    assert captured["payload"]["filter_category"] is None
