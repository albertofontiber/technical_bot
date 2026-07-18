#!/usr/bin/env python3
"""Run the still-unattempted principal Sol review after S224 Fable stopped."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.s224_review_s223_semantics as prior  # noqa: E402
from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.visual_gold import normalized_text_sha, sealed_artifact, write_json  # noqa: E402

PREREG=ROOT/"evals/s225_s223_sol_principal_review_prereg_v1.yaml"
LEDGER=ROOT/"evals/s225_sol_call_ledger_v1.json"
RESULT=ROOT/"evals/s225_s223_sol_principal_review_result_v1.json"


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--execute",action="store_true"); args=parser.parse_args()
    prereg=yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status")!="FROZEN_BEFORE_PAID_EXECUTION": raise ValueError("S225 not frozen")
    for label,spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT/spec["path"])!=spec["sha256"]: raise ValueError(f"S225 drift: {label}")
    text=prior.prompt(prior.SOL)
    if not args.execute:
        print(json.dumps({"status":"PREFLIGHT_PASS","prompt_chars":len(text),"sol_calls":1,"fable_calls":0,"target_calls":0},indent=2)); return 0
    if LEDGER.exists() or RESULT.exists(): raise RuntimeError("S225 already attempted")
    if not os.getenv("OPENAI_API_KEY"): raise RuntimeError("OPENAI_API_KEY missing")
    runtime=FrontierVisualRuntime(ledger_path=LEDGER,ledger_schema="s225_sol_call_ledger_v1",sol_model=prior.SOL,fable_model=prior.FABLE,sol_reasoning="xhigh",prices=prior.PRICES,openai_api_key=os.environ["OPENAI_API_KEY"],anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "unused"))
    try:
        review,_=runtime.call_sol([{"type":"input_text","text":text}],"semantic_review:sol_principal")
        prior.validate(review,prior.SOL)
    except Exception as exc:
        calls=(runtime.load_ledger().get("calls") or []) if LEDGER.exists() else []
        write_json(RESULT,sealed_artifact("s225_s223_sol_principal_review_result_v1",{"status":"HOLD_S225_EXTERNAL_OR_INVALID","reason":f"{type(exc).__name__}: {exc}","frontier_calls":len(calls),"provider_retries":0,"target_calls":0,"facts_moved_to_ok":0}))
        raise
    runtime.seal_complete(1)
    body={"status":"PASS_S225_SOL_PRINCIPAL" if review["verdict"]=="PASS" else "FAIL_S225_SOL_PRINCIPAL","review":review,"decision":{"dual_gate_pass":False,"target_probe":False,"production":False,"facts_moved_to_ok":0},"invariants":{"chunks_v2":"ACTIVE","chunks_v3":"FINAL_NO_GO_CHUNKS_V3_WHOLESALE","railway_merge_gate":False}}
    write_json(RESULT,sealed_artifact("s225_s223_sol_principal_review_result_v1",body)); print(json.dumps({"status":body["status"],"verdict":review["verdict"],"confirmed":review["confirmed_dev_gain_ids"]},indent=2)); return 0 if review["verdict"]=="PASS" else 2


if __name__=="__main__": raise SystemExit(main())
