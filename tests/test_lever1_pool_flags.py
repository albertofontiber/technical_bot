"""s74 / Lever 1 — paridad de los flags del cluster de inanición del pool.

2a `LEVER1_BROAD_FALLBACK` y 2b `LEVER1_KEYWORD_ORDER`: default OFF → comportamiento
byte-idéntico al histórico (prod inerte). Mockean DB/LLM, no tocan red.
"""
import httpx

from src.rag import retriever as R


# ====================== 2b: keyword_search order + limit ======================

def _capture_keyword_params(monkeypatch):
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None, params=None):
            captured["params"] = params
            return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    return captured


def test_2b_keyword_default_inert(monkeypatch):
    captured = _capture_keyword_params(monkeypatch)
    monkeypatch.delenv("LEVER1_KEYWORD_ORDER", raising=False)
    R.keyword_search("CAD-150", limit=5)
    p = captured["params"]
    assert "order" not in p          # sin order → orden físico (comportamiento histórico)
    assert p["limit"] == "5"


def test_2b_keyword_flag_adds_order_and_raises_limit(monkeypatch):
    captured = _capture_keyword_params(monkeypatch)
    monkeypatch.setenv("LEVER1_KEYWORD_ORDER", "on")
    R.keyword_search("CAD-150", limit=5)
    p = captured["params"]
    assert p["order"] == "page_number.asc,id.asc"   # order determinista neutral (NO content_type)
    assert p["limit"] == "15"                         # limit subido para que el winner entre


# ============= broad-fallback REMOVED (s85, DEC-071) =============

def _run_retrieve_capturing_vector(monkeypatch):
    calls = []

    def fake_vector_search(query, limit, threshold, product_filter, category, embedding, **kw):
        calls.append({"limit": limit, "category": category})
        return []

    monkeypatch.setattr(R, "vector_search", fake_vector_search)
    monkeypatch.setattr(R, "embed_query", lambda *a, **k: [0.0] * 1024)
    monkeypatch.setattr(R, "generate_hypothetical_document", lambda q: q)
    monkeypatch.setattr(R, "keyword_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "content_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "diagram_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "typed_search", lambda *a, **k: [])
    # query con categoría ("detector") y SIN modelo. Antes disparaba el broad-fallback;
    # tras la limpieza s85 sólo corre el canal principal (a effective_top_k, category=None).
    R.retrieve_chunks("cómo funciona un detector", top_k=50)
    return calls


def test_broad_fallback_removed_single_vector_call(monkeypatch):
    """(s85, DEC-071) El broad-5 (workaround del canal muerto, DEC-040) está eliminado:
    una sola llamada vectorial (el canal principal), a effective_top_k y SIN filtro de
    categoría. El flag legacy LEVER1_BROAD_FALLBACK ya no existe."""
    calls = _run_retrieve_capturing_vector(monkeypatch)
    assert len(calls) == 1, f"se esperaba 1 sola llamada vectorial (sin broad-5); got {calls}"
    assert calls[0]["category"] is None, "el canal principal corre sin filtro de categoría"
    assert calls[0]["limit"] == 50, "el canal principal corre a effective_top_k (=top_k=50)"
