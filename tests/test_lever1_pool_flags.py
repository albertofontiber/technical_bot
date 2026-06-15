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


# ====================== 2a: broad-fallback limit ======================

def _run_retrieve_capturing_vector(monkeypatch):
    calls = []

    def fake_vector_search(query, limit, threshold, product_filter, category, embedding):
        calls.append({"limit": limit, "category": category})
        return []

    monkeypatch.setattr(R, "vector_search", fake_vector_search)
    monkeypatch.setattr(R, "embed_query", lambda *a, **k: [0.0] * 1024)
    monkeypatch.setattr(R, "generate_hypothetical_document", lambda q: q)
    monkeypatch.setattr(R, "keyword_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "content_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "diagram_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "typed_search", lambda *a, **k: [])
    # query con categoría ("detector") y SIN modelo → dispara el broad-fallback
    # (detected_category set, _li_sano False bajo stamps); effective_top_k = top_k (sin modelos).
    R.retrieve_chunks("cómo funciona un detector", top_k=50)
    return [c for c in calls if c["category"] is None]  # el broad corre sin categoría


def test_2a_broad_fallback_default_inert(monkeypatch):
    monkeypatch.delenv("LEVER1_BROAD_FALLBACK", raising=False)
    broad = _run_retrieve_capturing_vector(monkeypatch)
    assert broad and broad[0]["limit"] == 5     # capeado a 5 = comportamiento histórico


def test_2a_broad_fallback_flag_uses_effective_top_k(monkeypatch):
    monkeypatch.setenv("LEVER1_BROAD_FALLBACK", "on")
    broad = _run_retrieve_capturing_vector(monkeypatch)
    assert broad and broad[0]["limit"] == 50    # effective_top_k (=top_k=50, sin modelos)
