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


def test_seven_seg_rango_en_contexto_display_sigue_excluido():
    # el caso original (r.I + rango en la misma oración) sigue fuera del anexo
    assert _atoms(
        "El display muestra r.I durante el rearme de 0 a 9 segundos.",
        mp.FAMILY_RANGE,
    ) == []


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
