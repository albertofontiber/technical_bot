"""Regression tests for MODEL_PATTERN + model_to_imatch_pattern.

These cover the TECH_DEBT #11 fix: the retriever's product-model detection
must work for Notifier (AFP, ID, AM, PEARL, INSPIRE, Sistema 5000) and Morley
(ZXe, ZXSe, DXc) in addition to the Detnov patterns that already worked, AND
must produce a PostgreSQL regex that tolerates separator variations while
rejecting digit extensions (ID-200 must not match ID2000).
"""
import re
import pytest

from src.rag.retriever import (
    MODEL_PATTERN,
    extract_product_models,
    model_to_imatch_pattern,
)
from src.rag.catalog import normkey as _normkey


# ----------------------------------------------------------------------------
# MODEL_PATTERN — extraction from natural-language Spanish queries
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected", [
    # --- Detnov (regression: must still work) ---
    ("En la Detnov CAD-250, ¿cómo se entra al menú?", ["CAD-250"]),
    ("El detector ASD535 da alarma intermitente", ["ASD535"]),
    ("Conectar baterías en la CAD-150", ["CAD-150"]),
    ("Tensión del DGD-600", ["DGD-600"]),
    ("Desactivar detector en CCD-103", ["CCD-103"]),
    ("¿Cómo sustituyo la batería de la ADW535?", ["ADW535"]),

    # --- Notifier centrales (new coverage) ---
    ("En la Notifier ID3000 programar coincidencia", ["ID3000"]),
    ("La Notifier AFP-400 muestra Tierra", ["AFP-400"]),
    ("¿Cuántos lazos soporta la AM2020/AFP1010?", ["AM2020", "AFP1010"]),
    ("Módulo de aislamiento en un lazo ID2000", ["ID2000"]),
    ("Retardo de alarma principal en la PEARL", ["PEARL"]),
    ("En la INSPIRE configurar contraseñas nivel 2 y 3", ["INSPIRE"]),
    ("Migrar de AFP-200 a ID3000", ["AFP-200", "ID3000"]),
    ("¿Cómo programo el sistema 5000?", ["Sistema 5000"]),
    ("Verificar VESDA-E VEP", ["VESDA-E VEP"]),
    ("La base B501 es compatible?", ["B501"]),

    # --- Morley centrales (new coverage) ---
    ("Resistencia de fin de línea en Morley ZXe", ["ZXe"]),
    ("En la Morley DXc añadir un detector", ["DXc"]),
    ("En la Morley RP1r tras descargar extinción", ["RP1r"]),
    ("Reemplazar ZXe convencional por ZXSe", ["ZXe", "ZXSe"]),

    # --- Cross-manual (both a Notifier and a Morley in the same query) ---
    ("¿Puedo usar un detector Notifier SDX-751 con una central Morley ZXe?",
     ["SDX-751", "ZXe"]),

    # --- Ambiguous forms: should NOT extract when the token is bare ---
    ("¿Cómo programo el panel?", []),              # no model
    ("Mi central da error al arrancar", []),       # no model
    ("¿Cuál es el consumo del ASD?", []),          # ASD alone is ambiguous (series)
])
def test_extract_product_models(query, expected):
    got = extract_product_models(query)
    # El detector devuelve la forma CANÓNICA del catálogo (p.ej. "DXc",
    # "VESDA-E-VEP", "AM2020"), no la query en mayúsculas. Comparamos por clave
    # canónica (fold + sin separadores) para validar QUÉ modelos y en qué ORDEN
    # se detectan, ignorando mayúsculas/separadores que downstream (imatch,
    # model_to_imatch_pattern) trata como equivalentes.
    assert [_normkey(g) for g in got] == [_normkey(e) for e in expected], (
        f"Query {query!r}\n  expected: {expected}\n  got: {got}"
    )


# ----------------------------------------------------------------------------
# model_to_imatch_pattern — the PostgreSQL regex emitted for PostgREST imatch
# ----------------------------------------------------------------------------

