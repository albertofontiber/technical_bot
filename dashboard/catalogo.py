# -*- coding: utf-8 -*-
"""La **Wiki de modelos**: qué modelos conoce el bot y con qué manuales responde.

QUÉ ES Y POR QUÉ EXISTE. La pidió Alberto en s331, anotando la fila
`notifier:lt-200` del packet de adjudicación: «deberíamos tener un listado de
modelos activos para poder validar y ajustar familias y modelos específicos,
que sea la "Wiki" de modelos del bot… para que los DGs puedan ver los modelos
que tenemos, los docs asociados a esos modelos, y poder revisar rápido».

El pedido nace de un dolor MEDIDO: la adjudicación del catálogo se venía
haciendo sobre un fichero markdown de 488 líneas que hay que leer entero para
contestar «¿qué modelos hay de esta familia?». Esta página contesta esa
pregunta en un clic, y contesta también las dos que el markdown nunca podía:
**qué modelos no tienen ningún manual** y **qué manuales no atestan a nadie**.

DE DÓNDE SALEN LOS DATOS — y por qué NO de Supabase. La fuente es el **catálogo
gobernado** (`data/catalog/*.jsonl`), que es REPO-FIRST por diseño (D1 de
`catalog_store`): viaja con el código, cambia sólo con un deploy y es la MISMA
estructura que el bot consulta en runtime para resolver un modelo. Leerlo aquí
significa que la Wiki no puede divergir de lo que el bot hace — no hay una
segunda copia que mantener. La única lectura remota es el **estado de los
documentos** (`documents.status`), y sólo en la ficha de un modelo: saber si un
manual sigue activo es dato vivo, no dato de repo.

Consecuencia de packaging que hay que recordar: `data/catalog/` tiene que estar
re-incluido en `.vercelignore` o esta página sale VACÍA en producción sin un
solo error — la clase exacta del fallo de `config/` en s326b. Lo vigila
`tests/test_s326_datos_del_panel_en_el_bundle.py`.

LA REGLA DE LOS FILTROS, y su única excepción. El resto del panel usa filtros
CERRADOS porque cada parámetro acaba en un filtro de PostgREST (`errores.py`,
`explorador.py`). Aquí `marca`, `estado` y `docs` siguen esa regla al pie. `q`
es la excepción DELIBERADA y es segura por una razón concreta: el catálogo se
filtra **en memoria, en este proceso**, con un `in` de Python sobre listas ya
cargadas — `q` no viaja a ninguna consulta, ni a PostgREST ni a SQL. Se recorta
a `_Q_MAX` caracteres para que no se pueda pedir una página con un texto
absurdo, y se pinta escapado como todo lo demás.

LO QUE ESTA PÁGINA NO HACE: escribir. «Ajustar» un modelo (darlo de alta,
retirarlo, mover un doc_map) pasa por la puerta gobernada
(`scripts/s324_lote_firmado_writer.py`) con dry-run, censo del radio de
explosión y recibo — un botón aquí se saltaría esa medida. La Wiki es el sitio
donde se VE el problema; el lote firmado sigue siendo el sitio donde se
arregla.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src.rag.catalog_store import CATALOG_DIR, load, norm_token

from . import datos

#: Estados ofrecidos. `consumibles` = lo que el bot PUEDE usar hoy para
#: responder (activo y no-candidate): es el defecto porque es la pregunta que
#: un DG hace de verdad («¿tenéis este modelo?»).
#:
#: `redirects` es una clase APARTE y no un subtipo de «retirado»: son 81 filas
#: que apuntan a OTRO id, casi todas CRUZANDO de marca (`morley:b501ap` →
#: `systemsensor:b501ap`, `detnov:140kit160` → `firebeam:140kit160`). El bot SÍ
#: las consume —resuelven a su destino, `catalog_store._consumable` sigue el
#: redirect— pero no son modelos distintos que listar: son el mismo equipo bajo
#: otra marca. Meterlas en «consumibles» duplicaría cada rebrand en la lista;
#: meterlas en «retirados» diría que no funcionan, y funcionan. Van a su propia
#: vista, que es además LA vista útil del OEM.
ESTADOS = ("consumibles", "candidates", "redirects", "retirados", "todos")
ESTADO_DEFECTO = "consumibles"

#: Filtro por cobertura documental. `sin` es el que descubre agujeros: un
#: modelo que el catálogo conoce y del que no tenemos ni un manual.
DOCS = ("todos", "con", "sin")
DOCS_DEFECTO = "todos"

#: Tope de filas de la lista. Mismo criterio que el Explorador: el panel busca
#: lectura y patrones; por encima de esto la respuesta correcta es afinar el
#: filtro, no una página más larga.
TOPE_FILAS = 300

#: Recorte del texto libre. No es una validación de seguridad (no la necesita:
#: `q` no sale de este proceso) — es una cota de cordura.
_Q_MAX = 60


@dataclass(frozen=True)
class Filtros:
    marca: str | None
    estado: str
    docs: str
    q: str


@dataclass(frozen=True)
class Modelo:
    """Una fila de la lista. Todo lo que se pinta, ya resuelto."""
    id: str
    marca: str
    canonico: str
    familia: str
    categoria: str
    estado: str
    candidate: bool
    vendido_bajo: tuple[str, ...]
    n_docs: int
    n_alias: int
    #: Sólo en las filas `redirect`: el id al que resuelven.
    redirige_a: str = ""


@dataclass(frozen=True)
class Ficha:
    """La ficha de UN modelo: lo de la fila + sus alias, sus documentos, sus
    relaciones y los paraguas que lo contienen."""
    modelo: Modelo
    alias: tuple[str, ...]
    documentos: tuple[tuple[str, str, str], ...]   # (source_file, rol, document_id)
    relaciones: tuple[tuple[str, str, str], ...]   # (tipo, otro_id, dirección)
    paraguas: tuple[str, ...]
    provenance: str


@dataclass(frozen=True)
class Indice:
    """El catálogo ya digerido para pintar. Se construye UNA vez por proceso."""
    modelos: tuple[Modelo, ...]
    marcas: tuple[str, ...]
    por_id: dict
    alias_por_id: dict
    docs_por_id: dict
    relaciones_por_id: dict
    paraguas_por_id: dict
    provenance_por_id: dict
    #: Documentos del doc_map que no atestan a NINGÚN id consumible. Es el otro
    #: agujero simétrico al de «modelo sin docs», y no se ve en ningún sitio más.
    docs_huerfanos: tuple[tuple[str, int], ...]
    leido: bool


def _vacio(leido: bool) -> Indice:
    return Indice((), (), {}, {}, {}, {}, {}, {}, (), leido)


@lru_cache(maxsize=1)
def indice() -> Indice:
    """El catálogo gobernado, digerido. Cacheado: es un fichero del repo, sólo
    cambia con un deploy.

    FAIL-OPEN a un índice vacío marcado `leido=False` si el catálogo no está o
    no parsea — la regla del panel es que este módulo NO lanza. La página
    distingue «no hay modelos» de «no pude leer el catálogo», que es la lección
    de `marcas_disponibles` (hallazgo Fable r1, s326): esconder la diferencia
    convierte un fallo de despliegue en una pantalla plausible.
    """
    try:
        cat = load(CATALOG_DIR)
    except Exception:                                        # noqa: BLE001
        return _vacio(False)

    alias_por_id: dict[str, list[str]] = {}
    for a in cat.aliases:
        alias_por_id.setdefault(a.get("id", ""), []).append(str(a.get("alias", "")))

    docs_por_id: dict[str, list[tuple[str, str, str]]] = {}
    for fila in cat.doc_map:
        fuente = str(fila.get("source_file") or "")
        did = str(fila.get("document_id") or "")
        for e in fila.get("entries", []):
            docs_por_id.setdefault(str(e.get("id", "")), []).append(
                (fuente, str(e.get("role") or "primary"), did))

    relaciones_por_id: dict[str, list[tuple[str, str, str]]] = {}
    for r in cat.relations:
        origen, destino = str(r.get("origen", "")), str(r.get("destino", ""))
        tipo = str(r.get("tipo", ""))
        relaciones_por_id.setdefault(origen, []).append((tipo, destino, "→"))
        relaciones_por_id.setdefault(destino, []).append((tipo, origen, "←"))

    paraguas_por_id: dict[str, list[str]] = {}
    for u in cat.umbrellas:
        for pid in u.get("ids", []):
            paraguas_por_id.setdefault(str(pid), []).append(str(u.get("termino", "")))

    modelos, provenance = [], {}
    for pid, p in cat.products.items():
        marca = pid.split(":", 1)[0] if ":" in pid else "(sin marca)"
        provenance[pid] = str(p.get("provenance") or "")
        modelos.append(Modelo(
            id=pid,
            marca=marca,
            canonico=str(p.get("canonical_model") or pid),
            familia=str(p.get("familia") or ""),
            categoria=str(p.get("categoria") or ""),
            estado=str(p.get("estado") or "activo"),
            candidate=bool(p.get("candidate")),
            vendido_bajo=tuple(str(v) for v in (p.get("vendido_bajo") or ())),
            n_docs=len(docs_por_id.get(pid, ())),
            n_alias=len(alias_por_id.get(pid, ())),
            redirige_a=str(p.get("redirect_to") or ""),
        ))
    modelos.sort(key=lambda m: (m.marca, norm_token(m.canonico)))

    consumibles = {m.id for m in modelos if _clase(m) == "consumibles"}
    huerfanos: dict[str, int] = {}
    for fila in cat.doc_map:
        ids = [str(e.get("id", "")) for e in fila.get("entries", [])]
        if ids and not any(i in consumibles for i in ids):
            huerfanos[str(fila.get("source_file") or "")] = len(ids)

    return Indice(
        modelos=tuple(modelos),
        marcas=tuple(sorted({m.marca for m in modelos})),
        por_id={m.id: m for m in modelos},
        alias_por_id={k: tuple(sorted(v)) for k, v in alias_por_id.items()},
        docs_por_id={k: tuple(sorted(v)) for k, v in docs_por_id.items()},
        relaciones_por_id={k: tuple(v) for k, v in relaciones_por_id.items()},
        paraguas_por_id={k: tuple(sorted(v)) for k, v in paraguas_por_id.items()},
        provenance_por_id=provenance,
        docs_huerfanos=tuple(sorted(huerfanos.items())),
        leido=True,
    )


def _clase(m: Modelo) -> str:
    """La clase de estado con que se filtra.

    El invariante que la página no puede romper es de UN SOLO SENTIDO y es el
    que importa: **nada que la Wiki llame `consumibles` puede ser algo que el
    resolver rechace** (`catalog_store._consumable`) — decir «sí tenemos ese
    modelo» de algo con lo que el bot no puede responder es el peor fallo
    posible en una pantalla que existe para adjudicar. Lo fija
    `tests/test_s331_wiki_modelos.py`.

    El sentido contrario SÍ diverge, a propósito: los `redirect` son
    consumibles para el resolver (los sigue hasta su destino) y aquí son clase
    propia, porque como FILA de una lista de modelos son el mismo equipo
    contado dos veces.
    """
    if m.estado == "redirect":
        return "redirects"
    if m.estado == "retirado":
        return "retirados"
    return "candidates" if m.candidate else "consumibles"


def normalizar(consulta: dict, *, marcas: tuple[str, ...]) -> Filtros:
    """Los parámetros de la URL → filtros. `marca`, `estado` y `docs` caen a su
    defecto si no están en su lista cerrada; `q` se recorta."""
    def _uno(nombre: str) -> str:
        valores = consulta.get(nombre) or [""]
        return str(valores[0])

    marca, estado, docs = _uno("marca"), _uno("estado"), _uno("docs")
    return Filtros(
        marca=marca if marca in marcas else None,
        estado=estado if estado in ESTADOS else ESTADO_DEFECTO,
        docs=docs if docs in DOCS else DOCS_DEFECTO,
        q=_uno("q").strip()[:_Q_MAX],
    )


def buscar(filtros: Filtros) -> tuple[tuple[Modelo, ...], int]:
    """(las filas a pintar, cuántas casaban en total). El total se devuelve
    aparte del recorte para poder DECIR que se recortó: una lista muda de 300
    parece la respuesta completa y no lo es."""
    ind = indice()
    q = norm_token(filtros.q) if filtros.q else ""
    salida = []
    for m in ind.modelos:
        if filtros.marca and m.marca != filtros.marca:
            continue
        if filtros.estado != "todos" and _clase(m) != filtros.estado:
            continue
        if filtros.docs == "con" and not m.n_docs:
            continue
        if filtros.docs == "sin" and m.n_docs:
            continue
        if q and not _casa(m, q, ind):
            continue
        salida.append(m)
    return tuple(salida[:TOPE_FILAS]), len(salida)


def _casa(m: Modelo, q: str, ind: Indice) -> bool:
    """¿El texto libre casa con este modelo? Busca en el id, el nombre
    canónico, la familia Y LOS ALIAS — buscar «minilaser» tiene que encontrar
    el modelo cuyo canónico es un código de pedido, que es justo el caso que
    Alberto señaló en `kidde:zlsm-md` («9-30501-KID» en portada y «Kidde
    MiniLaser» justo debajo)."""
    if q in norm_token(m.id) or q in norm_token(m.canonico) or (
            m.familia and q in norm_token(m.familia)):
        return True
    return any(q in norm_token(a) for a in ind.alias_por_id.get(m.id, ()))


def ficha(pid: str) -> Ficha | None:
    """La ficha de un modelo, o None si el id no existe. El id llega de la URL:
    NO se parsea ni se interpola en ninguna consulta — se busca en el dict del
    catálogo, así que un id inventado da None y la página responde 404."""
    ind = indice()
    m = ind.por_id.get(pid)
    if m is None:
        return None
    return Ficha(
        modelo=m,
        alias=ind.alias_por_id.get(pid, ()),
        documentos=ind.docs_por_id.get(pid, ()),
        relaciones=ind.relaciones_por_id.get(pid, ()),
        paraguas=ind.paraguas_por_id.get(pid, ()),
        provenance=ind.provenance_por_id.get(pid, ""),
    )


def estado_de_documentos(ids: tuple[str, ...]) -> dict[str, str]:
    """`document_id` → `status`, para los documentos de UNA ficha. Es la única
    lectura remota de esta página y es deliberadamente pequeña (los docs de un
    modelo, no la tabla): saber si un manual sigue activo es dato vivo.

    FAIL-OPEN a `{}` — sin el estado la ficha se pinta igual, sólo que sin la
    marca de «retirado». Un panel que se cae porque Supabase tarda sería peor
    que un panel que enseña el catálogo sin adornos."""
    ids = tuple(i for i in ids if i)
    if not ids:
        return {}
    # `in.(…)` con los ids ENTRECOMILLADOS: vienen del catálogo del repo, no
    # del teclado de nadie, pero un uuid mal escrito en un jsonl no puede
    # romper la sintaxis del filtro (misma cautela que `explorador.parametros`).
    lista = ",".join('"%s"' % i.replace("\\", "\\\\").replace('"', '\\"')
                     for i in ids[:100])
    res = datos.leer("documents", {"select": "id,status", "id": f"in.({lista})",
                                   "limit": "100"})
    if res.estado != datos.OK:
        return {}
    return {str(f.get("id")): str(f.get("status") or "") for f in res.filas}


def resumen() -> dict:
    """Las cifras de portada de la Wiki. Se calculan del índice ya cargado — no
    hay una segunda pasada por el catálogo."""
    ind = indice()
    consum = [m for m in ind.modelos if _clase(m) == "consumibles"]
    return {
        "modelos": len(consum),
        "marcas": len({m.marca for m in consum}),
        "sin_docs": sum(1 for m in consum if not m.n_docs),
        "candidates": sum(1 for m in ind.modelos if _clase(m) == "candidates"),
        "redirects": sum(1 for m in ind.modelos if _clase(m) == "redirects"),
        "docs_huerfanos": len(ind.docs_huerfanos),
        "leido": ind.leido,
    }
