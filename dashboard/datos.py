# -*- coding: utf-8 -*-
"""Lectura SÓLO LECTURA de Supabase, y el mapa de las 7 vistas.

REGLA DE ORO DE ESTE FICHERO: **la clave de servicio no sale de este proceso**.
Se usa aquí para hablar con PostgREST y lo que sube a la capa de arriba son
filas ya leídas. No hay ninguna función que devuelva la clave, ni cabeceras, ni
la URL construida.

LA SEGUNDA REGLA: **este módulo no lanza**. Una caída de Supabase no puede
convertirse en una traza de error servida al navegador — ni por lo que se
enseñaría de la infraestructura, ni porque un panel que se cae entero cuando una
tarjeta no carga es peor que uno que dice qué le falta. Cada lectura devuelve un
`Resultado` con su ESTADO declarado, y la página pinta el estado. Los cinco son
los mismos que ya distinguen el CLI de invitaciones y el informe de errores —
mismo vocabulario, mismas acciones detrás:

    ok · vacio · tabla_ausente · sin_credenciales · error

`vacio` no es un fallo: una vista de motivos del 👎 sin filas significa que nadie
ha votado que no. `tabla_ausente` tampoco: significa «falta aplicar esa
migración», y el panel dice cuál.

LAS VISTAS NO SE RECALCULAN AQUÍ. DEC-183 dejó el trabajo hecho en SQL: siete
vistas versionadas, con `security_invoker` y sin permisos para `anon`. El panel
las LEE. Si una pregunta no la responde ninguna vista, la respuesta correcta es
decirlo —y proponer la vista— no escribir aquí una consulta paralela que mañana
diverja de la que mira el dueño desde el dashboard de Supabase.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

OK = "ok"
VACIO = "vacio"
TABLA_AUSENTE = "tabla_ausente"
SIN_CREDENCIALES = "sin_credenciales"
ERROR = "error"

TIMEOUT_S = 10.0

#: Códigos con que PostgREST dice «esa tabla/vista no existe». Mismo criterio
#: que `logging_db._tabla_ausente` y que el CLI: en este repo «la migración aún
#: no está aplicada» es un estado ESPERADO, no una anomalía.
_CODIGOS_AUSENTE = ("PGRST205", "PGRST106", "42P01")
#: Y el código con que Postgres dice «esa COLUMNA no existe» — el que produce
#: el `select` explícito de las vistas cuando una columna DECLARADA desaparece
#: o se renombra (s324j, v9 §7): se traduce a un detalle legible en vez de a un
#: «Supabase respondió 400» mudo, y la tarjeta lo dice.
_CODIGO_COLUMNA_AUSENTE = "42703"


@dataclass(frozen=True)
class Resultado:
    estado: str
    filas: list[dict] = field(default_factory=list)
    detalle: str = ""

    @property
    def hay_datos(self) -> bool:
        return self.estado == OK and bool(self.filas)


def _cabeceras() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    }


def hay_credenciales() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def leer(recurso: str, params: dict) -> Resultado:
    """Una lectura de PostgREST, con todos los fallos traducidos a estado."""
    if not hay_credenciales():
        return Resultado(SIN_CREDENCIALES,
                         detalle="faltan SUPABASE_URL / SUPABASE_SERVICE_KEY")
    try:
        with httpx.Client(timeout=TIMEOUT_S) as cliente:
            resp = cliente.get(
                f"{SUPABASE_URL}/rest/v1/{recurso}",
                headers=_cabeceras(),
                params=params,
            )
    except httpx.HTTPError as exc:
        # El tipo, no el mensaje: un mensaje de httpx puede llevar la URL entera
        # dentro, y la URL lleva el proyecto de Supabase.
        return Resultado(ERROR, detalle=f"no se pudo hablar con Supabase "
                                        f"({type(exc).__name__})")
    if resp.status_code in (400, 404):
        try:
            codigo = str((resp.json() or {}).get("code") or "")
        except Exception:                                        # noqa: BLE001
            codigo = ""
        if codigo in _CODIGOS_AUSENTE or resp.status_code == 404:
            return Resultado(TABLA_AUSENTE, detalle=recurso)
        if codigo == _CODIGO_COLUMNA_AUSENTE:
            return Resultado(ERROR, detalle=(
                f"{recurso} ya no tiene una columna declarada (¿renombrada o "
                f"retirada en una migración? — revisa datos.VISTAS)"))
    if resp.status_code >= 400:
        return Resultado(ERROR, detalle=f"Supabase respondió {resp.status_code}")
    try:
        filas = resp.json()
    except Exception:                                            # noqa: BLE001
        return Resultado(ERROR, detalle="respuesta ilegible")
    if not isinstance(filas, list):
        return Resultado(ERROR, detalle="respuesta con forma inesperada")
    return Resultado(OK if filas else VACIO, filas)


# ------------------------------------------------------------------- las vistas


@dataclass(frozen=True)
class Columna:
    nombre: str
    etiqueta: str
    #: texto · numero · ms · pct · fecha · dia
    formato: str = "texto"


@dataclass(frozen=True)
class Vista:
    clave: str
    titulo: str
    pregunta: str
    orden: str
    limite: int
    columnas: tuple[Columna, ...]
    #: (columna de etiqueta, columna de valor, unidad) para el gráfico, o None.
    grafico: tuple[str, str, str] | None = None
    #: Qué hay que hacer si la vista no existe.
    si_falta: str = ""


VISTAS: tuple[Vista, ...] = (
    Vista(
        clave="bot_health_daily",
        titulo="Uso diario",
        pregunta="¿Cuántas consultas al día, de cuánta gente, y cuánto tardó?",
        orden="dia.desc",
        limite=21,
        columnas=(
            Columna("dia", "Día", "dia"),
            Columna("consultas_rag", "Consultas", "numero"),
            Columna("usuarios_unicos", "Personas", "numero"),
            Columna("latencia_pipeline_p50_ms", "Latencia p50", "ms"),
            Columna("latencia_pipeline_p95_ms", "Latencia p95", "ms"),
            Columna("no_info_heuristica", "«No tengo info»", "numero"),
            Columna("errores_transporte", "Fallos de envío", "numero"),
            Columna("filas_error", "Errores", "numero"),
            Columna("bot_version", "Versión", "texto"),
        ),
        grafico=("dia", "consultas_rag", "consultas"),
    ),
    Vista(
        clave="bot_health_semanal",
        titulo="Uso semanal (tendencia)",
        pregunta="Lo mismo agregado por semana: ¿sube o baja?",
        orden="semana.desc",
        limite=14,
        columnas=(
            Columna("semana", "Semana", "dia"),
            Columna("consultas_rag", "Consultas", "numero"),
            Columna("usuarios_unicos", "Personas", "numero"),
            Columna("latencia_pipeline_p50_ms", "Latencia p50", "ms"),
            Columna("latencia_pipeline_p95_ms", "Latencia p95", "ms"),
            Columna("no_info_heuristica", "«No tengo info»", "numero"),
            Columna("errores_transporte", "Fallos de envío", "numero"),
            Columna("filas_error", "Errores", "numero"),
        ),
        grafico=("semana", "consultas_rag", "consultas"),
    ),
    Vista(
        clave="bot_uso_por_canal",
        titulo="Por dónde entra el uso",
        pregunta="¿Texto o voz, y qué ruta: RAG, aclaración o atajo?",
        orden="semana.desc",
        limite=40,
        columnas=(
            Columna("semana", "Semana", "dia"),
            Columna("canal", "Canal / ruta", "texto"),
            Columna("consultas", "Consultas", "numero"),
            Columna("personas", "Personas", "numero"),
        ),
    ),
    Vista(
        clave="bot_feedback_semanal",
        titulo="Pulgares arriba y abajo",
        pregunta="¿Cuánto feedback llega por semana y de qué signo?",
        orden="semana.desc",
        limite=14,
        columnas=(
            Columna("semana", "Semana", "dia"),
            Columna("votos_up", "👍", "numero"),
            Columna("votos_down", "👎", "numero"),
            Columna("votos_down_con_motivo", "👎 con motivo", "numero"),
            Columna("votos_con_comentario", "Con comentario", "numero"),
            Columna("marcados_utiles", "Marcados útiles", "numero"),
            Columna("feedback_libre", "Texto libre", "numero"),
        ),
    ),
    Vista(
        clave="bot_motivos_negativos",
        titulo="Por qué votan que no",
        pregunta="El desglose del 👎 por motivo — la cola de mejora del bot.",
        orden="semana.desc",
        limite=40,
        columnas=(
            Columna("semana", "Semana", "dia"),
            Columna("motivo", "Motivo", "texto"),
            Columna("votos", "Votos", "numero"),
        ),
        grafico=("motivo", "votos", "votos"),
    ),
    Vista(
        clave="salud_canal_retrieval_v1",
        titulo="Salud de la búsqueda",
        pregunta="¿Cuántos turnos respondieron con el pool DEGRADADO, y qué "
                 "canal falló?",
        orden="dia.desc",
        limite=21,
        columnas=(
            Columna("dia", "Día", "dia"),
            Columna("turnos_rag", "Turnos", "numero"),
            Columna("turnos_con_medida", "Con medida", "numero"),
            Columna("turnos_degradados", "Degradados", "numero"),
            Columna("pct_turnos_degradados", "% degradado", "pct"),
            Columna("fallos_vector", "Vector", "numero"),
            Columna("fallos_enunciados", "Enunciados", "numero"),
            Columna("fallos_hyq_table", "HyQ tabla", "numero"),
            Columna("fallos_hyq_hydrate", "HyQ hidratación", "numero"),
        ),
        grafico=("dia", "turnos_degradados", "turnos"),
    ),
    Vista(
        clave="salud_latencia_etapas_v1",
        titulo="Dónde se va el tiempo",
        pregunta="Mediana diaria por etapa: buscar, reordenar, cobertura, "
                 "generar y el resto.",
        orden="dia.desc",
        limite=21,
        columnas=(
            Columna("dia", "Día", "dia"),
            Columna("turnos_rag", "Turnos", "numero"),
            Columna("turnos_con_medida", "Con medida", "numero"),
            # DOS totales, y la etiqueta tiene que distinguirlos o la tabla
            # miente: `total_p50_ms` es la mediana de TODOS los turnos RAG del
            # día y `total_p50_ms_medidos` la de los turnos que además tienen
            # las 4 etapas medidas. La suma de etapas sólo cuadra contra el
            # segundo — compararla con el global mezclaría dos muestras
            # distintas (es un hallazgo del dúo de s315, escrito en su
            # migración; se respeta aquí en vez de re-descubrirlo).
            Columna("total_p50_ms_medidos", "Total p50 (medidos)", "ms"),
            Columna("total_p50_ms", "Total p50 (todos)", "ms"),
            Columna("total_p95_ms", "Total p95 (todos)", "ms"),
            Columna("retrieve_p50_ms", "Buscar", "ms"),
            Columna("rerank_p50_ms", "Reordenar", "ms"),
            Columna("coverage_p50_ms", "Cobertura", "ms"),
            Columna("generate_p50_ms", "Generar", "ms"),
            Columna("resto_p50_ms", "Resto", "ms"),
        ),
        si_falta="falta aplicar la migración s315 "
                 "(supabase/migration_proposals/20260809180000_s315_*.sql)",
    ),
)

VISTAS_POR_CLAVE = {v.clave: v for v in VISTAS}


def leer_vista(vista: Vista) -> Resultado:
    """`select` EXPLÍCITO desde las columnas declaradas — la decisión INVERSA a
    la original, invertida a conciencia al exponer el panel a internet (s324j,
    v9 §7). El `select=*` de antes existía para que una columna nueva se
    enseñara en vez de esconderse — correcto para un panel interno; con DGs y
    datos de personas detrás, la regla pasa a ser que NADA se pinta sin que
    alguien lo haya declarado en `VISTAS`. Los dos sentidos quedan cubiertos:
    una columna nueva de la vista NO aparece hasta declararla aquí; una
    declarada que la vista pierde produce un 42703 que `leer` traduce a un
    detalle legible y la tarjeta lo dice — ninguno de los dos casos tumba la
    página."""
    return leer(vista.clave, {
        "select": ",".join(c.nombre for c in vista.columnas),
        "order": vista.orden, "limit": str(vista.limite),
    })


# --------------------------------------------------------- salud del panel


def salud() -> dict:
    """¿Responde Supabase, y desde cuándo hay datos?

    Es la tarjeta que contesta «¿el panel está mintiendo?». Sin ella, una vista
    vacía por una caída se lee igual que una vista vacía porque no hubo tráfico
    — y son la misma pantalla con dos significados opuestos.
    """
    if not hay_credenciales():
        return {"estado": SIN_CREDENCIALES, "detalle":
                "el panel no tiene credenciales de Supabase configuradas"}
    arranque = time.monotonic()
    primera = leer("bot_health_daily",
                   {"select": "dia", "order": "dia.asc", "limit": "1"})
    ultima = leer("bot_health_daily",
                  {"select": "dia", "order": "dia.desc", "limit": "1"})
    tardanza_ms = int((time.monotonic() - arranque) * 1000)

    if primera.estado in (ERROR, SIN_CREDENCIALES):
        return {"estado": primera.estado, "detalle": primera.detalle,
                "tardanza_ms": tardanza_ms}
    if primera.estado == TABLA_AUSENTE:
        return {"estado": TABLA_AUSENTE,
                "detalle": "la vista bot_health_daily no existe todavía",
                "tardanza_ms": tardanza_ms}
    return {
        "estado": OK,
        "desde": (primera.filas[0].get("dia") if primera.filas else None),
        "hasta": (ultima.filas[0].get("dia") if ultima.filas else None),
        "tardanza_ms": tardanza_ms,
        "detalle": "",
    }
