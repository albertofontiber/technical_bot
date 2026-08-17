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


# ─────────── s324f · corrección DESPUÉS de transcribir
#
# Contexto: en el piloto, un audio preguntando por *Detnov* se transcribió
# «Death Knob» y el bot no encontró nada — con «Detnov» YA presente en el prompt
# que se le manda a Whisper. El prompt es una pista, no un diccionario.

from src.bot.whisper_vocabulary import (  # noqa: E402
    _CONFUSIONES_OBSERVADAS,
    corregir_transcripcion,
)


def test_el_caso_real_del_piloto():
    assert corregir_transcripcion("centrales de Death Knob") == "centrales de Detnov"


def test_es_indiferente_a_mayusculas_y_espacios():
    for variante in ("death knob", "Death Knob", "DEATH KNOB", "Death  Knob"):
        assert "Detnov" in corregir_transcripcion(f"la {variante} CCD-103")


def test_no_toca_lo_que_no_esta_en_la_tabla():
    """Cada corrección de más es una pregunta buena corrompida."""
    for texto in ("cuantos lazos admite la CAD-250", "detector de Notifier", ""):
        assert corregir_transcripcion(texto) == texto


def test_respeta_limites_de_palabra():
    """Sin `\b`, una subcadena dentro de otra palabra se corrompería."""
    assert corregir_transcripcion("xdeath knobx") == "xdeath knobx"


def test_la_tabla_solo_crece_con_casos_observados():
    """Guardarraíl de DISCIPLINA, no de código: esta tabla es la misma clase de
    artefacto que `_MANUFACTURER_ALIASES` —curada a mano y corta a propósito—.
    Si alguien la llena de confusiones hipotéticas, cada entrada nueva es una
    forma nueva de corromper una transcripción que estaba bien. El tope obliga a
    parar y pensar; subirlo es una decisión, no un descuido."""
    assert len(_CONFUSIONES_OBSERVADAS) <= 25, (
        "si de verdad hay más de 25 confusiones OBSERVADAS, el problema ya no es "
        "una tabla de parches: toca revisar el hint o el modelo de transcripción"
    )