def _pg_regex_compile(pattern: str) -> re.Pattern:
    """Approximate PostgreSQL ARE regex by rewriting \\y → \\b for Python."""
    # Python supports \b as word-boundary. PostgreSQL uses \y. Rewrite for test.
    py = pattern.replace(r"\y", r"\b")
    return re.compile(py, re.IGNORECASE)


@pytest.mark.parametrize("query_token,stored_value,should_match", [
    # --- AFP/AM family — compound DB values must match ---
    ("AFP1010", "AM2020/AFP1010", True),
    ("AFP1010", "AM2020 and AFP1010", True),
    ("AFP1010", "AFP1010", True),
    ("AFP-1010", "AM2020/AFP1010", True),           # dashed query → compound store
    ("AM2020", "AM2020", True),
    ("AM2020", "AM2020/AFP1010", True),
    ("AM-8200", "AM-8200", True),
    ("AM-8200", "AM 8200G", True),                   # separator variance
    ("AM2020", "AM8200", False),                     # different number

    # --- ID family — digit extension must NOT match ---
    ("ID3000", "ID3000", True),
    ("ID3000", "ID3000 Repetidor", True),
    ("ID3000", "ID30000", False),                    # digit extension rejected
    ("ID-200", "ID-200", True),
    ("ID-200", "ID200", True),                       # separator variance
    ("ID-200", "ID2000", False),                     # critical: NOT a digit extension
    ("ID50", "ID50", True),
    ("ID50", "ID50/60", True),
    ("ID50", "ID500", False),

    # --- AFP — letter suffixes OK, digit extension not ---
    ("AFP-200", "AFP-200", True),
    ("AFP-200", "AFP-200E", True),                   # letter suffix accepted
    ("AFP-200", "AFP-2000", False),                  # digit extension rejected
    ("AFP-400", "AFP-300/AFP-400", True),            # matches at internal boundary

    # --- Sistema 5000 ---
    ("Sistema 5000", "Sistema 5000", True),
    ("Sistema 5000", "Sistema5000", True),           # separator optional
    ("System 5000", "Sistema 5000", False),          # different word

    # --- Morley centrales ---
    ("ZXe", "ZXe", True),
    ("ZXe", "ZXSe", False),                          # different model
    ("ZXe", "ZXr", False),
    ("ZXSe", "ZXSe", True),
    ("DXc", "DXc", True),

    # --- Detnov regression ---
    ("MAD-567", "MAD-567", True),
    ("CAD-150", "CAD-150", True),
    ("CAD-150", "CAD-150-8", True),                  # compound suffix still matched
])
def test_model_to_imatch_pattern(query_token, stored_value, should_match):
    pattern = model_to_imatch_pattern(query_token)
    assert pattern, f"Empty pattern for {query_token!r}"
    py_re = _pg_regex_compile(pattern)
    matched = bool(py_re.search(stored_value))
    assert matched == should_match, (
        f"query={query_token!r} pattern={pattern!r} stored={stored_value!r}\n"
        f"  expected match={should_match}, got={matched}"
    )


def test_model_to_imatch_pattern_empty_input():
    assert model_to_imatch_pattern("") == ""
    assert model_to_imatch_pattern("   ") == ""
    assert model_to_imatch_pattern(" - - ") == ""


def test_model_to_imatch_pattern_escaping():
    """Metacharacters in the input must be escaped before being emitted."""
    # A model with a literal '.' or '+' should be escaped (defense in depth —
    # our real MODEL_PATTERN doesn't emit those, but the helper must be safe).
    p = model_to_imatch_pattern("FOO+BAR.BAZ")
    # After escape, '+' and '.' are literal, not regex metacharacters.
    py_re = _pg_regex_compile(p)
    assert py_re.search("FOO+BAR.BAZ") is not None
    assert py_re.search("FOOXBARYBAZ") is None       # would match if . weren't escaped
