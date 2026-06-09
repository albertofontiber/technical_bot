"""Tests de la provenance del portal (Capa B del seam de Fase 2).

Cubren la lógica OEM (`channel_manufacturer`, sin tocar disco — lee el
`config/portal.yaml` real) y la atribución end-to-end vía un sidecar sintético
(monkeypatch del root, para no depender de los `Manuales_*` que van a .gitignore).
"""
import json

import pytest

from src.reingest import sidecar
from src.reingest.metadata import detect_document_metadata


@pytest.fixture(autouse=True)
def _clean_caches():
    """Cada test arranca/cierra con las caches del sidecar limpias."""
    sidecar.reload()
    yield
    sidecar.reload()


# --- lógica OEM (config real, sin disco) -------------------------------------

def test_oem_override_2xa_via_kidde():
    """La serie 2X-A por el canal Kidde → fabricante real Aritech, distr Kidde."""
    assert sidecar.channel_manufacturer("Manuales_Kidde/x.pdf", "2X-A") == ("Aritech", "Kidde")
    assert sidecar.channel_manufacturer("Manuales_Kidde/x.pdf", "2X-AT-F2") == ("Aritech", "Kidde")


def test_oem_override_via_own_channel_no_distributor():
    """La 2X-A por su propio canal Aritech → sin distributor (canal == fabricante)."""
    assert sidecar.channel_manufacturer("Manuales_Aritech/x.pdf", "2X-A") == ("Aritech", None)


def test_native_product_keeps_channel():
    assert sidecar.channel_manufacturer("Manuales_Kidde/x.pdf", "KE-DM3010R") == ("Kidde", None)
    assert sidecar.channel_manufacturer("Manuales_Aritech/x.pdf", "FD2705R") == ("Aritech", None)


def test_otros_is_generic_none():
    assert sidecar.channel_manufacturer("Manuales_Otros/x.pdf", "9-30441") == (None, None)


def test_non_portal_channel_unattributed():
    # Carpeta que NO es canal del portal → la decide el flujo viejo, no el canal.
    assert sidecar.channel_manufacturer("Manuales_Morley/x.pdf", "ZXe") == (None, None)


# --- atribución end-to-end con sidecar sintético -----------------------------

def test_portal_attribution_endtoend(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "portal.yaml").write_text(
        "channels: [Kidde]\n"
        "oem_overrides:\n"
        "  - equipo_prefix: '2X-'\n"
        "    manufacturer: Aritech\n",
        encoding="utf-8")
    folder = tmp_path / "Manuales_Kidde"
    folder.mkdir()
    (folder / "_metadata.json").write_text(json.dumps([
        {"local_filename": "2x-a_inst.pdf", "equipo": "2X-A", "series": "Serie 2X-A"},
        {"local_filename": "ke-dm.pdf", "equipo": "KE-DM3010R"},
    ]), encoding="utf-8")
    monkeypatch.setattr(sidecar, "_ROOT", str(tmp_path))
    monkeypatch.setattr(sidecar, "_PORTAL_CONFIG", str(tmp_path / "config" / "portal.yaml"))
    sidecar.reload()

    assert sidecar.lookup("Manuales_Kidde/2x-a_inst.pdf")["equipo"] == "2X-A"
    assert sidecar.lookup("Manuales_Kidde/nope.pdf") is None

    m = detect_document_metadata("Manuales_Kidde/2x-a_inst.pdf", "")
    assert (m.manufacturer, m.distributor, m.product_model) == ("Aritech", "Kidde", "2X-A")
    m2 = detect_document_metadata("Manuales_Kidde/ke-dm.pdf", "")
    assert (m2.manufacturer, m2.distributor, m2.product_model) == ("Kidde", None, "KE-DM3010R")

    # robustez: una ruta ABSOLUTA también resuelve (antes daba None → Capa B se
    # desactivaba en silencio; hallazgo del cross-model).
    assert sidecar.lookup(str(folder / "2x-a_inst.pdf")) is not None


def test_old_corpus_untouched():
    """Un doc fuera de los canales del portal no activa el sidecar-reader."""
    assert sidecar.lookup("Manuales_Notifier/AM-8200_manual.pdf") is None


def test_is_portal_channel():
    assert sidecar.is_portal_channel("Manuales_Kidde/x.pdf") is True
    assert sidecar.is_portal_channel("Manuales_Morley/x.pdf") is False


def test_empty_oem_prefix_does_not_capture_everything(tmp_path, monkeypatch):
    """Un override con equipo_prefix vacío (typo YAML) NO debe capturar TODOS los
    docs (toda cadena .startswith('')) — si no, un typo contamina un lote entero."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "portal.yaml").write_text(
        "channels: [Kidde]\noem_overrides:\n  - equipo_prefix: ''\n    manufacturer: WRONG\n",
        encoding="utf-8")
    monkeypatch.setattr(sidecar, "_PORTAL_CONFIG", str(tmp_path / "config" / "portal.yaml"))
    sidecar.reload()
    assert sidecar.channel_manufacturer("Manuales_Kidde/x.pdf", "KE-DM3010R") == ("Kidde", None)
