#!/usr/bin/env python3
"""Join selected S114 source receipts to frozen retrieval and serving positions."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "evals/s114_partial_evidence_search_v1.json"
POOLS = ROOT / "evals/s102_toc_pools.json"
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
OUT = ROOT / "evals/s114_partial_evidence_membership_v1.json"

RECEIPTS = {
    "cat017": [
        ("5bb83899-9d94-4fdd-8d42-24a670a036c5", "exact_one_licence_per_clip_loop"),
    ],
    "hp002": [
        ("a64c168c-c927-4f8b-a179-e465e6df3976", "v01_v02_switch_positions"),
        ("5b6a3a19-a924-4cf4-9513-bd50786ee3d9", "above_below_100_direction"),
    ],
    "hp010": [
        ("64cecd3f-204f-456e-91cc-e563280b1b99", "autosearch_procedure"),
        ("155a90fe-8c3f-484e-a617-7637fe29b547", "level3_and_memory_unlock"),
    ],
    "hp013": [
        ("a19e8735-0e84-471a-9224-4be148cc65b9", "pwr_r_input_voltage"),
        ("af577289-5d7f-4dfc-9187-8a3aca92d40d", "lithium_rtc_battery"),
    ],
    "hp015": [
        ("8954b9b2-18a0-464e-9e17-cc756d944b7c", "zone_disconnect_procedure"),
        ("fdb14497-4a5a-43db-a5f3-90f36448663e", "capacity_32_per_zone"),
    ],
}


def position(rows: list[dict], row_id: str) -> int | None:
    for index, row in enumerate(rows, start=1):
        if str(row.get("id")) == row_id:
            return index
    return None


def main() -> int:
    search = json.loads(SEARCH.read_text(encoding="utf-8"))
    pools = json.loads(POOLS.read_text(encoding="utf-8"))
    contexts = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    search_by_qid = {row["qid"]: row for row in search["rows"]}
    context_by_qid = {row["qid"]: row["context"] for row in contexts["rows"]}

    rows = []
    for qid, selected in RECEIPTS.items():
        candidate_by_id = {
            str(row["id"]): row for row in search_by_qid[qid]["candidate_rows"]
        }
        pool = pools[qid]
        context = context_by_qid[qid]
        receipts = []
        for row_id, role in selected:
            candidate = candidate_by_id.get(row_id)
            pool_row = next((row for row in pool if str(row.get("id")) == row_id), None)
            context_row = next(
                (row for row in context if str(row.get("id")) == row_id), None
            )
            if not candidate and not pool_row and not context_row:
                raise RuntimeError(f"{qid}: selected receipt {row_id} is not auditable")
            source = candidate or context_row or pool_row or {}
            receipts.append(
                {
                    "id": row_id,
                    "role": role,
                    "source_file": source.get("source_file"),
                    "page_number": source.get("page_number"),
                    "content_signals": (candidate or {}).get("content_signals", []),
                    "pool_position": position(pool, row_id),
                    "final_context_position": position(context, row_id),
                }
            )
        rows.append(
            {
                "qid": qid,
                "fact_key": search_by_qid[qid]["fact_key"],
                "receipts": receipts,
            }
        )

    payload = {
        "instrument": "s114_partial_evidence_membership_v1",
        "status": "frozen_pool_and_context_membership_receipt",
        "retrieval_pool": str(POOLS.relative_to(ROOT)).replace("\\", "/"),
        "serving_context": str(CONTEXTS.relative_to(ROOT)).replace("\\", "/"),
        "rows": rows,
        "cost_receipt": {
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
