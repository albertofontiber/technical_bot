#!/usr/bin/env python3
"""S270 Etapa 2 — probe v2 (SEGUNDO probe a los mismos 4 targets; DEC-126).

Wrapper del runner v1 (patrón s241): mismo diseño pareado K=3, mismo instrumento y
MISMA composición del gate; cambia el MECANISMO (must_preserve v2, validado en la
Etapa 1 v5 seed-273 GO) y el brazo ON corre con DETECCIÓN HÍBRIDA (Haiku, grounding
verbatim, no-retry; fallback det-solo declarado por fragmento si Haiku falla).
Prereg: evals/s270_etapa2_probe_v2_prereg_v1.yaml (cuenta de probes VISIBLE).

Preflight por defecto (0 llamadas); ``--execute --env-file`` para pagar.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s270_etapa2_probe as base  # noqa: E402

base.PREREG = ROOT / "evals/s270_etapa2_probe_v2_prereg_v1.yaml"
base.REPLICAS = ROOT / "evals/s270_etapa2_probe_v2_replicas_v1.jsonl"
base.OUT = ROOT / "evals/s270_etapa2_probe_v2_result_v1.json"
base.RESULT_SCHEMA = "s270_etapa2_probe_v2_result_v1"
base.RUNNER_KEY = "scripts/s270_etapa2_probe_v2.py"
base.RUNNER_FILE = Path(__file__)

HYBRID_PRICE_IN = 1.0   # USD/MTok Haiku 4.5 (mismos precios que el harness)
HYBRID_PRICE_OUT = 5.0


def _hybrid_client():
    import anthropic

    return anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    )


def run_replicate_v2(
    qid: str, question: str, chunks: list[dict], replicate: int
) -> dict[str, Any]:
    """run_replicate del v1 + brazo ON con detección HÍBRIDA inyectada
    (detect_fn=detect_atoms_hybrid con cliente no-retry; coste Haiku contabilizado
    en la réplica; fallback det-solo POR FRAGMENTO declarado si Haiku falla)."""
    from src.rag import generator, must_preserve

    if os.environ.get("MUST_PRESERVE_CONTRACT") != "off":
        raise RuntimeError("S270v2 la generación debe correr con el contrato OFF")
    result = generator.generate_answer(question, chunks)
    if result.get("stop_reason") != "end_turn":
        raise RuntimeError(
            f"S270v2 {qid}:r{replicate} stop_reason={result.get('stop_reason')!r}"
        )
    off_answer = str(result["answer"])
    client = _hybrid_client()
    usage: dict[str, Any] = {}
    hybrid_errors: list[str] = []

    def detector(fragment_text: str):
        try:
            return must_preserve.detect_atoms_hybrid(
                fragment_text, client=client, usage=usage
            )
        except Exception as exc:  # no-retry: det-solo para este fragmento
            hybrid_errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")
            return must_preserve.detect_atoms(fragment_text)

    os.environ["MUST_PRESERVE_CONTRACT"] = "on"
    try:
        on_answer, trace = must_preserve.apply_must_preserve_contract(
            question, chunks, off_answer, detect_fn=detector
        )
    finally:
        os.environ["MUST_PRESERVE_CONTRACT"] = "off"
    input_tokens = int(result.get("input_tokens") or 0)
    output_tokens = int(result.get("output_tokens") or 0)
    hybrid_cost = (
        usage.get("input_tokens", 0) * HYBRID_PRICE_IN
        + usage.get("output_tokens", 0) * HYBRID_PRICE_OUT
    ) / 1_000_000
    return {
        "qid": qid,
        "replicate": replicate,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": base.EXPECTED_MODEL,
        "stop_reason": result.get("stop_reason"),
        "off_answer": off_answer,
        "on_answer": on_answer,
        "must_preserve_trace": trace,
        "attestation": base.attestation_report(question, chunks, off_answer),
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "hybrid_usage": dict(usage),
        "hybrid_errors": hybrid_errors,
        "cost_usd": round(
            base.cost_usd(input_tokens, output_tokens) + hybrid_cost, 8
        ),
    }


base.run_replicate = run_replicate_v2

_base_preflight = base.preflight


def preflight_v2(prereg, rows, items, protected):
    report = _base_preflight(prereg, rows, items, protected)
    report["probe_number"] = 2
    # cota superior híbrida: detección en TODOS los fragmentos servidos × 3 réplicas
    calls = sum(len(rows[q]["context"]) for q in base.QIDS) * len(base.REPLICATES)
    in_tok = calls * 2200
    out_tok = calls * 1500
    report["hybrid_upper_bound"] = {
        "haiku_calls_max": calls,
        "est_cost_usd_max": round(
            (in_tok * HYBRID_PRICE_IN + out_tok * HYBRID_PRICE_OUT) / 1e6, 4
        ),
    }
    total = (
        report["estimated_cost"]["total_usd"]
        + report["hybrid_upper_bound"]["est_cost_usd_max"]
    )
    if total > base.COST_CEILING_USD:
        raise RuntimeError(f"S270v2 estimación total {total:.4f} > techo")
    report["estimated_cost_total_with_hybrid_usd"] = round(total, 4)
    return report


base.preflight = preflight_v2


if __name__ == "__main__":
    raise SystemExit(base.main())
