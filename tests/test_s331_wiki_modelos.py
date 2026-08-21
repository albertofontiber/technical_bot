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


def test_el_catalogo_AUSENTE_no_se_pinta_como_catalogo_vacio(tmp_path, monkeypatch,
                                                              entorno):
    """EL test que faltaba, y que existe porque el fallo PASÓ DE VERDAD (s331d):
    la página salió en el preview con «0 modelos» y sin un solo aviso.

    La versión anterior de este test simulaba el fallo lanzando una excepción
    desde `load()`, y ese NO es el modo de fallo real: `catalog_store._read_jsonl`
    devuelve `[]` cuando el fichero no existe, así que con `data/catalog/` fuera
    del bundle `load()` tiene ÉXITO y entrega un catálogo vacío. El `except` no
    se disparaba nunca. Se probaba una ficción y por eso dio verde mientras la
    página mentía en producción.

    Ahora se simula lo que pasa de verdad: un directorio de catálogo VACÍO."""
    monkeypatch.setattr(catalogo, "CATALOG_DIR", tmp_path)
    catalogo.indice.cache_clear()

    # Control: `load` NO lanza sobre un directorio vacío — es justo el problema.
    from src.rag.catalog_store import load as load_real
    assert load_real(tmp_path).products == {}

    assert catalogo.indice().leido is False, (
        "un catálogo gobernado sin un solo producto no es un estado legítimo de "
        "este repo: es un fallo de despliegue y `leido` tiene que decirlo")
    assert catalogo.resumen()["modelos"] == 0

    respuesta = Cliente(_sesion_valida()).get("/catalogo")
    assert respuesta.estado == 200
    texto = respuesta.texto.lower()
    assert "no se pudo leer el catálogo" in texto
    assert "vercelignore" in texto
    # y NO debe quedar ni rastro de la pantalla de ceros plausibles
    assert "modelos que el bot usa" not in texto


def test_si_load_LANZA_tambien_se_avisa(monkeypatch, entorno):
    """El otro camino (jsonl corrupto → `load` sí lanza) sigue cubierto."""
    def revienta(*_a, **_k):
        raise ValueError("products.jsonl:12: JSON inválido")

    monkeypatch.setattr(catalogo, "load", revienta)
    catalogo.indice.cache_clear()
    assert catalogo.indice().leido is False
    assert "no se pudo leer el catálogo" in Cliente(_sesion_valida()).get(
        "/catalogo").texto.lower()


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


def _modelo_con_varios_manuales():
    ind = catalogo.indice()
    return next(m for m in ind.modelos
                if catalogo._clase(m) == "consumibles" and m.n_docs >= 3)


def test_los_superseded_van_los_ULTIMOS_de_la_lista(entorno, monkeypatch):
    """Pedido de Alberto (21-ago): los manuales reemplazados no pueden abrir la
    lista. El fallo que esto cierra es de ORDEN, así que se comprueba sobre las
    POSICIONES en el HTML, no sobre la presencia de las palabras."""
    m = _modelo_con_varios_manuales()
    docs = catalogo.indice().docs_por_id[m.id]
    # el PRIMERO del doc_map se marca superseded a propósito: sin reordenación
    # saldría el primero de la tabla, que es justo lo que Alberto vio.
    estados = {d[2]: ("active", "") for d in docs}
    estados[docs[0][2]] = ("superseded", "")
    monkeypatch.setattr(catalogo, "estado_de_documentos", lambda _ids: estados)
    pagina = Cliente(_sesion_valida()).get(f"/catalogo/{m.id}").texto
    # SOLO la tarjeta de manuales. La primera versión de este test medía sobre la
    # página entera y fallaba: el nombre del fichero aparece ANTES, dentro del
    # `provenance` de la tarjeta de identidad, así que `index` devolvía esa
    # aparición y no la de la tabla. Medir la posición del token equivocado es
    # exactamente la clase de error que las guardas G1-G6 nombran.
    html = pagina[pagina.index("manual(es)"):]
    pos_super = html.index(docs[0][0][:30])
    otros = [html.index(d[0][:30]) for d in docs[1:] if d[0][:30] in html]
    assert otros, "el test necesita al menos otro manual en la página"
    assert pos_super > max(otros), "el superseded no quedó el último"


def test_el_nombre_del_manual_ENLAZA_cuando_hay_url(entorno, monkeypatch):
    m = _modelo_con_varios_manuales()
    docs = catalogo.indice().docs_por_id[m.id]
    url = "https://ejemplo.invalid/storage/manual%20uno.pdf"
    monkeypatch.setattr(catalogo, "estado_de_documentos",
                        lambda _ids: {docs[0][2]: ("active", url)})
    html = Cliente(_sesion_valida()).get(f"/catalogo/{m.id}").texto
    assert f'href="{url}"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'target="_blank"' in html


