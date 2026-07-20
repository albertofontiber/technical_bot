"""s274 Bloques C/D — tests por fix (P0, build flag-off).

Cada fix vive tras su flag estricto default-off (dúo Sol-C2: kill-switch y banking
selectivos) y con flags off la conducta es BYTE-IDÉNTICA. Los casos pineados salen de
los DIAGNÓSTICOS de s274 (evals/s274_serving_view_diag_v1.json · funnel N=3
evals/s274_hybrid_funnel_diag_v2.json), no de los textos gold.

Sin red, sin DB.
"""
from __future__ import annotations

import pytest

from src.rag import must_preserve as mp
from src.rag import post_rerank_coverage as prc
from src.rag.answer_planner import build_answer_plan
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


# ─────────────────────────── fixtures sintéticas ───────────────────────────

# Estructura espejo del hallazgo C1 (F12 hp017): cards del selector + bloque-warning
# blockquote FUERA de toda card (mismo patrón; texto del DIAGNÓSTICO, no del gold).
_WARN_BLOCK = (
    "> **Al programar reglas de causa-efecto evite las lógicas contradictorias.**\n"
    ">\n"
    "> **Es de vital importancia probar rigurosamente todas las reglas durante la "
    "puesta en marcha del sistema para verificar que no haya conflictos lógicos "
    "entre ellas.**"
)


def _callout_chunk(row_id="callout-chunk", warn_block=_WARN_BLOCK):
    prose = (
        "El objetivo de la programación causa-efecto es ofrecer un conjunto claro "
        "de reglas para el comportamiento de los equipos de salida."
    )
    filler = "Texto intermedio del manual sin gatillos de seguridad relevantes aquí."
    content = f"{prose}\n\n{filler}\n\n{warn_block}\n"
    start = 0
    end = len(prose)
    return {
        "id": row_id,
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": STRUCTURAL_LANE,
        "structural_neighbor_validated": True,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": start,
                "end": end,
                "quote": content[start:end],
                "facet": "rule_overview",
                "exact_source_span_validated": True,
            }
        ],
    }


# ───────────────────────────── C1: callout card ─────────────────────────────

def test_c1_off_is_byte_identical(monkeypatch):
    monkeypatch.delenv("COVERAGE_MANDATORY_CALLOUT", raising=False)
    chunk = _callout_chunk()
    attested = prc._attest(chunk)
    assert attested is not None
    assert "mandatory_callout_cards" not in attested
    served = prc.coverage_context_content(attested)
    assert "vital importancia" not in served


def test_c1_on_serves_full_warning_block_with_exact_receipt(monkeypatch):
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    chunk = _callout_chunk()
    attested = prc._attest(chunk)
    assert attested is not None
    # campo PROPIO: jamás dentro de served_coverage_cards (Sol-M4 estructural —
    # los consumidores de served cards, answer_planner incluido, no la ven)
    assert all(
        c.get("card_class") != "mandatory_callout"
        for c in attested["served_coverage_cards"]
    )
    callouts = attested["mandatory_callout_cards"]
    assert len(callouts) == 1  # cap 1 por chunk
    card = callouts[0]
    # el MERGE por hueco-sin-alfanuméricos cubre AMBOS warnings (Fable-M1: el check
    # merged_warning_block exige las dos componentes)
    assert "evite las lógicas contradictorias" in card["quote"]
    assert "vital importancia" in card["quote"]
    assert card["end"] - card["start"] <= prc.MAX_MANDATORY_CALLOUT_CHARS
    # clase propia SIN heredar validación semántica del selector (Sol-M4)
    assert card["local_semantic_validated"] is False
    assert card["exact_source_span_validated"] is True
    # receipts: el v3 queda byte-intacto y el callout tiene el suyo propio
    assert prc.has_exact_served_coverage_receipt(attested)
    assert prc.has_exact_mandatory_callout_receipt(attested)
    # y la vista servida incluye el bloque, sin depender de LOGICAL_RECORD_COVERAGE
    served = prc.coverage_context_content(attested, logical_record_expansion=False)
    assert "evite las lógicas contradictorias" in served
    assert "vital importancia" in served


