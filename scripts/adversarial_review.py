#!/usr/bin/env python3
"""Revisor adversarial CROSS-MODEL (GPT-5.5) — refinamiento A del agente revisor.

Da independencia CONCEPTUAL (modelo distinto del autor, que es Claude), rompiendo el
echo-chamber del mismo-modelo (lección validator s13). Complementa al sub-agente Claude
(que lee el repo y ancla en código) en decisiones de ALTO impacto. Ver docs/ADVERSARIAL_REVIEWER.md.

Uso:
  python scripts/adversarial_review.py <propuesta.md> [<contexto1> <contexto2> ...]
(el 1er fichero es la propuesta a atacar; el resto, contexto que GPT no puede leer del repo.)
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
MODEL = os.getenv("ADVERSARIAL_MODEL", "gpt-5.5")

SYS = (
    "Eres un REVISOR ADVERSARIAL. Ataca la propuesta y encuentra donde (a) viola el "
    "contrato de ingenieria, (b) repite un fallo conocido, (c) se sobre-ingenieriza. "
    "CALIBRACION: escudriña duro y reporta SOLO lo que GENUINAMENTE encuentres, cada "
    "hallazgo con NIVEL DE CONFIANZA (alto/medio/especulativo) y por que. Concluir que "
    "'es solido' es valioso cuando lo es; NO fabriques preocupaciones para parecer util. "
    "NO te ancles a la justificacion del autor. "
    "CONTRATO: best-practice + estructural (raiz, no parche) + escalable (30+ fabricantes, "
    "ES/EN) + precision > velocidad + sin quick-fixes + sin sobre-ingenieria + declarar "
    "TODOS los gaps materiales. "
    "SALIDA: hallazgos ordenados por severidad, cada uno con confianza + razon; o 'solido' "
    "si de verdad lo es. Menos de 450 palabras."
)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    files = sys.argv[1:]
    if not files:
        sys.exit("uso: adversarial_review.py <propuesta> [contexto...]")
    parts = []
    for i, f in enumerate(files):
        p = Path(f)
        rol = "PROPUESTA A ATACAR" if i == 0 else "CONTEXTO"
        parts.append(f"===== [{rol}] {p.name} =====\n{p.read_text(encoding='utf-8')}")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYS},
                  {"role": "user", "content": "\n\n".join(parts)}],
    )
    print(f"--- {MODEL} (revisor adversarial cross-model) ---")
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
