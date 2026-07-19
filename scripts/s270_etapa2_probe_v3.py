#!/usr/bin/env python3
"""S270 Etapa 2 — probe v3 (TERCER y ÚLTIMO probe de la sesión a los mismos targets).

Wrapper del runner v1 (patrón s241/probe-v2): mismo diseño pareado K=3, mismo
instrumento y MISMA composición del gate; mecanismo v3 (grounding fold-tolerante del
híbrido + disclosure de dos lados; validado en Etapa 1 v6 seed-274 GO). El brazo ON
registra los contadores de grounding híbrido por réplica (pasan/mueren por causa).
Prereg: evals/s270_etapa2_probe_v3_prereg_v1.yaml. Preflight por defecto;
``--execute --env-file`` para pagar.
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

# NO se importa el wrapper v2: su import rebinda los globals de base a las rutas v2
# (side-effect del patrón wrapper); v3 define sus propias constantes.
from scripts import s270_etapa2_probe as base  # noqa: E402

HYBRID_PRICE_IN = 1.0   # USD/MTok Haiku 4.5
HYBRID_PRICE_OUT = 5.0


def _hybrid_client():
    import anthropic

    return anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    )

base.PREREG = ROOT / "evals/s270_etapa2_probe_v3_prereg_v1.yaml"
base.REPLICAS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
base.OUT = ROOT / "evals/s270_etapa2_probe_v3_result_v1.json"
base.RESULT_SCHEMA = "s270_etapa2_probe_v3_result_v1"
base.RUNNER_KEY = "scripts/s270_etapa2_probe_v3.py"
base.RUNNER_FILE = Path(__file__)


def run_replicate_v3(
    qid: str, question: str, chunks: list[dict], replicate: int
) -> dict[str, Any]:
    from src.rag import generator, must_preserve

    if os.environ.get("MUST_PRESERVE_CONTRACT") != "off":
        raise RuntimeError("S270v3 la generación debe correr con el contrato OFF")
    result = generator.generate_answer(question, chunks)
    if result.get("stop_reason") != "end_turn":
        raise RuntimeError(
            f"S270v3 {qid}:r{replicate} stop_reason={result.get('stop_reason')!r}"
        )
    off_answer = str(result["answer"])
    client = _hybrid_client()
    usage: dict[str, Any] = {}
    grounding: dict[str, int] = {}
    hybrid_errors: list[str] = []

    def detector(fragment_text: str):
        try:
            return must_preserve.detect_atoms_hybrid(
                fragment_text, client=client, usage=usage, stats=grounding
            )
        except Exception as exc:
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
        "hybrid_grounding": dict(grounding),
        "hybrid_errors": hybrid_errors,
        "cost_usd": round(
            base.cost_usd(input_tokens, output_tokens) + hybrid_cost, 8
        ),
    }


base.run_replicate = run_replicate_v3

_base_preflight = base.preflight


def preflight_v3(prereg, rows, items, protected):
    report = _base_preflight(prereg, rows, items, protected)
    report["probe_number"] = 3
    calls = sum(len(rows[q]["context"]) for q in base.QIDS) * len(base.REPLICATES)
    est = (calls * 2200 * HYBRID_PRICE_IN + calls * 1500 * HYBRID_PRICE_OUT) / 1e6
    report["hybrid_upper_bound"] = {
        "haiku_calls_max": calls, "est_cost_usd_max": round(est, 4),
    }
    total = report["estimated_cost"]["total_usd"] + est
    if total > base.COST_CEILING_USD:
        raise RuntimeError(f"S270v3 estimación total {total:.4f} > techo")
    report["estimated_cost_total_with_hybrid_usd"] = round(total, 4)
    return report


base.preflight = preflight_v3


if __name__ == "__main__":
    raise SystemExit(base.main())
