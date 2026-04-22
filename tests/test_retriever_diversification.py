"""Regression tests for Sprint 3+4 retriever fixes (commit a6a45c3).

Covers:
- `_filter_to_query_models` — cross-product and cross-brand filter
- `_diversify_by_source_file` — multi-doc representation via round-robin

These tests use only in-memory chunk dicts + mocked corpus helpers; no DB
access. The DB-dependent helpers (`_get_source_files_for_model`,
`_fetch_top_chunks_by_source_file`) are patched to isolate unit logic.
"""
import pytest

from src.rag.retriever import (
    _filter_to_query_models,
    _diversify_by_source_file,
)


# ============================================================================
# _filter_to_query_models — cross-product + cross-brand filter
# ============================================================================


def test_filter_cross_product_same_brand():
    """CAD-150 query must drop CAD-250 chunks (both Detnov, different product)."""
    chunks = [
        {"id": "1", "product_model": "CAD-150-8", "similarity": 0.8},
        {"id": "2", "product_model": "CAD-250", "similarity": 0.9},
        {"id": "3", "product_model": "CAD-150-8", "similarity": 0.7},
        {"id": "4", "product_model": "CAD-150-8", "similarity": 0.6},
    ]
    result = _filter_to_query_models(chunks, ["CAD-150"])
    assert [c["id"] for c in result] == ["1", "3", "4"]


def test_filter_cross_brand():
    """ASD535 query must drop MINILÁSER 25 chunks (Notifier, different brand)."""
    chunks = [
        {"id": "1", "product_model": "ASD535", "similarity": 0.8},
        {"id": "2", "product_model": "MINILÁSER25", "similarity": 0.85},
        {"id": "3", "product_model": "ASD535", "similarity": 0.7},
        {"id": "4", "product_model": "ASD535", "similarity": 0.6},
    ]
    result = _filter_to_query_models(chunks, ["ASD535"])
    assert [c["id"] for c in result] == ["1", "3", "4"]


def test_filter_no_models_returns_all():
    """No models detected in query → no filtering, return originals."""
    chunks = [
        {"id": "1", "product_model": "CAD-150-8"},
        {"id": "2", "product_model": "CAD-250"},
    ]
    result = _filter_to_query_models(chunks, [])
    assert result == chunks


def test_filter_empty_chunks():
    """Empty input → empty output, no error."""
    assert _filter_to_query_models([], ["CAD-150"]) == []


def test_filter_fail_open_when_too_few():
    """If filter would leave < 3 chunks, return originals (better noisy than empty)."""
    chunks = [
        {"id": "1", "product_model": "CAD-150-8"},
        {"id": "2", "product_model": "CAD-250"},  # would be filtered out
        {"id": "3", "product_model": "CAD-250"},  # would be filtered out
    ]
    result = _filter_to_query_models(chunks, ["CAD-150"])
    # Fail-open: only 1 matches, <3 threshold, so return all
    assert [c["id"] for c in result] == ["1", "2", "3"]


def test_filter_multi_model_query():
    """Query mentioning 2 products keeps chunks matching either."""
    chunks = [
        {"id": "1", "product_model": "CAD-150-8"},
        {"id": "2", "product_model": "ID3000"},
        {"id": "3", "product_model": "CAD-250"},  # not mentioned → filtered
        {"id": "4", "product_model": "CAD-150-8"},
        {"id": "5", "product_model": "ID3000"},
    ]
    result = _filter_to_query_models(chunks, ["CAD-150", "ID3000"])
    assert [c["id"] for c in result] == ["1", "2", "4", "5"]


def test_filter_normalizes_separators():
    """AFP1010 query should match stored 'AM2020/AFP1010' and 'AFP-1010'."""
    chunks = [
        {"id": "1", "product_model": "AM2020/AFP1010"},
        {"id": "2", "product_model": "AFP-1010"},
        {"id": "3", "product_model": "ID3000"},  # not mentioned → filtered
        {"id": "4", "product_model": "AM2020/AFP1010"},
    ]
    result = _filter_to_query_models(chunks, ["AFP1010"])
    assert [c["id"] for c in result] == ["1", "2", "4"]


def test_filter_missing_product_model_dropped():
    """Chunks with empty/missing product_model don't match any query → filtered."""
    chunks = [
        {"id": "1", "product_model": "CAD-150-8"},
        {"id": "2", "product_model": ""},
        {"id": "3", "product_model": None},
        {"id": "4", "product_model": "CAD-150-8"},
        {"id": "5", "product_model": "CAD-150-8"},
    ]
    result = _filter_to_query_models(chunks, ["CAD-150"])
    assert [c["id"] for c in result] == ["1", "4", "5"]


def test_filter_case_insensitive():
    """Model matching ignores case (cad-150 matches CAD-150-8)."""
    chunks = [
        {"id": "1", "product_model": "cad-150-8"},
        {"id": "2", "product_model": "CAD-250"},
        {"id": "3", "product_model": "CAD-150-8"},
        {"id": "4", "product_model": "cad150-8"},
    ]
    result = _filter_to_query_models(chunks, ["CAD-150"])
    assert [c["id"] for c in result] == ["1", "3", "4"]


# ============================================================================
# _diversify_by_source_file — round-robin multi-doc representation
# ============================================================================


