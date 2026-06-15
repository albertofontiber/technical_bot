"""Tests de la capa de veredicto compartida (scripts/ab_verdict.py) — s73.
Paga la deuda del patrón: la tabla SHIP/ROLLBACK/GRIS antes vivía copiada en s59/s67/s69
sin tests. Cubre classify_pair (delta per-gold), global_verdict (tabla N golds) y
small_n_verdict (árbol n=2 de s73)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ab_verdict import (  # noqa: E402
    MARGEN_GANANCIA,
    classify_pair,
    global_verdict,
    small_n_verdict,
)


# ------------------------------------------------------------ classify_pair
def test_flip_pass_con_margen():
    assert classify_pair(["FALLO"] * 5, ["PASS"] * 5)["delta"] == "flip-pass"


def test_flip_pass_margen_justo():
    # 4 PASS / 1 FALLO → modal PASS, votos PASS=4 == MARGEN_GANANCIA
    r = classify_pair(["FALLO"] * 5, ["PASS", "PASS", "PASS", "PASS", "FALLO"])
    assert r["treat"]["votes"]["PASS"] == MARGEN_GANANCIA
    assert r["delta"] == "flip-pass"


def test_flip_pass_sin_margen():
    # 3 PASS / 2 FALLO → modal PASS, votos PASS=3 < margen → NO cuenta
    r = classify_pair(["FALLO"] * 5, ["PASS", "PASS", "PASS", "FALLO", "FALLO"])
    assert r["treat"]["veredicto"] == "PASS"
    assert r["delta"] == "flip-pass-sin-margen"


def test_regresion_de_pass():
    assert classify_pair(["PASS"] * 5, ["FALLO"] * 5)["delta"] == "regresion-de-pass"


def test_neutral_sin_pass_ningun_lado():
    r = classify_pair(["FALLO"] * 5, ["PARCIAL", "PARCIAL", "PARCIAL", "FALLO", "FALLO"])
    assert r["delta"] == "neutral"


def test_neutral_pass_ambos_lados():
    assert classify_pair(["PASS"] * 5, ["PASS"] * 5)["delta"] == "neutral"


# ------------------------------------------------------------ small_n_verdict (s73)
def test_s73_candidato_un_flip_otro_neutral():
    movers = [classify_pair(["FALLO"] * 5, ["PASS"] * 5),
              classify_pair(["FALLO"] * 5, ["FALLO"] * 5)]
    v = small_n_verdict(movers, factcov_no_cae=True, control_intacto=True)
    assert v["veredicto"] == "SHIP-CANDIDATO"   # NO 'SHIP' automático: 2º eje es humano


def test_s73_rollback_si_un_mover_regresa():
    movers = [classify_pair(["FALLO"] * 5, ["PASS"] * 5),
              classify_pair(["PASS"] * 5, ["FALLO"] * 5)]
    v = small_n_verdict(movers, factcov_no_cae=True, control_intacto=True)
    assert v["veredicto"] == "ROLLBACK"


def test_s73_rollback_si_control_regresa():
    movers = [classify_pair(["FALLO"] * 5, ["PASS"] * 5)]
    v = small_n_verdict(movers, factcov_no_cae=True, control_intacto=False)
    assert v["veredicto"] == "ROLLBACK"


def test_s73_gris_si_sube_pero_no_flipa():
    movers = [classify_pair(["FALLO"] * 5, ["PARCIAL"] * 5),
              classify_pair(["FALLO"] * 5, ["FALLO"] * 5)]
    v = small_n_verdict(movers, factcov_no_cae=True, control_intacto=True)
    assert v["veredicto"] == "GRIS"


def test_s73_gris_si_factcov_cae():
    movers = [classify_pair(["FALLO"] * 5, ["PASS"] * 5)]
    v = small_n_verdict(movers, factcov_no_cae=False, control_intacto=True)
    assert v["veredicto"] == "GRIS"


def test_s73_flip_sin_margen_no_es_candidato():
    movers = [classify_pair(["FALLO"] * 5, ["PASS", "PASS", "PASS", "FALLO", "FALLO"])]
    v = small_n_verdict(movers, factcov_no_cae=True, control_intacto=True)
    assert v["veredicto"] == "GRIS"


def test_margen_no_se_relaja_con_voto_invalido():
    # 4 PASS + 1 '?' → modal PASS pero n_valid=4 != 5 → NO cuenta como flip con margen
    r = classify_pair(["FALLO"] * 5, ["PASS", "PASS", "PASS", "PASS", "?"])
    assert r["treat"]["veredicto"] == "PASS"
    assert r["delta"] == "flip-pass-sin-margen"


# ------------------------------------------------------------ global_verdict (tabla s67)
def test_global_ship():
    assert global_verdict({"d_net": 2, "f_base": 5, "f_post": 5, "d_inest": 0})["veredicto"] == "SHIP"


def test_global_rollback_f_sube():
    assert global_verdict({"d_net": 3, "f_base": 5, "f_post": 8, "d_inest": 0})["veredicto"] == "ROLLBACK"


def test_global_gris_dnet_bajo():
    assert global_verdict({"d_net": 1, "f_base": 5, "f_post": 5, "d_inest": 0})["veredicto"] == "GRIS"


def test_global_rollback_control_mayor_1():
    m = {"d_net": 3, "f_base": 5, "f_post": 5, "d_inest": 0, "control_caidas": ["a", "b"]}
    assert global_verdict(m)["veredicto"] == "ROLLBACK"
