"""Tests del registro de identidad de marca (Capa A — seam de Fase 2).

Garantizan que externalizar las tablas hardcodeadas de `metadata.py` a
`config/manufacturers/*.yaml` NO regresó las 28 marcas vivas:

  - **estructural**: el registry reproduce (al menos) las tablas originales
    capturadas en `tests/fixtures/_metadata_tables_golden.json`. Es SUBSET/
    SUBSECUENCIA, no igualdad, para permitir AÑADIR fabricantes nuevos sin romper
    (Capa B / 30+) mientras se garantiza que los originales no cambian ni se
    reordenan.
  - **comportamiento**: `detect_document_metadata` atribuye los casos
    representativos por marca igual que antes del refactor (una rama por cada
    fuente de señal: prefijo, brand-pattern, letter-model, filename-only).

La equivalencia exacta sobre los 1068 docs reales se verificó one-time con CERO
regresión (golden `tests/fixtures/_metadata_equivalence_golden.json`).
"""
import glob
import json
import os
import re

import pytest

from src.reingest import manufacturer_registry as reg
from src.reingest.metadata import detect_document_metadata

_FIXT = os.path.join(os.path.dirname(__file__), "fixtures", "_metadata_tables_golden.json")
_BEHAV = os.path.join(os.path.dirname(__file__), "fixtures", "_metadata_equivalence_golden.json")
_STORE = "data/extraction/agent_anthropic-sonnet-45"


@pytest.fixture(autouse=True)
def _restore_registry():
    """Restaura el registry desde el config real tras tests que lo monkeypatchean."""
    yield
    reg.reload()


@pytest.fixture(scope="module")
def golden():
    with open(_FIXT, encoding="utf-8") as f:
        return json.load(f)


# --- equivalencia estructural (las tablas originales no regresan) -------------

def test_brand_patterns_preserved_in_order(golden):
    """Cada brand_pattern original aparece en el registry en el MISMO orden
    relativo (subsecuencia) — el orden es semántico (primer match gana)."""
    want = [(p, mfr, distr) for p, _flags, mfr, distr in golden["brand_patterns"]]
    have = [(p.pattern, mfr, distr) for p, mfr, distr in reg.BRAND_PATTERNS]
    it = iter(have)
    assert all(w in it for w in want), \
        "brand_patterns originales perdidos o reordenados respecto al golden"


def test_prefixes_preserved(golden):
    for prefix, mfr in golden["main_mfr_by_prefix"].items():
        assert reg.MAIN_MFR_BY_PREFIX.get(prefix) == mfr, f"prefijo {prefix} regresó"


def test_letter_models_preserved(golden):
    for model, (mfr, distr) in golden["letter_models"].items():
        assert reg.LETTER_MODELS.get(model) == (mfr, distr), f"letter-model {model} regresó"


def test_filename_only_preserved(golden):
    have = {(p.pattern, mfr, distr) for p, mfr, distr in reg.FILENAME_ONLY_PATTERNS}
    for p, _flags, mfr, distr in golden["filename_only_patterns"]:
        assert (p, mfr, distr) in have


def test_folder_hints_preserved(golden):
    have = {(n, mfr, distr) for n, mfr, distr in reg.FOLDER_HINTS}
    for n, mfr, distr in golden["folder_hints"]:
        assert (n, mfr, distr) in have


def test_non_product_codes_preserved(golden):
    assert set(golden["non_product_codes"]) <= reg.NON_PRODUCT_CODES


def test_generic_model_re_preserved(golden):
    assert reg.GENERIC_MODEL_RE.pattern == golden["model_re"][0]


def test_registry_loads_core_brands():
    """Las marcas con prefijo propio y las distribuidas están cargadas."""
    assert {"CAD", "AFP", "ZX"} <= set(reg.MAIN_MFR_BY_PREFIX)
    mfrs = {mfr for _p, mfr, _d in reg.BRAND_PATTERNS}
    assert {"Securiton", "Xtralis", "Pfannenberg", "Spectrex"} <= mfrs


# --- equivalencia de comportamiento (una rama por fuente de señal) ------------

