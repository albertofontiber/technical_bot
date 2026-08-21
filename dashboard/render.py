# -*- coding: utf-8 -*-
"""El HTML del panel: se compone AQUÍ, en el servidor, y sale cocinado.

POR QUÉ NO HAY MOTOR DE PLANTILLAS. Jinja2 haría el trabajo, pero traería su
propio modelo de escapado que hay que configurar bien (`autoescape=True` no es
el default de la librería) y un directorio de plantillas donde la lógica se
escurre. Aquí el problema es pequeño y la propiedad que hay que garantizar es
UNA: que ningún texto de nadie llegue al navegador sin escapar. Se garantiza con
un tipo, no con disciplina — `Seguro` marca lo que YA es HTML, y todo lo demás
pasa por `html.escape` al pintarse. Lo que no está marcado, se escapa; olvidarse
del marcador falla hacia el lado seguro (se ve el `<b>` en pantalla), que es el
único sentido aceptable para un fallo de escapado.

POR QUÉ NO HAY JAVASCRIPT NI FICHEROS ESTÁTICOS. La CSP del panel dice
`default-src 'none'` (no `script-src 'none'`, que es lo que decía este párrafo
hasta s328 — hallazgo Fable): no hay script propio ni ajeno que pueda ejecutarse,
y tampoco fuente, imagen ni conexión de fuera. Así que
un XSS —si se colara pese al párrafo anterior— no tiene dónde correr. Y sin
ficheros estáticos no hay ruta que sirva ficheros, que es no tener por dónde
recorrer un directorio. Los gráficos son SVG generado aquí, con la geometría en
ATRIBUTOS (`width`, `x`) y no en `style="..."`: un atributo `style` sería
«inline style» y obligaría a abrir la CSP con `unsafe-inline`, tirando la
protección para pintar cuatro barras.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from .fuente_marca import PLAYFAIR_PUERTA_B64


class Seguro(str):
    """HTML ya escapado. El único tipo que `_pintar` deja pasar tal cual."""


def esc(valor: object) -> str:
    """Cualquier cosa → texto seguro para incrustar. `None` y `''` se pintan
    como raya: una celda vacía y una celda con `None` se leen igual de mal."""
    if valor is None or valor == "":
        return "—"
    return html.escape(str(valor), quote=True)


def atributo(valor: object) -> str:
    """Como `esc`, pero para el VALOR DE UN ATRIBUTO: el vacío se queda vacío.

    POR QUÉ EXISTE (s334, fallo real que encontró Alberto en `/catalogo`): `esc`
    pinta `None` y `''` como raya —convención de PRESENTACIÓN, correcta en una
    celda de tabla— y esa misma raya, metida en `value="…"`, deja de ser un
    adorno y pasa a ser DATO. El buscador de la Wiki salía con un guión largo
    dentro, así que el primer «Aplicar» buscaba «—» y devolvía 0 modelos
    mientras la línea de sugerencias decía 72. Y no era sólo ahí: la opción
    «todas» de TODOS los desplegables del panel emitía `value="—"`; los filtros
    de lista cerrada lo sobrevivían por accidente (valor inválido → defecto),
    el texto libre no.

    La distinción que este helper nombra: `esc` es para lo que se LEE, `atributo`
    para lo que se ENVÍA. Escapa igual de fuerte (`quote=True`)."""
    return "" if valor is None else html.escape(str(valor), quote=True)


def _pintar(valor: object) -> str:
    return str(valor) if isinstance(valor, Seguro) else esc(valor)


def unir(partes) -> Seguro:
    return Seguro("".join(_pintar(p) for p in partes))


# ------------------------------------------------------------------ formato


def numero(valor: object) -> str:
    """`1234.0` → `1.234`. Separador de miles con punto (castellano) y los
    decimales sólo si los hay de verdad."""
    if valor is None or valor == "":
        return "—"
    try:
        numero_ = float(valor)
    except (TypeError, ValueError):
        return esc(valor)
    if numero_ == int(numero_):
        return f"{int(numero_):,}".replace(",", ".")
    return f"{numero_:,.1f}".replace(",", "@").replace(".", ",").replace("@", ".")


def milisegundos(valor: object) -> str:
    """Latencias en la unidad en que se piensan: por encima de 1 s, en segundos."""
    if valor is None or valor == "":
        return "—"
    try:
        ms = float(valor)
    except (TypeError, ValueError):
        return esc(valor)
    return f"{ms / 1000:.1f} s" if ms >= 1000 else f"{int(ms)} ms"


def porcentaje(valor: object) -> str:
    if valor is None or valor == "":
        return "—"
    try:
        # Coma decimal, igual que `numero`: dos convenciones distintas en la
        # misma tabla se leen como un error de la tabla.
        return f"{float(valor):.1f} %".replace(".", ",")
    except (TypeError, ValueError):
        return esc(valor)


def fecha(valor: object) -> str:
    """ISO de PostgREST → `2026-08-17 10:00`. Lo ilegible se enseña recortado,
    no se esconde: una fecha rara es información."""
    if not valor:
        return "—"
    texto = str(valor)
    try:
        return (datetime.fromisoformat(texto.replace("Z", "+00:00"))
                .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    except ValueError:
        return esc(texto[:16])


def recorte(valor: object, ancho: int) -> str:
    """Texto de persona, acotado. Se usa para las preguntas de los técnicos y
    para los comentarios del 👎: el panel enseña el PATRÓN, y cada carácter de
    más es texto libre de alguien en una pantalla que no lo necesita."""
    if valor is None or valor == "":
        return "—"
    texto = " ".join(str(valor).split())
    return esc(texto if len(texto) <= ancho else texto[: ancho - 1] + "…")


# ---------------------------------------------------------------- componentes


def tabla(cabeceras, filas, *, vacio: str = "Sin datos todavía.",
          cards: bool = False) -> Seguro:
    """Una tabla. Con `cards=True` cada celda lleva su etiqueta en un atributo y
    el CSS la reescribe como TARJETA por debajo de 640 px.

    Por qué (s327): una tabla de nueve columnas en un móvil enseña dos y esconde
    siete detrás de un scroll horizontal que nadie descubre. Es el mismo pivot
    que el war room aplicó a su tabla de empresas (`docs/RESPONSIVE.md`:
    «TablaEmpresas cards en <md»), aquí sin JS y sin duplicar el HTML: una clase
    y un `data-etiqueta` por celda. El `content:attr(...)` del CSS no es «inline
    style», así que la CSP sigue intacta.
    """
    if not filas:
        return nota(vacio)
    etiquetas = [str(_pintar(c)) for c in cabeceras]
    cabeza = unir(Seguro(f"<th>{_pintar(c)}</th>") for c in cabeceras)
    cuerpo_filas = []
    for fila in filas:
        celdas = []
        for indice, celda in enumerate(fila):
            etiqueta = (f' data-etiqueta="{esc(etiquetas[indice])}"'
                        if cards and indice < len(etiquetas) else "")
            celdas.append(f"<td{etiqueta}>{_pintar(celda)}</td>")
        cuerpo_filas.append(Seguro("<tr>" + "".join(celdas) + "</tr>"))
    clase = ' class="cards"' if cards else ""
    return Seguro(
        f'<div class="scroll"><table{clase}><thead><tr>{cabeza}</tr></thead>'
        f"<tbody>{unir(cuerpo_filas)}</tbody></table></div>"
    )


#: Alturas posibles de una columna, en porcentaje de la pista. Se emiten UNA vez
#: en la hoja de estilo (101 reglas, ~2 KB) y cada barra elige la suya por clase.
#: Es el rodeo que impone la CSP: un atributo `style` con la altura sería un
#: «inline style» y obligaría a abrir `unsafe-inline`. Una clase por punto
#: porcentual no crece con el número de gráficas ni de barras — es tabla fija.
_PASOS_ALTURA = 101

#: Ancho mínimo de una columna. Por debajo, el rótulo no se lee y el objetivo
#: táctil desaparece; cuando no caben, el gráfico hace scroll DENTRO de su caja
#: (nunca la página, que es lo que mide el gate de geometría).
_COLUMNA_MIN_PX = 44

#: A 12 px de rótulo VERTICAL entran 12 caracteres en los 88 px de la banda.
#: La cifra NO es a ojo: con 14 el gate de geometría midió 11 px de texto
#: cortado en escritorio y 23 en móvil, con los ids largos de la taxonomía
#: (`catalogo_especificaciones`) puestos a propósito en el arnés de medida.
#: El texto completo no se pierde: va en el `title` de la columna.
_ROTULO_MAX = 12


def columnas(pares, *, unidad: str = "", leyenda: str = "") -> Seguro:
    """Un gráfico de COLUMNAS, en HTML y CSS. Sin JavaScript y sin SVG.

    `pares` = [(etiqueta, valor)], y se pintan de IZQUIERDA A DERECHA en el orden
    en que llegan — que es lo que Alberto pidió y lo que una serie temporal
    necesita: el tiempo avanza hacia la derecha. La altura codifica el valor,
    escalada al máximo de la serie; si todos son 0 se enseñan igual (columnas a
    cero), porque «hoy no hubo tráfico» es un dato y no un fallo.

    POR QUÉ NO ES UN SVG (s328b). Lo era, y el SVG obligaba a elegir entre dos
    males: con medidas fijas se salía del móvil, y fluido escalaba TODO —incluida
    la letra—, así que en una tarjeta estrecha los rótulos caían a ~8 px,
    ilegibles y descuadrados con el resto de la página. No hay ajuste que lo
    arregle: una escala uniforme mueve el texto por definición. En HTML el texto
    es texto —12 px son 12 px a cualquier anchura— y la barra es lo único que
    estira, con su altura en porcentaje. De paso desaparece la clase de fallo
    entera de s328: no hay dos sistemas de coordenadas que puedan desalinearse,
    porque rótulo y columna son el MISMO elemento de la rejilla.

    `leyenda` explica QUÉ se está midiendo (unidad, ventana, si suma semanas).
    """
    pares = [(e, v) for e, v in pares if isinstance(v, (int, float))]
    if not pares:
        return Seguro("")
    tope = max((v for _, v in pares), default=0) or 1
    celdas = []
    for etiqueta, valor in pares:
        # Redondeo al entero: es el paso de la tabla de clases. Una barra con
        # valor > 0 nunca baja de 1 % para que «poco» no se lea como «nada».
        altura = int(round(_PASOS_ALTURA - 1) * (valor / tope)) if tope else 0
        altura = max(1, altura) if valor > 0 else 0
        rotulo = str(etiqueta)
        corto = (rotulo if len(rotulo) <= _ROTULO_MAX
                 else rotulo[:_ROTULO_MAX - 1] + "…")
        texto = f"{numero(valor)}{(' ' + unidad) if unidad else ''}"
        celdas.append(
            f'<li title="{esc(rotulo)}: {esc(texto)}">'
            f'<span class="dato">{esc(numero(valor))}</span>'
            f'<span class="pista"><span class="col h{altura}"></span></span>'
            f'<span class="rotulo">{esc(corto)}</span></li>'
        )
    pie = (f'<p class="leyenda">{esc(leyenda)}</p>') if leyenda else ""
    return Seguro(
        f'<div class="grafico"><ol class="columnas">{"".join(celdas)}</ol></div>'
        f"{pie}"
    )


def panel_graficos(elementos) -> Seguro:
    """La rejilla de la portada: cada elemento es una GRÁFICA CLICABLE con su
    título y su leyenda. `elementos` = [(titulo, href, cuerpo)].

    Una sola regla de layout (`auto-fit` + `minmax`) sirve móvil, tablet y
    escritorio sin media queries: 1 columna cuando no caben 280 px dos veces,
    2-3 cuando caben. Es la traducción CSS-only del pivot `sm/lg` del war room
    (`docs/RESPONSIVE.md`) a un panel que no tiene Tailwind ni JS.
    """
    tarjetas = []
    for titulo, href, cuerpo in elementos:
        tarjetas.append(Seguro(
            f'<a class="tarjeta grafica" href="{esc(href)}">'
            f'<h2>{esc(titulo)}</h2>{_pintar(cuerpo)}'
            f'<span class="ver-mas">Ver detalle →</span></a>'
        ))
    return Seguro(f'<div class="panel-graficos">{"".join(tarjetas)}</div>')


def tarjeta(titulo: str, cuerpo, *, pregunta: str = "",
            pie: str = "", enlace: tuple[str, str] | None = None) -> Seguro:
    """Una tarjeta del panel. `enlace` = (destino, texto) añade al pie un enlace
    —lo usa el índice de métricas para llevar al detalle de cada una (s327)."""
    cabecera = f"<h2>{esc(titulo)}</h2>" if titulo else ""
    sub = f'<p class="pregunta">{esc(pregunta)}</p>' if pregunta else ""
    partes = []
    if pie:
        partes.append(f'<p class="pie">{esc(pie)}</p>')
    if enlace:
        destino, texto = enlace
        partes.append(f'<p class="pie"><a href="{esc(destino)}">{esc(texto)}</a></p>')
    return Seguro(f'<section class="tarjeta">{cabecera}{sub}'
                  f'{_pintar(cuerpo)}{"".join(partes)}</section>')


def nota(texto: str) -> Seguro:
    return Seguro(f'<p class="nota">{esc(texto)}</p>')


def aviso(texto: str, *, tono: str = "aviso") -> Seguro:
    """`tono` ∈ {aviso, error, bien}. Se valida contra la lista: el tono acaba
    en un `class=` del HTML y no puede venir de fuera sin filtrar."""
    tono = tono if tono in ("aviso", "error", "bien") else "aviso"
    return Seguro(f'<p class="banda {tono}">{esc(texto)}</p>')


def cifra(valor: object, etiqueta: str, *, detalle: str = "") -> Seguro:
    extra = f'<div class="detalle">{esc(detalle)}</div>' if detalle else ""
    return Seguro(
        f'<div class="cifra"><div class="valor">{_pintar(valor)}</div>'
        f'<div class="rotulo">{esc(etiqueta)}</div>{extra}</div>'
    )


def rejilla(elementos) -> Seguro:
    return Seguro(f'<div class="rejilla">{unir(elementos)}</div>')


def formulario(accion: str, csrf: str, cuerpo, *,
               boton: str, peligroso: bool = False) -> Seguro:
    """Todo formulario del panel pasa por aquí, y por eso todos llevan CSRF: es
    imposible escribir uno que se olvide del token sin escribir el `<form>` a
    mano."""
    clase = "peligro" if peligroso else "principal"
    return Seguro(
        f'<form method="post" action="{esc(accion)}">'
        f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
        f"{_pintar(cuerpo)}"
        f'<button type="submit" class="{clase}">{esc(boton)}</button></form>'
    )


# --------------------------------------------------------------------- página

#: El orden lo fija Alberto (21-ago: «la tab de wiki de manuales ponla después
#: de "errores", no antes»). No es cosmético: la Wiki es una vista de referencia,
#: no algo que se mire en cada visita, así que va al final de la barra.
_NAV = (
    ("/", "Resumen"),
    ("/acceso", "Acceso"),
    ("/metricas", "Métricas"),
    ("/explorador", "Explorador"),
    ("/errores", "Errores"),
    ("/catalogo", "Modelos"),
)

_ESTILO = """
/* Design system del WAR ROOM (s324g, pedido por Alberto). Los valores salen de
   `war-room/src/app/globals.css` —shadcn/ui, estilo base-nova, baseColor
   neutral— para que las dos herramientas se vean como la misma casa.
   Se adoptan los TOKENS, no la tecnología: el panel sigue sin Tailwind, sin JS
   y sin dependencias, así que aquí sólo cambia este bloque y ni un componente.

   SIEMPRE OSCURO, igual que el war room («always dark, no light mode»): se
   retira el `@media prefers-color-scheme` para que no haya un segundo aspecto
   que nadie ha diseñado ni revisado. */
