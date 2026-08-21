# -*- coding: utf-8 -*-
"""s326b — los FICHEROS DE DATOS que el panel lee en runtime viajan al bundle.

Hermano de `test_s324j_panel_requirements` (que cubre los paquetes de terceros)
y nace del mismo tipo de fallo, una clase más callada: `.vercelignore` excluye
todo (`/*`) y re-incluye a mano lo que el panel necesita. Cuando el Explorador
empezó a leer `config/taxonomia_preguntas.yaml` (s326b), ese directorio NO
estaba re-incluido — así que en producción `cargar_taxonomia()` habría fallado,
el fail-open habría dejado el desplegable de categorías VACÍO y nadie lo habría
notado: sin excepción, sin 500 y sin log.

La regla que se fija: **todo fichero de datos que la superficie desplegada abre
en runtime tiene que sobrevivir a `.vercelignore`**. Se comprueba con la misma
semántica que aplica Vercel (gitignore-style, último patrón que casa gana), no
con un `fnmatch` ingenuo — que es justo lo que dio un falso «está incluido» al
diagnosticar esto.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Ficheros de datos que la superficie del panel abre en runtime. Al añadir uno
#: nuevo se apunta aquí; si no está re-incluido en .vercelignore, rojo.
DATOS_DEL_PANEL = (
    "config/taxonomia_preguntas.yaml",   # dashboard/explorador.py → src.clasificacion
    # s331 — los SIETE del catálogo gobernado: `dashboard/catalogo.py` (la Wiki
    # de modelos) llama a `catalog_store.load()`, que los abre todos. Omitir uno
    # daría un catálogo parcial SIN error: los alias desaparecerían del buscador,
    # o los paraguas de la ficha, y la página seguiría pintándose entera.
    "data/catalog/products.jsonl",
    "data/catalog/aliases.jsonl",
    "data/catalog/umbrellas.jsonl",
    "data/catalog/homonyms.jsonl",
    "data/catalog/relations.jsonl",
    "data/catalog/doc_map.jsonl",
    "data/catalog/docrel.jsonl",
)


def _patrones() -> list[str]:
    return [l.strip() for l in (REPO / ".vercelignore").read_text("utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def _casa(cuerpo: str, ruta: str) -> bool:
    if cuerpo == "*":                          # `/*` = todo lo de la raíz
        return True
    if cuerpo.startswith("**/"):               # `**/__pycache__` y similares
        return cuerpo[3:] in Path(ruta).parts
    if cuerpo.endswith("/*"):
        # `/data/*` casa con los HIJOS DIRECTOS de `data`. Basta con comprobar
        # que la ruta cuelga de ahí: si el hijo directo queda excluido, todo lo
        # que hay debajo también, y de eso se encarga el recorrido de padres de
        # `_incluido`.
        return ruta.startswith(cuerpo[:-2] + "/")
    return ruta == cuerpo or ruta.startswith(cuerpo + "/")


def _incluido_plano(ruta: str) -> bool:
    """Último patrón que casa gana, SIN la regla del directorio padre."""
    incluido = True
    for patron in _patrones():
        negado = patron.startswith("!")
        cuerpo = (patron[1:] if negado else patron).lstrip("/").rstrip("/")
        if _casa(cuerpo, ruta):
            incluido = negado
    return incluido


def _incluido(ruta: str) -> bool:
    """¿Sobrevive `ruta` a .vercelignore?

    Semántica gitignore COMPLETA, y la palabra que importa es «completa»: gana el
    último patrón que casa, **pero no se puede re-incluir un fichero si un
    directorio padre suyo está excluido**. Esa segunda regla es la que faltaba, y
    su ausencia costó un fallo real (s331d): con `/*` excluyendo `/data`, el
    patrón `!/data/catalog` NO re-incluye nada —git lo ignora— y sin embargo la
    versión plana de este comprobador decía «incluido». La Wiki de modelos salió
    a producción con 0 modelos y este test en verde.

    Así que se comprueba directorio a directorio, de la raíz hacia abajo: si
    algún padre queda excluido, el hijo no se salva por mucho `!` que lleve.
    """
    partes = Path(ruta).parts
    for i in range(1, len(partes)):
        if not _incluido_plano("/".join(partes[:i])):
            return False
    return _incluido_plano(ruta)


def test_los_datos_del_panel_sobreviven_al_vercelignore():
    for ruta in DATOS_DEL_PANEL:
        assert (REPO / ruta).is_file(), f"{ruta} no existe en el repo"
        assert _incluido(ruta), (
            f"{ruta} lo lee el panel en runtime pero .vercelignore lo deja "
            f"FUERA del bundle: en Vercel fallaría al abrirlo. Re-inclúyelo "
            f"(añade `!/<directorio>`) o deja de leerlo desde la superficie.")


def test_el_comprobador_aplica_la_regla_del_directorio_padre():
    """EL control que faltaba, escrito contra el fallo REAL de s331d.

    `!/data/catalog` con `/data` excluido por `/*` NO re-incluye nada: es la
    regla de gitignore que el comprobador plano se saltaba, y por eso este test
    daba verde mientras la página salía vacía en producción. Se fija con un
    `.vercelignore` sintético para que la comprobación no dependa del fichero
    real (que ya está arreglado y no volvería a destapar el fallo)."""
    import textwrap

    global _patrones
    original = _patrones
    try:
        _patrones = lambda: ["/*", "!/config", "!/data/catalog"]      # noqa: E731
        assert not _incluido("data/catalog/products.jsonl"), (
            "la re-inclusión de un hijo con el padre excluido NO funciona en "
            "gitignore; si este comprobador dice que sí, miente igual que mintió "
            "en s331d")
        assert _incluido("config/taxonomia_preguntas.yaml")

        _patrones = lambda: ["/*", "!/data", "/data/*", "!/data/catalog"]  # noqa: E731
        assert _incluido("data/catalog/products.jsonl"), (
            "con el padre re-incluido y vuelto a vaciar, el subdirectorio SÍ entra")
        assert not _incluido("data/gold/preguntas.yaml")
    finally:
        _patrones = original


def test_el_comprobador_discrimina():
    """Control negativo: si el comprobador dijera «incluido» a todo, el test de
    arriba pasaría siempre y no protegería nada."""
    assert not _incluido("evals/gold_answers_v1.yaml")     # excluido por /*
    assert not _incluido("docs/PLAN_RAG_2026.md")          # excluido por /*
    assert _incluido("dashboard/explorador.py")            # re-incluido
    assert _incluido("src/clasificacion.py")               # re-incluido
    assert not _incluido("scripts/__pycache__/x.pyc")      # excluido dentro
    assert _incluido("data/catalog/products.jsonl")        # re-incluido (s331)
    # …y el resto de `data/` NO viaja: la re-inclusión es del subdirectorio del
    # catálogo, no del árbol de datos entero (que lleva corpus y volcados).
    assert not _incluido("data/gold/preguntas.yaml")
