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
)


def _patrones() -> list[str]:
    return [l.strip() for l in (REPO / ".vercelignore").read_text("utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def _incluido(ruta: str) -> bool:
    """¿Sobrevive `ruta` a .vercelignore? Semántica gitignore: gana el ÚLTIMO
    patrón que casa; un patrón de directorio arrastra todo lo que hay dentro."""
    incluido = True
    for patron in _patrones():
        negado = patron.startswith("!")
        cuerpo = patron[1:] if negado else patron
        cuerpo = cuerpo.lstrip("/").rstrip("/")
        if cuerpo == "*":                      # `/*` = todo lo de la raíz
            casa = True
        elif cuerpo.startswith("**/"):         # `**/__pycache__` y similares
            casa = cuerpo[3:] in Path(ruta).parts
        else:
            casa = ruta == cuerpo or ruta.startswith(cuerpo + "/")
        if casa:
            incluido = negado
    return incluido


def test_los_datos_del_panel_sobreviven_al_vercelignore():
    for ruta in DATOS_DEL_PANEL:
        assert (REPO / ruta).is_file(), f"{ruta} no existe en el repo"
        assert _incluido(ruta), (
            f"{ruta} lo lee el panel en runtime pero .vercelignore lo deja "
            f"FUERA del bundle: en Vercel fallaría al abrirlo. Re-inclúyelo "
            f"(añade `!/<directorio>`) o deja de leerlo desde la superficie.")


def test_el_comprobador_discrimina():
    """Control negativo: si el comprobador dijera «incluido» a todo, el test de
    arriba pasaría siempre y no protegería nada."""
    assert not _incluido("evals/gold_answers_v1.yaml")     # excluido por /*
    assert not _incluido("docs/PLAN_RAG_2026.md")          # excluido por /*
    assert _incluido("dashboard/explorador.py")            # re-incluido
    assert _incluido("src/clasificacion.py")               # re-incluido
    assert not _incluido("scripts/__pycache__/x.pyc")      # excluido dentro