@pytest.fixture
def mock_corpus(monkeypatch):
    """Patch corpus-dependent helpers with in-memory stubs."""
    def _sources(model):
        db = {
            "CAD-150": ["CAD-150-Usuario", "CAD-150-Instalacion"],
            "CAD-250": ["CAD-250-MC-380", "CAD-250-Usuario", "CAD-250-Instalacion"],
            "ID3000": ["MPDT190", "MFDT190", "MCDT191"],
            "DGD-600": ["DGD-600-only"],  # single-doc product
        }
        return db.get(model, [])

    supplementary_pool: dict[str, list[dict]] = {}

    def _fetch(sf, query, limit=2):
        # return canned chunks for the requested source_file
        return supplementary_pool.get(sf, [])

    monkeypatch.setattr(
        "src.rag.retriever._get_source_files_for_model", _sources
    )
    monkeypatch.setattr(
        "src.rag.retriever._fetch_top_chunks_by_source_file", _fetch
    )
    return supplementary_pool


def test_diversify_single_doc_product_no_op(mock_corpus):
    """Products with only 1 source_file → no diversification, return as-is."""
    chunks = [
        {"id": "1", "source_file": "DGD-600-only", "similarity": 0.8},
        {"id": "2", "source_file": "DGD-600-only", "similarity": 0.7},
    ]
    result = _diversify_by_source_file(chunks, top_k=5, models=["DGD-600"], original_query="?")
    assert result == chunks


def test_diversify_fetches_missing_source(mock_corpus):
    """If a source_file exists in corpus but NOT in chunks, fetch supplementary."""
    # Initial: only Usuario. Missing: Instalacion.
    chunks = [
        {"id": "u1", "source_file": "CAD-150-Usuario", "similarity": 0.9},
        {"id": "u2", "source_file": "CAD-150-Usuario", "similarity": 0.8},
        {"id": "u3", "source_file": "CAD-150-Usuario", "similarity": 0.7},
        {"id": "u4", "source_file": "CAD-150-Usuario", "similarity": 0.65},
    ]
    mock_corpus["CAD-150-Instalacion"] = [
        {"id": "i1", "source_file": "CAD-150-Instalacion"},
        {"id": "i2", "source_file": "CAD-150-Instalacion"},
    ]
    result = _diversify_by_source_file(chunks, top_k=5, models=["CAD-150"], original_query="baterías")
    sources = {c["source_file"] for c in result}
    assert "CAD-150-Instalacion" in sources
    assert "CAD-150-Usuario" in sources


def test_diversify_round_robin_caps_single_source(mock_corpus):
    """Round-robin caps per-source to avoid a single doc monopolizing top_k."""
    # 10 chunks all from Usuario with high similarity
    chunks = [
        {"id": f"u{i}", "source_file": "CAD-150-Usuario", "similarity": 0.95 - i*0.01}
        for i in range(10)
    ]
    mock_corpus["CAD-150-Instalacion"] = [
        {"id": "i1", "source_file": "CAD-150-Instalacion"},
        {"id": "i2", "source_file": "CAD-150-Instalacion"},
    ]
    result = _diversify_by_source_file(chunks, top_k=8, models=["CAD-150"], original_query="?")

    src_counts = {}
    for c in result:
        src_counts[c["source_file"]] = src_counts.get(c["source_file"], 0) + 1
    # Usuario must not monopolize (max_per_source = top_k // 3 = 2, relaxed to fill)
    # Critical: Instalacion must be represented
    assert src_counts.get("CAD-150-Instalacion", 0) >= 1
    assert src_counts.get("CAD-150-Usuario", 0) < 8  # capped


def test_diversify_multi_model_query(mock_corpus):
    """Query mentioning 2 products should seek representation from both."""
    chunks = [
        {"id": "c1", "source_file": "CAD-150-Usuario", "similarity": 0.9},
        {"id": "c2", "source_file": "CAD-150-Usuario", "similarity": 0.85},
        {"id": "i1", "source_file": "MPDT190", "similarity": 0.8},
    ]
    mock_corpus["CAD-150-Instalacion"] = [
        {"id": "ci", "source_file": "CAD-150-Instalacion"},
    ]
    mock_corpus["MFDT190"] = [
        {"id": "mf", "source_file": "MFDT190"},
    ]
    result = _diversify_by_source_file(
        chunks, top_k=6, models=["CAD-150", "ID3000"], original_query="?"
    )
    sources = {c["source_file"] for c in result}
    # Should surface docs from BOTH products
    assert "CAD-150-Usuario" in sources or "CAD-150-Instalacion" in sources
    assert "MPDT190" in sources or "MFDT190" in sources


def test_diversify_no_op_when_all_sources_represented(mock_corpus):
    """If current chunks already cover every corpus source, no supplementary fetch."""
    chunks = [
        {"id": "u1", "source_file": "CAD-150-Usuario", "similarity": 0.9},
        {"id": "i1", "source_file": "CAD-150-Instalacion", "similarity": 0.8},
    ]
    # If supplementary was called, the pool is empty → would add nothing.
    # The no-op assertion is indirect: result should contain exactly these 2 ids.
    result = _diversify_by_source_file(chunks, top_k=5, models=["CAD-150"], original_query="?")
    result_ids = {c["id"] for c in result}
    assert result_ids == {"u1", "i1"}


def test_diversify_empty_input_returns_empty():
    """No chunks → no processing, return empty."""
    assert _diversify_by_source_file([], top_k=5, models=["CAD-150"], original_query="?") == []


def test_diversify_no_models_returns_unchanged(mock_corpus):
    """No detected models → no diversification, return chunks as-is."""
    chunks = [
        {"id": "1", "source_file": "X", "similarity": 0.8},
        {"id": "2", "source_file": "Y", "similarity": 0.7},
    ]
    result = _diversify_by_source_file(chunks, top_k=5, models=[], original_query="?")
    assert result == chunks
