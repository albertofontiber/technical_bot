# -*- coding: utf-8 -*-
"""s331 — la **Wiki de modelos** (`/catalogo`): lo que el bot sabe, visible.

La pidió Alberto anotando `notifier:lt-200` en el packet de adjudicación:
«deberíamos tener un listado de modelos activos… que sea la "Wiki" de modelos
del bot… para que los DGs puedan ver los modelos que tenemos, los docs
asociados a esos modelos, y poder revisar rápido».

Lo que se fija aquí, y por qué cada cosa:

  1. **La Wiki no puede mentir sobre lo que el bot usa.** Su clase
     `consumibles` tiene que ser EXACTAMENTE el predicado del resolver
     (`catalog_store._consumable`). Si divergen, la página diría «sí tenemos
     ese modelo» de algo que el bot no consume — el peor fallo posible en una
     pantalla que existe para adjudicar.
  2. **`q` es la excepción a los filtros cerrados** y hay que probar que es
     inocua: se filtra en memoria y se recorta.
  3. **Fail-open sin mentir**: si el catálogo no se puede leer, la página lo
     DICE (el modo de fallo esperado en Vercel es que `data/catalog/` no viaje
     al bundle, y eso no puede parecer un catálogo vacío).
  4. **La ruta con parámetro pasa por la puerta**, igual que `/metricas/<x>`:
     un id inventado es 404, y sin sesión no se ve nada.
"""
from __future__ import annotations

import pytest

from dashboard import catalogo
from src.rag.catalog_store import CATALOG_DIR, load

from tests.test_s324f_dashboard_rutas import (  # noqa: F401  (fixtures)
    Cliente, _sesion_valida, entorno,
)


@pytest.fixture(autouse=True)
def _indice_limpio():
    """El índice está cacheado por proceso; cada test parte de cero."""
    catalogo.indice.cache_clear()
    yield
    catalogo.indice.cache_clear()


# ------------------------------------------------------- 1. no mentir nunca


def test_la_wiki_nunca_llama_usable_a_algo_que_el_resolver_rechaza():
    """EL invariante de la página, en el sentido que importa: si la Wiki dice
    «el bot usa este modelo», el resolver tiene que consumirlo de verdad. Al
    revés está permitido y hay 81 casos a propósito (los `redirect`), que el
    test de abajo cubre aparte."""
    cat = load(CATALOG_DIR)
    ind = catalogo.indice()
    assert ind.leido and ind.modelos, "el catálogo real no se pudo leer"
    mentiras = [m.id for m in ind.modelos
                if catalogo._clase(m) == "consumibles"
                and not cat._consumable(m.id)]
    assert not mentiras, (
        f"{len(mentiras)} modelos que la Wiki pinta como utilizables y el "
        f"resolver NO consume (primeros: {mentiras[:5]}). Es el peor fallo "
        f"posible de esta pantalla: decir «sí tenemos ese modelo» de algo con "
        f"lo que el bot no puede responder.")


def test_los_redirect_son_clase_propia_y_apuntan_a_algo_que_si_se_usa():
    """La divergencia PERMITIDA, acotada: todo lo que el resolver consume y la
    Wiki no llama `consumibles` es un `redirect`, y su destino sí es utilizable.
    Si un día apareciera otra causa, este test la destapa en vez de dejarla
    pasar como «ya sabemos que difieren»."""
    cat = load(CATALOG_DIR)
    ind = catalogo.indice()
    otros = [m for m in ind.modelos
             if cat._consumable(m.id) and catalogo._clase(m) != "consumibles"]
    assert otros, "sin redirects el test no mide nada"
    for m in otros:
        assert catalogo._clase(m) == "redirects", (
            f"{m.id} (estado={m.estado}) diverge y NO es un redirect")
        assert m.redirige_a, f"{m.id} es redirect y no dice a dónde"
        assert cat._consumable(m.redirige_a), (
            f"{m.id} redirige a {m.redirige_a}, que no es utilizable")
    # y la ficha lo ENSEÑA: el rebrand es información, no ruido a esconder
    f = catalogo.ficha(otros[0].id)
    assert f is not None and f.modelo.redirige_a


