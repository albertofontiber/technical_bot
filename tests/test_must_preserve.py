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


def test_range_siete_segmentos_marcado_no_excluido():
    # v2 (funnel probe-1 hp011): el riesgo OCR ya no excluye en detección — se MARCA
    # y la exclusión con paridad de display vive en la selección del anexo
    atoms = _atoms(
        "El display muestra r.I durante el rearme de 0 a 9 segundos.",
        mp.FAMILY_RANGE,
    )
    assert len(atoms) == 1
    assert atoms[0]["meta"]["seven_segment_risk"] is True


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


# ─── binding C2: claim-proximity por ventana de cita (spec v3 §A.1) ───

def test_bind_cross_binding_numero_junto_a_otra_cita():
    """CRÍTICO C2 (Sol): la respuesta cita F1 pero el número compartido está en el
    contexto de F2 → el átomo de F1 NO es exigible (antes ligaba por escaneo de toda
    la respuesta y anexaba evidencia ajena)."""
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = (
        "La central dispone de un teclado retroiluminado [F1]. "
        "La tensión máxima del lazo es 30 V [F2]"
    )
    assert mp.bind_atoms(atoms, draft, {1, 2}, 1) == []


def test_bind_ventana_de_su_propia_cita_si_liga():
    """El mismo borrador SÍ liga cuando el átomo pertenece al fragmento 2 (el número
    está en la ventana de SU cita)."""
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = (
        "La central dispone de un teclado retroiluminado [F1]. "
        "La tensión máxima del lazo es 30 V [F2]"
    )
    bound = mp.bind_atoms(atoms, draft, {1, 2}, 2)
    assert [a["family"] for a in bound] == [mp.FAMILY_RANGE]


def test_bind_sin_cita_localizable_no_exigible():
    """cited_fragment_ids dice que F1 está citado pero el literal [F1] no aparece en
    el borrador → sin ventana localizable → conservador: nada exigible."""
    atoms = mp.detect_atoms(_RANGE_TEXT)
    assert mp.bind_atoms(atoms, "La tensión máxima del lazo es 30 V", {1}, 1) == []


def test_citation_window_une_oraciones_de_la_misma_cita():
    draft = "El rango va de 10 a 30 V [F1]. Otro dato [F2]. El paso es de 5 V [F1]."
    window = mp.citation_window(draft, 1)
    assert "10 a 30 V" in window and "paso es de 5 V" in window
    assert "Otro dato" not in window
    assert mp.citation_window(draft, 3) == ""


# ─── binding v2: presencia PARCIAL por familia (adjudicación post-seed-270, s243) ───

def test_bind_v2_solape_generico_de_anchors_ya_no_liga():
    """La clase de los 36 clean-FP de seed-270: un borrador que comparte ≥2 anchors
    GENÉRICOS de la oración del átomo pero ningún material PROPIO (números/scope)
    ya NO es exigible."""
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "La tensión del lazo se mide en la placa de bornes [F1]"
    assert mp.bind_atoms(atoms, draft, {1}, 1) == []


def test_bind_v2_numero_propio_si_liga():
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "El valor máximo admitido es 30 en esa posición [F1]"
    bound = mp.bind_atoms(atoms, draft, {1}, 1)
    assert [a["family"] for a in bound] == [mp.FAMILY_RANGE]


def test_bind_v3_bundle_dos_tokens_propios_ligan():
    """Apriete adjudicado post-seed-271: ≥2 tokens propios (aquí: 1 de miembro +
    1 de la cabecera)."""
    atoms = mp.detect_atoms(
        "## Pestaña Programa\n- Zona: define la zona\n- CBE: ecuación de control"
    )
    draft = "El campo CBE de la pestaña se configura primero [F1]"
    bound = mp.bind_atoms(atoms, draft, {1}, 1)
    assert [a["family"] for a in bound] == [mp.FAMILY_BUNDLE]


def test_bind_v3_bundle_un_solo_token_propio_ya_no_liga():
    """La clase de los 14 FP residuales de seed-271: UNA palabra técnica ubicua
    de un miembro no basta para hacer exigible el bundle."""
    atoms = mp.detect_atoms(
        "## Pestaña Programa\n- Zona: define la zona\n- CBE: ecuación de control"
    )
    draft = "El campo CBE controla la activación [F1]"  # 1 token propio (cbe)
    assert mp.bind_atoms(atoms, draft, {1}, 1) == []


_MANDATORY_FRAG = (
    "1. Pulse la tecla MENU para entrar en programación.\n"
    "2. Seleccione la zona de extinción con las flechas.\n"
    "Advertencia: desconecte la alimentación general antes de manipular el lazo."
)


def test_bind_v2_mandatory_exigible_con_contexto_procedimental():
    """s243 mandatory_safety_omission: la respuesta DA el procedimiento del
    fragmento → el callout adyacente es exigible."""
    atoms = [a for a in mp.detect_atoms(_MANDATORY_FRAG)
             if a["family"] == mp.FAMILY_MANDATORY]
    assert len(atoms) == 1
    assert atoms[0]["meta"]["procedural_context_tokens"]
    draft = "Para programar, pulse la tecla MENU y seleccione la zona [F1]"
    assert mp.bind_atoms(atoms, draft, {1}, 1) == atoms


def test_bind_v2_mandatory_no_exigible_sin_contexto_procedimental():
    atoms = [a for a in mp.detect_atoms(_MANDATORY_FRAG)
             if a["family"] == mp.FAMILY_MANDATORY]
    draft = "El panel dispone de cuatro salidas supervisadas [F1]"
    assert mp.bind_atoms(atoms, draft, {1}, 1) == []


def test_bind_v2_mandatory_duplicado_jamas_se_anexa():
    """Supresión de duplicados: cláusula ya presente → satisfied → nunca al anexo."""
    atoms = [a for a in mp.detect_atoms(_MANDATORY_FRAG)
             if a["family"] == mp.FAMILY_MANDATORY]
    draft = (
        "Pulse la tecla MENU y seleccione la zona. Advertencia: desconecte la "
        "alimentación general antes de manipular el lazo [F1]"
    )
    bound = mp.bind_atoms(atoms, draft, {1}, 1)
    assert bound == atoms  # exigible (contexto procedimental presente)
    assert mp.atom_satisfied(bound[0], draft) is True  # …pero duplicado → no anexo


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


