# -*- coding: utf-8 -*-
"""s324j — `api/requirements.txt` es la clausura EXACTA de la superficie del panel.

Por qué existe: el primer deploy real a Vercel (19-ago, commit da0a9d7) murió con
«Total bundle size (541.43 MB) exceeds the maximum function size (500 MB)» — el
builder instalaba el requirements.txt de la RAÍZ (el del bot entero). El arreglo
es `api/requirements.txt` (el builder Python de Vercel prefiere el que vive junto
al entrypoint), con SOLO lo que la superficie desplegada importa de verdad.

Este test impide las dos derivas de esa clase:
  · alguien importa un tercero nuevo en `api/`/`dashboard/` (o en los módulos
    puente de `src`/`scripts` que ya arrastra) sin declararlo → la función
    cascaría en frío en Vercel — aquí se pone rojo ANTES;
  · alguien apila dependencias en `api/requirements.txt` que la superficie no
    usa → el bundle re-engorda hacia el límite en silencio.
La clausura se calcula ESTÁTICA (parseo de imports con BFS sobre los módulos
locales alcanzables desde `api/index.py`): sin red, sin importar nada pesado.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent

#: import-name → nombre en PyPI (solo hace falta mapear los que difieren).
PYPI = {"dotenv": "python-dotenv"}

_IMPORT_RE = re.compile(r"^(?:import|from)\s+([A-Za-z0-9_.]+)", re.MULTILINE)


def _modulo_a_fichero(modulo: str) -> Path | None:
    """Resuelve `src.bot.access` → src/bot/access.py (o __init__.py), si es local."""
    base = REPO / Path(*modulo.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _clausura_de_terceros(semillas: list[Path]) -> set[str]:
    stdlib = set(sys.stdlib_module_names)
    vistos: set[Path] = set()
    cola = list(semillas)
    terceros: set[str] = set()
    while cola:
        fichero = cola.pop()
        if fichero in vistos:
            continue
        vistos.add(fichero)
        texto = fichero.read_text(encoding="utf-8")
        for modulo in _IMPORT_RE.findall(texto):
            raiz = modulo.split(".")[0]
            if raiz == "" or raiz in stdlib or raiz == "__future__":
                continue
            if modulo.startswith("."):        # relativos: mismo paquete, ya en BFS
                continue
            local = _modulo_a_fichero(modulo)
            if local is None and raiz in ("dashboard", "api", "src", "scripts"):
                # `from . import x` dentro de paquetes locales resuelve por el
                # paquete; barre el paquete raíz entero para no perder ramas.
                paquete = REPO / raiz
                local = paquete / "__init__.py" if (paquete / "__init__.py").is_file() else None
            if local is not None:
                cola.append(local)
                # Un `from src.bot import access` importa el submódulo aunque el
                # fichero resuelto sea el __init__: añade también el submódulo.
                sub = _modulo_a_fichero(modulo) or local
                cola.append(sub)
            elif raiz not in ("dashboard", "api", "src", "scripts"):
                terceros.add(raiz)
    return terceros


def _semillas_del_panel() -> list[Path]:
    ficheros = [REPO / "api" / "index.py"]
    ficheros += sorted((REPO / "dashboard").glob("*.py"))
    return ficheros


def test_api_requirements_es_la_clausura_exacta():
    requeridos = {PYPI.get(t, t) for t in _clausura_de_terceros(_semillas_del_panel())}
    declarados = {
        re.split(r"[<>=\[]", linea.strip())[0]
        for linea in (REPO / "api" / "requirements.txt").read_text("utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    }
    assert requeridos == declarados, (
        f"superficie importa {sorted(requeridos)} pero api/requirements.txt "
        f"declara {sorted(declarados)} — o falta declarar un tercero nuevo "
        f"(la función cascaría en frío) o sobra uno (el bundle re-engorda)"
    )


def test_los_pins_no_divergen_de_la_raiz():
    """Una sola fuente de versiones: cada línea de api/requirements.txt debe
    existir LITERAL en el requirements.txt raíz."""
    raiz = {
        linea.strip()
        for linea in (REPO / "requirements.txt").read_text("utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    }
    del_panel = [
        linea.strip()
        for linea in (REPO / "api" / "requirements.txt").read_text("utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]
    for linea in del_panel:
        assert linea in raiz, (
            f"{linea!r} no está literal en requirements.txt raíz — "
            f"dos fuentes de versión para el mismo paquete"
        )
