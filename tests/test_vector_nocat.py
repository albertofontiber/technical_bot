"""s85 — el filtro de la columna `category` MUERTA (DEC-040) está QUITADO de forma
PERMANENTE del path de retrieval (DEC-071, limpieza de raíz de s85).

`chunks_v2.category` lleva muerta desde el SWAP s44 (0 filas canónicas) → filtrar por
ella devolvía 0 filas en el ~85% de queries y mataba el canal semántico en silencio. La
limpieza retira el filtro (antes flag `VECTOR_NOCAT` en s84, ahora permanente y sin flag):
ninguna llamada vectorial recibe ya la categoría detectada. La DETECCIÓN se conserva (para
catálogo/boost), pero NUNCA como filtro. Mockea vector/keyword/content (no toca red).
"""
from src.rag import retriever as R


def _run_capturing_category(monkeypatch, query):
    """Captura el `category_filter` pasado a CADA llamada de vector_search en retrieve_chunks."""
    cats = []

    def fake_vector_search(query, top_k, threshold, product_filter, category_filter, query_embedding, **kw):
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


def test_dead_category_filter_never_reaches_vector_channel(monkeypatch):
    """Permanente (s85): aunque la query dispare detección de categoría, ninguna llamada
    vectorial recibe la categoría muerta — el filtro está quitado de raíz."""
    cats = _run_capturing_category(monkeypatch, _CATEGORY_QUERY)
    assert cats, "se esperaba al menos una llamada vectorial"
    assert all(c is None for c in cats), (
        f"el filtro de la columna muerta debe estar fuera del path (None); got {cats}")


def test_dead_category_filter_off_is_not_reintroducible_by_env(monkeypatch):
    """El comportamiento ya no depende de ningún flag: setear VECTOR_NOCAT (legacy) no
    reintroduce el filtro — sigue siendo None en todas las llamadas."""
    monkeypatch.setenv("VECTOR_NOCAT", "")  # valor falsy del flag legacy
    cats = _run_capturing_category(monkeypatch, _CATEGORY_QUERY)
    assert cats and all(c is None for c in cats), (
        f"sin flag: el filtro muerto sigue fuera del path; got {cats}")
