"""Tests de src/rag/must_preserve.py (S269 Track 2, diseño v2 dúo-adjudicado).

Pinean por familia (positivo/negativo/borde), el binding conservador, la attestation
fail-closed, la disclosure ante contradicción, el cap 4 del anexo y el passthrough
byte-idéntico con flag off. Casos SINTÉTICOS: la Etapa 1 (cohorte fresca + gold
independiente Luna/Haiku) es la medición real — estos tests fijan el CONTRATO."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.rag import must_preserve as mp


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("MUST_PRESERVE_CONTRACT", raising=False)
    yield


def _atoms(text, family=None):
    atoms = mp.detect_atoms(text)
    if family:
        atoms = [a for a in atoms if a["family"] == family]
    return atoms


# ─── flag (patrón _strict_on_off) ───

def test_flag_default_off():
    assert mp.contract_enabled() is False


def test_flag_on(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    assert mp.contract_enabled() is True


def test_flag_invalido_fail_fast(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "banana")
    with pytest.raises(RuntimeError, match="MUST_PRESERVE_CONTRACT"):
        mp.contract_enabled()


def test_flag_off_passthrough_byte_identico():
    """Con flag off apply devuelve el MISMO objeto respuesta (pipeline intacto)."""
    draft = "Respuesta cualquiera [F1]"
    out, trace = mp.apply_must_preserve_contract("query", [{"content": "x"}], draft)
    assert out is draft
    assert trace is None


# ─── F-RANGE ───

def test_range_con_paso_y_unidad():
    atoms = _atoms(
        "El tiempo de extinción se programa de 05 a 295 segundos, "
        "en intervalos de 5 segundos.",
        mp.FAMILY_RANGE,
    )
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["lower"] == 5.0
    assert meta["upper"] == 295.0
    assert meta["step"] == 5.0
    assert meta["unit"] == "segundos"


def test_range_scope_adyacente():
    atoms = _atoms(
        "En las posiciones A11 a C32 el umbral admite de 20 a 120 %.",
        mp.FAMILY_RANGE,
    )
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["lower"] == 20.0 and meta["upper"] == 120.0
    assert meta["scope"] == ["A11", "C32"]


def test_range_sin_paso_sigue_disparando():
    atoms = _atoms("La tensión de lazo va de 10 a 30 V.", mp.FAMILY_RANGE)
    assert len(atoms) == 1
    assert atoms[0]["meta"]["step"] is None


def test_range_dash_requiere_unidad():
    # un código de modelo con guiones NO es un rango
    assert _atoms("La central CAD-150-8 dispone del módulo MB.", mp.FAMILY_RANGE) == []
    assert len(_atoms("Alimentación 230-240 V según placa.", mp.FAMILY_RANGE)) == 1


def test_range_tolerancia_simetrica():
    atoms = _atoms("La tensión de salida admite ±10 % de desviación.", mp.FAMILY_RANGE)
    assert len(atoms) == 1
    assert atoms[0]["meta"]["tolerance"] == 10.0


def test_range_siete_segmentos_excluido():
    # riesgo OCR de display (r.I): la oración con rango queda FUERA del anexo automático
    atoms = _atoms(
        "El display muestra r.I durante el rearme de 0 a 9 segundos.",
        mp.FAMILY_RANGE,
    )
    assert atoms == []


# ─── F-BUNDLE ───

def test_bundle_heading_con_miembros():
    atoms = _atoms(
        "## Pestaña Programa\n"
        "- Zona: define la zona del punto\n"
        "- CBE: ecuación de control por evento",
        mp.FAMILY_BUNDLE,
    )
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["header"] == "Pestaña Programa"
    assert meta["members"] == ["Zona", "CBE"]
    assert "Pestaña Programa" in atoms[0]["span_text"]


def test_bundle_heading_sin_miembros_no_dispara():
    atoms = _atoms(
        "## Mantenimiento\nEl equipo requiere revisión periódica.",
        mp.FAMILY_BUNDLE,
    )
    assert atoms == []


def test_bundle_schema_definicion_sin_heading():
    atoms = _atoms(
        "Entrada: condición que dispara la regla\n"
        "Salida: acción que se ejecuta sobre el equipo asignado",
        mp.FAMILY_BUNDLE,
    )
    assert len(atoms) == 1
    assert atoms[0]["meta"]["members"] == ["Entrada", "Salida"]


def test_bundle_un_solo_miembro_no_dispara():
    atoms = _atoms("## Opciones\n- Retardo: tiempo de espera", mp.FAMILY_BUNDLE)
    assert atoms == []


# ─── F-MANDATORY ───

def test_mandatory_imprescindible():
    atoms = _atoms(
        "Es imprescindible aislar las zonas de extinción antes de la puesta en marcha.",
        mp.FAMILY_MANDATORY,
    )
    assert len(atoms) == 1
    assert "imprescindible" in atoms[0]["meta"]["triggers"]


def test_mandatory_antes_de_solo_no_dispara():
    # hallazgo F8 del dúo: "antes de" NUNCA como gatillo solo
    assert _atoms(
        "Antes de continuar, pulse la tecla MENU y espere.", mp.FAMILY_MANDATORY
    ) == []


def test_mandatory_before_solo_no_dispara():
    assert _atoms(
        "Before continuing, press the MENU key.", mp.FAMILY_MANDATORY
    ) == []


def test_mandatory_debe_mas_antes_de_dispara():
    atoms = _atoms(
        "El técnico debe desconectar la alimentación antes de abrir la envolvente.",
        mp.FAMILY_MANDATORY,
    )
    assert len(atoms) == 1
    assert "debe(n)+antes de" in atoms[0]["meta"]["triggers"]


def test_mandatory_must_not_dispara():
    atoms = _atoms(
        "The loop cable must not exceed the rated impedance.", mp.FAMILY_MANDATORY
    )
    assert len(atoms) == 1


# ─── F-COUNT ───

def test_count_consistente_no_dispara():
    assert _atoms(
        "Dispone de tres modos:\n- Modo A\n- Modo B\n- Modo C", mp.FAMILY_COUNT
    ) == []


def test_count_inconsistente_dispara_con_conflict():
    atoms = _atoms(
        "La central ofrece seis opciones de programación:\n"
        "- Retardo\n- Sensibilidad\n- Zona\n- Sirena\n- Reloj\n- Acceso\n- Volcado",
        mp.FAMILY_COUNT,
    )
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["declared_n"] == 6
    assert meta["enumerated_n"] == 7
    assert meta["conflict"] is True


def test_count_sin_enumeracion_no_dispara():
    assert _atoms("El panel soporta ocho zonas de detección.", mp.FAMILY_COUNT) == []


# ─── binding (conservador: en duda NO exigible) ───

_RANGE_TEXT = "La tensión de lazo va de 10 a 30 V, en pasos de 5 V."


def test_bind_fragmento_no_citado():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "La tensión de lazo llega a 30 V [F2]"
    assert mp.bind_atoms(atoms, draft, {2}, 1) == []


def test_bind_conservador_sin_toque_del_ancla():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "La central dispone de teclado frontal retroiluminado [F1]"
    assert mp.bind_atoms(atoms, draft, {1}, 1) == []


def test_bind_por_numero_exacto():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "La tensión máxima del lazo es 30 V [F1]"
    bound = mp.bind_atoms(atoms, draft, {1}, 1)
    assert [a["family"] for a in bound] == [mp.FAMILY_RANGE]


def test_bind_por_entidad_del_heading():
    atoms = mp.detect_atoms(
        "## Pestaña Programa\n- Zona: define la zona\n- CBE: ecuación de control"
    )
    draft = "Los puntos se configuran en la pestaña Programa [F3]"
    bound = mp.bind_atoms(atoms, draft, {3}, 3)
    assert [a["family"] for a in bound] == [mp.FAMILY_BUNDLE]


# ─── atom_satisfied ───

def test_range_satisfecho_no_va_al_anexo():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "El lazo admite de 10 a 30 V en pasos de 5 V [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is True


def test_range_incompleto_es_missing():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "La tensión máxima del lazo es 30 V [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is False


def test_bundle_miembro_perdido_es_missing():
    atoms = mp.detect_atoms(
        "## Pestaña Programa\n- Zona: define la zona\n- CBE: ecuación de control"
    )
    draft = "En la pestaña Programa se define la Zona del punto [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is False  # falta CBE


# ─── attestation (fail-closed del anexo) ───

def _fake_catalog():
    return SimpleNamespace(
        doc_map=[
            {
                "document_id": "doc-1",
                "source_file": "manual_cad150",
                "entries": [{"id": "detnov:cad-150", "role": "primary"}],
            }
        ],
        follow_redirect=lambda x: x,
    )


def test_attest_identity_ok():
    assert mp.attest_identity("doc-1", {"detnov:cad-150"}, _fake_catalog()) is True


def test_attest_identity_doc_de_otra_identidad():
    assert mp.attest_identity("doc-1", {"notifier:id3000"}, _fake_catalog()) is False


def test_attest_identity_sin_resolucion_fail_closed():
    assert mp.attest_identity("doc-1", set(), _fake_catalog()) is False
    assert mp.attest_identity(None, {"detnov:cad-150"}, _fake_catalog()) is False


def test_attest_identity_doc_desconocido():
    assert mp.attest_identity("doc-999", {"detnov:cad-150"}, _fake_catalog()) is False


# ─── render_appendix ───

def _mandatory_atom(n):
    return {
        "family": mp.FAMILY_MANDATORY,
        "span_start": 0,
        "span_end": 10,
        "span_text": f"Advertencia sintética número {n}.",
        "anchor_tokens": ["advertencia"],
        "meta": {"triggers": ["advertencia"], "fragment_number": 1},
    }


def test_render_cap_4():
    appendix = mp.render_appendix([_mandatory_atom(i) for i in range(6)], "draft")
    lines = appendix.split("\n")
    assert lines[0] == mp.APPENDIX_HEADER
    assert len(lines) == 1 + mp.APPENDIX_CAP


def test_render_sin_la_palabra_verificada():
    appendix = mp.render_appendix([_mandatory_atom(1)], "draft")
    assert "verificada" not in appendix.lower()
    assert "[F1]" in appendix


def test_render_contradiccion_numerica_disclosure():
    atoms = mp.detect_atoms("El rango de tensión es de 10 a 30 V.")
    atoms[0]["meta"]["fragment_number"] = 2
    draft = "El rango de tensión es de 10 a 25 V [F2]"
    appendix = mp.render_appendix(atoms, draft)
    assert "Nota: el manual también indica:" in appendix
    assert "[F2]" in appendix


def test_render_sin_contradiccion_sin_nota():
    atoms = mp.detect_atoms("El rango de tensión es de 10 a 30 V.")
    atoms[0]["meta"]["fragment_number"] = 2
    appendix = mp.render_appendix(atoms, "La central se programa desde el teclado [F2]")
    assert "Nota:" not in appendix
    assert '"El rango de tensión es de 10 a 30 V."' in appendix


def test_render_count_conflict_siempre_disclosure():
    atoms = mp.detect_atoms(
        "La central ofrece seis opciones:\n- A\n- B\n- C\n- D\n- E\n- F\n- G"
    )
    atoms[0]["meta"]["fragment_number"] = 1
    appendix = mp.render_appendix(atoms, "Hay seis opciones [F1]")
    assert "Nota: el manual también indica:" in appendix


# ─── apply end-to-end (con seams monkeypatcheados, $0) ───

def _wire(monkeypatch, resolved):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: set(resolved))
    monkeypatch.setattr(mp, "_load_catalog", _fake_catalog)


def test_apply_anexa_atomo_missing(monkeypatch):
    _wire(monkeypatch, {"detnov:cad-150"})
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "La tensión máxima del lazo es 30 V [F1]"
    out, trace = mp.apply_must_preserve_contract("cad-150", chunks, draft)
    assert out.startswith(draft)
    assert mp.APPENDIX_HEADER in out
    assert "de 10 a 30 V" in out
    assert trace["appendix_appended"] is True
    assert trace["atoms_appended"] >= 1


def test_apply_attestation_falla_no_anexa(monkeypatch):
    # el doc del fragmento NO pertenece a la identidad resuelta → anexo inerte
    _wire(monkeypatch, {"notifier:id3000"})
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "La tensión máxima del lazo es 30 V [F1]"
    out, trace = mp.apply_must_preserve_contract("id3000", chunks, draft)
    assert out is draft
    assert trace["appendix_appended"] is False


def test_apply_sin_identidad_resuelta_no_anexa(monkeypatch):
    _wire(monkeypatch, set())
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "La tensión máxima del lazo es 30 V [F1]"
    out, trace = mp.apply_must_preserve_contract("query sin modelo", chunks, draft)
    assert out is draft
    assert trace["reason"] == "identity_unresolved"


def test_apply_fragmento_no_citado_no_anexa(monkeypatch):
    _wire(monkeypatch, {"detnov:cad-150"})
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "La tensión máxima del lazo es 30 V"  # sin [F1]
    out, trace = mp.apply_must_preserve_contract("cad-150", chunks, draft)
    assert out is draft
    assert trace["appendix_appended"] is False


def test_apply_satisfecho_no_anexa(monkeypatch):
    _wire(monkeypatch, {"detnov:cad-150"})
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "El lazo admite de 10 a 30 V en pasos de 5 V [F1]"
    out, trace = mp.apply_must_preserve_contract("cad-150", chunks, draft)
    assert out is draft
    assert trace["atoms_bound"] >= 1
    assert trace["atoms_missing"] == 0
