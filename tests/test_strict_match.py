"""Tests del matcher canónico (strict_match) — foco en distinctive() y el
tratamiento de RANGOS vs signos reales. Regresión del fix s40: distinctive("110-230")
producía "-230" (guion de rango leído como signo) y el scorer lo marcaba ausente en
"110-230" por la frontera de dígito de _anchor_present (cat005 false-miss).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from strict_match import distinctive, norm_ocr  # noqa: E402


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
    # con la frontera de dígito que usa atomic_scorer._anchor_present.
    na = norm_ocr("alimentacion 110-230 vac, 50-60 hz")
    for a in distinctive("110-230 Vac"):
        bound = r"\d" if re.fullmatch(r"[+\-]?\d[\d.,]*", a) else r"\w"
        assert re.search(rf"(?<!{bound}){re.escape(a)}(?!{bound})", na), f"{a} no casa"
