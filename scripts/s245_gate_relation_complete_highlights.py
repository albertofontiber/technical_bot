#!/usr/bin/env python3
"""Open the frozen S245 non-target representation gate exactly once."""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.relation_complete_highlights import (  # noqa: E402
    MAX_ATOM_CHARS,
    MAX_ATOMS_PER_FRAGMENT,
    build_relation_complete_highlights,
    reconstruct_highlight_content,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s245_relation_complete_highlight_gate_freeze_v1.yaml"
PREREG = ROOT / "evals/s245_relation_complete_highlight_prereg_v1.yaml"
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
CANDIDATES = ROOT / "evals/s245_relation_complete_highlight_candidates_v1.json"
RESULT = ROOT / "evals/s245_relation_complete_highlight_gate_v1.json"

EN_ITEMS = {
    "s147_src_01", "s147_src_04", "s147_src_06", "s147_src_08",
    "s147_src_09", "s147_src_11", "s147_src_14",
}
ES_ITEMS = {
    "s147_src_02", "s147_src_03", "s147_src_05", "s147_src_07",
    "s147_src_10", "s147_src_12", "s147_src_13",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def verify_freeze() -> dict[str, Any]:
    value = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    if value.get("status") != "FROZEN_BEFORE_REAL_GATE_OPEN":
        raise RuntimeError("S245 gate freeze is not active")
    for spec in value["frozen_inputs"].values():
        path = ROOT / spec["path"]
        if file_sha(path) != spec["sha256"]:
            raise RuntimeError(f"S245 frozen input drift: {spec['path']}")
    return value


def serialize_atom(atom: Any) -> dict[str, Any]:
    return {
        "atom_id": atom.atom_id,
        "fragment_number": atom.fragment_number,
        "candidate_id": atom.candidate_id,
        "reason_labels": list(atom.reason_labels),
        "source_spans": [list(span) for span in atom.source_spans],
        "content": atom.content,
        "content_sha256": atom.content_sha256,
    }


def nonblank_density(source: str, atoms: list[Any]) -> tuple[int, int, float]:
    covered = bytearray(len(source))
    for atom in atoms:
        for start, end in atom.source_spans:
            for index in range(start, end):
                if not source[index].isspace():
                    covered[index] = 1
    denominator = sum(not char.isspace() for char in source)
    numerator = sum(covered)
    return numerator, denominator, numerator / max(1, denominator)


def ratio(hits: int, total: int) -> float:
    return hits / max(1, total)


def main() -> int:
    if CANDIDATES.exists() or RESULT.exists():
        raise RuntimeError("S245 real gate artifacts already exist; v1 cannot retry")
    verify_freeze()
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))

    # Build all source-form candidates before loading answer-point gold.
    source_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_items = source_payload["items"]
    if {row["item_id"] for row in source_items} != EN_ITEMS | ES_ITEMS:
        raise RuntimeError("S245 language partition or source population drift")
    candidate_rows: list[dict[str, Any]] = []
    source_bound_failures = 0
    total_covered = total_nonblank = 0
    item_densities: list[float] = []
    atoms_by_item: dict[str, list[Any]] = {}
    for item in source_items:
        atoms = build_relation_complete_highlights(
            item["excerpt"],
            fragment_number=1,
            candidate_id=item["chunk_id"],
        )
        atoms_by_item[item["item_id"]] = atoms
        for atom in atoms:
            if reconstruct_highlight_content(item["excerpt"], atom) != atom.content:
                source_bound_failures += 1
            if hashlib.sha256(atom.content.encode("utf-8")).hexdigest() != atom.content_sha256:
                source_bound_failures += 1
            if len(atom.content) > MAX_ATOM_CHARS:
                source_bound_failures += 1
        if len(atoms) > MAX_ATOMS_PER_FRAGMENT:
            source_bound_failures += 1
        covered, nonblank, density = nonblank_density(item["excerpt"], atoms)
        total_covered += covered
        total_nonblank += nonblank
        item_densities.append(density)
        candidate_rows.append(
            {
                "item_id": item["item_id"],
                "stratum": item["stratum"],
                "language": "en" if item["item_id"] in EN_ITEMS else "es",
                "source_sha256": item["excerpt_sha256"],
                "atoms": [serialize_atom(atom) for atom in atoms],
                "nonblank_source_chars": nonblank,
                "nonblank_highlighted_chars": covered,
                "nonblank_span_density": density,
            }
        )
    candidate_body = {
        "schema": "s245_relation_complete_highlight_candidates_v1",
        "status": "BUILT_BEFORE_GOLD_LOAD",
        "population": {"items": len(candidate_rows)},
        "rows": candidate_rows,
    }

    # Only now open the immutable answer-point ledger and score single-atom recall.
    gold_payload = json.loads(GOLD.read_text(encoding="utf-8"))
    gold_items = {row["item_id"]: row for row in gold_payload["items"]}
    if set(gold_items) != set(atoms_by_item):
        raise RuntimeError("S245 source/gold item mismatch")
    scored_rows: list[dict[str, Any]] = []
    buckets = {
        "global": [0, 0], "table": [0, 0], "prose": [0, 0],
        "es": [0, 0], "en": [0, 0],
    }
    for item in source_items:
        item_id = item["item_id"]
        atoms = atoms_by_item[item_id]
        language = "en" if item_id in EN_ITEMS else "es"
        point_rows = []
        for point in gold_items[item_id]["answer_points"]:
            matches = [
                atom.atom_id
                for atom in atoms
                if point["exact_quote"] in atom.content
            ]
            hit = bool(matches)
            for bucket in ("global", item["stratum"], language):
                buckets[bucket][0] += int(hit)
                buckets[bucket][1] += 1
            point_rows.append(
                {
                    "claim_sha256": hashlib.sha256(
                        point["claim"].encode("utf-8")
                    ).hexdigest(),
                    "exact_quote_sha256": hashlib.sha256(
                        point["exact_quote"].encode("utf-8")
                    ).hexdigest(),
                    "single_atom_covered": hit,
                    "matching_atom_ids": matches,
                }
            )
        scored_rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "language": language,
                "points": point_rows,
            }
        )

    metrics = {
        "single_atom_quote_covered": buckets["global"][0],
        "answer_points": buckets["global"][1],
        "single_atom_quote_recall": ratio(*buckets["global"]),
        "table_recall": ratio(*buckets["table"]),
        "prose_recall": ratio(*buckets["prose"]),
        "real_es_recall": ratio(*buckets["es"]),
        "real_en_recall": ratio(*buckets["en"]),
        "global_nonblank_span_density": total_covered / max(1, total_nonblank),
        "median_item_nonblank_span_density": statistics.median(item_densities),
        "source_bound_failures": source_bound_failures,
        "atoms": sum(len(atoms) for atoms in atoms_by_item.values()),
    }
    gate = prereg["gate_a"]
    checks = {
        "minimum_single_atom_quote_count": metrics["single_atom_quote_covered"]
        >= gate["minimum_single_atom_quote_count"],
        "minimum_single_atom_quote_ratio": metrics["single_atom_quote_recall"]
        >= gate["minimum_single_atom_quote_ratio"],
        "minimum_table_recall": metrics["table_recall"] >= gate["minimum_table_recall"],
        "minimum_prose_recall": metrics["prose_recall"] >= gate["minimum_prose_recall"],
        "minimum_real_es_recall": metrics["real_es_recall"] >= gate["minimum_real_es_recall"],
        "minimum_real_en_recall": metrics["real_en_recall"] >= gate["minimum_real_en_recall"],
        "maximum_global_nonblank_span_density": metrics["global_nonblank_span_density"]
        <= gate["maximum_global_nonblank_span_density"],
        "maximum_median_item_nonblank_span_density": metrics["median_item_nonblank_span_density"]
        <= gate["maximum_median_item_nonblank_span_density"],
        "source_bound_failures_zero": source_bound_failures == 0,
    }
    passed = all(checks.values())
    result_body = {
        "schema": "s245_relation_complete_highlight_gate_v1",
        "status": "GO_TO_PAIRED_NONTARGET_AB" if passed else "NO_GO_CLOSE_S245_V1",
        "metrics": metrics,
        "checks": checks,
        "rows": scored_rows,
        "decision": {
            "gate_b_authorized": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "tune_same_cohort": False,
        },
        "cost": {"model_calls": 0, "network_calls": 0, "database_calls": 0, "usd": 0},
    }
    candidates = {**candidate_body, "result_sha256": stable_sha(candidate_body)}
    result = {**result_body, "result_sha256": stable_sha(result_body)}
    CANDIDATES.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

