"""s273 — tests unitarios de la fusión por cuota del canal enunciados (build post-dúo).

Cubren la mecánica pura (_fuse_enunciados_quota), la protección de los DOS carve-outs
(E+H simultáneos — Fable-menor-2), la exclusión prod-neutral del batch T2Q1 (Sol-C2b)
y los invariantes del flag. Sin red: ninguna llamada a DB/modelo.
"""
import importlib
import json
import os

import pytest


@pytest.fixture()
def R(monkeypatch):
    monkeypatch.setenv("ENUNCIADOS_QUOTA_FUSION", "off")
    monkeypatch.setenv("HYQ_TABLE", "off")
    monkeypatch.setenv("CHUNKS_TABLE", "chunks_v2")
    import src.rag.retriever as retriever
    return retriever


def _chunk(cid, sim, **kw):
    return {"id": cid, "similarity": sim, **kw}


def _surr(sid, parent, sim):
    return {"id": sid, "parent_id": parent, "similarity": sim}


def test_flag_default_off_and_frozen_hyperparams(R):
    assert R.ENUNCIADOS_QUOTA_ON is False           # default off = prod inerte
    assert R.ENUNCIADOS_QUOTA == 6                  # congelado (prereg v2); no env-tunable
    assert R.ENUNCIADOS_MIN_SIM == 0.40
    assert os.getenv("ENUNCIADOS_QUOTA_6", None) is None  # no existe knob de entorno


def test_strict_parser_rejects_typos(R):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ENUNCIADOS_QUOTA_FUSION", "onn")
        with pytest.raises(RuntimeError):
            R._enunciados_quota_on()


def test_quota_reserves_slots_below_real_floor(R):
    """La diferencia con la mecánica s105: un parent BAJO el floor real entra igual."""
    results = [_chunk(f"r{i}", 0.60 - i * 0.001) for i in range(50)]   # floor 0.551
    by_parent = {"p1": _surr("s1", "p1", 0.43)}                        # < floor, ≥ barra
    fused = R._fuse_enunciados_quota(results, by_parent, 50)
    assert len(fused) == 50
    quota_rows = [c for c in fused if c.get("_enun_quota")]
    assert [c["parent_id"] for c in quota_rows] == ["p1"]              # entró con slot reservado
    assert "r49" not in {c.get("id") for c in fused}                   # desplazó la cola real


def test_quota_caps_at_q6_and_bar_040(R):
    results = [_chunk(f"r{i}", 0.60) for i in range(50)]
    by_parent = {f"p{i}": _surr(f"s{i}", f"p{i}", 0.55 - i * 0.01) for i in range(10)}
    by_parent["low"] = _surr("sl", "low", 0.39)                        # bajo la barra
    fused = R._fuse_enunciados_quota(results, by_parent, 50)
    quota_rows = [c for c in fused if c.get("_enun_quota")]
    assert len(quota_rows) == 6                                        # Q=6, no 10
    assert "low" not in {c["parent_id"] for c in quota_rows}           # barra 0.40 filtra
    sims = [c["similarity"] for c in quota_rows]
    assert sims == sorted(sims, reverse=True)                          # top-Q por sim


def test_dedup_at_fusion_boosts_without_buying_slot(R):
    """Prior art s105 heredado: padre YA en pool → keep-max boost, NO consume cuota."""
    results = [_chunk("p1", 0.50)] + [_chunk(f"r{i}", 0.45) for i in range(9)]
    by_parent = {"p1": _surr("s1", "p1", 0.58),                        # ya en pool → boost
                 "p2": _surr("s2", "p2", 0.41)}                        # nuevo → cuota
    fused = R._fuse_enunciados_quota(results, by_parent, 50)
    boosted = next(c for c in fused if c.get("id") == "p1")
    assert boosted["similarity"] == 0.58 and boosted.get("_enunciado_boosted") is True
    quota_rows = [c for c in fused if c.get("_enun_quota")]
    assert [c["parent_id"] for c in quota_rows] == ["p2"]              # p1 no compró slot


def test_atomicity_boost_on_copies_original_untouched(R):
    """Atomicidad S4: la lista/filas de entrada no se mutan (el caller reasigna al final)."""
    original = _chunk("p1", 0.50)
    results = [original]
    by_parent = {"p1": _surr("s1", "p1", 0.58)}
    R._fuse_enunciados_quota(results, by_parent, 50)
    assert original["similarity"] == 0.50 and "_enunciado_boosted" not in original


