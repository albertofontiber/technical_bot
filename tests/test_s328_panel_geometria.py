# -*- coding: utf-8 -*-
"""s328 — La GEOMETRÍA del panel, medida por un navegador de verdad.

POR QUÉ ESTE FICHERO EXISTE. `TECH_DEBT #94` declaró que el CSS del panel no
tenía red de seguridad y puso el gatillo en «el primer cambio de estructura
posterior a s327». Lo cobró antes: las gráficas de s327 se ampliaban ×2,3 en
escritorio y los rótulos se despegaban de sus barras hasta 264 px — y en móvil
también, 81 px, sobre un layout que yo había dado por verificado. La causa de
que no se viera es estructural: los demás tests llaman a `render.*` y miran el
HTML, y **la geometría no está en el HTML, la calcula el navegador**.

LOS TRES INVARIANTES, todos medidos sobre pantalla:
  1. **no desborda** — `scrollWidth == clientWidth` (el de s327, conservado);
  2. **no se AMPLÍA** — ningún SVG se pinta a más de 1 unidad de `viewBox` por
     píxel; hacia abajo sí encoge, que es lo que lo hace fluido;
  3. **el rótulo está a la altura de su barra** — centros verticales a menos de
     3 px. La sonda busca el rótulo dentro del SVG *y también* en una columna
     HTML hermana, para no quedarse ciega si alguien vuelve a partir el
     gráfico en dos sistemas de coordenadas: ese era el defecto.

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
    const centro = e => { const r = e.getBoundingClientRect();
                          return (r.top + r.bottom) / 2; };
    const anchoNatural = svg => {
        if (svg.viewBox && svg.viewBox.baseVal.width) return svg.viewBox.baseVal.width;
        const attr = parseFloat(svg.getAttribute('width'));
        return Number.isFinite(attr) && attr > 0 ? attr : null;
    };
    const rotulosDe = svg => {
        const dentro = [...svg.querySelectorAll('text')];
        if (dentro.length) return dentro.filter(e => !e.closest('title'));
        const padre = svg.parentElement;
        if (!padre) return [];
        return [...padre.querySelectorAll('*')].filter(e =>
            !svg.contains(e) && e !== svg && e.children.length === 0 &&
            (e.textContent || '').trim().length > 0);
    };
    const raiz = document.documentElement;
    let escala = null, desalineo = 0, svgs = 0;
    for (const svg of document.querySelectorAll('svg')) {
        svgs++;
        const natural = anchoNatural(svg);
        if (natural) {
            const s = svg.getBoundingClientRect().width / natural;
            escala = escala === null ? s : Math.max(escala, s);
        }
        const barras = [...svg.querySelectorAll('rect')];
        const rotulos = rotulosDe(svg);
        // Se emparejan por ORDEN: la fila i-ésima con el rótulo i-ésimo. Si el
        // SVG mete dos textos por fila (rótulo + valor), se toma el primero de
        // cada pareja quedándose con los que empiezan la fila.
        const porFila = rotulos.length >= barras.length * 2
            ? rotulos.filter((_, i) => i % 2 === 0) : rotulos;
        for (let i = 0; i < Math.min(barras.length, porFila.length); i++)
            desalineo = Math.max(desalineo,
                Math.abs(centro(barras[i]) - centro(porFila[i])));
    }
    return {desborde: raiz.scrollWidth - raiz.clientWidth,
            escala: escala, desalineo: desalineo, svgs: svgs};
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
    """El scroll horizontal en un móvil esconde columnas sin decirlo."""
    assert medidas[(ancho, ruta)]["desborde"] == 0, json.dumps(
        medidas[(ancho, ruta)])


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_ningun_grafico_se_amplia_por_encima_de_su_tamano_natural(
        medidas, ancho, ruta):
    """LA regresión de s327: sin tope, en una tarjeta ancha el SVG se pintaba
    a ×2,3 y parecía un zoom. Encoger sí; ampliar no."""
    escala = medidas[(ancho, ruta)]["escala"]
    if escala is None:
        assert medidas[(ancho, ruta)]["svgs"] == 0, \
            "hay SVG y no se le pudo medir el ancho natural: la sonda estaría ciega"
        pytest.skip("esta página no pinta gráficas")
    assert escala <= ESCALA_MAX, f"{ruta}@{ancho}: ampliado ×{escala:.2f}"


@pytest.mark.parametrize("ancho", ANCHOS)
@pytest.mark.parametrize("ruta", RUTAS)
def test_cada_rotulo_esta_a_la_altura_de_su_barra(medidas, ancho, ruta):
    """La consecuencia visible de tener DOS escalas: las filas se despegan de
    sus rótulos. Medido en s327 antes del arreglo: 264 px a 1440 y 81 px a 390."""
    desalineo = medidas[(ancho, ruta)]["desalineo"]
    assert desalineo <= DESALINEO_MAX_PX, \
        f"{ruta}@{ancho}: rótulo a {desalineo:.1f} px de su barra"


# ------------------------------------------------- el control negativo, VERSIONADO

#: Reconstrucción MÍNIMA del render de s327: SVG fluido SIN tope + los rótulos
#: FUERA, en filas HTML de 28 px fijos. Las dos mitades solo cuadran cuando el
#: SVG se pinta a 1 unidad = 1 px; en un contenedor ancho el SVG escala y los
#: rótulos no. Es exactamente el bug que Alberto vio.
_PAGINA_ROTA = """<!doctype html><html><head><style>
  body { margin:0; width:1200px; }
  .grafico { display:flex; gap:12px; align-items:flex-start; }
  .grafico svg { width:100%; height:auto; flex:1; }   /* fluido y SIN max-width */
  .etiquetas { flex:0 0 auto; padding-top:3px; }
  .etiqueta { height:22px; margin-bottom:6px; line-height:22px; font-size:13px; }
