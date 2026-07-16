#!/usr/bin/env python3
"""Build the zero-generation manifest for the S113 frozen full regression.

All 39 questions are represented. Questions whose final serving context did not
change reuse the S100 answer only when the guided planner produces no obligation.
Changed contexts reuse the exact S112 incremental answer under the same rule.
An S112 guided answer is reusable only when its complete guided prompt hash is
identical. Everything else is explicitly marked for a new generator call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
FINAL_CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
INCREMENTAL = ROOT / "evals/s112_incremental_answer_replay_v1.json"
GUIDED = ROOT / "evals/s112_guided_synthesis_probe_v1.json"
OUT = ROOT / "evals/s113_full_regression_preflight_v1.json"


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def guided_prompt_contract(
    *, question: str, context: list[dict], plan: list, system: str, model: str,
    max_tokens: int, coverage_context_content, render_answer_plan_guidance,
) -> dict:
    return {
        "question": question,
        "context": [coverage_context_content(chunk) for chunk in context],
        "context_headers": [
            {
                key: chunk.get(key)
                for key in (
                    "product_model",
                    "section_title",
                    "content_type",
                    "source_file",
                    "document_revision",
                    "document_revision_date",
                )
            }
            for chunk in context
        ],
        "plan": [item.to_dict() for item in plan],
        "guidance": render_answer_plan_guidance(plan),
        "system": system,
        "model": model,
        "max_tokens": max_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "LLM_MAX_TOKENS": "3500",
            "GENERATOR_PROMPT_VARIANT": "fidelity",
            "GENERATOR_SELECTION_BLOCK": "on",
            "GENERATOR_INCLUDE_CONTEXT": "0",
            "ANSWER_OBLIGATION_PLANNER": "guided",
        }
    )
    for key in (
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "CANONICAL_HYQ_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        os.environ[key] = "on"
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))

    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_planner import build_answer_plan, render_answer_plan_guidance
    from src.rag.generator import _assemble_system
    from src.rag.post_rerank_coverage import coverage_context_content

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    baseline_by_qid = {row["qid"]: row for row in baseline["per_gold"]}
    final_artifact = json.loads(FINAL_CONTEXTS.read_text(encoding="utf-8"))
    final_contexts = {row["qid"]: row for row in final_artifact["rows"]}
    incremental_artifact = json.loads(INCREMENTAL.read_text(encoding="utf-8"))
    incremental = {row["qid"]: row for row in incremental_artifact["rows"]}
    guided_artifact = json.loads(GUIDED.read_text(encoding="utf-8"))
    guided = {row["qid"]: row for row in guided_artifact["rows"] if row.get("executed")}

    # The just-frozen selection inputs must still be byte-identical.
    implementation_receipts = []
    for receipt in final_artifact["implementation_inputs"]:
        path = ROOT / receipt["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        implementation_receipts.append(
            {**receipt, "actual_sha256": actual, "equal": actual == receipt["sha256"]}
        )
    if not all(row["equal"] for row in implementation_receipts):
        raise RuntimeError("S113 context-selection implementation drifted")

    rows = []
    for qid in sorted(baseline_by_qid):
        base = baseline_by_qid[qid]
        final = final_contexts[qid]
        context = final["context"]
        context_changed = bool(final["appended_ids"])
        context_source = (
            "s113_integrated_context_with_appends"
            if context_changed else "s113_integrated_bit_inert_prefix"
        )

        plan = build_answer_plan(base["question"], context)
        contract = guided_prompt_contract(
            question=base["question"],
            context=context,
            plan=plan,
            system=_assemble_system(base["question"]),
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            coverage_context_content=coverage_context_content,
            render_answer_plan_guidance=render_answer_plan_guidance,
        )
        prompt_sha256 = stable_sha({"qid": qid, **contract})
        content_sha256 = stable_sha(contract["context"])

        reuse_source = None
        answer = None
        cached = guided.get(qid)
        if cached and cached.get("prompt_sha256") == prompt_sha256:
            reuse_source = "s112_guided_exact_prompt"
            answer = cached["answer"]
        elif not plan and context_changed:
            prior = incremental.get(qid)
            if prior and prior.get("serving_context_sha256") == content_sha256:
                reuse_source = "s112_incremental_exact_context_no_plan"
                answer = prior["answer"]
        elif not plan and not context_changed:
            reuse_source = "s100_bit_inert_no_plan"
            answer = base["answer"]

        rows.append(
            {
                "qid": qid,
                "question": base["question"],
                "context_source": context_source,
                "appended_ids": final["appended_ids"],
                "appended_lanes": final["appended_lanes"],
                "context_rows": len(context),
                "serving_context_sha256": content_sha256,
                "guided_prompt_sha256": prompt_sha256,
                "obligation_kinds": [item.kind for item in plan],
                "obligation_count": len(plan),
                "reuse_source": reuse_source,
                "requires_new_generator_call": reuse_source is None,
                "answer_sha256": (
                    hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else None
                ),
            }
        )

    payload = {
        "instrument": "s113_full_regression_preflight_v1",
        "scope": {
            "questions": len(rows),
            "fact_rows": sum(len(row["facts"]) for row in baseline["per_gold"]),
            "baseline": str(BASELINE.relative_to(ROOT)),
            "final_contexts": str(FINAL_CONTEXTS.relative_to(ROOT)),
        },
        "implementation_receipts": implementation_receipts,
        "gate": {
            "questions_with_changed_context": sum(bool(row["appended_ids"]) for row in rows),
            "questions_with_nonempty_answer_plan": sum(bool(row["obligation_count"]) for row in rows),
            "exact_paid_answer_reuses": sum(not row["requires_new_generator_call"] for row in rows),
            "new_generator_calls_required": sum(row["requires_new_generator_call"] for row in rows),
            "baseline_hydration_get_batches": 0,
            "reranker_calls_required": 0,
            "judge_calls_required_for_preflight": 0,
            "database_writes": 0,
            "interpretation": "ZERO_GENERATION_FULL_COHORT_MANIFEST",
        },
        "rows": rows,
        "limitations": [
            "S100 reuse is allowed only for a context selected as bit-inert by S111 and an empty guided plan.",
            "This preflight does not classify facts or authorize a release.",
            "Manual and judge review is still required for changed answers.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    print("new qids:", [row["qid"] for row in rows if row["requires_new_generator_call"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
