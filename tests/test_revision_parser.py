"""Tests for src/ingestion/revision_parser.py.

All cases here come from REAL filenames observed in the Notifier + Detnov
corpus. Do not invent synthetic examples — if a new pattern shows up in a
future manufacturer, add the actual filename here (with its source manufacturer
noted in a comment) rather than a simplified version.

Run with:
    pytest tests/test_revision_parser.py -v
"""
from __future__ import annotations

from datetime import date

import pytest

from src.ingestion.revision_parser import (
    RevisionInfo,
    detect_date,
    detect_doc_type,
    detect_language,
    detect_revision,
    normalize_family,
    parse_revision,
)


# ---------------------------------------------------------------------------
# Revision detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,expected",
    [
        # Notifier — "RV N DD-MM-YYYY"
        ("AM 8100-manual instalacion RV 3 30-01-2025.pdf", "3"),
        ("AM 8200N-manual instalacion RV 4 30-01-2025.pdf", "4"),
        ("AM 8200G manual instalacion Rv 3.pdf", "3"),
        ("AM-LCD manual de instalacion y usuario RV 0.pdf", "0"),
        # Notifier — "rev N DD-MM-YYYY"
        ("AM-8100 manual de usuario y programacion rev 4 30-10-2024.pdf", "Rev 4"),
        ("AM-8200N manual de usuario y programacion rev 3 30-10-2024.pdf", "Rev 3"),
        ("MANUAL DETECTOR DE GAS VGN _SP rev 0.pdf", "Rev 0"),
        # Detnov — "Rev. A" / "Rev B" / "RevB"
        ("170019 02012012 ETIQUETA INSTRUCCIONES EXTINCION SUPRA REV A .pdf", "Rev A"),
        ("1998M0901_FS24X_ES-AR54-10_ES-AR_RevB_17July2015.pdf", "Rev B"),
        # Notifier — "ISS N_Rev N"
        ("2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook.pdf", "Iss 1 Rev 4"),
        # Notifier — "issue N_MM-YYYY"
        ("4188-1122-ES issue 4_04-2025_Cyb.pdf", "4"),
        ("4188-1124-ES issue 6_01-2026_To.pdf", "6"),
        ("HOP-138-8ES  issue 6_01-2026_Co.pdf", "6"),
        # Notifier — "rvNN" concatenated
        ("HLSI-MA-025_rv03 Guia Rapida NFS_Supra.pdf", "3"),
        ("HLSI-MN-025_rv05 NFS Supra.pdf", "5"),
        ("HLSI-MA-025_rv03 Guide rapide NFS_Supra_XP__FR version 03.pdf", "3"),
        # Notifier — "v2.26", "v4", "V04"
        ("HONEYWELL-H-GTW-ESP-2.26 Instalador.pdf", None),  # version in filename but not prefixed by v/V separator
        ("HLSI-MN-025-I_NFS Supra Series v05.pdf", "v5"),
        ("GT-HLSI-1102 ITAC 2_1  25-02-2025 v4.pdf", "v4"),
        # Notifier — "R1.35" firmware version
        ("Actualizacion del firmware de INSPIRE a R1.35.pdf", "R1.35"),
        # MADT/MCDT — trailing _NN style
        ("MADT015_03.pdf", "03"),
        ("MADT190_14.pdf", "14"),
        ("MADT155_08.pdf", "08"),
        # MADT/MCDT — trailing single letter (Rev A style)
        ("MCDT156_A.pdf", "Rev A"),
        # None expected
        ("MADT606.pdf", None),
        ("MADT765.pdf", None),
        ("HLSI-MN-192_UCIP.pdf", None),
        ("IRK-2E.pdf", None),
    ],
)
def test_detect_revision(filename: str, expected: str | None):
    stem = filename.replace(".pdf", "").replace(".PDF", "")
    assert detect_revision(stem) == expected


