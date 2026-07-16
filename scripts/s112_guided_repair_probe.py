#!/usr/bin/env python3
"""One-call, checkpointed cheap-model repair probe for incomplete guided answers.

The repairer sees the existing draft and the already source-bound obligations,
not the full retrieval context. This keeps the executor call small and prevents
it from changing retrieval or rerank attribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s112_guided_synthesis_probe_v1.json"
FREEZE = ROOT / "evals/s112_synthesis_context_freeze_v1.json"
OUT = ROOT / "evals/s112_guided_repair_probe_v1.json"
CHECKPOINT = ROOT / "evals/s112_guided_repair_probe_v1.partial.jsonl"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def _stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_repair_prompt(question: str, answer: str, plan: list[dict]) -> str:
    obligations = "\n".join(
        f"- OBL-{index} [F{row['fragment_number']}]: {row['statement']}"
        for index, row in enumerate(plan, 1)
    )
    return f"""Pregunta original:
{question}

Respuesta ya generada:
{answer}

Obligaciones factuales source-bound:
{obligations}

Devuelve la respuesta completa revisada. Integra TODAS las obligaciones en el
paso o párrafo técnico pertinente; no las añadas como apéndice. Expresa cada
relación completa de forma explícita, en una frase o en frases consecutivas
inequívocas, y conserva la cita [F#] correspondiente. Mantén el resto de la
respuesta y sus citas. No añadas valores, procedimientos ni relaciones que no
figuren en la respuesta original o en estas obligaciones. Si dos obligaciones
se refieren al mismo punto o salida, explica juntas su relación operacional sin
convertir correlación en equivalencia. Devuelve solo la respuesta revisada."""


def _text(response) -> str:
    return "".join(
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()


def _load_checkpoint() -> dict | None:
    if not CHECKPOINT.exists():
        return None
    rows = [json.loads(line) for line in CHECKPOINT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) > 1:
        raise RuntimeError("repair probe allows exactly one checkpoint")
    return rows[0] if rows else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.s112_guided_synthesis_probe import _fact_results
    from src.rag.answer_planner import AnswerObligation, validate_answer_plan

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    questions = {item["qid"]: item["question"] for item in frozen["rows"]}
    incomplete = [
        row
        for row in source["rows"]
        if row.get("executed") and not row.get("all_obligations_covered")
    ]
    if len(incomplete) != 1:
        raise RuntimeError(f"expected exactly one incomplete guided answer, got {len(incomplete)}")
    row = incomplete[0]
    plan_rows = row["answer_planner"]["plan"]
    prompt = build_repair_prompt(questions[row["qid"]], row["answer"], plan_rows)
    contract = {
        "source_answer_sha256": hashlib.sha256(row["answer"].encode("utf-8")).hexdigest(),
        "prompt": prompt,
        "model": args.model,
        "max_tokens": 3000,
    }
    prompt_sha256 = _stable_sha(contract)
    checkpoint = _load_checkpoint()
    if checkpoint and checkpoint["prompt_sha256"] != prompt_sha256:
        raise RuntimeError("stale repair checkpoint; refusing repeat spend")

    if args.execute and checkpoint is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=args.model,
            max_tokens=3000,
            temperature=0,
            system=(
                "Eres un editor técnico de precisión. Tu única tarea es reparar "
                "cobertura factual de una respuesta ya fundamentada. No inventes."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        checkpoint = {
            "qid": row["qid"],
            "prompt_sha256": prompt_sha256,
            "model": args.model,
            "stop_reason": response.stop_reason,
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
            "answer": _text(response),
        }
        with CHECKPOINT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

    validation = None
    facts = None
    if checkpoint:
        plan = [AnswerObligation(**item) for item in plan_rows]
        validation = validate_answer_plan(checkpoint["answer"], plan)
        facts = _fact_results(row["qid"], checkpoint["answer"])
    payload = {
        "instrument": "s112_guided_repair_probe_v1",
        "production_writes": 0,
        "railway_changed": False,
        "source_qid": row["qid"],
        "source_answer_sha256": contract["source_answer_sha256"],
        "prompt_sha256": prompt_sha256,
        "executor_model": args.model,
        "full_retrieval_context_sent": False,
        "executed": checkpoint is not None,
        "paid_generator_calls": 1 if checkpoint else 0,
        "paid_reranker_calls": 0,
        "llm_judge_calls": 0,
        "input_tokens": checkpoint.get("input_tokens") if checkpoint else 0,
        "output_tokens": checkpoint.get("output_tokens") if checkpoint else 0,
        "stop_reason": checkpoint.get("stop_reason") if checkpoint else None,
        "facts": facts,
        "all_facts_present": bool(facts and all(item["present"] for item in facts)),
        "validation": validation,
        "answer_sha256": (
            hashlib.sha256(checkpoint["answer"].encode("utf-8")).hexdigest()
            if checkpoint else None
        ),
        "answer": checkpoint.get("answer") if checkpoint else None,
        "manual_review_required": bool(checkpoint),
        "limitations": [
            "Known-cohort repair probe; not held-out evidence.",
            "Deterministic coverage is a screen, not the semantic release verdict.",
            "The repair call receives only the existing answer and source-bound obligations.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("executed", "executor_model", "input_tokens", "output_tokens", "all_facts_present")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
