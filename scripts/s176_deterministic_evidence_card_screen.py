#!/usr/bin/env python3
"""Run the frozen zero-model deterministic evidence-card screen."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.omission_correction import (
    _STOPWORDS,
    fold,
    invalid_citations,
    point_covered,
    units_by_fragment,
)
from src.rag.evidence_units_v2 import reconstruct_unit_content


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
PREREG = ROOT / "evals/s176_deterministic_evidence_card_prereg_v1.yaml"
OUT = ROOT / "evals/s176_deterministic_evidence_card_screen_v1.json"
MAX_UNITS = 2
MAX_SOURCE_CHARS = 1800
MIN_MATCHED_TERMS = 2
MIN_QUERY_TERM_COVERAGE = 0.25


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", fold(value))
        if len(token) > 2 and token not in _STOPWORDS
    ]


def rank_units(question: str, units: list[Any]) -> list[tuple[float, Any, list[str]]]:
    query_terms = tokens(question)
    query_unique = set(query_terms)
    documents = [tokens(unit.content) for unit in units]
    document_frequency: Counter[str] = Counter()
    for terms in documents:
        document_frequency.update(set(terms))
    average_length = sum(map(len, documents)) / len(documents) if documents else 1.0
    ranked = []
    for unit, terms in zip(units, documents):
        frequencies = Counter(terms)
        matched = sorted(query_unique.intersection(frequencies))
        coverage = len(matched) / max(1, len(query_unique))
        if len(matched) < MIN_MATCHED_TERMS or coverage < MIN_QUERY_TERM_COVERAGE:
            continue
        score = 0.0
        for term in query_terms:
            frequency = document_frequency[term]
            if not frequency:
                continue
            inverse = math.log(
                1 + (len(documents) - frequency + 0.5) / (frequency + 0.5)
            )
            term_frequency = frequencies[term]
            denominator = term_frequency + 1.5 * (
                0.25 + 0.75 * len(terms) / max(average_length, 1.0)
            )
            if denominator:
                score += inverse * (term_frequency * 2.5 / denominator)
        ranked.append((score, unit, matched))
    return sorted(ranked, key=lambda row: (-row[0], row[1].unit_id))


def select_units(item: dict[str, Any]) -> list[tuple[float, Any, list[str]]]:
    chunk = {"id": item["chunk_id"], "content": item["excerpt"]}
    units = units_by_fragment([chunk])[1]
    selected = []
    used_chars = 0
    seen_content: set[str] = set()
    for score, unit, matched in rank_units(item["question"], units):
        if unit.content_sha256 in seen_content:
            continue
        if len(unit.content) > MAX_SOURCE_CHARS - used_chars:
            continue
        selected.append((score, unit, matched))
        seen_content.add(unit.content_sha256)
        used_chars += len(unit.content)
        if len(selected) == MAX_UNITS:
            break
    return selected


def render_card(baseline: str, selected: list[tuple[float, Any, list[str]]]) -> str:
    if not selected:
        return baseline
    rows = [baseline.rstrip(), "", "Evidencia literal del manual:"]
    for _score, unit, _matched in selected:
        rows.extend([f"- {unit.content} [F{unit.fragment_number}]"])
    return "\n".join(rows)


def validate_prereg() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_LOCAL_EXECUTION":
        raise RuntimeError("S176 preregistration is not frozen")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S176 frozen input drift: {spec['path']}")
    return prereg


def main() -> int:
    validate_prereg()
    if OUT.exists():
        raise RuntimeError("S176 output exists; same-cohort retries are forbidden")
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    baseline_payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    items = cohort["items"]
    baselines = {row["item_id"]: row for row in baseline_payload["receipts"]}
    if len(items) != 14 or set(baselines) != {row["item_id"] for row in items}:
        raise RuntimeError("S176 population mismatch")

    candidates: dict[str, str] = {}
    selection_receipts = []
    span_failures = 0
    for item in items:
        selected = select_units(item)
        for _score, unit, _matched in selected:
            if reconstruct_unit_content(item["excerpt"], unit) != unit.content:
                span_failures += 1
        answer = render_card(baselines[item["item_id"]]["answer"], selected)
        candidates[item["item_id"]] = answer
        selection_receipts.append(
            {
                "item_id": item["item_id"],
                "question_sha256": hashlib.sha256(
                    item["question"].encode("utf-8")
                ).hexdigest(),
                "selected": [
                    {
                        "unit_id": unit.unit_id,
                        "unit_kind": unit.unit_kind,
                        "fragment_number": unit.fragment_number,
                        "source_spans": [list(span) for span in unit.source_spans],
                        "content_sha256": unit.content_sha256,
                        "content_chars": len(unit.content),
                        "bm25_score": score,
                        "matched_question_terms": matched,
                    }
                    for score, unit, matched in selected
                ],
                "selected_source_chars": sum(
                    len(unit.content) for _score, unit, _matched in selected
                ),
                "candidate_answer_sha256": hashlib.sha256(
                    answer.encode("utf-8")
                ).hexdigest(),
            }
        )

    # Load evaluation gold only after deterministic candidates and receipts exist.
    gold_payload = json.loads(GOLD.read_text(encoding="utf-8"))
    gold = {row["item_id"]: row for row in gold_payload["items"] if row["eligible"]}
    rows = []
    baseline_points = candidate_points = 0
    baseline_complete = candidate_complete = regressions = invalid = 0
    for item in items:
        item_id = item["item_id"]
        points = gold[item_id]["answer_points"]
        baseline_answer = baselines[item_id]["answer"]
        candidate_answer = candidates[item_id]
        base_hits = [point_covered(baseline_answer, point) for point in points]
        candidate_hits = [point_covered(candidate_answer, point) for point in points]
        regressed = sum(
            before and not after for before, after in zip(base_hits, candidate_hits)
        )
        baseline_points += sum(base_hits)
        candidate_points += sum(candidate_hits)
        baseline_complete += int(all(base_hits))
        candidate_complete += int(all(candidate_hits))
        regressions += regressed
        invalid_rows = invalid_citations(candidate_answer, 1)
        invalid += len(invalid_rows)
        rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "answer_points": len(points),
                "baseline_points_covered": sum(base_hits),
                "candidate_points_covered": sum(candidate_hits),
                "baseline_complete": all(base_hits),
                "candidate_complete": all(candidate_hits),
                "regressed_points": regressed,
                "invalid_citations": invalid_rows,
            }
        )
    selected_questions = sum(bool(row["selected"]) for row in selection_receipts)
    selected_chars = [
        row["selected_source_chars"]
        for row in selection_receipts
        if row["selected"]
    ]
    mean_chars = sum(selected_chars) / len(selected_chars) if selected_chars else 0
    point_gain = candidate_points - baseline_points
    complete_gain = candidate_complete - baseline_complete
    checks = {
        "all_14_items_scored": len(rows) == 14,
        "frozen_baseline_26_points": baseline_points == 26,
        "frozen_baseline_6_complete": baseline_complete == 6,
        "point_gain_gte_4": point_gain >= 4,
        "complete_question_gain_gte_2": complete_gain >= 2,
        "regressed_points_zero": regressions == 0,
        "invalid_citations_zero": invalid == 0,
        "source_span_failures_zero": span_failures == 0,
        "selected_questions_gte_2": selected_questions >= 2,
        "selected_questions_lte_12": selected_questions <= 12,
        "mean_appended_source_chars_lte_1200": mean_chars <= 1200,
    }
    passed = all(checks.values())
    body = {
        "instrument": "s176_deterministic_evidence_card_screen_v1",
        "status": "GO_TO_BLINDED_ADVERSARIAL_REVIEW" if passed else "NO_GO",
        "population": {
            "items": len(items),
            "manufacturers": len({row["manufacturer"] for row in items}),
            "table": sum(row["stratum"] == "table" for row in items),
            "prose": sum(row["stratum"] == "prose" for row in items),
            "answer_points": sum(len(row["answer_points"]) for row in gold.values()),
            "target_question_overlap": 0,
        },
        "metrics": {
            "baseline_points_covered": baseline_points,
            "candidate_points_covered": candidate_points,
            "point_gain": point_gain,
            "baseline_questions_complete": baseline_complete,
            "candidate_questions_complete": candidate_complete,
            "complete_question_gain": complete_gain,
            "regressed_points": regressions,
            "invalid_citations": invalid,
            "source_span_failures": span_failures,
            "selected_questions": selected_questions,
            "selected_units": sum(len(row["selected"]) for row in selection_receipts),
            "mean_appended_source_chars": mean_chars,
        },
        "checks": checks,
        "selection_receipts": selection_receipts,
        "rows": rows,
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "usd": 0,
        },
        "decision": {
            "blinded_adversarial_review": passed,
            "target_probe": False,
            "runtime_or_production": False,
            "facts_moved_to_ok": 0,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
