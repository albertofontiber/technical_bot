# -*- coding: utf-8 -*-
"""s328 — La GEOMETRÍA del panel, medida por un navegador de verdad.

POR QUÉ ESTE FICHERO EXISTE. `TECH_DEBT #94` declaró que el CSS del panel no
tenía red de seguridad y puso el gatillo en «el primer cambio de estructura
posterior a s327». Lo cobró antes: las gráficas de s327 se ampliaban ×2,3 en
escritorio y los rótulos se despegaban de sus barras hasta 264 px — y en móvil
también, 81 px, sobre un layout que yo había dado por verificado. La causa de
que no se viera es estructural: los demás tests llaman a `render.*` y miran el
HTML, y **la geometría no está en el HTML, la calcula el navegador**.

LOS INVARIANTES, todos medidos sobre pantalla:
  1. **no desborda** — `scrollWidth == clientWidth` (el de s327, conservado);
  2. **la letra del gráfico NO escala** — todo el texto de las gráficas se pinta
     al MISMO tamaño, y ese tamaño es el del resto de la página. Es lo que pidió
     Alberto («el mismo tamaño de letra») y lo que ningún SVG escalado puede
     dar: una escala uniforme mueve el texto por definición. Con columnas HTML
     12 px son 12 px a cualquier anchura, y este invariante lo afirma;
  3. **el rótulo está centrado bajo su columna** — centros horizontales a menos
     de 3 px;
  4. **ningún SVG se amplía**, si alguna vez vuelve a haber uno. Hoy el panel no
     pinta SVG; la sonda se conserva porque es la que caza la clase de fallo de
     s327 y cuesta cero mantenerla.

Se SALTA si no hay Playwright o Chromium. No es opcional por comodidad: el
workflow `s328-panel-geometria.yml` lo corre con navegador siempre, y aquí se
salta para que la suite normal no dependa de un runtime de navegador.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
#: El entorno de desarrollo trae el navegador aquí y le dice a Playwright que NO
#: se lo descargue; en CI lo instala Playwright en su propia ruta. Se prueban las
#: dos, en ese orden, en vez de enlazar una a la otra desde el workflow: menos
#: fontanería y el test corre igual en los dos sitios.
#: Sobrescribible para poder EJERCITAR el camino «no hay navegador» — sin esto
#: la ruta era fija y el control de `PANEL_GEOMETRIA_EXIGIDA` no se podía probar
#: (lo intenté con `PLAYWRIGHT_BROWSERS_PATH` y no probaba nada).
CHROMIUM_DEL_ENTORNO = Path(os.getenv("PANEL_CHROMIUM",
                                      "/opt/pw-browsers/chromium"))
ANCHOS = (390, 768, 1440)
RUTAS = ("/", "/metricas", "/metricas/bot_health_daily", "/explorador", "/entrar")
DESALINEO_MAX_PX = 3.0
ESCALA_MAX = 1.01                      # 1 + holgura de redondeo del navegador

#: En CI el navegador es OBLIGATORIO. Sin esto, un fallo de runtime de Chromium
#: se leía como job VERDE (hallazgo Fable s328: un gate que degrada a skip
#: silencioso es el mismo patrón de cobertura-que-miente que #94 vino a cerrar).
#: El workflow la pone; en local, sin navegador, se salta.
EXIGIDO = os.getenv("PANEL_GEOMETRIA_EXIGIDA", "").strip() == "1"


def _sin_navegador(motivo: str):
    """Rojo si el gate es obligatorio; salto si es una corrida local."""
    if EXIGIDO:
        pytest.fail(f"PANEL_GEOMETRIA_EXIGIDA=1 y {motivo}")
    pytest.skip(motivo)


if EXIGIDO:                       # en CI la ausencia de la librería es un fallo
    import playwright.sync_api    # noqa: F401
    import uvicorn                # noqa: F401
else:
    pytest.importorskip("playwright.sync_api", reason="sin Playwright")
    pytest.importorskip("uvicorn", reason="sin uvicorn")


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(puerto: int, proceso, limite_s: float = 60.0) -> None:
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if proceso.poll() is not None:
            raise RuntimeError(
                f"el servidor murió al arrancar: {proceso.stdout.read()[:800]}")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", puerto)) == 0:
                return
    raise RuntimeError("el servidor no levantó a tiempo")


@pytest.fixture(scope="module")
def panel_servido():
    """(base_url, cookie) del panel real, con el transporte doblado."""
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "scripts.s328_panel_servidor_de_medida",
         "--puerto", str(puerto)],
        cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        cookie = proceso.stdout.readline().strip()
        assert cookie.startswith("COOKIE="), cookie
        _esperar(puerto, proceso)
        yield f"http://127.0.0.1:{puerto}", cookie[len("COOKIE="):]
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


#: Se mide TODO en una pasada del navegador y se devuelve en JSON: abrir
#: Chromium por aserción costaría minutos y el fallo se lee igual de bien.
#:
#: La sonda NO se apoya en nombres de clase (hallazgo Fable s328: buscar
#: `.etiquetas`/`.etiqueta` cazaba MI implementación de s327, no la clase de
#: error). Los rótulos de fuera se buscan como «hojas con texto en el subárbol
#: del padre del SVG», que es lo que es una columna de rótulos se llame como se
#: llame. Y un SVG sin `viewBox` ya no se salta: no se le puede medir la escala,
#: pero la ALINEACIÓN sí, y saltarlo hacía que el test 3 pasara en vacío.
_SONDA = """() => {
    const centroX = e => { const r = e.getBoundingClientRect();
                           return (r.left + r.right) / 2; };
    const px = e => parseFloat(getComputedStyle(e).fontSize);
    const raiz = document.documentElement;

    // (2) tamaños de letra REALES de todo el texto de las gráficas + el de la
    // leyenda, que es el texto pequeño de referencia del resto de la página.
    const tamanos = [];
    for (const e of document.querySelectorAll(
            '.columnas .rotulo, .columnas .dato, .leyenda'))
        tamanos.push(px(e));

    // (3) cada rótulo, centrado bajo SU columna
    let descentrado = 0, celdas = 0;
    for (const li of document.querySelectorAll('ol.columnas > li')) {
        const barra = li.querySelector('.pista'), rot = li.querySelector('.rotulo');
        if (!barra || !rot) continue;
        celdas++;
        descentrado = Math.max(descentrado, Math.abs(centroX(barra) - centroX(rot)));
    }

    // (4) ningún rótulo CORTADO por el CSS. El recorte a `_ROTULO_MAX` lo hace
    // Python y acaba en «…»; si además la banda se queda corta, el texto se
    // parte sin avisar y el gráfico miente sobre qué está midiendo.
    let recortado = 0;
    for (const rot of document.querySelectorAll('.columnas .rotulo'))
        recortado = Math.max(recortado, rot.scrollHeight - rot.clientHeight);

    // (5) si algún día vuelve a haber SVG, que no se amplíe
    let escala = null;
    for (const svg of document.querySelectorAll('svg')) {
        const vb = svg.viewBox && svg.viewBox.baseVal.width;
        const attr = parseFloat(svg.getAttribute('width'));
        const natural = vb || (Number.isFinite(attr) && attr > 0 ? attr : null);
        if (!natural) continue;
        const s = svg.getBoundingClientRect().width / natural;
        escala = escala === null ? s : Math.max(escala, s);
    }

    return {desborde: raiz.scrollWidth - raiz.clientWidth,
            tamanos: tamanos, descentrado: descentrado, celdas: celdas,
            recortado: recortado, escala: escala,
            svgs: document.querySelectorAll('svg').length};
}"""


@pytest.fixture(scope="module")
def medidas(panel_servido):
    from playwright.sync_api import Error as ErrorPlaywright, sync_playwright

    base, cookie = panel_servido
    nombre, valor = cookie.split("=", 1)
    salida = {}
    with sync_playwright() as pw:
        try:
            navegador = (pw.chromium.launch(
                             executable_path=str(CHROMIUM_DEL_ENTORNO))
                         if CHROMIUM_DEL_ENTORNO.exists()
                         else pw.chromium.launch())
        except ErrorPlaywright as exc:                       # noqa: BLE001
            _sin_navegador(f"sin Chromium utilizable: {exc}")
        try:
            ctx = navegador.new_context()
            ctx.add_cookies([{"name": nombre, "value": valor,
                              "domain": "127.0.0.1", "path": "/"}])
            pagina = ctx.new_page()
            for ancho in ANCHOS:
                pagina.set_viewport_size({"width": ancho, "height": 900})
                for ruta in RUTAS:
                    respuesta = pagina.goto(base + ruta, wait_until="networkidle")
                    assert respuesta is not None and respuesta.status == 200, \
                        f"{ruta}@{ancho} devolvió {respuesta and respuesta.status}"
                    salida[(ancho, ruta)] = pagina.evaluate(_SONDA)
        finally:
            navegador.close()
    return salida


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_ninguna_pagina_desborda_a_lo_ancho(medidas, ancho, ruta):
    """El scroll horizontal en un móvil esconde columnas sin decirlo. Que una
    gráfica con muchas columnas scrollee DENTRO de su caja es correcto; que
    scrollee la PÁGINA, no."""
    assert medidas[(ancho, ruta)]["desborde"] == 0, json.dumps(
        medidas[(ancho, ruta)])


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_la_letra_del_grafico_no_escala_y_es_la_de_la_pagina(medidas, ancho, ruta):
    """LA petición de Alberto, convertida en invariante: «el mismo tamaño de
    letra». Todo el texto de las gráficas —rótulos y cifras— se pinta al mismo
    tamaño, y ese tamaño es el de la leyenda, que es el texto pequeño del resto
    de la página. Un SVG escalado NO puede cumplir esto: la escala mueve el
    texto. Por eso el gráfico dejó de ser un SVG."""
    tamanos = medidas[(ancho, ruta)]["tamanos"]
    if not tamanos:
        pytest.skip("esta página no pinta gráficas")
    assert len(set(round(x, 2) for x in tamanos)) == 1, (
        f"{ruta}@{ancho}: la letra del gráfico no es uniforme: {sorted(set(tamanos))}")


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_cada_rotulo_esta_centrado_bajo_su_columna(medidas, ancho, ruta):
    """El heredero del invariante de s328. Entonces medía «el rótulo a la altura
    de su barra» porque eran dos sistemas de coordenadas; ahora rótulo y columna
    son el mismo `<li>`, así que esto debería ser imposible de romper — se mide
    igual, porque «debería ser imposible» es exactamente lo que se decía del
    layout anterior."""
    medida = medidas[(ancho, ruta)]
    if not medida["celdas"]:
        pytest.skip("esta página no pinta gráficas")
    assert medida["descentrado"] <= DESALINEO_MAX_PX, \
        f"{ruta}@{ancho}: rótulo a {medida['descentrado']:.1f} px del centro"


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_ningun_rotulo_se_corta_por_el_css(medidas, ancho, ruta):
    """El rótulo largo lo recorta PYTHON, con puntos suspensivos y el texto
    completo en el `title`. Si además la banda del CSS se queda corta, el texto
    se parte en silencio y la gráfica miente sobre qué está midiendo."""
    medida = medidas[(ancho, ruta)]
    if not medida["celdas"]:
        pytest.skip("esta página no pinta gráficas")
    assert medida["recortado"] == 0, \
        f"{ruta}@{ancho}: rótulo cortado {medida['recortado']} px por el CSS"


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_ningun_svg_se_amplia(medidas, ancho, ruta):
    """Hoy el panel no pinta SVG. Se conserva porque es la sonda que caza la
    clase de fallo de s327 y no cuesta nada tenerla armada."""
    medida = medidas[(ancho, ruta)]
    if medida["escala"] is None:
        assert medida["svgs"] == 0, "hay SVG sin ancho natural medible"
        pytest.skip("esta página no pinta SVG")
    assert medida["escala"] <= ESCALA_MAX, \
        f"{ruta}@{ancho}: SVG ampliado ×{medida['escala']:.2f}"


# ------------------------------------------------- los controles, VERSIONADOS


def _medir(html: str, ancho: int = 1200) -> dict:
    """Pasa la MISMA sonda del gate por una página cualquiera."""
    from playwright.sync_api import Error as ErrorPlaywright, sync_playwright

    with sync_playwright() as pw:
        try:
            navegador = (pw.chromium.launch(
                             executable_path=str(CHROMIUM_DEL_ENTORNO))
                         if CHROMIUM_DEL_ENTORNO.exists()
                         else pw.chromium.launch())
        except ErrorPlaywright as exc:                       # noqa: BLE001
            _sin_navegador(f"sin Chromium utilizable: {exc}")
        try:
            pagina = navegador.new_page(viewport={"width": ancho, "height": 600})
            pagina.set_content(html)
            return pagina.evaluate(_SONDA)
        finally:
            navegador.close()


#: Reconstrucción MÍNIMA del render de s327: SVG fluido SIN tope. Es el bug que
#: Alberto vio como «zoom». El gráfico ya no es un SVG, pero la sonda que lo
#: cazaba sigue armada y este control demuestra que sigue viva.
_PAGINA_SVG_QUE_SE_AMPLIA = """<!doctype html><html><head><style>
  body { margin:0; width:1200px; }
  svg { width:100%; height:auto; }        /* fluido y SIN max-width */
