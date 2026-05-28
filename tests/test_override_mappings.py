"""Tests: verifican que cada PDF descargado tiene overrides de modelo y categoría.

Este test protege contra una clase entera de bugs silenciosos:
si se descarga un nuevo PDF (o uno existente se renombra) y no tiene
entrada en los dicts de override, volvería a la detección por keywords
y a menudo acabaría con `product_model="unknown"` o categoría incorrecta.

Ejecutar:
    python -m pytest tests/test_override_mappings.py -v
o sin pytest:
    python tests/test_override_mappings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ingestion.chunker import (  # noqa: E402
    MORLEY_SOURCE_FILE_TO_CATEGORY,
    MORLEY_SOURCE_FILE_TO_MODEL,
    NOTIFIER_SOURCE_FILE_TO_MODEL,
    detect_product_model,
)

# (folder_name, model_dict, category_dict_or_None, label)
MANUFACTURERS = [
    ("Manuales_Morley", MORLEY_SOURCE_FILE_TO_MODEL, MORLEY_SOURCE_FILE_TO_CATEGORY, "Morley"),
    ("Manuales_Notifier", NOTIFIER_SOURCE_FILE_TO_MODEL, None, "Notifier"),
]

# Categorías EN 54 canónicas — debe coincidir con CATEGORY_KEYWORDS en chunker.py
CANONICAL_CATEGORIES = {
    "Centrales de incendios",
    "Detectores puntuales",
    "Detectores lineales",
    "Detectores de aspiración",
    "Pulsadores",
    "Sirenas y balizas",
    "Módulos de lazo",
    "Fuentes de alimentación",
    "Software y programación",
    "Accesorios y cableado",
}


def _pdf_stems(folder: Path) -> list[str]:
    return sorted(p.stem for p in folder.glob("*.pdf"))


def test_morley_all_pdfs_resolve_to_known_model() -> None:
    """Cada PDF de Morley debe producir product_model != 'unknown'.

    Esto cubre tanto los overrides del dict como la detección por regex
    sobre el filename — lo que importa es el outcome, no el mecanismo.
    """
    folder = ROOT / "Manuales_Morley"
    if not folder.is_dir():
        return  # corpus local, no está en el repo (igual que _no_orphan_overrides)
    unknown = []
    for pdf in folder.glob("*.pdf"):
        model = detect_product_model(text="", filename=pdf.name, manufacturer="Morley")
        if model == "unknown":
            unknown.append(pdf.name)
    assert not unknown, (
        f"{len(unknown)} PDFs Morley con product_model='unknown' "
        "(añadir al dict MORLEY_SOURCE_FILE_TO_MODEL):\n"
        + "\n".join(f"  - {s}" for s in unknown)
    )


def test_morley_all_pdfs_have_category_override() -> None:
    folder = ROOT / "Manuales_Morley"
    if not folder.is_dir():
        return  # corpus local, no está en el repo (igual que _no_orphan_overrides)
    stems = _pdf_stems(folder)
    missing = [s for s in stems if s not in MORLEY_SOURCE_FILE_TO_CATEGORY]
    assert not missing, (
        f"{len(missing)} PDFs Morley sin entrada en MORLEY_SOURCE_FILE_TO_CATEGORY:\n"
        + "\n".join(f"  - {s}" for s in missing)
    )


def test_morley_category_values_are_canonical() -> None:
    """Todas las categorías asignadas deben estar en la taxonomía EN 54 unificada."""
    bad = {
        stem: cat
        for stem, cat in MORLEY_SOURCE_FILE_TO_CATEGORY.items()
        if cat not in CANONICAL_CATEGORIES
    }
    assert not bad, (
        f"{len(bad)} entradas con categoría no canónica (typo o falta de normalización):\n"
        + "\n".join(f"  - {s}: {c!r}" for s, c in bad.items())
    )


def test_morley_no_orphan_overrides() -> None:
    """Detecta overrides que apuntan a PDFs que ya no existen (limpieza)."""
    folder = ROOT / "Manuales_Morley"
    if not folder.is_dir():
        return
    stems = set(_pdf_stems(folder))
    orphan_model = [k for k in MORLEY_SOURCE_FILE_TO_MODEL if k not in stems]
    orphan_cat = [k for k in MORLEY_SOURCE_FILE_TO_CATEGORY if k not in stems]
    assert not orphan_model, (
        f"{len(orphan_model)} entradas en MORLEY_SOURCE_FILE_TO_MODEL sin PDF correspondiente:\n"
        + "\n".join(f"  - {s}" for s in orphan_model)
    )
    assert not orphan_cat, (
        f"{len(orphan_cat)} entradas en MORLEY_SOURCE_FILE_TO_CATEGORY sin PDF correspondiente:\n"
        + "\n".join(f"  - {s}" for s in orphan_cat)
    )


if __name__ == "__main__":
    # Fallback runner sin pytest
    failed = 0
    tests = [
        test_morley_all_pdfs_resolve_to_known_model,
        test_morley_all_pdfs_have_category_override,
        test_morley_category_values_are_canonical,
        test_morley_no_orphan_overrides,
    ]
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}")
            print(f"       {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