def test_c1_oversize_group_is_omitted_entirely(monkeypatch):
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    # UNA sola oración-gatillo de >600 chars (sin frontera de oración interna)
    fat = (
        "> **Advertencia: nunca conecte la central sin verificar la tensión "
        + "de alimentación del circuito " + "x" * 700 + " final.**"
    )
    chunk = _callout_chunk(row_id="fat", warn_block=fat)
    attested = prc._attest(chunk)
    assert "mandatory_callout_cards" not in attested
    # >600 chars: se omite entero, jamás recorte a media oración


def test_c1_callout_lives_outside_planner_input(monkeypatch):
    """Sol-M4 estructural: la card vive en campo propio que build_answer_plan no
    lee — con flag ON el planner no deriva NINGUNA obligación del warning."""
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    chunk = _callout_chunk(row_id="planner")
    attested = prc._attest(chunk)
    assert attested is not None
    assert attested.get("mandatory_callout_cards")
    plan = build_answer_plan("¿Cómo se programa la salida de alarma?", [attested])
    for obligation in plan:
        assert "contradictorias" not in obligation.statement
        assert "vital importancia" not in obligation.statement


def test_c1_tampered_callout_field_fails_its_receipt(monkeypatch):
    monkeypatch.setenv("COVERAGE_MANDATORY_CALLOUT", "on")
    attested = prc._attest(_callout_chunk(row_id="tamper"))
    tampered = dict(attested)
    card = dict(tampered["mandatory_callout_cards"][0])
    card["quote"] = card["quote"].replace("evite", "aplique")
    tampered["mandatory_callout_cards"] = [card]
    assert prc.has_exact_mandatory_callout_receipt(tampered) is False
    served = prc.coverage_context_content(tampered)
    assert "vital importancia" not in served  # sin receipt no se sirve


# ───────────────── Fable-M1: gatillo-verbo en la whitelist MANDATORY ─────────────────

_WARN1 = "> **Al programar reglas de causa-efecto evite las lógicas contradictorias.**"


def test_verb_trigger_off_keeps_v5_behavior(monkeypatch):
    monkeypatch.delenv("MP_MANDATORY_VERB_TRIGGER", raising=False)
    atom = {"family": mp.FAMILY_MANDATORY, "span_text": _WARN1, "meta": {}}
    assert mp.atom_good_form(atom) is False  # diagnóstico: 'evite' no está en el
    # léxico de verbos finitos — NO es cláusula corta (72 chars ≥ 40)


def test_verb_trigger_on_accepts_imperative_clause_but_never_headers(monkeypatch):
    monkeypatch.setenv("MP_MANDATORY_VERB_TRIGGER", "on")
    atom = {"family": mp.FAMILY_MANDATORY, "span_text": _WARN1, "meta": {}}
    assert mp.atom_good_form(atom) is True
    # los gatillos-SUSTANTIVO jamás cuentan: cabecera sola sigue fuera
    header = {
        "family": mp.FAMILY_MANDATORY,
        "span_text": "### <ins>ADVERTENCIA</ins>",
        "meta": {},
    }
    assert mp.atom_good_form(header) is False
    # sustantivo-trigger sin verbo finito tampoco pasa con el flag
    noun_only = {
        "family": mp.FAMILY_MANDATORY,
        "span_text": "Advertencia importante acerca del cableado del circuito de extinción del sistema.",
        "meta": {},
    }
    assert mp.atom_good_form(noun_only) is False


# ───────────────────────────── D1a: DEFLINE con '=' ─────────────────────────────

_TONE_BLOCK = (
    "**Donde:**\n\n"
    "**Tono = tipo de sonido en el rango 1÷33\n"
    "Volumen = volumen en el rango 1÷4\n"
    "Z2:Z4 = zonas de la 2 a la 4**"
)


def test_d1a_off_equals_separator_not_recognized(monkeypatch):
    monkeypatch.delenv("MP_DEFLINE_EQ", raising=False)
    assert [a for a in mp.detect_atoms(_TONE_BLOCK) if a["family"] == mp.FAMILY_BUNDLE] == []


