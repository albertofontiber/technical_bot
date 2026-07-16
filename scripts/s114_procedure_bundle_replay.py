#!/usr/bin/env python3
"""Replay the shadow procedure-bundle selector over all frozen S113 questions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.procedure_bundle_coverage import (
    select_procedure_bundle_coverage,
    verify_source_span_receipt,
)

CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
SLICE = ROOT / "evals/s114_five_product_corpus_slice_v1.json"
OUT = ROOT / "evals/s114_procedure_bundle_replay_v1.json"
TARGETS = {
    "cat017": {
        "receipt_ids": {
            "4c186fb2-aa4b-4ca0-b316-c12ebab59712",
            "5bb83899-9d94-4fdd-8d42-24a670a036c5",
        },
        "required_terms": ["licencia", "cada circuito de lazo", "CLIP"],
    },
    "hp002": {
        "receipt_ids": {"a64c168c-c927-4f8b-a179-e465e6df3976"},
        "required_terms": ["V01", "V02"],
    },
    "hp010": {
        "receipt_ids": {"155a90fe-8c3f-484e-a617-7637fe29b547"},
        "required_terms": ["Nivel 3", "desbloquear"],
    },
}


def build_payload() -> dict:
    contexts = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    corpus = json.loads(SLICE.read_text(encoding="utf-8"))["rows"]
    rows = []
    for frozen in contexts["rows"]:
        selected, trace = select_procedure_bundle_coverage(
            frozen["question"], frozen["context"], corpus
        )
        rows.append(
            {
                "qid": frozen["qid"],
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_facets": [row["procedure_bundle_facet"] for row in selected],
                "selected_receipts": [
                    {
                        "candidate_id": str(row["id"]),
                        "manufacturer": row.get("manufacturer"),
                        "product_model": row.get("product_model"),
                        "rule_match": row["procedure_bundle_rule_match"],
                        "shadow_only": row["procedure_bundle_shadow_only"],
                        "source_spans": row["coverage_cards"],
                        "receipt_verified": all(
                            verify_source_span_receipt(row, card)
                            for card in row["coverage_cards"]
                        ),
                    }
                    for row in selected
                ],
                "trace": trace,
            }
        )
    by_qid = {row["qid"]: row for row in rows}
    target_row_selected = {
        qid: bool(target["receipt_ids"] & set(by_qid[qid]["selected_ids"]))
        for qid, target in TARGETS.items()
    }
    target_terms_in_served_spans = {
        qid: all(
            term.casefold() in "\n".join(
                card["quote"]
                for receipt in by_qid[qid]["selected_receipts"]
                for card in receipt["source_spans"]
            ).casefold()
            for term in target["required_terms"]
        )
        for qid, target in TARGETS.items()
    }
    recovered = {
        qid: target_row_selected[qid] and target_terms_in_served_spans[qid]
        for qid in TARGETS
    }
    protected_holds = {
        qid: by_qid[qid]["selected_ids"] == [] for qid in ("hp013", "hp015")
    }
    questions_with_appends = sum(bool(row["selected_ids"]) for row in rows)
    receipts = [
        receipt for row in rows for receipt in row["selected_receipts"]
    ]
    non_targets = [row for row in rows if row["qid"] not in TARGETS]
    product_scoped_controls = [
        row for row in non_targets if row["trace"]["product_scoped_candidates"] > 0
    ]
    potential_controls_by_facet = {
        facet: sum(facet in row["trace"]["potential_facets"] for row in non_targets)
        for facet in (
            "explicit_intra_document_reference",
            "procedural_access_prerequisite",
            "quantified_licensed_loop_prerequisite",
        )
    }
    gate = {
        "questions": len(rows),
        "target_row_selected": target_row_selected,
        "target_terms_in_served_spans": target_terms_in_served_spans,
        "target_recovered": recovered,
        "target_recovered_count": sum(recovered.values()),
        "protected_evaluation_holds_unchanged": protected_holds,
        "questions_with_shadow_appends": questions_with_appends,
        "non_target_questions": len(non_targets),
        "product_scoped_non_target_controls": len(product_scoped_controls),
        "selected_product_scoped_non_target_controls": sum(
            bool(row["selected_ids"]) for row in product_scoped_controls
        ),
        "potential_non_target_controls_by_facet": potential_controls_by_facet,
        "max_selected_per_question": max(map(lambda row: len(row["selected_ids"]), rows)),
        "all_source_span_receipts_verified": bool(receipts)
        and all(receipt["receipt_verified"] for receipt in receipts),
        "database_get_requests": 0,
        "database_writes": 0,
        "model_calls": 0,
    }
    gate["interpretation"] = (
        "GO_LOCAL_KNOWN_COHORT_SHADOW"
        if len(rows) == 39
        and all(recovered.values())
        and all(protected_holds.values())
        and gate["max_selected_per_question"] <= 1
        and gate["all_source_span_receipts_verified"]
        else "NO_GO_LOCAL_KNOWN_COHORT_SHADOW"
    )
    payload = {
        "instrument": "s114_procedure_bundle_replay_v1",
        "status": "known_cohort_shadow_not_release_evidence",
        "selector_inputs_exclude": ["qid", "facts", "expected_values", "gold_receipt_ids"],
        "gate": gate,
        "rows": rows,
        "limitations": [
            "The candidate slice is scoped to five known products and is not held out.",
            "Recovery requires the decisive terms inside exact bounded source spans.",
            "Only product-scoped and per-facet eligible controls are meaningful precision controls.",
            "A bounded evidence recovery is retrieval-stage progress, not an OK claim.",
            "The lane is not integrated into production serving.",
        ],
    }
    return payload


def main() -> int:
    payload = build_payload()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate = payload["gate"]
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