# ─── atom_satisfied C3: completitud real (spec v3 §A.2) ───

def test_range_sin_unidad_es_missing():
    """CRÍTICO C3 (Sol): los números pelados sin la unidad pareada NO satisfacen el
    F-RANGE (antes la unidad se ignoraba)."""
    atoms = mp.detect_atoms(_RANGE_TEXT)
    draft = "El lazo admite de 10 a 30 en pasos de 5 [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is False


def test_range_sin_scope_es_missing():
    atoms = mp.detect_atoms(
        "En las posiciones A11 a C32 el umbral admite de 20 a 120 %."
    )
    atom = next(a for a in atoms if a["family"] == mp.FAMILY_RANGE)
    assert atom["meta"]["scope"] == ["A11", "C32"]
    sin_scope = "El umbral admite de 20 a 120 % [F1]"
    assert mp.atom_satisfied(atom, sin_scope) is False
    con_scope = "En las posiciones A11 a C32 el umbral admite de 20 a 120 % [F1]"
    assert mp.atom_satisfied(atom, con_scope) is True


_COUNT_CONFLICT_TEXT = (
    "La central ofrece seis opciones de programación:\n"
    "- Retardo\n- Sensibilidad\n- Zona\n- Sirena\n- Reloj\n- Acceso\n- Volcado"
)


def test_count_conflict_numeros_presentes_no_satisface():
    """CRÍTICO C3 (Sol): un F-COUNT en conflicto JAMÁS se satisface por presencia de
    ambos números — eso evitaba justo el disclosure obligatorio (guard s243)."""
    atoms = mp.detect_atoms(_COUNT_CONFLICT_TEXT)
    draft = "Se citan seis opciones y se enumeran siete en total [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is False


def test_count_conflict_solo_disclosure_satisface():
    atoms = mp.detect_atoms(_COUNT_CONFLICT_TEXT)
    draft = (
        "Se declaran seis opciones, pero el manual también indica siete "
        "entradas enumeradas [F1]"
    )
    assert mp.atom_satisfied(atoms[0], draft) is True


def test_bundle_sin_cabecera_es_missing():
    """C3: el bundle exige la cabecera padre, no solo los miembros sueltos."""
    atoms = mp.detect_atoms(
        "## Pestaña Programa\n- Zona: define la zona\n- CBE: ecuación de control"
    )
    draft = "Los campos Zona y CBE definen los puntos del lazo [F1]"
    assert mp.atom_satisfied(atoms[0], draft) is False


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
    # v5 whitelist: la cláusula obligatoria completa (trigger + su oración con verbo)
    return {
        "family": mp.FAMILY_MANDATORY,
        "span_start": 0,
        "span_end": 10,
        "span_text": (
            f"Advertencia sintética {n}: desconecte la alimentación general antes "
            "de manipular el equipo."
        ),
        "anchor_tokens": ["advertencia"],
        "meta": {"triggers": ["advertencia"], "fragment_number": 1},
    }


def _range_atom_n(n, strength_tokens=""):
    return {
        "family": mp.FAMILY_RANGE,
        "span_start": 0,
        "span_end": 10,
        "span_text": f"rango sintético {n} de 10 a {20 + n} V {strength_tokens}",
        "anchor_tokens": ["rango"],
        "meta": {"lower": 10.0, "upper": 20.0 + n, "unit": "v", "fragment_number": 1},
    }


def test_render_cap_global_4_con_familias_mezcladas():
    atoms = (
        [_mandatory_atom(i) for i in range(2)]
        + [_range_atom_n(i) for i in range(3)]
        + [{
            "family": mp.FAMILY_BUNDLE, "span_start": 0, "span_end": 10,
            "span_text": (
                f"## Sección {i}\n- Campo{i}: definición del primer campo\n"
                f"- Extra{i}: descripción del segundo campo"
            ),
            "anchor_tokens": [], "meta": {"header": f"Sección {i}",
                                          "members": [f"Campo{i}", f"Extra{i}"],
                                          "fragment_number": 1},
        } for i in range(2)]
    )
    appendix = mp.render_appendix(atoms, "draft")
    lines = appendix.split("\n")
    assert lines[0] == mp.APPENDIX_HEADER
    assert len(lines) == 1 + mp.APPENDIX_CAP


def test_render_cap_por_familia_2_anti_monopolio():
    # v2 (funnel probe-1 hp002): 6 RANGE missing → solo 2 entran; los slots restantes
    # quedan para otras familias
    atoms = [_range_atom_n(i) for i in range(6)] + [_mandatory_atom(9)]
    selected = mp._select_for_appendix(atoms, "draft")
    families = [a["family"] for a in selected]
    assert families.count(mp.FAMILY_RANGE) == mp.APPENDIX_FAMILY_CAP
    assert mp.FAMILY_MANDATORY in families


def test_seleccion_prioriza_mandatory_y_count_conflict():
    # orden pre-declarado: MANDATORY primero, COUNT-conflicto después, resto por binding
    count_atom = {
        "family": mp.FAMILY_COUNT, "span_start": 0, "span_end": 10,
        "span_text": (
            "La central ofrece seis opciones de programación configurables."
        ),
        "anchor_tokens": ["opciones"],
        "meta": {"declared_n": 6, "enumerated_n": 7, "conflict": True,
                 "fragment_number": 1},
    }
    atoms = [_range_atom_n(i) for i in range(4)] + [count_atom, _mandatory_atom(1)]
    selected = mp._select_for_appendix(atoms, "draft")
    assert selected[0]["family"] == mp.FAMILY_MANDATORY
    assert selected[1]["family"] == mp.FAMILY_COUNT
    assert len(selected) == mp.APPENDIX_CAP


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


