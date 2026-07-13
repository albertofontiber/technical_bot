import re
from pathlib import Path

from src.rag.query_facets import expand_query_facets


V2 = Path(__file__).resolve().parents[1] / "config" / "retrieval_facets_v2.yaml"
V3 = Path(__file__).resolve().parents[1] / "config" / "retrieval_facets_v3.yaml"


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
