#!/usr/bin/env python3
"""Reconstruct the sealed S212 residual funnel from raw claims to final answer."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, plan_for  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402
from src.rag.query_evidence_compiler_v3 import validate_claim_response  # noqa: E402
from src.rag.query_evidence_compiler import (  # noqa: E402
    deterministic_fallback_candidates,
    merge_candidate_pool,
)


PREFLIGHT = ROOT / "evals/s212_query_evidence_compiler_preflight_v1.json"
PARTIAL = ROOT / "evals/s212_query_evidence_compiler_calls_v1.partial.jsonl"
RECEIPTS = ROOT / "evals/s212_query_evidence_compiler_receipts_v1.json"
SCORE = ROOT / "evals/s212_query_evidence_compiler_score_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
OUT = ROOT / "evals/s212_query_evidence_compiler_relation_funnel_v1.json"


def _sealed(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    if stable_sha(body) != expected:
        raise RuntimeError(f"sealed artifact drift: {path.name}")
    return value


def _overlaps(left, right) -> bool:
    return max(int(left[0]), int(right[0])) < min(int(left[1]), int(right[1]))


def _has_span(candidates, obligation) -> bool:
    return any(
        row.candidate_id == obligation.candidate_id
        and row.fragment_number == obligation.fragment_number
        and _overlaps(
            (row.source_start, row.source_end),
            (obligation.source_start, obligation.source_end),
        )
        for row in candidates
    )


def _selected_has_span(receipts, obligation) -> bool:
    return any(
        row["candidate_id"] == obligation.candidate_id
        and int(row["fragment_number"]) == obligation.fragment_number
        and _overlaps(
            (row["source_start"], row["source_end"]),
            (obligation.source_start, obligation.source_end),
        )
        for row in receipts
    )


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S212 relation funnel already exists")
    preflight = _sealed(PREFLIGHT)
    receipts = _sealed(RECEIPTS)
    score = _sealed(SCORE)
    cohort = {row["qid"]: row for row in preflight["rows"]}
    answers = {
        (row["qid"], int(row["replicate"])): row for row in receipts["rows"]
    }
    score_rows = {(row["qid"], row["kind"]): row for row in score["relation_rows"]}
    residual_keys = {
        (row["qid"], row["kind"])
        for row in json.loads(RESIDUAL.read_text(encoding="utf-8"))["rows"]
        if not row["covered"]
    }

    raw_claims = defaultdict(dict)
    calls = [
        json.loads(line)
        for line in PARTIAL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(calls) != 202:
        raise RuntimeError("S212 raw call journal is incomplete")
    pattern = re.compile(r"^(?P<qid>.+):r(?P<rep>[12]):extract:f(?P<fragment>\d+)$")
    for call in calls:
        if call["role"] != "extractor":
            continue
        match = pattern.match(call["call_id"])
        if not match:
            raise RuntimeError("S212 extractor call identity drift")
        raw_claims[(match.group("qid"), int(match.group("rep")))][
            int(match.group("fragment"))
        ] = json.loads(call["raw_output"])

    relation_rows = []
    classifications = Counter()
    stable_stage_counts = Counter()
    for qid in ("cat018", "hp002", "hp011", "hp017"):
        row = cohort[qid]
        obligations = {
            item.kind: item
            for item in plan_for(row)
            if item.kind in TARGET_KINDS[qid]
        }
        for kind in sorted(TARGET_KINDS[qid]):
            if (qid, kind) not in residual_keys:
                continue
            obligation = obligations[kind]
            replicas = []
            for replicate in (1, 2):
                model = []
                for fragment_number, chunk in enumerate(row["context"], 1):
                    bound, _ = validate_claim_response(
                        raw_claims[(qid, replicate)][fragment_number],
                        chunk=chunk,
                        fragment_number=fragment_number,
                    )
                    model.extend(bound)
                fallback = deterministic_fallback_candidates(
                    row["question"], row["context"], max_candidates=12
                )
                pool = merge_candidate_pool(model, fallback)
                selected = answers[(qid, replicate)]["selected_evidence"]
                scored = score_rows[(qid, kind)]["receipts"][replicate - 1]
                replicas.append(
                    {
                        "replicate": replicate,
                        "model_exact_claim_span": _has_span(model, obligation),
                        "deterministic_fallback_span": _has_span(fallback, obligation),
                        "candidate_pool_span": _has_span(pool, obligation),
                        "selected_span": _selected_has_span(selected, obligation),
                        "answer_covered": bool(scored["covered"]),
                        "qualified": bool(scored["qualified"]),
                    }
                )
            stable = {
                key: all(replica[key] for replica in replicas)
                for key in (
                    "model_exact_claim_span",
                    "deterministic_fallback_span",
                    "candidate_pool_span",
                    "selected_span",
                    "answer_covered",
                    "qualified",
                )
            }
            for key, present in stable.items():
                stable_stage_counts[key] += int(present)
            if not stable["candidate_pool_span"]:
                classification = "UPSTREAM_CANDIDATE_COVERAGE_MISS"
            elif not stable["selected_span"]:
                classification = "DOWNSTREAM_SELECTION_MISS"
            elif not stable["answer_covered"]:
                classification = "DOWNSTREAM_ANSWER_VALIDATION_MISS"
            elif not stable["qualified"]:
                classification = "DOWNSTREAM_SOURCE_QUALIFICATION_MISS"
            else:
                classification = "STABLE_QUALIFIED_GAIN"
            classifications[classification] += 1
            relation_rows.append(
                {
                    "qid": qid,
                    "kind": kind,
                    "replicas": replicas,
                    "stable": stable,
                    "classification": classification,
                }
            )

    body = {
        "schema": "s212_query_evidence_compiler_relation_funnel_v1",
        "status": "COMPLETE_CAUSAL_NO_GO_ANALYSIS",
        "residual_relations": len(relation_rows),
        "stable_stage_counts": dict(sorted(stable_stage_counts.items())),
        "classifications": dict(sorted(classifications.items())),
        "rows": relation_rows,
        "decision": {
            "s212_closed": True,
            "same_cohort_iteration": False,
            "facts_moved_to_ok": 0,
            "next": "TARGET_UPSTREAM_CANDIDATE_COVERAGE_BEFORE_SELECTION",
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
    print(
        json.dumps(
            {
                "status": payload["status"],
                "stable_stage_counts": body["stable_stage_counts"],
                "classifications": body["classifications"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
