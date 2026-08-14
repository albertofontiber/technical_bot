# -*- coding: utf-8 -*-
"""s322 #76 (DEC-216) — Inventario con filtros de categoría/atributos.

Gates del dúo r27: el caso DORADO de Alberto dispara y filtra; los atributos
son multi-valor por-fuente; la ruta sin filtro es byte-igual (caché y truncado
incluidos); el join es catálogo ∩ doc_map (jamás pm de chunks); honestidad
sobre lo no-clasificado.
"""
import os
import types

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import src.bot.telegram_bot as bot  # noqa: E402
import src.orchestrator.turn_plan as tp  # noqa: E402

ORO = "¿Qué centrales de cuatro lazos analógicas de Detnov tienes?"


# ---------- el plan (puro, $0) ----------

def test_caso_dorado_dispara_inventario_y_tipa_filtros():
    assert tp._ENUM_FABRICANTE.search(ORO)
    assert tp.filtros_inventario(ORO) == {
        "categoria": "central", "tecnologia": "analogica", "lazos": 4}


def test_filtros_none_sin_lexico():
    assert tp.filtros_inventario("¿qué productos de Detnov tienes?") is None


def test_filtros_en_ingles_y_numeral():
    assert tp.filtros_inventario("which analogue panels with 2 loops do you have?") == {
        "categoria": "central", "tecnologia": "analogica", "lazos": 2}


# ---------- el consumidor (catálogo fake) ----------

def _catalogo_fake():
    products = {
        "detnov:cad-150-4": {
            "id": "detnov:cad-150-4", "canonical_model": "CAD-150-4",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "central", "cita": "central analógica",
                              "provenance": "test"},
            "atributos": {
                "tecnologia": [{"valor": "analogica", "doc": "d1", "cita": "x"}],
                "lazos": [{"base": 4, "max": 4, "doc": "d1", "cita": "x"}]},
        },
        "detnov:cad-150-2": {
            "id": "detnov:cad-150-2", "canonical_model": "CAD-150-2",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "central", "cita": "c", "provenance": "t"},
            "atributos": {
                "tecnologia": [{"valor": "analogica", "doc": "d2", "cita": "x"}],
                "lazos": [{"base": 2, "max": 2, "doc": "d2", "cita": "x"}]},
        },
        "detnov:sad-150": {
            "id": "detnov:sad-150", "canonical_model": "SAD-150",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "sirena", "cita": "s", "provenance": "t"},
        },
        "detnov:msd-x": {  # sin clasificar
            "id": "detnov:msd-x", "canonical_model": "MSD-X",
            "estado": "activo", "vendido_bajo": ["Detnov"],
        },
        "detnov:viejo": {  # sin docs → no está "en lo que tenemos"
            "id": "detnov:viejo", "canonical_model": "VIEJO",
            "estado": "activo", "vendido_bajo": ["Detnov"],
        },
    }
    doc_map = [{"document_id": f"u{i}", "source_file": f"f{i}",
                "entries": [{"id": pid, "role": "primary", "scope": "doc"}]}
               for i, pid in enumerate(p for p in products if p != "detnov:viejo")]
    cat = types.SimpleNamespace(
        products=products, doc_map=doc_map,
        follow_redirect=lambda pid: pid)
    return cat


@pytest.fixture
def catalogo_fake(monkeypatch):
    cat = _catalogo_fake()
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado", lambda: cat)
    bot._inventario_cache.clear()
    yield cat
    bot._inventario_cache.clear()


def test_filtrado_caso_dorado(catalogo_fake):
    r = bot._inventario_fabricante(
        "Detnov", {"categoria": "central", "tecnologia": "analogica", "lazos": 4})
    assert "CAD-150-4" in r
    assert "CAD-150-2" not in r          # 2 lazos no casa con 4
    assert "SAD-150" not in r            # sirena no es central
    assert "sin clasificar" in r         # MSD-X contado honesto
    assert "VIEJO" not in r              # sin docs = no lo "tenemos"


def test_filtrado_lazos_2(catalogo_fake):
    r = bot._inventario_fabricante("Detnov", {"lazos": 2})
    assert "CAD-150-2" in r and "CAD-150-4" not in r


def test_ninguno_casa_es_honesto(catalogo_fake):
    r = bot._inventario_fabricante("Detnov", {"categoria": "central",
                                              "lazos": 8})
    assert "ninguno" in r.lower()
    assert "sin clasificar" in r


def test_cache_compuesta_no_contamina(catalogo_fake, monkeypatch):
    r4 = bot._inventario_fabricante("Detnov", {"lazos": 4})
    r2 = bot._inventario_fabricante("Detnov", {"lazos": 2})
    assert r4 != r2
    # y la clave sin filtro es otra entrada (no pisada por las filtradas)
    assert all("|" in k or k == "detnov" for k in bot._inventario_cache)


def test_catalogo_caido_degrada_a_lista_completa_con_aviso(monkeypatch):
    bot._inventario_cache.clear()
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado",
                        lambda: None)
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda n: [("CAD-150", 3), ("SAD-150", 1)])
    r = bot._inventario_fabricante("Detnov", {"lazos": 4})
    assert "Aún no tengo la clasificación" in r
    assert "CAD-150" in r                # la lista completa, no una lista falsa
    bot._inventario_cache.clear()


def test_sin_filtro_byte_igual_pre_76(monkeypatch):
    """La ruta sin filtro NO pasa por el catálogo: mismo texto, misma caché,
    mismo truncado que antes de #76 (gate 3 del dúo, caché y truncado)."""
    bot._inventario_cache.clear()
    llamadas = []
    monkeypatch.setattr(
        "src.rag.catalog_resolver.catalogo_cargado",
        lambda: llamadas.append(1))
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda n: [("CAD-150", 3)])
    r = bot._inventario_fabricante("Detnov")
    assert "CAD-150" in r and not llamadas   # el catálogo NI se toca
    assert bot._inventario_fabricante("Detnov") is r   # caché intacta
    bot._inventario_cache.clear()
