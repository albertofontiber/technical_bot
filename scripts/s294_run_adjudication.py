#!/usr/bin/env python3
"""s294_run_adjudication.py — corre la adjudicación CIEGA con el cross-model (F7).

Envía `evals/s294_adjudication_packet_v1.md` TAL CUAL (las instrucciones y la
taxonomía viven dentro del paquete) al mismo proveedor/modelo que el lado cross-model
del dúo, y persiste la respuesta cruda. No se envía la clave (`..._key_v1.json`), ni
el contexto del lever, ni cuál es la diana.

Uso: python scripts/s294_run_adjudication.py
Salida: evals/s294_adjudication_result_v1.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

MODEL = os.getenv("ADVERSARIAL_MODEL", "gpt-5.6-sol")
EFFORT = os.getenv("ADVERSARIAL_REASONING_EFFORT", "xhigh")
SUFFIX = os.getenv("S294_ROUND", "_r2")
PACKET = os.path.join("evals", f"s294_adjudication_packet{SUFFIX}.md")

SYSTEM = (
    "Eres un adjudicador técnico independiente del sector de protección contra "
    "incendios. Recibes un lote de oraciones extraídas de manuales y una taxonomía "
    "fijada de antemano. Juzga cada fila por sí misma, con el formato exacto que se "
    "te pide y sin prosa adicional. No conoces —ni debes suponer— qué fila motivó el "
    "diseño del sistema."
)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("falta OPENAI_API_KEY")
    packet = open(PACKET, encoding="utf-8").read()

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.responses.create(
        model=MODEL,
        instructions=SYSTEM,
        input=[{"role": "user", "content": packet}],
        reasoning={"effort": EFFORT},
        store=False,
    )
    text = getattr(resp, "output_text", "") or ""
    usage = getattr(resp, "usage", None)
    out = {
        "probe": f"s294_adjudication_result{SUFFIX}",
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "model": getattr(resp, "model", MODEL),
        "reasoning_effort": EFFORT,
        "response_id": getattr(resp, "id", None),
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "packet_path": PACKET,
        "raw": text,
    }
    path = os.path.join(os.getcwd(), "evals", f"s294_adjudication_result{SUFFIX}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}  ({out['model']}, {out['total_tokens']} tokens)")
    print(text[:1500])


if __name__ == "__main__":
    main()
