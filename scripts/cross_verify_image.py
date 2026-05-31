#!/usr/bin/env python3
"""Verificación cross-model de una página renderizada (GPT-5.5 lee la imagen).

Parte del pipeline de verificación del ruler (TECH_DEBT #33): un gold autorado
por un modelo (Claude/Opus) se confirma con OTRO modelo (GPT-5.5) leyendo la
MISMA fuente primaria renderizada. Romper el punto ciego compartido es lo que
distingue un ruler fiable del autor-único que falló en s30.

No le damos a GPT nuestra respuesta: le pedimos que transcriba/responda en frío
para poder comparar de forma independiente.

Uso:
  python scripts/cross_verify_image.py <ruta_png> "<pregunta de transcripción>"
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
MODEL = os.getenv("CROSS_VERIFY_MODEL", "gpt-5.5")


def main() -> int:
    try:  # consola Windows = cp1252; GPT transcribe '−'/'°' → evita UnicodeEncodeError
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 3:
        sys.exit("Uso: cross_verify_image.py <png> <pregunta>")
    img_path = Path(sys.argv[1])
    if not img_path.is_absolute():
        img_path = ROOT / img_path
    question = sys.argv[2]

    b64 = base64.b64encode(img_path.read_bytes()).decode()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    )
    print(f"--- {MODEL} sobre {img_path.name} ---")
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
