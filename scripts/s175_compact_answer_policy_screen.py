#!/usr/bin/env python3
"""Run the sealed S175 compact answer-policy development screen."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.omission_correction import invalid_citations, point_covered


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
PREREG = ROOT / "evals/s175_compact_answer_policy_prereg_v1.yaml"
PERMIT = ROOT / "evals/s175_compact_answer_policy_execution_permit_v1.yaml"
RECEIPTS = ROOT / "evals/s175_compact_answer_policy_receipts_v1.json"
RESULT = ROOT / "evals/s175_compact_answer_policy_screen_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)

CANDIDATE_SYSTEM = """Eres un asistente técnico para personal de protección contra incendios en campo.

CONTRATO DE RESPUESTA PARA UNA CONSULTA CONCRETA:
- Responde siempre en español y empieza por la respuesta directa a la pregunta.
- Los fragmentos proporcionados son la única fuente de verdad. No uses conocimiento previo ni completes relaciones por inferencia.
- Incluye todos los detalles del fragmento que cambien materialmente cómo ejecutar, interpretar o aplicar la respuesta: condiciones previas, alcance, polaridad, correspondencias, unidades, límites y advertencias. Conserva exactamente esas relaciones.
- Excluye información adyacente que no ayude a responder la pregunta.
- Cada oración factual o viñeta debe terminar inmediatamente con su cita [F1], [F2], etc. No cites un fragmento que no sostenga la afirmación.
- Si la evidencia no basta o una relación es ambigua, indícalo explícitamente; no la resuelvas.
- No afirmes compatibilidad, incompatibilidad ni ausencia de una función por falta de mención.
- No uses tablas Markdown ni añadas sugerencias de otras preguntas.
- Termina con «Fuente:» y el nombre del manual indicado en los encabezados de los fragmentos usados.

FORMATO:
Usa una respuesta corta y escaneable. Emplea pasos numerados para procedimientos y viñetas para parámetros sólo cuando aporten claridad. Antes de responder, comprueba en silencio que no has omitido ninguna condición material ni añadido nada que no esté en la fuente."""


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_candidate_prompt(item: dict[str, Any]) -> str:
    return f"""Pregunta del técnico: {item['question']}

[F1 | Producto: {item['product_model']} | Sección: {item['section_title']} | Manual: {item['source_file']} | Página: {item['page_number']}]
{item['excerpt']}

