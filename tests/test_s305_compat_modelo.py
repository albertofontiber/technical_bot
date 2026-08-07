"""s305/#64 — el generador puede cambiar de modelo sin romperse.

Los dos bloqueadores que s305 destapó al intentar medir el techo con generadores más
fuertes. Con el código anterior, poner un modelo de razonamiento en `LLM_MODEL` rompía el
bot en la PRIMERA consulta:

  1. `temperature` — el envelope la fija a 0 (reproducibilidad de eval) y los modelos de
     razonamiento la rechazan con 400 «deprecated for this model»;
  2. `content[0].text` — esos modelos devuelven un `ThinkingBlock` en la posición 0.

Contrato que se fija aquí, y el orden importa:
  · el modelo ACTUAL no cambia ni un byte (el envelope sigue llevando `temperature`, y el
    texto sale del mismo bloque) — un arreglo de compatibilidad que altere el camino vivo
    sería peor que el problema;
  · el rechazo se APRENDE en runtime (no hay lista de familias que mantener) y se reintenta
    UNA vez, con la identidad de caché recalculada sobre lo REALMENTE enviado;
  · el detector es estricto: un 400 por otra causa NO dispara el reintento — esconderlo
    detrás de un envelope distinto convertiría un error real en un fallo mudo.
"""

import httpx
import pytest

import src.rag.generator as generator
from src.rag.generator import _first_text_block, _rejects_temperature


# Un chunk ADMISIBLE mínimo: con la lista vacía el generador corta antes de llamar al
# modelo (no hay evidencia que servir) y estos tests medirían un camino que no existe.
_CHUNK = {
    "content": "Bornes 1 y 2: alimentación del sensor.",
    "similarity": 0.9,
    "source_file": "manual_x",
    "page_number": 4,
    "product_model": "CAD-250",
}


def _error_400(mensaje: str) -> "generator.anthropic.BadRequestError":
    """`BadRequestError` REAL del SDK: exige una `httpx.Response` con su `request`.
    Construirla de verdad (en vez de un doble) es lo que hace que el test ejerza el
    mismo tipo de excepción que llega en producción."""
    peticion = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    respuesta = httpx.Response(400, request=peticion,
                               json={"type": "error",
                                     "error": {"type": "invalid_request_error",
                                               "message": mensaje}})
    return generator.anthropic.BadRequestError(mensaje, response=respuesta, body=None)


class _Bloque:
    def __init__(self, tipo, text=None):
        self.type = tipo
        if text is not None:
            self.text = text


class _Uso:
    input_tokens = 100
    output_tokens = 50


class _Respuesta:
    """Mismos atributos que consume el generador: sin `stop_reason` ni `usage` el doble
    mediría un contrato distinto del real."""

    def __init__(self, bloques):
        self.content = bloques
        self.stop_reason = "end_turn"
        self.usage = _Uso()


# --------------------------------------------------------------- el bloque de texto


def test_texto_en_la_posicion_0_se_lee_igual_que_siempre():
    """El caso del modelo ACTUAL: equivalencia byte a byte con `content[0].text`."""
    resp = _Respuesta([_Bloque("text", "la respuesta")])
    assert _first_text_block(resp) == "la respuesta"


def test_texto_detras_de_un_bloque_de_razonamiento():
    """El bloqueador real: los modelos de razonamiento ponen `thinking` en content[0]."""
    resp = _Respuesta([_Bloque("thinking"), _Bloque("text", "la respuesta")])
    assert _first_text_block(resp) == "la respuesta"


def test_un_bloque_con_texto_pero_SIN_type_sigue_funcionando():
    """La equivalencia histórica, y no es teórica: la primera versión de este arreglo
    exigía `type == "text"` y rompió 29 tests con dobles que exponen `.text` sin declarar
    tipo — el código antiguo los leía. Un arreglo de compatibilidad que rompe la
    compatibilidad es peor que el problema que resuelve."""
    class _SinTipo:
        text = "la respuesta"

    assert _first_text_block(_Respuesta([_SinTipo()])) == "la respuesta"


def test_sin_nada_legible_falla_RUIDOSO():
    """Devolver «» dejaría que el transporte lo confundiera con «el modelo no supo
    contestar» — un fallo de integración disfrazado de respuesta legítima."""
    resp = _Respuesta([_Bloque("thinking"), _Bloque("tool_use")])
    with pytest.raises(ValueError, match="ningún bloque de texto"):
        _first_text_block(resp)


# ------------------------------------------------------------------- el detector


def test_el_detector_de_temperature_es_estricto():
    assert _rejects_temperature(Exception("`temperature` is deprecated for this model"))
    # Un 400 por OTRA causa no debe disparar el reintento: se propaga.
    assert not _rejects_temperature(Exception("max_tokens exceeds model maximum"))
    assert not _rejects_temperature(Exception("messages: final assistant content"))


