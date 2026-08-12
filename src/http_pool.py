# -*- coding: utf-8 -*-
"""s317 — Cliente HTTP COMPARTIDO de proceso (TECH_DEBT #72, fase 1: transporte).

POR QUÉ (perfil medido, `evals/s317_perfil_retrieval_v1.md`): una llamada servida
de `retrieve_chunks` construía CATORCE `httpx.Client` — 7,25 s solo en crear
contextos SSL (leer el bundle de CAs del disco 14 veces) + ~3,4 s de handshakes
TCP/TLS repetidos, sobre 19,0 s calientes. ~60 sitios de `src/` repetían el
patrón `with httpx.Client(timeout=X) as client:`.

ALCANCE v1 — SOLO transporte, CERO política: un cliente por proceso con pool
keep-alive y UN contexto SSL. Los timeouts siguen siendo POR PETICIÓN, con el
mismo valor que cada sitio ya declaraba (el shim los inyecta por defecto). NO
se añade NINGÚN reintento — ni de petición NI de connect (dúo r14, Sol M3/
Fable F1: hasta un retry de connect es política; la política consciente-de-
idempotencia entera es la fase 2 de #72, con su propio dúo).

RIESGOS RESIDUALES DECLARADOS (r14 — riesgo real, no «cubierto»):
- Conexión keep-alive que el servidor cerró y pasó el expiry-check ⇒ la
  petición falla con ReadError/RemoteProtocolError SIN reintento — un modo de
  fallo que el cliente-fresco no tenía. Mitigación: `keepalive_expiry=30 s`
  (< idle-timeouts típicos de Supabase/proxies). El sitio afectado falla como
  fallaría hoy un timeout (todas las rutas tienen su manejo).
- Bajo picos de concurrencia el pool puede encolar (PoolTimeout) donde el
  cliente-fresco nunca esperaba. Mitigación: `max_connections=40` (~3 turnos
  simultáneos de 14 peticiones); el kill-switch es la vuelta atrás sin deploy.

MIGRACIÓN (deliberadamente de un token por sitio):
    with httpx.Client(timeout=15.0) as client:     # antes
    with abierto(timeout=15.0) as client:          # después — cuerpo INTACTO
El shim delega get/post/patch/delete/request en el cliente compartido, inyecta
el timeout del sitio en cada petición, y su __exit__ NO cierra el cliente de
proceso.

KILL-SWITCH: `HTTP_POOL=off` degrada a un cliente fresco POR BLOQUE `with`
(dúo r14, Sol M2: por-petición no era «la forma de hoy» — los bloques de
logging_db/catalog_resolver reutilizan el cliente para varias peticiones);
fuera de un `with` (el cliente persistente de SupabaseHTTP) degrada a
por-petición, declarado. Reversible en Railway sin deploy. Default ON:
infraestructura de transporte con paridad medida (recibo v2: A/B intercalado
3 queries × 3 reps) y riesgos residuales declarados arriba.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CLIENTE: httpx.Client | None = None

# keepalive_expiry por debajo de los idle-timeouts típicos de proxies (Supabase/
# Cloudflare ~60-100 s): una conexión que el servidor ya cerró no se reutiliza.
_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=10,
                       keepalive_expiry=30.0)


def _pool_activo() -> bool:
    return os.getenv("HTTP_POOL", "on").strip().lower() not in {"off", "0", "false"}


def _retries_activo() -> bool:
    """Kill-switch PROPIO de los reintentos (#72 fase 2b, Sol r15 M1: el
    kill-switch del pool no cubre la fase 2 — cada mecanismo lleva el suyo)."""
    return os.getenv("HTTP_RETRIES", "on").strip().lower() not in {"off", "0", "false"}


# (Fable r15 F2) El set reintentable EXCLUYE PoolTimeout a conciencia:
# PoolTimeout ⊂ TransportError pero es agotamiento de recurso LOCAL (el pool
# saturado), no un transitorio de red — reintentarlo convierte backpressure en
# amplificación de carga justo bajo saturación. Se reintenta la RED
# (connect/read/write/protocolo), una vez, tras 0,2 s.
_BACKOFF_S = 0.2


def _es_reintentable(exc: Exception) -> bool:
    return isinstance(exc, httpx.TransportError) and not isinstance(exc, httpx.PoolTimeout)


def _cliente_proceso() -> httpx.Client:
    global _CLIENTE
    if _CLIENTE is None:
        with _LOCK:
            if _CLIENTE is None:
                # (Sol r14 M1, verificado ejecutando) los limits van EN el
                # transporte: un HTTPTransport explícito IGNORA los limits del
                # Client — con `Client(transport=t, limits=...)` el keep-alive
                # prometido era código muerto (expiry default 5 s).
                _CLIENTE = httpx.Client(
                    transport=httpx.HTTPTransport(limits=_LIMITS),
                    # timeout de RED para una llamada sin timeout de sitio
                    # (hoy: ninguna — los 55 sitios lo declaran; el shim solo
                    # inyecta el suyo cuando NO es None, Fable r14 F3).
                    timeout=30.0,
                )
    return _CLIENTE


class _Shim:
    """Fachada por-SITIO sobre el cliente de proceso: aplica el timeout que el
    sitio declaraba y no cierra nada del proceso al salir del `with`."""

    __slots__ = ("_timeout", "_reintentos", "_cm", "_local")

    def __init__(self, timeout: float | httpx.Timeout | None,
                 reintentos: int = 0):
        self._timeout = timeout
        # (#72 fase 2b) La idempotencia SE DECLARA por sitio, jamás se infiere
        # del verbo (hay POST /rpc/* de solo lectura y GETs con side-effects
        # posibles): reintentos>0 SOLO en sitios de solo-lectura declarados.
        # Alcance v1: sitios del serving SIN veredicto previo de no-retry —
        # los 4 canales s306 (VECTOR/ENUNCIADOS/HYQ_*) conservan su fail-open
        # MEDIDO intacto (dúo r15: no anidar ni re-litigar DEC-089/#63); los
        # scripts con bisección+poison (s104/s315) quedan FUERA (su política
        # de reanudación ya existe y un retry de POST sin upsert duplicaría).
        self._reintentos = max(0, int(reintentos))
        self._cm = None
        self._local = None

    # --- context manager (paridad de forma con `with httpx.Client(...)`) ----
    def __enter__(self) -> "_Shim":
        if not _pool_activo():
            # kill-switch: UN cliente fresco POR BLOQUE `with` — la semántica
            # EXACTA de hoy (Sol r14 M2: los bloques de logging_db y
            # catalog_resolver reutilizan el cliente para varias peticiones).
            # Se delega en el PROTOCOLO with del cliente (__enter__/__exit__),
            # no en .close(): es lo que el código de hoy hace y lo que los
            # fakes de la suite implementan.
            self._cm = httpx.Client(timeout=self._timeout)
            self._local = self._cm.__enter__()
        return self

    def __exit__(self, *exc) -> bool:
        if self._cm is not None:
            cm, self._cm, self._local = self._cm, None, None
            return bool(cm.__exit__(*exc))
        return False

    # --- delegación ----------------------------------------------------------
    def _request(self, metodo: str, url: str, **kwargs):
        intentos = 1 + (self._reintentos if _retries_activo() else 0)
        for intento in range(intentos):
            try:
                return self._enviar(metodo, url, **kwargs)
            except Exception as exc:               # noqa: BLE001
                if intento + 1 >= intentos or not _es_reintentable(exc):
                    raise
                # Ruidoso: el reintento es un evento de red real, no un detalle
                # (el fallo que PERSISTA tras esto propaga y lo registra el
                # manejo del sitio — trace de canal o fail-open declarado).
                logger.warning("http_pool: %s %s falló (%s) — reintento en %ss",
                               metodo, urlsplit(url).path,
                               type(exc).__name__, _BACKOFF_S)
                time.sleep(_BACKOFF_S)
        raise AssertionError("unreachable")

    def _enviar(self, metodo: str, url: str, **kwargs):
        if self._local is not None:
            return getattr(self._local, metodo.lower())(url, **kwargs)
        if _pool_activo():
            # el timeout del sitio, POR PETICIÓN; None jamás se inyecta (sería
            # timeout INFINITO explícito — Fable r14 F3): sin sitio, manda el
            # default del cliente de proceso (30 s).
            if self._timeout is not None:
                kwargs.setdefault("timeout", self._timeout)
            return _cliente_proceso().request(metodo, url, **kwargs)
        # kill-switch SIN `with` (el cliente persistente de SupabaseHTTP):
        # cliente fresco por petición, con la forma de hoy — timeout en el
        # constructor y llamada por método nominal (los fakes de la suite
        # interceptan exactamente esta forma; conftest fija HTTP_POOL=off).
        with httpx.Client(timeout=self._timeout) as c:
            return getattr(c, metodo.lower())(url, **kwargs)

    def get(self, url: str, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self._request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self._request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self._request("DELETE", url, **kwargs)

    def request(self, metodo: str, url: str, **kwargs):
        return self._request(metodo, url, **kwargs)


def abierto(timeout: float | httpx.Timeout | None = None,
            reintentos: int = 0) -> _Shim:
    """Sustituto de `httpx.Client(timeout=X)` en un `with`: mismo cuerpo, mismo
    timeout, transporte compartido. También sirve SIN `with` (p. ej. el cliente
    persistente de `SupabaseHTTP`).

    `reintentos` (#72 fase 2b): SOLO para sitios de solo-lectura DECLARADOS —
    reintenta transitorios de RED (TransportError sin PoolTimeout), jamás
    respuestas HTTP. Default 0 = byte-idéntico a hoy."""
    return _Shim(timeout, reintentos)


def cerrar() -> None:
    """Cierra el cliente de proceso (tests / apagado ordenado). El siguiente
    uso lo reconstruye."""
    global _CLIENTE
    with _LOCK:
        if _CLIENTE is not None:
            _CLIENTE.close()
            _CLIENTE = None