# enumeración de FORMA BUENA (v5 whitelist): miembros con descripción y verbos
_ENUM_GOOD = (
    "- Retardo: define el tiempo de espera de las salidas\n"
    "- Sensibilidad: define el umbral con que se activa el detector\n"
    "- Zona: define la zona asignada al punto\n"
    "- Sirena: configura el patrón de la salida acústica\n"
    "- Reloj: define la fecha con que se registran los eventos\n"
    "- Acceso: define el nivel con que se entra al menú\n"
    "- Volcado: permite exportar el registro de eventos"
)


def test_render_count_conflict_siempre_disclosure():
    atoms = mp.detect_atoms(
        "La central ofrece seis opciones de programación al instalador:\n"
        + _ENUM_GOOD
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


# ─── M9: exclusión 7-segmentos CONTEXTUAL (spec v3 §A.6) ───

def test_seven_seg_r_i_minuscula_con_contexto_display():
    # hallazgo 9 de Sol: la versión previa no reconocía el caso canónico minúsculo r.i
    assert mp.has_seven_segment_pattern(
        "El display muestra r.i al finalizar el rearme."
    ) is True


def test_seven_seg_codigo_corto_dr_con_contexto_display():
    assert mp.has_seven_segment_pattern(
        "El display muestra dr durante el retardo de disparo."
    ) is True


def test_seven_seg_sin_contexto_display_no_excluye():
    # A.1 como identificador de sección en prosa: sin contexto display no hay riesgo
    assert mp.has_seven_segment_pattern(
        "La sección A.1 describe el rango de 2 a 8 V."
    ) is False


def test_seven_seg_a1_en_heading_no_excluido():
    # "A.1" es numeración de sección aunque haya vocabulario de display en el bloque
    text = (
        "## A.1 Opciones de display\n"
        "- Zona: muestra la zona activa\n"
        "- CBE: código de la ecuación de control"
    )
    assert mp.has_seven_segment_pattern(text) is False
    atoms = [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_BUNDLE]
    assert len(atoms) == 1
    assert atoms[0]["meta"]["seven_segment_risk"] is False
    assert atoms[0]["meta"]["header"] == "A.1 Opciones de display"


def test_seven_seg_paridad_display_selecciona_solo_con_token_en_borrador():
    # v2 (funnel probe-1 hp011): el átomo con riesgo entra al anexo SOLO si el
    # borrador ya contiene su token display (r.i ≈ rI); sin él, excluido
    atoms = _atoms(
        "El display muestra r.I durante el rearme de 0 a 9 segundos.",
        mp.FAMILY_RANGE,
    )
    assert len(atoms) == 1
    atoms[0]["meta"]["fragment_number"] = 1
    sin_token = mp._select_for_appendix(atoms, "El rearme dura 9 segundos [F1]")
    assert sin_token == []
    con_token = mp._select_for_appendix(
        atoms, "El parámetro rI controla el rearme [F1]"
    )
    assert len(con_token) == 1


def test_display_parity_normaliza_puntos_y_mayusculas():
    assert mp._display_token_in_draft("ri", mp._fold("el parámetro rI"))
    assert mp._display_token_in_draft("ri", mp._fold("el display muestra r.i"))
    assert not mp._display_token_in_draft("ri", mp._fold("la brida del equipo"))
    assert mp.seven_segment_tokens(
        "El display muestra r.I durante el rearme."
    ) == {"ri"}
    assert mp.seven_segment_tokens("sin contexto alguno r.I") == set()


# ─── detector híbrido (spec v3 §B: fast-path det + Haiku con grounding verbatim) ───

_CHAIN_TEXT = (
    "Temperatura de funcionamiento: –10 °C ≤ Ta ≤ +55 °C.\n"
    "El equipo se instala en interior."
)


def _hybrid_payload(**slots):
    payload = {}
    for i in range(1, 9):
        payload[f"atom_{i}_family"] = ""
        payload[f"atom_{i}_span"] = ""
    payload.update(slots)
    return payload


class _FakeAnthropic:
    def __init__(self, payload):
        self.calls = 0
        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.calls += 1
                outer.kwargs = kwargs
                return SimpleNamespace(
                    content=[SimpleNamespace(type="tool_use", input=payload)],
                    usage=SimpleNamespace(input_tokens=111, output_tokens=42),
                )

        self.messages = _Messages()


def test_hybrid_sin_cliente_solo_determinista():
    # sin cliente NO se toca la red y el resultado es el determinista puro
    assert mp.detect_atoms_hybrid(_RANGE_TEXT) == mp.detect_atoms(_RANGE_TEXT)


def test_hybrid_acepta_span_verbatim_con_shape():
    # cadena de desigualdad: el regex determinista NO la cubre (diagnóstico v1);
    # el brazo Haiku la propone con span verbatim y el validador código la acepta
    assert [a for a in mp.detect_atoms(_CHAIN_TEXT)
            if a["family"] == mp.FAMILY_RANGE] == []
    client = _FakeAnthropic(_hybrid_payload(
        atom_1_family="F-RANGE", atom_1_span="–10 °C ≤ Ta ≤ +55 °C",
    ))
    usage = {}
    atoms = mp.detect_atoms_hybrid(_CHAIN_TEXT, client=client, usage=usage)
    hybrid = [a for a in atoms if a["meta"].get("origin") == "hybrid"]
    assert len(hybrid) == 1
    assert hybrid[0]["family"] == mp.FAMILY_RANGE
    assert hybrid[0]["span_text"] == "–10 °C ≤ Ta ≤ +55 °C"
    assert hybrid[0]["meta"]["lower"] == 10.0
    assert hybrid[0]["meta"]["upper"] == 55.0
    assert hybrid[0]["meta"]["unit"] == "°c"
    assert usage == {"input_tokens": 111, "output_tokens": 42, "calls": 1}
    # tool-use FORZADO con schema plano (patrón source_unit_gold)
    assert client.kwargs["tool_choice"] == {"type": "tool", "name": "proponer_atomos"}


def test_hybrid_descarta_span_no_verbatim():
    client = _FakeAnthropic(_hybrid_payload(
        atom_1_family="F-RANGE",
        atom_1_span="-10 °C hasta +55 °C",  # reescrito, NO substring del fragmento
    ))
    atoms = mp.detect_atoms_hybrid(_CHAIN_TEXT, client=client)
    assert [a for a in atoms if a["meta"].get("origin") == "hybrid"] == []


def test_hybrid_descarta_span_sin_shape_de_familia():
    client = _FakeAnthropic(_hybrid_payload(
        # verbatim pero sin números/unidad: no tiene shape F-RANGE
        atom_1_family="F-RANGE", atom_1_span="Temperatura de funcionamiento",
        # verbatim pero sin gatillo del léxico: no tiene shape F-MANDATORY
        atom_2_family="F-MANDATORY", atom_2_span="El equipo se instala en interior.",
        # familia inventada
        atom_3_family="F-INVENTADA", atom_3_span="Temperatura de funcionamiento",
    ))
    atoms = mp.detect_atoms_hybrid(_CHAIN_TEXT, client=client)
    assert [a for a in atoms if a["meta"].get("origin") == "hybrid"] == []


def test_hybrid_no_duplica_atomos_deterministas():
    client = _FakeAnthropic(_hybrid_payload(
        atom_1_family="F-RANGE", atom_1_span="de 10 a 30 V",  # ya cubierto por det
    ))
    atoms = mp.detect_atoms_hybrid(_RANGE_TEXT, client=client)
    assert atoms == mp.detect_atoms(_RANGE_TEXT)


def test_hybrid_schema_es_plano():
    # sin arrays/enums/refs (restricción de dialecto: source_unit_gold)
    schema = mp.hybrid_proposal_schema()
    blob = str(schema)
    assert "'type': 'array'" not in blob
    assert "enum" not in blob and "$ref" not in blob
    assert schema["additionalProperties"] is False


# ─── v2 (DEC-126, funnel probe-1): defline guion · label_run/sección · cross-fragmento ───


def test_bundle_defline_con_separador_guion():
    # funnel probe-1 cat018 F3: "**Zona** - número de zona asignada" (guion, no ':')
    atoms = _atoms(
        "## Pestaña Programa (Programación ecuaciones CBE)\n"
        "**Zona** - número de zona asignada\n"
        "**CBE** - ecuación CBE del punto.",
        mp.FAMILY_BUNDLE,
    )
    assert len(atoms) == 1
    assert atoms[0]["meta"]["members"] == ["Zona", "CBE"]


def test_count_label_run_y_tie_de_seccion():
    # v2: conteo bajo heading + pila de etiquetas OCR tras párrafos explicativos
    text = (
        "## Tipos de retardo\n"
        "Se puede asignar uno de seis tipos de retardo a una regla, como se explica "
        "a continuación.\n"
        "El comportamiento depende de la configuración del sitio y de las teclas "
        "disponibles para el usuario durante el retardo activo en la central.\n"
        "Estándar\n"
        "Fijo\n"
        "Est.Ext.\n"
        "No Silenc.\n"
        "No Sil.Ext\n"
        "RetExtStd\n"
        "SinRetExt\n"
    )
    atoms = [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_COUNT]
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["tie"] == "section"
    assert meta["enumeration_kind"] == "label_run"
    assert meta["declared_n"] == 6
    assert meta["enumerated_n"] == 7
    assert meta["conflict"] is True


def test_count_sin_heading_no_usa_tie_de_seccion():
    text = (
        "Se puede asignar uno de seis tipos de retardo a una regla.\n"
        "El comportamiento depende de la configuración del sitio y de la central "
        "durante todo el retardo activo hasta su finalización completa.\n"
        "Estándar\n"
        "Fijo\n"
        "Est.Ext.\n"
        "No Silenc.\n"
        "RetExtStd\n"
        "SinRetExt\n"
        "Otro\n"
    )
    assert [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_COUNT] == []


def test_cross_fragment_count_detecta_conflicto_pagina_adyacente():
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite seis modos de disparo configurables.",
            "document_id": "doc-1",
            "page_number": 44,
        },
        {
            "fragment_number": 2,
            "text": "- Modo A\n- Modo B\n- Modo C\n- Modo D\n- Modo E\n- Modo F\n- Modo G",
            "document_id": "doc-1",
            "page_number": 44,
        },
    ]
    atoms = mp.detect_cross_fragment_count_atoms(fragments)
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["cross_fragment"] is True
    assert (meta["declared_n"], meta["enumerated_n"]) == (6, 7)
    assert meta["count_fragment_number"] == 1
    assert meta["enum_fragment_number"] == 2
    assert "Modo A" in meta["enum_span_text"]