def test_no_quota_candidates_returns_topk_unchanged_membership(R):
    results = [_chunk(f"r{i}", 0.6 - i * 0.01) for i in range(5)]
    fused = R._fuse_enunciados_quota(results, {}, 50)
    assert [c["id"] for c in fused] == [c["id"] for c in results]


def test_dual_carveout_hyq_trim_respects_enun_quota_pool_under_50(R):
    """Fable-menor-2: E+H simultáneos con pool<50 — nada se recorta, E y H conviven."""
    results = [_chunk(f"r{i}", 0.55) for i in range(20)]
    e_quota = [dict(_surr(f"es{i}", f"ep{i}", 0.42), _enun_quota=True) for i in range(3)]
    results = results + e_quota                                        # pool 23 < 50
    hyq_quota = [_chunk(f"h{i}", 0.48, _hyq_surrogate=True) for i in range(4)]
    protected = [c for c in results if c.get("_enun_quota")]
    base = [c for c in results if not c.get("_enun_quota")]
    final = base[:max(0, 50 - len(hyq_quota) - len(protected))] + protected + hyq_quota
    ids = {c.get("id") for c in final}
    assert {"es0", "es1", "es2"} <= ids and {"h0", "h1", "h2", "h3"} <= ids
    assert len(final) == 27                                            # nadie evictado


def test_dual_carveout_full_pool_composition_bounds(R):
    """Pool lleno: composición final reales[:50−|E|−|H|] + E + H (reales ≥ 34 con E=6,H=10)."""
    reales = [_chunk(f"r{i}", 0.60 - i * 0.001) for i in range(50)]
    e_quota = [dict(_surr(f"es{i}", f"ep{i}", 0.42), _enun_quota=True) for i in range(6)]
    results = reales[:44] + e_quota                                    # salida de la fusión E
    hyq_quota = [_chunk(f"h{i}", 0.48, _hyq_surrogate=True) for i in range(10)]
    protected = [c for c in results if c.get("_enun_quota")]
    base = [c for c in results if not c.get("_enun_quota")]
    final = base[:max(0, 50 - len(hyq_quota) - len(protected))] + protected + hyq_quota
    assert len(final) == 50
    assert sum(1 for c in final if c.get("_enun_quota")) == 6          # E intacta (no evictada)
    assert sum(1 for c in final if c.get("_hyq_surrogate")) == 10      # H intacta
    assert sum(1 for c in final if str(c.get("id", "")).startswith("r")) == 34


def test_t2q1_exclusion_missing_file_is_noop(R, monkeypatch, tmp_path):
    monkeypatch.setattr(R, "_T2Q1_EXCLUSION_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(R, "_T2Q1_CACHE", None)
    assert R._t2q1_exclusion_ids() == frozenset()                      # pre-F2 = NO-OP


def test_t2q1_exclusion_loads_manifest_ids(R, monkeypatch, tmp_path):
    p = tmp_path / "excl.json"
    p.write_text(json.dumps({"batch": "enunciados-v1:T2Q1:h1", "ids": ["a", "b"]}),
                 encoding="utf-8")
    monkeypatch.setattr(R, "_T2Q1_EXCLUSION_PATH", str(p))
    monkeypatch.setattr(R, "_T2Q1_CACHE", None)
    assert R._t2q1_exclusion_ids() == frozenset({"a", "b"})


def test_swap_propagates_enun_quota_tag(R, monkeypatch):
    """El parent hidratado conserva la marca del carve-out (traceability del probe F3)."""
    monkeypatch.setattr(
        R, "_fetch_embeddings_by_id", lambda ids: {})
    # _enunciados_swap hidrata por REST; lo simulamos parcheando httpx.Client.get
    class _Resp:
        def raise_for_status(self):
            return None
        def json(self):
            return [{"id": "PARENT", "content": "texto real", "parent_id": None}]
    class _Cli:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, *a, **k):
            return _Resp()
    monkeypatch.setattr(R.httpx, "Client", _Cli)
    surr = {"id": "S1", "parent_id": "PARENT", "similarity": 0.43, "_enun_quota": True}
    out = R._enunciados_swap([surr])
    assert out and out[0]["id"] == "PARENT" and out[0].get("_enun_quota") is True
    assert out[0]["similarity"] == 0.43                                # sim del surrogate (famtie)
