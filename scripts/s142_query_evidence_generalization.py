#!/usr/bin/env python3
"""Run the frozen S142 query-evidence independent gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.query_evidence_obligations import extract_query_evidence_obligations


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s142_query_evidence_generalization_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s142_query_evidence_generalization_execution_permit_v1.yaml"
DEFAULT_OUT = ROOT / "evals/s142_query_evidence_generalization_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_freeze(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_INDEPENDENT_EXECUTION":
        raise RuntimeError("S142 extractor preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_LOCAL_FINAL":
        raise RuntimeError("S142 independent execution is not permitted")
    for label, spec in {
        **prereg["frozen_implementation"],
        **prereg["sealed_independent"],
    }.items():
        if not isinstance(spec, dict) or "path" not in spec:
            continue
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S142 frozen artifact drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S142 permitted artifact drift: {label}")
    return prereg


def run(prereg: dict[str, Any]) -> dict[str, Any]:
    cohort_spec = prereg["sealed_independent"]["cohort"]
    packet_spec = prereg["sealed_independent"]["source_packet"]
    cohort = json.loads((ROOT / cohort_spec["path"]).read_text(encoding="utf-8"))
    packet = json.loads((ROOT / packet_spec["path"]).read_text(encoding="utf-8"))
    if cohort.get("cohort_sha256") != cohort_spec["cohort_sha256"]:
        raise RuntimeError("S142 sealed cohort identity drift")
    packet_by = {row["item_id"]: row for row in packet["items"]}
    eligible = [row for row in cohort["items"] if row["eligible"]]
    rows = []
    claims_total = 0
    claims_covered = 0
    candidates_total = 0
    candidates_useful = 0
    positive_questions = 0
    deterministic = True
    leakage = 0
    for item in eligible:
        source = packet_by[item["item_id"]]
        chunk = {
            "id": item["item_id"],
            "content": source["excerpt"],
            "source_file": source["filename"],
            "manufacturer": source["manufacturer"],
            "section_title": source["stratum"],
        }
        first = extract_query_evidence_obligations(
            item["question"], [(1, chunk)], max_candidates=3
        )
        second = extract_query_evidence_obligations(
            item["question"], [(1, chunk)], max_candidates=3
        )
        deterministic &= first == second
        spans = []
        for candidate in first:
            if candidate.candidate_id != item["item_id"]:
                leakage += 1
                continue
            if not (
                0 <= candidate.source_start < candidate.source_end <= len(source["excerpt"])
            ):
                leakage += 1
                continue
            spans.append(source["excerpt"][candidate.source_start : candidate.source_end])
        claim_hits = [
            any(claim["exact_quote"] in span for span in spans)
            for claim in item["claims"]
        ]
        candidate_hits = [
            any(claim["exact_quote"] in span for claim in item["claims"])
            for span in spans
        ]
        claims_total += len(claim_hits)
        claims_covered += sum(claim_hits)
        candidates_total += len(candidate_hits)
        candidates_useful += sum(candidate_hits)
        positive_questions += int(bool(spans) and any(claim_hits))
        rows.append(
            {
                "item_id": item["item_id"],
                "question_sha256": hashlib.sha256(item["question"].encode("utf-8")).hexdigest(),
                "claims": len(claim_hits),
                "claims_covered": sum(claim_hits),
                "candidates": len(candidate_hits),
                "useful_candidates": sum(candidate_hits),
                "candidate_receipts": [
                    {
                        "candidate_id": candidate.candidate_id,
                        "source_start": candidate.source_start,
                        "source_end": candidate.source_end,
                        "source_span_sha256": hashlib.sha256(
                            source["excerpt"][candidate.source_start : candidate.source_end].encode("utf-8")
                        ).hexdigest(),
                        "semantic_identity": list(candidate.semantic_identity),
                        "score": candidate.score,
                    }
                    for candidate in first
                ],
            }
        )
    recall = claims_covered / claims_total if claims_total else 0.0
    precision = candidates_useful / candidates_total if candidates_total else 0.0
    gates = prereg["gates"]
    go = (
        recall >= gates["independent_claim_recall_min"]
        and precision >= gates["independent_candidate_precision_min"]
        and positive_questions >= gates["independent_positive_questions_min"]
        and leakage == gates["cross_item_leakage"]
        and deterministic
    )
    body = {
        "instrument": "s142_query_evidence_generalization_v1",
        "status": "GO" if go else "NO_GO",
        "frozen_extractor_sha256": prereg["frozen_implementation"]["extractor"]["sha256"],
        "sealed_cohort_sha256": cohort_spec["cohort_sha256"],
        "result": {
            "eligible_questions": len(eligible),
            "positive_questions": positive_questions,
            "claims_total": claims_total,
            "claims_covered": claims_covered,
            "claim_recall": round(recall, 8),
            "candidates_total": candidates_total,
            "useful_candidates": candidates_useful,
            "candidate_precision": round(precision, 8),
            "cross_item_leakage": leakage,
            "deterministic_two_runs": deterministic,
        },
        "rows": rows,
        "decision": {
            "integrate_versioned_s142_contract": "GO" if go else "NO_GO",
            "paid_answer_probe": "NO_GO_BEFORE_INTEGRATION_REGRESSION",
            "production": "NO_GO",
            "facts_moved_to_ok": 0,
        },
        "cost": {
            "incremental_model_calls": 0,
            "incremental_network_calls": 0,
            "incremental_database_calls": 0,
            "incremental_usd": 0,
            "cohort_authoring_known_usd": cohort["conservative_cost_usd"],
            "prior_unknown_reserve_usd": prereg["resources"]["cohort_authoring_prior_unknown_reserve_usd"],
        },
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    prereg = validate_freeze(args.prereg, args.permit)
    result = run(prereg)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["result"], "incremental_usd": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
