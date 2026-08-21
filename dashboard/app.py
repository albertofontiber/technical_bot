# -*- coding: utf-8 -*-
"""El servicio: rutas, puerta de sesión y páginas.

POR QUÉ UNA APLICACIÓN ASGI ESCRITA A MANO Y NO FastAPI (que ya está declarado
en `requirements.txt`). Tres razones, en orden de peso:

  1. **Los tests corren sin instalar nada.** El módulo importa `httpx` (ya
     usado en todo el repo) y biblioteca estándar. Un panel cuya suite depende
     de que FastAPI resuelva e importe bien es un panel que no se puede
     verificar en un entorno limpio — y verificar en el mismo turno es el
     Protocolo 1 de esta casa. El cliente de pruebas de `tests/` habla ASGI
     directamente, en proceso y sin socket.
  2. **Quien parsea HTTP es uvicorn en los dos casos.** Un framework por encima
     de ASGI no toca el parseo de la petición: recibe el `scope` ya validado.
     Lo que aporta —enrutado, validación de modelos, documentación
     automática— aquí es cero o negativo: son seis rutas de igualdad exacta, no
     hay JSON de entrada, y una ruta `/docs` autogenerada es superficie pública
     en un panel cuyo requisito es que NADA responda sin sesión.
  3. **Menos piezas que auditar** en un servicio que expone datos personales a
     internet. Todo lo que decide quién entra cabe en este fichero y en
     `sesion.py`.

  El precio, declarado: enrutado, cookies y cuerpo de formulario se escriben
  aquí (unas 60 líneas) en vez de heredarse. Si el panel creciera —subida de
  ficheros, API, varios roles— la decisión correcta sería cambiarla, y el coste
  de cambiarla es reescribir este fichero, no el resto.

EL ORDEN DE LA PUERTA, que es lo único que no se puede equivocar:

    cabeceras de seguridad → ruta pública o no → sesión válida → (si escribe)
    origen del navegador → token CSRF → acción

`RUTAS_PUBLICAS` tiene exactamente DOS entradas y las dos son la pantalla de
entrada. No hay excepción para «salud», ni para métricas, ni para un ping: un
endpoint sin sesión es un endpoint que alguien acabará usando para saber si el
panel existe. La consecuencia operativa, declarada: **no configures ningún
healthcheck de plataforma** (el panel vive en Vercel — tanda 2: el aviso decía
«Railway» por herencia; si algún día hiciera falta, apúntalo a `/entrar`, que es
lo único que responde 200 sin credenciales, y no dice nada de nadie).
"""
from __future__ import annotations

import hmac
import secrets
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.bot import access

from . import (auth, catalogo, cerrojo, datos, errores, explorador, gestion,
               render, sesion)
from .render import Seguro, atributo, esc

#: Tope del cuerpo de una petición. Los formularios del panel pesan bytes; esto
#: existe para que nadie ocupe memoria mandando un POST de 2 GB.
CUERPO_MAX_BYTES = 64 * 1024

RUTAS_PUBLICAS = frozenset({("GET", "/entrar"), ("POST", "/entrar")})

#: El único texto del 503 de identidad/cerrojo: un estado del SERVICIO, igual
#: para todo el mundo — sin señal por-usuario y sin mentir «credenciales
#: incorrectas» cuando la verdad es «no puedo comprobarlo» (s324j, v9 §1.3).
_TEXTO_503 = ("El panel no puede comprobar identidades ahora mismo. No es tu "
              "contraseña: vuelve a intentarlo en unos minutos.")


# --------------------------------------------------------- petición/respuesta


@dataclass
class Peticion:
    metodo: str
    ruta: str
    consulta: dict
    cabeceras: dict
    cuerpo: bytes
    ip: str
    #: Uno por PETICIÓN, no por página: es el que autoriza el `<style>` de la
    #: respuesta en la CSP, y lo pone la capa ASGI para que ningún manejador
    #: pueda servir una página sin él.
    nonce: str = ""
    #: Puesto por la puerta: el payload de la sesión, o None.
    sesion: dict | None = None

    def campo(self, nombre: str, defecto: str = "") -> str:
        valores = self.formulario.get(nombre) or []
        return valores[0] if valores else defecto

    @property
    def formulario(self) -> dict:
        if self._formulario is None:
            texto = self.cuerpo.decode("utf-8", errors="replace")
            self._formulario = urllib.parse.parse_qs(texto, keep_blank_values=True)
        return self._formulario

    _formulario: dict | None = field(default=None, repr=False)

    @property
    def usuario(self) -> str:
        return (self.sesion or {}).get("u", "")

    @property
    def csrf(self) -> str:
        return (self.sesion or {}).get("csrf", "")


@dataclass
class Respuesta:
    estado: int = 200
    cuerpo: bytes = b""
    tipo: str = "text/html; charset=utf-8"
    extra: list = field(default_factory=list)
    #: ¿esta respuesta incrusta la fuente de marca? Solo la puerta. Abre
    #: `font-src data:` en SU CSP y en ninguna otra: el resto del panel sigue
    #: con `default-src 'none'` y sin ninguna fuente de fuentes (s328c).
    fuente_incrustada: bool = False


def _redirigir(destino: str, *, extra: list | None = None) -> Respuesta:
    # 303: obliga al navegador a hacer GET del destino aunque viniera de un
    # POST — es la mitad del patrón POST-redirect-GET y evita que recargar
    # repita la escritura.
    return Respuesta(estado=303, cuerpo=b"", extra=[("location", destino)]
                     + (extra or []))


