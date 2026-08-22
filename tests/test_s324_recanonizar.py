"""La puerta sabe cambiar el `canonical_model` de un id, sin tocar el id.

Hace falta cuando el nombre por el que el catálogo conoce un producto no es el nombre por
el que conviene ALCANZARLO. El caso que lo motiva: `notifier:nas` tiene canónico «NAS», y
el token de tres letras dispara con la preposición portuguesa «nas» y con «NAS de red»
(Network Attached Storage) — medido en `evals/s339g_bateria.json`. El id que Alberto
adjudicó no cambia; cambia el nombre, que no es inmutable.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.s324_lote_firmado_writer import aplicar_plan
from src.rag.catalog_store import FILES

VACIO: dict = {"products_altas": [], "products_confirmar": [], "products_retirar": [],
               "aliases_quitar": [], "umbrellas_altas": [],
               "doc_map_modificaciones": [], "doc_map_altas": []}


@pytest.fixture
def catalogo(tmp_path: Path) -> Path:
    origen = tmp_path / "origen"
    origen.mkdir()
    filas = [{"id": "notifier:nas", "canonical_model": "NAS", "estado": "activo",
              "candidate": True, "added_by": "t", "provenance": "seed",
              "vendido_bajo": ["Notifier"]}]
    (origen / FILES["products"]).write_text(
        "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas), "utf-8")
    for k in ("aliases", "umbrellas", "doc_map", "homonyms", "relations", "docrel"):
        (origen / FILES[k]).write_text("", "utf-8")
    return origen


def _aplica(origen: Path, destino: Path, plan_extra: dict) -> list[dict]:
    destino.mkdir(exist_ok=True)
    aplicar_plan({**VACIO, **plan_extra}, destino, origen)
    return [json.loads(l) for l in (destino / FILES["products"]).read_text("utf-8").splitlines() if l.strip()]


def test_cambia_el_canonico_y_conserva_el_id(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", {"products_recanonizar": [
        {"id": "notifier:nas", "canonical_model": "Notifier Air Sample",
         "motivo": "el token de 3 letras es ambiguo"}]})
    assert filas[0]["id"] == "notifier:nas"            # el id NO se toca: es inmutable
    assert filas[0]["canonical_model"] == "Notifier Air Sample"
    assert "'NAS' → 'Notifier Air Sample'" in filas[0]["provenance"]
    assert "seed" in filas[0]["provenance"]            # no pisa la procedencia anterior


def test_es_idempotente(catalogo, tmp_path):
    """Aplicar dos veces el mismo renombrado no apila procedencia."""
    d1 = tmp_path / "d1"
    filas = _aplica(catalogo, d1, {"products_recanonizar": [
        {"id": "notifier:nas", "canonical_model": "Notifier Air Sample", "motivo": "x"}]})
    d2 = tmp_path / "d2"
    filas2 = _aplica(d1, d2, {"products_recanonizar": [
        {"id": "notifier:nas", "canonical_model": "Notifier Air Sample", "motivo": "x"}]})
    assert filas2[0]["provenance"] == filas[0]["provenance"]


def test_un_id_inexistente_no_revienta(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", {"products_recanonizar": [
        {"id": "notifier:no-existe", "canonical_model": "X", "motivo": "typo"}]})
    assert filas[0]["canonical_model"] == "NAS"


def test_plan_sin_la_clave_sigue_funcionando(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", {})
    assert filas[0]["canonical_model"] == "NAS"
