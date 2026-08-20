# -*- coding: utf-8 -*-
"""s327 — la portada de métricas de un vistazo, y que el panel se vea en el móvil.

Los dos pedidos de Alberto que fija este fichero:
  · «quiero ver todas las gráficas de un vistazo, sin scroll, con título y
    leyenda, y que al hacer click me lleve a un path con el detalle»;
  · «optimiza la web para verla desde el móvil».

Lo que se prueba de verdad, no por aproximación: que la ruta con parámetro
HEREDA la puerta de sesión (es la primera del panel y sería el sitio natural
para saltársela sin querer), que la clave sale de una lista CERRADA, que el SVG
es fluido (medidas fijas = gráfico saliéndose de la pantalla en un móvil) y que
el CSS lleva la regla anti-zoom de iOS que documenta el war room.
"""
from __future__ import annotations

import re

import pytest

from dashboard import app as panel
from dashboard import datos, explorador, render


# ------------------------------------------------------------------- dobles


FILAS_VISTA = [
    {"semana": "2026-08-17", "categoria": "catalogo_especificaciones",
     "taxonomia_version": 7, "consultas": 9, "personas": 1,
     "dia": "2026-08-17", "consultas_rag": 9, "usuarios_unicos": 1,
     "marca": "Detnov", "modelo": "CAD-250", "quien": "Alberto",
     "marca_libre": "hochiki", "menciones": 2, "motivo": "info", "votos": 3,
     "turnos_degradados": 0, "votos_up": 1, "votos_down": 2},
]


@pytest.fixture()
def doble(monkeypatch):
    def _leer(recurso, params, presupuesto=None):
        if recurso == "documents":
            return datos.Resultado(datos.OK, [{"manufacturer": "Detnov"}])
        return datos.Resultado(datos.OK, list(FILAS_VISTA))

    monkeypatch.setattr(datos, "leer", _leer)
    monkeypatch.setattr(panel.gestion, "listar_allowlist",
                        lambda: datos.Resultado(datos.VACIO))
    monkeypatch.setattr(panel.gestion, "listar_invitaciones",
                        lambda: datos.Resultado(datos.VACIO))
    monkeypatch.setattr(panel.gestion, "resumen_acceso",
                        lambda *a, **k: {"con_acceso": 2, "revocados": 0,
                                         "pendientes": 0, "usadas": 1})
    monkeypatch.setattr(panel.errores, "leer",
                        lambda dias: (datos.Resultado(datos.VACIO),
                                      datos.Resultado(datos.VACIO)))
    monkeypatch.setattr(datos, "salud", lambda: {"estado": datos.OK,
                                                 "desde": "2026-04-07",
                                                 "hasta": "2026-08-20",
                                                 "tardanza_ms": 120,
                                                 "detalle": ""})


def _peticion(ruta="/", consulta=None):
    return panel.Peticion(
        metodo="GET", ruta=ruta, consulta=consulta or {}, cabeceras={},
        cuerpo=b"", ip="1.2.3.4", nonce="nonce-de-pruebas",
        sesion={"u": "alberto", "csrf": "token"})


# ------------------------------------------------------------------ portada


def test_la_portada_pinta_todas_las_graficas_con_enlace_a_su_detalle(doble):
    texto = panel.pagina_resumen(_peticion()).cuerpo.decode("utf-8")
    assert 'class="panel-graficos"' in texto
    con_grafico = [v for v in datos.VISTAS if v.grafico]
    assert len(con_grafico) >= 8
    for vista in con_grafico:
        assert f'href="/metricas/{vista.clave}"' in texto, vista.clave
        assert vista.titulo in texto, vista.clave


def test_toda_grafica_declarada_tiene_leyenda():
    """«Que estas gráficas tengan título y leyenda» — el título es `titulo` y la
    leyenda se declara al lado del gráfico; sin ella, una barra es un número
    sin unidad ni ventana."""
    for vista in datos.VISTAS:
        if vista.grafico:
            assert vista.leyenda, f"{vista.clave} tiene gráfico y no leyenda"


def test_la_leyenda_se_pinta_bajo_las_barras():
    html = str(render.columnas([("Detnov", 4)], unidad="consultas",
                               leyenda="Suma de las semanas cargadas"))
    assert 'class="leyenda"' in html and "Suma de las semanas cargadas" in html


# ------------------------------------------------------- ruta con parámetro


