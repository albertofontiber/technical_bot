# -*- coding: utf-8 -*-
"""s323 fase C — el gate de identidad falla por lo NUEVO, no por lo gobernado.

Diseño (dúo r32): los invariantes se formulan sobre el PUNTERO (`document_id`),
nunca sobre `source_file` — el nombre solo corrobora una identidad ya ligada, así
que usarlo como clave contradiría el contrato canónico. Y las violaciones
preexistentes viven en un manifiesto versionado: un gate permanentemente rojo es
un gate que nadie mira.
"""
import json

import src.rag.identidad_gate as gate


def test_clave_de_violacion_es_el_puntero_no_el_nombre():
    """La identidad de una violación es su document_id (o chunk_id), jamás el
    nombre de fichero: dos revisiones distintas comparten nombre."""
    k = gate._clave("I2_puntero_no_activo",
                    {"document_id": "doc-1", "source_file": "MANUAL.pdf"})
    assert "doc-1" in k and "MANUAL.pdf" not in k
    k5 = gate._clave("I5_chunks_huerfanos",
                     {"chunk_id": "ch-9", "source_file": "MANUAL.pdf"})
    assert "ch-9" in k5 and "MANUAL.pdf" not in k5


def _evaluar_con(monkeypatch, tmp_path, censo, manifiesto=None):
    monkeypatch.setattr(gate, "_censo", lambda c: censo)
    monkeypatch.setattr(gate, "abierto",
                        lambda **k: __import__("contextlib").nullcontext(None))
    m = tmp_path / "excepciones.json"
    if manifiesto is not None:
        m.write_text(json.dumps({"excepciones": manifiesto}), encoding="utf-8")
    monkeypatch.setattr(gate, "MANIFIESTO", m)
    return gate.evaluar()


VACIO = {"I1_puntero_inexistente": [], "I2_puntero_no_activo": [],
         "I3_puntero_sin_chunks": [], "I4_document_id_duplicado": [],
         "I5_chunks_huerfanos": []}


def test_sin_violaciones_pasa(monkeypatch, tmp_path):
    v = _evaluar_con(monkeypatch, tmp_path, dict(VACIO))
    assert v["ok"] and v["nuevas"] == 0


def test_violacion_preexistente_NO_tiñe_de_rojo(monkeypatch, tmp_path):
    """Las 72 conocidas están gobernadas: si tiñeran cada ejecución, nadie
    miraría el gate y volveríamos al punto de partida."""
    censo = {**VACIO, "I2_puntero_no_activo": [{"document_id": "viejo",
                                                "source_file": "x", "status": "retired"}]}
    v = _evaluar_con(monkeypatch, tmp_path, censo,
                     manifiesto={"I2_puntero_no_activo|viejo": {"motivo": "preexistente"}})
    assert v["ok"] and v["nuevas"] == 0 and v["total"] == 1


def test_violacion_NUEVA_rompe_el_gate(monkeypatch, tmp_path):
    censo = {**VACIO, "I3_puntero_sin_chunks": [{"document_id": "nuevo",
                                                 "source_file": "y"}]}
    v = _evaluar_con(monkeypatch, tmp_path, censo, manifiesto={})
    assert not v["ok"] and v["nuevas"] == 1
    assert v["detalle_nuevas"][0]["invariante"] == "I3_puntero_sin_chunks"


def test_huerfano_nuevo_se_distingue_por_chunk(monkeypatch, tmp_path):
    """Un huérfano nuevo en un fichero que YA tenía huérfanos gobernados debe
    detectarse: por eso la clave es el chunk, no el documento ni el nombre."""
    censo = {**VACIO, "I5_chunks_huerfanos": [{"chunk_id": "ch-viejo", "source_file": "z"},
                                              {"chunk_id": "ch-nuevo", "source_file": "z"}]}
    v = _evaluar_con(monkeypatch, tmp_path, censo,
                     manifiesto={"I5_chunks_huerfanos|ch-viejo": {"motivo": "preexistente"}})
    assert not v["ok"] and v["nuevas"] == 1
    assert v["detalle_nuevas"][0]["chunk_id"] == "ch-nuevo"
