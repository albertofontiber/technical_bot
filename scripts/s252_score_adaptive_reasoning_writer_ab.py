#!/usr/bin/env python3
"""Score S252 only through its post-generation hash-bound permit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from scripts import s251_score_adaptive_reasoning_writer_ab as scoring
from scripts.s201_real_question_planner_gate import frozen_obligations
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s252_adaptive_reasoning_writer_ab_prereg_v1.yaml"
PERMIT = ROOT / "evals/s252_adaptive_reasoning_writer_score_execution_permit_v1.json"
GENERATION = ROOT / "evals/s252_adaptive_reasoning_writer_generation_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
OUT = ROOT / "evals/s252_adaptive_reasoning_writer_ab_result_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _verify_frozen_boundary() -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_AFTER_DUAL_FRONTIER_PASS":
        raise ValueError("S252 preregistration is not scoring-frozen")
    permit = _sealed(PERMIT)
    if permit.get("status") != "SCORE_EXECUTION_GO_POST_GENERATION_BOUND":
        raise ValueError("S252 score execution permit absent")
    if permit.get("frozen_scoring_inputs") != prereg["frozen_scoring_inputs"]:
        raise ValueError("S252 score permit/prereg input mismatch")
    for label, spec in permit["frozen_scoring_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S252 score input drift: {label}")
    generation_spec = permit["generation"]
    if generation_spec["path"] != GENERATION.relative_to(ROOT).as_posix():
        raise ValueError("S252 generation permit path mismatch")
    if _sha(GENERATION) != generation_spec["sha256"]:
        raise ValueError("S252 generation changed after score permit")
    return _sealed(GENERATION), _sealed(SCORE)


def _replicas(generated: dict[str, Any]) -> list[dict[str, Any]]:
    replicas = generated.get("replicas")
    if not isinstance(replicas, list) or len(replicas) != 2:
        raise ValueError("S252 requires exactly two replicas")
    if {row.get("replicate") for row in replicas} != {1, 2}:
        raise ValueError("S252 replica identities must be exactly 1 and 2")
    for row in replicas:
        for field in ("baseline_answer", "treatment_answer"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"S252 missing non-empty {field}")
    return sorted(replicas, key=lambda row: int(row["replicate"]))


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S252 score already exists")
    generation, score_packet = _verify_frozen_boundary()
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or tuple(row.get("qid") for row in generation.get("items") or []) != QIDS
        or score_packet.get("status") != "SEALED_SCORE_ONLY_OPEN_AFTER_GENERATION"
    ):
        raise ValueError("S252 generation or score packet invariant failed")
    score_by_qid = {str(row["qid"]): row for row in score_packet["items"]}
    rows = []
    all_residuals: set[str] = set()
    stable_control: set[str] = set()
    stable_treatment: set[str] = set()
    observed_gains: set[str] = set()
    regressions: set[str] = set()
    unsafe: set[str] = set()
    invalid: dict[str, list[list[int]]] = {}
    for generated in generation["items"]:
        qid = str(generated["qid"])
        item = score_by_qid[qid]
        obligations = frozen_obligations(item)
        residuals = set(map(str, item["residual_obligation_ids"]))
        all_residuals.update(residuals)
        canonical = scoring._arm(item["canonical_answer"], obligations, item)
        replicas = _replicas(generated)
        controls = [scoring._arm(row["baseline_answer"], obligations, item) for row in replicas]
        treatments = [scoring._arm(row["treatment_answer"], obligations, item) for row in replicas]
        control_sets = [set(row["covered_obligation_ids"]) for row in controls]
        treatment_sets = [set(row["covered_obligation_ids"]) for row in treatments]
        q_control = residuals & set.intersection(*control_sets)
        q_treatment = residuals & set.intersection(*treatment_sets)
        q_observed = q_treatment & (residuals - set.union(*control_sets))
        q_regressions = set(canonical["covered_obligation_ids"]) - set.intersection(*treatment_sets)
        stable_control.update(q_control)
        stable_treatment.update(q_treatment)
        observed_gains.update(q_observed)
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
            "stable_observed_gain_ids": sorted(q_observed),
            "protected_regression_ids": sorted(q_regressions),
        })
    if len(all_residuals) != 12:
        raise ValueError("S252 residual population drift")
    checks = {
        "stable_treatment_beats_control": len(stable_treatment) > len(stable_control),
        "stable_observed_gains_min_2": len(observed_gains) >= 2,
        "protected_regressions_zero": not regressions,
        "unsafe_conflicts_zero": not unsafe,
        "invalid_citations_zero": not invalid,
        "observed_response_usage_below_15": float(generation["actual_cost_usd"]) < 15,
    }
    passed = all(checks.values())
    body = {
        "status": "GO_FULL_ANSWER_DUAL_SEMANTIC_REVIEW" if passed else "NO_GO_CLOSE_S252",
        "metrics": {
            "canonical_facts_ok": 143, "denominator": 157,
            "stable_control_residual_ids": sorted(stable_control),
            "stable_treatment_residual_ids": sorted(stable_treatment),
            "stable_observed_gain_ids": sorted(observed_gains),
            "protected_regression_ids": sorted(regressions),
            "treatment_unsafe_conflict_ids": sorted(unsafe),
            "treatment_invalid_citations": invalid,
            "projected_facts_ok_before_semantic_review": 143 + len(stable_treatment),
            "observed_response_usage_cost_usd": generation["actual_cost_usd"],
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "official_fact_credit": 0,
            "production_default_changed": False,
            "same_target_tuning": False,
            "full_treatment_answers_must_be_reviewed": passed,
            "next": "one_shot_full_answer_sol_fable_review" if passed else "close_without_tuning",
        },
        "invariants": {
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(OUT, sealed_artifact("s252_adaptive_reasoning_writer_ab_result_v1", body))
    print(json.dumps({
        "status": body["status"], "stable_control": len(stable_control),
        "stable_treatment": len(stable_treatment),
        "stable_observed_gains": len(observed_gains),
    }, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

