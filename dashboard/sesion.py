# -*- coding: utf-8 -*-
"""La sesión del panel: una cookie FIRMADA, sin estado en servidor.

QUÉ HAY DENTRO DE LA COOKIE, y por qué eso y no un identificador opaco:

    base64url(json) . base64url(hmac_sha256(json, secreto))

El payload lleva `{u, iat, exp, csrf}`. La alternativa clásica —un id aleatorio
contra una tabla de sesiones— compra una cosa real (poder matar UNA sesión desde
el servidor) a cambio de una tabla, una migración, un job de limpieza y una
dependencia de Supabase en el camino de CADA petición del panel. Para dos
usuarios no paga; y el poder que se pierde se recupera entero por otra vía que
además es instantánea: **rotar `DASHBOARD_SECRET` donde esté desplegado invalida TODAS las
sesiones vivas al reiniciar**. Ése es el botón de pánico ante una cookie robada,
y está escrito en el runbook del panel.

LO QUE ESTA FIRMA SÍ GARANTIZA: que el payload no lo ha escrito nadie más.
`hmac.compare_digest` para comparar (sin canal de tiempo), verificación ANTES de
mirar el contenido, y `exp` comprobado en el SERVIDOR — el `Max-Age` de la
cookie es una cortesía para el navegador, no un control: quien roba la cookie
puede reenviarla cuando quiera y el único plazo que manda es el firmado dentro.

LO QUE NO GARANTIZA, declarado: el payload va FIRMADO, no cifrado. Cualquiera
que tenga la cookie puede leer el nombre de usuario. No hay nada más ahí dentro
—ni la contraseña, ni el hash, ni un token de Supabase— y por eso basta con
firmar. Si algún día hubiera que meter un dato sensible en el payload, la
respuesta correcta no es cifrarlo: es no meterlo.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

NOMBRE_COOKIE = "panel_sesion"
VARIABLE_SECRETO = "DASHBOARD_SECRET"

#: Longitud mínima del secreto. 32 caracteres ≈ 192 bits si se genera como
#: manda el runbook (`secrets.token_urlsafe(32)`); por debajo, la firma se
#: vuelve forzable y con ella toda la autenticación.
SECRETO_MIN_CHARS = 32

#: Duración por defecto. 8 h = una jornada: entrar una vez al día y no tener que
#: volver a teclear la contraseña a media tarde. Es también la ventana máxima de
#: una cookie robada, así que no se alarga «por comodidad» sin decirlo.
DURACION_DEFECTO_S = 8 * 3600
VARIABLE_DURACION = "DASHBOARD_SESION_HORAS"

#: Techo de lo que se acepta leer de la cookie antes de mirarla. Una cookie
#: gigante es basura o un intento de agotar memoria; el payload real ronda los
#: 200 bytes.
COOKIE_MAX_CHARS = 4096


def secreto() -> bytes:
    """El secreto de firma. FALLA si no está: un panel que se inventa un secreto
    al arrancar parece funcionar y cierra la sesión de todo el mundo en cada
    redespliegue — y peor, invita a que alguien «arregle» eso poniendo uno fijo
    en el código."""
    crudo = os.getenv(VARIABLE_SECRETO, "").strip()
    if len(crudo) < SECRETO_MIN_CHARS:
        raise RuntimeError(
            f"{VARIABLE_SECRETO} ausente o demasiado corto "
            f"(mínimo {SECRETO_MIN_CHARS} caracteres). Genera uno con "
            f"`python -c \"import secrets;print(secrets.token_urlsafe(32))\"` "
            f"y ponlo en las variables del despliegue (hoy Vercel). Rotarlo cierra "
            f"todas las sesiones abiertas."
        )
    return crudo.encode("utf-8")


def duracion_s() -> int:
    """Duración de la sesión, en segundos. Un valor ilegible cae al defecto en
    vez de tumbar el panel: es comodidad, no un control de seguridad."""
    try:
        horas = float(os.getenv(VARIABLE_DURACION, "").strip() or 0)
    except ValueError:
        return DURACION_DEFECTO_S
    if not (0 < horas <= 24):
        return DURACION_DEFECTO_S
    return int(horas * 3600)


def _b64(crudo: bytes) -> str:
    return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")


def _desb64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(cuerpo: bytes, clave: bytes) -> bytes:
    return hmac.new(clave, cuerpo, hashlib.sha256).digest()


def nueva(usuario: str, *, ahora: float | None = None,
          duracion: int | None = None) -> dict:
    """El payload de una sesión recién abierta, con su token CSRF dentro.

    El CSRF vive EN la sesión y no en una tabla aparte: así nace, viaja y muere
    con ella, no hay que limpiarlo, y un token de una sesión no vale en otra —
    que es exactamente la propiedad que se le pide.
    """
    ahora = time.time() if ahora is None else ahora
    return {
        "u": usuario,
        "iat": int(ahora),
        "exp": int(ahora + (duracion if duracion is not None else duracion_s())),
        "csrf": secrets.token_urlsafe(24),
    }


def firmar(payload: dict, clave: bytes) -> str:
    cuerpo = json.dumps(
        payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True
    ).encode("utf-8")
    return f"{_b64(cuerpo)}.{_b64(_firma(cuerpo, clave))}"


def verificar(cookie: str | None, clave: bytes, *,
              ahora: float | None = None) -> dict | None:
    """La cookie → payload, o `None`. NUNCA lanza y nunca dice POR QUÉ falló:
    quien la manda no tiene que aprender si el problema era la firma o el plazo.

    El orden importa: primero la firma, después el contenido. Si se parseara
    antes de verificar, el JSON de un desconocido llegaría al parser."""
    if not cookie or len(cookie) > COOKIE_MAX_CHARS:
        return None
    cuerpo_b64, punto, firma_b64 = cookie.partition(".")
    if not punto:
        return None
    try:
        cuerpo, firma = _desb64(cuerpo_b64), _desb64(firma_b64)
    except Exception:                                            # noqa: BLE001
        return None
    if not hmac.compare_digest(_firma(cuerpo, clave), firma):
        return None
    try:
        payload = json.loads(cuerpo.decode("utf-8"))
    except Exception:                                            # noqa: BLE001
        return None
    if not isinstance(payload, dict):
        return None
    usuario, expira, csrf = payload.get("u"), payload.get("exp"), payload.get("csrf")
    if not isinstance(usuario, str) or not usuario:
        return None
    if not isinstance(csrf, str) or not csrf:
        return None
    if not isinstance(expira, (int, float)) or isinstance(expira, bool):
        return None
    if expira <= (time.time() if ahora is None else ahora):
        return None
    return payload


def csrf_valido(payload: dict, enviado: str | None) -> bool:
    """¿El formulario trae el token de ESTA sesión? Comparación en tiempo
    constante, aunque el token no sea un secreto de larga vida: no cuesta nada
    y evita tener que razonar si aquí importaba o no."""
    esperado = (payload or {}).get("csrf")
    if not isinstance(esperado, str) or not isinstance(enviado, str) or not enviado:
        return False
    return hmac.compare_digest(esperado, enviado)


# ----------------------------------------------------------------- la cabecera
#
# Los atributos de la cookie, cada uno con lo que corta:
#   HttpOnly  — el JavaScript de la página no puede leerla. En un panel sin nada
#               de JS es cinturón sobre tirantes, y así sigue si mañana lo hay.
#   Secure    — no viaja por HTTP en claro. Se pone SIEMPRE, también en local:
#               los navegadores tratan `http://localhost` como origen seguro y
#               la aceptan igual, así que no hace falta una variable para
#               apagarla — y una variable para apagar `Secure` es exactamente la
#               que alguien deja encendida en producción.
#   SameSite=Strict — el navegador no manda la cookie en NINGUNA petición que
#               venga de otro sitio. Es la primera línea contra el CSRF; el
#               token de formulario es la segunda, porque `SameSite` depende del
#               navegador y el control no puede vivir sólo en el cliente.
#   Path=/    — una sola aplicación, un solo ámbito.


def cabecera_cookie(valor: str, *, max_age: int) -> str:
    return (
        f"{NOMBRE_COOKIE}={valor}; Max-Age={max_age}; Path=/; "
        f"HttpOnly; Secure; SameSite=Strict"
    )


def cabecera_borrado() -> str:
    """El logout: se vacía y se caduca. La cookie desaparece del navegador; la
    firma de la anterior sigue siendo válida hasta su `exp` si alguien se la
    quedó — el remedio para eso es rotar el secreto, y está dicho arriba."""
    return (
        f"{NOMBRE_COOKIE}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Strict"
    )


def leer_cookie(cabecera: str | None) -> str | None:
    """Saca `panel_sesion` de una cabecera `Cookie:` cruda."""
    for trozo in (cabecera or "").split(";"):
        nombre, sep, valor = trozo.strip().partition("=")
        if sep and nombre == NOMBRE_COOKIE:
            return valor.strip()
    return None
