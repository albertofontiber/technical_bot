#!/usr/bin/env python3
"""Score S228 only after all non-target generations are sealed."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.atomic_scorer import match_fact  # noqa: E402
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json  # noqa: E402
GEN = ROOT / "evals/s228_clause_bound_synthesis_generation_v1.json"
SCORE = ROOT / "evals/s219_omission_score_packet_v1.json"
OUT = ROOT / "evals/s228_clause_bound_synthesis_result_v1.json"
def sealed(path):
    value=json.loads(path.read_text(encoding="utf-8")); body=dict(value); expected=body.pop("result_sha256",None)
    if not expected or stable_sha(body)!=expected: raise ValueError(f"seal drift: {path.name}")
    return value
def covered(fact, answer): return match_fact(fact.get("valor") or fact.get("value"), fact.get("texto") or fact.get("text") or "", answer)[0] is True
def main():
    if OUT.exists(): raise RuntimeError("S228 score exists")
    gen=sealed(GEN); score=sealed(SCORE)
    if gen["status"]!="COMPLETE_SCORE_NOT_OPENED" or gen["score_packet_opened"] is not False: raise ValueError("generation incomplete")
    by={x["item_id"]:x for x in score["items"]}; gains=[]; regressions=[]; kidde_reg=[]; invalid={}
    rows=[]
    for item in gen["items"]:
        gold=by[item["item_id"]]; answers=[r["answer"] for r in item["replicas"]]
        bad=[invalid_citations(a,item["replicas"][i]["fragment_count"]) for i,a in enumerate(answers)]
        if any(bad): invalid[item["item_id"]]=bad
        if item["role"]=="historical_multichunk_development":
            stable=[f["key"] for f in gold["synthesis_miss_facts"] if all(covered(f,a) for a in answers)]
            reg=[f["key"] for f in gold["historical_ok_facts"] if covered(f,item["baseline_answer"]) and any(not covered(f,a) for a in answers)]
            gains+=stable; regressions+=reg; rows.append({"item_id":item["item_id"],"stable_gains":stable,"regressions":reg})
        else:
            reg=[f"{item['item_id']}:{f['fact_id']}" for f in gold["atomic_facts"] if covered(f,item["baseline_answer"]) and any(not covered(f,a) for a in answers)]
            kidde_reg+=reg; rows.append({"item_id":item["item_id"],"regressions":reg})
    checks={"provisional_matcher_gains_gte_3":len(gains)>=3,"protected_regressions_zero":not regressions,
            "kidde_regressions_zero":not kidde_reg,"invalid_citations_zero":not invalid,
            "cost_below_25":float(gen["actual_cost_usd"])<25,"target_calls_zero":gen["target_calls"]==0}
    passed=all(checks.values()); body={"status":"PROMISING_LOCAL_ONLY" if passed else "NO_GO_S228_LOCAL",
        "metrics":{"provisional_matcher_gains":gains,"protected_regressions":regressions,"kidde_regressions":kidde_reg,
                   "invalid_citations":invalid,"actual_cost_usd":gen["actual_cost_usd"]},"checks":checks,"rows":rows,
        "decision":{"target_probe":False,"official_fact_credit":0,"production":False,
                    "next":"fresh_independent_cohort_required" if passed else "close_clause_bound_line"},
        "invariants":{"chunks_v2":"ACTIVE_READ_ONLY","chunks_v3":"FINAL_NO_GO_CHUNKS_V3_WHOLESALE","railway_merge_gate":False}}
    write_json(OUT,sealed_artifact("s228_clause_bound_synthesis_result_v1",body)); print(json.dumps({"status":body["status"],"gains":len(gains),"regressions":len(regressions)+len(kidde_reg)},indent=2)); return 0 if passed else 2
if __name__=="__main__": raise SystemExit(main())
