#!/usr/bin/env python3
"""Paired local screen for S223; semantic promotion remains Frontier-gated."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atomic_scorer import match_fact  # noqa: E402
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import normalized_text_sha, sealed_artifact, stable_sha, write_json  # noqa: E402

PREREG = ROOT / "evals/s223_full_context_addendum_prereg_v1.yaml"
GENERATION = ROOT / "evals/s223_full_context_addendum_generation_v1.json"
SCORE = ROOT / "evals/s219_omission_score_packet_v1.json"
RESULT = ROOT / "evals/s223_full_context_addendum_result_v1.json"


def sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8")); body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected: raise ValueError(f"sealed drift: {path.name}")
    return value


def hit(fact: dict[str, Any], answer: str, external: bool = False) -> bool:
    return match_fact(fact.get("value") if external else fact.get("valor"), fact.get("text") if external else fact.get("texto", ""), answer)[0] is True


def main() -> int:
    if RESULT.exists(): raise RuntimeError("S223 result exists")
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    for label, spec in prereg["frozen_score_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]: raise ValueError(f"score drift: {label}")
    generation, score = sealed(GENERATION), sealed(SCORE)
    if generation["status"] != "COMPLETE_SCORE_NOT_OPENED" or not generation["monotonic_prefix_invariant"]: raise ValueError("S223 generation incomplete")
    outputs = {row["item_id"]: row for row in generation["items"]}
    canonical_candidate_hits=[]; stable_regressions=[]; rows=[]; kidde_regressions=[]; kb=kc=0
    for item in score["items"]:
        out=outputs[item["item_id"]]; baseline=out["baseline_answer"]; candidate=out["candidate_answer"]
        if not candidate.startswith(baseline): raise ValueError("non-monotonic candidate")
        if item["role"] == "historical_multichunk_development":
            covered=[str(f["key"]) for f in item["synthesis_miss_facts"] if hit(f,candidate)]
            canonical_candidate_hits += covered
            stable=[]; reg=[]
            for fact in item["historical_ok_facts"]:
                if hit(fact,baseline):
                    stable.append(str(fact["key"]))
                    if not hit(fact,candidate): reg.append(str(fact["key"])); stable_regressions.append(str(fact["key"]))
            rows.append({"item_id":item["item_id"],"candidate_synthesis_hits":covered,"stable_baseline_fact_ids":stable,"stable_regression_ids":reg})
        else:
            before=[hit(f,baseline,True) for f in item["atomic_facts"]]; after=[hit(f,candidate,True) for f in item["atomic_facts"]]
            kb+=sum(before); kc+=sum(after)
            for fact,b,a in zip(item["atomic_facts"],before,after):
                if b and not a: kidde_regressions.append(f"{item['item_id']}:{fact['fact_id']}")
    invalid={row["item_id"]: invalid_citations(row["candidate_answer"],row["fragment_count"]) for row in generation["items"]}; invalid={k:v for k,v in invalid.items() if v}
    checks={
        "canonical_candidate_synthesis_hits_gte_3":len(canonical_candidate_hits)>=3,
        "stable_local_regressions_zero":not stable_regressions,
        "kidde_regressions_zero":not kidde_regressions,
        "kidde_candidate_not_worse":kc>=kb,
        "invalid_citations_zero":not invalid,
        "token_limit_stops_zero":generation["metrics"]["token_limit_stops"]==0,
        "monotonic_prefix":generation["monotonic_prefix_invariant"] is True,
    }
    passed=all(checks.values())
    body={"status":"GO_S223_TO_DUAL_SEMANTIC_REVIEW" if passed else "NO_GO_S223_FULL_CONTEXT_ADDENDUM","metrics":{"canonical_candidate_synthesis_hits":canonical_candidate_hits,"stable_local_regressions":stable_regressions,"kidde_baseline_covered":kb,"kidde_candidate_covered":kc,"kidde_regressions":kidde_regressions,"invalid_citations":invalid,**generation["metrics"]},"checks":checks,"development_rows":rows,"decision":{"dual_frontier_semantic_review":passed,"full_non_target_guardrail":False,"target_probe":False,"production":False,"facts_moved_to_ok":0},"invariants":{"chunks_v2":"ACTIVE","chunks_v3":"FINAL_NO_GO_CHUNKS_V3_WHOLESALE","railway_merge_gate":False}}
    write_json(RESULT,sealed_artifact("s223_full_context_addendum_result_v1",body)); print(json.dumps({"status":body["status"],"candidate_hits":len(canonical_candidate_hits),"stable_regressions":len(stable_regressions),"kidde":f"{kc}/{kb}"},indent=2)); return 0 if passed else 2


if __name__ == "__main__": raise SystemExit(main())