def test_un_manual_SIN_url_no_pinta_un_enlace_roto(entorno, monkeypatch):
    """La clase de fallo de `render.esc("")` → «—» dentro de un atributo (s334):
    un documento sin `source_url` tiene que quedarse en TEXTO, no en un `href`
    vacío ni en un `href="—"` que el técnico pincharía para nada."""
    m = _modelo_con_varios_manuales()
    docs = catalogo.indice().docs_por_id[m.id]
    monkeypatch.setattr(catalogo, "estado_de_documentos",
                        lambda _ids: {d[2]: ("active", "") for d in docs})
    html = Cliente(_sesion_valida()).get(f"/catalogo/{m.id}").texto
    assert 'href=""' not in html
    assert 'href="—"' not in html
    assert docs[0][0][:30] in html          # el manual SIGUE apareciendo


def test_una_url_que_no_sea_http_NO_se_convierte_en_enlace(entorno, monkeypatch):
    """`source_url` viene de la DB, no del teclado de un visitante — pero es dato
    externo igual. Un `javascript:` en esa columna no puede acabar en un `href`
    del panel: la puerta es el esquema, no el escapado."""
    m = _modelo_con_varios_manuales()
    docs = catalogo.indice().docs_por_id[m.id]
    monkeypatch.setattr(catalogo, "estado_de_documentos",
                        lambda _ids: {docs[0][2]: ("active", "javascript:alert(1)")})
    html = Cliente(_sesion_valida()).get(f"/catalogo/{m.id}").texto
    assert "javascript:" not in html.lower()


def test_el_orden_de_manual_entierra_lo_reemplazado_y_no_lo_desconocido():
    """El rango es una decisión, no un detalle: `active` primero, lo reemplazado
    al final, y un estado que no reconocemos EN MEDIO — no sabemos que esté
    muerto, así que no se entierra."""
    o = catalogo.orden_de_manual
    assert o("active") < o("needs_review") < o("superseded") < o("retired")
    assert o("active") < o("loquesea") < o("superseded")


def test_la_pestana_de_modelos_va_DESPUES_de_errores():
    """Pedido de Alberto (21-ago). Se comprueba el ORDEN, no la pertenencia."""
    from dashboard.render import _NAV
    rutas = [r for r, _ in _NAV]
    assert rutas.index("/catalogo") > rutas.index("/errores")


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


# ------------------------------------------- 5. categoría y autocompletado (s331d)


def test_el_filtro_de_categoria_usa_clasificacion_y_no_el_campo_suelto():
    """`clasificacion.categoria` es vocabulario CERRADO y viene con cita; el
    campo suelto `categoria` es texto libre y cubre el 2%. La Wiki tiene que
    filtrar por el primero — si algún día alguien lo cambia al segundo, el
    filtro pasa de 168 modelos útiles a 21 descripciones de una sola fila."""
    import json
    from src.rag.catalog_store import CATALOG_DIR as REAL

    ind = catalogo.indice()
    crudo = [json.loads(l) for l in (REAL / "products.jsonl").read_text(
        "utf-8").splitlines() if l.strip()]
    esperado = {p["id"]: (p.get("clasificacion") or {}).get("categoria", "")
                for p in crudo if isinstance(p.get("clasificacion"), dict)}
    assert esperado, "el catálogo real no trae `clasificacion`: el test no mide nada"
    for pid, cat in esperado.items():
        if cat:
            assert ind.por_id[pid].categoria == cat.strip().lower()


def test_cada_categoria_del_desplegable_devuelve_algo():
    """El vocabulario se DERIVA del catálogo, así que ninguna opción puede salir
    vacía — es el fallo del filtro-que-no-filtra."""
    ind = catalogo.indice()
    assert ind.categorias, "sin vocabulario el test no mide nada"
    for cat in ind.categorias:
        _, total = catalogo.buscar(catalogo.Filtros(
            marca=None, estado="todos", docs="todos", q="", categoria=cat))
        assert total > 0, f"la categoría «{cat}» no devuelve ningún modelo"


def test_sin_clasificar_es_el_complemento_exacto():
    """El bucket de los no clasificados + los clasificados = el total. Si no
    cuadra, alguno se está cayendo entre dos filtros."""
    todos = len([m for m in catalogo.indice().modelos
                 if catalogo._clase(m) == "consumibles"])
    _, sin = catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="todos", q="",
        categoria=catalogo.SIN_CATEGORIA))
    con = sum(t for t in (catalogo.buscar(catalogo.Filtros(
        marca=None, estado="consumibles", docs="todos", q="", categoria=c))[1]
        for c in catalogo.indice().categorias))
    assert sin + con == todos


def test_una_categoria_inventada_cae_al_defecto():
    f = catalogo.normalizar({"categoria": ["'; DROP"]}, marcas=(),
                            categorias=("detector",))
    assert f.categoria is None


def test_el_autocompletado_ofrece_los_que_empiezan_por_lo_tecleado(entorno):
    """El pedido literal de Alberto: «si empiezo a escribir CAD ya me aparecen
    CAD-171, CAD-250». El filtrado por prefijo lo hace el NAVEGADOR sobre el
    `<datalist>`; lo que se prueba aquí es que las opciones viajan en el HTML."""
    respuesta = Cliente(_sesion_valida()).get("/catalogo")
    assert respuesta.estado == 200
    assert '<datalist id="modelos">' in respuesta.texto
    assert 'list="modelos"' in respuesta.texto
    for modelo in ("CAD-171", "CAD-250"):
        assert f'<option value="{modelo}">' in respuesta.texto, (
            f"{modelo} no viaja en el datalist: al teclear «CAD» no aparecería")


