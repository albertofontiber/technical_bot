"""Tests for cross-brand intent detection in retriever.

Cross-brand queries (products from 2+ manufacturers) must be flagged so
the generator can refuse to infer compatibility — per Alberto's policy
logged in memory (``project_techbot.md`` Key decisions), cross-brand
reasoning is disallowed even with explicit caveats.

Coverage:
- classify_model_manufacturer: per-model pattern classifier (0 DB roundtrip).
- detect_query_manufacturers: aggregate detection (literal names + model codes).
- is_cross_brand_query: the decision function consumed by generator.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.retriever import (  # noqa: E402
    classify_model_manufacturer,
    detect_query_manufacturers,
    is_cross_brand_query,
)


# ---------------------------------------------------------------------------
# classify_model_manufacturer
# ---------------------------------------------------------------------------

class TestClassifyModelManufacturer:
    def test_detnov_cad(self):
        assert classify_model_manufacturer("CAD-150") == "Detnov"
        assert classify_model_manufacturer("CAD-250") == "Detnov"
        assert classify_model_manufacturer("CCD-103") == "Detnov"

    def test_asd_securiton(self):
        # ASD = Securiton (fabricante real). Detnov es su DISTRIBUIDOR. classify
        # pasó a catalog-first (#6): devuelve la marca real del dato, no la del
        # seed. (Detnov↔Securiton están en el mismo ecosistema → una query
        # "ASD Detnov" no se marca cross-brand; ver _ECOSYSTEM_OF.)
        assert classify_model_manufacturer("ASD535") == "Securiton"
        assert classify_model_manufacturer("ASD-533") == "Securiton"

    def test_detnov_other(self):
        assert classify_model_manufacturer("DGD-600") == "Detnov"
        assert classify_model_manufacturer("MAD-461") == "Detnov"
        assert classify_model_manufacturer("CALYPSO-II") == "Detnov"

    def test_notifier_afp(self):
        assert classify_model_manufacturer("AFP-200") == "Notifier"
        assert classify_model_manufacturer("AFP1010") == "Notifier"
        assert classify_model_manufacturer("AFP-400") == "Notifier"

    def test_notifier_id(self):
        assert classify_model_manufacturer("ID3000") == "Notifier"
        assert classify_model_manufacturer("ID2000") == "Notifier"
        assert classify_model_manufacturer("ID50/60") == "Notifier"

    def test_notifier_sdx(self):
        assert classify_model_manufacturer("SDX-751") == "Notifier"
        assert classify_model_manufacturer("SDX-751EM") == "Notifier"

    def test_notifier_other(self):
        assert classify_model_manufacturer("PEARL") == "Notifier"
        assert classify_model_manufacturer("INSPIRE") == "Notifier"
        assert classify_model_manufacturer("VESDA-E") == "Notifier"
        assert classify_model_manufacturer("AM2020") == "Notifier"

    def test_morley_zx(self):
        assert classify_model_manufacturer("ZXe") == "Morley"
        assert classify_model_manufacturer("ZXSe") == "Morley"
        assert classify_model_manufacturer("DXc") == "Morley"

    def test_morley_other(self):
        assert classify_model_manufacturer("UCIP") == "Morley"
        assert classify_model_manufacturer("F5000") == "Morley"
        assert classify_model_manufacturer("MI-DCZM") == "Morley"
        assert classify_model_manufacturer("ECO1000") == "Morley"

    def test_unknown_returns_none(self):
        assert classify_model_manufacturer("BOGUS-999") is None
        assert classify_model_manufacturer("") is None
        assert classify_model_manufacturer("FOO") is None

    def test_case_insensitive(self):
        assert classify_model_manufacturer("cad-250") == "Detnov"
        assert classify_model_manufacturer("zxe") == "Morley"
        assert classify_model_manufacturer("afp-200") == "Notifier"


# ---------------------------------------------------------------------------
# detect_query_manufacturers
# ---------------------------------------------------------------------------

class TestDetectQueryManufacturers:
    def test_empty_query(self):
        assert detect_query_manufacturers("") == set()

    def test_single_manufacturer_by_model(self):
        result = detect_query_manufacturers("¿cómo programo la CAD-250?")
        assert result == {"Detnov"}

    def test_single_manufacturer_by_name(self):
        result = detect_query_manufacturers("tengo un panel Notifier y no arranca")
        assert result == {"Notifier"}

    def test_two_manufacturers_by_model(self):
        # Canonical cross-brand: one Notifier detector + one Morley panel.
        result = detect_query_manufacturers(
            "¿puedo usar un detector SDX-751 con la central ZXe?"
        )
        assert result == {"Notifier", "Morley"}

    def test_two_manufacturers_by_name_and_model(self):
        result = detect_query_manufacturers(
            "¿la central Morley ZXe acepta detectores Detnov CCD-103?"
        )
        assert result == {"Morley", "Detnov"}

    def test_three_manufacturers(self):
        result = detect_query_manufacturers(
            "comparar AFP-200, CAD-250 y ZXe"
        )
        assert result == {"Notifier", "Detnov", "Morley"}

    def test_honeywell_with_subbrand_collapses(self):
        # User says "Honeywell Notifier AFP-200" — just Notifier.
        result = detect_query_manufacturers(
            "el panel Honeywell Notifier AFP-200"
        )
        assert result == {"Notifier"}

    def test_honeywell_alone_stays(self):
        result = detect_query_manufacturers("tengo una central Honeywell")
        assert result == {"Honeywell"}

    def test_case_insensitive_names(self):
        result = detect_query_manufacturers("un detector NOTIFIER y un panel morley")
        assert result == {"Notifier", "Morley"}


# ---------------------------------------------------------------------------
# is_cross_brand_query
# ---------------------------------------------------------------------------

class TestIsCrossBrandQuery:
    def test_single_brand_false(self):
        is_cb, mfrs = is_cross_brand_query("cómo conectar la CAD-250")
        assert is_cb is False
        assert mfrs == {"Detnov"}

    def test_no_brand_false(self):
        is_cb, mfrs = is_cross_brand_query("cómo funciona un sistema de incendios")
        assert is_cb is False
        assert mfrs == set()

    def test_two_brands_true(self):
        is_cb, mfrs = is_cross_brand_query(
            "¿SDX-751 de Notifier compatible con Morley ZXe?"
        )
        assert is_cb is True
        assert mfrs == {"Notifier", "Morley"}

    def test_cm001_canonical(self):
        # Direct from baseline_v1.yaml cm001
        query = "¿Puedo usar un detector Notifier SDX-751 con una central Morley ZXe?"
        is_cb, mfrs = is_cross_brand_query(query)
        assert is_cb is True
        assert mfrs == {"Notifier", "Morley"}

    def test_honeywell_and_detnov_is_cross_brand(self):
        # Honeywell (unspecified subbrand) + Detnov = cross-brand.
        is_cb, mfrs = is_cross_brand_query(
            "¿un detector Honeywell funciona con central Detnov CAD-250?"
        )
        assert is_cb is True
        assert "Detnov" in mfrs
        assert "Honeywell" in mfrs or "Notifier" in mfrs or "Morley" in mfrs