def test_el_detalle_de_una_vista_declarada_responde(doble):
    vista = next(v for v in datos.VISTAS if v.grafico)
    respuesta = panel.pagina_metrica_detalle(_peticion(f"/metricas/{vista.clave}"))
    texto = respuesta.cuerpo.decode("utf-8")
    assert respuesta.estado == 200
    assert vista.titulo in texto
    assert f"Vista SQL: {vista.clave}" in texto
    assert 'href="/"' in texto            # migas de vuelta


def test_una_clave_inventada_es_404_y_no_llega_a_postgrest(monkeypatch):
    def _prohibido(recurso, params):
        raise AssertionError("una clave no declarada no puede leer nada")

    monkeypatch.setattr(datos, "leer", _prohibido)
    respuesta = panel.pagina_metrica_detalle(
        _peticion("/metricas/query_logs?select=*"))
    assert respuesta.estado == 404


def test_la_ruta_con_parametro_hereda_la_puerta_de_sesion(monkeypatch):
    """La primera ruta con parámetro del panel: si `despachar` la resolviera
    ANTES de la puerta, sería un agujero. Sin cookie ⇒ 303 a la entrada."""
    monkeypatch.setenv(panel.sesion.VARIABLE_SECRETO,
                       "secreto-de-pruebas-con-longitud-mas-que-suficiente")
    peticion = panel.Peticion(
        metodo="GET", ruta="/metricas/bot_marcas_semanal", consulta={},
        cabeceras={}, cuerpo=b"", ip="1.2.3.4", nonce="n")
    respuesta = panel.despachar(peticion)
    assert respuesta.estado == 303
    assert dict(respuesta.extra).get("location") == "/entrar"


def test_una_ruta_bajo_metricas_que_no_existe_no_abre_nada():
    peticion = panel.Peticion(
        metodo="POST", ruta="/metricas/lo-que-sea", consulta={},
        cabeceras={"host": "panel"}, cuerpo=b"", ip="1.2.3.4", nonce="n")
    assert panel.despachar(peticion).estado == 404   # POST no está enrutado


# -------------------------------------------------------------------- móvil


def test_s328b_el_rotulo_y_su_columna_son_EL_MISMO_elemento():
    """La clase de fallo de s328, ELIMINADA en vez de vigilada.

    Aquella era «dos sistemas de coordenadas que tienen que coincidir»: el SVG
    escalaba y los rótulos, en HTML aparte, no. Con columnas HTML el rótulo y su
    barra son hijos del MISMO `<li>` de la rejilla, así que no hay dos cosas que
    puedan desalinearse — no queda nada que medir, queda que comprobar que la
    estructura es esa.
    """
    html = str(render.columnas([("2026-08-17", 3), ("2026-08-18", 9)]))
    celdas = re.findall(r"<li .*?</li>", html)
    assert len(celdas) == 2
    for celda in celdas:
        assert 'class="pista"' in celda and 'class="rotulo"' in celda
    assert "<svg" not in html          # ya no hay SVG que pueda escalar


def test_s328b_la_altura_viaja_en_CLASE_y_no_en_un_atributo():
    """La CSP dice `default-src 'none'`: la geometría de la barra no puede ir en
    un atributo de estilo. Va en una clase de una tabla fija que la hoja de
    estilo trae entera, y por eso el gate de `style=` sigue verde."""
    html = str(render.columnas([("a", 1), ("b", 4)]))
    assert "style=" not in html
    clases = re.findall(r'class="col h(\d+)"', html)
    assert clases == ["25", "100"]                    # 1/4 y 4/4
    for altura in clases:
        assert f".columnas .col.h{altura} {{ height:{altura}%; }}" in render._ESTILO


def test_s328b_la_tabla_de_alturas_esta_ENTERA_en_la_hoja():
    """Una barra con una altura sin regla se pintaría a cero, en silencio."""
    reglas = re.findall(r"\.columnas \.col\.h(\d+) \{", render._ESTILO)
    assert sorted(int(x) for x in reglas) == list(range(render._PASOS_ALTURA))


def test_s328b_un_valor_pequeno_no_se_lee_como_cero():
    """1 de 1000 es «poco», no «nada»: la barra baja hasta 1 %, no hasta 0. El
    0 de verdad SÍ es 0 — «hoy no hubo tráfico» es un dato."""
    html = str(render.columnas([("mucho", 1000), ("poco", 1), ("nada", 0)]))
    assert re.findall(r'class="col h(\d+)"', html) == ["100", "1", "0"]