def test_cross_fragment_count_respeta_documento_y_pagina():
    base = {
        "fragment_number": 1,
        "text": "La central admite seis modos de disparo configurables.",
        "document_id": "doc-1",
        "page_number": 44,
    }
    enum = {
        "fragment_number": 2,
        "text": "- Modo A\n- Modo B\n- Modo C\n- Modo D\n- Modo E\n- Modo F\n- Modo G",
        "document_id": "doc-2",   # otro documento
        "page_number": 44,
    }
    assert mp.detect_cross_fragment_count_atoms([base, enum]) == []
    enum2 = dict(enum, document_id="doc-1", page_number=48)  # página no adyacente
    assert mp.detect_cross_fragment_count_atoms([base, enum2]) == []


def test_cross_fragment_count_consistente_no_forma_atomo():
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite seis modos de disparo configurables.",
            "document_id": "doc-1",
            "page_number": 44,
        },
        {
            "fragment_number": 2,
            "text": "- Modo A\n- Modo B\n- Modo C\n- Modo D\n- Modo E\n- Modo F",
            "document_id": "doc-1",
            "page_number": 44,
        },
    ]
    assert mp.detect_cross_fragment_count_atoms(fragments) == []


def test_apply_cross_fragment_anexa_con_cita_doble(monkeypatch):
    _wire(monkeypatch, {"detnov:cad-150"})
    chunks = [
        {
            "document_id": "doc-1",
            "page_number": 10,
            "content": "El panel ofrece seis modos de disparo seleccionables.",
        },
        {
            "document_id": "doc-1",
            "page_number": 10,
            "content": (
                "- Modo A: activa las salidas de forma manual\n"
                "- Modo B: activa las salidas de forma temporizada\n"
                "- Modo C: activa las salidas al confirmar la alarma\n"
                "- Modo D: activa las salidas en modo nocturno\n"
                "- Modo E: activa las salidas con doble detección\n"
                "- Modo F: activa las salidas por zona cruzada\n"
                "- Modo G: activa las salidas de forma remota"
            ),
        },
    ]
    draft = "El panel dispone de seis modos de disparo [F1]"
    out, trace = mp.apply_must_preserve_contract("cad-150", chunks, draft)
    assert trace["cross_atoms_detected"] == 1
    assert trace["appendix_appended"] is True
    appendix = out.split(mp.APPENDIX_HEADER)[1]
    assert "[F1]" in appendix
    assert "[F2]" in appendix
    assert "Nota: el manual también indica:" in out


