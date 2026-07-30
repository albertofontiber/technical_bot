"""s287 (DEC-164b) — contrato del arquetipo `variant_differentiation`.

Item 3 del spec sellado (`evals/s287_facet_lever_design_brief_v1.md`), AJUSTADO a
la ENMIENDA post-STOP: el pre-registro F2 se re-selló a ``{cat005, cat022}``
porque cat005 («…¿y en qué se diferencian las versiones digital y analógica?»)
es miembro genuino de la clase; el trigger ES natural se CONSERVA (estrecharlo
para que sólo cazara cat022 sería overfit al gold diana).

Los baselines pre-lever pineados aquí se leen del brazo ``pre`` del gate
(`evals/s287_facet_gates_v1.json` → ``gate_a.pre_archetypes``), que reconstruye
los blobs de `git HEAD`; NO de memoria.

FIX post-STOP-b2 pineado aquí: el gate (b.2) del control protegido cat005 paró
porque ``version`` es un **homógrafo** (edición de una norma) que sostenía solo
el ``required_any``.  Salió del discriminativo — y **permanece en ``terms``** —,
con lo que el control volvió a 0 anclas.  El contrato de las dos mitades del fix
está pineado en ``test_norm_edition_version_no_longer_satisfies_required_any``
y ``test_version_stays_in_the_class_vocabulary_without_veto_power``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from src.rag.evidence_coverage import (
    _project_terms,
    _tokens,
    match_evidence_facets,
    select_evidence_coverage_cards,
)
from src.rag.query_facets import expand_query_facets

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "config/retrieval_facets_v3.yaml"
EVIDENCE_V4 = ROOT / "config/evidence_coverage_facets_v4.yaml"
# s287 V1 cierre 1: el CARD-config de la lane structural
# (structural_neighbor_coverage.py:190).  v4 puntúa, v2 fabrica las cards.
EVIDENCE_V2 = ROOT / "config/evidence_coverage_facets_v2.yaml"

ARCHETYPE = "variant_differentiation"
EVIDENCE_FACET = "variant_attribute_matrix"
SPECTRAL_FACET = "spectral_band_cell"

# Prefijo-identidad [F3/Sol]: SHA256 del JSON canónico de los arquetipos
# PRE-LEVER (blob de HEAD antes del build).  Pinear el prefijo, y no el fichero
# entero, es lo que prueba que el arquetipo nuevo sólo APENDIZA al final de la
# ontología first_match — la única posición desde la que no puede mover la
# resolución de ninguna query existente.  Checkout-independiente.
V3_PRELEVER_ARCHETYPES_SHA256 = (
    "07278583e7b7fe877d0f399e386793cd7ecbd10de9f29e0cdbc52b78b94b81e1"
)
EVIDENCE_V4_PRELEVER_ARCHETYPES_SHA256 = (
    "b461af5425c680f5d0375a8dfeee2437f0c349afa1bf6ebdf7e299166e74bc3a"
)
V3_PRELEVER_IDS = [
    "compatibility",
    "replace_without_loss",
    "connect_install_wire",
    "battery_sizing",
    "capacity_quantity",
    "fault_reset_recovery",
    "program_delay_cause_effect",
]
EVIDENCE_V4_PRELEVER_KEYS = [
    "replace_without_loss",
    "capacity_quantity",
    "fault_reset_recovery",
    "connect_install_wire",
    "program_delay_cause_effect",
]

# Enunciados literales de `evals/gold_answers_v1.yaml` (split dev).
CAT022 = (
    "En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
    "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» "
    "(p. ej. 40/40LB)?"
)
CAT005 = (
    "¿Cuáles son las características técnicas de la central de detección de gas "
    "Fidegas CS4, y en qué se diferencian las versiones digital y analógica?"
)
# Arquetipo PRE-LEVER de las adyacentes, leído del baseline del gate.  Que
# sigan en el mismo sitio DESPUÉS del build es el contrato: la clase de
# «pídeme el modelo correcto» (cat011/cat021) y las de spec/EOL (hp004/hp009)
# no son comparativas de variantes y no deben ganar arquetipo.
PRE_LEVER_ARCHETYPES = {
    "cat011": (
        "Necesito un detector de humos analógico direccionable «751» para una "
        "instalación Notifier; ¿cuál es el modelo correcto?",
        None,
    ),
    "cat021": (
        "Necesito un detector de llama SharpEye «40/40» (Spectrex / Notifier) "
        "para una instalación; ¿qué modelo pido?",
        None,
    ),
    "hp009": (
        "¿Cuál es la resistencia de fin de línea recomendada para los lazos de "
        "la central Morley ZXe?",
        None,
    ),
    "hp004": (
        "¿Cuál es la tensión de funcionamiento y el consumo en reposo del "
        "detector DGD-600 de Detnov?",
        None,
    ),
}


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ── [F3] posición + prefijo-identidad ───────────────────────────────────────


def test_v3_prefix_identity_the_new_archetype_only_appends_at_the_end():
    payload = _load_yaml(V3)
    archetypes = payload["archetypes"]
    assert [row["id"] for row in archetypes] == [*V3_PRELEVER_IDS, ARCHETYPE]
    # El prefijo es BYTE-idéntico al pre-lever: nada reordenado, nada reescrito.
    assert _canonical_sha256(archetypes[:-1]) == V3_PRELEVER_ARCHETYPES_SHA256
    # Y la cabecera del schema tampoco se movió (el validador es compartido).
    assert payload["schema"] == "retrieval_facets_v3"
    assert payload["policy"] == "first_match"
    assert payload["max_needs"] == 3
    assert "multi_match" not in payload


def test_evidence_v4_twin_entry_is_appended_last_without_touching_the_prefix():
    """[F1] Sin la gemela en evidence-v4 el fail-closed lo descarta todo."""
    payload = _load_yaml(EVIDENCE_V4)
    keys = list(payload["archetypes"])
    assert keys == [*EVIDENCE_V4_PRELEVER_KEYS, ARCHETYPE]
    prefix = {key: payload["archetypes"][key] for key in EVIDENCE_V4_PRELEVER_KEYS}
    assert _canonical_sha256(prefix) == EVIDENCE_V4_PRELEVER_ARCHETYPES_SHA256
    # [F6] la faceta nueva declara su `required_any` discriminativo y no
    # inyecta dígitos (el validador lo exige, esto pinea la intención).
    (facet,) = payload["archetypes"][ARCHETYPE]
    assert facet["id"] == EVIDENCE_FACET
    # FIX post-STOP-b2: `version` FUERA del discriminativo (homógrafo de
    # edición-de-norma) pero DENTRO del vocabulario de clase.
    assert facet["required_any"] == ["bit", "incorporada"]
    assert "version" in facet["terms"]
    assert "version" not in facet["required_any"]
    assert set(facet["required_any"]).issubset(facet["terms"])
    assert not any(char.isdigit() for term in facet["terms"] for char in term)
    assert len(facet["terms"]) >= payload["min_distinct_terms"]


# ── [F2 re-sellado] enrutado de la clase: cat022 (diana) + cat005 (control) ──


@pytest.mark.parametrize(
    ("qid", "question"),
    [("cat022", CAT022), ("cat005", CAT005)],
)
def test_the_two_class_members_route_to_variant_differentiation(qid, question):
    plan = expand_query_facets(question, config_path=V3)
    assert plan["archetype"] == ARCHETYPE, qid
    assert len(plan["needs"]) == 3
    # Ningún token numérico entra por el arquetipo: los dígitos que se ven en
    # los needs son los de la PREGUNTA, nunca de la ontología.
    injected = " ".join(need.replace(question.strip(" ¿?"), "") for need in plan["needs"])
    assert not any(char.isdigit() for char in injected)


@pytest.mark.parametrize(
    ("qid", "case"), sorted(PRE_LEVER_ARCHETYPES.items())
)
def test_adjacent_queries_keep_their_pre_lever_archetype(qid, case):
    question, expected = case
    assert expand_query_facets(question, config_path=V3)["archetype"] == expected, qid


# ── [F4] frontera de palabra + trampas del vocabulario PCI ──────────────────


def test_presostato_diferencial_does_not_trigger_variant_differentiation():
    """`diferenc` como stem cazaría «diferencial» — por eso no existe."""
    for question in (
        "¿Cómo se conmuta el presostato diferencial de la bomba jockey?",
        "¿Qué presión diferencial marca el presostato del grupo de presión?",
        "¿Dónde se instala el manómetro diferencial del rociador?",
    ):
        plan = expand_query_facets(question, config_path=V3)
        assert plan["archetype"] != ARCHETYPE, question


def test_english_scope_triggers_and_its_own_boundary_trap():
    assert (
        expand_query_facets(
            "What are the differences between the 40/40L and 40/40L4 models?",
            config_path=V3,
        )["archetype"]
        == ARCHETYPE
    )
    assert (
        expand_query_facets(
            "What does the suffix B mean on this flame detector?", config_path=V3
        )["archetype"]
        == ARCHETYPE
    )
    # «differential» no es «difference»: el lookahead exige la palabra entera.
    assert (
        expand_query_facets(
            "Where is the differential pressure switch wired?", config_path=V3
        )["archetype"]
        != ARCHETYPE
    )


def test_a_bare_mention_of_diferencia_without_entre_does_not_fire():
    """El patrón principal es una CONJUNCIÓN (diferencia + entre)."""
    plan = expand_query_facets(
        "¿Qué diferencia de tensión admite la fuente de alimentación?",
        config_path=V3,
    )
    assert plan["archetype"] != ARCHETYPE


# ── [F6] match de evidence facet: positivo y negativo ───────────────────────


VARIANT_COMPARISON_SPAN = (
    "Existen dos versiones del detector: el modelo base y el modelo con "
    "sufijo B. La función de Prueba incorporada (BIT) sólo se incluye en la "
    "segunda. El sensor opera a una longitud de onda distinta según la "
    "descripción de cada versión."
)


def test_evidence_facet_matches_a_variant_comparison_span():
    (match,) = match_evidence_facets(
        VARIANT_COMPARISON_SPAN,
        archetype=ARCHETYPE,
        config_path=EVIDENCE_V4,
    )
    assert match["facet"] == EVIDENCE_FACET
    assert {"bit", "incorporada", "modelo", "version"}.issubset(match["term_hits"])


@pytest.mark.parametrize(
    "span",
    [
        # 0 términos de clase: prosa de instalación.
        "Apriete los prensacables y compruebe la continuidad de la pantalla.",
        # 1 solo término de clase: no llega a min_distinct_terms=2.
        "El modelo se suministra en carcasa antideflagrante certificada ATEX.",
        # >=2 términos de clase pero NINGUNO del required_any discriminativo:
        # sin él, una tabla de rangos por combustible pasaría como comparativa.
        (
            "La descripción del sensor indica el rango de sensibilidad por "
            "combustible y la longitud del cable recomendada."
        ),
    ],
)
def test_evidence_facet_rejects_spans_without_discriminative_support(span):
    assert (
        match_evidence_facets(span, archetype=ARCHETYPE, config_path=EVIDENCE_V4) == []
    )


def test_no_archetype_still_matches_nothing_fail_closed():
    """El fail-closed global sigue: sin arquetipo no hay faceta que apoyar."""
    assert (
        match_evidence_facets(
            VARIANT_COMPARISON_SPAN, archetype=None, config_path=EVIDENCE_V4
        )
        == []
    )


# ── FIX post-STOP-b2: el homógrafo `version` ya no sostiene el fail-closed ───
# Este bloque nació como `xfail(strict=True)` cuando el gate (b.2) cazó el leak.
# Con `version` fuera del `required_any` el test XPASS-eaba, así que el marcador
# se RETIRA y las aserciones quedan invertidas a contrato: pinean el
# comportamiento nuevo, no un gap abierto.

# Extracto real de la pág. 13 del manual Fidegas S/3-2 (el ancla que la lane
# seleccionaba para cat005, el CONTROL PROTEGIDO de 6/6 OK con appended_n=0).
NORM_DECLARATION_SPAN = (
    "DESCRIPCIÓN DEL PRODUCTO: Sensor remoto de gas Ref. S/3-2. "
    "EN 60079-0:2012 Explosive atmospheres - Part 0: Equipment - General "
    "requirements. Atmósferas explosivas. Parte 0: Equipo. Requisitos "
    "generales. (No existen cambios técnicos relevantes con respecto a la "
    "versión EN 60079-0:2009)."
)


def test_norm_edition_version_no_longer_satisfies_required_any():
    """Texto de norma con [descripcion, sensor, version] NO pasa el fail-closed.

    `version` aquí es la EDICIÓN DE UNA NORMA («respecto a la versión
    EN 60079-0:2009»), no una variante de producto.  Antes del fix ese único
    homógrafo aprobaba el `required_any` y la lane apendizaba una declaración UE
    de conformidad a cat005.
    """
    # El span sí alcanza `min_distinct_terms` con el vocabulario de la faceta —
    # lo que falla es el discriminativo, y eso es exactamente lo que cambió.
    payload = _load_yaml(EVIDENCE_V4)
    (facet,) = payload["archetypes"][ARCHETYPE]
    hits = set(_project_terms(_tokens(NORM_DECLARATION_SPAN), facet["terms"]))
    assert {"descripcion", "sensor", "version"}.issubset(hits)
    assert len(hits) >= payload["min_distinct_terms"]
    assert not hits.intersection(facet["required_any"])
    assert (
        match_evidence_facets(
            NORM_DECLARATION_SPAN, archetype=ARCHETYPE, config_path=EVIDENCE_V4
        )
        == []
    )


# ── s287 V1 cierre 1: la GEMELA en v2 (el CARD-config de la lane) ────────────
# El fallo que cierra este bloque estaba MEDIDO: la lane seleccionaba las anclas
# de cat022 y `n_via_coverage_append` seguía en 0 porque las cards se fabrican
# con evidence_coverage_facets_v2.yaml (MULTIFACET_CONFIG,
# structural_neighbor_coverage.py:190), que no tenía el arquetipo => cards
# vacías => `_attest` rechaza.  v4 puntúa (:189), v2 sirve.

# Span VERBATIM de chunks_v2 74cc9f95-…-3cae03c48371 (MNDT722_40-40L, p. 8):
# es la celda que el gold cat022 necesita — dos bandas espectrales distintas
# como el atributo que diferencia 40/40L de 40/40L4.
SPECTRAL_COMPARISON_SPAN = (
    "Existen dos versiones de detectores de llama UV/IR:\n\n"
    "• El modelo S40/40L (y LB) proporciona una combinación de sensores UV e IR "
    "en la que el sensor IR funciona a una longitud de onda entre 2,5 y 3,0µm y "
    "puede detectar combustibles a base de hidrocarburos y fuegos de gas, fuegos "
    "de hidróxido e hidrógeno y fuegos de metales o materia inorgánica.\n\n"
    "• El modelo S40/40L4 (y L4B) es igual al S40/40L, excepto en que el "
    "S40/40L4 funciona a una longitud de onda de 4,5 µm y solo es adecuado para "
    "la detección de fuegos de hidrocarburos.\n\n"
    "La función de Prueba incorporada (BIT) solo se incluye en los modelos "
    "S40/40LB y 40/40L4B."
)


def test_evidence_v2_twin_entry_exists_and_is_appended_last():
    payload = _load_yaml(EVIDENCE_V2)
    keys = list(payload["archetypes"])
    assert keys == [*EVIDENCE_V4_PRELEVER_KEYS, ARCHETYPE]
    prefix = {key: payload["archetypes"][key] for key in EVIDENCE_V4_PRELEVER_KEYS}
    assert _canonical_sha256(prefix) == EVIDENCE_V4_PRELEVER_ARCHETYPES_SHA256


def test_evidence_v2_entry_is_designed_for_the_micron_cell():
    """[H1] La selección de VENTANA es de PRIMER orden, no de segundo.

    Con una sola faceta y `required_any` [bit, incorporada] la única card cae en
    el span del BIT y los valores de banda no llegan nunca al generador.  De ahí
    DOS facetas y `max_cards: 2` en ambas (la clase es comparativa: una variante
    por span, mismo patrón que `system_total` en capacity_quantity).
    """
    payload = _load_yaml(EVIDENCE_V2)
    matrix, spectral = payload["archetypes"][ARCHETYPE]
    assert matrix["id"] == EVIDENCE_FACET
    assert spectral["id"] == SPECTRAL_FACET
    assert matrix["max_cards"] == spectral["max_cards"] == 2
    # La gemela conserva el discriminativo de v4 (incl. el FIX post-STOP-b2).
    assert matrix["required_any"] == ["bit", "incorporada"]
    assert matrix["terms"] == _load_yaml(EVIDENCE_V4)["archetypes"][ARCHETYPE][0]["terms"]
    # La faceta nueva es vocabulario de CLASE con discriminativo propio.
    assert spectral["required_any"] == ["espectral", "micrones", "onda"]
    for facet in (matrix, spectral):
        assert set(facet["required_any"]).issubset(facet["terms"])
        assert not any(char.isdigit() for term in facet["terms"] for char in term)
        assert len(facet["terms"]) >= payload["min_distinct_terms"]


def test_min_distinct_terms_is_global_only_no_dead_per_facet_key():
    """El validador y los DOS consumidores leen `min_distinct_terms` GLOBAL.

    Una clave por-faceta sería contrato-mentira inerte (la clase de defecto que
    esta misma sesión está cerrando), así que no se declara: se pinea que la
    global vale 2 y que ninguna faceta la sombrea.
    """
    payload = _load_yaml(EVIDENCE_V2)
    assert payload["min_distinct_terms"] == 2
    assert all(
        "min_distinct_terms" not in facet
        for facets in payload["archetypes"].values()
        for facet in facets
    )


def test_v2_cards_serve_both_spectral_bands_and_the_bit_difference():
    """El contrato de SERVIDO: los µm llegan al span, no solo al gate."""
    cards = select_evidence_coverage_cards(
        [{"id": "74cc9f95", "content": SPECTRAL_COMPARISON_SPAN}],
        archetype=ARCHETYPE,
        config_path=EVIDENCE_V2,
    )
    served = " ".join(card["quote"] for card in cards)
    assert "2,5 y 3,0µm" in served
    assert "4,5 µm" in served
    assert "Prueba incorporada (BIT)" in served
    assert {SPECTRAL_FACET, EVIDENCE_FACET} == {card["facet"] for card in cards}
    assert all(card["quote"] in SPECTRAL_COMPARISON_SPAN for card in cards)
    assert all(card["exact_source_span_validated"] for card in cards)


def test_v2_cards_also_fail_closed_on_the_norm_declaration_span():
    """El control protegido cat005 no depende de una sola mitad del par.

    v4 ya rechaza el span (la lane no lo selecciona), pero si algún día lo
    seleccionara, v2 tampoco debe fabricarle card.
    """
    assert (
        select_evidence_coverage_cards(
            [{"id": "norm", "content": NORM_DECLARATION_SPAN}],
            archetype=ARCHETYPE,
            config_path=EVIDENCE_V2,
        )
        == []
    )
    assert (
        match_evidence_facets(
            NORM_DECLARATION_SPAN, archetype=ARCHETYPE, config_path=EVIDENCE_V2
        )
        == []
    )


def test_version_stays_in_the_class_vocabulary_without_veto_power():
    """La otra mitad del fix: `version` sigue siendo vocabulario de la clase.

    Se quitó su poder de **sostener sola** el fail-closed, no su pertenencia:
    «versiones digital y analógica» o «Tabla 2: Versiones del detector» siguen
    contando para `min_distinct_terms` cuando hay soporte discriminativo real.
    """
    (match,) = match_evidence_facets(
        VARIANT_COMPARISON_SPAN, archetype=ARCHETYPE, config_path=EVIDENCE_V4
    )
    assert "version" in match["term_hits"]
    # Y sin `bit`/`incorporada`, dos términos de clase (incl. `version`) no bastan.
    assert (
        match_evidence_facets(
            "Tabla 2: Versiones del detector. Modelo y referencia de pedido.",
            archetype=ARCHETYPE,
            config_path=EVIDENCE_V4,
        )
        == []
    )
