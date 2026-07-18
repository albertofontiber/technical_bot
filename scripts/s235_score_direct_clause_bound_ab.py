#!/usr/bin/env python3
"""Open S235 score inputs only after generation is complete and score both arms."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s201_real_question_planner_gate import (  # noqa: E402
    frozen_conflicts,
    frozen_obligations,
)
from src.rag.answer_planner import (  # noqa: E402
    AnswerObligation,
    validate_answer_conflicts,
    validate_answer_plan,
)
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json  # noqa: E402

GENERATION = ROOT / "evals/s235_direct_clause_bound_generation_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
OUT = ROOT / "evals/s235_direct_clause_bound_ab_result_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _covered_ids(answer: str, obligations: list[AnswerObligation]) -> set[str]:
    result = validate_answer_plan(answer, obligations)
    return {str(row["obligation_id"]) for row in result["rows"] if row["covered"]}


def _unsafe_ids(answer: str, item: dict[str, Any]) -> set[str]:
    return {
        str(row["conflict_id"])
        for row in validate_answer_conflicts(answer, frozen_conflicts(item))["unsafe"]
    }


def _arm_score(
    answer: str,
    obligations: list[AnswerObligation],
    item: dict[str, Any],
) -> dict[str, Any]:
    covered = _covered_ids(answer, obligations)
    return {
        "covered_obligation_ids": sorted(covered),
        "covered": len(covered),
        "unsafe_conflict_ids": sorted(_unsafe_ids(answer, item)),
        "invalid_citations": invalid_citations(answer, int(item["fragment_count"])),
    }


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S235 score already exists")
    generation = _sealed(GENERATION)
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or tuple(item["qid"] for item in generation.get("items") or []) != QIDS
    ):
        raise ValueError("S235 generation is incomplete or score isolation drifted")
    score = _sealed(SCORE)
    if score.get("status") != "SEALED_SCORE_ONLY_OPEN_AFTER_GENERATION":
        raise ValueError("S235 score packet status drift")
    score_by_qid = {str(item["qid"]): item for item in score["items"]}

    rows = []
    all_residual_ids: set[str] = set()
    causal_gains: set[str] = set()
    stable_treatment_residuals: set[str] = set()
    stable_baseline_residuals: set[str] = set()
    protected_regressions: set[str] = set()
    treatment_unsafe: set[str] = set()
    treatment_invalid: dict[str, list[list[int]]] = {}
    for generated in generation["items"]:
        qid = str(generated["qid"])
        item = score_by_qid[qid]
        obligations = frozen_obligations(item)
        residual = set(map(str, item["residual_obligation_ids"]))
        all_residual_ids.update(residual)
        canonical = _arm_score(item["canonical_answer"], obligations, item)
        canonical_covered = set(canonical["covered_obligation_ids"])
        baseline_rows = [
            _arm_score(replica["baseline_answer"], obligations, item)
            for replica in generated["replicas"]
        ]
        treatment_rows = [
            _arm_score(replica["treatment_answer"], obligations, item)
            for replica in generated["replicas"]
        ]
        baseline_sets = [set(row["covered_obligation_ids"]) for row in baseline_rows]
        treatment_sets = [set(row["covered_obligation_ids"]) for row in treatment_rows]
        stable_baseline = residual & set.intersection(*baseline_sets)
        stable_treatment = residual & set.intersection(*treatment_sets)
        never_baseline = residual - set.union(*baseline_sets)
        causal = stable_treatment & never_baseline
        regressions = canonical_covered - set.intersection(*treatment_sets)
        stable_baseline_residuals.update(stable_baseline)
        stable_treatment_residuals.update(stable_treatment)
        causal_gains.update(causal)
        protected_regressions.update(regressions)
        for row in treatment_rows:
            treatment_unsafe.update(row["unsafe_conflict_ids"])
        invalid = [row["invalid_citations"] for row in treatment_rows]
        if any(invalid):
            treatment_invalid[qid] = invalid
        rows.append(
            {
                "qid": qid,
                "canonical": canonical,
                "baseline_replicates": baseline_rows,
                "treatment_replicates": treatment_rows,
                "stable_baseline_residual_ids": sorted(stable_baseline),
                "stable_treatment_residual_ids": sorted(stable_treatment),
                "causal_gain_ids": sorted(causal),
                "protected_regression_ids": sorted(regressions),
            }
        )

    if len(all_residual_ids) != 12:
        raise ValueError("S235 scored residual population is not twelve")
    checks = {
        "stable_treatment_beats_stable_baseline": len(stable_treatment_residuals)
        > len(stable_baseline_residuals),
        "at_least_one_strict_causal_gain": bool(causal_gains),
        "protected_regressions_zero": not protected_regressions,
        "treatment_unsafe_conflicts_zero": not treatment_unsafe,
        "treatment_invalid_citations_zero": not treatment_invalid,
        "actual_cost_below_25": float(generation["actual_cost_usd"]) < 25,
    }
    passed = all(checks.values())
    projected_ok = 143 + len(stable_treatment_residuals)
    reaches_98 = projected_ok >= 154
    body = {
        "status": "GO_FRONTIER_SEMANTIC_ADJUDICATION" if passed else "NO_GO_S235_DIRECT_AB",
        "metrics": {
            "canonical_facts_ok": 143,
            "denominator": 157,
            "stable_baseline_residuals": sorted(stable_baseline_residuals),
            "stable_treatment_residuals": sorted(stable_treatment_residuals),
            "strict_causal_gain_ids": sorted(causal_gains),
            "protected_regression_ids": sorted(protected_regressions),
            "treatment_unsafe_conflict_ids": sorted(treatment_unsafe),
            "treatment_invalid_citations": treatment_invalid,
            "projected_facts_ok_before_semantic_review": projected_ok,
            "projected_percent_before_semantic_review": round(100 * projected_ok / 157, 2),
            "projected_reaches_98": reaches_98,
            "actual_cost_usd": generation["actual_cost_usd"],
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "official_fact_credit": 0,
            "production_default_changed": False,
            "next": "one_shot_sol_fable_semantic_review" if passed else "close_or_redesign_from_observed_stage",
        },
        "invariants": {
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(OUT, sealed_artifact("s235_direct_clause_bound_ab_result_v1", body))
    print(
        json.dumps(
            {
                "status": body["status"],
                "stable_baseline": len(stable_baseline_residuals),
                "stable_treatment": len(stable_treatment_residuals),
                "strict_causal": len(causal_gains),
                "projected_ok": projected_ok,
                "reaches_98": reaches_98,
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
