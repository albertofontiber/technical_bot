"""s332 B1-B3 — asunciones DECLARADAS de la tabla de confusiones ASR.

Cubre las tres piezas del nivel 1 (la tabla que previene y gobierna):
  · la primitiva `Asuncion` con sus DOS enums cerrados (guard estricto);
  · la tabla con `modo`/`case_sensitive`/`flag` POR FILA — con `ASR_AVISOS` off la
    conducta servida es la de hoy (la fila `death knob` corrige, y calla) y con on
    aparecen las filas nuevas: `bqide`→Kidde reescribe, `ID`↔Kidde sólo AVISA;
  · la propagación de las asunciones por `normalize_voice_query`.

El homógrafo es el riesgo real de la fila `ID` (Fable-2): «id» minúscula es el
imperativo español de «ir», e ID3000/ID3002/IDNet son familias que existen. Los
casos negativos de abajo son el contrato, no adorno.
"""
from __future__ import annotations

import pytest

from src.bot.voice_query_normalization import normalize_voice_query
from src.bot.whisper_vocabulary import (
    asr_avisos_on,
    corregir_transcripcion,
    corregir_transcripcion_con_asunciones,
)
from src.orchestrator.contracts import Asuncion


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.delenv("ASR_AVISOS", raising=False)
    yield


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ASR_AVISOS", "on")
    yield


# ─────────────────────────── 1 · la primitiva `Asuncion`
def test_asuncion_valida_se_construye():
    a = Asuncion(kind="marca_asr", detectado="BQide", asumido="Kidde", modo="reescrito")
    assert (a.kind, a.detectado, a.asumido, a.modo) == (
        "marca_asr", "BQide", "Kidde", "reescrito")
    b = Asuncion(kind="marca_corregida", detectado="Kidde", asumido="Kidde", modo="aviso")
    assert b.modo == "aviso"


@pytest.mark.parametrize("kind", ["marca", "asr", "", "MARCA_ASR"])
def test_asuncion_kind_fuera_del_enum_revienta(kind):
    with pytest.raises(ValueError, match="kind"):
        Asuncion(kind=kind, detectado="BQide", asumido="Kidde", modo="reescrito")


@pytest.mark.parametrize("modo", ["reescribir", "warn", "", "AVISO"])
def test_asuncion_modo_fuera_del_enum_revienta(modo):
    with pytest.raises(ValueError, match="modo"):
        Asuncion(kind="marca_asr", detectado="BQide", asumido="Kidde", modo=modo)


@pytest.mark.parametrize("detectado,asumido", [("", "Kidde"), ("   ", "Kidde"),
                                               ("BQide", ""), ("BQide", "  ")])
def test_asuncion_vacia_revienta(detectado, asumido):
    """Un aviso sin lo detectado o sin el término gobernado no dice nada."""
    with pytest.raises(ValueError):
        Asuncion(kind="marca_asr", detectado=detectado, asumido=asumido, modo="aviso")


# ─────────────────────────── 2 · flag OFF = la conducta de hoy, byte a byte
def test_off_la_fila_de_s324f_sigue_corrigiendo_y_sigue_muda(flag_off):
    texto, asunciones = corregir_transcripcion_con_asunciones("la death knob dañada")
    assert texto == "la Detnov dañada"
    assert asunciones == ()


def test_off_las_filas_nuevas_no_existen(flag_off):
    for crudo in ("¿Qué centrales BQide tienes?", "¿Qué centrales ID tienes?"):
        texto, asunciones = corregir_transcripcion_con_asunciones(crudo)
        assert texto == crudo
        assert asunciones == ()


def test_off_el_envoltorio_compat_devuelve_solo_el_texto(flag_off):
    assert corregir_transcripcion("centrales de Death Knob") == "centrales de Detnov"


# ─────────────────────────── 3 · flag ON = las filas nuevas, con voz
def test_on_bqide_se_reescribe_y_lo_declara(flag_on):
    texto, asunciones = corregir_transcripcion_con_asunciones("¿Qué centrales BQide tienes?")
    assert texto == "¿Qué centrales Kidde tienes?"
    assert asunciones == (
        Asuncion(kind="marca_asr", detectado="BQide", asumido="Kidde", modo="reescrito"),
    )


def test_on_bqide_es_insensible_a_mayusculas_en_su_fila(flag_on):
    texto, asunciones = corregir_transcripcion_con_asunciones("¿Qué centrales BQIDE tienes?")
    assert texto == "¿Qué centrales Kidde tienes?"
    assert [a.detectado for a in asunciones] == ["BQIDE"]


