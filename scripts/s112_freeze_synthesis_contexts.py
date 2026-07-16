#!/usr/bin/env python3
"""Read-only freeze of the served contexts for the projected synthesis cohort."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
CONTRACT = ROOT / "evals/s112_postchange_transition_contract_v1.yaml"
LATEST_CONTEXTS = ROOT / "evals/s111_combined_contexts_v1.json"
S109_RUNTIME = ROOT / "evals/s109_post_rerank_runtime_replay_v1.json"
S108_HYQ = ROOT / "evals/s108_doc_scoped_hyq_replay_v1.json"
S110_COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
OUT = ROOT / "evals/s112_synthesis_context_freeze_v1.json"

SELECT = (
    "id,content,context,product_model,manufacturer,source_file,page_number,"
    "section_title,section_path,content_type,language,document_id,parent_id"
)


def projected_class(fact: dict, transitions: dict) -> str:
    return transitions.get(fact["key"], {}).get("candidate", fact["clase"])


def synthesis_rows(
    baseline: dict,
    contract: dict,
    chunks_by_id: dict,
    *,
    context_overrides: dict[str, list[dict]] | None = None,
    context_appends: dict[str, list[dict]] | None = None,
) -> list[dict]:
    transitions = contract["transitions"]
    rows = []
    for gold in baseline["per_gold"]:
        facts = [
            {**fact, "projected_class": projected_class(fact, transitions)}
            for fact in gold["facts"]
            if projected_class(fact, transitions) == "synthesis-miss"
        ]
        if not facts:
            continue
        overrides = context_overrides or {}
        appends = context_appends or {}
        if gold["qid"] in overrides:
            context = overrides[gold["qid"]]
            context_source = "s111_final_serving_context"
        else:
            missing = [
                chunk_id for chunk_id in gold["served_ids"] if chunk_id not in chunks_by_id
            ]
            if missing:
                raise RuntimeError(f"{gold['qid']}: missing served chunks {missing}")
            context = [chunks_by_id[chunk_id] for chunk_id in gold["served_ids"]]
            context.extend(appends.get(gold["qid"], []))
            context_source = (
                "s100_prefix_plus_validated_post_rerank_appends"
                if appends.get(gold["qid"])
                else "s100_served_context_unchanged"
            )
        rows.append(
            {
                "qid": gold["qid"],
                "question": gold["question"],
                "baseline_answer": gold["answer"],
                "synthesis_facts": facts,
                "context_source": context_source,
                "served_context": context,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY missing")

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    latest_contexts = json.loads(LATEST_CONTEXTS.read_text(encoding="utf-8"))
    s109_runtime = json.loads(S109_RUNTIME.read_text(encoding="utf-8"))
    s108_hyq = json.loads(S108_HYQ.read_text(encoding="utf-8"))
    s110_cohort = yaml.safe_load(S110_COHORT.read_text(encoding="utf-8"))
    transitions = contract["transitions"]
    target_golds = [
        gold
        for gold in baseline["per_gold"]
        if any(projected_class(fact, transitions) == "synthesis-miss" for fact in gold["facts"])
    ]
    s109_append_ids = {
        receipt["qid"]: [row["id"] for row in receipt.get("appended", [])]
        for receipt in s109_runtime.get("receipts", [])
        if receipt.get("appended")
    }
    ids = list(
        dict.fromkeys(
            [chunk_id for gold in target_golds for chunk_id in gold["served_ids"]]
            + [chunk_id for values in s109_append_ids.values() for chunk_id in values]
        )
    )
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    chunks_by_id = {}
    calls = 0
    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(ids), 40):
            batch = ids[start : start + 40]
            response = client.get(
                f"{url}/rest/v1/chunks_v2",
                headers=headers,
                params={"select": SELECT, "id": f"in.({','.join(batch)})"},
            )
            response.raise_for_status()
            calls += 1
            for chunk in response.json():
                chunks_by_id[str(chunk["id"])] = chunk

    context_overrides = {
        row["qid"]: row["context"] for row in latest_contexts.get("rows", [])
    }
    generator_after_s109 = {
        claim.split(".", 1)[0]
        for claim in s110_cohort.get("post_s109_funnel_reconciliation", {}).get(
            "generator_after_s109", []
        )
    }
    hyq_selected = {
        row["qid"]: row.get("selected", [])[:2]
        for row in s108_hyq.get("selections", [])
        if row.get("qid") in generator_after_s109
    }
    context_appends = {}
    for gold in target_golds:
        qid = gold["qid"]
        rows_for_qid = [
            chunks_by_id[chunk_id]
            for chunk_id in s109_append_ids.get(qid, [])
            if chunk_id in chunks_by_id
        ]
        rows_for_qid.extend(hyq_selected.get(qid, []))
        if rows_for_qid:
            context_appends[qid] = rows_for_qid
    rows = synthesis_rows(
        baseline,
        contract,
        chunks_by_id,
        context_overrides=context_overrides,
        context_appends=context_appends,
    )
    payload = {
        "instrument": "s112_synthesis_context_freeze_v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": str(BASELINE.relative_to(ROOT)),
        "transition_contract": str(CONTRACT.relative_to(ROOT)),
        "latest_contexts": str(LATEST_CONTEXTS.relative_to(ROOT)),
        "corpus_snapshot_from_baseline": baseline["manifest"]["corpus"],
        "gate": {
            "questions": len(rows),
            "synthesis_facts": sum(len(row["synthesis_facts"]) for row in rows),
            "unique_served_chunks": len(ids),
            "chunks_fetched": len(chunks_by_id),
            "database_calls": calls,
            "model_calls": 0,
        },
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