</style></head><body><div class="grafico">
  <div class="etiquetas">
    <div class="etiqueta">2026-08-08</div><div class="etiqueta">2026-08-09</div>
    <div class="etiqueta">2026-08-10</div><div class="etiqueta">2026-08-11</div>
  </div>
  <svg viewBox="0 0 410 112" preserveAspectRatio="xMinYMin meet">
    <rect x="0" y="0"  width="200" height="22" rx="3"></rect>
    <rect x="0" y="28" width="300" height="22" rx="3"></rect>
    <rect x="0" y="56" width="120" height="22" rx="3"></rect>
    <rect x="0" y="84" width="410" height="22" rx="3"></rect>
  </svg></div></body></html>"""


def test_la_sonda_DISCRIMINA_el_render_roto_de_s327():
    """EL CONTROL NEGATIVO, dentro del repo y no en prosa.

    Fable (s328) señaló que «13 rojos con el render de s327» era una afirmación
    mía no reproducible: ese render ya no existe en el árbol, así que la única
    evidencia de que el gate discrimina vivía en un comentario. Aquí el patrón
    roto se reconstruye en una página sintética y se le exige a la sonda que lo
    marque — si alguien ablanda la sonda, este test se pone rojo antes de que el
    gate empiece a mentir en verde.

    Lo que se afirma sobre la página rota, con la MISMA sonda del gate:
      · se AMPLÍA (el SVG se pinta a más de 1 unidad de `viewBox` por píxel);
      · el rótulo NO está a la altura de su barra.
    """
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
            pagina = navegador.new_page(viewport={"width": 1200, "height": 600})
            pagina.set_content(_PAGINA_ROTA)
            medida = pagina.evaluate(_SONDA)
        finally:
            navegador.close()

    assert medida["svgs"] == 1, medida
    assert medida["escala"] > ESCALA_MAX, (
        f"la sonda NO ve la ampliación del render roto: {json.dumps(medida)}")
    assert medida["desalineo"] > DESALINEO_MAX_PX, (
        f"la sonda NO ve el desalineo del render roto: {json.dumps(medida)}")


def test_la_sonda_da_verde_al_render_VIGENTE():
    """La otra mitad del control: la sonda no marca lo que está bien.

    Sin esto, una sonda que dijera «roto» siempre pasaría el test de arriba.
    Se le da el SVG que `render.barras` produce HOY, con el tope del CSS puesto.
    """
    from playwright.sync_api import Error as ErrorPlaywright, sync_playwright

    from dashboard import render

    grafico = str(render.barras([("2026-08-08", 2), ("2026-08-09", 5),
                                 ("2026-08-10", 1)], unidad="consultas"))
    pagina_sana = (
        "<!doctype html><html><head><style>body{margin:0;width:1200px;}"
        f"svg.grafico{{display:block;width:100%;height:auto;"
        f"max-width:{render.ANCHO_GRAFICO}px;}}"
        "svg.grafico .rotulo{font-size:13px;}</style></head><body>"
        f"{grafico}</body></html>")

    with sync_playwright() as pw:
        try:
            navegador = (pw.chromium.launch(
                             executable_path=str(CHROMIUM_DEL_ENTORNO))
                         if CHROMIUM_DEL_ENTORNO.exists()
                         else pw.chromium.launch())
        except ErrorPlaywright as exc:                       # noqa: BLE001
            _sin_navegador(f"sin Chromium utilizable: {exc}")
        try:
            pagina = navegador.new_page(viewport={"width": 1200, "height": 600})
            pagina.set_content(pagina_sana)
            medida = pagina.evaluate(_SONDA)
        finally:
            navegador.close()

    assert medida["escala"] <= ESCALA_MAX, json.dumps(medida)
    assert medida["desalineo"] <= DESALINEO_MAX_PX, json.dumps(medida)
