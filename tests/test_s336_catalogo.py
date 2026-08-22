# -*- coding: utf-8 -*-
"""s336 B3 — el aparato de catálogo del lote de clasificación.

1. `swap_products_validado`: escritura ATÓMICA con shadow COMPLETO (Sol-5/
   Sol2-6) — el candidato inválido REVIENTA y el vivo queda byte-idéntico
   (control negativo G4: el rollback se prueba con el fallo real, no simulado).
2. Validador: `clasificacion.doc` (Sol2-2) y `alcance` (#76b) con forma cerrada.
3. Display POR FUENTE (#76b(c)): entradas de capacidad con `alcance` divergente
   NO se fusionan en «hasta max» (fixture clase AFP1010: 2 lazos ES / 4 EN);
   sin alcance divergente, conducta de hoy byte-idéntica.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag import catalog_store as cs


def _fila_base(pid="testmarca:x1", **extra):
    fila = {"id": pid, "canonical_model": "X1", "estado": "activo",
            "vendido_bajo": ["Testmarca"], "provenance": "test s336",
            "added_by": "test"}
    fila.update(extra)
    return fila


def _catalogo_sintetico(tmp_path: Path, filas) -> Path:
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="catalogo_", dir=tmp_path))
    (d / cs.FILES["products"]).write_text(
        "\n".join(json.dumps(f, ensure_ascii=False, sort_keys=True)
                  for f in filas) + "\n", encoding="utf-8")
    return d


# ── 1 · swap atómico ───────────────────────────────────────────────────────────

def test_swap_valido_reemplaza_y_deja_backup(tmp_path):
    d = _catalogo_sintetico(tmp_path, [_fila_base()])
    nuevas = [_fila_base(clasificacion={
        "categoria": "central", "cita": "la central X1", "doc": "doc-x1",
        "provenance": "s336 test"})]
    backup = cs.swap_products_validado(nuevas, catalog_dir=d)
    assert backup.exists() and "bak-" in backup.name
    vivo = (d / cs.FILES["products"]).read_text(encoding="utf-8")
    assert '"categoria": "central"' in vivo and '"doc": "doc-x1"' in vivo


def test_swap_invalido_revienta_y_el_vivo_queda_byte_identico(tmp_path):
    d = _catalogo_sintetico(tmp_path, [_fila_base()])
    antes = (d / cs.FILES["products"]).read_bytes()
    rotas = [_fila_base(clasificacion={
        "categoria": "NO-EXISTE", "cita": "x", "provenance": "y"})]
    with pytest.raises(ValueError, match="INVÁLIDO"):
        cs.swap_products_validado(rotas, catalog_dir=d)
    assert (d / cs.FILES["products"]).read_bytes() == antes  # rollback real
    assert not list(d.glob("*.bak-*"))                       # ni backup huérfano


# ── 2 · validador: clasificacion.doc y alcance ────────────────────────────────

def _valida(tmp_path, fila):
    return cs.validate(_catalogo_sintetico(tmp_path, [fila]))


def test_clasificacion_doc_vacio_revienta(tmp_path):
    errs = _valida(tmp_path, _fila_base(clasificacion={
        "categoria": "central", "cita": "c", "provenance": "p", "doc": "  "}))
    assert any("clasificacion.doc" in e for e in errs)


def test_alcance_forma_cerrada(tmp_path):
    ok = _fila_base(
        clasificacion={"categoria": "central", "cita": "c", "provenance": "p",
                       "doc": "d"},
        atributos={"lazos": [{"max": 2, "doc": "d-es", "cita": "2 lazos",
                              "alcance": {"eje": "idioma_doc", "valor": "es"}}]})
    assert _valida(tmp_path, ok) == []
    mal_eje = _fila_base(
        clasificacion={"categoria": "central", "cita": "c", "provenance": "p"},
        atributos={"lazos": [{"max": 2, "doc": "d", "cita": "c",
                              "alcance": {"eje": "mercado", "valor": "us"}}]})
    assert any("alcance inválido" in e for e in _valida(tmp_path, mal_eje))
    clave_extra = _fila_base(
        clasificacion={"categoria": "central", "cita": "c", "provenance": "p"},
        atributos={"lazos": [{"max": 2, "doc": "d", "cita": "c",
                              "alcance": {"eje": "idioma_doc", "valor": "es",
                                          "otra": 1}}]})
    assert any("alcance inválido" in e for e in _valida(tmp_path, clave_extra))


# ── 3 · display por-fuente (#76b(c), fixture clase AFP1010) ───────────────────

def _cat_con_afp(tmp_path, con_alcance: bool):
    lazos = [{"base": 2, "max": 2, "doc": "doc-es", "cita": "2 lazos"},
             {"base": 4, "max": 4, "doc": "doc-us", "cita": "4 loops"}]
    if con_alcance:
        lazos[0]["alcance"] = {"eje": "idioma_doc", "valor": "es"}
        lazos[1]["alcance"] = {"eje": "idioma_doc", "valor": "en"}
    fila = _fila_base(
        pid="testmarca:afp-fixture", canonical_model="AFP-FIXTURE",
        clasificacion={"categoria": "central", "cita": "panel de control",
                       "doc": "doc-es", "provenance": "s336 fixture"},
        atributos={"tecnologia": [{"valor": "analogica", "doc": "doc-es",
                                   "cita": "analógica"}],
                   "lazos": lazos})
    d = _catalogo_sintetico(tmp_path, [fila])
    (d / cs.FILES["doc_map"]).write_text(json.dumps({
        "document_id": "t", "source_file": "doc-es",
        "entries": [{"id": "testmarca:afp-fixture", "role": "primary",
                     "scope": "doc", "provenance": "test"}]},
        ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    assert cs.validate(d) == []
    return cs.load(d)


@pytest.mark.parametrize("con_alcance,espera_por_fuente", [(True, True),
                                                           (False, False)])
def test_capacidad_divergente_se_sirve_por_fuente(tmp_path, monkeypatch,
                                                  con_alcance,
                                                  espera_por_fuente):
    from src.bot import telegram_bot as tb
    from src.rag import catalog_resolver

    cat = _cat_con_afp(tmp_path, con_alcance)
    monkeypatch.setattr(catalog_resolver, "catalogo_cargado", lambda: cat)
    out = tb._inventario_filtrado("testmarca", {"categoria": "central",
                                                "lazos": 4})
    assert out and "AFP-FIXTURE" in out
    if espera_por_fuente:
        assert " / " in out and "(es)" in out and "(en)" in out
        assert "hasta 2 lazos (es)" in out and "hasta 4 lazos (en)" in out
    else:
        assert "hasta 4 lazos" in out and " / " not in out
