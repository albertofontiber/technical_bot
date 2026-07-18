#!/usr/bin/env python3
"""Deterministically score the sealed S206 answer A/B."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts.atomic_scorer import match_fact
from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, plan_for
from src.rag.answer_planner import obligation_covered, validate_answer_plan

PREFLIGHT = ROOT / "evals/s206_answer_facet_ab_preflight_v1.json"
RECEIPTS = ROOT / "evals/s206_answer_facet_ab_receipts_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
OUT = ROOT / "evals/s206_answer_facet_ab_score_v1.json"
TARGETS = ("cat018", "hp002", "hp011", "hp017")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def invalid_citations(answer: str, context_rows: int) -> list[int]:
    refs = [int(raw) for raw in re.findall(r"\[F(\d+)\]", answer or "")]
    return sorted({ref for ref in refs if ref < 1 or ref > context_rows})


def hp017_cardinality_contradiction(answer: str) -> bool:
    folded = _fold(answer)
    says_six = bool(re.search(r"\b(?:6|seis)\s+(?:tipos|opciones|modos)", folded))
    option_patterns = (
        r"\bfijo\b",
        r"\bestandar\b",
        r"no\s+silenc",
        r"est(?:andar)?\.?\s*ext",
        r"retextstd|ret(?:ardo)?\s*ext(?:endido)?\s*std",
        r"no\s+sil(?:enc)?\.?\s*ext",
        r"sinretext|sin\s+ret(?:ardo)?\s*ext",
    )
    enumerated = sum(bool(re.search(pattern, folded)) for pattern in option_patterns)
    disclosure = bool(
        re.search(
            r"inconsisten|contradic|dice\s+seis|declara\s+seis|"
            r"enumera\s+siete|lista\s+siete|siete\s+opciones|"
            r"tabla\s+(?:contiene|muestra)\s+siete",
            folded,
        )
    )
    return says_six and enumerated >= 6 and not disclosure


def obligation_cited_near_evidence(answer: str, obligation: Any) -> bool:
    """Require the source citation and covered relation in the same bounded window."""
    marker = f"[F{obligation.fragment_number}]"
    for match in re.finditer(re.escape(marker), answer or ""):
        start = max(0, match.start() - 700)
        end = min(len(answer), match.end() + 300)
        window = answer[start:end]
        if obligation_covered(window, obligation):
            return True
    return False


def _relation_scores(row: dict[str, Any], answer: str) -> dict[str, dict[str, Any]]:
    obligations = [
        item for item in plan_for(row) if item.kind in TARGET_KINDS[row["qid"]]
    ]
    validation = validate_answer_plan(answer, obligations)
    by_id = {item.obligation_id: item for item in obligations}
    output: dict[str, dict[str, Any]] = {}
    for scored in validation["rows"]:
        item = by_id[scored["obligation_id"]]
        source_cited = obligation_cited_near_evidence(answer, item)
        output[item.kind] = {
            "covered": bool(scored["covered"]),
            "source_fragment_cited": source_cited,
            "qualified": bool(scored["covered"] and source_cited),
            "fragment_number": item.fragment_number,
            "obligation_id": item.obligation_id,
        }
    return output


def main() -> int:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    if receipts.get("status") != "COMPLETE" or receipts.get("calls") != 28:
        raise RuntimeError("S206 receipts are incomplete")
    if receipts.get("preflight_sha256") != file_sha(PREFLIGHT):
        raise RuntimeError("S206 receipts/preflight mismatch")

    cohort = {str(row["qid"]): row for row in preflight["rows"]}
    calls: dict[str, dict[str, dict[int, dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for call in receipts["rows"]:
        calls[call["qid"]][call["arm"]][int(call["replicate"])] = call
    if any(
        set(calls[qid][arm]) != {1, 2}
        for qid in cohort
        for arm in ("control", "treatment")
    ):
        raise RuntimeError("S206 2x2 matrix is incomplete")

    prior_covered = {
        (str(row["qid"]), str(row["kind"]))
        for row in residual["rows"]
        if row.get("covered")
    }
    residual_keys = {
        (str(row["qid"]), str(row["kind"]))
        for row in residual["rows"]
        if not row.get("covered")
    }
    relation_rows = []
    target_complete_rows = []
    stable_gains = 0
    relation_regressions = 0
    local_contradictions = 0
    all_invalid_citations: list[dict[str, Any]] = []
    max_token_stops = 0

    for qid in TARGETS:
        row = cohort[qid]
        scored: dict[str, dict[int, dict[str, dict[str, Any]]]] = {
            "control": {},
            "treatment": {},
        }
        complete: dict[str, dict[int, bool]] = {"control": {}, "treatment": {}}
        for arm in ("control", "treatment"):
            for replicate in (1, 2):
                call = calls[qid][arm][replicate]
                answer = call["answer"]
                scored[arm][replicate] = _relation_scores(row, answer)
                complete[arm][replicate] = all(
                    value["qualified"] for value in scored[arm][replicate].values()
                )
                invalid = invalid_citations(answer, row["context_rows"])
                if invalid:
                    all_invalid_citations.append(
                        {"call_id": call["call_id"], "invalid_refs": invalid}
                    )
                max_token_stops += int(call.get("stop_reason") == "max_tokens")
                if qid == "hp017" and hp017_cardinality_contradiction(answer):
                    local_contradictions += 1

        for kind in sorted(TARGET_KINDS[qid]):
            controls = [scored["control"][rep][kind]["qualified"] for rep in (1, 2)]
            treatments = [
                scored["treatment"][rep][kind]["qualified"] for rep in (1, 2)
            ]
            stable_gain = (qid, kind) in residual_keys and all(treatments) and not any(controls)
            protected = (qid, kind) in prior_covered or all(controls)
            regression = protected and not all(treatments)
            stable_gains += int(stable_gain)
            relation_regressions += int(regression)
            relation_rows.append(
                {
                    "qid": qid,
                    "kind": kind,
                    "control_qualified": controls,
                    "treatment_qualified": treatments,
                    "stable_gain": stable_gain,
                    "protected_relation": protected,
                    "regression": regression,
                }
            )
        stable_complete_gain = all(complete["treatment"].values()) and not any(
            complete["control"].values()
        )
        target_complete_rows.append(
            {
                "qid": qid,
                "control_complete": [complete["control"][rep] for rep in (1, 2)],
                "treatment_complete": [complete["treatment"][rep] for rep in (1, 2)],
                "stable_complete_gain": stable_complete_gain,
            }
        )

    guardrail_rows = []
    guardrail_regressions = 0
    unstable_guardrail_controls = 0
    for qid, row in cohort.items():
        if row["role"] == "target":
            continue
        for arm in ("control", "treatment"):
            for rep in (1, 2):
                call = calls[qid][arm][rep]
                invalid = invalid_citations(call["answer"], row["context_rows"])
                if invalid:
                    all_invalid_citations.append(
                        {"call_id": call["call_id"], "invalid_refs": invalid}
                    )
                max_token_stops += int(call.get("stop_reason") == "max_tokens")
        for fact in row["facts"]:
            arm_scores: dict[str, list[bool]] = {"control": [], "treatment": []}
            details: dict[str, list[str]] = {"control": [], "treatment": []}
            for arm in ("control", "treatment"):
                for rep in (1, 2):
                    call = calls[qid][arm][rep]
                    present, method, detail = match_fact(
                        fact.get("valor"), fact.get("texto", ""), call["answer"]
                    )
                    arm_scores[arm].append(present is True)
                    details[arm].append(f"{method}:{detail}")
            stable_control = all(arm_scores["control"])
            regression = stable_control and not all(arm_scores["treatment"])
            unstable_guardrail_controls += int(not stable_control)
            guardrail_regressions += int(regression)
            guardrail_rows.append(
                {
                    "qid": qid,
                    "fact_key": fact["key"],
                    "control_present": arm_scores["control"],
                    "treatment_present": arm_scores["treatment"],
                    "stable_control": stable_control,
                    "regression": regression,
                    "details": details,
                }
            )

    stable_complete_gains = sum(
        row["stable_complete_gain"] for row in target_complete_rows
    )
    checks = {
        "stable_residual_relation_gain_min_4": stable_gains >= 4,
        "stable_target_questions_complete_gain_min_2": stable_complete_gains >= 2,
        "previously_covered_relation_regressions_zero": relation_regressions == 0,
        "protected_core_regressions_zero": guardrail_regressions == 0,
        "all_guardrail_controls_mechanically_stable": unstable_guardrail_controls == 0,
        "local_new_contradictions_zero": local_contradictions == 0,
        "invalid_citations_zero": not all_invalid_citations,
        "max_token_stops_zero": max_token_stops == 0,
    }
    local_go = all(checks.values())
    body: dict[str, Any] = {
        "schema": "s206_answer_facet_ab_score_v1",
        "status": "LOCAL_GO_PENDING_SEALED_DUO_RESULT_REVIEW" if local_go else "NO_GO",
        "inputs": {
            "preflight_sha256": file_sha(PREFLIGHT),
            "receipts_sha256": file_sha(RECEIPTS),
            "residual_sha256": file_sha(RESIDUAL),
        },
        "metrics": {
            "stable_residual_relation_gains": stable_gains,
            "stable_target_questions_complete_gains": stable_complete_gains,
            "relation_regressions": relation_regressions,
            "guardrail_regressions": guardrail_regressions,
            "unstable_guardrail_controls": unstable_guardrail_controls,
            "local_contradictions": local_contradictions,
            "invalid_citation_calls": len(all_invalid_citations),
            "max_token_stops": max_token_stops,
        },
        "relation_rows": relation_rows,
        "target_complete_rows": target_complete_rows,
        "guardrail_rows": guardrail_rows,
        "invalid_citations": all_invalid_citations,
        "checks": checks,
        "relation_proxy_projection": {
            "stable_s141_relations_gained": stable_gains,
            "canonical_facts_ok_before": 143,
            "canonical_facts_ok_after": None,
            "claim_98_percent_allowed": False,
            "reason": (
                "S141 relation coverage is a diagnostic proxy. Canonical fact credit "
                "requires a separate atomic fact adjudication after the semantic duo."
            ),
        },
        "decision": {
            "production": False,
            "production_default": "off",
            "facts_moved_to_ok": 0,
            "next": (
                "RUN_ONE_SEALED_SOL_XHIGH_PLUS_FABLE_SEMANTIC_RESULT_REVIEW"
                if local_go
                else "CLOSE_S206_NO_GO_WITHOUT_PROMPT_ITERATION"
            ),
        },
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "metrics": body["metrics"]}, ensure_ascii=False))
    return 0 if local_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