# ---------------------------------------------------------------------------
# Date detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,expected",
    [
        ("AM 8100-manual instalacion RV 3 30-01-2025.pdf", date(2025, 1, 30)),
        ("AM-8100 manual de usuario y programacion rev 4 30-10-2024.pdf", date(2024, 10, 30)),
        ("1998M0901_FS24X_ES-AR54-10_ES-AR_RevB_17July2015.pdf", date(2015, 7, 17)),
        ("170019 02012012 ETIQUETA INSTRUCCIONES EXTINCION SUPRA REV A .pdf", date(2012, 1, 2)),
        ("4188-1122-ES issue 4_04-2025_Cyb.pdf", date(2025, 4, 1)),
        ("4188-1124-ES issue 6_01-2026_To.pdf", date(2026, 1, 1)),
        ("GT-HLSI-1102 ITAC 2_1  25-02-2025 v4.pdf", date(2025, 2, 25)),
        # No date
        ("MADT015_03.pdf", None),
        ("HLSI-MN-192_UCIP.pdf", None),
    ],
)
def test_detect_date(filename: str, expected: date | None):
    assert detect_date(filename) == expected


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,expected",
    [
        ("D700-3-Sp.pdf", "es"),
        ("ASD Cold Environments_SP.pdf", "es"),
        ("D 1036-1_M700KAC_SP.pdf", "es"),
        ("997-670-005-3_Operating_ES.pdf", "es"),
        ("33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores.pdf", "es"),
        ("HLSI-MA-192_05 Quick Start Guide UCIP GPRS_GB.pdf", "en"),
        ("997-670-007-3_Operating_PT.pdf", "pt"),
        ("HSR-E24_Multi.pdf", "multi"),
        ("08895_04-multiling.pdf", "multi"),
        ("HLSI-MN-025-I_NFS Supra Series FR 25_03_2014 Sbr.pdf", "fr"),
    ],
)
def test_detect_language(filename: str, expected: str | None):
    assert detect_language(filename) == expected


# ---------------------------------------------------------------------------
# Doc type detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,expected",
    [
        ("AM 8200N-manual instalacion RV 4 30-01-2025.pdf", "instalacion"),
        ("AM-8100 manual de usuario y programacion rev 4 30-10-2024.pdf", "guia_rapida"),
        # ^ NOTE: "guia_rapida" check runs before "usuario"; but this filename has neither
        #   "guia rapida" nor "quick start"... let's fix the expectation below.
    ],
)
def test_detect_doc_type_placeholder(filename, expected):
    # Placeholder — real assertions below
    pass


def test_detect_doc_type_real():
    assert detect_doc_type("HLSI-MA-025_rv03 Guia Rapida NFS_Supra") == "guia_rapida"
    assert detect_doc_type("I56-6577-006_ES FAAST Notifier LT-200 QIG") == "guia_rapida"
    assert detect_doc_type("AM 8200N-manual instalacion RV 4 30-01-2025") == "instalacion"
    assert detect_doc_type("E56-6514ES-000_Notifier_NFXI-OSI-RIE_Installation_Guide") == "instalacion"
    assert detect_doc_type("AM-8100 manual de usuario y programacion rev 4") == "usuario"
    assert detect_doc_type("997-671-005-3_Configuration_ES") == "programacion"
    assert detect_doc_type("2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook") == "hoja_datos"
    assert detect_doc_type("19152_00_ICAM_Maintenance_Guide_A4_Spanish_lores") == "mantenimiento"
    assert detect_doc_type("MADT606") is None


# ---------------------------------------------------------------------------
# Full parse integration
# ---------------------------------------------------------------------------
def test_parse_full_notifier_am8200n():
    info = parse_revision("AM 8200N-manual instalacion RV 4 30-01-2025.pdf")
    assert info.revision == "4"
    assert info.revision_date == date(2025, 1, 30)
    assert info.doc_type == "instalacion"
    assert info.language is None
    assert "AM 8200N" in info.document_family
    assert "RV" not in info.document_family
    assert "2025" not in info.document_family


def test_parse_full_detnov_fsl100():
    info = parse_revision(
        "2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook.pdf"
    )
    assert info.revision == "Iss 1 Rev 4"
    assert info.doc_type == "hoja_datos"
    assert info.language == "es"


def test_parse_full_madt_internal_rev():
    info = parse_revision("MADT015_03.pdf")
    assert info.revision == "03"
    assert info.revision_date is None
    assert info.doc_type is None


def test_parse_first_pages_fallback():
    info = parse_revision(
        "HLSI-MN-192_UCIP.pdf",
        first_pages_text="Manual técnico UCIP GPRS\nRevisión 5 - Enero 2024\n...",
    )
    assert info.revision == "Rev 5"


def test_normalize_family_strips_language_and_rev():
    assert "rv03" not in normalize_family("HLSI-MA-025_rv03 Guia Rapida NFS_Supra").lower()
    fam = normalize_family("AM 8200N-manual instalacion RV 4 30-01-2025")
    assert "RV" not in fam
    assert "2025" not in fam
