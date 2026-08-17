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
`script-src 'none'`: no hay script propio ni ajeno que pueda ejecutarse, así que
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


class Seguro(str):
    """HTML ya escapado. El único tipo que `_pintar` deja pasar tal cual."""


def esc(valor: object) -> str:
    """Cualquier cosa → texto seguro para incrustar. `None` y `''` se pintan
    como raya: una celda vacía y una celda con `None` se leen igual de mal."""
    if valor is None or valor == "":
        return "—"
    return html.escape(str(valor), quote=True)


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


def tabla(cabeceras, filas, *, vacio: str = "Sin datos todavía.") -> Seguro:
    if not filas:
        return nota(vacio)
    cabeza = unir(
        Seguro(f"<th>{_pintar(c)}</th>") for c in cabeceras
    )
    cuerpo = unir(
        Seguro("<tr>" + "".join(f"<td>{_pintar(celda)}</td>" for celda in fila)
               + "</tr>")
        for fila in filas
    )
    return Seguro(
        f'<div class="scroll"><table><thead><tr>{cabeza}</tr></thead>'
        f"<tbody>{cuerpo}</tbody></table></div>"
    )


def barras(pares, *, ancho: int = 320, unidad: str = "") -> Seguro:
    """Un gráfico de barras horizontal en SVG, sin una línea de JavaScript.

    `pares` = [(etiqueta, valor)]. Se dibuja con el máximo como escala; si todos
    los valores son 0 se enseña la tabla igualmente (barras a cero), porque «hoy
    no hubo tráfico» es un dato y no un fallo.
    """
    pares = [(e, v) for e, v in pares if isinstance(v, (int, float))]
    if not pares:
        return Seguro("")
    tope = max((v for _, v in pares), default=0) or 1
    alto_fila, hueco = 22, 6
    alto = len(pares) * (alto_fila + hueco)
    filas = []
    for indice, (etiqueta, valor) in enumerate(pares):
        y = indice * (alto_fila + hueco)
        largo = max(1, int(ancho * (valor / tope)))
        texto = f"{numero(valor)}{(' ' + unidad) if unidad else ''}"
        filas.append(
            f'<rect x="0" y="{y}" width="{largo}" height="{alto_fila}" '
            f'rx="3" class="barra"></rect>'
            f'<text x="{largo + 8}" y="{y + 15}" class="valor">{esc(texto)}</text>'
            f'<title>{esc(etiqueta)}: {esc(texto)}</title>'
        )
    etiquetas = unir(
        Seguro(f'<div class="etiqueta">{esc(e)}</div>') for e, _ in pares
    )
    return Seguro(
        f'<div class="grafico"><div class="etiquetas">{etiquetas}</div>'
        f'<svg role="img" viewBox="0 0 {ancho + 90} {alto}" '
        f'width="{ancho + 90}" height="{alto}">{"".join(filas)}</svg></div>'
    )


def tarjeta(titulo: str, cuerpo, *, pregunta: str = "",
            pie: str = "") -> Seguro:
    cabecera = f"<h2>{esc(titulo)}</h2>"
    if pregunta:
        cabecera += f'<p class="pregunta">{esc(pregunta)}</p>'
    final = f'<p class="pie">{esc(pie)}</p>' if pie else ""
    return Seguro(
        f'<section class="tarjeta">{cabecera}{_pintar(cuerpo)}{final}</section>'
    )


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

_NAV = (
    ("/", "Resumen"),
    ("/acceso", "Acceso"),
    ("/metricas", "Métricas"),
    ("/errores", "Errores"),
)

_ESTILO = """
:root { color-scheme: light dark;
  --fondo:#f6f7f9; --papel:#fff; --tinta:#1b1f24; --suave:#5b6672;
  --linea:#e2e6ea; --acento:#1f6feb; --barra:#4c8dff;
  --malo:#b3261e; --malo-fondo:#fdeceb; --bien:#0f6b3f; --bien-fondo:#e8f5ee;
  --avisa:#8a5300; --avisa-fondo:#fdf3e2; }
@media (prefers-color-scheme: dark) { :root {
  --fondo:#14171a; --papel:#1c2024; --tinta:#e8eaed; --suave:#9aa4af;
  --linea:#2c3238; --acento:#79a9ff; --barra:#3b6fc4;
  --malo:#ff8a80; --malo-fondo:#3a1f1d; --bien:#8fd6ae; --bien-fondo:#12291f;
  --avisa:#f0c27a; --avisa-fondo:#332713; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--fondo); color:var(--tinta);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
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
  border-radius:10px; padding:16px; margin-bottom:16px; }
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
  border-radius:10px; padding:12px 16px; min-width:150px; flex:1; }
.cifra .valor { font-size:22px; font-weight:600; }
.cifra .rotulo { color:var(--suave); font-size:12px; }
.cifra .detalle { color:var(--suave); font-size:12px; margin-top:4px; }
.grafico { display:flex; gap:12px; align-items:flex-start; overflow-x:auto; }
.etiquetas { padding-top:3px; }
.etiqueta { height:22px; margin-bottom:6px; font-size:13px; color:var(--suave);
  white-space:nowrap; line-height:22px; }
.barra { fill:var(--barra); }
.valor { fill:var(--suave); font-size:12px; }
.banda { border-radius:8px; padding:10px 12px; margin:0 0 12px; font-size:14px; }
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
input, select { padding:7px 9px; border:1px solid var(--linea); border-radius:7px;
  background:var(--fondo); color:var(--tinta); font:inherit; min-width:200px; }
button.principal, button.peligro { padding:8px 14px; border:0; border-radius:7px;
  cursor:pointer; font:inherit; color:#fff; }
button.principal { background:var(--acento); }
button.peligro { background:none; color:var(--malo); text-decoration:underline;
  padding:4px; min-width:0; }
.enlace { font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
  font-size:13px; word-break:break-all; background:var(--fondo);
  border:1px dashed var(--linea); border-radius:7px; padding:10px;
  margin:8px 0; }
.entrar { max-width:340px; margin:12vh auto; }
.entrar form { flex-direction:column; align-items:stretch; }
.entrar input, .entrar button { width:100%; }
footer { color:var(--suave); font-size:12px; text-align:center; padding:24px; }
"""


def pagina(titulo: str, cuerpo, *, nonce: str, usuario: str | None = None,
           ruta: str = "", csrf: str = "") -> str:
    """El documento entero. `nonce` es por RESPUESTA: la CSP sólo autoriza el
    `<style>` que lleve ese número, así que un `<style>` inyectado no pinta."""
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
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        f"<title>{esc(titulo)}</title>"
        f'<style nonce="{esc(nonce)}">{_ESTILO}</style></head><body>'
        f"{cabecera}<main>{_pintar(cuerpo)}</main>"
        "<footer>Panel interno · datos de personas: mira sólo lo que "
        "necesites</footer></body></html>"
    )
