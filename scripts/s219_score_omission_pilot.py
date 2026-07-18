#!/usr/bin/env python3
"""Score S219 only after generation has sealed every answer."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atomic_scorer import match_fact  # noqa: E402
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PREREG = ROOT / "evals/s219_omission_pilot_prereg_v1.yaml"
GENERATION = ROOT / "evals/s219_omission_generation_result_v1.json"
SCORE_PACKET = ROOT / "evals/s219_omission_score_packet_v1.json"
RESULT = ROOT / "evals/s219_omission_pilot_result_v1.json"


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _covered(value: Any, text: Any, answer: str) -> bool:
    return match_fact(value, text or "", answer)[0] is True


def verify() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S219 preregistration is not frozen")
    for label, spec in prereg["frozen_score_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S219 frozen score input drift: {label}")
    generation = _sealed(GENERATION)
    score = _sealed(SCORE_PACKET)
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or len(generation.get("items") or []) != 9
        or score.get("status") != "SEALED_SCORE_ONLY"
        or len(score.get("items") or []) != 9
        or generation.get("target_calls") != 0
    ):
        raise ValueError("S219 generation or scoring geometry drift")
    return prereg, generation, score


def main() -> int:
    if RESULT.exists():
        raise RuntimeError("S219 result exists; rescoring is forbidden")
    prereg, generation, score = verify()
    generated = {row["item_id"]: row for row in generation["items"]}
    score_by = {row["item_id"]: row for row in score["items"]}
    if set(generated) != set(score_by):
        raise ValueError("S219 generation/score identity mismatch")

    development_rows = []
    synthesis_gains: list[str] = []
    protected_regressions: list[str] = []
    kidde_rows = []
    kidde_regressions: list[str] = []
    kidde_baseline_covered = 0
    kidde_candidate_covered = 0
    candidate_invalid_citations: dict[str, list[int]] = {}

    for item_id, item in score_by.items():
        output = generated[item_id]
        baseline = output["baseline_answer"]
        candidate = output["candidate_answer"]
        invalid = invalid_citations(candidate, int(output["fragment_count"]))
        if invalid:
            candidate_invalid_citations[item_id] = invalid
        if item["role"] == "historical_multichunk_development":
            gained = []
            for fact in item["synthesis_miss_facts"]:
                if _covered(fact.get("valor"), fact.get("texto"), candidate):
                    gained.append(str(fact["key"]))
                    synthesis_gains.append(str(fact["key"]))
            regressed = []
            for fact in item["historical_ok_facts"]:
                if not _covered(fact.get("valor"), fact.get("texto"), candidate):
                    regressed.append(str(fact["key"]))
                    protected_regressions.append(str(fact["key"]))
            development_rows.append(
                {
                    "item_id": item_id,
                    "synthesis_fact_ids": [
                        fact["key"] for fact in item["synthesis_miss_facts"]
                    ],
                    "gained_fact_ids": gained,
                    "historical_ok_facts": len(item["historical_ok_facts"]),
                    "protected_regression_ids": regressed,
                    "selected_units": len(output["selected_unit_ids"]),
                    "candidate_source": output["candidate_source"],
                }
            )
        else:
            baseline_hits = []
            candidate_hits = []
            regressed = []
            for fact in item["atomic_facts"]:
                before = _covered(fact.get("value"), fact.get("text"), baseline)
                after = _covered(fact.get("value"), fact.get("text"), candidate)
                baseline_hits.append(before)
                candidate_hits.append(after)
                if before and not after:
                    fact_id = f"{item_id}:{fact['fact_id']}"
                    regressed.append(fact_id)
                    kidde_regressions.append(fact_id)
            kidde_baseline_covered += sum(baseline_hits)
            kidde_candidate_covered += sum(candidate_hits)
            kidde_rows.append(
                {
                    "item_id": item_id,
                    "atomic_facts": len(item["atomic_facts"]),
                    "baseline_covered": sum(baseline_hits),
                    "candidate_covered": sum(candidate_hits),
                    "regression_ids": regressed,
                    "selected_units": len(output["selected_unit_ids"]),
                    "candidate_source": output["candidate_source"],
                }
            )

    metrics = generation["metrics"]
    checks = {
        "development_synthesis_gains_gte_3_of_7": len(synthesis_gains) >= 3,
        "development_protected_regressions_zero": not protected_regressions,
        "kidde_guardrail_regressions_zero": not kidde_regressions,
        "kidde_candidate_not_worse": (
            kidde_candidate_covered >= kidde_baseline_covered
        ),
        "invalid_selector_outputs_zero": metrics["invalid_selector_outputs"] == 0,
        "candidate_invalid_citations_zero": not candidate_invalid_citations,
        "token_limit_stops_zero": metrics["token_limit_stops"] == 0,
        "actual_cost_below_internal_stop": (
            float(metrics["actual_cost_usd"])
            < float(prereg["budget"]["internal_stop_usd"])
        ),
        "canonical_target_calls_zero": generation["target_calls"] == 0,
    }
    passed = all(checks.values())
    body = {
        "status": (
            "GO_S219_TO_FULL_PROTECTED_REGRESSION"
            if passed
            else "NO_GO_S219_OMISSION_PILOT"
        ),
        "population": {
            "historical_multichunk_development_items": 7,
            "development_synthesis_facts": 7,
            "development_historical_ok_facts": 17,
            "kidde_multisource_guardrail_items": 2,
            "kidde_atomic_facts": 9,
            "canonical_targets": 0,
        },
        "metrics": {
            "development_synthesis_gains": len(synthesis_gains),
            "development_synthesis_gain_ids": synthesis_gains,
            "development_protected_regressions": protected_regressions,
            "kidde_baseline_facts_covered": kidde_baseline_covered,
            "kidde_candidate_facts_covered": kidde_candidate_covered,
            "kidde_regressions": kidde_regressions,
            "candidate_invalid_citations": candidate_invalid_citations,
            **metrics,
        },
        "checks": checks,
        "development_rows": development_rows,
        "kidde_rows": kidde_rows,
        "decision": {
            "next": (
                "full_35_question_protected_regression"
                if passed
                else "close_exact_s157_multichunk_post_answer_line"
            ),
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "external_validation_claimed": False,
        },
        "invariants": {
            "chunks_v2": "ACTIVE",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(
        RESULT,
        sealed_artifact("s219_omission_pilot_result_v1", body),
    )
    print(
        json.dumps(
            {
                "status": body["status"],
                "synthesis_gains": len(synthesis_gains),
                "protected_regressions": len(protected_regressions),
                "kidde": f"{kidde_candidate_covered}/{kidde_baseline_covered}",
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
