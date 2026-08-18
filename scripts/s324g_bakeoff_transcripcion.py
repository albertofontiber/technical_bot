# -*- coding: utf-8 -*-
"""s324g — Bake-off de transcripción: ¿el problema es el prompt o el MODELO?

CONTEXTO. En el piloto, «Detnov» se transcribió «Death Knob» y, al reintentarlo,
«Death Knife». La tabla de confusiones que puse es un parche reactivo: cubre lo
visto y falla con la variante siguiente del mismo nombre. Alberto lo dijo con
razón, y además señaló lo que de verdad importa: aunque la corrección acertara,
**el técnico ve su pregunta mal transcrita**, y eso hunde la confianza igual.

LO QUE MIDE. El repo ya expone tres modelos (`src/config.py`) y usa el más
VIEJO por defecto (`whisper-1`, 2022). Los otros dos nunca se han probado. Esto
genera audio con TTS diciendo frases reales del dominio y compara los tres.

GAP DECLARADO, y no es menor: **la voz es sintética**. Un técnico en obra tiene
acento, prisa y ruido de fondo. Este bake-off sirve para ORDENAR los candidatos,
no para prometer una tasa de acierto en campo; el testigo real sigue siendo un
audio de verdad. Si el modelo nuevo no gana aquí, tampoco ganará allí — pero si
gana aquí, hay que confirmarlo con un audio humano antes de cambiar nada.
"""
from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv                                   # noqa: E402

load_dotenv(".env")

from src.bot.whisper_vocabulary import get_whisper_prompt        # noqa: E402

SALIDA = pathlib.Path(os.environ.get("BAKEOFF_DIR", "."))

#: Frases del dominio con las marcas que más duelen si se pierden. La marca va
#: en el sujeto: si se transcribe mal, el turno se queda sin ancla y el bot
#: responde «no tengo eso» — el fallo exacto del piloto.
FRASES = [
    ("Detnov",        "¿Qué centrales de Detnov tienes?"),
    ("Detnov",        "Necesito el manual de la CAD 250 de Detnov"),
    ("Kidde",         "¿Qué centrales de Kidde tienes?"),
    ("Aritech",       "Dame las centrales de Aritech"),
    ("Xtralis",       "¿Tienes documentación de Xtralis?"),
    ("Notifier",      "¿Cuántos lazos admite la ID3000 de Notifier?"),
    ("Morley",        "Busco el conexionado de un detector Morley"),
    ("System Sensor", "¿Qué detectores de System Sensor tienes?"),
]

MODELOS = ("whisper-1", "gpt-4o-mini-transcribe-2025-12-15", "gpt-4o-transcribe")


def _tts(cliente, texto: str, destino: pathlib.Path) -> None:
    """Voz sintética en español. `alloy` es neutra; no imita a un técnico."""
    with cliente.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts", voice="alloy", input=texto,
        instructions="Habla en español de España, tono neutro, ritmo normal.",
        response_format="mp3",
    ) as r:
        r.stream_to_file(destino)


def main() -> int:
    from openai import OpenAI

    cliente = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = get_whisper_prompt()
    SALIDA.mkdir(parents=True, exist_ok=True)

    print(f"prompt de vocabulario: {len(prompt)} chars\n")
    aciertos = {m: 0 for m in MODELOS}
    total = 0

    for i, (marca, frase) in enumerate(FRASES):
        audio = SALIDA / f"frase_{i}.mp3"
        if not audio.exists():
            _tts(cliente, frase, audio)
        total += 1
        print(f"[{i}] dicho: {frase!r}   (marca: {marca})")
        for modelo in MODELOS:
            try:
                with open(audio, "rb") as fh:
                    t = cliente.audio.transcriptions.create(
                        model=modelo, file=fh, language="es", prompt=prompt,
                    )
                texto = (t.text or "").strip()
            except Exception as exc:                             # noqa: BLE001
                print(f"      {modelo:34s} ERROR {type(exc).__name__}: {str(exc)[:70]}")
                continue
            ok = marca.lower().replace(" ", "") in texto.lower().replace(" ", "")
            aciertos[modelo] += ok
            print(f"      {modelo:34s} {'OK ' if ok else 'NO '} {texto[:64]}")
        print()

    print("=" * 72)
    print(f"MARCA BIEN TRANSCRITA (de {total} frases):")
    for modelo in MODELOS:
        print(f"  {modelo:34s} {aciertos[modelo]}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