def test_s328b_el_rotulo_largo_se_recorta_pero_no_se_pierde():
    """Bajo una columna de 44 px no cabe `catalogo_especificaciones`. Se recorta
    en pantalla y el texto completo queda en el `title` de la columna."""
    largo = "catalogo_especificaciones"
    html = str(render.columnas([(largo, 3)], unidad="consultas"))
    assert f'title="{largo}: 3 consultas"' in html
    assert ">catalogo_es…<" in html       # 12 caracteres, `_ROTULO_MAX`
    assert f">{largo}<" not in html


def test_el_css_lleva_las_reglas_de_movil_del_war_room():
    css = render._ESTILO
    assert "@media (max-width:639px)" in css          # pivot `sm` del war room
    assert "input, select, textarea { font-size:16px; }" in css   # anti-zoom iOS
    assert "min-height:44px" in css                   # tap target Apple HIG


def test_la_rejilla_se_adapta_sin_media_queries():
    css = render._ESTILO
    assert "grid-template-columns:repeat(auto-fit, minmax(280px, 1fr))" in css


def test_las_tablas_anchas_se_reescriben_como_tarjetas_en_movil():
    """Una tabla de nueve columnas en un móvil enseña dos. Con `cards=True`
    cada celda lleva su etiqueta y el CSS la reescribe como tarjeta — el pivot
    tabla→cards del war room, aquí sin JS."""
    html = str(render.tabla(["Cuándo", "Pregunta"],
                            [["2026-08-18", "¿cuántos lazos?"]], cards=True))
    assert 'class="cards"' in html
    assert 'data-etiqueta="Cuándo"' in html and 'data-etiqueta="Pregunta"' in html
    css = render._ESTILO
    assert "table.cards thead { display:none; }" in css
    assert "content:attr(data-etiqueta)" in css
    # y el valor ENVUELVE en la tarjeta en vez de cortarse
    assert "overflow-wrap:anywhere" in css


def test_sin_cards_la_tabla_no_lleva_etiquetas_repetidas():
    """El modo tarjetas es opt-in: las tablas estrechas (gestión de acceso) no
    pagan un atributo por celda."""
    html = str(render.tabla(["a", "b"], [["1", "2"]]))
    assert "data-etiqueta" not in html and 'class="cards"' not in html


def test_las_tablas_pueden_desbordar_sin_romper_la_pagina():
    html = str(render.tabla(["a", "b"], [["1", "2"]]))
    assert 'class="scroll"' in html
    assert ".scroll { overflow-x:auto" in render._ESTILO


# ------------------------------------------------- el eje pregunta/no-pregunta


def test_el_explorador_lista_solo_preguntas_por_defecto():
    filtros = explorador.normalizar({}, categorias=("otros",), marcas=[])
    assert filtros.tipo == "preguntas"
    assert explorador.parametros(filtros)["es_pregunta"] == "is.true"


@pytest.mark.parametrize("tipo,esperado", [
    ("preguntas", "is.true"),
    ("no_preguntas", "is.false"),
    ("todos", None),
    ("inventado", "is.true"),        # fuera de lista ⇒ defecto
])
def test_el_filtro_de_tipo_es_lista_cerrada(tipo, esperado):
    filtros = explorador.normalizar({"tipo": [tipo]}, categorias=("otros",),
                                    marcas=[])
    assert explorador.parametros(filtros).get("es_pregunta") == esperado


# ------------------------------------------- el presupuesto de tiempo (Sol)


def test_sin_presupuesto_agotado_se_lee_normal(monkeypatch):
    from dashboard.datos import Presupuesto
    presupuesto = Presupuesto(30)
    assert not presupuesto.agotado() and presupuesto.restante() > 25