# ------------------------------------------------- el envelope, extremo a extremo


class _MensajesFalsos:
    """Cliente que rechaza `temperature` como lo hace el proveedor real."""

    def __init__(self, modelos_que_rechazan: set[str]):
        self.rechazan = modelos_que_rechazan
        self.envelopes: list[dict] = []

    def create(self, **kw):
        self.envelopes.append(dict(kw))
        if kw["model"] in self.rechazan and "temperature" in kw:
            raise _error_400("`temperature` is deprecated for this model")
        return _Respuesta([_Bloque("thinking"), _Bloque("text", "respuesta del modelo")])


@pytest.fixture(autouse=True)
def _memoria_limpia():
    """El aprendizaje es de PROCESO: sin limpiar, un test contaminaría al siguiente."""
    generator._MODELS_REJECTING_TEMPERATURE.clear()
    yield
    generator._MODELS_REJECTING_TEMPERATURE.clear()


def _cliente_falso(monkeypatch, rechazan: set[str]) -> _MensajesFalsos:
    mensajes = _MensajesFalsos(rechazan)

    class _Cliente:
        def __init__(self, **kw):
            self.messages = mensajes

    monkeypatch.setattr(generator.anthropic, "Anthropic", _Cliente)
    return mensajes


def test_el_modelo_actual_sigue_enviando_temperature(monkeypatch):
    """La garantía que hace seguro este arreglo: el camino VIVO no cambia."""
    mensajes = _cliente_falso(monkeypatch, rechazan=set())
    generator.generate_answer("¿bornes del sensor?", [dict(_CHUNK)])
    assert len(mensajes.envelopes) == 1, "no debe haber reintento donde no hay rechazo"
    assert mensajes.envelopes[0]["temperature"] == 0
    assert mensajes.envelopes[0]["model"] == generator.LLM_MODEL


def test_un_modelo_que_rechaza_temperature_se_reintenta_sin_ella(monkeypatch):
    mensajes = _cliente_falso(monkeypatch, rechazan={generator.LLM_MODEL})
    generator.generate_answer("¿bornes del sensor?", [dict(_CHUNK)])

    assert len(mensajes.envelopes) == 2, "debe reintentar exactamente una vez"
    assert "temperature" in mensajes.envelopes[0]       # el primero, como siempre
    assert "temperature" not in mensajes.envelopes[1]   # el reintento, sin ella
    # Y lo APRENDE: el siguiente turno ya no paga el 400.
    assert generator.LLM_MODEL in generator._MODELS_REJECTING_TEMPERATURE
    generator.generate_answer("otra pregunta", [dict(_CHUNK)])
    assert len(mensajes.envelopes) == 3
    assert "temperature" not in mensajes.envelopes[2]


def test_un_400_por_otra_causa_NO_se_reintenta(monkeypatch):
    """Reintentar a ciegas escondería un error real de la petición."""
    mensajes = _MensajesFalsos(set())

    def create(**kw):
        mensajes.envelopes.append(dict(kw))
        raise _error_400("max_tokens exceeds model maximum")

    mensajes.create = create

    class _Cliente:
        def __init__(self, **kw):
            self.messages = mensajes

    monkeypatch.setattr(generator.anthropic, "Anthropic", _Cliente)
    with pytest.raises(generator.anthropic.BadRequestError):
        generator.generate_answer("¿bornes?", [dict(_CHUNK)])
    assert len(mensajes.envelopes) == 1                # sin reintento
    assert not generator._MODELS_REJECTING_TEMPERATURE  # y sin aprender nada falso


# ----------------------------------------------- el seam de entorno (s308, GO Alberto)


def test_llm_model_es_configurable_por_entorno_y_su_default_no_cambia():
    """El swap de modelo es una variable de Railway (patrón CHUNKS_TABLE), no un
    deploy de código; y SIN la variable, producción queda byte-idéntica."""
    import subprocess
    import sys

    salida = subprocess.run(
        [sys.executable, "-c",
         "import os; os.environ.pop('LLM_MODEL', None); "
         "from src.config import LLM_MODEL; print(LLM_MODEL)"],
        capture_output=True, text=True, cwd=".",
    )
    assert salida.stdout.strip() == "claude-sonnet-4-6"

    salida = subprocess.run(
        [sys.executable, "-c",
         "import os; os.environ['LLM_MODEL'] = 'claude-opus-5'; "
         "from src.config import LLM_MODEL; print(LLM_MODEL)"],
        capture_output=True, text=True, cwd=".",
    )
    assert salida.stdout.strip() == "claude-opus-5"
