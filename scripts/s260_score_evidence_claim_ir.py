#!/usr/bin/env python3
"""Score S260 only after the complete generation artifact is sealed."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
import hashlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s201_real_question_planner_gate import frozen_conflicts, frozen_obligations
from src.rag.answer_planner import validate_answer_conflicts, validate_answer_plan
from src.rag.omission_correction import invalid_citations
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json


GENERATION = ROOT / "evals/s260_evidence_claim_ir_generation_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
TAXONOMY = ROOT / "evals/s243_synthesis_miss_causal_taxonomy_v1.yaml"
OUT = ROOT / "evals/s260_evidence_claim_ir_result_v1.json"
PREREG = ROOT / "evals/s260_evidence_claim_ir_prereg_v1.yaml"
EXECUTION_PERMIT = ROOT / "evals/s260_evidence_claim_ir_execution_permit_v1.yaml"
SCORE_PERMIT = ROOT / "evals/s260_evidence_claim_ir_score_execution_permit_v1.yaml"
LEDGER = ROOT / "evals/s260_evidence_claim_ir_call_ledger_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_score_authorization() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    execution = yaml.safe_load(EXECUTION_PERMIT.read_text(encoding="utf-8"))
    permit = yaml.safe_load(SCORE_PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_AFTER_DUAL_FRONTIER_PASS":
        raise RuntimeError("S260 preregistration is not frozen")
    if execution.get("status") != "EXECUTION_GO_PAID_BOUNDED_NO_RETRY":
        raise RuntimeError("S260 execution permit is invalid")
    if permit.get("status") != "SCORE_EXECUTION_GO_FROZEN_AFTER_GENERATION":
        raise RuntimeError("S260 score permit is invalid")
    expected = {
        "prereg": PREREG,
        "execution_permit": EXECUTION_PERMIT,
        "generation": GENERATION,
        "call_ledger": LEDGER,
    }
    for key, path in expected.items():
        spec = permit[key]
        if spec["path"] != path.relative_to(ROOT).as_posix() or spec["sha256"] != _file_sha(path):
            raise RuntimeError(f"S260 score authorization drift: {key}")
    if execution["frozen_artifacts"]["prereg"]["sha256"] != _file_sha(PREREG):
        raise RuntimeError("S260 preregistration is not bound by execution permit")
    if permit["frozen_scoring_inputs"] != prereg["frozen_scoring_inputs"]:
        raise RuntimeError("S260 scoring manifest drift")
    for spec in prereg["frozen_scoring_inputs"].values():
        if _file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S260 scoring input drift: {spec['path']}")


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _score_answer(answer: str, item: dict[str, Any]) -> dict[str, Any]:
    obligations = frozen_obligations(item)
    plan = validate_answer_plan(answer, obligations)
    covered = {
        str(row["obligation_id"])
        for row in plan["rows"]
        if row["covered"]
    }
    unsafe = {
        str(row["conflict_id"])
        for row in validate_answer_conflicts(answer, frozen_conflicts(item))["unsafe"]
    }
    return {
        "covered_obligation_ids": sorted(covered),
        "unsafe_conflict_ids": sorted(unsafe),
        "invalid_citations": invalid_citations(answer, int(item["fragment_count"])),
        "answer_chars": len(answer),
    }


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S260 score already exists")
    _validate_score_authorization()
    generation = _sealed(GENERATION)
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or tuple(item.get("qid") for item in generation.get("items") or []) != QIDS
        or any(len(item.get("replicas") or []) != 2 for item in generation["items"])
    ):
        raise ValueError("S260 generation is incomplete")
    score = _sealed(SCORE)
    score_by_qid = {str(item["qid"]): item for item in score["items"]}
    taxonomy = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    family_by_id = {
        str(row["obligation_id"]): str(row["family"])
        for row in taxonomy["rows"]
    }

    stable_residuals: set[str] = set()
    protected_regressions: set[str] = set()
    unsafe_conflicts: set[str] = set()
    invalid: dict[str, list[list[int]]] = {}
    rows = []
    for generated in generation["items"]:
        qid = str(generated["qid"])
        item = score_by_qid[qid]
        canonical = _score_answer(item["canonical_answer"], item)
        canonical_covered = set(canonical["covered_obligation_ids"])
        replica_scores = [
            _score_answer(replica["answer"], item)
            for replica in generated["replicas"]
        ]
        replica_sets = [set(row["covered_obligation_ids"]) for row in replica_scores]
        stable = set(map(str, item["residual_obligation_ids"])) & set.intersection(
            *replica_sets
        )
        regressions = canonical_covered - set.intersection(*replica_sets)
        stable_residuals.update(stable)
        protected_regressions.update(regressions)
        for row in replica_scores:
            unsafe_conflicts.update(row["unsafe_conflict_ids"])
        bad = [row["invalid_citations"] for row in replica_scores]
        if any(bad):
            invalid[qid] = bad
        rows.append(
            {
                "qid": qid,
                "canonical": canonical,
                "replicas": replica_scores,
                "stable_residual_ids": sorted(stable),
                "protected_regression_ids": sorted(regressions),
            }
        )

    stable_by_family: dict[str, list[str]] = {}
    for obligation_id in sorted(stable_residuals):
        stable_by_family.setdefault(family_by_id[obligation_id], []).append(obligation_id)
    compound = stable_by_family.get("compound_relation_qualifier_loss", [])
    checks = {
        "all_eight_calls_complete": all(
            len(item["replicas"]) == 2 for item in generation["items"]
        ),
        "stable_residual_gains_gte_3": len(stable_residuals) >= 3,
        "stable_compound_relation_gains_gte_2": len(compound) >= 2,
        "protected_regressions_zero": not protected_regressions,
        "unsafe_conflicts_zero": not unsafe_conflicts,
        "invalid_citations_zero": not invalid,
        "actual_cost_below_5": float(generation["actual_cost_usd"]) < 5,
    }
    passed = all(checks.values())
    projected_ok = 143 + len(stable_residuals)
    body = {
        "status": "GO_TO_DUAL_FRONTIER_RESULT_REVIEW" if passed else "NO_GO_S260_ANSWER_IR",
        "metrics": {
            "canonical_facts_ok": 143,
            "denominator": 157,
            "stable_residual_ids": sorted(stable_residuals),
            "stable_residuals_by_family": stable_by_family,
            "protected_regression_ids": sorted(protected_regressions),
            "unsafe_conflict_ids": sorted(unsafe_conflicts),
            "invalid_citations": invalid,
            "projected_facts_ok_before_semantic_review": projected_ok,
            "projected_percent_before_semantic_review": round(100 * projected_ok / 157, 2),
            "projected_reaches_98": projected_ok >= 154,
            "actual_cost_usd": generation["actual_cost_usd"],
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "official_fact_credit": 0,
            "production_default_changed": False,
            "next": (
                "one_shot_blind_sol_fable_full_answer_review"
                if passed
                else "close_without_tuning_or_successor_correction_loop"
            ),
        },
        "limitations": {
            "independent_efficacy_validation": False,
            "target_screen_one_shot": True,
        },
        "invariants": {
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(OUT, sealed_artifact("s260_evidence_claim_ir_result_v1", body))
    print(
        json.dumps(
            {
                "status": body["status"],
                "stable_gains": len(stable_residuals),
                "compound_gains": len(compound),
                "regressions": len(protected_regressions),
                "projected_ok": projected_ok,
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
