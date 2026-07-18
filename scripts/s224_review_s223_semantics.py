#!/usr/bin/env python3
"""Run one independent Sol/Fable semantic gate over sealed S223 outputs."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.visual_gold import normalized_text_sha, sealed_artifact, stable_sha, write_json  # noqa: E402

PREREG = ROOT / "evals/s224_s223_semantic_review_prereg_v1.yaml"
GENERATION = ROOT / "evals/s223_full_context_addendum_generation_v1.json"
LOCAL_RESULT = ROOT / "evals/s223_full_context_addendum_result_v1.json"
SCORE = ROOT / "evals/s219_omission_score_packet_v1.json"
PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
REVIEWS = ROOT / "evals/s224_s223_semantic_reviews_v1.json"
LEDGER = ROOT / "evals/s224_frontier_call_ledger_v1.json"
RESULT = ROOT / "evals/s224_s223_semantic_review_result_v1.json"

SOL = "gpt-5.6-sol"; FABLE = "claude-fable-5"
PRICES = {"sol": {"input": 15.0, "output": 120.0}, "fable": {"input": 30.0, "output": 150.0}}
DEV_IDS = {"cat008", "cat016", "cat017", "hp001", "hp003", "hp010", "hp015"}


def sealed(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8")); body=dict(value); expected=body.pop("result_sha256",None)
    if not expected or stable_sha(body)!=expected: raise ValueError(f"sealed drift: {path.name}")
    return value


def build_review_packet() -> dict[str, Any]:
    generation, score, packet = sealed(GENERATION), sealed(SCORE), sealed(PACKET)
    outputs={row["item_id"]:row for row in generation["items"]}; scores={row["item_id"]:row for row in score["items"]}; inputs={row["item_id"]:row for row in packet["items"]}
    rows=[]
    for item_id,out in outputs.items():
        baseline=out["baseline_answer"]; candidate=out["candidate_answer"]; addendum=candidate[len(baseline):]
        cited=sorted({int(value) for value in re.findall(r"\[F(\d+)\]",addendum)})
        source=[{"fragment_number":n,"content":inputs[item_id]["context"][n-1]["content"]} for n in cited]
        scoring=scores[item_id]
        row={"item_id":item_id,"role":scoring["role"],"question":inputs[item_id]["question"],"baseline_answer":baseline,"addendum":addendum,"cited_source_fragments":source}
        if item_id in DEV_IDS:
            row["canonical_missing_facts"]=scoring["synthesis_miss_facts"]
            row["historical_ok_facts"]=scoring["historical_ok_facts"]
        else:
            row["kidde_atomic_facts"]=scoring["atomic_facts"]
        rows.append(row)
    return {"contract":"s224_s223_semantic_review_packet_v1","items":rows}


def prompt(reviewer: str) -> str:
    contract = f"""You are {reviewer}, an independent critical semantic reviewer. Review a monotonic post-answer addendum mechanism. The baseline is preserved byte-for-byte; judge only whether each addendum is supported by its cited source fragments, materially relevant to the field question, non-redundant, and does not contradict or dangerously broaden the baseline.

For each DEVELOPMENT item, canonical_missing_facts are the exact historical facts the mechanism is intended to recover. Mark canonical_gain=true only if the ADDENDUM itself fully states every material qualifier in at least one listed missing fact. Lexical overlap is insufficient. For Kidde guardrails, identify any loss, contradiction, unsupported claim, or material scope broadening relative to the atomic facts and question.

Overall PASS requires: at least 3 development item IDs with canonical_gain=true; zero unsupported addendum claims; zero material contradictions; zero unsafe or irrelevant scope broadening; zero Kidde regressions. Do not repair or suggest prompt tuning. Return only JSON:
{{"reviewer":"{reviewer}","verdict":"PASS or FAIL","confirmed_dev_gain_ids":["..."],"blocking_findings":["..."],"items":[{{"item_id":"...","canonical_gain":true,"supported":true,"material_contradiction":false,"scope_broadening":false,"kidde_regression":false,"notes":"..."}}]}}

