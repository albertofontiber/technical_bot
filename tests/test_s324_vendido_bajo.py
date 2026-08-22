"""La puerta s324 sabe añadir marcas a `vendido_bajo` — y sólo añadir.

Una fusión Morley↔Notifier deja UN id superviviente, y sin `vendido_bajo` con las dos
marcas el producto sólo es alcanzable bajo una: `_productos_marca` (src/bot/telegram_bot.py)
filtra por namespace del id **o** por `vendido_bajo`, así que el lado que perdió el id
desaparece del inventario de su marca. Eso es justo lo que Alberto pidió evitar
(«debería ser findable para ambas marcas»).
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
    filas = [{"id": "notifier:x1", "canonical_model": "X1", "estado": "activo",
              "candidate": False, "added_by": "t", "provenance": "t",
              "vendido_bajo": ["Notifier"]}]
    (origen / FILES["products"]).write_text(
        "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas), "utf-8")
    for k in ("aliases", "umbrellas", "doc_map", "homonyms", "relations", "docrel"):
        (origen / FILES[k]).write_text("", "utf-8")
    return origen


def _aplica(origen: Path, destino: Path, vb: list[dict]) -> list[dict]:
    destino.mkdir(exist_ok=True)
    aplicar_plan({**VACIO, "products_vendido_bajo": vb}, destino, origen)
    return [json.loads(l) for l in (destino / FILES["products"]).read_text("utf-8").splitlines() if l.strip()]


def test_anade_la_marca_que_falta(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", [
        {"id": "notifier:x1", "marcas": ["Morley"], "motivo": "fusión R3"}])
    assert filas[0]["vendido_bajo"] == ["Notifier", "Morley"]
    assert "vendido_bajo += ['Morley']" in filas[0]["provenance"]


def test_no_duplica_una_marca_que_ya_estaba(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", [
        {"id": "notifier:x1", "marcas": ["Notifier"], "motivo": "no-op"}])
    assert filas[0]["vendido_bajo"] == ["Notifier"]
    assert "vendido_bajo +=" not in filas[0]["provenance"]


def test_nunca_QUITA_una_marca(catalogo, tmp_path):
    """Control: la op es aditiva por diseño. Perder una marca retiraría un producto
    del inventario de esa marca sin que nadie lo pidiera."""
    filas = _aplica(catalogo, tmp_path / "d", [
        {"id": "notifier:x1", "marcas": ["Morley"], "motivo": "fusión"}])
    assert "Notifier" in filas[0]["vendido_bajo"]


def test_un_id_inexistente_no_revienta_el_lote(catalogo, tmp_path):
    filas = _aplica(catalogo, tmp_path / "d", [
        {"id": "notifier:no-existe", "marcas": ["Morley"], "motivo": "typo"}])
    assert len(filas) == 1


def test_plan_sin_la_clave_sigue_funcionando(catalogo, tmp_path):
    """Aditivo: los planes anteriores no llevan `products_vendido_bajo`."""
    d = tmp_path / "d"
    d.mkdir()
    aplicar_plan(dict(VACIO), d, catalogo)
    filas = [json.loads(l) for l in (d / FILES["products"]).read_text("utf-8").splitlines() if l.strip()]
    assert filas[0]["vendido_bajo"] == ["Notifier"]
