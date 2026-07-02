"""Tests de src/rag/catalog_resolver.py (s91 F2-S1, plan v2.2).

Pinean: detección-en-frase (multi-palabra, negativos digit-only, ZXe len-3 — la bomba r2),
resolución por la puerta (ZXe→variantes, RP1r→Supra prefer [hp011], APIC clarify sin expansión),
los dos brazos de política (add=hipótesis / replace=medido), fail-fast de flags legacy (v2.1a),
shadow no-muta, stamp del catálogo-commit (v2.1b), y el seam 2 (whitelist en
_filter_to_query_models con fail-open ≥3). Skip si data/catalog no está cargado (igual que
test_catalog_store)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.rag import catalog_resolver as R

pytestmark = pytest.mark.skipif(
    not (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").exists(),
    reason="catálogo no cargado")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("IDENTITY_RESOLVE", "IDENTITY_RESOLVE_POLICY", *R.LEGACY_FLAGS):
        monkeypatch.delenv(f, raising=False)
    yield


# ─── flag / fail-fast (v2.1a) ───
def test_mode_default_off():
    assert R.mode() == "off"


def test_mode_invalido(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "yes")
    with pytest.raises(RuntimeError, match="inválido"):
        R.mode()


@pytest.mark.parametrize("legacy", R.LEGACY_FLAGS)
def test_fail_fast_contra_cada_flag_legacy(monkeypatch, legacy):
    monkeypatch.setenv("IDENTITY_RESOLVE", "shadow")
    monkeypatch.setenv(legacy, "1")
    with pytest.raises(RuntimeError, match="EXCLUYENTE"):
        R.mode()


def test_legacy_on_con_resolve_off_no_falla(monkeypatch):
    # el mundo actual (LEVER2 en evals viejos) sigue funcionando con el resolver apagado
    monkeypatch.setenv("LEVER2_IDENTITY", "1")
    assert R.mode() == "off"


def test_lista_de_flags_legacy_cubre_el_codigo():
    # v2.1a: si aparece un flag de identidad nuevo en el retriever, esta lista debe crecer
    src = (Path(R.ROOT) / "src" / "rag" / "retriever.py").read_text(encoding="utf-8")
    for f in ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "IDENTITY_MAP"):
        assert f in src and f in R.LEGACY_FLAGS


# ─── detección (regex generada del catálogo) ───
def test_detecta_zxe_en_frase():
    # la bomba r2: norm('ZXe')='zxe' (3 chars) DEBE detectarse
    assert "zxe" in [t.replace(" ", "") for t in R.detect("avería en la central Morley ZXe de 2 lazos")]


def test_detecta_multi_palabra():
    assert any("faast" in t for t in R.detect("sensibilidad del FAAST LT-200"))


def test_no_detecta_digit_only():
    assert R.detect("el código de error 808 en pantalla") == []
    assert R.detect("revisa el 816 y el 777163") == []


def test_no_detecta_en_query_generica():
    assert R.detect("cuántos detectores soporta un lazo estándar de la central") == []


# ─── resolución por la puerta (contrato expand) ───
def test_zxe_expande_a_variantes():
    res = R.resolve_query("central ZXe")
    rec = next(r for r in res["records"] if "zx" in r["token"])
    assert rec["via"] == "paraguas" and rec["expand"] is True
    assert set(rec["ids"]) == {"morley:zx1e", "morley:zx2e", "morley:zx5e"}
    assert set(res["add_models"]) == {"ZX1e", "ZX2e", "ZX5e"}


def test_hp011_rp1r_prefer_supra():
    res = R.resolve_query("conectar el RP1r al software de gestión")
    rec = next(r for r in res["records"] if r["token"] == "rp1r")
    assert rec["via"] == "homonimo" and rec["politica"] == "prefer:notifier:rp1r-supra"
    assert rec["ids"] == ["notifier:rp1r-supra"] and rec["expand"] is True


def test_apic_clarify_no_expande():
    res = R.resolve_query("tarjeta APIC compatible")
    rec = next(r for r in res["records"] if r["token"] == "apic")
    assert rec["expand"] is False
    assert res["add_models"] == [] and res["allowed_sources"] == frozenset()


def test_zxse_expande_y_permite_mie_mi_600():
    # la clase pm=unknown: el doc de la familia ZXSe debe estar en allowed_sources
    res = R.resolve_query("central ZXSe instalación")
    assert res["add_models"], "ZXSe debe expandir a variantes"
    assert any("MIE-MI-600" in s for s in res["allowed_sources"])


# ─── seam 1: brazos add / replace ───
def test_brazo_add_conserva_el_token(monkeypatch):
    res = R.resolve_query("central ZXe")
    out = R.apply_to_models(["ZXE"], res)
    assert out[0] == "ZXE" and {"ZX1e", "ZX2e", "ZX5e"} <= set(out)


def test_brazo_replace_retira_el_paraguas(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("central ZXe")
    out = R.apply_to_models(["ZXE"], res)
    assert "ZXE" not in out and {"ZX1e", "ZX2e", "ZX5e"} == set(out)


# ─── entrada única del retriever ───
def test_off_passthrough_exacto():
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert models == ["ZXE"] and res is None


def test_shadow_no_muta(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "shadow")
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert models == ["ZXE"] and res is None


def test_on_aplica_seam1_y_devuelve_allowed(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert {"ZX1e", "ZX2e", "ZX5e"} <= set(models)
    assert res is not None and len(res["allowed_sources"]) > 0


def test_on_sin_tokens_passthrough(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    models, res = R.resolve_for_retrieval("cuántos detectores soporta un lazo", ["X999"])
    assert models == ["X999"] and res is None


# ─── seam 2: whitelist en _filter_to_query_models ───
def _chunk(pm, src):
    return {"product_model": pm, "source_file": src, "content": "x"}


def test_seam2_whitelist_protege_pm_unknown():
    from src.rag.retriever import _filter_to_query_models
    allowed = frozenset({"MIE-MI-600"})
    chunks = [_chunk("unknown", "MIE-MI-600")] * 3 + [_chunk("ZXAE", "MIE-MI-310")]
    out = _filter_to_query_models(chunks, ["ZX2Se"], identity_allowed=allowed)
    assert len(out) == 3 and all(c["source_file"] == "MIE-MI-600" for c in out)


def test_seam2_fail_open_bajo_3():
    from src.rag.retriever import _filter_to_query_models
    allowed = frozenset({"MIE-MI-600"})
    chunks = [_chunk("unknown", "MIE-MI-600")] * 2 + [_chunk("CAD-150-8", "55315013")] * 3
    out = _filter_to_query_models(chunks, ["CAD-150"], identity_allowed=allowed)
    # <3 supervivientes del whitelist → cae al substring nivel-1 (CAD-150 matchea CAD-150-8)
    assert any(c["product_model"] == "CAD-150-8" for c in out)


def test_seam2_none_es_el_comportamiento_actual():
    from src.rag.retriever import _filter_to_query_models
    chunks = [_chunk("CAD-150-8", "55315013")] * 3 + [_chunk("CAD-250", "otros")]
    a = _filter_to_query_models(chunks, ["CAD-150"])
    b = _filter_to_query_models(chunks, ["CAD-150"], identity_allowed=None)
    assert a == b and all(c["product_model"] == "CAD-150-8" for c in a)


# ─── stamp (v2.1b) ───
def test_catalog_commit_stamp():
    st = R.catalog_commit()
    assert st and st != "unknown"


# ─── round-trip muestreado (H8: negativos > tautología) ───
def test_roundtrip_muestra_de_canonicals():
    import json
    rows = [json.loads(l) for l in
            (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").open(encoding="utf-8")]
    consum = [r for r in rows if r.get("estado") == "activo" and not r.get("candidate")][::40]
    fallos = []
    for p in consum:
        cm = p["canonical_model"]
        segs = "".join(__import__("re").findall(r"[a-z]+|\d+", cm.lower()))
        if not segs or segs.isdigit():
            continue                      # digit-only: excluido del detector a propósito
        if not R.detect(f"manual del {cm} por favor"):
            fallos.append(cm)
    assert not fallos, f"canonicals no detectados: {fallos[:10]}"