# ─── v3 (funnel probe-2): grounding fold-tolerante + disclosure de dos lados ───


def test_ground_hybrid_span_fold_tolerante_devuelve_substring_exacto():
    frag = "La tensión del lazo va\nde 10 a 30 V según\nla configuración."
    altered = "la tension del lazo va  de 10 a 30 v"
    grounded = mp.ground_hybrid_span(frag, altered)
    assert grounded is not None
    assert grounded in frag                      # substring EXACTO del fragmento
    assert "tensión" in grounded and "\n" in grounded
    assert mp.ground_hybrid_span(frag, "lazo del la tension va") is None  # parafraseo


def test_hybrid_stats_cuenta_grounding_fold():
    client = _FakeAnthropic(_hybrid_payload(
        atom_1_family="F-RANGE",
        atom_1_span="La tension de lazo va  DE 10 A 30 V",  # sin acento + re-espaciado
    ))
    stats = {}
    atoms = mp.detect_atoms_hybrid(_RANGE_TEXT, client=client, stats=stats)
    assert stats.get("proposals") == 1
    # el span foldeado ancla; puede quedar como fold_relocated+accepted o
    # descartarse por solape con el determinista — nunca rejected_grounding
    assert "rejected_grounding" not in stats
    assert atoms  # el determinista sigue presente


def test_render_count_conflict_dos_lados_con_citas():
    text = (
        "La central ofrece seis opciones de programación al instalador:\n"
        + _ENUM_GOOD
    )
    atoms = [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_COUNT]
    assert len(atoms) == 1
    meta = atoms[0]["meta"]
    assert meta["enum_span_text"].startswith("- Retardo")
    atoms[0]["meta"]["fragment_number"] = 3
    appendix = mp.render_appendix(atoms, "Hay seis opciones [F3]")
    assert "Nota: el manual también indica:" in appendix
    assert '"La central ofrece seis opciones' in appendix   # lado del conteo
    assert "- Volcado" in appendix                          # lado de la enumeración
    assert appendix.count("[F3]") == 2                      # cita en ambos lados


# ─── v4 (s271): guards de ACTIVACIÓN — bloqueadores 1/2/3 de DEC-127b ───

# Caso REAL hp001 (chunk CAD-250_Manual-Configuracion-MC-380-es-2026-c p29, extracto
# verbatim): el conteo «2, 4, 6 u 8 lazos …» NO debe ligar con el crumb de menú
# «Sistema | Otros | Reiniciar» del screenshot.
_HP001_AVANZADO_FRAG = (
    "## 5.4. AVANZADO\n"
    "\n"
    "En esta sección podrá establecer los parámetros básicos de configuración de la "
    "central, así como ajustes de ingeniero para facilitar trabajos de puesta en "
    "marcha y configuración. Para acceder a estos ajustes pulse:\n"
    "\n"
    "**AJUSTES** (Menú principal) **> AVANZADO** (Submenú)\n"
    "\n"
    "Al tocar el campo **LAZOS**, se desplegarán las combinaciones posibles según el "
    "número de cabinas que haya indicado en el punto anterior. 2, 4, 6 u 8 lazos si "
    "ha definido una sola central, hasta 16 lazos, si ha definido 2 cabinas,. hasta "
    "24 con 3 cabinas y 32 lazos con 4 cabinas. Si el número de lazos que debe "
    "configurar no se muestra, revise el número de paneles configurado o pruebe a "
    "realizar scroll del desplegable.\n"
    "\n"
    "[Screenshot showing:\n"
    "Avanzado interface with dropdown menu:\n"
    "\n"
    "Sistema | Otros | Reiniciar\n"
    "\n"
    "Paneles | 1\n"
    "\n"
    "Lazos   | 2\n"
)

_HP001_COUNT_SPAN = (
    "2, 4, 6 u 8 lazos si ha definido una sola central, hasta 16 lazos, si ha "
    "definido 2 cabinas,."
)

# Caso REAL cat007 (chunk I56-3947-202_FAAST LT_MULTI p25, extracto verbatim): tabla
# OCR T1..T10 con celdas EN BLANCO — el lado-enumeración de un disclosure jamás.
_CAT007_BLANK_TABLE = (
    "| T1  |   |\n"
    "| --- | - |\n"
    "| T2  |   |\n"
    "| T3  |   |\n"
    "| T4  |   |\n"
    "| T5  |   |\n"
    "| T6  |   |\n"
    "| T7  |   |\n"
    "| T8  |   |\n"
    "| T9  |   |\n"
    "| T10 |   |"
)

_CAT007_RELAY_FRAG = (
    "## ADVERTENCIA: Conmutación de cargas inductivas\n"
    "\n"
    "Las cargas inductivas pueden provocar sobretensionesç de desconexión que pueden "
    "dañar los contactos de los relés del módulo (ver arriba).\n"
    "\n"
    "Para proteger los contactos de los relés, conecte un supresor de voltaje "
    "transitorio (por ejemplo, 1N6284CA) para toda la carga según se indica.\n"
    "\n"
    "Como alternativa, para aplicaciones de CC sin supervisión, instale un diodo con "
    "tensión de ruptura inverso superior a diez veces la tensión del circuito.\n"
    "\n"
    + _CAT007_BLANK_TABLE + "\n"
)

