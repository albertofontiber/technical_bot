#!/usr/bin/env python3
"""Score sealed S210 answers only after every model response is checkpointed."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, plan_for
from scripts.s206_score_answer_facet_ab import hp017_cardinality_contradiction
from src.rag.answer_planner import validate_answer_plan
from src.rag.evidence_units_v2 import build_header_aware_evidence_units
from src.rag.omission_correction import point_covered
from src.rag.query_evidence_compiler import stable_sha


PREFLIGHT = ROOT / "evals/s210_query_evidence_compiler_preflight_v1.json"
RECEIPTS = ROOT / "evals/s210_query_evidence_compiler_receipts_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
GUARDRAIL_GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
OUT = ROOT / "evals/s210_query_evidence_compiler_score_v1.json"
TARGETS = ("cat018", "hp002", "hp011", "hp017")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_sealed(value: dict[str, Any]) -> None:
    body = dict(value)
    expected = body.pop("result_sha256")
    if stable_sha(body) != expected:
        raise RuntimeError("S210 sealed artifact hash drift")


def invalid_citations(answer: str, context_rows: int) -> list[int]:
    refs = [int(raw) for raw in re.findall(r"\[F(\d+)\]", answer or "")]
    return sorted({ref for ref in refs if ref < 1 or ref > context_rows})


def _overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return max(left[0], right[0]) < min(left[1], right[1])


def _relation_scores(row: dict[str, Any], call: dict[str, Any]) -> dict[str, Any]:
    obligations = [
        item for item in plan_for(row) if item.kind in TARGET_KINDS[row["qid"]]
    ]
    validation = validate_answer_plan(call["candidate_answer"], obligations)
    validated = {item["obligation_id"]: item for item in validation["rows"]}
    output: dict[str, Any] = {}
    for obligation in obligations:
        support = any(
            evidence["candidate_id"] == obligation.candidate_id
            and int(evidence["fragment_number"]) == obligation.fragment_number
            and _overlaps(
                (int(evidence["source_start"]), int(evidence["source_end"])),
                (obligation.source_start, obligation.source_end),
            )
            for evidence in call["selected_evidence"]
        )
        covered = bool(validated[obligation.obligation_id]["covered"])
        output[obligation.kind] = {
            "covered": covered,
            "source_span_receipt": support,
            "qualified": covered and support,
            "obligation_id": obligation.obligation_id,
            "fragment_number": obligation.fragment_number,
        }
    return output


def _useful_guardrail_receipt(
    receipt: dict[str, Any], useful_spans: set[tuple[int, int]]
) -> bool:
    observed = (int(receipt["source_start"]), int(receipt["source_end"]))
    return any(_overlaps(observed, span) for span in useful_spans)


def main() -> int:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    _assert_sealed(preflight)
    _assert_sealed(receipts)
    if receipts.get("status") != "COMPLETE" or receipts.get("calls") != 202:
        raise RuntimeError("S210 receipts incomplete")
    if receipts.get("preflight_sha256") != file_sha(PREFLIGHT):
        raise RuntimeError("S210 receipts/preflight mismatch")

    cohort = {str(row["qid"]): row for row in preflight["rows"]}
    calls: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for call in receipts["rows"]:
        calls[call["qid"]][int(call["replicate"])] = call
    if set(calls) != set(cohort) or any(set(reps) != {1, 2} for reps in calls.values()):
        raise RuntimeError("S210 two-replicate answer matrix incomplete")

    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    residual_keys = {
        (str(row["qid"]), str(row["kind"]))
        for row in residual["rows"]
        if not row["covered"]
    }
    prior_covered = {
        (str(row["qid"]), str(row["kind"]))
        for row in residual["rows"]
        if row["covered"]
    }
    relation_rows = []
    stable_gains = protected_regressions = hp017_gains = 0
    invalid_calls = []
    prefix_failures = []
    appendix_chars = []

    for qid in TARGETS:
        scores = {
            replicate: _relation_scores(cohort[qid], calls[qid][replicate])
            for replicate in (1, 2)
        }
        for kind in sorted(TARGET_KINDS[qid]):
            qualified = [scores[replicate][kind]["qualified"] for replicate in (1, 2)]
            stable_gain = (qid, kind) in residual_keys and all(qualified)
            regression = (qid, kind) in prior_covered and not all(
                scores[replicate][kind]["covered"] for replicate in (1, 2)
            )
            stable_gains += int(stable_gain)
            hp017_gains += int(qid == "hp017" and stable_gain)
            protected_regressions += int(regression)
            relation_rows.append(
                {
                    "qid": qid,
                    "kind": kind,
                    "qualified": qualified,
                    "stable_gain": stable_gain,
                    "protected_relation": (qid, kind) in prior_covered,
                    "regression": regression,
                    "receipts": [scores[replicate][kind] for replicate in (1, 2)],
                }
            )
        for replicate in (1, 2):
            call = calls[qid][replicate]
            expected_prefix = cohort[qid]["baseline_answer"] + "\n\n---\n\n"
            if not call["candidate_answer"].startswith(expected_prefix):
                prefix_failures.append(f"{qid}:r{replicate}")
            bad = invalid_citations(call["candidate_answer"], cohort[qid]["context_rows"])
            if bad:
                invalid_calls.append({"call_id": f"{qid}:r{replicate}", "refs": bad})
            appendix_chars.append(int(call["appendix_chars"]))

    gold = {
        str(item["item_id"]): item
        for item in json.loads(GUARDRAIL_GOLD.read_text(encoding="utf-8"))["items"]
        if item.get("eligible")
    }
    guardrail_rows = []
    point_regressions = 0
    point_gains = 0
    selected_evidence = useful_evidence = 0
    for qid, row in cohort.items():
        if row["role"] != "independent_guardrail":
            continue
        item = gold[qid]
        units = build_header_aware_evidence_units(
            row["context"][0]["content"], fragment_number=1, candidate_id=qid
        )
        by_id = {unit.unit_id: unit for unit in units}
        useful_unit_ids = {
            unit_id
            for point in item["answer_points"]
            for unit_id in point["support_unit_ids"]
        }
        useful_spans = {
            span for unit_id in useful_unit_ids for span in by_id[unit_id].source_spans
        }
        point_rows = []
        for point in item["answer_points"]:
            before = point_covered(row["baseline_answer"], point)
            after = [
                point_covered(calls[qid][replicate]["candidate_answer"], point)
                for replicate in (1, 2)
            ]
            regression = before and not all(after)
            stable_gain = not before and all(after)
            point_regressions += int(regression)
            point_gains += int(stable_gain)
            point_rows.append(
                {
                    "claim": point["claim"],
                    "baseline": before,
                    "candidate": after,
                    "stable_gain": stable_gain,
                    "regression": regression,
                }
            )
        for replicate in (1, 2):
            call = calls[qid][replicate]
            expected_prefix = row["baseline_answer"] + "\n\n---\n\n"
            if not call["candidate_answer"].startswith(expected_prefix):
                prefix_failures.append(f"{qid}:r{replicate}")
            bad = invalid_citations(call["candidate_answer"], row["context_rows"])
            if bad:
                invalid_calls.append({"call_id": f"{qid}:r{replicate}", "refs": bad})
            appendix_chars.append(int(call["appendix_chars"]))
            selected_evidence += len(call["selected_evidence"])
            useful_evidence += sum(
                _useful_guardrail_receipt(receipt, useful_spans)
                for receipt in call["selected_evidence"]
            )
        guardrail_rows.append({"qid": qid, "points": point_rows})

    evidence_precision = useful_evidence / selected_evidence if selected_evidence else 0.0
    mean_appendix_chars = sum(appendix_chars) / len(appendix_chars)
    baseline_cardinality_contradiction = hp017_cardinality_contradiction(
        cohort["hp017"]["baseline_answer"]
    )
    candidate_cardinality_contradictions = [
        hp017_cardinality_contradiction(calls["hp017"][replicate]["candidate_answer"])
        for replicate in (1, 2)
    ]
    new_cardinality_contradictions = sum(
        observed and not baseline_cardinality_contradiction
        for observed in candidate_cardinality_contradictions
    )
    cost = float(receipts["cost"]["estimated_usd"])
    ceiling = float(receipts["cost"]["budget_ceiling_usd"])
    checks = {
        "stable_residual_relation_gains_gte_11": stable_gains >= 11,
        "stable_hp017_relation_gains_gte_4": hp017_gains >= 4,
        "previously_covered_target_regressions_zero": protected_regressions == 0,
        "new_cardinality_contradictions_zero": new_cardinality_contradictions == 0,
        "guardrail_point_regressions_zero": point_regressions == 0,
        "selected_evidence_precision_gte_0_70": evidence_precision >= 0.70,
        "baseline_prefix_failures_zero": not prefix_failures,
        "invalid_citations_zero": not invalid_calls,
        "mean_appendix_chars_lte_5000": mean_appendix_chars <= 5_000,
        "actual_cost_below_ceiling": cost < ceiling,
    }
    local_go = all(checks.values())
    body = {
        "schema": "s210_query_evidence_compiler_score_v1",
        "status": "LOCAL_GO_PENDING_FRONTIER_ATOMIC_REVIEW" if local_go else "NO_GO",
        "inputs": {
            "preflight_sha256": file_sha(PREFLIGHT),
            "receipts_sha256": file_sha(RECEIPTS),
            "residual_sha256": file_sha(RESIDUAL),
            "guardrail_gold_sha256": file_sha(GUARDRAIL_GOLD),
        },
        "metrics": {
            "stable_residual_relation_gains": stable_gains,
            "stable_hp017_relation_gains": hp017_gains,
            "previously_covered_target_regressions": protected_regressions,
            "baseline_cardinality_contradiction": baseline_cardinality_contradiction,
            "candidate_cardinality_contradictions": candidate_cardinality_contradictions,
            "new_cardinality_contradictions": new_cardinality_contradictions,
            "guardrail_point_gains": point_gains,
            "guardrail_point_regressions": point_regressions,
            "selected_evidence": selected_evidence,
            "useful_selected_evidence": useful_evidence,
            "selected_evidence_precision": round(evidence_precision, 8),
            "mean_appendix_chars": round(mean_appendix_chars, 2),
            "max_appendix_chars": max(appendix_chars),
            "invalid_citation_calls": len(invalid_calls),
            "baseline_prefix_failures": len(prefix_failures),
        },
        "relation_rows": relation_rows,
        "guardrail_rows": guardrail_rows,
        "invalid_citations": invalid_calls,
        "prefix_failures": prefix_failures,
        "checks": checks,
        "relation_proxy_projection": {
            "canonical_facts_ok_before": 143,
            "stable_relation_gains": stable_gains,
            "canonical_facts_ok_after": None,
            "claim_98_percent_allowed": False,
            "reason": "Fact credit requires the sealed Sol xhigh and Fable atomic result review.",
        },
        "cost": receipts["cost"],
        "decision": {
            "frontier_atomic_review": local_go,
            "same_cohort_retry": False,
            "prompt_or_threshold_tuning": False,
            "runtime_integration": False,
            "production_default": "off",
            "facts_moved_to_ok": 0,
            "next": (
                "RUN_ONE_SEALED_SOL_XHIGH_PLUS_FABLE_ATOMIC_RESULT_REVIEW"
                if local_go
                else "CLOSE_S210_WITHOUT_ITERATION"
            ),
        },
        "invariants": {
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "metrics": body["metrics"]}))
    return 0 if local_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