:root { color-scheme: dark;
  --fondo:#0f1117;          /* --background */
  --papel:#161b27;          /* --card */
  --tinta:#e2e8f0;          /* --foreground */
  --suave:#94a3b8;          /* --muted-foreground */
  --linea:#2d3548;          /* --border / --input */
  --acento:#3b82f6;         /* --primary */
  --barra:#3b82f6;
  --hueco:#1a2035;          /* --muted / --secondary / --accent */
  --radio:0.5rem;           /* --radius */
  --malo:#ef4444;           /* --destructive */
  --malo-fondo:#2a1620;
  --bien:#34d399; --bien-fondo:#12261f;
  --avisa:#fbbf24; --avisa-fondo:#2a2113; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fondo); color:var(--tinta);
  font:15px/1.5 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased; }
header { background:var(--papel); border-bottom:1px solid var(--linea);
  padding:0 20px; display:flex; align-items:center; gap:20px; flex-wrap:wrap; }
header .marca { font-weight:600; padding:14px 0; }
header nav { display:flex; gap:4px; flex:1; flex-wrap:wrap; }
header nav a { padding:14px 12px; text-decoration:none; color:var(--suave);
  border-bottom:2px solid transparent; }
header nav a.activa { color:var(--acento); border-bottom-color:var(--acento); }
header .sesion { color:var(--suave); font-size:13px; display:flex;
  align-items:center; gap:10px; }
