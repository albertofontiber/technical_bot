import hashlib
import re
from pathlib import Path

import pytest
import yaml

from src.rag.query_facets import MULTI_MATCH_SCHEMA, _load, expand_query_facets


V2 = Path(__file__).resolve().parents[1] / "config" / "retrieval_facets_v2.yaml"
V3 = Path(__file__).resolve().parents[1] / "config" / "retrieval_facets_v3.yaml"
V4 = Path(__file__).resolve().parents[1] / "config" / "retrieval_facets_v4.yaml"
V5 = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "retrieval_facets_v5_document_local.yaml"
)

# s279 seccion 3 / A11: the shared validator changed for v5, so the v4 the
# first-match consumers load is pinned BYTE-equal (LF-normalized, checkout
# independent) — equivalence verified, not assumed.
V4_SHA256_LF = "fcc5aa7ade886a864cdd654757a79709136968c3d010ffde8a94dc0eae0401bb"

CAT017_QUERY = (
    "¿Como se cablea y se da de alta (configura) un lazo en la central "
    "Notifier INSPIRE (E10/E15)?"
)


def test_facets_add_no_hidden_numeric_tokens():
    question = "¿Cómo se conecta un módulo de aislamiento en un lazo?"
    plan = expand_query_facets(question)
    assert plan["archetype"] == "connect_install_wire"
    assert not re.search(r"\d", " ".join(plan["needs"]))


def test_false_premise_procedure_opens_architecture_and_persistence_lanes():
    plan = expand_query_facets(
        "Necesito cambiar una batería tampón sin perder configuración"
    )
    assert plan["archetype"] == "replace_without_loss"
    emitted = " ".join(plan["needs"])
    assert "redundancia" in emitted
    assert "persistente" in emitted


def test_neutral_specs_query_falls_through_without_expansion():
    question = "¿Cuáles son las características técnicas del equipo?"
    plan = expand_query_facets(question)
    assert plan == {
        "archetype": None,
        "needs": ["Cuáles son las características técnicas del equipo"],
    }


def test_v2_stem_prefix_matches_conjugated_change_without_qid_vocabulary():
    plan = expand_query_facets(
        "¿Cómo se cambia una batería tampón sin perder configuración?", config_path=V2
    )
    assert plan["archetype"] == "replace_without_loss"
    assert "redundancia" in " ".join(plan["needs"])


def test_v3_does_not_treat_password_configuration_as_cause_effect():
    plan = expand_query_facets(
        "En la INSPIRE, ¿cómo se configuran las contraseñas de nivel 2 y nivel 3?",
        config_path=V3,
    )
    assert plan["archetype"] is None


def test_v3_routes_compatibility_before_installation_language():
    plan = expand_query_facets(
        "¿Es compatible este detector y puedo montarlo en el lazo?", config_path=V3
    )
    assert plan["archetype"] == "compatibility"


def test_v3_still_routes_real_cause_effect_programming():
    plan = expand_query_facets(
        "¿Cómo se programa una zona para activar una salida de sirena?", config_path=V3
    )
    assert plan["archetype"] == "program_delay_cause_effect"


def test_v3_installation_noun_and_installed_context_do_not_trigger_install_route():
    assert expand_query_facets(
        "Necesito un detector para una instalación Notifier", config_path=V3
    )["archetype"] is None
    assert expand_query_facets(
        "Central Morley instalada en España: ¿cuál es el nivel de alarma?",
        config_path=V3,
    )["archetype"] is None


def test_v3_conjugated_connection_still_routes_install_task():
    plan = expand_query_facets(
        "¿Cómo se conecta un módulo aislador al lazo?", config_path=V3
    )
    assert plan["archetype"] == "connect_install_wire"


def test_v3_fault_noun_in_spec_question_does_not_trigger_troubleshooting():
    plan = expand_query_facets(
        "¿Cómo se comporta el relé de avería ante un fallo de alimentación?",
        config_path=V3,
    )
    assert plan["archetype"] is None


def test_v3_diagnostic_and_reset_intents_still_route_fault_recovery():
    assert expand_query_facets(
        "El equipo muestra una alarma y quiero diagnosticarla", config_path=V3
    )["archetype"] == "fault_reset_recovery"
    assert expand_query_facets(
        "Después de resetear no vuelve a normal", config_path=V3
    )["archetype"] == "fault_reset_recovery"


def test_v3_battery_capacity_is_not_device_capacity():
    plan = expand_query_facets(
        "¿Cómo se calcula la capacidad de batería en Ah?", config_path=V3
    )
    assert plan["archetype"] == "battery_sizing"


# --- s279 seccion 3 + A11: v5 document-local fork, shared-validator guards ---


def test_v4_bytes_and_loaded_payload_survive_the_v5_validator_change():
    raw = V4.read_bytes()
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == V4_SHA256_LF
    # The new validator must load v4 as the EXACT parse of those bytes: no
    # mutation, no defaulting, no new keys (A11 equivalence, not assumption).
    assert _load(str(V4.resolve())) == yaml.safe_load(raw.decode("utf-8"))


