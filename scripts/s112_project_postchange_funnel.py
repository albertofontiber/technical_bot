#!/usr/bin/env python3
"""Apply the preregistered S112 transitions to the frozen S100 fact funnel."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
CONTRACT = ROOT / "evals/s112_postchange_transition_contract_v1.yaml"
LOCAL_GATE = ROOT / "evals/s112_answer_planner_local_replay_v1.json"
OUT = ROOT / "evals/s112_postchange_funnel_projection_v1.json"


def project_funnel(baseline: dict, contract: dict, local_gate: dict) -> dict:
    if local_gate["gate"]["interpretation"].startswith("NO_GO"):
        raise RuntimeError("answer-planner local gate is NO-GO")
    facts = {
        fact["key"]: fact
        for gold in baseline["per_gold"]
        for fact in gold["facts"]
    }
    if len(facts) != sum(baseline["aggregate_hist"].values()):
        raise RuntimeError("baseline fact keys are not unique")

    transitions = contract["transitions"]
    unknown = sorted(set(transitions) - set(facts))
    if unknown:
        raise RuntimeError(f"transition keys absent from baseline: {unknown}")
    already_ok = sorted(key for key in transitions if facts[key]["clase"] == "OK")
    if already_ok:
        raise RuntimeError(f"transition contract includes baseline OK rows: {already_ok}")

    projected = {key: fact["clase"] for key, fact in facts.items()}
    evidence = {}
    for key, transition in transitions.items():
        projected[key] = transition["candidate"]
        evidence[key] = transition["evidence"]

    detailed = Counter(projected.values())
    rest_classes = {
        "corpus-gap",
        "meta-ref",
        *contract.get("category_projection", {}).keys(),
    }
    headline = {
        "OK": detailed["OK"],
        "synthesis-miss": detailed["synthesis-miss"],
        "rerank-miss": detailed["rerank-miss"],
        "retrieval-miss": detailed["retrieval-miss"],
        "rest": sum(detailed[name] for name in rest_classes),
    }
    if sum(headline.values()) != len(facts):
        raise RuntimeError(
            f"headline partition is incomplete: {sum(headline.values())}/{len(facts)}"
        )

    conservative_denominator = len(facts) - detailed["meta-ref"]
    core_denominator = conservative_denominator - sum(
        detailed[name] for name in contract.get("category_projection", {})
    )
    return {
        "instrument": "s112_postchange_funnel_projection_v1",
        "status": "candidate_projection_not_official_full_regression",
        "baseline_histogram": baseline["aggregate_hist"],
        "candidate_headline_histogram": headline,
        "candidate_detailed_histogram": dict(sorted(detailed.items())),
        "delta_ok": headline["OK"] - baseline["aggregate_hist"]["OK"],
        "total_fact_rows": len(facts),
        "conservative_scored_denominator": conservative_denominator,
        "conservative_ok_rate_percent": round(
            100 * headline["OK"] / conservative_denominator, 2
        ),
        "core_denominator_excluding_meta_and_adjudicated_noncore": core_denominator,
        "core_ok_rate_percent": round(100 * headline["OK"] / core_denominator, 2),
        "transitions_applied": len(transitions),
        "transition_evidence": evidence,
        "release_gate": {
            "local_answer_planner": local_gate["gate"]["interpretation"],
            "adversarial_review": "pending",
            "full_frozen_regression": "pending",
            "official_histogram": False,
        },
    }


def main() -> int:
    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    local_gate = json.loads(LOCAL_GATE.read_text(encoding="utf-8"))
    payload = project_funnel(baseline, contract, local_gate)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["candidate_headline_histogram"], ensure_ascii=False, indent=2))
    print(
        f"OK {payload['candidate_headline_histogram']['OK']}/"
        f"{payload['conservative_scored_denominator']} = "
        f"{payload['conservative_ok_rate_percent']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
