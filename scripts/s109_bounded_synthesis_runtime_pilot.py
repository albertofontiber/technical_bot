#!/usr/bin/env python3
"""Bounded synthesis measurement for the five recovered retrieval facts.

The paid reranker top-10 is reused from frozen artifacts. Coverage is rebuilt
through the actual runtime seam, then at most one production generator call per
question is allowed. Exact fact+citation checks replace an LLM judge, and JSONL
checkpoints prevent repeat spend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
POOLS = ROOT / "evals/s102_toc_pools.json"
RUNTIME = ROOT / "evals/s109_post_rerank_runtime_replay_v1.json"
OUT = ROOT / "evals/s109_bounded_synthesis_runtime_pilot_v1.json"
CHECKPOINT = ROOT / "evals/s109_bounded_synthesis_runtime_pilot_v1.partial.jsonl"
QIDS = ("hp011", "hp012", "hp013", "hp014", "hp017")
FALLBACK_SIMILARITY = 0.8
MAX_CONTEXT_CHARS = 80000


def _stable_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    folded = "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()
    return folded.replace("ω", "ohm")


def _fact_present(qid: str, text: str) -> bool:
    value = _fold(text)
    if qid == "hp011":
        return bool(re.search(
            r"(?:0[,.]?5|05).{0,80}295.{0,30}(?:segundo|seg\b|s\b)",
            value,
            re.S,
        ))
    if qid == "hp012":
        return "afp1010" in value and "792" in value and bool(
            re.search(r"(?:\b4\b|cuatro).{0,45}(?:lib|lazo)", value, re.S)
            or re.search(r"(?:lib|lazo).{0,45}(?:\b4\b|cuatro)", value, re.S)
        )
    if qid == "hp013":
        return "pwr-r" in value and "redundan" in value
    if qid == "hp014":
        return bool(re.search(r"\b35\b(?![,.]\d).{0,30}\bohm", value, re.S))
    if qid == "hp017":
        literal = "instruccion de entrada" in value and "instruccion de salida" in value
        semantic = (
            "regla" in value
            and bool(re.search(r"condicion(?:es)? de entrada", value))
            and bool(re.search(
                r"(?:accion(?:es)?|instruccion) de salida", value
            ))
        )
        return literal or semantic
    raise KeyError(qid)


def _cited_by_support(qid: str, answer: str, citations: list[str]) -> bool:
    folded_answer = (answer or "").casefold()
    for citation in citations:
        start = 0
        needle = citation.casefold()
        while True:
            position = folded_answer.find(needle, start)
            if position < 0:
                break
            # Markdown bullets often split one fact across adjacent lines. A
            # bounded citation window is stricter than whole-answer credit but
            # does not falsely require all clauses to share one paragraph.
            window = answer[max(0, position - 600): position + len(citation) + 600]
            if _fact_present(qid, window):
                return True
            start = position + len(needle)
    return False


def _postgrest_in(values: list[str]) -> str:
    escaped = [
        '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        for value in values
    ]
    return "in.(" + ",".join(escaped) + ")"


def _hydrate_missing(ids: list[str], url: str, key: str) -> dict[str, dict]:
    if not ids:
        return {}
    select = (
        "id,content,context,product_model,category,section_title,content_type,"
        "manufacturer,protocol,doc_type,language,has_diagram,diagram_url,"
        "source_file,page_number,document_id"
    )
    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            f"{url.rstrip('/')}/rest/v1/chunks_v2",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"select": select, "id": _postgrest_in(ids), "limit": str(len(ids))},
        )
        response.raise_for_status()
    rows = {str(row["id"]): row for row in response.json()}
    if set(rows) != set(ids):
        raise RuntimeError("frozen prefix hydration incomplete")
    for row in rows.values():
        row["similarity"] = FALLBACK_SIMILARITY
        row["_channel"] = "FROZEN_PREFIX_FALLBACK"
    return rows


def _load_checkpoints() -> dict[str, dict]:
    rows = {}
    if CHECKPOINT.exists():
        for raw in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row = json.loads(raw)
                rows[row["qid"]] = row
    return rows


def _append_checkpoint(row: dict) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    os.environ.update({
        "CHUNKS_TABLE": "chunks_v2",
        "LLM_MAX_TOKENS": "3500",
        "GENERATOR_PROMPT_VARIANT": "fidelity",
        "GENERATOR_SELECTION_BLOCK": "on",
        "GENERATOR_INCLUDE_CONTEXT": "0",
    })
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.config import (
        LLM_MAX_TOKENS,
        LLM_MODEL,
        SUPABASE_SERVICE_KEY,
        SUPABASE_URL,
    )
    from src.rag.generator import _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import apply_post_rerank_coverage_with_trace

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    questions = {
        row["qid"]: row for row in baseline["per_gold"] if row["qid"] in QIDS
    }
    pools = json.loads(POOLS.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    runtime_receipts = {row["qid"]: row for row in runtime["receipts"]}
    retrieval_rows = {
        row["qid"]: row for row in runtime["retrieval_facts_after_runtime"]
    }
    checkpoints = _load_checkpoints()
    contexts: dict[str, tuple] = {}
    preflight = []
    for qid in QIDS:
        question = questions[qid]
        by_id = {str(row["id"]): dict(row) for row in pools[qid]}
        prefix_ids = [str(value) for value in question["served_ids"]]
        missing = [value for value in prefix_ids if value not in by_id]
        by_id.update(_hydrate_missing(missing, SUPABASE_URL, SUPABASE_SERVICE_KEY))
        prefix = [by_id[value] for value in prefix_ids]
        context, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            prefix,
            enabled=True,
            structural_enabled=True,
            hyq_enabled=True,
        )
        appended_ids = [str(row["id"]) for row in context[len(prefix):]]
        expected_ids = [str(row["id"]) for row in runtime_receipts[qid]["appended"]]
        if appended_ids != expected_ids:
            raise RuntimeError(f"coverage runtime drift for {qid}")
        content_chars = sum(len(row.get("content") or "") for row in context)
        if content_chars > MAX_CONTEXT_CHARS:
            raise RuntimeError(f"context cap exceeded for {qid}")
        context_sha = _stable_sha(context)
        support_ids = set(retrieval_rows[qid]["same_family_supporting_ids"])
        support_citations = [
            f"[F{index}]" for index, row in enumerate(context, 1)
            if str(row.get("id") or "") in support_ids
        ]
        if not support_citations:
            raise RuntimeError(f"no supporting citation in runtime context for {qid}")
        checkpoint = checkpoints.get(qid)
        if checkpoint and checkpoint["context_sha256"] != context_sha:
            raise RuntimeError(f"stale paid checkpoint for {qid}; refusing repeat spend")
        contexts[qid] = (context, context_sha, support_citations, trace)
        preflight.append({
            "qid": qid,
            "context_sha256": context_sha,
            "context_rows": len(context),
            "content_chars": content_chars,
            "support_citations": support_citations,
            "checkpoint_reusable": bool(checkpoint),
        })

    if args.execute:
        for row in preflight:
            qid = row["qid"]
            if qid in checkpoints:
                continue
            context, context_sha, support_citations, _ = contexts[qid]
            result = generate_answer(questions[qid]["question"], context)
            answer = result["answer"]
            fact_present = _fact_present(qid, answer)
            cited = _cited_by_support(qid, answer, support_citations)
            checkpoint = {
                "qid": qid,
                "context_sha256": context_sha,
                "model": LLM_MODEL,
                "max_output_tokens": LLM_MAX_TOKENS,
                "stop_reason": result.get("stop_reason"),
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "support_citations": support_citations,
                "fact_present": fact_present,
                "fact_cited_by_support": cited,
                "synthesis_success": fact_present and cited,
                "answer": answer,
            }
            _append_checkpoint(checkpoint)
            checkpoints[qid] = checkpoint

    rows = []
    for preflight_row in preflight:
        checkpoint = checkpoints.get(preflight_row["qid"])
        rescored = dict(checkpoint or {})
        if checkpoint:
            answer = checkpoint["answer"]
            fact_present = _fact_present(preflight_row["qid"], answer)
            cited = _cited_by_support(
                preflight_row["qid"], answer, preflight_row["support_citations"]
            )
            rescored.update({
                "fact_present": fact_present,
                "fact_cited_by_support": cited,
                "synthesis_success": fact_present and cited,
            })
        rows.append({
            **preflight_row,
            "executed": checkpoint is not None,
            **rescored,
        })
    executed = [row for row in rows if row["executed"]]
    success = [row for row in executed if row.get("synthesis_success")]
    gate = {
        "queries": len(QIDS),
        "paid_generator_calls": len(executed),
        "paid_reranker_calls": 0,
        "llm_judge_calls": 0,
        "total_input_tokens": sum(row.get("input_tokens") or 0 for row in executed),
        "total_output_tokens": sum(row.get("output_tokens") or 0 for row in executed),
        "candidate_ok_qids": [row["qid"] for row in success],
        "synthesis_miss_qids": [
            row["qid"] for row in executed if not row.get("synthesis_success")
        ],
        "interpretation": (
            "MEASURED_DOWNSTREAM_CLASSIFICATION"
            if len(executed) == len(QIDS) else "PREFLIGHT_NO_PAID_CALLS"
        ),
    }
    payload = {
        "instrument": "s109_bounded_synthesis_runtime_pilot_v1",
        "execution_requested": args.execute,
        "production_writes": 0,
        "railway_changed": False,
        "treatment": {
            "runtime_seam": "post_rerank_coverage",
            "generator_model": LLM_MODEL,
            "max_calls": len(QIDS),
            "checker": "exact_fact_and_supporting_fragment_citation_v1",
        },
        "system_prompt_sha256": _stable_sha(_assemble_system("contract probe")),
        "gate": gate,
        "rows": rows,
        "limitations": [
            "Known development cohort; stage measurement, not held-out proof.",
            "Candidate OK is not official OK until protected-OK regression and release gates pass.",
            "No LLM judge is used; exact fact and supporting-fragment citation checks score outputs.",
        ],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
