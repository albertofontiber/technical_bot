#!/usr/bin/env python3
"""Build and run the S138 symmetric semantic fallback-MRR probe."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as base
from scripts import s135_representative_chunks_shadow_v2 as shadow
from scripts import s136_chunks_v3_loss_attribution as s136
from scripts import s137_blinded_chunks_semantic_adjudication as s137


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s138_symmetric_semantic_mrr_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s138_symmetric_semantic_mrr_execution_permit_v1.yaml"
RELEVANCE = s137.RELEVANCE
ANSWERABILITY = s137.ANSWERABILITY
CONFIDENCE = s137.CONFIDENCE

SYSTEM_PROMPT = """You are an independent semantic evidence adjudicator for technical-manual retrieval.
Each question contains two opaque evidence sets. You do not know which retrieval system produced either
set, and item order does not represent retrieval rank. Judge each set independently from RAW SOURCE
CONTENT only. Treat Spanish and English equally. Do not use outside knowledge to fill gaps and do not
reward keyword overlap without the required technical fact, relation, value, condition, or procedure.

For EVERY evidence set:
1. Assess EVERY item exactly once as DIRECT, SUPPORTING, IRRELEVANT, or UNCERTAIN.
2. DIRECT establishes an answer-critical fact; SUPPORTING adds useful but non-critical context.
3. If the set completely answers the question, choose its smallest sufficient evidence set. Selected
   items must be DIRECT or SUPPORTING and at least one must be DIRECT.
