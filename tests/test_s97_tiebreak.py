"""s97 — tie-break semántico de empates en _diversify_by_source_file (pre-registro v2).

Contratos del dúo: clave-TUPLA (similarity JAMÁS mutada — H2), scope within-source
(source_order intocado — H6/C1), flag default off comportamiento idéntico, parser
estricto fail-fast, fail-open si el fetch de embeddings falla.
"""
import pytest

import src.rag.retriever as R


def _pool():
    # 2 fuentes; docA con 3 empatados a 0.80 (n1=aguja con mejor coseno, n2, n3)
    # + 1 chunk 0.85; docB con 2 chunks 0.80 empatados.
    return [
        {"id": "a-high", "source_file": "docA", "similarity": 0.85},
        {"id": "n2", "source_file": "docA", "similarity": 0.80},
        {"id": "n3", "source_file": "docA", "similarity": 0.80},
        {"id": "n1", "source_file": "docA", "similarity": 0.80},
        {"id": "b1", "source_file": "docB", "similarity": 0.80},
        {"id": "b2", "source_file": "docB", "similarity": 0.80},
    ]


COS = {"n1": 0.9, "n2": 0.3, "n3": 0.2, "b1": 0.1, "b2": 0.8}


@pytest.fixture
def tiebreak_env(monkeypatch):
    monkeypatch.setenv("DIVERSIFY_TIEBREAK", "cosine")
    monkeypatch.setattr(R, "_fetch_embeddings_by_id",
                        lambda ids: {i: [COS[i]] for i in ids if i in COS})
    monkeypatch.setattr(R, "_cos", lambda q, e: e[0])
    monkeypatch.setattr(R, "_get_source_files_for_model", lambda m: ["docA", "docB"])
    monkeypatch.setattr(R, "_series", type("S", (), {
        "series_enabled": staticmethod(lambda: False),
        "any_series": staticmethod(lambda m: False),
        "shared_sources_for": staticmethod(lambda m: [])})())
    return monkeypatch


def test_parser_estricto(monkeypatch):
    for raw, esperado in [("", False), ("off", False), ("cosine", True)]:
        monkeypatch.setenv("DIVERSIFY_TIEBREAK", raw)
        assert R._tiebreak_on() is esperado, raw
    monkeypatch.setenv("DIVERSIFY_TIEBREAK", "cos")
    with pytest.raises(RuntimeError):
        R._tiebreak_on()


def test_flag_off_orden_identico(monkeypatch):
    monkeypatch.delenv("DIVERSIFY_TIEBREAK", raising=False)
    monkeypatch.setattr(R, "_get_source_files_for_model", lambda m: ["docA", "docB"])
    monkeypatch.setattr(R, "_series", type("S", (), {
        "series_enabled": staticmethod(lambda: False),
        "any_series": staticmethod(lambda m: False),
        "shared_sources_for": staticmethod(lambda m: [])})())
    called = []
    monkeypatch.setattr(R, "_fetch_embeddings_by_id",
                        lambda ids: called.append(ids) or {})
    out = R._diversify_by_source_file(_pool(), 6, ["M1"], "q",
                                      query_embedding=[1.0])
    assert not called                                   # ni un GET con flag off
    ids_a = [c["id"] for c in out if c["source_file"] == "docA"]
    assert ids_a == ["a-high", "n2", "n3", "n1"]        # orden de inserción (hoy)


def test_tiebreak_reordena_solo_empatados_within_source(tiebreak_env):
    out = R._diversify_by_source_file(_pool(), 6, ["M1"], "q",
                                      query_embedding=[1.0])
    ids_a = [c["id"] for c in out if c["source_file"] == "docA"]
    # a-high (0.85, sin empate) primero; el grupo 0.80 por coseno: n1(.9) n2(.3) n3(.2)
    assert ids_a == ["a-high", "n1", "n2", "n3"]
    ids_b = [c["id"] for c in out if c["source_file"] == "docB"]
    assert ids_b == ["b2", "b1"]                        # b2(.8) > b1(.1)


def test_similarity_jamas_mutada(tiebreak_env):
    """(H2 CRÍTICO) mutar similarity = cosine-merge DEC-050 entero."""
    out = R._diversify_by_source_file(_pool(), 6, ["M1"], "q",
                                      query_embedding=[1.0])
    assert all(c["similarity"] in (0.85, 0.80) for c in out)


def test_source_order_intocado(tiebreak_env):
    """(H6/C1) el desempate ENTRE fuentes sigue siendo el de hoy: docA entra primero
    (mejor top 0.85) aunque el mejor coseno del pool viva en docA igualmente; con
    top_k=3 el round-robin da docA, docB, docA."""
    out = R._diversify_by_source_file(_pool(), 3, ["M1"], "q",
                                      query_embedding=[1.0])
    assert [c["source_file"] for c in out] == ["docA", "docB", "docA"]


def test_fail_open_si_fetch_falla(tiebreak_env, monkeypatch):
    def boom(ids):
        raise RuntimeError("hiccup")
    monkeypatch.setattr(R, "_fetch_embeddings_by_id", boom)
    out = R._diversify_by_source_file(_pool(), 6, ["M1"], "q",
                                      query_embedding=[1.0])
    ids_a = [c["id"] for c in out if c["source_file"] == "docA"]
    assert ids_a == ["a-high", "n2", "n3", "n1"]        # orden actual, sin romper


def test_sin_query_embedding_noop(tiebreak_env):
    out = R._diversify_by_source_file(_pool(), 6, ["M1"], "q",
                                      query_embedding=None)
    ids_a = [c["id"] for c in out if c["source_file"] == "docA"]
    assert ids_a == ["a-high", "n2", "n3", "n1"]
