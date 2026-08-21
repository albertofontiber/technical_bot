"""s331 M2 — cohorte G0-b' del detector de mención no-resuelta.

Canónico: `evals/s331_variantes_hilo_propuesta_v6.md` §3.C.1 (dos puertas asimétricas) y
§4 gate **G0-b'** — «cohorte detector CON los FP de los revisores … 0 FP en puerta 2»;
ítems **B7** (veto multi-fabricante sobre el MULTIMAP término→{fabricantes}) y **B11**
(la cohorte se materializa como fichero en el build) del checklist §11.

Cubre:
  · PUERTA 1 (`detect_unresolved_mentions`, conducta / bajo daño): positivos = la variante
    no gobernada del caso real Kidde y un código inventado con forma de modelo.
  · PUERTA 1, NEGATIVOS OBLIGATORIOS = los falsos positivos NOMBRADOS POR LOS REVISORES
    ('230VAC', '24VDC', 'UNE-23007', 'EN-54', 'ISO9001', solo-dígitos, 'RS-485') + un
    término que SÍ resuelve contra el catálogo gobernado (en grafía canónica y ASR).
  · PUERTA 2 (`mention_route_cut_eligible`, corte-de-ruta / alto daño): extensión de
    término gobernado con cola ≤6 y un solo fabricante ⇒ True; todo lo demás ⇒ False,
    incluido el VETO multi-fabricante (multimap monkeypatcheado).

SIN RED: el detector es file-based (data/catalog/*.jsonl + los dos léxicos de config) y
NO usa la presencia de corpus — el fixture revienta si algún path toca la DB y un test
aserta que la caché `_presence` queda intacta.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.rag import catalog_resolver as CR

pytestmark = pytest.mark.skipif(
    not (Path(CR.ROOT) / "data" / "catalog" / "products.jsonl").exists(),
    reason="catálogo no cargado")


class _RedProhibida(BaseException):
    """Deriva de BaseException A PROPÓSITO (patrón `test_catalog_resolver`): los fail-open
    del resolver capturan `Exception`, así que una fuga a la DB debe REVENTAR el test, no
    degradar en silencio."""


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _boom(*_a, **_k):  # pragma: no cover - solo dispara si hay regresión
        raise _RedProhibida("el detector de menciones tocó red (s331 §3.C.1: prohibido)")

    for fn in ("_load_presence", "_try_corpus_fingerprint", "_corpus_fingerprint",
               "_fetch_corpus_pm_elements", "_inactive_document_ids"):
        monkeypatch.setattr(CR, fn, _boom)
    yield


# ---------------------------------------------------------------------------
# PUERTA 1 — positivos
# ---------------------------------------------------------------------------
def test_puerta1_variante_no_gobernada_del_caso_real():
    """El usuario extiende un término gobernado con una cola que el catálogo NO tiene:
    `detect()` resuelve la FAMILIA ('2x-af1') pero la variante entera no resuelve ⇒ es
    una mención no-resuelta, y se devuelve en la forma SUPERFICIAL del usuario."""
    assert CR.detect_unresolved_mentions(
        "tengo la 2X-AF1-XQ2 instalada", ["2X-AF1"]) == ["2X-AF1-XQ2"]


def test_puerta1_codigo_inventado_con_forma_de_modelo():
    assert CR.detect_unresolved_mentions(
        "¿Es compatible con la TSR-9100?", []) == ["TSR-9100"]


def test_puerta1_dedupe_por_normkey_y_orden_de_aparicion():
    """Dedupe por normkey (la grafía ASR y la canónica son la MISMA mención) y orden de
    aparición: el contrato del output que consume `turn_identity`."""
    out = CR.detect_unresolved_mentions(
        "tengo la 2X-AF1-XQ2, la TSR-9100 y otra vez la 2X-AF1XQ2", [])
    assert out == ["2X-AF1-XQ2", "TSR-9100"]


# ---------------------------------------------------------------------------
# PUERTA 1 — negativos OBLIGATORIOS (los FP nombrados por los revisores, G0-b')
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fp, motivo", [
    ("230VAC", "unidad: 'vac' tras quitar los dígitos iniciales"),
    ("24VDC", "unidad: 'vdc'"),
    ("24kΩ", "unidad: 'kohm' (Ω normalizada)"),
    ("UNE-23007", "norma: prefijo 'une' + dígitos"),
    ("EN-54", "norma: prefijo 'en' + dígitos (y NON_PRODUCT_CODES)"),
    ("ISO9001", "norma: prefijo 'iso' + dígitos"),
    ("IP65", "estanqueidad: 'ip' + dígitos (adjudicación advisor M2 — léxico de normas; "
             "verificado 0 términos gobernados 'ipNN*')"),
    ("2026", "solo-dígitos: no tiene forma de modelo"),
    ("RS-485", "NON_PRODUCT_CODES (seed de la política)"),
])
def test_puerta1_falsos_positivos_de_los_revisores(fp, motivo):
    assert CR.detect_unresolved_mentions(
        f"La instalación es de {fp} según la ficha", []) == [], motivo


@pytest.mark.parametrize("grafia", ["2X-AF1-FB-S", "2X-AF1-FBS"])
def test_puerta1_termino_que_si_resuelve_no_es_mencion(grafia):
    """El caso real del hilo: la variante ESTÁ en el catálogo gobernado (canónica y en
    grafía ASR, `norm_token` absorbe FBS↔FB-S) ⇒ jamás es una mención no-resuelta."""
    assert CR.detect_unresolved_mentions(f"Sobre la {grafia}.", []) == []


def test_espejo_non_product_codes_sin_deriva():
    """CONTRA-DERIVA del bridge de capas (build M2): el contrato de imports prohíbe
    `rag → orchestrator` (`ALLOWED["rag"] = {raiz, ingestion, rag}`,
    `tests/test_import_contract.py`), así que `catalog_resolver` lleva un ESPEJO literal
    del seed `NON_PRODUCT_CODES`. Este test —en `tests/`, capa que el contrato no mira— es
    lo que mantiene UNA sola fuente de verdad: si el seed cambia y el espejo no, CI cae."""
    from src.orchestrator.conversation_policy import NON_PRODUCT_CODES
    assert CR._NON_PRODUCT_CODES_ESPEJO == NON_PRODUCT_CODES


def test_puerta1_excluye_los_modelos_ya_resueltos_del_turno():
    """Exclusión (a) por `resolved_models`: un código que NO está en el catálogo pero que
    el turno ya trae bindeado no vuelve a proponerse como mención."""
    assert CR.detect_unresolved_mentions(
        "¿Es compatible con la TSR-9100?", ["TSR-9100"]) == []


def test_puerta1_no_toca_la_presencia_de_corpus(monkeypatch):
    monkeypatch.setattr(CR, "_presence", None)
    assert CR.detect_unresolved_mentions("tengo la 2X-AF1-XQ2 instalada", []) == [
        "2X-AF1-XQ2"]
    assert CR._presence is None      # el detector no consulta ni calienta la presencia


# ---------------------------------------------------------------------------
# PUERTA 2 — corte-de-ruta (0 FP exigido por G0-b')
# ---------------------------------------------------------------------------
def test_puerta2_extension_de_termino_gobernado():
    """'2X-AF1-XQ2' extiende el término GOBERNADO COMPLETO '2X-AF1' (kidde:2x-af1, un solo
    fabricante) con cola 'XQ2' (3 ≤ 6) ⇒ elegible para cortar ruta."""
    assert CR.mention_route_cut_eligible("2X-AF1-XQ2") is True


@pytest.mark.parametrize("mencion, motivo", [
    ("230VAC", "unidad — y no extiende ningún término gobernado"),
    ("SLC1", "sin prefijo gobernado: 'slc' no es término del catálogo"),
    ("UNE-23007", "norma"),
    ("2X-AF1", "el término EXACTO no es una extensión (cola vacía)"),
    ("2X-AF1-XQ2345678", "cola de 9 > 6: ya no tiene forma de sufijo de variante"),
])
def test_puerta2_negativos(mencion, motivo):
    assert CR.mention_route_cut_eligible(mencion) is False, motivo


def test_puerta2_veto_multifabricante(monkeypatch):
    """(ítem B7 §11) Si el término ganador mapea a MÁS DE UN fabricante, la mención NO
    corta ruta (cae a puerta 1). El multimap se monkeypatchea porque el catálogo real no
    tiene hoy esa colisión en '2xaf1' — y el índice normal del catálogo la ocultaría al
    colapsar cada normkey a un solo producto."""
    real = dict(CR._governed_term_manufacturers())
    assert real["2xaf1"] == frozenset({"Kidde Commercial"})   # premisa del caso positivo
    real["2xaf1"] = frozenset({"Kidde Commercial", "Marca Fantasma"})
    monkeypatch.setattr(CR, "_governed_term_manufacturers", lambda: real)
    assert CR.mention_route_cut_eligible("2X-AF1-XQ2") is False


def test_puerta2_termino_sin_fabricante_no_corta(monkeypatch):
    """Dirección segura de la puerta de alto daño: un término cuyo fabricante no es
    verificable (multimap sin entrada) tampoco corta ruta."""
    real = dict(CR._governed_term_manufacturers())
    real["2xaf1"] = frozenset()
    monkeypatch.setattr(CR, "_governed_term_manufacturers", lambda: real)
    assert CR.mention_route_cut_eligible("2X-AF1-XQ2") is False
