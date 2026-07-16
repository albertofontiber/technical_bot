import importlib.util


def _module():
    spec = importlib.util.spec_from_file_location(
        "s112_guided_synthesis_probe",
        "scripts/s112_guided_synthesis_probe.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fact_checks_require_compound_relations():
    module = _module()
    assert not all(
        row["present"]
        for row in module._fact_results(
            "hp003", "Hay dos baterias de 12 V y un cable puente."
        )
    )
    assert all(
        row["present"]
        for row in module._fact_results(
            "hp003",
            "Dos baterias de 12 V 7 Ah van en serie; el cable puente une el positivo "
            "de una bateria con el negativo de la otra.",
        )
    )


def test_hp017_requires_correct_menu_number_and_default_rule_action():
    module = _module()
    wrong = "Editar Configuracion > 8: Causa y Efecto; hay reglas por defecto."
    right = (
        "Editar Configuracion > 7: Causa y Efecto; elimina las reglas por defecto "
        "antes de crear reglas personalizadas."
    )
    assert module._fact_results("hp017", wrong)[0]["present"] is False
    assert module._fact_results("hp017", right)[0]["present"] is True
