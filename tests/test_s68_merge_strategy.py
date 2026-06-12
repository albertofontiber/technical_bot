"""s68 — _merge_channels bajo MERGE_STRATEGY (diseño _s68_merge_design.md v6.1 §2).

Contratos: `stamps` = comportamiento histórico EXACTO (keyword-first dedup + sort por
similarity) · `quota` = composición V-D (léxicos con límites actuales; dual-canal →
registro VECTOR conserva coseno; vector llena hasta cap) · `cosine` = V-A′ (score único
coseno, sin boosts, fallo-abierto sin embedding). Wiring L-i′: bajo variantes el canal
vectorial va SIN category, SIN broad-5 y SIN 3c-i (réplica s59/DEC-040; los 5 tests de
la rama `s59-lever-code-ROLLBACKED` se re-escriben aquí condicionales al flag)."""
import os

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import src.rag.retriever as rt  # noqa: E402


def _c(cid, sim, channel=None):
    d = {"id": cid, "similarity": sim, "content": f"c-{cid}"}
    if channel:
        d["_channel"] = channel
    return d


# --------------------------------------------------------------- _merge_channels
def test_stamps_keyword_first_y_sort_historico():
    kw = [_c("a", 0.80), _c("dual", 0.80)]
    vec = [_c("dual", 0.61, "VECTOR"), _c("v1", 0.66, "VECTOR")]
    out = rt._merge_channels(kw, vec, cap=50, strategy="stamps")
    by_id = {c["id"]: c for c in out}
    assert by_id["dual"]["similarity"] == 0.80          # el stamp PISA al coseno (histórico)
    assert [c["id"] for c in out] == ["a", "dual", "v1"]  # sort desc, estable


def test_quota_dual_conserva_registro_vector():
    kw = [_c("dual", 0.80), _c("kw1", 0.65)]
    vec = [_c("dual", 0.61, "VECTOR"), _c("v1", 0.58, "VECTOR")]
    out = rt._merge_channels(kw, vec, cap=50, strategy="quota")
    by_id = {c["id"]: c for c in out}
    assert by_id["dual"]["similarity"] == 0.61          # volteo: gana el coseno (F4 declarado)
    assert by_id["dual"]["_channel"] == "VECTOR"
    assert "v1" in by_id                                 # el vector llena el resto


def test_quota_vector_llena_hasta_cap_y_lexicos_no_se_capan():
    kw = [_c(f"k{i}", 0.80) for i in range(4)]
    vec = [_c(f"v{i}", 0.70 - i * 0.01, "VECTOR") for i in range(10)]
    out = rt._merge_channels(kw, vec, cap=6, strategy="quota")
    assert len(out) == 6                                 # 4 léxicos + 2 cosenos top
    assert {c["id"] for c in out if c["id"].startswith("v")} == {"v0", "v1"}
    out2 = rt._merge_channels([_c(f"k{i}", 0.8) for i in range(8)], vec[:2], cap=6,
                              strategy="quota")
    assert len(out2) == 8                                # léxicos con límites ACTUALES (sin cap)


def test_cosine_rescore_y_dedup(monkeypatch):
    monkeypatch.setattr(rt, "_fetch_embeddings_by_id",
                        lambda ids: {"kw1": [1.0, 0.0], "dual": [0.0, 1.0]})
    kw = [_c("kw1", 0.85), _c("dual", 0.80)]
    vec = [_c("dual", 0.42, "VECTOR")]
    out = rt._merge_channels(kw, vec, cap=50, strategy="cosine",
                             query_embedding=[1.0, 0.0])
    by_id = {c["id"]: c for c in out}
    assert by_id["kw1"]["similarity"] == pytest.approx(1.0)   # re-puntuado a coseno
    assert len(out) == 2                                       # dedup por id
    assert out[0]["id"] == "kw1"                               # sort por coseno


def test_rescore_fallo_abierto_sin_embedding(monkeypatch):
    monkeypatch.setattr(rt, "_fetch_embeddings_by_id", lambda ids: {})
    chunks = [_c("x", 0.85)]
    rt._rescore_to_cosine(chunks, [1.0, 0.0])
    assert chunks[0]["similarity"] == 0.85               # conserva el stamp (declarado)


def test_tag_channel_primera_gana():
    c = _c("a", 0.8)
    rt._tag_channel([c], "MODEL")
    rt._tag_channel([c], "CONTENT")
    assert c["_channel"] == "MODEL"


def test_flag_default_stamps():
    from src.config import MERGE_STRATEGY
    assert os.getenv("MERGE_STRATEGY") in (None, "stamps") and MERGE_STRATEGY == "stamps" \
        or MERGE_STRATEGY == os.getenv("MERGE_STRATEGY")


# ------------------------------------------- wiring L-i′ (réplica condicional s59)
def _run_retrieve(monkeypatch, strategy):
    """retrieve_chunks con red mockeada; captura las llamadas a vector_search y si
    se encolaron tasks 3c-i (la query dispara categoría sin modelo)."""
    calls = {"vector": [], "content": []}
    monkeypatch.setattr(rt, "MERGE_STRATEGY", strategy)
    monkeypatch.setattr(rt, "embed_query", lambda q: [0.1, 0.2])
    monkeypatch.setattr(rt, "HYDE_ENABLED", False)

    def fake_vector(query, top_k, threshold, product, category, emb=None):
        calls["vector"].append({"top_k": top_k, "category": category})
        return []

    def fake_content(term, limit=10, product_model=None, category=None):
        calls["content"].append({"term": term, "category": category})
        return []

    monkeypatch.setattr(rt, "vector_search", fake_vector)
    monkeypatch.setattr(rt, "content_search", fake_content)
    monkeypatch.setattr(rt, "keyword_search", lambda m, limit=5: [])
    monkeypatch.setattr(rt, "extract_product_models", lambda q: [])
    monkeypatch.setattr(rt, "_filter_by_document_status", lambda c: c)
    monkeypatch.setattr(rt, "_filter_by_language", lambda c: c)
    # query sin modelo CON término de categoría → detected_category + 3c
    rt.retrieve_chunks("cómo configurar la central de incendios", top_k=10)
    return calls


def test_li_stamps_mantiene_category_broad5_y_3ci(monkeypatch):
    calls = _run_retrieve(monkeypatch, "stamps")
    cats = [v["category"] for v in calls["vector"]]
    assert any(c is not None for c in cats), "canal principal CON categoría (histórico)"
    assert len(calls["vector"]) == 2, "broad-5 presente (histórico)"
    assert any(c["category"] is not None for c in calls["content"]), "3c-i vivas (histórico)"


@pytest.mark.parametrize("strategy", ["quota", "cosine"])
def test_li_variantes_sin_category_sin_broad5_sin_3ci(monkeypatch, strategy):
    calls = _run_retrieve(monkeypatch, strategy)
    assert [v["category"] for v in calls["vector"]] == [None], \
        "L-i′: UN solo canal vectorial, SIN filter_category, SIN broad-5 (réplica s59)"
    assert all(c["category"] is None for c in calls["content"]), \
        "L-i′: 3c-i eliminadas (pre-check Y1: 0 filas con categoría canónica)"
