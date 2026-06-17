#!/usr/bin/env python3
"""Tests del localizador grado-audit — cubren los FP/FN que cazó el dúo s79.

Run: python scripts/test_audit_locator.py   (o pytest)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_locator import (  # noqa: E402
    citation_score, citation_present, locate, anchor_coverage, token_containment,
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


def main():
    print("=== tests audit_locator ===")
    for t in (test_digit_boundary_fp, test_cross_product_source_tie, test_ocr_prose_fn_cat016,
              test_true_negative, test_same_number_different_fact):
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
