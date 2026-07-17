#!/usr/bin/env python3
"""Build and execute the bounded S137 blinded semantic adjudication."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as base
from scripts import s135_representative_chunks_shadow_v2 as shadow
from scripts import s136_chunks_v3_loss_attribution as s136


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s137_blinded_chunks_semantic_adjudication_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s137_blinded_chunks_semantic_adjudication_execution_permit_v1.yaml"

RELEVANCE = {"DIRECT", "SUPPORTING", "IRRELEVANT", "UNCERTAIN"}
ANSWERABILITY = {"COMPLETE", "PARTIAL", "NONE"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
SUCCESS = "CANDIDATE_SUCCESS_AT_10"
FAILURE = "REAL_CANDIDATE_RETRIEVAL_LOSS"
HOLD = "HOLD"

SYSTEM_PROMPT = """You are an independent semantic evidence adjudicator for technical-manual retrieval.
Judge only whether the supplied RAW SOURCE CONTENT supports the user's question. The evidence labels are
opaque and randomly ordered. You do not know retrieval arm, rank, score, gold status, or chunk provenance.
Do not infer those hidden values. Treat Spanish and English evidence equivalently. Do not reward keyword
overlap without the required technical relation, value, condition, or procedure. Do not use outside
knowledge to fill missing evidence.

For every question:
1. Assess EVERY evidence item exactly once as DIRECT, SUPPORTING, IRRELEVANT, or UNCERTAIN.
2. DIRECT means the item establishes at least one answer-critical fact, relation, value, or procedure.
3. SUPPORTING adds useful context but is not independently answer-critical.
4. Record exact or near duplicates by opaque evidence ID.
5. If the supplied evidence can completely answer the question, choose the smallest sufficient set of
   evidence IDs. Every selected item must be DIRECT or SUPPORTING and at least one must be DIRECT.
