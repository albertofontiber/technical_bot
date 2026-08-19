# -*- coding: utf-8 -*-
"""Gestión de acceso desde el panel — la parte de GESTIÓN que escribe.

QUÉ ESCRIBE, exhaustivo: una fila nueva en `bot_invitaciones` (emitir), y dos
`UPDATE` que ponen marca de tiempo y firma (anular una invitación, revocar un
acceso). Nada más. No toca corpus, ni catálogo, ni golds, ni `query_logs`, ni
`user_consent` — DEC-231 §4. La invariante de auditoría, AMPLIADA en s324j
(v9 §3.2): las peticiones no-GET del panel viven en DOS ficheros enumerables —
las tres de gestión AQUÍ, y en `cerrojo.py` la RPC de `admitir` y el DELETE de
`acierto` del cerrojo distribuido. Ningún otro módulo escribe.

QUÉ NO IMPLEMENTA: el CANJE. Cuando el invitado pulsa el enlace, quien lo canjea
es el bot (`logging_db.canjear_invitacion`, un solo `UPDATE` condicional que
gana exactamente uno de dos pulsadores simultáneos). El panel emite y anula; no
tiene ninguna razón para poder dar por canjeada una invitación, así que no
puede.

LA REGLA DEL TOKEN, heredada tal cual de `src.bot.access` y NO reescrita aquí:
se genera con un CSPRNG, en la base se guarda su SHA-256, y el enlace se enseña
UNA vez. El panel no puede volver a mostrarlo porque nadie puede: lo que hay
guardado es una huella. Si se pierde, se anula y se emite otro.
  Consecuencia de interfaz que hay que cuidar: el enlace aparece en la
respuesta del POST que lo crea y en ninguna otra — NO hay redirección (nunca
hubo un POST-redirect-GET aquí, y la prosa que lo afirmaba era falsa — s324j,
ronda F-m1): `app.accion_invitar` RENDERIZA la respuesta a propósito, porque
tras un 303 no habría de dónde reconstruir un token que no se guarda. El precio
(el F5 reenvía el formulario) lo paga la idempotencia por `op`, no un PRG.

LA FIRMA DE CADA ACCIÓN. `alta_por` / `revocado_por` / `revocada_por` se
rellenan con `panel:<usuario>`, no con el nombre a secas: al mirar la tabla
dentro de seis meses hay que poder distinguir lo que hizo alguien desde el CLI
de lo que hizo alguien desde la web. Es la mitad barata de la auditoría.
(s324j: la anulación firma en `revocada_por` — columna de la migración 020 —
y NO en la nota: la firma-en-nota de r41 mezclaba auditoría con texto humano y
además estaba ROTA contra Supabase real, porque la 016 nunca concedió
`UPDATE (nota)`; hallazgo S-C1 del dúo, DEC-239.)
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from src.bot import access
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

from . import datos

TIMEOUT_S = 15.0


@dataclass(frozen=True)
class Accion:
    """El resultado de una escritura, listo para pintar.

    `tono` es del vocabulario cerrado de `render.aviso`. `enlace` sólo viene
    relleno al emitir una invitación, y sólo esa vez.
    """

    ok: bool
    mensaje: str
    tono: str = "bien"
    enlace: str | None = None
    detalle: str = ""


def _cabeceras(extra: dict | None = None) -> dict:
    base = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    base.update(extra or {})
    return base


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


#: Estado de escritura PROPIO de este módulo (s324j, v9 §4.2, ronda F3-M1): una
#: violación de unicidad (código PostgreSQL `23505`) no es «Supabase respondió
#: 409» — es «esta operación YA se hizo», y el único camino que lo consume (la
#: emisión con `op`) tiene que poder decirlo. Para el resto de escrituras un
#: duplicado sigue siendo el error que es.
DUPLICADO = "duplicado"
_CODIGO_UNICIDAD = "23505"


def _escribir(metodo: str, tabla: str, *, params: dict | None = None,
              json: dict | None = None) -> tuple[str, list[dict], str]:
    """(estado, filas, detalle). Mismo vocabulario de estados que `datos.leer`
    —más `DUPLICADO`, solo de escritura— y la misma promesa: no lanza. Una
    escritura que falla tiene que producir un mensaje en pantalla, nunca un 500
    con traza."""
    if not datos.hay_credenciales():
        return datos.SIN_CREDENCIALES, [], "el panel no tiene credenciales"
    try:
        with httpx.Client(timeout=TIMEOUT_S) as cliente:
            resp = cliente.request(
                metodo, f"{SUPABASE_URL}/rest/v1/{tabla}",
                headers=_cabeceras(), params=params, json=json,
            )
    except httpx.HTTPError as exc:
        return datos.ERROR, [], f"no se pudo hablar con Supabase ({type(exc).__name__})"
    if resp.status_code in (400, 404, 409):
        try:
            codigo = str((resp.json() or {}).get("code") or "")
        except Exception:                                        # noqa: BLE001
            codigo = ""
        if codigo == _CODIGO_UNICIDAD:
            return DUPLICADO, [], tabla
        if codigo in datos._CODIGOS_AUSENTE or resp.status_code == 404:
            return datos.TABLA_AUSENTE, [], tabla
    if resp.status_code >= 400:
        return datos.ERROR, [], f"Supabase respondió {resp.status_code}"
    if resp.status_code == 204 or not resp.content:
        return datos.OK, [], ""
    try:
        cuerpo = resp.json()
    except Exception:                                            # noqa: BLE001
        return datos.ERROR, [], "respuesta ilegible"
    return datos.OK, (cuerpo if isinstance(cuerpo, list) else [cuerpo]), ""


# --------------------------------------------------------------------- listas
#
# Los `select` son EXPLÍCITOS y no `*`: al revés que en las vistas de métricas.
# El motivo es la minimización — estas dos tablas son las únicas del panel con
# identificadores directos de personas, así que se nombra columna por columna lo
# que se trae, y una columna nueva en la tabla no aparece sola en una pantalla.
# `token_hash` no está en ninguna de las dos listas: el panel no lo necesita
# para nada y lo que no se trae no se puede filtrar por accidente.

_SELECT_ALLOWLIST = ("telegram_user_id,nota,origen,alta_por,alta_at,"
                     "revocado_at,revocado_por,motivo_revocacion")
_SELECT_INVITACIONES = ("id,nota,creada_por,creada_at,expira_at,canjeada_at,"
                        "canjeada_por,revocada_at")


def listar_allowlist() -> datos.Resultado:
    return datos.leer("bot_allowlist",
                      {"select": _SELECT_ALLOWLIST, "order": "alta_at.desc",
                       "limit": "500"})


def listar_invitaciones() -> datos.Resultado:
    return datos.leer("bot_invitaciones",
                      {"select": _SELECT_INVITACIONES, "order": "creada_at.desc",
                       "limit": "500"})


def resumen_acceso(allowlist: datos.Resultado,
                   invitaciones: datos.Resultado) -> dict:
    """Las cuatro cifras de cabecera. Puras: reciben lo ya leído."""
    ahora = _ahora()
    activos = sum(1 for f in allowlist.filas if not f.get("revocado_at"))
    estados = [access.estado_invitacion(f, ahora) for f in invitaciones.filas]
    return {
        "con_acceso": activos,
        "revocados": len(allowlist.filas) - activos,
        "pendientes": estados.count(access.ESTADO_PENDIENTE),
        "usadas": estados.count(access.ESTADO_USADA),
    }


# ------------------------------------------------------------------ escrituras


def _nombre_del_bot() -> str | None:
    return (os.getenv("TELEGRAM_BOT_USERNAME") or "").lstrip("@") or None


#: La forma admisible del token de operación `op` (v9 §4.2): lo genera el panel
#: con `secrets.token_urlsafe(16)` al pintar el formulario, así que cualquier
#: otra cosa es un formulario manipulado — y el CHECK de la 020 lo rechazaría
#: en la base con un error críptico; mejor cortarlo aquí con un mensaje claro.
_OP_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def generar_invitacion(*, nota: str, dias: int, por: str, op: str) -> Accion:
    """Emite una invitación de un solo uso y devuelve el enlace UNA vez.

    `op` identifica LA OPERACIÓN (el formulario pintado), no su contenido: el
    F5 reenvía el mismo `op` y el UNIQUE de la base lo convierte en `DUPLICADO`
    — no se crea una segunda credencial y no se finge poder re-enseñar el
    enlace (v9 §4.2)."""
    nota = (nota or "").strip()
    if not nota:
        # Obligatoria por el mismo motivo que en el CLI: sin «para quién es», el
        # listado no se puede auditar y una revocación se convierte en adivinar.
        return Accion(False, "Escribe para quién es la invitación (nombre y "
                             "cargo): sin eso el listado no se puede auditar.",
                      tono="error")
    if len(nota) > 200:
        return Accion(False, "La nota es demasiado larga (máximo 200 "
                             "caracteres).", tono="error")
    try:
        dias = int(dias)
    except (TypeError, ValueError):
        return Accion(False, "La caducidad tiene que ser un número de días.",
                      tono="error")
    if not 1 <= dias <= access.DIAS_CADUCIDAD_MAX:
        return Accion(
            False,
            f"La caducidad va de 1 a {access.DIAS_CADUCIDAD_MAX} días "
            f"(pediste {dias}). Un enlace de vida larga es justo el que se "
            f"queda olvidado en un chat.",
            tono="error",
        )
    if not _OP_RE.fullmatch(op or ""):
        return Accion(False, "El formulario llegó incompleto. Recarga la "
                             "página y vuelve a intentarlo.", tono="error")

    token = access.token_nuevo()
    estado, filas, detalle = _escribir(
        "POST", "bot_invitaciones",
        json={
            "token_hash": access.hash_token(token),
            "nota": nota,
            "creada_por": f"panel:{por}",
            "expira_at": _iso(_ahora() + timedelta(days=dias)),
            "op": op,
        },
    )
    if estado == DUPLICADO:
        # El mismo `op` ya insertó: es el F5 del formulario que acaba de
        # emitir. No se crea nada y no se miente sobre el enlace, que solo se
        # enseñó al crearla — nadie puede volver a verlo (es una huella).
        return Accion(
            False,
            "Ya emitiste esta invitación: está en la lista de abajo. El "
            "enlace solo se enseñó al crearla; si lo perdiste, anúlala y "
            "emite otra.",
            tono="aviso",
        )
    if estado != datos.OK or not filas:
        return Accion(False, _texto_de_fallo(estado, detalle,
                                             "emitir la invitación"),
                      tono="error", detalle=detalle)

    bot = _nombre_del_bot()
    enlace = (access.enlace_invitacion(bot, token) if bot
              else f"https://t.me/<NOMBRE_DEL_BOT>?start={token}")
    aviso = "" if bot else (
        " OJO: falta `TELEGRAM_BOT_USERNAME` en el entorno del panel, así que "
        "hay que sustituir <NOMBRE_DEL_BOT> a mano."
    )
    return Accion(
        True,
        f"Invitación emitida para «{nota}». Caduca en {dias} día(s). "
        f"Este enlace NO se puede volver a ver: cópialo ahora." + aviso,
        enlace=enlace,
    )


def revocar_invitacion(*, invitacion_id: str, por: str) -> Accion:
    try:
        identificador = str(uuid.UUID(str(invitacion_id).strip()))
    except (ValueError, AttributeError):
        return Accion(False, "Ese identificador de invitación no es válido.",
                      tono="error")

    estado, filas, detalle = _escribir(
        "GET", "bot_invitaciones",
        params={"id": f"eq.{identificador}", "select": _SELECT_INVITACIONES},
    )
    if estado != datos.OK:
        return Accion(False, _texto_de_fallo(estado, detalle,
                                             "leer la invitación"),
                      tono="error", detalle=detalle)
    if not filas:
        return Accion(False, "Esa invitación ya no existe.", tono="error")
    fila = filas[0]
    if fila.get("canjeada_at"):
        # El mismo aviso que da el CLI, y por el mismo motivo: anular una
        # invitación YA canjeada no le quita el acceso a nadie, y creer que sí
        # es la forma de dejar dentro a quien creías haber echado.
        return Accion(
            False,
            "Esa invitación YA se canjeó: anularla no quita el acceso. Para "
            "quitarlo, revoca el acceso de esa persona en la tabla de arriba.",
            tono="error",
        )
    if fila.get("revocada_at"):
        return Accion(False, "Esa invitación ya estaba anulada.", tono="aviso")

    estado, filas, detalle = _escribir(
        "PATCH", "bot_invitaciones",
        params={"id": f"eq.{identificador}", "revocada_at": "is.null",
                "canjeada_at": "is.null"},
        # La anulación se FIRMA en `revocada_por` (migración 020) — la columna
        # que r41 no tenía y suplió firmando en la nota. Aquello mezclaba
        # auditoría con texto humano Y estaba roto contra Supabase real: la 016
        # nunca concedió `UPDATE (nota)` y el PATCH entero moría con 42501
        # (hallazgo S-C1 del dúo, s324j/DEC-239). El CHECK
        # `bot_invitaciones_revocacion_completa` exige fecha y firma JUNTAS.
        json={"revocada_at": _iso(_ahora()),
              "revocada_por": f"panel:{por}"},
    )
    if estado != datos.OK:
        return Accion(False, _texto_de_fallo(estado, detalle,
                                             "anular la invitación"),
                      tono="error", detalle=detalle)
    if not filas:
        # La condición del PATCH la ganó otro: alguien la canjeó entre la
        # lectura y la escritura. No se dice «anulada» sin haberlo hecho.
        return Accion(False, "No se ha anulado: alguien la canjeó o la anuló "
                             "mientras mirabas. Recarga la página.",
                      tono="error")
    return Accion(True, f"Invitación anulada: {fila.get('nota') or '(sin nota)'}.")


def revocar_acceso(*, telegram_user_id: str, por: str, motivo: str) -> Accion:
    try:
        identificador = int(str(telegram_user_id).strip())
    except (TypeError, ValueError):
        return Accion(False, "Ese identificador de Telegram no es un número.",
                      tono="error")

    estado, filas, detalle = _escribir(
        "PATCH", "bot_allowlist",
        params={"telegram_user_id": f"eq.{identificador}",
                "revocado_at": "is.null"},
        json={"revocado_at": _iso(_ahora()),
              "revocado_por": f"panel:{por}",
              "motivo_revocacion": (motivo or "").strip()[:200] or None},
    )
    if estado != datos.OK:
        return Accion(False, _texto_de_fallo(estado, detalle, "revocar el acceso"),
                      tono="error", detalle=detalle)
    if not filas:
        return Accion(False, "Esa persona no tenía acceso activo (no está en la "
                             "lista, o ya estaba revocada).", tono="aviso")

    partes = [
        f"Acceso revocado: {filas[0].get('nota') or '(sin nota)'}.",
        # La latencia REAL con sus dos casos, igual que la imprime el CLI. Los
        # dos plazos NO se suman: la gracia se cuenta desde la última
        # confirmación de la base. Cifras derivadas del diseño de `access`.
        f"Deja de entrar en hasta {int(access.TTL_FRESCO_S / 60)} min con "
        f"Supabase sano, y hasta {int(access.GRACIA_DEGRADADA_S / 60)} min si "
        f"Supabase está caído. Para cortar YA: reinicia el bot en Railway.",
    ]
    if identificador in access.ids_bootstrap():
        # El agujero que la revocación NO cubre, dicho en voz alta.
        partes.append(
            f"OJO: {identificador} está en BOT_ALLOWLIST_BOOTSTRAP, así que la "
            f"puerta lo deja pasar SIN mirar la base y esta revocación no le "
            f"afecta. Hay que quitarlo de esa variable en Railway."
        )
    return Accion(True, " ".join(partes))


def invitaciones_pendientes_tras_revocar(
    invitaciones: datos.Resultado,
) -> list[dict]:
    """Las invitaciones que siguen vivas. Se enseñan tras revocar un acceso
    porque una invitación pendiente emitida para esa misma persona le devuelve
    la entrada en cuanto la pulse — y NO se pueden cruzar automáticamente: una
    invitación sin canjear no tiene `telegram_user_id`. Lo decide una persona
    mirando las notas, que es justo para lo que existe la nota."""
    ahora = _ahora()
    return [f for f in invitaciones.filas
            if access.estado_invitacion(f, ahora) == access.ESTADO_PENDIENTE]


def _texto_de_fallo(estado: str, detalle: str, intento: str) -> str:
    """Un fallo de escritura, en castellano y con la acción concreta detrás."""
    if estado == datos.SIN_CREDENCIALES:
        return (f"No se pudo {intento}: el panel no tiene credenciales de "
                f"Supabase (SUPABASE_URL / SUPABASE_SERVICE_KEY).")
    if estado == datos.TABLA_AUSENTE:
        return (f"No se pudo {intento}: falta aplicar "
                f"migrations/016_allowlist_invitaciones.sql en Supabase.")
    return f"No se pudo {intento}: {detalle or 'fallo al hablar con Supabase'}."
