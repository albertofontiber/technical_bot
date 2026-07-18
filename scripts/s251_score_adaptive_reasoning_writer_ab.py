#!/usr/bin/env python3
"""Score S251 after the complete generation checkpoint is sealed."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.s201_real_question_planner_gate import frozen_conflicts, frozen_obligations
from src.rag.answer_planner import AnswerObligation, validate_answer_conflicts, validate_answer_plan
from src.rag.omission_correction import invalid_citations
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json

ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "evals/s251_adaptive_reasoning_writer_generation_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
OUT = ROOT / "evals/s251_adaptive_reasoning_writer_ab_result_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _covered(answer: str, obligations: list[AnswerObligation]) -> set[str]:
    result = validate_answer_plan(answer, obligations)
    return {str(row["obligation_id"]) for row in result["rows"] if row["covered"]}


def _arm(answer: str, obligations: list[AnswerObligation], item: dict[str, Any]) -> dict[str, Any]:
    covered = _covered(answer, obligations)
    unsafe = validate_answer_conflicts(answer, frozen_conflicts(item))["unsafe"]
    return {
        "covered_obligation_ids": sorted(covered),
        "covered": len(covered),
        "unsafe_conflict_ids": sorted(str(row["conflict_id"]) for row in unsafe),
        "invalid_citations": invalid_citations(answer, int(item["fragment_count"])),
    }


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S251 score already exists")
    generation = _sealed(GENERATION)
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or tuple(row["qid"] for row in generation["items"]) != QIDS
    ):
        raise ValueError("S251 generation is incomplete")
    score = _sealed(SCORE)
    score_by_qid = {str(row["qid"]): row for row in score["items"]}
    rows = []
    all_residuals: set[str] = set()
    stable_control: set[str] = set()
    stable_treatment: set[str] = set()
    strict_gains: set[str] = set()
    regressions: set[str] = set()
    unsafe: set[str] = set()
    invalid: dict[str, list[list[int]]] = {}
    for generated in generation["items"]:
        qid = str(generated["qid"])
        item = score_by_qid[qid]
        obligations = frozen_obligations(item)
        residuals = set(map(str, item["residual_obligation_ids"]))
        all_residuals.update(residuals)
        canonical = _arm(item["canonical_answer"], obligations, item)
        controls = [_arm(row["baseline_answer"], obligations, item) for row in generated["replicas"]]
        treatments = [_arm(row["treatment_answer"], obligations, item) for row in generated["replicas"]]
        control_sets = [set(row["covered_obligation_ids"]) for row in controls]
        treatment_sets = [set(row["covered_obligation_ids"]) for row in treatments]
        q_control = residuals & set.intersection(*control_sets)
        q_treatment = residuals & set.intersection(*treatment_sets)
        q_gains = q_treatment & (residuals - set.union(*control_sets))
        q_regressions = set(canonical["covered_obligation_ids"]) - set.intersection(*treatment_sets)
        stable_control.update(q_control)
        stable_treatment.update(q_treatment)
        strict_gains.update(q_gains)
        regressions.update(q_regressions)
        for result in treatments:
            unsafe.update(result["unsafe_conflict_ids"])
        invalid_rows = [result["invalid_citations"] for result in treatments]
        if any(invalid_rows):
            invalid[qid] = invalid_rows
        rows.append({
            "qid": qid, "canonical": canonical,
            "control_replicates": controls, "treatment_replicates": treatments,
            "stable_control_residual_ids": sorted(q_control),
            "stable_treatment_residual_ids": sorted(q_treatment),
            "strict_causal_gain_ids": sorted(q_gains),
            "protected_regression_ids": sorted(q_regressions),
        })
    if len(all_residuals) != 12:
        raise ValueError("S251 residual population drift")
    checks = {
        "stable_treatment_beats_control": len(stable_treatment) > len(stable_control),
        "strict_causal_gains_min_2": len(strict_gains) >= 2,
        "protected_regressions_zero": not regressions,
        "unsafe_conflicts_zero": not unsafe,
        "invalid_citations_zero": not invalid,
        "actual_cost_below_15": float(generation["actual_cost_usd"]) < 15,
    }
    passed = all(checks.values())
    body = {
        "status": "GO_FRONTIER_SEMANTIC_REVIEW" if passed else "NO_GO_CLOSE_S251",
        "metrics": {
            "canonical_facts_ok": 143, "denominator": 157,
            "stable_control_residual_ids": sorted(stable_control),
            "stable_treatment_residual_ids": sorted(stable_treatment),
            "strict_causal_gain_ids": sorted(strict_gains),
            "protected_regression_ids": sorted(regressions),
            "treatment_unsafe_conflict_ids": sorted(unsafe),
            "treatment_invalid_citations": invalid,
            "projected_facts_ok_before_semantic_review": 143 + len(stable_treatment),
            "actual_cost_usd": generation["actual_cost_usd"],
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "official_fact_credit": 0,
            "production_default_changed": False,
            "same_target_tuning": False,
            "next": "one_shot_sol_fable_semantic_review" if passed else "close_without_tuning",
        },
        "invariants": {
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(OUT, sealed_artifact("s251_adaptive_reasoning_writer_ab_result_v1", body))
    print(json.dumps({
        "status": body["status"], "stable_control": len(stable_control),
        "stable_treatment": len(stable_treatment), "strict_gains": len(strict_gains),
    }, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

