from src.bot.whisper_vocabulary import (
    _MAX_PROMPT_CHARS,
    _STATIC_HINT,
    _select_hard_models,
    get_whisper_prompt,
)
from src.rag.catalog import all_models, model_manufacturer


def test_hard_model_priority_reserves_one_slot_per_manufacturer():
    models = ["A100", "A200", "B900", "CLEAN", "C700", "B800"]
    manufacturers = {
        "A100": "Maker A",
        "A200": "Maker A",
        "B900": "Maker B",
        "C700": "Maker C",
        "B800": "Maker B",
    }

    selected = _select_hard_models(models, manufacturers.get)

    assert selected[:3] == ["A100", "B900", "C700"]
    assert selected[3:] == ["A200", "B800"]


def test_hard_model_selection_remains_frequency_ordered_without_lookup():
    assert _select_hard_models(["A100", "A200", "PLAIN", "B300"]) == [
        "A100",
        "A200",
        "B300",
    ]


def test_real_prompt_is_bounded_and_represents_catalog_manufacturers():
    prompt = get_whisper_prompt()
    hard_models = _select_hard_models(all_models(), model_manufacturer)
    expected_first = {}
    for model in hard_models:
        manufacturer = model_manufacturer(model)
        if manufacturer:
            expected_first.setdefault(manufacturer, model)

    assert prompt.startswith(_STATIC_HINT)
    assert len(prompt) <= _MAX_PROMPT_CHARS
    assert expected_first
    assert all(model in prompt for model in expected_first.values())
