"""s332 B6 — sección `asunciones` del trace (tri-estado, patrón turn_identity).

Cubre: tri-estado y coherencia cerrada (sin `on` no hay ítems), cedazo por ítem
(kind/modo enum + asumido token gobernado; `detectado` NO existe en el esquema),
tope de ítems, y el validador del sink rechazando shapes rotos.
"""
from __future__ import annotations

import json

from src.rag.runtime_trace import (
    build_rag_serving_trace,
    validate_rag_serving_trace,
)


def _trace(**overrides):
    base = dict(
        coverage_trace=None,
        served_chunks=[],
        must_preserve_trace=None,
        must_preserve_outcome=None,
        release_policy={"profile": "legacy"},
        transport_parts=1,
    )
    base.update(overrides)
    return build_rag_serving_trace(**base)


def test_sin_cablear_es_not_wired_y_valida():
    trace = _trace()
    assert trace["asunciones"] == {"status": "not_wired", "n": 0, "items": []}
    assert validate_rag_serving_trace(trace) == trace


def test_off_explicito_no_degrada_a_not_wired():
    trace = _trace(asunciones_obs={"status": "off"})
    assert trace["asunciones"]["status"] == "off"
    assert trace["asunciones"]["n"] == 0


def test_on_con_items_validos_y_privacidad():
    obs = {"status": "on", "items": [
        {"kind": "marca_asr", "modo": "reescrito", "asumido": "Kidde"},
        {"kind": "marca_corregida", "modo": "reescrito", "asumido": "Kidde"},
        {"kind": "marca_asr", "modo": "aviso", "asumido": "Kidde",
         "detectado": "BQide"},  # se DESCARTA el campo extra, no el ítem entero…
    ]}
    trace = _trace(asunciones_obs=obs)
    sec = trace["asunciones"]
    assert sec["status"] == "on" and sec["n"] == len(sec["items"])
    # …y `detectado` (contenido ASR/usuario) JAMÁS aparece en el trace:
    assert "detectado" not in json.dumps(trace)
    assert "BQide" not in json.dumps(trace)
    assert validate_rag_serving_trace(trace) == trace


def test_items_invalidos_se_descartan_uno_a_uno():
    obs = {"status": "on", "items": [
        {"kind": "marca_asr", "modo": "reescrito", "asumido": "Kidde"},
        {"kind": "otro", "modo": "reescrito", "asumido": "Kidde"},        # kind fuera de enum
        {"kind": "marca_asr", "modo": "quiza", "asumido": "Kidde"},       # modo fuera de enum
        {"kind": "marca_asr", "modo": "aviso", "asumido": "x" * 60},      # token demasiado largo
        "no-es-mapping",
    ]}
    sec = _trace(asunciones_obs=obs)["asunciones"]
    assert sec["n"] == 1 and sec["items"][0]["asumido"] == "Kidde"


def test_tope_de_items():
    obs = {"status": "on", "items": [
        {"kind": "marca_asr", "modo": "aviso", "asumido": f"M{i}"} for i in range(20)
    ]}
    assert _trace(asunciones_obs=obs)["asunciones"]["n"] == 8


def test_validador_rechaza_shapes_rotos():
    base = _trace(asunciones_obs={"status": "on", "items": [
        {"kind": "marca_asr", "modo": "reescrito", "asumido": "Kidde"}]})
    roto_n = json.loads(json.dumps(base))
    roto_n["asunciones"]["n"] = 3  # n ≠ len(items)
    assert validate_rag_serving_trace(roto_n) is None
    roto_items = json.loads(json.dumps(base))
    roto_items["asunciones"]["items"] = [{"kind": "marca_asr", "modo": "reescrito"}]
    assert validate_rag_serving_trace(roto_items) is None
    roto_coherencia = json.loads(json.dumps(base))
    roto_coherencia["asunciones"]["status"] = "off"  # off con ítems
    assert validate_rag_serving_trace(roto_coherencia) is None
    sin_seccion = {k: v for k, v in base.items() if k != "asunciones"}
    assert validate_rag_serving_trace(sin_seccion) is None
