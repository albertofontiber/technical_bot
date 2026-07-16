#!/usr/bin/env python3
"""Zero-model replay of the S112 answer planner over frozen S111 contexts."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atomic_scorer import match_fact
from scripts.s110_bounded_synthesis_regression import (
    _citation_near_fact,
    _claim_present,
)
from scripts.s112_incremental_answer_replay import merge_support_packets
from src.rag.answer_planner import apply_answer_planner

FREEZE = ROOT / "evals/s111_combined_contexts_v1.json"
ANSWERS = ROOT / "evals/s112_incremental_answer_replay_v1.json"
COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
SERVED_SUPPORT = ROOT / "evals/s111_served_support_cohort_v1.yaml"
OUT = ROOT / "evals/s112_answer_planner_local_replay_v1.json"
SEMANTIC_REVIEW = ROOT / "evals/s112_protected_semantic_review_v1.yaml"

_NUMBER_WORDS = {
    "un": "1", "uno": "1", "una": "1", "one": "1",
    "dos": "2", "two": "2", "tres": "3", "three": "3",
    "cuatro": "4", "four": "4", "cinco": "5", "five": "5",
    "seis": "6", "six": "6", "siete": "7", "seven": "7",
    "ocho": "8", "eight": "8", "nueve": "9", "nine": "9",
    "diez": "10", "ten": "10",
}


def _sha(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _digits_for_number_words(value: str) -> str:
    output = value or ""
    for word, digit in _NUMBER_WORDS.items():
        output = re.sub(rf"(?i)\b{word}\b", digit, output)
    return output


def protected_fact_present(fact: dict, answer: str) -> tuple[bool | None, str]:
    present, method, _detail = match_fact(
        fact.get("valor"), fact.get("texto", ""), answer
    )
    if present is True or not fact.get("valor"):
        return present, method
    normalized_value = _digits_for_number_words(str(fact["valor"]))
    normalized_answer = _digits_for_number_words(answer)
    normalized, normalized_method, _ = match_fact(
        normalized_value, fact.get("texto", ""), normalized_answer
    )
    return normalized, f"{normalized_method}+number_word_normalization"


def semantic_adjudication(
    review: dict,
    *,
    qid: str,
    fact_key: str,
    answer_sha256: str,
) -> dict | None:
    """Return a pass only for an exact, explicitly reviewed answer boundary."""
    matches = [
        row
        for row in review.get("adjudications", [])
        if row.get("qid") == qid and row.get("fact_key") == fact_key
    ]
    if len(matches) != 1:
        return None
    row = matches[0]
    if row.get("verdict") != "pass" or row.get("answer_sha256") != answer_sha256:
        return None
    return row


def main() -> int:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    answer_artifact = json.loads(ANSWERS.read_text(encoding="utf-8"))
    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    served_support = yaml.safe_load(SERVED_SUPPORT.read_text(encoding="utf-8"))
    semantic_review = yaml.safe_load(SEMANTIC_REVIEW.read_text(encoding="utf-8"))
    answers = {row["qid"]: row for row in answer_artifact["rows"]}
    claims_by_qid: dict[str, list[dict]] = {}
    for claim in merge_support_packets(cohort, served_support):
        claims_by_qid.setdefault(claim["qid"], []).append(claim)

    rows = []
    for frozen in freeze["rows"]:
        qid = frozen["qid"]
        raw_answer = answers[qid]["answer"]
        revised, planner = apply_answer_planner(
            frozen["question"], frozen["context"], raw_answer, mode="supplement"
        )
        targets = []
        for claim in claims_by_qid.get(qid, []):
            support_ids = {
                chunk_id
                for bundle in claim["support_any"]
                for chunk_id in bundle
            }
            citations = [
                f"[f{index}]"
                for index, chunk in enumerate(frozen["context"], 1)
                if str(chunk.get("id") or "") in support_ids
            ]
            present = _claim_present(claim["claim_id"], revised)
            targets.append(
                {
                    "claim_id": claim["claim_id"],
                    "present": present,
                    "cited_by_support": _citation_near_fact(
                        claim["claim_id"], revised, citations
                    ),
                    "support_citations": citations,
                }
            )

        protected = []
        for fact in frozen["protected_ok_facts"]:
            lexical_present, method = protected_fact_present(fact, revised)
            adjudication = semantic_adjudication(
                semantic_review,
                qid=qid,
                fact_key=fact["key"],
                answer_sha256=_sha(revised),
            )
            present = lexical_present is True or adjudication is not None
            protected.append(
                {
                    "key": fact["key"],
                    "present": present,
                    "lexical_present": lexical_present,
                    "method": (
                        f"{method}+exact_hash_semantic_review"
                        if adjudication is not None
                        else method
                    ),
                    "semantic_review": (
                        {
                            "instrument": semantic_review["instrument"],
                            "matcher_limitation": adjudication["matcher_limitation"],
                        }
                        if adjudication is not None
                        else None
                    ),
                }
            )
        rows.append(
            {
                "qid": qid,
                "raw_answer_sha256": _sha(raw_answer),
                "revised_answer_sha256": _sha(revised),
                "answer_changed": revised != raw_answer,
                "planner": planner,
                "target_claims": targets,
                "protected_ok_facts": protected,
                "revised_answer": revised,
            }
        )

    targets = [claim for row in rows for claim in row["target_claims"]]
    protected = [fact for row in rows for fact in row["protected_ok_facts"]]
    obligations = [
        item for row in rows for item in (row["planner"] or {}).get("plan", [])
    ]
    gate = {
        "questions": len(rows),
        "questions_changed": sum(row["answer_changed"] for row in rows),
        "obligations": len(obligations),
        "obligations_post_validation_covered": sum(
            (row["planner"] or {}).get("validation", {}).get("covered", 0)
            for row in rows
        ),
        "target_claims_present": sum(claim["present"] for claim in targets),
        "target_claims_cited_by_support": sum(
            claim["present"] and claim["cited_by_support"] for claim in targets
        ),
        "protected_ok_facts_lexical_present": sum(
            fact["lexical_present"] is True for fact in protected
        ),
        "protected_ok_facts_present": sum(fact["present"] is True for fact in protected),
        "protected_ok_facts_total": len(protected),
        "model_calls": 0,
        "database_calls": 0,
        "interpretation": (
            "GO_LOCAL_DETERMINISTIC_KNOWN_COHORT_ADVERSARIAL_REVIEW_COMPLETE"
            if all(fact["present"] is True for fact in protected)
            else "NO_GO_PROTECTED_REGRESSION"
        ),
    }
    payload = {
        "instrument": "s112_answer_planner_local_replay_v1",
        "mode": "supplement",
        "inputs": {
            "freeze": str(FREEZE.relative_to(ROOT)),
            "answers": str(ANSWERS.relative_to(ROOT)),
            "cohort": str(COHORT.relative_to(ROOT)),
            "semantic_review": str(SEMANTIC_REVIEW.relative_to(ROOT)),
        },
        "gate": gate,
        "rows": rows,
        "limitations": [
            "Known development cohort; this is not held-out precision evidence.",
            "The supplement is source-extractive and does not repair unsupported upstream evidence.",
            "Protected fact matching is deterministic and number-word normalized; semantic review remains a release gate.",
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