def test_el_resumen_cuadra_con_las_filas():
    """Las cifras de portada salen del MISMO índice que la tabla: si alguien
    cambia un filtro y no la cifra, esto se pone rojo."""
    resumen = catalogo.resumen()
    todos, total = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="todos", q=""))
    assert total == resumen["modelos"]
    _, sin_docs = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="sin", q=""))
    assert sin_docs == resumen["sin_docs"]


def test_un_modelo_sin_manuales_se_puede_aislar():
    """La pregunta que el markdown de adjudicación no podía contestar: ¿qué
    modelos conoce el catálogo y no cubre ningún manual?"""
    filas, total = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="sin", q=""))
    assert all(m.n_docs == 0 for m in filas)
    con, _ = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="con", q=""))
    assert all(m.n_docs > 0 for m in con)
    assert total > 0, "si esto fuera 0, el filtro no estaría midiendo nada"


def test_los_huerfanos_no_atestan_a_ningun_consumible():
    """El agujero simétrico: manuales del doc_map que no sirven a nadie
    utilizable. Si uno de ellos atestara a un consumible, el censo mentiría."""
    ind = catalogo.indice()
    consumibles = {m.id for m in ind.modelos
                   if catalogo._clase(m) == "consumibles"}
    huerfanos = {f for f, _ in ind.docs_huerfanos}
    assert huerfanos, "sin huérfanos el test no mide nada"
    for pid, docs in ind.docs_por_id.items():
        if pid not in consumibles:
            continue
        for fuente, _rol, _did in docs:
            assert fuente not in huerfanos, (
                f"{fuente} está contado como huérfano y sin embargo atesta a "
                f"{pid}, que sí es utilizable")


# ------------------------------------------------------------ 2. el filtro `q`


def test_q_busca_tambien_en_los_alias():
    """El caso REAL que lo motiva (anotación de Alberto en `kidde:zlsm-md`): la
    portada lleva el código de pedido «9-30501-KID» y justo debajo «Kidde
    MiniLaser». Quien busca por el nombre comercial tiene que encontrarlo
    aunque el canónico sea el código."""
    ind = catalogo.indice()
    conalias = [m for m in ind.modelos if ind.alias_por_id.get(m.id)]
    assert conalias, "el catálogo real no tiene alias: el test no mide nada"
    m = conalias[0]
    alias = ind.alias_por_id[m.id][0]
    filas, _ = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="todos", docs="todos", q=alias))
    assert m.id in {f.id for f in filas}


def test_q_se_recorta_y_no_sale_del_proceso():
    """`q` es la única excepción a los filtros cerrados del panel. Es segura
    porque se aplica en memoria — aquí se fija el recorte, que es la cota de
    cordura, y que un texto que no casa da lista vacía en vez de error."""
    largo = "x" * 500
    f = catalogo.normalizar({"q": [largo]}, marcas=())
    assert len(f.q) == catalogo._Q_MAX
    filas, total = catalogo.buscar(f)
    assert filas == () and total == 0


def test_los_demas_filtros_si_son_cerrados():
    """`marca`, `estado` y `docs` caen a su defecto si no están en su lista —
    la regla del panel, sin excepción."""
    f = catalogo.normalizar(
        {"marca": ["'; DROP TABLE"], "estado": ["inventado"], "docs": ["nope"]},
        marcas=("notifier",))
    assert f.marca is None
    assert f.estado == catalogo.ESTADO_DEFECTO
    assert f.docs == catalogo.DOCS_DEFECTO


# --------------------------------------------------------- 3. fail-open honesto


