"""s84 — VECTOR_NOCAT: bypass del filtro de la columna `category` MUERTA (DEC-040).

default OFF → comportamiento histórico (el canal vectorial principal recibe la categoría
detectada, que devuelve 0 filas bajo stamps). ON → categoría=None (canal vivo). Mockea
vector/keyword/content (no toca red).
"""
from src.rag import retriever as R


def _run_capturing_category(monkeypatch, query):
    """Captura el `category_filter` pasado a CADA llamada de vector_search en retrieve_chunks."""
    cats = []

    def fake_vector_search(query, top_k, threshold, product_filter, category_filter, query_embedding):
        cats.append(category_filter)
        return []

    monkeypatch.setattr(R, "vector_search", fake_vector_search)
    monkeypatch.setattr(R, "embed_query", lambda *a, **k: [0.0] * 1024)
    monkeypatch.setattr(R, "keyword_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "content_search", lambda *a, **k: [])
    monkeypatch.setattr(R, "extract_product_models", lambda q: [])  # no-model → category-detection path
    R.retrieve_chunks(query, top_k=5)
    return cats


# Query sin modelo que DISPARA detección de categoría ('Detectores puntuales' vía 'detector').
_CATEGORY_QUERY = "el detector de humo da una alarma intermitente"


def test_nocat_default_off_passes_detected_category(monkeypatch):
    """OFF (histórico): el canal vectorial principal recibe la categoría detectada (no-None)."""
    monkeypatch.delenv("VECTOR_NOCAT", raising=False)
    cats = _run_capturing_category(monkeypatch, _CATEGORY_QUERY)
    assert any(c is not None for c in cats), (
        f"OFF: el canal principal debe recibir la categoría detectada; got {cats}")


def test_nocat_on_bypasses_dead_category(monkeypatch):
    """ON: ninguna llamada vectorial recibe la categoría muerta (todas None)."""
    monkeypatch.setenv("VECTOR_NOCAT", "1")
    cats = _run_capturing_category(monkeypatch, _CATEGORY_QUERY)
    assert cats, "se esperaba al menos una llamada vectorial"
    assert all(c is None for c in cats), (
        f"ON: el filtro de la columna muerta debe estar bypaseado (None); got {cats}")
