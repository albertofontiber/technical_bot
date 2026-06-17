#!/usr/bin/env python3
"""Tests del localizador grado-audit — cubren los FP/FN que cazó el dúo s79.

Run: python scripts/test_audit_locator.py   (o pytest)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_locator import (  # noqa: E402
    citation_score, citation_present, locate, anchor_coverage, token_containment,
    fact_present, fact_match_score, measurable, short_codes,
)
from strict_match import chunk_has_quote_strict  # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  {'OK ' if cond else 'FALLO'}  {name}")
    if not cond:
        FAILS.append(name)


def test_digit_boundary_fp():
    """'24' NO debe machear dentro de '240' (FP que el `in` crudo del matcher viejo cometía)."""
    # cov de la cita "tension nominal 24 V": anchor '24' con frontera de dígito
    cov_240 = anchor_coverage("tension nominal 24 V", "la tension de salida es de 240 V continuos")
    cov_24 = anchor_coverage("tension nominal 24 V", "alimentacion a 24 V en reposo nominal")
    check("anchor '24' NO machea '240' (cov<1)", cov_240 < 1.0)
    check("anchor '24' SI machea '24 V' (cov==1)", cov_24 == 1.0)


def test_cross_product_source_tie():
    """La clave '2222' de OTRO producto NO debe localizarse cuando el gold es de otro manual."""
    quote = "Introduzca la clave de administrador por defecto, 2222"
    chunks = [
        {"id": "A", "source_file": "55315008-CAD-150-8-Usuario",
         "product_model": "CAD-150-8",
         "content": "Introduzca la clave de administrador por defecto 2222 para acceder al menu"},
        {"id": "B", "source_file": "MANUAL-OTRO-PRODUCTO-XYZ",
         "product_model": "XYZ-99",
         "content": "La clave de administrador por defecto es 2222 en este equipo"},
    ]
    found = locate(quote, chunks, gold_sources=["55315008-Manual-...-CAD-150-8-Usuario.pdf"])
    ids = [r["id"] for r in found]
    check("source-tie: localiza el chunk del manual del gold (A)", "A" in ids)
    check("source-tie: NO localiza el '2222' del OTRO producto (B)", "B" not in ids)


def test_ocr_prose_fn_cat016():
    """El caso REAL cat016: el matcher viejo daba FALSO-NEGATIVO (falso corpus-gap); el nuevo lo encuentra."""
    gold_quote = ("3.1.1.5 Menu PRUEBA Zonas... nos permite poner en modo de prueba la zona que "
                  "seleccionemos. Esta opcion nos permite hacer la prueba de los detectores sin tener "
                  "que rearmar la central... el retardo... quedaria anulado... Si trascurridos 20 minutos "
                  "no se ha efectuado ningun disparo el equipo pasara a estado normal.")
    # chunk REAL (wording/acentos distintos, sin el nº de seccion "3.1.1.5"):
    real_chunk = ("La opción PRUEBA del menú ZONA, nos permite poner en modo de prueba la zona que "
                  "seleccionemos. Esta opción nos permite hacer la prueba de los detectores sin tener que "
                  "rearmar la central tras cada disparo. En modo prueba el retardo de las sirenas queda "
                  "anulado. Si transcurridos 20 minutos no se ha producido ningún disparo, el equipo "
                  "vuelve a estado normal.")
    old = chunk_has_quote_strict(real_chunk, gold_quote)
    new = citation_present(gold_quote, real_chunk)
    check("matcher VIEJO da FALSO-NEGATIVO en el chunk real (demuestra el bug)", old is False)
    check("localizador NUEVO SÍ encuentra el chunk real (arregla el FN)", new is True)


def test_true_negative():
    """Un chunk no relacionado NO debe localizarse."""
    quote = "Introduzca la clave de administrador por defecto, 2222"
    chunk = "El detector optico FAAST LT-200 dispone de dos rele de alarma con contactos NC-C-NA"
    check("true-negative: chunk ajeno no se localiza", citation_present(quote, chunk) is False)


def test_same_number_different_fact():
    """Mismo número, hecho ajeno: '47' presente pero sin la prosa del hecho -> score 0 (piso de prosa)."""
    quote = "las salidas de sirena llevan una resistencia de fin de linea de 47 kohm"
    chunk = "el equipo soporta hasta 47 dispositivos en configuracion de lazo cerrado direccionable"
    score = citation_score(quote, chunk)
    check("same-number-diff-fact: '47' presente pero prosa ajena -> no presente", score < 0.55)


def test_measurable():
    """s81/dúo r3: medible = el VALOR es verificable (datum anclable o prosa); single-digit-value
    y frases sin tokens → NO-medible (candidatos al juez semántico, diferido)."""
    check("47 kohm (anchor) -> medible", measurable("47 kohm") is True)
    check("NC-C-NA (codigo) -> medible", measurable("NC-C-NA") is True)
    check("'bucle cerrado' (prosa) -> medible", measurable("bucle cerrado") is True)
    check("'1 A' (single-digit value) -> NO-medible", measurable("1 A") is False)
    check("'4 circuitos' (single-digit value) -> NO-medible", measurable("4 circuitos") is False)
    check("'una vez al ano' (sin tokens) -> NO-medible", measurable("una vez al año") is False)
    check("'r.1' (seccion corta) -> NO-medible", measurable("r.1") is False)


def test_fact_value_required():
    """s81/dúo r3 (crít): el VALOR debe estar (cov>0); la prosa del enunciado SOLA no basta →
    mata el FP 'valor marcado presente por contexto sin el dato'."""
    texto = "la resistencia de fin de linea de las salidas de sirena es de 47 kohm"
    con_valor = "cada salida lleva una resistencia de fin de linea de 47 kohm supervisada"
    sin_valor = "cada salida de sirena lleva una resistencia de fin de linea supervisada en placa"
    check("valor presente -> score alto (>=0.7)", (fact_match_score("47 kohm", texto, con_valor) or 0) >= 0.7)
    check("valor AUSENTE (solo prosa del enunciado) -> 0.0 (NO FP)",
          fact_match_score("47 kohm", texto, sin_valor) == 0.0)


def test_fact_present_shortcode():
    """s81/dúo: NC-C-NA via anchor_present (frontera); '1 A' no-medible -> None (no falso CORPUS-GAP)."""
    check("NC-C-NA presente",
          fact_present("NC-C-NA", "los rele de alarma de placa", "dos rele con contactos NC-C-NA y comun") is True)
    check("NC-C-NA ausente -> False",
          fact_present("NC-C-NA", "los rele de alarma de placa", "soporta 47 dispositivos en lazo cerrado") is False)
    check("'1 A' no-medible -> None",
          fact_present("1 A", "corriente maxima 1 A por salida de sirena", "salida de sirena de 1 A maxima") is None)


def test_fact_no_fp_same_number():
    """s81/dúo: el valor 47 presente pero en contexto AJENO → no presente (el texto desambigua)."""
    texto = "resistencia de fin de linea de 47 kohm en las salidas de sirena"
    ajeno = "el equipo soporta hasta 47 dispositivos direccionables en configuracion de lazo cerrado"
    real = "cada salida de sirena lleva una resistencia de fin de linea de 47 kohm supervisada"
    check("47 presente pero hecho ajeno -> NO presente", fact_present("47 kohm", texto, ajeno) is not True)
    check("el hecho real SI se localiza", fact_present("47 kohm", texto, real) is True)


def main():
    print("=== tests audit_locator ===")
    for t in (test_digit_boundary_fp, test_cross_product_source_tie, test_ocr_prose_fn_cat016,
              test_true_negative, test_same_number_different_fact,
              test_measurable, test_fact_value_required, test_fact_present_shortcode,
              test_fact_no_fp_same_number):
        print(f"\n[{t.__name__}]")
        t()
    print()
    if FAILS:
        print(f"FALLARON {len(FAILS)}: {FAILS}")
        return 1
    print("TODOS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
