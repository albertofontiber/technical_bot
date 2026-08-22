# -*- coding: utf-8 -*-
"""El lote de clasificación, parametrizado por marca (cierre de s336-lote).

Cubre las tres cosas que pueden salir MAL al escalar el método a otra marca, y
que el pipeline de Notifier no podía fallar porque la marca estaba incrustada:

1. los recibos de una marca pisando los de otra,
2. la provenance prometiendo un gold que no juzgó esas filas,
3. el writer escribiendo filas de una marca con el juicio de otra.

Más un guard-test de artefacto: el censo de Notifier NO puede cambiar, porque
las 411 filas escritas llevan su sha en la provenance.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lib_lote_marca as L  # noqa: E402


# ---------------------------------------------------------------- rutas
def test_notifier_conserva_los_nombres_historicos():
    """Están CITADOS en la decisión del lote; renombrarlos rompe la traza."""
    assert L.ruta("censo", "notifier").name == "s336_censo_diana_v1.json"
    assert L.ruta("gate", "notifier").name == "s336_gate_result_v1.json"
    assert L.ruta("gt", "notifier", "yaml").name == "s336_gt_v1.yaml"


def test_otra_marca_no_pisa_los_recibos_de_notifier():
    for etapa in ("censo", "poblacion", "elegibles", "gate", "escritura"):
        assert L.ruta(etapa, "morley") != L.ruta(etapa, "notifier")
        assert "morley" in L.ruta(etapa, "morley").name


def test_la_marca_se_normaliza_como_el_namespace_del_catalogo():
    assert L.normaliza_marca("System Sensor") == "systemsensor"
    assert L.normaliza_marca("Notifier") == "notifier"
    assert L.ruta("censo", "System Sensor").name.count("systemsensor") == 1


def test_etapa_desconocida_es_error_no_ruta_inventada():
    with pytest.raises(ValueError):
        L.ruta("etapa-que-no-existe", "morley")


# ---------------------------------------------------------- provenance
def test_la_provenance_deriva_del_recibo_real(tmp_path):
    gate = tmp_path / "gate.json"; gate.write_text("{}", encoding="utf-8")
    gt = tmp_path / "gt.yaml"; gt.write_text("filas: []", encoding="utf-8")
    censo = tmp_path / "censo.json"; censo.write_text('{"total": 3}', encoding="utf-8")
    prov = L.provenance("morley", gate, gt, censo)
    assert "morley" in prov
    assert L.sha_fichero(gt) in prov and L.sha_fichero(censo) in prov


def test_la_provenance_de_otra_marca_no_arrastra_el_gold_de_notifier(tmp_path):
    """El fallo que motivó derivarla: la constante llevaba los sha de Notifier."""
    gate = tmp_path / "g.json"; gate.write_text("{}", encoding="utf-8")
    gt = tmp_path / "gt.yaml"; gt.write_text("otro gold", encoding="utf-8")
    censo = tmp_path / "c.json"; censo.write_text("{}", encoding="utf-8")
    prov = L.provenance("morley", gate, gt, censo)
    assert "c8bb02620b4ade74" not in prov      # GT de Notifier
    assert "37cc4aa409ab484f" not in prov      # censo de Notifier


# -------------------------------------------------------------- candado
class _CatFalso:
    """Catálogo mínimo con dos marcas; `_productos_marca` lo lee vía vista_de."""


def test_el_candado_caza_los_recibos_cruzados(monkeypatch):
    vista = {"notifier:afp-1010": {"id": "notifier:afp-1010"},
             "notifier:nfs-320": {"id": "notifier:nfs-320"}}
    monkeypatch.setattr(L, "vista_de", lambda cat, marca: vista)
    limpios = L.candado_de_vista(list(vista), None, "notifier")
    assert limpios == []
    intrusos = L.candado_de_vista(
        ["notifier:afp-1010", "morley:zx5", "kidde:2x-f"], None, "notifier")
    assert intrusos == ["morley:zx5", "kidde:2x-f"]


# ------------------------------------------------- guard-tests de artefacto
def test_el_censo_de_notifier_sigue_siendo_el_que_cita_la_provenance():
    """Las 411 filas escritas prometen `censo 37cc4aa409ab484f`. Si este test
    cae, o se re-corrió el censo encima (la guarda existe para eso) o la
    promesa de esas filas dejó de ser cierta."""
    p = L.ruta("censo", "notifier")
    assert hashlib.sha256(p.read_bytes()).hexdigest()[:16] == "37cc4aa409ab484f"


def test_el_censo_no_se_deja_pisar_sin_force():
    """Re-correrlo hoy recalcularía la diana contra el catálogo YA escrito."""
    r = subprocess.run([sys.executable, "scripts/s336_censo_diana.py",
                        "--marca", "notifier"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "YA EXISTE" in r.stdout


@pytest.mark.parametrize("script", [
    "s336_censo_diana.py", "s336_poblacion.py",
    "s336_capacidad_y_fulltext.py", "s336_gate_y_packet.py", "s336_writer.py"])
def test_todas_las_etapas_aceptan_marca(script):
    r = subprocess.run([sys.executable, f"scripts/{script}", "--help"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr
    assert "--marca" in r.stdout


# ------------------------------------- lo que destapó el revisor adversarial
@pytest.mark.parametrize("grafia", [
    "Morley-IAS", "Pepperl-Fuchs", "Aguilera Electrónica", "System Sensor",
    "NOTIFIER", "morley ias"])
def test_la_marca_se_normaliza_EXACTAMENTE_como_el_join(grafia):
    """Un normalizador propio divergía del real en cuanto había guiones o
    acentos: dos grafías de la MISMA vista daban rutas distintas y la guarda
    anti-pisado se saltaba sola."""
    from src.bot.telegram_bot import _norm_marca
    assert L.normaliza_marca(grafia) == _norm_marca(grafia)


def test_dos_grafias_de_la_misma_marca_dan_el_mismo_recibo():
    assert L.ruta("censo", "Pepperl-Fuchs") == L.ruta("censo", "pepperl fuchs")
    assert L.ruta("censo", "Morley-IAS") == L.ruta("censo", "Morley IAS")


def test_la_guarda_protege_censo_y_gold(tmp_path):
    existe = tmp_path / "censo.json"; existe.write_text("{}", encoding="utf-8")
    assert L.guarda_de_pisado(existe, "morley", force=False)
    assert L.guarda_de_pisado(existe, "morley", force=True) is None
    assert L.guarda_de_pisado(tmp_path / "nuevo.json", "morley", False) is None


def test_el_recibo_de_escritura_rota_en_vez_de_pisarse(tmp_path):
    """El writer es incremental por diseño: abortar rompería su uso legítimo,
    pero sobrescribir perdió el recibo del lote original (361/PASS)."""
    base = tmp_path / "escritura_v1.json"
    assert L.ruta_no_destructiva(base) == base
    base.write_text("{}", encoding="utf-8")
    r2 = L.ruta_no_destructiva(base)
    assert r2.name == "escritura_v1_r2.json"
    r2.write_text("{}", encoding="utf-8")
    assert L.ruta_no_destructiva(base).name == "escritura_v1_r3.json"


def test_el_recibo_del_lote_original_esta_recuperado():
    """La corrida de recuperación lo había pisado; su antes/después no era
    recomputable y la única copia estaba en git."""
    r1 = L.carga_recibo(L.EVALS / "s336_escritura_result_v1_r1.json")
    assert r1["escritas"] == 361 and r1["veredicto_lote"] == "PASS"
    assert r1["antes"]["clasificados"] == 3


def test_el_gate_no_corre_sin_gold_congelado():
    r = subprocess.run([sys.executable, "scripts/s336_gate_y_packet.py",
                        "--marca", "marcainexistentedeprueba"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "no hay GT congelado" in r.stdout