def test_d1a_on_detects_equals_definition_schema(monkeypatch):
    monkeypatch.setenv("MP_DEFLINE_EQ", "on")
    bundles = [a for a in mp.detect_atoms(_TONE_BLOCK) if a["family"] == mp.FAMILY_BUNDLE]
    assert bundles, "el schema Tono=/Volumen= debe formar bundle (funnel N=3, 015f)"
    members = bundles[0]["meta"]["members"]
    assert "Tono" in members and "Volumen" in members


def test_d1a_compact_assignment_is_not_a_defline(monkeypatch):
    monkeypatch.setenv("MP_DEFLINE_EQ", "on")
    assert mp._defline_match("x=1") is None          # sin espacios: no separa
    assert mp._defline_match("valor =") is None      # sin definición a la derecha


# ───────────────────────────── D1c: stem binding ─────────────────────────────

_A5D9_ATOM = {
    "family": mp.FAMILY_BUNDLE,
    "span_text": "se guardan como valores nominales (100 %) del flujo de aire",
    "meta": {"header": "", "members": ["valores nominales", "flujo de aire"]},
}
_A5D9_WINDOW = "Un valor de flujo por debajo del 80 % del nominal indica obstrucción [F2]."


def test_d1c_off_exact_token_match_only(monkeypatch):
    monkeypatch.delenv("MP_STEM_BINDING", raising=False)
    assert mp.atom_exigible_in(_A5D9_ATOM, _A5D9_WINDOW) is False


def test_d1c_on_plural_stem_binds(monkeypatch):
    monkeypatch.setenv("MP_STEM_BINDING", "on")
    assert mp.atom_exigible_in(_A5D9_ATOM, _A5D9_WINDOW) is True


def test_d1c_stem_does_not_lower_the_two_token_threshold(monkeypatch):
    monkeypatch.setenv("MP_STEM_BINDING", "on")
    monkeypatch.delenv("MP_DISTINCTIVE_TOKEN", raising=False)
    atom = {
        "family": mp.FAMILY_BUNDLE,
        "span_text": "Ajustes del sistema y parámetros",
        "meta": {"header": "", "members": ["sistemas", "parámetros"]},
    }
    # solo 1 token (stem sistema~sistemas) presente → sigue sin ligar (clase seed-271)
    assert mp.atom_exigible_in(atom, "El sistema se reinicia [F1].") is False


# ─────────────────────── D2: binding 1-token DISTINTIVO ───────────────────────

_CBE_ATOM = {
    "family": mp.FAMILY_BUNDLE,
    "span_text": "Pestaña Programmazione: campos Zona y CBE del punto seleccionado.",
    "meta": {"header": "Programmazione", "members": ["CBE", "Zona"]},
}
_CBE_WINDOW = "Usa las teclas flecha para seleccionar el parámetro CBE [F3]."


def test_d2_off_single_token_never_binds(monkeypatch):
    monkeypatch.delenv("MP_DISTINCTIVE_TOKEN", raising=False)
    assert mp.atom_exigible_in(_CBE_ATOM, _CBE_WINDOW) is False


def test_d2_on_acronym_token_binds_generic_token_does_not(monkeypatch):
    monkeypatch.setenv("MP_DISTINCTIVE_TOKEN", "on")
    assert mp.atom_exigible_in(_CBE_ATOM, _CBE_WINDOW) is True
    generic = {
        "family": mp.FAMILY_BUNDLE,
        "span_text": "Ajuste del sistema y parámetros generales de instalación.",
        "meta": {"header": "", "members": ["sistema", "instalación"]},
    }
    # 1 solo token matcheado y NO distintivo (clase seed-271) → no liga
    assert mp.atom_exigible_in(generic, "El sistema se reinicia [F1].") is False


def test_d2_distinctive_definition_closed():
    assert mp._distinctive_token("c1l1m2", "módulo C1L1M2") is True   # dígito
    assert mp._distinctive_token("cbe", "el campo CBE") is True       # acrónimo
    assert mp._distinctive_token("sistema", "el sistema general") is False
    assert mp._distinctive_token("ajuste", "el ajuste fino") is False


