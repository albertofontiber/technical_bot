# -*- coding: utf-8 -*-
"""Los errores del bot, agregados — REUTILIZANDO la agregación que ya existe.

QUÉ SE REUTILIZA Y QUÉ NO, con el motivo de cada mitad.
`scripts/s324e_bot_errores_insights.py` ya divide su trabajo en tres capas y lo
dice en su propio comentario: I/O arriba, una función PURA en medio (`agregar`,
que es la que prueban sus tests) e impresión abajo. El panel toma la de en medio
TAL CUAL —es la lógica, y dos copias de una agregación divergen en cuanto una de
las dos aprenda algo— y sustituye las otras dos:

  · la IMPRESIÓN, obviamente: aquí sale HTML y allí sale una consola;
  · el I/O, y esto sí es una decisión: `leer()` LANZA ante un fallo de red,
    que es la conducta correcta de un script de consola (revienta, se ve, se
    reintenta) y la incorrecta de una página web (un 500 con traza). El panel
    lee con `datos.leer`, que traduce cada fallo a un estado declarado.

O sea: se reutiliza la lógica y se cambia el envoltorio, que es lo que significa
reutilizar. La alternativa —copiar `agregar` aquí y «adaptarla»— habría creado
la segunda fuente de la verdad que este repo lleva 300 sesiones evitando.

LOS DOS ORÍGENES, y por qué no se suman. `bot_errors` (migración 015) tiene el
diagnóstico: clase, severidad, módulo:línea, si el técnico recibió aviso. Las
filas heredadas de `query_logs` con `source='error'` (s286) sólo tienen la marca
`Tipo@etapa`. Desde que la 015 está aplicada, **un mismo fallo escribe en las
dos**, así que sumarlas contaría cada error dos veces. El panel las enseña en
bloques separados, con esa frase escrita en la página.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# La hoja PURA del informe de consola, sin una segunda copia. Es un import de
# `scripts/` desde una aplicación, y está declarado como tal: el día que el
# panel sea el consumidor principal, `agregar` se gradúa a un módulo propio y
# los dos la importan de ahí. Hoy graduarla sería mover código para no tener que
# escribir este párrafo.
from scripts.s324e_bot_errores_insights import agregar  # noqa: E402

from . import datos

#: Cuántas filas se traen como mucho. El panel busca PATRONES, no es un export:
#: con más de esto, la respuesta correcta no es una página web más larga sino
#: `python -m scripts.s324e_bot_errores_insights --all`, que además pagina.
TOPE_FILAS = 2000

#: Ventanas ofrecidas. Cerrada a propósito: el valor entra por la URL y acaba en
#: un filtro de PostgREST, así que se elige de una lista y no se parsea.
VENTANAS = (7, 30, 90, 0)          # 0 = todo el histórico
VENTANA_DEFECTO = 7

_SELECT_INCIDENCIAS = (
    "codigo,clase,severidad,reintentable,tipo_excepcion,etapa,origen,"
    "mensaje_corto,usuario_avisado,bot_version,created_at,"
    "query_logs(query,telegram_user_id)"
)


def ventana_valida(bruto: object) -> int:
    """El parámetro `?dias=` de la URL → una de las ventanas de la lista."""
    try:
        dias = int(str(bruto))
    except (TypeError, ValueError):
        return VENTANA_DEFECTO
    return dias if dias in VENTANAS else VENTANA_DEFECTO


def _desde(dias: int) -> str | None:
    if dias <= 0:
        return None
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    return corte.isoformat().replace("+00:00", "Z")


def leer(dias: int) -> tuple[datos.Resultado, datos.Resultado]:
    """(incidencias de `bot_errors`, filas heredadas de `query_logs`)."""
    desde = _desde(dias)
    comun = {"order": "created_at.desc", "limit": str(TOPE_FILAS)}
    filtro = {"created_at": f"gte.{desde}"} if desde else {}

    incidencias = datos.leer(
        "bot_errors", {"select": _SELECT_INCIDENCIAS, **comun, **filtro}
    )
    heredadas = datos.leer(
        "query_logs",
        {"select": "query,response,telegram_user_id,created_at",
         "source": "eq.error", **comun, **filtro},
    )
    return incidencias, heredadas


def resumen(incidencias: datos.Resultado, heredadas: datos.Resultado, *,
            top: int = 8) -> dict:
    """Las cifras. Delega en la función pura del script; aquí sólo se decide qué
    entra (una lectura fallida aporta cero filas, no una excepción)."""
    return agregar(
        incidencias.filas if incidencias.estado == datos.OK else [],
        heredadas.filas if heredadas.estado == datos.OK else [],
        top=top,
    )
