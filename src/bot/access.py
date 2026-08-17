# -*- coding: utf-8 -*-
"""s324e — CONTROL DE ACCESO al bot: allowlist por `telegram_user_id` +
invitación de UN SOLO USO. Esta es la hoja de DECISIÓN; el transporte y la
persistencia viven fuera.

POR QUÉ existe. Hoy no hay control de acceso: cualquiera que encuentre
`@PCI_Soporte_tecnico_bot` y envíe `/accept` entra. Con un usuario real (Alberto)
eso es una anécdota; con un piloto de Directores Generales deja de serlo por tres
motivos distintos, y conviene no mezclarlos:
  · **gasto** — cada consulta paga generación, embedding y rerank;
  · **confidencialidad** — el corpus son manuales de fabricantes y el bot los
    sirve citados;
  · **RGPD** — sin puerta, el bot registra la consulta de cualquiera que pase.

QUÉ ES ESTE MÓDULO — una hoja PURA, igual que `error_taxonomy`:
  · sin I/O, sin red, sin SDK; el estado de la base ENTRA como parámetro
    (`consultar`), así que se prueba entero sin tocar Supabase;
  · el único estado que guarda es la CACHÉ, y va **keyed por `telegram_user_id`**
    (misma disciplina que `logging_db._consent_cache`, auditada en
    `evals/s324e_aislamiento_usuarios_auditoria_v1.md` §P1: nada de estado de
    proceso compartido entre personas);
  · lee entorno solo para sus tres flags, registradas en `src/flags.py`.

TRI-ESTADO, y por qué no un `bool`. La consulta a la base devuelve
`AUTORIZADO` / `DESCONOCIDO` / `INDETERMINADO`. Un bool obligaría a colapsar «no
está en la lista» con «no he podido preguntarlo», que es justo la distinción de
la que depende el fail-closed con matiz: al primero se le enseña la puerta, al
segundo se le pide que reintente — y ninguno de los dos entra.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

# --------------------------------------------------------------- tri-estado

AUTORIZADO = "autorizado"
DESCONOCIDO = "desconocido"
INDETERMINADO = "indeterminado"      # la base no contesta, o la tabla no existe

#: Vocabulario CERRADO de lo que puede devolver `consultar`. Cualquier otra cosa
#: se trata como INDETERMINADO: un valor que no reconocemos JAMÁS puede abrir la
#: puerta (un typo en el llamante no debe convertirse en un permiso).
ESTADOS = (AUTORIZADO, DESCONOCIDO, INDETERMINADO)

# Resultado de un canje de invitación. Mismo reparto: el vocabulario se declara
# aquí y `logging_db.canjear_invitacion` devuelve estas mismas cadenas SIN
# importarlas (la matriz de imports prohíbe `raiz → bot`); un test los pina.
CANJE_OK = "ok"
CANJE_INVALIDA = "invalida"
CANJE_INDETERMINADO = "indeterminado"
CANJES = (CANJE_OK, CANJE_INVALIDA, CANJE_INDETERMINADO)


# ------------------------------------------------------------------ ventanas
#
# Los tres plazos de la caché, cada uno con el fallo que acota:
#
#   FRESCO   — cuánto vale un SÍ confirmado antes de re-preguntar. 600 s es el
#              mismo valor que `_CONSENT_CACHE_TTL_S`, y a propósito: fija el
#              techo de lo que tarda una REVOCACIÓN en surtir efecto sin
#              reiniciar el worker (≤10 min), que es la promesa que el runbook
#              de supresión ya da para el consentimiento. Dos plazos distintos
#              para dos revocaciones serían dos promesas que explicar.
#   NEGATIVO — cuánto vale un NO. Corto (60 s) porque el alta la puede hacer el
#              script desde OTRO proceso: con el plazo del sí, un DG recién dado
#              de alta se quedaría fuera 10 minutos sin que nada fallara. No se
#              cachea «para siempre» como los misses de consentimiento: aquí el
#              estado cambia desde fuera del bot.
#   GRACIA   — cuánto se sirve un sí YA CADUCADO cuando la base no contesta (el
#              matiz del fail-closed). **1 hora**, y este número ES la peor
#              latencia de una revocación, así que se elige contra eso: la
#              gracia existe para que un DG no se quede fuera por un BLIP de
#              Supabase, y un blip dura segundos o minutos, no un día. El 24 h
#              inicial acotaba el infinito pero regalaba 24 h de acceso a un
#              revocado durante una caída — con el agravante de que en una caída
#              de Supabase el bot casi no puede responder igualmente (el RAG lee
#              los chunks de ahí), o sea que la gracia larga no compraba
#              servicio, solo alargaba el agujero. Si Alberto prefiere más
#              tolerancia a costa de revocación, es esta constante.
TTL_FRESCO_S = 600.0
TTL_NEGATIVO_S = 60.0
GRACIA_DEGRADADA_S = 3600.0


# -------------------------------------------------------------------- flags


#: Valores que APAGAN la puerta. Todo lo demás la deja PUESTA — ver abajo.
VALORES_APAGADO = frozenset({"off", "0", "false", "no"})
#: Valores que la encienden explícitamente. La unión de ambos es el vocabulario
#: RECONOCIDO; cualquier cosa fuera es una errata y se trata como tal.
VALORES_ENCENDIDO = frozenset({"on", "1", "true", "yes", "si", "sí"})


def acceso_activo() -> bool:
    """Interruptor maestro de la puerta. Default OFF = conducta de HOY, exacta.

    Nace apagada (al revés que `BOT_ERROR_REPLY`) porque el orden de despliegue
    de este repo lo exige: `main` auto-despliega a Railway y las migraciones las
    aplica Alberto A MANO. Si la puerta naciera encendida, el commit que la trae
    cerraría el bot antes de que exista la tabla que dice quién puede entrar.
    Secuencia correcta: desplegar (inerte) → aplicar la 016 → verificar con el
    script → encender la variable en Railway. Y es también el kill-switch: si la
    puerta se atasca, `BOT_ALLOWLIST=off` devuelve el bot de hoy sin deploy.

    SOLO UN «OFF» RECONOCIBLE APAGA LA PUERTA (dúo, crítico 1). Antes esto era
    `valor in {"on","1","true","yes"}`, así que un `BOT_ALLOWLIST=onn` en Railway
    —una errata de una tecla— dejaba el piloto ABIERTO A INTERNET en silencio.
    Un control de acceso no puede degradar a fail-open por una errata: la lógica
    se invierte y lo NO RECONOCIDO cierra. La asimetría es deliberada — apagar un
    control debe costar escribirlo bien; encenderlo, no.

    El precio, declarado: una errata deja el bot cerrado para todos. Por eso hay
    DOS salidas, y ninguna exige tocar código: `BOT_ALLOWLIST_BOOTSTRAP` (que no
    pasa por base ni caché) y `validar_configuracion()`, que aborta el ARRANQUE
    con el valor mal escrito en el mensaje — así el fallo se ve en el deploy, no
    en un DG que no puede entrar.
    """
    return os.getenv("BOT_ALLOWLIST", "off").strip().lower() not in VALORES_APAGADO


def validar_configuracion() -> None:
    """Fail-fast de ARRANQUE de las tres flags de acceso. La llama `run_bot`.

    Patrón de la casa (`config._strict_on_off`: «no reconocido — fail-fast»), y
    aquí importa el doble: las tres variables se escriben a mano en Railway y
    las tres fallan en silencio hacia un lado malo si tienen una errata —
    `BOT_ALLOWLIST` cerrando el bot entero, `BOT_ALLOWLIST_BOOTSTRAP` dejando
    fuera a quien administra, `BOT_DAILY_LIMIT` volviendo al default sin avisar.
    Un deploy que no arranca con el motivo escrito es mejor que cualquiera de las
    tres: es ruidoso, es inmediato y Railway conserva el despliegue anterior.
    """
    crudo = os.getenv("BOT_ALLOWLIST", "off").strip().lower()
    if crudo not in (VALORES_APAGADO | VALORES_ENCENDIDO):
        raise RuntimeError(
            f"BOT_ALLOWLIST={crudo!r} no reconocido (on|off) — fail-fast. La "
            f"puerta queda CERRADA con cualquier valor que no sea un apagado "
            f"explícito ({'|'.join(sorted(VALORES_APAGADO))}); corrige la "
            f"variable en Railway."
        )

    bruto = os.getenv("BOT_ALLOWLIST_BOOTSTRAP", "")
    ilegibles = [t.strip() for t in bruto.replace(";", ",").split(",")
                 if t.strip() and not t.strip().lstrip("-").isdigit()]
    if ilegibles:
        raise RuntimeError(
            f"BOT_ALLOWLIST_BOOTSTRAP tiene entradas que no son ids de Telegram: "
            f"{ilegibles} — fail-fast. Se ignorarían en silencio y quien "
            f"administra se quedaría fuera justo cuando hiciera falta entrar."
        )

    # Mismo default que `limite_diario` a propósito: dos lectores del mismo flag
    # con defaults distintos son una DIVERGENCIA que el registro de s311 obliga a
    # declarar, y aquí no hay ninguna que declarar — sin la variable, el valor
    # válido es el propio default y la validación pasa sola.
    tope = os.getenv("BOT_DAILY_LIMIT", "30")
    try:
        int(tope.strip())
    except ValueError:
        raise RuntimeError(
            f"BOT_DAILY_LIMIT={tope!r} no es un entero — fail-fast (si no, se "
            f"caería al default 30 sin que nadie lo supiera)."
        ) from None


def ids_bootstrap() -> frozenset[int]:
    """Ids SIEMPRE autorizados, declarados en el entorno (`12345,67890`).

    Es la respuesta explícita a «Alberto ya usa el bot y no puede quedarse fuera
    al desplegar», y es deliberadamente una VARIABLE y no un `if user_id == …`
    en el código: el valor es visible en Railway, no exige deploy para cambiarlo,
    queda registrado en `src/flags.py` y no ata el producto a una persona.

    Además es el ÚNICO camino que no depende de la base: si la 016 no está
    aplicada, o Supabase está caído y la caché vacía (worker recién arrancado),
    estos ids entran igual. Sin eso, un fail-closed honesto se convierte en
    «nadie puede arreglar el bot desde el bot».

    Precio declarado: quien controle el entorno de Railway se puede dar acceso.
    Es el mismo nivel de confianza que ya tiene `TELEGRAM_BOT_TOKEN` — quien
    controla el entorno controla el bot entero — así que no añade superficie.
    """
    crudo = os.getenv("BOT_ALLOWLIST_BOOTSTRAP", "")
    return _parsear_ids(crudo)


def limite_diario() -> int:
    """Tope de mensajes por persona y día. `0` (o negativo) = sin tope.

    30 por defecto: la medición real de este bot son 96 consultas en 4 meses de
    un usuario, y un DG en piloto activo hará del orden de 5-20 en un día bueno.
    30 deja holgura para un día intenso y acota el gasto de una cuenta
    comprometida o de un bucle accidental a algo que se nota y no arruina.
    """
    try:
        return int(os.getenv("BOT_DAILY_LIMIT", "30").strip())
    except ValueError:
        # Un valor mal escrito en Railway no puede desactivar el tope EN
        # SILENCIO: se cae al default, que es el valor conservador.
        return 30


def _parsear_ids(crudo: str) -> frozenset[int]:
    """`"1, 2 ,x,3"` → `{1, 2, 3}`. Lo ilegible se ignora en vez de reventar: un
    espacio de más en una variable de Railway no puede tumbar el arranque."""
    salida = set()
    for trozo in (crudo or "").replace(";", ",").split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            valor = int(trozo)
        except ValueError:
            continue
        if valor > 0:
            salida.add(valor)
    return frozenset(salida)


# ------------------------------------------------------------------ mensajes
#
# Reglas de redacción (las mismas de `error_taxonomy`, más una): esto NO puede
# parecer un error. Es un piloto por invitación, así que el mensaje describe una
# situación normal y da la salida concreta. Sin disculpas, sin jerga y sin
# insinuar que la persona ha hecho algo mal.

MENSAJE_NO_AUTORIZADO = (
    "Este asistente está en piloto privado, solo por invitación.\n\n"
    "Si te han enviado un enlace de invitación, ábrelo desde este mismo "
    "Telegram y quedarás dado de alta. Si no lo tienes, escribe a "
    "info@fontiber.com."
)

MENSAJE_INDETERMINADO = (
    "No he podido comprobar tu acceso ahora mismo. Vuelve a intentarlo en unos "
    "minutos."
)

MENSAJE_INVITACION_NO_VALIDA = (
    "Esa invitación ya no es válida: puede haber caducado, haberse usado ya o "
    "haber sido anulada. Pide una nueva a quien te la envió."
)

MENSAJE_INVITACION_ACEPTADA = "✅ Invitación aceptada. Ya tienes acceso al piloto."

# El canje quedó EN EL AIRE: la petición pudo confirmarse en la base y perderse
# la respuesta. Antes se servía aquí `MENSAJE_INDETERMINADO` («vuelve a
# intentarlo»), y el dúo cazó que puede ser MENTIRA: si el canje sí se confirmó,
# el enlace ya está quemado y reintentar no funcionará nunca. Este texto es
# verdad en los dos casos — que es la única forma de no tener que adivinar cuál
# ocurrió — y va acompañado de una liberación best-effort en `logging_db`.
MENSAJE_CANJE_INCIERTO = (
    "No he podido confirmar tu alta ahora mismo. Vuelve a pulsar el enlace en "
    "unos minutos; si te dice que ya no es válido, pide uno nuevo a quien te lo "
    "envió."
)

# El piloto es 1:1. Ver `es_chat_privado`: esto es un CONTROL, no un consejo.
MENSAJE_SOLO_PRIVADO = (
    "Solo atiendo en conversación privada, de uno a uno. Escríbeme por privado "
    "y te ayudo."
)


# ------------------------------------------------------------ chat privado
#
# EL RED LINE DEL DUEÑO, CONVERTIDO EN CONTROL (dúo, crítico 2). «Cada DG tiene
# su sesión y son independientes; un usuario ve sólo aquello por lo que
# pregunta» (auditoría §P1). Eso se sostenía en una NOTA operativa — «el piloto
# va en chats privados 1:1»— y una nota no es un control: un DG autorizado podía
# meter el bot en un grupo y sus respuestas las leían participantes no
# invitados. La puerta autorizaba al REMITENTE y jamás miraba DÓNDE se iba a
# publicar la respuesta.
#
# Se prohíbe el grupo en vez de gobernarlo porque no hay caso de uso que lo pida
# (el piloto es 1:1 por diseño) y porque «gobernarlo» significaría autorizar
# CHATS además de personas — otra tabla, otra revocación y otro modo de fallo,
# para nadie. Segunda capa recomendada, que no es código: desactivar el modo
# grupo del bot en BotFather (`/setjoingroups → Disable`), y así el bot no puede
# ni ser añadido.

TIPOS_CHAT_PERMITIDOS = frozenset({"private"})

#: Chats de grupo a los que ya se les explicó la regla, para no repetirlo en
#: cada mensaje. Es estado de PROCESO pero va keyed por CHAT y no guarda nada de
#: nadie: solo «a este grupo ya se le dijo». Acotado por el nº de grupos.
_grupos_avisados: set[int] = set()


def es_chat_privado(tipo: object) -> bool:
    """¿`update.effective_chat.type` es un chat 1:1?

    Estricto a propósito: un tipo AUSENTE o desconocido NO es privado. Telegram
    puede añadir tipos nuevos, y la respuesta segura ante uno que no conocemos
    es la misma que ante un grupo.
    """
    return isinstance(tipo, str) and tipo.strip().lower() in TIPOS_CHAT_PERMITIDOS


def debe_avisar_del_grupo(chat_id: object) -> bool:
    """¿Toca explicar la regla en este grupo, o ya se hizo?

    Una vez por chat y proceso. Sin esto, un grupo activo recibiría el mismo
    aviso por cada mensaje que llegara al bot — ruido para ellos y envíos para
    nosotros. (El volumen ya es bajo por construcción: en grupos, el modo
    privacidad de Telegram viene activado y el bot solo recibe comandos y
    menciones. Esto cubre el caso en que alguien lo desactive.)
    """
    try:
        clave = int(chat_id)
    except (TypeError, ValueError):
        return False
    if clave in _grupos_avisados:
        return False
    if len(_grupos_avisados) >= CACHE_MAX_ENTRADAS:
        # Misma cota, política más simple: no hay nada que caduque aquí, así que
        # se vacía. El precio es repetir un aviso ya dado, que es inofensivo.
        _grupos_avisados.clear()
    _grupos_avisados.add(clave)
    return True


# --------------------------------------------------------- aviso de canje
#
# Un solo uso limita el daño a UNA persona, pero no garantiza QUÉ persona: quien
# reciba el enlace reenviado y lo pulse antes, entra. Lo que sí se puede hacer es
# que el reenvío sea DETECTABLE EN MINUTOS en vez de en la siguiente auditoría —
# y eso es este aviso: enfrenta para quién era la invitación con quién la ha
# canjeado de verdad.
#
# MÍNIMO NECESARIO (es dato de una persona viajando a otra): la nota, el nombre
# que Telegram ya expone al conversar, el alias público si lo hay, y el id que
# hace falta para revocar. Nada de esto se PERSISTE nuevo por el aviso: el id ya
# vive en `bot_invitaciones.canjeada_por` (inventariado en la matriz) y el nombre
# solo viaja en el mensaje. Declarado en `docs/RGPD_RETENCION.md`.


def texto_aviso_canje(*, nota: str | None, nombre: str | None,
                      alias: str | None, telegram_user_id: int) -> str:
    """El aviso que recibe quien administra cuando alguien canjea una invitación."""
    quien = (nombre or "").strip() or "(sin nombre en Telegram)"
    if alias:
        quien += f" (@{str(alias).lstrip('@')})"
    return (
        "🔑 Invitación canjeada\n\n"
        f"Era para: {(nota or '').strip() or '(sin nota)'}\n"
        f"La ha canjeado: {quien} · id {telegram_user_id}\n\n"
        "Si no es quien esperabas, el enlace se reenvió. Quítale el acceso con:\n"
        f"python -m scripts.s324e_invitaciones revocar-acceso {telegram_user_id}"
    )


def mensaje_limite(limite: int) -> str:
    """Qué lee quien agota su cupo. Dice las tres cosas que necesita saber: qué
    ha pasado, que no está roto, y cuándo vuelve a poder preguntar. NO promete
    una hora concreta — el contador va por día UTC y prometer «a las 00:00»
    sería falso para quien mira su reloj de Madrid."""
    return (
        f"Has llegado al límite de {limite} consultas al día que tiene este "
        "piloto. No es un fallo: es un tope para controlar el coste mientras "
        "estamos en beta. Mañana vuelves a tenerlas disponibles; si necesitas "
        "más, escribe a info@fontiber.com."
    )


# ---------------------------------------------------------------- veredicto


@dataclass(frozen=True)
class Veredicto:
    """Qué se hace con este update. Datos, no comportamiento.

    `origen` es telemetría honesta: dice de DÓNDE salió el permiso (de la base,
    de la caché fresca, de la caché degradada por caída, o del bootstrap). Sin
    él, un piloto servido enteramente desde caché degradada se vería igual que
    uno sano en los logs.
    """

    permitido: bool
    motivo: str
    origen: str
    mensaje: str = ""


_PERMITIDO_DB = Veredicto(True, "en_allowlist", "db")
_PERMITIDO_CACHE = Veredicto(True, "en_allowlist", "cache")
_PERMITIDO_DEGRADADO = Veredicto(True, "en_allowlist", "cache_degradada")
_PERMITIDO_BOOTSTRAP = Veredicto(True, "bootstrap", "bootstrap")
_DENEGADO_DB = Veredicto(False, "no_autorizado", "db", MENSAJE_NO_AUTORIZADO)
_DENEGADO_CACHE = Veredicto(False, "no_autorizado", "cache", MENSAJE_NO_AUTORIZADO)
_DENEGADO_INDETERMINADO = Veredicto(
    False, "indeterminado", "db", MENSAJE_INDETERMINADO
)
_DENEGADO_SIN_USUARIO = Veredicto(False, "sin_usuario", "puerta")


# -------------------------------------------------------------------- caché


@dataclass
class _Entrada:
    permitido: bool
    confirmado_en: float        # última vez que la BASE lo dijo (monotonic)
    expira_en: float            # hasta cuándo vale sin re-preguntar


#: Caché de proceso, keyed por `telegram_user_id`. Se vacía al reiniciar el
#: worker, que es la conducta correcta: un arranque limpio vuelve a preguntar.
_cache: dict[int, _Entrada] = {}

# COTA DE MEMORIA (2º revisor, menor 5). Las entradas caducan LÓGICAMENTE pero
# nadie las borraba: como la clave es un `telegram_user_id` ajeno y CADA
# desconocido deja su denegación cacheada, el diccionario crecía de forma
# monótona con quien quisiera escribir al bot. A escala del piloto es
# irrelevante —de ahí que el hallazgo sea menor y especulativo— pero es una
# estructura sin cota alimentada desde fuera, en el componente que precisamente
# atiende a los no autorizados, y eso se acota en vez de razonarse.
#
# Política, en este orden: primero se tira lo ya CADUCADO (que no cuesta nada
# porque no se estaba usando) y, si aún no basta, lo más antiguo. Precio
# declarado: tirar una entrada POSITIVA le cuesta a esa persona una consulta a
# la base — y, si justo entonces Supabase está caído, pierde la gracia
# degradada. Es el lado correcto del intercambio: bajo un flujo capaz de llenar
# 10.000 entradas, lo que hay que proteger es que el worker siga en pie.
CACHE_MAX_ENTRADAS = 10_000


def reiniciar_cache() -> None:
    """Vacía la caché. Para los tests y para un eventual comando de operación —
    NO se llama desde el camino servido."""
    _cache.clear()
    _uso.clear()
    _grupos_avisados.clear()


def _podar_cache(ahora: float) -> None:
    """Mantiene `_cache` bajo la cota. No hace nada hasta llegar a ella."""
    if len(_cache) < CACHE_MAX_ENTRADAS:
        return
    for user_id in [u for u, e in _cache.items() if e.expira_en <= ahora]:
        _cache.pop(user_id, None)
    if len(_cache) < CACHE_MAX_ENTRADAS:
        return
    # Nada caducado que tirar. Se sacrifica el decil por (NEGATIVOS primero,
    # luego los más antiguos). El orden importa y lo cazó su propio test: con
    # «solo el más antiguo» una riada de denegaciones FRESCAS desalojaba antes
    # que nada al DG legítimo —su confirmación es más vieja que la del último
    # intruso— que es exactamente al revés de lo que hay que proteger. Perder un
    # NO cuesta una consulta a la base; perder un SÍ le cuesta a esa persona la
    # gracia degradada si justo entonces Supabase está caído.
    sobra = max(1, len(_cache) // 10)
    for user_id, _entrada in sorted(
        _cache.items(), key=lambda par: (par[1].permitido, par[1].confirmado_en)
    )[:sobra]:
        _cache.pop(user_id, None)


def _podar_uso(dia: str) -> None:
    """Ídem para el contador diario: lo de otros días ya no sirve para nada."""
    if len(_uso) < CACHE_MAX_ENTRADAS:
        return
    for user_id in [u for u, (d, _n) in _uso.items() if d != dia]:
        _uso.pop(user_id, None)
    if len(_uso) >= CACHE_MAX_ENTRADAS:
        # Más de 10.000 personas distintas en un mismo día: no es el piloto. Se
        # descarta lo más viejo por orden de inserción (el orden del dict), y
        # esas personas recuperan cupo — un tope de gasto que se reinicia es
        # mejor que un worker que se queda sin memoria.
        for user_id in list(_uso)[: max(1, len(_uso) // 10)]:
            _uso.pop(user_id, None)


def recordar_alta(telegram_user_id: int, *, ahora: float | None = None) -> None:
    """Marca a esta persona como autorizada SIN preguntar a la base.

    Se llama justo después de un canje CONFIRMADO. Sin esto, el canje dejaría
    en la caché el NO de hace un segundo (el que se resolvió al comprobar la
    puerta antes de canjear) y el DG recién invitado rebotaría contra su propia
    invitación durante `TTL_NEGATIVO_S`. El estado ya está commiteado en la
    base: adelantarlo en la caché no inventa nada.
    """
    ahora = time.monotonic() if ahora is None else ahora
    _cache[int(telegram_user_id)] = _Entrada(
        permitido=True, confirmado_en=ahora, expira_en=ahora + TTL_FRESCO_S
    )


def olvidar(telegram_user_id: int) -> None:
    """Descacheado puntual de una persona (revocación en caliente)."""
    _cache.pop(int(telegram_user_id), None)


# ------------------------------------------------------------------ decisión


def decidir(
    telegram_user_id: int | None,
    consultar: Callable[[int], str],
    *,
    ahora: float | None = None,
    bootstrap: Iterable[int] | None = None,
) -> Veredicto:
    """¿Puede esta persona usar el bot? TOTAL: siempre devuelve un veredicto.

    `consultar(user_id) -> ESTADOS` es la única entrada de I/O y se invoca SOLO
    cuando la caché no alcanza. Si lanza, o devuelve algo que no está en
    `ESTADOS`, se trata como INDETERMINADO — es decir, nunca como un permiso.

    EL FAIL-CLOSED CON MATIZ, que es la decisión de diseño de esta función:
      · base OK y en la lista → entra, y se cachea el sí (`TTL_FRESCO_S`);
      · base OK y no está     → NO entra, y se cachea el no (`TTL_NEGATIVO_S`);
      · base CAÍDA y esta persona tenía un sí CONFIRMADO hace menos de
        `GRACIA_DEGRADADA_S` (1 h) → entra (degradado). **Este plazo es la peor
        latencia de una revocación**: con la base sana son ≤`TTL_FRESCO_S`
        (10 min), y con la base caída, hasta 1 h más;
      · base CAÍDA y no consta un sí previo → NO entra. **Nadie nuevo entra
        durante una caída**, que es la mitad del requisito que un simple
        «fail-open si la base falla» se salta.

    El matiz del matiz: en la rama degradada NO se refresca `confirmado_en`. Si
    se refrescara, cada mensaje renovaría la gracia y el tope de 24 h no llegaría
    nunca — la cota tiene que contarse desde la última confirmación REAL de la
    base, no desde el último uso.
    """
    ahora = time.monotonic() if ahora is None else ahora

    try:
        user_id = int(telegram_user_id or 0)
    except (TypeError, ValueError):
        user_id = 0
    if user_id <= 0:
        # Un update sin autor identificable (post de canal, servicio) no tiene a
        # quién autorizar. Se deniega en silencio: no hay a quién contestar.
        return _DENEGADO_SIN_USUARIO

    permitidos = frozenset(bootstrap) if bootstrap is not None else ids_bootstrap()
    if user_id in permitidos:
        # ANTES que la caché y que la base a propósito: es el camino que tiene
        # que funcionar precisamente cuando lo demás no funciona.
        return _PERMITIDO_BOOTSTRAP

    entrada = _cache.get(user_id)
    if entrada is not None and entrada.expira_en > ahora:
        return _PERMITIDO_CACHE if entrada.permitido else _DENEGADO_CACHE

    try:
        estado = consultar(user_id)
    except Exception:                                        # noqa: BLE001
        estado = INDETERMINADO
    if estado not in ESTADOS:
        estado = INDETERMINADO

    if estado in (AUTORIZADO, DESCONOCIDO):
        _podar_cache(ahora)          # la cota, ANTES de crecer
    if estado == AUTORIZADO:
        _cache[user_id] = _Entrada(True, ahora, ahora + TTL_FRESCO_S)
        return _PERMITIDO_DB
    if estado == DESCONOCIDO:
        _cache[user_id] = _Entrada(False, ahora, ahora + TTL_NEGATIVO_S)
        return _DENEGADO_DB

    if (
        entrada is not None
        and entrada.permitido
        and (ahora - entrada.confirmado_en) <= GRACIA_DEGRADADA_S
    ):
        return _PERMITIDO_DEGRADADO
    return _DENEGADO_INDETERMINADO


# ------------------------------------------------------------- tope diario
#
# En MEMORIA, y declarado: un redeploy de Railway reinicia los contadores. Es
# una barrera de GASTO en un piloto, no una cuota contractual, y la alternativa
# (contar `query_logs` en cada mensaje) añadiría un roundtrip al camino caliente
# y seguiría sin contar los turnos que no se registran (saludos, cortesía). Se
# prefiere una barrera barata y honesta a una exacta y cara.

#: user_id -> (día UTC, consumido). Un valor por persona: al cambiar el día se
#: sobrescribe, así que no crece con el tiempo, solo con el nº de usuarios.
_uso: dict[int, tuple[str, int]] = {}


def dia_utc(momento: datetime | None = None) -> str:
    """`'2026-08-17'`. UTC y no hora local a propósito: el bot no sabe en qué
    huso está cada DG, y un contador que depende del cliente no es un contador.
    Por eso el mensaje del tope dice «mañana» y no una hora."""
    momento = momento or datetime.now(timezone.utc)
    return momento.astimezone(timezone.utc).date().isoformat()


def consumir_cuota(
    telegram_user_id: int,
    *,
    limite: int | None = None,
    dia: str | None = None,
) -> Veredicto:
    """Cuenta UN mensaje de esta persona y dice si todavía cabe.

    `limite <= 0` desactiva el tope (kill-switch por variable, sin deploy).
    El mensaje que agota el cupo es el ÚLTIMO que se atiende: con límite 30, la
    consulta 30 se responde y la 31 se rechaza.
    """
    limite = limite_diario() if limite is None else limite
    if limite <= 0:
        return Veredicto(True, "sin_tope", "cuota")

    dia = dia or dia_utc()
    user_id = int(telegram_user_id)
    _podar_uso(dia)
    dia_previo, consumido = _uso.get(user_id, (dia, 0))
    if dia_previo != dia:
        consumido = 0                      # día nuevo: el contador se sustituye

    if consumido >= limite:
        # No se sigue incrementando: el contador solo tiene que saber «ya no
        # cabe», y un número que crece sin techo es memoria por nada.
        _uso[user_id] = (dia, consumido)
        return Veredicto(False, "tope_diario", "cuota", mensaje_limite(limite))

    _uso[user_id] = (dia, consumido + 1)
    return Veredicto(True, "dentro_de_cuota", "cuota")


def consumo_actual(telegram_user_id: int, *, dia: str | None = None) -> int:
    """Lo consumido hoy por esa persona (para tests y diagnóstico)."""
    dia = dia or dia_utc()
    dia_previo, consumido = _uso.get(int(telegram_user_id), (dia, 0))
    return consumido if dia_previo == dia else 0


# --------------------------------------------------------------- invitación
#
# EL TOKEN. Tres propiedades, y de dónde sale cada una:
#
#   no adivinable — `secrets.token_urlsafe(24)` = 192 bits de un CSPRNG. No
#     `random`, que es un Mersenne Twister reproducible: con unas cuantas
#     salidas se predice el resto, y aquí «la siguiente salida» es una llave.
#   cabe en el enlace — Telegram acota el payload de `?start=` a 64 caracteres
#     del alfabeto `A-Za-z0-9_-`. 24 bytes → 32 caracteres exactos de ese
#     alfabeto, sin relleno: la mitad del techo, con margen para prefijar algo
#     el día que haga falta.
#   no reutilizable desde la base — en Supabase se guarda el SHA-256, nunca el
#     token. Quien lea la tabla (una copia de seguridad, la consola, una clave
#     filtrada) NO obtiene invitaciones utilizables. El precio, declarado: el
#     enlace se enseña UNA vez al crearlo; si se pierde, se anula y se emite
#     otro. Es el precio correcto.
#
# Por qué SHA-256 y no bcrypt/argon2: los KDF lentos existen para secretos de
# ENTROPÍA BAJA (contraseñas que una persona elige). Contra 192 bits aleatorios
# no aportan nada — no hay diccionario que recorrer — y sí añaden dependencia y
# latencia al canje. La comparación la hace el índice UNIQUE de la base sobre el
# hash, no una comparación en Python, así que tampoco hay canal de tiempo que
# proteger.

LONGITUD_TOKEN_BYTES = 24
LONGITUD_PAYLOAD_MAX = 64                  # el techo de Telegram para `?start=`

# CADUCIDAD. El default baja de 7 días a 2 (Alberto): acorta la ventana en la
# que un enlace olvidado en un chat sigue vivo, que es el vector que más le
# preocupa. Y hay un MÁXIMO real (dúo, menor 7): antes se decía «se acota a 7
# días» y era falso — `--dias` aceptaba cualquier entero y el esquema solo
# exigía `expira_at NOT NULL`, así que un `--dias 3650` pasaba. Ahora la cota la
# imponen los DOS lados: esta constante en el emisor y un CHECK en la 016, que
# es el que de verdad la garantiza (el script no es el único cliente posible).
DIAS_CADUCIDAD_DEFECTO = 2
DIAS_CADUCIDAD_MAX = 7
_ALFABETO_PAYLOAD = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)


def token_nuevo() -> str:
    """Un token de invitación. Se enseña una vez y no se guarda en claro."""
    return secrets.token_urlsafe(LONGITUD_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Lo que SÍ se guarda. Definido aquí —y no en el script ni en el bot— para
    que el emisor y el que canjea no puedan divergir jamás."""
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def es_payload_plausible(payload: object) -> bool:
    """¿Merece la pena preguntarle a la base por esto?

    Filtro barato ANTES del roundtrip: cualquiera puede escribir `/start loquesea`
    y sin esto cada basura costaría una consulta a Supabase. Comprueba forma, no
    validez — la validez la decide el canje atómico, que es el único sitio donde
    se puede decidir.
    """
    if not isinstance(payload, str):
        return False
    payload = payload.strip()
    # 20 caracteres: por debajo no puede ser un `token_urlsafe(24)` (32) ni nada
    # que hayamos emitido nosotros.
    if not (20 <= len(payload) <= LONGITUD_PAYLOAD_MAX):
        return False
    return all(caracter in _ALFABETO_PAYLOAD for caracter in payload)


def enlace_invitacion(bot_username: str, token: str) -> str:
    """`https://t.me/<bot>?start=<token>` — la forma que Telegram convierte en
    `context.args` del handler de `/start`."""
    return f"https://t.me/{str(bot_username).lstrip('@')}?start={token}"
