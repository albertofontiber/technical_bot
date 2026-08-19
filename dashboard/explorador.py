# -*- coding: utf-8 -*-
"""El Explorador: la vista fila-a-fila de preguntas, con filtros CERRADOS.

QUÉ ES. La pantalla que DEC-231 dejó fuera de la v1 del panel («leer las
conversaciones… entra cuando el piloto lo pida y con su propia vuelta de
RGPD») y que Alberto reabrió a conciencia en s326 (adjudicación (a): prosa
completa — pregunta y comentario del técnico). Lee `bot_explorador_v1`
(migración 021), que ya junta pregunta + clasificación + feedback del autor +
alias de allowlist; aquí solo se eligen filas.

LA REGLA DE LOS FILTROS es la de `errores.py`, aplicada tres veces: cada
parámetro de la URL acaba en un filtro de PostgREST, así que NINGUNO se parsea
— se elige de una lista cerrada o cae al defecto. Periodo y feedback son listas
fijas; categoría sale de la taxonomía versionada (la misma del clasificador);
marca se valida contra los nombres canónicos de `documents.manufacturer`
(activos) — la MISMA fuente con que el clasificador canonicaliza `marcas`, así
el filtro y el dato no pueden divergir, y el filtro funciona aunque la 021 aún
no esté aplicada (hallazgo Fable r1 s326: la versión anterior de este párrafo
describía la fuente vieja).

Y el mismo reparto de papeles que el resto del panel: este módulo no lanza
(lee con `datos.leer`, que traduce fallos a estado), y no recalcula nada que
la vista SQL ya sepa hacer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

# A NIVEL DE MÓDULO a propósito (incidente del preview, 19-ago): el gate de la
# clausura del panel (test_s324j_panel_requirements) escanea imports a columna
# 0 — un import perezoso lo esquivaba y PyYAML faltó en la función de Vercel:
# /explorador servía un 500 en runtime. Visible aquí, el gate exige el paquete
# ANTES del deploy; si aún así faltara, el panel entero falla EN FRÍO y en el
# log (fail-closed de arranque, el patrón de la sonda del lifespan), no con un
# 500 mudo a mitad de clic.
from src.clasificacion import cargar_taxonomia

from . import datos

#: Ventanas de tiempo ofrecidas (días; 0 = todo el histórico).
VENTANAS = (7, 30, 90, 0)
VENTANA_DEFECTO = 30

#: Filtro de feedback ofrecido. `comentados` = con texto del «✍️ Te lo explico».
FEEDBACK = ("todos", "up", "down", "comentados")
FEEDBACK_DEFECTO = "todos"

#: El panel busca lectura y patrones, no es un export: por encima de esto, la
#: respuesta correcta es SQL en Supabase, no una página más larga.
TOPE_FILAS = 500

_SELECT = ("id,created_at,canal,ruta,categoria,taxonomia_version,marcas,"
           "modelos,pregunta,response_length,quien,verdict,reason_class,comment")


@dataclass(frozen=True)
class Filtros:
    dias: int
    categoria: str | None
    marca: str | None
    feedback: str


@lru_cache(maxsize=1)
def categorias_validas() -> tuple[str, ...]:
    """Los ids de la taxonomía vigente — la misma lista que usa el clasificador,
    para que el filtro y el dato no puedan divergir. Cacheada: la taxonomía
    solo cambia con un deploy. FAIL-OPEN a `()` si el YAML no está o no parsea
    (regla del panel: este módulo no lanza) — el select queda en «todas» y la
    validación rechaza cualquier parámetro de categoría; la página vive."""
    try:
        return cargar_taxonomia().ids
    except Exception:                                        # noqa: BLE001
        return ()


def marcas_disponibles() -> tuple[list[str], bool]:
    """(marcas canónicas del corpus, ¿se pudo leer?). La fuente es la MISMA con
    que el clasificador canonicaliza (`documents.manufacturer`, activos): el
    filtro y el dato no pueden divergir. Filtrar por una marca sin preguntas da
    «vacío», que es la verdad. El booleano existe porque «no hay marcas» y «no
    se pudo leer la lista» son pantallas distintas (hallazgo Fable r1 s326):
    la página lo dice en vez de esconder el filtro en silencio."""
    filas = datos.leer("documents", {"select": "manufacturer",
                                     "status": "eq.active", "limit": "1000"})
    if filas.estado not in (datos.OK, datos.VACIO):
        return [], False
    return sorted({str(f.get("manufacturer"))
                   for f in filas.filas if f.get("manufacturer")}), True


def normalizar(consulta: dict, *, categorias: tuple[str, ...],
               marcas: list[str]) -> Filtros:
    """Los parámetros de la URL → filtros de las listas cerradas, o el defecto."""
    def _uno(nombre: str) -> str:
        valores = consulta.get(nombre) or [""]
        return str(valores[0])

    try:
        dias = int(_uno("dias"))
    except (TypeError, ValueError):
        dias = VENTANA_DEFECTO
    if dias not in VENTANAS:
        dias = VENTANA_DEFECTO

    categoria = _uno("categoria")
    marca = _uno("marca")
    feedback = _uno("feedback")
    return Filtros(
        dias=dias,
        categoria=categoria if categoria in categorias else None,
        marca=marca if marca in marcas else None,
        feedback=feedback if feedback in FEEDBACK else FEEDBACK_DEFECTO,
    )


def parametros(filtros: Filtros) -> dict:
    """Los filtros → parámetros de PostgREST sobre `bot_explorador_v1`."""
    params = {
        "select": _SELECT,
        "order": "created_at.desc",
        "limit": str(TOPE_FILAS),
    }
    if filtros.dias > 0:
        corte = datetime.now(timezone.utc) - timedelta(days=filtros.dias)
        params["created_at"] = f"gte.{corte.isoformat().replace('+00:00', 'Z')}"
    if filtros.categoria:
        params["categoria"] = f"eq.{filtros.categoria}"
    if filtros.marca:
        # `cs` = el array `marcas` CONTIENE ese valor. Entrecomillado porque los
        # nombres canónicos llevan guiones y espacios; el valor viene de la
        # whitelist derivada del dato, nunca del teclado del visitante. Y aun
        # así se escapan `\` y `"` (hallazgo Fable r1 s326): un nombre de
        # fabricante mal ingestado no puede romper la sintaxis del filtro.
        marca = filtros.marca.replace("\\", "\\\\").replace('"', '\\"')
        params["marcas"] = 'cs.{"%s"}' % marca
    if filtros.feedback in ("up", "down"):
        params["verdict"] = f"eq.{filtros.feedback}"
    elif filtros.feedback == "comentados":
        params["comment"] = "not.is.null"
    return params


def leer(filtros: Filtros) -> datos.Resultado:
    return datos.leer("bot_explorador_v1", parametros(filtros))