6. If answerability is PARTIAL or NONE, minimum_sufficient_evidence_ids must be empty.
7. Keep each rationale under 90 words. Return only the required structured JSON."""


class S137Failure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def schema() -> dict[str, Any]:
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
    question = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "question_id",
            "answerability",
            "minimum_sufficient_evidence_ids",
            "evidence_assessments",
            "confidence",
            "rationale",
        ],
        "properties": {
            "question_id": {"type": "string"},
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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["judgements"],
        "properties": {"judgements": {"type": "array", "items": question}},
    }


def validate_prereg(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    specs = {"design": prereg["design"], **prereg["frozen_inputs"]}
    for name, spec in specs.items():
        path = root / spec["path"]
        if base.file_sha(path) != spec["sha256"]:
            raise S137Failure(f"S137 dependency drift: {name}")
    s136_gate = base.load_yaml(root / prereg["frozen_inputs"]["s136_gate"]["path"])
    if s136_gate.get("status") != "NO_GO":
        raise S137Failure("S136 gate is no longer the frozen NO_GO input")
    expected = sorted(prereg["population"]["question_ids"])
    seed = base.load_json(root / prereg["frozen_inputs"]["s136_seed"]["path"])
    observed = sorted(row["question_id"] for row in seed["attributions"])
    if observed != expected:
        raise S137Failure("S137 question population drift")


def blind_label(seed: str, question_id: str, candidate_id: str) -> str:
    digest = hashlib.sha256(f"{seed}|{question_id}|{candidate_id}".encode()).hexdigest()
    return f"E-{digest[:12].upper()}"


def _reconstruct(
    prereg: dict[str, Any], store: Path, *, root: Path = ROOT
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    s136_prereg = base.load_yaml(
        root / prereg["frozen_inputs"]["s136_prereg"]["path"]
    )
    s136.validate_contract(s136_prereg, root=root)
    s135_prereg = base.load_yaml(
        root / prereg["frozen_inputs"]["s135_prereg"]["path"]
    )
    shadow.validate_contract(s135_prereg, root=root)
    cohort, pairs = base.load_cohort(s135_prereg, root=root)
    cohort = shadow.plan_queries(cohort)
    selected = base.load_selected_metadata(s135_prereg, pairs, root=root)
    baseline, _ = base.load_baseline_rows(s135_prereg, selected, root=root)
    records = base.validate_raw_store(s135_prereg, store)
    candidate, _ = shadow.materialize_candidate_rows(
        s135_prereg, selected, baseline, records
    )
    gold, _ = shadow.build_provenance_gold(cohort, candidate, records)
    return cohort, candidate, gold


def assert_public_packet_blind(packet: dict[str, Any]) -> None:
    forbidden = {
        "arm",
        "rank",
        "score",
        "database_id",
        "document_id",
        "chunk_id",
        "extraction_sha256",
        "strict_context_donor",
        "is_gold_member",
        "context",
        "s135_classification",
        "s136_classification",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            overlap = forbidden.intersection(value)
            if overlap:
                raise S137Failure(f"blind packet leaks fields: {sorted(overlap)}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(packet)


def build_packet(
    prereg: dict[str, Any], store: Path, *, root: Path = ROOT
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_prereg(prereg, root=root)
    cohort, candidate, gold = _reconstruct(prereg, store, root=root)
    s136_seed = base.load_json(root / prereg["frozen_inputs"]["s136_seed"]["path"])
    attr_by_qid = {row["question_id"]: row for row in s136_seed["attributions"]}
    cohort_by_qid = {row["question_id"]: row for row in cohort}
    candidate_by_id = {row["id"]: row for row in candidate}
    gold_by_qid: dict[str, set[str]] = collections.defaultdict(set)
    for row in gold:
        if row["arm"] == "candidate_v3":
            gold_by_qid[row["question_id"]].add(row["chunk_id"])

    public_questions = []
    private_questions = []
    top_n = int(prereg["population"]["candidate_top_ranked_items"])
    seed = prereg["blind_packet"]["deterministic_seed"]
    for question_id in sorted(prereg["population"]["question_ids"]):
        attr = attr_by_qid[question_id]
        ranked_rows = attr["top_candidate_rows"]
        ranked_by_id = {row["id"]: row for row in ranked_rows}
        selected_ids = [row["id"] for row in ranked_rows[:top_n]]
        for identifier in sorted(gold_by_qid[question_id]):
            if identifier not in selected_ids:
                selected_ids.append(identifier)
        if len(selected_ids) != len(set(selected_ids)):
            raise S137Failure(f"duplicate selected ID: {question_id}")
        labels = {
            identifier: blind_label(seed, question_id, identifier)
            for identifier in selected_ids
        }
        if len(labels.values()) != len(set(labels.values())):
            raise S137Failure(f"blind-label collision: {question_id}")
        public_evidence = []
        private_evidence = []
        for identifier in sorted(selected_ids, key=lambda item: labels[item]):
            row = candidate_by_id[identifier]
            public_evidence.append(
                {
                    "evidence_id": labels[identifier],
                    "section_title": row.get("section_title"),
                    "section_path": row.get("section_path"),
                    "page_number": row.get("page_number"),
                    "source_content": row["content"],
                }
            )
            rank_row = ranked_by_id.get(identifier)
            private_evidence.append(
                {
                    "evidence_id": labels[identifier],
                    "candidate_id": identifier,
                    "candidate_rank": rank_row.get("rank") if rank_row else None,
                    "candidate_score": rank_row.get("score") if rank_row else None,
                    "strict_context_donor": (
                        rank_row.get("strict_context_donor")
                        if rank_row
                        else row.get("context") is not None
                    ),
                    "is_gold_member": identifier in gold_by_qid[question_id],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                }
            )
        q = cohort_by_qid[question_id]
        public_questions.append(
            {
                "question_id": question_id,
                "question": q["question"],
                "manufacturer": q["manufacturer"],
                "product_model": q["product_model"],
                "evidence": public_evidence,
            }
        )
        private_questions.append(
            {
                "question_id": question_id,
                "s136_baseline_rank": attr["recomputed_baseline_rank"],
                "s136_candidate_rank": attr["recomputed_candidate_rank"],
                "s136_classification": attr["classification"],
                "evidence": private_evidence,
            }
        )

    packet = {
        "instrument": "s137_blinded_packet_v1",
        "status": "FROZEN_BLIND_PACKET",
        "questions": public_questions,
        "checks": {
            "question_count": len(public_questions),
            "top_ranked_items_per_question": top_n,
            "context_excluded": True,
            "ranks_and_gold_excluded": True,
        },
        "manifests": {"questions_sha256": base.canonical_sha(public_questions)},
    }
    assert_public_packet_blind(packet)
    mapping = {
        "instrument": "s137_private_mapping_v1",
        "status": "PRIVATE_NOT_JUDGE_INPUT",
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "questions": private_questions,
        "manifests": {"questions_sha256": base.canonical_sha(private_questions)},
    }
    return packet, mapping


def packet_for_judge(packet: dict[str, Any]) -> str:
    return json.dumps({"questions": packet["questions"]}, ensure_ascii=False, sort_keys=True)


def user_prompt(packet: dict[str, Any]) -> str:
    return "Adjudicate this frozen blinded packet.\n\n" + packet_for_judge(packet)


def validate_judgement(
    judgement: dict[str, Any], packet: dict[str, Any], *, question_ids: set[str] | None = None
) -> None:
    errors = sorted(
        Draft202012Validator(schema()).iter_errors(judgement),
        key=lambda error: list(error.path),
    )
    if errors:
        raise S137Failure(f"judgement schema violation: {errors[0].message}")
    packet_by_qid = {row["question_id"]: row for row in packet["questions"]}
    expected_qids = question_ids if question_ids is not None else set(packet_by_qid)
    rows = judgement.get("judgements")
    if not isinstance(rows, list):
        raise S137Failure("judgement missing judgements list")
    observed_qids = [row.get("question_id") for row in rows]
    if len(observed_qids) != len(set(observed_qids)) or set(observed_qids) != expected_qids:
        raise S137Failure("judgement question set mismatch")
    for row in rows:
        qid = row["question_id"]
        expected_ids = {item["evidence_id"] for item in packet_by_qid[qid]["evidence"]}
        assessments = row.get("evidence_assessments")
        if not isinstance(assessments, list):
            raise S137Failure(f"missing evidence assessments: {qid}")
        assessed_ids = [item.get("evidence_id") for item in assessments]
        if len(assessed_ids) != len(set(assessed_ids)) or set(assessed_ids) != expected_ids:
            raise S137Failure(f"evidence assessment set mismatch: {qid}")
        by_id = {item["evidence_id"]: item for item in assessments}
        for item in assessments:
            if item.get("relevance") not in RELEVANCE:
                raise S137Failure(f"unknown relevance: {qid}")
            redundant = item.get("redundant_with")
            if not isinstance(redundant, list) or not set(redundant).issubset(expected_ids):
                raise S137Failure(f"unknown redundant_with ID: {qid}")
            if item["evidence_id"] in redundant:
                raise S137Failure(f"self redundancy: {qid}")
        if row.get("answerability") not in ANSWERABILITY:
            raise S137Failure(f"unknown answerability: {qid}")
        if row.get("confidence") not in CONFIDENCE:
            raise S137Failure(f"unknown confidence: {qid}")
        minimum = row.get("minimum_sufficient_evidence_ids")
        if not isinstance(minimum, list) or len(minimum) != len(set(minimum)):
            raise S137Failure(f"invalid minimum set: {qid}")
        if not set(minimum).issubset(expected_ids):
            raise S137Failure(f"unknown minimum-set ID: {qid}")
        if row["answerability"] == "COMPLETE":
            if not minimum:
                raise S137Failure(f"complete judgement without minimum set: {qid}")
            labels = [by_id[item]["relevance"] for item in minimum]
            if not set(labels).issubset({"DIRECT", "SUPPORTING"}) or "DIRECT" not in labels:
                raise S137Failure(f"inconsistent complete minimum set: {qid}")
        elif minimum:
            raise S137Failure(f"non-complete judgement has minimum set: {qid}")
        if len(str(row.get("rationale", "")).split()) > 90:
            raise S137Failure(f"rationale exceeds 90 words: {qid}")


def terminal_decisions(
    judgement: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, str]:
    map_by_qid = {
        row["question_id"]: {
            item["evidence_id"]: item["candidate_rank"] for item in row["evidence"]
        }
        for row in mapping["questions"]
    }
    output = {}
    for row in judgement["judgements"]:
        minimum = row["minimum_sufficient_evidence_ids"]
        ranks = [map_by_qid[row["question_id"]][item] for item in minimum]
        output[row["question_id"]] = (
            SUCCESS
            if row["answerability"] == "COMPLETE"
            and minimum
            and all(rank is not None and rank <= 10 for rank in ranks)
            else FAILURE
        )
    return output


def _openai_format() -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "s137_semantic_adjudication",
            "schema": schema(),
            "strict": True,
        },
        "verbosity": "low",
    }


def _anthropic_output_config(effort: str) -> dict[str, Any]:
    return {"effort": effort, "format": {"type": "json_schema", "schema": schema()}}


def conservative_openai_cost(usage: dict[str, Any], pricing: dict[str, Any]) -> float:
    return round(
        (
            int(usage.get("input_tokens", 0)) * float(pricing["cache_write"])
            + int(usage.get("output_tokens", 0)) * float(pricing["output"])
        )
        / 1_000_000,
        8,
    )


def anthropic_cost(usage: dict[str, Any], pricing: dict[str, Any]) -> float:
    return round(
        (
            int(usage.get("input_tokens", 0)) * float(pricing["input"])
            + int(usage.get("output_tokens", 0)) * float(pricing["output"])
        )
        / 1_000_000,
        8,
    )


def worst_case_cost(
    prereg: dict[str, Any], openai_input: int, anthropic_input: int
) -> float:
    prices = prereg["pricing_usd_per_million_tokens"]
    primary = prereg["models"]["primary"]
    independent = prereg["models"]["independent"]
    arbitration = prereg["models"]["optional_arbitration"]
    total = (
        openai_input * prices["openai_gpt_5_6_sol"]["cache_write"]
        + primary["max_output_tokens"] * prices["openai_gpt_5_6_sol"]["output"]
        + anthropic_input * prices["anthropic_claude_fable_5"]["input"]
        + independent["max_output_tokens"] * prices["anthropic_claude_fable_5"]["output"]
        + arbitration["max_counted_input_tokens"]
        * prices["openai_gpt_5_6_sol"]["cache_write"]
        + arbitration["max_output_tokens"] * prices["openai_gpt_5_6_sol"]["output"]
    ) / 1_000_000
    return round(total, 8)


def validate_permit(prereg: dict[str, Any], permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise S137Failure("S137 paid execution permit is not GO")
    if base.file_sha(root / permit["preregistration"]["path"]) != permit["preregistration"]["sha256"]:
        raise S137Failure("S137 preregistration drift after permit")
    for name in ("runner", "tests", "public_packet", "private_mapping"):
        spec = permit[name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise S137Failure(f"S137 permitted artifact drift: {name}")
    if permit["external_usd_ceiling"] != prereg["budget"]["stricter_s137_runtime_ceiling_usd"]:
        raise S137Failure("S137 permit budget drift")


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    base.write_payload(path, payload)


def _parse_json(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise S137Failure(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise S137Failure(f"{label} returned non-object JSON")
    return value


def _openai_call(client: Any, model_cfg: dict[str, Any], prompt: str) -> tuple[Any, str]:
    response = client.responses.create(
        model=model_cfg["model"],
        reasoning={"effort": model_cfg["reasoning_effort"]},
        instructions=SYSTEM_PROMPT,
        input=prompt,
        text=_openai_format(),
        max_output_tokens=model_cfg["max_output_tokens"],
        store=False,
    )
    if getattr(response, "status", None) != "completed":
        raise S137Failure(f"OpenAI response not completed: {getattr(response, 'status', None)}")
    return response, response.output_text


def _anthropic_call(client: Any, model_cfg: dict[str, Any], prompt: str) -> tuple[Any, str]:
    response = client.messages.create(
        model=model_cfg["model"],
        max_tokens=model_cfg["max_output_tokens"],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": model_cfg["thinking"]},
        output_config=_anthropic_output_config(model_cfg["effort"]),
    )
    if response.stop_reason == "max_tokens":
        raise S137Failure("Anthropic response truncated at max_tokens")
    texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not texts:
        raise S137Failure("Anthropic response has no text block")
    return response, "".join(texts)


def _response_record(
    *,
    provider: str,
    model: str,
    packet: dict[str, Any],
    response: Any,
    judgement: dict[str, Any],
    usage: dict[str, Any],
    cost: float,
) -> dict[str, Any]:
    return {
        "instrument": "s137_blinded_judge_response_v1",
        "status": "VALIDATED",
        "provider": provider,
        "model": model,
        "response_id": response.id,
        "created_at": utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "usage": usage,
        "conservative_cost_usd": cost,
        "judgement": judgement,
    }


def _subset_packet(packet: dict[str, Any], question_ids: set[str]) -> dict[str, Any]:
    questions = [row for row in packet["questions"] if row["question_id"] in question_ids]
    return {
        **packet,
        "questions": questions,
        "manifests": {"questions_sha256": base.canonical_sha(questions)},
    }


def _subset_judgement(judgement: dict[str, Any], question_ids: set[str]) -> dict[str, Any]:
    return {"judgements": [
        row for row in judgement["judgements"] if row["question_id"] in question_ids
    ]}


def arbitration_prompt(
    packet: dict[str, Any], first: dict[str, Any], second: dict[str, Any]
) -> str:
    payload = {
        "questions": packet["questions"],
        "independent_judgement_A": first,
        "independent_judgement_B": second,
    }
    return (
        "Independently resolve the semantic disagreements in this blinded packet. "
        "The two prior judgements are anonymised and advisory; re-read the raw source content, "
        "apply the same rubric, and return your own complete assessment for every supplied item.\n\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def build_aggregate(
    packet: dict[str, Any], mapping: dict[str, Any], sol: dict[str, Any],
    fable: dict[str, Any], arbitration: dict[str, Any] | None
) -> dict[str, Any]:
    sol_decisions = terminal_decisions(sol["judgement"], mapping)
    fable_decisions = terminal_decisions(fable["judgement"], mapping)
    disagreements = {
        qid for qid in sol_decisions if sol_decisions[qid] != fable_decisions[qid]
    }
    arbitration_decisions = (
        terminal_decisions(arbitration["judgement"], mapping) if arbitration else {}
    )
    final = {}
    for qid in sorted(sol_decisions):
        if qid not in disagreements:
            final[qid] = sol_decisions[qid]
        else:
            final[qid] = arbitration_decisions.get(qid, HOLD)
    question_rows = []
    mapping_by_qid = {row["question_id"]: row for row in mapping["questions"]}
    for qid in sorted(final):
        question_rows.append(
            {
                "question_id": qid,
                "sol_terminal": sol_decisions[qid],
                "fable_terminal": fable_decisions[qid],
                "initial_agreement": qid not in disagreements,
                "arbitration_terminal": arbitration_decisions.get(qid),
                "final_terminal": final[qid],
                "frozen_baseline_rank": mapping_by_qid[qid]["s136_baseline_rank"],
                "frozen_candidate_exact_gold_rank": mapping_by_qid[qid]["s136_candidate_rank"],
            }
        )
    costs = [sol["conservative_cost_usd"], fable["conservative_cost_usd"]]
    if arbitration:
        costs.append(arbitration["conservative_cost_usd"])
    checks = {
        "question_set_exact": set(final) == {
            row["question_id"] for row in packet["questions"]
        },
        "all_terminal": all(value in {SUCCESS, FAILURE} for value in final.values()),
        "all_three_candidate_success_at_10": len(final) == 3
        and all(value == SUCCESS for value in final.values()),
        "actual_cost_below_internal_ceiling": sum(costs) < 10,
        "facts_moved_to_ok_zero": True,
    }
    go = all(checks.values())
    return {
        "instrument": "s137_blinded_chunks_semantic_adjudication_v1",
        "status": "GO" if go else "NO_GO",
        "claim": "semantic_adjudication_of_three_frozen_s135_losses_only",
        "checks": checks,
        "questions": question_rows,
        "summary": {
            "candidate_success_at_10": sum(value == SUCCESS for value in final.values()),
            "real_candidate_retrieval_loss": sum(value == FAILURE for value in final.values()),
            "hold": sum(value == HOLD for value in final.values()),
            "initial_disagreements": len(disagreements),
        },
        "cost": {
            "paid_calls": len(costs),
            "conservative_actual_usd": round(sum(costs), 8),
            "internal_ceiling_usd": 10,
            "user_ceiling_usd": 50,
        },
        "authorization": {
            "chunks_v3_production_migration": False,
            "migration_apply": False,
            "deploy": False,
            "facts_moved_to_ok": 0,
        },
        "decision": (
            "GO_TO_RECONCILE_S135_PROMOTION_GATE"
            if go
            else "NO_GO_KEEP_CHUNKS_V3_OUT_OF_PRODUCTION"
        ),
    }


def execute_paid(
    prereg: dict[str, Any], permit: dict[str, Any], env_file: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_prereg(prereg, root=root)
    validate_permit(prereg, permit, root=root)
    packet1_path = root / prereg["execution"]["public_packet_seed1"]
    packet2_path = root / prereg["execution"]["public_packet_seed2"]
    mapping1_path = root / prereg["execution"]["private_mapping_seed1"]
    mapping2_path = root / prereg["execution"]["private_mapping_seed2"]
    if packet1_path.read_bytes() != packet2_path.read_bytes():
        raise S137Failure("public packet seeds are not byte-identical")
    if mapping1_path.read_bytes() != mapping2_path.read_bytes():
        raise S137Failure("private mapping seeds are not byte-identical")
    packet = base.load_json(packet1_path)
    mapping = base.load_json(mapping1_path)
    assert_public_packet_blind(packet)

    from dotenv import dotenv_values
    from anthropic import Anthropic
    from openai import OpenAI

    secrets = dotenv_values(env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise S137Failure("provider API key missing")
    openai_client = OpenAI(api_key=openai_key)
    anthropic_client = Anthropic(api_key=anthropic_key)
    prompt = user_prompt(packet)
    primary = prereg["models"]["primary"]
    independent = prereg["models"]["independent"]
    open_count = openai_client.responses.input_tokens.count(
        model=primary["model"],
        reasoning={"effort": primary["reasoning_effort"]},
        instructions=SYSTEM_PROMPT,
        input=prompt,
        text=_openai_format(),
    ).input_tokens
    anth_count = anthropic_client.messages.count_tokens(
        model=independent["model"],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": independent["thinking"]},
        output_config=_anthropic_output_config(independent["effort"]),
    ).input_tokens
    if open_count > primary["max_counted_input_tokens"]:
        raise S137Failure("OpenAI counted input exceeds preregistered cap")
    if anth_count > independent["max_counted_input_tokens"]:
        raise S137Failure("Anthropic counted input exceeds preregistered cap")
    worst = worst_case_cost(prereg, open_count, anth_count)
    ceiling = prereg["budget"]["stricter_s137_runtime_ceiling_usd"]
    preflight = {
        "instrument": "s137_paid_preflight_v1",
        "status": "GO" if worst < ceiling else "NO_GO",
        "created_at": utc_now(),
        "packet_questions_sha256": packet["manifests"]["questions_sha256"],
        "counted_input_tokens": {"openai": open_count, "anthropic": anth_count},
        "worst_case_usd_including_optional_arbitration": worst,
        "internal_ceiling_usd": ceiling,
        "user_ceiling_usd": prereg["budget"]["user_authorized_ceiling_usd"],
    }
    _write(root / prereg["execution"]["paid_preflight"], preflight)
    if worst >= ceiling:
        raise S137Failure("S137 worst-case cost exceeds internal ceiling")

    prices = prereg["pricing_usd_per_million_tokens"]
    sol_response, sol_text = _openai_call(openai_client, primary, prompt)
    sol_judgement = _parse_json(sol_text, "Sol")
    validate_judgement(sol_judgement, packet)
    sol_usage = sol_response.usage.model_dump(mode="json")
    sol_record = _response_record(
        provider="openai",
        model=primary["model"],
        packet=packet,
        response=sol_response,
        judgement=sol_judgement,
        usage=sol_usage,
        cost=conservative_openai_cost(sol_usage, prices["openai_gpt_5_6_sol"]),
    )
    _write(root / prereg["execution"]["sol_response"], sol_record)

    fable_response, fable_text = _anthropic_call(
        anthropic_client, independent, prompt
    )
    fable_judgement = _parse_json(fable_text, "Fable")
    validate_judgement(fable_judgement, packet)
    fable_usage = fable_response.usage.model_dump(mode="json")
    fable_record = _response_record(
        provider="anthropic",
        model=independent["model"],
        packet=packet,
        response=fable_response,
        judgement=fable_judgement,
        usage=fable_usage,
        cost=anthropic_cost(fable_usage, prices["anthropic_claude_fable_5"]),
    )
    _write(root / prereg["execution"]["fable_response"], fable_record)

    sol_terminal = terminal_decisions(sol_judgement, mapping)
    fable_terminal = terminal_decisions(fable_judgement, mapping)
    disagreements = {
        qid for qid in sol_terminal if sol_terminal[qid] != fable_terminal[qid]
    }
    arbitration_record = None
    if disagreements:
        arbitration_cfg = prereg["models"]["optional_arbitration"]
        subset = _subset_packet(packet, disagreements)
        arb_prompt = arbitration_prompt(
            subset,
            _subset_judgement(sol_judgement, disagreements),
            _subset_judgement(fable_judgement, disagreements),
        )
        arb_count = openai_client.responses.input_tokens.count(
            model=arbitration_cfg["model"],
            reasoning={"effort": arbitration_cfg["reasoning_effort"]},
            instructions=SYSTEM_PROMPT,
            input=arb_prompt,
            text=_openai_format(),
        ).input_tokens
        if arb_count > arbitration_cfg["max_counted_input_tokens"]:
            raise S137Failure("arbitration counted input exceeds preregistered cap")
        reserved = (
            arb_count * prices["openai_gpt_5_6_sol"]["cache_write"]
            + arbitration_cfg["max_output_tokens"]
            * prices["openai_gpt_5_6_sol"]["output"]
        ) / 1_000_000
        spent = sol_record["conservative_cost_usd"] + fable_record["conservative_cost_usd"]
        if spent + reserved >= ceiling:
            raise S137Failure("arbitration would exceed S137 internal ceiling")
        arb_response, arb_text = _openai_call(
            openai_client, arbitration_cfg, arb_prompt
        )
        arb_judgement = _parse_json(arb_text, "arbitration")
        validate_judgement(arb_judgement, subset, question_ids=disagreements)
        arb_usage = arb_response.usage.model_dump(mode="json")
        arbitration_record = _response_record(
            provider="openai",
            model=arbitration_cfg["model"],
            packet=subset,
            response=arb_response,
            judgement=arb_judgement,
            usage=arb_usage,
            cost=conservative_openai_cost(
                arb_usage, prices["openai_gpt_5_6_sol"]
            ),
        )
        _write(root / prereg["execution"]["arbitration_response"], arbitration_record)

    aggregate = build_aggregate(
        packet, mapping, sol_record, fable_record, arbitration_record
    )
    _write(root / prereg["execution"]["aggregate"], aggregate)
    return aggregate


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
        packet, mapping = build_packet(prereg, args.store.resolve())
        _write(ROOT / prereg["execution"][f"public_packet_seed{args.seed}"], packet)
        _write(ROOT / prereg["execution"][f"private_mapping_seed{args.seed}"], mapping)
        return 0
    if not args.confirm_paid:
        raise S137Failure("paid execution requires --confirm-paid")
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    aggregate = execute_paid(
        prereg, base.load_yaml(permit_path), args.env_file.resolve()
    )
    return 0 if aggregate["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