# ─────────────────── D1b: F-RELATION + híbrido runtime ───────────────────

_REL_A5D9 = (
    "Al realizar un reset inicial se registrarán los valores de la medición del "
    "flujo de aire y se guardarán como valores nominales (100 %)."
)
_REL_7AA7 = (
    "Instrucción de salida: esta parte de la regla solo puede procesarse cuando se "
    "cumplen todas las condiciones de entrada programadas."
)


def test_d1b_off_family_and_prompt_are_v3_identical(monkeypatch):
    monkeypatch.delenv("MP_HYBRID_DETECT", raising=False)
    assert mp._hybrid_families() == mp.FAMILIES
    assert mp._hybrid_prompt() == mp._HYBRID_PROMPT
    assert mp._atom_from_verbatim_span("F-RELATION", _REL_A5D9, _REL_A5D9) is None


def test_d1b_on_relation_shape_accepts_anchored_clauses_only(monkeypatch):
    monkeypatch.setenv("MP_HYBRID_DETECT", "on")
    assert mp.FAMILY_RELATION in mp._hybrid_families()
    assert "F-RELATION" in mp._hybrid_prompt()
    # (a) número con unidad
    assert mp._atom_from_verbatim_span("F-RELATION", _REL_A5D9, _REL_A5D9) is not None
    # (c) cabeza de definición con etiqueta de ≥2 tokens
    assert mp._atom_from_verbatim_span("F-RELATION", _REL_7AA7, _REL_7AA7) is not None
    # títulos y prosa sin ancla NO
    assert mp._atom_from_verbatim_span("F-RELATION", "## A5.2 Crear una regla", "## A5.2 Crear una regla") is None
    prosa = (
        "El objetivo de la programación es ofrecer un conjunto claro de reglas "
        "para determinar el comportamiento general de los equipos."
    )
    assert mp._atom_from_verbatim_span("F-RELATION", prosa, prosa) is None


def test_d1b_relation_binding_and_satisfaction(monkeypatch):
    monkeypatch.setenv("MP_HYBRID_DETECT", "on")
    atom = mp._atom_from_verbatim_span("F-RELATION", _REL_A5D9, _REL_A5D9)
    # binding: número propio compartido con la ventana
    assert mp.atom_exigible_in(atom, "El valor vuelve al 100 % tras el reset [F2].")
    # el qualifier podado (número presente, rol perdido) NO satisface
    assert mp.atom_satisfied(atom, "El umbral es 100 % [F2].") is False
    assert mp.atom_satisfied(atom, _REL_A5D9 + " [F2]") is True


def test_d1b_runtime_wiring_fails_open_without_credentials(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setenv("MP_HYBRID_DETECT", "on")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"acme:panel"})
    monkeypatch.setattr(mp, "attest_identity", lambda d, r, c=None: True)
    monkeypatch.setattr(mp, "_load_catalog", lambda: object())
    chunks = [{"content": "Texto sin átomos.", "document_id": "doc-1"}]
    answer, trace = mp.apply_must_preserve_contract("query", chunks, "Respuesta [F1].")
    assert answer == "Respuesta [F1]."
    assert trace["hybrid"]["enabled"] is True
    assert trace["hybrid"]["client_available"] is False  # sin key → determinista puro
    assert trace["hybrid"]["fragments"] == []


def test_d1b_budget_is_two_longest_cited_fragments(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setenv("MP_HYBRID_DETECT", "on")
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"acme:panel"})
    monkeypatch.setattr(mp, "attest_identity", lambda d, r, c=None: True)
    monkeypatch.setattr(mp, "_load_catalog", lambda: object())
    monkeypatch.setattr(mp, "_runtime_hybrid_client", lambda: object())
    calls: list[str] = []

    def fake_hybrid(text, client=None, usage=None, **kw):
        calls.append(text)
        return []

    monkeypatch.setattr(mp, "detect_atoms_hybrid", fake_hybrid)
    chunks = [
        {"content": "corto", "document_id": "d"},
        {"content": "texto medio con algo más", "document_id": "d"},
        {"content": "el texto más largo de los tres fragmentos servidos aquí", "document_id": "d"},
    ]
    _answer, trace = mp.apply_must_preserve_contract(
        "q", chunks, "Uso [F1] y [F2] y [F3]."
    )
    assert trace["hybrid"]["fragments"] == [2, 3]  # los 2 más largos, determinista
    assert len(calls) == mp.HYBRID_RUNTIME_MAX_CALLS