header form { margin:0; }
header button { background:none; border:0; color:var(--suave); cursor:pointer;
  text-decoration:underline; font:inherit; font-size:13px; padding:0; }
main { max-width:1100px; margin:0 auto; padding:20px; }
h1 { font-size:20px; margin:4px 0 16px; }
h2 { font-size:15px; margin:0 0 2px; }
.tarjeta { background:var(--papel); border:1px solid var(--linea);
  border-radius:var(--radio); padding:16px; margin-bottom:16px; }
.pregunta { color:var(--suave); font-size:13px; margin:0 0 12px; }
.pie, .nota { color:var(--suave); font-size:13px; margin:10px 0 0; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--linea);
  white-space:nowrap; }
th { color:var(--suave); font-weight:600; font-size:12px;
  text-transform:uppercase; letter-spacing:.03em; }
td.ancho, th.ancho { white-space:normal; min-width:260px; }
.rejilla { display:flex; gap:10px; flex-wrap:wrap; }
.cifra { background:var(--papel); border:1px solid var(--linea);
  border-radius:var(--radio); padding:12px 16px; min-width:150px; flex:1; }
.cifra .valor { font-size:22px; font-weight:600; }
.cifra .rotulo { color:var(--suave); font-size:12px; }
.cifra .detalle { color:var(--suave); font-size:12px; margin-top:4px; }
/* GRÁFICO DE COLUMNAS (s328b, adjudicación de Alberto: «que salgan de izquierda
   a derecha, no de arriba a abajo»). HTML y CSS, sin SVG y sin JavaScript.

   La clave de por qué esto es mejor que el SVG que había: aquí **el texto no
   escala**. 12 px son 12 px a cualquier anchura de tarjeta, así que la letra del
   gráfico es la misma que la del resto de la página —lo que Alberto pidió— y no
   hay forma de que el rótulo se descuadre de su columna, porque son el MISMO
   elemento de la rejilla. La clase de fallo de s328 (dos sistemas de
   coordenadas) deja de existir, no se vigila.

   Lo único que estira es la barra, con la altura en porcentaje de su pista. Y
   como un atributo `style` con la altura sería «inline style» y la CSP dice
   `default-src 'none'`, la altura viaja en una CLASE de una tabla fija
   (`.h0`…`.h100`, generada abajo): no crece con las gráficas ni con las barras.
   (Este párrafo llevaba el atributo escrito literal y lo cazó
   `test_sin_atributos_style_en_el_html`, que busca la cadena en el HTML servido
   y no distingue un comentario de un atributo. No se ablanda el gate por un
   comentario: se reescribe el comentario.) */
