#!/usr/bin/env python3
"""Checkpointed, generator-only probe of guided answer obligations.

The probe reuses frozen final serving contexts, performs no retrieval, rerank,
or judge calls, and refuses to spend twice for the same complete prompt.
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

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s112_synthesis_context_freeze_v1.json"
OUT = ROOT / "evals/s112_guided_synthesis_probe_v1.json"
CHECKPOINT = ROOT / "evals/s112_guided_synthesis_probe_v1.partial.jsonl"
QIDS = ("cat016", "cat018", "hp001", "hp003", "hp017")
EXPECTED_KINDS = {
    "cat016": {"commissioning_menu_bundle"},
    "cat018": {"point_programming_fields", "output_software_type"},
    "hp001": {"credential_administrator", "credential_user"},
    "hp003": {"battery_series_spec", "battery_bridge"},
    "hp017": set(),
}
SUPERSEDED_QIDS = {"hp017"}


def _stable_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _fact_results(qid: str, answer: str) -> list[dict]:
    value = _fold(answer)
    checks: list[tuple[str, bool]]
    if qid == "cat016":
        checks = [
            (
                "cat016#1:menu ZONA + ELEMENTO",
                all(term in value for term in ("menu zona", "menu elemento"))
                and ("asign" in value or "ubicacion" in value),
            )
        ]
    elif qid == "cat018":
        checks = [
            (
                "cat018#1:pestana Programacion: Zona + CBE",
                "pestana" in value
                and "program" in value
                and "zona" in value
                and "cbe" in value,
            ),
            (
                "cat018#2:Tipo SW / asociacion CBE",
                "tipo sw" in value.replace("-", " ")
                and "snd" in value
                and "cbe" in value
                and ("salida" in value or "modulo" in value),
            ),
        ]
    elif qid == "hp001":
        checks = [
            (
                "hp001#2:1111",
                bool(re.search(r"administrador.{0,80}\b2222\b", value, re.S))
                and bool(re.search(r"usuario.{0,80}\b1111\b", value, re.S)),
            )
        ]
    elif qid == "hp003":
        checks = [
            (
                "hp003#0:12V",
                bool(re.search(r"(?:dos|2).{0,50}12\s*v", value, re.S))
                and "serie" in value
                and bool(re.search(r"7\s*a\s*/?\s*h|7\s*ah", value)),
            ),
            (
                "hp003#1:cable puente",
                "puente" in value
                and bool(re.search(r"positiv\w*.{0,100}negativ\w*", value, re.S))
                and ("una bateria" in value and "otra" in value),
            ),
        ]
    elif qid == "hp017":
        checks = [
            (
                "hp017#2:Editar Configuracion",
                "editar configuracion" in value
                and bool(re.search(r"\b7\b.{0,30}causa y efecto", value, re.S))
                and "por defecto" in value
                and "elimin" in value,
            )
        ]
    else:
        raise KeyError(qid)
    return [{"fact_key": key, "present": present} for key, present in checks]


def _load_checkpoints() -> dict[str, dict]:
    rows = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["qid"]] = row
    return rows


def _append_checkpoint(row: dict) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--execute-qids",
        default="",
        help="Comma-separated bounded subset. Empty performs zero-call preflight.",
    )
    args = parser.parse_args()
    requested = tuple(filter(None, (item.strip() for item in args.execute_qids.split(","))))
    if any(qid not in QIDS for qid in requested):
        raise RuntimeError(f"execute-qids must be a subset of {QIDS}")
    if any(not EXPECTED_KINDS[qid] for qid in requested):
        raise RuntimeError("execute-qids contains a conflict-held question")

    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "LLM_MAX_TOKENS": "3500",
            "GENERATOR_PROMPT_VARIANT": "fidelity",
            "GENERATOR_SELECTION_BLOCK": "on",
            "GENERATOR_INCLUDE_CONTEXT": "0",
            "ANSWER_OBLIGATION_PLANNER": "guided",
        }
    )
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_planner import (
        build_answer_plan,
        render_answer_plan_guidance,
        validate_answer_plan,
    )
    from src.rag.generator import RELEVANCE_THRESHOLD, _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import (
        coverage_context_content,
        is_validated_coverage_chunk,
    )

    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen_by_qid = {row["qid"]: row for row in frozen["rows"]}
    checkpoints = _load_checkpoints()
    historical_checkpoints = {}
    preflight = []
    runtime = {}
    for qid in QIDS:
        row = frozen_by_qid[qid]
        # The freeze contains the exact served rows; older S100 rows were
        # rehydrated without their transient similarity score. Restore only
        # the already-served admission bit, never add a new chunk.
        served = [
            {
                **chunk,
                "similarity": (
                    chunk.get("similarity")
                    if chunk.get("similarity") is not None
                    else 0.8
                ),
            }
            for chunk in row["served_context"]
        ]
        relevant = [
            chunk
            for chunk in served
            if chunk.get("similarity", 0) >= RELEVANCE_THRESHOLD
            or is_validated_coverage_chunk(chunk)
        ]
        plan = build_answer_plan(row["question"], relevant)
        kinds = {item.kind for item in plan}
        if kinds != EXPECTED_KINDS[qid]:
            raise RuntimeError(
                f"planner contract drift for {qid}: expected {EXPECTED_KINDS[qid]}, got {kinds}"
            )
        prompt_contract = {
            "qid": qid,
            "question": row["question"],
            "context": [coverage_context_content(chunk) for chunk in relevant],
            "context_headers": [
                {
                    key: chunk.get(key)
                    for key in (
                        "product_model",
                        "section_title",
                        "content_type",
                        "source_file",
                        "document_revision",
                        "document_revision_date",
                    )
                }
                for chunk in relevant
            ],
            "plan": [item.to_dict() for item in plan],
            "guidance": render_answer_plan_guidance(plan),
            "system": _assemble_system(row["question"]),
            "model": LLM_MODEL,
            "max_tokens": LLM_MAX_TOKENS,
        }
        prompt_sha256 = _stable_sha(prompt_contract)
        checkpoint = checkpoints.get(qid)
        if checkpoint and checkpoint.get("prompt_sha256") != prompt_sha256:
            if qid not in SUPERSEDED_QIDS:
                raise RuntimeError(f"stale checkpoint for {qid}; refusing repeat spend")
            historical_checkpoints[qid] = checkpoint
            checkpoints.pop(qid)
            checkpoint = None
        citations = sorted({f"[F{item.fragment_number}]" for item in plan})
        preflight.append(
            {
                "qid": qid,
                "prompt_sha256": prompt_sha256,
                "context_rows": len(relevant),
                "content_chars": sum(len(coverage_context_content(c)) for c in relevant),
                "obligation_kinds": sorted(kinds),
                "obligation_citations": citations,
                "checkpoint_reusable": checkpoint is not None,
                "checkpoint_superseded_by_conflict_gate": qid in historical_checkpoints,
            }
        )
        runtime[qid] = (row, relevant, prompt_sha256, citations, plan)

    for qid in requested:
        if qid in checkpoints:
            continue
        row, relevant, prompt_sha256, citations, plan = runtime[qid]
        result = generate_answer(row["question"], relevant)
        answer = result["answer"]
        facts = _fact_results(qid, answer)
        planner = result.get("answer_planner") or {}
        local_validation = validate_answer_plan(answer, plan)
        checkpoint = {
            "qid": qid,
            "prompt_sha256": prompt_sha256,
            "model": LLM_MODEL,
            "max_output_tokens": LLM_MAX_TOKENS,
            "stop_reason": result.get("stop_reason"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "facts": facts,
            "all_facts_present": all(fact["present"] for fact in facts),
            "all_obligations_covered": (
                local_validation.get("covered") == local_validation.get("total")
            ),
            "obligation_citations_present": all(citation in answer for citation in citations),
            "answer_planner": planner,
            "answer": answer,
            "manual_review_required": True,
        }
        _append_checkpoint(checkpoint)
        checkpoints[qid] = checkpoint

    rows = []
    for row in preflight:
        checkpoint = checkpoints.get(row["qid"])
        rescored = dict(checkpoint or {})
        if checkpoint:
            _frozen, _relevant, _prompt_sha, _citations, plan = runtime[row["qid"]]
            facts = _fact_results(row["qid"], checkpoint["answer"])
            local_validation = validate_answer_plan(checkpoint["answer"], plan)
            rescored.update(
                {
                    "facts": facts,
                    "all_facts_present": all(fact["present"] for fact in facts),
                    "obligation_citations_present": all(
                        citation in checkpoint["answer"]
                        for citation in row["obligation_citations"]
                    ),
                    "all_obligations_covered": (
                        local_validation["covered"] == local_validation["total"]
                    ),
                    "local_validation": local_validation,
                }
            )
        rows.append(
            {
                **row,
                "executed": checkpoint is not None,
                "historical_probe": historical_checkpoints.get(row["qid"]),
                **rescored,
            }
        )

    executed = [row for row in rows if row["executed"]]
    facts = [fact for row in executed for fact in row.get("facts", [])]
    gate = {
        "queries": len(QIDS),
        "requested_this_run": list(requested),
        "paid_generator_calls_available": len(executed),
        "historical_paid_calls_superseded_by_conflict": len(historical_checkpoints),
        "paid_reranker_calls": 0,
        "llm_judge_calls": 0,
        "input_tokens": sum(row.get("input_tokens") or 0 for row in executed),
        "output_tokens": sum(row.get("output_tokens") or 0 for row in executed),
        "deterministic_candidate_facts_present": sum(fact["present"] for fact in facts),
        "deterministic_candidate_facts_total": len(facts),
        "all_obligations_covered_qids": [
            row["qid"] for row in executed if row.get("all_obligations_covered")
        ],
        "manual_review_required_qids": [row["qid"] for row in executed],
        "interpretation": (
            "MEASURED_GUIDED_PROBE_PENDING_MANUAL_REVIEW"
            if executed
            else "PREFLIGHT_ZERO_CALL"
        ),
    }
    payload = {
        "instrument": "s112_guided_synthesis_probe_v1",
        "production_writes": 0,
        "railway_changed": False,
        "planner_mode": "guided",
        "gate": gate,
        "rows": rows,
        "superseded_qids": {
            "hp017": "served sources conflict on menu item 7 versus 8"
        },
        "limitations": [
            "Known development cohort; no held-out precision claim.",
            "Deterministic fact checks are screening only; every executed answer requires review.",
            "No retrieval, rerank, or LLM judge call is made by this probe.",
        ],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