# ─────────────────── C2: binding servidos-no-citados ───────────────────

def test_c2_off_uncited_fragments_are_ignored(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.delenv("MP_SERVED_BINDING", raising=False)
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"acme:panel"})
    monkeypatch.setattr(mp, "attest_identity", lambda d, r, c=None: True)
    monkeypatch.setattr(mp, "_load_catalog", lambda: object())
    chunks = [
        {"content": "Respuesta base.", "document_id": "d"},
        {"content": "El rango va de 5 a 30 minutos en el parámetro r.i.", "document_id": "d"},
    ]
    answer, trace = mp.apply_must_preserve_contract(
        "q", chunks, "El parámetro admite de 5 a 30 minutos [F1]."
    )
    assert "served_uncited_bound" not in trace


def test_c2_on_served_uncited_atom_appends_with_source_cite(monkeypatch):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setenv("MP_SERVED_BINDING", "on")
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"acme:panel"})
    monkeypatch.setattr(mp, "attest_identity", lambda d, r, c=None: True)
    monkeypatch.setattr(mp, "_load_catalog", lambda: object())
    uncited = (
        "El rearme queda inhibido hasta finalizar la extinción del circuito, "
        "de 5 a 30 minutos según la configuración del panel."
    )
    chunks = [
        {"content": "Texto citado sin átomos.", "document_id": "d"},
        {"content": uncited, "document_id": "d"},
    ]
    draft = "Tras el disparo, espera el rearme del panel de extinción; el retardo llega a 30 minutos [F1]."
    answer, trace = mp.apply_must_preserve_contract("q", chunks, draft)
    assert trace["served_uncited_bound"] >= 1
    assert "[F2]" in answer  # el anexo cita el fragmento FUENTE no citado
    assert "de 5 a 30 minutos" in answer


def test_c2_reinforced_threshold_blocks_weak_overlap(monkeypatch):
    monkeypatch.setenv("MP_SERVED_BINDING", "on")
    atom = {
        "family": mp.FAMILY_BUNDLE,
        "span_text": "Menú de sistema: opciones de configuración y parámetros generales",
        "meta": {"header": "Menú", "members": ["opciones", "parámetros"]},
        "anchor_tokens": [],
    }
    # 2 tokens matcheados pero sin número propio → bajo el umbral reforzado (≥3)
    draft = "Las opciones y parámetros se revisan en la puesta en marcha [F1]."
    assert mp._served_uncited_exigible(atom, draft) is False


# ─────────────────── inertes juntos: byte-idéntico con todo off ───────────────────

def test_all_flags_off_apply_is_unchanged_vs_pre_s274(monkeypatch):
    for flag in (
        "COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING", "MP_DEFLINE_EQ",
        "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
        "MP_MANDATORY_VERB_TRIGGER",
    ):
        monkeypatch.delenv(flag, raising=False)
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"acme:panel"})
    monkeypatch.setattr(mp, "attest_identity", lambda d, r, c=None: True)
    monkeypatch.setattr(mp, "_load_catalog", lambda: object())
    chunks = [
        {"content": "ADVERTENCIA: nunca conecte el lazo con la central alimentada. "
                    "Desconecte la alimentación y compruebe la polaridad.",
         "document_id": "d"},
        {"content": "Fragmento servido no citado con datos de 5 a 30 minutos.",
         "document_id": "d"},
    ]
    draft = "Desconecte la alimentación y compruebe la polaridad del lazo [F1]."
    answer, trace = mp.apply_must_preserve_contract("q", chunks, draft)
    assert "hybrid" not in trace
    assert "served_uncited_bound" not in trace
    assert "[F2]" not in answer