def test_agotado_el_presupuesto_la_lectura_ni_se_intenta(monkeypatch):
    """El fallo que evita (hallazgo Sol s327): la portada encadena ~16 lecturas
    de hasta 10 s y la función de Vercel muere a los 30 s — sin tope, la página
    entera se va en un 504 en vez de pintar sus tarjetas con su estado."""
    from dashboard.datos import Presupuesto

    def _prohibido(*a, **k):
        raise AssertionError("con el presupuesto agotado no se llama a la red")

    monkeypatch.setattr(datos.httpx, "Client", _prohibido)
    monkeypatch.setattr(datos, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(datos, "SUPABASE_SERVICE_KEY", "clave")
    resultado = datos.leer("bot_marcas_semanal", {}, Presupuesto(0))
    assert resultado.estado == datos.SIN_TIEMPO


def test_la_portada_dice_cuando_no_dio_tiempo(monkeypatch):
    """«No dio tiempo» y «Supabase falló» son mensajes distintos: el segundo
    manda a mirar la infraestructura y el primero, a abrir el detalle."""
    texto = str(panel._pintar_resultado(
        datos.Resultado(datos.SIN_TIEMPO, detalle="bot_marcas_semanal"),
        que="datos de esa vista"))
    assert "No dio tiempo" in texto
    assert "detalle" in texto


def test_la_portada_acota_las_barras_para_que_quepa(doble):
    """«De un vistazo» con 14 barras por tarjeta no es de un vistazo: en la
    portada cada gráfica enseña las 5 de más peso y el detalle, la serie."""
    assert panel.BARRAS_EN_PORTADA == 5
    vista = next(v for v in datos.VISTAS if v.grafico and v.grafico_agregado)
    muchas = datos.Resultado(datos.OK, [
        {vista.grafico[0]: f"e{i}", vista.grafico[1]: 20 - i} for i in range(12)])
    portada = str(panel._grafico_de_vista(vista, muchas,
                                          tope=panel.BARRAS_EN_PORTADA))
    detalle = str(panel._grafico_de_vista(vista, muchas))
    assert portada.count("<li ") == 5
    assert detalle.count("<li ") == 12


# ---------------------------------------------- la fuente de marca de la puerta


def test_s328c_la_fuente_cubre_TODO_el_logotipo():
    """Un glifo que falte cae a la serif del sistema y el titular sale con DOS
    tipografías, que es peor que no poner fuente de marca. El subconjunto se
    recortó al texto del logotipo: si alguien cambia el texto sin regenerar
    (`python -m scripts.s328c_recortar_fuente_marca`), esto se pone rojo."""
    from dashboard import fuente_marca

    peticion = panel.Peticion(
        metodo="GET", ruta="/entrar", consulta={}, cabeceras={}, cuerpo=b"",
        ip="1.2.3.4", nonce="n", sesion=None)
    html = panel.pagina_entrar(peticion).cuerpo.decode("utf-8")
    logotipo = re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)
    letras = set(re.sub(r"<[^>]+>", "", logotipo).replace("&nbsp;", " "))
    faltan = letras - set(fuente_marca.GLIFOS)
    assert not faltan, f"el logotipo usa glifos que la fuente no trae: {faltan}"


def test_s328c_la_fuente_solo_viaja_en_la_puerta():
    """3 KB y una apertura de la CSP no los paga una página que no pinta el
    logotipo. El `@font-face` se inyecta por `clase_cuerpo`, no está en la hoja
    común."""
    from dashboard import fuente_marca

    marca = fuente_marca.PLAYFAIR_PUERTA_B64[:40]
    assert marca not in render._ESTILO                    # no en la hoja común
    puerta = render.pagina("x", render.nota("y"), nonce="n",
                           clase_cuerpo="entrada")
    otra = render.pagina("x", render.nota("y"), nonce="n")
    assert "@font-face" in puerta and marca in puerta
    assert "@font-face" not in otra and marca not in otra


def test_s328c_la_csp_abre_font_src_SOLO_en_la_puerta():
    """`font-src data:` es una apertura real de una CSP que hoy es
    `default-src 'none'`. Vive en la respuesta de `/entrar` y en ninguna otra."""
    puerta = dict(panel._cabeceras_seguridad("n", fuente=True))
    resto = dict(panel._cabeceras_seguridad("n"))
    assert "font-src data:" in puerta["content-security-policy"]
    assert "font-src" not in resto["content-security-policy"]
    # y NINGUNA de las dos deja entrar a un tercero
    for cabecera in (puerta, resto):
        assert "googleapis" not in cabecera["content-security-policy"]
        assert "gstatic" not in cabecera["content-security-policy"]


def test_s328c_la_puerta_declara_que_incrusta_la_fuente():
    """El flag de la respuesta es lo que abre la CSP: si `pagina_entrar` deja de
    ponerlo, la fuente se incrusta y el navegador la bloquea, en silencio."""
    peticion = panel.Peticion(
        metodo="GET", ruta="/entrar", consulta={}, cabeceras={}, cuerpo=b"",
        ip="1.2.3.4", nonce="n", sesion=None)
    assert panel.pagina_entrar(peticion).fuente_incrustada is True