@pytest.mark.parametrize("filename,exp_model,exp_mfr,exp_distr", [
    ("CAD-150_manual_instalacion.pdf", "CAD-150", "Detnov", None),       # prefijo propio
    ("AM-8200_panel.pdf",              "AM-8200", "Notifier", None),     # prefijo propio
    ("ASD-535_datasheet.pdf",          "ASD-535", "Securiton", "Detnov"),  # brand-pattern + distr
    ("VESDA-VLF_installation.pdf",     "VESDA-VLF", "Xtralis", "Notifier"),
    ("Z728_datasheet.pdf",             "Z728", "Pepperl-Fuchs", "Detnov"),
    ("DS-741_sirena.pdf",              "DS-741", "Pfannenberg", "Detnov"),
    ("SGMI100_radio.pdf",              "SGMI100", "Argus Security", "Detnov"),
    ("40-40R_spectrex.pdf",            "40-40R", "Spectrex", "Detnov"),
    ("PEARL_config.pdf",               "PEARL", "Notifier", None),        # letter-model
    ("DXc_manual.pdf",                 "DXc", "Morley", None),            # letter-model
    ("B501_detector.pdf",              "B501", "Notifier", None),         # filename-only
])
def test_attribution_representative(filename, exp_model, exp_mfr, exp_distr):
    m = detect_document_metadata(filename, "")
    assert (m.product_model, m.manufacturer, m.distributor) == (exp_model, exp_mfr, exp_distr)


def test_reload_is_idempotent():
    """reload() vuelve a cargar desde disco sin alterar el contenido."""
    before = [(p.pattern, mfr, d) for p, mfr, d in reg.BRAND_PATTERNS]
    reg.reload()
    after = [(p.pattern, mfr, d) for p, mfr, d in reg.BRAND_PATTERNS]
    assert before == after


def test_registry_rejects_prefix_conflict(tmp_path, monkeypatch):
    """Dos YAML que asignan el MISMO prefijo a marcas distintas → error duro
    (no pisado silencioso). Esperable con OEM/relabeling a 30+ marcas."""
    d = tmp_path / "manufacturers"
    d.mkdir()
    (d / "a.yaml").write_text("manufacturer: A\ndistributor: null\nmodel_prefixes: [XX]\n", encoding="utf-8")
    (d / "b.yaml").write_text("manufacturer: B\ndistributor: null\nmodel_prefixes: [XX]\n", encoding="utf-8")
    monkeypatch.setattr(reg, "_CONFIG_DIR", str(d))
    with pytest.raises(ValueError, match="conflicto"):
        reg.reload()


@pytest.mark.skipif(not os.path.isdir(_STORE),
                    reason="corpus extraído no disponible (entorno sin data/extraction)")
def test_behavior_snapshot_full_corpus():
    """Gate FUERTE de no-regresión: la atribución de los 1068 docs reales == el
    golden congelado (estado post-Capa-A+B). Detecta cualquier deriva — incluida
    una que AÑADA atribución espuria a una marca viva (el agujero que el test
    estructural-subset no cubre, señalado por el dúo)."""
    from src.reingest.contextualize import full_document_text
    golden = json.load(open(_BEHAV, encoding="utf-8"))
    sha_re = re.compile(r"^[0-9a-f]{64}\.json$")
    diffs = []
    for p in glob.glob(os.path.join(_STORE, "*.json")):
        sha = os.path.basename(p)[:-5]
        if not sha_re.match(os.path.basename(p)) or sha not in golden:
            continue
        rec = json.load(open(p, encoding="utf-8"))
        m = detect_document_metadata(rec.get("source_path") or "", full_document_text(rec)[:8000])
        got = {"source_file": m.source_file, "manufacturer": m.manufacturer,
               "distributor": m.distributor, "product_model": m.product_model,
               "doc_type": m.doc_type, "category": m.category}
        if got != golden[sha]:
            diffs.append((sha[:12], golden[sha], got))
    assert not diffs, f"{len(diffs)} regresiones de atribución (muestra): {diffs[:5]}"
