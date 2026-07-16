import importlib.util


def _module():
    spec = importlib.util.spec_from_file_location(
        "s112_guided_repair_probe", "scripts/s112_guided_repair_probe.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repair_prompt_is_bounded_to_draft_and_source_obligations():
    module = _module()
    prompt = module.build_repair_prompt(
        "Pregunta",
        "Respuesta [F1]",
        [
            {
                "fragment_number": 3,
                "statement": "Pestaña Programa; Zona; CBE.",
            }
        ],
    )
    assert "Respuesta [F1]" in prompt
    assert "OBL-1 [F3]: Pestaña Programa; Zona; CBE." in prompt
    assert "full retrieval" not in prompt.lower()
    assert "No añadas valores" in prompt