def test_on_la_fila_vieja_tambien_declara_su_asuncion(flag_on):
    texto, asunciones = corregir_transcripcion_con_asunciones("la death knob dañada")
    assert texto == "la Detnov dañada"
    assert asunciones == (
        Asuncion(kind="marca_asr", detectado="death knob", asumido="Detnov",
                 modo="reescrito"),
    )


def test_on_id_solo_avisa_y_deja_el_texto_intacto(flag_on):
    """La familia ID existe: reescribirla corrompería al usuario legítimo."""
    crudo = "¿Qué centrales ID tienes?"
    texto, asunciones = corregir_transcripcion_con_asunciones(crudo)
    assert texto == crudo
    assert asunciones == (
        Asuncion(kind="marca_asr", detectado="ID", asumido="Kidde", modo="aviso"),
    )


@pytest.mark.parametrize("crudo", [
    "id al menú de configuración",   # imperativo español de «ir» (case)
    "ve e id a la pantalla",
])
def test_on_el_id_minuscula_no_dispara_nada(flag_on, crudo):
    assert corregir_transcripcion_con_asunciones(crudo) == (crudo, ())


@pytest.mark.parametrize("crudo", [
    "la ID3000 en fallo",
    "IDNet no responde",
    "la ID3002",
])
def test_on_las_familias_id_no_disparan_nada(flag_on, crudo):
    """`\\b` no corta ID3000/IDNet: letra→dígito y letra→letra no son frontera."""
    assert corregir_transcripcion_con_asunciones(crudo) == (crudo, ())


def test_on_una_fila_que_casa_varias_veces_produce_una_sola_asuncion(flag_on):
    texto, asunciones = corregir_transcripcion_con_asunciones(
        "BQide y otra BQide más")
    assert texto == "Kidde y otra Kidde más"
    assert len(asunciones) == 1


# ─────────────────────────── 4 · el lever, estricto y sin caché
def test_asr_avisos_valor_raro_revienta_ruidoso(monkeypatch):
    monkeypatch.setenv("ASR_AVISOS", "1")
    with pytest.raises(RuntimeError, match="ASR_AVISOS"):
        asr_avisos_on()


def test_asr_avisos_se_lee_en_cada_llamada(monkeypatch):
    """Sin caché de módulo: un flip en Railway togglea sin restart (y los tests
    pueden alternar el entorno dentro de un mismo proceso)."""
    monkeypatch.delenv("ASR_AVISOS", raising=False)
    assert asr_avisos_on() is False
    monkeypatch.setenv("ASR_AVISOS", "on")
    assert asr_avisos_on() is True
    monkeypatch.setenv("ASR_AVISOS", "off")
    assert asr_avisos_on() is False


# ─────────────────────────── 5 · propagación por el camino de VOZ
def test_normalize_voice_query_propaga_la_asuncion(flag_on):
    crudo = "¿Qué centrales BQide tienes?"
    resultado = normalize_voice_query(crudo, models=())

    assert "Kidde" in resultado.normalized
    assert resultado.raw == crudo                      # el ASR crudo sigue visible
    assert [(a.detectado, a.asumido, a.modo) for a in resultado.asunciones] == [
        ("BQide", "Kidde", "reescrito")]


def test_normalize_voice_query_sin_flag_no_propaga_nada(flag_off):
    crudo = "¿Qué centrales BQide tienes?"
    resultado = normalize_voice_query(crudo, models=())

    assert resultado.normalized == crudo
    assert resultado.asunciones == ()