# Tira de etiquetas OCR REAL de hp017 (freeze s113 F1): etiquetas CON texto — el
# guard de contenido informativo NO debe matarla (≠ celdas en blanco).
_HP017_LABEL_STRIP = (
    "TECLU\ntardoRet.Tipo\nEstándar\nFijo\nEst.Ext.\nNo Silenc.\nNo Sil.Ext\n"
    "Estándar 0\nEstándar 0"
)


def _count_atoms(text):
    return [a for a in mp.detect_atoms(text) if a["family"] == mp.FAMILY_COUNT]


def test_count_navcrumb_real_hp001_no_liga():
    """Bloqueador 3 (caso real): ningún F-COUNT puede ligar el conteo de lazos con el
    crumb de navegación «Sistema | Otros | Reiniciar»."""
    atoms = _count_atoms(_HP001_AVANZADO_FRAG)
    assert atoms == []


def test_count_navcrumb_sintetico_positivo_sigue_ligando():
    """Control positivo: el mismo conteo con una enumeración LEGÍTIMA de su dominio
    (heading compartiendo tokens con la oración) sigue formando átomo."""
    text = (
        "## Modos de disparo\n"
        "La central admite seis modos de disparo configurables para la instalación.\n"
        "El comportamiento depende del cableado del panel y del firmware cargado.\n"
        "- Elemento A\n- Elemento B\n- Elemento C\n- Elemento D\n- Elemento E\n"
        "- Elemento F\n- Elemento G\n"
    )
    atoms = _count_atoms(text)
    assert len(atoms) == 1
    assert atoms[0]["meta"]["tie"] == "section"
    assert (atoms[0]["meta"]["declared_n"], atoms[0]["meta"]["enumerated_n"]) == (6, 7)


def test_count_tie_seccion_sin_relevancia_no_liga():
    """Tie estricto: heading sin tokens de la oración del conteo + enumeración sin el
    sustantivo contado → el par NO liga (mejor silencio)."""
    text = (
        "## Historial de revisiones\n"
        "La central admite seis modos de disparo configurables para la instalación.\n"
        "El comportamiento depende del cableado del panel y del firmware cargado.\n"
        "- Elemento A\n- Elemento B\n- Elemento C\n- Elemento D\n- Elemento E\n"
        "- Elemento F\n- Elemento G\n"
    )
    assert _count_atoms(text) == []


def test_count_tie_seccion_sustantivo_del_dominio_liga():
    """Tie estricto vía sustantivo: la enumeración contiene el sustantivo contado
    (modos↔Modo) aunque el heading no comparta tokens."""
    text = (
        "## Historial de revisiones\n"
        "La central admite seis modos de disparo configurables para la instalación.\n"
        "El comportamiento depende del cableado del panel y del firmware cargado.\n"
        "- Modo A\n- Modo B\n- Modo C\n- Modo D\n- Modo E\n- Modo F\n- Modo G\n"
    )
    atoms = _count_atoms(text)
    assert len(atoms) == 1
    assert atoms[0]["meta"]["tie"] == "section"


def test_count_enum_vacia_real_cat007_no_forma_atomo():
    """Bloqueador 2 (caso real): la tabla T1..T10 de celdas en blanco no es una
    enumeración de miembros — el conteo «diez veces …» no forma átomo con ella."""
    assert _count_atoms(_CAT007_RELAY_FRAG) == []


def test_select_disclosure_con_enum_vacia_no_dispara():
    """Defensa en profundidad en la SELECCIÓN: un disclosure cuyo lado-enumeración es
    la tabla en blanco no dispara ENTERO (mejor silencio que basura)."""
    atom = {
        "family": mp.FAMILY_COUNT, "span_start": 0, "span_end": 10,
        "span_text": (
            "Como alternativa, para aplicaciones de CC sin supervisión, instale un "
            "diodo con tensión de ruptura inverso superior a diez veces la tensión "
            "del circuito."
        ),
        "anchor_tokens": ["diodo"],
        "meta": {"declared_n": 10, "enumerated_n": 9, "conflict": True,
                 "enum_span_text": _CAT007_BLANK_TABLE, "fragment_number": 29},
    }
    assert mp._select_for_appendix([atom], "el diodo soporta diez veces [F29]") == []
    assert mp.render_appendix([atom], "el diodo soporta diez veces [F29]") == ""


def test_informative_span_basico():
    assert mp.informative_span("") is False
    assert mp.informative_span("—: | |  ·") is False
    assert mp.informative_span(_CAT007_BLANK_TABLE) is False
    assert mp.informative_span(_HP017_LABEL_STRIP) is True   # etiquetas CON texto
    assert mp.informative_span(
        "| RELÉ | ACCIÓN |\n| --- | --- |\n| ALARMA 1 | Controlada por el panel |"
    ) is True  # tabla real con valores


def test_select_no_anexa_span_no_informativo():
    atom = {
        "family": mp.FAMILY_RANGE, "span_start": 0, "span_end": 5,
        "span_text": "| |  —", "anchor_tokens": [],
        "meta": {"lower": 10.0, "upper": 30.0, "unit": "v", "fragment_number": 1},
    }
    assert mp._select_for_appendix([atom], "el rango llega a 30 V [F1]") == []


def test_render_dedup_nota_duplicada_hp001():
    """Bloqueador 1 (caso real): dos átomos F-COUNT con el MISMO span (la oración de
    lazos de hp001, matches «8 lazos» y «2 cabinas») anexan UNA sola nota. (v5: el
    lado-enumeración crumb del caso original ya muere ANTES por la whitelist; el
    dedup se pinea sobre el lado del conteo, que es cláusula de forma buena.)"""
    import copy as _copy

    atom = {
        "family": mp.FAMILY_COUNT, "span_start": 0, "span_end": 10,
        "span_text": _HP001_COUNT_SPAN,
        "anchor_tokens": ["lazos"],
        "meta": {"declared_n": 8, "enumerated_n": 3, "conflict": True,
                 "fragment_number": 3},
    }
    dup = _copy.deepcopy(atom)
    dup["meta"]["declared_n"] = 2
    draft = "El campo LAZOS admite 8 lazos según la central [F3]"
    appendix = mp.render_appendix([atom, dup], draft)
    assert appendix.count(_HP001_COUNT_SPAN) == 1
    assert appendix.count("Nota: el manual también indica:") == 1


