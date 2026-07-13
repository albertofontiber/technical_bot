#!/usr/bin/env python3
"""Bounded production-generator replay over the 11 changed S110 contexts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s110_combined_contexts_v1.json"
COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
OUT = ROOT / "evals/s110_bounded_synthesis_regression_v2.json"
CHECKPOINT = ROOT / "evals/s110_bounded_synthesis_regression_v2.partial.jsonl"
PRIOR_CHECKPOINT = ROOT / "evals/s110_bounded_synthesis_regression_v1.partial.jsonl"


def _stable_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()


def _claim_present(claim_id: str, answer: str) -> bool:
    text = _fold(answer)
    if claim_id == "cat001.isolator.pearl_max_25":
        return "aislador" in text and bool(re.search(r"\b25\b", text))
    if claim_id == "cat010.supply.nominal_24vdc":
        return bool(re.search(r"\b24\s*v(?:dc|\s*cc|\s*dc)?\b", text))
    if claim_id == "hp005.output.select_specific_siren_circuit":
        return "circuito" in text and "sirena" in text and bool(
            re.search(r"seleccion|elegir|aplicar|funcion especial", text)
        )
    if claim_id == "hp009.loop.closed_topology":
        return bool(re.search(r"(?:lazo|bucle).{0,35}cerrad|cerrad.{0,35}(?:lazo|bucle)", text, re.S))
    if claim_id == "hp009.loop.return_terminals":
        return "retorno" in text and bool(re.search(r"terminal|borne|inicio|out", text))
    if claim_id == "hp009.loop.no_eol_resistor":
        return bool(re.search(
            r"(?:no|sin).{0,40}(?:resistencia|rfl|eol).{0,35}(?:fin|final).{0,20}linea"
            r"|(?:resistencia|rfl|eol).{0,35}(?:fin|final).{0,20}linea.{0,40}(?:no|sin)",
            text,
            re.S,
        ))
    if claim_id == "hp011.reset_inhibit.dash_until_extinction_or_tA":
        return bool(re.search(r"(?:--|- -|guion).{0,120}(?:finalizar|fin).{0,35}extincion", text, re.S))
    if claim_id == "hp011.reset_inhibit.default_00_anytime":
        return "00" in text and bool(re.search(
            r"(?:permitid|permite).{0,60}(?:cualquier momento|siempre)|(?:cualquier momento|siempre).{0,60}(?:permitid|permite)",
            text,
            re.S,
        ))
    raise KeyError(claim_id)


def _citation_near_fact(claim_id: str, answer: str, citations: list[str]) -> bool:
    folded = _fold(answer)
    for citation in citations:
        start = 0
        while True:
            position = folded.find(citation.casefold(), start)
            if position < 0:
                break
            window = answer[max(0, position - 800): position + len(citation) + 800]
            if _claim_present(claim_id, window):
                return True
            start = position + len(citation)
    return False


def _load_checkpoints(path: Path) -> dict[str, dict]:
    rows = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["qid"]] = row
    return rows


def _append_checkpoint(row: dict) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


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

    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.generator import _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import coverage_context_content
    from src.rag.rerank_pool_coverage import LANE as POOL_LANE

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    claims_by_qid: dict[str, list[dict]] = {}
    for claim in cohort["residual_rerank_claims"]:
        claims_by_qid.setdefault(claim["qid"], []).append(claim)

    checkpoints = _load_checkpoints(CHECKPOINT)
    prior_v1 = _load_checkpoints(PRIOR_CHECKPOINT)
    rows = []
    for frozen in freeze["rows"]:
        qid = frozen["qid"]
        context_sha = _stable_sha(frozen["context"])
        serving_context_sha = _stable_sha(
            [coverage_context_content(chunk) for chunk in frozen["context"]]
        )
        if context_sha != frozen["context_sha256"]:
            raise RuntimeError(f"frozen context hash mismatch for {qid}")
        prior = checkpoints.get(qid)
        if prior and (
            prior["context_sha256"] != context_sha
            or prior["serving_context_sha256"] != serving_context_sha
        ):
            raise RuntimeError(f"stale paid checkpoint for {qid}; refusing repeat spend")
        # Pool-only prompts are byte-identical to v1: that lane was already
        # excerpt-bounded. Reuse those paid answers; only contexts containing
        # structural/HYQ rows changed under v2 compression.
        pool_only = bool(frozen["appended_lanes"]) and all(
            lane == POOL_LANE for lane in frozen["appended_lanes"]
        )
        if args.execute and prior is None and pool_only and qid in prior_v1:
            old = prior_v1[qid]
            if old["context_sha256"] != context_sha:
                raise RuntimeError(f"v1 reuse context mismatch for {qid}")
            prior = {
                **old,
                "serving_context_sha256": serving_context_sha,
                "reused_from_v1": True,
            }
            _append_checkpoint(prior)
            checkpoints[qid] = prior
        if args.execute and prior is None:
            result = generate_answer(frozen["question"], frozen["context"])
            prior = {
                "qid": qid,
                "context_sha256": context_sha,
                "serving_context_sha256": serving_context_sha,
                "model": LLM_MODEL,
                "max_output_tokens": LLM_MAX_TOKENS,
                "stop_reason": result.get("stop_reason"),
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "answer": result["answer"],
                "reused_from_v1": False,
            }
            _append_checkpoint(prior)
            checkpoints[qid] = prior

        answer = (prior or {}).get("answer", "")
        claim_results = []
        for claim in claims_by_qid.get(qid, []):
            support_ids = {
                value for bundle in claim["support_any"] for value in bundle
            }
            citations = [
                f"[f{index}]"
                for index, chunk in enumerate(frozen["context"], 1)
                if str(chunk.get("id") or "") in support_ids
            ]
            present = _claim_present(claim["claim_id"], answer) if answer else False
            claim_results.append(
                {
                    "claim_id": claim["claim_id"],
                    "support_citations": citations,
                    "present": present,
                    "cited_by_support": (
                        _citation_near_fact(claim["claim_id"], answer, citations)
                        if answer else False
                    ),
                }
            )
        rows.append(
            {
                "qid": qid,
                "executed": prior is not None,
                "context_sha256": context_sha,
                "serving_context_sha256": serving_context_sha,
                "protected_ok_facts": frozen["protected_ok_facts"],
                "baseline_answer": frozen["baseline_answer"],
                "target_claims": claim_results,
                **(prior or {}),
            }
        )

    executed = [row for row in rows if row["executed"]]
    fresh = [row for row in executed if not row.get("reused_from_v1")]
    target_results = [claim for row in rows for claim in row["target_claims"]]
    gate = {
        "changed_questions": len(rows),
        "paid_generator_calls": len(executed),
        "new_paid_generator_calls": len(fresh),
        "reused_identical_prompt_calls": len(executed) - len(fresh),
        "paid_reranker_calls": 0,
        "llm_judge_calls": 0,
        "total_input_tokens": sum(row.get("input_tokens") or 0 for row in executed),
        "total_output_tokens": sum(row.get("output_tokens") or 0 for row in executed),
        "new_input_tokens": sum(row.get("input_tokens") or 0 for row in fresh),
        "new_output_tokens": sum(row.get("output_tokens") or 0 for row in fresh),
        "target_claims_present": sum(row["present"] for row in target_results),
        "target_claims_cited_by_support": sum(
            row["present"] and row["cited_by_support"] for row in target_results
        ),
        "protected_ok_facts_pending_manual_regression": sum(
            len(row["protected_ok_facts"]) for row in rows
        ),
        "max_tokens_stops": sum(
            row.get("stop_reason") == "max_tokens" for row in executed
        ),
        "interpretation": (
            "MEASURED_PENDING_LOCAL_PROTECTED_REVIEW"
            if len(executed) == len(rows)
            else "PREFLIGHT_NO_OR_PARTIAL_PAID_CALLS"
        ),
    }
    payload = {
        "instrument": "s110_bounded_synthesis_regression_v2",
        "execution_requested": args.execute,
        "frozen_contexts_sha256": freeze["frozen_contexts_sha256"],
        "generator_model": LLM_MODEL,
        "system_prompt_sha256": _stable_sha(_assemble_system("contract probe")),
        "gate": gate,
        "rows": rows,
        "limitations": [
            "No reranker or judge model is called; only one production generator call per changed question is allowed.",
            "Target regex checks are diagnostics and do not replace the local protected-OK source review.",
            "Known development cohort; official OK remains unchanged.",
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