# ─────────────────────────── 6 · el render, en el camino REAL de `handle_voice`
#
# La declaración sólo vale si el técnico la VE: se ejerce el manejador de verdad
# (dobles al borde — transcripción, consentimiento y `_servir_turno`) y se lee el
# mensaje que sale por `reply_text`.
def _correr_voz(monkeypatch, transcripcion: str) -> tuple[list, list]:
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import src.bot.telegram_bot as bot

    monkeypatch.setattr(bot, "has_consent", lambda _uid: True)

    async def _transcribe(_path):
        return transcripcion
    monkeypatch.setattr(bot, "transcribe_audio", _transcribe)
    monkeypatch.setattr(bot, "_servir_turno", AsyncMock())

    voz = SimpleNamespace(file_id="v1", duration=3, file_name=None,
                          mime_type="audio/ogg")
    mensaje = SimpleNamespace(
        text=None, voice=voz, audio=None, reply_to_message=None,
        chat=SimpleNamespace(send_action=AsyncMock()), reply_text=AsyncMock())
    update = SimpleNamespace(message=mensaje,
                             effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(
        bot=SimpleNamespace(get_file=AsyncMock(
            return_value=SimpleNamespace(download_to_drive=AsyncMock()))),
        user_data={})

    asyncio.run(bot.handle_voice(update, context))
    llamadas = mensaje.reply_text.await_args_list
    return [c.args[0] for c in llamadas], [c.kwargs for c in llamadas]


def test_confirmacion_declara_la_marca_reescrita(monkeypatch, flag_on):
    mensajes, kwargs = _correr_voz(monkeypatch, "¿Qué centrales BQide tienes?")

    assert mensajes[0] == (
        "🎤 ¿Qué centrales BQide tienes?\n"
        "🏷 Entiendo que preguntas por Kidde (el audio se transcribió como "
        "«BQide»). Si no es eso, dímelo."
    )
    # Sin `parse_mode` a propósito: el ASR crudo puede traer cualquier carácter y
    # un Markdown mal formado tumbaría el mensaje entero.
    assert kwargs[0] == {}


def test_confirmacion_avisa_de_la_confusion_sin_tocar_el_texto(monkeypatch, flag_on):
    mensajes, _ = _correr_voz(monkeypatch, "¿Qué centrales ID tienes?")

    assert mensajes[0] == (
        "🎤 ¿Qué centrales ID tienes?\n"
        "ℹ️ Nota: hay una confusión de voz observada «ID»↔Kidde. "
        "Si dictaste Kidde, dímelo."
    )


def test_confirmacion_sin_flag_es_la_de_hoy(monkeypatch, flag_off):
    """GC0 en miniatura: con el lever apagado, el mensaje servido no cambia."""
    mensajes, _ = _correr_voz(monkeypatch, "¿Qué centrales BQide tienes?")
    assert mensajes[0] == "🎤 ¿Qué centrales BQide tienes?"


# ─────────────────────── s334 · 4ª/5ª corrupciones observadas de «Kidde» (21-ago tarde)
def test_kide_e_itide_reescriben_con_flag_on(monkeypatch):
    monkeypatch.setenv("ASR_AVISOS", "on")
    from src.bot.whisper_vocabulary import corregir_transcripcion_con_asunciones
    for crudo in ("Quería decir de KIDE.", "ITIDE", "¿qué centrales itide tienes?"):
        texto, asun = corregir_transcripcion_con_asunciones(crudo)
        assert "Kidde" in texto, crudo
        assert [a.modo for a in asun] == ["reescrito"], crudo


def test_kide_no_colisiona_con_kidde_ni_con_flag_off(monkeypatch):
    from src.bot.whisper_vocabulary import corregir_transcripcion_con_asunciones
    monkeypatch.setenv("ASR_AVISOS", "on")
    texto, asun = corregir_transcripcion_con_asunciones("¿Qué centrales de KIDDE tienes?")
    assert texto == "¿Qué centrales de KIDDE tienes?" and not asun  # \b: kidde intacta
    monkeypatch.delenv("ASR_AVISOS", raising=False)
    texto, asun = corregir_transcripcion_con_asunciones("Quería decir de KIDE.")
    assert texto == "Quería decir de KIDE." and not asun            # flag off = hoy

# ───────────────────── s335b · 8ª corrupción observada de «Kidde» (21-ago 15:54Z)
def test_quide_reescribe_con_flag_on_y_quiere_jamas(monkeypatch):
    """«quide» (f8dcb59a) se tabula — 0 hits en corpus, sin lectura legítima; con la
    fila, «Quería decir quide.» recorre tabla→plantilla→rebuild como KIDE en s334.
    Su gemela «quiere» (4c868ab7, misma conversación) NO se tabula JAMÁS: palabra
    española real (145 apariciones en chunks_v2) — este test la PINNA fuera."""
    monkeypatch.setenv("ASR_AVISOS", "on")
    from src.bot.whisper_vocabulary import (
        _CONFUSIONES_OBSERVADAS,
        corregir_transcripcion_con_asunciones,
    )
    texto, asun = corregir_transcripcion_con_asunciones("Quería decir quide.")
    assert "Kidde" in texto and [a.modo for a in asun] == ["reescrito"]
    assert asun[0].detectado.lower() == "quide"
    # la palabra legítima pasa INTACTA, y ninguna fila la tiene como patrón
    texto, asun = corregir_transcripcion_con_asunciones("El cliente quiere dos centrales.")
    assert texto == "El cliente quiere dos centrales." and not asun
    assert all("quiere" not in fila[0] for fila in _CONFUSIONES_OBSERVADAS)


def test_quide_flag_off_no_cambia(monkeypatch):
    monkeypatch.delenv("ASR_AVISOS", raising=False)
    from src.bot.whisper_vocabulary import corregir_transcripcion_con_asunciones
    texto, asun = corregir_transcripcion_con_asunciones("Quería decir quide.")
    assert texto == "Quería decir quide." and not asun