def test_render_dedup_solape_90_mismos_numeros():
    base = {
        "family": mp.FAMILY_RANGE, "span_start": 0, "span_end": 10,
        "anchor_tokens": ["salida"],
        "meta": {"lower": 10.0, "upper": 30.0, "unit": "v", "fragment_number": 1},
    }
    a1 = dict(base, span_text="La salida admite de 10 a 30 V en la placa de bornes.")
    a2 = dict(base, span_text="La salida admite de 10 a 30 V en la placa de bornes")
    selected = mp._select_for_appendix([a1, a2], "la salida llega a 30 [F1]")
    assert len(selected) == 1


def test_render_dedup_no_colapsa_hechos_distintos():
    base = {
        "family": mp.FAMILY_RANGE, "span_start": 0, "span_end": 10,
        "anchor_tokens": ["retardo"],
    }
    a1 = dict(base, span_text="El tiempo de retardo T1 va de 10 a 30 s.",
              meta={"lower": 10.0, "upper": 30.0, "unit": "s", "fragment_number": 1})
    a2 = dict(base, span_text="El tiempo de retardo T1 va de 10 a 35 s.",
              meta={"lower": 10.0, "upper": 35.0, "unit": "s", "fragment_number": 1})
    selected = mp._select_for_appendix([a1, a2], "el retardo llega a 30 s [F1]")
    assert len(selected) == 2


def test_render_dedup_no_colapsa_advertencias_hermanas_sin_numeros():
    """Apriete del review adversarial s271: ratio ≥0.90 con CERO números en ambos
    lados no basta — un token de contenido distinto (sirena vs fuente) = hecho
    distinto, se conservan ambos."""
    base = {
        "family": mp.FAMILY_MANDATORY, "span_start": 0, "span_end": 10,
        "anchor_tokens": ["desconecte"],
        "meta": {"triggers": ["advertencia"], "fragment_number": 1},
    }
    a1 = dict(base, span_text=(
        "Advertencia: desconecte el cable de la sirena antes de manipular el equipo."
    ))
    a2 = dict(base, span_text=(
        "Advertencia: desconecte el cable de la fuente antes de manipular el equipo."
    ))
    selected = mp._select_for_appendix([a1, a2], "draft")
    assert len(selected) == 2


def test_count_tie_rechaza_fila_clave_valor():
    """Residual del review adversarial s271: una fila clave-valor de screenshot con
    el sustantivo contado como etiqueta («Lazos | 2 | 4») escapaba al crumb por el
    dígito y el sustantivo la endosaba — no es una enumeración de miembros."""
    text = (
        "## Lazos del sistema\n"
        "La central admite ocho lazos de detección configurables en total.\n"
        "El comportamiento depende del número de cabinas configurado previamente.\n"
        "Lazos | 2 | 4\n"
    )
    assert _count_atoms(text) == []


def test_cross_fragment_count_rechaza_fila_clave_valor():
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite ocho lazos de detección configurables.",
            "document_id": "doc-1",
            "page_number": 29,
        },
        {
            "fragment_number": 2,
            "text": "Lazos | 2 | 4",
            "document_id": "doc-1",
            "page_number": 29,
        },
    ]
    assert mp.detect_cross_fragment_count_atoms(fragments) == []


def test_cross_fragment_count_rechaza_crumb_de_navegacion():
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite seis modos de disparo configurables.",
            "document_id": "doc-1",
            "page_number": 44,
        },
        {
            "fragment_number": 2,
            "text": "Sistema | Otros | Reiniciar",
            "document_id": "doc-1",
            "page_number": 44,
        },
    ]
    assert mp.detect_cross_fragment_count_atoms(fragments) == []


def test_cross_fragment_count_rechaza_nueva_seccion_sin_sustantivo():
    """El bloque par vive bajo un heading PROPIO del fragmento j (no es continuación)
    y no contiene el sustantivo contado → no liga."""
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite seis niveles de acceso configurables.",
            "document_id": "doc-1",
            "page_number": 44,
        },
        {
            "fragment_number": 2,
            "text": (
                "## Otro apartado\n- Elemento A\n- Elemento B\n- Elemento C\n"
                "- Elemento D\n- Elemento E\n- Elemento F\n- Elemento G"
            ),
            "document_id": "doc-1",
            "page_number": 44,
        },
    ]
    assert mp.detect_cross_fragment_count_atoms(fragments) == []


def test_cross_fragment_count_sustantivo_liga_aunque_haya_heading():
    fragments = [
        {
            "fragment_number": 1,
            "text": "La central admite seis niveles de acceso configurables.",
            "document_id": "doc-1",
            "page_number": 44,
        },
        {
            "fragment_number": 2,
            "text": (
                "## Niveles de acceso\n- Nivel A\n- Nivel B\n- Nivel C\n"
                "- Nivel D\n- Nivel E\n- Nivel F\n- Nivel G"
            ),
            "document_id": "doc-1",
            "page_number": 44,
        },
    ]
    atoms = mp.detect_cross_fragment_count_atoms(fragments)
    assert len(atoms) == 1
    assert atoms[0]["meta"]["cross_fragment"] is True


# ─── v5 (s271 iteración final): WHITELIST fail-closed de forma-buena ───

# Caso REAL Etapa 3 v2 (cat007 [F42]): cabecera-sola anexada como MANDATORY.
_CAT007_HEADING_ONLY = "### <ins>ADVERTENCIA</ins>"

# Caso REAL Etapa 3 v2 (hp001 [F3]): volcado de descripción de UI multi-línea que el
# navcrumb-guard (solo líneas únicas) no cubría.
_HP001_UI_DUMP = (
    "- Right sidebar with options: GENERAL, VERSIONES, USUARIOS, AVANZADO "
    "(highlighted), CONECTIVIDAD, IMPRESORA, LOGS, TEST\n"
    '- Bottom buttons: "Guardar y reiniciar" and "INICIO"\n'
    '- Header: "detnov Panel_template 20:17 - martes, 31 de marzo de 2020"]'
)