.grafico { overflow-x:auto; padding-bottom:2px; }
ol.columnas { display:flex; align-items:stretch; gap:8px; list-style:none;
  margin:0; padding:0; min-width:100%; width:max-content; }
ol.columnas li { flex:1 1 0; min-width:44px; max-width:72px; display:flex;
  flex-direction:column; align-items:center; gap:4px; }
/* `.dato`, NO `.cifra`: esa clase ya es de las tarjetas de KPI (min-width:150px)
   y reusarla forzaba columnas de 150 px — solo cabían dos por tarjeta. */
.columnas .dato { font-size:12px; color:var(--suave); line-height:1.2;
  white-space:nowrap; }
.columnas .pista { display:flex; align-items:flex-end; justify-content:center;
  width:100%; height:120px; }
.columnas .col { display:block; width:100%; background:var(--barra);
  border-radius:3px 3px 0 0; min-height:0; }
/* El rótulo va VERTICAL: bajo una columna de 44 px no cabe una fecha en
   horizontal, y `writing-mode` —a diferencia de `transform:rotate`— SÍ ocupa
   sitio en el layout, así que la banda reserva su alto sola y el recorte con
   puntos suspensivos sigue funcionando. */
.columnas .rotulo { writing-mode:vertical-rl; transform:rotate(180deg);
  font-size:12px; color:var(--suave); line-height:1; max-height:88px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.leyenda { margin:8px 0 0; font-size:12px; color:var(--suave); }
.banda { border-radius:var(--radio); padding:10px 12px; margin:0 0 12px; font-size:14px; }
.banda.error { background:var(--malo-fondo); color:var(--malo); }
.banda.bien { background:var(--bien-fondo); color:var(--bien); }
.banda.aviso { background:var(--avisa-fondo); color:var(--avisa); }
.estado { font-size:12px; padding:2px 8px; border-radius:20px;
  background:var(--linea); color:var(--suave); }
.estado.activo, .estado.pendiente { background:var(--bien-fondo); color:var(--bien); }
.estado.revocado, .estado.anulada, .estado.caducada { background:var(--malo-fondo);
  color:var(--malo); }
form { display:flex; gap:8px; align-items:flex-end; flex-wrap:wrap; margin:0; }
label { display:flex; flex-direction:column; gap:4px; font-size:13px;
  color:var(--suave); }
input, select { padding:7px 9px; border:1px solid var(--linea); border-radius:var(--radio);
  background:var(--hueco); color:var(--tinta); font:inherit; min-width:200px; }
button.principal, button.peligro { padding:8px 14px; border:0; border-radius:var(--radio);
  cursor:pointer; font:inherit; color:#fff; }
button.principal { background:var(--acento); }
button.peligro { background:none; color:var(--malo); text-decoration:underline;
  padding:4px; min-width:0; }
.enlace { font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
  font-size:13px; word-break:break-all; background:var(--hueco);
  border:1px dashed var(--linea); border-radius:var(--radio); padding:10px;
  margin:8px 0; }
.entrar { max-width:340px; margin:12vh auto; }   /* la usa también `_error` */

/* ===================== LA PUERTA (s328) =====================
   Identidad de marca FONTIBER, pedida por Alberto: que el login del panel se vea
   como el del Data Room (dataroom.fontiber.com/login). Los tokens salen de
   `dataroom/src/app/globals.css` —navy #0c1932, cobre #c75b39, arena #f5f3ef—
   igual que el resto del panel tomó los del war room: se adoptan los VALORES,
   no la tecnología (allí es Tailwind + React; aquí sigue sin ser nada).

   SOLO la puerta, y a propósito: detrás sigue el design system del war room. La
   puerta es la cara de la casa y la herramienta es la herramienta; repintar el
   panel entero no es lo que se pidió. Por eso todo cuelga de `body.entrada` y
   ni una regla de aquí puede alcanzar al resto.

   TRES COSAS DEL ORIGINAL NO ESTÁN, y ninguna por olvido:
   · el botón «Mostrar» de la contraseña necesita JavaScript, y la CSP de este
     panel dice `default-src 'none'`: no hay script propio ni ajeno que corra;
   · «¿Olvidaste tu contraseña?» y «El acceso requiere verificación en dos
     pasos» describen cosas que el Data Room TIENE y este panel NO —no hay
     recuperación ni 2FA—. Un enlace muerto y una promesa de seguridad falsa son
     peores que su ausencia; en su lugar queda el aviso verdadero que ya había;
   · la Playfair Display del logotipo es de Google Fonts, y cargarla obligaría a
     abrir la CSP a `fonts.googleapis.com` y `fonts.gstatic.com` en un panel que
     hoy no pide NADA de fuera. Va la pila serif del sistema. Si Alberto quiere
     la Playfair exacta, la vía que no toca la CSP es incrustarla en base64: se
     decide, no se cuela. */
body.entrada { --navy:#0c1932; --navy-claro:#142850; --cobre:#c75b39;
  --arena:#f5f3ef; --papel-claro:#ffffff; --linea-clara:#e5e5e5;
  --linea-campo:#d4d4d4; --tinta-clara:#171717; --rotulo-claro:#404040;
  background:var(--navy); color:var(--arena);
  display:flex; align-items:center; justify-content:center;
  min-height:100dvh; padding:24px 16px; box-sizing:border-box; }
body.entrada main { max-width:384px; width:100%; padding:0; margin:0; }
body.entrada footer { display:none; }   /* el aviso va dentro, ver `.pie-puerta` */
/* `.entrar` NO es solo de la puerta: la página de ERROR la reutiliza
   (app.py, `_error`). Por eso su regla original se conserva intacta arriba y la
   de la puerta va acotada — hallazgo Fable s328, y era doble: además de
   desmentir la claim de aislamiento, reescribirla suelta le cambiaba el layout
   a una página que nadie estaba tocando. TODO lo de aquí abajo cuelga de
   `body.entrada`, sin excepción. */
body.entrada .entrar { max-width:none; margin:0; }
body.entrada .marca-puerta { text-align:center; margin:0 0 32px; }
body.entrada .marca-puerta h1 { font-family:"Playfair Display",Georgia,"Times New Roman",serif;
  font-weight:400; font-size:30px; line-height:1.2; letter-spacing:-.02em;
  color:#fff; margin:0; white-space:nowrap; }
body.entrada .marca-puerta h1 span { color:var(--cobre); }
body.entrada .marca-puerta p { margin:8px 0 0; font-size:14px;
  color:rgba(245,243,239,.8); }
body.entrada .tarjeta { background:var(--papel-claro);
  border:1px solid var(--linea-clara); border-radius:12px; padding:24px;
  box-shadow:0 1px 2px rgba(0,0,0,.05); }
body.entrada .tarjeta form { flex-direction:column; align-items:stretch;
  gap:16px; }
body.entrada .tarjeta label { gap:4px; font-size:14px; font-weight:500;
  color:var(--rotulo-claro); }
body.entrada .tarjeta input { width:100%; box-sizing:border-box;
  padding:8px 12px; font-size:14px; border-radius:8px;
  border:1px solid var(--linea-campo); background:var(--papel-claro);
  color:var(--tinta-clara); }
body.entrada .tarjeta input:focus { outline:none; border-color:var(--tinta-clara);
  box-shadow:0 0 0 1px var(--tinta-clara); }
body.entrada .tarjeta button { width:100%; padding:9px 12px; font-size:14px;
  font-weight:500; border:0; border-radius:8px; background:var(--navy);
  color:#fff; cursor:pointer; }
body.entrada .tarjeta button:hover { background:var(--navy-claro); }
/* La banda de error del panel es oscura; sobre navy con tarjeta blanca no se
   lee. Aquí toma la forma clara del aviso del Data Room. */
body.entrada .banda.error { background:#fef2f2; border:1px solid #fecaca;
  color:#b91c1c; text-align:center; margin:0 0 16px; }
body.entrada .pie-puerta { margin:16px 0 0; text-align:center; font-size:12px;
  color:rgba(245,243,239,.5); }
/* La portada: TODAS las gráficas de un vistazo (s327, pedido de Alberto: «no
   quiero hacer scroll para ir viendo gráficas»). Una sola regla sirve los tres
   tamaños —`auto-fit` reparte lo que quepa— así que no hay media query que
   mantener ni breakpoint que recordar. */
.panel-graficos { display:grid; gap:14px;
  grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); }
a.tarjeta.grafica { display:block; text-decoration:none; color:inherit;
  transition:border-color .15s, transform .15s; }
a.tarjeta.grafica:hover, a.tarjeta.grafica:focus-visible {
  border-color:var(--acento); transform:translateY(-1px); }
a.tarjeta.grafica h2 { margin:0 0 10px; font-size:15px; }
.ver-mas { display:inline-block; margin-top:10px; font-size:12px;
  color:var(--acento); }
.migas { font-size:13px; color:var(--suave); margin:0 0 14px; }
h2.seccion { margin:22px 0 12px; font-size:14px; text-transform:uppercase;
  letter-spacing:.06em; color:var(--suave); }
.migas a { color:var(--acento); }
footer { color:var(--suave); font-size:12px; text-align:center; padding:24px; }

/* ------------------------------------------------------------------ MÓVIL
   Reglas tomadas de `docs/RESPONSIVE.md` del war room, traducidas a un panel
   sin Tailwind: pivot en 640 px (su `sm`), targets de 44 px (Apple HIG) y la
   regla anti-zoom de iOS —Safari hace zoom al enfocar un input con menos de
   16 px, y el zoom deja la página descuadrada hasta que recargas—. */
@media (max-width:639px) {
  body { font-size:15px; }
  main { padding:12px; }
  header { padding:0 12px; gap:10px; }
  header .marca { padding:12px 0; font-size:14px; }
  /* `flex:1 0 100%` y no `width:100%`: el nav hereda `flex:1 1 0%` del CSS de
     escritorio y una base de 0% gana a cualquier width — medido con el
     navegador, no supuesto (la nav salía en columna y de 110 px). */
  header nav { display:flex; flex-wrap:wrap; gap:2px; flex:1 0 100%;
    order:3; border-top:1px solid var(--linea); padding:4px 0; }
  header nav a { padding:10px 12px; min-height:44px; display:flex;
    align-items:center; }
  header .sesion { margin-left:auto; font-size:13px; }
  input, select, textarea { font-size:16px; }   /* anti-zoom iOS */
  /* La puerta pinta sus campos a 14 px con más especificidad que la
     regla de arriba, así que el anti-zoom hay que repetirlo AQUÍ o
     iOS hace zoom al tocar el campo de usuario. */
  body.entrada .tarjeta input { font-size:16px; }
  button, .tarjeta form button { min-height:44px; }
  form { flex-direction:column; align-items:stretch; }
  form label { width:100%; }
  input, select { min-width:0; width:100%; }
  .tarjeta { padding:14px; }
  /* La pista baja de 120 a 96 px: en un móvil la tarjeta ya es alta y con nueve
     gráficas cada centímetro cuenta. La LETRA no baja — es lo que pidió Alberto
     («el mismo tamaño de letra») y es justo lo que el SVG no podía darle. */
  .columnas .pista { height:96px; }
  .cifra .valor { font-size:22px; }
  table { font-size:13px; }
  td, th { padding:8px 6px; }
  /* tabla → tarjetas (pivot del war room, aquí en 640 px y sin JS) */
  table.cards, table.cards tbody, table.cards tr, table.cards td { display:block; }
  table.cards thead { display:none; }
  table.cards tr { border:1px solid var(--linea); border-radius:var(--radio);
    padding:8px 10px; margin:0 0 10px; background:var(--hueco); }
  table.cards td { display:flex; gap:10px; align-items:baseline;
    border:0; padding:5px 0; }
  table.cards td::before { content:attr(data-etiqueta); color:var(--suave);
    font-size:12px; flex:0 0 38%; }
  /* el valor ENVUELVE en vez de cortarse: en una tarjeta hay sitio a lo alto,
     que es justo lo que no había en la fila de una tabla. */
  table.cards td > * { min-width:0; }
  table.cards td, table.cards td .ancho { overflow-wrap:anywhere;
    white-space:normal; display:block; }
  table.cards td { display:flex; }
  table.cards td:empty { display:none; }
  .ancho { max-width:none; }
}
@media (min-width:640px) and (max-width:1023px) {
  main { padding:16px; }
}
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:var(--fondo); }
::-webkit-scrollbar-thumb { background:var(--linea); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#4a5568; }
""" + "".join(
    f".columnas .col.h{i} {{ height:{i}%; }}\n" for i in range(_PASOS_ALTURA))


#: CSS que viaja SOLO con la puerta. La fuente de marca son 3 KB y una apertura
#: de la CSP (`font-src data:`), y ninguna de las dos cosas tiene por qué pagarla
#: una página que no pinta el logotipo. `font-display:swap` para que el titular
#: se vea desde el primer píxel aunque la fuente tardara: la puerta es lo primero
#: que alguien ve del sistema.
_ESTILO_PUERTA = f"""
@font-face {{
  font-family:"Playfair Display";
  font-style:normal; font-weight:400; font-display:swap;
  src:url(data:font/woff2;base64,{PLAYFAIR_PUERTA_B64}) format("woff2");
}}
"""


def pagina(titulo: str, cuerpo, *, nonce: str, usuario: str | None = None,
           ruta: str = "", csrf: str = "", clase_cuerpo: str = "") -> str:
    """El documento entero. `nonce` es por RESPUESTA: la CSP sólo autoriza el
    `<style>` que lleve ese número, así que un `<style>` inyectado no pinta.

    `clase_cuerpo` existe para UNA cosa (s328): la puerta lleva la identidad de
    marca Fontiber y el resto del panel el design system del war room. Una clase
    en el `<body>` acota el repintado a esa página — sin ella habría que colar
    reglas por ruta, que es la vía por la que un estilo se escapa a donde nadie
    lo esperaba."""
    if usuario:
        def _enlace(destino: str, nombre: str) -> Seguro:
            clase = ' class="activa"' if destino == ruta else ""
            return Seguro(f'<a href="{esc(destino)}"{clase}>{esc(nombre)}</a>')

        enlaces = unir(_enlace(destino, nombre) for destino, nombre in _NAV)
        salir = formulario("/salir", csrf, Seguro(""), boton="Salir",
                           peligroso=True)
        cabecera = (
            f'<header><span class="marca">Panel del bot PCI</span>'
            f"<nav>{enlaces}</nav>"
            f'<span class="sesion">{esc(usuario)} · {salir}</span></header>'
        )
    else:
        cabecera = ""
    cuerpo_abre = f' class="{esc(clase_cuerpo)}"' if clase_cuerpo else ""
    extra_css = _ESTILO_PUERTA if clase_cuerpo == "entrada" else ""
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        f"<title>{esc(titulo)}</title>"
        f'<style nonce="{esc(nonce)}">{_ESTILO}{extra_css}</style></head>'
        f"<body{cuerpo_abre}>"
        f"{cabecera}<main>{_pintar(cuerpo)}</main>"
        "<footer>Panel interno · datos de personas: mira sólo lo que "
        "necesites</footer></body></html>"
    )
