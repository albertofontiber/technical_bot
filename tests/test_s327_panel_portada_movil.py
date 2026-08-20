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
    html = str(render.barras([("Detnov", 4)], unidad="consultas",
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


def test_el_svg_es_fluido_y_no_lleva_medidas_fijas():
    """Con `width="410"` el gráfico se sale de un iPhone. El tamaño lo pone el
    CSS; el SVG solo lleva su sistema de coordenadas."""
    html = str(render.barras([("Detnov", 4), ("Notifier", 2)]))
    cabecera = html[html.index("<svg"):html.index(">", html.index("<svg"))]
    assert "viewBox=" in cabecera
    assert "width=" not in cabecera and "height=" not in cabecera
    assert ".grafico svg { width:100%; height:auto;" in render._ESTILO


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
    assert portada.count("<rect") == 5
    assert detalle.count("<rect") == 12
