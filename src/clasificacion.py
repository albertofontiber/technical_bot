# -*- coding: utf-8 -*-
"""Clasificación batch de preguntas (s326): la tabla derivada `query_clasificacion`.

QUÉ HACE. Recorre las filas de `query_logs` sin clasificar (o clasificadas con
una taxonomía anterior a la vigente) y escribe, por cada una: si el mensaje ES
UNA PREGUNTA (`es_pregunta`), la CATEGORÍA temática (taxonomía cerrada
`config/taxonomia_preguntas.yaml`), las MARCAS y MODELOS canónicos que toca, y
las menciones de marca que NO resuelven contra el catálogo (`marcas_libres` —
la señal de demanda no cubierta).

DOS EJES ORTOGONALES, no uno (s327, adjudicación de Alberto). «¿Pide algo?» y
«¿de qué tema?» son preguntas distintas: una queja sobre un catálogo mal
servido TIENE tema (catálogo) y NO es una pregunta. Mezclarlas en una sola
etiqueta obligaba a perder una de las dos. Las vistas de análisis filtran
`es_pregunta`; las no-preguntas se miran aparte, que es donde vive el feedback
en prosa. La regla del eje: interrogación ⇒ pregunta (código, $0, manda sobre
el LLM) · resto, inferido · **ante la duda, pregunta**.

DÓNDE CORRE, y dónde NO. Es un job BATCH: el script
`scripts/clasificar_preguntas.py` (manual: backfill y re-taxonomización) y el
seam `schedule_clasificacion` del worker (flag `CLASIFICADOR_PREGUNTAS`,
default off). JAMÁS corre en la ruta de respuesta del bot: una métrica que
nadie necesita en tiempo real no puede costarle latencia ni un fallo a un
técnico. Por eso mismo la tabla es DERIVADA (1:1 con `query_logs`, CASCADE):
borrarla y reconstruirla es siempre seguro, y re-taxonomizar = subir `version`
en el YAML y dejar que el job re-recorra el histórico.

DETERMINISTA PRIMERO, LLM EN EL RESIDUO:
  · rutas de atajo con la intención ya decidida por el plan de turno →
    categoría por REGLA ($0; hoy: `catalog_shortcut`);
  · modelos = `product_models` (lo que el bot RESOLVIÓ en el turno — la verdad
    del runtime, no una re-adivinación) + marca por catálogo + escaneo del
    texto contra los nombres canónicos de `documents` y los alias curados;
  · solo la CATEGORÍA de las filas restantes va al LLM (Haiku, taxonomía
    cerrada, JSON estricto). Un fallo del LLM deja la fila SIN clasificar (se
    reintenta en la siguiente corrida) — nunca se escribe basura con formato.

FRONTERA DE IMPORTS, deliberada: este módulo es RAÍZ y solo importa raíz — el
conocimiento de catálogo (nombres canónicos, marca-de-modelo, alias) NO es
suyo y se INYECTA como `Catalogo` desde los llamadores (el seam del bot y el
script, que sí pueden importar `rag`). Así la matriz de test_import_contract
(raiz→rag prohibido) ni se toca, y el núcleo se prueba sin red.

SESGO DECLARADO de `marcas`/`modelos`: miden lo que el bot ENTENDIÓ, no
siempre lo que el técnico quiso (una marca destrozada por el ASR no resuelve
— DEC-233). El hueco se enseña (`bot_marcas_sin_corpus_semanal` y el bucket
sin-marca), no se esconde.
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

import yaml

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from .http_pool import abierto

logger = logging.getLogger(__name__)

#: La taxonomía VIGENTE. La versión vive DENTRO del fichero (una sola fuente).
#: Cambiar los IDS exige además migración hermana que altere el CHECK; cambiar
#: solo descripciones, no. El v1 queda como recibo de las 109 primeras filas.
RUTA_TAXONOMIA = Path(__file__).resolve().parent.parent / "config" / \
    "taxonomia_preguntas.yaml"

#: Haiku 4.5: el escalón de coste correcto para elegir 1 etiqueta de 9. El
#: gate de acuerdo (propuesta §3.B.5) decide si se queda; subir de modelo sin
#: medir sería gastar por si acaso.
MODELO_LLM = "claude-haiku-4-5-20251001"
LLM_TIMEOUT_S = 15.0
LLM_MAX_TOKENS = 200

#: Tope de filas que una corrida examina (el seam del worker pasa el suyo).
CAP_DEFECTO = 500
_LOTE_ESCRITURA = 50

_COLUMNAS_FILA = "id,query,route,source,product_models,created_at"

PROMPT = """Eres el clasificador de mensajes de un asistente técnico de \
sistemas de protección contra incendios (PCI). Los usuarios son técnicos de \
mantenimiento e instalación.

