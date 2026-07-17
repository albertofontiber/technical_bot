import pytest

from src.bot.voice_query_normalization import normalize_voice_query


MODELS = (
    "CAD-250",
    "ID3000",
    "AFP-400",
    "2X-A",
    "ZXe",
    "20/20I",
    "CAD-150",
    "CAD-150-8",
)


@pytest.mark.parametrize(
    "raw,expected,canonical",
    [
        ("consumo de ce a de doscientos cincuenta", "consumo de CAD-250", "CAD-250"),
        ("fallo en i de tres mil", "fallo en ID3000", "ID3000"),
        ("reiniciar a efe pe cuatrocientos", "reiniciar AFP-400", "AFP-400"),
        ("configurar dos equis a", "configurar 2X-A", "2X-A"),
        ("averia en zeta equis e", "averia en ZXe", "ZXe"),
        ("alcance del veinte veinte i", "alcance del 20/20I", "20/20I"),
        ("usar ce a de uno cinco cero", "usar CAD-150", "CAD-150"),
        ("usar ce a de ciento cincuenta ocho", "usar CAD-150-8", "CAD-150-8"),
    ],
)
def test_normalizes_exact_catalog_derived_spoken_forms(raw, expected, canonical):
    result = normalize_voice_query(raw, models=MODELS)

    assert result.normalized == expected
    assert result.changed is True
    assert [item.canonical for item in result.substitutions] == [canonical]


@pytest.mark.parametrize(
    "raw",
    [
        "consumo de CAD-250",  # already directly detectable
        "consumo de cad 250",  # separator variation already detectable
        "consumo de cabe doscientos cincuenta",  # phonetic guess is unsafe
        "configura dos equipos en la zona a",  # isolated words are not a full code
        "modelo completamente desconocido nueve nueve nueve",
        "",
    ],
)
def test_unknown_or_already_detectable_transcript_fails_open(raw):
    result = normalize_voice_query(raw, models=MODELS)

    assert result.normalized == raw
    assert result.substitutions == ()


def test_ambiguous_spoken_surface_is_not_rewritten():
    # "cu diez" can be the spoken letter Q + 10 or the literal model CU10.
    result = normalize_voice_query("revisar cu diez", models=("Q10", "CU10"))

    assert result.normalized == "revisar cu diez"
    assert result.substitutions == ()


def test_very_short_alphanumeric_code_is_too_ambiguous_for_auto_rewrite():
    result = normalize_voice_query("valor equis uno", models=("X1",))

    assert result.normalized == "valor equis uno"
    assert result.substitutions == ()


def test_normalizes_multiple_non_overlapping_models_in_order():
    result = normalize_voice_query(
        "comparar i de tres mil con a efe pe cuatrocientos",
        models=MODELS,
    )

    assert result.normalized == "comparar ID3000 con AFP-400"
    assert [item.canonical for item in result.substitutions] == ["ID3000", "AFP-400"]


def test_missing_catalog_input_is_byte_stable():
    raw = "  i de tres mil  "

    result = normalize_voice_query(raw, models=())

    assert result.raw == raw
    assert result.normalized == raw
