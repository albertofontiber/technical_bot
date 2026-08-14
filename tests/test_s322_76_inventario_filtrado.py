# -*- coding: utf-8 -*-
"""s322 #76 (DEC-216) — Inventario con filtros de categoría/atributos + vista
agrupada.

Gates del dúo r27: el caso DORADO de Alberto dispara y filtra; los atributos
son multi-valor por-fuente; el join es catálogo ∩ doc_map (jamás pm de
chunks); honestidad sobre lo no-clasificado.

RE-CONTRATO (Alberto 14-ago, mismo día): la ruta sin filtro YA NO es
byte-igual — el inventario genérico se sirve AGRUPADO por tipología y ordenado
por familia cuando el catálogo tiene clasificación para la marca. La garantía
que se conserva: marca sin clasificación o catálogo caído → la lista plana de
siempre (degradación honesta, nunca romper el turno). Y `zonas` (centrales
convencionales) entra como clave hermana de `lazos` con la misma semántica de
capacidad «hasta N».
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


def test_filtros_zonas_convencionales():
    """(s322, Alberto) La característica de una convencional son ZONAS —
    clave hermana de lazos, jamás fusionadas."""
    assert tp.filtros_inventario(
        "¿qué centrales convencionales de 4 zonas tienes de Kidde?") == {
        "categoria": "central", "tecnologia": "convencional", "zonas": 4}


def test_zonas_de_extincion_no_es_zonas_de_deteccion():
    """(r28 Fable M3) «zonas de extinción» es un concepto DISTINTO ya presente
    en el dominio — no debe producir un filtro de zonas de detección."""
    assert tp.filtros_inventario(
        "¿qué centrales tienes para 3 zonas de extinción?") == {
        "categoria": "central"}


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
        "detnov:nc-2": {   # convencional: zonas, no lazos
            "id": "detnov:nc-2", "canonical_model": "NC-2",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "central", "cita": "c", "provenance": "t"},
            "atributos": {
                "tecnologia": [{"valor": "convencional", "doc": "d5", "cita": "x"}],
                "zonas": [{"base": 2, "max": 2, "doc": "d5", "cita": "x"}]},
        },
        "detnov:nc-8": {
            "id": "detnov:nc-8", "canonical_model": "NC-8",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "central", "cita": "c", "provenance": "t"},
            "atributos": {
                "tecnologia": [{"valor": "convencional", "doc": "d6", "cita": "x"}],
                "zonas": [{"base": 8, "max": 8, "doc": "d6", "cita": "x"}]},
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
    assert "CAD-150-4" in r and "hasta 4 lazos" in r
    assert "CAD-150-2" not in r          # capacidad 2 < 4: fuera
    assert "SAD-150" not in r            # sirena no es central
    assert "sin clasificar" in r         # MSD-X contado honesto
    assert "VIEJO" not in r              # sin docs = no lo "tenemos"


def test_filtrado_lazos_capacidad(catalogo_fake):
    """Semántica «hasta N» (Alberto 14-ago): pedir 2 lazos DEVUELVE también la
    de capacidad 4 — una central de 4 sirve para 2."""
    r = bot._inventario_fabricante("Detnov", {"lazos": 2})
    assert "CAD-150-2" in r
    assert "CAD-150-4" in r and "hasta 4 lazos" in r


def test_filtrado_zonas_capacidad(catalogo_fake):
    """Zonas con la MISMA semántica de capacidad; una convencional de 8 zonas
    sirve para 4. Y las analógicas sin dato de zonas NO se cuelan como si
    casaran: sección parcial honesta."""
    r = bot._inventario_fabricante(
        "Detnov", {"categoria": "central", "tecnologia": "convencional",
                   "zonas": 4})
    assert "NC-8" in r and "hasta 8 zonas" in r
    assert "NC-2" not in r               # capacidad 2 < 4: fuera
    assert "CAD-150-4" not in r          # analógica no es convencional


def test_inaplicable_no_es_faltante(catalogo_fake):
    """(r28 Fable M2) Una convencional con ZONAS ancladas no «carece del dato»
    de lazos — no tiene lazos como concepto. Pedir lazos la EXCLUYE (no va a
    la sección parcial como si fuera un manual incompleto), y viceversa."""
    r = bot._inventario_fabricante("Detnov", {"categoria": "central",
                                              "lazos": 2})
    assert "CAD-150-2" in r
    assert "NC-2" not in r and "NC-8" not in r      # inaplicable ≠ sin dato
    r2 = bot._inventario_fabricante("Detnov", {"categoria": "central",
                                               "zonas": 2})
    assert "NC-2" in r2
    assert "CAD-150-2" not in r2                    # analógica: zonas ajeno


def test_parcial_sin_dato_anclado_se_lista_no_se_oculta(catalogo_fake):
    """(s322 caso CAD-150-4 real) Un producto que casa en lo ANCLADO pero cuyo
    manual no especifica el atributo filtrado NI se excluye en silencio (mentir
    por omisión) NI se lista como si casara (inventar): sección propia."""
    r = bot._inventario_fabricante("Detnov", {"categoria": "sirena", "lazos": 2})
    assert "SAD-150" in r
    assert "sin dato de lazos" in r
    assert "ninguno" in r.lower()          # y el encabezado dice la verdad


def test_ninguno_casa_es_honesto(catalogo_fake):
    r = bot._inventario_fabricante("Detnov", {"categoria": "central",
                                              "lazos": 88})
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


# ---------- la vista agrupada (Alberto 14-ago) ----------

def test_sin_filtro_marca_clasificada_sale_agrupada(catalogo_fake):
    """«¿qué productos Detnov tienes?» → agrupado por tipología, ordenado por
    familia gobernada (o modelo como familia-de-uno), sin listado plano
    infinito; lo sin-clasificar contado, jamás oculto."""
    r = bot._inventario_fabricante("Detnov")
    assert "*Centrales* (4):" in r
    assert "*Sirenas* (1):" in r
    assert r.index("CAD-150-2") < r.index("CAD-150-4") < r.index("NC-2")
    assert r.index("*Centrales*") < r.index("*Sirenas*")   # orden canónico
    assert "1 productos aún sin clasificar" in r           # MSD-X
    assert "VIEJO" not in r
    assert bot._inventario_fabricante("Detnov") is r       # éxito cacheado


def test_orden_por_familia_gobernada_y_natural(monkeypatch):
    """(r28 Sol M4 + Fable m1) El campo `familia` del catálogo manda sobre el
    orden alfabético puro (ZX1E/ZX1SE se intercalarían), y dentro de familia
    el orden es NATURAL (CAD-150-4 antes que CAD-150-12)."""
    bot._inventario_cache.clear()
    def _p(pid, modelo, familia=None):
        p = {"id": pid, "canonical_model": modelo, "estado": "activo",
             "vendido_bajo": ["Detnov"],
             "clasificacion": {"categoria": "central", "cita": "c",
                               "provenance": "t"}}
        if familia:
            p["familia"] = familia
        return p
    products = {
        "detnov:zx1e": _p("detnov:zx1e", "ZX1E", "ZXe"),
        "detnov:zx1se": _p("detnov:zx1se", "ZX1SE", "ZXSe"),
        "detnov:zx2e": _p("detnov:zx2e", "ZX2E", "ZXe"),
        "detnov:c12": _p("detnov:c12", "CAD-150-12", "CAD-150"),
        "detnov:c4": _p("detnov:c4", "CAD-150-4", "CAD-150"),
    }
    doc_map = [{"document_id": f"u{i}", "source_file": f"f{i}",
                "entries": [{"id": pid, "role": "primary", "scope": "doc"}]}
               for i, pid in enumerate(products)]
    cat = types.SimpleNamespace(products=products, doc_map=doc_map,
                                follow_redirect=lambda pid: pid)
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado", lambda: cat)
    r = bot._inventario_fabricante("Detnov")
    # familias contiguas: ZX1E · ZX2E juntos, ZX1SE aparte (no intercalado)
    assert r.index("ZX1E") < r.index("ZX2E") < r.index("ZX1SE")
    # orden natural intra-familia
    assert r.index("CAD-150-4") < r.index("CAD-150-12")
    bot._inventario_cache.clear()


def test_agrupado_queda_acotado_bajo_el_limite_de_telegram(monkeypatch):
    """Cota por CONSTRUCCIÓN también en la vista agrupada: con 300 sirenas el
    texto cabe, TODA categoría aparece con su conteo y el resto se resume."""
    bot._inventario_cache.clear()
    products = {
        f"detnov:s{i:03d}": {
            "id": f"detnov:s{i:03d}", "canonical_model": f"KE-AS3{i:03d}",
            "estado": "activo", "vendido_bajo": ["Detnov"],
            "clasificacion": {"categoria": "sirena", "cita": "s",
                              "provenance": "t"}}
        for i in range(300)}
    products["detnov:c1"] = {
        "id": "detnov:c1", "canonical_model": "CAD-1", "estado": "activo",
        "vendido_bajo": ["Detnov"],
        "clasificacion": {"categoria": "central", "cita": "c", "provenance": "t"}}
    doc_map = [{"document_id": f"u{i}", "source_file": f"f{i}",
                "entries": [{"id": pid, "role": "primary", "scope": "doc"}]}
               for i, pid in enumerate(products)]
    cat = types.SimpleNamespace(products=products, doc_map=doc_map,
                                follow_redirect=lambda pid: pid)
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado", lambda: cat)
    r = bot._inventario_fabricante("Detnov")
    # (r28 Sol m1/Fable M1) cota REAL por construcción: presupuesto 3500 +
    # línea compacta de categorías restantes (≤120) + margen — no «<4096 de
    # milagro». 3700 la encierra con holgura y sin depender del caso.
    assert len(r) < 3700
    assert "*Centrales* (1):" in r and "*Sirenas* (300):" in r
    assert "más" in r                    # «…y N más» en la categoría truncada
    bot._inventario_cache.clear()


def test_sin_filtro_marca_sin_clasificacion_lista_plana_intacta(monkeypatch):
    """La garantía que SÍ se conserva del gate 3 r27: marca sin clasificación
    en el catálogo → la lista plana de siempre (misma fuente DB, misma caché,
    mismo truncado). El agrupado jamás inventa grupos sin datos."""
    bot._inventario_cache.clear()
    products = {"detnov:x1": {"id": "detnov:x1", "canonical_model": "X1",
                              "estado": "activo", "vendido_bajo": ["Detnov"]}}
    cat = types.SimpleNamespace(
        products=products,
        doc_map=[{"document_id": "u0", "source_file": "f0",
                  "entries": [{"id": "detnov:x1", "role": "primary",
                               "scope": "doc"}]}],
        follow_redirect=lambda pid: pid)
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado", lambda: cat)
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda n: [("CAD-150", 3)])
    r = bot._inventario_fabricante("Detnov")
    assert "CAD-150" in r and "referencias" in r   # el formato plano de siempre
    assert "*Centrales*" not in r
    assert bot._inventario_fabricante("Detnov") is r   # caché intacta
    bot._inventario_cache.clear()


def test_catalogo_caido_sin_filtro_sirve_lista_plana(monkeypatch):
    """Catálogo caído + sin filtros → lista plana de la DB, como siempre."""
    bot._inventario_cache.clear()
    monkeypatch.setattr("src.rag.catalog_resolver.catalogo_cargado",
                        lambda: None)
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda n: [("CAD-150", 3)])
    r = bot._inventario_fabricante("Detnov")
    assert "CAD-150" in r and "referencias" in r
    bot._inventario_cache.clear()
