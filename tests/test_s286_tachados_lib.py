"""Tests del tokenizador de tachados (fixtures = casos-borde reales de los briefs v1/v1.1)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from s286_tachados_lib import strip_content, strip_line  # noqa: E402


class TestParesBasicos:
    def test_par_simple(self):
        r = strip_content("El módulo ~~Addressing.~~ del sistema")
        assert r.text == "El módulo Addressing. del sistema"
        assert r.pairs == ["Addressing."] and r.orphans == 0

    def test_dentro_de_negrita(self):
        r = strip_content("| **~~Physical~~ Characteristics** |")
        assert r.text == "| **Physical Characteristics** |"

    def test_con_espacios_interiores(self):
        r = strip_content("ver ~~ el texto ~~ aquí")
        assert r.text == "ver  el texto  aquí"

    def test_doble_marca_con_ins(self):
        r = strip_content("(disponible en ~~<ins>firesecurityproducts.com</ins>~~).")
        assert r.text == "(disponible en <ins>firesecurityproducts.com</ins>)."

    def test_idempotencia(self):
        r1 = strip_content("~~a~~ y ~~b~~")
        r2 = strip_content(r1.text)
        assert r1.text == "a y b" and not r2.changed


class TestLiterales:
    def test_arte_ascii_run_largo_intacto(self):
        art = "  •~~~~~~~~~~~•\n  S+ S- ≋ R+ R-"
        r = strip_content(art)
        assert r.text == art and not r.changed
        assert r.literals >= 1 and r.orphans == 0

    def test_subrayado_puntero_cbe_run10_intacto(self):
        cbe = "G33 = (G23 G24)\n     ~~~~~~~~~~"
        r = strip_content(cbe)
        assert r.text == cbe and not r.changed

    def test_run3_intacto(self):
        r = strip_content("delimitador ~~~ raro")
        assert not r.changed

    def test_run4_standalone_es_literal(self):
        r = strip_content("puntero corto:\n~~~~\nfin")
        assert not r.changed and r.run4_literal == 1

    def test_run4_con_espacio_a_un_lado_es_literal(self):
        r = strip_content("texto ~~~~ texto")
        assert not r.changed


class TestRun4Flanqueado:
    def test_agileiq_pares_adyacentes(self):
        r = strip_content("F[~~Retirado del~~~~servicio~~Parpadeorojo/azul]")
        assert r.text == "F[Retirado delservicioParpadeorojo/azul]"
        assert r.pairs == ["Retirado del", "servicio"] and r.orphans == 0


class TestHuerfanos:
    def test_huerfano_se_conserva(self):
        r = strip_content("marca suelta ~~ sin pareja")
        assert r.text == "marca suelta ~~ sin pareja"
        assert r.orphans == 1 and not r.changed

    def test_par_mas_huerfano(self):
        r = strip_content("~~a~~ y ~~ suelto")
        assert r.text == "a y ~~ suelto"
        assert r.pairs == ["a"] and r.orphans == 1

    def test_frase_partida_en_dos_lineas_no_empareja_cross_linea(self):
        r = strip_content("inicio ~~tachado\nsigue~~ fin")
        assert not r.changed and r.orphans == 2


class TestManifest:
    def test_eyeball_por_longitud(self):
        largo = "x" * 100
        r = strip_content(f"~~{largo}~~")
        assert r.eyeball_flags == [largo]

    def test_eyeball_por_puntuacion_de_frase(self):
        r = strip_content("~~Primera frase. Segunda parte~~")
        assert len(r.eyeball_flags) == 1

    def test_sin_eyeball_en_heading_corto(self):
        r = strip_content("## ~~INSTALLATION~~")
        assert r.eyeball_flags == []


class TestCasosRealesDB:
    def test_formula_numerador(self):
        r = strip_content("Nº máximo sensores < ~~3000 µA~~ = NºDet")
        assert r.text == "Nº máximo sensores < 3000 µA = NºDet"

    def test_no_enfatizado_securiton(self):
        r = strip_content("El restablecimiento *in situ* ~~no~~ provocará la reinicialización")
        assert r.text == "El restablecimiento *in situ* no provocará la reinicialización"

    def test_linea_sin_marcas_intacta(self):
        s = "línea normal sin nada especial"
        assert strip_line(s).text == s
