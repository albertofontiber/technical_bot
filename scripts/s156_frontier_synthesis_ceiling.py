#!/usr/bin/env python3
"""Run the bounded Fable/Sol synthesis ceiling diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_PREREG = ROOT / "evals/s156_frontier_synthesis_ceiling_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s156_frontier_synthesis_ceiling_execution_permit_v1.yaml"
DEFAULT_RECEIPTS = ROOT / "evals/s156_frontier_synthesis_ceiling_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s156_frontier_synthesis_ceiling_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
QIDS = ("cat018", "hp002", "hp011", "hp017")
RUNTIME_ENV = {
    "CHUNKS_TABLE": "chunks_v2",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "ANSWER_OBLIGATION_PLANNER": "guided",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _configure_runtime() -> None:
    os.environ.update(RUNTIME_ENV)


def build_prompt(row: dict[str, Any]) -> tuple[str, str]:
    """Rebuild the current guided generator prompt from the frozen served rows."""
    _configure_runtime()
    from src.rag.answer_planner import build_answer_plan, render_answer_plan_guidance
    from src.rag.generator import _assemble_system
    from src.rag.post_rerank_coverage import coverage_context_content

    query = str(row["question"])
    context_parts = []
    for index, chunk in enumerate(row["context"], 1):
        source_file = str(chunk.get("source_file") or "")
        manual = source_file.rsplit(".pdf", 1)[0] if source_file else "desconocido"
        revision = chunk.get("document_revision")
        revision_date = chunk.get("document_revision_date")
        rev_parts = ([f"rev. {revision}"] if revision else []) + (
            [str(revision_date)] if revision_date else []
        )
        rev = ", ".join(rev_parts) if rev_parts else "sin revisión registrada"
        diagram = " [DIAGRAMA DISPONIBLE]" if (
            chunk.get("has_diagram") and chunk.get("diagram_url")
        ) else ""
        header = (
            f"[Fragmento {index} | Producto: {chunk.get('product_model', 'desconocido')} "
            f"| Sección: {chunk.get('section_title', '')} | Tipo: {chunk.get('content_type', '')} "
            f"| Relevancia: {float(chunk.get('similarity') or 0):.2f}{diagram} "
            f"| Manual: {manual} | Rev: {rev}]"
        )
        context_parts.append(f"{header}\n{coverage_context_content(chunk)}")
    context = "\n\n---\n\n".join(context_parts)
    plan = build_answer_plan(query, row["context"])
    guidance = render_answer_plan_guidance(plan)
    prompt = f"""Pregunta del técnico: {query}
{guidance}
Fragmentos relevantes de los manuales técnicos:

{context}

