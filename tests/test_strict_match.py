"""Tests del matcher canónico (strict_match) — foco en distinctive() y el
tratamiento de RANGOS vs signos reales. Regresión del fix s40: distinctive("110-230")
producía "-230" (guion de rango leído como signo) y el scorer lo marcaba ausente en
"110-230" por la frontera de dígito de _anchor_present (cat005 false-miss).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from strict_match import anchor_present, distinctive, norm_ocr  # noqa: E402


def test_distinctive_rango_no_genera_signo_espurio():
    # el guion es separador de RANGO, no signo → números SIN signo
    assert distinctive("110-230 Vac") == {"110", "230"}
    assert distinctive("24-28 V") == {"24", "28"}
    # "4-20 mA": el 4 es de 1 dígito (excluido); el RHS es 20, NO -20
    assert distinctive("4-20 mA") == {"20"}


def test_distinctive_conserva_signos_reales():
    # signo real (no precedido de dígito) → se conserva
    assert distinctive("-10/+55 C") == {"-10", "+55"}
    assert distinctive("rango -20/+60") == {"-20", "+60"}
    assert distinctive("tolerancia +60") == {"+60"}


def test_distinctive_decimales_y_enteros():
    assert distinctive("0,75 A") == {"0,75"}
    assert distinctive("2,0 A a 30 V CC") == {"2,0", "30"}
    assert distinctive("1230") == {"1230"}  # no se parte


def test_distinctive_suma_colapsa_al_numero():
    # suma "X+Y": el '+' pegado a dígito es operador → número sin signo
    assert distinctive("99+99") == {"99"}
    assert distinctive("159+159") == {"159"}


def test_distinctive_codigos_de_modelo():
    assert "afp1010" in distinctive("central AFP1010")
    assert "mi-310" in distinctive("DOC MI-310")


def test_rango_casa_con_frontera_de_digito():
    # el bug s40 al completo: cada anchor de un rango DEBE casar en el texto del bot
    # con la frontera de dígito de anchor_present (canónica desde s46).
    na = norm_ocr("alimentacion 110-230 vac, 50-60 hz")
    for a in distinctive("110-230 Vac"):
        assert anchor_present(a, na), f"{a} no casa"


def test_anchor_present_frontera_digito():
    # el ARTEFACTO s45 (DEC-019): '99' NO debe casar dentro de '990' ni '1993'.
    # El substring crudo all(a in nc) lo contaba → inflaba SÍNTESIS en el funnel.
    assert not anchor_present("99", norm_ocr("rango 990 mA"))
    assert not anchor_present("99", norm_ocr("ano 1993"))
    assert anchor_present("99", norm_ocr("son 99 zonas"))
    # número con unidad pegada SÍ casa; número mayor que lo contiene NO.
    assert anchor_present("24", norm_ocr("alimentacion 24V"))
    assert not anchor_present("24", norm_ocr("hasta 240 v"))
    # no-regresión cat001 (síntesis-genuina, DEC-019): '159' casa en la suma '159+159'.
    assert anchor_present("159", norm_ocr("159+159"))


def test_anchor_present_politica_congelada_s46():
    # CONGELA la decisión de F0#2 (frontera `\d`, no `[\d.,]`) — para que cambiarla
    # sea deliberado. Trade-off verificado en el dúo Protocolo 3:
    #  (a) LÍMITE ACEPTADO: `\d` deja pasar el separador de millar/decimal español.
    assert anchor_present("792", norm_ocr("capacidad 13.792 eventos"))  # FP conocido
    assert anchor_present("159", norm_ocr("tension 2.159 v"))           # FP conocido
    #  (b) A CAMBIO: `\d` NO sufre los FN comunes que `[\d.,]` sí introduciría.
    assert anchor_present("295", norm_ocr("los valores son 295, 300 y 450"))  # coma de lista
    assert anchor_present("295", norm_ocr("el maximo es 295."))               # fin de frase


def test_anchor_present_codigo_frontera_palabra():
    # código de modelo → frontera de PALABRA: token completo, no dentro de otro
    assert anchor_present("afp1010", norm_ocr("central AFP1010 v2"))
    assert not anchor_present("mi-310", norm_ocr("doc MI-3100"))