SEALED REVIEW PACKET:
"""
    return contract + json.dumps(build_review_packet(), ensure_ascii=False)


def validate(value: dict[str, Any], reviewer: str) -> None:
    required={"reviewer","verdict","confirmed_dev_gain_ids","blocking_findings","items"}
    if not required<=set(value) or value["reviewer"]!=reviewer or value["verdict"] not in {"PASS","FAIL"}: raise ValueError(f"invalid review shape: {reviewer}")
    ids=[row.get("item_id") for row in value["items"]]
    if len(ids)!=9 or set(ids)!=DEV_IDS|{"kidde_2xa_interface_tradeoffs","kidde_modulaser_role_selection"}: raise ValueError(f"review item geometry: {reviewer}")
    confirmed=set(value["confirmed_dev_gain_ids"])
    derived={row["item_id"] for row in value["items"] if row["item_id"] in DEV_IDS and row.get("canonical_gain") is True}
    blockers=[]
    for row in value["items"]:
        if row.get("supported") is not True or row.get("material_contradiction") is not False or row.get("scope_broadening") is not False or row.get("kidde_regression") is not False: blockers.append(row["item_id"])
    expected_pass=len(derived)>=3 and confirmed==derived and not blockers and not value["blocking_findings"]
    if (value["verdict"]=="PASS")!=expected_pass: raise ValueError(f"review verdict inconsistent: {reviewer}")


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--execute",action="store_true"); args=parser.parse_args()
    prereg=yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status")!="FROZEN_BEFORE_PAID_EXECUTION": raise ValueError("S224 not frozen")
    for label,spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT/spec["path"])!=spec["sha256"]: raise ValueError(f"S224 drift: {label}")
    packet=build_review_packet(); chars=len(json.dumps(packet,ensure_ascii=False))
    if not args.execute:
        print(json.dumps({"status":"PREFLIGHT_PASS","items":9,"prompt_chars":chars,"frontier_calls":2,"target_calls":0},indent=2)); return 0
    if any(path.exists() for path in (REVIEWS,LEDGER,RESULT)): raise RuntimeError("S224 already attempted")
    missing=[key for key in ("OPENAI_API_KEY","ANTHROPIC_API_KEY") if not os.getenv(key)]
    if missing: raise RuntimeError(f"missing credentials: {missing}")
    runtime=FrontierVisualRuntime(ledger_path=LEDGER,ledger_schema="s224_frontier_call_ledger_v1",sol_model=SOL,fable_model=FABLE,sol_reasoning="xhigh",prices=PRICES,openai_api_key=os.environ["OPENAI_API_KEY"],anthropic_api_key=os.environ["ANTHROPIC_API_KEY"])
    try:
        # Fable is called once first so a transient Sol outage cannot erase the independent opinion.
        fable,_=runtime.call_fable([{"type":"text","text":prompt(FABLE)}],10000,"semantic_review:fable")
        validate(fable,FABLE)
        sol,_=runtime.call_sol([{"type":"input_text","text":prompt(SOL)}],"semantic_review:sol")
        validate(sol,SOL)
    except Exception as exc:
        calls=(runtime.load_ledger().get("calls") or []) if LEDGER.exists() else []
        write_json(RESULT,sealed_artifact("s224_s223_semantic_review_result_v1",{"status":"HOLD_S224_EXTERNAL_OR_INVALID","reason":f"{type(exc).__name__}: {exc}","frontier_calls":len(calls),"provider_retries":0,"target_calls":0,"facts_moved_to_ok":0,"chunks_v3":"FINAL_NO_GO_CHUNKS_V3_WHOLESALE","railway_merge_gate":False}))
        raise
    runtime.seal_complete(2)
    write_json(REVIEWS,sealed_artifact("s224_s223_semantic_reviews_v1",{"status":"COMPLETE","reviews":{"principal_sol":sol,"independent_fable":fable}}))
    passed=sol["verdict"]==fable["verdict"]=="PASS"
    body={"status":"GO_S224_TO_FULL_NON_TARGET_GUARDRAIL" if passed else "NO_GO_S224_SEMANTIC_REVIEW","decisions":{"principal_sol":sol["verdict"],"independent_fable":fable["verdict"]},"confirmed_dev_gain_ids":{"principal_sol":sol["confirmed_dev_gain_ids"],"independent_fable":fable["confirmed_dev_gain_ids"]},"blocking_findings":{"principal_sol":sol["blocking_findings"],"independent_fable":fable["blocking_findings"]},"decision":{"full_non_target_guardrail":passed,"target_probe":False,"production":False,"facts_moved_to_ok":0},"invariants":{"chunks_v2":"ACTIVE","chunks_v3":"FINAL_NO_GO_CHUNKS_V3_WHOLESALE","railway_merge_gate":False}}
    write_json(RESULT,sealed_artifact("s224_s223_semantic_review_result_v1",body)); print(json.dumps({"status":body["status"],"sol":sol["verdict"],"fable":fable["verdict"]},indent=2)); return 0 if passed else 2


if __name__=="__main__": raise SystemExit(main())
