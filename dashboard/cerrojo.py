# -*- coding: utf-8 -*-
"""El cerrojo anti-fuerza-bruta DISTRIBUIDO del panel (s324j; diseño:
`evals/s324i_panel_vercel_propuesta_v9.md` §3, validado en seis rondas del dúo).

POR QUÉ EXISTE. `auth.Cerrojo` cuenta en memoria del proceso, y en serverless
cada intento puede caer en una instancia distinta: la espera creciente casi no
llega a aplicarse (`docs/DASHBOARD_DESPLIEGUE.md`). Aquí el contador vive en
`panel_intentos` (migración 019) y la ADMISIÓN entera es UNA función en la base
(`panel_puerta`): poda, siembra, comprobación y conteo en una sola transacción —
contar AL admitir es lo que acota el rebaño concurrente que «comprobar → scrypt
→ registrar» dejaba pasar (v9 §3.2).

LAS CLAVES SALEN SEUDONIMIZADAS, la estructura no (v9 §3.1): se conservan los
DOS espacios de nombres de `auth.claves_de` (`u:` / `ip:`, contados por
separado, cierra el peor) y se sustituye el identificador por
`b64url_sin_relleno(HMAC-SHA256(K, identificador)[:16])`, con
`K = HMAC-SHA256(DASHBOARD_SECRET, "panel_intentos:v1")` — clave DERIVADA con
etiqueta de propósito, no el secreto de firma a pelo. Un volcado de la tabla no
enseña ni usuarios ni IPs (minimización; sigue siendo dato personal
SEUDONIMIZADO y así está declarado en la matriz de retención — v9 §6). Precio
declarado: rotar `DASHBOARD_SECRET` rota `K` y resetea los contadores — 5
intentos de margen por clave sobre el suelo scrypt, en un evento raro y manual.

LA CLAVE `ip:` ESTÁ APAGADA hasta que la regla de confianza de
`X-Forwarded-For` en Vercel esté MEDIDA y fijada (v9 §3.1/§8, ronda F5-M1): con
una IP mal calibrada todos los usuarios compartirían UNA clave `ip:` (la del
proxy, o `'?'`), y como el bloqueo es el MAX de las claves, 5 fallos de un
atacante serían un 429 GLOBAL del panel — denegación de servicio con la
protección en verde. Hasta la medición, este cerrojo cuenta y bloquea SOLO por
`u:`; encender la mitad `ip:` es voltear `INCLUIR_CLAVE_IP`, gateado por esa
medición (el gate está en el runbook).

LA FRONTERA DEL FAIL-OPEN ES «¿SE PUDO HABLAR?» (v9 §3.5, rondas F2-M2/S3-M1/
S4-M1): un fallo de CONEXIÓN (timeout, DNS, red — PostgREST no llegó a
responder) permite el intento con un log a nivel ERROR: un fallo de telemetría
no deja fuera al legítimo, pero tampoco es invisible. CUALQUIER RESPUESTA HTTP
>= 400 es otra cosa: PostgREST habló y algo está mal de forma REPRODUCIBLE
(función sin migrar, firma, permisos, SQL) — eso es configuración, y se lanza
`CerrojoNoDisponible` para que la entrada responda el MISMO 503 que
`IdentidadNoDisponible`. Un panel que no puede contar intentos por estar mal
desplegado no debe estar atendiendo logins.

NOTA DE AUDITORÍA (la invariante de `gestion.py`, ampliada — v9 §3.2): las
peticiones no-GET del panel viven en DOS ficheros enumerables: las tres de
gestión en `gestion.py`, y aquí la RPC de `admitir` y el DELETE de `acierto`.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Protocol

import httpx

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

from . import auth, sesion

logger = logging.getLogger(__name__)

TIMEOUT_S = 15.0

#: v9 §3.1 / ronda F5-M1: la mitad `ip:` NI CUENTA NI BLOQUEA hasta que la
#: medición de XFF fije la regla de confianza en Vercel. NO voltear sin la
#: medición hecha y escrita (runbook, `docs/DASHBOARD_DESPLIEGUE.md`).
INCLUIR_CLAVE_IP = False


class CerrojoNoDisponible(RuntimeError):
    """El cerrojo distribuido NO pudo operar por CONFIGURACIÓN, no por red.

    La produce cualquier respuesta HTTP >= 400 de la RPC (función sin migrar,
    ACL, firma, SQL) o la ausencia de credenciales del panel. La capa de rutas
    la convierte en el mismo 503 que `auth.IdentidadNoDisponible` — fail-closed
    para estados persistentes (v9 §3.5)."""


class Cerrojo(Protocol):
    """El contrato que comparten el cerrojo en memoria y el distribuido."""

    def admitir(self, claves: tuple[str, ...], ahora: float | None = None) -> float:
        ...

    def acierto(self, claves: tuple[str, ...]) -> None:
        ...


# ------------------------------------------------------- las claves, seudónimas


def _clave_derivada() -> bytes:
    """`K`: derivada del secreto de firma con etiqueta de propósito, para no
    reutilizar el mismo secreto en dos roles (v9 §3.1)."""
    return hmac.new(sesion.secreto(), b"panel_intentos:v1", hashlib.sha256).digest()


def _seudonimo(clave_plana: str, k: bytes) -> str:
    """`u:alberto` → `u:<b64url(HMAC(K, "alberto")[:16])>`. El espacio de
    nombres queda a la vista (audita y separa las dos mitades del cerrojo); el
    identificador, nunca."""
    ns, _, identificador = clave_plana.partition(":")
    mac = hmac.new(k, identificador.encode("utf-8"), hashlib.sha256).digest()[:16]
    return f"{ns}:{auth._b64url_sin_relleno(mac)}"


def claves_seudonimas(claves: tuple[str, ...]) -> tuple[str, ...]:
    """Las claves de `auth.claves_de`, seudonimizadas — y con la mitad `ip:`
    APAGADA mientras `INCLUIR_CLAVE_IP` sea False (ronda F5-M1)."""
    k = _clave_derivada()
    return tuple(
        _seudonimo(clave, k)
        for clave in claves
        if INCLUIR_CLAVE_IP or not clave.startswith("ip:")
    )


# ------------------------------------------------------ el cerrojo distribuido


def _transporte_rpc(payload: dict) -> httpx.Response:
    """POST /rest/v1/rpc/panel_puerta. La clave de servicio no sale de aquí."""
    with httpx.Client(timeout=TIMEOUT_S) as cliente:
        return cliente.post(
            f"{SUPABASE_URL}/rest/v1/rpc/panel_puerta",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )


def _transporte_delete(params: dict) -> httpx.Response:
    with httpx.Client(timeout=TIMEOUT_S) as cliente:
        return cliente.delete(
            f"{SUPABASE_URL}/rest/v1/panel_intentos",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params=params,
        )


class CerrojoSupabase:
    """`admitir` = la RPC `panel_puerta` (una transacción: poda, cap, siembra,
    comprobación y conteo — v9 §3.2-§3.4); `acierto` = un DELETE por PostgREST.

    Los transportes se INYECTAN para que la suite corra sin red (puerta 10)."""

    def __init__(self, rpc=None, delete=None) -> None:
        self._rpc = rpc or _transporte_rpc
        self._delete = delete or _transporte_delete

    def admitir(self, claves: tuple[str, ...], ahora: float | None = None) -> float:
        # `ahora` se ignora a propósito: el reloj es `now()` DE LA BASE —
        # coherente entre instancias serverless que nacen y mueren (v9 §3.2).
        if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
            raise CerrojoNoDisponible(
                "el panel no tiene credenciales de Supabase (SUPABASE_URL / "
                "SUPABASE_SERVICE_KEY): configuración, no red"
            )
        payload = {
            "claves": list(claves_seudonimas(claves)),
            "libres": auth.FALLOS_LIBRES,
            "base_s": auth.BLOQUEO_BASE_S,
            "max_s": auth.BLOQUEO_MAX_S,
            "retencion_s": auth.CERROJO_RETENCION_S,
            "cap": auth.CERROJO_MAX_ENTRADAS,
        }
        try:
            resp = self._rpc(payload)
        except httpx.HTTPError as exc:
            # No se pudo HABLAR: fail-open CON log — un fallo de telemetría no
            # deja fuera al legítimo, pero tampoco es invisible (v9 §3.5).
            logger.error(
                "cerrojo: fail-open, no se pudo hablar con Supabase (%s)",
                type(exc).__name__,
            )
            return 0.0
        if resp.status_code >= 400:
            # PostgREST HABLÓ y rechazó: reproducible ⇒ configuración ⇒ 503.
            raise CerrojoNoDisponible(
                f"panel_puerta respondió {resp.status_code}: ¿falta aplicar "
                f"migrations/019_panel_usuarios_cerrojo.sql, o sus GRANT?"
            )
        try:
            espera = float(resp.json())
        except Exception:                                        # noqa: BLE001
            raise CerrojoNoDisponible(
                "panel_puerta devolvió un cuerpo ilegible"
            ) from None
        return max(0.0, espera)

    def acierto(self, claves: tuple[str, ...]) -> None:
        # La devolución del provisional. Si falla, NO se bloquea el login bueno:
        # el +1 fantasma decae solo (precio declarado en v9 §3.2) — pero se deja
        # log, que un acierto que nunca limpia también es una señal.
        seudonimas = claves_seudonimas(claves)
        if not seudonimas:
            return
        try:
            resp = self._delete({"clave": f"in.({','.join(seudonimas)})"})
        except httpx.HTTPError as exc:
            logger.error("cerrojo: acierto sin limpiar (%s)", type(exc).__name__)
            return
        if resp.status_code >= 400:
            logger.error("cerrojo: acierto rechazado (%s)", resp.status_code)


# --------------------------------------------------------------- el enchufe

_activo: Cerrojo = auth.Cerrojo()


def usar_cerrojo(cerrojo: Cerrojo) -> Cerrojo:
    """Sustituye el cerrojo activo y devuelve el anterior — el mismo punto de
    extensión que `auth.usar_backend`: quien arranca elige (v9 §9). En local y
    en tests queda el de memoria; `api/index.py` enchufa `CerrojoSupabase`."""
    global _activo
    anterior, _activo = _activo, cerrojo
    return anterior


def activo() -> Cerrojo:
    return _activo


def sonda() -> None:
    """La sonda de arranque (v9 §3.5): con `CerrojoSupabase` enchufado, llama a
    `panel_puerta` con la lista de claves VACÍA — una prueba real de extremo a
    extremo (función migrada, GRANT concedidos, caché de PostgREST recargada)
    sin efecto sobre NINGÚN contador (sí ejecuta la poda de caducados y toma el
    lock un instante — efectos benignos, dichos). Si falla, el arranque aborta
    con el motivo escrito — el criterio de `auth.validar_configuracion`. Con el
    cerrojo de memoria no hay nada que sondear."""
    if not isinstance(_activo, CerrojoSupabase):
        return
    try:
        _activo.admitir(())
    except CerrojoNoDisponible as exc:
        raise RuntimeError(
            f"El cerrojo distribuido no está operativo: {exc}. El panel NO "
            f"arranca sin él (fail-closed para configuración, v9 §3.5)."
        ) from exc
