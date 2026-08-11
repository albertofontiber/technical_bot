# -*- coding: utf-8 -*-
"""s317 — Puerta de revisión de la ingesta (#73): batería de CASOS REALES (v1.1).

Cada caso viene del corpus vivo (muestreo de `documents` en s317), de los dos
fallos reales de s316d, o de un hallazgo del dúo r13 (Sol 8 · Fable 7).
Precisión-primero: los tests de NO-disparo pesan tanto como los de disparo —
un falso BLOQUEO pierde un manual legítimo (lección de la guardia #70).
"""
import pytest

from src.reingest.revision_gate import (
    BLOQUEADO,
    NO_COMPARABLE,
    SIN_SENAL,
    SUPERSEDE,
    cruzar,
    indice_corpus,
    indice_de_senales,
    parsear_senal,
    senales_de_filename,
    senales_de_portada,
    senales_documento,
    serializar_senal,
)

# Nombres REALES del corpus (documents.source_pdf_filename, s317).
_CORPUS = [
    {"source_pdf_filename": "aritech_ins570-8_combined.pdf"},
    {"source_pdf_filename":
        "00-3301-501-4000-04_r004_2x-a-lb_loop_board_installation_sheet_ml.pdf"},
    {"source_pdf_filename": "MI_KIDDE_KE_DP312x_SNx_202512_ES_242d.pdf"},
    {"source_pdf_filename": "4188-1124-ES issue 6_01-2026_To.pdf"},
    {"source_pdf_filename": "4188-1124-PT issue 4_01-2026_To.pdf"},
    {"source_pdf_filename": "15274 RevB - RZA-4X_Eng.pdf"},
    {"source_pdf_filename": "HD_KE_DP3021B_202407_ES_861a.pdf"},
    {"source_pdf_filename": "HD_KE_DB3010B_202407_ES_1065.pdf"},
    {"source_pdf_filename": "MNDT951_v5-87.pdf"},
    {"source_pdf_filename": "MNDT951I_v7-1.pdf"},
    {"source_pdf_filename":
        "3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet.pdf"},
    {"source_pdf_filename": "ms1-2-4.pdf"},
    {"source_pdf_filename": "18-187110-10.pdf"},
    {"source_pdf_filename": "AM-8100 manual de usuario y programacion rev 4 30-10-2024.pdf"},
]


@pytest.fixture(scope="module")
def indice():
    return indice_corpus(_CORPUS)


# --- Los DOS fallos reales de s316d (la razón de ser de la puerta) -----------