Responde aplicando exclusivamente el contrato y el fragmento anterior."""


def response_text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    )


def call_cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def validate_authorization() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S175 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S175 execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S175 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S175 permitted artifact drift: {spec['path']}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if RECEIPTS.exists() or RESULT.exists():
        raise RuntimeError("S175 checkpoint exists; retries are forbidden")
    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S175 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    baseline_payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    items = cohort["items"]
    if len(items) != 14 or any(
        key in item for item in items for key in ("answer_points", "exact_quote")
    ):
        raise RuntimeError("S175 generation cohort contains gold or has drifted")
    baselines = {row["item_id"]: row for row in baseline_payload["receipts"]}
    if set(baselines) != {row["item_id"] for row in items}:
        raise RuntimeError("S175 baseline population mismatch")

    model = prereg["model"]["id"]
    max_output = prereg["model"]["max_output_tokens"]
    prices = prereg["pricing_usd_per_million_tokens"]
    ceiling = prereg["budget"]["internal_ceiling_usd"]
    jobs = []
    total_counted_input = 0
    for item in items:
        prompt = build_candidate_prompt(item)
        counted = client.messages.count_tokens(
            model=model,
            system=CANDIDATE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ).input_tokens
        total_counted_input += counted
        jobs.append((item, prompt, counted))
    worst = (
        total_counted_input * prices["input"]
        + len(jobs) * max_output * prices["output"]
    ) / 1_000_000
    if worst >= ceiling:
        raise RuntimeError("S175 preflight exceeds internal ceiling")

    receipts = []
    actual = 0.0
    for item, prompt, counted in jobs:
        response = client.messages.create(
            model=model,
            max_tokens=max_output,
            temperature=0,
            system=CANDIDATE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response_text(response)
        usage = response.usage.model_dump(mode="json")
        cost = call_cost(usage, prices)
        actual += cost
        receipt = {
            "item_id": item["item_id"],
            "response_id": response.id,
            "counted_input_tokens": counted,
            "usage": usage,
            "cost_usd": round(cost, 8),
            "stop_reason": response.stop_reason,
            "answer": answer,
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        }
        receipts.append(receipt)
        write_json(
            RECEIPTS,
            {
                "instrument": "s175_compact_answer_policy_receipts_v1",
                "status": "IN_PROGRESS",
                "receipts": receipts,
            },
        )
    write_json(
        RECEIPTS,
        {
            "instrument": "s175_compact_answer_policy_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "system_sha256": hashlib.sha256(CANDIDATE_SYSTEM.encode("utf-8")).hexdigest(),
            "receipts": receipts,
        },
    )

    # Gold is deliberately unavailable until every candidate response is sealed.
    gold_payload = json.loads(GOLD.read_text(encoding="utf-8"))
    gold = {row["item_id"]: row for row in gold_payload["items"] if row["eligible"]}
    candidates = {row["item_id"]: row for row in receipts}
    rows = []
    baseline_points = candidate_points = 0
    baseline_complete = candidate_complete = 0
    regressions = invalid_candidate_citations = token_stops = 0
    for item in items:
        item_id = item["item_id"]
        points = gold[item_id]["answer_points"]
        baseline_answer = baselines[item_id]["answer"]
        candidate_answer = candidates[item_id]["answer"]
        base_hits = [point_covered(baseline_answer, point) for point in points]
        candidate_hits = [point_covered(candidate_answer, point) for point in points]
        row_regressions = sum(
            before and not after for before, after in zip(base_hits, candidate_hits)
        )
        invalid = invalid_citations(candidate_answer, 1)
        baseline_points += sum(base_hits)
        candidate_points += sum(candidate_hits)
        baseline_complete += int(all(base_hits))
        candidate_complete += int(all(candidate_hits))
        regressions += row_regressions
        invalid_candidate_citations += len(invalid)
        token_stops += int(candidates[item_id]["stop_reason"] == "max_tokens")
        rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "answer_points": len(points),
                "baseline_points_covered": sum(base_hits),
                "candidate_points_covered": sum(candidate_hits),
                "baseline_complete": all(base_hits),
                "candidate_complete": all(candidate_hits),
                "regressed_points": row_regressions,
                "invalid_candidate_citations": invalid,
            }
        )
    baseline_input = sum(row["counted_input_tokens"] for row in baselines.values())
    input_reduction = 1 - total_counted_input / baseline_input
    point_gain = candidate_points - baseline_points
    complete_gain = candidate_complete - baseline_complete
    checks = {
        "all_14_items_scored": len(rows) == 14,
        "frozen_baseline_26_points": baseline_points == 26,
        "frozen_baseline_6_complete": baseline_complete == 6,
        "point_gain_gte_4": point_gain >= 4,
        "complete_question_gain_gte_2": complete_gain >= 2,
        "regressed_points_zero": regressions == 0,
        "invalid_candidate_citations_zero": invalid_candidate_citations == 0,
        "token_limit_stops_zero": token_stops == 0,
        "counted_input_reduction_gte_35_percent": input_reduction >= 0.35,
        "actual_cost_below_ceiling": actual < ceiling,
    }
    passed = all(checks.values())
    body = {
        "instrument": "s175_compact_answer_policy_screen_v1",
        "status": "GO_TO_BLINDED_ADVERSARIAL_REVIEW" if passed else "NO_GO",
        "population": {
            "items": len(items),
            "manufacturers": len({row["manufacturer"] for row in items}),
            "table": sum(row["stratum"] == "table" for row in items),
            "prose": sum(row["stratum"] == "prose" for row in items),
            "answer_points": sum(len(row["answer_points"]) for row in gold.values()),
            "target_question_overlap": 0,
            "gold_loaded_after_candidate_checkpoint": True,
        },
        "metrics": {
            "baseline_points_covered": baseline_points,
            "candidate_points_covered": candidate_points,
            "point_gain": point_gain,
            "baseline_questions_complete": baseline_complete,
            "candidate_questions_complete": candidate_complete,
            "complete_question_gain": complete_gain,
            "regressed_points": regressions,
            "invalid_candidate_citations": invalid_candidate_citations,
            "token_limit_stops": token_stops,
            "baseline_counted_input_tokens": baseline_input,
            "candidate_counted_input_tokens": total_counted_input,
            "counted_input_reduction": input_reduction,
        },
        "checks": checks,
        "rows": rows,
        "cost": {
            "worst_case_preflight_usd": round(worst, 8),
            "actual_usd": round(actual, 8),
            "paid_calls": len(receipts),
        },
        "decision": {
            "blinded_adversarial_review": passed,
            "target_probe": False,
            "runtime_or_production": False,
            "facts_moved_to_ok": 0,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    write_json(RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"candidate_system_sha256": hashlib.sha256(CANDIDATE_SYSTEM.encode()).hexdigest()}))
        return 0
    prereg = validate_authorization()
    print(json.dumps(execute(prereg, args.env_file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