def test_v5_schema_loads_with_bounded_multi_match_and_six_term_archetype():
    payload = _load(str(V5.resolve()))
    assert payload["schema"] == MULTI_MATCH_SCHEMA
    assert payload["policy"] == "first_match"
    assert payload["max_needs"] == 3
    assert payload["multi_match"] == {"enabled": True, "max": 2}
    # v4 archetypes preserved EXACTLY and in order ahead of the new one, so
    # the primary facet of every existing query cannot move under v5.
    v4_payload = yaml.safe_load(V4.read_text(encoding="utf-8"))
    assert payload["archetypes"][:-1] == v4_payload["archetypes"]
    commissioning = payload["archetypes"][-1]
    assert commissioning["id"] == "commissioning_setup"
    (need,) = commissioning["needs"]
    assert need.replace("{query}", "").split() == [
        "sitio",
        "edificio",
        "licencia",
        "bin",
        "alta",
        "portal",
    ]


def test_v5_config_is_rejected_for_first_match_consumers():
    with pytest.raises(RuntimeError, match="first_match consumers"):
        expand_query_facets(CAT017_QUERY, config_path=V5)


def test_multi_match_mode_is_rejected_on_first_match_schemas():
    with pytest.raises(RuntimeError, match="multi_match mode"):
        expand_query_facets(CAT017_QUERY, config_path=V4, multi_match=True)


def test_multi_match_returns_primary_plus_second_archetype_in_stable_order():
    plan = expand_query_facets(CAT017_QUERY, config_path=V5, multi_match=True)
    assert plan["archetype"] == "connect_install_wire"
    assert plan["archetypes"] == ["connect_install_wire", "commissioning_setup"]
    # Primary facet needs are byte-identical to the v4 first-match expansion;
    # the second archetype only APPENDS its need group, in declaration order.
    v4_plan = expand_query_facets(CAT017_QUERY, config_path=V4)
    assert plan["needs"][: len(v4_plan["needs"])] == v4_plan["needs"]
    assert plan["needs"][-1] == (
        "Como se cablea y se da de alta (configura) un lazo en la central "
        "Notifier INSPIRE (E10/E15) sitio edificio licencia bin alta portal"
    )
    assert len(plan["needs"]) == len(v4_plan["needs"]) + 1


def test_multi_match_is_capped_at_two_archetypes_in_declaration_order():
    plan = expand_query_facets(
        "¿Cuantos detectores admite el lazo, como se conectan y como se dan "
        "de alta?",
        config_path=V5,
        multi_match=True,
    )
    # Three archetypes match; only the first two (declaration order) survive.
    assert plan["archetypes"] == ["capacity_quantity", "connect_install_wire"]
    assert plan["archetype"] == "capacity_quantity"


def test_multi_match_no_match_falls_through_with_empty_archetypes():
    plan = expand_query_facets(
        "¿Cuáles son las características técnicas del equipo?",
        config_path=V5,
        multi_match=True,
    )
    assert plan == {
        "archetype": None,
        "archetypes": [],
        "needs": ["Cuáles son las características técnicas del equipo"],
    }


def test_unknown_schema_still_raises_runtimeerror(tmp_path):
    bad = tmp_path / "facets_unknown_schema.yaml"
    bad.write_text(
        V4.read_text(encoding="utf-8").replace(
            "schema: retrieval_facets_v4", "schema: retrieval_facets_v99", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="unsupported retrieval facet schema"):
        expand_query_facets("¿Como se conecta el lazo?", config_path=bad)


def test_multi_match_key_is_rejected_outside_the_v5_schema(tmp_path):
    bad = tmp_path / "facets_v4_with_multi_match.yaml"
    bad.write_text(
        V4.read_text(encoding="utf-8").replace(
            "policy: first_match\n",
            "policy: first_match\nmulti_match:\n  enabled: true\n  max: 2\n",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="exclusive to the document-local"):
        expand_query_facets("¿Como se conecta el lazo?", config_path=bad)


@pytest.mark.parametrize(
    "mutation",
    [
        ("multi_match:\n  enabled: true\n  max: 2\n", ""),
        (
            "multi_match:\n  enabled: true\n  max: 2\n",
            "multi_match:\n  enabled: true\n  max: 3\n",
        ),
        (
            "multi_match:\n  enabled: true\n  max: 2\n",
            "multi_match:\n  enabled: false\n  max: 2\n",
        ),
    ],
)
def test_v5_multi_match_block_is_pinned_by_the_validator(tmp_path, mutation):
    old, new = mutation
    text = V5.read_text(encoding="utf-8")
    assert old in text
    bad = tmp_path / f"facets_v5_mut_{hashlib.sha256(new.encode()).hexdigest()[:8]}.yaml"
    bad.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(RuntimeError, match="requires multi_match"):
        _load(str(bad.resolve()))
