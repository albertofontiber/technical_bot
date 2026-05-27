#!/usr/bin/env python3
"""Auditoría adversarial del pre-registro §9 de PLAN_RAG_2026 con GPT-5.5.

Aplica el principio cross-model judge al propio pre-registro: §9 fue redactado
por Opus 4.7; aquí GPT-5.5 (full, no Instant) actúa como auditor adversarial
independiente. Output: evals/preregistration_review.md.

Uso:
    python scripts/external_review_preregistration.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gpt-5.5"
PLAN_PATH = Path("docs/PLAN_RAG_2026.md")
# Output path resolves to evals/preregistration_review_<model>.md tras la
# llamada, para no pisar reviews previas si se re-corre con otro modelo.
OUTPUT_DIR = Path("evals")

SYSTEM = """Eres un auditor crítico de pre-registros de experimentos A/B en
ML/IR (information retrieval). Tu tarea NO es validar el pre-registro: es
encontrar problemas. Aplica:

1. Best practices de A/B testing (Kohavi/Tang/Xu et al., FDA-style preregistration).
2. Estadística aplicada a evaluación de sistemas RAG/retrieval.
3. Anti-patrones: p-hacking, HARKing, garden of forking paths, selección post-hoc,
   under-powered studies, MDE no justificado.

Sé concreto. Cita la sub-sección exacta del pre-registro que critiques. Si una
decisión está bien tomada, dilo en 1 línea — no expandas elogios. Prioriza
hallazgos accionables sobre comentarios genéricos."""

USER = """Audita este pre-registro. Identifica:

(a) **Sesgos metodológicos** y supuestos no declarados.
(b) **Gaps de pre-registro** — ¿qué reglas faltan que deberían fijarse antes del run?
(c) **Reglas mal calibradas** — umbrales/MDE/test que no se sostienen.
(d) **Riesgos de p-hacking** o selección post-hoc.
(e) **BP omitidas** del estado del arte en A/B testing de sistemas RAG.

Para cada hallazgo:
1. Cita la sub-sección (9.1, 9.2, ...).
2. Explica el problema en 1-2 frases.
3. Sugiere corrección concreta.

Termina con un veredicto:
[APROBADO | APROBADO_CON_AJUSTES_MENORES | REVISIÓN_MAYOR_REQUERIDA].

Contexto del proyecto (para que tengas marco, no para defender el pre-registro):
RAG sobre manuales PCI (paneles incendio). Eval N=17 preguntas hp* sintéticas
validadas humanamente. Comparación A/B: chunks viejo (OpenAI 1536) vs chunks_v2
(Voyage 1024 + Haiku contextual + dedup). Decisión binaria: SWAP o no SWAP de
la tabla en producción.

---

{section}
"""


def extract_section_9(text: str) -> str:
    """Extrae §9 (Pre-registro) del plan, hasta el próximo header o Changelog."""
    m = re.search(
        r"^## 9\. Pre-registro.*?(?=^## (?:\d+\.|Changelog))",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        raise RuntimeError("No se encontró §9 en el plan")
    return m.group(0).strip()


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY no está en el entorno", file=sys.stderr)
        return 1

    plan_text = PLAN_PATH.read_text(encoding="utf-8")
    section = extract_section_9(plan_text)
    print(f"§9 extraído: {len(section)} chars, {section.count(chr(10))} líneas")

    client = OpenAI(api_key=api_key)

    candidates = [MODEL, "gpt-5.5-2026-04-23", "gpt-5.4", "gpt-5.3-chat-latest", "gpt-5.2", "gpt-5"]
    last_err: Exception | None = None
    resp = None
    used_model = None
    for candidate in candidates:
        try:
            print(f"  intentando modelo: {candidate}")
            resp = client.chat.completions.create(
                model=candidate,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": USER.format(section=section)},
                ],
            )
            used_model = candidate
            break
        except Exception as e:
            last_err = e
            print(f"    fallo: {e}")
            continue

    if resp is None:
        print(f"ERROR: ningún modelo respondió. Último error: {last_err}",
              file=sys.stderr)
        return 2

    review = resp.choices[0].message.content
    usage = resp.usage

    output_path = OUTPUT_DIR / f"preregistration_review_{used_model}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"# Auditoría adversarial del pre-registro §9\n\n"
        f"**Modelo solicitado**: `{used_model}`\n"
        f"**Modelo respondió**: `{resp.model}`\n"
        f"**Tokens**: {usage.prompt_tokens} prompt / "
        f"{usage.completion_tokens} completion\n\n"
        f"---\n\n{review}\n",
        encoding="utf-8",
    )
    print(f"\nReview escrita en {output_path}")
    print(f"Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