def test_las_sugerencias_respetan_los_filtros_pero_NO_el_texto():
    """Respetan categoría/marca/estado —para que sugieran lo que una búsqueda
    devolvería— e ignoran `q`, porque filtrar por el texto ya escrito es lo que
    hace el navegador: hacerlo dos veces vaciaría la lista."""
    base = catalogo.Filtros(marca=None, estado="consumibles", docs="todos",
                            q="", categoria="detector")
    con_texto = catalogo.Filtros(marca=None, estado="consumibles", docs="todos",
                                 q="zzz-no-existe", categoria="detector")
    assert catalogo.sugerencias(base) == catalogo.sugerencias(con_texto)
    _, total = catalogo.buscar(base)
    assert len(catalogo.sugerencias(base)) == total

    otra = catalogo.Filtros(marca=None, estado="consumibles", docs="todos",
                            q="", categoria="central")
    assert catalogo.sugerencias(base) != catalogo.sugerencias(otra)


def test_el_autocompletado_no_mete_javascript():
    """`<datalist>` es marcado, no script: la CSP `default-src 'none'` del panel
    sigue intacta y el panel sigue sin una línea de JS."""
    fuente = (__import__("pathlib").Path("dashboard/app.py").read_text("utf-8"))
    i = fuente.index("def pagina_catalogo(")
    j = fuente.index("def pagina_catalogo_ficha(")
    bloque = fuente[i:j]
    for prohibido in ("<script", "oninput", "onkeyup", "onchange", "javascript:"):
        assert prohibido not in bloque


# ---------------------------------- 6. el guión largo en un atributo (s334)


def test_el_buscador_no_sale_pre_relleno_con_un_guion(entorno):
    """EL fallo que encontró Alberto: `/catalogo` servía
    `<input ... value="—">` con el texto vacío, así que el primer «Aplicar»
    buscaba «—» y devolvía 0 modelos mientras la línea de sugerencias decía 72.

    Causa: `render.esc` pinta `''` como raya —convención de PRESENTACIÓN, buena
    en una celda— y esa raya dentro de `value="…"` deja de ser adorno y pasa a
    ser DATO. Se arregla con `render.atributo`, que escapa igual pero deja el
    vacío vacío."""
    import re

    texto = Cliente(_sesion_valida()).get("/catalogo").texto
    campo = re.search(r'<input type="search"[^>]*>', texto)
    assert campo, "no se encontró el buscador"
    assert 'value=""' in campo.group(0), (
        f"el buscador sale pre-relleno: {campo.group(0)}")
    assert "—" not in campo.group(0)


def test_ningun_select_manda_un_guion_como_valor():
    """La misma clase, en TODOS los desplegables del panel: la opción «todas»
    llevaba `value="—"`. Los filtros de lista cerrada lo sobrevivían por
    accidente (valor inválido → defecto), pero es dato equivocado viajando."""
    from dashboard.app import _opciones_select

    html = _opciones_select([("", "todas"), ("notifier", "notifier")], "")
    assert '<option value="" selected>todas</option>' in html
    assert 'value="—"' not in html


def test_buscar_y_sugerencias_no_pueden_contradecirse_con_el_texto_vacio():
    """Con el texto vacío, la lista y las sugerencias miran la MISMA población,
    así que no pueden contradecirse: o las dos tienen algo o las dos están
    vacías. Es exactamente lo que se veía roto (72 sugeridos, 0 resultados).

    NO se exige igualdad numérica: las sugerencias deduplican por nombre
    canónico (1.709 productos → 1.448 nombres únicos), que es lo correcto —
    ofrecer el mismo texto dos veces en un desplegable no ayuda a nadie."""
    for estado in ("consumibles", "candidates", "todos"):
        for docs in ("todos", "sin", "con"):
            f = catalogo.Filtros(marca=None, estado=estado, docs=docs, q="",
                                 categoria=None)
            _, total = catalogo.buscar(f)
            sug = catalogo.sugerencias(f)
            assert bool(sug) == bool(total), (
                f"estado={estado} docs={docs}: {total} resultados pero "
                f"{len(sug)} sugerencias — la página se contradice")
            assert len(sug) <= min(total, catalogo.TOPE_SUGERENCIAS)


def test_render_distingue_lo_que_se_lee_de_lo_que_se_envia():
    """El contrato de los dos helpers, fijado: `esc` es para lo que se LEE
    (vacío → raya), `atributo` para lo que se ENVÍA (vacío → vacío). Los dos
    escapan igual de fuerte."""
    from dashboard import render

    assert render.esc("") == "—" and render.esc(None) == "—"
    assert render.atributo("") == "" and render.atributo(None) == ""
    assert render.atributo('a"b<c') == render.esc('a"b<c')