Responde la pregunta del técnico basándote exclusivamente en los fragmentos anteriores."""
    return _assemble_system(query), prompt


def _citations(answer: str) -> list[int]:
    return [int(value) for value in re.findall(r"\[F(\d+)\]", answer)]


def score_answer(qid: str, answer: str, frozen: dict[str, Any]) -> dict[str, Any]:
    from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, plan_for
    from src.rag.answer_planner import validate_answer_plan

    row = frozen[qid]
    obligations = [item for item in plan_for(row) if item.kind in TARGET_KINDS[qid]]
    validation = validate_answer_plan(answer, obligations)
    citations = _citations(answer)
    invalid = sorted({number for number in citations if not 1 <= number <= len(row["context"])})
    return {
        "relations": len(obligations),
        "covered": validation["covered"],
        "covered_kinds": [item["kind"] for item in validation["rows"] if item["covered"]],
        "missing_kinds": [item["kind"] for item in validation["rows"] if not item["covered"]],
        "citations": len(citations),
        "invalid_citations": invalid,
    }


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S156 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S156 execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S156 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S156 permitted artifact drift: {spec['path']}")
    return prereg


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    if DEFAULT_RECEIPTS.exists() or DEFAULT_RESULT.exists():
        raise RuntimeError("S156 output exists; retries are forbidden")
    secrets = dotenv_values(env_file)
    anthropic_key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not anthropic_key or not openai_key:
        raise RuntimeError("S156 provider API key missing")
    anthropic = Anthropic(api_key=anthropic_key)
    openai = OpenAI(api_key=openai_key)
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in payload["rows"]}
    jobs = [(qid, *build_prompt(frozen[qid])) for qid in QIDS]
    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]

    prepared: dict[str, list[dict[str, Any]]] = {"fable": [], "sol": []}
    for qid, system, prompt in jobs:
        fable_count = anthropic.messages.count_tokens(
            model=models["fable"]["id"], system=system,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"}, output_config={"effort": "xhigh"},
        ).input_tokens
        sol_count = openai.responses.input_tokens.count(
            model=models["sol"]["id"], reasoning={"effort": "xhigh"},
            instructions=system, input=prompt,
        ).input_tokens
        prepared["fable"].append({"qid": qid, "system": system, "prompt": prompt, "counted": fable_count})
        prepared["sol"].append({"qid": qid, "system": system, "prompt": prompt, "counted": sol_count})
    worst = sum(
        sum(job["counted"] for job in prepared[arm]) * prices[arm]["input"]
        + len(QIDS) * models[arm]["max_output_tokens"] * prices[arm]["output"]
        for arm in ("fable", "sol")
    ) / 1_000_000
    if worst >= prereg["budget"]["internal_ceiling_usd"]:
        raise RuntimeError("S156 preflight exceeds internal budget")

    receipts: list[dict[str, Any]] = []
    answers: dict[str, dict[str, dict[str, Any]]] = {"fable": {}, "sol": {}}
    actual = 0.0
    for arm in ("fable", "sol"):
        for job in prepared[arm]:
            try:
                if arm == "fable":
                    response = anthropic.messages.create(
                        model=models[arm]["id"], max_tokens=models[arm]["max_output_tokens"],
                        system=job["system"], messages=[{"role": "user", "content": job["prompt"]}],
                        thinking={"type": "adaptive"}, output_config={"effort": "xhigh"},
                    )
                    answer = "".join(
                        block.text for block in response.content if getattr(block, "type", "") == "text"
                    )
                    usage = response.usage.model_dump(mode="json")
                    stop = response.stop_reason
                    response_id = response.id
                else:
                    response = openai.responses.create(
                        model=models[arm]["id"], reasoning={"effort": "xhigh"},
                        instructions=job["system"], input=job["prompt"],
                        max_output_tokens=models[arm]["max_output_tokens"], store=False,
                    )
                    answer = response.output_text
                    usage = response.usage.model_dump(mode="json")
                    stop = response.status
                    response_id = response.id
                call_cost = _cost(usage, prices[arm])
                actual += call_cost
                receipt = {
                    "arm": arm, "qid": job["qid"], "status": "COMPLETE",
                    "response_id": response_id, "counted_input_tokens": job["counted"],
                    "stop": stop, "usage": usage, "cost_usd": round(call_cost, 8),
                    "answer": answer, "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                }
                answers[arm][job["qid"]] = receipt
            except Exception as exc:
                receipt = {
                    "arm": arm, "qid": job["qid"], "status": "FAILED_NO_RETRY",
                    "counted_input_tokens": job["counted"], "error": str(exc),
                }
            receipts.append(receipt)
            _write(DEFAULT_RECEIPTS, {
                "instrument": "s156_frontier_synthesis_ceiling_receipts_v1",
                "status": "IN_PROGRESS", "receipts": receipts,
            })

    # Oracle loading and target scoring occur only after every provider output is checkpointed.
    from scripts.s141_source_bound_technical_obligations import TARGET_KINDS

    arm_rows: dict[str, Any] = {}
    for arm in ("fable", "sol"):
        rows = []
        for qid in QIDS:
            receipt = answers[arm].get(qid)
            rows.append({
                "qid": qid,
                **(score_answer(qid, receipt["answer"], frozen) if receipt else {
                    "relations": len(TARGET_KINDS[qid]),
                    "covered": 0, "covered_kinds": [], "missing_kinds": [],
                    "citations": 0, "invalid_citations": [],
                }),
                "stop": receipt.get("stop") if receipt else None,
            })
        covered = sum(row["covered"] for row in rows)
        complete_calls = len(answers[arm])
        invalid = sum(len(row["invalid_citations"]) for row in rows)
        no_token_stop = all(
            row["stop"] not in {"max_tokens", "incomplete", "failed"} for row in rows
        )
        passed = complete_calls == 4 and covered >= prereg["validation"]["relations_min"] and invalid == 0 and no_token_stop
        arm_rows[arm] = {
            "calls_complete": complete_calls, "relations": 13, "covered": covered,
            "coverage": covered / 13, "invalid_citations": invalid,
            "no_token_limit_stop": no_token_stop, "gate": "GO" if passed else "NO_GO",
            "rows": rows,
        }
    passing = [arm for arm, row in arm_rows.items() if row["gate"] == "GO"]
    body = {
        "instrument": "s156_frontier_synthesis_ceiling_v1",
        "status": "GO_TO_FRESH_ROUTING_COHORT" if passing else "NO_GO_MODEL_SUBSTITUTION",
        "population": {"questions": 4, "relations": 13, "calls_planned": 8},
        "arms": arm_rows, "passing_arms": passing,
        "cost": {"worst_case_preflight_usd": round(worst, 8), "actual_usd": round(actual, 8)},
        "decision": {"production": False, "facts_moved_to_ok": 0,
                     "fresh_routing_test": bool(passing), "same_target_tuning": False},
    }
    result = {**body, "result_sha256": stable_sha(body)}
    _write(DEFAULT_RESULT, result)
    _write(DEFAULT_RECEIPTS, {
        "instrument": "s156_frontier_synthesis_ceiling_receipts_v1", "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(), "receipts": receipts,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        payload = json.loads(FREEZE.read_text(encoding="utf-8"))
        frozen = {str(row["qid"]): row for row in payload["rows"]}
        print(json.dumps({qid: {"system_chars": len(build_prompt(frozen[qid])[0]),
                                     "prompt_chars": len(build_prompt(frozen[qid])[1])} for qid in QIDS}))
        return 0
    prereg = validate_authorization(DEFAULT_PREREG, DEFAULT_PERMIT)
    print(json.dumps(execute(prereg, args.env_file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
