#!/usr/bin/env python3
"""Run the single, checkpointed S161 production-generator answer probe."""
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

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
PREREG = ROOT / "evals/s161_table_preamble_answer_probe_prereg_v1.yaml"
PERMIT = ROOT / "evals/s161_table_preamble_answer_probe_execution_permit_v1.yaml"
RECEIPTS = ROOT / "evals/s161_table_preamble_answer_probe_receipts_v1.json"
RESULT = ROOT / "evals/s161_table_preamble_answer_probe_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
QID = "cat007"
TABLE_ID = "e49a4944-4157-42e3-a1c5-15ec4a6e8926"
FAULT_BEHAVIOR_ID = "8221ec70-6882-41b5-8dd6-705a1a7e739a"
RATINGS_ID = "422ed8a7-8bea-49d6-ac82-da39d6fb9050"
PREAMBLE_ID = "297b07e9-5ec1-43e3-91be-47a685d5c860"
RUNTIME_ENV = {
    "CHUNKS_TABLE": "chunks_v2",
    "POST_RERANK_COVERAGE": "on",
    "TABLE_PREAMBLE_CLOSURE": "on",
    "STRUCTURAL_NEIGHBOR_COVERAGE": "off",
    "CANONICAL_HYQ_COVERAGE": "off",
    "RERANK_POOL_COVERAGE": "off",
    "STRUCTURAL_CASCADE_COVERAGE": "off",
    "COMPATIBILITY_BUNDLE_COVERAGE": "off",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "ANSWER_OBLIGATION_PLANNER": "guided",
    "LLM_MAX_TOKENS": "3500",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    folded = "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()
    return re.sub(r"[`*_~]", "", folded)


def _citation_numbers(answer: str) -> list[int]:
    return [int(value) for value in re.findall(r"\[F(\d+)\]", answer, re.I)]


def _near(text: str, pattern: str, required: list[str], radius: int = 1000) -> bool:
    for match in re.finditer(pattern, text, re.I | re.S):
        window = text[max(0, match.start() - radius) : match.end() + radius]
        if all(re.search(item, window, re.I | re.S) for item in required):
            return True
    return False


def _citation_near(text: str, pattern: str, fragment: int, radius: int = 1000) -> bool:
    return _near(text, pattern, [rf"\[f{fragment}\]"], radius=radius)


def score_answer(
    answer: str,
    fragment_ids: list[str],
    fragment_contents: list[str] | None = None,
) -> dict[str, Any]:
    """Deterministically score the frozen recovered and protected claims."""
    folded = _fold(answer)
    positions = {row_id: index + 1 for index, row_id in enumerate(fragment_ids)}
    table_fragment = positions[TABLE_ID]
    behavior_fragment = positions[FAULT_BEHAVIOR_ID]
    ratings_fragment = positions[RATINGS_ID]
    preamble_fragment = positions[PREAMBLE_ID]
    citations = _citation_numbers(answer)
    invalid = sorted({value for value in citations if not 1 <= value <= len(fragment_ids)})

    qualifier_pattern = (
        r"(?:ch\s*2|canal\s*2).{0,180}"
        r"(?:solo|unicamente).{0,90}(?:2|dos)\s+canales"
        r"|(?:solo|unicamente).{0,90}(?:2|dos)\s+canales.{0,180}"
        r"(?:ch\s*2|canal\s*2)"
    )
    qualifier_present = bool(re.search(qualifier_pattern, folded, re.S))
    qualifier_cited = _citation_near(
        folded, qualifier_pattern, preamble_fragment, radius=700
    )
    contact_terms = [r"\bnc\b", r"\bc\b", r"\b(?:no|na)\b"]

    alarm_pattern = r"rele(?:s)?\s+de\s+alarma|alarma.{0,40}rele"
    alarm_semantic = _near(
        folded,
        alarm_pattern,
        [r"canal\s*1|ch\s*1", r"canal\s*2|ch\s*2", *contact_terms],
        radius=650,
    )
    alarm_cited = _citation_near(folded, alarm_pattern, table_fragment, radius=800)

    fault_relay_pattern = r"rele(?:s)?\s+de\s+(?:averia|fallo)|(?:averia|fallo).{0,40}rele"
    fault_relay_semantic = _near(
        folded,
        fault_relay_pattern,
        [r"canal\s*1|ch\s*1", r"canal\s*2|ch\s*2", r"aux", *contact_terms],
        radius=700,
    )
    fault_relay_cited = _citation_near(
        folded, fault_relay_pattern, table_fragment, radius=900
    )

    fault_conditions_pattern = r"condicion(?:es)?\s+de\s+(?:averia|fallo)|fallo\s+comun"
    fault_conditions_semantic = _near(
        folded,
        fault_conditions_pattern,
        [r"canal\s*1|ch\s*1", r"canal\s*2|ch\s*2", r"comun"],
        radius=650,
    )
    fault_conditions_cited = _citation_near(
        folded, fault_conditions_pattern, behavior_fragment, radius=900
    )

    sounder_pattern = r"salida(?:s)?\s+de\s+sirena|sirena\s*[12]"
    sounder_semantic = _near(
        folded,
        sounder_pattern,
        [r"sirena\s*1", r"(?:17.{0,30}18|17\s*[-/]\s*18)", r"sirena\s*2", r"(?:19.{0,30}20|19\s*[-/]\s*20)"],
        radius=900,
    )
    sounder_cited = _citation_near(folded, sounder_pattern, table_fragment, radius=1000)

    eol_pattern = r"47\s*k\s*(?:ohm|ω)|47\s*kohm"
    eol_semantic = _near(
        folded,
        eol_pattern,
        [r"sirena\s*1|salida\s*1", r"sirena\s*2|salida\s*2"],
        radius=750,
    )
    eol_cited = _citation_near(folded, eol_pattern, table_fragment, radius=900)

    recovered = {
        "alarm_relay_contacts": alarm_semantic and alarm_cited and qualifier_present and qualifier_cited,
        "fault_relay_contacts": fault_relay_semantic and fault_relay_cited and qualifier_present and qualifier_cited,
        "fault_conditions": fault_conditions_semantic and fault_conditions_cited and qualifier_present and qualifier_cited,
        "sounder_outputs": sounder_semantic and sounder_cited and qualifier_present and qualifier_cited,
        "sounder_eol": eol_semantic and eol_cited and qualifier_present and qualifier_cited,
    }

    service_pattern = r"modo\s+de\s+servicio|sin\s+alimentacion|corte\s+de\s+alimentacion"
    service_semantic = _near(
        folded,
        service_pattern,
        [r"modo\s+de\s+servicio", r"sin\s+alimentacion|corte\s+de\s+alimentacion"],
        radius=700,
    )
    non_latched_pattern = r"no\s+(?:esta\s+)?enclavad|no\s+enclavado"
    dc_pattern = r"2(?:[.,]0)?\s*a.{0,35}30\s*v\s*(?:cc|dc)"
    ac_pattern = r"0[.,]5\s*a.{0,35}30\s*v\s*(?:ca|ac)"
    rating_support_fragments = {ratings_fragment}
    if fragment_contents is not None:
        if len(fragment_contents) != len(fragment_ids):
            raise ValueError("fragment content/id length mismatch")
        for index, content in enumerate(fragment_contents, 1):
            source = _fold(content)
            source_dc_pattern = (
                r"\b2(?:[.,]0)?(?:\s*\|\s*|\s+)a.{0,60}30\s*v\s*(?:cc|dc)"
            )
            source_ac_pattern = (
                r"0[.,]5(?:\s*\|\s*|\s+)a.{0,60}30\s*v\s*(?:ca|ac)"
            )
            if re.search(source_dc_pattern, source, re.S) and re.search(
                source_ac_pattern, source, re.S
            ):
                rating_support_fragments.add(index)

    def citation_near_any(pattern: str, fragments: set[int], radius: int) -> bool:
        return any(
            _citation_near(folded, pattern, fragment, radius=radius)
            for fragment in fragments
        )

    protected = {
        "service_or_unpowered": service_semantic
        and _citation_near(folded, service_pattern, behavior_fragment, radius=900),
        "fault_not_latched": bool(re.search(non_latched_pattern, folded, re.S))
        and _citation_near(folded, non_latched_pattern, behavior_fragment, radius=700),
        "relay_rating_dc": bool(re.search(dc_pattern, folded, re.S))
        and citation_near_any(dc_pattern, rating_support_fragments, radius=700),
        "relay_rating_ac": bool(re.search(ac_pattern, folded, re.S))
        and citation_near_any(ac_pattern, rating_support_fragments, radius=700),
    }

    relay_life_pattern = r"(?:10\s*\^\s*5|100\s*[.,]?\s*000|\b105\b).{0,40}operacion"
    unsupported_life = bool(re.search(relay_life_pattern, folded, re.S)) and not _near(
        folded,
        relay_life_pattern,
        [r"no\s+(?:se\s+)?puede\s+confirmar|ocr|ambigu"],
        radius=250,
    )
    return {
        "fragment_positions": positions,
        "rating_support_fragments": sorted(rating_support_fragments),
        "citations": citations,
        "invalid_citations": invalid,
        "qualifier_present": qualifier_present,
        "qualifier_cited": qualifier_cited,
        "recovered": recovered,
        "recovered_covered": sum(recovered.values()),
        "protected": protected,
        "protected_covered": sum(protected.values()),
        "unsupported_relay_life_claim": unsupported_life,
    }


def _configure_runtime(env_file: Path) -> None:
    secrets = dotenv_values(env_file)
    for key, value in secrets.items():
        if value and key not in os.environ:
            os.environ[key] = value
    os.environ.update(RUNTIME_ENV)


def _build_context() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    from src.rag.post_rerank_coverage import apply_post_rerank_coverage_with_trace

    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    row = next(item for item in payload["rows"] if item["qid"] == QID)
    prefix_sha = stable_sha(row["context"])
    context, trace = apply_post_rerank_coverage_with_trace(
        row["question"],
        row["context"],
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=True,
        hyq_enabled=False,
        pool_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
    )
    if stable_sha(context[: len(row["context"])]) != prefix_sha:
        raise RuntimeError("S161 protected prefix mutated")
    appended = context[len(row["context"]) :]
    if [str(item.get("id") or "") for item in appended] != [PREAMBLE_ID]:
        raise RuntimeError("S161 exact table preamble was not uniquely appended")
    return row, context, trace


def validate_authorization() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_INTEGRATION":
        raise RuntimeError("S161 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_ONE_PAID_CALL":
        raise RuntimeError("S161 execution permit is absent")
    for spec in permit["frozen_artifacts"].values():
        path = ROOT / spec["path"]
        if file_sha(path) != spec["sha256"]:
            raise RuntimeError(f"S161 frozen input drift: {spec['path']}")
    return prereg


def execute(env_file: Path) -> dict[str, Any]:
    if RECEIPTS.exists() or RESULT.exists():
        raise RuntimeError("S161 output already exists; retries are forbidden")
    prereg = validate_authorization()
    row, context, trace = _build_context()

    from anthropic import Anthropic
    from scripts.s156_frontier_synthesis_ceiling import build_prompt
    from src.config import ANTHROPIC_API_KEY, LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.generator import generate_answer

    if LLM_MODEL != prereg["runtime"]["generator_model"] or LLM_MAX_TOKENS != 3500:
        raise RuntimeError("S161 generator runtime drift")
    system, prompt = build_prompt({**row, "context": context})
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    counted = client.messages.count_tokens(
        model=LLM_MODEL,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ).input_tokens
    conservative_prices = {"input": 5.0, "output": 25.0}
    worst = (
        counted * conservative_prices["input"]
        + LLM_MAX_TOKENS * conservative_prices["output"]
    ) / 1_000_000
    if worst >= prereg["budget"]["internal_ceiling_usd"]:
        raise RuntimeError("S161 conservative preflight exceeds internal budget")

    response = generate_answer(row["question"], context)
    answer = str(response["answer"])
    receipt = {
        "instrument": "s161_table_preamble_answer_probe_receipts_v1",
        "status": "COMPLETE_BEFORE_SCORING",
        "qid": QID,
        "model": LLM_MODEL,
        "counted_input_tokens": counted,
        "input_tokens": response.get("input_tokens"),
        "output_tokens": response.get("output_tokens"),
        "stop_reason": response.get("stop_reason"),
        "conservative_worst_case_usd": round(worst, 8),
        "answer": answer,
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
    }
    _write(RECEIPTS, receipt)

    scoring = score_answer(
        answer,
        [str(item["id"]) for item in context],
        [str(item.get("content") or "") for item in context],
    )
    passed = (
        scoring["recovered_covered"] == 5
        and scoring["protected_covered"] == 4
        and not scoring["invalid_citations"]
        and response.get("stop_reason") != "max_tokens"
        and not scoring["unsupported_relay_life_claim"]
    )
    body = {
        "instrument": "s161_table_preamble_answer_probe_v1",
        "status": "ANSWER_GO_PROTECTED_REGRESSION_REQUIRED" if passed else "ANSWER_NO_GO",
        "qid": QID,
        "source_context": {
            "protected_prefix_rows": len(row["context"]),
            "served_rows": len(context),
            "appended_ids": trace.get("appended_ids"),
            "protected_prefix_equal": trace.get("protected_prefix_equal"),
            "lane_trace": trace.get("lanes"),
        },
        "generation": {
            "model": LLM_MODEL,
            "input_tokens": response.get("input_tokens"),
            "output_tokens": response.get("output_tokens"),
            "stop_reason": response.get("stop_reason"),
            "conservative_worst_case_usd": round(worst, 8),
            "paid_generator_calls": 1,
            "paid_reranker_calls": 0,
            "paid_judge_calls": 0,
            "retries": 0,
        },
        "scoring": scoring,
        "decision": {
            "answer_probe": "GO" if passed else "NO_GO",
            "production": False,
            "provisional_facts_moved_to_ok": 5 if passed else 0,
            "source_contract_gap_to_synthesis_miss": 0 if passed else 5 - scoring["recovered_covered"],
            "protected_regression_required": passed,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    _write(RESULT, result)
    return result


def rescore_checkpoint() -> dict[str, Any]:
    """Attribute the immutable provider checkpoint without another model call."""
    if not RECEIPTS.exists() or not RESULT.exists():
        raise RuntimeError("S161 paid checkpoint is incomplete")
    row, context, trace = _build_context()
    receipt = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    answer = str(receipt["answer"])
    scoring = score_answer(
        answer,
        [str(item["id"]) for item in context],
        [str(item.get("content") or "") for item in context],
    )
    target_atomic_ok = scoring["recovered_covered"]
    body = {
        "instrument": "s161_table_preamble_answer_probe_attribution_v1",
        "status": "ATOMIC_RECOVERY_GO_RUNTIME_CANDIDATE_NO_GO",
        "source_result": "evals/s161_table_preamble_answer_probe_v1.json",
        "source_receipt": "evals/s161_table_preamble_answer_probe_receipts_v1.json",
        "answer_sha256": receipt["answer_sha256"],
        "scoring": scoring,
        "attribution_correction": {
            "prior_rating_false_negatives": 2,
            "reason": (
                "The immutable answer cites fragment 4, whose exact served table "
                "contains both relay ratings. The initial scorer accepted only "
                "the duplicate support in fragment 9."
            ),
            "provider_retry": False,
            "model_calls": 0,
        },
        "atomic_stage_transitions": {
            "source_contract_gap_to_ok": target_atomic_ok,
            "source_contract_gap_to_synthesis_miss": 5 - target_atomic_ok,
            "document_extraction_hold_remains": 1,
        },
        "decision": {
            "atomic_recovered_claims": "GO" if target_atomic_ok == 5 else "NO_GO",
            "runtime_candidate": "NO_GO" if scoring["unsupported_relay_life_claim"] else "GO",
            "production": False,
            "protected_regression": False,
            "next": "resolve_document_extraction_hold_before_runtime_promotion",
        },
        "source_context": {
            "protected_prefix_equal": trace.get("protected_prefix_equal"),
            "appended_ids": trace.get("appended_ids"),
        },
    }
    output = ROOT / "evals/s161_table_preamble_answer_probe_attribution_v1.json"
    result = {**body, "result_sha256": stable_sha(body)}
    _write(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--rescore", action="store_true")
    args = parser.parse_args()
    _configure_runtime(args.env_file)
    if args.execute:
        print(json.dumps(execute(args.env_file), ensure_ascii=False, indent=2))
        return 0
    if args.rescore:
        print(json.dumps(rescore_checkpoint(), ensure_ascii=False, indent=2))
        return 0
    row, context, trace = _build_context()
    print(
        json.dumps(
            {
                "qid": row["qid"],
                "protected_prefix_rows": len(row["context"]),
                "served_rows": len(context),
                "appended_ids": trace.get("appended_ids"),
                "model_calls": 0,
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