def test_si_el_catalogo_no_se_lee_la_pagina_lo_dice(monkeypatch, entorno):
    """El modo de fallo esperado en Vercel es que `data/catalog/` no viaje al
    bundle. Eso NO puede parecer «no hay modelos»: la página tiene que decir
    que no pudo leer el catálogo y señalar `.vercelignore`."""
    def revienta(*_a, **_k):
        raise FileNotFoundError("data/catalog/products.jsonl")

    monkeypatch.setattr(catalogo, "load", revienta)
    catalogo.indice.cache_clear()
    assert catalogo.indice().leido is False
    assert catalogo.resumen()["modelos"] == 0

    respuesta = Cliente(_sesion_valida()).get("/catalogo")
    assert respuesta.estado == 200
    assert "no se pudo leer el catálogo" in respuesta.texto.lower()
    assert "vercelignore" in respuesta.texto.lower()


# ------------------------------------------------------------- 4. las rutas


def test_la_lista_se_sirve_con_sesion(entorno):
    respuesta = Cliente(_sesion_valida()).get("/catalogo")
    assert respuesta.estado == 200
    assert "modelos que el bot usa" in respuesta.texto.lower()


def test_sin_sesion_no_se_ve_nada(entorno):
    for ruta in ("/catalogo", "/catalogo/notifier:id1000"):
        respuesta = Cliente(None).get(ruta)
        assert respuesta.estado == 303
        assert respuesta.cabecera("location") == "/entrar"


def test_la_ficha_de_un_modelo_real_pinta_sus_manuales(entorno, monkeypatch):
    """La ficha se prueba SIN red: `estado_de_documentos` es la única lectura
    remota y es fail-open, así que se anula y la página tiene que vivir igual."""
    monkeypatch.setattr(catalogo, "estado_de_documentos", lambda _ids: {})
    ind = catalogo.indice()
    m = next(m for m in ind.modelos
             if catalogo._clase(m) == "consumibles" and m.n_docs > 0)
    respuesta = Cliente(_sesion_valida()).get(f"/catalogo/{m.id}")
    assert respuesta.estado == 200
    assert m.canonico in respuesta.texto
    fuente = ind.docs_por_id[m.id][0][0]
    assert fuente[:30] in respuesta.texto


def test_un_id_inventado_es_404_no_una_consulta(entorno):
    """El sufijo de la ruta NUNCA se usa como nombre de recurso: se busca en el
    dict del catálogo. Mismo criterio que `/metricas/<clave>`."""
    respuesta = Cliente(_sesion_valida()).get("/catalogo/no:existe")
    assert respuesta.estado == 404


def test_la_ficha_no_rompe_el_sello_de_las_rutas():
    """`/catalogo/` entra en `RUTAS` y NO en `RUTAS_PUBLICAS`: hereda la puerta
    entera. Se afirma aquí además del test genérico porque es una ruta con
    parámetro, que es donde es fácil colarse."""
    from dashboard import app as panel
    assert ("GET", "/catalogo") in panel.RUTAS
    assert ("GET", "/catalogo/") in panel.RUTAS
    assert ("GET", "/catalogo") not in panel.RUTAS_PUBLICAS
    assert ("GET", "/catalogo/") not in panel.RUTAS_PUBLICAS


def test_la_wiki_es_de_SOLO_LECTURA():
    """No hay forma de escribir el catálogo desde el panel: cambiarlo pasa por
    el lote firmado con dry-run, censo y recibo. Si algún día alguien añade un
    POST aquí, este test lo para y obliga a justificarlo."""
    from dashboard import app as panel
    assert not [c for c in panel.RUTAS
                if c[1].startswith("/catalogo") and c[0] != "GET"]
    fuente = (__import__("pathlib").Path("dashboard/catalogo.py")
              .read_text("utf-8"))
    for prohibido in ("write_jsonl", "requests.post", "datos.escribir"):
        assert prohibido not in fuente
