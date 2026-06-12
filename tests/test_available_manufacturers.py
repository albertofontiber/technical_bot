"""get_available_manufacturers debe PAGINAR documents (fix s65).

PostgREST capa la respuesta a max-rows=1000 aunque `limit` pida más (lección
s64, re-cazada en el smoke s65: con 1.170 docs, Aritech/Kidde/Edwards —
insertadas por el backfill al final de la tabla— desaparecían del catálogo
"Tengo manuales de:"). El test simula el cap y exige que la función junte
todas las páginas.
"""
from __future__ import annotations

import httpx

from src.rag import retriever


class _FakeResponse:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        return None

    def json(self):
        return self._rows


class _FakeClient:
    """Simula el cap server-side: nunca devuelve más de 1000 filas por GET."""

    def __init__(self, all_rows):
        self._all = all_rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, headers=None, params=None):
        offset = int(params.get("offset", "0"))
        limit = min(int(params.get("limit", "1000")), 1000)  # el cap
        return _FakeResponse(self._all[offset:offset + limit])


def test_pagina_mas_alla_del_cap_de_1000(monkeypatch):
    rows = [{"manufacturer": "Notifier"}] * 1000 + [{"manufacturer": "Aritech"},
                                                    {"manufacturer": "Kidde"}]
    monkeypatch.setattr(httpx, "Client", lambda timeout: _FakeClient(rows))
    out = retriever.get_available_manufacturers()
    assert "Aritech" in out and "Kidde" in out and "Notifier" in out


def test_filtra_unknown_y_null(monkeypatch):
    rows = [{"manufacturer": "Detnov"}, {"manufacturer": "unknown"},
            {"manufacturer": None}, {}]
    monkeypatch.setattr(httpx, "Client", lambda timeout: _FakeClient(rows))
    assert retriever.get_available_manufacturers() == ["Detnov"]