def _cabeceras_seguridad(nonce: str, *, fuente: bool = False) -> list:
    """Las mismas en TODA respuesta: página, redirección, 404 y 403.

    **Se aplican en `_enviar`, no en cada manejador**, y eso es una corrección:
    la primera versión las ponía en quien construía la página, así que las
    redirecciones salían desnudas — incluida la del login CORRECTO, que es la
    que lleva la cookie de sesión en un `Set-Cookie` y la que más falta le hace
    un `Cache-Control: no-store` delante de un proxy. Lo cazó su propio test.
    Puestas aquí, no hay forma de escribir una respuesta que se las salte.

    Cada una con lo que corta:
      · CSP `default-src 'none'` — nada carga de ningún sitio salvo lo que se
        autorice explícitamente. `script-src` ni aparece: al no estar,
        `default-src` lo cubre y NO hay JavaScript posible, ni propio ni
        inyectado. El único permiso es el `<style>` que lleve este nonce.
      · `form-action 'self'` — un formulario inyectado no puede enviar a otro
        sitio (que es como se roban credenciales cuando hay un XSS).
      · `frame-ancestors 'none'` — nadie mete el panel en un iframe:
        clickjacking sobre el botón «revocar acceso».
      · `Cache-Control: no-store` — esto es lo más importante de la lista para
        el RGPD: sin ella, un proxy o el disco del navegador se quedan copias
        de páginas con identificadores de Telegram y preguntas de técnicos.
      · `Referrer-Policy: same-origin` — la URL del panel no viaja a ningún
        sitio EXTERNO, y sí viaja dentro del propio panel. **(s324f) Era
        `no-referrer`, y con eso el panel se saboteaba a sí mismo**: dejaba sin
        `Referer` al respaldo del control de origen, así que un login legítimo
        acababa en 403 cuando el navegador tampoco mandaba `Origin` (que es lo
        normal en un formulario del mismo sitio). Frente a terceros protege
        igual; hacia dentro, devuelve la señal que la defensa necesitaba.
    """
    # `font-src data:` SOLO donde hace falta (la puerta). Se replica la
    # propiedad del Data Room —que el navegador no le pida nada a un tercero:
    # su CSP es `font-src 'self'` y `next/font/google` auto-hospeda— con el
    # medio que tiene este panel: los bytes van incrustados. Lo que NO se hace
    # es abrir `fonts.googleapis.com`/`fonts.gstatic.com`, que sería meter un
    # tercero en la carga de una página de login.
    fuentes = " font-src data:;" if fuente else ""
    return [
        ("content-security-policy",
         "default-src 'none'; "
         f"style-src 'nonce-{nonce}';{fuentes} "
         "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        ("referrer-policy", "same-origin"),
        ("cache-control", "no-store, no-cache, must-revalidate, private"),
        ("pragma", "no-cache"),
        ("permissions-policy",
         "geolocation=(), camera=(), microphone=(), interest-cohort=()"),
        ("cross-origin-opener-policy", "same-origin"),
        ("cross-origin-resource-policy", "same-origin"),
        # Sólo tiene efecto sobre HTTPS; en local el navegador la ignora. Sin
        # `includeSubDomains`: el panel no manda sobre los subdominios vecinos
        # de un dominio compartido.
        ("strict-transport-security", "max-age=31536000"),
    ]


def _ip_cliente(cabeceras: dict, directa: str) -> str:
    """De quién viene la petición, para el cerrojo de intentos.

    Se toma el elemento **más a la derecha** de `X-Forwarded-For`, no el
    primero. La cabecera se construye «cliente, proxy1, proxy2…» y cada salto
    AÑADE la dirección que vio: por tanto el último valor lo escribió el proxy
    de confianza (el borde de la plataforma — hoy Vercel; el texto decía
    «Railway» por herencia, tanda 2) y es la dirección que de verdad conectó.
    Los de la izquierda los puede escribir cualquiera — usar el primero, que es
    el error habitual, convierte el cerrojo por IP en decorativo: basta con
    mandar una cabecera distinta en cada intento.

    Alcance honesto: esto es correcto con EXACTAMENTE un proxy de confianza
    delante, que es el despliegue de hoy. Si algún día hay CDN, hay que contar
    saltos, y este comentario es el aviso.
    """
    reenviado = cabeceras.get("x-forwarded-for", "")
    if reenviado:
        ultimo = reenviado.split(",")[-1].strip()
        if ultimo:
            return ultimo[:64]
    return (directa or "?")[:64]


def _mismo_origen(peticion: Peticion) -> bool:
    """¿El POST nace en el propio panel? Defensa ANTE del token CSRF.

    Cubre además el hueco que el token no puede cubrir: el formulario de
    ENTRADA no tiene sesión todavía, así que no hay token que meterle. Un POST
    de entrada desde otro sitio (login CSRF) trae `Origin: https://otro.sitio`
    y muere aquí.

    ⚠️ **(s324f) ESTO RECHAZABA EL LOGIN LEGÍTIMO, y se descubrió abriendo el
    panel en un navegador de verdad — no lo vio ningún test.** La versión
    anterior decía «los navegadores actuales mandan `Origin` en todo POST», y es
    FALSO para el envío normal de un formulario del mismo sitio: varios
    navegadores lo omiten precisamente porque no hay nada cruzado que declarar.
    El respaldo previsto era `Referer`… que **el propio panel suprimía** con su
    cabecera `Referrer-Policy: no-referrer`. Resultado: un formulario del panel,
    servido por el panel, se quedaba sin ninguna de las dos señales y moría en su
    propia defensa con un 403 que no explicaba nada.

    Se arregla por los dos lados: aquí se acepta **`Sec-Fetch-Site: same-origin`**
    —que los navegadores modernos sí mandan SIEMPRE y que un atacante no puede
    falsificar desde otro sitio, porque la escribe el navegador— y en las
    cabeceras se pasa a `Referrer-Policy: same-origin`, que devuelve el respaldo
    sin filtrar la URL a terceros.

    Si no viene NINGUNA de las tres señales, se RECHAZA. Esa dureza sí se
    sostiene: un cliente que no manda ninguna no es un navegador haciendo su
    trabajo normal.
    """
    anfitrion = (peticion.cabeceras.get("host") or "").strip().lower()
    if not anfitrion:
        return False

    # 1) La señal que el navegador escribe él mismo y que no se puede falsificar
    #    desde otro origen. `same-origin` es el propio panel; `none` es teclear
    #    la URL a mano (no hay sitio de partida), que también es legítimo.
    sitio = (peticion.cabeceras.get("sec-fetch-site") or "").strip().lower()
    if sitio in ("same-origin", "none"):
        return True
    if sitio:
        # La mandó y dice `cross-site` / `same-site`: es una respuesta EXPLÍCITA
        # y manda sobre lo demás. No se sigue mirando.
        return False

    # 2) Navegadores viejos o clientes sin `Sec-Fetch-*`: Origin, y si no, Referer.
    origen = (peticion.cabeceras.get("origin") or "").strip()
    if not origen:
        origen = (peticion.cabeceras.get("referer") or "").strip()
    if not origen:
        return False
    try:
        partido = urllib.parse.urlsplit(origen)
    except ValueError:
        return False
    return bool(partido.netloc) and partido.netloc.lower() == anfitrion


# --------------------------------------------------------------------- páginas


def _nonce() -> str:
    return secrets.token_urlsafe(16)


def pagina_entrar(peticion: Peticion, *, mensaje: str = "",
                  estado: int = 200) -> Respuesta:
    banda = render.aviso(mensaje, tono="error") if mensaje else Seguro("")
    # La puerta lleva la marca FONTIBER (s328, pedido de Alberto: «que sea como
    # la del dataroom»). El logotipo copia el patrón de `BrandLogo` de allí —
    # «Fontiber» hereda el blanco del titular y la segunda mitad va en cobre—,
    # con el nombre de ESTA herramienta. El detalle de qué se adopta y qué NO
    # (el «Mostrar», el «olvidé mi contraseña», el 2FA, la Playfair) está en el
    # bloque `LA PUERTA` de `render._ESTILO`, junto al CSS que lo hace.
    cuerpo = Seguro(
        '<div class="entrar">'
        '<div class="marca-puerta">'
        "<h1>Fontiber <span>Bot&nbsp;PCI</span></h1>"
        "<p>Panel de control del asistente técnico</p>"
        "</div>"
        f"{banda}"
        '<section class="tarjeta"><form method="post" action="/entrar">'
        '<label>Usuario<input name="usuario" autocomplete="username" '
        'autofocus required></label>'
        '<label>Contraseña<input name="contrasena" type="password" '
        'autocomplete="current-password" required></label>'
        '<button type="submit" class="principal">Continuar</button>'
        "</form></section>"
        '<p class="pie-puerta">Acceso restringido. Todo lo que hay detrás '
        "son datos de personas.</p>"
        "</div>"
    )
    return Respuesta(
        estado=estado,
        cuerpo=render.pagina("Entrar · Panel del bot", cuerpo,
                             nonce=peticion.nonce,
                             clase_cuerpo="entrada").encode("utf-8"),
        fuente_incrustada=True,
    )


def accion_entrar(peticion: Peticion) -> Respuesta:
    usuario = peticion.campo("usuario").strip()
    contrasena = peticion.campo("contrasena")
    claves = auth.claves_de(usuario, peticion.ip)

    # CONTAR AL ADMITIR, no al fallar (s324j, v9 §3.2): si `admitir` devuelve
    # 0.0, el intento YA está contado — así N peticiones concurrentes no pasan
    # todas la comprobación antes de que ninguna registre. `acierto` es la
    # devolución del provisional. El +1 fantasma de un proceso que muera entre
    # medias decae solo (precio declarado).
    try:
        espera = cerrojo.activo().admitir(claves, time.monotonic())
    except cerrojo.CerrojoNoDisponible:
        # Configuración rota (función sin migrar, ACL…): un panel que no puede
        # contar intentos no debe estar atendiendo logins (v9 §3.5).
        return _error(503, _TEXTO_503, peticion.nonce)
    if espera > 0:
        return pagina_entrar(
            peticion,
            mensaje=f"Demasiados intentos fallidos. Vuelve a probar en "
                    f"{int(espera // 60) + 1} minuto(s).",
            estado=429,
        )

    try:
        identidad = auth.autenticar(usuario, contrasena)
    except auth.IdentidadNoDisponible:
        # «No puedo comprobarlo» ≠ «credencial mala»: 503 de estado, igual para
        # todo el mundo (v9 §1.3). El +1 de `admitir` queda como fantasma en el
        # fallo PARCIAL (cerrojo vivo, lectura de usuarios caída) — declarado.
        return _error(503, _TEXTO_503, peticion.nonce)
    if identidad is None:
        # El fallo ya está contado (en `admitir`). UN SOLO mensaje para las dos
        # causas: decir «ese usuario no existe» regala la mitad de la
        # credencial a quien esté probando.
        return pagina_entrar(peticion,
                             mensaje="Usuario o contraseña incorrectos.",
                             estado=401)

    cerrojo.activo().acierto(claves)
    payload = sesion.nueva(identidad.nombre)
    # `h` lo añade LA PUERTA, no `sesion.nueva` (v9 §2, F5-m1): el payload es
    # un dict y `firmar` firma lo que le den; `sesion.py` documenta el campo
    # con este dueño escrito.
    payload["h"] = identidad.sello
    cookie = sesion.firmar(payload, sesion.secreto())
    return _redirigir("/", extra=[
        ("set-cookie", sesion.cabecera_cookie(
            cookie, max_age=int(payload["exp"] - payload["iat"]))),
    ])


def accion_salir(peticion: Peticion) -> Respuesta:
    return _redirigir("/entrar",
                      extra=[("set-cookie", sesion.cabecera_borrado())])


def _estado_pintado(estado: str) -> Seguro:
    return Seguro(f'<span class="estado {esc(estado)}">{esc(estado)}</span>')


def _tarjeta_salud(salud: dict) -> Seguro:
    if salud.get("estado") == datos.OK:
        cuerpo = render.rejilla([
            render.cifra(Seguro('<span class="estado activo">responde</span>'),
                         "Supabase",
                         detalle=f"{salud.get('tardanza_ms', '?')} ms"),
            render.cifra(render.fecha(salud.get("desde")), "Primer dato"),
            render.cifra(render.fecha(salud.get("hasta")), "Último dato"),
        ])
        pie = ""
    else:
        cuerpo = render.aviso(
            _texto_salud(salud), tono="error" if salud.get("estado") in
            (datos.ERROR, datos.SIN_CREDENCIALES) else "aviso")
        pie = ("Mientras esto no se arregle, las tarjetas vacías de abajo NO "
               "significan «no hubo tráfico».")
    return render.tarjeta("Salud del panel", cuerpo,
                          pregunta="¿Responde Supabase y desde cuándo hay datos?",
                          pie=pie)


def _texto_salud(salud: dict) -> str:
    estado = salud.get("estado")
    if estado == datos.SIN_CREDENCIALES:
        return ("El panel no tiene credenciales de Supabase: falta "
                "SUPABASE_URL / SUPABASE_SERVICE_KEY en su entorno.")
    if estado == datos.TABLA_AUSENTE:
        return ("Supabase responde, pero no encuentra la vista bot_health_daily "
                "(¿falta aplicar la migración s301?).")
    return f"No se puede leer de Supabase: {salud.get('detalle') or 'sin detalle'}."


def _pintar_resultado(resultado: datos.Resultado, *, que: str,
                      si_falta: str = "") -> Seguro:
    """El estado de una lectura, en castellano. Es lo que hace que una tarjeta
    vacía no mienta."""
    if resultado.estado == datos.VACIO:
        return render.nota(f"Sin datos todavía: nadie ha generado {que} en la "
                           f"ventana mirada. No es un fallo.")
    if resultado.estado == datos.TABLA_AUSENTE:
        extra = f" — {si_falta}" if si_falta else ""
        return render.aviso(f"Esa vista no existe todavía en Supabase{extra}.",
                            tono="aviso")
    if resultado.estado == datos.SIN_CREDENCIALES:
        return render.aviso("El panel no tiene credenciales de Supabase.",
                            tono="error")
    if resultado.estado == datos.SIN_TIEMPO:
        return render.aviso(
            "No dio tiempo a cargar esta tarjeta (la página tiene un límite de "
            "tiempo). Ábrela en su detalle para verla sola.", tono="aviso")
    return render.aviso(f"No se pudo leer: {resultado.detalle or 'fallo'}.",
                        tono="error")


def _formatear(valor: object, formato: str) -> str:
    if formato == "numero":
        return render.numero(valor)
    if formato == "ms":
        return render.milisegundos(valor)
    if formato == "pct":
        return render.porcentaje(valor)
    if formato == "fecha":
        return render.fecha(valor)
    if formato == "dia":
        return esc(valor) if valor else "—"
    return esc(valor)


def _tabla_de_vista(vista: datos.Vista, resultado: datos.Resultado) -> Seguro:
    """SOLO columnas declaradas — nada se pinta sin que alguien lo haya
    declarado (s324j, v9 §7). El razonamiento anterior («las de más van al
    final con su nombre crudo») era correcto para un panel interno y se
    invirtió al exponerlo a internet: una columna nueva de una vista NO aparece
    hasta que alguien la declare en `datos.VISTAS`. La dirección contraria —una
    declarada que la vista ya no trae— la detecta el `select` explícito de
    `datos.leer_vista` (la vista responde 42703 y la tarjeta lo dice); si aun
    así llegara una fila sin la columna, aquí simplemente no se pinta y la
    página no rompe."""
    presentes = {c for fila in resultado.filas for c in fila}
    declaradas = [c for c in vista.columnas if c.nombre in presentes]
    cabeceras = [c.etiqueta for c in declaradas]
    filas = [
        [_formatear(fila.get(c.nombre), c.formato) for c in declaradas]
        for fila in resultado.filas
    ]
    # `cards=True`: en móvil estas tablas tienen hasta nueve columnas y se
    # reescriben como tarjetas (s327).
    return render.tabla(cabeceras, filas, cards=True)


def _grafico_de_vista(vista: datos.Vista, resultado: datos.Resultado, *,
                      tope: int = 14) -> Seguro:
    if not vista.grafico or not resultado.filas:
        return Seguro("")
    col_etiqueta, col_valor, unidad = vista.grafico
    if vista.grafico_agregado:
        # (s326, hallazgo Sol r1) Vistas DIMENSIONALES: sumar por etiqueta
        # sobre TODAS las filas cargadas — si no, las «14 filas» mezclan
        # semanas y una etiqueta sale repetida en barras indistinguibles. La
        # ventana del gráfico es la de la tabla (vista.limite) y la tabla
        # sigue siendo la verdad fila a fila.
        total: dict[str, float] = {}
        for f in resultado.filas:
            try:
                total[str(f.get(col_etiqueta, "?"))] = (
                    total.get(str(f.get(col_etiqueta, "?")), 0)
                    + (f.get(col_valor) or 0))
            except TypeError:
                continue
        pares = sorted(total.items(), key=lambda kv: kv[1], reverse=True)[:tope]
    else:
        # Las vistas temporales vienen en orden descendente (lo más reciente
        # primero) porque es como se lee una tabla; el gráfico se lee al revés.
        pares = [(str(f.get(col_etiqueta, "?")), f.get(col_valor))
                 for f in reversed(resultado.filas[:tope])]
    return render.columnas(pares, unidad=unidad, leyenda=vista.leyenda)


#: Cuánto puede tardar la portada LEYENDO, en total (s327, hallazgo Sol). La
#: función de Vercel muere a los 30 s (`vercel.json`) y aquí se encadenan ~16
#: lecturas: sin tope, una Supabase lenta mata la página entera en vez de
#: dejarla pintar sus tarjetas con el estado de cada una. 18 s deja margen
#: holgado para renderizar y responder dentro del límite.
PRESUPUESTO_PORTADA_S = 18.0

#: Barras por gráfica en la PORTADA. Es un resumen: con 14 barras cada tarjeta
#: mide media pantalla y «verlo todo de un vistazo» deja de ser cierto. El
#: detalle enseña la serie completa.
BARRAS_EN_PORTADA = 5


def pagina_resumen(peticion: Peticion) -> Respuesta:
    presupuesto = datos.Presupuesto(PRESUPUESTO_PORTADA_S)
    salud = datos.salud()
    diario = datos.leer_vista(datos.VISTAS_POR_CLAVE["bot_health_daily"],
                              presupuesto)
    allowlist = gestion.listar_allowlist()
    invitaciones = gestion.listar_invitaciones()
    cifras = gestion.resumen_acceso(allowlist, invitaciones)

    ultimos = diario.filas[:7] if diario.estado == datos.OK else []
    consultas = sum(int(f.get("consultas_rag") or 0) for f in ultimos)
    personas = max((int(f.get("usuarios_unicos") or 0) for f in ultimos),
                   default=0)

    # (s324f) Los errores se cuentan de `bot_errors`, la fuente VIVA, y no de
    # `filas_error` de la vista diaria — que cuenta el mecanismo HEREDADO de
    # s286 (`query_logs` con `source='error'`).
    #
    # Cazado abriendo el panel: la portada decía **0 errores** la misma noche en
    # que había DOS registrados, y la pestaña de Errores los enseñaba bien. El
    # sitio donde uno mira primero daba el dato equivocado, que es peor que no
    # dar ninguno: «0 errores» se lee como «todo va bien» y aquí significaba
    # «estoy mirando donde ya no se escribe».
    #
    # Misma ventana de 7 días que el resto de la tarjeta, y misma función que
    # usa la pestaña, para que las dos cifras no puedan volver a divergir.
    incidencias, _heredadas = errores.leer(7)
    # (dúo r41) «no se pudo leer» NO es «cero». El primer arreglo cambió la
    # fuente pero mantuvo el mismo defecto en otra forma: si `bot_errors` no
    # responde, un `0` en la portada se lee como «todo va bien» cuando lo cierto
    # es «no lo sé». La pestaña de Errores sí distinguía las dos cosas, así que
    # las dos pantallas podían volver a divergir justo cuando algo falla.
    fallos = (len(incidencias.filas) if incidencias.estado == datos.OK else None)

    tarjetas = [
        _tarjeta_salud(salud),
        render.tarjeta(
            "Los últimos 7 días",
            render.rejilla([
                render.cifra(render.numero(consultas), "Consultas"),
                render.cifra(render.numero(personas), "Personas (día pico)"),
                (render.cifra(render.numero(fallos), "Errores")
                 if fallos is not None else
                 render.cifra("—", "Errores", detalle="no se pudo leer")),
                render.cifra(render.numero(cifras["con_acceso"]), "Con acceso",
                             detalle=f"{cifras['pendientes']} invitación(es) "
                                     f"pendiente(s)"),
            ]) if ultimos else _pintar_resultado(diario, que="consultas"),
            pregunta="Lo que hay que mirar antes de abrir cualquier pestaña.",
        ),
    ]
    # (s327, pedido de Alberto: «quiero verlo todo de un vistazo, sin scroll»)
    # TODAS las vistas con gráfico, en una rejilla, cada una con su título y su
    # leyenda y clicable hacia su detalle. Se leen en el mismo turno: son 9
    # lecturas a PostgREST, ninguna depende de otra y la página tolera que
    # cualquiera falle (cada tarjeta pinta su estado).
    graficas = []
    for vista in datos.VISTAS:
        if not vista.grafico:
            continue
        resultado = datos.leer_vista(vista, presupuesto)
        if resultado.hay_datos:
            cuerpo = _grafico_de_vista(vista, resultado,
                                       tope=BARRAS_EN_PORTADA)
        else:
            cuerpo = _pintar_resultado(resultado, que="datos de esa vista",
                                       si_falta=vista.si_falta)
        graficas.append((vista.titulo, f"/metricas/{vista.clave}", cuerpo))

    cuerpo_portada = [render.unir(tarjetas)]
    if graficas:
        cuerpo_portada.append(Seguro('<h2 class="seccion">Métricas</h2>'))
        cuerpo_portada.append(render.panel_graficos(graficas))
    return _pagina(peticion, "Resumen", cuerpo_portada, ruta="/")


def pagina_metrica_detalle(peticion: Peticion) -> Respuesta:
    """El detalle de UNA métrica: su gráfico grande y su tabla completa.

    La clave viaja en la RUTA (`/metricas/<clave>`) y se resuelve contra
    `VISTAS_POR_CLAVE` — lista cerrada, igual que los filtros del Explorador:
    lo que no está declarado es un 404, así que de la URL no sale nunca un
    nombre de recurso hacia PostgREST.
    """
    clave = peticion.ruta[len("/metricas/"):].strip("/")
    vista = datos.VISTAS_POR_CLAVE.get(clave)
    if vista is None:
        return _error(404, "No hay nada en esa dirección.", peticion.nonce)

    resultado = datos.leer_vista(vista)
    if resultado.hay_datos:
        cuerpo = render.unir([
            _grafico_de_vista(vista, resultado),
            _tabla_de_vista(vista, resultado),
        ])
    else:
        cuerpo = _pintar_resultado(resultado, que="datos de esa vista",
                                   si_falta=vista.si_falta)
    tarjetas = [
        Seguro('<p class="migas"><a href="/">← Resumen</a> · '
               '<a href="/metricas">Todas las métricas</a></p>'),
        render.tarjeta(vista.titulo, cuerpo, pregunta=vista.pregunta,
                       pie=f"Vista SQL: {vista.clave}"),
    ]
    return _pagina(peticion, vista.titulo, tarjetas, ruta="/metricas")


def pagina_metricas(peticion: Peticion) -> Respuesta:
    # El MISMO presupuesto que la portada, y por el mismo motivo (hallazgo
    # Fable s327: el cierre de S2 se había quedado a medias): esta página lee
    # las 14 vistas y además pinta la tabla entera de cada una, así que es la
    # que más cerca está del límite de la función.
    presupuesto = datos.Presupuesto(PRESUPUESTO_PORTADA_S)
    tarjetas = []
    for vista in datos.VISTAS:
        resultado = datos.leer_vista(vista, presupuesto)
        if resultado.hay_datos:
            cuerpo = render.unir([
                _grafico_de_vista(vista, resultado),
                _tabla_de_vista(vista, resultado),
            ])
        else:
            cuerpo = _pintar_resultado(resultado, que="datos de esa vista",
                                       si_falta=vista.si_falta)
        tarjetas.append(render.tarjeta(
            vista.titulo, cuerpo, pregunta=vista.pregunta,
            pie=f"Vista SQL: {vista.clave}",
            enlace=(f"/metricas/{vista.clave}", "Ver solo esta métrica →")))
    tarjetas.append(render.tarjeta(
        "Sobre quién pregunta",
        render.nota(
            "Desde s326 (adjudicación de Alberto) «Quién pregunta cuánto» SÍ "
            "cruza con la lista de acceso: el alias es la nota de la allowlist "
            "— el mismo dato que ya enseña la pestaña de Acceso. Y el texto de "
            "las preguntas se lee en el Explorador, que reabre a conciencia lo "
            "que DEC-231 dejó fuera de la v1. Sigue siendo dato de personas: "
            "mira solo lo que necesites."),
    ))
    return _pagina(peticion, "Métricas", tarjetas, ruta="/metricas")


def pagina_explorador(peticion: Peticion) -> Respuesta:
    """Pregunta a pregunta, CON su texto (adjudicación (a), s326): clasificación,
    feedback del autor y su comentario. Filtros de listas CERRADAS (patrón
    errores.py): nada de la URL se parsea, se elige o cae al defecto."""
    categorias = explorador.categorias_validas()
    marcas, marcas_ok = explorador.marcas_disponibles()
    filtros = explorador.normalizar(peticion.consulta,
                                    categorias=categorias, marcas=marcas)
    resultado = explorador.leer(filtros)

    _opciones = _opciones_select

    dias = _opciones(
        [(str(d), "todo" if d == 0 else f"{d} días")
         for d in explorador.VENTANAS], str(filtros.dias))
    categoria = _opciones(
        [("", "todas")] + [(c, c) for c in categorias], filtros.categoria or "")
    marca = _opciones(
        [("", "todas")] + [(m, m) for m in marcas], filtros.marca or "")
    feedback = _opciones(
        [("todos", "todos"), ("up", "👍"), ("down", "👎"),
         ("comentados", "con comentario")], filtros.feedback)
    tipo = _opciones(
        [("preguntas", "solo preguntas"), ("no_preguntas", "solo lo que NO lo es"),
         ("todos", "todo")], filtros.tipo)

    tarjetas = [render.tarjeta(
        "Filtros",
        render.unir([Seguro(
            # GET a propósito: leer no cambia estado, no lleva CSRF, y la URL
            # resultante se puede compartir entre los usuarios del panel.
            '<form method="get" action="/explorador">'
            f'<label>Periodo<select name="dias">{dias}</select></label>'
            f'<label>Categoría<select name="categoria">{categoria}</select></label>'
            f'<label>Fabricante<select name="marca">{marca}</select></label>'
            f'<label>Feedback<select name="feedback">{feedback}</select></label>'
            f'<label>Tipo<select name="tipo">{tipo}</select></label>'
            '<button type="submit" class="principal">Aplicar</button>'
            "</form>")] + ([] if marcas_ok else [render.aviso(
                # «no hay marcas» y «no se pudo leer la lista» son pantallas
                # distintas (Fable r1 s326): sin esto, el filtro desaparecía en
                # silencio justo cuando Supabase falla.
                "No se pudo leer la lista de fabricantes: ese filtro no está "
                "disponible ahora.", tono="aviso")])),
        pregunta="Listas cerradas: periodo, feedback y tipo son fijos, la "
                 "categoría es la taxonomía vigente y las marcas son las "
                 "canónicas del corpus. Por defecto solo se listan los "
                 "mensajes que PIDEN algo (s327).",
    )]

    if resultado.estado == datos.OK:
        def _fila(f: dict) -> list:
            veredicto = {"up": "👍", "down": "👎"}.get(f.get("verdict") or "", "—")
            if f.get("reason_class"):
                veredicto += f" · {f['reason_class']}"
            return [
                esc(str(f.get("created_at") or "")[:16].replace("T", " ")),
                esc(f.get("quien")),
                esc(f"{f.get('canal') or '?'} · {f.get('ruta') or '?'}"),
                esc(f.get("categoria") or "(sin clasificar)"),
                esc(", ".join((f.get("marcas") or []) + (f.get("modelos") or []))
                    or "—"),
                Seguro(f'<span class="ancho">{esc(f.get("pregunta"))}</span>'),
                esc(veredicto),
                (Seguro(f'<span class="ancho">{esc(f.get("comment"))}</span>')
                 if f.get("comment") else "—"),
            ]

        tarjetas.append(render.tarjeta(
            f"{len(resultado.filas)} pregunta(s)",
            render.tabla(
                ["Cuándo", "Quién", "Canal · ruta", "Categoría",
                 "Marcas y modelos", "Pregunta", "Feedback", "Comentario"],
                [_fila(f) for f in resultado.filas],
                cards=True,
            ),
            pregunta=f"De la más reciente a la más antigua (tope "
                     f"{explorador.TOPE_FILAS}; para exportar, SQL en Supabase).",
            pie="Prosa escrita por técnicos — dato personal (s326 reabre el "
                "«fuera de v1» de DEC-231): mira solo lo que necesites.",
        ))
    else:
        tarjetas.append(render.tarjeta(
            "Preguntas",
            _pintar_resultado(
                resultado, que="preguntas con esos filtros",
                si_falta="falta aplicar migrations/021_query_clasificacion.sql"),
        ))
    return _pagina(peticion, "Explorador", tarjetas, ruta="/explorador")


def _opciones_select(pares, elegido: str) -> str:
    """`[(valor, texto)]` → `<option>`s, con el elegido marcado. Estaba escrito
    dos veces (Explorador y Catálogo) y es exactamente el mismo HTML."""
    return "".join(
        f'<option value="{atributo(valor)}"'
        + (" selected" if valor == elegido else "")
        + f">{esc(texto)}</option>"
        for valor, texto in pares
    )


def pagina_catalogo(peticion: Peticion) -> Respuesta:
    """La **Wiki de modelos**: qué modelos conoce el bot y con qué manuales
    responde de cada uno (s331, pedido de Alberto en el packet de adjudicación).

    Filtros de listas CERRADAS como el resto del panel, con UNA excepción
    declarada: `q` es texto libre porque el catálogo se filtra EN MEMORIA —
    ese parámetro no viaja a ninguna consulta. El razonamiento completo está
    en el módulo `dashboard/catalogo.py`.
    """
    ind = catalogo.indice()
    filtros = catalogo.normalizar(peticion.consulta, marcas=ind.marcas,
                                  categorias=ind.categorias)
    resumen = catalogo.resumen()

    if not resumen["leido"]:
        # No es «no hay modelos»: es «no pude leer el catálogo». La diferencia
        # importa — en Vercel el modo de fallo esperado es que `data/catalog/`
        # no haya viajado al bundle, y eso NO puede parecer un catálogo vacío.
        # PASÓ DE VERDAD (s331d): la primera versión de esta página salió con
        # «0 modelos» y sin aviso, porque `catalog_store` devuelve listas vacías
        # cuando los ficheros no están en vez de lanzar. Ahora `leido` significa
        # «estaba ahí y traía productos».
        return _pagina(peticion, "Modelos", [render.tarjeta(
            "Modelos",
            render.aviso("No se pudo leer el catálogo gobernado "
                         "(data/catalog/*.jsonl): o no está en el bundle o vino "
                         "vacío. En producción lo más probable es que el "
                         "directorio no haya viajado — revisa .vercelignore, y "
                         "recuerda que gitignore NO deja re-incluir algo dentro "
                         "de un directorio excluido.", tono="error"),
        )], ruta="/catalogo")

    filas, total = catalogo.buscar(filtros)

    marca = _opciones_select(
        [("", "todas")] + [(m, m) for m in ind.marcas], filtros.marca or "")
    estado = _opciones_select(
        [("consumibles", "los que el bot usa"), ("candidates", "en cuarentena"),
         ("redirects", "el mismo equipo con otra marca"),
         ("retirados", "retirados"), ("todos", "todos")], filtros.estado)
    docs = _opciones_select(
        [("todos", "con o sin manual"), ("con", "solo con manual"),
         ("sin", "solo SIN manual")], filtros.docs)
    categoria = _opciones_select(
        [("", "todas")] + [(c, c) for c in ind.categorias]
        + [(catalogo.SIN_CATEGORIA, catalogo.SIN_CATEGORIA)],
        filtros.categoria or "")
    # El autocompletado del buscador: `<datalist>` es MARCADO, no script, así
    # que da el pre-filtrado según se teclea con la CSP `default-src 'none'`
    # intacta y sin una línea de JavaScript (pedido de Alberto, s331d).
    sugeridos = catalogo.sugerencias(filtros)
    datalist = ('<datalist id="modelos">'
                + "".join(f'<option value="{esc(x)}">' for x in sugeridos)
                + "</datalist>")

    cifras = render.rejilla([
        render.cifra(resumen["modelos"], "modelos que el bot usa",
                     detalle=f"{resumen['marcas']} fabricantes"),
        render.cifra(resumen["sin_docs"], "sin ningún manual",
                     detalle="el catálogo los conoce, el corpus no los cubre"),
        render.cifra(resumen["candidates"], "en cuarentena",
                     detalle="propuestos, aún sin adjudicar"),
        render.cifra(resumen["sin_clasificar"], "sin categoría de producto",
                     detalle=f"solo {resumen['clasificados']} clasificados "
                             f"con cita"),
        render.cifra(resumen["docs_huerfanos"], "manuales huérfanos",
                     detalle="no atestan a ningún modelo utilizable"),
    ])

    def _fila(m: catalogo.Modelo) -> list:
        marcas_venta = ", ".join(m.vendido_bajo) or "—"
        return [
            Seguro(f'<a href="/catalogo/{esc(m.id)}">{esc(m.canonico)}</a>'),
            esc(m.marca),
            esc(m.familia or "—"),
            esc(m.categoria or "—"),
            esc(marcas_venta),
            esc(m.n_docs) if m.n_docs else Seguro('<strong>0</strong>'),
            esc(m.n_alias),
        ]

    recorte = ("" if total <= catalogo.TOPE_FILAS else
               f" — se pintan {len(filas)}, afina el filtro para ver el resto")
    tarjetas = [
        render.tarjeta(
            "El catálogo de un vistazo", cifras,
            pregunta="Lo que el bot PUEDE usar hoy para responder: modelo "
                     "activo y ya adjudicado. Un modelo en cuarentena existe "
                     "en el catálogo pero el bot no lo consume.",
        ),
        render.tarjeta(
            "Buscar",
            Seguro(
                '<form method="get" action="/catalogo">'
                f'<label>Texto<input type="search" name="q" list="modelos"'
                f' autocomplete="off" maxlength="{catalogo._Q_MAX}"'
                f' value="{atributo(filtros.q)}" placeholder="escribe CAD, minilaser…">'
                f"</label>{datalist}"
                f'<label>Categoría<select name="categoria">{categoria}</select></label>'
                f'<label>Fabricante<select name="marca">{marca}</select></label>'
                f'<label>Estado<select name="estado">{estado}</select></label>'
                f'<label>Manuales<select name="docs">{docs}</select></label>'
                '<button type="submit" class="principal">Aplicar</button>'
                "</form>"),
            pregunta="Al escribir salen los modelos que casan (teclea «CAD» y "
                     "aparecen CAD-171, CAD-250…): eliges uno y pulsas Aplicar. "
                     "El texto busca también en los ALIAS, así que «minilaser» "
                     "encuentra el modelo cuyo nombre canónico es un código de "
                     "pedido.",
            pie=f"{len(sugeridos)} modelo(s) sugeridos con los filtros de "
                f"categoría, fabricante y estado que tengas puestos.",
        ),
        render.tarjeta(
            f"{total} modelo(s){recorte}",
            render.tabla(
                ["Modelo", "Fabricante", "Familia", "Categoría",
                 "Se vende como", "Manuales", "Alias"],
                [_fila(m) for m in filas],
                vacio="Ningún modelo casa con esos filtros.",
                cards=True,
            ),
            pie="Fuente: el catálogo gobernado del repo — la MISMA estructura "
                "que el bot consulta para resolver un modelo. Para cambiar "
                "algo hace falta un lote firmado con recibo, no un botón.",
        ),
    ]
    return _pagina(peticion, "Modelos", tarjetas, ruta="/catalogo")


def pagina_catalogo_ficha(peticion: Peticion) -> Respuesta:
    """La ficha de UN modelo: sus alias, sus manuales, sus relaciones y los
    paraguas que lo contienen. El id viaja en la ruta y se busca en el dict del
    catálogo — lo que no existe es un 404, nunca un nombre de recurso hacia
    PostgREST (mismo criterio que `/metricas/<clave>`)."""
    pid = urllib.parse.unquote(peticion.ruta[len("/catalogo/"):]).strip("/")
    f = catalogo.ficha(pid)
    if f is None:
        return _error(404, "No hay ningún modelo con ese identificador.",
                      peticion.nonce)

    m = f.modelo
    estados = catalogo.estado_de_documentos(tuple(d[2] for d in f.documentos))
    clase = {"consumibles": "el bot lo usa", "candidates": "en cuarentena",
             "redirects": "el mismo equipo con otra marca",
             "retirados": "retirado"}[catalogo._clase(m)]

    identidad = render.tabla(
        ["Campo", "Valor"],
        [["Identificador", Seguro(f"<code>{esc(m.id)}</code>")],
         ["Nombre canónico", esc(m.canonico)],
         ["Estado", esc(f"{clase} ({m.estado})")]]
        + ([["Es el mismo equipo que",
             Seguro(f'<a href="/catalogo/{esc(m.redirige_a)}">'
                    f'{esc(m.redirige_a)}</a>')]] if m.redirige_a else [])
        + [
         ["Familia", esc(m.familia or "—")],
         ["Categoría", esc(m.categoria or "—")],
         ["Cita de la categoría", esc(f.modelo.categoria_cita or "—")],
         ["Se vende bajo", esc(", ".join(m.vendido_bajo) or "—")],
         ["Alias", esc(", ".join(f.alias) or "—")],
         ["Paraguas que lo contienen", esc(", ".join(f.paraguas) or "—")],
         ["Origen de la fila", esc(f.provenance or "—")]],
        cards=True,
    )

    def _doc(d) -> list:
        fuente, rol, did = d
        est = estados.get(did, "")
        return [esc(fuente), esc(rol),
                esc(est or "—") if est == "active" else
                Seguro(f"<strong>{esc(est or '?')}</strong>")]

    documentos = render.tabla(
        ["Manual", "Rol", "Estado"], [_doc(d) for d in f.documentos],
        vacio="Este modelo no tiene ningún manual asociado: el bot lo conoce "
              "pero no tiene con qué responder sobre él.",
        cards=True,
    )

    relaciones = render.tabla(
        ["Relación", "Con", ""],
        [[esc(t), Seguro(f'<a href="/catalogo/{esc(o)}">{esc(o)}</a>'), esc(d)]
         for t, o, d in f.relaciones],
        vacio="Sin relaciones declaradas.", cards=True,
    )

    tarjetas = [
        Seguro('<p class="migas"><a href="/catalogo">← Modelos</a></p>'),
        render.tarjeta(m.canonico, identidad,
                       pregunta="Los identificadores son INMUTABLES: un modelo "
                                "mal nombrado se corrige con un alias o un "
                                "redirect, nunca renombrando el id."),
        render.tarjeta(f"{len(f.documentos)} manual(es)", documentos,
                       pregunta="`primary` = el manual reclama el modelo como "
                                "sujeto. `secondary` = lo menciona y sirve como "
                                "fuente, sin reclamarlo.",
                       pie="El estado sale de Supabase; si no se pudo leer, la "
                           "columna queda en «?»."),
        render.tarjeta("Relaciones", relaciones),
    ]
    return _pagina(peticion, m.canonico, tarjetas, ruta="/catalogo")


def pagina_errores(peticion: Peticion) -> Respuesta:
    dias = errores.ventana_valida(
        (peticion.consulta.get("dias") or [""])[0]
    )
    incidencias, heredadas = errores.leer(dias)
    resumen = errores.resumen(incidencias, heredadas)

    enlaces = " · ".join(
        f'<a href="/errores?dias={d}">{"todo" if d == 0 else str(d) + " días"}</a>'
        if d != dias else
        f'<strong>{"todo" if d == 0 else str(d) + " días"}</strong>'
        for d in errores.VENTANAS
    )
    tarjetas = [
        render.tarjeta("Ventana", Seguro(f'<p class="pregunta">{enlaces}</p>'),
                       pregunta="Qué periodo se está mirando."),
    ]

    if incidencias.estado == datos.OK:
        tarjetas.append(render.tarjeta(
            "Incidencias registradas",
            render.rejilla([
                render.cifra(render.numero(resumen["n_incidencias"]),
                             "Incidencias"),
                render.cifra(render.numero(resumen["tecnicos_afectados"]),
                             "Técnicos afectados"),
                render.cifra(render.numero(resumen["sin_avisar"]),
                             "Sin aviso al técnico",
                             detalle="el fallo que este trabajo existe para "
                                     "que sea 0"),
            ]),
            pregunta="Cuánto y a cuántos.",
        ))
        for titulo, clave, pregunta in (
            ("Por clase de fallo", "por_clase",
             "Separa «hay que esperar» de «hay que arreglar código»."),
            ("Por severidad", "por_severidad", ""),
            ("Por etapa", "por_etapa", "En qué punto del turno nace."),
            ("Por módulo:línea", "por_origen", "La cola de trabajo, ordenada."),
            ("Por día", "por_dia", "Un pico y un goteo son problemas distintos."),
        ):
            conteos = list(resumen[clave].items())[:12]
            tarjetas.append(render.tarjeta(
                titulo,
                render.unir([
                    render.columnas([(k, v) for k, v in conteos]),
                    render.tabla(["Valor", "Incidencias"],
                                 [[k, render.numero(v)] for k, v in conteos]),
                ]) if conteos else render.nota("Ninguna."),
                pregunta=pregunta,
            ))
        tarjetas.append(render.tarjeta(
            "Las preguntas que más fallan",
            render.tabla(
                ["Veces", "Pregunta"],
                [[render.numero(n), Seguro(f'<span class="ancho">'
                                           f"{render.recorte(q, 110)}</span>")]
                 for q, n in resumen["top_preguntas"]],
                vacio="Ninguna incidencia tiene consulta enlazada.",
            ),
            pregunta="Una pregunta que rompe el bot dos veces es material de "
                     "eval, no una anécdota.",
            pie="Texto escrito por técnicos: se muestra recortado y sin autor.",
        ))
    else:
        tarjetas.append(render.tarjeta(
            "Incidencias registradas",
            _pintar_resultado(incidencias, que="errores",
                              si_falta="falta aplicar migrations/015_bot_errores.sql"),
            pie="El bot NO está roto por esto: sin la tabla, los errores "
                "quedan degradados en query_logs (abajo).",
        ))

    tarjetas.append(render.tarjeta(
        "Filas de error heredadas (query_logs)",
        render.unir([
            render.tabla(
                ["Marca Tipo@etapa", "Filas"],
                [[k, render.numero(v)]
                 for k, v in list(resumen["heredadas_por_tipo"].items())[:12]],
                vacio="Ninguna.",
            ),
            render.nota(
                "Las dos fuentes NO se suman: desde que la 015 está aplicada, "
                "cada error escribe en las dos y sumarlas contaría cada fallo "
                "dos veces."),
        ]),
        pregunta="El histórico anterior a la tabla de errores (s286).",
    ))
    return _pagina(peticion, "Errores", tarjetas, ruta="/errores")


def _fila_allowlist(fila: dict, csrf: str) -> list:
    revocado = bool(fila.get("revocado_at"))
    identificador = fila.get("telegram_user_id")
    if revocado:
        accion = Seguro(f'<span class="nota">{render.fecha(fila.get("revocado_at"))}'
                        f"</span>")
    else:
        accion = render.formulario(
            "/acceso/revocar", csrf,
            Seguro(
                f'<input type="hidden" name="telegram_user_id" '
                f'value="{esc(identificador)}">'
                f'<input type="hidden" name="motivo" value="revocado desde el panel">'
            ),
            boton="Revocar acceso", peligroso=True,
        )
    return [
        _estado_pintado("revocado" if revocado else "activo"),
        esc(identificador),
        Seguro(f'<span class="ancho">{render.recorte(fila.get("nota"), 60)}</span>'),
        esc(fila.get("origen")),
        render.fecha(fila.get("alta_at")),
        esc(fila.get("alta_por")),
        accion,
    ]


def _fila_invitacion(fila: dict, csrf: str, ahora) -> list:
    estado = access.estado_invitacion(fila, ahora)
    if estado == access.ESTADO_PENDIENTE:
        accion = render.formulario(
            "/acceso/anular-invitacion", csrf,
            Seguro(f'<input type="hidden" name="invitacion_id" '
                   f'value="{esc(fila.get("id"))}">'),
            boton="Anular", peligroso=True,
        )
    else:
        accion = Seguro("")
    return [
        _estado_pintado(estado),
        Seguro(f'<span class="ancho">{render.recorte(fila.get("nota"), 60)}</span>'),
        render.fecha(fila.get("expira_at")),
        esc(fila.get("canjeada_por")),
        esc(fila.get("creada_por")),
        accion,
    ]


def pagina_acceso(peticion: Peticion, *, resultado: gestion.Accion | None = None,
                  avisar_pendientes: bool = False) -> Respuesta:
    csrf = peticion.csrf
    allowlist = gestion.listar_allowlist()
    invitaciones = gestion.listar_invitaciones()
    cifras = gestion.resumen_acceso(allowlist, invitaciones)
    ahora = datetime.now(timezone.utc)

    tarjetas = []
    if resultado is not None:
        banda = [render.aviso(resultado.mensaje,
                              tono=resultado.tono if not resultado.ok else "bien")]
        if resultado.enlace:
            banda.append(Seguro(
                f'<div class="enlace">{esc(resultado.enlace)}</div>'))
            banda.append(render.nota(
                "Mándaselo por el canal que uses. Es de UN SOLO USO: quien lo "
                "pulse primero se queda el acceso."))
        if avisar_pendientes:
            pendientes = gestion.invitaciones_pendientes_tras_revocar(invitaciones)
            if pendientes:
                banda.append(render.aviso(
                    f"Hay {len(pendientes)} invitación(es) PENDIENTES. Si alguna "
                    f"era para esta persona, anúlala también o volverá a entrar.",
                    tono="aviso"))
        tarjetas.append(render.tarjeta("Resultado", render.unir(banda)))

    tarjetas.append(render.tarjeta(
        "Invitar a alguien",
        render.formulario(
            "/acceso/invitar", csrf,
            Seguro(
                # `op` identifica LA OPERACIÓN, no su contenido (s324j, v9
                # §4.2): nace al PINTAR el formulario, viaja oculto, y el
                # UNIQUE de la base convierte el F5 (mismo op) en «ya emitiste»
                # sin crear una segunda credencial. Dos pestañas = dos op = dos
                # invitaciones — correcto, porque son dos operaciones.
                f'<input type="hidden" name="op" value="{esc(secrets.token_urlsafe(16))}">'
                '<label>Para quién es (nombre y cargo)'
                '<input name="nota" maxlength="200" required '
                'placeholder="Juan Pérez, DG de Acme"></label>'
                '<label>Caduca en'
                f'<select name="dias">'
                + "".join(
                    f'<option value="{d}"'
                    + (" selected" if d == access.DIAS_CADUCIDAD_DEFECTO else "")
                    + f">{d} día{'s' if d > 1 else ''}</option>"
                    for d in range(1, access.DIAS_CADUCIDAD_MAX + 1)
                )
                + "</select></label>"
            ),
            boton="Generar enlace",
        ),
        pregunta="Se emite un enlace de un solo uso. El enlace se ve UNA vez: "
                 "en la base sólo queda su huella.",
        pie=f"La nota es obligatoria: sin «para quién es», el listado no se "
            f"puede auditar. Máximo {access.DIAS_CADUCIDAD_MAX} días.",
    ))

    tarjetas.append(render.tarjeta(
        "Quién puede usar el bot",
        render.tabla(
            ["Estado", "ID de Telegram", "Quién es", "Origen", "Alta",
             "Alta por", ""],
            [_fila_allowlist(f, csrf) for f in allowlist.filas],
        ) if allowlist.hay_datos else _pintar_resultado(
            allowlist, que="altas",
            si_falta="falta aplicar migrations/016_allowlist_invitaciones.sql"),
        pregunta=f"{cifras['con_acceso']} con acceso · {cifras['revocados']} "
                 f"revocados.",
        pie="Revocar deja de dar acceso en hasta 10 min (60 si Supabase está "
            "caído). Para cortar al instante, reinicia el bot en Railway.",
    ))

    tarjetas.append(render.tarjeta(
        "Invitaciones",
        render.tabla(
            ["Estado", "Para quién", "Caduca", "Canjeada por", "Emitida por",
             ""],
            [_fila_invitacion(f, csrf, ahora) for f in invitaciones.filas],
        ) if invitaciones.hay_datos else _pintar_resultado(
            invitaciones, que="invitaciones",
            si_falta="falta aplicar migrations/016_allowlist_invitaciones.sql"),
        pregunta=f"{cifras['pendientes']} pendiente(s) · {cifras['usadas']} "
                 f"usada(s).",
        pie="«Canjeada por» es quien PULSÓ el enlace; si no coincide con la "
            "nota, el enlace se reenvió y hay que revocar ese acceso.",
    ))
    return _pagina(peticion, "Acceso", tarjetas, ruta="/acceso")


def accion_invitar(peticion: Peticion) -> Respuesta:
    resultado = gestion.generar_invitacion(
        nota=peticion.campo("nota"),
        dias=peticion.campo("dias", str(access.DIAS_CADUCIDAD_DEFECTO)),
        por=peticion.usuario,
        op=peticion.campo("op"),
    )
    # Se RENDERIZA en vez de redirigir, y es deliberado: el enlace se enseña una
    # sola vez y no puede viajar en la URL de una redirección (quedaría en el
    # historial del navegador y en los logs de cualquier proxy). El F5 que ese
    # render deja abierto NO emite una credencial de más: reenvía el MISMO `op`,
    # que choca con el UNIQUE de la base y produce el aviso «ya emitiste esta
    # invitación» sin crear nada (s324j, v9 §4.2 — la idempotencia por
    # operación es lo que sustituye al PRG que aquí no se puede usar).
    return pagina_acceso(peticion, resultado=resultado)


def accion_anular_invitacion(peticion: Peticion) -> Respuesta:
    resultado = gestion.revocar_invitacion(
        invitacion_id=peticion.campo("invitacion_id"), por=peticion.usuario)
    return pagina_acceso(peticion, resultado=resultado)


def accion_revocar_acceso(peticion: Peticion) -> Respuesta:
    resultado = gestion.revocar_acceso(
        telegram_user_id=peticion.campo("telegram_user_id"),
        por=peticion.usuario,
        motivo=peticion.campo("motivo"),
    )
    return pagina_acceso(peticion, resultado=resultado,
                         avisar_pendientes=resultado.ok)


def _pagina(peticion: Peticion, titulo: str, tarjetas, *,
            ruta: str) -> Respuesta:
    cuerpo = render.unir([Seguro(f"<h1>{esc(titulo)}</h1>")] + list(tarjetas))
    documento = render.pagina(
        f"{titulo} · Panel del bot", cuerpo, nonce=peticion.nonce,
        usuario=peticion.usuario, ruta=ruta, csrf=peticion.csrf,
    )
    return Respuesta(cuerpo=documento.encode("utf-8"))


# ---------------------------------------------------------------------- rutas

RUTAS = {
    ("GET", "/"): pagina_resumen,
    ("GET", "/acceso"): pagina_acceso,
    ("GET", "/metricas"): pagina_metricas,
    # `/metricas/<clave>`: el prefijo es la clave de enrutado (ver `despachar`);
    # NO está en RUTAS_PUBLICAS, así que pasa por la puerta como cualquier otra.
    ("GET", "/metricas/"): pagina_metrica_detalle,
    ("GET", "/catalogo"): pagina_catalogo,
    # Ficha de un modelo. Segunda ruta con parámetro del panel: se
    # normaliza a su clave ANTES de la puerta, igual que /metricas/.
    ("GET", "/catalogo/"): pagina_catalogo_ficha,
    ("GET", "/explorador"): pagina_explorador,
    ("GET", "/errores"): pagina_errores,
    ("GET", "/entrar"): pagina_entrar,
    ("POST", "/entrar"): accion_entrar,
    ("POST", "/salir"): accion_salir,
    ("POST", "/acceso/invitar"): accion_invitar,
    ("POST", "/acceso/anular-invitacion"): accion_anular_invitacion,
    ("POST", "/acceso/revocar"): accion_revocar_acceso,
}


def _error(estado: int, texto: str, nonce: str) -> Respuesta:
    """Una página de error SIN contexto: ni menú, ni usuario, ni pistas de qué
    hay detrás. Un 404 del panel se tiene que parecer al 404 de cualquier sitio."""
    cuerpo = Seguro(
        f'<div class="entrar"><h1>{esc(estado)}</h1>'
        f'<section class="tarjeta">{render.nota(texto)}'
        f'<p class="pie"><a href="/entrar">Ir a la entrada</a></p>'
        f"</section></div>"
    )
    documento = render.pagina(f"{estado} · Panel del bot", cuerpo, nonce=nonce)
    return Respuesta(estado=estado, cuerpo=documento.encode("utf-8"))


def despachar(peticion: Peticion) -> Respuesta:
    """La puerta. Nada de aquí abajo se salta ningún paso de arriba — con UNA
    excepción declarada y acotada: `POST /salir` verifica firma y CSRF pero NO
    revalida el sello contra el backend (s324j, v9 §2, ronda S4-m1) — borrar tu
    propia cookie no puede depender de que Supabase responda, y el logout no
    lee ni escribe nada de nadie, así que saltarse la revalidación no abre
    ninguna puerta."""
    clave = (peticion.metodo, peticion.ruta)
    manejador = RUTAS.get(clave)
    if manejador is None and peticion.metodo == "GET":
        # Las rutas CON PARÁMETRO del panel (s327, s331). Se normalizan a su
        # clave ANTES de la puerta, así que heredan TODAS sus comprobaciones —
        # y el sufijo no se usa como nombre de recurso: cada manejador lo
        # resuelve contra su lista cerrada (`VISTAS_POR_CLAVE`, el dict de
        # productos del catálogo) o devuelve 404.
        for prefijo in ("/metricas/", "/catalogo/"):
            if peticion.ruta.startswith(prefijo):
                clave = ("GET", prefijo)
                manejador = RUTAS.get(clave)
                break
    if manejador is None:
        return _error(404, "No hay nada en esa dirección.", peticion.nonce)

    if clave not in RUTAS_PUBLICAS:
        payload = sesion.verificar(
            sesion.leer_cookie(peticion.cabeceras.get("cookie")),
            sesion.secreto(),
        )
        if payload is None:
            # 303 a la entrada y NUNCA un 401 con contenido: quien no tiene
            # sesión no ve ni el esqueleto de la página protegida.
            return _redirigir("/entrar")
        peticion.sesion = payload

    # Origen y CSRF van ANTES de la revalidación de sello (ronda del dúo sobre
    # el cableado, F-m1): son comprobaciones LOCALES (gratis), la del sello es
    # un RTT a Supabase. Un POST malformado o cross-site con sesión válida no
    # debe gastar una llamada de red antes de un rechazo que se computa gratis.
    # El resultado aceptar/rechazar es idéntico — solo cambia cuál rechazo gana
    # y se quita la amplificación.
    if peticion.metodo == "POST":
        if not _mismo_origen(peticion):
            return _error(403, "Petición rechazada: viene de otro sitio.",
                          peticion.nonce)
        if clave not in RUTAS_PUBLICAS and not sesion.csrf_valido(
                peticion.sesion or {}, peticion.campo("csrf")):
            return _error(403, "Formulario caducado. Vuelve a cargar la página.",
                          peticion.nonce)

    if clave not in RUTAS_PUBLICAS and clave != ("POST", "/salir"):
        # LA REVALIDACIÓN POR PETICIÓN (v9 §2): el sello de la cookie contra el
        # sello VIGENTE del backend. Es lo que hace efectivos en la SIGUIENTE
        # petición la revocación y el cambio de contraseña — la promesa por la
        # que Alberto eligió (a2). La regla completa:
        #   · `h` ausente o no-cadena → fuera (cookies de antes del despliegue;
        #     `compare_digest` no llega a ver un None);
        #   · `sello(u)` devuelve None (revocado/cambiada) → fuera;
        #   · sellos distintos → fuera;
        #   · el backend NO PUDO comprobar → 503 sin servir nada y SIN matar la
        #     cookie (un timeout no es un cierre de sesión falso; el revocado
        #     durante la caída ve el mismo 503 que todos).
        # «Fuera» es siempre el mismo camino: 303 a /entrar borrando la cookie.
        # `/salir` es la excepción declarada: borrar tu propia cookie no puede
        # depender de que Supabase responda.
        payload = peticion.sesion or {}
        h = payload.get("h")
        if not isinstance(h, str) or not h:
            return _redirigir("/entrar", extra=[
                ("set-cookie", sesion.cabecera_borrado())])
        try:
            vigente = auth.backend_activo().sello(payload["u"])
        except auth.IdentidadNoDisponible:
            return _error(503, _TEXTO_503, peticion.nonce)
        if vigente is None or not hmac.compare_digest(vigente, h):
            return _redirigir("/entrar", extra=[
                ("set-cookie", sesion.cabecera_borrado())])

    return manejador(peticion)


# ------------------------------------------------------------------ capa ASGI


async def _leer_cuerpo(receive) -> bytes | None:
    """El cuerpo entero, o `None` si se pasa del tope."""
    trozos, total = [], 0
    while True:
        evento = await receive()
        if evento["type"] == "http.disconnect":
            return b""
        trozos.append(evento.get("body", b""))
        total += len(trozos[-1])
        if total > CUERPO_MAX_BYTES:
            return None
        if not evento.get("more_body"):
            return b"".join(trozos)


async def app(scope, receive, send) -> None:
    if scope["type"] == "lifespan":
        while True:
            mensaje = await receive()
            if mensaje["type"] == "lifespan.startup":
                try:
                    comprobar_arranque()
                except Exception as exc:                         # noqa: BLE001
                    await send({"type": "lifespan.startup.failed",
                                "message": str(exc)})
                    return
                await send({"type": "lifespan.startup.complete"})
            elif mensaje["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    if scope["type"] != "http":
        return

    cabeceras = {k.decode("latin-1").lower(): v.decode("latin-1")
                 for k, v in scope.get("headers", [])}
    metodo = scope["method"].upper()
    # El nonce nace AQUÍ, uno por petición, y viaja hasta la cabecera y hasta el
    # `<style>` del documento. Que lo ponga la capa de transporte es lo que
    # garantiza que no hay respuesta sin CSP.
    nonce = _nonce()
    cuerpo = b""
    if metodo in ("POST", "PUT", "PATCH"):
        tipo = cabeceras.get("content-type", "")
        if not tipo.startswith("application/x-www-form-urlencoded"):
            await _enviar(send, _error(415, "Formato de envío no admitido.",
                                       nonce), nonce)
            return
        leido = await _leer_cuerpo(receive)
        if leido is None:
            await _enviar(send, _error(413, "Envío demasiado grande.", nonce),
                          nonce)
            return
        cuerpo = leido

    cliente = scope.get("client") or ("", 0)
    peticion = Peticion(
        metodo="GET" if metodo == "HEAD" else metodo,
        ruta=scope.get("path", "/") or "/",
        consulta=urllib.parse.parse_qs(
            (scope.get("query_string") or b"").decode("latin-1")),
        cabeceras=cabeceras,
        cuerpo=cuerpo,
        ip=_ip_cliente(cabeceras, cliente[0] if cliente else ""),
        nonce=nonce,
    )
    try:
        respuesta = despachar(peticion)
    except Exception:                                            # noqa: BLE001
        # Última red. Lo que NO se hace: enseñar la excepción. Un 500 del panel
        # sale con el mismo cuerpo genérico que cualquier otro error; el detalle
        # va a los logs del proceso, que es donde lo puede leer quien despliega.
        import logging
        logging.getLogger(__name__).exception("fallo sirviendo %s", peticion.ruta)
        respuesta = _error(500, "Algo ha fallado en el panel.", nonce)
    if metodo == "HEAD":
        respuesta = Respuesta(respuesta.estado, b"", respuesta.tipo,
                              respuesta.extra)
    await _enviar(send, respuesta, nonce)


async def _enviar(send, respuesta: Respuesta, nonce: str) -> None:
    cabeceras = [(b"content-type", respuesta.tipo.encode("latin-1")),
                 (b"content-length", str(len(respuesta.cuerpo)).encode())]
    for nombre, valor in respuesta.extra + _cabeceras_seguridad(
            nonce, fuente=respuesta.fuente_incrustada):
        cabeceras.append((nombre.encode("latin-1"),
                          str(valor).encode("latin-1")))
    await send({"type": "http.response.start", "status": respuesta.estado,
                "headers": cabeceras})
    await send({"type": "http.response.body", "body": respuesta.cuerpo})


def comprobar_arranque() -> None:
    """Lo que TIENE que estar bien antes de aceptar la primera petición.

    Se ejecuta en el `lifespan` de ASGI, así que un fallo aquí impide que
    uvicorn empiece a servir: el despliegue anterior se conserva y el motivo
    queda escrito en los logs. Mismo criterio que `access.validar_configuracion`
    en el bot.

    Con los backends de Supabase enchufados (v9 §9/§3.5) comprueba TAMBIÉN lo
    suyo: credenciales presentes, y la sonda del cerrojo (`panel_puerta` con
    claves vacías — extremo a extremo real, sin tocar contadores). LÍMITE
    declarado: en el runtime de Vercel el `lifespan` no está garantizado; allí
    el control compensatorio es el smoke del runbook, y en runtime los estados
    de configuración fail-CIERRAN igualmente (503).
    """
    sesion.secreto()
    auth.validar_configuracion()
    if isinstance(auth.backend_activo(), auth.BackendSupabase):
        if not datos.hay_credenciales():
            raise RuntimeError(
                "El backend de usuarios es Supabase y faltan SUPABASE_URL / "
                "SUPABASE_SERVICE_KEY: el panel no podría autenticar a nadie."
            )
    cerrojo.sonda()
