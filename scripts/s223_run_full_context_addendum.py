#!/usr/bin/env python3
"""Audit a draft against all served context and append only missing details."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.s219_run_omission_pilot as prior  # noqa: E402
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import normalized_text_sha  # noqa: E402

PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
BASELINES = ROOT / "evals/s219_baseline_answer_receipts_v1.json"
PREREG = ROOT / "evals/s223_full_context_addendum_prereg_v1.yaml"
RECEIPTS = ROOT / "evals/s223_full_context_addendum_receipts_v1.json"
GENERATION = ROOT / "evals/s223_full_context_addendum_generation_v1.json"

SYSTEM = """Eres un auditor técnico de completitud, no un redactor de respuesta completa.
Compara cada parte explícita de la pregunta y el borrador con TODOS los fragmentos
servidos. Devuelve solo precisiones materialmente necesarias que falten: valores,
relaciones, condiciones, excepciones, prerrequisitos, límites, consecuencias o
pasos de verificación. No repitas ni reescribas el borrador, no añadas temas que
la pregunta no solicita, no contradigas contenido correcto, no uses conocimiento
externo y cita cada precisión con [F#]. Si no falta nada, devuelve addendum vacío.
Devuelve únicamente el JSON requerido."""
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["addendum"],
    "properties": {"addendum": {"type": "string"}},
}


def verify() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S223 preregistration is not frozen")
    for label, spec in prereg["frozen_generation_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S223 frozen input drift: {label}")
    packet = prior._sealed(PACKET)
    receipts = prior._sealed(BASELINES)
    if packet.get("status") != "SEALED_NO_SCORE_FACTS" or receipts.get("status") != "COMPLETE":
        raise ValueError("S223 inherited baseline boundary drift")
    baselines = {
        item["item_id"]: item["baseline_answer"]
        for item in packet["items"]
        if item["baseline_answer"] is not None
    }
    baselines.update({row["item_id"]: row["answer"] for row in receipts["receipts"]})
    if len(baselines) != 9:
        raise ValueError("S223 baseline matrix incomplete")
    return prereg, packet, baselines


def execute(prereg: dict[str, Any], packet: dict[str, Any], baselines: dict[str, str], env_file: Path) -> int:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if RECEIPTS.exists() or GENERATION.exists():
        raise RuntimeError("S223 already attempted")
    key = (dotenv_values(env_file).get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S223 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key, max_retries=0)
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    by_item = {item["item_id"]: item for item in packet["items"]}

    def call(item_id: str) -> tuple[str, Any]:
        item = by_item[item_id]
        payload = json.dumps(
            {
                "question": item["question"],
                "draft_answer": baselines[item_id],
                "served_fragments": [
                    {"fragment_number": index, "content": chunk["content"]}
                    for index, chunk in enumerate(item["context"], 1)
                ],
            },
            ensure_ascii=False,
        )
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["max_output_tokens"],
            temperature=0,
            system=SYSTEM,
            messages=[{"role": "user", "content": payload}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        return item_id, response

    rows = []
    receipts = []
    actual = 0.0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(call, item_id) for item_id in by_item]
        for future in as_completed(futures):
            item_id, response = future.result()
            raw = prior._text(response)
            addendum = str(json.loads(raw).get("addendum") or "").strip()
            invalid = invalid_citations(addendum, len(by_item[item_id]["context"]))
            if invalid:
                raise ValueError(f"S223 invalid citations {item_id}: {invalid}")
            baseline = baselines[item_id]
            candidate = baseline + (("\n\n### Precisiones adicionales\n\n" + addendum) if addendum else "")
            if not candidate.startswith(baseline):
                raise ValueError("S223 monotonic prefix invariant failed")
            usage = prior._usage(response)
            cost = prior._cost(usage, prices)
            actual += cost
            receipts.append({
                "item_id": item_id, "response_id": response.id, "usage": usage,
                "cost_usd": round(cost, 8), "stop_reason": response.stop_reason,
                "addendum": addendum, "addendum_sha256": hashlib.sha256(addendum.encode()).hexdigest(),
            })
            rows.append({
                "item_id": item_id, "role": by_item[item_id]["role"],
                "fragment_count": len(by_item[item_id]["context"]),
                "baseline_answer": baseline, "candidate_answer": candidate,
                "selected_unit_ids": [], "candidate_source": "full_context_monotonic_addendum",
            })
            prior._checkpoint(RECEIPTS, "s223_full_context_addendum_receipts_v1", {"status": "IN_PROGRESS", "receipts": receipts})
    prior._checkpoint(RECEIPTS, "s223_full_context_addendum_receipts_v1", {"status": "COMPLETE", "receipts": receipts})
    stops = sum(row["stop_reason"] == "max_tokens" for row in receipts)
    ordered = sorted(rows, key=lambda row: list(by_item).index(row["item_id"]))
    prior._checkpoint(GENERATION, "s223_full_context_addendum_generation_v1", {
        "status": "COMPLETE_SCORE_NOT_OPENED", "created_at": datetime.now(timezone.utc).isoformat(),
        "items": ordered,
        "metrics": {"auditor_calls": len(receipts), "invalid_selector_outputs": 0, "token_limit_stops": stops, "actual_cost_usd": round(actual, 8)},
        "monotonic_prefix_invariant": True, "score_packet_opened": False,
        "provider_retries": 0, "target_calls": 0, "official_fact_credit": 0,
    })
    print(json.dumps({"status": "COMPLETE_SCORE_NOT_OPENED", "calls": len(receipts), "cost_usd": round(actual, 8)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=prior.DEFAULT_ENV)
    args = parser.parse_args()
    prereg, packet, baselines = verify()
    if not args.execute:
        print(json.dumps({"status": "PREFLIGHT_PASS", "items": 9, "auditor_calls": 9, "target_calls": 0, "score_packet_opened": False}, indent=2))
        return 0
    return execute(prereg, packet, baselines, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
