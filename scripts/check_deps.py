#!/usr/bin/env python3
"""CI gate: toda dependencia third-party importada en src/ debe estar declarada
en requirements.txt.

Análisis estático (AST) → caza imports *lazy* (dentro de funciones), que es
exactamente la clase del bug de `voyageai` que rompió producción en sesión 27:
un `import voyageai` dentro de una función nunca se dispara con un import-smoke,
solo el análisis estático lo ve. No necesita keys ni instalar el paquete.

Mapea módulo → distribución vía importlib.metadata (cuando el paquete está
instalado, p.ej. en CI tras `pip install -r requirements.txt`) con un fallback
estático para los nombres que difieren del módulo por si no está instalado.

Uso: python scripts/check_deps.py   (exit 1 si hay imports no declarados)
"""
from __future__ import annotations

import ast
import re
import sys
from importlib.metadata import packages_distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
REQUIREMENTS = ROOT / "requirements.txt"

# Paquetes cuyo nombre de distribución != nombre del módulo importado. Solo se
# usa como fallback si el paquete no está instalado en el entorno que corre el
# check (cuando sí lo está, importlib.metadata.packages_distributions resuelve
# el mapping automáticamente y esto es redundante).
KNOWN_MODULE_TO_DIST = {
    "fitz": "pymupdf",
    "PIL": "pillow",
    "dotenv": "python-dotenv",
    "telegram": "python-telegram-bot",
    "lingua": "lingua-language-detector",
    "yaml": "pyyaml",
    "cv2": "opencv-python",
}


def _norm(name: str) -> str:
    """Normaliza un nombre de distribución (PEP 503): lower + - _ . → '-'."""
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_distributions() -> set[str]:
    """Distribuciones declaradas en requirements.txt (normalizadas)."""
    dists: set[str] = set()
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        pkg = re.split(r"[<>=!~\[ ]", line, maxsplit=1)[0].strip()
        if pkg:
            dists.add(_norm(pkg))
    return dists


def imported_top_level_modules() -> dict[str, set[Path]]:
    """Módulos top-level importados en src/ → archivos donde aparecen."""
    mods: dict[str, set[Path]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.setdefault(alias.name.split(".")[0], set()).add(path)
            elif isinstance(node, ast.ImportFrom):
                # node.level > 0 son imports relativos (from .x) → first-party.
                if node.level == 0 and node.module:
                    mods.setdefault(node.module.split(".")[0], set()).add(path)
    return mods


def main() -> int:
    declared = declared_distributions()
    module_to_dists = packages_distributions()
    stdlib = sys.stdlib_module_names
    first_party = {"src"}

    missing: dict[str, set[Path]] = {}
    for mod, files in imported_top_level_modules().items():
        if mod in stdlib or mod in first_party:
            continue
        candidates = {_norm(d) for d in module_to_dists.get(mod, [])}
        if mod in KNOWN_MODULE_TO_DIST:
            candidates.add(_norm(KNOWN_MODULE_TO_DIST[mod]))
        candidates.add(_norm(mod))  # módulo == distribución (voyageai, anthropic…)
        if not (candidates & declared):
            missing[mod] = files

    if missing:
        print("FALLO: imports en src/ NO declarados en requirements.txt:\n")
        for mod, files in sorted(missing.items()):
            where = ", ".join(str(f.relative_to(ROOT)) for f in sorted(files))
            print(f"  - {mod}  ({where})")
        print("\nDeclara cada paquete en requirements.txt y vuelve a correr.")
        return 1

    print(
        f"OK: {len(declared)} dependencias en requirements.txt cubren todos "
        "los imports third-party de src/."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
