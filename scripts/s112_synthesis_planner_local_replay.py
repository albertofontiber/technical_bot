#!/usr/bin/env python3
"""Zero-call replay of the answer planner over the projected synthesis cohort.

This is a development instrument, not an OK adjudicator.  It binds every
answer to the most recent already-paid generator artifact, applies only the
deterministic planner, and records fact-level movement plus evidence receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atomic_scorer import match_fact
from src.rag.answer_planner import apply_answer_planner

FREEZE = ROOT / "evals/s112_synthesis_context_freeze_v1.json"
INCREMENTAL = ROOT / "evals/s112_incremental_answer_replay_v1.json"
S109 = ROOT / "evals/s109_bounded_synthesis_runtime_pilot_v1.json"
OUT = ROOT / "evals/s112_synthesis_planner_local_replay_v1.json"


def _sha(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _answers_by_qid(payload: dict) -> dict[str, str]:
    return {
        str(row["qid"]): str(row.get("answer") or "")
        for row in payload.get("rows", [])
        if row.get("qid") and row.get("answer")
    }


def latest_answer(row: dict, incremental: dict[str, str], s109: dict[str, str]) -> tuple[str, str]:
    qid = str(row["qid"])
    if qid in incremental:
        return incremental[qid], "s112_incremental_answer_replay_v1"
    if qid in s109:
        return s109[qid], "s109_bounded_synthesis_runtime_pilot_v1"
    return str(row.get("baseline_answer") or ""), "s100_factlevel_full_baseline_answer"


def _citation_numbers(answer: str) -> set[int]:
    return {
        int(value)
        for value in re.findall(r"(?i)\[f(\d+)\]", answer or "")
    }


def _fact_match(fact: dict, answer: str) -> dict:
    present, method, detail = match_fact(
        fact.get("valor"), fact.get("texto", ""), answer
    )
    return {
        "present": present,
        "method": method,
        "detail": detail,
    }


def main() -> int:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    incremental = _answers_by_qid(
        json.loads(INCREMENTAL.read_text(encoding="utf-8"))
    )
    s109 = _answers_by_qid(json.loads(S109.read_text(encoding="utf-8")))

    rows = []
    for frozen in freeze["rows"]:
        raw_answer, answer_source = latest_answer(frozen, incremental, s109)
        revised_answer, planner = apply_answer_planner(
            frozen["question"],
            frozen["served_context"],
            raw_answer,
            mode="supplement",
        )
        cited_fragments = _citation_numbers(revised_answer)
        facts = []
        for fact in frozen["synthesis_facts"]:
            before = _fact_match(fact, raw_answer)
            after = _fact_match(fact, revised_answer)
            facts.append(
                {
                    "key": fact["key"],
                    "projected_class": fact["projected_class"],
                    "before": before,
                    "after": after,
                    "local_transition": (
                        "candidate_fact_coverage_gain"
                        if before["present"] is not True and after["present"] is True
                        else "no_deterministic_fact_gain"
                    ),
                    "manual_review_required": True,
                }
            )
        plan = (planner or {}).get("plan", [])
        rows.append(
            {
                "qid": frozen["qid"],
                "question": frozen["question"],
                "context_source": frozen["context_source"],
                "answer_source": answer_source,
                "raw_answer_sha256": _sha(raw_answer),
                "revised_answer_sha256": _sha(revised_answer),
                "answer_changed": revised_answer != raw_answer,
                "planner": planner,
                "all_obligation_citations_present": all(
                    int(item["fragment_number"]) in cited_fragments for item in plan
                ),
                "facts": facts,
                "revised_answer": revised_answer,
            }
        )

    facts = [fact for row in rows for fact in row["facts"]]
    obligations = [
        item
        for row in rows
        for item in ((row.get("planner") or {}).get("plan") or [])
    ]
    gate = {
        "questions": len(rows),
        "projected_synthesis_facts": len(facts),
        "questions_changed": sum(row["answer_changed"] for row in rows),
        "obligations": len(obligations),
        "obligations_covered_after": sum(
            (row.get("planner") or {}).get("validation", {}).get("covered", 0)
            for row in rows
        ),
        "candidate_fact_coverage_gains": sum(
            fact["local_transition"] == "candidate_fact_coverage_gain"
            for fact in facts
        ),
        "model_calls": 0,
        "database_calls": 0,
        "release_decision": "NO_GO_DEVELOPMENT_COHORT_REQUIRES_GUIDED_GENERATION_AND_REVIEW",
    }
    payload = {
        "instrument": "s112_synthesis_planner_local_replay_v1",
        "mode": "supplement_development_only",
        "inputs": {
            "freeze": str(FREEZE.relative_to(ROOT)),
            "incremental_answers": str(INCREMENTAL.relative_to(ROOT)),
            "s109_answers": str(S109.relative_to(ROOT)),
        },
        "gate": gate,
        "rows": rows,
        "limitations": [
            "Known development cohort; no held-out precision claim is permitted.",
            "Supplement mode measures extractive coverage, not response coherence.",
            "Every fact transition remains manual-review-required until guided generation is checked.",
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
