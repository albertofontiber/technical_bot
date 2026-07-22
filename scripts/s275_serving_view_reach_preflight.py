"""S275: deterministic reach audit for a generalized serving-view candidate.

This is a read-only preflight.  It measures whether each S274 residual's exact
source-bound obligation span was present in the generator view frozen by S113.
It does not score answers, call models, or authorize another target probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "evals" / "s113_full_contexts_freeze_v1.json"
PACKET_PATH = ROOT / "evals" / "s235_direct_clause_bound_score_packet_v1.json"

INPUT_SHA256_LF = {
    "evals/s113_full_contexts_freeze_v1.json": (
        "556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498"
    ),
    "evals/s235_direct_clause_bound_score_packet_v1.json": (
        "b9d7d4036c9aa00aeb521628da7e876cbc04ccb7ea6fa48a130960c43f2c8f48"
    ),
}

TARGET_IDS = (
    "obl_2f5d79e354b9",
    "obl_7bba8d03d496",
    "obl_a5d9fa1f9253",
    "obl_015f9b9aaa3a",
    "obl_b2043cd4379b",
    "obl_7aa723717412",
)

# The output sibling (7aa7) is already selected and contains all three matcher
# anchors.  Only the input sibling (b2043) is wholly absent from the serving
# view.  This is a causal reach hypothesis, not conversion credit.
PURE_SERVING_VIEW_GAPS = {"obl_b2043cd4379b"}
SELECTED_DEFINITION_SIBLING = "obl_7aa723717412"


def _sha256_lf(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(set(ranges)):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _intersection(
    span_start: int, span_end: int, ranges: list[tuple[int, int]]
) -> tuple[int, list[list[int]]]:
    intersections: list[list[int]] = []
    for start, end in ranges:
        left = max(span_start, start)
        right = min(span_end, end)
        if left < right:
            intersections.append([left, right])
    return sum(end - start for start, end in intersections), intersections


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def _load_obligations(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    obligations: dict[str, dict[str, Any]] = {}
    for item in packet["items"]:
        for obligation in item["obligations"]:
            oid = obligation["obligation_id"]
            if oid in TARGET_IDS:
                obligations[oid] = {"qid": item["qid"], **obligation}
    if set(obligations) != set(TARGET_IDS):
        missing = sorted(set(TARGET_IDS) - set(obligations))
        raise ValueError(f"missing target obligations: {missing}")
    return obligations


def build_report() -> dict[str, Any]:
    for relative, expected in INPUT_SHA256_LF.items():
        actual = _sha256_lf(ROOT / relative)
        if actual != expected:
            raise ValueError(f"input hash mismatch for {relative}: {actual}")

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    obligations = _load_obligations(packet)
    rows_by_qid = {row["qid"]: row for row in freeze["rows"]}

    targets: dict[str, dict[str, Any]] = {}
    for oid in TARGET_IDS:
        obligation = obligations[oid]
        qid = obligation["qid"]
        candidate_id = obligation["candidate_id"]
        row = rows_by_qid[qid]
        candidates = {chunk["id"]: chunk for chunk in row["context"]}
        if candidate_id not in candidates:
            raise ValueError(f"candidate {candidate_id} absent from S113 row {qid}")
        candidate = candidates[candidate_id]
        content = str(candidate.get("content") or "")
        span_start = int(obligation["source_start"])
        span_end = int(obligation["source_end"])
        if not (0 <= span_start < span_end <= len(content)):
            raise ValueError(f"invalid source span for {oid}")

        if candidate_id in row["prefix_ids"]:
            view_kind = "protected_prefix_full_chunk"
            served_ranges = [(0, len(content))]
        else:
            view_kind = "validated_coverage_cards"
            served_ranges = _merge(
                [
                    (int(card["start"]), int(card["end"]))
                    for card in candidate.get("served_coverage_cards") or []
                ]
            )
        covered_chars, overlap_ranges = _intersection(
            span_start, span_end, served_ranges
        )
        served_overlap_text = "\n".join(content[start:end] for start, end in overlap_ranges)
        required_anchors = [str(anchor) for anchor in obligation["required_anchors"]]
        normalized_overlap = _norm(served_overlap_text)
        required_anchor_hits = [
            anchor for anchor in required_anchors if _norm(anchor) in normalized_overlap
        ]
        span_chars = span_end - span_start
        if covered_chars == span_chars:
            status = "FULL"
        elif covered_chars == 0:
            status = "ABSENT"
        else:
            status = "PARTIAL"

        targets[oid] = {
            "qid": qid,
            "candidate_id": candidate_id,
            "fragment_number": obligation["fragment_number"],
            "view_kind": view_kind,
            "source_span": [span_start, span_end],
            "source_span_chars": span_chars,
            "served_ranges": [list(pair) for pair in served_ranges],
            "served_overlap_ranges": overlap_ranges,
            "served_overlap_chars": covered_chars,
            "served_overlap_pct": round(100.0 * covered_chars / span_chars, 2),
            "required_anchors": required_anchors,
            "required_anchor_hits_in_served_overlap": required_anchor_hits,
            "all_required_anchors_in_served_overlap": (
                len(required_anchor_hits) == len(required_anchors)
            ),
            "status": status,
            "pure_serving_view_gap": oid in PURE_SERVING_VIEW_GAPS,
            "definition_sibling_role": (
                "missing_sibling"
                if oid in PURE_SERVING_VIEW_GAPS
                else "selected_sibling"
                if oid == SELECTED_DEFINITION_SIBLING
                else None
            ),
        }

    histogram = {
        status: sum(row["status"] == status for row in targets.values())
        for status in ("FULL", "PARTIAL", "ABSENT")
    }
    report: dict[str, Any] = {
        "schema": "s275_serving_view_reach_preflight_v1",
        "status": "READ_ONLY_PREFLIGHT_COMPLETE",
        "inputs_sha256_lf": INPUT_SHA256_LF,
        "population": {
            "target_ids": list(TARGET_IDS),
            "target_count": len(TARGET_IDS),
            "source": "six S274 synthesis residuals",
        },
        "method": {
            "prefix_view": "full frozen chunk",
            "coverage_view": "union of S113 served_coverage_cards",
            "unit": "exact S235 source_start/source_end span",
            "answer_scoring": False,
            "model_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "targets": targets,
        "summary": {
            "view_status_histogram": histogram,
            "pure_serving_view_gaps": sorted(PURE_SERVING_VIEW_GAPS),
            "definition_sibling_card_direct_target": sorted(PURE_SERVING_VIEW_GAPS),
            "already_selected_definition_sibling": SELECTED_DEFINITION_SIBLING,
            "direct_causal_candidate_count": len(PURE_SERVING_VIEW_GAPS),
            "cannot_by_itself_supply_required_plus_5": True,
        },
        "decision": {
            "gold_round_2": "CLOSED_NO_GO",
            "serving_view_candidate": "bounded missing-definition-sibling card",
            "execution_authorized": False,
            "probe_5_on_same_targets_forbidden": True,
            "next_gate": "fresh disjoint offline census and mutation cohort before any paid run",
        },
    }
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report["result_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        expected = json.loads(args.check.read_text(encoding="utf-8"))
        if expected != report:
            raise SystemExit(f"artifact drift: {args.check}")
        print(f"OK: {args.check}")
        return
    print(rendered, end="")


if __name__ == "__main__":
    main()