Mensaje del técnico: «{q}»

Responde TRES cosas:

1. `es_pregunta`: ¿el mensaje PIDE algo al asistente (información, un \
procedimiento, un dato)? Cuenta como pregunta aunque no lleve signo de \
interrogación («dame el esquema de la CAD-250», «necesito el manual»). NO son \
preguntas: continuar la conversación respondiendo a lo que el asistente acaba \
de preguntar («programación principalmente», «sobre la 2X-AF1-FBS»), acusar \
recibo («ok, entendido») y comentar o quejarse de la respuesta anterior («esto \
incluye más productos que centrales de incendios»). **ANTE LA DUDA, true.**

2. `categoria`: EXACTAMENTE una de la lista, por el TEMA del mensaje — también \
si no es una pregunta (una queja sobre un catálogo mal servido es de tema \
catálogo). Si no trata de ningún tema, `otros`.

{categorias}

3. `marcas_mencionadas`: las MARCAS de fabricante de equipos PCI que aparezcan \
(solo fabricantes, no modelos; lista vacía si no hay).

Responde SOLO con un JSON en una línea, sin nada más:
{{"es_pregunta": true, "categoria": "<id>", "marcas_mencionadas": ["<marca>", ...]}}"""

#: Regla DETERMINISTA de Alberto, LITERAL: «no necesariamente una pregunta será
#: todo aquello que acabe en "?" (que estas sí serán)». Es decir: TERMINAR en
#: interrogación ⇒ pregunta, y punto; no terminar no dice nada (lo infiere el
#: LLM). La primera versión buscaba el signo en CUALQUIER posición y eso forzaba
#: a pregunta una queja como «la respuesta a "¿cuántos lazos?" estaba mal» —
#: contaminando justo el análisis que este eje viene a limpiar (hallazgo Sol
#: s327). Se aceptan cierres tipográficos y espacios después del signo.
#: HUECO DECLARADO (Fable, s327): «¿cuántos lazos» —apertura sin cierre, que el
#: teclado español del móvil produce a menudo— NO lo coge esta regla y cae al
#: LLM. No se amplía a propósito: la adjudicación de Alberto es sobre el signo
#: FINAL, y el sesgo «ante la duda, pregunta» ya cubre ese caso sin inventar
#: reglas que él no pidió.
_CIERRES_TRAS_INTERROGACION = ' \t\r\n"\'»)]}.…'


def termina_en_interrogacion(texto: str) -> bool:
    return (texto or "").strip().rstrip(
        _CIERRES_TRAS_INTERROGACION).endswith(("?", "？"))


class ClasificacionNoDisponible(RuntimeError):
    """Supabase no responde o rechaza: la corrida no puede ni empezar/seguir.
    (Un fallo POR FILA del LLM no es esto: se cuenta y se sigue.)"""


class Catalogo(NamedTuple):
    """El conocimiento de catálogo que los LLAMADORES inyectan (ver docstring
    del módulo): los nombres canónicos de `documents.manufacturer`, la marca de
    un modelo detectado, y el resolutor de alias coloquiales del runtime."""

    nombres: list[str]
    marca_de_modelo: Callable[[str], "str | None"]
    resolver_alias: Callable[[str], str]


@dataclass(frozen=True)
class Taxonomia:
    version: int
    #: (id, descripcion) en el orden del YAML.
    categorias: tuple[tuple[str, str], ...]
    #: ruta del plan de turno → categoría (clasificación por regla, $0).
    regla_rutas: dict[str, str] = field(default_factory=dict)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(c for c, _ in self.categorias)


def cargar_taxonomia(ruta: Path = RUTA_TAXONOMIA) -> Taxonomia:
    crudo = yaml.safe_load(ruta.read_text("utf-8"))
    categorias = tuple((c["id"], str(c["descripcion"]).strip())
                       for c in crudo["categorias"])
    ids = {c for c, _ in categorias}
    regla = dict(crudo.get("regla_rutas") or {})
    desconocidas = set(regla.values()) - ids
    if "otros" not in ids or desconocidas:
        raise ValueError(f"taxonomía inválida: falta 'otros' o regla_rutas "
                         f"apunta fuera de la lista ({sorted(desconocidas)})")
    return Taxonomia(version=int(crudo["version"]), categorias=categorias,
                     regla_rutas=regla)


# ------------------------------------------------------------ núcleo puro


def construir_prompt(taxonomia: Taxonomia, query: str) -> str:
    lineas = "\n".join(f"- {cid}: {desc}" for cid, desc in taxonomia.categorias)
    return PROMPT.format(categorias=lineas, q=query.strip()[:1500])


_MARCA_RE = re.compile(r"^[0-9a-zñç&/. _-]{2,40}$")


def _normalizar(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in plano if not unicodedata.combining(c)).lower()


def parsear_respuesta(raw: str, ids_validos: tuple[str, ...]
                      ) -> tuple[str, list[str], bool] | None:
    """JSON estricto → (categoria, marcas_mencionadas, es_pregunta), o None.

    ESTRICTO a propósito (espejo de `intent_llm.parse_decision`): una categoría
    fuera de la lista NO se degrada a 'otros' — se descarta la respuesta entera
    y la fila queda pendiente. 'otros' significa «el clasificador ELIGIÓ otros»,
    nunca «el clasificador se rompió»; mezclarlos dejaría las gráficas mintiendo
    en silencio.
    """
    texto = (raw or "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return None
    try:
        datos = json.loads(texto[inicio:fin + 1])
    except ValueError:
        return None
    if not isinstance(datos, dict):
        return None
    categoria = datos.get("categoria")
    if categoria not in ids_validos:
        return None
    crudas = datos.get("marcas_mencionadas")
    if not isinstance(crudas, list):
        crudas = []
    marcas: list[str] = []
    for m in crudas[:5]:
        limpia = _normalizar(str(m)).strip()
        if limpia and _MARCA_RE.match(limpia) and limpia not in marcas:
            marcas.append(limpia)
    # `es_pregunta` ausente o con forma rara → True: es el sesgo que pidió
    # Alberto («ante la duda, pregunta»), y aquí además cubre el caso de un
    # modelo que se salte el campo.
    crudo_es = datos.get("es_pregunta")
    es_pregunta = crudo_es if isinstance(crudo_es, bool) else True
    return str(categoria), marcas, es_pregunta


def indice_de_marcas(nombres_canonicos: list[str]) -> dict[str, str]:
    """token normalizado → nombre canónico de `documents.manufacturer`.

    Entra el nombre completo y además su PRIMER segmento (guion/espacio) si
    tiene ≥4 letras — es lo que un técnico teclea («morley» por «Morley-IAS»).
    Un token que apunte a DOS marcas distintas se descarta: ambigüedad no
    adivina.
    """
    indice: dict[str, str] = {}
    ambiguos: set[str] = set()

    def _apunta(token: str, canonico: str) -> None:
        if not token or token in ambiguos:
            return
        previo = indice.get(token)
        if previo is not None and previo != canonico:
            del indice[token]
            ambiguos.add(token)
            return
        indice[token] = canonico

    for nombre in nombres_canonicos:
        norm = _normalizar(nombre).strip()
        _apunta(norm, nombre)
        primero = re.split(r"[\s\-_/]+", norm, maxsplit=1)[0]
        if len(primero) >= 4:
            _apunta(primero, nombre)
    return indice


def escanear_marcas(texto: str, indice: dict[str, str]) -> list[str]:
    """Marcas canónicas mencionadas en el texto, por matching de token completo
    (con límite de palabra: «kidde» no salta dentro de otra palabra)."""
    encontradas: list[str] = []
    norm = _normalizar(texto)
    for token, canonico in indice.items():
        if canonico in encontradas:
            continue
        if re.search(rf"(?<![0-9a-z]){re.escape(token)}(?![0-9a-z])", norm):
            encontradas.append(canonico)
    return sorted(encontradas)


def canonicalizar_libres(libres: list[str], indice: dict[str, str],
                         resolver_alias: Callable[[str], str],
                         ) -> tuple[list[str], list[str]]:
    """Separa las menciones del LLM en (canónicas del corpus, realmente libres).

    Cada mención pasa por el alias curado del runtime y por el índice de
    nombres: lo que resuelve se muda a `marcas` (canónico); solo lo desconocido
    queda en `marcas_libres` — así `bot_marcas_sin_corpus_semanal` no acusa de
    «hueco» a una grafía coloquial de una marca que SÍ tenemos.
    """
    canonicas: list[str] = []
    restantes: list[str] = []
    for cruda in libres:
        resuelta = _normalizar(resolver_alias(cruda))
        canonico = indice.get(resuelta) or indice.get(cruda)
        if canonico:
            if canonico not in canonicas:
                canonicas.append(canonico)
        elif cruda not in restantes:
            restantes.append(cruda)
    return sorted(canonicas), restantes


def clasificar_fila(fila: dict, taxonomia: Taxonomia, indice: dict[str, str],
                    marca_de_modelo: Callable[[str], str | None],
                    resolver_alias: Callable[[str], str],
                    llm: Callable[[str], str] | None,
                    modelo_llm: str) -> dict | None:
    """Una fila de `query_logs` → la fila de `query_clasificacion`, o None si
    el LLM no dio una respuesta válida (la fila queda pendiente, se reintenta).

    Determinista SIEMPRE (marcas/modelos); el LLM solo decide la categoría del
    residuo y aporta menciones de marca — que se canonicalizan antes de
    escribir.
    """
    query = fila.get("query") or ""
    ruta = fila.get("route") or "rag"
    modelos = sorted({str(m).strip().upper()
                      for m in (fila.get("product_models") or []) if str(m).strip()})
    marcas = {m for m in (marca_de_modelo(m) for m in modelos) if m}
    marcas.update(escanear_marcas(query, indice))
    marcas_libres: list[str] = []

    categoria = taxonomia.regla_rutas.get(ruta)
    if categoria is not None:
        # Una ruta de atajo es siempre una PETICIÓN (el técnico pidió el
        # catálogo): es_pregunta True por construcción, sin LLM.
        origen, modelo, es_pregunta = "regla", None, True
    else:
        if llm is None:
            return None
        veredicto = parsear_respuesta(llm(construir_prompt(taxonomia, query)),
                                      taxonomia.ids)
        if veredicto is None:
            return None
        categoria, menciones, es_pregunta = veredicto
        extra, marcas_libres = canonicalizar_libres(menciones, indice,
                                                    resolver_alias)
        marcas.update(extra)
        origen, modelo = "llm", modelo_llm

    # La regla DURA de Alberto, aplicada DESPUÉS del LLM porque manda sobre él:
    # lo que lleva interrogación es pregunta, punto. Un modelo que dijera `false`
    # sobre «¿cuántos lazos tiene?» no puede ganarle a un signo de interrogación.
    if termina_en_interrogacion(query):
        es_pregunta = True

    return {
        "query_log_id": fila["id"],
        "categoria": categoria,
        "es_pregunta": es_pregunta,
        "taxonomia_version": taxonomia.version,
        "marcas": sorted(marcas),
        "modelos": modelos,
        "marcas_libres": marcas_libres,
        "origen": origen,
        "modelo_llm": modelo,
        "clasificado_at": datetime.now(timezone.utc).isoformat(),
    }


def es_pendiente(fila: dict, version: int) -> bool:
    """¿La fila necesita (re)clasificación con la taxonomía vigente?

    El embed 1:1 de PostgREST puede venir como objeto, lista o null según la
    versión del servidor — se aceptan las tres formas a propósito.
    """
    clasif = fila.get("query_clasificacion")
    if isinstance(clasif, list):
        clasif = clasif[0] if clasif else None
    if not isinstance(clasif, dict):
        return True
    try:
        return int(clasif.get("taxonomia_version") or 0) < version
    except (TypeError, ValueError):
        return True


# ------------------------------------------------------------------- I/O


def _cabeceras(extra: dict | None = None) -> dict:
    base = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    base.update(extra or {})
    return base


def _leer(recurso: str, params: dict) -> list:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        raise ClasificacionNoDisponible("faltan SUPABASE_URL / SUPABASE_SERVICE_KEY")
    try:
        with abierto(timeout=15.0) as cliente:
            resp = cliente.get(f"{SUPABASE_URL}/rest/v1/{recurso}",
                               headers=_cabeceras(), params=params)
    except Exception as exc:                                  # noqa: BLE001
        raise ClasificacionNoDisponible(
            f"no se pudo leer {recurso} ({type(exc).__name__})") from exc
    if resp.status_code >= 400:
        raise ClasificacionNoDisponible(f"{recurso} respondió {resp.status_code}")
    return resp.json()


def aplanar_vieja(fila: dict) -> dict | None:
    """Una fila de `query_clasificacion` con su padre embebido → la forma de
    fila de `query_logs` que consume `clasificar_fila` (el embed !inner puede
    venir como objeto o lista según la versión de PostgREST)."""
    padre = fila.get("query_logs")
    if isinstance(padre, list):
        padre = padre[0] if padre else None
    return padre if isinstance(padre, dict) else None


def leer_pendientes(version: int, cap: int) -> list[dict]:
    """Filas de `query_logs` a clasificar: DOS consultas dirigidas, no un
    barrido del histórico (hallazgo Sol r1 s326: el barrido más-antiguo-primero
    con tope de páginas dejaba las filas nuevas PERMANENTEMENTE fuera en cuanto
    el prefijo vigente superase el tope).

      1. sin NINGUNA clasificación — anti-join de PostgREST (`!left` +
         `query_clasificacion=is.null`): solo devuelve lo pendiente;
      2. con clasificación de una taxonomía ANTERIOR — desde la propia
         `query_clasificacion` (`taxonomia_version=lt.N`) con el padre !inner.

    Las dos se auto-drenan: cada fila clasificada sale de ambos conjuntos, así
    que la corrida siguiente CONTINÚA sola, sin cursor ni offset.
    """
    pendientes = [
        fila for fila in _leer("query_logs", {
            "select": f"{_COLUMNAS_FILA},query_clasificacion!left(taxonomia_version)",
            "query_clasificacion": "is.null",
            "source": "neq.error",
            "order": "created_at.asc",
            "limit": str(cap),
        })
        if es_pendiente(fila, version)                # cinturón, no la puerta
    ]
    hueco = cap - len(pendientes)
    if hueco <= 0:
        return pendientes[:cap]
    viejas = _leer("query_clasificacion", {
        "select": f"taxonomia_version,query_logs!inner({_COLUMNAS_FILA})",
        "taxonomia_version": f"lt.{version}",
        "query_logs.source": "neq.error",
        "order": "clasificado_at.asc",
        "limit": str(hueco),
    })
    for fila in viejas:
        padre = aplanar_vieja(fila)
        if padre is not None:
            # La marca decide el VERBO de escritura (incidente del backfill,
            # 19-ago): una fila que YA tiene clasificación se re-escribe con
            # PATCH (UPDATE de columnas, jamás la PK); una nueva, con INSERT.
            # El upsert merge-duplicates de PostgREST quedó descartado: su
            # DO UPDATE SET incluye la PK y exigiría GRANT UPDATE(query_log_id)
            # — exactamente el permiso que el trinquete del gate ACL prohíbe.
            padre["_ya_clasificada"] = True
            pendientes.append(padre)
    return pendientes


def escribir_clasificaciones(nuevas: list[dict],
                             existentes: list[dict] | None = None) -> int:
    """Re-clasificar SOBRESCRIBE, nunca apila — con el VERBO que el GRANT
    permite (la PK jamás se re-escribe):

      · `nuevas` → INSERT en lotes con `resolution=ignore-duplicates`: si una
        corrida concurrente ya insertó la fila, la nuestra se ignora — ambas
        eran de la taxonomía vigente, el resultado es equivalente;
      · `existentes` (marcadas por `leer_pendientes`) → PATCH por fila con el
        payload SIN `query_log_id` (UPDATE de columnas concedido; mover una
        clasificación a otra pregunta no es una operación que exista).
    """
    escritas = 0
    for i in range(0, len(nuevas), _LOTE_ESCRITURA):
        lote = nuevas[i:i + _LOTE_ESCRITURA]
        try:
            with abierto(timeout=15.0) as cliente:
                resp = cliente.post(
                    f"{SUPABASE_URL}/rest/v1/query_clasificacion",
                    headers=_cabeceras({
                        "Prefer": "resolution=ignore-duplicates,return=minimal",
                        "Content-Type": "application/json",
                    }),
                    params={"on_conflict": "query_log_id"},
                    content=json.dumps(lote),
                )
        except Exception as exc:                              # noqa: BLE001
            raise ClasificacionNoDisponible(
                f"no se pudo escribir query_clasificacion "
                f"({type(exc).__name__})") from exc
        if resp.status_code >= 400:
            raise ClasificacionNoDisponible(
                f"query_clasificacion respondió {resp.status_code}: "
                f"{resp.text[:200]}")
        escritas += len(lote)
    for fila in (existentes or []):
        cuerpo = {k: v for k, v in fila.items() if k != "query_log_id"}
        try:
            with abierto(timeout=15.0) as cliente:
                resp = cliente.patch(
                    f"{SUPABASE_URL}/rest/v1/query_clasificacion",
                    headers=_cabeceras({
                        "Prefer": "return=minimal",
                        "Content-Type": "application/json",
                    }),
                    params={"query_log_id": f"eq.{fila['query_log_id']}"},
                    content=json.dumps(cuerpo),
                )
        except Exception as exc:                              # noqa: BLE001
            raise ClasificacionNoDisponible(
                f"no se pudo actualizar query_clasificacion "
                f"({type(exc).__name__})") from exc
        if resp.status_code >= 400:
            raise ClasificacionNoDisponible(
                f"query_clasificacion (update) respondió {resp.status_code}: "
                f"{resp.text[:200]}")
        escritas += 1
    return escritas


def construir_llm(api_key: str, modelo: str = MODELO_LLM) -> Callable[[str], str]:
    """El llamador del LLM, con la config del INTENT_LLM que ya pagó su diseño:
    timeout corto y max_retries=1 (batch: un reintento sí compensa; en la ruta
    de respuesta no lo haría)."""
    import anthropic

    cliente = anthropic.Anthropic(api_key=api_key, timeout=LLM_TIMEOUT_S,
                                  max_retries=1)

    def _llamar(prompt: str) -> str:
        msg = cliente.messages.create(
            model=modelo, max_tokens=LLM_MAX_TOKENS, temperature=0,
            messages=[{"role": "user", "content": prompt}])
        _llamar.tokens_entrada += getattr(msg.usage, "input_tokens", 0) or 0
        _llamar.tokens_salida += getattr(msg.usage, "output_tokens", 0) or 0
        return "".join(b.text for b in msg.content
                       if getattr(b, "type", "") == "text")

    _llamar.tokens_entrada = 0
    _llamar.tokens_salida = 0
    return _llamar


def correr_pendientes(cap: int = CAP_DEFECTO, *, catalogo: Catalogo,
                      api_key: str | None = None,
                      modelo: str = MODELO_LLM, dry_run: bool = False,
                      llm: Callable[[str], str] | None = None) -> dict:
    """Una corrida completa: leer pendientes → clasificar → escribir → recibo.

    El recibo dice lo que PASÓ, no lo que se intentó: `llm_fallos` son filas que
    quedaron pendientes (respuesta inválida o excepción por fila) y volverán a
    entrar en la siguiente corrida.
    """
    taxonomia = cargar_taxonomia()
    indice = indice_de_marcas(catalogo.nombres)
    pendientes = leer_pendientes(taxonomia.version, cap)

    if llm is None and api_key:
        llm = construir_llm(api_key, modelo)

    recibo = {
        "taxonomia_version": taxonomia.version,
        "examinadas": len(pendientes),
        "por_regla": 0,
        "por_llm": 0,
        "llm_fallos": 0,
        "sin_llm": 0,
        "escritas": 0,
        "dry_run": dry_run,
        "modelo_llm": modelo if llm is not None else None,
        "tokens_entrada": 0,
        "tokens_salida": 0,
        "duracion_s": 0.0,
    }
    arranque = time.monotonic()
    nuevas: list[dict] = []
    existentes: list[dict] = []
    for fila in pendientes:
        ruta = fila.get("route") or "rag"
        if taxonomia.regla_rutas.get(ruta) is None and llm is None:
            recibo["sin_llm"] += 1
            continue
        try:
            clasif = clasificar_fila(
                fila, taxonomia, indice,
                marca_de_modelo=catalogo.marca_de_modelo,
                resolver_alias=catalogo.resolver_alias,
                llm=llm, modelo_llm=modelo)
        except ClasificacionNoDisponible:
            raise
        except Exception:                                     # noqa: BLE001
            logger.warning("clasificación falló para %s", fila.get("id"),
                           exc_info=True)
            clasif = None
        if clasif is None:
            recibo["llm_fallos"] += 1
            continue
        recibo["por_regla" if clasif["origen"] == "regla" else "por_llm"] += 1
        (existentes if fila.get("_ya_clasificada") else nuevas).append(clasif)

    if (nuevas or existentes) and not dry_run:
        recibo["escritas"] = escribir_clasificaciones(nuevas, existentes)
    if llm is not None:
        recibo["tokens_entrada"] = getattr(llm, "tokens_entrada", 0)
        recibo["tokens_salida"] = getattr(llm, "tokens_salida", 0)
    recibo["duracion_s"] = round(time.monotonic() - arranque, 2)
    return recibo
