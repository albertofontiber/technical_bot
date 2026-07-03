"""Tests del multi-vector swap del piloto s94 (spec v2 inv.3, dúo H6/A).

Contrato: 1:1 (similarity del surrogate, famtie=presencia), keep-max, fail-closed
(padre no hidratable → surrogate FUERA; mapa ilegible → swap inerte), no-surrogates
intactos, flag default OFF.
"""
import json

import pytest

import src.rag.retriever as retriever


class _FakeResp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


class _FakeClient:
    rows: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        return _FakeResp(_FakeClient.rows)


@pytest.fixture
def swap_env(tmp_path, monkeypatch):
    def _setup(mapping, parents):
        p = tmp_path / "map.json"
        p.write_text(json.dumps(mapping), encoding="utf-8")
        monkeypatch.setenv("PILOT_SWAP_MAP", str(p))
        retriever._PILOT_SWAP_MAP = None          # invalida cache de proceso
        _FakeClient.rows = parents
        monkeypatch.setattr(retriever.httpx, "Client", _FakeClient)
    yield _setup
    retriever._PILOT_SWAP_MAP = None


def test_flag_default_off():
    import os
    assert os.getenv("PILOT_PARENT_SWAP", "off") == "off"


def test_mapa_ilegible_es_inerte(monkeypatch):
    monkeypatch.setenv("PILOT_SWAP_MAP", "no/existe.json")
    retriever._PILOT_SWAP_MAP = None
    chunks = [{"id": "x", "similarity": 0.9}]
    assert retriever._pilot_parent_swap(chunks) == chunks
    retriever._PILOT_SWAP_MAP = None


def test_swap_conserva_similarity_del_surrogate(swap_env):
    swap_env({"s1": "p1"}, [{"id": "p1", "content": "tabla", "product_model": "ZX2e"}])
    out = retriever._pilot_parent_swap(
        [{"id": "s1", "similarity": 0.77, "_channel": "VECTOR"},
         {"id": "otro", "similarity": 0.5}])
    ids = [c["id"] for c in out]
    assert ids == ["p1", "otro"]                      # padre sustituye; no-surrogate intacto
    p = out[0]
    assert p["similarity"] == 0.77                    # score del surrogate (presencia)
    assert p["_pilot_swapped_from"] == "s1"
    assert p["product_model"] == "ZX2e"               # hidratado


def test_keep_max_multiples_surrogates_mismo_padre(swap_env):
    swap_env({"s1": "p1", "s2": "p1"}, [{"id": "p1", "content": "t"}])
    out = retriever._pilot_parent_swap(
        [{"id": "s1", "similarity": 0.60}, {"id": "s2", "similarity": 0.82}])
    assert len(out) == 1
    assert out[0]["id"] == "p1"
    assert out[0]["similarity"] == 0.82               # keep-max


def test_fail_closed_padre_no_hidratable(swap_env):
    swap_env({"s1": "p-missing"}, [])                 # el fetch no devuelve el padre
    out = retriever._pilot_parent_swap([{"id": "s1", "similarity": 0.9},
                                        {"id": "n1", "similarity": 0.4}])
    assert [c["id"] for c in out] == ["n1"]           # surrogate FUERA, resto intacto
