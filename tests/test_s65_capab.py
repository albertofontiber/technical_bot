"""Tests de la LÓGICA PURA del runner s65 (scripts/s65_capab.py) — capa B #43.

Cubre las funciones que deciden mutaciones (diseño v2 post-dúo):
  - parse_revision: anclado a los DOS patrones verificados del lote s55
    (anti-greedy — la basura B3 nació de un parser codicioso).
  - consensus: moda + unanimidad (F6/X2: source mixto NO decide solo).
  - keyword_brand: cross-check de marca por filename.
  - propose_b6: semántica honesta de status (X3 — retired solo con señal
    fuerte; needs_review = cola humana).
  - mismatch_direction: direccionalidad A2 (default documents-pierde;
    excepciones a curación, caso MAD565).
Sin red: todo puro.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from s65_capab import (  # noqa: E402
    consensus,
    keyword_brand,
    mismatch_direction,
    norm_fname,
    parse_revision,
    propose_b6,
)


# ---------------------------------------------------------------- revision
def test_parse_revision_portal_rnnn():
    assert parse_revision(
        "00-3280-501-4009-05_r005_2x-a_series_installation_manual_es") == "r005"
    assert parse_revision(
        "03-0210-501-4300-06_r006_excellence_series_addressable_mcp_installation_sheet_ml"
    ) == "r006"


def test_parse_revision_iss():
    assert parse_revision("sds0098es_solo_a10_iss_2.1") == "iss 2.1"


def test_parse_revision_sin_patron_es_none():
    # Anti-greedy: nada de cazar palabras ni códigos sueltos (lección B3).
    assert parse_revision("Manual_CAD-201-MI-715-es") is None
    assert parse_revision("Instruction Manual SGMCB200") is None
    assert parse_revision("18-187110-10") is None
    assert parse_revision("2010-2-pak-rmsdk-161721-es") is None  # sin _rNNN_


# ---------------------------------------------------------------- consensus
def test_consensus_unanime():
    assert consensus(["Aritech", "Aritech", "Aritech"]) == ("Aritech", True)


def test_consensus_mixto_no_unanime():
    moda, unanime = consensus(["Kidde", "Kidde", "Aritech"])
    assert moda == "Kidde" and unanime is False


def test_consensus_ignora_none_y_vacio():
    assert consensus([None, "Edwards", None, "Edwards"]) == ("Edwards", True)
    assert consensus([None, None]) == (None, False)
    assert consensus([]) == (None, False)


# ---------------------------------------------------------------- keyword
def test_keyword_brand_cross_check():
    assert keyword_brand("1998M0901_FS24X_PT-BR54-10_PT-BR_RevB") == "Honeywell"
    assert keyword_brand("manual-sharpeye-40-40-series-winhost") == "Spectrex"
    assert keyword_brand("085501945t_PA5_Installation_manual") == "Pfannenberg"
    assert keyword_brand("bcn-3100017-es_r002_nc_series_panel") is None


# ---------------------------------------------------------------- propose_b6
def test_b6_duplicado_fantasma_retired():
    status, causa = propose_b6("MNDT250P", 0, dup_of="otro-id")
    assert status == "retired" and "duplicado" in causa


def test_b6_sin_contenido_sin_dup_needs_review():
    # Gap real de ingesta (p.ej. patológicos #7) → cola humana, NO retired (X3).
    status, _ = propose_b6("D1058-1_NFXI-WS-WSF", 0, dup_of=None)
    assert status == "needs_review"


def test_b6_portugues_sufijo_p_retired():
    status, causa = propose_b6("MNDT510P.pdf", 31, dup_of=None)
    assert status == "retired" and "portugués" in causa


def test_b6_frances_manuel_retired():
    status, _ = propose_b6("NF30-50_Manuel_d'utilisation_lr", 12, dup_of=None)
    assert status == "retired"


def test_b6_candidato_es_en_needs_review():
    # Contenido en tabla vieja sin señal de descarte → candidato (cola punto 3).
    status, causa = propose_b6("MCDT191_1", 1238, dup_of=None)
    assert status == "needs_review" and "candidato" in causa
    # bilingüe IT-EN = caso-a-caso de la política → cola, no descarte automático
    status, _ = propose_b6("Smart 2_MT251_Ita-Eng", 50, dup_of=None)
    assert status == "needs_review"


# ------------------------------------------------------- mismatch_direction
def test_a2_default_documents_pierde():
    d, ev = mismatch_direction("Detnov", "Securiton", True, "ASD535_TD_T131192es_h")
    assert d == "documents"


def test_a2_keyword_apoya_chunks():
    d, _ = mismatch_direction("Detnov", "Spectrex", True,
                              "manual-spectrex-sharpeye-20-20ml-user-manual")
    assert d == "documents"


def test_a2_excepcion_mad565_a_curacion():
    # Código Detnov en el filename contra chunks=Spectrex → NO automático (F6).
    d, ev = mismatch_direction(
        "Detnov", "Spectrex", True,
        "55356500-Manual-Sirena-Analogica-MAD565-I_ES_GB_MI-466-m-202")
    assert d == "curation"


def test_a2_no_unanime_a_curacion():
    d, _ = mismatch_direction("Morley", "Notifier", False, "doc_mixto_xyz")
    assert d == "curation"


# ---------------------------------------------------------------- norm
def test_norm_fname_pdf_insensible():
    assert norm_fname("MNDT250P.pdf") == norm_fname("MNDT250P") == "mndt250p"
