#!/usr/bin/env python3
"""Standalone Phase 0 parity probe (fix GATE-PARIDAD-VACUO).

Drives one turn through BOTH routes and reports PRE-LLM byte parity:

  * DIRECT — ``execute_rag_turn(...)`` as the handler / gold harness call it;
  * ORCH   — the same turn through ``src.orchestrator.run_turn(TurnRequest, ...)``.

Both routes share ONE deterministic replay-adapters instance (frozen retrieval,
identity rerank, no-op shadow, empty coverage fetchers). The real
``generate_answer`` runs with a faked Anthropic client, so the ACTUAL provider
request envelope (``system`` + ``messages``) is captured with zero network — the
deepest reachable comparison point without changing any behavior.

This is a self-contained diagnostic; it does NOT touch the default flow of
``scripts/test_bot_vs_gold.py``. Exit code 0 = parity holds, 1 = mismatch.

Usage: python scripts/parity_probe_orchestrator.py
"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.rag.generator as gen  # noqa: E402
from src.orchestrator import (  # noqa: E402
    TurnRequest,
    execute_rag_turn,
    replay_adapters,
    run_turn,
)
from src.orchestrator.contracts import PlanKind  # noqa: E402


_QUERY = "¿Cuál es la tensión del lazo de la CAD-250?"
_RESOLVED_QUERY = f"{_QUERY} (contexto: CAD-250)"
_RETRIEVAL_TOP_K = 50
_RERANK_TOP_K = 5

_FIXTURE = [
    {
        "id": "chunk-1",
        "content": "La tensión nominal del lazo es 24 V CC.",
        "similarity": 0.93,
        "product_model": "CAD-250",
        "section_title": "Especificaciones eléctricas",
        "content_type": "specs",
        "source_file": "manual_cad250.pdf",
        "document_revision": "A",
    },
    {
        "id": "chunk-2",
        "content": "El consumo en reposo es de 120 mA.",
        "similarity": 0.88,
        "product_model": "CAD-250",
        "section_title": "Consumo",
        "content_type": "specs",
        "source_file": "manual_cad250.pdf",
    },
]


class _CaptureMessages:
    def __init__(self, envelopes):
        self._envelopes = envelopes

    def create(self, **kwargs):
        self._envelopes.append(copy.deepcopy(kwargs))
        return SimpleNamespace(
            content=[SimpleNamespace(text="La tensión del lazo es 24 V CC [F1].")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
        )


def _install_capture(envelopes):
    gen.anthropic.Anthropic = lambda api_key=None: SimpleNamespace(  # type: ignore[assignment]
        messages=_CaptureMessages(envelopes)
    )


def _probe(*, resolved: bool) -> dict:
    envelopes: list[dict] = []
    _install_capture(envelopes)
    adapters = replay_adapters(retrieved=_FIXTURE, generate=gen.generate_answer)

    direct = execute_rag_turn(
        query=_QUERY,
        query_for_retrieval=_RESOLVED_QUERY if resolved else _QUERY,
        target_models=["CAD-250"] if resolved else None,
        available_models=["CAD-250", "MAD-461"] if resolved else None,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        adapters=adapters,
    )
    request = TurnRequest(
        query=_QUERY,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        query_for_retrieval=_RESOLVED_QUERY if resolved else None,
        target_models=("CAD-250",) if resolved else None,
        available_models=("CAD-250", "MAD-461") if resolved else None,
    )
    result = run_turn(request, adapters)

    if len(envelopes) != 2:
        return {"ok": False, "error": f"expected 2 writer calls, got {len(envelopes)}"}
    direct_env, orch_env = envelopes
    checks = {
        "plan_is_single_hop": result.plan.kind is PlanKind.SINGLE_HOP,
        "context_chunks": list(result.retrieval.chunks) == list(direct["chunks"]),
        "system_prompt": orch_env["system"] == direct_env["system"],
        "user_message": (
            orch_env["messages"][0]["content"] == direct_env["messages"][0]["content"]
        ),
        "full_envelope": orch_env == direct_env,
    }
    return {"ok": all(checks.values()), "checks": checks}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("Phase 0 orchestrator parity probe (DIRECT vs ORCH, PRE-LLM bytes)\n")
    all_ok = True
    for label, resolved in (("standalone turn", False), ("resolved turn", True)):
        report = _probe(resolved=resolved)
        if not report["ok"] and "checks" not in report:
            print(f"[{label}] ERROR: {report['error']}")
            all_ok = False
            continue
        status = "PARIDAD" if report["ok"] else "MISMATCH"
        print(f"[{label}] {status}")
        for name, ok in report["checks"].items():
            print(f"    {'OK ' if ok else 'XX '} {name}")
        all_ok = all_ok and report["ok"]
        print()

    print("=" * 60)
    print("RESULTADO:", "PARIDAD byte-a-byte (context+prompt+plan)" if all_ok else "FALLO")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