def test_s316d_ins570_bloqueado_por_portada(indice):
    """El candidato Casmar no llevaba «ins570» en el filename — solo la portada
    decía INS570-3. El corpus tiene issue 8: BLOQUEADO."""
    senales = senales_documento(
        "serie_2000_sirenas_balizas_instrucciones.pdf",
        "Serie 2000 sirenas y balizas\nINS570-3\nInstrucciones de instalación")
    v = cruzar(senales, indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "aritech_ins570-8_combined.pdf"


def test_s316d_pn_utc_bloqueado(indice):
    """P/N 00-3301-501-4000-03 vs corpus -04_r004: la doble señal P/N+_rNNN."""
    v = cruzar(senales_de_filename(
        "00-3301-501-4000-03_r003_2x-a-lb_loop_board_installation_sheet_ml.pdf"),
        indice)
    assert v.resultado == BLOQUEADO
    assert "00 3301 501 4000" in v.motivo
    assert v.contra and "r004" in v.contra


# --- Dirección SUPERSEDE (revisión nueva procede y se anota) -----------------

def test_revision_nueva_es_supersede(indice):
    v = cruzar(senales_de_filename(
        "00-3301-501-4000-05_r005_2x-a-lb_loop_board_installation_sheet_ml.pdf"),
        indice)
    assert v.resultado == SUPERSEDE
    assert "supersede" in v.motivo


def test_fecha_portal_casmar_bloqueada_y_supersede(indice):
    """La familia del par supersedido VIVO del corpus (DP312x 202503/202512)."""
    viejo = cruzar(senales_de_filename(
        "MI_KIDDE_KE_DP312x_SNx_202503_ES_acf9.pdf"), indice)
    assert viejo.resultado == BLOQUEADO
    assert viejo.contra == "MI_KIDDE_KE_DP312x_SNx_202512_ES_242d.pdf"
    nuevo = cruzar(senales_de_filename(
        "MI_KIDDE_KE_DP312x_SNx_202601_ES_ffff.pdf"), indice)
    assert nuevo.resultado == SUPERSEDE


# --- Idioma = identidad (jamás cross-supersede) ------------------------------

def test_idiomas_no_se_supersedendan(indice):
    v = cruzar(senales_de_filename("4188-1124-PT issue 5_11-2025_To.pdf"), indice)
    assert v.resultado == SUPERSEDE
    assert v.contra == "4188-1124-PT issue 4_01-2026_To.pdf"


def test_issue_mismo_idioma_bloquea_pese_a_fecha_distinta(indice):
    """La fecha de los nombres Notifier cambia con cada issue: sin la poda de
    rachas-fecha, dos issues del mismo doc no compartirían base."""
    v = cruzar(senales_de_filename("4188-1124-ES issue 5_04-2025_To.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "4188-1124-ES issue 6_01-2026_To.pdf"


def test_language_columna_ambigua_no_bloquea():
    """(Sol r13 M1) Misma base con `language` DISTINTO en documents (el nombre
    no distingue idioma) → NO_COMPARABLE, jamás bloqueo a ciegas."""
    indice = indice_corpus([
        {"source_pdf_filename": "Manual central NFG-8 rev 3.pdf", "language": "es"},
        {"source_pdf_filename": "Manual central NFG-8 rev 4.pdf", "language": "pt"},
    ])
    v = cruzar(senales_de_filename("Manual central NFG-8 rev 2.pdf"), indice)
    assert v.resultado == NO_COMPARABLE
    assert "idiomas" in v.motivo


# --- El bug Fable r13 F1: la fecha JAMÁS entra en la tupla de revisión -------

def test_fecha_no_contamina_la_tupla_rev(indice):
    """«rev 4 30-10-2024»: la v1 capturaba rev=(4,30,10) y comparaba DÍAS.
    v1.1: multi-parte solo con `.`/`_` — la fecha queda fuera de la tupla."""
    senales = senales_de_filename(
        "AM-8100 manual de usuario y programacion rev 3 05-11-2024.pdf")
    rev_num = [s for s in senales if s.formato == "rev_num"]
    assert rev_num and rev_num[0].rev == (3,)
    v = cruzar(senales, indice)
    assert v.resultado == BLOQUEADO           # 3 < 4, comparación de REVISIÓN
    assert "supersedida por 4" in v.motivo


def test_rev_multiparte_real_con_puntos():
    """«Rev 3.2» y «rev1_1_4» (LDA, reales) SÍ son multi-parte."""
    s32 = senales_de_filename("ZES22S02-MU Manual de Usuario ZES-22 Rev 3.2.pdf")
    assert any(s.rev == (3, 2) and s.formato == "rev_num" for s in s32)
    s114 = senales_de_filename("NEO8060S02-MU - MANUAL SERIE NEO rev1_1_4.pdf")
    assert any(s.rev == (1, 1, 4) for s in s114)


# --- Contrato #73 LITERAL: corpus >= candidata ⇒ BLOQUEADO (r13) -------------

def test_misma_revision_bytes_distintos_BLOQUEA(indice):
    """(Sol r13 M2/Fable F5) El pre-registro del TECH_DEBT dice >=: un duplicado
    activo de la MISMA edición es la clase #4. El override existe para el caso
    adjudicado."""
    v = cruzar(senales_de_filename("HD_KE_DP3021B_202407_ES_9f9f.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert "misma revisión" in v.motivo


def test_hash_cms_todo_digitos_se_poda_en_familia_fecha(indice):
    v = cruzar(senales_de_filename("HD_KE_DB3010B_202301_ES_abcd.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "HD_KE_DB3010B_202407_ES_1065.pdf"


# --- INTRA-LOTE (Sol r13 C1/Fable F2) ----------------------------------------

def test_intra_lote_bloquea_la_menor():
    """Dos revisiones del mismo manual en el MISMO lote: la menor se bloquea
    contra la mayor (así pudo nacer el par vivo 202503/202512)."""
    fn_a = "MI_ACME_X100_202503_ES_aaaa.pdf"
    fn_b = "MI_ACME_X100_202512_ES_bbbb.pdf"
    sen_a, sen_b = senales_de_filename(fn_a), senales_de_filename(fn_b)
    v_menor = cruzar(sen_a, indice_de_senales([(s, fn_b) for s in sen_b]),
                     igualdad_bloquea=False)
    assert v_menor.resultado == BLOQUEADO
    v_mayor = cruzar(sen_b, indice_de_senales([(s, fn_a) for s in sen_a]),
                     igualdad_bloquea=False)
    assert v_mayor.resultado == SUPERSEDE


def test_intra_lote_igualdad_no_se_bloquea_mutuamente():
    """Misma revisión en el lote: con igualdad bloqueante se excluirían LOS DOS
    — degrada a revisión-a-mano."""
    fn_a, fn_b = "MI_ACME_X100_202503_ES_aaaa.pdf", "MI_ACME_X100_202503_ES_bbbb.pdf"
    v = cruzar(senales_de_filename(fn_a),
               indice_de_senales([(s, fn_b) for s in senales_de_filename(fn_b)]),
               igualdad_bloquea=False)
    assert v.resultado == NO_COMPARABLE


# --- Persistencia (Sol r13 C2): la señal sobrevive a la ingesta --------------

def test_senal_persistida_roundtrip():
    for fn in ("4188-1124-ES issue 6_01-2026_To.pdf",
               "15274 RevB - RZA-4X_Eng.pdf",
               "MI_KIDDE_KE_DP312x_SNx_202512_ES_242d.pdf"):
        for s in senales_de_filename(fn):
            recuperada = parsear_senal(serializar_senal(s))
            assert recuperada is not None
            assert (recuperada.base, recuperada.formato, recuperada.rev) == \
                (s.base, s.formato, s.rev)
    assert parsear_senal(None) is None
    assert parsear_senal("nota libre del lote") is None


def test_indice_lee_columna_revision_persistida():
    """Una revisión que solo la PORTADA delató: su filename no emite señal,
    pero la columna `revision` persistida la mantiene visible — un candidato
    viejo posterior se bloquea igual."""
    senales_portada = senales_de_portada("Serie 2000\nINS570-9\nInstrucciones")
    assert senales_portada, "precondición: la portada emite señal INS"
    indice = indice_corpus([{
        "source_pdf_filename": "serie_2000_sirenas_instrucciones.pdf",  # mudo
        "revision": serializar_senal(senales_portada[0]),
    }])
    v = cruzar(senales_de_portada("Serie 2000\nINS570-7\nInstrucciones"), indice)
    assert v.resultado == BLOQUEADO


# --- PORTADA acotada (Fable F3/F4) -------------------------------------------

def test_portada_solo_familias_span_independientes():
    """Las familias cuya base sería «portada-menos-span» jamás casarían con
    bases-filename: retiradas de portada, no prometidas."""
    senales = senales_de_portada("Manual de instalación\nissue 5\nrev 3")
    assert senales == []


def test_portada_anti_cita_de_hermanos():
    """«ver INS570-2» citando a un doc hermano NO puede bloquear (las
    remisiones internas son frecuentes: 329 en el censo s294)."""
    con_cita = senales_de_portada(
        "Módulo de expansión XYZ\npara detalles de sirenas ver INS570-2\n")
    assert all(s.base != "ins570" for s in con_cita)
    titulada = senales_de_portada("Serie 2000\nINS570-3\nInstrucciones")
    assert any(s.base == "ins570" for s in titulada)


# --- iss_fecha (Sol r13 M6: «ISS 07NOV23» del TECH_DEBT) ---------------------

def test_iss_fecha_ddmmmyy():
    viejo = senales_de_filename("MAN0987 panel FSL100 ISS 07NOV23.pdf")
    assert any(s.formato == "iss_fecha" and s.rev == (2023, 11, 7)
               for s in viejo)
    indice = indice_corpus([
        {"source_pdf_filename": "MAN0987 panel FSL100 ISS 12MAR25.pdf"}])
    assert cruzar(viejo, indice).resultado == BLOQUEADO


# --- Familia v y bases que NO deben cruzar -----------------------------------

def test_familia_v_y_sufijo_de_modelo_distinto(indice):
    assert cruzar(senales_de_filename("MNDT951_v5-20.pdf"),
                  indice).resultado == BLOQUEADO
    v = cruzar(senales_de_filename("MNDT951I_v6-0.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "MNDT951I_v7-1.pdf"


def test_rnnn_sin_pn_multigrupo(indice):
    v = cruzar(senales_de_filename(
        "3103072-ml_r003_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet.pdf"),
        indice)
    assert v.resultado == BLOQUEADO


def test_rev_letra_bloqueada(indice):
    v = cruzar(senales_de_filename("15274 RevA - RZA-4X_Eng.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "15274 RevB - RZA-4X_Eng.pdf"


# --- Índice con TODAS las revisiones (Sol r13 M4/Fable F7) -------------------

def test_indice_conserva_aridades_mixtas():
    """Aridades mixtas en la misma base: el candidato compara contra la máxima
    de SU aridad, no contra «la primera vista»."""
    indice = indice_corpus([
        {"source_pdf_filename": "PANEL-X manual rev 2.pdf"},
        {"source_pdf_filename": "PANEL-X manual rev 3.4.pdf"},
    ])
    v = cruzar(senales_de_filename("PANEL-X manual rev 1.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert "supersedida por 2" in v.motivo


def test_indice_revision_maxima():
    indice = indice_corpus([
        {"source_pdf_filename": "D391 Issue 2 WR2001.pdf"},
        {"source_pdf_filename": "D391 Issue 3 WR2001.pdf"},
    ])
    v = cruzar(senales_de_filename("D391 Issue 1 WR2001.pdf"), indice)
    assert v.resultado == BLOQUEADO
    assert v.contra == "D391 Issue 3 WR2001.pdf"


# --- PRECISIÓN: lo que NO puede disparar -------------------------------------

@pytest.mark.parametrize("filename", [
    "ms1-2-4.pdf",                       # guiones cortos ≠ P/N con revisión
    "18-187110-10.pdf",                  # sin token _rNNN no se afirma P/N
    "FAAST Understanding EN54-20_SP.pdf",        # EN54-20 = norma, no revisión
    "DXC-puedo-cambiar-la-clave-de-nivel-3.pdf",  # FAQ con número final
    "997-267-000-6_Eng.pdf",             # P/N sin _rNNN: no se afirma
    "guia para revisar bombas jockey.pdf",        # «revisar» ≠ rev+letra
    "NF30-50_Manuel_d'utilisation_lr.pdf",
])
def test_precision_sin_senal_afirmable(filename, indice):
    v = cruzar(senales_de_filename(filename), indice)
    assert v.resultado == SIN_SENAL, (filename, v)


def test_senal_solo_no_bloquea_sin_cruce(indice):
    v = cruzar(senales_de_filename("D999 issue 7 - XYZ_Eng.pdf"), indice)
    assert v.resultado == SIN_SENAL


def test_formatos_distintos_no_se_comparan(indice):
    senales = senales_de_filename("15274 rev 2 - RZA-4X_Eng.pdf")
    assert all(s.formato != "rev_letra" for s in senales)
    assert cruzar(senales, indice).resultado == SIN_SENAL


def test_conflicto_filename_portada_se_retira():
    """Filename dice INS570-3 y la portada INS570-4 → evidencia en conflicto:
    la señal se retira y NO bloquea."""
    senales = senales_documento(
        "aritech_ins570-3_notas.pdf",
        "ARITECH\nINS570-4\nInstrucciones")
    assert all(s.base != "ins570" for s in senales)


def test_pn_contradice_rnnn_no_afirma():
    senales = senales_de_filename("00-3301-501-4000-03_r004_loop_board_ml.pdf")
    assert all(s.formato not in ("pn_utc", "rnnn") for s in senales)


def test_poda_de_anios_viejos():
    """(Fable F6) Años ≤2019 también podan de la base (manuales viejos)."""
    s = senales_de_filename("SMART3 TOXICOS MTEX 4749_SP REV 3 1998.pdf")
    rev = [x for x in s if x.formato == "rev_num"]
    assert rev and "1998" not in rev[0].base and rev[0].rev == (3,)