</style></head><body>
  <svg viewBox="0 0 410 56"><rect x="0" y="0" width="200" height="22"></rect></svg>
</body></html>"""


#: El fallo que le toca vigilar a la estructura NUEVA: el rótulo deja de estar
#: bajo su columna, y la letra del gráfico deja de ser la de la página.
_PAGINA_COLUMNAS_ROTA = """<!doctype html><html><head><style>
  body { margin:0; width:1200px; }
  ol.columnas { display:flex; gap:8px; list-style:none; margin:0; padding:0; }
  ol.columnas li { flex:1 1 0; display:flex; flex-direction:column; }
  .columnas .pista { height:120px; display:flex; align-items:flex-end; }
  .columnas .col { width:100%; height:60%; background:#66f; }
  .columnas .dato { font-size:12px; }
  .columnas .rotulo { font-size:19px; margin-left:60px; }  /* ni centrado ni 12px */
  .leyenda { font-size:12px; }
</style></head><body><ol class="columnas">
  <li><span class="dato">3</span><span class="pista"><span class="col"></span></span>
      <span class="rotulo">2026-08-17</span></li>
  <li><span class="dato">9</span><span class="pista"><span class="col"></span></span>
      <span class="rotulo">2026-08-18</span></li>
</ol><p class="leyenda">consultas por día</p></body></html>"""


def test_la_sonda_DISCRIMINA_un_svg_que_se_amplia():
    """El control negativo de s328, conservado. Era prosa («13 rojos con el
    render de s327») hasta que Fable señaló que nadie podía reproducirlo; desde
    entonces el patrón roto vive aquí. El gráfico ya no es un SVG, pero la sonda
    sigue armada y esto prueba que no se ha quedado ciega por el camino."""
    medida = _medir(_PAGINA_SVG_QUE_SE_AMPLIA)
    assert medida["svgs"] == 1, medida
    assert medida["escala"] > ESCALA_MAX, (
        f"la sonda NO ve la ampliación: {json.dumps(medida)}")


def test_la_sonda_DISCRIMINA_columnas_descentradas_y_con_otra_letra():
    """El control del fallo que le toca vigilar a la estructura NUEVA.

    Sin esto, los dos invariantes de columnas serían afirmaciones sin probar:
    un gate que nunca ha visto su fallo no se sabe si lo vería."""
    medida = _medir(_PAGINA_COLUMNAS_ROTA)
    assert medida["celdas"] == 2, medida
    assert medida["descentrado"] > DESALINEO_MAX_PX, (
        f"la sonda NO ve el descentrado: {json.dumps(medida)}")
    assert len(set(round(x, 2) for x in medida["tamanos"])) > 1, (
        f"la sonda NO ve la letra desigual: {json.dumps(medida)}")


def test_la_sonda_da_verde_al_render_VIGENTE():
    """La otra mitad del control: la sonda no marca lo que está bien.

    Sin esto, una sonda que dijera «roto» siempre pasaría los dos de arriba. Se
    le da lo que `render.columnas` produce HOY con la hoja de estilo REAL."""
    from dashboard import render

    grafico = str(render.columnas(
        [("2026-08-17", 2), ("2026-08-18", 5), ("2026-08-19", 1)],
        unidad="consultas", leyenda="Consultas RAG por día"))
    medida = _medir(
        "<!doctype html><html><head><style>body{margin:0;width:1200px;}"
        f"{render._ESTILO}</style></head><body>{grafico}</body></html>")

    assert medida["celdas"] == 3, medida
    assert medida["descentrado"] <= DESALINEO_MAX_PX, json.dumps(medida)
    assert len(set(round(x, 2) for x in medida["tamanos"])) == 1, json.dumps(medida)
    assert medida["svgs"] == 0, json.dumps(medida)
