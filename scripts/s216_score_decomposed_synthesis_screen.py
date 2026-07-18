#!/usr/bin/env python3
"""Score sealed S216 generation outputs after every provider call is complete."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.atomic_scorer import match_fact
from src.rag.omission_correction import point_covered


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s216_synthesis_screen_packet_v1.json"
GENERATION = ROOT / "evals/s216_generation_receipts_v1.json"
SINGLE_GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
MULTI_SCORE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
OUT = ROOT / "evals/s216_decomposed_synthesis_screen_v1.json"
TARGETS = {"cat018", "hp002", "hp011", "hp017"}


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _answers(payload: dict[str, Any]) -> dict[tuple[str, str, int], str]:
    rows = payload.get("answers") or []
    output = {
        (row["item_id"], row["arm"], int(row["replicate"])): row["answer"]
        for row in rows
    }
    if len(rows) != 196 or len(output) != 196:
        raise RuntimeError("S216 final answer matrix must be exactly 49x2x2")
    return output


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S216 score exists; rescoring is forbidden")
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    if generation.get("status") != "COMPLETE_SCORE_NOT_OPENED":
        raise RuntimeError("S216 generation is not complete")
    rows = packet["rows"]
    if len(rows) != 49 or any(row["item_id"] in TARGETS for row in rows):
        raise RuntimeError("S216 generation packet population drift")
    answers = _answers(generation)

    # Score packets are opened only in this separate post-generation process.
    single = json.loads(SINGLE_GOLD.read_text(encoding="utf-8"))
    single_by = {
        row["item_id"]: row for row in single["items"] if row.get("eligible")
    }
    multi = json.loads(MULTI_SCORE.read_text(encoding="utf-8"))
    multi_by = {str(row["qid"]): row for row in multi["rows"]}

    single_rows: list[dict[str, Any]] = []
    stable_point_gains: list[str] = []
    stable_complete_gains: list[str] = []
    point_regressions: list[str] = []
    for row in rows:
        item_id = row["item_id"]
        if row["role"] != "single_source_development":
            continue
        points = single_by[item_id]["answer_points"]
        arm_hits: dict[str, list[list[bool]]] = {"control": [], "treatment": []}
        for arm in ("control", "treatment"):
            for replicate in (1, 2):
                answer = answers[(item_id, arm, replicate)]
                arm_hits[arm].append(
                    [point_covered(answer, point) for point in points]
                )
        gains = []
        regressions = []
        for index in range(len(points)):
            control = [values[index] for values in arm_hits["control"]]
            treatment = [values[index] for values in arm_hits["treatment"]]
            point_id = f"{item_id}:point_{index + 1}"
            if treatment == [True, True] and control == [False, False]:
                stable_point_gains.append(point_id)
                gains.append(point_id)
            if control == [True, True] and treatment != [True, True]:
                point_regressions.append(point_id)
                regressions.append(point_id)
        control_complete = [all(values) for values in arm_hits["control"]]
        treatment_complete = [all(values) for values in arm_hits["treatment"]]
        complete_gain = treatment_complete == [True, True] and control_complete == [False, False]
        if complete_gain:
            stable_complete_gains.append(item_id)
        single_rows.append(
            {
                "item_id": item_id,
                "answer_points": len(points),
                "control_points": [sum(values) for values in arm_hits["control"]],
                "treatment_points": [sum(values) for values in arm_hits["treatment"]],
                "control_complete": control_complete,
                "treatment_complete": treatment_complete,
                "stable_gain_ids": gains,
                "regression_ids": regressions,
                "stable_complete_gain": complete_gain,
            }
        )

    multi_rows: list[dict[str, Any]] = []
    protected_regressions: list[str] = []
    protected_facts = 0
    stable_control_facts = 0
    for row in rows:
        item_id = row["item_id"]
        if row["role"] != "protected_multichunk":
            continue
        facts = [
            fact
            for fact in multi_by[item_id]["facts"]
            if fact.get("baseline_class") == "OK"
        ]
        protected_facts += len(facts)
        item_regressions: list[str] = []
        stable_item = 0
        for fact in facts:
            control = [
                match_fact(fact.get("valor"), fact.get("texto", ""), answers[(item_id, "control", rep)])[0]
                is True
                for rep in (1, 2)
            ]
            treatment = [
                match_fact(fact.get("valor"), fact.get("texto", ""), answers[(item_id, "treatment", rep)])[0]
                is True
                for rep in (1, 2)
            ]
            if control == [True, True]:
                stable_control_facts += 1
                stable_item += 1
                if treatment != [True, True]:
                    fact_id = str(fact["key"])
                    protected_regressions.append(fact_id)
                    item_regressions.append(fact_id)
        multi_rows.append(
            {
                "item_id": item_id,
                "protected_facts": len(facts),
                "stable_control_facts": stable_item,
                "regression_ids": item_regressions,
            }
        )
    if len(single_rows) != 14 or len(multi_rows) != 35 or protected_facts != 87:
        raise RuntimeError("S216 score population drift")

    checks = {
        "stable_point_gains_gte_4": len(stable_point_gains) >= 4,
        "stable_complete_gains_gte_2": len(stable_complete_gains) >= 2,
        "development_point_regressions_zero": not point_regressions,
        "protected_multichunk_regressions_zero": not protected_regressions,
        "all_87_historical_ok_facts_examined": protected_facts == 87,
        "target_questions_zero": all(row["item_id"] not in TARGETS for row in rows),
    }
    passed = all(checks.values())
    body = {
        "schema": "s216_decomposed_synthesis_screen_v2",
        "status": "GO_TO_DUAL_SEMANTIC_REVIEW" if passed else "NO_GO",
        "population": {
            "questions": 49,
            "single_source_development": 14,
            "protected_multichunk": 35,
            "development_answer_points": 37,
            "historical_ok_facts_examined": protected_facts,
            "stable_contemporary_control_facts": stable_control_facts,
            "target_questions": 0,
        },
        "metrics": {
            "stable_point_gains": len(stable_point_gains),
            "stable_point_gain_ids": stable_point_gains,
            "stable_complete_question_gains": len(stable_complete_gains),
            "stable_complete_gain_ids": stable_complete_gains,
            "development_point_regressions": point_regressions,
            "protected_multichunk_regressions": protected_regressions,
        },
        "checks": checks,
        "single_source_rows": single_rows,
        "protected_multichunk_rows": multi_rows,
        "decision": {
            "dual_semantic_review": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "external_validation": False,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["metrics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
