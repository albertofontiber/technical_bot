"""Tests del filtro de idioma en RETRIEVAL (retriever._filter_by_language).

Distinto de src/ingestion/language_filter.py (filtro en INGESTA, por página):
este descarta CHUNKS no-ES/EN en el momento del retrieval, para que un chunk en
idioma extranjero no desplace a uno servible ni contamine la respuesta
(política de idiomas, sesión 38; filtro diferido desde s30).
"""
from __future__ import annotations

from src.rag.retriever import _filter_by_language, _SERVED_LANGUAGES


def _c(cid, lang):
    return {"id": cid, "language": lang, "content": "x"}


def test_keeps_es_and_en():
    chunks = [_c(1, "es"), _c(2, "en")]
    assert _filter_by_language(chunks) == chunks


def test_drops_foreign_languages():
    chunks = [_c(1, "es"), _c(2, "fr"), _c(3, "de"), _c(4, "pt"), _c(5, "en")]
    kept = _filter_by_language(chunks)
    assert {c["language"] for c in kept} == {"es", "en"}
    assert len(kept) == 2


def test_keeps_unlabeled_chunks():
    # language NULL / ausente -> se conserva (no ocultar contenido sin etiqueta).
    chunks = [_c(1, "es"), _c(2, None), {"id": 3, "content": "x"}]
    assert len(_filter_by_language(chunks)) == 3


def test_case_insensitive():
    chunks = [_c(1, "ES"), _c(2, "En")]
    assert len(_filter_by_language(chunks)) == 2


def test_fail_open_when_all_foreign():
    # Un modelo documentado SOLO en PT -> filtrar deja vacío -> fail-open
    # devuelve los originales para que decida el generador (admit), no el retriever.
    chunks = [_c(1, "fr"), _c(2, "pt")]
    assert _filter_by_language(chunks) == chunks


def test_empty_input():
    assert _filter_by_language([]) == []


def test_served_languages_constant():
    assert _SERVED_LANGUAGES == {"es", "en"}