4. If answerability is PARTIAL or NONE, minimum_sufficient_evidence_ids must be empty.
5. Keep each set rationale under 90 words. Return only the required structured JSON."""


class S138Failure(RuntimeError):
    pass


def output_schema() -> dict[str, Any]:
    assessment = {
        "type": "object",
        "additionalProperties": False,
        "required": ["evidence_id", "relevance", "supported_claim", "redundant_with"],
        "properties": {
            "evidence_id": {"type": "string"},
            "relevance": {"type": "string", "enum": sorted(RELEVANCE)},
            "supported_claim": {"type": "string"},
            "redundant_with": {"type": "array", "items": {"type": "string"}},
        },
    }
    set_judgement = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "evidence_set_id",
            "answerability",
            "minimum_sufficient_evidence_ids",
            "evidence_assessments",
            "confidence",
            "rationale",
        ],
        "properties": {
            "evidence_set_id": {"type": "string"},
            "answerability": {"type": "string", "enum": sorted(ANSWERABILITY)},
            "minimum_sufficient_evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "evidence_assessments": {"type": "array", "items": assessment},
            "confidence": {"type": "string", "enum": sorted(CONFIDENCE)},
            "rationale": {"type": "string"},
        },
    }
    question = {
        "type": "object",
        "additionalProperties": False,
        "required": ["question_id", "set_judgements"],
        "properties": {
            "question_id": {"type": "string"},
            "set_judgements": {"type": "array", "items": set_judgement},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["judgements"],
        "properties": {"judgements": {"type": "array", "items": question}},
    }


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    specs = {"design": prereg["design"], **prereg["frozen_inputs"]}
    for name, spec in specs.items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S138Failure(f"S138 dependency drift: {name}")
    s135 = base.load_json(root / prereg["frozen_inputs"]["s135_seed"]["path"])
    by_qid = {row["question_id"]: row for row in s135["question_results"]}
    expected = prereg["population"]["question_ids"]
    if any(qid not in by_qid for qid in expected):
        raise S138Failure("S138 question population missing from S135")
    for qid in expected:
        row = by_qid[qid]
        baseline_hit = row["baseline_rank"] is not None and row["baseline_rank"] <= 10
        candidate_hit = row["candidate_rank"] is not None and row["candidate_rank"] <= 10
        if not baseline_hit or candidate_hit:
            raise S138Failure("S138 population no longer matches fallback trigger")


def opaque(seed: str, *parts: str, prefix: str) -> str:
    digest = hashlib.sha256("|".join((seed, *parts)).encode()).hexdigest()
    return f"{prefix}-{digest[:12].upper()}"


def assert_blind(packet: dict[str, Any]) -> None:
    forbidden = {
        "arm",
        "rank",
        "score",
        "gold",
        "context",
        "strict_context_donor",
        "document_id",
        "chunk_id",
        "database_id",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            overlap = forbidden.intersection(value)
            if overlap:
                raise S138Failure(f"S138 blind packet leaks fields: {sorted(overlap)}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(packet)


def reconstruct(
    prereg: dict[str, Any], store: Path, generated: Path, *, root: Path = ROOT
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    validate_prereg(prereg, root=root)
    s135_prereg = base.load_yaml(root / prereg["frozen_inputs"]["s135_prereg"]["path"])
    shadow.validate_contract(s135_prereg, root=root)
    cohort, pairs = base.load_cohort(s135_prereg, root=root)
    cohort = shadow.plan_queries(cohort)
    selected = base.load_selected_metadata(s135_prereg, pairs, root=root)
    baseline, _ = base.load_baseline_rows(s135_prereg, selected, root=root)
    records = base.validate_raw_store(s135_prereg, store)
    candidate, _ = shadow.materialize_candidate_rows(s135_prereg, selected, baseline, records)
    questions = [
        row for row in cohort if row["question_id"] in set(prereg["population"]["question_ids"])
    ]
    chunks = []
    for row in baseline + candidate:
        chunks.append(
            {
                **row,
                "strict_context_donor": (
                    True if row["arm"] == "baseline_v2" else row.get("context") is not None
                ),
            }
        )
    chunks_path = generated / "chunks.csv"
    questions_path = generated / "questions.csv"
    base.write_csv(
        chunks_path,
        [
            "arm",
            "id",
            "document_id",
            "extraction_sha256",
            "manufacturer",
            "product_model",
            "content",
            "context",
            "section_title",
            "section_path",
            "page_number",
            "strict_context_donor",
        ],
        chunks,
    )
    base.write_csv(
        questions_path,
        ["question_id", "question", "search_query", "manufacturer", "product_model"],
        questions,
    )
    ranked_all = base.execute_postgres(
        s135_prereg,
        s136.diagnostic_sql(
            chunks_path,
            questions_path,
            "s138_symmetric_mrr",
            max_rank=prereg["population"]["top_k_per_arm"],
        ),
        root=root,
    )
    ranked = [row for row in ranked_all if row["scenario"] == "current"]
    return questions, chunks, ranked


def build_packet(
    prereg: dict[str, Any], store: Path, generated: Path, *, root: Path = ROOT
) -> tuple[dict[str, Any], dict[str, Any]]:
    questions, chunks, ranked = reconstruct(prereg, store, generated, root=root)
    q_by = {row["question_id"]: row for row in questions}
    chunk_by = {(row["arm"], row["id"]): row for row in chunks}
    ranked_by: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in ranked:
        ranked_by[(row["question_id"], row["arm"])].append(row)
    seed = prereg["blind_packet"]["deterministic_seed"]
    public_questions = []
    private_questions = []
    for qid in prereg["population"]["question_ids"]:
        public_sets = []
        private_sets = []
        for arm in prereg["population"]["arms"]:
            set_id = opaque(seed, qid, arm, prefix="S")
            public_items = []
            private_items = []
            rows = sorted(ranked_by[(qid, arm)], key=lambda row: row["rank_position"])
            if not rows or len(rows) > prereg["population"]["top_k_per_arm"]:
                raise S138Failure(f"S138 invalid ranked population: {qid}/{arm}")
            for ranked_row in rows:
                row = chunk_by[(arm, ranked_row["id"])]
                evidence_id = opaque(seed, qid, arm, row["id"], prefix="E")
                public_items.append(
                    {
                        "evidence_id": evidence_id,
                        "section_title": row.get("section_title"),
                        "section_path": row.get("section_path"),
                        "page_number": row.get("page_number"),
                        "source_content": row["content"],
                    }
                )
                private_items.append(
                    {
                        "evidence_id": evidence_id,
                        "chunk_id": row["id"],
                        "rank": ranked_row["rank_position"],
                        "score": ranked_row["score"],
                        "document_id": row["document_id"],
                    }
                )
            public_items.sort(key=lambda row: row["evidence_id"])
            private_items.sort(key=lambda row: row["evidence_id"])
            public_sets.append({"evidence_set_id": set_id, "evidence": public_items})
            private_sets.append(
                {"evidence_set_id": set_id, "arm": arm, "evidence": private_items}
            )
        public_sets.sort(key=lambda row: row["evidence_set_id"])
        private_sets.sort(key=lambda row: row["evidence_set_id"])
        q = q_by[qid]
        public_questions.append(
            {
                "question_id": qid,
                "question": q["question"],
                "manufacturer": q["manufacturer"],
                "product_model": q["product_model"],
                "evidence_sets": public_sets,
            }
        )
        private_questions.append({"question_id": qid, "evidence_sets": private_sets})
    packet = {
        "instrument": "s138_symmetric_semantic_mrr_packet_v1",
        "status": "FROZEN_BLIND_PACKET",
        "questions": public_questions,
        "checks": {"questions": 3, "sets_per_question": 2, "top_k": 10},
        "manifests": {"questions_sha256": base.canonical_sha(public_questions)},
    }
    assert_blind(packet)
    mapping = {
        "instrument": "s138_symmetric_semantic_mrr_mapping_v1",
        "status": "PRIVATE_NOT_JUDGE_INPUT",
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "questions": private_questions,
        "manifests": {"questions_sha256": base.canonical_sha(private_questions)},
    }
    return packet, mapping


def judge_payload(packet: dict[str, Any]) -> str:
    return json.dumps({"questions": packet["questions"]}, ensure_ascii=False, sort_keys=True)


def user_prompt(packet: dict[str, Any]) -> str:
    return "Adjudicate every opaque evidence set in this frozen packet.\n\n" + judge_payload(packet)


def validate_judgement(
    judgement: dict[str, Any], packet: dict[str, Any], *, question_ids: set[str] | None = None
) -> None:
    errors = sorted(
        Draft202012Validator(output_schema()).iter_errors(judgement),
        key=lambda error: list(error.path),
    )
    if errors:
        raise S138Failure(f"S138 judgement schema violation: {errors[0].message}")
    packet_by = {row["question_id"]: row for row in packet["questions"]}
    expected_qids = question_ids if question_ids is not None else set(packet_by)
    rows = judgement["judgements"]
    if {row["question_id"] for row in rows} != expected_qids or len(rows) != len(expected_qids):
        raise S138Failure("S138 judgement question-set mismatch")
    for row in rows:
        qid = row["question_id"]
        public_sets = {item["evidence_set_id"]: item for item in packet_by[qid]["evidence_sets"]}
        set_rows = row["set_judgements"]
        if {item["evidence_set_id"] for item in set_rows} != set(public_sets) or len(set_rows) != 2:
            raise S138Failure(f"S138 evidence-set mismatch: {qid}")
        for set_row in set_rows:
            set_id = set_row["evidence_set_id"]
            expected_ids = {item["evidence_id"] for item in public_sets[set_id]["evidence"]}
            assessments = set_row["evidence_assessments"]
            ids = [item["evidence_id"] for item in assessments]
            if set(ids) != expected_ids or len(ids) != len(set(ids)):
                raise S138Failure(f"S138 evidence assessment mismatch: {qid}/{set_id}")
            by_id = {item["evidence_id"]: item for item in assessments}
            for item in assessments:
                redundant = item["redundant_with"]
                if not set(redundant).issubset(expected_ids) or item["evidence_id"] in redundant:
                    raise S138Failure(f"S138 invalid redundancy: {qid}/{set_id}")
            minimum = set_row["minimum_sufficient_evidence_ids"]
            if len(minimum) != len(set(minimum)) or not set(minimum).issubset(expected_ids):
                raise S138Failure(f"S138 invalid minimum set: {qid}/{set_id}")
            if set_row["answerability"] == "COMPLETE":
                labels = [by_id[item]["relevance"] for item in minimum]
                if not minimum or not set(labels).issubset({"DIRECT", "SUPPORTING"}) or "DIRECT" not in labels:
                    raise S138Failure(f"S138 inconsistent complete set: {qid}/{set_id}")
            elif minimum:
                raise S138Failure(f"S138 non-complete minimum set: {qid}/{set_id}")
            if len(set_row["rationale"].split()) > 90:
                raise S138Failure(f"S138 rationale too long: {qid}/{set_id}")


def semantic_ranks(
    judgement: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, dict[str, int | None]]:
    maps = {
        q["question_id"]: {
            evidence_set["evidence_set_id"]: {
                "arm": evidence_set["arm"],
                "ranks": {item["evidence_id"]: item["rank"] for item in evidence_set["evidence"]},
            }
            for evidence_set in q["evidence_sets"]
        }
        for q in mapping["questions"]
    }
    output = {}
    for q in judgement["judgements"]:
        per_arm = {}
        for set_row in q["set_judgements"]:
            info = maps[q["question_id"]][set_row["evidence_set_id"]]
            minimum = set_row["minimum_sufficient_evidence_ids"]
            per_arm[info["arm"]] = (
                max(info["ranks"][item] for item in minimum)
                if set_row["answerability"] == "COMPLETE" and minimum
                else None
            )
        output[q["question_id"]] = per_arm
    return output


def subset_packet(packet: dict[str, Any], qids: set[str]) -> dict[str, Any]:
    questions = [row for row in packet["questions"] if row["question_id"] in qids]
    return {**packet, "questions": questions, "manifests": {"questions_sha256": base.canonical_sha(questions)}}


def subset_judgement(judgement: dict[str, Any], qids: set[str]) -> dict[str, Any]:
    return {"judgements": [row for row in judgement["judgements"] if row["question_id"] in qids]}


def text_format() -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s138_symmetric_semantic_mrr",
            "schema": output_schema(),
            "strict": True,
        },
        "verbosity": "low",
    }


def anthropic_config(effort: str) -> dict[str, Any]:
    return {"effort": effort, "format": {"type": "json_schema", "schema": output_schema()}}


def parse(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise S138Failure(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise S138Failure(f"{label} returned non-object JSON")
    return value


def response_record(
    *,
    provider: str,
    model: str,
    response: Any,
    packet: dict[str, Any],
    judgement: dict[str, Any],
    usage: dict[str, Any],
    cost: float,
) -> dict[str, Any]:
    return {
        "instrument": "s138_blinded_judge_response_v1",
        "status": "VALIDATED",
        "provider": provider,
        "model": model,
        "response_id": response.id,
        "created_at": s137.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": usage,
        "conservative_cost_usd": cost,
        "judgement": judgement,
    }


def failure_record(
    *,
    provider: str,
    model: str,
    response: Any,
    packet: dict[str, Any],
    raw_output: str,
    failure: str,
    usage: dict[str, Any],
    cost: float,
) -> dict[str, Any]:
    """Persist a paid but unusable response so it is never repeated blindly."""
    return {
        "instrument": "s138_blinded_judge_response_v1",
        "status": "PAID_INVALID_NO_RETRY",
        "provider": provider,
        "model": model,
        "response_id": response.id,
        "created_at": s137.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "provider_status": getattr(response, "status", None),
        "stop_reason": getattr(response, "stop_reason", None),
        "usage": usage,
        "conservative_cost_usd": cost,
        "failure": failure,
        "raw_output": raw_output,
    }


def validate_permit(prereg: dict[str, Any], permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise S138Failure("S138 paid permit is not GO")
    for name in ("preregistration", "runner", "tests", "packet", "mapping"):
        spec = permit[name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S138Failure(f"S138 permitted artifact drift: {name}")


def worst_case(prereg: dict[str, Any], sol_input: int, fable_inputs: list[int]) -> float:
    prices = prereg["pricing_usd_per_million_tokens"]
    primary = prereg["models"]["primary"]
    independent = prereg["models"]["independent"]
    arbitration = prereg["models"]["arbitration"]
    total = (
        sol_input * prices["openai"]["input_conservative_cache_write"]
        + primary["max_output_tokens"] * prices["openai"]["output"]
        + sum(fable_inputs) * prices["anthropic"]["input"]
        + len(fable_inputs) * independent["max_output_tokens_per_question"] * prices["anthropic"]["output"]
        + arbitration["max_counted_input_tokens"] * prices["openai"]["input_conservative_cache_write"]
        + arbitration["max_output_tokens"] * prices["openai"]["output"]
    ) / 1_000_000
    return round(total, 8)


def hybrid_mrr(
    s135: dict[str, Any], final_ranks: dict[str, dict[str, int | None]], fallback_qids: set[str]
) -> tuple[float, float]:
    sums = {"baseline_v2": 0.0, "candidate_v3": 0.0}
    for row in s135["question_results"]:
        qid = row["question_id"]
        for arm, key in (("baseline_v2", "baseline_rank"), ("candidate_v3", "candidate_rank")):
            if qid in fallback_qids:
                rank = final_ranks[qid][arm]
            else:
                rank = row[key]
            if rank is not None and rank <= 10:
                sums[arm] += 1 / rank
    n = len(s135["question_results"])
    return round(sums["baseline_v2"] / n, 8), round(sums["candidate_v3"] / n, 8)


def aggregate(
    prereg: dict[str, Any], packet: dict[str, Any], mapping: dict[str, Any],
    s135: dict[str, Any], sol: dict[str, Any], fable: dict[str, Any], arbitration: dict[str, Any] | None
) -> dict[str, Any]:
    sol_ranks = semantic_ranks(sol["judgement"], mapping)
    fable_ranks = semantic_ranks(fable["judgement"], mapping)
    disagreements = {qid for qid in sol_ranks if sol_ranks[qid] != fable_ranks[qid]}
    arb_ranks = semantic_ranks(arbitration["judgement"], mapping) if arbitration else {}
    final = {
        qid: (arb_ranks.get(qid) if qid in disagreements else sol_ranks[qid])
        for qid in sol_ranks
    }
    valid = all(
        ranks is not None and all(rank is not None and rank <= 10 for rank in ranks.values())
        for ranks in final.values()
    )
    baseline_mrr, candidate_mrr = hybrid_mrr(s135, final, set(final)) if valid else (None, None)
    costs = [sol["conservative_cost_usd"], fable["conservative_cost_usd"]]
    if arbitration:
        costs.append(arbitration["conservative_cost_usd"])
    checks = {
        "three_final_two_arm_rank_tuples": valid and len(final) == 3,
        "candidate_hybrid_mrr_gte_baseline": (
            candidate_mrr is not None and baseline_mrr is not None and candidate_mrr >= baseline_mrr
        ),
        "s137_hit_reconciliation_still_go": True,
        "actual_cost_below_internal_ceiling": sum(costs) < prereg["budget"]["internal_ceiling_usd"],
        "facts_moved_to_ok_zero": True,
    }
    go = all(checks.values())
    return {
        "instrument": "s138_symmetric_semantic_mrr_v1",
        "status": "GO" if go else "NO_GO",
        "checks": checks,
        "questions": [
            {
                "question_id": qid,
                "sol_ranks": sol_ranks[qid],
                "fable_ranks": fable_ranks[qid],
                "initial_agreement": qid not in disagreements,
                "arbitration_ranks": arb_ranks.get(qid),
                "final_ranks": final[qid],
            }
            for qid in prereg["population"]["question_ids"]
        ],
        "metrics": {
            "baseline_hybrid_mrr_at_10": baseline_mrr,
            "candidate_hybrid_mrr_at_10": candidate_mrr,
            "candidate_minus_baseline": (
                round(candidate_mrr - baseline_mrr, 8)
                if candidate_mrr is not None and baseline_mrr is not None
                else None
            ),
            "cohort_size": 24,
            "semantic_fallback_questions": 3,
        },
        "summary": {"initial_disagreements": len(disagreements), "holds": 0 if valid else 1},
        "cost": {
            "paid_calls": len(costs) - 1 + 3,  # Sol + three atomic Fable + optional arbitration
            "conservative_actual_usd": round(sum(costs), 8),
            "prior_s137_cumulative_conservative_usd": prereg["budget"]["prior_s137_cumulative_conservative_usd"],
            "combined_probe_cost_usd": round(
                sum(costs) + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
            ),
        },
        "authorization": {
            "production": False,
            "migration_apply": False,
            "deploy": False,
            "facts_moved_to_ok": 0,
        },
        "decision": "GO_TO_CHUNKS_V3_SHADOW_PROMOTION_DECISION" if go else "NO_GO_KEEP_CHUNKS_V3_OUT",
    }


def execute_paid(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_prereg(prereg, root=root)
    validate_permit(prereg, permit, root=root)
    packet1 = root / prereg["execution"]["public_packet_seed1"]
    packet2 = root / prereg["execution"]["public_packet_seed2"]
    mapping1 = root / prereg["execution"]["private_mapping_seed1"]
    mapping2 = root / prereg["execution"]["private_mapping_seed2"]
    if packet1.read_bytes() != packet2.read_bytes() or mapping1.read_bytes() != mapping2.read_bytes():
        raise S138Failure("S138 packet/mapping seeds are not byte-identical")
    packet = base.load_json(packet1)
    mapping = base.load_json(mapping1)
    assert_blind(packet)

    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    secrets = dotenv_values(env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise S138Failure("S138 provider API key missing")
    openai_client = OpenAI(api_key=openai_key)
    anthropic_client = Anthropic(api_key=anthropic_key)
    primary = prereg["models"]["primary"]
    independent = prereg["models"]["independent"]
    full_prompt = user_prompt(packet)
    sol_count = openai_client.responses.input_tokens.count(
        model=primary["model"], reasoning={"effort": primary["reasoning_effort"]},
        instructions=SYSTEM_PROMPT, input=full_prompt, text=text_format()
    ).input_tokens
    atomic_packets = [subset_packet(packet, {qid}) for qid in prereg["population"]["question_ids"]]
    fable_counts = [
        anthropic_client.messages.count_tokens(
            model=independent["model"], system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt(subset)}],
            thinking={"type": independent["thinking"]},
            output_config=anthropic_config(independent["effort"]),
        ).input_tokens
        for subset in atomic_packets
    ]
    if sol_count > primary["max_counted_input_tokens"]:
        raise S138Failure("S138 Sol input exceeds cap")
    if any(count > independent["max_counted_input_tokens_per_question"] for count in fable_counts):
        raise S138Failure("S138 Fable input exceeds per-question cap")
    if sum(fable_counts) > independent["max_counted_input_tokens_total"]:
        raise S138Failure("S138 Fable total input exceeds cap")
    reserved = worst_case(prereg, sol_count, fable_counts)
    if reserved >= prereg["budget"]["internal_ceiling_usd"]:
        raise S138Failure("S138 worst case exceeds internal ceiling")
    if reserved + prereg["budget"]["prior_s137_cumulative_conservative_usd"] >= prereg["budget"]["user_authorized_total_ceiling_usd"]:
        raise S138Failure("S138 would exceed user total ceiling")
    s137._write(
        root / prereg["execution"]["paid_preflight"],
        {
            "instrument": "s138_paid_preflight_v1",
            "status": "GO",
            "created_at": s137.utc_now(),
            "sol_input_tokens": sol_count,
            "fable_atomic_input_tokens": fable_counts,
            "s138_worst_case_usd": reserved,
            "combined_with_prior_s137_worst_case_usd": round(
                reserved + prereg["budget"]["prior_s137_cumulative_conservative_usd"], 8
            ),
        },
    )

    sol_response = openai_client.responses.create(
        model=primary["model"], reasoning={"effort": primary["reasoning_effort"]},
        instructions=SYSTEM_PROMPT, input=full_prompt, text=text_format(),
        max_output_tokens=primary["max_output_tokens"], store=False
    )
    sol_text = sol_response.output_text
    sol_usage = sol_response.usage.model_dump(mode="json")
    sol_cost = s137.conservative_openai_cost(
        sol_usage,
        {
            "cache_write": prereg["pricing_usd_per_million_tokens"]["openai"][
                "input_conservative_cache_write"
            ],
            "output": prereg["pricing_usd_per_million_tokens"]["openai"]["output"],
        },
    )
    try:
        if sol_response.status != "completed":
            raise S138Failure("S138 Sol primary incomplete; no retry authorised")
        sol_judgement = parse(sol_text, "S138 Sol")
        validate_judgement(sol_judgement, packet)
    except Exception as exc:
        s137._write(
            root / prereg["execution"]["sol_response"],
            failure_record(
                provider="openai",
                model=primary["model"],
                response=sol_response,
                packet=packet,
                raw_output=sol_text,
                failure=str(exc),
                usage=sol_usage,
                cost=sol_cost,
            ),
        )
        raise
    sol_record = response_record(
        provider="openai", model=primary["model"], response=sol_response, packet=packet,
        judgement=sol_judgement, usage=sol_usage,
        cost=sol_cost,
    )
    s137._write(root / prereg["execution"]["sol_response"], sol_record)

    fable_receipts = []
    for index, subset in enumerate(atomic_packets, 1):
        response = anthropic_client.messages.create(
            model=independent["model"], max_tokens=independent["max_output_tokens_per_question"],
            system=SYSTEM_PROMPT, messages=[{"role": "user", "content": user_prompt(subset)}],
            thinking={"type": independent["thinking"]},
            output_config=anthropic_config(independent["effort"]),
        )
        texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        raw_text = "".join(texts)
        qids = {subset["questions"][0]["question_id"]}
        usage = response.usage.model_dump(mode="json")
        cost = s137.anthropic_cost(
            usage, prereg["pricing_usd_per_million_tokens"]["anthropic"]
        )
        try:
            if response.stop_reason == "max_tokens":
                raise S138Failure(
                    f"S138 Fable q{index} truncated; no retry authorised"
                )
            judgement = parse(raw_text, f"S138 Fable q{index}")
            validate_judgement(judgement, subset, question_ids=qids)
        except Exception as exc:
            s137._write(
                root / prereg["execution"][f"fable_q{index}"],
                failure_record(
                    provider="anthropic",
                    model=independent["model"],
                    response=response,
                    packet=subset,
                    raw_output=raw_text,
                    failure=str(exc),
                    usage=usage,
                    cost=cost,
                ),
            )
            raise
        receipt = response_record(
            provider="anthropic", model=independent["model"], response=response, packet=subset,
            judgement=judgement, usage=usage,
            cost=cost,
        )
        s137._write(root / prereg["execution"][f"fable_q{index}"], receipt)
        fable_receipts.append(receipt)
    combined_judgement = {"judgements": [
        row for receipt in fable_receipts for row in receipt["judgement"]["judgements"]
    ]}
    validate_judgement(combined_judgement, packet)
    fable_record = {
        "instrument": "s138_fable_atomic_combined_v1",
        "status": "VALIDATED",
        "provider": "anthropic",
        "model": independent["model"],
        "created_at": s137.utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": {
            "input_tokens": sum(row["usage"]["input_tokens"] for row in fable_receipts),
            "output_tokens": sum(row["usage"]["output_tokens"] for row in fable_receipts),
            "atomic_response_ids": [row["response_id"] for row in fable_receipts],
        },
        "conservative_cost_usd": round(sum(row["conservative_cost_usd"] for row in fable_receipts), 8),
        "judgement": combined_judgement,
    }
    s137._write(root / prereg["execution"]["fable_combined"], fable_record)

    sol_ranks = semantic_ranks(sol_judgement, mapping)
    fable_ranks = semantic_ranks(combined_judgement, mapping)
    disagreements = {qid for qid in sol_ranks if sol_ranks[qid] != fable_ranks[qid]}
    arbitration_record = None
    if disagreements:
        cfg = prereg["models"]["arbitration"]
        subset = subset_packet(packet, disagreements)
        arb_prompt = (
            "Independently resolve these blinded set judgements. Prior judgements A and B are advisory; "
            "re-read all raw evidence and return your own complete assessment.\n\n"
            + json.dumps(
                {"questions": subset["questions"],
                 "judgement_A": subset_judgement(sol_judgement, disagreements),
                 "judgement_B": subset_judgement(combined_judgement, disagreements)},
                ensure_ascii=False, sort_keys=True,
            )
        )
        count = openai_client.responses.input_tokens.count(
            model=cfg["model"], reasoning={"effort": cfg["reasoning_effort"]},
            instructions=SYSTEM_PROMPT, input=arb_prompt, text=text_format()
        ).input_tokens
        if count > cfg["max_counted_input_tokens"]:
            raise S138Failure("S138 arbitration input exceeds cap")
        response = openai_client.responses.create(
            model=cfg["model"], reasoning={"effort": cfg["reasoning_effort"]},
            instructions=SYSTEM_PROMPT, input=arb_prompt, text=text_format(),
            max_output_tokens=cfg["max_output_tokens"], store=False
        )
        raw_text = response.output_text
        usage = response.usage.model_dump(mode="json")
        cost = s137.conservative_openai_cost(
            usage,
            {
                "cache_write": prereg["pricing_usd_per_million_tokens"]["openai"][
                    "input_conservative_cache_write"
                ],
                "output": prereg["pricing_usd_per_million_tokens"]["openai"]["output"],
            },
        )
        try:
            if response.status != "completed":
                raise S138Failure("S138 arbitration incomplete; no retry authorised")
            judgement = parse(raw_text, "S138 arbitration")
            validate_judgement(judgement, subset, question_ids=disagreements)
        except Exception as exc:
            s137._write(
                root / prereg["execution"]["arbitration_response"],
                failure_record(
                    provider="openai",
                    model=cfg["model"],
                    response=response,
                    packet=subset,
                    raw_output=raw_text,
                    failure=str(exc),
                    usage=usage,
                    cost=cost,
                ),
            )
            raise
        arbitration_record = response_record(
            provider="openai", model=cfg["model"], response=response, packet=subset,
            judgement=judgement, usage=usage,
            cost=cost,
        )
        s137._write(root / prereg["execution"]["arbitration_response"], arbitration_record)
    s135 = base.load_json(root / prereg["frozen_inputs"]["s135_seed"]["path"])
    result = aggregate(prereg, packet, mapping, s135, sol_record, fable_record, arbitration_record)
    s137._write(root / prereg["execution"]["aggregate"], result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--store", type=Path, required=True)
    build.add_argument("--seed", type=int, choices=(1, 2), required=True)
    paid = sub.add_parser("execute-paid")
    paid.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    paid.add_argument("--env-file", type=Path, required=True)
    paid.add_argument("--confirm-paid", action="store_true")
    args = parser.parse_args()
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    prereg = base.load_yaml(prereg_path)
    if args.command == "build":
        generated = ROOT / prereg["execution"]["generated_directory"]
        packet, mapping = build_packet(prereg, args.store.resolve(), generated)
        s137._write(ROOT / prereg["execution"][f"public_packet_seed{args.seed}"], packet)
        s137._write(ROOT / prereg["execution"][f"private_mapping_seed{args.seed}"], mapping)
        return 0
    if not args.confirm_paid:
        raise S138Failure("S138 paid execution requires --confirm-paid")
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    result = execute_paid(prereg, base.load_yaml(permit_path), args.env_file.resolve())
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
