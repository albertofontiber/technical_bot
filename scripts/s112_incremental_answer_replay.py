#!/usr/bin/env python3
"""Incremental answer replay over the final S111 serving boundary.

Only prompts whose question, system prompt, or served context changed are sent
to the production generator. Byte-equivalent S110 prompts reuse their paid
answer, and a local checkpoint prevents accidental repeat spend.
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
FREEZE = ROOT / "evals/s111_combined_contexts_v1.json"
COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
SERVED_SUPPORT = ROOT / "evals/s111_served_support_cohort_v1.yaml"
PRIOR_RESULT = ROOT / "evals/s110_bounded_synthesis_regression_v2.json"
PRIOR_CHECKPOINT = ROOT / "evals/s110_bounded_synthesis_regression_v2.partial.jsonl"
OUT = ROOT / "evals/s112_incremental_answer_replay_v1.json"
CHECKPOINT = ROOT / "evals/s112_incremental_answer_replay_v1.partial.jsonl"


def stable_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def load_checkpoints(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row["qid"]] = row
    return rows


def reusable_prior(
    prior: dict | None,
    *,
    question_sha256: str,
    serving_context_sha256: str,
    system_prompt_sha256: str,
    prior_system_prompt_sha256: str,
) -> dict | None:
    """Return a paid prior only when the complete generator prompt is equal."""
    if prior is None or system_prompt_sha256 != prior_system_prompt_sha256:
        return None
    if prior.get("question_sha256") not in (None, question_sha256):
        return None
    if prior.get("serving_context_sha256") != serving_context_sha256:
        return None
    return {
        **prior,
        "question_sha256": question_sha256,
        "system_prompt_sha256": system_prompt_sha256,
        "reused_from_s110": True,
    }


def assert_checkpoint_compatible(
    row: dict,
    *,
    question_sha256: str,
    serving_context_sha256: str,
    system_prompt_sha256: str,
) -> None:
    expected = {
        "question_sha256": question_sha256,
        "serving_context_sha256": serving_context_sha256,
        "system_prompt_sha256": system_prompt_sha256,
    }
    for key, value in expected.items():
        if row.get(key) != value:
            raise RuntimeError(
                f"stale paid checkpoint for {row.get('qid')}: {key} mismatch; "
                "refusing repeat spend"
            )


def merge_support_packets(cohort: dict, served_support: dict) -> list[dict]:
    claims = {
        claim["claim_id"]: {**claim, "support_any": list(claim["support_any"])}
        for claim in cohort["residual_rerank_claims"]
    }
    for claim in served_support["claims"]:
        current = claims[claim["claim_id"]]
        bundles = {tuple(bundle) for bundle in current["support_any"]}
        bundles.update(tuple(bundle["ids"]) for bundle in claim["support_any"])
        current["support_any"] = [list(bundle) for bundle in sorted(bundles)]
    return list(claims.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "LLM_MAX_TOKENS": "3500",
            "GENERATOR_PROMPT_VARIANT": "fidelity",
            "GENERATOR_SELECTION_BLOCK": "on",
            "GENERATOR_INCLUDE_CONTEXT": "0",
        }
    )
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from scripts.atomic_scorer import match_fact
    from scripts.s110_bounded_synthesis_regression import (
        _citation_near_fact,
        _claim_present,
    )
    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.generator import _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import coverage_context_content

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    served_support = yaml.safe_load(SERVED_SUPPORT.read_text(encoding="utf-8"))
    prior_result = json.loads(PRIOR_RESULT.read_text(encoding="utf-8"))
    prior_rows = load_checkpoints(PRIOR_CHECKPOINT)
    checkpoints = load_checkpoints(CHECKPOINT)

    claims_by_qid: dict[str, list[dict]] = {}
    for claim in merge_support_packets(cohort, served_support):
        claims_by_qid.setdefault(claim["qid"], []).append(claim)

    system_prompt_sha256 = stable_sha(_assemble_system("contract probe"))
    prior_system_prompt_sha256 = prior_result["system_prompt_sha256"]
    rows = []
    for frozen in freeze["rows"]:
        qid = frozen["qid"]
        question_sha256 = stable_sha(frozen["question"])
        serving_context_sha256 = stable_sha(
            [coverage_context_content(chunk) for chunk in frozen["context"]]
        )

        paid = checkpoints.get(qid)
        if paid is not None:
            assert_checkpoint_compatible(
                paid,
                question_sha256=question_sha256,
                serving_context_sha256=serving_context_sha256,
                system_prompt_sha256=system_prompt_sha256,
            )
        else:
            paid = reusable_prior(
                prior_rows.get(qid),
                question_sha256=question_sha256,
                serving_context_sha256=serving_context_sha256,
                system_prompt_sha256=system_prompt_sha256,
                prior_system_prompt_sha256=prior_system_prompt_sha256,
            )

        if args.execute and paid is None:
            result = generate_answer(frozen["question"], frozen["context"])
            paid = {
                "qid": qid,
                "question_sha256": question_sha256,
                "serving_context_sha256": serving_context_sha256,
                "system_prompt_sha256": system_prompt_sha256,
                "model": LLM_MODEL,
                "max_output_tokens": LLM_MAX_TOKENS,
                "stop_reason": result.get("stop_reason"),
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "answer": result["answer"],
                "reused_from_s110": False,
            }
            with CHECKPOINT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(paid, ensure_ascii=False) + "\n")
                handle.flush()
            checkpoints[qid] = paid

        answer = (paid or {}).get("answer", "")
        target_claims = []
        for claim in claims_by_qid.get(qid, []):
            support_ids = {
                chunk_id for bundle in claim["support_any"] for chunk_id in bundle
            }
            citations = [
                f"[f{index}]"
                for index, chunk in enumerate(frozen["context"], 1)
                if str(chunk.get("id") or "") in support_ids
            ]
            present = _claim_present(claim["claim_id"], answer) if answer else False
            target_claims.append(
                {
                    "claim_id": claim["claim_id"],
                    "support_citations": citations,
                    "present": present,
                    "cited_by_support": (
                        _citation_near_fact(claim["claim_id"], answer, citations)
                        if answer
                        else False
                    ),
                }
            )

        protected = []
        for fact in frozen["protected_ok_facts"]:
            baseline_present, baseline_method, _ = match_fact(
                fact.get("valor"), fact.get("texto", ""), frozen["baseline_answer"]
            )
            current_present, current_method, detail = match_fact(
                fact.get("valor"), fact.get("texto", ""), answer
            ) if answer else (False, "not_executed", "")
            protected.append(
                {
                    "key": fact["key"],
                    "baseline_present": baseline_present,
                    "baseline_method": baseline_method,
                    "current_present": current_present,
                    "current_method": current_method,
                    "possible_regression": bool(
                        baseline_present is True and current_present is not True
                    ),
                    "detail": detail,
                }
            )

        rows.append(
            {
                "qid": qid,
                "executed": paid is not None,
                "requires_new_generator_call": reusable_prior(
                    prior_rows.get(qid),
                    question_sha256=question_sha256,
                    serving_context_sha256=serving_context_sha256,
                    system_prompt_sha256=system_prompt_sha256,
                    prior_system_prompt_sha256=prior_system_prompt_sha256,
                ) is None,
                "question_sha256": question_sha256,
                "serving_context_sha256": serving_context_sha256,
                "system_prompt_sha256": system_prompt_sha256,
                "target_claims": target_claims,
                "protected_ok_facts": protected,
                **(paid or {}),
            }
        )

    executed = [row for row in rows if row["executed"]]
    fresh = [row for row in executed if not row.get("reused_from_s110")]
    targets = [claim for row in rows for claim in row["target_claims"]]
    protected = [fact for row in rows for fact in row["protected_ok_facts"]]
    gate = {
        "changed_questions": len(rows),
        "byte_equivalent_reuses": sum(not row["requires_new_generator_call"] for row in rows),
        "new_generator_calls_required": sum(row["requires_new_generator_call"] for row in rows),
        "paid_generator_calls_available": len(executed),
        "fresh_paid_generator_calls": len(fresh),
        "reranker_calls": 0,
        "judge_calls": 0,
        "new_input_tokens": sum(row.get("input_tokens") or 0 for row in fresh),
        "new_output_tokens": sum(row.get("output_tokens") or 0 for row in fresh),
        "target_claims_present": sum(claim["present"] for claim in targets),
        "target_claims_cited_by_support": sum(
            claim["present"] and claim["cited_by_support"] for claim in targets
        ),
        "protected_facts_checked_deterministically": len(protected),
        "possible_protected_regressions": [
            fact["key"] for fact in protected if fact["possible_regression"]
        ],
        "max_tokens_stops": sum(
            row.get("stop_reason") == "max_tokens" for row in executed
        ),
        "interpretation": (
            "MEASURED_INCREMENTAL_REPLAY"
            if len(executed) == len(rows)
            else "PREFLIGHT_REUSE_AND_COST_GATE"
        ),
    }
    payload = {
        "instrument": "s112_incremental_answer_replay_v1",
        "execution_requested": args.execute,
        "frozen_contexts_sha256": freeze["frozen_contexts_sha256"],
        "generator_model": LLM_MODEL,
        "system_prompt_sha256": system_prompt_sha256,
        "gate": gate,
        "rows": rows,
        "limitations": [
            "Deterministic fact matching is a regression screen, not final semantic adjudication.",
            "Only byte-equivalent complete generator prompts may reuse a paid S110 answer.",
            "No reranker or LLM judge is called by this instrument.",
        ],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
