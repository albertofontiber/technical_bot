#!/usr/bin/env python3
"""Run the frozen non-target mutation/negative gate for S249."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.quantitative_claim_contract import (  # noqa: E402
    extract_quantitative_fields,
    find_partial_quantitative_claims,
)
from src.rag.relation_complete_highlights import (  # noqa: E402
    JOINER,
    build_relation_complete_highlights,
)
from src.rag.visual_gold import write_json  # noqa: E402

COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
BASELINES = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
BASELINE_SCORING = ROOT / "evals/s193_terra_id_planner_deterministic_append_v1.json"
PRIOR_ATOMS = ROOT / "evals/s245_relation_complete_highlight_candidates_v1.json"
OUTPUT = ROOT / "evals/s249_partial_quantitative_claim_contract_gate_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _nonblank_count(text: str) -> int:
    return sum(not char.isspace() for char in text)


def _covered_nonblank_offsets(source: str, spans: set[tuple[int, int]]) -> int:
    offsets = {index for start, end in spans for index in range(start, end)}
    return sum(index in offsets and not char.isspace() for index, char in enumerate(source))


def _remove_field(text: str, raw: str) -> str:
    index = text.rfind(raw)
    if index < 0:
        raise ValueError("mutation field not found")
    return text[:index] + "[valor omitido]" + text[index + len(raw):]


def build_report() -> dict[str, Any]:
    cohort = _load(COHORT)
    gold = _load(GOLD)
    baselines = _load(BASELINES)
    baseline_scoring = _load(BASELINE_SCORING)
    prior_atoms = _load(PRIOR_ATOMS)
    gold_by_id = {row["item_id"]: row for row in gold["items"]}
    answer_by_id = {row["item_id"]: row["answer"] for row in baselines["receipts"]}
    score_by_id = {row["item_id"]: row for row in baseline_scoring["rows"]}
    language_by_id = {row["item_id"]: row["language"] for row in prior_atoms["rows"]}

    rows: list[dict[str, Any]] = []
    mutation_cases = mutation_hits = 0
    negative_cases = false_positives = 0
    source_bound_failures = 0
    global_nonblank = global_covered = 0
    represented_questions: set[str] = set()
    represented_manufacturers: set[str] = set()
    represented_languages: set[str] = set()
    represented_strata: set[str] = set()
    item_densities: list[float] = []
    real_baseline_findings = 0
    real_baseline_findings_with_missing_gold = 0

    for item in cohort["items"]:
        item_id = str(item["item_id"])
        source = str(item["excerpt"])
        atoms = build_relation_complete_highlights(
            source, fragment_number=1, candidate_id=str(item["chunk_id"])
        )
        qualifying = []
        spans: set[tuple[int, int]] = set()
        mutation_rows = []
        for atom in atoms:
            if "numeric_bundle" not in atom.reason_labels:
                continue
            fields = extract_quantitative_fields(atom.content)
            unique = {field.canonical for field in fields}
            if len(unique) < 2:
                continue
            reconstructed = JOINER.join(source[slice(*span)] for span in atom.source_spans)
            source_bound_failures += int(reconstructed != atom.content)
            qualifying.append(atom)
            spans.update(atom.source_spans)
            represented_questions.add(item_id)
            represented_manufacturers.add(str(item["manufacturer"]))
            represented_languages.add(str(language_by_id[item_id]))
            represented_strata.add(str(item["stratum"]))

            # Remove the last distinct field deterministically. All other source
            # bytes and the fragment citation remain available to the detector.
            target = fields[-1]
            mutated = _remove_field(atom.content, target.raw) + " [F1]"
            findings = find_partial_quantitative_claims(
                mutated, [{"id": item["chunk_id"], "content": atom.content}]
            )
            mutation_cases += 1
            caught = any(target.canonical in row.missing_fields for row in findings)
            mutation_hits += int(caught)

            complete_findings = find_partial_quantitative_claims(
                atom.content + " [F1]",
                [{"id": item["chunk_id"], "content": atom.content}],
            )
            negative_cases += 1
            false_positives += int(bool(complete_findings))

            unrelated = f"Dato auxiliar: {fields[0].raw}. [F1]"
            unrelated_findings = find_partial_quantitative_claims(
                unrelated,
                [{"id": item["chunk_id"], "content": atom.content}],
            )
            negative_cases += 1
            false_positives += int(bool(unrelated_findings))
            mutation_rows.append(
                {
                    "atom_id": atom.atom_id,
                    "field_count": len(unique),
                    "removed_field": target.canonical,
                    "mutation_detected": caught,
                    "complete_false_positive": bool(complete_findings),
                    "unrelated_false_positive": bool(unrelated_findings),
                }
            )

        nonblank = _nonblank_count(source)
        covered = _covered_nonblank_offsets(source, spans)
        density = covered / nonblank if nonblank else 0.0
        global_nonblank += nonblank
        global_covered += covered
        item_densities.append(density)

        baseline_findings = find_partial_quantitative_claims(
            answer_by_id[item_id],
            [{"id": item["chunk_id"], "content": source}],
        )
        missing_quotes = {
            point["exact_quote"]
            for point, scored in zip(
                gold_by_id[item_id]["answer_points"], score_by_id[item_id]["points"]
            )
            if not scored["baseline"]
        }
        baseline_supported = sum(
            any(quote in finding.source_content for quote in missing_quotes)
            for finding in baseline_findings
        )
        real_baseline_findings += len(baseline_findings)
        real_baseline_findings_with_missing_gold += baseline_supported
        rows.append(
            {
                "item_id": item_id,
                "manufacturer": item["manufacturer"],
                "language": language_by_id[item_id],
                "stratum": item["stratum"],
                "qualifying_atoms": len(qualifying),
                "nonblank_source_chars": nonblank,
                "qualifying_nonblank_chars": covered,
                "source_span_density": density,
                "mutations": mutation_rows,
                "real_baseline_findings": len(baseline_findings),
                "real_baseline_findings_with_missing_gold": baseline_supported,
            }
        )

    true_positives = mutation_hits
    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 0.0
    metrics = {
        "qualifying_atoms": mutation_cases,
        "represented_questions": len(represented_questions),
        "represented_manufacturers": len(represented_manufacturers),
        "represented_languages": sorted(represented_languages),
        "represented_strata": sorted(represented_strata),
        "mutation_recall": mutation_hits / mutation_cases if mutation_cases else 0.0,
        "negative_precision": precision,
        "false_positive_rate": false_positives / negative_cases if negative_cases else 1.0,
        "global_source_span_density": global_covered / global_nonblank if global_nonblank else 1.0,
        "median_item_source_span_density": statistics.median(item_densities),
        "source_bound_failures": source_bound_failures,
        "baseline_answer_mutations": 0,
        "real_baseline_findings": real_baseline_findings,
        "real_baseline_findings_with_missing_gold": real_baseline_findings_with_missing_gold,
    }
    checks = {
        "qualifying_atoms_min": metrics["qualifying_atoms"] >= 12,
        "questions_min": metrics["represented_questions"] >= 8,
        "manufacturers_min": metrics["represented_manufacturers"] >= 6,
        "languages_required": metrics["represented_languages"] == ["en", "es"],
        "strata_required": metrics["represented_strata"] == ["prose", "table"],
        "mutation_recall_min": metrics["mutation_recall"] >= 0.90,
        "negative_precision_min": metrics["negative_precision"] >= 0.95,
        "false_positive_rate_max": metrics["false_positive_rate"] <= 0.05,
        "global_density_max": metrics["global_source_span_density"] <= 0.25,
        "median_density_max": metrics["median_item_source_span_density"] <= 0.30,
        "source_bound_failures_zero": metrics["source_bound_failures"] == 0,
        "baseline_answer_mutations_zero": metrics["baseline_answer_mutations"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "s249_partial_quantitative_claim_contract_gate_v1",
        "status": "GO_TO_FRONTIER_DESIGN_REVIEW" if passed else "NO_GO_CLOSE_S249_V1",
        "population": {
            "questions": 14,
            "manufacturers": 14,
            "target_question_overlap": 0,
        },
        "metrics": metrics,
        "checks": checks,
        "rows": rows,
        "decision": {
            "frontier_review_authorized": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "tune_same_cohort": False,
        },
        "cost": {"model_calls": 0, "usd": 0},
    }


def main() -> int:
    report = build_report()
    write_json(OUTPUT, report)
    print(json.dumps({"status": report["status"], **report["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

