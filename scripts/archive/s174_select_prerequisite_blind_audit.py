"""Select the frozen S174 adjudication packet without reading candidate quotes."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s174_prerequisite_corpus_census_v1.json"
OUT = ROOT / "evals/s174_prerequisite_blind_audit_packet_v1.json"
SOURCE_SHA = "ba9162cb05de0d125723a747830e7017e17462ce775e8ddb3e3a89e8d03e1774"
SEED = "s174_blind_v1"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def main() -> None:
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError("S174 census drift")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    access_by_manufacturer = defaultdict(list)
    entitlements = []
    for row in source["candidates"]:
        if row["facet"] == "access_prerequisite":
            access_by_manufacturer[row["manufacturer"]].append(row)
        elif row["facet"] == "quantified_entitlement":
            entitlements.append(row)
    selected = []
    selection_receipt = {}
    for manufacturer in sorted(access_by_manufacturer):
        rows = sorted(
            access_by_manufacturer[manufacturer], key=lambda row: row["candidate_id"]
        )[:2]
        selected.extend(rows)
        selection_receipt[manufacturer] = [row["candidate_id"] for row in rows]
    selected.extend(sorted(entitlements, key=lambda row: row["candidate_id"]))
    if len(access_by_manufacturer) != 10 or len(selected) != 37:
        raise ValueError("S174 frozen population expectation failed")

    selected.sort(
        key=lambda row: hashlib.sha256(
            f"{SEED}:{row['candidate_id']}".encode("utf-8")
        ).hexdigest()
    )
    items = [
        {
            "audit_id": f"s174_audit_{index:02d}",
            **row,
        }
        for index, row in enumerate(selected, 1)
    ]
    body = {
        "instrument": "s174_prerequisite_blind_audit_packet_v1",
        "status": "SEALED_BEFORE_CONTENT_ADJUDICATION",
        "source_census_sha256": SOURCE_SHA,
        "selection": {
            "seed": SEED,
            "access_manufacturers": len(access_by_manufacturer),
            "access_candidates": sum(
                row["facet"] == "access_prerequisite" for row in items
            ),
            "quantified_entitlement_candidates": sum(
                row["facet"] == "quantified_entitlement" for row in items
            ),
            "access_candidate_ids_by_manufacturer": selection_receipt,
        },
        "items": items,
        "authorization": {
            "content_adjudication": True,
            "model_calls": 0,
            "runtime_or_production": False,
        },
    }
    body["packet_sha256"] = stable_sha(body)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