def test_whitelist_span_good_form_casos():
    # cláusula completa (verbo conjugado + ≥40 chars)
    assert mp.span_good_form(
        "La central ofrece seis opciones de programación al instalador."
    ) is True
    # fila etiqueta+valor (número CON unidad + etiqueta en la misma línea)
    assert mp.span_good_form("| Potencia nominal | 2 | A | carga resistiva |") is True
    # número pelado sin unidad NO es valor (caso real hp001: «Lazos   | 2»)
    assert mp.span_good_form("Lazos   | 2") is False
    # heading/markers jamás cuentan como contenido (caso real cat007)
    assert mp.span_good_form(_CAT007_HEADING_ONLY) is False
    # volcado de UI: infinitivos/gerundios y timestamps no son cláusula ni valor
    assert mp.span_good_form(_HP001_UI_DUMP) is False
    # corto sin verbo
    assert mp.span_good_form("hay seis opciones") is False


def test_whitelist_heading_solo_advertencia_real_cat007_no_se_anexa():
    atom = {
        "family": mp.FAMILY_MANDATORY, "span_start": 0, "span_end": 10,
        "span_text": _CAT007_HEADING_ONLY,
        "anchor_tokens": ["advertencia"],
        "meta": {"triggers": ["advertencia"], "fragment_number": 42},
    }
    assert mp.atom_good_form(atom) is False
    assert mp._select_for_appendix(
        [atom], "Siga el procedimiento del módulo de relés [F42]"
    ) == []


def test_whitelist_mandatory_exige_trigger_y_su_oracion():
    good = _mandatory_atom(1)
    assert mp.atom_good_form(good) is True
    # trigger presente pero SIN verbo (título largo) → no es cláusula
    title_only = dict(good, span_text="ADVERTENCIA GENERAL DE SEGURIDAD DEL SISTEMA "
                                      "DE DETECCIÓN Y EXTINCIÓN")
    assert mp.atom_good_form(title_only) is False


def test_whitelist_ui_dump_como_lado_de_disclosure_no_dispara():
    """Caso real hp001 (Etapa 3 v2): «Lazos   | 2» · volcado de UI. El lado del
    conteo ya falla (número sin unidad); y aunque el conteo fuera cláusula buena,
    el volcado de UI mata el disclosure ENTERO."""
    real = {
        "family": mp.FAMILY_COUNT, "span_start": 0, "span_end": 10,
        "span_text": "Lazos   | 2",
        "anchor_tokens": ["ledes"],
        "meta": {"declared_n": 2, "enumerated_n": 3, "conflict": True,
                 "enum_span_text": _HP001_UI_DUMP, "fragment_number": 3},
    }
    assert mp.atom_good_form(real) is False
    good_count_bad_enum = dict(real, span_text=(
        "La central dispone de dos ledes configurables en el panel frontal."
    ))
    assert mp.atom_good_form(good_count_bad_enum) is False
    draft = "El panel dispone de dos ledes [F3]"
    assert mp.render_appendix([real, good_count_bad_enum], draft) == ""


def test_whitelist_bundle_exige_descripcion_de_miembros():
    base = {
        "family": mp.FAMILY_BUNDLE, "span_start": 0, "span_end": 10,
        "anchor_tokens": [],
        "meta": {"header": "Opciones", "members": ["Zona", "CBE"],
                 "fragment_number": 1},
    }
    con_desc = dict(base, span_text=(
        "## Opciones\n- Zona: define la zona del punto\n"
        "- CBE: ecuación de control por evento"
    ))
    solo_nombres = dict(base, span_text="## Opciones\n- Zona\n- CBE")
    assert mp.atom_good_form(con_desc) is True
    assert mp.atom_good_form(solo_nombres) is False


def test_whitelist_disclosure_strip_de_etiquetas_queda_en_silencio():
    """Calibración DOCUMENTADA (v5): la tira OCR de etiquetas de hp017 (solo
    nombres, sin cláusula ni valores-con-unidad) NO pasa la whitelist como lado de
    disclosure — ese disclosure calla; obl_872c sobrevive vía el disclosure cuyo
    lado-enumeración es la TABLA de la F2 (filas con cláusulas), verificado en la
    certificación det-only v2."""
    atom = {
        "family": mp.FAMILY_COUNT, "span_start": 0, "span_end": 10,
        "span_text": (
            "Se puede asignar uno de seis tipos de retardo de salida a una regla, "
            "como se explica a continuación."
        ),
        "anchor_tokens": ["tipos"],
        "meta": {"declared_n": 6, "enumerated_n": 8, "conflict": True,
                 "enum_span_text": _HP017_LABEL_STRIP, "fragment_number": 1},
    }
    assert mp.span_good_form(atom["span_text"]) is True    # el conteo es cláusula
    assert mp.atom_good_form(atom) is False                # la tira no pasa
    # la tabla F2 (filas con cláusula) SÍ pasa como lado de enumeración
    tabla_f2 = (
        "| Acción de usuario | Fijo | Estándar |\n"
        "| --- | --- | --- |\n"
        "| La salida se detiene si se pulsa SILENCIAR SIRENAS durante el retardo. "
        "| × | ✓ |"
    )
    assert mp.span_good_form(tabla_f2) is True


def test_apply_detect_fn_inyectable(monkeypatch):
    _wire(monkeypatch, {"detnov:cad-150"})
    chunks = [{"document_id": "doc-1", "content": _RANGE_TEXT}]
    draft = "La tensión máxima del lazo es 30 V [F1]"
    llamadas = []

    def detector(texto):
        llamadas.append(texto)
        return mp.detect_atoms(texto)

    out, trace = mp.apply_must_preserve_contract(
        "cad-150", chunks, draft, detect_fn=detector
    )
    assert llamadas, "el detector inyectado debe usarse"
    assert trace["appendix_appended"] is True
