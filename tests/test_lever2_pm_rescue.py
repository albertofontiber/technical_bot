"""Brazo B (s72): rescate de product_model MAL-ATRIBUIDO en _filter_to_query_models,
tras flag LEVER2_PM_RESCUE (default OFF = paridad con el comportamiento histórico).

cat013: la query cross-marca 'central Detnov CAD-150 + detector Notifier SDX-751' pierde
los chunks SDX-751 porque su product_model está mis-atribuido a LOCAL-360 (TECH_DEBT
#43/#18-mfr); el filtro de modelo los expulsa. El rescate los recupera con guarda por
manufacturer (anti cross-brand): marca desconocida o equivocada → NO rescata.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.retriever import _filter_to_query_models  # noqa: E402


def _chunk(cid, pm, mfr, sf="doc", content=""):
    return {"id": cid, "product_model": pm, "manufacturer": mfr,
            "source_file": sf, "content": content}


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    monkeypatch.delenv("LEVER2_PM_RESCUE", raising=False)
    yield


MODELS = ["CAD-150", "SDX-751"]   # CAD-150=Detnov, SDX-751=Notifier (cross-marca cat013)


def _pool():
    # 3 CAD-150 correctos (Detnov) + 1 SDX-751 mis-atribuido a LOCAL-360 (Notifier)
    return [
        _chunk("c1", "CAD-150", "Detnov"),
        _chunk("c2", "CAD-150", "Detnov"),
        _chunk("c3", "CAD-150", "Detnov"),
        _chunk("sdx", "LOCAL-360", "Notifier", sf="I56-1320-001 SDX-751TEM datasheet"),
    ]


def _ids(chunks):
    return {c["id"] for c in chunks}


def test_rescate_off_es_paridad():
    """Flag OFF: el SDX-751 mis-atribuido NO se rescata (comportamiento histórico)."""
    out = _filter_to_query_models(_pool(), MODELS)
    assert "sdx" not in _ids(out)
    assert _ids(out) == {"c1", "c2", "c3"}


def test_rescate_on_recupera_misatribuido(monkeypatch):
    """Flag ON: el chunk SDX-751 (mfr Notifier, token en source_file) se rescata sin
    perder los correctos."""
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    out = _filter_to_query_models(_pool(), MODELS)
    assert "sdx" in _ids(out)
    assert {"c1", "c2", "c3"} <= _ids(out)


def test_rescate_on_guarda_cross_brand(monkeypatch):
    """Flag ON: un chunk con el token SDX-751 pero manufacturer EQUIVOCADO (Detnov)
    NO se rescata (guarda anti-cross-brand); el legítimo (Notifier) sí."""
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    pool = _pool() + [_chunk("decoy", "XYZ", "Detnov", sf="ref a SDX-751 mencionado")]
    out = _filter_to_query_models(pool, MODELS)
    assert "decoy" not in _ids(out)
    assert "sdx" in _ids(out)


def test_rescate_on_marca_desconocida_no_rescata(monkeypatch):
    """Flag ON: un modelo de marca desconocida con 0 supervivientes NO dispara rescate
    (sin manufacturer conocido = sin guarda fiable → conservador)."""
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    pool = [
        _chunk("c1", "CAD-150", "Detnov"),
        _chunk("c2", "CAD-150", "Detnov"),
        _chunk("c3", "CAD-150", "Detnov"),
        _chunk("b", "WHATEVER", "BogusBrand", sf="BOGUS-999 datasheet"),
    ]
    out = _filter_to_query_models(pool, ["CAD-150", "BOGUS-999"])
    assert "b" not in _ids(out)


def test_invariante_single_model_nunca_cambia(monkeypatch):
    """Invariante (dúo s72): una query de 1 SOLO modelo NUNCA cambia bajo el rescate.
    Si tiene supervivientes → no dispara; si tiene 0 → filtered arranca en 0, el rescate
    aporta cap=2 < umbral fail-open=3 → el fail-open devuelve los originales igual que
    con el flag OFF. Restringe el blast-radius PASS-control a los golds multi-modelo."""
    pool = [
        _chunk("a", "OTHER", "Notifier", sf="SDX-751 datasheet"),
        _chunk("b", "OTHER", "Notifier", sf="SDX-751 manual"),
        _chunk("c", "OTHER", "Detnov", sf="algo"),
    ]
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    out_on = _filter_to_query_models([dict(c) for c in pool], ["SDX-751"])
    monkeypatch.delenv("LEVER2_PM_RESCUE", raising=False)
    out_off = _filter_to_query_models([dict(c) for c in pool], ["SDX-751"])
    assert _ids(out_on) == _ids(out_off)   # idéntico: fail-open en ambos (2 < 3)


def test_rescate_solo_source_file_no_content(monkeypatch):
    """Enmienda dúo s72: el rescate machea SOLO source_file, NO content. Un chunk del
    mismo fabricante que menciona el token solo en prosa (content) NO se rescata."""
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    pool = [
        _chunk("c1", "CAD-150", "Detnov"),
        _chunk("c2", "CAD-150", "Detnov"),
        _chunk("c3", "CAD-150", "Detnov"),
        # Notifier, token SOLO en content (prosa) → NO debe colarse
        _chunk("prosa", "OTRO", "Notifier", sf="doc-notifier",
               content="comparativa contra el SDX-751 de la competencia"),
        # Notifier, token en source_file → SÍ se rescata
        _chunk("real", "LOCAL-360", "Notifier", sf="I56-1320-001 SDX-751TEM"),
    ]
    out = _filter_to_query_models(pool, MODELS)
    assert "prosa" not in _ids(out)        # content-match desactivado
    assert "real" in _ids(out)             # source_file-match sí


def test_rescate_on_no_rescata_si_modelo_ya_tiene_supervivientes(monkeypatch):
    """Flag ON: si el modelo YA tiene chunks por substring, no se rescata de más
    (el rescate es solo para cores con CERO supervivientes)."""
    monkeypatch.setenv("LEVER2_PM_RESCUE", "1")
    pool = [
        _chunk("c1", "CAD-150", "Detnov"),
        _chunk("c2", "CAD-150", "Detnov"),
        _chunk("c3", "CAD-150", "Detnov"),
        # otro chunk Detnov que menciona CAD-150 pero pm distinto: NO debe colarse,
        # porque cad150 ya tiene supervivientes
        _chunk("x", "CAD-999", "Detnov", sf="CAD-150 mencionado de pasada"),
    ]
    out = _filter_to_query_models(pool, ["CAD-150"])
    assert "x" not in _ids(out)
