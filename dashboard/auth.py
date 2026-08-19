# -*- coding: utf-8 -*-
"""Autenticación del panel — la pieza ENCHUFABLE de DEC-231 §3.

EL CONTRATO, y es todo el contrato:

    autenticar(usuario, contraseña) -> Usuario | None

Nada más arriba en la pila sabe CÓMO se comprueba una identidad. Hoy la
comprueba `BackendEntorno` (contraseña con hash fuerte en una variable de
el proveedor de despliegue); el día que sepamos qué es técnicamente el login del war room —el
pendiente que DEC-231 deja en manos de Alberto— se escribe otro backend, se
llama a `usar_backend()` y no se toca ni una ruta ni una plantilla. Por eso la
interfaz devuelve `Usuario | None` y no un booleano: un backend corporativo
traerá al menos un nombre para mostrar y firmar las acciones, y `bool` obligaría
a cambiar la firma el primer día.

POR QUÉ `scrypt` DE LA BIBLIOTECA ESTÁNDAR Y NO argon2/bcrypt. El encargo los
nombra como ejemplo («p. ej.»), y los tres valen: son KDF lentos y con sal. La
diferencia es el COSTE DE TENERLOS. `hashlib.scrypt` es memory-hard (RFC 7914),
está en la stdlib de Python desde 3.6, y no añade **ninguna** dependencia nueva
a un repo cuyo CI instala `requirements.txt` en limpio para reproducir Railway.
argon2-cffi y bcrypt son ruedas compiladas: superficie de supply-chain y un
fallo de build más en el despliegue, a cambio de nada medible para dos usuarios.
Con `n=2**15, r=8, p=1` cada verificación cuesta 32 MiB de memoria y del orden
de 100 ms — el mismo orden que un bcrypt con coste 12.
  Precio declarado: si algún día hay que migrar a argon2, hay que re-emitir los
hashes. Barato, porque el formato lleva el algoritmo escrito delante y
`verificar` puede aprender a leer los dos.

EL FORMATO DEL REGISTRO (estilo PHC, un solo campo de texto):

    scrypt$n=32768,r=8,p=1$<sal_b64>$<hash_b64>

Los parámetros viajan DENTRO del registro, no en el código. Dos consecuencias
que valen el par de líneas que cuesta parsearlos: subir el coste mañana no
invalida los hashes de hoy (cada uno se verifica con los suyos), y los tests
pueden usar parámetros baratos sin tocar los de producción.

LO QUE NUNCA PASA: la contraseña en claro no se escribe en el repo, ni en un
fichero, ni en un log. `scripts/s324f_dashboard_password.py` la pide por
`getpass`, imprime el registro y no guarda nada.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from typing import Protocol

# ------------------------------------------------------------------ parámetros
#
# Cotas de lo que `verificar` acepta leer de un registro. No son gusto: un
# registro viene de una variable de entorno que escribe una persona, y
# `n=1073741824` en esa variable no es una contraseña más segura — es una
# petición de 4 TiB de memoria que tumba el panel en el primer intento de login.
# Se acota lo que se acepta LEER, no sólo lo que se genera.
N_DEFECTO = 2 ** 15
R_DEFECTO = 8
P_DEFECTO = 1

N_MIN, N_MAX = 2 ** 10, 2 ** 20
R_MAX, P_MAX = 32, 16
#: Techo de memoria por verificación (128·r·n). 256 MiB deja pasar cualquier
#: parámetro razonable y corta el registro hostil.
MEMORIA_MAX_BYTES = 256 * 1024 * 1024

ALGORITMO = "scrypt"
LONGITUD_SAL_BYTES = 16
LONGITUD_CLAVE_BYTES = 32


class RegistroInvalido(ValueError):
    """El texto no es un registro de contraseña legible (formato o cotas)."""


class IdentidadNoDisponible(RuntimeError):
    """El backend NO pudo comprobar la identidad — y eso no es «credencial mala».

    La lanza SOLO el transporte (Supabase caído, tabla ausente, credenciales
    del panel sin configurar, cualquier respuesta HTTP >= 400 de la lectura de
    usuarios), nunca una contraseña equivocada. Aplanar los dos casos en `None`
    haría que un usuario legítimo viera «Usuario o contraseña incorrectos»
    durante una caída — una mentira (s324j, v9 §1.3). La capa de rutas la
    convierte en un 503 uniforme, igual para todo el mundo: no hay señal
    por-usuario que un atacante pueda leer. `BackendEntorno` no la lanza nunca.
    """


# ---------------------------------------------------------------------- base64
# Sin relleno a propósito: el registro viaja dentro de una variable de entorno
# junto a otros campos, y un `=` suelto invita a que alguien lo confunda con un
# separador. `_desb64` lo repone antes de decodificar.


def _b64(crudo: bytes) -> str:
    return base64.b64encode(crudo).decode("ascii").rstrip("=")


def _desb64(texto: str) -> bytes:
    relleno = "=" * (-len(texto) % 4)
    return base64.b64decode(texto + relleno)


# ------------------------------------------------------------------- el hash


def _derivar(contrasena: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    # `maxmem` explícito: el default de OpenSSL son 32 MiB justos y `n=2**15,
    # r=8` pide exactamente eso — sin el margen, la configuración por defecto de
    # este módulo falla con «memory limit exceeded». Cazado ejecutándolo.
    maxmem = 128 * r * (n + p + 2) + (1 << 20)
    return hashlib.scrypt(
        contrasena.encode("utf-8"),
        salt=sal,
        n=n,
        r=r,
        p=p,
        maxmem=maxmem,
        dklen=LONGITUD_CLAVE_BYTES,
    )


def hash_contrasena(contrasena: str, *, n: int = N_DEFECTO, r: int = R_DEFECTO,
                    p: int = P_DEFECTO, sal: bytes | None = None) -> str:
    """Un registro nuevo. La sal es aleatoria de un CSPRNG y va en el registro."""
    _validar_parametros(n, r, p)
    sal = secrets.token_bytes(LONGITUD_SAL_BYTES) if sal is None else sal
    clave = _derivar(contrasena, sal, n, r, p)
    return f"{ALGORITMO}$n={n},r={r},p={p}${_b64(sal)}${_b64(clave)}"


def _validar_parametros(n: int, r: int, p: int) -> None:
    if not (N_MIN <= n <= N_MAX) or n & (n - 1):
        raise RegistroInvalido(
            f"n={n} fuera de rango o no es potencia de 2 "
            f"(entre {N_MIN} y {N_MAX})"
        )
    if not (1 <= r <= R_MAX) or not (1 <= p <= P_MAX):
        raise RegistroInvalido(f"r={r}/p={p} fuera de rango")
    if 128 * r * n > MEMORIA_MAX_BYTES:
        raise RegistroInvalido(
            f"el registro pide {128 * r * n // (1024 * 1024)} MiB por "
            f"verificación (techo: {MEMORIA_MAX_BYTES // (1024 * 1024)} MiB)"
        )


def _partir(registro: str) -> tuple[int, int, int, bytes, bytes]:
    partes = (registro or "").strip().split("$")
    if len(partes) != 4 or partes[0] != ALGORITMO:
        raise RegistroInvalido("formato: scrypt$n=..,r=..,p=..$sal$hash")
    try:
        params = dict(
            trozo.split("=", 1) for trozo in partes[1].split(",") if trozo
        )
        n, r, p = int(params["n"]), int(params["r"]), int(params["p"])
    except (KeyError, ValueError):
        raise RegistroInvalido("parámetros ilegibles") from None
    _validar_parametros(n, r, p)
    try:
        sal, clave = _desb64(partes[2]), _desb64(partes[3])
    except Exception:                                            # noqa: BLE001
        raise RegistroInvalido("sal o hash no son base64") from None
    if not sal or not clave:
        raise RegistroInvalido("sal o hash vacíos")
    return n, r, p, sal, clave


def verificar(contrasena: str, registro: str) -> bool:
    """¿Esta contraseña produce ese registro? Nunca lanza: un registro corrupto
    en las variables del despliegue tiene que ser un «no» rotundo, no un 500 que revele su forma."""
    try:
        n, r, p, sal, esperado = _partir(registro)
    except RegistroInvalido:
        return False
    try:
        obtenido = _derivar(contrasena, sal, n, r, p)
    except (ValueError, MemoryError):                            # noqa: BLE001
        return False
    return hmac.compare_digest(obtenido, esperado)


def validar_registro_estricto(registro: str) -> None:
    """Lanza `RegistroInvalido` si el registro no es EXACTAMENTE lo que
    `hash_contrasena` emite. Es la puerta del script de alta de usuarios del
    panel (s324j, v9 §1.1 — rondas S3-M3/S4-M2): `_partir` tolera una sal o un
    hash de UN byte, y `verificar` deriva siempre `LONGITUD_CLAVE_BYTES` — un
    registro así es legible y NO PUEDE verificar jamás: un usuario inalcanzable
    que ningún login rescata. Aquí se exige la forma canónica completa: sal de
    16, clave de 32, y solo los parámetros `n,r,p` (sin extras que `_partir`
    ignoraría en silencio).

    Lo que esto garantiza es que el registro es ESTRUCTURALMENTE verificable —
    no que case con una contraseña concreta (un hash aleatorio de 32 bytes pasa
    la forma): ese par lo comprueba el challenge del script, que re-pide la
    contraseña y corre `verificar` antes de emitir el INSERT."""
    n, r, p, sal, clave = _partir(registro)                      # cotas incluidas
    params = dict(
        trozo.split("=", 1)
        for trozo in registro.split("$")[1].split(",") if trozo
    )
    if set(params) != {"n", "r", "p"}:
        raise RegistroInvalido(
            f"parámetros extra o ausentes: {sorted(params)} (canónico: n,r,p)"
        )
    if len(sal) != LONGITUD_SAL_BYTES:
        raise RegistroInvalido(
            f"sal de {len(sal)} bytes (canónica: {LONGITUD_SAL_BYTES})"
        )
    if len(clave) != LONGITUD_CLAVE_BYTES:
        raise RegistroInvalido(
            f"hash de {len(clave)} bytes (canónico: {LONGITUD_CLAVE_BYTES}) — "
            f"un hash de otra longitud es LEGIBLE pero jamás verificará"
        )


# ------------------------------------------------------------------- usuario


@dataclass(frozen=True)
class Usuario:
    """Quién ha entrado. Lo MÍNIMO que el panel necesita: un nombre para
    enseñar arriba a la derecha y para firmar las altas y las revocaciones
    («quién dio de alta a quién» es la mitad del requisito de auditoría), y el
    `sello` de su credencial, que viaja en la cookie como `h` y hace efectivas
    la revocación y el cambio de contraseña en la SIGUIENTE petición (s324j,
    v9 §2). Sin correo, sin rol y sin perfil: v1 no distingue permisos — quien
    entra, administra.

    `sello` NO tiene default a propósito (v9, ronda S4-M4): un default `""`
    dejaría construir dobles que compilan y luego expulsan al usuario en la
    segunda petición — una rotura conductual escondida detrás de una de
    construcción. Sin default, el constructor que falte se rompe EN EL TEST."""

    nombre: str
    sello: str


class Backend(Protocol):
    """La interfaz que sustituirá el login del war room.

    Dos métodos y una excepción: `autenticar` comprueba una credencial (y
    devuelve el usuario CON su sello); `sello` revalida en cada petición que el
    usuario sigue activo y con la misma credencial (`None` = fuera). Cualquier
    imposibilidad de COMPROBAR — no de acertar — se señala lanzando
    `IdentidadNoDisponible`, nunca devolviendo `None`."""

    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None:
        ...

    def sello(self, nombre: str) -> str | None:
        ...


# ------------------------------------------------- backend v1: por entorno

VARIABLE_USUARIOS = "DASHBOARD_USUARIOS"

#: Registro SEÑUELO. Cuando el usuario no existe se verifica contra éste en vez
#: de devolver `None` de inmediato: si no, el tiempo de respuesta distinguiría
#: «ese usuario no existe» (microsegundos) de «existe y la contraseña falla»
#: (~100 ms de scrypt), y eso es un oráculo de enumeración de cuentas servido
#: gratis. Se genera al importar, con una contraseña aleatoria que nadie conoce.
_SENUELO = hash_contrasena(secrets.token_urlsafe(16), n=N_DEFECTO)


def _normalizar_usuario(nombre: str) -> str:
    return (nombre or "").strip().lower()


#: El charset de un nombre de usuario del panel — EL MISMO que impone el CHECK
#: de `panel_usuarios` en la 019 (la puerta 6-bis los ata con una tabla de
#: casos compartida). Existe por dos motivos que no son estética: un nombre que
#: la tabla no puede contener no debe ni consultarse, y los caracteres que la
#: sintaxis de filtros de PostgREST trata como estructura (`,`, `(`, `)`…) no
#: pueden llegar a un `usuario=eq.X` construido con entrada del formulario
#: (s324j, v9 §5).
USUARIO_RE = re.compile(r"^[a-z0-9._@-]{1,64}$")


def usuario_admisible(nombre: str) -> bool:
    """¿Este nombre (YA normalizado) puede existir en `panel_usuarios`?"""
    return bool(USUARIO_RE.fullmatch(nombre))


def _b64url_sin_relleno(crudo: bytes) -> str:
    return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")


def sello_de_registro(registro: str) -> str:
    """El sello de una credencial: cambia exactamente cuando cambia el registro.

    `b64url_sin_relleno(sha256(registro)[:16])` — 16 bytes y base64url, el MISMO
    contrato de truncado que las claves del cerrojo (v9 §2/§3.1, un solo
    contrato en todo el diseño). Puede viajar en una cookie firmada y no
    cifrada: es un truncado de SHA-256 sobre un registro que contiene una sal
    aleatoria de 16 bytes — no es invertible, no permite diccionario (la sal no
    se conoce) y no sirve para entrar. Lo único que revela es «la credencial
    cambió», que es su función."""
    crudo = hashlib.sha256(registro.encode("utf-8")).digest()[:16]
    return _b64url_sin_relleno(crudo)


def parsear_usuarios(crudo: str) -> dict[str, str]:
    """`'ana:scrypt$...;luis:scrypt$...'` → `{'ana': 'scrypt$...'}`.

    Separador `;` (o salto de línea, que es como Railway deja pegar varias
    líneas) y NO `,`: la coma ya vive dentro de los parámetros del registro
    (`n=32768,r=8,p=1`) y partir por ella trocearía cada hash por la mitad.

    Las entradas ilegibles se DESCARTAN en silencio aquí y las caza
    `validar_configuracion()` al arrancar: quien decide si el panel puede
    levantarse es el arranque, no cada intento de login.
    """
    usuarios: dict[str, str] = {}
    for entrada in (crudo or "").replace("\n", ";").split(";"):
        entrada = entrada.strip()
        if not entrada:
            continue
        nombre, sep, registro = entrada.partition(":")
        nombre = _normalizar_usuario(nombre)
        if not sep or not nombre or not registro.strip():
            continue
        usuarios[nombre] = registro.strip()
    return usuarios


class BackendEntorno:
    """Usuarios y hashes en `DASHBOARD_USUARIOS`. Se lee en CADA intento (no se
    cachea al importar) para que cambiar la variable en Railway surta efecto al
    reiniciar el servicio y no dependa de cuándo se importó el módulo.

    Implementa `sello` igual que el backend de Supabase (digest del registro de
    la variable): la paridad hace que el modo local y los dobles ejerzan la
    MISMA revalidación por petición que producción, no una excepción."""

    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None:
        usuarios = parsear_usuarios(os.getenv(VARIABLE_USUARIOS, ""))
        clave = _normalizar_usuario(usuario)
        registro = usuarios.get(clave)
        if registro is None:
            verificar(contrasena, _SENUELO)      # tiempo constante, ver _SENUELO
            return None
        if not verificar(contrasena, registro):
            return None
        return Usuario(nombre=clave, sello=sello_de_registro(registro))

    def sello(self, nombre: str) -> str | None:
        registro = parsear_usuarios(os.getenv(VARIABLE_USUARIOS, "")).get(
            _normalizar_usuario(nombre)
        )
        return None if registro is None else sello_de_registro(registro)


class BackendSupabase:
    """Los usuarios del panel en `panel_usuarios` (migración 019) — la primera
    implementación real de la interfaz enchufable de DEC-231 §3, y el motivo de
    (a2): revocar es un `UPDATE` efectivo en la SIGUIENTE petición, no un
    redespliegue (DEC-237/DEC-239; diseño: evals/s324i_panel_vercel_propuesta_v9.md).

    LA DISCIPLINA DEL SEÑUELO SE HEREDA, no solo la interfaz (v9 §5):
      · la entrada se acota ANTES de viajar en un filtro (`usuario_admisible`);
        un nombre que no pasa el charset se trata como inexistente — señuelo y
        `None`, SIN consulta;
      · una sola consulta por PK con `activo` EN el filtro: ausente e inactivo
        son la misma respuesta vacía y el código no puede distinguirlos ni por
        accidente;
      · respuesta VACÍA → señuelo scrypt y `None` (el coste ~100 ms se paga
        exista o no el usuario);
      · CUALQUIER otro resultado del transporte — conexión imposible,
        `tabla_ausente`, `sin_credenciales`, toda respuesta HTTP >= 400 — es
        «no puedo comprobarlo»: `IdentidadNoDisponible`, sin señuelo (una caída
        falla igual para todos, antes de tocar credencial alguna; no necesita
        tiempo constante — necesita no mentir). Es la regla simétrica a la del
        cerrojo (v9, ronda S4-M1/S6-M4).

    El transporte se INYECTA (un callable con la firma de `datos.leer`) para
    que la suite corra sin red — la lección de s324h (v9, puerta 10)."""

    _SELECT = "usuario,registro"

    def __init__(self, leer=None) -> None:
        if leer is None:
            from . import datos                  # perezoso: no cargar config en tests
            leer = datos.leer
        self._leer = leer

    def _registro_activo(self, nombre: str) -> str | None:
        """El registro del usuario ACTIVO `nombre`, `None` si no existe/inactivo.
        Lanza `IdentidadNoDisponible` si el transporte no pudo responder OK."""
        from . import datos
        resultado = self._leer("panel_usuarios", {
            "select": self._SELECT,
            "usuario": f"eq.{nombre}",
            "activo": "is.true",
            "limit": "1",
        })
        if resultado.estado == datos.VACIO:
            return None
        if resultado.estado != datos.OK or not resultado.filas:
            raise IdentidadNoDisponible(
                f"panel_usuarios ilegible ({resultado.estado}: "
                f"{resultado.detalle or 'sin detalle'})"
            )
        registro = resultado.filas[0].get("registro")
        if not isinstance(registro, str) or not registro:
            raise IdentidadNoDisponible("panel_usuarios devolvió una fila sin registro")
        return registro

    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None:
        clave = _normalizar_usuario(usuario)
        if not usuario_admisible(clave):
            verificar(contrasena, _SENUELO)      # inadmisible ≡ inexistente
            return None
        registro = self._registro_activo(clave)
        if registro is None:
            verificar(contrasena, _SENUELO)      # tiempo constante, ver _SENUELO
            return None
        if not verificar(contrasena, registro):
            return None
        return Usuario(nombre=clave, sello=sello_de_registro(registro))

    def sello(self, nombre: str) -> str | None:
        # Sin señuelo: aquí solo llegan nombres que ya pasaron una firma HMAC
        # válida (la cookie), no entrada del atacante (v9 §2). El guard del
        # charset se aplica igual — barato, y la consulta imposible no se hace.
        clave = _normalizar_usuario(nombre)
        if not usuario_admisible(clave):
            return None
        registro = self._registro_activo(clave)
        return None if registro is None else sello_de_registro(registro)


_backend: Backend = BackendEntorno()


def usar_backend(backend: Backend) -> Backend:
    """Sustituye el backend activo y devuelve el anterior. ES el punto de
    extensión de DEC-231 §3 — y también lo que permite probar las rutas sin
    pagar un scrypt por test."""
    global _backend
    anterior, _backend = _backend, backend
    return anterior


def backend_activo() -> Backend:
    return _backend


def autenticar(usuario: str, contrasena: str) -> Usuario | None:
    """LA interfaz. Todo lo de arriba llama aquí y a nada más."""
    return _backend.autenticar(usuario, contrasena)


# --------------------------------------------------------- fuerza bruta
#
# scrypt ya impone un suelo (~100 ms por intento ≈ 10 intentos/s por núcleo),
# que basta contra un diccionario perezoso y NO basta contra alguien decidido
# con una contraseña débil. El cerrojo pone el techo.
#
# Se cuenta por USUARIO y por IP, y basta con que uno de los dos esté cerrado:
#   · sólo por IP  → un botnet con mil direcciones no encuentra la puerta;
#   · sólo por usuario → cualquiera deja fuera a Alberto escribiendo su nombre.
# Ninguna de las dos sola sirve, así que van las dos y se declara el precio: SÍ,
# alguien puede provocar un bloqueo de 15 minutos del usuario `alberto`. Es
# molesto y acotado; la alternativa (no cerrar por usuario) regala el ataque
# distribuido, que es el que de verdad entra.

#: Intentos gratis antes de empezar a cerrar.
FALLOS_LIBRES = 4
#: Primer bloqueo, en segundos. Dobla con cada fallo posterior.
BLOQUEO_BASE_S = 60.0
#: Techo del bloqueo. 15 min: castiga al automatismo sin convertir un error de
#: teclado en el final de la tarde.
BLOQUEO_MAX_S = 900.0
#: Cota de memoria de la tabla de intentos, misma disciplina que
#: `access.CACHE_MAX_ENTRADAS`: es una estructura alimentada DESDE FUERA por
#: quien quiera, en el componente que atiende precisamente a los no autorizados.
CERROJO_MAX_ENTRADAS = 10_000
#: Retención de una fila de intentos en el cerrojo DISTRIBUIDO (s324j, v9
#: §3.4/§6): la poda de `panel_puerta` borra lo más viejo que esto en cada
#: escritura, y es también el plazo RGPD de `panel_intentos` — con la salvedad
#: de que LA FUENTE del plazo es la POLICY de la 019 (doctrina s299: «si
#: divergieran, manda la política»); el test de integración pg valida esta
#: constante por IGUALDAD contra el predicado real en `pg_policies`.
CERROJO_RETENCION_S = 24 * 3600


@dataclass
class _Intentos:
    fallos: int
    ultimo: float


class Cerrojo:
    """Contador de fallos con espera creciente. Sin estado en base a propósito:
    un panel de dos usuarios no necesita coordinar el cerrojo entre réplicas, y
    montar esa coordinación sería inventar un problema. Precio declarado: si
    Railway reinicia el servicio, los contadores se van con él."""

    def __init__(self) -> None:
        self._tabla: dict[str, _Intentos] = {}

    def espera(self, clave: str, ahora: float) -> float:
        """Segundos que faltan para poder reintentar (`0.0` = adelante)."""
        entrada = self._tabla.get(clave)
        if entrada is None or entrada.fallos <= FALLOS_LIBRES:
            return 0.0
        castigo = min(
            BLOQUEO_BASE_S * (2 ** (entrada.fallos - FALLOS_LIBRES - 1)),
            BLOQUEO_MAX_S,
        )
        return max(0.0, entrada.ultimo + castigo - ahora)

    def bloqueado(self, claves: tuple[str, ...], ahora: float) -> float:
        """La mayor espera de todas las claves: basta una cerrada para cerrar."""
        return max((self.espera(c, ahora) for c in claves), default=0.0)

    def fallo(self, claves: tuple[str, ...], ahora: float) -> None:
        self._podar(ahora)
        for clave in claves:
            entrada = self._tabla.get(clave)
            if entrada is None:
                self._tabla[clave] = _Intentos(1, ahora)
            else:
                entrada.fallos += 1
                entrada.ultimo = ahora

    def admitir(self, claves: tuple[str, ...], ahora: float | None = None) -> float:
        """CONTAR LA ADMISIÓN, no el fallo (s324j, v9 §3.2). Devuelve los
        segundos de espera (`0.0` = adelante — y el intento YA está contado);
        `acierto` es la devolución del provisional.

        Por qué así: con «comprobar → scrypt → registrar el fallo», N
        peticiones concurrentes pasan la comprobación antes de que ninguna
        registre y el umbral no bloquea nada (el rebaño). Contando AL admitir,
        la petición K ve los K−1 incrementos anteriores y con
        `FALLOS_LIBRES = 4` entran ~5, no N. La SECUENCIA no cambia: el intento
        k ve `fallos = k−1`, igual que con el par `bloqueado`+`fallo` de antes
        (el sexto intento de una tanda fallida se bloquea en ambos). Precio
        declarado: si el proceso muere entre `admitir` y `acierto`, queda un
        +1 fantasma que decae solo (solo pesa por encima de `FALLOS_LIBRES`).

        Este doble en memoria fija la SEMÁNTICA DE BLOQUEO Y BACKOFF que
        `panel_puerta` reproduce en SQL para el cerrojo distribuido
        (`dashboard/cerrojo.py`); la tabla de casos de la puerta 4 ata esa
        parte. Lo que NO es idéntico, a propósito (ronda de verificación,
        S3-M2): la RETENCIÓN. El SQL poda una clave inactiva a las
        `CERROJO_RETENCION_S` (24 h) SIEMPRE —requisito RGPD de `panel_intentos`,
        que es dato personal seudonimizado—; este `_podar` solo actúa cuando la
        tabla llega al cap, porque un dict en memoria no tiene ese requisito.
        La diferencia solo se nota en una clave que lleva >24 h sin actividad y
        por debajo del cap: en SQL renace su backoff, en memoria persiste. Es
        una divergencia declarada, no un defecto de paridad."""
        if ahora is None:
            ahora = time.monotonic()
        espera = self.bloqueado(claves, ahora)
        if espera > 0:
            return espera                        # bloqueado: sin incrementar
        self.fallo(claves, ahora)                # la admisión, contada YA
        return 0.0

    def acierto(self, claves: tuple[str, ...]) -> None:
        """Un login bueno limpia el historial de esas claves."""
        for clave in claves:
            self._tabla.pop(clave, None)

    def _podar(self, ahora: float) -> None:
        if len(self._tabla) < CERROJO_MAX_ENTRADAS:
            return
        # Primero lo que ya cumplió condena: no se está usando para nada.
        for clave in [c for c in self._tabla if self.espera(c, ahora) <= 0.0]:
            self._tabla.pop(clave, None)
        if len(self._tabla) < CERROJO_MAX_ENTRADAS:
            return
        # Todo bloqueado y la tabla llena: se sacrifica lo más antiguo. Perder
        # un bloqueo vivo le regala al atacante otra tanda de intentos gratis;
        # quedarse sin memoria le regala el servicio entero.
        for clave, _ in sorted(self._tabla.items(), key=lambda par: par[1].ultimo)[
            : max(1, len(self._tabla) // 10)
        ]:
            self._tabla.pop(clave, None)

    def reiniciar(self) -> None:
        self._tabla.clear()


def claves_de(usuario: str, ip: str) -> tuple[str, ...]:
    return (f"u:{_normalizar_usuario(usuario)}", f"ip:{(ip or '?').strip()}")


# ------------------------------------------------------- fail-fast de arranque


def validar_configuracion() -> None:
    """Aborta el ARRANQUE si el panel no puede autenticar a nadie.

    Mismo patrón que `access.validar_configuracion` y por el mismo motivo: estas
    variables se escriben a mano en Railway, y las tres formas de equivocarse
    —no ponerla, pegar media línea, pegar la contraseña en claro— producen un
    panel que levanta y no deja entrar. Un deploy que no arranca con el motivo
    escrito es ruidoso, inmediato y Railway conserva la versión anterior.

    NO valida el backend enchufado por `usar_backend`: el día que autentique el
    war room, esta comprobación de `DASHBOARD_USUARIOS` deja de aplicar y el
    backend nuevo traerá la suya.
    """
    if not isinstance(_backend, BackendEntorno):
        return
    crudo = os.getenv(VARIABLE_USUARIOS, "")
    if not crudo.strip():
        raise RuntimeError(
            f"{VARIABLE_USUARIOS} está vacía: el panel no podría autenticar a "
            f"nadie. Genera un registro con "
            f"`python -m scripts.s324f_dashboard_password` y pégalo en Railway."
        )
    usuarios = parsear_usuarios(crudo)
    if not usuarios:
        raise RuntimeError(
            f"{VARIABLE_USUARIOS} no tiene ninguna entrada legible "
            f"(formato: `usuario:scrypt$n=..,r=..,p=..$sal$hash`, separadas "
            f"por `;`)."
        )
    malos = []
    for nombre, registro in usuarios.items():
        try:
            _partir(registro)
        except RegistroInvalido as exc:
            malos.append(f"{nombre} ({exc})")
    if malos:
        raise RuntimeError(
            f"{VARIABLE_USUARIOS} tiene registros no válidos: {', '.join(malos)}. "
            f"¿Pegaste la contraseña en claro en vez del hash? Genera el "
            f"registro con `python -m scripts.s324f_dashboard_password`."
        )
