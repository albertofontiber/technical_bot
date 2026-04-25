"""Verify Anthropic prompt caching is working in generator and judge.

Runs the same query twice and checks that:
- First call: cache_creation_input_tokens > 0 (writes cache)
- Second call: cache_read_input_tokens > 0 (reads cache, ~10% price)

Output is bit-identical between calls (Anthropic guarantee with temperature=0).
"""
from __future__ import annotations
import sys
import io
import os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import anthropic
from src.rag.generator import SYSTEM_PROMPT
from src.config import LLM_MODEL, ANTHROPIC_API_KEY
from scripts.run_eval import JUDGE_SYSTEM_PROMPT, JUDGE_MODEL


def test_caching(label: str, model: str, system_prompt: str, user_message: str) -> None:
    print(f"\n=== {label} ===")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"  System prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")
    for run in (1, 2):
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            temperature=0,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        u = resp.usage
        cache_w = getattr(u, "cache_creation_input_tokens", 0) or 0
        cache_r = getattr(u, "cache_read_input_tokens", 0) or 0
        regular = u.input_tokens
        print(
            f"  Run {run}: input={regular}  cache_write={cache_w}  cache_read={cache_r}  "
            f"output={u.output_tokens}"
        )


if __name__ == "__main__":
    # Generator
    test_caching(
        "Generator (SYSTEM_PROMPT)",
        LLM_MODEL,
        SYSTEM_PROMPT,
        "Pregunta del técnico: ¿cómo se conectan las baterías de la CAD-250?\n\nFragmentos:\n[Fragmento 1] (sample)",
    )

    # Judge
    test_caching(
        "Judge (JUDGE_SYSTEM_PROMPT)",
        JUDGE_MODEL,
        JUDGE_SYSTEM_PROMPT,
        "PREGUNTA DEL TÉCNICO:\nTest query.\n\nCONDUCTA ESPERADA: answer\n\nSECCIÓN F:\n(none)\n\nSECCIÓN V:\n(none)\n\nRESPUESTA DEL BOT:\nTest answer.",
    )
