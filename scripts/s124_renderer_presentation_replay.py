"""Zero-call presentation replay for source_bound_renderer_s124_v1."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s122_enforced_answer_contract_replay import build_report as build_s122_report
from src.rag.answer_planner import (
    SOURCE_BOUND_RENDERER_CURRENT,
    _closed_loop_has_unsafe_eol_claim,
)

OUTPUT = ROOT / "evals" / "s124_renderer_presentation_replay_v1.json"


def build_report() -> dict[str, Any]:
    report = build_s122_report(renderer_contract_version=SOURCE_BOUND_RENDERER_CURRENT)
    rows = {row["qid"]: row for row in report["rows"]}
    hp009 = rows["hp009"]["answer_after"]
    hp017 = rows["hp017"]["answer_after"]
    presentation_checks = {
        "renderer_contract_versioned": (
            report["versions"]["renderer"] == "source_bound_renderer_s124_v1"
        ),
        "hp009_internal_validation_language_removed": (
            "respuesta generada no superó la validación factual" not in hp009.casefold()
        ),
        "hp009_raw_english_removed": not any(
            phrase in hp009.casefold()
            for phrase in (
                "on left panel",
                "on right panel",
                "complete loop circuit",
            )
        ),
        "hp009_product_scope_retained": "ZX2e/ZX5e" in hp009,
        "hp009_eol_safety_retained": (
            "no especifica una resistencia de fin de línea" in hp009
            and "circuito cerrado" in hp009
            and not _closed_loop_has_unsafe_eol_claim(hp009)
        ),
        "hp009_obligations_2_of_2": (
            rows["hp009"]["final_validation"]["total"] == 2
            and rows["hp009"]["final_validation"]["covered"] == 2
        ),
        "hp017_internal_operation_removed": "cause_effect_menu_path" not in hp017,
        "hp017_malformed_source_markup_removed": ".; **" not in hp017,
        "hp017_prerequisite_mislabel_removed": "estos prerrequisitos" not in hp017,
        "hp017_conflict_humanized": (
            "número de menú de Causa y Efecto" in hp017
            and "No selecciones ningún número de menú" in hp017
        ),
        "hp017_fail_closed_retained": (
            rows["hp017"]["action"] == "fail_closed"
            and rows["hp017"]["query_core_coverage"] is False
        ),
        "hp017_obligations_2_of_2": (
            rows["hp017"]["final_validation"]["total"] == 2
            and rows["hp017"]["final_validation"]["covered"] == 2
        ),
        "hp017_conflict_safe": (
            rows["hp017"]["final_conflict_validation"]["total"] == 1
            and rows["hp017"]["final_conflict_validation"]["safe"] == 1
            and not rows["hp017"]["final_conflict_validation"]["unsafe"]
        ),
        "all_s122_safety_and_population_checks_retained": all(
            report["checks"].values()
        ),
    }
    report.update(
        {
            "instrument": "s124_renderer_presentation_replay_v1",
            "status": (
                "LOCAL_RENDERER_PRESENTATION_GO"
                if all(presentation_checks.values())
                else "LOCAL_RENDERER_PRESENTATION_NO_GO"
            ),
            "authority": "local_deterministic_presentation_replay_only",
            "presentation_checks": presentation_checks,
            "limitations": [
                "Cached-answer replay validates deterministic presentation only.",
                "No model, network, retrieval, rerank, judge or database call is made.",
                "The replay does not authorize deployment or corpus migration.",
            ],
        }
    )
    return report


def main() -> int:
    report = build_report()
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "presentation_checks": report["presentation_checks"],
                "counts": report["counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "LOCAL_RENDERER_PRESENTATION_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
