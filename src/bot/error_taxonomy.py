# -*- coding: utf-8 -*-
"""s324e — TAXONOMÍA de errores del bot: clasificar una excepción por CAUSA y
decidir, con ese dato, qué se le dice al técnico, si tiene sentido reintentar y
qué severidad tiene para quien opera el piloto.

POR QUÉ existe (el fallo que cierra). Hoy el bot tiene 24 `except Exception`
dispersos y CERO `add_error_handler`: fuera de dos puntos (`accept_command` y
`_process_query`) una excepción no manejada acaba en SILENCIO — el técnico
escribe, no pasa nada, y no queda ni rastro para saber por qué. Y donde SÍ hay
mensaje, es uno solo para todo: un timeout de red transitorio (reintentar
funciona) y un `KeyError` nuestro (reintentar NO funciona nunca) se le cuentan
al técnico con la misma frase. Un mensaje que no distingue eso no es honesto:
le hace perder el tiempo o le hace creer que el bot está roto cuando no lo está.

QUÉ ES ESTE MÓDULO — una hoja PURA:
  · sin I/O, sin red, sin lectura de entorno, sin estado de proceso;
  · no importa NINGÚN SDK (ni telegram, ni anthropic, ni openai, ni httpx);
  · todas sus funciones son deterministas y testeables con dobles triviales.
El transporte (responder al técnico) y la persistencia (registrar la incidencia)
viven fuera, en `telegram_bot.py` y `logging_db.py`. Aquí solo se DECIDE.

CLASIFICACIÓN NOMINAL, y por qué NO `isinstance`. Se clasifica por el nombre
CUALIFICADO de las clases del MRO de la excepción (`anthropic.RateLimitError`,
`telegram.error.RetryAfter`, …) en vez de por `isinstance` contra las clases
reales. Motivo: `isinstance` obligaría a importar los tres SDK en una hoja que
carga en el arranque del worker — y un SDK que reestructure sus excepciones
tumbaría el proceso ENTERO en el import, es decir, el mecanismo que existe para
que nada quede en silencio sería justo lo que apaga el bot. Con nombres, el peor
caso es una excepción que cae al residual `BUG` (ruidosa y visible), nunca un
arranque roto.
El agujero conocido de lo nominal — que un SDK renombre una clase y dejemos de
reconocerla — se cierra con un test que construye excepciones REALES de httpx,
telegram y anthropic y comprueba que esta tabla las clasifica: si un `pip
install -U` mueve un nombre, la suite se pone roja, no producción.

RESIDUAL HONESTO. Lo que no encaja en ninguna causa conocida es `BUG` — nuestro
defecto — a propósito. La tentación era mapear `KeyError`/`TypeError` a «datos
ausentes»: eso convierte nuestros propios fallos en «al manual le faltaba algo»
y hace desaparecer de las métricas justo la clase que hay que arreglar.
`DATOS_AUSENTES` solo se alcanza cuando alguien lo SEÑALA explícitamente
(`raise DatosAusentes(...)`), nunca por inferencia.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

# --------------------------------------------------------------------- clases

RED_DATOS = "red_datos"
LLM_SATURADO = "llm_saturado"
LLM_FALLO = "llm_fallo"
TRANSPORTE_TELEGRAM = "transporte_telegram"
DATOS_AUSENTES = "datos_ausentes"
BUG = "bug"

#: Vocabulario CERRADO. Es el mismo CHECK que la tabla `bot_errors` (migración
#: 015) impone en la base: una clase nueva se añade en los DOS sitios o la fila
#: se rechaza — el vocabulario no puede derivar en silencio.
CLASES = (RED_DATOS, LLM_SATURADO, LLM_FALLO, TRANSPORTE_TELEGRAM,
          DATOS_AUSENTES, BUG)

#: `aviso`   — transitorio y esperable en producción; no exige acción.
#: `grave`   — hay que mirarlo: o es defecto nuestro o degrada el servicio.
#: `critico` — sistémico: afecta a TODOS los técnicos (credencial, token, doble
#:             poller). Es la señal de «esto no se arregla solo».
SEVERIDADES = ("aviso", "grave", "critico")


class DatosAusentes(Exception):
    """Señal EXPLÍCITA de «el dato que hacía falta no está» (no un defecto).

    Alcance declarado: hoy NINGÚN sitio del producto la lanza (0 call sites).
    Está aquí como la costura nominal para cuando el pipeline sepa distinguir
    «no hay manual/registro para esto» de «me he roto», y para que ese día no
    haya que inventar una heurística. Deducirla de un `KeyError` sería peor que
    no tenerla: disfrazaría defectos nuestros de huecos de corpus.
    """


@dataclass(frozen=True)
class Decision:
    """Qué se hace con un fallo de esta clase. Datos, no comportamiento."""

    clase: str
    severidad: str
    reintentable: bool          # ¿repetir la MISMA acción puede funcionar?
    mensaje: str                # lo que lee el técnico (español, sobrio)
    con_codigo: bool            # ¿se le da un código de incidencia que citar?
    entregable: bool = True     # ¿podemos siquiera hablarle? (bot bloqueado: no)


@dataclass(frozen=True)
class Incidencia:
    """Lo que se persiste de un fallo. Sin secretos y sin traza completa."""

    codigo: str
    clase: str
    severidad: str
    reintentable: bool
    tipo_excepcion: str
    etapa: str
    origen: str | None
    mensaje_corto: str


# ------------------------------------------------------------------- mensajes
# Reglas de redacción (piloto con Directores Generales, bot declarado beta):
#   · en español y sobrio — ni disculpa efusiva ni jerga de stacktrace;
#   · JAMÁS culpar al técnico: el fallo es del sistema aunque la pregunta fuese
#     rara (y si de verdad hace falta que acote, se le pide sin reproche);
#   · decir lo que ha pasado en términos que él pueda USAR: si reintentar sirve,
#     se dice; si no sirve, NO se le manda reintentar (es la mentira cómoda de
#     hoy: «inténtalo de nuevo» ante un bug determinista falla siempre igual);
#   · nunca prometer que «ya está arreglado» ni dar hora de vuelta.

_MENSAJES: dict[str, Decision] = {
    RED_DATOS: Decision(
        clase=RED_DATOS,
        severidad="aviso",
        reintentable=True,
        mensaje=(
            "No he podido consultar la base de manuales ahora mismo (fallo de "
            "conexión). Vuelve a enviarme la pregunta en unos segundos."
        ),
        con_codigo=False,
    ),
    # «servicio de IA» y no «el que redacta las respuestas»: por esta clase pasan
    # tanto la generación (Anthropic) como la transcripción de audio (Whisper), y
    # nombrar la generación ante un fallo de transcripción sería decirle al
    # técnico algo que no es verdad.
    LLM_SATURADO: Decision(
        clase=LLM_SATURADO,
        severidad="aviso",
        reintentable=True,
        mensaje=(
            "El servicio de IA del que dependo está saturado en este momento. "
            "Espera unos segundos y repite la pregunta."
        ),
        con_codigo=False,
    ),
    LLM_FALLO: Decision(
        clase=LLM_FALLO,
        severidad="grave",
        reintentable=False,
        mensaje=(
            "Ha fallado el servicio de IA del que dependo, así que no he podido "
            "completar la respuesta. El aviso queda registrado. Si te corre "
            "prisa, avisa a soporte con este código:"
        ),
        con_codigo=True,
    ),
    TRANSPORTE_TELEGRAM: Decision(
        clase=TRANSPORTE_TELEGRAM,
        severidad="grave",
        reintentable=False,
        mensaje=(
            "Tenía la respuesta preparada pero no he conseguido enviártela por "
            "Telegram. Queda registrado; si repites la pregunta más concreta "
            "suele salir. Código de la incidencia:"
        ),
        con_codigo=True,
    ),
    DATOS_AUSENTES: Decision(
        clase=DATOS_AUSENTES,
        severidad="aviso",
        reintentable=False,
        mensaje=(
            "No tengo ese dato en los manuales que llevo cargados, así que "
            "prefiero no responder antes que inventarlo. Queda anotado como "
            "hueco de documentación."
        ),
        con_codigo=False,
    ),
    BUG: Decision(
        clase=BUG,
        severidad="grave",
        reintentable=False,
        mensaje=(
            "Me he encontrado con un fallo interno al procesar esto. No es cosa "
            "de tu pregunta: es un defecto mío y repetirla daría igual. Ya está "
            "registrado para corregirlo. Código de la incidencia:"
        ),
        con_codigo=True,
    ),
}

# Variantes de una clase que NO comparten decisión con el resto de la clase.
# Se mantienen como Decision COMPLETAS (no como parches sobre `_MENSAJES`) para
# que leer la tabla baste para saber qué ve el técnico.
_BOT_BLOQUEADO = Decision(
    clase=TRANSPORTE_TELEGRAM,
    severidad="aviso",
    reintentable=False,
    # No se entrega: el técnico bloqueó al bot o borró el chat. Se conserva el
    # texto por si un día hay otro canal, pero `entregable=False` impide el
    # intento — reintentar un envío a quien nos bloqueó solo genera más errores.
    mensaje="",
    con_codigo=False,
    entregable=False,
)
_CRITICO_TRANSPORTE = Decision(
    clase=TRANSPORTE_TELEGRAM,
    severidad="critico",
    reintentable=False,
    mensaje=(
        "Hay un problema de configuración del canal de Telegram que me impide "
        "atenderte con garantías. Ya está registrado como incidencia crítica. "
        "Código:"
    ),
    con_codigo=True,
)
# El proveedor no contesta (5xx, conexión, timeout): reintentar SÍ puede
# funcionar. Es constante de módulo y no un `Decision(...)` en línea dentro de
# `clasificar` para que el test que recorre TODAS las decisiones la alcance
# (r37: una decisión que solo existe dentro de una función se queda fuera de
# los invariantes sin que nadie lo note).
_LLM_NO_RESPONDE = Decision(
    clase=LLM_FALLO,
    severidad="grave",
    reintentable=True,
    mensaje=(
        "El servicio de IA del que dependo no está respondiendo. Vuelve a "
        "intentarlo en un minuto."
    ),
    con_codigo=False,
)
_CRITICO_LLM = Decision(
    clase=LLM_FALLO,
    severidad="critico",
    reintentable=False,
    mensaje=(
        "No puedo atenderte ahora mismo: el servicio de IA del que dependo me "
        "rechaza las credenciales. Esto afecta a todo el mundo, no solo a ti, y "
        "está registrado como incidencia crítica. Código:"
    ),
    con_codigo=True,
)


# ---------------------------------------------------------- tablas nominales
# Nombre CUALIFICADO (`modulo_raiz.NombreClase`) → decisión. El módulo raíz se
# normaliza: `httpx._exceptions.ReadTimeout` se consulta como `httpx.ReadTimeout`
# (los SDK exponen la clase en el paquete y la definen en un privado).

_PROVEEDORES_LLM = frozenset({"anthropic", "openai", "voyageai"})

# telegram.error.* — el transporte. `TimedOut`/`NetworkError` son de red PERO se
# clasifican como transporte a propósito: el técnico no distingue «no llegó tu
# mensaje» de «no llegó mi respuesta», y la acción útil es la misma.
_TELEGRAM: dict[str, Decision] = {
    "RetryAfter": Decision(
        clase=TRANSPORTE_TELEGRAM, severidad="aviso", reintentable=True,
        mensaje=(
            "Telegram me está limitando el ritmo de envío. Espera unos segundos "
            "y repite la pregunta."
        ),
        con_codigo=False,
    ),
    "TimedOut": Decision(
        clase=TRANSPORTE_TELEGRAM, severidad="aviso", reintentable=True,
        mensaje=(
            "Se me ha agotado el tiempo hablando con Telegram. Vuelve a "
            "enviarme la pregunta en unos segundos."
        ),
        con_codigo=False,
    ),
    "NetworkError": Decision(
        clase=TRANSPORTE_TELEGRAM, severidad="aviso", reintentable=True,
        mensaje=(
            "He tenido un problema de red con Telegram. Vuelve a enviarme la "
            "pregunta en unos segundos."
        ),
        con_codigo=False,
    ),
    "BadRequest": _MENSAJES[TRANSPORTE_TELEGRAM],
    "Forbidden": _BOT_BLOQUEADO,
    "ChatMigrated": _BOT_BLOQUEADO,
    "InvalidToken": _CRITICO_TRANSPORTE,
    "Conflict": _CRITICO_TRANSPORTE,
}

# httpx.* — nuestra red hacia Supabase (todo `src/` habla REST por httpx).
_HTTPX = {
    "TimeoutException", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
    "PoolTimeout", "TransportError", "ConnectError", "ReadError", "WriteError",
    "RemoteProtocolError", "ProxyError", "NetworkError", "CloseError",
    "LocalProtocolError", "UnsupportedProtocol",
}

# Excepciones de los SDK de LLM, por nombre de clase (anthropic y openai las
# comparten; voyageai reusa nombres análogos).
_LLM_SATURADO_NOMBRES = {
    "RateLimitError", "OverloadedError", "APIOverloadedError",
    # voyageai.error.* — nombres PROPIOS que no coinciden con anthropic/openai
    # (dúo r37): Voyage se llama por SDK en serving (`rag/reranker.py`), así que
    # estas clases sí llegan aquí.
    "ServiceUnavailableError",
}
_LLM_CRITICO_NOMBRES = {
    "AuthenticationError", "PermissionDeniedError",
}
_LLM_REINTENTABLE_NOMBRES = {
    "APIConnectionError", "APITimeoutError", "InternalServerError",
    "APIStatusError", "APIResponseValidationError", "ConnectionError",
    "ServerError",                                   # voyageai.error
}


def _nombres_mro(exc: BaseException) -> list[str]:
    """`['anthropic.RateLimitError', 'anthropic.APIStatusError', …]`, de la clase
    concreta hacia arriba. El módulo se reduce a su raíz para que
    `httpx._exceptions.ReadTimeout` y `httpx.ReadTimeout` sean lo mismo."""
    salida: list[str] = []
    for cls in type(exc).__mro__:
        if cls in (object, BaseException, Exception):
            continue
        raiz = (getattr(cls, "__module__", "") or "").split(".")[0]
        salida.append(f"{raiz}.{cls.__name__}" if raiz else cls.__name__)
    return salida


def _codigo_http(exc: BaseException) -> int | None:
    """Código HTTP de la excepción, si lo lleva. Se prueban las DOS formas que
    usan los SDK: `.status_code` (anthropic/openai) y `.response.status_code`
    (httpx.HTTPStatusError). Cualquier fallo al leerlo devuelve None: un
    accessor que explota jamás puede tumbar la clasificación."""
    for lectura in (
        lambda: getattr(exc, "status_code", None),
        lambda: getattr(getattr(exc, "response", None), "status_code", None),
    ):
        try:
            valor = lectura()
        except Exception:                                    # noqa: BLE001
            continue
        if isinstance(valor, int):
            return valor
    return None


def clasificar(exc: BaseException | None) -> Decision:
    """Excepción → decisión. TOTAL: siempre devuelve una decisión, nunca lanza.

    Orden de precedencia (de lo más específico a lo más general):
      1. la señal explícita nuestra (`DatosAusentes`);
      2. Telegram (el transporte, con sus variantes crítica y no-entregable);
      3. los SDK de LLM — saturación ≠ credencial ≠ fallo real;
      4. httpx (red hacia Supabase);
      5. residual: BUG.
    """
    if exc is None:
        # Un handler invocado sin excepción es en sí mismo un defecto nuestro:
        # se clasifica como tal en vez de devolver un «no pasa nada».
        return _MENSAJES[BUG]

    nombres = _nombres_mro(exc)

    for nombre in nombres:
        if nombre.endswith(".DatosAusentes") or nombre == "DatosAusentes":
            return _MENSAJES[DATOS_AUSENTES]

    for nombre in nombres:
        raiz, _, corto = nombre.partition(".")
        if raiz == "telegram":
            decision = _TELEGRAM.get(corto)
            if decision is not None:
                return decision
            if corto == "TelegramError":            # base: cualquier otra suya
                return _MENSAJES[TRANSPORTE_TELEGRAM]

    for nombre in nombres:
        raiz, _, corto = nombre.partition(".")
        if raiz not in _PROVEEDORES_LLM:
            continue
        codigo = _codigo_http(exc)
        # 429 (límite) y 529 (sobrecargado de Anthropic) mandan sobre el nombre:
        # los SDK envuelven ambos en `APIStatusError` según versión.
        if codigo in (429, 529) or corto in _LLM_SATURADO_NOMBRES:
            return _MENSAJES[LLM_SATURADO]
        if corto in _LLM_CRITICO_NOMBRES or codigo in (401, 403):
            return _CRITICO_LLM
        # Un 4xx CONOCIDO manda sobre el NOMBRE (dúo r37). Es determinista:
        # repetir la misma petición vuelve a fallar igual. Sin esta línea, un
        # `APIStatusError` BASE con 400/402 —que el SDK lanza cuando no tiene
        # subclase para ese código— caía en la rama reintentable por su nombre
        # y al técnico se le decía «vuelve a intentarlo» ante algo que no va a
        # funcionar nunca. (Las subclases con nombre propio —BadRequestError,
        # NotFoundError…— ya caían bien; el agujero era solo la base.)
        if codigo is not None and 400 <= codigo < 500:
            return _MENSAJES[LLM_FALLO]
        if corto in _LLM_REINTENTABLE_NOMBRES or (codigo or 0) >= 500:
            return _LLM_NO_RESPONDE
        return _MENSAJES[LLM_FALLO]

    for nombre in nombres:
        raiz, _, corto = nombre.partition(".")
        if raiz != "httpx":
            continue
        if corto == "HTTPStatusError":
            codigo = _codigo_http(exc)
            # 4xx contra Supabase = petición MAL FORMADA por nosotros. Llamarlo
            # «fallo de red» ocultaría un defecto nuestro tras un transitorio.
            if codigo is not None and 400 <= codigo < 500:
                return _MENSAJES[BUG]
            return _MENSAJES[RED_DATOS]
        if corto in _HTTPX or corto == "HTTPError":
            return _MENSAJES[RED_DATOS]

    return _MENSAJES[BUG]


# ------------------------------------------------------------------ redacción

_RE_URL = re.compile(r"https?://\S+", re.I)
# Token de bot de Telegram: `123456789:AA...`. Se nombra aparte del patrón
# genérico para que quede EXPLÍCITO qué secreto concreto se está tapando (es el
# riesgo que s286 citó para prohibir `str(exc)` en las filas de error).
_RE_TOKEN_TELEGRAM = re.compile(r"\b\d{6,12}:[A-Za-z0-9_\-]{20,}")
_RE_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{20,}\b")
_RE_DIGITOS = re.compile(r"\b\d{7,}\b")
_RE_ESPACIOS = re.compile(r"\s+")

#: Techo del mensaje persistido. Corto a propósito: el valor de diagnóstico está
#: en las primeras palabras («column X does not exist», «Connection reset») y
#: cada carácter de más es superficie para que se cuele texto del técnico.
MAX_MENSAJE = 200


def redactar(texto: object, *,
             prohibido: str | Iterable[str] | None = None,
             max_chars: int = MAX_MENSAJE) -> str:
    """Deja un mensaje de excepción apto para guardar: sin secretos, sin URLs,
    sin identificadores largos y acotado.

    `prohibido` es el texto del técnico: si el mensaje lo lleva dentro (una
    `ValueError` que hace eco de su entrada), se descarta el mensaje ENTERO en
    vez de intentar recortarlo. Es la única defensa fiable — un texto libre no
    se puede sanear a trozos.

    Acepta VARIOS textos (dúo r37): en la ruta de voz conviven la transcripción
    CRUDA y la consulta normalizada, y una excepción puede hacer eco de
    cualquiera de las dos. Comprobar solo una dejaba la otra sin defensa.
    """
    try:
        crudo = str(texto or "")
    except Exception:                                        # noqa: BLE001
        return "(mensaje ilegible)"
    if not crudo:
        return ""

    limpio = _RE_URL.sub("[url]", crudo)
    limpio = _RE_TOKEN_TELEGRAM.sub("[token]", limpio)
    limpio = _RE_TOKEN.sub("[token]", limpio)
    limpio = _RE_DIGITOS.sub("[num]", limpio)
    limpio = _RE_ESPACIOS.sub(" ", limpio).strip()

    agujas = (prohibido,) if isinstance(prohibido, str) else (prohibido or ())
    for candidato in agujas:
        if not isinstance(candidato, str):
            continue
        aguja = _RE_ESPACIOS.sub(" ", candidato).strip().lower()
        # 12 caracteres: por debajo, la coincidencia sería casual (un modelo de
        # equipo o una palabra técnica que aparece en ambos textos).
        if len(aguja) >= 12 and aguja[:12] in limpio.lower():
            return "(omitido: el mensaje reproducía la consulta)"

    return limpio[:max_chars]


# --------------------------------------------------------------------- origen

#: Carpetas del repo que cuentan como «código nuestro» al buscar el origen.
_NUESTRO = ("src", "scripts", "harness")


def origen(exc: BaseException | None) -> str | None:
    """`'src/rag/generator.py:939'` — el frame MÁS PROFUNDO de código nuestro.

    Se descarta el resto del stack a propósito: los frames de librería son ruido
    para agrupar («¿qué módulo NUESTRO falla más?») y la ruta absoluta del
    proceso incluye el directorio de usuario, que es dato personal. Se devuelve
    la ruta RELATIVA desde `src/`, nunca la absoluta.
    """
    if exc is None:
        return None
    try:
        tb = exc.__traceback__
        encontrado = None
        while tb is not None:
            nombre = (tb.tb_frame.f_code.co_filename or "").replace("\\", "/")
            partes = nombre.split("/")
            for ancla in _NUESTRO:
                if ancla in partes:
                    indice = len(partes) - 1 - partes[::-1].index(ancla)
                    encontrado = f"{'/'.join(partes[indice:])}:{tb.tb_lineno}"
                    break
            tb = tb.tb_next
        return encontrado
    except Exception:                                        # noqa: BLE001
        return None


# ------------------------------------------------------------------ incidencia


def nuevo_codigo() -> str:
    """Código corto que el técnico puede citar y que une su mensaje con la fila.

    8 hex = 4.300 millones: a la escala del piloto la colisión es irrelevante, y
    un código que quepa en un mensaje de chat vale más que uno irrepetible."""
    return uuid.uuid4().hex[:8]


def describir(exc: BaseException | None, *, etapa: str,
              decision: Decision | None = None,
              codigo: str | None = None,
              consulta: str | Iterable[str] | None = None) -> Incidencia:
    """Excepción → la fila que se persiste. Pura y total (no lanza nunca).

    `consulta` NO se guarda aquí: se pasa solo para poder DESCARTAR el mensaje
    de la excepción si lo reproduce (ver `redactar`). La consulta vive en
    `query_logs`, que sí está gobernada por la matriz de retención. Admite
    varios textos — en voz, la transcripción cruda Y la consulta normalizada.
    """
    decision = decision if decision is not None else clasificar(exc)
    try:
        tipo = type(exc).__name__ if exc is not None else "SinExcepcion"
    except Exception:                                        # noqa: BLE001
        tipo = "Desconocida"
    return Incidencia(
        codigo=codigo or nuevo_codigo(),
        clase=decision.clase,
        severidad=decision.severidad,
        reintentable=decision.reintentable,
        tipo_excepcion=tipo[:80],
        etapa=(etapa or "desconocida")[:60],
        origen=origen(exc),
        mensaje_corto=redactar(exc, prohibido=consulta),
    )


def texto_para_usuario(decision: Decision, codigo: str,
                       sufijo: str | None = None) -> str:
    """El mensaje final, con su código si la clase lo lleva. Sin `parse_mode`:
    se envía como texto plano a propósito — un mensaje de error que Telegram
    rechaza por un metacarácter volvería a dejar al técnico en silencio, que es
    exactamente el fallo que este módulo existe para cerrar.

    `sufijo` lo aporta la ETAPA, no la clase: una alternativa concreta que solo
    tiene sentido allí (en la ruta de voz, «escríbeme la pregunta»). Va aparte
    para que la tabla de clases no tenga que conocer cada llamante.
    """
    if not decision.entregable:
        return ""
    partes = [decision.mensaje]
    if decision.con_codigo:
        partes.append(codigo)
    if sufijo:
        partes.append(sufijo.strip())
    return " ".join(p for p in partes if p)
